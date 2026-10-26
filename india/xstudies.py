"""XO1 (moving-average and MACD crossovers), FX1 (the rupee against the dollar) and FII1 (foreign investor cash flows): three registered studies
Madhav asked for in the India chat of 26 Oct 2026; SR1 (support and resistance as an entry), his yes of 26 Oct 12:19 Toronto. Each spec is written first (india/registrations/<id>_v1.json, with every variant and its expected
sign); `run` registers the study with the spec's frozen k, computes, and records every variant in the ledger. Research rows only: nothing dated
2024 or later is used and no holdout folder is opened (index and stock panels come from india.teachers_stock, which cuts at 2024-01-01).

  python -m india.xstudies check XO1|FX1|FII1|SR1|all     event counts per period only (no means, no t, no verdicts): a code check before the run
  python -m india.xstudies run XO1|FX1|FII1|SR1|all     register, compute, record; manifests/xstudies_<id>.json and a results table in registrations/
"""
from __future__ import annotations

import json
import math
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from india import paths, registry
from india import teachers_stock as ts

REG_DIR = Path(__file__).resolve().parent / "registrations"
CUT = pd.Timestamp("2024-01-01")
SPLIT = ts.SPLIT


def spec(study: str) -> dict:
    return json.loads((REG_DIR / f"{study.lower()}_v1.json").read_text())


def _clean(x):
    if isinstance(x, dict):
        return {str(k): _clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_clean(v) for v in x]
    if isinstance(x, (np.floating, float)):
        return None if (x != x or math.isinf(x)) else float(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.bool_,)):
        return bool(x)
    return x


def _cool(on: pd.Series, gap: int) -> pd.Series:
    """One event per `gap` sessions on a single series (an index)."""
    keep = np.zeros(len(on), bool)
    last = -10 ** 9
    for i, v in enumerate(on.fillna(False).astype(bool).values):
        if v and i - last >= gap:
            keep[i] = True
            last = i
    return pd.Series(keep, index=on.index)


def _period_counts(dates: pd.Series, on: pd.Series) -> dict:
    o = on.reindex(dates.index).fillna(False).astype(bool)
    y = pd.to_datetime(dates).dt.year
    return {"events_dev": int((o & (y < SPLIT)).sum()), "events_val": int((o & (y >= SPLIT)).sum())}


# ------------------------------------------------------------------------------------------------------------------------- XO1

def _index_frame(name: str) -> pd.DataFrame:
    piv = ts.index_panel()
    c = piv[name].dropna()
    c = c[c.index < CUT]
    M = pd.DataFrame(index=c.index)
    M["date"] = c.index
    for k in (5, 20, 21, 60, 63):
        M[f"fwd{k}"] = ts._fwd_close(c, k)
    M["abs20"] = M["fwd20"].abs()
    sma20, sma50, sma200 = c.rolling(20, min_periods=20).mean(), c.rolling(50, min_periods=50).mean(), c.rolling(200, min_periods=200).mean()
    above = sma50 > sma200
    up2050 = sma20 > sma50
    ema12, ema26 = c.ewm(span=12, adjust=False).mean(), c.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    sig = macd.ewm(span=9, adjust=False).mean()
    warm = pd.Series(np.arange(len(c)) >= 60, index=c.index)
    ok = sma200.notna()
    M["ok"] = ok
    ok2 = ok & ok.shift(1, fill_value=False)                       # a cross needs both days to have the averages (no false cross on the first day)
    v50 = sma50.notna() & sma50.notna().shift(1, fill_value=False)
    w2 = warm & warm.shift(1, fill_value=False)
    M["gc"] = _cool(above & ~above.shift(1, fill_value=True) & ok2, 20)
    M["dc"] = _cool(~above & above.shift(1, fill_value=False) & ok2, 20)
    M["x2050up"] = _cool(up2050 & ~up2050.shift(1, fill_value=True) & v50, 10)
    M["x2050dn"] = _cool(~up2050 & up2050.shift(1, fill_value=False) & v50, 10)
    mu = macd > sig
    M["macdup"] = _cool(mu & ~mu.shift(1, fill_value=True) & w2, 10)
    M["macddn"] = _cool(~mu & mu.shift(1, fill_value=False) & w2, 10)
    M["state50gt200"] = above & ok
    lo = pd.concat([sma20, sma50, sma200], axis=1).min(axis=1)
    hi = pd.concat([sma20, sma50, sma200], axis=1).max(axis=1)
    M["converge"] = ((hi / lo - 1) < 0.02) & ok
    return M


