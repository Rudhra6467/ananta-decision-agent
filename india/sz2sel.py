"""SZ2 selection (registrations/sz2_v1.json, frozen 19 Oct 2026): how much of the book an SP1 index decision may use, and through which option
structure. Everything here is EXPLORATORY (every SP1 year has been seen; synthetic prices); the sizing never changes which decision is made.

  python -m india.sz2 select      the full run: today's-scale trades, the historical paths, the bootstraps, eligibility, the choice, the report
  python -m india.sz2 rehearse    the same with 200 paths and no ledger rows (a rehearsal)

Inputs: gold/studies/SZ2_trades.parquet (2017-2023 walk-forward decisions) and the holdout-era table (2024-01-01..2026-10-16, built by
`python -m india.sz2 trades_holdout` through the logged sealed purpose sz2_selection, Madhav 23 Oct 2026), both per trade x structure.
Decisions as stated (Madhav, 23 Oct 2026): (a) the holdout-era policy trades are read through that logged purpose; (b) the IV shift is 0 and
stated (R01's measured shift comes after its four weeks, about 15 Nov, as one pre-registered sensitivity run). The margin proxy multiplier is
the one recorded once in manifests/sz2_margin_check.json (1.0 for both indices: the proxy was above Kite's figure in all five baskets).

Engine (sizing_rule, survival_simulation): W = equity at the session's start (open overnight positions at their 15:29 mark); at 09:16 the
NEXTOPEN exit is booked first and its gap against the 15:29 mark counts against the new session; each SP1 trade in decision order (Nifty
before Bank Nifty at the same point) is sized lots = floor(f x W / planned max loss per lot), cut to the budget (5% x W - today's realised loss
- the overnight gap loss - the planned max loss of open positions), and must fit the free cash (margin proxy); 0 lots = NO TRADE (size_zero,
budget or margin). Planned max losses, spreads and fees are recomputed at today's contracts (lot 65 Nifty, 30 Bank Nifty, each index at its
16 Oct 2026 close) with today's cost table. Because every entry fits the budget, the 5% daily limit can be reached only when a position loses
more than its planned max loss; sessions where any taken position's marked loss comes within 80% of its planned max loss, and any session with
an overnight gap loss of 5% of W, are replayed minute by minute (the limit closes everything at the next minute with doubled exit
half-spreads and stops new entries). A miss is a session whose loss exceeds 5% of W by more than its stop-close costs. A 22% drawdown from the
high-water mark pauses new entries (the paused path keeps its open positions to their exits; the unpaused path is reported beside it; in a
bootstrap path the pause ends trading).
"""
from __future__ import annotations

import datetime as dt
import json
import math
import sys
import time

import numpy as np
import pandas as pd

from india import costs, paths
from india import sz2 as Z

TODAY = dt.date(2026, 10, 16)
LOT_T = {"NIFTY": 65, "BANKNIFTY": 30}
FRACTIONS = (0.02, 0.03, 0.04, 0.05)
TIERS = (60_000.0, 200_000.0, 500_000.0, 1_000_000.0)
DEFAULT = ("LONG_ATM", 0.02)
DAY_LIMIT, PAUSE = 0.05, 0.22
PATHS, PATH_LEN, BLOCK, STAT_MEAN, SEED = 2000, 250, 20, 60, 20261019
WINDOWS = {"2024": (dt.date(2024, 1, 1), TODAY), "2017": (dt.date(2017, 1, 2), TODAY)}
SCENARIOS = ("a", "b", "c")
FLAG_AT = 0.8
NMIN = Z.NMIN


# ============================================================================================================================ trades at today's scale
def load_trades() -> pd.DataFrame:
    from india import sealed
    a = pd.read_parquet(paths.gold() / "studies" / "SZ2_trades.parquet")
    b = pd.read_parquet(sealed.sz2_output_dir("sz2_selection") / "SZ2_trades_holdout.parquet")
    t = pd.concat([a, b], ignore_index=True)
    t["date"] = pd.to_datetime(t["date"]).dt.date
    t["date_out"] = pd.to_datetime(t["date_out"]).dt.date
    return t[(t["date"] >= WINDOWS["2017"][0]) & (t["date"] <= TODAY)].reset_index(drop=True)


def scale_close() -> dict:
    from india import sealed
    df = sealed.read_sz2("sz2_selection", "scale_close")
    m = {"NIFTY 50": "NIFTY", "NIFTY BANK": "BANKNIFTY"}
    out = {m[n]: float(c) for n, c in zip(df["index_name"], df["close"])}
    if set(out) != set(LOT_T):
        raise SystemExit(f"the 16 Oct 2026 closes are missing: {out}")
    return out


def _hs(sym, p):
    return Z._hs(sym, p)


