"""Multi-timeframe entry study v1 — implements docs/research/MTF_ENTRY_STUDY_V1.md exactly.

5m trigger, 15m/1h confirmation, 4h market type, regime-aware exits, long and short,
real Kraken Pro (Canada) charges plus a low-fee reference. Research only: no TAKEs.

Run (needs numpy + pandas; the App backend venv has them):
    python -m src.research.mtf_entry run   --db <lab5_5m.sqlite> --out ~/ananta_runs/mtf_entry_v1
    python -m src.research.mtf_entry holdout --out ~/ananta_runs/mtf_entry_v1   # once, CONFIRMED only
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import os
import sqlite3
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

VERSION = "mtf.entry.v1"
COINS = ["BTC", "ETH", "SOL", "ADA", "DOGE", "AVAX", "BCH", "LINK", "LTC", "XRP"]
DISC_END = 1704067200        # 2024-01-01T00:00Z (exclusive)
CONF_END = 1785542400        # 2026-08-01T00:00Z (exclusive)  research-law discovery end
SPLITS = ("DISCOVERY", "CONFIRM", "HOLDOUT")
STEP = {"5m": 300, "15m": 900, "1h": 3600, "4h": 14400}
BARS_PER_H = 12

TRIGGERS = ("T1_BREAKOUT", "T2_PULLBACK_RECLAIM", "T3_SQUEEZE_RELEASE")
CONFIRMS = ("C0", "C1", "C2")
GATES = ("G0", "G1")
EXITS = ("X1_FIXED", "X2_TREND", "X3_ADAPTIVE")
DIRS = ("LONG", "SHORT")

# per-side fees in fraction; slippage per side
COSTS = {
    "KRAKEN_T1_TAKER": {"entry": 0.0080, "target": 0.0080, "stop": 0.0080, "slip": 0.0005},
    "KRAKEN_T1_MAKER": {"entry": 0.0040, "target": 0.0040, "stop": 0.0080, "slip": 0.0005},
    "KRAKEN_T3": {"entry": 0.0022, "target": 0.0022, "stop": 0.0038, "slip": 0.0005},
    "LOW_FEE": {"entry": 0.00045, "target": 0.00045, "stop": 0.00045, "slip": 0.0005},
}
PRIMARY = "KRAKEN_T1_MAKER"
KIND_TARGET, KIND_STOP, KIND_TIME, KIND_SPLIT = 0, 1, 2, 3  # target = maker exit; others = taker


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
def load_5m(db: str, coin: str) -> dict[str, np.ndarray]:
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        a = np.array(con.execute(
            "SELECT event_unix, open, high, low, close, volume FROM bars WHERE instrument=? ORDER BY event_unix",
            (f"{coin}-USD-SPOT",)).fetchall(), dtype=float)
    finally:
        con.close()
    return {"t": a[:, 0].astype(np.int64), "o": a[:, 1], "h": a[:, 2], "l": a[:, 3], "c": a[:, 4], "v": a[:, 5]}


def resample(b: dict[str, np.ndarray], tf: str) -> dict[str, np.ndarray]:
    """UTC-aligned buckets, complete buckets only. 'tc' = bucket close time (open + step)."""
    step = STEP[tf]
    need = step // 300
    key = b["t"] - (b["t"] % step)
    starts = np.flatnonzero(np.r_[True, key[1:] != key[:-1]])
    counts = np.diff(np.r_[starts, len(key)])
    o = b["o"][starts]
    h = np.maximum.reduceat(b["h"], starts)
    lo = np.minimum.reduceat(b["l"], starts)
    c = b["c"][np.r_[starts[1:], len(key)] - 1]
    v = np.add.reduceat(b["v"], starts)
    ok = counts == need
    k = key[starts][ok]
    return {"t": k, "tc": k + step, "o": o[ok], "h": h[ok], "l": lo[ok], "c": c[ok], "v": v[ok]}


def ema(x: np.ndarray, n: int) -> np.ndarray:
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy()


def atr(h, lo, c, n: int = 14) -> np.ndarray:
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - lo, np.maximum(np.abs(h - pc), np.abs(lo - pc)))
    return pd.Series(tr).ewm(alpha=1.0 / n, adjust=False).mean().to_numpy()


def mapper(htf_tc: np.ndarray, t5_close: np.ndarray, step: int) -> tuple[np.ndarray, np.ndarray]:
    """Index of the last higher-timeframe bar CLOSED at or before each 5m close; valid if not stale."""
    idx = np.searchsorted(htf_tc, t5_close, side="right") - 1
    valid = idx >= 0
    safe = np.where(valid, idx, 0)
    valid &= (t5_close - htf_tc[safe]) <= 2 * step
    return safe, valid


# ---------------------------------------------------------------------------
# Features per coin
# ---------------------------------------------------------------------------
def features(b: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    t5c = b["t"] + 300
    c, o, h, lo, v = b["c"], b["o"], b["h"], b["l"], b["v"]
    f: dict[str, np.ndarray] = {}
    valid = np.ones(len(c), dtype=bool)

    # 4h market type
    b4 = resample(b, "4h")
    e20, e50 = ema(b4["c"], 20), ema(b4["c"], 50)
    trend4 = np.where((b4["c"] > e50) & (e20 > e50), 1, np.where((b4["c"] < e50) & (e20 < e50), -1, 0))
    atrp4 = atr(b4["h"], b4["l"], b4["c"]) / b4["c"]
    pct4 = pd.Series(atrp4).rolling(180, min_periods=60).rank(pct=True).to_numpy()
    vol4 = np.where(pct4 >= 0.70, 1, np.where(pct4 <= 0.30, -1, 0))
    i4, ok4 = mapper(b4["tc"], t5c, STEP["4h"])
    warm4 = np.arange(len(b4["c"])) >= 60
    f["trend4"], f["vol4"] = trend4[i4], vol4[i4]
    valid &= ok4 & warm4[i4] & ~np.isnan(pct4[i4])

    # confirmations on 1h and 15m
    for tf in ("1h", "15m"):
        bt = resample(b, tf)
        e = ema(bt["c"], 20)
        e_prev3 = np.r_[np.full(3, np.nan), e[:-3]]
        up = (bt["c"] > e) & (e > e_prev3)
        dn = (bt["c"] < e) & (e < e_prev3)
        it, okt = mapper(bt["tc"], t5c, STEP[tf])
        warm = np.arange(len(bt["c"])) >= 50
        f[f"up_{tf}"], f[f"dn_{tf}"] = up[it], dn[it]
        valid &= okt & warm[it]
        if tf == "1h":
            a1 = atr(bt["h"], bt["l"], bt["c"])
            f["atr1h"] = a1[it]
        else:
            f["ema15"] = e[it]

    # 5m trigger inputs
    ema5 = ema(c, 20)
    hh24 = pd.Series(h).rolling(24).max().shift(1).to_numpy()
    ll24 = pd.Series(lo).rolling(24).min().shift(1).to_numpy()
    vm48 = pd.Series(v).rolling(48).mean().shift(1).to_numpy()
    volx = (vm48 > 0) & (v >= 2.0 * vm48)
    f["T1_LONG"] = (c > hh24) & volx
    f["T1_SHORT"] = (c < ll24) & volx

    touch_l = (lo <= f["ema15"]).astype(float)
    touch_s = (h >= f["ema15"]).astype(float)
    rec_l = pd.Series(touch_l).rolling(6).max().shift(1).to_numpy() > 0
    rec_s = pd.Series(touch_s).rolling(6).max().shift(1).to_numpy() > 0
    c_prev, e5_prev = np.r_[np.nan, c[:-1]], np.r_[np.nan, ema5[:-1]]
    f["T2_LONG"] = rec_l & (c_prev <= e5_prev) & (c > ema5) & (c > o)
    f["T2_SHORT"] = rec_s & (c_prev >= e5_prev) & (c < ema5) & (c < o)

    sma = pd.Series(c).rolling(20).mean().to_numpy()
    sd = pd.Series(c).rolling(20).std(ddof=0).to_numpy()
    upper, lower = sma + 2 * sd, sma - 2 * sd
    width = (upper - lower) / sma
    q20 = pd.Series(width).rolling(288, min_periods=288).quantile(0.20).to_numpy()
    squeezed_prev = np.r_[False, (width[:-1] <= q20[:-1])]
    f["T3_LONG"] = squeezed_prev & (c > upper)
    f["T3_SHORT"] = squeezed_prev & (c < lower)

    valid &= np.isfinite(f["atr1h"]) & (f["atr1h"] > 0)
    f["valid"] = valid
    f["split"] = np.where(b["t"] < DISC_END, 0, np.where(b["t"] < CONF_END, 1, 2)).astype(np.int8)
    return f


# ---------------------------------------------------------------------------
# Exit simulation (long convention; shorts pass negated prices)
# ---------------------------------------------------------------------------
def simulate(o, h, lo, c, i: int, end: int, A: float, mode: str) -> tuple[float, int, int, float, float]:
    """Entry at o[i+1]. Returns (gross_return, kind, exit_idx, mfe24, mae24)."""
    e = o[i + 1]
    ae = abs(e)
    j0 = i + 1
    w24 = min(end, j0 + 24 * BARS_PER_H - 1)
    mfe24 = (h[j0:w24 + 1].max() - e) / ae
    mae24 = (lo[j0:w24 + 1].min() - e) / ae
    if mode == "FIXED":
        k_stop, k_tgt, hours = 1.0, 2.0, 24
    elif mode == "RANGE":
        k_stop, k_tgt, hours = 1.0, 1.5, 12
    else:
        k_stop, k_tgt, hours = 1.0, None, 72
    last = min(end, j0 + hours * BARS_PER_H - 1)
    seg_o, seg_h, seg_l = o[j0:last + 1], h[j0:last + 1], lo[j0:last + 1]
    s0 = e - k_stop * A
    if k_tgt is not None:
        tg = e + k_tgt * A
        hs = np.flatnonzero(seg_l <= s0)
        ht = np.flatnonzero(seg_h >= tg)
        fs = hs[0] if hs.size else 10**9
        ft = ht[0] if ht.size else 10**9
        if fs == 10**9 and ft == 10**9:
            kind = KIND_TIME if last == j0 + hours * BARS_PER_H - 1 else KIND_SPLIT
            return (c[last] - e) / ae, kind, last, mfe24, mae24
        if fs <= ft:  # stop first when both in the same bar (pessimistic)
            fill = min(s0, seg_o[fs])
            return (fill - e) / ae, KIND_STOP, j0 + fs, mfe24, mae24
        fill = max(tg, seg_o[ft])
        return (fill - e) / ae, KIND_TARGET, j0 + ft, mfe24, mae24
    # trailing: state known before each bar only
    best_prev = np.maximum.accumulate(np.r_[e, seg_h[:-1]])
    armed = best_prev >= e + 1.0 * A
    stop = np.where(armed, np.maximum(s0, best_prev - 1.5 * A), s0)
    hit = np.flatnonzero(seg_l <= stop)
    if hit.size:
        k = hit[0]
        fill = min(stop[k], seg_o[k])
        return (fill - e) / ae, KIND_STOP, j0 + k, mfe24, mae24
    kind = KIND_TIME if last == j0 + hours * BARS_PER_H - 1 else KIND_SPLIT
    return (c[last] - e) / ae, kind, last, mfe24, mae24


def net(gross: np.ndarray, kind: np.ndarray, cost: str) -> np.ndarray:
    k = COSTS[cost]
    exit_fee = np.where(kind == KIND_TARGET, k["target"], k["stop"])
    return gross - k["entry"] - exit_fee - 2 * k["slip"]


# ---------------------------------------------------------------------------
# Per coin: raw signals -> outcomes -> variants
# ---------------------------------------------------------------------------
def run_coin(db: str, coin: str) -> dict[str, Any]:
    t0 = time.time()
    b = load_5m(db, coin)
    f = features(b)
    n = len(b["c"])
    split = f["split"]
    # last index of each split, for force-close at split boundary
    split_end = np.zeros(n, dtype=np.int64)
    for s in range(3):
        idx = np.flatnonzero(split == s)
        if idx.size:
            split_end[idx] = idx[-1]
    arrs = {"LONG": (b["o"], b["h"], b["l"], b["c"]), "SHORT": (-b["o"], -b["l"], -b["h"], -b["c"])}
    out: dict[str, Any] = {"coin": coin, "raw": {}, "variants": {}}
    for trig, d in itertools.product(TRIGGERS, DIRS):
        key = f"{trig.split('_')[0]}_{d}"
        sig = np.flatnonzero(f[key] & f["valid"])
        sig = sig[sig + 1 < n]
        sig = sig[split_end[sig] > sig]  # need at least one bar after the signal inside the split
        o_, h_, l_, c_ = arrs[d]
        rows = []
        for i in sig:
            A = f["atr1h"][i]
            end = split_end[i]
            r_fixed = simulate(o_, h_, l_, c_, i, end, A, "FIXED")
            r_trend = simulate(o_, h_, l_, c_, i, end, A, "TREND")
            r_range = simulate(o_, h_, l_, c_, i, end, A, "RANGE")
            rows.append((i, r_fixed, r_trend, r_range))
        sgn = 1 if d == "LONG" else -1
        trend = f["trend4"][sig]
        match = trend == sgn
        conf1 = f["up_1h"][sig] if d == "LONG" else f["dn_1h"][sig]
        conf15 = f["up_15m"][sig] if d == "LONG" else f["dn_15m"][sig]
        G = np.array([r[1][0] for r in rows]), np.array([r[2][0] for r in rows]), np.array([r[3][0] for r in rows])
        K = np.array([r[1][1] for r in rows]), np.array([r[2][1] for r in rows]), np.array([r[3][1] for r in rows])
        X = np.array([r[1][2] for r in rows]), np.array([r[2][2] for r in rows]), np.array([r[3][2] for r in rows])
        mfe = np.array([r[1][3] for r in rows]) if rows else np.array([])
        mae = np.array([r[1][4] for r in rows]) if rows else np.array([])
        out["raw"][f"{trig}|{d}"] = {
            "n": int(len(sig)),
            "split": split[sig].tolist(),
            "mfe24": np.round(mfe, 6).tolist(), "mae24": np.round(mae, 6).tolist(),
            "trend4": trend.tolist(), "vol4": f["vol4"][sig].tolist(),
        }
        for conf, gate, ex in itertools.product(CONFIRMS, GATES, EXITS):
            keep = np.ones(len(sig), dtype=bool)
            if conf in ("C1", "C2"):
                keep &= conf1
            if conf == "C2":
                keep &= conf15
            if gate == "G1":
                keep &= match
            if ex == "X1_FIXED":
                g, k, x = G[0], K[0], X[0]
            elif ex == "X2_TREND":
                g, k, x = G[1], K[1], X[1]
            else:
                g, k, x = np.where(match, G[1], G[2]), np.where(match, K[1], K[2]), np.where(match, X[1], X[2])
            chosen, last_exit = [], -1
            for m in np.flatnonzero(keep):
                if sig[m] >= last_exit:  # entry at sig+1 is after the previous exit bar
                    chosen.append(m)
                    last_exit = x[m]
            chosen = np.array(chosen, dtype=np.int64)
            vid = f"{trig}|{conf}|{gate}|{ex}|{d}"
            out["variants"][vid] = {
                "split": split[sig[chosen]].tolist() if chosen.size else [],
                "gross": np.round(g[chosen], 7).tolist() if chosen.size else [],
                "kind": k[chosen].astype(int).tolist() if chosen.size else [],
                "trend4": trend[chosen].tolist() if chosen.size else [],
                "vol4": f["vol4"][sig[chosen]].tolist() if chosen.size else [],
                "hold_h": (np.round((x[chosen] - sig[chosen]) / BARS_PER_H, 3)).tolist() if chosen.size else [],
            }
    out["seconds"] = round(time.time() - t0, 1)
    out["bars"] = int(n)
    return out


# ---------------------------------------------------------------------------
# Aggregation and pass rules (pre-registered)
# ---------------------------------------------------------------------------
def stats(x: np.ndarray) -> dict[str, Any]:
    n = len(x)
    if n == 0:
        return {"n": 0}
    w, lz = x[x > 0], -x[x <= 0]
    sd = x.std(ddof=1) if n > 1 else 0.0
    return {"n": int(n), "mean_pct": round(100 * x.mean(), 4), "win_rate": round(len(w) / n, 3),
            "pf": round(w.sum() / lz.sum(), 3) if lz.sum() > 0 else None,
            "t": round(x.mean() / (sd / math.sqrt(n)), 2) if sd > 0 else None,
            "total_pct": round(100 * x.sum(), 2)}


def aggregate(coins: list[dict], splits_wanted=(0, 1)) -> dict[str, Any]:
    vids = list(coins[0]["variants"].keys())
    table = {}
    for vid in vids:
        row = {}
        for s in splits_wanted:
            per_cost = {}
            for cost in COSTS:
                pooled, pos_coins = [], 0
                for cd in coins:
                    v = cd["variants"][vid]
                    sp = np.array(v["split"], dtype=int)
                    m = sp == s
                    if not m.any():
                        continue
                    x = net(np.array(v["gross"])[m], np.array(v["kind"])[m], cost)
                    pooled.append(x)
                    pos_coins += int(x.sum() > 0)
                x = np.concatenate(pooled) if pooled else np.array([])
                per_cost[cost] = {**stats(x), "coins_positive": pos_coins}
            row[SPLITS[s]] = per_cost
        table[vid] = row
    return table


def passes_discovery(r: dict) -> bool:
    d = r["DISCOVERY"][PRIMARY]
    return (d.get("n", 0) >= 200 and d["mean_pct"] > 0 and (d.get("pf") or 0) >= 1.15
            and (d.get("t") or 0) >= 3.0 and d["coins_positive"] >= 6)


def passes_confirm(r: dict) -> bool:
    d = r["CONFIRM"][PRIMARY]
    return d.get("n", 0) >= 100 and d["mean_pct"] > 0 and (d.get("pf") or 0) >= 1.05


def cells(coins: list[dict], split: int = 0) -> dict[str, Any]:
    """Diagnostic: mean net per trade by 4h market type, per trigger+direction, at C0/G0/X1 and C2/G0/X3."""
    out = {}
    for base in ("C0|G0|X1_FIXED", "C2|G0|X3_ADAPTIVE"):
        for trig, d in itertools.product(TRIGGERS, DIRS):
            vid = f"{trig}|{base.split('|')[0]}|{base.split('|')[1]}|{base.split('|')[2]}|{d}"
            buckets: dict[str, list] = {}
            for cd in coins:
                v = cd["variants"][vid]
                sp = np.array(v["split"], dtype=int)
                m = sp == split
                if not m.any():
                    continue
                x = net(np.array(v["gross"])[m], np.array(v["kind"])[m], PRIMARY)
                tr = np.array(v["trend4"])[m]
                vo = np.array(v["vol4"])[m]
                for xi, ti, vi in zip(x, tr, vo):
                    buckets.setdefault(f"{['DOWN','RANGE','UP'][ti+1]}/{['LOWVOL','NORMVOL','HIGHVOL'][vi+1]}", []).append(xi)
            out[vid] = {k: stats(np.array(v)) for k, v in sorted(buckets.items())}
    return out


def breakeven(coins: list[dict], split: int = 0) -> dict[str, Any]:
    out = {}
    rt = {k: 100 * (v["entry"] + v["target"] + 2 * v["slip"]) for k, v in COSTS.items()}
    for key in coins[0]["raw"]:
        mfe = np.concatenate([np.array(cd["raw"][key]["mfe24"])[np.array(cd["raw"][key]["split"], dtype=int) == split] for cd in coins])
        if not mfe.size:
            continue
        mfe = 100 * mfe
        out[key] = {"n": int(mfe.size), "mfe24_median_pct": round(float(np.median(mfe)), 3),
                    "mfe24_p75_pct": round(float(np.percentile(mfe, 75)), 3),
                    "share_beating_roundtrip": {k: round(float((mfe > 3 * v).mean()), 3) for k, v in rt.items()},
                    "roundtrip_cost_pct": rt}
    return out


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "holdout", "selftest"])
    ap.add_argument("--db", default=os.path.expanduser("~/code/ananta-decision-agent/ananta-quant-research-db/lab5_5m.sqlite"))
    ap.add_argument("--out", default=os.path.expanduser("~/ananta_runs/mtf_entry_v1"))
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--coins", default=",".join(COINS))
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    raw_dir = out / "coins"
    raw_dir.mkdir(exist_ok=True)
    if a.cmd == "run":
        todo = [c for c in a.coins.split(",") if not (raw_dir / f"{c}.json").exists()]
        print(f"{VERSION}: coins todo={todo}", flush=True)
        with ProcessPoolExecutor(max_workers=a.workers) as ex:
            for r in ex.map(run_coin, [a.db] * len(todo), todo):
                (raw_dir / f"{r['coin']}.json").write_text(json.dumps(r))
                print(f"  {r['coin']} bars={r['bars']} {r['seconds']}s", flush=True)
        coins = [json.loads((raw_dir / f"{c}.json").read_text()) for c in COINS if (raw_dir / f"{c}.json").exists()]
        table = aggregate(coins, (0, 1))
        disc = [v for v, r in table.items() if passes_discovery(r)]
        conf = [v for v in disc if passes_confirm(table[v])]
        report = {"version": VERSION, "coins": [c["coin"] for c in coins], "variants_tried": len(table),
                  "discovery_pass": disc, "confirmed": conf, "table": table,
                  "cells_discovery": cells(coins, 0), "breakeven_discovery": breakeven(coins, 0)}
        (out / "report_setA.json").write_text(json.dumps(report, indent=1, default=str))
        (out / "frozen_confirmed.json").write_text(json.dumps({"confirmed": conf, "frozen_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}))
        print(json.dumps({"variants_tried": len(table), "discovery_pass": disc, "confirmed": conf}, indent=1))
    elif a.cmd == "holdout":
        frozen = json.loads((out / "frozen_confirmed.json").read_text())["confirmed"]
        marker = out / "holdout_done.json"
        if marker.exists():
            print("holdout already run once:", marker.read_text())
            return
        coins = [json.loads((raw_dir / f"{c}.json").read_text()) for c in COINS]
        table = aggregate(coins, (2,))
        res = {v: table[v]["HOLDOUT"] for v in frozen}
        marker.write_text(json.dumps({"ran_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "variants": frozen, "result": res}, indent=1))
        print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