def _stock_frame() -> pd.DataFrame:
    cols = ["sid", "date", "n", "liq_rank", "c", "dist_sma20", "dist_sma50", "dist_sma200", "fwd20", "net20", "net60", "nifty_vs200", "nifty_below_both"]
    P = pd.read_parquet(paths.gold() / "teachers" / "stock_panel.parquet", columns=cols)
    P["date"] = pd.to_datetime(P["date"])
    P = P[P["date"] < CUT].sort_values(["sid", "date"]).reset_index(drop=True)
    sma20 = P["c"] / (1 + P["dist_sma20"])
    sma50 = P["c"] / (1 + P["dist_sma50"])
    sma200 = P["c"] / (1 + P["dist_sma200"])
    consec = (P["sid"] == P["sid"].shift(1)) & (P["n"] == P["n"].shift(1) + 1)
    seg = (~consec).cumsum()

    def cross(state: pd.Series, valid: pd.Series, up: bool) -> pd.Series:
        prev = state.shift(1)
        hit = (state & (prev == False)) if up else (~state & (prev == True))   # noqa: E712
        return (hit & consec & valid & valid.shift(1, fill_value=False)).fillna(False).astype(bool)

    v200 = sma50.notna() & sma200.notna()
    v50 = sma20.notna() & sma50.notna()
    above = (sma50 > sma200).where(v200)
    up2050 = (sma20 > sma50).where(v50)
    P["gc"] = cross(above.fillna(False).astype(bool), v200, True)
    P["dc"] = cross(above.fillna(False).astype(bool), v200, False)
    P["x2050up"] = cross(up2050.fillna(False).astype(bool), v50, True)
    P["x2050dn"] = cross(up2050.fillna(False).astype(bool), v50, False)
    g = P.groupby(seg)["c"]
    ema12 = g.transform(lambda x: x.ewm(span=12, adjust=False).mean())
    ema26 = g.transform(lambda x: x.ewm(span=26, adjust=False).mean())
    macd = ema12 - ema26
    sig = macd.groupby(seg).transform(lambda x: x.ewm(span=9, adjust=False).mean())
    warm = P.groupby(seg).cumcount() >= 60
    mu = (macd > sig)
    prev_mu = mu.groupby(seg).shift(1)
    P["macdup"] = (mu & (prev_mu == False) & warm).fillna(False).astype(bool)   # noqa: E712
    P["macddn"] = (~mu & (prev_mu == True) & warm).fillna(False).astype(bool)   # noqa: E712
    allv = sma20.notna() & sma50.notna() & sma200.notna()
    lo = pd.concat([sma20, sma50, sma200], axis=1).min(axis=1)
    hi = pd.concat([sma20, sma50, sma200], axis=1).max(axis=1)
    conv = ((hi / lo - 1) < 0.02) & allv
    P["converge"] = (conv & ~(conv.groupby(seg).shift(1).fillna(False).astype(bool)) & consec).astype(bool)
    P["abs20"] = P["fwd20"].abs()
    liq = P["liq_rank"] <= 250
    for k, gap in (("gc", 20), ("dc", 20), ("x2050up", 10), ("x2050dn", 10), ("macdup", 10), ("macddn", 10), ("converge", 20)):
        P[k] = ts._cooldown(P, P[k] & liq, gap)
    P["liq"] = liq
    P["s5"] = ts.sample5(P)
    return P


def xo1_results(counts_only: bool = False) -> dict:
    out = {}
    for tag, name in (("NIFTY", "NIFTY 50"), ("BANK", "NIFTY BANK")):
        M = _index_frame(name)
        for ev, col, h in (("gc", "fwd60", 60), ("dc", "fwd60", 60), ("x2050up", "fwd20", 20), ("x2050dn", "fwd20", 20), ("macdup", "fwd20", 20),
                           ("macddn", "fwd20", 20), ("state50gt200", "fwd20", 20), ("converge", "abs20", 20)):
            key = f"{tag}|{ev}|{col}"
            cnt = _period_counts(M["date"], M[ev] & M["ok"])
            if counts_only:
                out[key] = cnt
                continue
            r = ts.msplit(M, M[ev], col, h=h, base=M["ok"])
            r["extra"] = {**r["extra"], **cnt}
            out[key] = r
    P = _stock_frame()
    base = P["liq"] & (P["s5"] | P[["gc", "dc", "x2050up", "x2050dn", "macdup", "macddn", "converge"]].any(axis=1))
    d = P[base]
    for ev, col in (("gc", "net60"), ("dc", "net60"), ("x2050up", "net20"), ("x2050dn", "net20"), ("macdup", "net20"), ("macddn", "net20"), ("converge", "abs20")):
        key = f"STK|{ev}|{col}"
        cnt = _period_counts(P["date"], P[ev])
        if counts_only:
            out[key] = cnt
            continue
        r = ts.level(d, d[ev], col)
        r["extra"] = {**r["extra"], **cnt}
        out[key] = r
    for state, mask in (("uptrend", P["nifty_vs200"] > 0), ("downtrend", P["nifty_below_both"].fillna(False).astype(bool))):
        key = f"STK|x2050up_{state}|net20"
        ev = P["x2050up"] & mask
        cnt = _period_counts(P["date"], ev)
        if counts_only:
            out[key] = cnt
            continue
        dd = P[base & mask]
        r = ts.level(dd, ev.reindex(dd.index), "net20")
        r["extra"] = {**r["extra"], **cnt}
        out[key] = r
    for ev, col in (("gc", "net60"), ("x2050up", "net20")):
        key = f"STK|{ev}|{col}|absolute"
        cnt = _period_counts(P["date"], P[ev])
        if counts_only:
            out[key] = cnt
            continue
        r = ts.absolute(P[P["liq"]], P[ev], col)
        r["extra"] = {**r["extra"], **cnt}
        out[key] = r
    return out


