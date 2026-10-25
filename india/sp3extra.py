"""SP3's remaining parts, exactly as the frozen spec (registrations/sp3_v1.json, sha 20f9070f3d3a61c9) lists them, on dev 2010-2017 and
validation 2018-2023 only (every row dated 2023-12-29 or earlier; the holdout is not opened here):

  python -m india.sp3extra index [--no-registry]   the INDEX rows: NIFTY and BANKNIFTY near-month futures shadow books (stage_2 index_actions,
                                                   stage_3 market features with each index's own trend and 20-session return, stage_4 models
                                                   per index and action, stage_5 index_book); rows INDEX|<index>|policy and
                                                   INDEX|<index>|vs_intercept_only into the ledger (rule seen_val_only, the frozen union_k bar)
  python -m india.sp3extra real                    the real stock fit once more (lambda, c, decisions), cached for the parts below
  python -m india.sp3extra nulls <first> <last>    state-shuffle null draws for seeds first..last (tests.nulls; descriptive)
  python -m india.sp3extra ablation <group>        one drop-one feature-group ablation (stage_6 reports), a full refit without the group
  python -m india.sp3extra months                  the policy book started in each of 12 months (2010 and 2018 starts)
  python -m india.sp3extra reverse                 the reverse family priority (tests.robustness): priority flags recomputed, full refit, books
  python -m india.sp3extra filters                 filters-as-findings: named conditions as on/off slices of the baseline population, per family
                                                   and action, dev and validation (descriptive)
  python -m india.sp3extra report                  collects every part into manifests/sp3_extra.json and the "Remaining parts" section of
                                                   registrations/sp3_results.md

Nothing here tunes the frozen policy: the nulls, ablations, start months, reverse priority and slices are reports the spec asked for.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import pickle
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from india import costs, paths
from india import sp3learn as Lr
from india import sp3run as R

G = paths.gold() / "studies"
OUT = Path.home() / "ananta_runs" / "sp3x"
YEARS, DEV_YEARS, VAL_YEARS = Lr.YEARS, Lr.DEV_YEARS, Lr.VAL_YEARS
GAP = Lr.GAP
E_END = pd.Timestamp(R.E_END)


def _log_to(name: str):
    OUT.mkdir(parents=True, exist_ok=True)
    f = OUT / name

    def log(m):
        print(m, flush=True)
        with f.open("a") as fh:
            fh.write(f"{dt.datetime.now().isoformat(timespec='seconds')} {m}\n")
    return log


def _jdump(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1, default=str))


# ============================================================================================================================ INDEX rows
TICK = 0.05
IDX = {"NIFTY": "NIFTY 50", "BANKNIFTY": "NIFTY BANK"}
IW = 61                                            # bars T+1 .. T+61, as the stock windows
# stage_2 index_actions in the spec's order (ties in score go to the earlier one): long then short x {hold 5, 10, 20; close beyond the 10-day
# average, capped at 60 sessions; close beyond the 20-day low (long) / high (short), 20-session limit}; no ATR stop on any index action
IACTIONS = [(f"{side}_{k}", side, k) for side in ("long", "short") for k in ("hold_5", "hold_10", "hold_20", "sma10_cap60", "x20_lim20")]
INA = len(IACTIONS)
IMIN_VAL_TRADES = 100


def _index_inputs(sym: str, sess: pd.DatetimeIndex) -> dict:
    """Spot bars (the index, for the exit decisions), the near-month contract chain (fills and marks) and lots, all to 2023-12-29."""
    import duckdb
    D = paths.data_dir()
    ix = pd.read_parquet(D / "silver" / "kite_index" / "day" / "day.parquet", columns=["index_name", "date", "open", "high", "low", "close"])
    ix["date"] = pd.to_datetime(ix["date"])
    ix = ix[(ix["index_name"] == IDX[sym]) & (ix["date"] <= E_END)].drop_duplicates("date", keep="last").set_index("date").sort_index()
    spot = ix.reindex(sess).ffill()
    con = duckdb.connect()
    fut = con.execute(f"select date, expiry, open, high, low, close, lot_est from read_parquet('{D / 'silver' / 'fo_bhavcopy' / 'year=*' / 'part.parquet'}') "
                      "where instrument = 'FUTIDX' and symbol = ? and date <= ?", [sym, E_END.date()]).df()
    con.close()
    fut["date"], fut["expiry"] = pd.to_datetime(fut["date"]), pd.to_datetime(fut["expiry"])
    # one monthly contract per expiry month: the files label a few contracts with two dates (an expiry moved for a holiday, e.g. June 2023's
    # 29th -> 28th, Feb 2014), so the contract key is the expiry month and its expiry is its last traded session (the label when the contract
    # outlives the data)
    fut["ym"] = fut["expiry"].dt.year * 12 + fut["expiry"].dt.month - 1
    g = fut.groupby("ym").agg(last_row=("date", "max"), label=("expiry", "min"))
    eff = np.where(g["last_row"] >= g["label"] - pd.Timedelta(days=7), g["last_row"], g["label"])
    fut["expiry"] = fut["ym"].map(dict(zip(g.index, pd.to_datetime(eff))))
    fut = fut.sort_values(["date", "expiry", "open"]).drop_duplicates(["date", "expiry"], keep="last")
    lot = fut.groupby("date")["lot_est"].max().reindex(sess).ffill().bfill()
    return {"spot": spot, "fut": fut, "lot": lot, "relabelled_months": int((g["last_row"] < g["label"]).sum())}


def build_index_outcomes(sym: str, log=print) -> dict:
    """Per signal session T (2005-2023) of one index: the entry contract, the window's long-basis P&L in points (marks at every close, fills at
    every open, rolls at the close two sessions before expiry into the next month), ticks and dated fees per leg, and the 10 actions' exit bars
    decided on the index's own closes (fills on the future). Returns arrays indexed by candidate."""
    sess = R.sessions()
    sd = sess.to_numpy().astype("datetime64[D]")
    pos = {d: i for i, d in enumerate(sess)}
    inp = _index_inputs(sym, sess)
    spot, fut, lot = inp["spot"], inp["fut"], inp["lot"]
    exps = sorted(fut["expiry"].unique())
    e_idx = np.array([int(sess.searchsorted(e)) for e in exps])      # the expiry session (or the next session if the expiry is not one)
    roll_idx = e_idx - 2                                              # the roll session: two sessions before expiry
    # price lookup per (expiry index, session index)
    fut["ei"] = fut["expiry"].map({e: k for k, e in enumerate(exps)})
    fut["si"] = fut["date"].map(pos)
    fut = fut.dropna(subset=["si"])
    O = {(int(a), int(b)): float(o) for a, b, o in zip(fut["ei"], fut["si"], fut["open"]) if o == o and o > 0}
    C = {(int(a), int(b)): float(c) for a, b, c in zip(fut["ei"], fut["si"], fut["close"]) if c == c and c > 0}
    sO, sH, sL, sC = (spot[c].to_numpy(float) for c in ("open", "high", "low", "close"))
    LOT = lot.to_numpy(float)
    first_fut = fut["date"].min()
    n_s = len(sess)
    cands = [i for i in range(n_s - 1) if sess[i] >= pd.Timestamp("2005-01-01") and sess[i + 1] >= first_fut]
    N = len(cands)
    Pc = np.full((N, IW), np.nan); Po = np.full((N, IW), np.nan)
    roll_at = np.zeros((N, IW), bool)
    nroll_before = np.zeros((N, IW), np.int16)          # rolls at closes of bars < j (paid before an exit at the open of bar j)
    n_valid = np.zeros(N, np.int16)
    E = np.full(N, np.nan); lotv = np.full(N, np.nan); val_T = np.full(N, np.nan)
    fee_in = np.zeros((N, 2)); fee_roll = np.zeros((N, IW, 2)); fee_out = np.zeros((N, IW, 2))   # [:, ..., 0] long, 1 short; fractions of lot x E
    WS = {k: np.full((N, IW), np.nan) for k in ("O", "H", "L", "C")}
    HH20 = np.full((N, IW), np.nan); LL20 = np.full((N, IW), np.nan)
    cnt = {"entry_spot": 0, "carried_close": 0, "exit_open_carried": 0, "roll_new_spot": 0, "rolls": 0}
    roll_list = list(roll_idx)

    def contract_for(s: int) -> int:
        k = int(np.searchsorted(roll_idx, s, side="right"))           # first expiry whose roll session is after s
        return min(k, len(exps) - 1)

    def fdate(s):
        return pd.Timestamp(sd[s]).date()

    # spot 20-bar lows/highs before each session (history included)
    lowS, highS = pd.Series(sL), pd.Series(sH)
    ll20_all = lowS.rolling(20, min_periods=20).min().shift(1).to_numpy()
    hh20_all = highS.rolling(20, min_periods=20).max().shift(1).to_numpy()
    for n, i in enumerate(cands):
        s0 = i + 1
        nv = min(IW, n_s - s0)
        n_valid[n] = nv
        k = contract_for(s0)
        o0 = O.get((k, s0))
        if o0 is None:
            o0 = float(sO[s0]); cnt["entry_spot"] += 1
        E[n] = o0
        lt = LOT[s0] if LOT[s0] == LOT[s0] else np.nan
        lotv[n] = lt
        cT = C.get((k, i), float(sC[i]))
        val_T[n] = cT * lt
        notional = o0 * lt
        fee_in[n, 0] = costs.cost("futures", "buy", notional, when=fdate(s0)) / notional
        fee_in[n, 1] = costs.cost("futures", "sell", notional, when=fdate(s0)) / notional
        realized, b, last_c, rolls = 0.0, o0, o0, 0
        for j in range(nv):
            s = s0 + j
            if j > 0:
                op = O.get((k, s))
                if op is None:
                    op = last_c; cnt["exit_open_carried"] += 1
                Po[n, j] = realized + op - b
                fee_out[n, j, 0] = costs.cost("futures", "sell", op * lt, when=fdate(s)) / notional
                fee_out[n, j, 1] = costs.cost("futures", "buy", op * lt, when=fdate(s)) / notional
                nroll_before[n, j] = rolls
            c = C.get((k, s))
            if c is None:
                c = last_c; cnt["carried_close"] += 1
            last_c = c
            Pc[n, j] = realized + c - b
            WS["O"][n, j], WS["H"][n, j], WS["L"][n, j], WS["C"][n, j] = sO[s], sH[s], sL[s], sC[s]
            LL20[n, j], HH20[n, j] = ll20_all[s], hh20_all[s]
            if s == roll_idx[k] and j < nv - 1 and k + 1 < len(exps):
                k2 = k + 1
                cn = C.get((k2, s))
                if cn is None:
                    cn = float(sC[s]); cnt["roll_new_spot"] += 1
                realized += c - b
                b, last_c = cn, cn
                roll_at[n, j] = True
                rolls += 1; cnt["rolls"] += 1
                fee_roll[n, j, 0] = (costs.cost("futures", "sell", c * lt, when=fdate(s)) + costs.cost("futures", "buy", cn * lt, when=fdate(s))) / notional
                fee_roll[n, j, 1] = (costs.cost("futures", "buy", c * lt, when=fdate(s)) + costs.cost("futures", "sell", cn * lt, when=fdate(s))) / notional
                k = k2
    # exits: decided on the index's closes, filled at the next open of the future (exit bar k >= 1); IW = never inside the window
    idx = np.arange(IW)[None, :]
    valid = idx < n_valid[:, None]
    Cw = WS["C"]
    sma10 = pd.DataFrame(Cw).T.rolling(10, min_periods=10).mean().T.to_numpy()
    exit_bar = np.full((N, INA), IW, np.int16)
    for a, (name, side, kind) in enumerate(IACTIONS):
        if kind.startswith("hold_"):
            pend = idx + 1 >= int(kind.split("_")[1])
        elif kind == "sma10_cap60":
            beyond = (Cw < sma10) if side == "long" else (Cw > sma10)
            pend = ((idx + 1 >= 10) & beyond) | (idx + 1 >= 60)
        else:
            beyond = (Cw < LL20) if side == "long" else (Cw > HH20)
            pend = beyond | (idx + 1 >= 20)
        pend = pend & valid
        first = np.where(pend.any(axis=1), pend.argmax(axis=1), IW)
        exit_bar[:, a] = np.where(first < IW, first + 1, IW)
    # gross per action: long-basis points with the sign and the adverse ticks (entry 1, each roll 2, exit 1), as a fraction of the entry open
    gross = np.full((N, INA), np.nan); hold = np.zeros((N, INA), np.int16); fees = np.zeros((N, INA)); end_data = np.zeros((N, INA), bool)
    rows = np.arange(N)
    rolls_upto = roll_at.cumsum(axis=1)
    for a, (name, side, kind) in enumerate(IACTIONS):
        sg = 1.0 if side == "long" else -1.0
        d = 0 if side == "long" else 1
        kb = exit_bar[:, a].astype(int)
        inside = kb < n_valid
        last = n_valid.astype(int) - 1
        pts = np.where(inside, sg * Po[rows, np.minimum(kb, IW - 1)] - (2 + 2 * nroll_before[rows, np.minimum(kb, IW - 1)]) * TICK,
                       sg * Pc[rows, last] - (1 + 2 * rolls_upto[rows, last]) * TICK)
        gross[:, a] = pts / E
        hold[:, a] = np.where(inside, kb, n_valid)
        cum_roll_fee = np.cumsum(fee_roll[:, :, d], axis=1)
        fees[:, a] = fee_in[:, d] + np.where(inside, np.where(kb >= 1, cum_roll_fee[rows, np.maximum(kb - 1, 0)], 0) + fee_out[rows, np.minimum(kb, IW - 1), d],
                                             cum_roll_fee[rows, last])
        end_data[:, a] = ~inside
    flat = float(np.mean(np.abs(sH - sL) < 1e-9)) if len(sH) else float("nan")
    fut_days = set(fut["date"])
    info = {"index": sym, "candidates": N, "first_signal": str(sess[cands[0]].date()), "last_signal": str(sess[cands[-1]].date()), "counts": cnt,
            "spot_days_with_high_equal_low_share": round(flat, 4), "expiries": len(exps), "contract_months_relabelled": inp["relabelled_months"],
            "sessions_without_any_future_row": [str(x.date()) for x in sess if x >= pd.Timestamp("2005-01-01") and x not in fut_days]}
    log(f"  {sym}: {N} candidates {info['first_signal']}..{info['last_signal']}, counts {cnt}")
    return {"sym": sym, "sess": sess, "sess_i": np.array(cands), "s0": np.array(cands) + 1, "n_valid": n_valid, "E": E, "lot": lotv, "val_T": val_T,
            "Pc": Pc, "Po": Po, "roll_at": roll_at, "fee_in": fee_in, "fee_roll": fee_roll, "fee_out": fee_out, "exit_bar": exit_bar,
            "gross": gross, "hold": hold, "fees": fees, "end_data": end_data, "info": info}


