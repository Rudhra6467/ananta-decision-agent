"""The exposure dial (engine fix 1, review #25): how much of the account may be in the market today, decided by market state
alone, before any setup is looked at. Setups then only choose which coins fill what the dial allows.

  dial v1     GATE50_200: Bitcoin's daily close above BOTH its 50-day and 200-day averages -> 100%, else 0% (review #25: the best
              return per unit of fall in 2018-2023 and 2024-2026)
  challenger  GATE50_VOL: the 50-day gate, sized to 40% yearly volatility (passed too, behind v1); runs beside it on paper
  benchmark   GATE50: Bitcoin above its 50-day average. The hurdle: every Ananta strategy must beat it after costs over the
              same days, or it is the live strategy (Universe Rule v2, section 8)

Paper books of the four (HOLD as the reference), from the day the dial started (2026-10-10), on the universe feed's Bitcoin daily
candles, with NDAX costs: the live scoreboard every other book is compared with.

  state(j)    the dial now, the challenger's weight, the benchmark, and why
  books(j)    each paper book since the start: return, worst fall, days in the market
Paper only.
"""
from __future__ import annotations

import math
import statistics
import time
from datetime import datetime, timezone

START = "2026-10-10"
BOOKS = ("HOLD", "GATE50", "GATE50_200", "GATE50_VOL")
ROLE = {"GATE50_200": "dial v1", "GATE50_VOL": "challenger", "GATE50": "benchmark (the hurdle)", "HOLD": "reference"}
_CACHE: dict = {"t": 0, "v": None}


def _btc(j) -> list[tuple]:
    from jarvis.service import feed

    return [(t, o, h, l, c) for t, o, h, l, c, v in feed.daily(j, "BTC")]


def state(j) -> dict:
    from src.research import review25 as R

    if _CACHE["v"] and time.time() - _CACHE["t"] < 600:
        return _CACHE["v"]
    D = _btc(j)
    if len(D) < 210:
        return {"dial": None, "note": "not enough Bitcoin history in the feed yet"}
    c = [b[4] for b in D]
    e50, s200 = R.ema(c, 50)[-1], R.sma(c, 200)[-1]
    w = {k: R.targets(D, k)[-1] for k in BOOKS}
    r = [math.log(c[k] / c[k - 1]) for k in range(len(c) - R.VOL_N, len(c))]
    vol = statistics.pstdev(r) * math.sqrt(365)
    day = datetime.fromtimestamp(D[-1][0], timezone.utc).strftime("%Y-%m-%d")
    dial = w["GATE50_200"]
    why = [f"Bitcoin closed {day} at {c[-1]:,.0f}", f"{'above' if c[-1] > e50 else 'below'} its 50-day average ({e50:,.0f})",
           f"{'above' if c[-1] > s200 else 'below'} its 200-day average ({s200:,.0f})"]
    out = {"dial": dial, "dial_words": "OPEN: buying allowed" if dial > 0 else "CLOSED: no new buys; cash is the position",
           "why": why, "challenger_weight": round(w["GATE50_VOL"], 2), "benchmark_in": w["GATE50"] > 0, "btc_vol_30d_pct": round(100 * vol, 1),
           "as_of_day": day, "rule": "review #25: dial v1 = Bitcoin above its 50-day and 200-day averages"}
    _CACHE.update(t=time.time(), v=out)
    return out


def books(j, start: str = START) -> dict:
    from src.intelligence.explorer_engine import HALF_SPREAD, NDAX_FEE
    from src.research import review25 as R

    D = _btc(j)
    if len(D) < 210:
        return {"books": [], "note": "not enough history"}
    t0 = R._t(start)
    out = []
    for k in BOOKS:
        r = R.run(D, R.targets(D, k), NDAX_FEE + HALF_SPREAD["BTC"], t0, 4_102_444_800)
        out.append({"book": k, "role": ROLE[k], "return_pct": r["total_pct"], "worst_fall_pct": r["max_drawdown_pct"], "trades": r["trades"], "days": r["days"]})
    return {"since": start, "books": out,
            "how_to_read": "Paper books on Bitcoin's daily candles since the dial started. Every other book is judged against the benchmark "
                           "over the same days; the dial must keep beating it to stay."}


def dial_by_day(j) -> dict[str, float]:
    """The dial in force on each UTC day: decided on the previous day's close (no peeking), so a day's buys follow yesterday's close."""
    from src.research import review25 as R

    D = _btc(j)
    if len(D) < 210:
        return {}
    w = R.targets(D, "GATE50_200")
    out = {}
    for k in range(1, len(D)):
        out[datetime.fromtimestamp(D[k][0], timezone.utc).strftime("%Y-%m-%d")] = w[k - 1]
    out[datetime.fromtimestamp(D[-1][0] + 86400, timezone.utc).strftime("%Y-%m-%d")] = w[-1]
    return out


def hurdle_since(j, t0: int) -> float | None:
    """The benchmark's return (%) from t0 to now: what a strategy started at t0 must beat."""
    from src.intelligence.explorer_engine import HALF_SPREAD, NDAX_FEE
    from src.research import review25 as R

    D = _btc(j)
    if len(D) < 210:
        return None
    return R.run(D, R.targets(D, "GATE50"), NDAX_FEE + HALF_SPREAD["BTC"], int(t0), 4_102_444_800)["total_pct"]