# ------------------------------------------------------------------------------------------------------------------------- FX1

def _usdinr_on_sessions(sessions: pd.DatetimeIndex) -> pd.DataFrame:
    m = pd.read_parquet(paths.data_dir() / "silver/macro/macro.parquet")
    m["date"] = pd.to_datetime(m["date"])
    u = m[(m["series"] == "DEXINUS") & (m["date"] < CUT)].dropna(subset=["value"]).sort_values("date").set_index("date")["value"]
    u = u[u > 0]
    f = pd.DataFrame(index=u.index)
    f["usdinr"] = u
    f["dep5"] = u / u.shift(5) - 1
    f["dep1"] = u / u.shift(1) - 1
    f["thr5"] = f["dep5"].rolling(756, min_periods=500).quantile(0.9)
    f["thr1"] = f["dep1"].rolling(756, min_periods=500).quantile(0.9)
    f["chg126"] = u / u.shift(126) - 1
    f["max3y_prev"] = u.rolling(756, min_periods=500).max().shift(1)
    idx = pd.DataFrame({"date": sessions, "known_by": sessions - pd.Timedelta(days=1)}).sort_values("known_by")
    j = pd.merge_asof(idx, f.reset_index().rename(columns={"date": "fdate"}).sort_values("fdate"), left_on="known_by", right_on="fdate",
                      direction="backward", tolerance=pd.Timedelta(days=7))
    return j.set_index("date").drop(columns=["known_by"])


def fx1_frame() -> pd.DataFrame:
    piv = ts.index_panel()
    n = piv["NIFTY 50"].dropna()
    n = n[n.index < CUT]
    M = pd.DataFrame(index=n.index)
    M["date"] = n.index
    for k in (5, 20, 21, 63):
        M[f"nfwd{k}"] = ts._fwd_close(n, k)
    for tag, name in (("bank", "NIFTY BANK"), ("it", "NIFTY IT"), ("pharma", "NIFTY PHARMA")):
        s = piv[name].reindex(n.index)
        M[f"{tag}fwd20"] = ts._fwd_close(s, 20)
    M["itx20"] = M["itfwd20"] - M["nfwd20"]
    M["pharmax20"] = M["pharmafwd20"] - M["nfwd20"]
    U = _usdinr_on_sessions(n.index)
    M = M.join(U)
    M["ok_dep"] = M["dep5"].notna() & M["thr5"].notna()
    M["ok_dep1"] = M["dep1"].notna() & M["thr1"].notna()
    M["ok_126"] = M["chg126"].notna()
    M["ok_3y"] = M["max3y_prev"].notna()
    M["weak5"] = (M["dep5"] >= M["thr5"]) & M["ok_dep"]
    M["weak1"] = (M["dep1"] >= M["thr1"]) & M["ok_dep1"]
    M["h42_up5"] = (M["chg126"] >= 0.05) & M["ok_126"]
    M["h42_break3y"] = (M["usdinr"] > M["max3y_prev"]) & M["ok_3y"]
    return M