def index_features(sym: str, X: dict) -> pd.DataFrame:
    """stage_3 market features for the index candidates: SP3's market table, with trend and 20-session return computed on the index itself."""
    m = pd.read_parquet(G / "SP3_market.parquet")
    m["date"] = pd.to_datetime(m["date"])
    m = m.set_index("date")
    if sym != "NIFTY":
        D = paths.data_dir()
        ix = pd.read_parquet(D / "silver" / "kite_index" / "day" / "day.parquet", columns=["index_name", "date", "close"])
        ix["date"] = pd.to_datetime(ix["date"])
        s = ix[(ix["index_name"] == IDX[sym]) & (ix["date"] <= E_END)].drop_duplicates("date", keep="last").set_index("date")["close"].sort_index()
        a50, a200 = R._vs(s, 50), R._vs(s, 200)
        trend = pd.Series(np.where(a50.isna() | a200.isna(), "missing", np.where((a50 > 0) & (a200 > 0), "above_both", np.where((a50 < 0) & (a200 < 0), "below_both", "mixed"))), index=s.index)
        m["nifty_trend"] = trend.reindex(m.index).fillna("missing")
        m["nifty_ret20"] = (s / s.shift(20) - 1).reindex(m.index)
    f = m.reindex(X["sess"][X["sess_i"]]).reset_index()
    for c in R.MARKET_CAT:
        f[c] = f[c].fillna("missing")
    return f


