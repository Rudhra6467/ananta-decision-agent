"""Review #26 (docs/research/REVIEW_26.md): the expected-value table, rule x market state x liquidity tier, walk-forward.

  python -m src.research.review26      -> docs/research/review26.json (the table) and REVIEW_26_RESULTS.md is written by hand
"""
from __future__ import annotations

import json
import math
import os
import random
import sqlite3
import statistics
import sys
from pathlib import Path

DAY = 86400
RULES = ("H07", "M1a", "M2a", "M2a-G", "M3a", "M3b")
FEE, FLOOR = 0.0020, {"A": 0.0020, "B": 0.0040, "C": 0.0080}
SPLIT_T = 1704067200                       # 2024-01-01
START_T = 1514764800                       # 2018-01-01
MIN_DAYS, Z_MIN, SHRINK = 30, 2.0, 50
EPISODE = 20


def _lake() -> Path:
    return Path(os.path.expanduser(os.getenv("ANANTA_LAKE", "~/ananta_lake"))) / "agent" / "daily.sqlite"


def load() -> dict[str, list[tuple]]:
    con = sqlite3.connect(f"file:{_lake()}?mode=ro", uri=True)
    try:
        out: dict[str, list] = {}
        for t, coin, o, h, l, c, v in con.execute("SELECT t, coin, o, h, l, c, v FROM bars ORDER BY coin, t"):
            out.setdefault(coin, []).append((t, o, h, l, c, v))
        return out
    finally:
        con.close()


def dial_map(btc: list[tuple]) -> dict[int, str]:
    from src.research import review25 as R

    w = R.targets([b[:5] for b in btc], "GATE50_200")
    return {b[0]: ("OPEN" if w[i] > 0 else "CLOSED") for i, b in enumerate(btc)}


