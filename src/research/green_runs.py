"""Green-run journal v1 (GR1). Pre-registration: docs/research/GREEN_RUNS_STUDY_V1.md.

5m runs of k = 2..5 consecutive green candles (plus a k=0 every-6th-bar baseline), their context from
closed higher-timeframe bars, three entry regions and four exits, net of NDAX / zero-fee / Kraken costs.

    python -m src.research.green_runs events --db LAB --out DIR          # per-coin event files (DISCOVERY + CONFIRM only)
    python -m src.research.green_runs cells --out DIR                    # journal + every cell, pass flags
    python -m src.research.green_runs reference --db FRESH10 --out DIR2 --cells DIR/cells_pass.csv

HOLDOUT (from 2026-08-01) is never simulated.
"""
from __future__ import annotations

import argparse
import itertools
import json
import os
import sqlite3
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:  # the laptop research venv has numba; without it the same code runs as plain Python (tests)
    from numba import njit
except ImportError:  # pragma: no cover
    def njit(*a, **k):
        if a and callable(a[0]):
            return a[0]
        return lambda f: f

VERSION = "green.runs.v1"
LAB10 = ["BTC", "ETH", "SOL", "ADA", "DOGE", "AVAX", "BCH", "LINK", "LTC", "XRP"]
FRESH10 = ["DOT", "ETC", "NEAR", "UNI", "XLM", "ALGO", "AAVE", "FIL", "ATOM", "TRX"]
DISC_END = 1704067200       # 2024-01-01
CONF_END = 1785542400       # 2026-08-01, HOLDOUT starts here and is never simulated
KS = (0, 2, 3, 4, 5)
ENTRIES = ("NOW", "PB25", "PB50")
EXITS = ("B1", "B2", "B3", "B4")
EXIT_PARAMS = {"B1": (0.015, 0.010, 48), "B2": (0.03, 0.015, 288), "B3": (0.05, 0.025, 864), "B4": (0.0, 0.0, 288)}
HALF_SPREAD = {"BTC": 0.00178, "ETH": 0.00084, "SOL": 0.00289, "ADA": 0.00273, "DOGE": 0.00307,
               "AVAX": 0.00370, "BCH": 0.00400, "LINK": 0.00341, "LTC": 0.00334, "XRP": 0.00251}
FRESH_HS = 0.0040
COSTS = ("NDAX_NOW", "ZERO_FEE", "KRAKEN_T1")
FEATURES = {  # name -> value labels (codes are the index)
    "trend_1d": ("DOWN", "FLAT", "UP"), "trend_4h": ("DOWN", "FLAT", "UP"), "trend_1h": ("DOWN", "FLAT", "UP"),
    "btc_4h": ("DOWN", "FLAT", "UP"), "vol_prior": ("LOW", "NORMAL", "HIGH"), "squeeze": ("NO", "YES"),
    "run_vol": ("NORMAL", "EXPANDING"), "rsi5": ("<50", "50-70", ">70"), "origin": ("OTHER", "FROM_4H_LOW"),
    "run_size": ("SMALL", "MEDIUM", "LARGE"), "session": ("0-8", "8-16", "16-24"),
}
FEAT = list(FEATURES)
KIND_TARGET, KIND_STOP, KIND_TIME = 0, 1, 2


# ---------------------------------------------------------------------------
# Data and indicators
# ---------------------------------------------------------------------------
def load_5m(db: str, coin: str) -> dict[str, np.ndarray]:
    con = sqlite3.connect(f"file:{os.path.expanduser(db)}?mode=ro", uri=True)
    try:
        a = np.array(con.execute(
            "SELECT event_unix, open, high, low, close, volume FROM bars WHERE instrument=? AND event_unix < ? ORDER BY event_unix",
            (f"{coin}-USD-SPOT", CONF_END)).fetchall(), dtype=float)
    finally:
        con.close()
    if a.size == 0:
        return {}
    return {"t": a[:, 0].astype(np.int64), "o": a[:, 1], "h": a[:, 2], "l": a[:, 3], "c": a[:, 4], "v": a[:, 5]}