def index_design(f: pd.DataFrame, train: np.ndarray) -> np.ndarray:
    cats = {}
    for c in R.MARKET_NUM:
        v = f[c].to_numpy(dtype=float)
        cats[c] = Lr.tercile_level(v, Lr.tercile_cuts(v[train]))
    for c in R.MARKET_CAT:
        cats[c] = f[c].to_numpy()
    mats = [np.ones((len(f), 1))]
    for c, v in cats.items():
        for lv in sorted(set(v[train])):
            mats.append((v == lv).astype(float)[:, None])
    return np.concatenate(mats, axis=1)


class IndexBook:
    """stage_5 index_book: one position at a time; entries at T+1's open in the contract chosen there; the daily return is the change in the
    position's mark at each close in fractions of one future's notional (the entry open x the lot), net of the dated fees on the day each leg
    is paid; rolls at the close two sessions before expiry; a close-based exit fills at the next open; the index is not bought back at the open
    where its position left (as the stock book's rule); idle days return 0. A shadow book: no survival lines (Rs 60,000 cannot margin a lot)."""

    def __init__(self, X: dict):
        self.X = X
        self.row_of_s0 = {int(s): n for n, s in enumerate(X["s0"])}

    def run(self, s_first: int, s_last: int, entries: dict) -> dict:
        """entries: {entry session: (candidate row, action)}. Returns the daily series (index = session) and the trades."""
        X = self.X
        ret = np.zeros(s_last - s_first + 1)
        trades = []
        pos = None              # (row, action, s0, exit_bar k, inside)
        for s in range(s_first, s_last + 1):
            r_today = 0.0
            exited = False
            if pos is not None:
                n, a, s0, k, inside, sg, d = pos
                j = s - s0
                if inside and j == k:
                    r_today += sg * (X["Po"][n, j] - X["Pc"][n, j - 1]) / X["E"][n] - TICK / X["E"][n] - X["fee_out"][n, j, d]
                    trades.append({"row": n, "action": IACTIONS[a][0], "entry_s": s0, "exit_s": s, "net": float(X["gross"][n, a] - X["fees"][n, a]), "hold": int(k)})
                    pos, exited = None, True
            if pos is None and not exited and s in entries:
                n, a = entries[s]
                sg, d = (1.0, 0) if IACTIONS[a][1] == "long" else (-1.0, 1)
                k = int(X["exit_bar"][n, a])
                pos = (n, a, s, k, k < X["n_valid"][n], sg, d)
                r_today += sg * X["Pc"][n, 0] / X["E"][n] - TICK / X["E"][n] - X["fee_in"][n, d]
                if X["roll_at"][n, 0]:
                    r_today += -2 * TICK / X["E"][n] - X["fee_roll"][n, 0, d]
            elif pos is not None and not exited:
                n, a, s0, k, inside, sg, d = pos
                j = s - s0
                if j < X["n_valid"][n]:
                    r_today += sg * (X["Pc"][n, j] - X["Pc"][n, j - 1]) / X["E"][n]
                    if X["roll_at"][n, j]:
                        r_today += -2 * TICK / X["E"][n] - X["fee_roll"][n, j, d]
            ret[s - s_first] = r_today
        if pos is not None:
            n, a, s0, k, inside, sg, d = pos
            trades.append({"row": n, "action": IACTIONS[a][0], "entry_s": s0, "exit_s": -1, "net": float("nan"), "hold": int(s_last - s0 + 1)})
        dates = pd.to_datetime(X["sess"][s_first:s_last + 1])
        return {"daily": pd.Series(ret, index=dates), "trades": pd.DataFrame(trades)}


def _first_of_year(sess) -> dict:
    return {y: int(sess.searchsorted(pd.Timestamp(f"{y}-01-01"))) for y in range(2005, 2025)}


def index_fold(X: dict, f: pd.DataFrame, y: int, intercept_only: bool = False) -> dict:
    sess = X["sess"]
    fy = _first_of_year(sess)
    ly = {t: fy[t + 1] - 1 for t in range(2005, 2024)}
    si = X["sess_i"]
    year = sess[si].year.to_numpy()
    cutoff = fy[y] - GAP
    train = (si <= cutoff) & (year >= 2005)
    test = year == y
    Xd = index_design(f, train)
    if intercept_only:
        Xd = Xd[:, :1]
    tr, te = np.flatnonzero(train), np.flatnonzero(test)
    pred = np.full((len(si), INA), np.nan); se = pred.copy(); oofp = pred.copy(); oofs = pred.copy()
    hm = np.zeros(INA)
    lams = {}
    if len(tr) < Lr.MIN_TRAIN or len(np.unique(year[tr])) < Lr.MIN_TRAIN_YEARS:
        return {"year": y, "skipped": True, "decisions": pd.DataFrame({"row": te, "action": -1, "score": np.nan}), "c": None, "lambdas": {}}
    for a in range(INA):
        yv = X["gross"][tr, a]
        good = np.isfinite(yv) & ~X["end_data"][tr, a]
        mdl = Lr.fit_family_action(Xd[tr[good]], yv[good], year[tr[good]], si[tr[good]], fy, ly)
        oofp[tr[good], a], oofs[tr[good], a] = mdl["oof_pred"], mdl["oof_se"]
        if len(te):
            pred[te, a], se[te, a] = Lr.predict(mdl, Xd[te])
        hm[a] = float(X["hold"][tr[good], a].mean())
        lams[IACTIONS[a][0]] = mdl["lambda"]
    fee = np.array([(costs.cost("futures", "buy", v, when=pd.Timestamp(sess[s]).date()) + costs.cost("futures", "sell", v, when=pd.Timestamp(sess[s]).date())) / v
                    if v == v and v > 0 else np.nan for v, s in zip(X["val_T"], si)])
    book = IndexBook(X)

    def decide(rows, P, S, c):
        pn = P[rows] - fee[rows, None]
        sm = np.where(np.isfinite(pn) & (pn > c * S[rows]) & (pn > 0), pn / hm[None, :], -np.inf)
        act = np.where(np.isfinite(sm.max(axis=1)), sm.argmax(axis=1), -1)
        return act, np.where(act >= 0, sm.max(axis=1), np.nan)

    inner = sorted(set(year[tr]) & set(range(2005, y)))
    table = {}
    for c in Lr.C_GRID:
        act, sc = decide(tr, oofp, oofs, c)
        vals = []
        for t in inner:
            m = year[tr] == t
            ent = {int(X["s0"][r]): (int(r), int(a)) for r, a in zip(tr[m], act[m]) if a >= 0}
            if not m.any():
                continue
            vals.append(float(book.run(fy[t], ly[t], ent)["daily"].mean()))
        table[c] = float(np.mean(vals)) if vals else float("nan")
    best_c = max(Lr.C_GRID, key=lambda c: (table[c] if table[c] == table[c] else -np.inf, c))
    act, sc = decide(te, pred, se, best_c)
    return {"year": y, "skipped": False, "c": best_c, "c_table": {str(k): round(v, 8) for k, v in table.items()}, "lambdas": lams,
            "decisions": pd.DataFrame({"row": te, "action": act, "score": sc}), "hold_mean": dict(zip([a[0] for a in IACTIONS], hm.round(2)))}