def fx1_results(counts_only: bool = False) -> dict:
    M = fx1_frame()
    plan = [("weak5", "nfwd5", 5, "ok_dep"), ("weak5", "nfwd20", 20, "ok_dep"), ("weak5", "bankfwd20", 20, "ok_dep"), ("weak5", "itx20", 20, "ok_dep"),
            ("weak5", "pharmax20", 20, "ok_dep"), ("weak1", "nfwd5", 5, "ok_dep1"), ("h42_up5", "nfwd21", 21, "ok_126"), ("h42_up5", "nfwd63", 63, "ok_126"),
            ("h42_break3y", "nfwd21", 21, "ok_3y"), ("h42_break3y", "nfwd63", 63, "ok_3y")]
    out = {}
    for ev, col, h, ok in plan:
        key = f"{ev}|{col}"
        cnt = {**_period_counts(M["date"], M[ev]), "base_sessions": int(M[ok].sum())}
        if counts_only:
            out[key] = cnt
            continue
        r = ts.msplit(M, M[ev], col, h=h, base=M[ok])
        r["extra"] = {**r["extra"], **cnt}
        out[key] = r
    return out


# ------------------------------------------------------------------------------------------------------------------------- FII1

def fii1_frame() -> pd.DataFrame:
    piv = ts.index_panel()
    n = piv["NIFTY 50"].dropna()
    n = n[n.index < CUT]
    fl = pd.read_parquet(paths.data_dir() / "silver/flows/fii_dii_cash.parquet")
    fl["date"] = pd.to_datetime(fl["date"])
    fl = fl[(fl["category"] == "FPI_equity") & (fl["date"] < CUT)].groupby("date")["net_cr"].sum().sort_index()
    sess = n.index.values
    pos = np.searchsorted(sess, fl.index.values, side="left")          # the first Nifty session on or after the reporting date
    keep = pos < len(sess)
    daily = pd.Series(fl.values[keep], index=pd.DatetimeIndex(sess[pos[keep]])).groupby(level=0).sum().reindex(n.index)
    M = pd.DataFrame(index=n.index)
    M["date"] = n.index
    M["net1"] = daily
    M["net5"] = daily.rolling(5, min_periods=4).sum()
    for col in ("net1", "net5"):
        M[f"{col}_lo"] = M[col].rolling(756, min_periods=500).quantile(0.1)
        M[f"{col}_hi"] = M[col].rolling(756, min_periods=500).quantile(0.9)
    M["ok1"] = M["net1"].notna() & M["net1_lo"].notna()
    M["ok5"] = M["net5"].notna() & M["net5_lo"].notna()
    M["neg1"] = (M["net1"] <= M["net1_lo"]) & M["ok1"]
    M["pos1"] = (M["net1"] >= M["net1_hi"]) & M["ok1"]
    M["neg5"] = (M["net5"] <= M["net5_lo"]) & M["ok5"]
    M["pos5"] = (M["net5"] >= M["net5_hi"]) & M["ok5"]
    for k in (1, 5, 20):
        M[f"nfwd{k}"] = ts._fwd_close(n, k)
    M["ret0"] = n.pct_change()
    return M


def fii1_results(counts_only: bool = False) -> dict:
    M = fii1_frame()
    plan = [("neg5", "nfwd1", 1, "ok5"), ("neg5", "nfwd5", 5, "ok5"), ("neg5", "nfwd20", 20, "ok5"), ("neg1", "nfwd1", 1, "ok1"), ("neg1", "nfwd5", 5, "ok1"),
            ("pos5", "nfwd5", 5, "ok5"), ("pos5", "nfwd20", 20, "ok5"), ("pos1", "nfwd1", 1, "ok1")]
    out = {}
    for ev, col, h, ok in plan:
        key = f"{ev}|{col}"
        cnt = {**_period_counts(M["date"], M[ev]), "base_sessions": int(M[ok].sum())}
        if counts_only:
            out[key] = cnt
            continue
        r = ts.msplit(M, M[ev], col, h=h, base=M[ok])
        r["extra"] = {**r["extra"], **cnt}
        out[key] = r
    return out


