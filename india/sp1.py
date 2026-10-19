"""SP1: Scenario Playbook phase 1, index intraday playbook (registrations/sp1_v2.json, frozen 19 Oct 2026).

  python -m india.sp1 selftest      hand-built paths for the exits and the option leg
  python -m india.sp1 outcomes      every action's outcome per index, day and decision point, 2015-2023 (silver/gold only):
                                    gold/studies/SP1_outcomes.parquet (no learning, no policy, no ledger)
  python -m india.sp1 run           learning, policy, tests, nulls, book, ledger rows, report (needs outcomes)

Outcomes: for each of NIFTY / BANKNIFTY, each session in gold/scenario/index_states.parquet, each decision point (D0 09:15 -> fill at the 09:16
open +2 ticks; D1 09:30; D2 09:45; D3 10:15) and each of the 12 actions (2 directions x 6 exits; ORSTOP not at D0 and only when its stop is on the
right side of the entry by >= 0.1 daily ATR14): the future-proxy gross bps, its dated cost in bps, and the synthetic option leg (EXPLORATORY).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from india import costs, greeks, ocstudy, paths

HERE = Path(__file__).parent
SPEC = HERE / "registrations" / "sp1_v2.json"
IDX = {"NIFTY": "NIFTY 50", "BANKNIFTY": "NIFTY BANK"}
TICK = 0.05
NMIN = 375
POINT_ENTRY = {"D0": 1, "D1": 15, "D2": 30, "D3": 60}      # entry bar (minutes after 09:15) per decision point
EXIT_1130, EXIT_1515 = 135, 360
EXITS = ("T1130", "T1515", "ORSTOP", "ATRSTOP", "TRAIL", "NEXTOPEN")
ACTIONS = [(x, d) for x in EXITS for d in (1, -1)]           # fixed order: the action id is the position (tie-break: lower id)
OPT_HALF = {"NIFTY": 0.5, "BANKNIFTY": 1.0}
WEEKLY_FROM = {"NIFTY": dt.date(2019, 2, 11), "BANKNIFTY": dt.date(2016, 5, 27)}
MIN_PER_YEAR = 365 * 24 * 60
YEARS = list(range(2015, 2024))


def spec_sha() -> str:
    return hashlib.sha256(SPEC.read_bytes()).hexdigest()[:16]


# ----------------------------------------------------------------------------------------------------------------------------- exits
def trail_exit(O, H, L, e, d, k, X):
    """Chandelier trail: level = best price since entry (entry price included, bars before t) -/+ k; checked from the entry bar; a bar that
    opens beyond the level fills at its open. Time exit at the open of bar X. Returns exit price, exit bar, stopped."""
    n, T = O.shape
    rows = np.arange(n)
    cols = np.arange(T)[None, :]
    has = (e >= 0) & (e < X)
    ee = np.where(has, e, X)
    live = (cols >= ee[:, None]) & (cols < X) & has[:, None]
    entry = O[rows, np.clip(ee, 0, T - 1)]
    if True:
        hi = np.where(cols >= ee[:, None], H, -np.inf)
        lo = np.where(cols >= ee[:, None], L, np.inf)
        run_hi = np.maximum.accumulate(hi, axis=1)
        run_lo = np.minimum.accumulate(lo, axis=1)
        prev_hi = np.concatenate([np.full((n, 1), -np.inf), run_hi[:, :-1]], axis=1)
        prev_lo = np.concatenate([np.full((n, 1), np.inf), run_lo[:, :-1]], axis=1)
        best_l = np.maximum(prev_hi, entry[:, None])
        best_s = np.minimum(prev_lo, entry[:, None])
        lvl = np.where(d[:, None] > 0, best_l - k[:, None], best_s + k[:, None])
    hit = live & np.where(d[:, None] > 0, L <= lvl, H >= lvl)
    th = ocstudy.first_true(hit)
    stopped = th >= 0
    tc = np.clip(th, 0, T - 1)
    lv = lvl[rows, tc]
    ot = O[rows, tc]
    fill = np.where(d > 0, np.minimum(ot, lv), np.maximum(ot, lv))
    px = np.where(stopped, fill, O[rows, min(X, T - 1)])
    tx = np.where(stopped, th, X)
    return np.where(has, px, np.nan), np.where(has, tx, -1), stopped & has


# ----------------------------------------------------------------------------------------------------------------------------- data
def _chains(syms=("NIFTY", "BANKNIFTY")) -> pd.DataFrame:
    D = paths.data_dir()
    files = [str(D / "silver/fo_greeks" / f"year={y}" / "part.parquet") for y in range(2014, 2024) if (D / "silver/fo_greeks" / f"year={y}" / "part.parquet").exists()]
    con = duckdb.connect()
    df = con.execute(f"""select date, symbol, expiry, strike, opt_type, fwd, iv, coalesce(volume, 0) as volume
                         from read_parquet({files!r}) where list_contains(?, symbol)""", [list(syms)]).df()
    con.close()
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["expiry"] = pd.to_datetime(df["expiry"]).dt.date
    return df


class OptionBook:
    """Previous-session chain per (symbol, trade date): the expiry (nearest strictly after the trade date), listed strikes, traded IVs, carry."""

    def __init__(self, chains: pd.DataFrame, prev_session: dict, prev_close: dict):
        self.by = {k: g for k, g in chains.groupby(["symbol", "date"])}
        self.prev = prev_session
        self.pc = prev_close  # (symbol, date) -> index close of that date

    def setup(self, sym: str, day: dt.date):
        p = self.prev.get(day)
        g = self.by.get((sym, p)) if p else None
        if g is None or g.empty:
            return None
        ex = sorted(e for e in g["expiry"].unique() if e > day)
        if not ex:
            return None
        e = ex[0]
        c = g[g["expiry"] == e]
        spot_prev = self.pc.get((sym, p))
        fwd = c["fwd"].dropna()
        if spot_prev is None or fwd.empty:
            return None
        out = {"expiry": e, "carry": float(fwd.median()) / spot_prev, "listed": np.sort(c["strike"].unique())}
        for t in ("CE", "PE"):
            x = c[(c["opt_type"] == t) & (c["volume"] > 0) & c["iv"].notna() & (c["iv"] > 0)]
            out[t] = (x["strike"].to_numpy(), x["iv"].to_numpy())
        return out


def _t_years(day: dt.date, minute: int, expiry: dt.date) -> float:
    now = dt.datetime.combine(day, dt.time(9, 15)) + dt.timedelta(minutes=int(minute))
    end = dt.datetime.combine(expiry, dt.time(15, 30))
    return max((end - now).total_seconds() / 60.0, 1.0) / MIN_PER_YEAR


def option_leg(sym, day, setup, d, spot_in, m_in, spot_out, day_out, m_out, stopped, lot, spread_mult=1.0):
    """Synthetic ATM option bought at entry, sold at the index exit. Returns dict or None (no chain / no traded IV)."""
    if setup is None or not (spot_in == spot_in and spot_out == spot_out):
        return None
    typ = "CE" if d > 0 else "PE"
    K = float(setup["listed"][np.abs(setup["listed"] - spot_in).argmin()])
    ks, ivs = setup[typ]
    if len(ks) == 0:
        return None
    iv = float(ivs[np.abs(ks - K).argmin()]) if K not in ks else float(ivs[ks == K][0])
    e = setup["expiry"]
    car = setup["carry"]
    p_in = float(greeks.black76(np.array([spot_in * car]), np.array([K]), np.array([_t_years(day, m_in, e)]), np.array([iv]), np.array([typ == "CE"]))[0][0])
    p_out = float(greeks.black76(np.array([spot_out * car]), np.array([K]), np.array([_t_years(day_out, m_out, e)]), np.array([iv]), np.array([typ == "CE"]))[0][0])
    p_in, p_out = max(p_in, 0.05), max(p_out, 0.05)
    h_in = max(OPT_HALF[sym], 0.0025 * p_in) * spread_mult
    h_out = max(OPT_HALF[sym], 0.0025 * p_out) * spread_mult * (2.0 if stopped else 1.0)
    buy, sell = (p_in + h_in), max(p_out - h_out, 0.0)
    fees = costs.cost("options", "buy", buy * lot, day.year, when=day) + costs.cost("options", "sell", sell * lot, day_out.year, when=day_out)
    net = (sell - buy) * lot - fees
    return {"opt_K": K, "opt_iv": iv, "opt_expiry": e, "opt_carry": car, "opt_dte": (e - day).days, "opt_prem_in": p_in, "opt_prem_out": p_out,
            "opt_net_rs": net, "opt_ret": net / (p_in * lot) if p_in > 0 else np.nan}


# ----------------------------------------------------------------------------------------------------------------------------- outcomes
def outcomes(log=print, src: dict | None = None, out_file: Path | None = None) -> pd.DataFrame:
    """src (optional, a registered holdout run): days, specials, states, index, lots, chains. Without src: silver/gold 2015-2023. Same code."""
    D = paths.data_dir()
    src = src or {}
    days_all, specials = (src["days"], src["specials"]) if "days" in src else ocstudy._calendar()
    nxt = {days_all[i]: days_all[i + 1] for i in range(len(days_all) - 1)}
    prv = {days_all[i]: days_all[i - 1] for i in range(1, len(days_all))}
    st = src["states"] if "states" in src else pd.read_parquet(D / "gold/scenario/index_states.parquet")
    index = src["index"] if "index" in src else ocstudy.load_index()
    lots = src["lots"] if "lots" in src else ocstudy.load_lots()
    lot = lots.set_index(["date", "symbol"])["lot"].to_dict()
    log("loading option chains (previous-session IV, silver/fo_greeks 2014-2023)")
    chains = src["chains"] if "chains" in src else _chains()
    pc = {}
    for sym, name in IDX.items():
        a = index[name]
        for i, d in enumerate(a["dates"]):
            pc[(sym, d)] = float(a["close"][i, -1])
    ob = OptionBook(chains, prv, pc)
    rows = []
    for sym, name in IDX.items():
        a = index[name]
        pos = {d: i for i, d in enumerate(a["dates"])}
        s = st[st["index"] == sym].sort_values("date").reset_index(drop=True)
        dd = list(s["date"])
        sel = np.array([pos[d] for d in dd])
        O, H, L, C = (a[f][sel] for f in ("open", "high", "low", "close"))
        nd = len(dd)
        atr = s["atr14_prev"].to_numpy(float)
        # next session's 09:16 open for NEXTOPEN (only when the calendar's next session is a usable session for this index)
        nx_open = np.array([a["open"][pos[nxt[d]], 1] if (d in nxt and nxt[d] in pos and a["ok"][pos[nxt[d]]] and nxt[d] not in specials) else np.nan for d in dd])
        nx_day = [nxt.get(d) for d in dd]
        orh, orl = H[:, :15].max(1), L[:, :15].min(1)
        h5 = H.reshape(nd, 75, 5).max(2)
        l5 = L.reshape(nd, 75, 5).min(2)
        c5 = C.reshape(nd, 75, 5)[:, :, -1]
        tr = ocstudy.tr5(h5, l5, c5)
        prev_tail = np.vstack([np.full((1, 14), np.nan), tr[:-1, -14:]])
        setups = [ob.setup(sym, d) for d in dd]
        lots_d = np.array([lot.get((d, sym), np.nan) for d in dd])
        for P, e0 in POINT_ENTRY.items():
            e = np.full(nd, e0)
            entry = O[:, e0]
            atr5 = ocstudy.atr_at(tr, prev_tail, e // 5)
            for aid, (X, dirc) in enumerate(ACTIONS):
                d = np.full(nd, dirc)
                avail = np.ones(nd, bool)
                stop0 = np.full(nd, np.nan)
                if X == "ORSTOP":
                    if P == "D0":
                        continue
                    stop = np.where(d > 0, orl, orh)
                    stop0 = stop
                    dist = np.where(d > 0, entry - stop, stop - entry)
                    avail = dist >= 0.1 * atr
                    px, tx, stp, _, _ = ocstudy.simulate(O, H, L, np.where(avail, e, -1), d, stop, EXIT_1515)
                elif X in ("T1130", "T1515"):
                    stop = np.where(d > 0, -np.inf, np.inf)
                    px, tx, stp, _, _ = ocstudy.simulate(O, H, L, e, d, stop, EXIT_1130 if X == "T1130" else EXIT_1515)
                elif X == "ATRSTOP":
                    stop = entry - d * 0.5 * atr
                    stop0 = stop
                    px, tx, stp, _, _ = ocstudy.simulate(O, H, L, e, d, stop, EXIT_1515)
                elif X == "TRAIL":
                    px, tx, stp = trail_exit(O, H, L, e, d, 3.0 * atr5, EXIT_1515)
                    stop0 = entry - d * 3.0 * atr5
                else:  # NEXTOPEN: intraday stop 1 x ATR to the close, else the next session's 09:16 open
                    pad = lambda A, v: np.concatenate([A, v[:, None]], axis=1)
                    stop = entry - d * 1.0 * atr
                    stop0 = stop
                    Op, Hp, Lp = pad(O, nx_open), pad(H, nx_open), pad(L, nx_open)
                    px, tx, stp, _, _ = ocstudy.simulate(Op, Hp, Lp, e, d, stop, NMIN)
                    avail = avail & (stp | ~np.isnan(nx_open))
                ok = avail & ~np.isnan(px) & ~np.isnan(atr)
                gross = d * (px - entry) / entry * 1e4
                ticks = 2 + (2 if P == "D0" else 0) + (2 if (X == "NEXTOPEN") else 0) * (~stp)
                for i in np.where(ok)[0]:
                    day = dd[i]
                    nextday = (X == "NEXTOPEN") and not stp[i]
                    day_out = nx_day[i] if nextday else day
                    m_out = 1 if nextday else int(tx[i])
                    lt = lots_d[i]
                    bv, sv = (entry[i] * lt, px[i] * lt) if dirc > 0 else (px[i] * lt, entry[i] * lt)
                    fees = costs.cost("futures", "buy", bv, day.year, when=day) + costs.cost("futures", "sell", sv, day.year, when=day)
                    cost_bps = (fees / lt + ticks[i] * TICK) / entry[i] * 1e4
                    r = {"date": day, "year": day.year, "index": sym, "point": P, "action": aid, "exit": X, "dir": dirc, "entry": float(entry[i]),
                         "exit_px": float(px[i]), "exit_min": int(tx[i]), "next_day": bool(nextday), "stopped": bool(stp[i]), "gross_bps": float(gross[i]),
                         "cost_bps": float(cost_bps), "lot": float(lt), "era": "weekly" if day >= WEEKLY_FROM[sym] else "monthly",
                         "stop0": float(stop0[i]), "atr_d": float(atr[i])}
                    leg = option_leg(sym, day, setups[i], dirc, float(entry[i]), e0, float(px[i]), day_out, m_out, bool(stp[i]), lt)
                    if leg:
                        r.update(leg)
                        leg2 = option_leg(sym, day, setups[i], dirc, float(entry[i]), e0, float(px[i]), day_out, m_out, bool(stp[i]), lt, spread_mult=2.0)
                        r["opt_net_rs_x2"], r["opt_ret_x2"] = leg2["opt_net_rs"], leg2["opt_ret"]
                    rows.append(r)
            log(f"{sym} {P}: {len(rows):,} outcome rows")
    out = pd.DataFrame(rows)
    out["net_bps"] = out["gross_bps"] - out["cost_bps"]
    if out_file is not None:
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out.to_parquet(out_file, index=False)
        return out
    out.to_parquet(D / "gold/studies/SP1_outcomes.parquet", index=False)
    summ = {"rows": len(out), "spec_sha": spec_sha(), "by_index_point": out.groupby(["index", "point"]).size().to_dict(),
            "option_leg_share": round(float(out["opt_ret"].notna().mean()), 4) if "opt_ret" in out else 0.0,
            "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    (D / "manifests/sp1_outcomes.json").write_text(json.dumps({k: (str(v) if isinstance(v, dict) else v) for k, v in summ.items()}, indent=1))
    return out


# ----------------------------------------------------------------------------------------------------------------------------- features
LAMBDAS = (1, 3, 10, 30, 100, 300, 1000)
C_GRID = (0.5, 1.0, 1.5, 2.0, 2.5)
TEST_YEARS = list(range(2017, 2024))
DEV_YEARS = (2017,)
DEC_BAR_COL = {"D1": "D1", "D2": "D2", "D3": "D3"}


def _terc(train: pd.Series, x: pd.Series) -> pd.Series:
    q = train.dropna().quantile([1 / 3, 2 / 3]).to_list()
    if len(q) < 2 or any(v != v for v in q):
        return pd.Series("missing", index=x.index)
    return pd.Series(np.where(x.isna(), "missing", np.where(x <= q[0], "low", np.where(x <= q[1], "mid", "high"))), index=x.index)


def _fixed3(x: pd.Series, lo: float, hi: float, names=("down", "flat", "up")) -> pd.Series:
    return pd.Series(np.where(x.isna(), "missing", np.where(x <= lo, names[0], np.where(x >= hi, names[2], names[1]))), index=x.index)


LEVELS = {"trend": ["mixed", "up", "down", "missing"], "vix": ["mid", "low", "high", "missing"], "us": ["flat", "down", "up", "missing"],
          "positioning": ["mid", "low", "high", "missing"], "event": ["none", "today", "recent"], "expiry": ["no", "yes"],
          "gap": ["flat", "down", "up", "missing"], "move": ["mid", "low", "high", "missing"], "breadth": ["mid", "weak", "strong", "missing"],
          "agreement": ["no", "yes"], "or_width": ["mid", "low", "high", "missing"]}
OVERNIGHT = ["trend", "vix", "us", "positioning", "event", "expiry", "gap"]
OPENING = ["move", "breadth", "agreement", "or_width"]


def feature_frame(st: pd.DataFrame, point: str, train_mask: pd.Series) -> pd.DataFrame:
    """Categorical state at a decision point; terciles fitted on the training rows only (train_mask)."""
    f = pd.DataFrame(index=st.index)
    f["trend"] = st["trend"].fillna("missing")
    f["vix"] = _terc(st.loc[train_mask, "vix_prev"], st["vix_prev"])
    f["us"] = _fixed3(st["us_qqq_ret"], -0.005, 0.005)
    f["positioning"] = _terc(st.loc[train_mask, "fii_long_share"], st["fii_long_share"])
    f["event"] = np.where(st["event_scheduled"], "today", np.where(st["event_recent"], "recent", "none"))
    f["expiry"] = np.where(st["expiry"], "yes", "no")
    f["gap"] = _fixed3(st["gap"], -0.0025, 0.0025)
    if point != "D0":
        mv = st[f"move_{point}"]
        f["move"] = _terc(mv[train_mask], mv)
        f["breadth"] = _fixed3(st[f"breadth_{point}"], 0.40, 0.60, names=("weak", "mid", "strong"))
        f["agreement"] = np.where(st[f"agree_{point}"], "yes", "no")
        ow = st["or15_atr"] if point == "D1" else st["or30_atr"]
        f["or_width"] = _terc(ow[train_mask], ow)
    return f


def design(f: pd.DataFrame, drop: tuple = ()) -> np.ndarray:
    cols = [np.ones(len(f))]
    for c in f.columns:
        if c in drop:
            continue
        for lv in LEVELS[c][1:]:
            cols.append((f[c].astype(str).to_numpy() == lv).astype(float))
    return np.column_stack(cols)


# ----------------------------------------------------------------------------------------------------------------------------- ridge
def ridge_fit(X: np.ndarray, y: np.ndarray, lam: float):
    p = X.shape[1]
    P = np.eye(p) * lam
    P[0, 0] = 0.0
    XtX = X.T @ X
    A_inv = np.linalg.pinv(XtX + P)
    beta = A_inv @ (X.T @ y)
    return beta, A_inv, XtX


def ridge_se(x: np.ndarray, A_inv: np.ndarray, XtX: np.ndarray, s2: float) -> np.ndarray:
    M = A_inv @ XtX @ A_inv
    return np.sqrt(np.maximum(np.einsum("ij,jk,ik->i", x, M, x), 0.0) * s2)


def _winsor(y: np.ndarray) -> np.ndarray:
    lo, hi = np.nanpercentile(y, [1, 99])
    return np.clip(y, lo, hi)


class Model:
    """One ridge per (index, point, action): lambda by leave-one-year-out within the training years, out-of-fold residual variance."""

    def __init__(self, X, y, years, lam: float | None = None, intercept_only: bool = False):
        if intercept_only:
            X = X[:, :1]
        self.io = intercept_only
        yw = _winsor(y)
        uy = sorted(set(years))
        if lam is None:
            best, best_mse = None, np.inf
            for lm in LAMBDAS:
                err = []
                for h in uy:
                    tr, te = years != h, years == h
                    if tr.sum() < 20 or te.sum() == 0:
                        continue
                    b, _, _ = ridge_fit(X[tr], yw[tr], lm)
                    err.append((X[te] @ b - yw[te]) ** 2)
                mse = float(np.mean(np.concatenate(err))) if err else np.inf
                if mse < best_mse - 1e-12:
                    best, best_mse = lm, mse
            lam = best if best is not None else 100.0
        self.lam = lam
        oof = []
        for h in uy:
            tr, te = years != h, years == h
            if tr.sum() < 20 or te.sum() == 0:
                continue
            b, _, _ = ridge_fit(X[tr], yw[tr], lam)
            oof.append(X[te] @ b - yw[te])
        r = np.concatenate(oof) if oof else (yw - yw.mean())
        self.s2 = float(np.mean(r ** 2))
        self.beta, self.A_inv, self.XtX = ridge_fit(X, yw, lam)

    def predict(self, X):
        if self.io:
            X = X[:, :1]
        return X @ self.beta, ridge_se(X, self.A_inv, self.XtX, self.s2)


# ----------------------------------------------------------------------------------------------------------------------------- policy
def planned_cost_bps(o: pd.DataFrame) -> np.ndarray:
    """Cost known at decision time: dated futures fees on the entry value for both legs, planned ticks (no stop assumed)."""
    ticks = 2 + np.where(o["point"] == "D0", 2, 0) + np.where(o["exit"] == "NEXTOPEN", 2, 0)
    out = np.empty(len(o))
    for i, (d, e, lt) in enumerate(zip(o["date"], o["entry"], o["lot"])):
        v = e * lt
        out[i] = (costs.cost("futures", "buy", v, d.year, when=d) + costs.cost("futures", "sell", v, d.year, when=d)) / lt
    return (out + ticks * TICK) / o["entry"].to_numpy() * 1e4


def run_policy(pred: pd.DataFrame, c: float, cost_mult: float = 1.0) -> pd.DataFrame:
    """pred: one row per (date, point, action) with pred_gross, se, pcost, realised net/gross/cost. Sequential D0..D3; first point with a
    qualifying action (pred_net > c*se and > 0) trades the action with the highest pred_net (ties: lower action id)."""
    p = pred.copy()
    p["pred_net"] = p["pred_gross"] - cost_mult * p["pcost"]
    q = p[(p["pred_net"] > c * p["se"]) & (p["pred_net"] > 0)]
    if q.empty:
        return pd.DataFrame(columns=["date", "point", "action", "net_bps"])
    q = q.sort_values(["date", "point", "pred_net", "action"], ascending=[True, True, False, True])
    first = q.groupby("date").head(1)
    first = first.assign(net_bps=first["gross_bps"] - cost_mult * first["cost_bps"])
    return first


def daily(trades: pd.DataFrame, all_days, col: str = "net_bps") -> pd.Series:
    s = pd.Series(0.0, index=pd.Index(sorted(all_days), name="date"))
    if len(trades):
        t = trades.groupby("date")[col].sum()
        s.loc[t.index] = t.values
    return s


def nw_t(x: pd.Series, lag: int = 1) -> tuple[float, float, int]:
    x = pd.Series(x, dtype=float).dropna()
    n = len(x)
    if n < 3:
        return (float("nan"), float("nan"), n)
    u = x - x.mean()
    g0 = float((u * u).sum() / n)
    s = g0
    for k in range(1, lag + 1):
        gk = float((u.iloc[k:].to_numpy() * u.iloc[:-k].to_numpy()).sum() / n)
        s += 2 * (1 - k / (lag + 1)) * gk
    se = math.sqrt(max(s, 1e-18) / n)
    return (float(x.mean()), float(x.mean() / se), n)


# ----------------------------------------------------------------------------------------------------------------------------- walk-forward
def fold_predictions(o: pd.DataFrame, st: pd.DataFrame, sym: str, test_year: int, target: str = "gross_bps", drop: tuple = (),
                     intercept_only: bool = False, lam_from: dict | None = None, shuffle_rng=None, train_years: list | None = None,
                     predict_years: list | None = None):
    """Fit one model per (point, action) on the training years and predict the predict_years (default: the test year).
    Returns predictions and the models' lambdas. shuffle_rng: state rows of the training years permuted in month blocks (null)."""
    s = st[st["index"] == sym].set_index("date").sort_index()
    tr_years = train_years if train_years is not None else [y for y in range(2015, test_year)]
    pr_years = predict_years if predict_years is not None else [test_year]
    tr_days = [d for d in s.index if d.year in tr_years]
    if tr_days:
        tr_days = tr_days[:-1] if test_year in pr_years and train_years is None else tr_days  # drop the last training session (its NEXTOPEN label is the test year's open)
    s_tr_mask = pd.Series(s.index.isin(tr_days), index=s.index)
    feats_src = s.copy()
    if shuffle_rng is not None:
        trs = set(tr_days)
        tr_idx = [d for d in s.index if d in trs]
        months = pd.Series([(d.year, d.month) for d in tr_idx], index=tr_idx)
        blocks = [list(g.index) for _, g in months.groupby(months)]
        order = shuffle_rng.permutation(len(blocks))
        donor = [d for b in order for d in blocks[b]]
        feats_src.loc[tr_idx] = s.loc[donor].to_numpy()
    out, lams = [], {}
    oo = o[o["index"] == sym]
    for point in POINT_ENTRY:
        f = feature_frame(feats_src, point, s_tr_mask)
        f_real = feature_frame(s, point, s_tr_mask) if shuffle_rng is not None else f
        X_all = pd.DataFrame(design(f, drop), index=f.index)
        X_pred_all = pd.DataFrame(design(f_real, drop), index=f.index)
        op = oo[oo["point"] == point]
        for aid in sorted(op["action"].unique()):
            oa = op[op["action"] == aid]
            tr = oa[oa["date"].isin(tr_days)].dropna(subset=[target])
            te = oa[oa["date"].map(lambda d: d.year in pr_years)].dropna(subset=["gross_bps"])
            if len(tr) < 60 or te.empty:
                continue
            X = X_all.loc[tr["date"]].to_numpy()
            yrs = np.array([d.year for d in tr["date"]])
            lam = (lam_from or {}).get((point, aid))
            m = Model(X, tr[target].to_numpy(float), yrs, lam=lam, intercept_only=intercept_only)
            lams[(point, aid)] = m.lam
            pg, se = m.predict(X_pred_all.loc[te["date"]].to_numpy())
            te = te.assign(pred_gross=pg, se=se, s2=m.s2)
            out.append(te)
    return (pd.concat(out, ignore_index=True) if out else pd.DataFrame()), lams