def today_scale(t: pd.DataFrame, idx_t: dict) -> pd.DataFrame:
    """Per available trade x structure: planned max loss, net P&L, entry costs, margin and the 15:29 mark per lot at today's contracts and cost
    table, for cost multipliers 1 and 2 (scenario c). GROSS is kept separate for the demeaned scenario (b)."""
    rows = []
    av = t[t["available"]].reset_index(drop=True)
    fee = lambda side, v: costs.cost("options", side, v, TODAY.year, when=TODAY)
    for r in av.itertuples(index=False):
        sym = r.index
        lot, I = LOT_T[sym], idx_t[sym]
        sc = I / r.entry_idx
        legs = json.loads(r.legs)
        p_in = [x * sc for x in json.loads(r.p_in)]
        p_out = [x * sc for x in json.loads(r.p_out)]
        p_s = [x * sc for x in json.loads(r.p_stress)] if r.p_stress else None
        hs_in = sum(_hs(sym, p) for p in p_in) * lot
        hs_out = sum(_hs(sym, p) for p in p_out) * lot * (2.0 if r.stopped else 1.0)
        f_in = sum(fee("buy" if s > 0 else "sell", p * lot) for (K, s), p in zip(legs, p_in))
        f_out = sum(fee("sell" if s > 0 else "buy", p * lot) for (K, s), p in zip(legs, p_out))
        gross = (r.v_out - r.v_in) * sc * lot
        rec = {"i": r.Index if hasattr(r, "Index") else None}
        for m in (1.0, 2.0):
            def exit_cost(ps):
                return 2 * sum(_hs(sym, p) for p in ps) * lot * m + sum(fee("sell" if s > 0 else "buy", p * lot) for (K, s), p in zip(legs, ps)) * m
            full = r.full_core_frac * lot * I + hs_in * m + f_in * m + exit_cost([0.05] * len(legs))
            ml = full
            if p_s is not None and r.stressed_core_frac == r.stressed_core_frac:
                ml = min(full, r.stressed_core_frac * lot * I + hs_in * m + f_in * m + exit_cost(p_s))
            ml = max(ml, 1.0)
            rec[f"ml_{int(m)}"] = ml
            rec[f"entry_cost_{int(m)}"] = (hs_in + f_in) * m
            rec[f"net_{int(m)}"] = gross - (hs_in + hs_out + f_in + f_out) * m
            rec[f"stopclose_{int(m)}"] = (sum(_hs(sym, p) for p in p_in) * lot + f_in) * m    # the extra exit half-spread and exit fees of a limit close
        rec["gross"] = gross
        long_prem = sum(p for (K, s), p in zip(legs, p_in) if s > 0) * lot
        shorts = [(K, s) for K, s in legs if s < 0]
        span = sum(abs(legs[0][0] - K) for K, s in shorts) * lot + 0.02 * lot * I * len(shorts)
        rec["margin"] = long_prem + span * MARGIN_MULT.get(sym, 1.0)
        rec["net_dated_R"] = r.net_R_dated
        rows.append(rec)
    x = pd.DataFrame(rows)
    out = pd.concat([av.drop(columns=["marks_R"]), x.drop(columns=["i"])], axis=1)
    out["marks_R"] = av["marks_R"].to_numpy()
    return out


MARGIN_MULT: dict = {}


# ============================================================================================================================ sessions x slots
class Slots:
    """For one structure and one scenario on one window: per session (in calendar order) up to two SP1 trades (Nifty, Bank Nifty) in decision
    order, with everything the engine needs per lot."""
    F = ("exists", "avail", "m_in", "m_out", "ml", "net", "ecost", "marg", "nextopen", "mark1529", "flag", "stopclose", "sym", "reason", "row")

    def __init__(self, days: list, tt: pd.DataFrame, t_all: pd.DataFrame, structure: str, scen: str):
        n = len(days)
        pos = {d: i for i, d in enumerate(days)}
        self.n = n
        self.days = days
        A = {f: np.zeros((n, 2)) for f in self.F}
        A["reason"] = np.full((n, 2), "", dtype=object)
        A["sym"] = np.full((n, 2), "", dtype=object)
        A["row"] = np.full((n, 2), -1)
        m = "2" if scen == "c" else "1"
        sub = tt[tt["structure"] == structure]
        key = {(d, i): q for q, d, i in zip(sub.index, sub["date"], sub["index"])}
        if scen == "b":
            g = sub.groupby(["index", "exit"])["gross"].transform("mean")
            net = (sub["gross"] - g) - (sub["net_1"].rsub(sub["gross"]))          # demeaned gross minus today's spreads and fees
            shift = -g
        else:
            net = sub[f"net_{m}"]
            shift = pd.Series(0.0, index=sub.index)
        self.marks = {}
        # unavailable rows (strike / liquidity) still occupy their slot as NO TRADE
        allrows = t_all[(t_all["structure"] == structure) & t_all["date"].isin(set(pos))]
        order = allrows.assign(_ix=allrows["index"].map({"NIFTY": 0, "BANKNIFTY": 1})).sort_values(["date", "m_in", "_ix"])
        fill = {}
        for r in order.itertuples():
            k = pos[r.date]
            j = fill.get(k, 0)
            if j > 1:
                continue
            fill[k] = j + 1
            A["exists"][k, j] = 1
            A["sym"][k, j] = r.index
            A["m_in"][k, j] = r.m_in
            A["m_out"][k, j] = r.m_out + (NMIN if r.next_day else 0)
            A["nextopen"][k, j] = float(r.next_day)
            if not r.available:
                A["reason"][k, j] = r.reason
                continue
            q = key.get((r.date, r.index))
            if q is None:
                A["reason"][k, j] = "strike"
                continue
            ml = float(sub.at[q, f"ml_{m}"])
            A["avail"][k, j] = 1
            A["ml"][k, j] = ml
            A["net"][k, j] = float(net.loc[q])
            A["ecost"][k, j] = float(sub.at[q, f"entry_cost_{m}"])
            A["marg"][k, j] = float(sub.at[q, "margin"])
            A["stopclose"][k, j] = float(sub.at[q, f"stopclose_{m}"])
            mk = np.asarray(sub.at[q, "marks_R"], dtype=float)
            if scen == "b" and len(mk) > 1:
                mk = mk + float(shift.loc[q]) / ml * np.linspace(0, 1, len(mk))
            pl = mk * ml - A["ecost"][k, j]                          # open P&L per lot at each minute's close, entry costs paid
            self.marks[(k, j)] = pl
            if r.next_day:
                p1529 = int(NMIN - 1 - r.m_in)
                A["mark1529"][k, j] = float(pl[min(p1529, len(pl) - 1)])
            A["flag"][k, j] = float(pl.min() <= -FLAG_AT * ml)
            A["row"][k, j] = int(q)
        self.A = A