def run_index(write_registry: bool = True, log=print) -> dict:
    R._check_spec()
    t0 = time.time()
    out = {"spec_version": "sp3-v1-2026-10-20-frozen", "rows": {}, "per_index": {}}
    series = {}
    for sym in IDX:
        X = build_index_outcomes(sym, log)
        f = index_features(sym, X)
        sess = X["sess"]
        fy = _first_of_year(sess)
        folds = {y: index_fold(X, f, y) for y in YEARS}
        folds0 = {y: index_fold(X, f, y, intercept_only=True) for y in YEARS}
        log(f"  {sym}: c by year {{{', '.join(f'{y}:{folds[y]['c']}' for y in YEARS)}}}  {time.time() - t0:.0f}s")
        book = IndexBook(X)
        s0, s1 = fy[2010], fy[2024] - 1
        res = {}
        for lab, fl in (("policy", folds), ("intercept_only", folds0)):
            dec = pd.concat([fl[y]["decisions"] for y in YEARS], ignore_index=True)
            ent = {int(X["s0"][r]): (int(r), int(a)) for r, a in zip(dec["row"], dec["action"]) if a >= 0}
            res[lab] = book.run(s0, s1, ent)
            res[lab]["n_decisions"] = int((dec["action"] >= 0).sum())
        pol, ino = res["policy"]["daily"], res["intercept_only"]["daily"]
        series[f"INDEX|{sym}|policy"] = pol
        series[f"INDEX|{sym}|vs_intercept_only"] = pol - ino
        tr = res["policy"]["trades"]
        tr_dates = pd.to_datetime(sess[tr["entry_s"].to_numpy()]) if len(tr) else pd.DatetimeIndex([])
        closed = tr[tr["exit_s"] >= 0] if len(tr) else tr
        val_tr = int((tr_dates.year >= 2018).sum()) if len(tr) else 0
        dev_tr = int((tr_dates.year < 2018).sum()) if len(tr) else 0
        acts = tr["action"].value_counts().to_dict() if len(tr) else {}
        by_year = {int(y): int(n) for y, n in pd.Series(tr_dates.year).value_counts().sort_index().items()} if len(tr) else {}
        out["per_index"][sym] = {"info": X["info"], "trades": {"dev": dev_tr, "val": val_tr, "min_val_trades": IMIN_VAL_TRADES}, "actions_taken": acts, "trades_by_year": by_year,
                                 "net_per_trade_mean": float(closed["net"].mean()) if len(closed) else None, "win_rate": float((closed["net"] > 0).mean()) if len(closed) else None,
                                 "c_by_year": {y: folds[y]["c"] for y in YEARS}, "c_by_year_intercept_only": {y: folds0[y]["c"] for y in YEARS},
                                 "lambdas_2023": folds[2023]["lambdas"], "hold_mean_2023": folds[2023].get("hold_mean"),
                                 "intercept_only_trades": int(len(res["intercept_only"]["trades"])), "per_year_policy": Lr.per_year(pol), "eras_policy": Lr.eras(pol)}
        X_small = {k: X[k] for k in ("sess_i", "exit_bar", "gross", "fees", "hold", "end_data")}
        np.savez_compressed(OUT / f"index_{sym}.npz", **{k: v for k, v in X_small.items()})
        tr.to_csv(OUT / f"index_{sym}_policy_trades.csv", index=False)
    rows = {k: Lr.daily_row(v) for k, v in series.items()}
    out["rows"] = rows
    ledger = []
    if write_registry:
        import os
        from india import registry
        os.environ.setdefault("ANANTA_RERUN_REASON", "25 Oct 2026: SP3's INDEX rows, not run on 23 Oct (the spec's index book); same frozen spec and the same frozen bar (union_k 742)")
        reg = registry.register(
            "SP3", family="SP3", title="SP3 positional playbook: situation-dependent entry, exit and holding time (sp3-v1-2026-10-20-frozen): the INDEX rows",
            hypothesis="the situation-aware NIFTY and BANKNIFTY near-month futures shadow books earn more per day than zero and than the same policy without situation features",
            variants=list(rows), note=f"frozen spec sha {R.SPEC_SHA}; dev 2010-2017 reported, validation 2018-2023 SEEN (rule seen_val_only); holdout untouched",
            bar_families=Lr.BAR_FAMILIES, union_k=Lr.UNION_K, holdout_k=Lr.HOLDOUT_K)
        for name, r in rows.items():
            sym = name.split("|")[1]
            dv, vl = r["dev"], r["val"]
            vt = out["per_index"][sym]["trades"]["val"]
            extra = {"exploratory": False, "statistic": "Newey-West t, 5 lags, daily series (bps of one future's notional)", "dev_days": dv["days"], "val_days": vl["days"],
                     "val_trades": vt, "min_trades_ok": vt >= IMIN_VAL_TRADES, "boot_p_le_0_val": vl.get("boot_p_le_0"), "sharpe_ann_val": vl.get("sharpe_ann"),
                     "c_by_year": out["per_index"][sym]["c_by_year"], "book": "shadow, one position, near-month future"}
            ledger.append(registry.record(reg, variant=name, dev=(dv["mean"], dv["t_nw5"], dv["quarters"]), val=(vl["mean"], vl["t_nw5"], vl["quarters"]), extra=extra, expect=1, rule="seen_val_only"))
        registry.mirror_to_catalog()
    out["ledger"] = ledger
    out["seconds"] = round(time.time() - t0, 1)
    R._write("sp3_index.json", out)
    for name, r in rows.items():
        v = next((l["verdict"] for l in ledger if l["variant"] == name), "not recorded")
        log(f"  {name}: dev {r['dev']['mean']*1e4:+.2f} bp t {r['dev']['t_nw5']:+.2f} | val {r['val']['mean']*1e4:+.2f} bp t {r['val']['t_nw5']:+.2f} -> {v}")
    return out


# ============================================================================================================================ stock parts
def real_fit(log=print) -> dict:
    """The real stock fit (as sp3learn.run makes it), cached: per fold the lambdas per (family, action), c per K row and the decisions."""
    p = OUT / "real_folds.pkl"
    if p.exists():
        return pickle.loads(p.read_bytes())
    d = Lr.Data()
    folds = {}
    for y in YEARS:
        fo = Lr.learn_fold(d, y, log=log)
        folds[y] = {"c": fo["c"], "lambdas": {k: m["lambda"] for k, m in fo["models"].items()}, "decisions": fo["decisions"], "cutoff": fo["cutoff"],
                    "hold_mean": fo["hold_mean"], "skipped": [s["family"] for s in fo["skipped"]]}
    p.write_bytes(pickle.dumps(folds))
    return folds


def _book_series(d: Lr.Data, dec: pd.DataFrame, K: int = 5, inr: float = 60_000.0, s0: int | None = None, s1: int | None = None, **kw) -> dict:
    s0 = d.first_of_year[2010] if s0 is None else s0
    s1 = d.last_of_year[2023] if s1 is None else s1
    rows = dec["cand_id"].to_numpy(); act = dec["action"].to_numpy(); sc = dec["score"].to_numpy()
    res = Lr.Book(d, K, inr, **kw).run(s0, s1, Lr.fn_from_days(Lr.policy_days(d, rows, act, sc)), keep_trades=False)
    return {"daily": res["daily"].set_index("date")["ret"], "counters": res["counters"]}


def _summ(series: pd.Series) -> dict:
    out = {}
    for per, years in (("dev", DEV_YEARS), ("val", VAL_YEARS)):
        x = series[series.index.year.isin(years)]
        out[per] = {"mean": float(x.mean()) if len(x) else float("nan"), "t_nw5": Lr.nw_t(x.to_numpy()) if len(x) else float("nan"), "days": int(len(x))}
    return out