def calibrate_c(o: pd.DataFrame, st: pd.DataFrame, sym: str, test_year: int, lams: dict, intercept_only: bool = False) -> float:
    """Nested leave-one-year-out inside the training years: the c with the best mean daily net on the held-out training years (ties: larger c)."""
    tr_years = list(range(2015, test_year))
    score = {c: [] for c in C_GRID}
    for h in tr_years:
        inner = [y for y in tr_years if y != h]
        pr, _ = fold_predictions(o, st, sym, test_year, intercept_only=intercept_only, lam_from=lams, train_years=inner, predict_years=[h])
        if pr.empty:
            continue
        days_h = [d for d in st.loc[st["index"] == sym, "date"] if d.year == h]
        for c in C_GRID:
            score[c].append(daily(run_policy(pr, c), days_h))
    best, best_v = C_GRID[-1], -np.inf
    for c in C_GRID:
        if score[c]:
            v = float(pd.concat(score[c]).mean())
            if v > best_v + 1e-12 or (abs(v - best_v) <= 1e-12 and c > best):
                best, best_v = c, v
    return best


# ----------------------------------------------------------------------------------------------------------------------------- run
class _DryRegistry:
    """Stand-in for india.registry in dry runs: nothing is written to the ledger."""

    @staticmethod
    def register(*a, **k):
        return {"family": "OC", "study": "SP1-dry", "at": None}

    @staticmethod
    def record(reg, variant, dev, val, extra=None, expect=0, rule="standard"):
        return {"verdict": "DRY", "z": None}

    @staticmethod
    def threshold(k):
        from india import registry
        return registry.threshold(k)

    @staticmethod
    def family_count(f):
        from india import registry
        return registry.family_count(f)


