"""Candidate v3 — the ONE-TIME holdout check for the frozen v2 trend-dip candidate.

Implements docs/research/CANDIDATE_V3.md. Uses entry_v2 functions unchanged (frozen at 613ac43).
    python -m src.research.candidate_v3 holdout --out ~/ananta_runs/candidate_v3
A marker file makes a second run refuse.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

import numpy as np

from src.research import entry_v2 as v2
from src.research import mtf_entry as v1

VERSION = "candidate.v3"
FROZEN = ("S3_TREND_CONTROL", "LONG", "E_DIP", "X_TRAIL")
HALF_SPREAD = {"BTC": 0.00178, "ETH": 0.00084, "SOL": 0.00289, "ADA": 0.00273, "DOGE": 0.00307,
               "AVAX": 0.00370, "BCH": 0.00400, "LINK": 0.00341, "LTC": 0.00334, "XRP": 0.00251}
NDAX_FEE = 0.0020
KRAKEN = {"maker": 0.0040, "taker": 0.0080, "slip": 0.0005}


def frozen_trades(db: str, coin: str, split_wanted: int = 2) -> dict[str, Any]:
    """Exactly the v2 loop for the frozen variant, with trade details kept."""
    b = v1.load_5m(db, coin)
    t5, n = b["t"], len(b["t"])
    f5 = v1.features(b)
    S = v2.setups(b)
    split = f5["split"]
    split_end = np.zeros(n, dtype=np.int64)
    for s in range(3):
        idx = np.flatnonzero(split == s)
        if idx.size:
            split_end[idx] = idx[-1]
    o_, h_, l_, c_ = b["o"], b["h"], b["l"], b["c"]
    ks = np.flatnonzero(S["flags"][(FROZEN[0], FROZEN[1])])
    trades, last_exit = [], -1
    for k in ks:
        T = S["tc"][k]
        j0 = int(np.searchsorted(t5, T, side="left"))
        if j0 >= n or t5[j0] - T >= 3600:
            continue
        end = int(split_end[j0])
        jw = min(end, j0 + 24 * v2.BPH - 1)
        if j0 <= last_exit:
            continue
        A = S["A"][k]
        L = S["c"][k] - 0.5 * A
        hits = np.flatnonzero(l_[j0:jw + 1] < L)
        if not hits.size:
            continue
        j = j0 + int(hits[0])
        e, partial = min(L, o_[j]), True
        if o_[j] < L:
            partial = False
        if j > end or 3.0 * A / abs(e) < v2.MIN_TARGET:
            continue
        g, kind, x = v2.sim(o_, h_, l_, c_, j, e, end, A, FROZEN[3], partial)
        last_exit = x
        if int(split[j]) != split_wanted:
            continue
        trades.append({"coin": coin, "setup_ts": int(T), "entry_ts": int(t5[j]), "exit_ts": int(t5[x]) + 300,
                       "entry": float(e), "gross": float(g), "kind": int(kind), "hold_h": round((x - j) / v2.BPH, 2),
                       "b1_entry": float(o_[j0]), "b1_exit": float(c_[x])})
    hold = np.flatnonzero(split == split_wanted)
    bh = {"first_open": float(o_[hold[0]]), "last_close": float(c_[hold[-1]])} if hold.size else None
    return {"coin": coin, "trades": trades, "buy_hold": bh}


def ndax_net(t: dict) -> float:
    hs = HALF_SPREAD[t["coin"]]
    return t["gross"] - NDAX_FEE - (NDAX_FEE + hs)  # limit entry: fee only; market exit: fee + half-spread


def kraken_net(t: dict) -> float:
    exitf = KRAKEN["maker"] if t["kind"] == v2.K_TARGET else KRAKEN["taker"]
    return t["gross"] - KRAKEN["maker"] - exitf - 2 * KRAKEN["slip"]


def b1_net(t: dict) -> float:
    hs = HALF_SPREAD[t["coin"]]
    return (t["b1_exit"] - t["b1_entry"]) / t["b1_entry"] - 2 * (NDAX_FEE + hs)


def summarize(x: np.ndarray, rng: np.random.Generator) -> dict[str, Any]:
    if x.size == 0:
        return {"n": 0}
    boots = rng.choice(x, size=(10_000, x.size), replace=True).mean(axis=1)
    w, lz = x[x > 0], -x[x <= 0]
    return {"n": int(x.size), "mean_pct": round(100 * x.mean(), 3),
            "ci90_pct": [round(100 * np.percentile(boots, 5), 3), round(100 * np.percentile(boots, 95), 3)],
            "win_rate": round(len(w) / x.size, 3), "pf": round(w.sum() / lz.sum(), 3) if lz.sum() > 0 else None}


def holdout(db: str, out: Path) -> dict[str, Any]:
    marker = out / "holdout_done.json"
    if marker.exists():
        raise SystemExit(f"holdout already run once: {marker}")
    out.mkdir(parents=True, exist_ok=True)
    rows = [frozen_trades(db, c) for c in v1.COINS]
    trades = [t for r in rows for t in r["trades"]]
    rng = np.random.default_rng(20260929)
    nd = np.array([ndax_net(t) for t in trades])
    kr = np.array([kraken_net(t) for t in trades])
    b1 = np.array([b1_net(t) for t in trades])
    per_coin = {c: {"n": sum(1 for t in trades if t["coin"] == c),
                    "ndax_total_usd_at_100": round(100 * sum(ndax_net(t) for t in trades if t["coin"] == c), 2)} for c in v1.COINS}
    bh = []
    for r in rows:
        if r["buy_hold"]:
            ret = r["buy_hold"]["last_close"] / r["buy_hold"]["first_open"] - 1
            bh.append(ret - 2 * (NDAX_FEE + HALF_SPREAD[r["coin"]]))
    res = {
        "version": VERSION, "ran_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "window": "2026-08-01 -> 2026-09-12 (data end)",
        "candidate_ndax": summarize(nd, rng), "candidate_kraken_t1": summarize(kr, rng),
        "b1_same_window_long_ndax": summarize(b1, rng),
        "candidate_book_return_pct_on_1000": round(100 * (100 * nd.sum()) / 1000, 2),
        "b2_buy_and_hold_equal_weight_pct": round(100 * float(np.mean(bh)), 2) if bh else None,
        "per_coin": per_coin, "hold_h_median": float(np.median([t["hold_h"] for t in trades])) if trades else None,
        "trades": trades,
    }
    s = res["candidate_ndax"]
    res["holdout_pass"] = bool(s.get("n", 0) >= 20 and s["mean_pct"] > 0 and nd.mean() >= (b1.mean() if b1.size else -1))
    (out / "holdout_result.json").write_text(json.dumps(res, indent=1))
    marker.write_text(json.dumps({"ran_at": res["ran_at"], "pass": res["holdout_pass"]}))
    return res


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["holdout"])
    ap.add_argument("--db", default=os.path.expanduser("~/code/ananta-decision-agent/ananta-quant-research-db/lab5_5m.sqlite"))
    ap.add_argument("--out", default=os.path.expanduser("~/ananta_runs/candidate_v3"))
    a = ap.parse_args(argv)
    r = holdout(a.db, Path(a.out))
    print(json.dumps({k: v for k, v in r.items() if k != "trades"}, indent=1))


if __name__ == "__main__":
    main()
