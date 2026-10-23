"""SP3 stages 4-6 on dev (2010-2017) and validation (2018-2023): walk-forward situation models, the policy, the books and their
comparisons, the test rows into the registry, the results document. Reads only the stage 2-3 outputs of india/sp3run.py (every row dated
2023-12-29 or earlier). The holdout is never opened here.

  python -m india.sp3learn run                 the full stock run (models, policy, books, tests, registry rows, results doc)
  python -m india.sp3learn run --no-registry   the same without writing to the test ledger (a rehearsal)
  python -m india.sp3learn baseline            only the 25 actions x 20 seeds unfiltered baseline books (cached for the run)

Models (stage_4_learning): per (family, action), ridge of GROSS return on one-hot situation features, intercept unpenalised, target winsorised
at the training 1st/99th percentiles with the clipped mean added back; lambda by purged leave-one-year-out (62-session purge before and
embargo after the held-out year) from {1, 3, 10, 30, 100, 300, 1000}; the prediction's standard error from the sandwich with the out-of-fold
residuals. Expanding walk-forward: test year y in 2010..2023, training = candidates signalled at least 62 sessions before y's first session,
from 2005. c (the qualifying margin, predicted net > c x SE) from {0.5, 1, 1.5, 2, 2.5, 3, 4, 6, 10} by the same leave-one-year-out folds:
the out-of-fold predictions run a one-year book on each held-out training year and the c with the best mean daily book return wins (ties to
the larger c), separately for each K / capital row. Score = predicted net / the training mean hold of that (family, action).
"""
from __future__ import annotations

import datetime as dt
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from india import costs, paths
from india import sp3run as R

G = paths.gold() / "studies"
YEARS = list(range(2010, 2024))
DEV_YEARS, VAL_YEARS = list(range(2010, 2018)), list(range(2018, 2024))
LAMBDAS = (1, 3, 10, 30, 100, 300, 1000)
C_GRID = (0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 6.0, 10.0)
K_ROWS = {"K5": (5, 60_000.0), "K10": (10, 200_000.0), "K20": (20, 1_000_000.0)}
MIN_TRAIN, MIN_TRAIN_YEARS = 300, 3
GAP = R.STOP_GAP                       # 62 market sessions
BASELINE_SEEDS = list(range(101, 121))
SURV_DAY, SURV_DD = 0.05, 0.22
NW_LAGS, BOOT_DRAWS, BOOT_BLOCK, BOOT_SEED = 5, 2000, 20, 17
MIN_VAL_TRADES = 200
A = R.ACTION_NAMES                     # the 25 choosable actions in the spec's order
REAL_FAMS = [f for f in R.prep.REAL if f not in R.prep.NEEDS_RESULTS]


# ============================================================================================================================ data
class Data:
    """Everything the learner needs, as arrays indexed by cand_id."""

    def __init__(self):
        t0 = time.time()
        self.cand = pd.read_parquet(G / "SP3_candidates.parquet").sort_values("cand_id").reset_index(drop=True)
        assert (self.cand["cand_id"].to_numpy() == np.arange(len(self.cand))).all()
        self.N = len(self.cand)
        self.feat = pd.read_parquet(G / "SP3_features.parquet").sort_values("cand_id").reset_index(drop=True)
        self.market = pd.read_parquet(G / "SP3_market.parquet")
        self.sess = R.sessions()
        self.sess_days = self.sess.to_numpy().astype("datetime64[D]")
        w = np.load(G / "SP3_windows.npz")
        self.O, self.C, self.S, self.n_valid = w["O"], w["C"], w["S"], w["n_valid"]
        out = pd.read_parquet(G / "SP3_outcomes.parquet", columns=["cand_id", "action", "exit_bar", "exit_px", "reason", "gross", "gross_alt", "gross_prehalt", "exit_date", "hold"])
        acts = A + [f"random_exit_{j}" for j in range(R.RANDOM_DRAWS)]
        ai = {a: i for i, a in enumerate(acts)}
        self.actions = acts
        na = len(acts)
        shape = (self.N, na)
        self.gross = np.full(shape, np.nan, np.float32); self.gross_alt = self.gross.copy(); self.gross_prehalt = self.gross.copy()
        self.exit_bar = np.full(shape, -1, np.int16); self.exit_px = np.full(shape, np.nan, np.float32); self.hold = np.full(shape, 0, np.int16)
        self.exit_fee = np.ones(shape, bool); self.exit_s = np.full(shape, -1, np.int32)
        ci, aidx = out["cand_id"].to_numpy(), out["action"].map(ai).to_numpy()
        self.gross[ci, aidx] = out["gross"]; self.gross_alt[ci, aidx] = out["gross_alt"]; self.gross_prehalt[ci, aidx] = out["gross_prehalt"]
        self.exit_bar[ci, aidx] = out["exit_bar"]; self.exit_px[ci, aidx] = out["exit_px"]; self.hold[ci, aidx] = out["hold"]
        self.exit_fee[ci, aidx] = ~out["reason"].isin(R.NO_EXIT_FEE_REASONS).to_numpy()
        self.exit_s[ci, aidx] = np.searchsorted(self.sess_days, out["exit_date"].to_numpy().astype("datetime64[D]"))
        self.reason_end_failed = np.zeros(shape, bool)
        self.reason_end_failed[ci, aidx] = (out["reason"] == "end_failed").to_numpy()
        del out
        c = self.cand
        self.ok = (c["status"] == "OK").to_numpy()
        self.sess_i = c["sess_i"].to_numpy().astype(int)
        self.year = c["year"].to_numpy().astype(int)
        self.fam = c["family"].to_numpy()
        self.prio = c["priority_family"].to_numpy().astype(bool)
        self.sid = c["sid"].to_numpy()
        self.sid_code = pd.factorize(c["sid"])[0]
        self.entry_s = self.S[:, 0]
        self.entry_o = c["entry_o"].to_numpy(); self.raw_entry_o = c["raw_entry_o"].to_numpy(); self.raw_close_T = c["raw_close_T"].to_numpy()
        self.hs = c["hs"].to_numpy(); self.liq = c["liq_rank"].to_numpy()
        self.h13 = R.prep.hash_many(c["sid"], c["signal_date"], R.prep.CTL_SALT)
        self.h17 = R.prep.hash_many(c["sid"], c["signal_date"], 17)
        self.first_of_year = {y: int(self.sess.searchsorted(pd.Timestamp(f"{y}-01-01"))) for y in range(2005, 2025)}
        self.last_of_year = {y: self.first_of_year[y + 1] - 1 for y in range(2005, 2024)}
        self.seconds = round(time.time() - t0, 1)

    def fee_frac(self, slot: float, dates) -> np.ndarray:
        """Round-trip fees at slot size, both legs on the decision date, as a fraction of the slot (stage_4 predicted_net)."""
        out = np.empty(len(dates))
        cache = {}
        for i, d in enumerate(pd.DatetimeIndex(pd.to_datetime(np.asarray(dates))).date):
            if d not in cache:
                cache[d] = (costs.cost("delivery", "buy", slot, when=d) + costs.cost("delivery", "sell", slot, when=d)) / slot
            out[i] = cache[d]
        return out


