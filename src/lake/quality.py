"""Quality check for one symbol's clean candles: what is missing, doubled or impossible, before any research uses it.

Checked: rows, first and last candle, missing minutes (and the 10 longest gaps), duplicate times, broken candles (high under the
open/close, low over them, a price at or under zero), minutes with no trades, and jumps of 30%+ from one candle to the next.
Grade: A = under 0.1% missing and nothing broken; B = under 1% missing and broken under 0.01%; C = anything worse (research may
use it only with the gap list in hand). Results go to reports/quality/<symbol>.json.

Suspect redenominations (added 2026-10-05 after review #15 found COCOS x1220 and BNX /100): a close 10x or more above, or a
tenth or less of, the previous candle's close. A token swap Binance did not back-adjust looks exactly like this; a real market
move of that size in one candle practically never happens. Any suspect makes the grade C, and the research loader
(src/lake/research.load) refuses a coin with a suspect it has not been told about (its BREAKS list).
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone

from src.lake import root
from src.lake.binance_vision import clean_dir

STEP = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600, "1d": 86400}


def _day(t) -> str | None:
    return datetime.fromtimestamp(int(t), timezone.utc).strftime("%Y-%m-%d %H:%M") if t is not None else None


def check(symbol: str, interval: str = "1m", market: str = "spot", con=None) -> dict:
    import duckdb

    con = con or duckdb.connect()
    step = STEP[interval]
    path = clean_dir(interval, market) / f"symbol={symbol}" / "**" / "*.parquet"
    con.execute(f"CREATE OR REPLACE TEMP VIEW q AS SELECT * FROM read_parquet('{path}', hive_partitioning=true)")
    n, n_distinct, t0, t1 = con.execute("SELECT count(*), count(DISTINCT t), min(t), max(t) FROM q").fetchone()
    if not n:
        return {"symbol": symbol, "rows": 0, "grade": "C", "note": "no data"}
    expected = (t1 - t0) // step + 1
    missing = expected - n_distinct
    gaps = con.execute(f"""
        WITH s AS (SELECT t, lag(t) OVER (ORDER BY t) AS p FROM (SELECT DISTINCT t FROM q))
        SELECT p, t, (t - p) // {step} - 1 AS missing FROM s WHERE t - p > {step} ORDER BY missing DESC LIMIT 10""").fetchall()
    n_gaps = con.execute(f"SELECT count(*) FROM (SELECT t - lag(t) OVER (ORDER BY t) AS d FROM (SELECT DISTINCT t FROM q)) WHERE d > {step}").fetchone()[0]
    broken = con.execute("SELECT count(*) FROM q WHERE h < greatest(o, c) OR l > least(o, c) OR l <= 0 OR o <= 0 OR c <= 0").fetchone()[0]
    no_trades = con.execute("SELECT count(*) FROM q WHERE v = 0").fetchone()[0]
    jumps = con.execute("SELECT count(*) FROM (SELECT c / lag(c) OVER (ORDER BY t) - 1 AS r FROM q) WHERE abs(r) >= 0.30").fetchone()[0]
    suspects = con.execute("""SELECT t, r FROM (SELECT t, c / lag(c) OVER (ORDER BY t) AS r FROM q)
                              WHERE r >= 10 OR r <= 0.1 ORDER BY t""").fetchall()
    miss_pct = 100 * missing / expected
    broken_pct = 100 * broken / n
    grade = "A" if miss_pct < 0.1 and broken == 0 else "B" if miss_pct < 1 and broken_pct < 0.01 else "C"
    if suspects:
        grade = "C"
    out = {"symbol": symbol, "interval": interval, "market": market, "rows": n, "duplicates": n - n_distinct, "first": _day(t0), "last": _day(t1),
           "expected": expected, "missing": missing, "missing_pct": round(miss_pct, 4), "gaps": n_gaps,
           "longest_gaps": [{"from": _day(p), "to": _day(t), "missing": m} for p, t, m in gaps],
           "broken_candles": broken, "no_trade_candles": no_trades, "jumps_30pct": jumps,
           "suspect_redenominations": [{"at": _day(t), "t": int(t), "ratio": round(float(r), 6)} for t, r in suspects], "grade": grade, "checked_at": int(time.time())}
    d = root() / "reports" / "quality"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{market}_{interval}_{symbol}.json").write_text(json.dumps(out, indent=1))
    return out