def fii_beta() -> dict:
    """TWT-H48, descriptive: the same-day sensitivity of the Nifty's return to the FPI net flow, the flow in units of its trailing 252-session
    standard deviation (known before the day), by year; correlations at lags -1/0/+1 show whether flows follow the price or lead it."""
    M = fii1_frame()
    z = M["net1"] / M["net1"].rolling(252, min_periods=200).std().shift(1)
    D = pd.DataFrame({"r": M["ret0"], "z": z, "r_prev": M["ret0"].shift(1), "r_next": M["ret0"].shift(-1), "y": M.index.year}).dropna()
    rows = {}
    for y, g in D.groupby("y"):
        if len(g) < 100:
            continue
        b = float(np.cov(g["r"], g["z"])[0, 1] / np.var(g["z"], ddof=1))
        rows[int(y)] = {"beta_pct_per_sd": round(100 * b, 3), "corr_same_day": round(float(g["r"].corr(g["z"])), 3),
                        "corr_flow_vs_previous_day_return": round(float(g["r_prev"].corr(g["z"])), 3),
                        "corr_flow_vs_next_day_return": round(float(g["r_next"].corr(g["z"])), 3), "days": int(len(g))}
    pre = [v["beta_pct_per_sd"] for k, v in rows.items() if k <= 2016]
    post = [v["beta_pct_per_sd"] for k, v in rows.items() if k >= 2017]
    t = None
    if len(pre) > 2 and len(post) > 2:
        se = math.sqrt(np.var(pre, ddof=1) / len(pre) + np.var(post, ddof=1) / len(post))
        t = round((np.mean(post) - np.mean(pre)) / se, 2) if se else None
    return {"by_year": rows, "pre_2003_2016_mean_beta": round(float(np.mean(pre)), 3) if pre else None,
            "post_2017_2023_mean_beta": round(float(np.mean(post)), 3) if post else None, "welch_t_post_minus_pre_yearly": t,
            "note": "descriptive only (same-day; not a trading rule, not a registered verdict); beta = Nifty % move per one trailing-SD of FPI net flow"}


# ------------------------------------------------------------------------------------------------------------------------- SR1

PIVOT = 5          # the technicals panel's swing rule (india/technicals.py PIVOT, SR_WINDOW): 5 bars each side, levels from the last 60 sessions