def _real_series() -> dict:
    b = pd.read_parquet(G / "SP3_book_daily.parquet")
    b["date"] = pd.to_datetime(b["date"])
    return {k: g.set_index("date")["ret"] for k, g in b.groupby("book")}


# ---- nulls: lambda and c fixed at the real fit's values; one ridge per (family, action) with the purged leave-one-year-out residual SE
def _fit_fixed(X: np.ndarray, Y: np.ndarray, lams: np.ndarray, years: np.ndarray, sess_i: np.ndarray, fy: dict, ly: dict) -> list[dict]:
    """fit_family_action at a fixed lambda per column of Y (same rows for every column): the same winsorising and add-back, the same purged
    leave-one-year-out residuals and sandwich; the year systems are shared across the actions (one X'X per held-out year)."""
    X = X.astype(np.float64)
    lo, hi = np.percentile(Y, [1, 99], axis=0)
    Yw = np.clip(Y, lo, hi)
    delta = (Y - Yw).mean(axis=0)
    p = X.shape[1]
    oof = np.full(Y.shape, np.nan)
    for t in np.unique(years):
        out = years == t
        f_t, l_t = fy[int(t)], ly[int(t)]
        fit = ~(out | ((sess_i >= f_t - GAP) & (sess_i < f_t)) | ((sess_i > l_t) & (sess_i <= l_t + GAP)))
        if fit.sum() < 30:
            continue
        Xf = X[fit]
        XtX, XtY = Xf.T @ Xf, Xf.T @ Yw[fit]
        for a in range(Y.shape[1]):
            P = np.eye(p) * lams[a]; P[0, 0] = 0.0
            oof[out, a] = X[out] @ np.linalg.solve(XtX + P, XtY[:, a])
    XtX, XtY = X.T @ X, X.T @ Yw
    res = []
    for a in range(Y.shape[1]):
        P = np.eye(p) * lams[a]; P[0, 0] = 0.0
        beta = np.linalg.solve(XtX + P, XtY[:, a])
        e = Yw[:, a] - oof[:, a]
        e = np.where(np.isnan(e), Yw[:, a] - X @ beta, e)
        Ainv = np.linalg.inv(XtX + P)
        V = Ainv @ (X.T @ (X * (e ** 2)[:, None])) @ Ainv
        b = beta.copy(); b[0] += delta[a]
        res.append({"beta": b, "V": V})
    return res


