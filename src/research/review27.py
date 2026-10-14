"""Review #27 (docs/research/REVIEW_27.md): stops for dip-style buys. Tight vs structural vs disaster-only vs no stop, 10-day time
exit, H07 and 200-day-touch entries on the 120 lake coins, both periods, after costs.

  python -m src.research.review27      -> docs/research/review27.json
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

from src.research.review26 import DAY, SPLIT_T, START_T, _net, load, tier_at

DAYS = 10
VARIANTS = ("TIGHT", "STRUCT", "DISASTER", "NOSTOP")
MIN_DAYS = 30


def entries(S, i: int, r10) -> list[str]:
    out = []
    c, s200 = S.c[i], S.sma200[i]
    if s200 is None:
        return out
    if r10[i] is not None and r10[i] < 30 and c > s200:
        out.append("H07")
    if S.l[i] <= s200 and c >= 0.97 * s200 and any(S.c[k] > 1.05 * (S.sma200[k] or 9e99) for k in range(max(0, i - 20), i)):
        out.append("TOUCH200")
    return out


def run_trade(D, S, k: int, stop: float | None) -> tuple[float, int] | None:
    for d in range(k, len(D)):
        if d == k + DAYS:
            return D[d][1], d
        if stop:
            if D[d][1] <= stop:
                return D[d][1], d
            if D[d][3] <= stop:
                return stop, d
    return None


def simulate(D) -> list[dict]:
    from src.research import reads as R

    S = R.Series(D)
    r10 = R.rsi(S.c, 10)
    out, busy = [], {}
    for i in range(210, len(D) - 1):
        if D[i][0] < START_T:
            continue
        for kind in entries(S, i, r10):
            if busy.get(kind, -1) >= i:
                continue
            k = i + 1
            entry, atr = D[k][1], S.atr[i]
            if not atr:
                continue
            tier = tier_at(D, i)
            stops = {"TIGHT": entry - atr, "STRUCT": min(S.l[max(0, i - 9):i + 1]) - 0.5 * atr, "DISASTER": 0.85 * entry, "NOSTOP": None}
            ends = []
            for v in VARIANTS:
                r = run_trade(D, S, k, stops[v])
                if r is None:
                    break
                ends.append((v, _net(entry, r[0], tier), r[1]))
            if len(ends) < len(VARIANTS):
                continue
            busy[kind] = max(e[2] for e in ends)
            for v, net, xi in ends:
                out.append({"kind": kind, "variant": v, "t": D[i][0], "exit_t": D[xi][0], "tier": tier, "net": net})
    return out


def summary(trades: list[dict]) -> dict:
    res = {}
    for kind in ("H07", "TOUCH200", "ALL"):
        res[kind] = {}
        for v in VARIANTS:
            row = {}
            for period in ("DISCOVERY", "CONFIRM"):
                xs = [t for t in trades if t["variant"] == v and t["tier"] in "AB" and (kind == "ALL" or t["kind"] == kind)
                      and (t["t"] < SPLIT_T) == (period == "DISCOVERY")]
                row[period] = {"trades": len(xs), "market_days": len({t["exit_t"] // DAY for t in xs}),
                               "mean_net_pct": round(statistics.mean([t["net"] for t in xs]), 2) if xs else None,
                               "win_pct": round(100 * sum(t["net"] > 0 for t in xs) / len(xs), 1) if xs else None}
            res[kind][v] = row
    verdict = {}
    for kind in ("H07", "TOUCH200", "ALL"):
        tight = res[kind]["TIGHT"]
        passing = []
        for v in ("STRUCT", "DISASTER", "NOSTOP"):
            r = res[kind][v]
            ok = all(r[p]["market_days"] >= MIN_DAYS and r[p]["mean_net_pct"] is not None and tight[p]["mean_net_pct"] is not None
                     and r[p]["mean_net_pct"] > tight[p]["mean_net_pct"] for p in ("DISCOVERY", "CONFIRM"))
            if ok:
                passing.append(v)
        best = max(passing, key=lambda v: res[kind][v]["CONFIRM"]["mean_net_pct"]) if passing else None
        verdict[kind] = {"passing": passing, "use": best or "TIGHT (no change)"}
    return {"results": res, "verdict": verdict}


def main() -> dict:
    data = load()
    trades = []
    for n, (coin, D) in enumerate(sorted(data.items())):
        if len(D) >= 260:
            trades += simulate(D)
        if n % 30 == 0:
            print(f"  {n}/{len(data)} coins, {len(trades)} rows", file=sys.stderr, flush=True)
    return {"review": 27, "coins": len(data), "rows": len(trades), **summary(trades)}


if __name__ == "__main__":
    out = main()
    (Path(__file__).resolve().parents[2] / "docs" / "research" / "review27.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out["verdict"]))