# ============================================================================================================================ the engine
def run_paths(S: Slots, src: np.ndarray, f: float, W0: float, paused_mode: bool, stop_at_pause: bool = False) -> dict:
    """src: (P, L) session indices into S. Returns per-path daily equity, log growth, pause, limit days, misses, taken counts and reasons."""
    P, L = src.shape
    A = S.A
    E = np.full(P, W0)
    hwm = E.copy()
    paused = np.zeros(P, bool)
    pause_at = np.full(P, -1)
    on_net = np.zeros(P); on_mark = np.zeros(P)
    eq = np.zeros((P, L)); lg = np.zeros((P, L))
    limit_days = np.zeros(P, int); misses = np.zeros(P, int); breaches = np.zeros(P, int)
    taken = np.zeros(P, int); seen = np.zeros(P, int)
    reasons = {"size_zero": 0, "budget": 0, "margin": 0, "liquidity": 0, "strike": 0, "paused": 0, "limit": 0}
    taken_rows = []
    for t in range(L):
        s = src[:, t]
        W = E.copy()
        gap = on_net - on_mark
        gap_loss = np.maximum(0.0, -gap)
        E = E + gap
        day_closed = gap_loss >= DAY_LIMIT * W
        on_net[:] = 0.0; on_mark[:] = 0.0
        lots = np.zeros((P, 2))
        realized = np.zeros(P)
        new_on_net = np.zeros(P); new_on_mark = np.zeros(P)
        block = paused if paused_mode else np.zeros(P, bool)
        for j in range(2):
            ex = A["exists"][s, j] > 0
            seen += ex
            av = A["avail"][s, j] > 0
            ml = np.where(av, A["ml"][s, j], 1.0)
            reason_rows = ex & ~av
            for rsn in ("liquidity", "strike"):
                reasons[rsn] += int((reason_rows & (A["reason"][s, j] == rsn)).sum())
            cand = ex & av
            reasons["paused"] += int((cand & block).sum())
            reasons["limit"] += int((cand & ~block & day_closed).sum())
            cand = cand & ~block & ~day_closed
            # open earlier slot and realised earlier slot at this entry minute
            open_ml = np.zeros(P); open_marg = np.zeros(P); real_before = np.zeros(P)
            if j == 1:
                m_in = A["m_in"][s, 1]
                still = A["m_out"][s, 0] > m_in
                open_ml = np.where(still, lots[:, 0] * A["ml"][s, 0], 0.0)
                open_marg = np.where(still, lots[:, 0] * A["marg"][s, 0], 0.0)
                real_before = np.where(~still & (A["nextopen"][s, 0] == 0), lots[:, 0] * A["net"][s, 0], 0.0)
            l0 = np.floor(f * W / ml)
            budget = DAY_LIMIT * W - np.maximum(0.0, -real_before) - gap_loss - open_ml
            lb = np.where(l0 * ml <= budget, l0, np.floor(np.maximum(budget, 0.0) / ml))
            z = cand & (l0 <= 0)
            reasons["size_zero"] += int(z.sum())
            bz = cand & (l0 > 0) & (lb <= 0)
            reasons["budget"] += int(bz.sum())
            ok = cand & (lb > 0)
            free = W - open_marg
            mz = ok & (lb * A["marg"][s, j] > free)
            reasons["margin"] += int(mz.sum())
            ok = ok & ~mz
            lots[:, j] = np.where(ok, lb, 0.0)
        for j in range(2):
            nx = A["nextopen"][s, j] > 0
            realized += np.where(~nx, lots[:, j] * A["net"][s, j], 0.0)
            new_on_net += np.where(nx, lots[:, j] * A["net"][s, j], 0.0)
            new_on_mark += np.where(nx, lots[:, j] * A["mark1529"][s, j], 0.0)
            taken += lots[:, j] > 0
            breaches += (lots[:, j] > 0) & (-A["net"][s, j] > A["ml"][s, j])
        stopc = (lots * A["stopclose"][s]).sum(axis=1)
        # minute replay where the limit could bind
        fl = ((A["flag"][s] > 0) & (lots > 0)).any(axis=1) | day_closed
        for p in np.flatnonzero(fl):
            r = _exact_session(S, int(s[p]), f, W[p], gap_loss[p], bool(block[p]))
            lots[p] = r["lots"]
            realized[p], new_on_net[p], new_on_mark[p], stopc[p] = r["realized"], r["on_net"], r["on_mark"], r["stopclose"]
            limit_days[p] += int(r["limit"])
        E = E + realized + new_on_mark
        on_net, on_mark = new_on_net, new_on_mark
        day_pl = E - W
        misses += day_pl < -(DAY_LIMIT * W + stopc + 1e-9)
        hwm = np.maximum(hwm, E)
        newp = ~paused & (E < (1 - PAUSE) * hwm)
        pause_at = np.where(newp, t, pause_at)
        paused = paused | newp
        eq[:, t] = E
        lg[:, t] = np.log(np.maximum(E, 1e-9) / np.maximum(W, 1e-9))
        for j in range(2):
            m = lots[:, j] > 0
            if P == 1 and m[0]:
                taken_rows.append((int(A["row"][s[0], j]), float(lots[0, j]), t))
    return {"eq": eq, "lg": lg, "paused": paused, "pause_at": pause_at, "limit_days": limit_days, "misses": misses, "breaches": breaches,
            "taken": taken, "seen": seen, "reasons": reasons, "taken_rows": taken_rows}


