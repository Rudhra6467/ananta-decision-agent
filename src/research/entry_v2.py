"""Entry study v2 — implements docs/research/ENTRY_STUDY_V2.md exactly.

4h setups with daily context, 5m entry timing (now / limit dip / reclaim), ATR4h exits
with a >=3% minimum target, long and short, real Kraken Pro Canada charges.
Research only: nothing here can issue a TAKE.

    python -m src.research.entry_v2 run     --out ~/ananta_runs/entry_v2
    python -m src.research.entry_v2 holdout --out ~/ananta_runs/entry_v2   # once, CONFIRMED only
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import os
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.research import mtf_entry as v1

VERSION = "entry.v2"
v1.STEP["1d"] = 86400
BPH = 12
SETUPS = ("S1_TREND_PULLBACK", "S2_BREAKOUT", "S3_TREND_CONTROL")
TIMINGS = ("E_NOW", "E_DIP", "E_RECLAIM")
EXITS = ("X_TARGET", "X_TRAIL")
DIRS = ("LONG", "SHORT")
MIN_TARGET = 0.03
COSTS = {
    "KRAKEN_T1": {"maker": 0.0040, "taker": 0.0080, "slip": 0.0005},
    "KRAKEN_T1_ALLTAKER": {"maker": 0.0080, "taker": 0.0080, "slip": 0.0005},
    "KRAKEN_T3": {"maker": 0.0022, "taker": 0.0038, "slip": 0.0005},
    "LOW_FEE": {"maker": 0.00045, "taker": 0.00045, "slip": 0.0005},
}
PRIMARY = "KRAKEN_T1"
K_TARGET, K_STOP, K_TIME, K_SPLIT = 0, 1, 2, 3


def trend_of(c: np.ndarray) -> np.ndarray:
    e20, e50 = v1.ema(c, 20), v1.ema(c, 50)
    return np.where((c > e50) & (e20 > e50), 1, np.where((c < e50) & (e20 < e50), -1, 0))


def setups(b: dict[str, np.ndarray]) -> dict[str, Any]:
    """All setup flags on the 4h grid (LONG and SHORT), known at each 4h close."""
    b4 = v1.resample(b, "4h")
    bd = v1.resample(b, "1d")
    c, h, lo, v = b4["c"], b4["h"], b4["l"], b4["v"]
    n = len(c)
    e20 = v1.ema(c, 20)
    tr4 = trend_of(c)
    trd_all = trend_of(bd["c"])
    idd, okd = v1.mapper(bd["tc"], b4["tc"], v1.STEP["1d"])
    trd = np.where(okd & (idd >= 50), trd_all[idd], 99)  # 99 = unknown
    A = v1.atr(h, lo, c)
    hh30 = pd.Series(h).rolling(30).max().shift(1).to_numpy()
    ll30 = pd.Series(lo).rolling(30).min().shift(1).to_numpy()
    vm30 = pd.Series(v).rolling(30).mean().shift(1).to_numpy()
    volx = (vm30 > 0) & (v >= 1.5 * vm30)
    lo_prev, h_prev, e20_prev = np.r_[np.nan, lo[:-1]], np.r_[np.nan, h[:-1]], np.r_[np.nan, e20[:-1]]
    touch_l = (lo <= e20) | (lo_prev <= e20_prev)
    touch_s = (h >= e20) | (h_prev >= e20_prev)
    warm = (np.arange(n) >= 60) & (trd != 99) & np.isfinite(A)
    flags = {
        ("S1_TREND_PULLBACK", "LONG"): (trd == 1) & (tr4 == 1) & touch_l & (c > e20),
        ("S1_TREND_PULLBACK", "SHORT"): (trd == -1) & (tr4 == -1) & touch_s & (c < e20),
        ("S2_BREAKOUT", "LONG"): (c > hh30) & volx & (trd != -1),
        ("S2_BREAKOUT", "SHORT"): (c < ll30) & volx & (trd != 1),
        ("S3_TREND_CONTROL", "LONG"): (trd == 1) & (tr4 == 1),
        ("S3_TREND_CONTROL", "SHORT"): (trd == -1) & (tr4 == -1),
    }
    return {"tc": b4["tc"], "c": c, "A": A, "flags": {k: f & warm for k, f in flags.items()}}


def sim(o, h, lo, c, j: int, e: float, end: int, A: float, mode: str, partial: bool) -> tuple[float, int, int]:
    """Long convention (shorts pass negated arrays). Entry price e at bar j.
    partial=True: the fill happened inside bar j (limit), so bar j cannot hit the target and its
    high does not count toward the trail; a stop inside bar j is assumed hit (pessimistic)."""
    ae = abs(e)
    s0 = e - 1.5 * A
    maxbars = (7 if mode == "X_TARGET" else 14) * 24 * BPH
    last = min(end, j + maxbars - 1)
    seg_o, seg_h, seg_l = o[j:last + 1], h[j:last + 1].copy(), lo[j:last + 1]
    if partial:
        if seg_l[0] <= s0:
            return (s0 - e) / ae, K_STOP, j
        seg_h[0] = max(e, c[j])  # only the post-fill part we can vouch for
    if mode == "X_TARGET":
        tg = e + 3.0 * A
        hs = np.flatnonzero(seg_l <= s0)
        ht = np.flatnonzero(seg_h >= tg)
        if partial and ht.size and ht[0] == 0:
            ht = ht[1:]
        fs = hs[0] if hs.size else 10**9
        ft = ht[0] if ht.size else 10**9
        if fs == 10**9 and ft == 10**9:
            kind = K_TIME if last == j + maxbars - 1 else K_SPLIT
            return (c[last] - e) / ae, kind, last
        if fs <= ft:
            fill = s0 if (partial and fs == 0) else min(s0, seg_o[fs])
            return (fill - e) / ae, K_STOP, j + fs
        return (max(tg, seg_o[ft]) - e) / ae, K_TARGET, j + ft
    best_prev = np.maximum.accumulate(np.r_[e, seg_h[:-1]])
    armed = best_prev >= e + 1.5 * A
    stop = np.where(armed, np.maximum(s0, best_prev - 2.5 * A), s0)
    hit = np.flatnonzero(seg_l <= stop)
    if hit.size:
        k = hit[0]
        fill = stop[k] if (partial and k == 0) else min(stop[k], seg_o[k])
        return (fill - e) / ae, K_STOP, j + k
    kind = K_TIME if last == j + maxbars - 1 else K_SPLIT
    return (c[last] - e) / ae, kind, last


def run_coin(db: str, coin: str) -> dict[str, Any]:
    t0 = time.time()
    b = v1.load_5m(db, coin)
    t5 = b["t"]
    n = len(t5)
    f5 = v1.features(b)  # only the 5m reclaim flags are used from here
    S = setups(b)
    split = f5["split"]
    split_end = np.zeros(n, dtype=np.int64)
    for s in range(3):
        idx = np.flatnonzero(split == s)
        if idx.size:
            split_end[idx] = idx[-1]
    neg = {"LONG": (b["o"], b["h"], b["l"], b["c"]), "SHORT": (-b["o"], -b["l"], -b["h"], -b["c"])}
    out: dict[str, Any] = {"coin": coin, "variants": {}, "dip_attempts": {}, "dip_fills": {}}
    for (setup, d), flag in S["flags"].items():
        o_, h_, l_, c_ = neg[d]
        sgn = 1 if d == "LONG" else -1
        rec = f5["T2_LONG"] if d == "LONG" else f5["T2_SHORT"]
        ks = np.flatnonzero(flag)
        for timing, ex in itertools.product(TIMINGS, EXITS):
            trades, last_exit = [], -1
            attempts = fills = 0
            for k in ks:
                T = S["tc"][k]
                j0 = int(np.searchsorted(t5, T, side="left"))
                if j0 >= n or t5[j0] - T >= 3600:
                    continue
                end = int(split_end[j0])
                jw = min(end, j0 + 24 * BPH - 1)
                if j0 <= last_exit:
                    continue  # position still open
                A = S["A"][k]
                if timing == "E_NOW":
                    j, e, partial, maker = j0, o_[j0], False, False
                elif timing == "E_DIP":
                    attempts += 1
                    L = sgn * S["c"][k] - 0.5 * A  # in the (possibly negated) price space
                    hits = np.flatnonzero(l_[j0:jw + 1] < L)
                    if not hits.size:
                        continue
                    fills += 1
                    j = j0 + int(hits[0])
                    e, partial, maker = min(L, o_[j]), True, True
                    if o_[j] < L:
                        partial = False  # opened through the limit: filled at the open, whole bar is post-entry
                else:
                    r = np.flatnonzero(rec[j0:jw])
                    if not r.size:
                        continue
                    j = j0 + int(r[0]) + 1
                    e, partial, maker = o_[j], False, False
                if j > end or 3.0 * A / abs(e) < MIN_TARGET:
                    continue
                g, kind, x = sim(o_, h_, l_, c_, j, e, end, A, ex, partial)
                trades.append((int(split[j]), round(float(g), 7), kind, int(maker), round((x - j) / BPH, 2)))
                last_exit = x
            vid = f"{setup}|{timing}|{ex}|{d}"
            out["variants"][vid] = trades
            if timing == "E_DIP":
                out["dip_attempts"][vid], out["dip_fills"][vid] = attempts, fills
    out["seconds"] = round(time.time() - t0, 1)
    return out


def net(trades: list, cost: str) -> np.ndarray:
    k = COSTS[cost]
    if not trades:
        return np.array([])
    a = np.array(trades, dtype=float)
    g, kind, maker = a[:, 1], a[:, 2], a[:, 3]
    entry = np.where(maker == 1, k["maker"], k["taker"])
    exitf = np.where(kind == K_TARGET, k["maker"], k["taker"])
    return g - entry - exitf - 2 * k["slip"]


def table(coins: list[dict], splits=(0, 1)) -> dict[str, Any]:
    out = {}
    for vid in coins[0]["variants"]:
        row = {}
        for s in splits:
            pc = {}
            for cost in COSTS:
                xs, pos = [], 0
                for cd in coins:
                    tr = [t for t in cd["variants"][vid] if t[0] == s]
                    x = net(tr, cost)
                    if x.size:
                        xs.append(x)
                        pos += int(x.sum() > 0)
                x = np.concatenate(xs) if xs else np.array([])
                pc[cost] = {**v1.stats(x), "coins_positive": pos}
            gs = np.concatenate([np.array([t[1] for t in cd["variants"][vid] if t[0] == s]) for cd in coins])
            pc["GROSS"] = v1.stats(gs)
            row[v1.SPLITS[s]] = pc
        out[vid] = row
    return out


def pass_disc(r: dict) -> bool:
    d = r["DISCOVERY"][PRIMARY]
    return (d.get("n", 0) >= 100 and d["mean_pct"] > 0 and (d.get("pf") or 0) >= 1.15
            and (d.get("t") or 0) >= 2.5 and d["coins_positive"] >= 6)


def pass_conf(r: dict) -> bool:
    d = r["CONFIRM"][PRIMARY]
    return d.get("n", 0) >= 50 and d["mean_pct"] > 0 and (d.get("pf") or 0) >= 1.05


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "holdout"])
    ap.add_argument("--db", default=os.path.expanduser("~/code/ananta-decision-agent/ananta-quant-research-db/lab5_5m.sqlite"))
    ap.add_argument("--out", default=os.path.expanduser("~/ananta_runs/entry_v2"))
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--coins", default=",".join(v1.COINS))
    a = ap.parse_args(argv)
    out = Path(a.out)
    (out / "coins").mkdir(parents=True, exist_ok=True)
    if a.cmd == "run":
        todo = [c for c in a.coins.split(",") if not (out / "coins" / f"{c}.json").exists()]
        with ProcessPoolExecutor(max_workers=a.workers) as ex:
            for r in ex.map(run_coin, [a.db] * len(todo), todo):
                (out / "coins" / f"{r['coin']}.json").write_text(json.dumps(r))
                print(f"  {r['coin']} {r['seconds']}s", flush=True)
        coins = [json.loads((out / "coins" / f"{c}.json").read_text()) for c in v1.COINS]
        tab = table(coins, (0, 1))
        disc = [v for v, r in tab.items() if pass_disc(r)]
        conf = [v for v in disc if pass_conf(tab[v])]
        fills = {v: {"attempts": sum(cd["dip_attempts"].get(v, 0) for cd in coins),
                     "fills": sum(cd["dip_fills"].get(v, 0) for cd in coins)} for v in coins[0]["dip_attempts"]}
        (out / "report_setA.json").write_text(json.dumps({"version": VERSION, "variants_tried": len(tab), "discovery_pass": disc,
                                                          "confirmed": conf, "dip_fill_rates": fills, "table": tab}, indent=1))
        (out / "frozen_confirmed.json").write_text(json.dumps({"confirmed": conf, "frozen_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}))
        print(json.dumps({"variants_tried": len(tab), "discovery_pass": disc, "confirmed": conf}, indent=1))
    else:
        conf = json.loads((out / "frozen_confirmed.json").read_text())["confirmed"]
        marker = out / "holdout_done.json"
        if marker.exists():
            print("holdout already run once:", marker.read_text())
            return
        if not conf:
            print("no CONFIRMED variants: holdout stays unused")
            return
        coins = [json.loads((out / "coins" / f"{c}.json").read_text()) for c in v1.COINS]
        tab = table(coins, (2,))
        res = {v: tab[v]["HOLDOUT"] for v in conf}
        marker.write_text(json.dumps({"ran_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "result": res}, indent=1))
        print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
