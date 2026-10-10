"""Review #25 (docs/research/REVIEW_25.md): the benchmark (Bitcoin with its 50-day gate) and the exposure dial.

  python -m src.research.review25        -> docs/research/REVIEW_25_RESULTS.md and review25.json
Daily candles from the lake's agent pack (~/ananta_lake/agent/daily.sqlite). Positions change at the next day's open.
"""
from __future__ import annotations

import json
import math
import os
import sqlite3
import statistics
from datetime import datetime, timezone
from pathlib import Path

DAY = 86400
SPLITS = {"DISCOVERY": ("2018-01-01", "2023-12-31"), "CONFIRM": ("2024-01-01", "2099-01-01")}
TARGET_VOL, VOL_N, STEP = 0.40, 30, 0.25


def _t(s: str) -> int:
    return int(datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


def daily(coin: str) -> list[tuple]:
    p = Path(os.path.expanduser(os.getenv("ANANTA_LAKE", "~/ananta_lake"))) / "agent" / "daily.sqlite"
    con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    try:
        return [tuple(r) for r in con.execute("SELECT t, o, h, l, c FROM bars WHERE coin=? ORDER BY t", (coin,))]
    finally:
        con.close()


def ema(x: list[float], n: int) -> list[float | None]:
    out, k, e = [], 2 / (n + 1), None
    for i, v in enumerate(x):
        e = v if e is None else v * k + e * (1 - k)
        out.append(e if i >= n - 1 else None)
    return out


def sma(x: list[float], n: int) -> list[float | None]:
    out, s = [], 0.0
    for i, v in enumerate(x):
        s += v
        if i >= n:
            s -= x[i - n]
        out.append(s / n if i >= n - 1 else None)
    return out


def targets(D: list[tuple], kind: str) -> list[float]:
    """Wanted weight (0..1) after each day's close."""
    c = [b[4] for b in D]
    e50, s200 = ema(c, 50), sma(c, 200)
    out, cur = [], 0.0
    for i in range(len(D)):
        if kind == "HOLD":
            w = 1.0
        else:
            on = e50[i] is not None and c[i] > e50[i]
            if kind == "GATE50_200":
                on = on and s200[i] is not None and c[i] > s200[i]
            w = 1.0 if on else 0.0
            if kind == "GATE50_VOL" and on and i > VOL_N:
                r = [math.log(c[k] / c[k - 1]) for k in range(i - VOL_N + 1, i + 1)]
                vol = statistics.pstdev(r) * math.sqrt(365)
                w = min(1.0, TARGET_VOL / vol) if vol > 0 else 1.0
                if cur > 0 and abs(w - cur) < STEP:
                    w = cur                                     # small changes are not worth their costs
        out.append(w)
        cur = w
    return out


def run(D: list[tuple], w: list[float], cost: float, t0: int, t1: int) -> dict:
    """Equity from t0 to t1: the weight decided at day i's close is held from day i+1's open."""
    eq, peak, mdd, held, trades, rets, days = 1.0, 1.0, 0.0, 0.0, 0, [], 0
    for i in range(1, len(D)):
        t = D[i][0]
        if t < t0 or t > t1:
            continue
        e0 = eq
        eq *= 1 + held * (D[i][1] / D[i - 1][4] - 1)      # yesterday's close -> today's open, on what was held
        want = w[i - 1]
        if want != held:                                   # trade at today's open
            eq *= 1 - cost * abs(want - held)
            trades += 1
            held = want
        eq *= 1 + held * (D[i][4] / D[i][1] - 1)           # today's open -> close
        rets.append(eq / e0 - 1)
        peak = max(peak, eq)
        mdd = min(mdd, eq / peak - 1)
        days += 1
    yrs = days / 365 or 1
    sd = statistics.pstdev(rets) if len(rets) > 1 else 0
    return {"total_pct": round(100 * (eq - 1), 1), "cagr_pct": round(100 * (eq ** (1 / yrs) - 1), 1), "max_drawdown_pct": round(100 * mdd, 1),
            "return_over_drawdown": round((eq ** (1 / yrs) - 1) / abs(mdd), 2) if mdd else None,
            "sharpe": round(statistics.mean(rets) / sd * math.sqrt(365), 2) if sd else None,
            "time_in_market_pct": None, "trades": trades, "days": days}


def main() -> dict:
    from src.intelligence.explorer_engine import HALF_SPREAD, NDAX_FEE

    out: dict = {"review": 25, "splits": SPLITS, "results": {}}
    data = {c: daily(c) for c in ("BTC", "ETH")}
    kinds = ("HOLD", "GATE50", "GATE50_200", "GATE50_VOL")
    for name, (a, b) in SPLITS.items():
        t0, t1 = _t(a), _t(b)
        res = {}
        D = data["BTC"]
        cost = NDAX_FEE + HALF_SPREAD["BTC"]
        for k in kinds:
            w = targets(D, k)
            r = run(D, w, cost, t0, t1)
            r["time_in_market_pct"] = round(100 * sum(1 for i in range(1, len(D)) if t0 <= D[i][0] <= t1 and w[i - 1] > 0) / max(1, r["days"]), 1)
            res[k] = r
        # the pair: half each, each with its own gate (run separately, combine equity daily)
        parts = []
        for c in ("BTC", "ETH"):
            Dc = data[c]
            parts.append(run(Dc, targets(Dc, "GATE50"), NDAX_FEE + HALF_SPREAD[c], t0, t1))
        res["PAIR_GATE50"] = {"total_pct": round((parts[0]["total_pct"] + parts[1]["total_pct"]) / 2, 1),
                              "note": "average of the two gated halves (no rebalancing between them); drawdown not combined",
                              "btc": parts[0], "eth": parts[1]}
        out["results"][name] = res
    verdict = {}
    for k in ("GATE50_200", "GATE50_VOL"):
        ok = []
        for name in SPLITS:
            g, x = out["results"][name]["GATE50"], out["results"][name][k]
            better = (x["return_over_drawdown"] or 0) > (g["return_over_drawdown"] or 0)
            not_much_lower = x["total_pct"] >= g["total_pct"] - 0.2 * abs(g["total_pct"])
            ok.append(better and not_much_lower)
        verdict[k] = "PASS" if all(ok) else "MIXED" if any(ok) else "FAIL"
    out["verdict"] = verdict
    return out


if __name__ == "__main__":
    r = main()
    root = Path(__file__).resolve().parents[2]
    (root / "docs" / "research" / "review25.json").write_text(json.dumps(r, indent=1))
    print(json.dumps(r, indent=1))