def _exact_session(S: Slots, k: int, f: float, W: float, gap_loss: float, blocked: bool) -> dict:
    """One session minute by minute (only where the 5% limit could bind): entries at their minute with the same sizing, open P&L at every
    minute's close, the limit closing everything at the next minute with doubled exit half-spreads, no entries after it."""
    A = S.A
    lots = np.zeros(2)
    out = {"lots": lots, "realized": 0.0, "on_net": 0.0, "on_mark": 0.0, "stopclose": 0.0, "limit": False}
    if gap_loss >= DAY_LIMIT * W:
        out["limit"] = True
        return out
    realized, closed, hit = 0.0, [False, False], False
    m_in = [int(A["m_in"][k, j]) for j in range(2)]
    m_out = [int(A["m_out"][k, j]) for j in range(2)]
    for m in range(0, NMIN):
        for j in range(2):
            if hit or blocked or m != m_in[j] or not (A["exists"][k, j] > 0 and A["avail"][k, j] > 0):
                continue
            ml = A["ml"][k, j]
            open_ml = sum(lots[i] * A["ml"][k, i] for i in range(2) if lots[i] > 0 and not closed[i])
            open_marg = sum(lots[i] * A["marg"][k, i] for i in range(2) if lots[i] > 0 and not closed[i])
            l0 = math.floor(f * W / ml)
            budget = DAY_LIMIT * W - max(0.0, -realized) - gap_loss - open_ml
            lb = l0 if l0 * ml <= budget else math.floor(max(budget, 0.0) / ml)
            if l0 > 0 and lb > 0 and lb * A["marg"][k, j] <= W - open_marg:
                lots[j] = lb
                out["stopclose"] += lb * A["stopclose"][k, j]
        for j in range(2):
            if lots[j] > 0 and not closed[j] and m_out[j] < NMIN and m == m_out[j]:
                realized += lots[j] * A["net"][k, j]
                closed[j] = True
        if hit:
            break
        open_pl = 0.0
        for j in range(2):
            if lots[j] > 0 and not closed[j]:
                pl = S.marks[(k, j)]
                open_pl += lots[j] * pl[min(m - m_in[j], len(pl) - 1)]
        if realized + open_pl <= -DAY_LIMIT * W:
            hit = True
            out["limit"] = True
            for j in range(2):
                if lots[j] > 0 and not closed[j]:
                    pl = S.marks[(k, j)]
                    realized += lots[j] * (pl[min(m + 1 - m_in[j], len(pl) - 1)] - A["stopclose"][k, j])
                    closed[j] = True
    for j in range(2):
        if lots[j] > 0 and not closed[j]:          # still open at the close: an overnight (NEXTOPEN) position
            out["on_net"] += lots[j] * A["net"][k, j]
            out["on_mark"] += lots[j] * A["mark1529"][k, j]
    out["realized"] = realized
    out["lots"] = lots
    return out


# ============================================================================================================================ bootstraps
def draws(n: int, kind: str, rng: np.random.Generator) -> np.ndarray:
    if kind == "block20":
        nb = math.ceil(PATH_LEN / BLOCK)
        starts = rng.integers(0, n - BLOCK + 1, size=(PATHS, nb))
        return (starts[:, :, None] + np.arange(BLOCK)[None, None, :]).reshape(PATHS, -1)[:, :PATH_LEN]
    out = np.zeros((PATHS, PATH_LEN), int)
    cur = rng.integers(0, n, size=PATHS)
    for t in range(PATH_LEN):
        if t > 0:
            new = rng.random(PATHS) < 1.0 / STAT_MEAN
            cur = np.where(new, rng.integers(0, n, size=PATHS), (cur + 1) % n)
        out[:, t] = cur
    return out


def block_se_of_mean(x: np.ndarray, rng: np.random.Generator, n_draws: int = 2000) -> float:
    n = len(x)
    nb = math.ceil(n / BLOCK)
    starts = rng.integers(0, n - BLOCK + 1, size=(n_draws, nb))
    idx = (starts[:, :, None] + np.arange(BLOCK)[None, None, :]).reshape(n_draws, -1)[:, :n]
    return float(x[idx].mean(axis=1).std(ddof=1))