def resample(b: dict[str, np.ndarray], step: int) -> dict[str, np.ndarray]:
    """UTC-aligned complete buckets only; 'tc' = bucket close time."""
    need = step // 300
    key = b["t"] - (b["t"] % step)
    starts = np.flatnonzero(np.r_[True, key[1:] != key[:-1]])
    counts = np.diff(np.r_[starts, len(key)])
    c = b["c"][np.r_[starts[1:], len(key)] - 1]
    ok = counts == need
    k = key[starts][ok]
    return {"t": k, "tc": k + step, "c": c[ok]}


def ema(x: np.ndarray, n: int) -> np.ndarray:
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy()


def atr(h, lo, c, n: int = 14) -> np.ndarray:
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - lo, np.maximum(np.abs(h - pc), np.abs(lo - pc)))
    return pd.Series(tr).ewm(alpha=1.0 / n, adjust=False).mean().to_numpy()


def rsi(c: np.ndarray, n: int = 14) -> np.ndarray:
    d = np.diff(c, prepend=c[0])
    up = pd.Series(np.maximum(d, 0)).ewm(alpha=1.0 / n, adjust=False).mean().to_numpy()
    dn = pd.Series(np.maximum(-d, 0)).ewm(alpha=1.0 / n, adjust=False).mean().to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(dn > 0, 100 - 100 / (1 + up / dn), 100.0)


def htf_trend_at(b: dict[str, np.ndarray], step: int, t_close: np.ndarray, warm: int = 50) -> tuple[np.ndarray, np.ndarray]:
    """Trend code (0 down, 1 flat, 2 up) of the last bar of `step` CLOSED at or before each time; validity."""
    r = resample(b, step)
    if len(r["c"]) == 0:
        return np.ones(len(t_close), dtype=np.int8), np.zeros(len(t_close), dtype=bool)
    e20, e50 = ema(r["c"], 20), ema(r["c"], 50)
    tr = np.where((r["c"] > e50) & (e20 > e50), 2, np.where((r["c"] < e50) & (e20 < e50), 0, 1)).astype(np.int8)
    idx = np.searchsorted(r["tc"], t_close, side="right") - 1
    ok = idx >= 0
    safe = np.where(ok, idx, 0)
    ok &= (t_close - r["tc"][safe]) <= 2 * step
    ok &= safe >= warm
    return tr[safe], ok


def run_length(o: np.ndarray, c: np.ndarray) -> np.ndarray:
    g = (c > o).astype(np.int64)
    idx = np.arange(len(g))
    last_non = np.maximum.accumulate(np.where(g == 0, idx, -1))
    return np.where(g == 1, idx - last_non, 0)


