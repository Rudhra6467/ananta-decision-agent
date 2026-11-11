"""Price and history charts behind a tap, for both markets (Madhav, 10 Nov 2026 19:09 Toronto: "the 4 objects in 2 boxes from home tab
has to show their respective charts ... with more filters like 1D,5D,1M,3M,6M and timeframes of 5M,15M,30M,1H,4H,1D").

One rule for both markets: a range is how far back, a timeframe is one candle. A pair is offered when it draws 4 to 300 candles on a phone,
so 1D with 5-minute candles works and 6M with 5-minute candles is greyed out. The app asks /v3/candles/<name>?range=&tf= and draws what
comes back (src/place.tsx PriceChart). A history line (the stocks, the options line, the coins, the cash) is one point a session or a night,
with ranges that fit the days on record and ALL.

  pick(market, range, tf)     the range and timeframe to draw, and the timeframes offered for that range
  agg(bars, key)              candles merged by a key (India's 4-hour candles from hourly ones)
  shape(...)                  the answer the app draws: candles, first and last, the change over the range, high and low
  history(...)                the same answer for a line of (day, value) points
"""
from __future__ import annotations

import datetime as dt
from typing import Callable, Iterable

RANGES = ("1D", "5D", "1M", "3M", "6M")
TFS = ("5M", "15M", "30M", "1H", "4H", "1D")
DAYS = {"1D": 1, "5D": 5, "1M": 30, "3M": 91, "6M": 182}             # calendar days back (crypto trades every day)
SESSIONS = {"1D": 1, "5D": 5, "1M": 21, "3M": 63, "6M": 125}         # trading sessions back (India)
PER_DAY = {"india": {"5M": 75, "15M": 25, "30M": 13, "1H": 7, "4H": 2, "1D": 1},          # 09:15 to 15:30, 375 minutes
           "crypto": {"5M": 288, "15M": 96, "30M": 48, "1H": 24, "4H": 6, "1D": 1}}
LO, HI, AIM = 4, 300, 80
TF_MIN = {"5M": 5, "15M": 15, "30M": 30, "1H": 60, "4H": 240, "1D": 1440}
TF_WORDS = {"5M": "5-minute", "15M": "15-minute", "30M": "30-minute", "1H": "hourly", "4H": "4-hour", "1D": "daily"}
RANGE_WORDS = {"1D": "over the day", "5D": "over 5 days", "1M": "over a month", "3M": "over 3 months", "6M": "over 6 months", "ALL": "since the start"}


def count(market: str, rng: str, tf: str) -> int:
    back = SESSIONS if market == "india" else DAYS
    return PER_DAY["india" if market == "india" else "crypto"][tf] * back[rng]


def offered(market: str, rng: str) -> list[str]:
    return [tf for tf in TFS if LO <= count(market, rng, tf) <= HI]


def pick(market: str, rng: str | None, tf: str | None) -> tuple[str, str, list[str]]:
    """The range and timeframe to draw: an unknown range is 1D; a timeframe not offered for the range is the one nearest 80 candles."""
    r = str(rng or "1D").upper()
    r = r if r in RANGES else "1D"
    ok = offered(market, r)
    t = str(tf or "").upper()
    if t not in ok:
        t = min(ok, key=lambda x: abs(count(market, r, x) - AIM))
    return r, t, ok


def agg(bars: list[list], key: Callable[[list], object]) -> list[list]:
    """[t, o, h, l, c] candles merged where key() is the same: the first open, the highest high, the lowest low, the last close."""
    out: list[list] = []
    last = object()
    for b in bars:
        k = key(b)
        if out and k == last:
            o = out[-1]
            o[2], o[3], o[4] = max(o[2], b[2]), min(o[3], b[3]), b[4]
        else:
            out.append(list(b[:5]))
            last = k
    return out


def _r(x: float) -> float:
    return round(float(x), 2 if abs(x) < 1000 else 1)


def shape(name: str, market: str, rng: str, tf: str, ok: list[str], bars: Iterable[list], *, kind: str = "candles", ccy: str = "", tz_min: int = 0,
          ranges: Iterable[str] = RANGES, live: bool = False, note: str = "", words: str = "", fell_back: str = "", base: float | None = None) -> dict:
    bs = [[int(b[0]), _r(b[1]), _r(b[2]), _r(b[3]), _r(b[4])] for b in bars if b and b[4] is not None]
    out = {"name": name, "market": market, "kind": kind, "ccy": ccy, "range": rng, "tf": tf, "ranges": list(ranges),
           "tfs": [{"id": t, "ok": t in ok} for t in TFS] if kind == "candles" else [], "tz_min": tz_min, "intraday": tf != "1D", "bars": bs,
           "live": live, "note": note, "words": words}
    if fell_back:
        out["fell_back"] = fell_back
    if bs:
        first = float(base) if isinstance(base, (int, float)) and base else (bs[0][1] if kind == "candles" else bs[0][4])
        last = bs[-1][4]
        out.update({"first": first, "last": last, "hi": max(b[2] for b in bs), "lo": min(b[3] for b in bs), "change": _r(last - first),
                    "change_pct": round(100 * (last / first - 1), 2) if first else None, "over": RANGE_WORDS.get(rng, "")})
    return out


def before(all_bars: list[list], kept: list[list]) -> float | None:
    """The close just before the first kept candle: the base the change is counted from (on 1D, the previous session's close)."""
    if not kept or not all_bars:
        return None
    i = next((k for k, b in enumerate(all_bars) if b[0] == kept[0][0]), 0)
    return float(all_bars[i - 1][4]) if i > 0 else None


def day_t(day: str, hour: int = 0, tz_min: int = 0) -> int:
    """A date's midnight (or an hour of it) as epoch seconds in a market's own clock."""
    d = dt.date.fromisoformat(str(day)[:10])
    return int(dt.datetime(d.year, d.month, d.day, hour, tzinfo=dt.timezone(dt.timedelta(minutes=tz_min))).timestamp())


def history(name: str, market: str, points: list[tuple[str, float]], rng: str | None, *, ccy: str, per: str = "session", tz_min: int = 0,
            note: str = "", words: str = "", neutral: bool = False) -> dict:
    """A line of (day, value) points with the ranges its record can fill: 5D, 1M, 3M or 6M when the record is longer, and ALL."""
    pts = [(d, float(v)) for d, v in points if isinstance(v, (int, float))]
    back = SESSIONS if per == "session" else DAYS
    ranges = [r for r in ("5D", "1M", "3M", "6M") if back[r] < len(pts) - 1] + ["ALL"]
    r = str(rng or "ALL").upper()
    r = r if r in ranges else "ALL"
    keep = pts if r == "ALL" else pts[-(back[r] + 1):]
    bars = [[day_t(d, 0, tz_min) if len(str(d)) >= 10 else 0, v, v, v, v] for d, v in keep]
    out = shape(name, market, r, "1D", ["1D"], bars, kind="line", ccy=ccy, tz_min=tz_min, ranges=ranges, note=note, words=words)
    if neutral:                    # cash or coins held: a buy moves money between them, so a fall is not a loss (no green or red)
        out["neutral"] = True
    return out