def spa_pvalue(d: np.ndarray, rng: np.random.Generator, n_draws: int = 2000) -> float:
    """Hansen's SPA against one benchmark reduces to a recentred, studentised stationary-bootstrap test of the mean difference (H0: <= 0)."""
    n = len(d)
    if n < 40 or np.allclose(d, d[0]):
        return float("nan")
    mu = d.mean()
    se = block_se_of_mean(d, rng, n_draws)
    if not se > 0:
        return float("nan")
    cur = rng.integers(0, n, size=n_draws)
    sums = np.zeros(n_draws)
    for t in range(n):
        if t > 0:
            new = rng.random(n_draws) < 1.0 / STAT_MEAN
            cur = np.where(new, rng.integers(0, n, size=n_draws), (cur + 1) % n)
        sums += d[cur]
    stat = (sums / n - mu) / se          # the bootstrap distribution recentred at the sample mean (the least favourable null, mu = 0)
    return float((stat >= mu / se).mean())


# ============================================================================================================================ the run
def run(n_paths: int = PATHS, write_registry: bool = True, log=print) -> dict:
    global PATHS, MARGIN_MULT
    PATHS = n_paths
    t0 = time.time()
    from india import sealed, sp1_holdout
    mc = json.loads((paths.manifest_dir() / "sz2_margin_check.json").read_text())
    MARGIN_MULT = mc.get("proxy_multiplier", {})
    idx_t = scale_close()
    t_all = load_trades()
    tt = today_scale(t_all, idx_t)
    log(f"trades: {t_all['date'].nunique()} decision days, {len(t_all)} trade x structure rows, {len(tt)} available; today's scale {idx_t}  {time.time() - t0:.0f}s")
    cal, _ = sp1_holdout.calendar_full()
    days = {w: [d for d in cal if lo <= d <= hi] for w, (lo, hi) in WINDOWS.items()}
    rng = np.random.default_rng(SEED)
    boots = {(w, k): draws(len(days[w]), k, rng) for w in WINDOWS for k in ("block20", "stationary")}
    variants = [(s, f) for f in FRACTIONS for s in Z.STRUCTURES]
    slots = {(s, sc, w): Slots(days[w], tt[tt["date"].isin(set(days[w]))], t_all, s, sc) for s in Z.STRUCTURES for sc in SCENARIOS for w in WINDOWS}
    log(f"slots built  {time.time() - t0:.0f}s")
    res = []
    hist_series = {}
    for s, f in variants:
        for W0 in TIERS:
            row = {"structure": s, "f": f, "tier": W0}
            # historical paths (scenario a): from 2017 and from 2024, paused and unpaused
            for w in WINDOWS:
                S = slots[(s, "a", w)]
                src = np.arange(S.n)[None, :]
                for pm in (True, False):
                    h = run_paths(S, src, f, W0, paused_mode=pm)
                    e = h["eq"][0]
                    key = f"hist{w}_{'paused' if pm else 'unpaused'}"
                    dd = float((e / np.maximum.accumulate(np.r_[W0, e])[1:] - 1).min())
                    row[key] = {"end_equity": float(e[-1]), "max_drawdown": dd, "pause_session": int(h["pause_at"][0]), "limit_days": int(h["limit_days"][0]),
                                "misses": int(h["misses"][0]), "miss_share": float(h["misses"][0] / S.n), "breaches": int(h["breaches"][0]),
                                "taken": int(h["taken"][0]), "seen": int(h["seen"][0]), "reasons": h["reasons"], "mean_log_growth": float(h["lg"][0].mean())}
                    if pm and w == "2024" and W0 == TIERS[0]:
                        hist_series[(s, f)] = h["lg"][0]
                    if pm and w == "2017" and W0 == TIERS[0]:
                        row["_taken_rows"] = h["taken_rows"]
                        row["_lg2017"] = h["lg"][0]
            # bootstraps
            for sc in SCENARIOS:
                for (w, k), src in boots.items():
                    b = run_paths(slots[(s, sc, w)], src, f, W0, paused_mode=True)
                    p = float(b["paused"].mean())
                    g = b["lg"].sum(axis=1)
                    row[f"boot_{sc}_{w}_{k}"] = {"p_pause": p, "mc_error": math.sqrt(max(p * (1 - p), 1e-12) / src.shape[0]),
                                                 "miss_share_max_path": float((b["misses"] / PATH_LEN).max()), "miss_share_mean": float((b["misses"] / PATH_LEN).mean()),
                                                 "median_log_growth": float(np.median(g)), "median_se": float(1.2533 * g.std(ddof=1) / math.sqrt(len(g))),
                                                 "limit_days_mean": float(b["limit_days"].mean())}
            pp = [row[f"boot_{sc}_{w}_{k}"]["p_pause"] for sc in SCENARIOS for (w, k) in boots]
            miss_ok = (row["hist2017_unpaused"]["miss_share"] <= 0.02 and row["hist2024_unpaused"]["miss_share"] <= 0.02
                       and all(row[f"boot_a_{w}_{k}"]["miss_share_max_path"] <= 0.02 for (w, k) in boots))
            row["worst_p_pause"] = max(pp)
            row["eligible"] = bool(max(pp) <= 0.10 and miss_ok)
            row["miss_ok"] = bool(miss_ok)
            res.append(row)
        log(f"  {s} f={f:.0%}: eligible at {[r['tier'] for r in res if r['structure'] == s and r['f'] == f and r['eligible']]}  {time.time() - t0:.0f}s")
    # ---- the choice (selection_rule.choice)
    elig_all = [(s, f) for s, f in variants if all(r["eligible"] for r in res if r["structure"] == s and r["f"] == f)]
    choice = {"eligible_at_all_four_tiers": [f"{s} {f:.0%}" for s, f in elig_all]}
    med_ml = tt.groupby("structure")["ml_1"].median().to_dict()
    if elig_all:
        means = {v: float(hist_series[v].mean()) for v in elig_all}
        best = max(elig_all, key=lambda v: means[v])
        se = {}
        for v in elig_all:
            dlt = hist_series[v] - hist_series[best]
            se[v] = block_se_of_mean(dlt, np.random.default_rng(SEED + 1)) * 250 if v != best else 0.0
        within = [v for v in elig_all if (means[best] - means[v]) * 250 <= se[v] + 1e-15]
        if DEFAULT in elig_all and DEFAULT in within:
            chosen, why = DEFAULT, "the default is eligible at every tier and within one SE of the best"
        else:
            chosen = sorted(within, key=lambda v: (v[1], med_ml.get(v[0], 1e18)))[0]
            why = "the lowest-risk variant within one SE of the best (smallest f, then the smaller planned max loss per lot)"
        spa = spa_pvalue(hist_series[chosen] - hist_series[DEFAULT], np.random.default_rng(SEED + 2)) if chosen != DEFAULT and DEFAULT in hist_series else float("nan")
        choice.update({"best": f"{best[0]} {best[1]:.0%}", "best_mean_daily_log_growth_x250": means[best] * 250,
                       "chosen": f"{chosen[0]} {chosen[1]:.0%}", "why": why, "chosen_mean_x250": means[chosen] * 250,
                       "default_mean_x250": float(hist_series[DEFAULT].mean() * 250), "se_x250": {f"{v[0]} {v[1]:.0%}": se[v] for v in elig_all},
                       "within_one_se": [f"{v[0]} {v[1]:.0%}" for v in within], "spa_p_vs_default": spa})
    else:
        choice.update({"chosen": None, "why": "no variant is eligible at all four tiers (the choice rule's filter), so the rule selects none: SP1's option line stays "
                                              "shadow-only (the main book does not trade SP1 options) unless Madhav decides otherwise; the shadow lines continue"})
    e60 = [f"{r['structure']} {r['f']:.0%}" for r in res if r["tier"] == TIERS[0] and r["eligible"]]
    choice["eligible_at_60000"] = e60
    if not e60:
        choice["at_60000"] = "no variant is eligible at Rs 60,000: the main book does not trade SP1 options there"
    # smallest tier at which each index trades at all and at which a variant becomes eligible
    choice["first_eligible_tier"] = {f"{s} {f:.0%}": next((r["tier"] for r in sorted(res, key=lambda r: r["tier"]) if r["structure"] == s and r["f"] == f and r["eligible"]), None) for s, f in variants}
    # at the STARTING equity of each tier (no growth): the share of each index's trades that one lot fits (floor(f x W0 / planned max loss) >= 1)
    fit = {}
    for sym in LOT_T:
        for W0 in TIERS:
            best_share = 0.0
            for s, f in variants:
                x = tt[(tt["index"] == sym) & (tt["structure"] == s)]
                if len(x):
                    best_share = max(best_share, float((np.floor(f * W0 / x["ml_1"]) >= 1).mean()))
            fit.setdefault(sym, {})[int(W0)] = round(best_share, 3)
    choice["share_of_trades_one_lot_fits_at_start_best_variant"] = fit
    choice["smallest_tier_index_trades"] = {sym: next((W0 for W0, v in d.items() if v > 0), None) for sym, d in fit.items()}
    # ---- per-variant extras on the 2017 paused path at Rs 60,000: sessions-left buckets and eras of the trades taken
    extras = {}
    for r in res:
        if r["tier"] != TIERS[0]:
            continue
        rows = r.pop("_taken_rows", [])
        lg = r.pop("_lg2017", None)
        if rows:
            ti = tt.loc[[x[0] for x in rows]].copy()
            ti["lots"] = [x[1] for x in rows]
            ti["net_R"] = ti["net_1"] / ti["ml_1"]
            ti["bucket"] = pd.cut(ti["sessions_left"], [0, 3, 7, 1000], labels=["2-3", "4-7", "8+"]).astype(str)
            d_ = pd.to_datetime(ti["date"])
            ti["era"] = np.where(d_ >= pd.Timestamp("2026-04-01"), "from 1 Apr 2026 (STT 0.15%)", np.where(d_ >= pd.Timestamp("2024-11-20"),
                                 "20 Nov 2024 - 31 Mar 2026 (SEBI rules)", "to 19 Nov 2024 (weekly expiries)"))
            extras[f"{r['structure']} {r['f']:.0%}"] = {
                "by_bucket": {k: {"n": int(len(g)), "mean_net_R": round(float(g["net_R"].mean()), 4)} for k, g in ti.groupby("bucket")},
                "by_era": {k: {"n": int(len(g)), "mean_net_R": round(float(g["net_R"].mean()), 4)} for k, g in ti.groupby("era")},
                "dated_cost_mean_net_R": round(float(ti["net_dated_R"].mean()), 4), "todays_cost_mean_net_R": round(float(ti["net_R"].mean()), 4)}
        if lg is not None:
            r["_lg"] = lg
    # ---- ledger: one EXPLORATORY row per variant at Rs 60,000 (family SZ)
    ledger = []
    cal_days = days["2017"]
    if write_registry:
        from india import registry
        import os
        os.environ.setdefault("ANANTA_RERUN_REASON", "the SZ2 selection run (first run of the frozen spec)")
        reg = registry.register("SZ2", family="SZ", title="Sizing v2: fraction x structure for SP1's option line (sz2-v1-2026-10-19-frozen), at Rs 60,000",
                                hypothesis="exploratory: each variant's daily log growth on the historical paused path (2017-2023 dev, 2024-01-01..2026-10-16 seen); the selection is counted, never confirmed",
                                variants=[f"{s}|{f:.2f}" for s, f in variants], note="every SP1 year seen; synthetic prices; IV shift 0 (stated); margin proxy multiplier 1.0",
                                union_k=len(variants))      # the bar is frozen at the grid's 20 rows, so it cannot drift as they are recorded
        from india import sp3learn as Lr
        for r in res:
            if r["tier"] != TIERS[0] or "_lg" not in r:
                continue
            ser = pd.Series(r.pop("_lg"), index=pd.to_datetime(cal_days))
            dv, vl = ser[ser.index.year <= 2023], ser[ser.index.year >= 2024]
            qd, qv = dv.index.to_period("Q").nunique(), vl.index.to_period("Q").nunique()
            ledger.append(registry.record(reg, variant=f"{r['structure']}|{r['f']:.2f}", dev=(float(dv.mean()), Lr.nw_t(dv.to_numpy()), qd),
                                          val=(float(vl.mean()), Lr.nw_t(vl.to_numpy()), qv), expect=1, rule="seen_val_only",
                                          extra={"exploratory": True, "eligible_all_tiers": (r["structure"], r["f"]) in elig_all, "worst_p_pause": r["worst_p_pause"],
                                                 "chosen": choice.get("chosen") == f"{r['structure']} {r['f']:.0%}", "statistic": "daily log growth, Newey-West t (5 lags)"}))
        registry.mirror_to_catalog()
    for r in res:
        r.pop("_lg", None)
    out = {"spec_version": "sz2-v1-2026-10-19-frozen", "today_scale": {"lots": LOT_T, "index_close_2026_10_16": idx_t, "cost_table": f"costs.py {costs.COST_MODEL} at {TODAY}"},
           "decisions_23_oct": {"a": "holdout-era policy trades read through the logged sealed purpose sz2_selection", "b": Z.IV_SHIFT_NOTE},
           "margin_proxy_multiplier": MARGIN_MULT, "paths": PATHS, "path_len": PATH_LEN, "seed": SEED, "windows": {k: [str(a), str(b)] for k, (a, b) in WINDOWS.items()},
           "sessions": {w: len(days[w]) for w in WINDOWS}, "trades": {"rows": int(len(t_all)), "available": int(len(tt))}, "variants": res, "choice": choice, "extras": extras,
           "ledger": [{"variant": l["variant"], "verdict": l["verdict"], "z": l["z"]} for l in ledger], "seconds": round(time.time() - t0, 1)}
    (paths.manifest_dir() / "sz2_results.json").write_text(json.dumps(out, indent=1, default=str))
    flat = []
    for r in res:
        fr = {"structure": r["structure"], "f": r["f"], "tier": r["tier"], "eligible": r["eligible"], "worst_p_pause": r["worst_p_pause"], "miss_ok": r["miss_ok"]}
        for k, v in r.items():
            if isinstance(v, dict) and k.startswith(("hist", "boot")):
                for kk, vv in v.items():
                    if not isinstance(vv, dict):
                        fr[f"{k}.{kk}"] = vv
        flat.append(fr)
    pd.DataFrame(flat).to_parquet(paths.gold() / "studies" / "SZ2_variants.parquet", index=False)
    write_doc(out)
    return out