def run(log=print, null_draws: int = 200, dry: bool = False) -> dict:
    from india import registry
    if dry:
        registry = _DryRegistry

    D = paths.data_dir()
    spec = json.loads(SPEC.read_text())
    assert spec["status"].startswith("FROZEN"), "SP1 spec is not frozen"
    o = pd.read_parquet(D / "gold/studies/SP1_outcomes.parquet")
    o["date"] = pd.to_datetime(o["date"]).dt.date
    log("planned costs at decision time")
    o["pcost"] = planned_cost_bps(o)
    st = pd.read_parquet(D / "gold/scenario/index_states.parquet")
    st["date"] = pd.to_datetime(st["date"]).dt.date
    res = {"spec_sha": spec_sha(), "indices": {}}
    policy_trades, io_trades, fold_meta = [], [], []
    rng = np.random.default_rng(7)
    for sym in IDX:
        all_days = {y: [d for d in st.loc[st["index"] == sym, "date"] if d.year == y] for y in TEST_YEARS}
        pol_daily, io_daily, bf_daily, x2_daily, opt_daily = [], [], [], [], []
        for y in TEST_YEARS:
            pr, lams = fold_predictions(o, st, sym, y)
            c = calibrate_c(o, st, sym, y, lams)
            t = run_policy(pr, c)
            t = t.assign(index=sym, c=c)
            policy_trades.append(t)
            pol_daily.append(daily(t, all_days[y]))
            x2_daily.append(daily(run_policy(pr, c, cost_mult=2.0), all_days[y]))
            opt_daily.append(daily(t, all_days[y], col="opt_ret") * 1e4)
            pio, lams_io = fold_predictions(o, st, sym, y, intercept_only=True)
            cio = calibrate_c(o, st, sym, y, lams_io, intercept_only=True)
            tio = run_policy(pio, cio).assign(index=sym, c=cio)
            io_trades.append(tio)
            io_daily.append(daily(tio, all_days[y]))
            # best fixed (point, action) of the training years by mean realised net
            trn = o[(o["index"] == sym) & (o["year"] < y)]
            bf = trn.groupby(["point", "action"])["net_bps"].mean().idxmax()
            bft = o[(o["index"] == sym) & (o["year"] == y) & (o["point"] == bf[0]) & (o["action"] == bf[1])]
            bf_daily.append(daily(bft, all_days[y]))
            fold_meta.append({"index": sym, "test_year": y, "c": c, "c_intercept_only": cio, "trades": int(len(t)), "best_fixed": [bf[0], int(bf[1])],
                              "lambda_median": float(np.median(list(lams.values()))) if lams else None})
            log(f"{sym} {y}: c={c} trades={len(t)} mean daily net={pol_daily[-1].mean():.2f} bps (intercept-only {io_daily[-1].mean():.2f}, c={cio})")
        P, IO, BF, X2, OP = (pd.concat(x) for x in (pol_daily, io_daily, bf_daily, x2_daily, opt_daily))
        res["indices"][sym] = {"policy": P, "io": IO, "bf": BF, "x2": X2, "opt": OP}
    pt = pd.concat(policy_trades, ignore_index=True)
    iot = pd.concat(io_trades, ignore_index=True)
    tag = "_dry" if dry else ""
    pt.to_parquet(D / f"gold/studies/SP1_policy_trades{tag}.parquet", index=False)
    iot.to_parquet(D / f"gold/studies/SP1_intercept_only_trades{tag}.parquet", index=False)
    # state-shuffle null (lambda and c fixed at the real fit's values per fold)
    null = {sym: [] for sym in IDX}
    nul_freq = {sym: [] for sym in IDX}
    if null_draws:
        log(f"state-shuffle null: {null_draws} draws")
        fixed = {(m["index"], m["test_year"]): m for m in fold_meta}
        lam_cache = {}
        for sym in IDX:
            for y in TEST_YEARS:
                _, lam_cache[(sym, y)] = fold_predictions(o, st, sym, y)
        for k in range(null_draws):
            for sym in IDX:
                vals, n_tr = [], 0
                for y in TEST_YEARS:
                    if y < 2018:
                        continue
                    pr, _ = fold_predictions(o, st, sym, y, lam_from=lam_cache[(sym, y)], shuffle_rng=rng)
                    t = run_policy(pr, fixed[(sym, y)]["c"])
                    days_y = [d for d in st.loc[st["index"] == sym, "date"] if d.year == y]
                    vals.append(daily(t, days_y))
                    n_tr += len(t)
                null[sym].append(float(pd.concat(vals).mean()))
                nul_freq[sym].append(n_tr)
            if (k + 1) % 20 == 0:
                log(f"null draw {k + 1}/{null_draws}")
    return score(res, pt, iot, fold_meta, null, nul_freq, o, st, log, registry, dry=dry)