# ============================================================================================================================ design
def tercile_cuts(v: np.ndarray) -> tuple:
    x = v[~np.isnan(v)]
    return (float(np.quantile(x, 1 / 3)), float(np.quantile(x, 2 / 3))) if len(x) >= 30 else (np.nan, np.nan)


def tercile_level(v: np.ndarray, cuts: tuple) -> np.ndarray:
    lo, hi = cuts
    return np.where(np.isnan(v) | np.isnan(lo), "missing", np.where(v <= lo, "low", np.where(v <= hi, "mid", "high")))


def design(d: Data, train_mask: np.ndarray, drop_group: str | None = None) -> tuple[np.ndarray, list[str]]:
    """One-hot situation matrix for every candidate with this fold's tercile cuts (fitted on the training rows: market numerics on the training
    sessions, stock numerics on the training candidates). Column 0 is the intercept. drop_group removes one feature group (ablations)."""
    f = d.feat
    cats = {}
    train_sess = np.unique(d.sess_i[train_mask])
    mk = d.market.set_index("date").reindex(d.sess[train_sess])
    for c in R.MARKET_NUM:
        cats[c] = tercile_level(f[c].to_numpy(dtype=float), tercile_cuts(mk[c].to_numpy(dtype=float)))
    for c in R.STOCK_NUM:
        cats[c] = tercile_level(f[c].to_numpy(dtype=float), tercile_cuts(f[c].to_numpy(dtype=float)[train_mask]))
    for c in R.MARKET_CAT + R.STOCK_CAT:
        cats[c] = f[c].to_numpy()
    drop = set(R.GROUPS.get(drop_group, [])) if drop_group else set()
    cols, mats = ["intercept"], [np.ones((d.N, 1), np.float32)]
    for c, v in cats.items():
        if c in drop:
            continue
        levels = sorted(set(v[train_mask]))
        for lv in levels:
            cols.append(f"{c}={lv}")
            mats.append((v == lv).astype(np.float32)[:, None])
    return np.concatenate(mats, axis=1), cols


# ============================================================================================================================ ridge
def _solve(XtX: np.ndarray, Xty: np.ndarray, lam: float) -> np.ndarray:
    p = len(Xty)
    P = np.eye(p) * lam
    P[0, 0] = 0.0
    return np.linalg.solve(XtX + P, Xty)


def fit_family_action(X: np.ndarray, y: np.ndarray, years: np.ndarray, sess_i: np.ndarray, first_of_year: dict, last_of_year: dict) -> dict:
    """Ridge with purged leave-one-year-out lambda and the OOF residual sandwich. X: rows of one (family, action) training set (intercept first);
    y: the GROSS label. Returns beta (with the winsor add-back on the intercept), lambda, V (p x p), oof predictions and SEs per row, hold not included."""
    lo, hi = np.percentile(y, [1, 99])
    yw = np.clip(y, lo, hi)
    delta = float(np.mean(y - yw))
    X = X.astype(np.float64)
    yrs = np.unique(years)
    sse = {lam: 0.0 for lam in LAMBDAS}
    oof = {lam: np.full(len(y), np.nan) for lam in LAMBDAS}
    for t in yrs:
        out = years == t
        f_t, l_t = first_of_year[int(t)], last_of_year[int(t)]
        purge = (sess_i >= f_t - GAP) & (sess_i < f_t)
        embargo = (sess_i > l_t) & (sess_i <= l_t + GAP)
        fit = ~(out | purge | embargo)
        if fit.sum() < 30:
            continue
        Xf, yf = X[fit], yw[fit]
        XtX, Xty = Xf.T @ Xf, Xf.T @ yf
        for lam in LAMBDAS:
            b = _solve(XtX, Xty, lam)
            pred = X[out] @ b
            oof[lam][out] = pred
            sse[lam] += float(((yw[out] - pred) ** 2).sum())
    best = max(LAMBDAS, key=lambda l: (-sse[l], l))          # the smallest error; ties to the larger lambda
    XtX, Xty = X.T @ X, X.T @ yw
    beta = _solve(XtX, Xty, best)
    e = yw - oof[best]
    e = np.where(np.isnan(e), yw - X @ beta, e)             # rows never held out (a single year): in-sample residual
    P = np.eye(X.shape[1]) * best
    P[0, 0] = 0.0
    Ainv = np.linalg.inv(XtX + P)
    V = Ainv @ (X.T @ (X * (e ** 2)[:, None])) @ Ainv
    se_oof = np.sqrt(np.maximum(np.einsum("ij,jk,ik->i", X, V, X), 0))
    beta_out = beta.copy()
    beta_out[0] += delta
    return {"beta": beta_out, "lambda": best, "V": V, "oof_pred": oof[best] + delta, "oof_se": se_oof, "delta": delta, "winsor": (float(lo), float(hi)),
            "sse": {str(k): round(v, 6) for k, v in sse.items()}}