def tier_at(D: list[tuple], i: int) -> str:
    qv = sorted(D[k][5] * D[k][4] for k in range(max(0, i - 30), i))
    if len(qv) < 30:
        return "C"
    med = qv[len(qv) // 2]
    return "A" if med >= 20e6 else "B" if med >= 1e6 else "C"


def _net(entry: float, exit_px: float, tier: str) -> float:
    k = FEE + FLOOR[tier]
    return 100 * (exit_px / entry * (1 - k) ** 2 - 1)


def simulate(coin: str, D: list[tuple], B, dial: dict) -> list[dict]:
    """Every rule's trades on one coin, exits as live (watch_engine._manage on daily candles)."""
    from jarvis.service import watch_engine as W
    from src.research import reads as R

    S = B if coin == "BTC" else R.Series(D)
    r10 = R.rsi(S.c, 10)
    out = []
    for rule in RULES:
        spec = W.DAILY[rule]
        busy_until, last_sig = -1, None
        for i in range(60, len(D) - 1):
            if D[i][0] < START_T or i <= busy_until:
                continue
            if spec["kind"] == "h07" and i < 210:
                continue
            ok, stop, _ = W._fires(spec, S, B, i, r10)
            if not ok:
                continue
            if spec["kind"] == "read" and last_sig is not None and D[i][0] - last_sig <= EPISODE * DAY:
                continue
            last_sig = D[i][0]
            k = i + 1
            entry = D[k][1]
            days = spec.get("days", 30)
            exit_px, exit_i = None, None
            for d in range(k, len(D)):
                if d == k + days:
                    exit_px, exit_i = D[d][1], d
                    break
                if stop:
                    if D[d][1] <= stop:
                        exit_px, exit_i = D[d][1], d
                        break
                    if D[d][3] <= stop:
                        exit_px, exit_i = stop, d
                        break
                if spec.get("rsi_exit") and r10[d] is not None and r10[d] > spec["rsi_exit"] and d + 1 < len(D):
                    exit_px, exit_i = D[d + 1][1], d + 1
                    break
            if exit_px is None:
                continue                                   # still open at the end of the data
            tier = tier_at(D, i)
            out.append({"rule": rule, "coin": coin, "t": D[i][0], "exit_t": D[exit_i][0], "state": dial.get(D[i][0], "CLOSED"),
                        "tier": tier, "net": _net(entry, exit_px, tier), "days": days})
            busy_until = exit_i
    return out


def baseline(data: dict, dial: dict, rng: random.Random, n_per: int = 4000) -> dict:
    """Random entries per (state, tier, hold days, period): mean net %."""
    pools: dict = {}
    for coin, D in data.items():
        for i in range(60, len(D) - 31):
            if D[i][0] < START_T:
                continue
            key = (dial.get(D[i][0], "CLOSED"), tier_at(D, i) if i % 7 == 0 else None)
            if key[1] is None:
                continue                                   # tier every 7th day keeps this fast; days are still random within
            pools.setdefault(key, []).append((coin, i))
    out = {}
    for (state, tier), pool in pools.items():
        for days in (10, 30):
            for period in ("DISCOVERY", "CONFIRM"):
                sel = [p for p in pool if (data[p[0]][p[1]][0] < SPLIT_T) == (period == "DISCOVERY")]
                if not sel:
                    continue
                vals = []
                for coin, i in (rng.choice(sel) for _ in range(min(n_per, 3 * len(sel)))):
                    D = data[coin]
                    if i + 1 + days < len(D):
                        vals.append(_net(D[i + 1][1], D[i + 1 + days][1], tier))
                if vals:
                    out[(state, tier, days, period)] = statistics.mean(vals)
    return out


def table(trades: list[dict], base: dict) -> list[dict]:
    rows = []
    for rule in RULES:
        for state in ("OPEN", "CLOSED"):
            for tier in "ABC":
                cell = {"rule": rule, "state": state, "tier": tier}
                ok_all = True
                pooled = []
                for period in ("DISCOVERY", "CONFIRM"):
                    xs = [t for t in trades if t["rule"] == rule and t["state"] == state and t["tier"] == tier and (t["t"] < SPLIT_T) == (period == "DISCOVERY")]
                    b = base.get((state, tier, xs[0]["days"] if xs else 10, period))
                    ex = [t["net"] - b for t in xs] if b is not None else []
                    md = len({t["exit_t"] // DAY for t in xs})
                    sd = statistics.pstdev(ex) if len(ex) > 1 else 0
                    z = statistics.mean(ex) / (sd / math.sqrt(md)) if sd and md else 0
                    cell[period] = {"trades": len(xs), "market_days": md, "mean_net_pct": round(statistics.mean([t["net"] for t in xs]), 2) if xs else None,
                                    "mean_excess_pct": round(statistics.mean(ex), 2) if ex else None, "z": round(z, 2), "baseline_pct": round(b, 2) if b is not None else None}
                    pooled += ex
                d, c = cell["DISCOVERY"], cell["CONFIRM"]
                ok = (d["market_days"] >= MIN_DAYS and (d["mean_excess_pct"] or 0) > 0 and d["z"] >= Z_MIN and (d["mean_net_pct"] or 0) > 0
                      and (c["mean_excess_pct"] or 0) > 0 and (c["mean_net_pct"] or 0) > 0)
                n = d["market_days"] + c["market_days"]
                cell["passes"] = ok
                cell["expected_excess_pct"] = round(statistics.mean(pooled) * n / (n + SHRINK), 2) if ok and pooled else 0.0
                rows.append(cell)
    return rows


def main() -> dict:
    from src.research import reads as R

    data = load()
    btc = data["BTC"]
    B = R.Series(btc)
    dial = dial_map(btc)
    trades = []
    for k, (coin, D) in enumerate(sorted(data.items())):
        if len(D) < 120:
            continue
        trades += simulate(coin, D, B, dial)
        if k % 20 == 0:
            print(f"  {k}/{len(data)} coins, {len(trades)} trades", file=sys.stderr, flush=True)
    base = baseline(data, dial, random.Random(26))
    rows = table(trades, base)
    return {"review": 26, "coins": len(data), "trades": len(trades), "cells": rows,
            "passing": [f"{r['rule']}|{r['state']}|{r['tier']}" for r in rows if r["passes"]]}


if __name__ == "__main__":
    out = main()
    root = Path(__file__).resolve().parents[2]
    (root / "docs" / "research" / "review26.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({"trades": out["trades"], "passing": out["passing"]}))