def _period(s: pd.Series, val: bool) -> pd.Series:
    return s[[(d.year >= 2018) == val for d in s.index]]


def score(res, pt, iot, fold_meta, null, nul_freq, o, st, log, registry, dry: bool = False) -> dict:
    D = paths.data_dir()
    reg = registry.register("SP1", family="OC", title="Scenario Playbook phase 1: index intraday playbook (sp1_v2.json)",
                            hypothesis="a policy that reads the situation chooses intraday index actions that earn net of costs, and beats the same policy without the situation",
                            variants=["NIFTY|future_proxy|policy", "NIFTY|future_proxy|vs_intercept_only", "BANKNIFTY|future_proxy|policy",
                                      "BANKNIFTY|future_proxy|vs_intercept_only", "NIFTY|option|policy", "BANKNIFTY|option|policy", "BOOK|option|sized"],
                            note=f"spec {spec_sha()}; SEEN period 2017-2023 (rule seen_val_only); the 2024+ holdout is the only confirmation")
    rows = {}
    for sym, r in res["indices"].items():
        P, IO, BF, X2, OP = r["policy"], r["io"], r["bf"], r["x2"], r["opt"]
        tr_val = int(((pt["index"] == sym) & pt["date"].map(lambda d: d.year >= 2018)).sum())
        nulls = null.get(sym) or []
        real_val = float(_period(P, True).mean())
        extra_common = {"spec": spec_sha(), "val_trades": tr_val, "min_trades_ok": tr_val >= 100,
                        "days_traded_share_val": round(float((_period(P, True) != 0).mean()), 3),
                        "per_year": {int(y): round(float(P[[d.year == y for d in P.index]].mean()), 2) for y in TEST_YEARS},
                        "positive_folds": int(sum(1 for y in TEST_YEARS if P[[d.year == y for d in P.index]].mean() > 0)),
                        "eras": {"2017-2019": round(float(P[[d.year <= 2019 for d in P.index]].mean()), 2),
                                 "2020": round(float(P[[d.year == 2020 for d in P.index]].mean()), 2),
                                 "2021-2023": round(float(P[[d.year >= 2021 for d in P.index]].mean()), 2)},
                        "nw_lag5_val": nw_t(_period(P, True), 5), "costs_x2_val": nw_t(_period(X2, True)),
                        "intercept_only_val": nw_t(_period(IO, True)), "best_fixed_val": nw_t(_period(BF, True)),
                        "null_p_val": round(float(np.mean([v >= real_val for v in nulls])), 4) if nulls else None,
                        "null_mean_trades_val": float(np.mean(nul_freq[sym])) if nul_freq.get(sym) else None,
                        "chosen": pt[pt["index"] == sym].groupby(["point", "exit", "dir"]).size().sort_values(ascending=False).head(8).to_dict()}
        extra_common["chosen"] = {f"{k[0]}|{k[1]}|{'long' if k[2] > 0 else 'short'}": int(v) for k, v in extra_common["chosen"].items()}
        for name, series, extra in ((f"{sym}|future_proxy|policy", P, extra_common),
                                    (f"{sym}|future_proxy|vs_intercept_only", P - IO, {"spec": spec_sha(), "min_trades_ok": tr_val >= 100}),
                                    (f"{sym}|option|policy", OP, {"spec": spec_sha(), "unit": "bps of premium per day", "min_trades_ok": tr_val >= 100,
                                                                  "label": "EXPLORATORY (synthetic options, IV held constant)",
                                                                  "per_trade_val": opt_stats(pt[(pt["index"] == sym) & pt["date"].map(lambda d: d.year >= 2018)])})):
            dev, val = nw_t(_period(series, False)), nw_t(_period(series, True))
            line = registry.record(reg, name, dev=dev, val=val, extra=extra, expect=1, rule="seen_val_only")
            rows[name] = {"dev": dev, "val": val, "verdict": line["verdict"], "z": line["z"], "extra": extra}
            log(f"{name}: dev {dev[0]:.2f} (t {dev[1]:.2f}) val {val[0]:.2f} (t {val[1]:.2f}) -> {line['verdict']}")
    book = book_sim(pt, o, st, log)
    bt = book.pop("_daily")
    unp = book_sim(pt, o, st, log, pause=False)
    unp.pop("_daily")
    book["unpaused"] = unp
    dev, val = boot_t(bt[[d.year < 2018 for d in bt.index]]), boot_t(bt[[d.year >= 2018 for d in bt.index]])
    line = registry.record(reg, "BOOK|option|sized", dev=dev, val=val, extra={"spec": spec_sha(), "label": "EXPLORATORY", **book}, expect=1, rule="seen_val_only")
    rows["BOOK|option|sized"] = {"dev": dev, "val": val, "verdict": line["verdict"], "z": line["z"], "extra": book}
    man = {"at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "spec_sha": spec_sha(), "folds": fold_meta, "rows": rows,
           "coefficients": learned(o, st), "family_z": registry.threshold(registry.family_count("OC"))}
    if dry:
        (Path.home() / "ananta_runs/sp1_check/sp1_results_dry.json").write_text(json.dumps(man, indent=1, default=str))
        return man
    (D / "manifests/sp1_results.json").write_text(json.dumps(man, indent=1, default=str))
    write_report(man)
    return man