# ---------------------------------------------------------------------------
# Events + context (uses only bars closed at or before each event bar)
# ---------------------------------------------------------------------------
def events_for(b: dict[str, np.ndarray], btc: dict[str, np.ndarray] | None) -> pd.DataFrame:
    t, o, h, lo, c, v = b["t"], b["o"], b["h"], b["l"], b["c"], b["v"]
    n = len(c)
    tc5 = t + 300
    r = run_length(o, c)
    base = (np.arange(n) % 6 == 0)
    kk = np.where(np.isin(r, (2, 3, 4, 5)), r, np.where(base, 0, -1))
    ev = np.flatnonzero(kk >= 0)
    k = kk[ev]
    s = np.where(k > 0, ev - k + 1, ev)  # run start (baseline: the bar itself)
    # contiguity s-288 .. i
    gap = np.r_[0, (np.diff(t) != 300).astype(np.int64)]
    cg = np.cumsum(gap)
    lo_i = s - 288
    ok = (lo_i >= 0) & (ev + 1 < n)
    lo_safe = np.maximum(lo_i, 0)
    ok &= cg[ev] - cg[lo_safe] == 0
    # higher-timeframe trends at the event close
    tcl = tc5[ev]
    f: dict[str, np.ndarray] = {}
    for name, step in (("trend_1d", 86400), ("trend_4h", 14400), ("trend_1h", 3600)):
        f[name], okx = htf_trend_at(b, step, tcl)
        ok &= okx
    bt = btc if btc is not None else b
    f["btc_4h"], okb = htf_trend_at(bt, 14400, tcl)
    ok &= okb
    # volume / squeeze / momentum / origin / size at the run start (bars before s) and the event bar
    vs = pd.Series(v)
    m24 = vs.rolling(24).mean().shift(1).to_numpy()
    m288 = vs.rolling(288).mean().shift(1).to_numpy()
    m48 = vs.rolling(48).mean().shift(1).to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        vp = m24[s] / m288[s]
    f["vol_prior"] = np.where(vp < 0.7, 0, np.where(vp > 1.3, 2, 1)).astype(np.int8)
    csum_v = np.r_[0.0, np.cumsum(v)]
    runv = (csum_v[ev + 1] - csum_v[s]) / (ev - s + 1)
    with np.errstate(divide="ignore", invalid="ignore"):
        f["run_vol"] = ((runv / m48[s]) >= 1.5).astype(np.int8)
    sma = pd.Series(c).rolling(20).mean().to_numpy()
    sd = pd.Series(c).rolling(20).std(ddof=0).to_numpy()
    width = 4 * sd / sma
    q20 = pd.Series(width).rolling(288, min_periods=288).quantile(0.20).to_numpy()
    sm1 = np.maximum(s - 1, 0)
    f["squeeze"] = (width[sm1] <= q20[sm1]).astype(np.int8)
    r5 = rsi(c)[ev]
    f["rsi5"] = np.where(r5 < 50, 0, np.where(r5 <= 70, 1, 2)).astype(np.int8)
    ll48 = pd.Series(lo).rolling(48).min().shift(1).to_numpy()
    f["origin"] = (lo[s] <= ll48[s]).astype(np.int8)
    a5 = atr(h, lo, c)
    with np.errstate(divide="ignore", invalid="ignore"):
        rs = (c[ev] - o[s]) / a5[sm1]
    f["run_size"] = np.where(rs < 1, 0, np.where(rs <= 2, 1, 2)).astype(np.int8)
    f["session"] = (((tcl % 86400) // 3600) // 8).astype(np.int8)
    ok &= np.isfinite(vp) & np.isfinite(m48[s]) & np.isfinite(q20[sm1]) & np.isfinite(a5[sm1]) & np.isfinite(ll48[s])
    df = pd.DataFrame({"i": ev, "s": s, "k": k.astype(np.int8), "t_close": tcl, **f})
    df = df[ok].reset_index(drop=True)
    df["split"] = np.where(df["t_close"] <= DISC_END, 0, 1).astype(np.int8)
    df = df[df["t_close"] <= CONF_END].reset_index(drop=True)  # an event must close before HOLDOUT
    return df


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------
@njit(cache=True)
def _sim_one(o, h, lo, c, i, s, entry, ex, run_low):
    """Returns (gross, entry_kind(0 market,1 limit), exit_kind, filled). Pessimistic intrabar order."""
    n = len(c)
    if entry == 0:
        j = i + 1
        P = o[j]
        ek = 0
        fill_intrabar = False
    else:
        frac = 0.25 if entry == 1 else 0.50
        L = c[i] - frac * (c[i] - o[s])
        j = -1
        P = 0.0
        fill_intrabar = False
        for m in range(i + 1, min(i + 13, n)):
            if o[m] <= L:
                j = m
                P = o[m]
                break
            if lo[m] <= L:
                j = m
                P = L
                fill_intrabar = True
                break
        if j < 0:
            return np.nan, 1, -1, 0
        ek = 1
    if ex == 3:
        S = run_low
        R = P - S
        if R <= 0.0 or R / P < 0.002:
            return np.nan, ek, -1, 1
        T = P + 2.0 * R
        H = 288
    elif ex == 0:
        T, S, H = P * 1.015, P * 0.990, 48
    elif ex == 1:
        T, S, H = P * 1.03, P * 0.985, 288
    else:
        T, S, H = P * 1.05, P * 0.975, 864
    end = j + H
    if end > n:
        return np.nan, ek, -1, 1
    for m in range(j, end):
        if m > j:  # a gap through a level fills at the open
            if o[m] <= S:
                return o[m] / P - 1.0, ek, 1, 1
            if o[m] >= T:
                return o[m] / P - 1.0, ek, 0, 1
        if lo[m] <= S:  # stop first when both are touched in one bar
            return S / P - 1.0, ek, 1, 1
        if h[m] >= T and not (m == j and fill_intrabar):
            return T / P - 1.0, ek, 0, 1
    return c[end - 1] / P - 1.0, ek, 2, 1


@njit(cache=True)
def _sim_all(o, h, lo, c, I, S, K, RL, entry, ex):
    m = len(I)
    g = np.full(m, np.nan)
    ek = np.zeros(m, np.int8)
    xk = np.full(m, -1, np.int8)
    for q in range(m):
        if K[q] == 0 and (entry != 0 or ex == 3):
            continue
        a, b_, x_, _f = _sim_one(o, h, lo, c, I[q], S[q], entry, ex, RL[q])
        g[q] = a
        ek[q] = b_
        xk[q] = x_
    return g, ek, xk


def cost_sides(coin: str, cost: str) -> tuple[float, float]:
    """(limit side, market side) cost fractions."""
    hs = HALF_SPREAD.get(coin, FRESH_HS)
    if cost == "NDAX_NOW":
        return 0.0020, 0.0020 + hs
    if cost == "ZERO_FEE":
        return 0.0, hs
    return 0.0040, 0.0080 + 0.0005


def net_of(g: np.ndarray, ek: np.ndarray, xk: np.ndarray, coin: str, cost: str) -> np.ndarray:
    lim, mkt = cost_sides(coin, cost)
    ec = np.where(ek == 1, lim, mkt)
    xc = np.where(xk == KIND_TARGET, lim, mkt)
    return (g - ec - (1 + g) * xc).astype(np.float32)


def forward_stats(b: dict[str, np.ndarray], ev: np.ndarray) -> dict[str, np.ndarray]:
    """From the NOW entry (open of i+1): return, best move up, worst move down over 1h / 4h / 24h."""
    o, h, lo, c = b["o"], b["h"], b["l"], b["c"]
    n = len(c)
    out: dict[str, np.ndarray] = {}
    P = o[np.minimum(ev + 1, n - 1)]
    hs, ls = pd.Series(h), pd.Series(lo)
    for lab, H in (("1h", 12), ("4h", 48), ("24h", 288)):
        mx = hs[::-1].rolling(H, min_periods=H).max()[::-1].to_numpy()  # max of h[j .. j+H-1]
        mn = ls[::-1].rolling(H, min_periods=H).min()[::-1].to_numpy()
        j = ev + 1
        endi = j + H - 1
        good = endi < n
        jj = np.minimum(j, n - 1)
        out[f"ret_{lab}"] = np.where(good, c[np.minimum(endi, n - 1)] / P - 1, np.nan).astype(np.float32)
        out[f"up_{lab}"] = np.where(good, mx[jj] / P - 1, np.nan).astype(np.float32)
        out[f"dn_{lab}"] = np.where(good, mn[jj] / P - 1, np.nan).astype(np.float32)
    return out


def run_coin(db: str, coin: str, out: str) -> dict[str, Any]:
    t0 = time.time()
    b = load_5m(db, coin)
    if not b:
        return {"coin": coin, "skipped": True}
    btc = load_5m(db, "BTC") if coin != "BTC" else None
    if btc is not None and not btc:
        btc = None
    df = events_for(b, btc)
    I, S = df["i"].to_numpy(np.int64), df["s"].to_numpy(np.int64)
    K = df["k"].to_numpy(np.int64)
    lo = b["l"]
    # run low: lowest low from s to i
    RL = _run_lows(lo, S, I)
    for ei, en in enumerate(ENTRIES):
        for xi, xn in enumerate(EXITS):
            g, ek, xk = _sim_all(b["o"], b["h"], lo, b["c"], I, S, K, RL, ei, xi)
            for cost in COSTS:
                df[f"{en}_{xn}_{cost}"] = net_of(g, ek, xk, coin, cost)
    for k_, v_ in forward_stats(b, I).items():
        df[k_] = v_
    nx = np.minimum(I + 1, len(b["c"]) - 1)
    df["next_green"] = (b["c"][nx] > b["o"][nx]).astype(np.int8)
    df["coin"] = coin
    df["year"] = pd.to_datetime(df["t_close"], unit="s").dt.year.astype(np.int16)
    df["day"] = (df["t_close"] // 86400).astype(np.int32)
    p = Path(os.path.expanduser(out)) / f"events_{coin}.pkl"
    df.to_pickle(p)
    return {"coin": coin, "events": int(len(df)), "by_k": {int(k): int(v) for k, v in df["k"].value_counts().items()},
            "secs": round(time.time() - t0, 1)}


@njit(cache=True)
def _run_lows(lo, S, I):
    out = np.empty(len(S))
    for q in range(len(S)):
        m = lo[S[q]]
        for x in range(S[q] + 1, I[q] + 1):
            if lo[x] < m:
                m = lo[x]
        out[q] = m
    return out


# ---------------------------------------------------------------------------
# Cells
# ---------------------------------------------------------------------------
def combos() -> list[tuple[str, str]]:
    return [(e, x) for e in ENTRIES for x in EXITS]


def specs() -> list[tuple[str, ...]]:
    return [()] + [(f,) for f in FEAT] + list(itertools.combinations(FEAT, 2))


def _cell_stats(d: pd.DataFrame, keys: list[str], cols: list[str]) -> pd.DataFrame:
    """Per cell: n, mean, coin-day clustered t, coins positive, share of years positive; one row per cost column."""
    x = d.dropna(subset=[cols[0]])  # the NaN pattern is the same for every cost of one entry/exit
    if x.empty:
        return pd.DataFrame()
    out = []
    g0 = x.groupby(keys + ["coin", "day"], sort=False, observed=True)
    cnt = g0[cols[0]].count().rename("count")
    for col in cols:
        g = pd.concat([g0[col].sum().rename("sum"), cnt], axis=1).reset_index()
        tot = g.groupby(keys, observed=True).agg(S=("sum", "sum"), n=("count", "sum"), G=("sum", "size")).reset_index()
        g = g.merge(tot[keys + ["S", "n"]], on=keys)
        g["dev2"] = (g["sum"] - g["count"] * g["S"] / g["n"]) ** 2
        tot = tot.merge(g.groupby(keys, observed=True)["dev2"].sum().rename("var").reset_index(), on=keys)
        tot["mean"] = tot["S"] / tot["n"]
        se = np.sqrt(tot["var"] * tot["G"] / np.maximum(tot["G"] - 1, 1)) / tot["n"]
        tot["t"] = np.where(se > 0, tot["mean"] / se, 0.0)
        lv = list(range(len(keys)))
        pc = x.groupby(keys + ["coin"], observed=True)[col].mean().gt(0).groupby(level=lv).sum().rename("coins_pos")
        py = x.groupby(keys + ["year"], observed=True)[col].mean().gt(0).groupby(level=lv).mean().rename("years_pos")
        tot = tot.set_index(keys).join(pc).join(py).reset_index()
        tot["cost"] = col.split("_", 2)[2]  # "NOW_B1_NDAX_NOW" -> "NDAX_NOW"
        out.append(tot[keys + ["cost", "n", "mean", "t", "coins_pos", "years_pos"]])
    return pd.concat(out, ignore_index=True)


def cells_for_combo(pkl_dir: str, entry: str, exit_: str) -> pd.DataFrame:
    cols = [f"{entry}_{exit_}_{c}" for c in COSTS]
    parts = []
    for p in sorted(Path(pkl_dir).glob("events_*.pkl")):
        e = pd.read_pickle(p)
        parts.append(e[["k", "split", "coin", "day", "year"] + FEAT + cols])
        del e
    d = pd.concat(parts, ignore_index=True)
    if entry != "NOW" or exit_ == "B4":
        d = d[d["k"] > 0]
    rows = []
    for sp in specs():
        keys = ["k", "split"] + list(sp)
        st = _cell_stats(d, keys, cols)
        if st.empty:
            continue
        st["f1"] = sp[0] if len(sp) > 0 else ""
        st["v1"] = st[sp[0]].map(lambda z, f=sp[0]: FEATURES[f][int(z)]) if len(sp) > 0 else ""
        st["f2"] = sp[1] if len(sp) > 1 else ""
        st["v2"] = st[sp[1]].map(lambda z, f=sp[1]: FEATURES[f][int(z)]) if len(sp) > 1 else ""
        st = st.drop(columns=list(sp))
        st["entry"], st["exit"] = entry, exit_
        rows.append(st)
    return pd.concat(rows, ignore_index=True)


def wide(cells: pd.DataFrame) -> pd.DataFrame:
    key = ["cost", "entry", "exit", "k", "f1", "v1", "f2", "v2"]
    a = cells[cells["split"] == 0].drop(columns="split").set_index(key).add_prefix("d_")
    b = cells[cells["split"] == 1].drop(columns="split").set_index(key).add_prefix("c_")
    w = a.join(b, how="outer").reset_index()
    base = w[(w["k"] == 0) & (w["entry"] == "NOW")][["cost", "exit", "f1", "v1", "f2", "v2", "d_mean", "c_mean"]]
    base = base.rename(columns={"d_mean": "d_base", "c_mean": "c_base"})
    w = w.merge(base, on=["cost", "exit", "f1", "v1", "f2", "v2"], how="left")
    w["pass_discovery"] = ((w["d_n"] >= 300) & (w["d_mean"] > 0) & (w["d_t"] >= 3.5) & (w["d_coins_pos"] >= 6)
                           & (w["d_years_pos"] >= 0.6) & (w["k"] > 0) & (w["d_mean"] > w["d_base"].fillna(-9)))
    w["pass_confirm"] = (w["pass_discovery"] & (w["c_n"] >= 150) & (w["c_mean"] > 0) & (w["c_t"] >= 2.5)
                         & (w["c_coins_pos"] >= 6) & (w["c_mean"] > w["c_base"].fillna(-9)))
    return w


def journal(pkl_dir: str) -> dict[str, Any]:
    d = pd.concat([pd.read_pickle(p) for p in sorted(Path(pkl_dir).glob("events_*.pkl"))], ignore_index=True)
    out: dict[str, Any] = {}
    for sp, name in ((0, "DISCOVERY"), (1, "CONFIRM")):
        x = d[d["split"] == sp]
        rows = {}
        for k in KS:
            y = x[x["k"] == k]
            if y.empty:
                continue
            rows[str(k)] = {
                "n": int(len(y)), "p_next_green": round(float(y["next_green"].mean()), 4),
                **{f"mean_{c}_pct": round(100 * float(y[c].mean()), 3) for c in ("ret_1h", "ret_4h", "ret_24h")},
                **{f"median_{c}_pct": round(100 * float(y[c].median()), 3)
                   for c in ("up_1h", "dn_1h", "up_4h", "dn_4h", "up_24h", "dn_24h")},
                "fill_PB25": round(float(y["PB25_B2_NDAX_NOW"].notna().mean()), 3) if k else None,
                "fill_PB50": round(float(y["PB50_B2_NDAX_NOW"].notna().mean()), 3) if k else None,
            }
        out[name] = rows
    return out


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["events", "cells", "reference"])
    ap.add_argument("--db")
    ap.add_argument("--out", required=True)
    ap.add_argument("--coins", default=",".join(LAB10))
    ap.add_argument("--cells")
    ap.add_argument("--workers", type=int, default=5)
    a = ap.parse_args(argv)
    out = Path(os.path.expanduser(a.out))
    out.mkdir(parents=True, exist_ok=True)
    if a.cmd in ("events", "reference"):
        coins = a.coins.split(",") if a.cmd == "events" else FRESH10
        with ProcessPoolExecutor(max_workers=a.workers) as ex:
            res = list(ex.map(run_coin, [a.db] * len(coins), coins, [str(out)] * len(coins)))
        (out / "events_run.json").write_text(json.dumps({"version": VERSION, "coins": res}, indent=1))
        print(json.dumps(res, indent=1))
        if a.cmd == "events":
            return
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        parts = list(ex.map(cells_for_combo, [str(out)] * len(combos()), *zip(*combos())))
    cells = pd.concat(parts, ignore_index=True)
    w = wide(cells)
    w.to_csv(out / "cells.csv", index=False)
    j = journal(str(out))
    npass = {c: int(w[(w["cost"] == c) & w["pass_confirm"]].shape[0]) for c in COSTS}
    summary = {"version": VERSION, "cells_counted": int(len(w)), "pass_discovery": {c: int(w[(w["cost"] == c) & w["pass_discovery"]].shape[0]) for c in COSTS},
               "pass_confirm": npass, "journal": j}
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    w[w["pass_discovery"]].to_csv(out / "cells_pass.csv", index=False)
    print(json.dumps({k: summary[k] for k in ("cells_counted", "pass_discovery", "pass_confirm")}, indent=1))


if __name__ == "__main__":
    main()