def _permuted_features(d: Lr.Data, seed: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """tests.nulls: market-feature rows permuted across dates in month blocks (each session takes the row at the same position of another month,
    the last row when that month is shorter); stock-feature vectors permuted within family and signal month."""
    rng = np.random.default_rng(seed)
    mk = d.market.copy()
    mk["date"] = pd.to_datetime(mk["date"])
    mk = mk.set_index("date").sort_index()
    months = mk.index.to_period("M")
    groups = {m: np.flatnonzero(months == m) for m in months.unique()}
    keys = list(groups)
    perm = rng.permutation(len(keys))
    src = np.empty(len(mk), int)
    for m, pk in zip(keys, perm):
        tgt, s = groups[m], groups[keys[pk]]
        src[tgt] = s[np.minimum(np.arange(len(tgt)), len(s) - 1)]
    mcols = R.MARKET_CAT + R.MARKET_NUM
    mk_null = mk.copy()
    mk_null[mcols] = mk[mcols].to_numpy()[src]
    f = d.feat.copy()
    sig = pd.to_datetime(d.cand["signal_date"])
    mrow = mk_null.reindex(sig)
    for c in mcols:
        v = mrow[c].to_numpy()
        f[c] = np.where(pd.isna(v), "missing", v) if c in R.MARKET_CAT else v.astype(float)
    scols = R.STOCK_CAT + R.STOCK_NUM
    key = pd.Series(d.fam).astype(str) + "|" + sig.dt.to_period("M").astype(str).to_numpy()
    order = np.arange(d.N)
    for _, idx in pd.Series(order).groupby(key.to_numpy()):
        ix = idx.to_numpy()
        if len(ix) > 1:
            order[ix] = ix[rng.permutation(len(ix))]
    f[scols] = d.feat[scols].to_numpy()[order]
    return f, mk_null.reset_index()


def null_draw(d: Lr.Data, real: dict, seed: int | None) -> dict:
    """One state-shuffle draw (seed None = the real features: a parity check that this fitter reproduces the real decisions)."""
    feat0, mk0 = d.feat, d.market
    if seed is not None:
        d.feat, d.market = _permuted_features(d, seed)
    try:
        decs = []
        fy, ly = d.first_of_year, d.last_of_year
        for y in YEARS:
            train, test, _ = Lr.fold_masks(d, y)
            Xd, _ = Lr.design(d, train)
            lab = Lr.labels(d, y)
            rf = real[y]
            pred = np.full((d.N, Lr.NA), np.nan); se = pred.copy()
            hm = rf["hold_mean"]
            for fam in sorted(set(d.fam[train])):
                if fam not in hm:
                    continue
                tr = np.flatnonzero(train & (d.fam == fam)); te = np.flatnonzero(test & (d.fam == fam))
                if not len(te):
                    continue
                goods = {}
                for a in range(Lr.NA):
                    g = np.isfinite(lab[tr, a])
                    goods.setdefault(g.tobytes(), (g, []))[1].append(a)
                for g, acts in goods.values():
                    rows = tr[g]
                    lams = np.array([rf["lambdas"][(fam, a)] for a in acts], float)
                    fits = _fit_fixed(Xd[rows], lab[rows][:, acts], lams, d.year[rows], d.sess_i[rows], fy, ly)
                    for a, m in zip(acts, fits):
                        pred[te, a], se[te, a] = Lr.predict(m, Xd[te])
            te_rows = np.flatnonzero(test)
            fee = d.fee_frac(12_000.0, d.cand["signal_date"].to_numpy()[test])
            hmte = np.array([hm.get(f_, np.full(Lr.NA, np.nan)) for f_ in d.fam[te_rows]])
            pn = pred[te_rows] - fee[:, None]
            c = rf["c"]["K5"]
            sm = np.where(np.isfinite(pn) & (pn > c * se[te_rows]) & (pn > 0), pn / hmte, -np.inf)
            act = np.where(np.isfinite(sm.max(axis=1)), sm.argmax(axis=1), -1)
            decs.append(pd.DataFrame({"cand_id": te_rows, "action": act, "score": np.where(act >= 0, sm.max(axis=1), np.nan), "year": y}))
        dec = pd.concat(decs, ignore_index=True)
        b = _book_series(d, dec)
        s = _summ(b["daily"])
        return {"seed": seed, "dev_mean": s["dev"]["mean"], "val_mean": s["val"]["mean"], "val_t": s["val"]["t_nw5"], "dev_t": s["dev"]["t_nw5"],
                "entries": b["counters"]["entries"], "qualify_share": float((dec["action"] >= 0).mean()),
                "qualify_share_val": float((dec.loc[dec["year"] >= 2018, "action"] >= 0).mean()),
                "same_as_real_decisions": None if seed is not None else _same(dec, real)}
    finally:
        d.feat, d.market = feat0, mk0


def _same(dec: pd.DataFrame, real: dict) -> float:
    r = pd.concat([real[y]["decisions"]["K5"] for y in YEARS], ignore_index=True)
    m = dec.merge(r[["cand_id", "action"]], on="cand_id", suffixes=("", "_real"))
    return float((m["action"] == m["action_real"]).mean())


def run_nulls(first: int, last: int, log=print) -> None:
    R._check_spec()
    real = real_fit(log)
    d = Lr.Data()
    nd = OUT / "nulls"
    nd.mkdir(parents=True, exist_ok=True)
    seeds = [None] if first == 0 else list(range(first, last + 1))
    for seed in seeds:
        f = nd / f"seed_{seed if seed is not None else 'real'}.json"
        if f.exists():
            continue
        t0 = time.time()
        r = null_draw(d, real, seed)
        r["seconds"] = round(time.time() - t0, 1)
        _jdump(f, r)
        log(f"  null seed {seed}: val {r['val_mean']*1e4:+.2f} bp t {r['val_t']:+.2f} entries {r['entries']} qualify {r['qualify_share']:.3f}  {r['seconds']}s")


# ---- ablations
def run_ablation(group: str, log=print) -> dict:
    R._check_spec()
    if group not in R.GROUPS:
        raise SystemExit(f"unknown group {group}; groups: {list(R.GROUPS)}")
    d = Lr.Data()
    t0 = time.time()
    decs = []
    for y in YEARS:
        fo = Lr.learn_fold(d, y, drop_group=group, log=lambda m: log(f"[{group}] " + m.strip()))
        decs.append(fo["decisions"]["K5"].assign(c=fo["c"]["K5"]))
    dec = pd.concat(decs, ignore_index=True)
    b = _book_series(d, dec)
    real = _real_series()["policy"]
    out = {"group": group, "features_dropped": R.GROUPS[group], "policy": _summ(b["daily"]), "real_minus_ablated": _summ(real - b["daily"].reindex(real.index).fillna(0.0)),
           "entries": b["counters"]["entries"], "c_by_year": dict(zip(YEARS, [float(x) for x in dec.groupby("year")["c"].first()])), "seconds": round(time.time() - t0, 1)}
    _jdump(OUT / "ablations" / f"{group}.json", out)
    log(f"  ablation {group}: val {out['policy']['val']['mean']*1e4:+.2f} bp (t {out['policy']['val']['t_nw5']:+.2f}); real minus ablated val "
        f"{out['real_minus_ablated']['val']['mean']*1e4:+.2f} bp (t {out['real_minus_ablated']['val']['t_nw5']:+.2f})")
    return out


# ---- 12 start months
def run_months(log=print) -> dict:
    R._check_spec()
    real = real_fit(log)
    d = Lr.Data()
    dec = pd.concat([real[y]["decisions"]["K5"] for y in YEARS], ignore_index=True)
    out = {"from_2010": {}, "from_2018": {}}
    for start_year, key in ((2010, "from_2010"), (2018, "from_2018")):
        for m in range(1, 13):
            s0 = int(d.sess.searchsorted(pd.Timestamp(f"{start_year}-{m:02d}-01")))
            b = _book_series(d, dec, s0=s0)
            s = _summ(b["daily"])
            out[key][f"{start_year}-{m:02d}"] = {"dev": s["dev"] if start_year == 2010 else None, "val": s["val"], "entries": b["counters"]["entries"],
                                               "breaches": b["counters"]["breaches"]}
            log(f"  start {start_year}-{m:02d}: val {s['val']['mean']*1e4:+.2f} bp t {s['val']['t_nw5']:+.2f}")
    vals = [v["val"]["mean"] for v in out["from_2018"].values()]
    out["summary_from_2018"] = {"val_mean_min": min(vals), "val_mean_max": max(vals), "positive_starts": int(sum(v > 0 for v in vals))}
    vals10 = [v["val"]["mean"] for v in out["from_2010"].values()]
    out["summary_from_2010"] = {"val_mean_min": min(vals10), "val_mean_max": max(vals10), "positive_starts": int(sum(v > 0 for v in vals10))}
    _jdump(OUT / "months.json", out)
    return out


# ---- reverse family priority
def reverse_priority_flags(d: Lr.Data) -> np.ndarray:
    """stage_1 priority in the reverse order of the real families (LO52 first ... RETEST last); ANY still only where no real family fired; CTL
    outside the order. Spacing was applied before priority, so the candidate rows are the same; only the priority flags change."""
    real_order = [f for f in R.prep.PRIORITY if f != "ANY"]
    order = list(reversed(real_order)) + ["ANY"]
    pr = {f: k for k, f in enumerate(order)}
    c = d.cand[["sid", "signal_date", "family"]].copy()
    c["_p"] = c["family"].map(pr)
    c = c[c["family"] != "CTL"]
    best = c.sort_values(["sid", "signal_date", "_p"], kind="mergesort").drop_duplicates(["sid", "signal_date"])
    flags = np.zeros(d.N, bool)
    flags[best.index.to_numpy()] = True
    return flags


def run_reverse(log=print) -> dict:
    R._check_spec()
    t0 = time.time()
    d = Lr.Data()
    old = d.prio.copy()
    d.prio = reverse_priority_flags(d)
    changed = int((old != d.prio).sum())
    log(f"  reverse priority: {changed} priority flags change ({int(d.prio.sum())} priority rows)")
    # the baseline's fixed action per fold, on reverse-priority long books (not cached over the real ones)
    f = OUT / "baseline_long_reverse.npy"
    if f.exists():
        long = np.load(f)
    else:
        pool = Lr.baseline_pool(d)
        s0, s1 = d.first_of_year[2005], d.last_of_year[2023]
        long = np.zeros((Lr.NA, len(Lr.BASELINE_SEEDS), s1 - s0 + 1), np.float32)
        for a in range(Lr.NA):
            for j, seed in enumerate(Lr.BASELINE_SEEDS):
                long[a, j] = Lr.Book(d, 5, 60_000.0).run(s0, s1, Lr.baseline_fn(d, pool, seed, lambda y, a=a: a), keep_trades=False)["daily"]["ret"].to_numpy()
            log(f"  reverse long books: {Lr.A[a]} done {time.time() - t0:.0f}s")
        np.save(f, long)
    decs, decs0, fixed = [], [], {}
    for y in YEARS:
        fo = Lr.learn_fold(d, y, log=lambda m: log("[reverse] " + m.strip()))
        fo0 = Lr.learn_fold(d, y, intercept_only=True, log=lambda m: log("[reverse io] " + m.strip()))
        decs.append(fo["decisions"]["K5"]); decs0.append(fo0["decisions"]["K5"])
        fixed[y] = Lr.fixed_action_for(d, long, fo["cutoff"])[0]
    dec, dec0 = pd.concat(decs, ignore_index=True), pd.concat(decs0, ignore_index=True)
    pol = _book_series(d, dec)["daily"]
    io = _book_series(d, dec0)["daily"]
    pool = Lr.baseline_pool(d)
    s0, s1 = d.first_of_year[2010], d.last_of_year[2023]
    base = pd.concat([Lr.Book(d, 5, 60_000.0).run(s0, s1, Lr.baseline_fn(d, pool, seed, lambda y: fixed[y]), keep_trades=False)["daily"].set_index("date")["ret"]
                      for seed in Lr.BASELINE_SEEDS], axis=1).mean(axis=1)
    out = {"priority_flags_changed": changed, "policy": _summ(pol), "vs_baseline": _summ(pol - base), "vs_intercept_only": _summ(pol - io), "baseline": _summ(base),
           "fixed_action_by_year": {y: Lr.A[fixed[y]] for y in YEARS}, "seconds": round(time.time() - t0, 1)}
    _jdump(OUT / "reverse.json", out)
    log(f"  reverse: policy val {out['policy']['val']['mean']*1e4:+.2f} bp t {out['policy']['val']['t_nw5']:+.2f}; vs baseline val {out['vs_baseline']['val']['mean']*1e4:+.2f} bp t {out['vs_baseline']['val']['t_nw5']:+.2f}")
    return out


# ---- filters as findings
def run_filters(log=print) -> dict:
    """Each named condition (india/conditions.py) as on/off slices of the unfiltered baseline population (every real-family priority candidate
    with an outcome, the population the baseline book draws from), per family and action: mean net return per trade (GROSS minus the dated
    round-trip fees of a Rs 12,000 slot), dev and validation. Descriptive: a filter is never hand-added to the policy."""
    from india import conditions
    R._check_spec()
    t0 = time.time()
    d = Lr.Data()
    pool = Lr.baseline_pool(d)
    pool = pool[(d.year[pool] >= 2010) & (d.year[pool] <= 2023)]
    fc = ["sid", "date", "liq_rank", "ret_20", "ret_60", "dist_sma20", "dist_sma50", "dist_sma200", "vol_ratio20", "deliv_pct", "rv20"]
    feat = pd.read_parquet(paths.gold() / "features" / "daily.parquet", columns=fc)
    feat["date"] = pd.to_datetime(feat["date"])
    feat = feat[feat["date"] <= E_END]
    ctx = conditions.apply_market(conditions.context_table(feat[["date", "liq_rank", "dist_sma200"]]))
    liq = feat[feat["liq_rank"] <= 500].copy()
    stock = pd.concat([liq[["sid", "date"]], conditions.apply_stock(liq)], axis=1)
    c = pd.DataFrame({"k": pool, "sid": d.sid[pool], "date": pd.to_datetime(d.cand["signal_date"].to_numpy()[pool]), "family": d.fam[pool], "year": d.year[pool]})
    c = c.merge(stock, on=["sid", "date"], how="left").merge(ctx, left_on="date", right_index=True, how="left")
    fee = d.fee_frac(12_000.0, c["date"].to_numpy())
    net = d.gross[c["k"].to_numpy(), :Lr.NA] - fee[:, None]
    conds = [x for x in c.columns if x.startswith("cond_")]
    per = np.where(c["year"] < 2018, "dev", "val")
    fams = sorted(c["family"].unique())
    fcode = c["family"].map({f_: i for i, f_ in enumerate(fams)}).to_numpy()
    gid = fcode * 2 + (per == "val").astype(int)
    ng = len(fams) * 2
    fin = np.isfinite(net)
    net0 = np.where(fin, net, 0.0)
    recs = []
    for cond in conds:
        on = c[cond].to_numpy()
        S, Nn = {}, {}
        for state in (1.0, 0.0):
            m = on == state
            s_ = np.zeros((ng, Lr.NA)); n_ = np.zeros((ng, Lr.NA))
            np.add.at(s_, gid[m], net0[m]); np.add.at(n_, gid[m], fin[m])
            S[state], Nn[state] = s_, n_
        for fi, fam in enumerate(fams):
            for pi, p_ in enumerate(("dev", "val")):
                g = fi * 2 + pi
                for a in range(Lr.NA):
                    n1, n0 = Nn[1.0][g, a], Nn[0.0][g, a]
                    recs.append({"condition": cond[5:], "family": fam, "action": Lr.A[a], "period": p_, "n_on": int(n1), "n_off": int(n0),
                                 "mean_on": S[1.0][g, a] / n1 if n1 else np.nan, "mean_off": S[0.0][g, a] / n0 if n0 else np.nan})
    t = pd.DataFrame(recs)
    t["diff"] = t["mean_on"] - t["mean_off"]
    t.to_parquet(G / "SP3_filter_slices.parquet", index=False)
    # the compact view: pooled over families, the baseline's most-used fixed action (hold_60d_nostop) and hold_20d
    pooled = []
    for cond in conds:
        on = c[cond].to_numpy()
        for act in ("hold_60d_nostop", "hold_20d"):
            a = Lr.A.index(act)
            row = {"condition": cond[5:], "action": act, "expect": conditions.ALL[cond[5:]][2], "what": conditions.ALL[cond[5:]][1]}
            for p_ in ("dev", "val"):
                m = (per == p_) & np.isfinite(net[:, a])
                x_on, x_off = net[m & (on == 1), a], net[m & (on == 0), a]
                row[f"{p_}_n_on"], row[f"{p_}_n_off"] = int(len(x_on)), int(len(x_off))
                row[f"{p_}_diff"] = float(x_on.mean() - x_off.mean()) if len(x_on) and len(x_off) else np.nan
            row["same_sign"] = bool(np.sign(row["dev_diff"]) == np.sign(row["val_diff"])) if row["dev_diff"] == row["dev_diff"] and row["val_diff"] == row["val_diff"] else None
            pooled.append(row)
    agree = t[(t["n_on"] >= 200) & (t["n_off"] >= 200)].pivot_table(index=["condition", "family", "action"], columns="period", values="diff")
    agree = agree.dropna()
    agree = agree[np.sign(agree["dev"]) == np.sign(agree["val"])]
    out = {"population": "real-family priority candidates 2010-2023 with outcomes (the baseline book's pool)", "candidates": int(len(c)), "conditions": [x[5:] for x in conds],
           "pooled": pooled, "cells": int(len(t)), "cells_with_200_each_side_same_sign_dev_val": int(len(agree)),
           "largest_same_sign_cells": [{"condition": i[0], "family": i[1], "action": i[2], "dev_diff": round(float(r["dev"]), 5), "val_diff": round(float(r["val"]), 5)}
                                       for i, r in agree.reindex(agree["val"].abs().sort_values(ascending=False).index).head(15).iterrows()],
           "file": str(G / "SP3_filter_slices.parquet"), "seconds": round(time.time() - t0, 1)}
    _jdump(OUT / "filters.json", out)
    log(f"  filters: {len(conds)} conditions, {len(t)} cells, {len(agree)} cells with dev and validation the same sign (n>=200 each side)")
    return out


# ============================================================================================================================ report
def report(log=print) -> dict:
    o = {"at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    real = _real_series()["policy"]
    rs = _summ(real)
    o["real_policy"] = rs
    p = paths.manifest_dir() / "sp3_index.json"
    o["index"] = json.loads(p.read_text()) if p.exists() else None
    nd = OUT / "nulls"
    nulls = [json.loads(f.read_text()) for f in sorted(nd.glob("seed_*.json"))] if nd.exists() else []
    parity = next((x for x in nulls if x["seed"] is None), None)
    draws = [x for x in nulls if x["seed"] is not None]
    if draws:
        v = np.array([x["val_mean"] for x in draws]); dv = np.array([x["dev_mean"] for x in draws])
        o["nulls"] = {"draws": len(draws), "seeds": f"{min(x['seed'] for x in draws)}-{max(x['seed'] for x in draws)}",
                      "share_val_at_or_above_real": float((v >= rs["val"]["mean"]).mean()), "share_dev_at_or_above_real": float((dv >= rs["dev"]["mean"]).mean()),
                      "null_val_mean_median": float(np.median(v)), "null_val_mean_p5": float(np.quantile(v, 0.05)), "null_val_mean_p95": float(np.quantile(v, 0.95)),
                      "null_entries_median": float(np.median([x["entries"] for x in draws])), "null_qualify_share_median": float(np.median([x["qualify_share"] for x in draws])),
                      "parity_real_features": parity}
    ab = [json.loads(f.read_text()) for f in sorted((OUT / "ablations").glob("*.json"))] if (OUT / "ablations").exists() else []
    o["ablations"] = ab
    for name in ("months", "reverse", "filters"):
        f = OUT / f"{name}.json"
        o[name] = json.loads(f.read_text()) if f.exists() else None
    R._write("sp3_extra.json", o)
    _write_section(o)
    return o


def _bp(x):
    return f"{x*1e4:+.2f} bp" if x == x and x is not None else "n/a"


def _write_section(o: dict) -> Path:
    L = ["## Remaining parts (run 25 Oct 2026, `python -m india.sp3extra`)", "",
         "Same frozen spec, same dev 2010-2017 and validation 2018-2023 (SEEN); nothing here changes the frozen policy. Numbers are daily book returns "
         "(Newey-West t, 5 lags) unless said otherwise.", ""]
    ix = o.get("index")
    if ix:
        L += ["### INDEX rows (near-month futures shadow book, bps of one future's notional, rule seen_val_only, the frozen union bar z 3.985)", "",
              "| row | dev mean/day | dev t | val mean/day | val t | val Sharpe | verdict |", "|---|---|---|---|---|---|---|"]
        verdict = {l["variant"]: l["verdict"] for l in ix.get("ledger", [])}
        for name, r in ix["rows"].items():
            L.append(f"| {name} | {_bp(r['dev']['mean'])} | {r['dev']['t_nw5']:+.2f} | {_bp(r['val']['mean'])} | {r['val']['t_nw5']:+.2f} | {r['val'].get('sharpe_ann', float('nan')):+.2f} | {verdict.get(name, 'not recorded')} |")
        for sym, p in ix["per_index"].items():
            L.append(f"- {sym}: trades dev {p['trades']['dev']}, validation {p['trades']['val']} (minimum {p['trades']['min_val_trades']}); net per closed trade "
                     f"{_bp(p['net_per_trade_mean']) if p['net_per_trade_mean'] is not None else 'n/a'}, win rate {p['win_rate'] if p['win_rate'] is None else round(p['win_rate'], 3)}; "
                     f"actions taken {p['actions_taken']}; c by year {p['c_by_year']}; data handling {p['info']['counts']}")
        L += ["- Exit decisions use the index's own closes (and its 20-session lows/highs); fills and marks use the future, rolled at the close two sessions "
              "before expiry with both legs' dated fees and a tick each; the index is not re-entered at the open where its position left; the shadow book has no survival lines.", ""]
    n = o.get("nulls")
    if n:
        par = n.get("parity_real_features") or {}
        L += ["### State-shuffle nulls (tests.nulls; descriptive, cannot reach the bar)", "",
              f"- {n['draws']} draws (seeds {n['seeds']}): market rows permuted across dates in month blocks, stock-feature vectors permuted within family and month, "
              "models refitted with lambda and c fixed at the real fit's values, policy and K=5 book rerun.",
              f"- share of null books at or above the real one: validation {n['share_val_at_or_above_real']:.3f}, dev {n['share_dev_at_or_above_real']:.3f} "
              f"(real validation {_bp(o['real_policy']['val']['mean'])}; null median {_bp(n['null_val_mean_median'])}, 5-95% {_bp(n['null_val_mean_p5'])} .. {_bp(n['null_val_mean_p95'])})",
              f"- how often the null trades: median {n['null_entries_median']:.0f} book entries; median share of candidates with a qualifying action {n['null_qualify_share_median']:.3f}",
              f"- parity check (this fitter on the real features): {par.get('same_as_real_decisions')} of the decisions equal the real run's; validation {_bp(par.get('val_mean', float('nan')))}", ""]
    if o.get("ablations"):
        L += ["### Drop-one feature-group ablations (full refit without the group)", "",
              "The real K=5 policy book made 953 entries over 2010-2023. An ablated book that trades far more pays far more in costs, so a large 'real minus "
              "ablated' says the group kept the policy out of costly trades, not that it found winners. Descriptive only.", "",
              "| group dropped | val mean/day (t) | real minus ablated, val (t) | dev mean/day (t) | book entries |", "|---|---|---|---|---|"]
        for a in o["ablations"]:
            L.append(f"| {a['group']} ({', '.join(a['features_dropped'])}) | {_bp(a['policy']['val']['mean'])} ({a['policy']['val']['t_nw5']:+.2f}) | "
                     f"{_bp(a['real_minus_ablated']['val']['mean'])} ({a['real_minus_ablated']['val']['t_nw5']:+.2f}) | {_bp(a['policy']['dev']['mean'])} ({a['policy']['dev']['t_nw5']:+.2f}) | {a['entries']} |")
        L.append("")
    m = o.get("months")
    if m:
        s18, s10 = m["summary_from_2018"], m["summary_from_2010"]
        L += ["### The book started in 12 different months", "",
              f"- started in each month of 2010: validation mean from {_bp(s10['val_mean_min'])} to {_bp(s10['val_mean_max'])}; positive in {s10['positive_starts']} of 12",
              f"- started in each month of 2018 (validation only): from {_bp(s18['val_mean_min'])} to {_bp(s18['val_mean_max'])}; positive in {s18['positive_starts']} of 12", ""]
    r = o.get("reverse")
    if r:
        L += ["### Reverse family priority", "",
              f"- {r['priority_flags_changed']} priority flags change; policy validation {_bp(r['policy']['val']['mean'])} (t {r['policy']['val']['t_nw5']:+.2f}); "
              f"vs baseline {_bp(r['vs_baseline']['val']['mean'])} (t {r['vs_baseline']['val']['t_nw5']:+.2f}); vs intercept-only {_bp(r['vs_intercept_only']['val']['mean'])} "
              f"(t {r['vs_intercept_only']['val']['t_nw5']:+.2f}); dev policy {_bp(r['policy']['dev']['mean'])} (t {r['policy']['dev']['t_nw5']:+.2f})", ""]
    fl = o.get("filters")
    if fl:
        L += ["### Filters as findings (on/off slices of the baseline population; descriptive)", "",
              f"Population: {fl['population']} ({fl['candidates']} candidates); net = GROSS minus a Rs 12,000 slot's dated round-trip fees; full table "
              f"`gold/studies/SP3_filter_slices.parquet` ({fl['cells']} cells; {fl['cells_with_200_each_side_same_sign_dev_val']} with at least 200 trades on each side and "
              "the same sign in dev and validation).", "",
              "Differences are per trade (net return of a trade with the condition on minus off, in bp of the slot), pooled over families.", "",
              "| condition | action | dev on-off (n on/off) | val on-off (n on/off) | same sign |", "|---|---|---|---|---|"]
        for p in fl["pooled"]:
            L.append(f"| {p['condition']} | {p['action']} | {_bp(p['dev_diff'])} ({p['dev_n_on']}/{p['dev_n_off']}) | {_bp(p['val_diff'])} ({p['val_n_on']}/{p['val_n_off']}) | {p['same_sign']} |")
        L.append("")
    done = {"INDEX rows (NIFTY, BANKNIFTY futures book)": bool(ix), "state-shuffle nulls (200 draws)": bool(n and n["draws"] >= 200),
            "drop-one feature-group ablations": len(o.get("ablations") or []) == len(R.GROUPS), "12 start months": bool(m), "reverse family priority": bool(r),
            "filters-as-findings slices": bool(fl)}
    still = [k for k, v in done.items() if not v]
    L += ["### Still not run", ""] + ([f"- {k}" for k in still] or ["- none: every part the spec listed is in"]) + [""]
    p = R.HERE / "registrations" / "sp3_results.md"
    txt = p.read_text()
    head = txt.split("## Remaining parts (run 25 Oct 2026")[0].rstrip("\n")
    if "## Not run in this session" in head and not still:
        head = head.replace("## Not run in this session", "## Not run in the 23 Oct session (all run on 25 Oct: see Remaining parts below)")
    p.write_text(head + "\n\n" + "\n".join(L))
    return p


if __name__ == "__main__":
    paths.ensure()
    a = sys.argv[1:]
    cmd = a[0] if a else ""
    if cmd == "index":
        run_index(write_registry="--no-registry" not in a, log=_log_to("index.log"))
    elif cmd == "real":
        real_fit(_log_to("real.log"))
    elif cmd == "nulls":
        run_nulls(int(a[1]), int(a[2]), log=_log_to(f"nulls_{a[1]}_{a[2]}.log"))
    elif cmd == "ablation":
        run_ablation(a[1], log=_log_to(f"ablation_{a[1]}.log"))
    elif cmd == "months":
        run_months(_log_to("months.log"))
    elif cmd == "reverse":
        run_reverse(_log_to("reverse.log"))
    elif cmd == "filters":
        run_filters(_log_to("filters.log"))
    elif cmd == "report":
        report(_log_to("report.log"))
    else:
        print(__doc__)