def predict(model: dict, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    X = X.astype(np.float64)
    return X @ model["beta"], np.sqrt(np.maximum(np.einsum("ij,jk,ik->i", X, model["V"], X), 0))


# ============================================================================================================================ books
class Book:
    """The slot-limited book (stage_5_book): K equal slots of book_inr / K, no compounding; shares = floor(slot / T's raw close); the rupee result
    = shares x raw entry fill x (adjusted exit fill / adjusted entry fill) minus the dated fees on the actual values; a slot freed at an open can
    be refilled at that open, but not with the stock that just left; a stock already held is HELD (no add); equity marked at every close and the
    daily return = the change in equity / book_inr; survival: equity under 95% of the previous close closes everything at the next open and
    blocks entries that day (logged); equity 22% under its high-water mark logs the pause (the continuing path keeps trading; paused_mode stops
    new entries from that date). cost_mult doubles fees and spreads (the robustness row)."""

    def __init__(self, d: Data, K: int, book_inr: float, cost_mult: float = 1.0, survival: bool = True, paused_mode: bool = False, label: str = ""):
        self.d, self.K, self.book_inr, self.m, self.survival, self.paused_mode, self.label = d, K, book_inr, cost_mult, survival, paused_mode, label
        self.slot = book_inr / K

    def run(self, s0: int, s1: int, entries_fn, keep_trades: bool = True) -> dict:
        d, K, m, slot = self.d, self.K, self.m, self.slot
        O, C, S, exit_bar, exit_px, exit_fee = d.O, d.C, d.S, d.exit_bar, d.exit_px, d.exit_fee
        cash, prev_eq, hwm = self.book_inr, self.book_inr, self.book_inr
        positions: dict[int, dict] = {}
        breach, paused = False, False
        cnt = {"entries": 0, "NO_SLOT": 0, "NO_SIZE": 0, "HELD": 0, "NO_REBUY": 0, "breaches": 0, "pause_date": None, "idle_days": 0, "days": 0, "closed_by_breach": 0}
        trades, eq_rows = [], np.zeros((s1 - s0 + 1, 4))
        dates = d.sess_days

        def realise(sc: int, p: dict, px_adj: float, s_exit: int, fee: bool, reason: str):
            nonlocal cash
            proceeds = p["shares"] * p["raw_fill"] * (px_adj / p["entry_fill"])
            fee_out = costs.cost("delivery", "sell", proceeds, when=dates[s_exit].astype(object)) * m if fee else 0.0
            cash += proceeds - fee_out
            if keep_trades:
                trades.append({**p["rec"], "exit_s": int(s_exit), "exit_fill": px_adj, "cost_out": fee_out, "pnl_rs": proceeds - p["shares"] * p["raw_fill"] - p["cost_in"] - fee_out, "reason": reason})
            del positions[sc]

        for s in range(s0, s1 + 1):
            exited_today: set[int] = set()
            if breach:   # survival: everything out at this session's open (the stock's first bar at or after s)
                for sc, p in list(positions.items()):
                    if p["exit_s"] <= s:
                        continue          # its own exit is due today: handled below
                    k, j = p["k"], p["j"]
                    while j + 1 <= p["eb"] and S[k, j + 1] <= s:
                        j += 1
                    jj = j if S[k, j] >= s else j + 1      # the stock's first bar at or after s (before its own exit bar)
                    realise(sc, p, float(O[k, jj]) * (1 - d.hs[k] * m), int(S[k, jj]), True, "survival_day")
                    exited_today.add(sc)
                    cnt["closed_by_breach"] += 1
            for sc, p in list(positions.items()):
                if p["exit_s"] <= s:
                    realise(sc, p, p["exit_fill"], p["exit_s"], p["exit_fee"], "exit")
                    exited_today.add(sc)
            if not breach and not (self.paused_mode and paused):
                for k, a, extra in entries_fn(s, positions):
                    sc = d.sid_code[k]
                    if sc in positions:
                        cnt["HELD"] += 1
                        continue
                    if sc in exited_today:
                        cnt["NO_REBUY"] += 1
                        continue
                    if len(positions) >= K:
                        cnt["NO_SLOT"] += 1
                        continue
                    rc = d.raw_close_T[k]
                    shares = int(slot // rc) if rc == rc and rc > 0 else 0
                    if shares <= 0:
                        cnt["NO_SIZE"] += 1
                        continue
                    hs = d.hs[k] * m
                    entry_fill, raw_fill = float(d.entry_o[k]) * (1 + hs), float(d.raw_entry_o[k]) * (1 + hs)
                    cost_in = costs.cost("delivery", "buy", shares * raw_fill, when=dates[s].astype(object)) * m
                    cash -= shares * raw_fill + cost_in
                    eb = int(exit_bar[k, a])
                    rec = {"book": self.label, "K": K, "cand_id": int(k), "sid": d.sid[k], "family": d.fam[k], "action": d.actions[a], "signal_s": int(d.sess_i[k]), "entry_s": int(s),
                           "shares": shares, "entry_fill": entry_fill, "raw_entry_fill": raw_fill, "cost_in": cost_in, **(extra or {})}
                    positions[sc] = {"k": k, "a": a, "shares": shares, "entry_fill": entry_fill, "raw_fill": raw_fill, "cost_in": cost_in, "eb": eb, "j": 0,
                                     "exit_s": int(d.exit_s[k, a]), "exit_fill": float(exit_px[k, a]) * (1 - hs), "exit_fee": bool(exit_fee[k, a]), "rec": rec}
                    cnt["entries"] += 1
            # mark to market at the close
            mtm = 0.0
            for sc, p in positions.items():
                k, j = p["k"], p["j"]
                while j + 1 <= p["eb"] and S[k, j + 1] <= s:
                    j += 1
                p["j"] = j
                mtm += p["shares"] * p["raw_fill"] * (float(C[k, j]) / p["entry_fill"])
            eq = cash + mtm
            breach = False
            if self.survival and eq < prev_eq * (1 - SURV_DAY) and positions:
                breach = True
                cnt["breaches"] += 1
            hwm = max(hwm, eq)
            if not paused and eq < hwm * (1 - SURV_DD):
                paused = True
                cnt["pause_date"] = str(dates[s])
            cnt["days"] += 1
            cnt["idle_days"] += int(len(positions) < K)
            eq_rows[s - s0] = (s, eq, (eq - prev_eq) / self.book_inr, len(positions))
            prev_eq = eq
        for sc, p in list(positions.items()):      # open at the end: marked, not closed (data_end)
            if keep_trades:
                k, j = p["k"], p["j"]
                trades.append({**p["rec"], "exit_s": -1, "exit_fill": float(C[k, j]), "cost_out": 0.0, "pnl_rs": p["shares"] * p["raw_fill"] * (float(C[k, j]) / p["entry_fill"] - 1) - p["cost_in"], "reason": "open_at_end"})
        daily = pd.DataFrame(eq_rows, columns=["s", "equity", "ret", "n_pos"])
        daily["s"] = daily["s"].astype(int)
        daily["date"] = pd.to_datetime(dates[daily["s"].to_numpy()])
        return {"daily": daily, "trades": pd.DataFrame(trades), "counters": cnt}


def by_day(d: Data, rows: np.ndarray, actions: np.ndarray, order: np.ndarray) -> dict[int, list]:
    """rows (cand ids) with their chosen action and an order key -> {entry session: [(k, a, None), ...] sorted by the key}."""
    out: dict[int, list] = {}
    o = np.argsort(order, kind="mergesort")
    for k, a in zip(rows[o], actions[o]):
        out.setdefault(int(d.entry_s[k]), []).append((int(k), int(a), None))
    return out


def fn_from_days(days: dict) -> callable:
    return lambda s, positions: days.get(s, ())


# ============================================================================================================================ policy
NA = len(A)


def choose(pred_net: np.ndarray, se: np.ndarray, hold_mean: np.ndarray, c: float) -> tuple[np.ndarray, np.ndarray]:
    """Rows x actions -> (chosen action index or -1, its score). Qualifies: predicted net > c x SE and > 0; the highest score wins; ties go to the
    earlier action in the spec's order (argmax takes the first maximum)."""
    ok = (pred_net > c * se) & (pred_net > 0) & np.isfinite(pred_net)
    score = np.where(ok, pred_net / hold_mean[None, :], -np.inf)
    best = score.argmax(axis=1)
    sc = score[np.arange(len(score)), best]
    return np.where(np.isfinite(sc), best, -1), np.where(np.isfinite(sc), sc, np.nan)


def policy_days(d: Data, rows: np.ndarray, act: np.ndarray, score: np.ndarray) -> dict:
    """Entries by session: the chosen rows in descending score, ties by ascending hash(sid, date, 17)."""
    m = act >= 0
    r, a, s = rows[m], act[m], score[m]
    order = np.lexsort((d.h17[r], -s))
    out: dict[int, list] = {}
    for k, ai, sc in zip(r[order], a[order], s[order]):
        out.setdefault(int(d.entry_s[k]), []).append((int(k), int(ai), {"score": float(sc)}))
    return out


def fold_masks(d: Data, y: int) -> tuple[np.ndarray, np.ndarray, int]:
    cutoff = d.first_of_year[y] - GAP
    base = d.ok & d.prio & (d.fam != "CTL")
    train = base & (d.sess_i <= cutoff) & (d.year >= 2005)
    test = base & (d.year == y)
    return train, test, cutoff


def labels(d: Data, y: int) -> np.ndarray:
    """GROSS labels for training in fold y: a trade whose exit (a halt's resume bar) falls on or after y's first session is valued at its last
    close before the halt."""
    lab = d.gross[:, :NA].astype(np.float64)
    late = d.exit_s[:, :NA] >= d.first_of_year[y]
    return np.where(late, d.gross_prehalt[:, :NA], lab)


def one_year_book(d: Data, K: int, book_inr: float, t: int, rows: np.ndarray, act: np.ndarray, score: np.ndarray) -> float:
    """The inner-CV book: starts empty on t's first session, runs to its last; returns the mean daily return."""
    b = Book(d, K, book_inr, label="inner")
    res = b.run(d.first_of_year[t], d.last_of_year[t], fn_from_days(policy_days(d, rows, act, score)), keep_trades=False)
    return float(res["daily"]["ret"].mean())


def learn_fold(d: Data, y: int, intercept_only: bool = False, drop_group: str | None = None, log=print) -> dict:
    """Stage 4 for test year y: models per (family, action), lambda, c per K row, the test-year decisions per K row."""
    t0 = time.time()
    train, test, cutoff = fold_masks(d, y)
    X, cols = design(d, train, drop_group)
    if intercept_only:
        X, cols = X[:, :1], cols[:1]
    lab = labels(d, y)
    fams = sorted(set(d.fam[train]))
    pred = np.full((d.N, NA), np.nan); se = np.full((d.N, NA), np.nan)
    oof_pred = np.full((d.N, NA), np.nan); oof_se = np.full((d.N, NA), np.nan)
    hold_mean = {}
    models = {}
    skipped = []
    for fam in fams:
        tr = np.flatnonzero(train & (d.fam == fam))
        te = np.flatnonzero(test & (d.fam == fam))
        if len(tr) < MIN_TRAIN or len(np.unique(d.year[tr])) < MIN_TRAIN_YEARS:
            skipped.append({"family": fam, "train_rows": int(len(tr)), "train_years": int(len(np.unique(d.year[tr])))})
            continue
        hm = np.zeros(NA)
        for a in range(NA):
            yv = lab[tr, a]
            good = np.isfinite(yv)
            mdl = fit_family_action(X[tr[good]], yv[good], d.year[tr[good]], d.sess_i[tr[good]], d.first_of_year, d.last_of_year)
            hm[a] = float(d.hold[tr[good], a].mean())
            oof_pred[tr[good], a], oof_se[tr[good], a] = mdl["oof_pred"], mdl["oof_se"]
            if len(te):
                pred[te, a], se[te, a] = predict(mdl, X[te])
            models[(fam, a)] = {"lambda": mdl["lambda"], "beta": mdl["beta"], "delta": mdl["delta"], "winsor": mdl["winsor"], "n": int(good.sum())}
        hold_mean[fam] = hm
    # c per K row by the inner one-year books on the out-of-fold predictions; then the test-year decisions
    inner_years = sorted(set(d.year[train]) & set(range(2005, y)))
    decisions, c_chosen, c_table = {}, {}, {}
    for name, (K, inr) in K_ROWS.items():
        fee_tr = d.fee_frac(inr / K, d.cand["signal_date"].to_numpy()[train])
        fee_te = d.fee_frac(inr / K, d.cand["signal_date"].to_numpy()[test])
        tr_rows, te_rows = np.flatnonzero(train), np.flatnonzero(test)
        hm_tr = np.array([hold_mean.get(f, np.full(NA, np.nan)) for f in d.fam[tr_rows]])
        hm_te = np.array([hold_mean.get(f, np.full(NA, np.nan)) for f in d.fam[te_rows]])
        pn_tr = oof_pred[tr_rows] - fee_tr[:, None]
        pn_te = pred[te_rows] - fee_te[:, None]
        table = {}
        for c in C_GRID:
            # the score divides by each row's own family hold mean for that action
            score_mat = np.where(np.isfinite(pn_tr) & (pn_tr > c * oof_se[tr_rows]) & (pn_tr > 0), pn_tr / hm_tr, -np.inf)
            act = np.where(np.isfinite(score_mat.max(axis=1)), score_mat.argmax(axis=1), -1)
            sc = np.where(act >= 0, score_mat.max(axis=1), np.nan)
            vals = []
            for t in inner_years:
                m = d.year[tr_rows] == t
                if not m.any():
                    continue
                vals.append(one_year_book(d, K, inr, t, tr_rows[m], act[m], sc[m]))
            table[c] = float(np.mean(vals)) if vals else float("nan")
        best_c = max(C_GRID, key=lambda c: (table[c] if table[c] == table[c] else -np.inf, c))
        c_chosen[name], c_table[name] = best_c, {str(k): round(v, 7) for k, v in table.items()}
        score_mat = np.where(np.isfinite(pn_te) & (pn_te > best_c * se[te_rows]) & (pn_te > 0), pn_te / hm_te, -np.inf)
        act = np.where(np.isfinite(score_mat.max(axis=1)), score_mat.argmax(axis=1), -1)
        sc = np.where(act >= 0, score_mat.max(axis=1), np.nan)
        decisions[name] = pd.DataFrame({"cand_id": te_rows, "action": act, "score": sc, "year": y, "c": best_c, "pred_net_best": np.where(act >= 0, pn_te[np.arange(len(te_rows)), np.maximum(act, 0)], np.nan),
                                        "any_qualifies": (score_mat > -np.inf).any(axis=1)})
    log(f"  fold {y}: train {int(train.sum())} test {int(test.sum())} families {len(hold_mean)} skipped {[s['family'] for s in skipped]} c {c_chosen} "
        f"trades K5 {int((decisions['K5']['action'] >= 0).sum())} of {len(decisions['K5'])}  {time.time() - t0:.0f}s")
    return {"year": y, "cutoff": cutoff, "cols": cols, "models": models, "hold_mean": hold_mean, "skipped": skipped, "c": c_chosen, "c_table": c_table, "decisions": decisions,
            "inner_years": inner_years}


# ============================================================================================================================ baseline
BAR_FAMILIES = ["exit", "stop", "gate", "reposition", "staging", "indicator", "portfolio", "context", "context_events", "filter", "events", "flows", "SP3"]
UNION_K, HOLDOUT_K = 742, 7


def baseline_pool(d: Data) -> np.ndarray:
    """The unfiltered baseline's candidates: every real-family priority row (ANY and CTL are not real families)."""
    return np.flatnonzero(d.ok & d.prio & ~np.isin(d.fam, ["CTL", "ANY"]))


def baseline_fn(d: Data, pool: np.ndarray, seed: int, action_of_year) -> callable:
    """Entries by session in ascending hash(sid, date, seed) with the fixed action for the signal's year (a callable year -> action index)."""
    h = R.prep.hash_many(d.sid[pool], d.cand["signal_date"].to_numpy()[pool], seed)
    o = np.argsort(h, kind="mergesort")
    days: dict[int, list] = {}
    for k in pool[o]:
        days.setdefault(int(d.entry_s[k]), []).append(int(k))
    def fn(s, positions):
        return [(k, action_of_year(max(2010, int(d.year[k]))), None) for k in days.get(s, ())]
    return fn


def baseline_long_books(d: Data, log=print) -> np.ndarray:
    """25 actions x 20 seeds unfiltered K=5 books from 2005 to 2023 (for the fixed action of each fold: the best 20-seed mean daily return on the
    sessions up to the fold's cutoff). Cached in gold/studies/SP3_baseline_long.npy as [action, seed, session]."""
    f = G / "SP3_baseline_long.npy"
    if f.exists():
        return np.load(f)
    t0 = time.time()
    pool = baseline_pool(d)
    s0, s1 = d.first_of_year[2005], d.last_of_year[2023]
    out = np.zeros((NA, len(BASELINE_SEEDS), s1 - s0 + 1), np.float32)
    for a in range(NA):
        for j, seed in enumerate(BASELINE_SEEDS):
            res = Book(d, 5, 60_000.0, label="baseline_long").run(s0, s1, baseline_fn(d, pool, seed, lambda y, a=a: a), keep_trades=False)
            out[a, j] = res["daily"]["ret"].to_numpy()
        log(f"  baseline long books: action {A[a]} done  {time.time() - t0:.0f}s")
    np.save(f, out)
    return out


def fixed_action_for(d: Data, long: np.ndarray, cutoff: int) -> tuple[int, dict]:
    s0 = d.first_of_year[2005]
    seg = long[:, :, : max(1, cutoff - s0 + 1)]
    means = seg.mean(axis=(1, 2))
    best = int(np.argmax(means))
    return best, {A[i]: round(float(means[i]), 7) for i in range(NA)}


# ============================================================================================================================ statistics
def nw_t(x: np.ndarray, lags: int = NW_LAGS) -> float:
    x = np.asarray(x, float)
    n = len(x)
    if n < 10:
        return float("nan")
    e = x - x.mean()
    s = float(e @ e) / n
    for l in range(1, lags + 1):
        s += 2 * (1 - l / (lags + 1)) * float(e[l:] @ e[:-l]) / n
    return float(x.mean() / math.sqrt(s / n)) if s > 0 else float("nan")


def block_boot(x: np.ndarray, draws: int = BOOT_DRAWS, block: int = BOOT_BLOCK, seed: int = BOOT_SEED) -> dict:
    x = np.asarray(x, float)
    n = len(x)
    if n < block * 2:
        return {"p_le_0": float("nan"), "ci5": float("nan"), "ci95": float("nan")}
    rng = np.random.default_rng(seed)
    nb = int(math.ceil(n / block))
    starts = rng.integers(0, n - block + 1, size=(draws, nb))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(draws, -1)[:, :n]
    means = x[idx].mean(axis=1)
    return {"p_le_0": float((means <= 0).mean()), "ci5": float(np.quantile(means, 0.05)), "ci95": float(np.quantile(means, 0.95))}


def daily_row(series: pd.Series) -> dict:
    """A daily book row: dev and validation mean, Newey-West t, quarters, annualised Sharpe, bootstrap."""
    out = {}
    for per, years in (("dev", DEV_YEARS), ("val", VAL_YEARS)):
        x = series[series.index.year.isin(years)]
        q = x.index.to_period("Q").nunique()
        out[per] = {"mean": float(x.mean()), "t_nw5": nw_t(x.to_numpy()), "days": int(len(x)), "quarters": int(q), "sharpe_ann": float(x.mean() / x.std(ddof=1) * math.sqrt(250)) if x.std(ddof=1) > 0 else float("nan"),
                    "total": float(x.sum()), **{"boot_" + k: v for k, v in block_boot(x.to_numpy()).items()}}
    return out


def trade_row(tr: pd.DataFrame, col: str, dates: pd.Series) -> dict:
    out = {}
    for per, years in (("dev", DEV_YEARS), ("val", VAL_YEARS)):
        m = dates.dt.year.isin(years)
        x, dd = tr.loc[m, col], dates[m]
        q = x.groupby(dd.dt.to_period("Q")).mean()
        se = q.std(ddof=1) / math.sqrt(len(q)) if len(q) > 2 else float("nan")
        out[per] = {"mean": float(x.mean()) if len(x) else float("nan"), "t_blk": float(q.mean() / se) if se and se > 0 else float("nan"), "n": int(len(x)), "quarters": int(len(q))}
    return out


def per_year(series: pd.Series) -> dict:
    return {int(y): {"mean": round(float(g.mean()), 7), "total": round(float(g.sum()), 5), "days": int(len(g))} for y, g in series.groupby(series.index.year)}


def eras(series: pd.Series) -> dict:
    out = {}
    for name, (a, b) in {"2018-2019": (2018, 2019), "2020": (2020, 2020), "2021-2023": (2021, 2023)}.items():
        x = series[(series.index.year >= a) & (series.index.year <= b)]
        out[name] = {"mean": round(float(x.mean()), 7), "t_nw5": round(nw_t(x.to_numpy()), 3), "days": int(len(x))}
    return out


# ============================================================================================================================ the run
def ctl_fn(d: Data, pol_trades: pd.DataFrame, slot: float, counters: dict) -> callable:
    """stage_5 ctl_book: each policy entry that took a slot on session s is shadowed by the next CTL candidate of the same signal day in ascending
    hash(sid, date, 13) that the CTL book does not hold (NO_SIZE skipped; NO_CTL when the day's list runs out), with the same action."""
    ctl_rows = np.flatnonzero(d.ok & (d.fam == "CTL"))
    pool: dict[int, list] = {}
    for k in ctl_rows[np.argsort(d.h13[ctl_rows], kind="mergesort")]:
        pool.setdefault(int(d.sess_i[k]), []).append(int(k))
    ptr: dict[int, int] = {}
    by_s: dict[int, list] = {}
    for t in pol_trades.itertuples():
        by_s.setdefault(int(t.entry_s), []).append((int(t.signal_s), int(d.actions.index(t.action)), int(t.cand_id)))
    def fn(s, positions):
        out, taken = [], set()
        for sig, a, cid in by_s.get(s, ()):
            lst, p, chosen = pool.get(sig, []), ptr.get(sig, 0), None
            while p < len(lst):
                k = lst[p]; p += 1
                if d.sid_code[k] in positions or d.sid_code[k] in taken or int(d.entry_s[k]) != s:
                    continue
                if not (d.raw_close_T[k] > 0) or int(slot // d.raw_close_T[k]) <= 0:
                    counters["ctl_NO_SIZE"] += 1
                    continue
                chosen = k
                break
            ptr[sig] = p
            if chosen is None:
                counters["NO_CTL"] += 1
                continue
            taken.add(d.sid_code[chosen])
            out.append((chosen, a, {"shadow_of": cid}))
        return out
    return fn


def nifty_daily(d: Data) -> pd.Series:
    ix = pd.read_parquet(paths.data_dir() / "silver" / "kite_index" / "day" / "day.parquet", columns=["index_name", "date", "close"])
    ix = ix[ix["index_name"] == "NIFTY 50"].copy()
    ix["date"] = pd.to_datetime(ix["date"])
    s = ix.set_index("date")["close"].sort_index()
    return s.pct_change()


def run(write_registry: bool = True, log=print) -> dict:
    R._check_spec()
    t0 = time.time()
    RUNS = R.RUNS
    RUNS.mkdir(parents=True, exist_ok=True)
    d = Data()
    log(f"data loaded in {d.seconds}s: {d.N} candidates, {int(d.ok.sum())} with outcomes")
    long = baseline_long_books(d, log)
    folds, folds0 = {}, {}
    for y in YEARS:
        folds[y] = learn_fold(d, y, log=log)
        folds0[y] = learn_fold(d, y, intercept_only=True, log=lambda m: log("    intercept-only " + m.strip()))
    fixed = {y: fixed_action_for(d, long, folds[y]["cutoff"]) for y in YEARS}
    log("fixed actions by year: " + ", ".join(f"{y}:{A[fixed[y][0]]}" for y in YEARS))
    s0, s1 = d.first_of_year[2010], d.last_of_year[2023]
    dec = {name: pd.concat([folds[y]["decisions"][name] for y in YEARS], ignore_index=True) for name in K_ROWS}
    dec0 = pd.concat([folds0[y]["decisions"]["K5"] for y in YEARS], ignore_index=True)
    books, daily, trades = {}, {}, []

    def run_book(label: str, df: pd.DataFrame, K: int, inr: float, action_override=None, row_filter=None, **kw):
        rows = df["cand_id"].to_numpy(); act = df["action"].to_numpy().copy(); sc = df["score"].to_numpy()
        if action_override is not None:
            act = np.where(act >= 0, np.array([action_override(int(d.year[k])) for k in rows]), -1)
        if row_filter is not None:
            m = row_filter(rows); rows, act, sc = rows[m], act[m], sc[m]
        res = Book(d, K, inr, label=label, **kw).run(s0, s1, fn_from_days(policy_days(d, rows, act, sc)))
        books[label] = res
        daily[label] = res["daily"].set_index("date")["ret"]
        trades.append(res["trades"])
        log(f"  book {label}: entries {res['counters']['entries']} NO_SLOT {res['counters']['NO_SLOT']} NO_SIZE {res['counters']['NO_SIZE']} breaches {res['counters']['breaches']} "
            f"pause {res['counters']['pause_date']} mean/day {daily[label].mean():.6f}  {time.time() - t0:.0f}s")
        return res

    run_book("policy", dec["K5"], 5, 60_000.0)
    run_book("policy_K10", dec["K10"], 10, 200_000.0)
    run_book("policy_K20", dec["K20"], 20, 1_000_000.0)
    run_book("intercept_only", dec0, 5, 60_000.0)
    run_book("policy_K3", dec["K5"], 3, 60_000.0)
    run_book("policy_K8", dec["K5"], 8, 60_000.0)
    run_book("policy_cost2", dec["K5"], 5, 60_000.0, cost_mult=2.0)
    run_book("policy_paused", dec["K5"], 5, 60_000.0, paused_mode=True)
    run_book("policy_liq_1_125", dec["K5"], 5, 60_000.0, row_filter=lambda rows: d.liq[rows] <= 125)
    run_book("policy_liq_126_250", dec["K5"], 5, 60_000.0, row_filter=lambda rows: d.liq[rows] > 125)
    run_book("fixed_exit", dec["K5"], 5, 60_000.0, action_override=lambda y: fixed[y][0])
    # the unfiltered baseline: 20 seeds, the fixed action of each signal's year
    pool = baseline_pool(d)
    base_cols = []
    for seed in BASELINE_SEEDS:
        res = Book(d, 5, 60_000.0, label=f"baseline_{seed}").run(s0, s1, baseline_fn(d, pool, seed, lambda y: fixed[y][0]), keep_trades=(seed == BASELINE_SEEDS[0]))
        base_cols.append(res["daily"].set_index("date")["ret"].rename(seed))
        if seed == BASELINE_SEEDS[0]:
            trades.append(res["trades"]); books["baseline_101"] = res
    base = pd.concat(base_cols, axis=1)
    daily["baseline"] = base.mean(axis=1)
    log(f"  baseline (20 seeds): mean/day {daily['baseline'].mean():.6f}; seed spread {base.mean().min():.6f}..{base.mean().max():.6f}  {time.time() - t0:.0f}s")
    # CTL shadow of the policy's K=5 entries
    ctl_cnt = {"ctl_NO_SIZE": 0, "NO_CTL": 0}
    pol_tr = books["policy"]["trades"]
    res = Book(d, 5, 60_000.0, label="ctl").run(s0, s1, ctl_fn(d, pol_tr, 12_000.0, ctl_cnt))
    books["ctl"] = res; daily["ctl"] = res["daily"].set_index("date")["ret"]; trades.append(res["trades"])
    log(f"  ctl: entries {res['counters']['entries']} NO_CTL {ctl_cnt['NO_CTL']} mean/day {daily['ctl'].mean():.6f}")
    nifty = nifty_daily(d).reindex(daily["policy"].index).fillna(0.0)
    # ---- the rows
    series = {"STOCK|book|policy": daily["policy"], "STOCK|book|vs_baseline": daily["policy"] - daily["baseline"], "STOCK|book|vs_intercept_only": daily["policy"] - daily["intercept_only"],
              "STOCK|book|vs_ctl": daily["policy"] - daily["ctl"], "STOCK|book|exit_choice": daily["policy"] - daily["fixed_exit"],
              "STOCK|book|K10": daily["policy_K10"], "STOCK|book|K20": daily["policy_K20"], "STOCK|book|vs_nifty": daily["policy"] - nifty}
    exploratory = {"STOCK|book|K10", "STOCK|book|K20", "STOCK|book|vs_nifty", "STOCK|trade|policy", "STOCK|trade|exit_choice"}
    rows = {k: daily_row(v) for k, v in series.items()}
    pt = pol_tr[pol_tr["reason"] != "open_at_end"].copy()
    pt["net_ret"] = pt["pnl_rs"] / (pt["shares"] * pt["raw_entry_fill"])
    pt["signal_date"] = pd.to_datetime(d.sess_days[pt["signal_s"].to_numpy()])
    rows["STOCK|trade|policy"] = trade_row(pt, "net_ret", pt["signal_date"])
    fee5 = d.fee_frac(12_000.0, pt["signal_date"])
    ai = pt["action"].map(d.actions.index).to_numpy(); ci = pt["cand_id"].to_numpy()
    fx = np.array([fixed[int(d.year[k])][0] for k in ci])
    pt["exit_choice_diff"] = (d.gross[ci, ai] - fee5) - (d.gross[ci, fx] - fee5)
    rows["STOCK|trade|exit_choice"] = trade_row(pt, "exit_choice_diff", pt["signal_date"])
    val_trades = int((pt["signal_date"].dt.year >= 2018).sum())
    dev_trades = int((pt["signal_date"].dt.year < 2018).sum())
    # ---- registry
    ledger = []
    if write_registry:
        from india import registry
        regs = [r for r in registry._rows() if r["kind"] == "registration" and r["study"] == "SP3"]
        reg = regs[-1] if regs else registry.register(
            "SP3", family="SP3", title="SP3 positional playbook: situation-dependent entry, exit and holding time for liquid stocks (sp3-v1-2026-10-20-frozen)",
            hypothesis="the situation-aware policy book (K=5, Rs 60,000) earns more per day than zero, than the unfiltered baseline, than the same policy without situation features, than matched controls with the same exits, and than its entries with the baseline's fixed exit",
            variants=list(rows), note=f"frozen spec sha {R.SPEC_SHA}; dev 2010-2017 reported, validation 2018-2023 SEEN (rule seen_val_only); holdout 2024-01-01..2026-09-30 untouched, opened only by the registered sp3_holdout run after approval",
            bar_families=BAR_FAMILIES, union_k=UNION_K, holdout_k=HOLDOUT_K)
        for name, r in rows.items():
            dv, vl = r["dev"], r["val"]
            tkey = "t_nw5" if "t_nw5" in dv else "t_blk"
            extra = {"exploratory": name in exploratory, "statistic": "Newey-West t, 5 lags, daily series" if tkey == "t_nw5" else "quarter-block means, t over quarters",
                     "dev_days_or_n": dv.get("days", dv.get("n")), "val_days_or_n": vl.get("days", vl.get("n")), "val_trades": val_trades, "min_trades_ok": val_trades >= MIN_VAL_TRADES,
                     "boot_p_le_0_val": vl.get("boot_p_le_0"), "sharpe_ann_val": vl.get("sharpe_ann"), "c_K5_by_year": {y: folds[y]["c"]["K5"] for y in YEARS}}
            ledger.append(registry.record(reg, variant=name, dev=(dv["mean"], dv[tkey], dv["quarters"]), val=(vl["mean"], vl[tkey], vl["quarters"]), extra=extra, expect=1, rule="seen_val_only"))
        registry.mirror_to_catalog()
    # ---- outputs
    tr_all = pd.concat([t for t in trades if len(t)], ignore_index=True)
    for c in ("signal_s", "entry_s", "exit_s"):
        tr_all[c.replace("_s", "_date")] = pd.to_datetime(np.where(tr_all[c] >= 0, d.sess_days[np.maximum(tr_all[c].to_numpy(), 0)], np.datetime64("NaT")))
    tr_all.to_parquet(G / "SP3_policy_trades.parquet", index=False)
    dly = pd.concat([v["daily"].assign(book=k, K=v["counters"].get("K", None)) for k, v in books.items()], ignore_index=True)
    dly["K"] = dly["book"].map(lambda b: {"policy": 5, "policy_K10": 10, "policy_K20": 20, "policy_K3": 3, "policy_K8": 8}.get(b, 5))
    dly.to_parquet(G / "SP3_book_daily.parquet", index=False)
    chosen_by_year = {int(y): {A[a]: int(n) for a, n in g["action"].value_counts().items() if a >= 0} for y, g in dec["K5"].groupby("year")}
    learned = {}
    for (fam, a), m in folds[2023]["models"].items():
        if fam not in learned:
            top = dec["K5"][(dec["K5"]["year"] == 2023) & (dec["K5"]["cand_id"].map(lambda k: d.fam[k]) == fam)]["action"]
            top = int(top[top >= 0].mode().iloc[0]) if (top >= 0).any() else 0
            learned[fam] = {"action": A[top], "coefficients": None}
        if A[a] == learned[fam]["action"]:
            cols = folds[2023]["cols"]
            order = np.argsort(-np.abs(m["beta"][1:]))[:8]
            learned[fam]["coefficients"] = {cols[i + 1]: round(float(m["beta"][i + 1]), 5) for i in order}
            learned[fam]["intercept"] = round(float(m["beta"][0]), 5); learned[fam]["lambda"] = m["lambda"]; learned[fam]["n_train"] = m["n"]
    robustness = {"per_year_policy": per_year(daily["policy"]), "per_year_vs_baseline": per_year(series["STOCK|book|vs_baseline"]),
                  "val_years_positive_policy": int(sum(per_year(daily["policy"])[y]["mean"] > 0 for y in VAL_YEARS)),
                  "val_years_positive_vs_baseline": int(sum(per_year(series["STOCK|book|vs_baseline"])[y]["mean"] > 0 for y in VAL_YEARS)),
                  "eras_policy": eras(daily["policy"]), "eras_vs_baseline": eras(series["STOCK|book|vs_baseline"]),
                  "costs_x2": daily_row(daily["policy_cost2"]), "K3": daily_row(daily["policy_K3"]), "K8": daily_row(daily["policy_K8"]),
                  "liq_1_125": daily_row(daily["policy_liq_1_125"]), "liq_126_250": daily_row(daily["policy_liq_126_250"]),
                  "paused_path": daily_row(daily["policy_paused"]), "stops_at_last_close": "identical: no end_failed window among the candidates (sp3_outcomes.json)",
                  "reverse_priority": "not run in this session (needs a stage-1 rerun with the reverse order)"}
    counters = {k: v["counters"] for k, v in books.items()}
    counters["ctl_extra"] = ctl_cnt
    out = {"spec_version": "sp3-v1-2026-10-20-frozen", "periods": {"dev": "2010-2017 (reported, not gating)", "val": "2018-2023 (SEEN: rule seen_val_only)", "holdout": "untouched, not opened"},
           "rows": rows, "exploratory_rows": sorted(exploratory), "ledger": ledger, "trades": {"dev": dev_trades, "val": val_trades, "min_val_trades": MIN_VAL_TRADES},
           "c_by_year": {y: folds[y]["c"] for y in YEARS}, "c_tables_K5": {y: folds[y]["c_table"]["K5"] for y in YEARS}, "fixed_action_by_year": {y: A[fixed[y][0]] for y in YEARS},
           "fixed_action_means_2023": fixed[2023][1], "skipped_families_by_year": {y: [s["family"] for s in folds[y]["skipped"]] for y in YEARS},
           "lambda_counts": {str(l): int(sum(1 for y in YEARS for m in folds[y]["models"].values() if m["lambda"] == l)) for l in LAMBDAS},
           "actions_chosen_by_year_K5": chosen_by_year, "learned_2023": learned, "book_counters": counters, "robustness": robustness,
           "idle_slot_share_policy": round(counters["policy"]["idle_days"] / max(1, counters["policy"]["days"]), 4),
           "baseline_seed_means": {int(k): round(float(v), 7) for k, v in base.mean().items()},
           "not_run_this_session": ["INDEX rows (NIFTY, BANKNIFTY futures book)", "state-shuffle nulls (200 draws)", "drop-one feature-group ablations", "12 start months", "reverse family priority", "filters-as-findings slices"],
           "files": [str(G / "SP3_policy_trades.parquet"), str(G / "SP3_book_daily.parquet")], "seconds": round(time.time() - t0, 1)}
    R._write("sp3_results.json", out)
    write_doc(out)
    return out


def write_doc(o: dict) -> Path:
    L = ["# SP3 results: dev 2010-2017 and validation 2018-2023 (stocks)", "",
         f"Generated by `python -m india.sp3learn run` on {dt.date.today()} from the frozen spec `registrations/sp3_v1.json` (sha {R.SPEC_SHA}). HISTORICAL BACKTEST on seen "
         "years: 2018-2023 was shaped by earlier studies, so every row is scored with rule `seen_val_only` and nothing here confirms anything; only the registered holdout run "
         "(2024-01-01 to 2026-09-30, opened once after Madhav's approval) can. The index rows and the descriptive nulls/ablations are not in this run (listed at the end).", "",
         "## The rows (daily book series: Newey-West t with 5 lags; trade rows: quarter-block means)", "",
         "| row | dev mean/day | dev t | val mean/day | val t | val Sharpe | val boot p(<=0) | verdict |", "|---|---|---|---|---|---|---|---|"]
    verdict = {l["variant"]: l["verdict"] for l in o["ledger"]}
    for name, r in o["rows"].items():
        dv, vl = r["dev"], r["val"]
        t = "t_nw5" if "t_nw5" in dv else "t_blk"
        L.append(f"| {name}{' (exploratory)' if name in o['exploratory_rows'] else ''} | {dv['mean']*1e4:+.2f} bp | {dv[t]:+.2f} | {vl['mean']*1e4:+.2f} bp | {vl[t]:+.2f} | "
                 f"{vl.get('sharpe_ann', float('nan')):+.2f} | {vl.get('boot_p_le_0', float('nan')):.3f} | {verdict.get(name, 'not recorded')} |")
    L += ["", f"Trades in the K=5 policy book: dev {o['trades']['dev']}, validation {o['trades']['val']} (minimum {o['trades']['min_val_trades']} for a non-INCONCLUSIVE row). "
          f"Idle-slot share of days: {o['idle_slot_share_policy']}. Book counters: {json.dumps(o['book_counters']['policy'])}.", "",
          "## What the walk-forward chose", "",
          f"- c (qualifying margin) by test year, K=5: {o['c_by_year']}", f"- the baseline's fixed action by year: {o['fixed_action_by_year']}",
          f"- lambda counts over all (family, action, year) models: {o['lambda_counts']} (1000 = the heaviest shrinkage: the situation features add little beyond the family mean)",
          f"- families not modelled (fewer than 300 training rows or 3 years): {o['skipped_families_by_year']}", "",
          "### Actions the policy chose, by year (K=5)", ""]
    for y, c in o["actions_chosen_by_year_K5"].items():
        L.append(f"- {y}: {dict(sorted(c.items(), key=lambda kv: -kv[1])[:6])}")
    L += ["", "### What the 2023 models learned (largest coefficients, the family's most-chosen action)", ""]
    for fam, m in o["learned_2023"].items():
        L.append(f"- {fam} / {m['action']} (lambda {m.get('lambda')}, n {m.get('n_train')}, intercept {m.get('intercept')}): {m.get('coefficients')}")
    rb = o["robustness"]
    L += ["", "## Robustness", "", f"- validation years with a positive policy book: {rb['val_years_positive_policy']} of 6; positive vs baseline: {rb['val_years_positive_vs_baseline']} of 6 (robust at 4+)",
          f"- eras (policy): {rb['eras_policy']}", f"- eras (vs baseline): {rb['eras_vs_baseline']}",
          f"- costs and spreads x2: val mean {rb['costs_x2']['val']['mean']*1e4:+.2f} bp/day, t {rb['costs_x2']['val']['t_nw5']:+.2f}",
          f"- K=3: val {rb['K3']['val']['mean']*1e4:+.2f} bp/day (t {rb['K3']['val']['t_nw5']:+.2f}); K=8: val {rb['K8']['val']['mean']*1e4:+.2f} bp/day (t {rb['K8']['val']['t_nw5']:+.2f})",
          f"- liquidity halves: rank 1-125 val {rb['liq_1_125']['val']['mean']*1e4:+.2f} bp/day (t {rb['liq_1_125']['val']['t_nw5']:+.2f}); rank 126-250 val {rb['liq_126_250']['val']['mean']*1e4:+.2f} bp/day (t {rb['liq_126_250']['val']['t_nw5']:+.2f})",
          f"- paused path (no entries after a 22% drawdown): val {rb['paused_path']['val']['mean']*1e4:+.2f} bp/day; pause date {o['book_counters']['policy'].get('pause_date')}",
          f"- permanent stops at the last close: {rb['stops_at_last_close']}", f"- reverse family priority: {rb['reverse_priority']}", "",
          "## Cross-check (india/checks/sp3_crosscheck.py)", ""]
    cc = paths.manifest_dir() / "sp3_crosscheck.json"
    if cc.exists():
        c = json.loads(cc.read_text())
        oc, bk = c.get("outcomes", {}), c.get("book", {})
        L += [f"- outcomes: {oc.get('agree')} of {oc.get('sampled')} sampled (candidate, action) rows re-derived bar by bar with exitlab._exit on the holding bars agree to the rupee ({oc.get('differ')} differ)",
              f"- book days: {bk.get('agree')} of {bk.get('days')} K=5 policy-book days recomputed from the trade list agree within Rs 1; the rest differ by under Rs 200 where a survival closure fell on a session the stock did not trade (the book credits the cash a session early)", ""]
    L += ["## Not run in this session", ""] + [f"- {x}" for x in o["not_run_this_session"]] + ["",
          "## Files", ""] + [f"- `{f}`" for f in o["files"]] + ["- `manifests/sp3_results.json`, `manifests/sp3_outcomes.json`, `manifests/sp3_features.json`, `manifests/sp3_bars.json`, `manifests/sp3_crosscheck.json`", ""]
    p = R.HERE / "registrations" / "sp3_results.md"
    p.write_text("\n".join(L))
    return p


if __name__ == "__main__":
    paths.ensure()
    a = sys.argv[1:]
    logf = (R.RUNS / "learn.log")
    R.RUNS.mkdir(parents=True, exist_ok=True)
    def log(m):
        print(m, flush=True)
        with logf.open("a") as fh:
            fh.write(f"{dt.datetime.now().isoformat(timespec='seconds')} {m}\n")
    if a[:1] == ["run"]:
        o = run(write_registry="--no-registry" not in a, log=log)
        print(json.dumps({k: o[k] for k in ("rows", "trades", "c_by_year", "fixed_action_by_year", "seconds")}, indent=1, default=str))
    elif a[:1] == ["baseline"]:
        d = Data()
        baseline_long_books(d, log)
    else:
        print(__doc__)
