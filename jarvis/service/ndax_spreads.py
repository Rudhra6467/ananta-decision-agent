"""Measured NDAX costs (worker S1, Oct 15): what a paper fill on NDAX really costs, from the worker Mac's minute-by-minute bid
and ask (pulled nightly into ~/ananta_worker_data by worker.pull). Read-only; nothing here trades or changes a cost by itself.

  table(days=14)   per coin: minutes measured, the median and 90th-percentile half-spread (% of the mid), the same on down days
                   (Bitcoin's UTC day -3% or worse, from the worker's Binance mids), the median by hour of day (UTC), NDAX's mid
                   against Binance's mid x USD/CAD (the premium, %), and the cost the books assume per side (registry.cost) next
                   to the measured cost per side (NDAX's 0.20% fee + the median half-spread)
  summary(days)    the short version for the gate, the Evidence page and Ask: coins measured, and which cost more than assumed
The plan's stage S2 (after 14 clean days, about Oct 26): rerun the $500 backtest with each coin's 75th-percentile half-spread;
a coin whose real cost erases its edge leaves the book's list, and Madhav decides. Until then this is evidence, not a setting.
"""
from __future__ import annotations

import sqlite3
import statistics
import time
from pathlib import Path

DEST = Path.home() / "ananta_worker_data"
NDAX_FEE = 0.0020
DOWN_DAY = -0.03
FULL_DAY_MINUTES = 1400                  # a worker day with fewer minutes of NDAX quotes is a part day (the first day, Oct 11, had 392)


def _q(xs: list[float], p: float) -> float | None:
    if not xs:
        return None
    s = sorted(xs)
    return s[min(len(s) - 1, int(p * (len(s) - 1) + 0.5))]


def _pct(x: float | None, nd: int = 3) -> float | None:
    return None if x is None else round(100 * x, nd)


def _days(days: int, dest: Path) -> list[Path]:
    today = time.strftime("%Y-%m-%d", time.gmtime())
    since = time.strftime("%Y-%m-%d", time.gmtime(time.time() - days * 86400))
    return [f for f in sorted(dest.glob("l1_*.sqlite")) if since <= f.name[3:13] < today]


def table(days: int = 14, dest: Path | None = None, cost_fn=None) -> dict:
    dest = dest or DEST
    files = _days(days, dest)
    hs: dict[str, list[float]] = {}
    hs_down: dict[str, list[float]] = {}
    by_hour: dict[str, dict[int, list[float]]] = {}
    prem: dict[str, list[float]] = {}
    down_days = []
    full_days = []
    for f in files:
        con = sqlite3.connect(f"file:{f}?mode=ro", uri=True)
        try:
            if (con.execute("SELECT COUNT(DISTINCT t / 60) FROM ndax").fetchone()[0] or 0) >= FULL_DAY_MINUTES:
                full_days.append(f.name[3:13])
            fx = dict(con.execute("SELECT t / 60, usdcad FROM fx WHERE usdcad > 0").fetchall())
            fx_any = next(iter(fx.values()), None)
            bmid = {(t // 60, c): (b + a) / 2 for t, c, b, a in con.execute("SELECT t, coin, bid, ask FROM binance WHERE bid > 0 AND ask > 0")}
            btc = [m for (_, c), m in sorted(bmid.items()) if c == "BTC"]
            down = bool(btc) and btc[-1] / btc[0] - 1 <= DOWN_DAY
            if down:
                down_days.append(f.name[3:13])
            for t, c, b, a in con.execute("SELECT t, coin, bid, ask FROM ndax WHERE bid > 0 AND ask > bid"):
                mid = (a + b) / 2
                h = (a - b) / 2 / mid
                hs.setdefault(c, []).append(h)
                by_hour.setdefault(c, {}).setdefault(time.gmtime(t).tm_hour, []).append(h)
                if down:
                    hs_down.setdefault(c, []).append(h)
                bm, usd = bmid.get((t // 60, c)), fx.get(t // 60, fx_any)
                if bm and usd:
                    prem.setdefault(c, []).append(mid / (bm * usd) - 1)
        finally:
            con.close()
    rows = []
    for c in sorted(hs):
        med = _q(hs[c], 0.5)
        assumed = None
        if cost_fn:
            try:
                assumed = cost_fn(c)
            except Exception:  # noqa: BLE001
                assumed = None
        measured = NDAX_FEE + med if med is not None else None
        rows.append({"coin": c, "minutes": len(hs[c]), "half_spread_median_pct": _pct(med), "half_spread_p75_pct": _pct(_q(hs[c], 0.75)),
                     "half_spread_p90_pct": _pct(_q(hs[c], 0.9)), "down_days_median_pct": _pct(_q(hs_down.get(c, []), 0.5)),
                     "worst_hour_utc": max(by_hour[c], key=lambda k: statistics.median(by_hour[c][k])) if by_hour.get(c) else None,
                     "premium_vs_binance_pct": _pct(_q(prem.get(c, []), 0.5), 2),
                     "cost_per_side_measured_pct": _pct(measured), "cost_per_side_assumed_pct": _pct(assumed),
                     "dearer_than_assumed": (measured > assumed + 0.0005) if (measured is not None and assumed is not None) else None})
    return {"days": [f.name[3:13] for f in files], "full_days": full_days, "down_days": down_days, "coins": rows,
            "how": "half-spread = (ask - bid) / 2 / mid, once a minute; cost per side = NDAX's 0.20% fee + the median half-spread"}


def summary(days: int = 14, dest: Path | None = None, cost_fn=None) -> dict:
    dest = dest or DEST
    t = table(days, dest, cost_fn)
    dear = [r["coin"] for r in t["coins"] if r["dearer_than_assumed"]]
    full, part = len(t["full_days"]), len(t["days"]) - len(t["full_days"])
    days_words = f"{full} full day{'s' if full != 1 else ''}" + (f" and {part} part day{'s' if part != 1 else ''}" if part else "")
    return {"days_measured": len(t["days"]), "full_days": full, "part_days": part, "coins": len(t["coins"]), "dearer_than_assumed": dear,
            "dear_detail": {r["coin"]: [r["cost_per_side_measured_pct"], r["cost_per_side_assumed_pct"]] for r in t["coins"] if r["dearer_than_assumed"]},
            "line": (f"NDAX measured on {days_words}, {len(t['coins'])} coins; costlier than our model: "
                     f"{', '.join(dear) if dear else 'none'}") if t["days"] else "no worker days pulled yet"}