def opt_stats(t: pd.DataFrame) -> dict:
    x = t["opt_ret"].dropna()
    if x.empty:
        return {}
    return {"trades": int(len(x)), "mean": round(float(x.mean()), 4), "median": round(float(x.median()), 4), "share_positive": round(float((x > 0).mean()), 3),
            "p01": round(float(x.quantile(0.01)), 3), "p99": round(float(x.quantile(0.99)), 3),
            "mean_without_top_1pct": round(float(x[x < x.quantile(0.99)].mean()), 4),
            "by_era": {k: round(float(v), 4) for k, v in t.dropna(subset=["opt_ret"]).groupby("era")["opt_ret"].mean().items()}}


def boot_t(x: pd.Series, block: int = 20, draws: int = 2000, seed: int = 7) -> tuple[float, float, int]:
    x = pd.Series(x, dtype=float).dropna()
    n = len(x)
    if n < block * 2:
        return (float("nan"), float("nan"), n)
    rng = np.random.default_rng(seed)
    a = x.to_numpy()
    nb = int(np.ceil(n / block))
    means = []
    for _ in range(draws):
        st = rng.integers(0, n - block + 1, nb)
        means.append(np.concatenate([a[s:s + block] for s in st])[:n].mean())
    se = float(np.std(means, ddof=1))
    return (float(a.mean()), float(a.mean() / se) if se > 0 else float("nan"), n)


