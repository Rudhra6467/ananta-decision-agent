"""Higher timeframes from the 1-minute base (one source of truth: every 5m, 15m, 1h, 4h and daily candle is built from the
same checked 1-minute candles, so research on any timeframe agrees with every other).

A candle is kept only when at least 80% of its minutes exist (a 5-minute candle needs 4 of 5, a daily candle 1,152 of 1,440);
the share of minutes present is stored with it, so a study can be stricter. Times are the candle's open, UTC seconds.
"""
from __future__ import annotations

from src.lake.binance_vision import clean_dir

FRAMES = {"5m": 300, "15m": 900, "1h": 3600, "4h": 14400, "1d": 86400}
MIN_SHARE = 0.8


def build(symbol: str, frames: tuple = tuple(FRAMES), market: str = "spot", con=None) -> dict:
    import shutil

    import duckdb

    con = con or duckdb.connect()
    con.execute("SET TimeZone='UTC'")
    src = clean_dir("1m", market) / f"symbol={symbol}" / "**" / "*.parquet"
    out = {}
    for f in frames:
        step = FRAMES[f]
        dst = clean_dir(f, market) / f"symbol={symbol}"
        if dst.exists():
            shutil.rmtree(dst)
        dst.mkdir(parents=True, exist_ok=True)
        con.execute(f"""
            COPY (
              SELECT b AS t, arg_min(o, t) AS o, max(h) AS h, min(l) AS l, arg_max(c, t) AS c, sum(v) AS v, sum(qv) AS qv, sum(n) AS n,
                     sum(tbv) AS tbv, count(*) / {step // 60}.0 AS share, year(to_timestamp(b)) AS year
              FROM (SELECT *, (t // {step}) * {step} AS b FROM read_parquet('{src}', hive_partitioning=true))
              GROUP BY b HAVING count(*) >= {MIN_SHARE} * {step // 60} ORDER BY b
            ) TO '{dst}' (FORMAT parquet, PARTITION_BY (year), COMPRESSION zstd, OVERWRITE_OR_IGNORE)""")
        out[f] = con.execute(f"SELECT count(*) FROM read_parquet('{dst}/**/*.parquet')").fetchone()[0]
    return {"symbol": symbol, "candles": out}