def _pct(x):
    return f"{x:.1%}" if x == x and x is not None else "n/a"


def write_doc(o: dict) -> None:
    from india import ocstudy  # noqa: F401
    ch = o["choice"]
    L = ["# SZ2 results: sizing v2 for SP1's option line (EXPLORATORY)", "",
         f"Generated by `python -m india.sz2 select` on {dt.date.today()} from the frozen spec `registrations/sz2_v1.json`. Every SP1 year 2017 to 16 Oct 2026 has "
         "been seen and the option prices are synthetic (Black-76 on the previous session's smile), so every rupee path here is optimistic and EXPLORATORY. The "
         "sizing never changes which SP1 decision is made.", "",
         "## Decisions this run follows", "",
         f"- Madhav, 23 Oct 2026, SZ2 (a): the holdout-era decisions (2024-01-01..2026-10-16, the completed SP1 holdout run's own policy trades) are read "
         "through the logged sealed purpose `sz2_selection` (`india/sealed.py read_sz2`, every read in `manifests/sealed_access.jsonl`).",
         f"- Madhav, 23 Oct 2026, SZ2 (b): {o['decisions_23_oct']['b']}.",
         f"- Margin proxy multiplier (recorded once, `manifests/sz2_margin_check.json`): {o['margin_proxy_multiplier']}.",
         f"- Today's scale: lots {o['today_scale']['lots']}, index closes of 16 Oct 2026 {o['today_scale']['index_close_2026_10_16']}, {o['today_scale']['cost_table']}.",
         f"- Bootstraps: {o['paths']} paths x {o['path_len']} sessions, 20-session blocks and a stationary bootstrap (mean block 60), windows {o['windows']}, seed {o['seed']}, the same draws for every variant.", "",
         "## The choice", ""]
    if ch.get("chosen"):
        L += [f"- **Chosen: {ch['chosen']}** ({ch['why']}).", f"- Best eligible: {ch['best']} (mean daily log growth x 250 on the paused 2024-26 path at Rs 60,000: {ch['best_mean_daily_log_growth_x250']:+.3f}); "
              f"chosen {ch['chosen_mean_x250']:+.3f}; default {ch['default_mean_x250']:+.3f}.", f"- Within one SE of the best: {ch['within_one_se']}.",
              f"- Hansen's SPA p-value of the chosen against the default (exploratory): {ch['spa_p_vs_default']}."]
    else:
        L += [f"- **{ch['why']}**"]
    L += [f"- Eligible at all four tiers: {ch['eligible_at_all_four_tiers'] or 'none'}.", f"- Eligible at Rs 60,000: {ch['eligible_at_60000'] or 'none'}." + (f" {ch['at_60000']}." if ch.get("at_60000") else ""),
          f"- Smallest tier at which each index trades at all (one lot fits at the starting equity, best variant): {ch['smallest_tier_index_trades']}; "
          f"share of trades one lot fits at the start, by tier: {ch['share_of_trades_one_lot_fits_at_start_best_variant']}.",
          "- A variant eligible at Rs 60,000 is often eligible because one lot rarely fits there (see 'taken / seen' below): eligibility is a survival filter, not a sign of edge.", "",
          "This sets nothing live: `paper_config.json main.sizing` changes only with Madhav's approval (the SP1 line's sizing is pinned on lock day).", "",
          "## Every variant at every tier", "",
          "Worst pause probability = the largest of the 12 bootstrap probabilities (scenarios a recorded, b no edge, c costs x2; two windows; two bootstrap kinds). "
          "Historical columns: the paused path from 2017-01-02 at that tier.", "",
          "| structure | f | tier | eligible | worst P(pause) | P(pause) worst under a / b / c | misses ok | taken / seen (2017 path) | end equity | max drawdown | limit days | breaches |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in o["variants"]:
        h = r["hist2017_paused"]
        by = {sc: max(v["p_pause"] for k, v in r.items() if k.startswith(f"boot_{sc}_")) for sc in SCENARIOS}
        L.append(f"| {r['structure']} | {r['f']:.0%} | Rs {r['tier']:,.0f} | {'yes' if r['eligible'] else 'no'} | {r['worst_p_pause']:.3f} | {by['a']:.3f} / {by['b']:.3f} / {by['c']:.3f} | "
                 f"{r['miss_ok']} | {h['taken']} / {h['seen']} | Rs {h['end_equity']:,.0f} | {h['max_drawdown']:.1%} | {h['limit_days']} | {h['breaches']} |")
    L += ["", "## Reasons a trade was not taken (2017 paused path, Rs 60,000)", ""]
    for r in o["variants"]:
        if r["tier"] == 60_000.0:
            L.append(f"- {r['structure']} {r['f']:.0%}: {r['hist2017_paused']['reasons']}")
    L += ["", "## By sessions-left bucket and era (trades taken on the 2017 path at Rs 60,000; net R at today's scale, and with each trade's dated costs)", ""]
    for k, v in o["extras"].items():
        L.append(f"- {k}: buckets {v['by_bucket']}; eras {v['by_era']}; mean net R today's costs {v['todays_cost_mean_net_R']}, dated costs {v['dated_cost_mean_net_R']}")
    L += ["", "## Limits (as the spec states)", "", "- synthetic prices miss real behaviour on the biggest days; the daily-limit close uses synthetic minute marks; the margin is a conservative proxy; "
          "market impact is not modelled; the SP1 decisions were selected on these years.",
          "- Engine choices stated here: the limit close fills at the next minute's mark less one more entry-level half-spread and the exit fees; "
          "margin of open positions is held at their entry value; in scenario (b) the minute marks are shifted by the same demeaning, spread evenly over the trade.", "",
          "## Ledger", "", f"{len(o['ledger'])} EXPLORATORY rows in family SZ (one per variant at Rs 60,000; rule seen_val_only: the selection is counted, never confirmed).", "",
          "## Files", "", "- `manifests/sz2_results.json`, `gold/studies/SZ2_variants.parquet` (aggregates only), `gold/studies/SZ2_trades.parquet`; the holdout-era trade table stays in the sealed tree.", ""]
    from pathlib import Path
    (Path(Z.__file__).parent / "registrations" / "sz2_results.md").write_text("\n".join(L))


def main(cmd: str) -> None:
    paths.ensure()
    from pathlib import Path
    logf = Path.home() / "ananta_runs" / "sz2" / "select.log"
    logf.parent.mkdir(parents=True, exist_ok=True)

    def log(m):
        print(m, flush=True)
        with logf.open("a") as fh:
            fh.write(f"{dt.datetime.now().isoformat(timespec='seconds')} {m}\n")
    if cmd == "rehearse":
        run(n_paths=200, write_registry=False, log=log)
    else:
        run(log=log)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "select")