# ----------------------------------------------------------------------------------------------------------------------------- book
def loss_per_lot(r) -> float:
    """Spec loss cap: premium minus the Black-76 value at the stop moved a further 0.25 daily ATR against the trade, at T of 15:15 that day with
    the entry IV, plus spreads and fees; exits without a stop (T1130, T1515) and NEXTOPEN: the full premium plus the entry spread and fees."""
    sym, day, lot = r.index, r.date, r.lot
    p_in = r.opt_prem_in
    h_in = max(OPT_HALF[sym], 0.0025 * p_in)
    if r.exit in ("T1130", "T1515", "NEXTOPEN") or not (r.stop0 == r.stop0):
        return (p_in + h_in) * lot + costs.cost("options", "buy", (p_in + h_in) * lot, day.year, when=day)
    S = r.stop0 - r.dir * 0.25 * r.atr_d
    T = _t_years(day, 360, r.opt_expiry)
    v = float(greeks.black76(np.array([S * r.opt_carry]), np.array([r.opt_K]), np.array([T]), np.array([r.opt_iv]), np.array([r.dir > 0]))[0][0])
    v = max(v, 0.05)
    h_out = max(OPT_HALF[sym], 0.0025 * v) * 2.0
    sell = max(v - h_out, 0.0)
    buy = p_in + h_in
    fees = costs.cost("options", "buy", buy * lot, day.year, when=day) + costs.cost("options", "sell", sell * lot, day.year, when=day)
    return (buy - sell) * lot + fees