def _levels(h: np.ndarray, l: np.ndarray, c: np.ndarray, w: int, k: int = PIVOT) -> tuple[np.ndarray, np.ndarray]:
    """Support and resistance as of the previous session for every row of one continuous run, exactly as india.technicals.panel finds them on the
    bars up to yesterday: swing points whose bar lies in [t - w, t - k - 1] (so confirmed by yesterday), S = the highest swing low below
    yesterday's close, R = the lowest swing high above it. Rows before the w-th of the run get no level."""
    from numpy.lib.stride_tricks import sliding_window_view as swv

    n = len(c)
    S, R = np.full(n, np.nan), np.full(n, np.nan)
    if n <= w or w - k < 1:
        return S, R
    ctr = np.arange(k, n - k)
    lw, hw = swv(l, 2 * k + 1).min(axis=1), swv(h, 2 * k + 1).max(axis=1)
    pl, ph = np.full(n, np.nan), np.full(n, np.nan)
    pl[ctr] = np.where(l[ctr] == lw, l[ctr], np.nan)
    ph[ctr] = np.where(h[ctr] == hw, h[ctr], np.nan)
    t = np.arange(w, n)
    VL, VH = swv(pl, w - k)[t - w], swv(ph, w - k)[t - w]          # pivot bars t-w .. t-k-1
    cp = c[t - 1][:, None]
    with np.errstate(invalid="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)          # an all-empty window is a row with no level (NaN), not an error
        S[t] = np.nanmax(np.where(VL < cp, VL, np.nan), axis=1)
        R[t] = np.nanmin(np.where(VH > cp, VH, np.nan), axis=1)
    return S, R


def _sr_stock_frame() -> pd.DataFrame:
    cols = ["sid", "date", "n", "liq_rank", "h", "l", "c", "fwd20", "net20"]
    P = pd.read_parquet(paths.gold() / "teachers" / "stock_panel.parquet", columns=cols)
    P["date"] = pd.to_datetime(P["date"])
    P = P[P["date"] < CUT].sort_values(["sid", "date"]).reset_index(drop=True)
    consec = (P["sid"] == P["sid"].shift(1)) & (P["n"] == P["n"].shift(1) + 1)
    seg = (~consec).cumsum().values
    h, l, c = (P[x].astype(float).values for x in ("h", "l", "c"))
    out = {w: (np.full(len(P), np.nan), np.full(len(P), np.nan)) for w in (20, 60)}
    bounds = np.flatnonzero(np.diff(seg)) + 1
    for a, b in zip(np.r_[0, bounds], np.r_[bounds, len(P)]):
        if b - a <= 20:
            continue
        for w in (20, 60):
            s, r = _levels(h[a:b], l[a:b], c[a:b], w)
            out[w][0][a:b], out[w][1][a:b] = s, r
    cprev = pd.Series(c).shift(1).where(consec).values
    liq = (P["liq_rank"] <= 250).values
    with np.errstate(invalid="ignore"):
        for w in (20, 60):
            S, R = out[w]
            P[f"S{w}"], P[f"R{w}"] = S, R
            P[f"bounce{w}"] = (l <= S * 1.01) & (c >= S) & (c <= S * 1.015) & (c > cprev)
            P[f"break{w}"] = c > R
        P["breakdown60"] = c < out[60][0]
    for k in ("bounce20", "bounce60", "break20", "break60", "breakdown60"):
        P[k] = ts._cooldown(P, P[k].fillna(False).astype(bool) & liq, 10)
    P["liq"] = liq
    P["s5"] = ts.sample5(P)
    return P


def _sr_index_frame(name: str) -> pd.DataFrame:
    c = ts.index_panel()[name].dropna()
    c = c[c.index < CUT]
    v = c.astype(float).values
    S, R = _levels(v, v, v, 60)                    # closes stand in for highs and lows, as in the live panel
    M = pd.DataFrame(index=c.index)
    M["date"] = c.index
    M["fwd20"] = ts._fwd_close(c, 20)
    cp = c.shift(1).values
    M["ok"] = np.arange(len(c)) >= 60
    with np.errstate(invalid="ignore"):
        M["bounce60"] = _cool(pd.Series((cp <= S * 1.01) & (v > cp) & (v >= S) & (v <= S * 1.015), index=c.index), 10)
        M["break60"] = _cool(pd.Series(v > R, index=c.index), 10)
    return M


def sr1_results(counts_only: bool = False) -> dict:
    out = {}
    for tag, name in (("NIFTY", "NIFTY 50"), ("BANK", "NIFTY BANK")):
        M = _sr_index_frame(name)
        for ev in ("bounce60", "break60"):
            key = f"{tag}|{ev}|fwd20"
            cnt = _period_counts(M["date"], M[ev] & M["ok"])
            if counts_only:
                out[key] = cnt
                continue
            r = ts.msplit(M, M[ev], "fwd20", h=20, base=M["ok"])
            r["extra"] = {**r["extra"], **cnt}
            out[key] = r
    P = _sr_stock_frame()
    evs = ["bounce20", "bounce60", "break20", "break60", "breakdown60"]
    base = P["liq"] & (P["s5"] | P[evs].any(axis=1))
    d = P[base]
    for ev in evs:
        key = f"STK|{ev}|net20"
        cnt = _period_counts(P["date"], P[ev])
        if counts_only:
            out[key] = cnt
            continue
        r = ts.level(d, d[ev], "net20")
        r["extra"] = {**r["extra"], **cnt}
        out[key] = r
    for ev in ("bounce60", "break60"):
        key = f"STK|{ev}|net20|absolute"
        cnt = _period_counts(P["date"], P[ev])
        if counts_only:
            out[key] = cnt
            continue
        r = ts.absolute(P[P["liq"]], P[ev], "net20")
        r["extra"] = {**r["extra"], **cnt}
        out[key] = r
    return out


# ------------------------------------------------------------------------------------------------------------------------- run

FUNCS = {"XO1": xo1_results, "FX1": fx1_results, "FII1": fii1_results, "SR1": sr1_results}


def check(study: str) -> dict:
    return FUNCS[study](counts_only=True)


def run(study: str) -> dict:
    s = spec(study)
    k = int(s["bar"]["union_k"])
    if abs(registry.threshold(k) - float(s["bar"]["z"])) > 0.01:
        raise ValueError(f"{study}: the spec's z {s['bar']['z']} does not match k {k}")
    reg = registry.register(study, family=s["family"], title=s["title"], hypothesis=s["hypothesis"], variants=list(s["variants"]),
                            note=f"spec india/registrations/{study.lower()}_v1.json (written before the run)", bar_families=s["bar"].get("bar_families"),
                            union_k=k)
    res = FUNCS[study]()
    rows = []
    for var, expect in s["variants"].items():
        r = res.get(var)
        if r is None:
            line = registry.record(reg, var, (float("nan"), float("nan"), 0), (float("nan"), float("nan"), 0), extra={"missing": True}, expect=expect)
        else:
            line = registry.record(reg, var, tuple(r["dev"]), tuple(r["val"]), extra=_clean(r.get("extra", {})), expect=expect)
        rows.append({"variant": var, "expect": expect, "verdict": line["verdict"], "z": line["z"], "dev": _clean(list(line["dev"])),
                     "val": _clean(list(line["val"])), "extra": _clean(line["extra"])})
    out = {"study": study, "registered_at": reg["at"], "k": k, "rows": rows}
    if study == "FII1":
        out["twt_h48_descriptive"] = fii_beta()
    (paths.manifest_dir() / f"xstudies_{study.lower()}.json").write_text(json.dumps(out, indent=1, default=str))
    _table(study, out)
    return out


# My reading of the 26 Oct run, in plain words (written after the results; the numbers are in the tables below each)
TAKEAWAY = {
    "XO1": [
        "**Crossovers are not a buy call here. Nothing reached the bar (z 3.11), and on stocks the classic buy crosses did slightly WORSE than ordinary days.**",
        "- **Stocks, 50/200 golden cross (2,557 events in 2000-17, 936 in 2018-23):** the next 60 sessions were about 2.7% worse than an ordinary day in "
        "the same quarter, in both periods (t -2.6 and -2.2): OPPOSITE. The cross comes after the move.",
        "- **Stocks, 20/50 upward cross (10,551 / 3,892 events):** about 0.5-0.7% worse over 20 sessions: OPPOSITE. Taken as a trade after costs, golden "
        "and 20/50 crosses earned about zero (REJECTED).",
        "- **Stocks, death cross and 20/50 downward cross:** no difference from ordinary days (REJECTED).",
        "- **MACD signal-line crosses:** upward crosses are no help on stocks, Nifty or Bank Nifty (REJECTED). Downward crosses on stocks were "
        "weaker in 2000-17 (t -2.8) but not in 2018-23 (INCONCLUSIVE).",
        "- **Index 50/200 crosses:** there were only 8 golden and 8 death crosses on the Nifty in 2003-17, and 5 each in 2018-23 (Bank Nifty about the same), "
        "far too few to judge: INCONCLUSIVE. The 20/50 crosses (about 34 and 14) are also INCONCLUSIVE.",
        "- **Holding the Nifty only while the 50-day is above the 200-day:** not better. In 2018-23 the next 20 sessions were weaker in that state "
        "(t -2.4, only 10 blocks): INCONCLUSIVE.",
        "- **Averages converging (20, 50 and 200-day within 2%):** on stocks it was followed by SMALLER moves, not bigger ones (t -2.8 and -2.9): "
        "OPPOSITE. It marks a quiet stock that stays quiet.",
        "- **What Ananta does with this:** nothing changes in the paper rules. Crossovers stay a description of the trend, never a reason to buy.",
    ],
    "FX1": [
        "**The rupee moves tell us nothing useful about the next weeks of Indian stocks.**",
        "- **Sharp weak-rupee weeks (443 sessions in 2003-17, 158 in 2018-23) and days (440 / 139):** no effect on the Nifty or Bank Nifty over 5 and "
        "20 sessions, and no edge for IT or Pharma over the Nifty. Every row is REJECTED (largest |t| 1.4).",
        "- **TWT-H42 restated on the rupee (a 5% weaker rupee over 126 sessions, or a 3-year high in USD/INR):** these states last for months, so "
        "there are too few independent quarters (23 and 10; 9 and 11): INCONCLUSIVE. Where there is a reading it points the other way: in 2018-23 "
        "the Nifty's next 21 sessions were about 4% BETTER after a weak-rupee stretch (t 2.8, 10 blocks).",
        "- **Data:** the USD/INR series (FRED DEXINUS) was already in the macro table from 1990, so no new download was needed.",
    ],
    "FII1": [
        "**Foreign investor flows, as NSDL reports them, do not predict the Nifty's next 1, 5 or 20 sessions.**",
        "- **Sharp outflow days (442 in 2003-17, 221 in 2018-23) and weeks (464 / 209):** the Nifty did no worse afterwards (REJECTED, every |t| under 1.4).",
        "- **Sharp inflow days (408 / 208) and weeks (407 / 202):** the Nifty did no better (REJECTED).",
        "- **TWT-H48 (descriptive):** the day's flow barely moves with the same day's Nifty: 0.04% per standard deviation of flow before 2017, "
        "0.05% after, with no change across the SIP era (t 0.2).",
        "- **Flows follow the price:** most years the flow correlates 0.2-0.46 with the PREVIOUS session's Nifty return and about zero with the next "
        "one. Part of this is NSDL's reporting date sitting a day after the trade, but either way the flows trail the market rather than lead it.",
    ],
    "SR1": [
        "**Support and resistance are not an entry signal here. Nothing reached the bar (z 3.21), and on stocks a close through resistance did WORSE than "
        "ordinary days.** The levels are the technicals panel's own (swing points with 5 bars each side; checked to match it exactly).",
        "- **Stocks, breakout above 60-session resistance (35,883 events in 2000-17, 13,411 in 2018-23):** the next 20 sessions were about 0.95% worse "
        "than an ordinary day in the same quarter in 2000-17 and 0.54% worse in 2018-23 (t -4.6 and -2.9): OPPOSITE. Over 20-session resistance "
        "(23,226 / 8,521): about 1.1% and 0.5% worse (t -4.3 and -2.0): OPPOSITE. As a trade after costs the breakout earned about zero (REJECTED).",
        "- **Stocks, bounce off support (touched it and closed up within 1.5% above):** no edge over ordinary days, from 60-session support "
        "(10,946 / 5,102: +0.1% and +0.2%, t 0.6 and 0.8) or 20-session support (5,001 / 2,355). As a trade the 60-session bounce made about +0.9% "
        "after costs in both periods, which is the market's own drift, not significant (t 1.5 and 1.0): REJECTED.",
        "- **Stocks, close below 60-session support (31,331 / 11,514):** not followed by weaker returns (REJECTED).",
        "- **Nifty and Bank Nifty, bounce off and break through 60-session levels:** no difference from other sessions (REJECTED, every |t| under 1.2).",
        "- **What Ananta does with this:** nothing changes in the paper rules. Support and resistance stay a description of where the price has turned "
        "before, never a reason to buy; a close through resistance is, if anything, a reason not to chase (as TWT-H10 'don't chase' found).",
    ],
}


def _f(x, pct: bool = True) -> str:
    if x is None or (isinstance(x, float) and x != x):
        return "n/a"
    return f"{100 * x:+.2f}%" if pct else f"{x:+.2f}"


def _table(study: str, out: dict) -> Path:
    s = spec(study)
    L = [f"# {study} results: {s['title']}", "", f"Registered {out['registered_at']} (spec `{study.lower()}_v1.json`, written before the run); "
         f"family {s['family']}, k = {out['k']}, z = {registry.threshold(out['k']):.2f}. Development to 2017, validation 2018-2023; nothing from 2024 on.", ""]
    if TAKEAWAY.get(study):
        L += ["## In plain words", ""] + TAKEAWAY[study] + ["", "## The rows", ""]
    L += ["Verdicts: VALIDATED and CONDITIONAL would be passes; OPPOSITE means significantly the other way round in 2000/2003-2017 and the same way in 2018-23; "
          "INCONCLUSIVE means too few independent blocks (16 needed per period) or a reading below the bar.", "",
         "| variant | expected | verdict | dev mean | dev t | dev blocks | val mean | val t | val blocks | events dev / val |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in out["rows"]:
        e = r["extra"] or {}
        d, v = r["dev"], r["val"]
        L.append(f"| {r['variant']} | {'+' if r['expect'] > 0 else '-'} | {r['verdict']} | {_f(d[0])} | {_f(d[1], False)} | {d[2]} | {_f(v[0])} | {_f(v[1], False)} | {v[2]} | "
                 f"{e.get('events_dev', 'n/a')} / {e.get('events_val', 'n/a')} |")
    if out.get("twt_h48_descriptive"):
        h = out["twt_h48_descriptive"]
        L += ["", "## TWT-H48, descriptive: how much the Nifty moves with same-day FPI flows", "",
              f"Mean yearly beta (Nifty % move per one trailing standard deviation of the day's FPI net flow): 2003-2016 {h['pre_2003_2016_mean_beta']}, "
              f"2017-2023 {h['post_2017_2023_mean_beta']} (Welch t across years {h['welch_t_post_minus_pre_yearly']}).", "",
              "| year | beta % per SD | corr same day | corr with previous day's return | corr with next day's return | days |", "|---|---|---|---|---|---|"]
        for y, v in sorted(h["by_year"].items()):
            L.append(f"| {y} | {v['beta_pct_per_sd']} | {v['corr_same_day']} | {v['corr_flow_vs_previous_day_return']} | {v['corr_flow_vs_next_day_return']} | {v['days']} |")
    p = REG_DIR / f"{study.lower()}_results_v1.md"
    p.write_text("\n".join(L) + "\n")
    return p


def main(argv: list[str]) -> None:
    cmd = argv[1] if len(argv) > 1 else "check"
    which = argv[2] if len(argv) > 2 else "all"
    studies = list(FUNCS) if which == "all" else [which]
    for st in studies:
        if cmd == "check":
            print(st, json.dumps(check(st)), flush=True)
        elif cmd == "run":
            o = run(st)
            for r in o["rows"]:
                print(st, r["variant"], r["verdict"], r["dev"], r["val"], flush=True)
        elif cmd == "report":                       # re-render the results page from the saved run (no new ledger rows)
            print(_table(st, json.loads((paths.manifest_dir() / f"xstudies_{st.lower()}.json").read_text())))


if __name__ == "__main__":
    paths.ensure()
    main(sys.argv)
