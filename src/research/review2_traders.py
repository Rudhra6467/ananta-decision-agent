"""Repair-shop review #2 (docs/repair_shop/REVIEW_2.md): learn from Hyperliquid traders' entries.

    python -m src.research.review2_traders context --db LAB5 --out DIR          # S1: engine state at every 15m scan
    python -m src.research.review2_traders analyze --db LAB5 --hl HL.sqlite --out DIR   # S2-S4: D1, D1b, D2, D3, D4

External trades are reference, never teacher: output is diagnostics + at most 5 candidate contexts.
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import os
import pickle
import sqlite3
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.intelligence import explorer_engine as xe
from src.research import explorer_replay as xr
from src.research import hl_bench as hb

CUT = 1785542400                       # 2026-08-01: entries after this are holdout, dropped
HORIZONS = {"1h": 3600, "4h": 14400, "24h": 86400, "5d": 432000}


# ---------------------------------------------------------------------------
# S1 context table
# ---------------------------------------------------------------------------
def context_coin(db: str, coin: str, out: str) -> dict:
    b5 = xr.load_5m(db, coin)
    bts, bctx = xr.btc_context(db) if coin != "BTC" else ([], [])
    import bisect

    def ctx(T):
        i = bisect.bisect_right(bts, T) - 1
        return bctx[i] if i >= 0 and T - bts[i] <= 7200 else {}

    eng = xe.CoinEngine(coin, btc_ctx=ctx)
    eng.random_rate = 0.0
    rows, ev, i = [], xr.event_stream(b5), 0
    while i < len(ev):
        T = ev[i][0]
        while i < len(ev) and ev[i][0] == T:
            eng.on_bar(ev[i][2], ev[i][3])
            i += 1
        if T % 900 == 0:
            rec = eng.scan(T)
            if "state" in rec:
                rows.append({"T": T, **rec["state"], "setups": ",".join(rec.get("setups") or [])})
            eng.trades, eng.orders, eng.closed, eng.missed, eng.actual_closed = [], [], [], [], []  # state only
    df = pd.DataFrame(rows)
    df.to_pickle(Path(out) / f"context_{coin}.pkl")
    return {"coin": coin, "scans": len(df)}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def bucket(df: pd.DataFrame) -> pd.DataFrame:
    """Categorical context features used by D2 / D4."""
    out = pd.DataFrame(index=df.index)
    for c in ("S1", "S2", "S3", "trend_4h", "daily_above_ema50", "btc_S1", "btc_S2", "contracted_now", "contracted_12h", "in_support"):
        out[c] = df[c].astype(str)
    out["rsi1h"] = pd.cut(df["rsi1h"], [-1, 40, 60, 101], labels=["<40", "40-60", ">60"]).astype(str)
    out["rsi15"] = pd.cut(df["rsi15"], [-1, 30, 70, 101], labels=["<30", "30-70", ">70"]).astype(str)
    out["momentum"] = pd.cut(df["roc_pct"].fillna(0.5), [-1, 0.3, 0.7, 2], labels=["low", "mid", "high"]).astype(str)
    out["vol1h"] = pd.cut(df["vol1h"].fillna(1.0), [-1, 0.8, 1.5, 1e9], labels=["quiet", "normal", "busy"]).astype(str)
    out["green_run"] = np.where(df["green_run_5m"].fillna(0) >= 3, ">=3", "<3")
    out["session"] = pd.cut(df["hour_utc"], [-1, 7, 15, 24], labels=["0-8", "8-16", "16-24"]).astype(str)
    return out


def clustered(x: np.ndarray, cl: np.ndarray) -> tuple[float, float, int]:
    """mean, t (clustered by cl), n."""
    ok = ~np.isnan(x)
    x, cl = x[ok], cl[ok]
    n = len(x)
    if n < 2:
        return float("nan"), 0.0, n
    m = x.mean()
    s = pd.Series(x - m).groupby(cl).sum().to_numpy()
    se = math.sqrt((s ** 2).sum()) / n
    return float(m), float(m / se) if se > 0 else 0.0, n


def load_trips(hl: str) -> tuple[pd.DataFrame, dict]:
    con = sqlite3.connect(f"file:{os.path.expanduser(hl)}?mode=ro", uri=True)
    acc = dict(con.execute("SELECT address, source FROM accounts").fetchall())
    rows, excluded = [], {}
    for a, src in acc.items():
        f = con.execute("SELECT time, coin, side, px, sz, start_pos, closed_pnl, fee FROM fills WHERE address=? ORDER BY time, tid", (a,)).fetchall()
        if not f:
            continue
        trips = hb.round_trips(f)
        beh = hb.behaviour(trips)
        if beh.get("trips", 0) and (beh["hold_h_median"] < 10 / 60 or beh["trips_per_week"] > 200):
            excluded[a[:10]] = {"source": src, "median_hold_h": beh["hold_h_median"], "trips_per_week": beh["trips_per_week"]}
            continue
        for t in trips:
            if t["coin"] in xe.COINS and t["open_ms"] / 1000 < CUT:
                rows.append({"address": a, "source": src, "coin": t["coin"], "t": int(t["open_ms"] // 1000), "dir": t["dir"],
                             "net": t["net"], "hold_h": t["hold_h"], "notional": t["max_notional"]})
    con.close()
    return pd.DataFrame(rows), excluded


def forward(db: str, trips: pd.DataFrame) -> pd.DataFrame:
    """Signed forward move after each entry and its excess over the coin-month average move (drift removed)."""
    out = []
    for coin, g in trips.groupby("coin"):
        b = xr.load_5m(db, coin)
        t = np.array([x[0] for x in b], dtype=np.int64) + 300
        c = np.array([x[4] for x in b])
        month = pd.to_datetime(t, unit="s").strftime("%Y-%m").to_numpy()
        g = g.copy()
        i0 = np.searchsorted(t, g["t"].to_numpy(), side="right") - 1
        valid = i0 >= 0
        p0 = np.where(valid, c[np.maximum(i0, 0)], np.nan)
        sign = np.where(g["dir"].to_numpy() == "LONG", 1.0, -1.0)
        emonth = pd.to_datetime(g["t"], unit="s").dt.strftime("%Y-%m").to_numpy()
        for lab, h in HORIZONS.items():
            k = h // 300
            i1 = np.searchsorted(t, g["t"].to_numpy() + h, side="right") - 1
            ok = valid & (i1 > i0) & (i1 < len(c))
            raw = np.where(ok, c[np.minimum(i1, len(c) - 1)] / p0 - 1, np.nan)
            # coin-month drift over all 5m bars at this horizon
            fr = np.full(len(c), np.nan)
            fr[:-k] = c[k:] / c[:-k] - 1
            drift = pd.Series(fr).groupby(month).mean()
            d = drift.reindex(emonth).to_numpy()
            g[f"ret_{lab}"] = sign * raw
            g[f"xs_{lab}"] = sign * (raw - d)
        out.append(g)
    return pd.concat(out, ignore_index=True)


def join_context(ctx_dir: Path, trips: pd.DataFrame) -> pd.DataFrame:
    parts = []
    for coin, g in trips.groupby("coin"):
        cx = pd.read_pickle(ctx_dir / f"context_{coin}.pkl").sort_values("T")
        g = g.sort_values("t")
        m = pd.merge_asof(g, cx, left_on="t", right_on="T", direction="backward", tolerance=1800)
        T = cx["T"].to_numpy()
        fired = cx["setups"].to_numpy() != ""
        cs = np.r_[0, np.cumsum(fired)]
        lo = np.searchsorted(T, m["t"].to_numpy() - 7200, side="right")
        hi = np.searchsorted(T, m["t"].to_numpy(), side="right")
        m["our_setup_2h"] = (cs[hi] - cs[lo]) > 0
        parts.append(m)
    return pd.concat(parts, ignore_index=True)


def analyze(db: str, hl: str, out: Path) -> dict[str, Any]:
    trips, excluded = load_trips(hl)
    df = forward(db, trips)
    df = join_context(out, df)
    df = df.dropna(subset=["S1"]).reset_index(drop=True)
    df["cl"] = df["address"].str[:12] + ":" + (df["t"] // 86400).astype(str)
    rep: dict[str, Any] = {"entries": int(len(df)), "accounts": int(df["address"].nunique()), "excluded_hft": excluded,
                           "by_dir": df["dir"].value_counts().to_dict()}

    def summ(x: pd.DataFrame) -> dict:
        r = {"n": int(len(x)), "win_rate": round(float((x["net"] > 0).mean()), 3) if len(x) else None}
        for lab in HORIZONS:
            m, t, n = clustered(x[f"xs_{lab}"].to_numpy(), x["cl"].to_numpy())
            r[f"xs_{lab}_pct"] = round(100 * m, 3) if n else None
            r[f"t_{lab}"] = round(t, 2)
        return r

    # D1 information in timing
    rep["D1"] = {f"{d}|{s}": summ(g) for (d, s), g in df.groupby(["dir", "source"])}
    rep["D1"].update({f"{d}|ALL": summ(g) for d, g in df.groupby("dir")})
    # D1b skill without survivorship: first half ranks accounts, second half is scored
    df = df.sort_values("t")
    df["half"] = df.groupby("address").cumcount() / df.groupby("address")["t"].transform("size")
    first = df[df["half"] < 0.5].groupby("address")["net"].agg(["sum", "size"])
    second_n = df[df["half"] >= 0.5].groupby("address").size()
    elig = first[(first["size"] >= 10)].index.intersection(second_n[second_n >= 10].index)
    ranked = first.loc[elig, "sum"].sort_values(ascending=False)
    top = set(ranked.index[: max(1, len(ranked) // 3)])
    sk = df[(df["address"].isin(top)) & (df["half"] >= 0.5)]
    rest = df[(df["address"].isin(set(elig) - top)) & (df["half"] >= 0.5)]
    rep["D1b"] = {"eligible_accounts": len(elig), "skilled_accounts": len(top),
                  "skilled_second_half": {d: summ(g) for d, g in sk.groupby("dir")},
                  "others_second_half": {d: summ(g) for d, g in rest.groupby("dir")},
                  "skilled_second_half_net_usd": round(float(sk["net"].sum()), 2)}
    # D2 winners vs losers context (their long trades)
    longs = df[df["dir"] == "LONG"]
    B = bucket(longs)
    rep["D2"] = {}
    for f in B.columns:
        rep["D2"][f] = {}
        for v, idx in B.groupby(f).groups.items():
            g = longs.loc[idx]
            if len(g) >= 50:
                rep["D2"][f][v] = {"n": len(g), "win_rate": round(float((g["net"] > 0).mean()), 3),
                                   "xs_24h_pct": round(100 * float(g["xs_24h"].mean()), 3)}
    # D3 coverage
    win = longs[longs["net"] > 0]
    rep["D3"] = {"long_entries": int(len(longs)), "our_setup_within_2h_all": round(float(longs["our_setup_2h"].mean()), 3),
                 "our_setup_within_2h_winning": round(float(win["our_setup_2h"].mean()), 3),
                 "state_when_we_did_nothing_S1": longs[~longs["our_setup_2h"]]["S1"].value_counts(normalize=True).round(3).to_dict(),
                 "state_when_we_did_nothing_S2": longs[~longs["our_setup_2h"]]["S2"].value_counts(normalize=True).round(3).to_dict()}
    # D4 candidate contexts from the skilled group's second-half LONG entries
    skl = sk[sk["dir"] == "LONG"]
    Bs = bucket(skl)
    cands, tested = [], 0
    feats = list(Bs.columns)
    for combo in [(f,) for f in feats] + list(itertools.combinations(feats, 2)):
        for vals, idx in Bs.groupby(list(combo)).groups.items():
            vals = vals if isinstance(vals, tuple) else (vals,)
            g = skl.loc[idx]
            tested += 1
            if len(g) < 150:
                continue
            for lab in ("24h", "5d"):
                m, t, n = clustered(g[f"xs_{lab}"].to_numpy(), g["cl"].to_numpy())
                if m > 0 and t >= 3:
                    cands.append({"context": dict(zip(combo, vals)), "horizon": lab, "n": n, "xs_pct": round(100 * m, 3), "t": round(t, 2)})
    cands.sort(key=lambda c: -c["t"])
    seen, top5 = set(), []
    for c in cands:
        k = json.dumps(c["context"], sort_keys=True)
        if k not in seen:
            seen.add(k)
            top5.append(c)
        if len(top5) == 5:
            break
    rep["D4"] = {"cells_tested": tested, "qualifying": len(cands), "candidates_top5": top5}
    df.to_pickle(out / "entries_joined.pkl")
    (out / "review2_report.json").write_text(json.dumps(rep, indent=1, default=str))
    return rep


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["context", "analyze"])
    ap.add_argument("--db", required=True)
    ap.add_argument("--hl")
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=5)
    a = ap.parse_args(argv)
    out = Path(os.path.expanduser(a.out))
    out.mkdir(parents=True, exist_ok=True)
    if a.cmd == "context":
        with ProcessPoolExecutor(max_workers=a.workers) as ex:
            res = list(ex.map(context_coin, [a.db] * len(xe.COINS), xe.COINS, [str(out)] * len(xe.COINS)))
        print(json.dumps(res))
    else:
        r = analyze(a.db, a.hl, out)
        print(json.dumps({k: r[k] for k in ("entries", "accounts", "by_dir", "D1b", "D3")}, indent=1, default=str))
        print(json.dumps(r["D4"], indent=1))


if __name__ == "__main__":
    main()