def book_sim(pt: pd.DataFrame, o: pd.DataFrame, st: pd.DataFrame, log, pause: bool = True) -> dict:
    """Rs 60,000 from 2017-01-01, both indices (NIFTY first at each point), fractional-Kelly lots on the option return per rupee of premium
    (second ridge without the event feature, fitted per fold), loss caps at 5% of the session's starting equity, the daily limit and the 22% pause."""
    cfg = json.loads((HERE / "paper_config.json").read_text())
    W0 = float(cfg["books"]["main"]["capital_inr"])
    lim = cfg["survival"]["daily_loss_limit_pct"] / 100
    pause_dd = cfg["survival"]["pause_drawdown_pct"] / 100
    # option-return models per fold for mu and sigma^2
    mus = []
    for sym in IDX:
        for y in TEST_YEARS:
            oo = o.dropna(subset=["opt_ret"])
            pr, _ = fold_predictions(oo, st, sym, y, target="opt_ret", drop=("event",))
            if not pr.empty:
                mus.append(pr[["date", "index", "point", "action", "pred_gross", "s2"]].rename(columns={"pred_gross": "mu_opt", "s2": "s2_opt"}))
    mu = pd.concat(mus, ignore_index=True) if mus else pd.DataFrame(columns=["date", "index", "point", "action", "mu_opt", "s2_opt"])
    t = pt.merge(mu, on=["date", "index", "point", "action"], how="left")
    t["pt_order"] = t["point"].map({"D0": 0, "D1": 1, "D2": 2, "D3": 3})
    t["ix_order"] = t["index"].map({"NIFTY": 0, "BANKNIFTY": 1})
    t = t.sort_values(["date", "pt_order", "ix_order"])
    days = sorted(set(st["date"]) & {d for d in st["date"] if d.year >= 2017})
    W, hwm, paused_on = W0, W0, None
    Wu = W0
    eq, eq_u, reasons = [], [], {"size_zero": 0, "no_option": 0, "loss_cap": 0, "paused": 0, "daily_limit_breach": 0, "taken": 0}
    by_day = {d: g for d, g in t.groupby("date")}
    carry = 0.0  # NEXTOPEN P&L realised at the next session's open
    for d in days:
        start = W
        pnl = carry
        carry = 0.0
        g = by_day.get(d)
        budget = lim * start + min(pnl, 0.0)  # an overnight loss counts against the new session
        if g is not None:
            for r in g.itertuples():
                if paused_on is not None and pause:
                    reasons["paused"] += 1
                    continue
                if not (r.opt_ret == r.opt_ret) or not (r.opt_prem_in == r.opt_prem_in):
                    reasons["no_option"] += 1
                    continue
                prem_lot = r.opt_prem_in * r.lot
                mu_, s2_ = r.mu_opt, r.s2_opt
                if not (mu_ == mu_) or mu_ <= 0 or not (s2_ == s2_) or s2_ <= 0:
                    reasons["size_zero"] += 1
                    continue
                n = math.floor(0.25 * start * mu_ / s2_ / prem_lot)
                loss_lot = loss_per_lot(r)
                cap = math.floor(max(budget, 0.0) / loss_lot) if loss_lot > 0 else 0
                if n <= 0:
                    reasons["size_zero"] += 1
                    continue
                if cap <= 0:
                    reasons["loss_cap"] += 1
                    continue
                n = min(n, cap)
                budget -= n * loss_lot
                trade = n * r.opt_net_rs
                reasons["taken"] += 1
                if r.next_day:
                    carry += trade
                else:
                    pnl += trade
        if pnl < -lim * start - 1e-9:
            reasons["daily_limit_breach"] += 1
        W += pnl
        hwm = max(hwm, W)
        if paused_on is None and W < (1 - pause_dd) * hwm:
            paused_on = d
        eq.append((d, W))
    s = pd.Series(dict(eq))
    daily_rs = s.diff().fillna(s.iloc[0] - W0)
    dd = float((s / s.cummax() - 1).min())
    yearly = {int(y): round(float(v), 0) for y, v in s.groupby([d.year for d in s.index]).last().items()}
    out = {"path": "paused at the 22% rule" if pause else "unpaused (what would have happened without the pause)", "start_inr": W0,
           "end_inr": round(float(s.iloc[-1]), 0), "max_drawdown": round(dd, 4), "pause_date": str(paused_on) if paused_on else None,
           "equity_at_year_end": yearly, "reasons": reasons, "_daily": daily_rs}
    log(f"book ({'paused' if pause else 'unpaused'}): Rs {W0:,.0f} -> Rs {s.iloc[-1]:,.0f}; max drawdown {dd:.1%}; pause {paused_on}; {reasons}")
    return out


# ----------------------------------------------------------------------------------------------------------------------------- learned / report
def learned(o: pd.DataFrame, st: pd.DataFrame) -> dict:
    """What the final fold (trained 2015-2022) learned: for each index and point, the actions with the highest mean predicted net across the
    2023 days, and their largest coefficients (bps)."""
    out = {}
    for sym in IDX:
        pr, _ = fold_predictions(o, st, sym, 2023)
        if pr.empty:
            continue
        pr["pred_net"] = pr["pred_gross"] - pr["pcost"]
        top = pr.groupby(["point", "action"])["pred_net"].mean().sort_values(ascending=False).head(6)
        out[sym] = [{"point": p, "action": f"{ACTIONS[a][0]}|{'long' if ACTIONS[a][1] > 0 else 'short'}", "mean_pred_net_bps": round(float(v), 2)} for (p, a), v in top.items()]
    return out


def _f(x, nd=2):
    return "–" if x is None or x != x else f"{x:.{nd}f}"


def write_report(man: dict) -> None:
    L = ["# SP1 results: index intraday playbook (Scenario Playbook phase 1)", "",
         f"Spec `sp1_v2.json` sha `{man['spec_sha']}` (frozen before any result; reviewed twice independently). Run {man['at']}.",
         "**SEEN-period evidence**: 2017-2023 shaped this design through OC v1, so these rows use the seen_val_only rule (verdict on 2018-2023 at the "
         f"family z = {man['family_z']:.2f}; 2017 reported). The only confirmatory test is the registered 2024-2026 holdout run.", "",
         "Unit: net basis points of the index per day (0 on no-trade days), after dated futures costs; option rows in bps of premium per day "
         "(EXPLORATORY, synthetic prices); the book in rupees.", "",
         "| Row | 2017 (t, days) | 2018-2023 (t, days) | Verdict |", "|---|---|---|---|"]
    for k, r in man["rows"].items():
        L.append(f"| {k} | {_f(r['dev'][0])} ({_f(r['dev'][1])}, {r['dev'][2]}) | {_f(r['val'][0])} ({_f(r['val'][1])}, {r['val'][2]}) | {r['verdict']} |")
    L += ["", "## Per index", ""]
    for k, r in man["rows"].items():
        if k.endswith("|future_proxy|policy"):
            x = r["extra"]
            L += [f"### {k.split('|')[0]}", "",
                  f"- validation trades {x['val_trades']} (days traded {x['days_traded_share_val']:.0%}); per year {x['per_year']}; positive folds {x['positive_folds']}/7; eras {x['eras']}",
                  f"- benchmarks 2018-2023 (mean, t, days): intercept-only {tuple(round(v, 2) for v in x['intercept_only_val'][:2])}, best fixed of training {tuple(round(v, 2) for v in x['best_fixed_val'][:2])}, costs x2 {tuple(round(v, 2) for v in x['costs_x2_val'][:2])}, Newey-West lag 5 t {x['nw_lag5_val'][1]:.2f}",
                  f"- state-shuffle null: p = {x['null_p_val']}; the null policies made {x['null_mean_trades_val']} trades on average in 2018-2023",
                  f"- most chosen: {x['chosen']}", ""]
    b = man["rows"].get("BOOK|option|sized", {}).get("extra", {})
    L += ["## The Rs 60,000 book (EXPLORATORY)", "", f"```\n{json.dumps(b, indent=1, default=str)}\n```", "",
          "## What the last fold learned (trained 2015-2022, mean predicted net over 2023 days)", "", f"```\n{json.dumps(man['coefficients'], indent=1)}\n```", "",
          "## Folds", "", f"```\n{json.dumps(man['folds'], indent=1)}\n```"]
    (HERE / "registrations" / "sp1_results.md").write_text("\n".join(L) + "\n")


# ----------------------------------------------------------------------------------------------------------------------------- selftest
def selftest() -> dict:
    T = 30
    O = np.full((1, T), 100.0); H = O + 0.2; L = O - 0.2
    # long trail with k=1: entry 100 at bar 2; highs rise to 103 by bar 6 (best 103), bar 8 low 101.9 <= 102 -> stopped at 102
    for t, v in zip(range(3, 7), (101, 102, 102.5, 103)):
        O[0, t] = v; H[0, t] = v; L[0, t] = v - 0.1
    O[0, 7] = 102.6; H[0, 7] = 102.7; L[0, 7] = 102.4
    O[0, 8] = 102.3; H[0, 8] = 102.4; L[0, 8] = 101.9
    px, tx, st = trail_exit(O, H, L, np.array([2]), np.array([1]), np.array([1.0]), 20)
    assert st[0] and tx[0] == 8 and abs(px[0] - 102.0) < 1e-9, (px, tx, st)
    # gap below the trail fills at the open
    O2, L2 = O.copy(), L.copy()
    O2[0, 8] = 101.5; L2[0, 8] = 101.4
    px, tx, st = trail_exit(O2, H, L2, np.array([2]), np.array([1]), np.array([1.0]), 20)
    assert st[0] and abs(px[0] - 101.5) < 1e-9
    # short mirror
    px, tx, st = trail_exit(200 - O, 200 - L, 200 - H, np.array([2]), np.array([-1]), np.array([1.0]), 20)
    assert st[0] and tx[0] == 8 and abs(px[0] - 98.0) < 1e-9, (px, tx)
    # no hit -> time exit at the open of X
    px, tx, st = trail_exit(O, H, L, np.array([2]), np.array([1]), np.array([50.0]), 20)
    assert (not st[0]) and tx[0] == 20 and abs(px[0] - O[0, 20]) < 1e-9
    # option: ATM call ~ 0.4 F sigma sqrt(T) (r small), and a long call gains when the index rises
    F, sig, Tt = 20000.0, 0.15, 7 / 365
    c = float(greeks.black76(np.array([F]), np.array([F]), np.array([Tt]), np.array([sig]), np.array([True]))[0][0])
    assert abs(c - 0.3989 * F * sig * math.sqrt(Tt)) / c < 0.02, c
    setup = {"expiry": dt.date(2023, 1, 12), "carry": 1.0, "listed": np.array([17900.0, 18000.0, 18100.0]),
             "CE": (np.array([18000.0]), np.array([0.14])), "PE": (np.array([18000.0]), np.array([0.15]))}
    up = option_leg("NIFTY", dt.date(2023, 1, 9), setup, 1, 18010.0, 15, 18150.0, dt.date(2023, 1, 9), 360, False, 50)
    dn = option_leg("NIFTY", dt.date(2023, 1, 9), setup, 1, 18010.0, 15, 17900.0, dt.date(2023, 1, 9), 360, True, 50)
    assert up["opt_K"] == 18000.0 and up["opt_net_rs"] > 0 > dn["opt_net_rs"], (up, dn)
    # time decay: an unchanged index loses value over the day
    fl = option_leg("NIFTY", dt.date(2023, 1, 9), setup, 1, 18010.0, 15, 18010.0, dt.date(2023, 1, 9), 360, False, 50)
    assert fl["opt_prem_out"] < fl["opt_prem_in"]
    # action list: 12 actions, the fixed order
    assert len(ACTIONS) == 12 and ACTIONS[0] == ("T1130", 1) and ACTIONS[-1] == ("NEXTOPEN", -1)
    return {"selftest": "PASS", "spec_sha": spec_sha()}


if __name__ == "__main__":
    paths.ensure()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "selftest"
    if cmd == "selftest":
        print(selftest())
    elif cmd == "outcomes":
        o = outcomes(lambda s: print(f"[{dt.datetime.now():%H:%M:%S}] {s}", flush=True))
        print(len(o))
    elif cmd in ("run", "dry"):
        draws = int(sys.argv[2]) if len(sys.argv) > 2 else (200 if cmd == "run" else 2)
        run(lambda s: print(f"[{dt.datetime.now():%H:%M:%S}] {s}", flush=True), null_draws=draws, dry=(cmd == "dry"))
    else:
        raise SystemExit(__doc__)
