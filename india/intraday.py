"""Silver 5-minute bars from Kite, rescaled to raw prices day by day. (One Kite row carried a volume beyond bigint; such volumes are kept NULL.)

Kite's candles are adjusted for every split, bonus, dividend and demerger as of the fetch date (I0 registration, 4a), so each
day's bars are multiplied by scale = NSE cash close / Kite daily close for that symbol and day: the intraday shape is Kite's,
the price level is NSE's. Rows keep both: kite_* as fetched and raw_* after the rescale; a day with no NSE close (not series EQ
that day, or a holiday in one source) keeps scale NULL and raw_* NULL rather than a guess.
  python -m india.intraday build      one Parquet per year under silver/kite_5m (2024 on under sealed/silver/kite_5m)
"""
from __future__ import annotations

import datetime as dt
import sys

import duckdb

from india import paths


def build() -> dict:
    root = paths.data_dir()
    con = duckdb.connect()
    con.execute("set threads to 6")
    files = str(paths.bronze("kite_5m") / "*.jsonl.gz")
    cm = f"'{root}/silver/cm_bhavcopy/year=*/part.parquet', '{root}/sealed/silver/cm_bhavcopy/year=*/part.parquet'"
    kd = f"'{root}/silver/kite_day/kite_day.parquet', '{root}/sealed/silver/kite_day/kite_day.parquet'"
    con.execute(f"""
        create or replace table bars as
        with raw as (select symbol, token, fetched_at, unnest(candles) as c
                     from read_json_auto('{files}', format = 'newline_delimited', maximum_object_size = 268435456)),
             typed as (select symbol, token, fetched_at, json_extract_string(c, '$[0]') as ts_text,
                              json_extract(c, '$[1]')::double as kite_open, json_extract(c, '$[2]')::double as kite_high,
                              json_extract(c, '$[3]')::double as kite_low, json_extract(c, '$[4]')::double as kite_close,
                              case when json_extract(c, '$[5]')::double < 1e13 then json_extract(c, '$[5]')::bigint end as kite_volume from raw),
             dedup as (select *, row_number() over (partition by symbol, ts_text order by fetched_at desc) as rn from typed)
        select symbol, token, ts_text, strptime(substr(ts_text, 1, 19), '%Y-%m-%dT%H:%M:%S') as ts, substr(ts_text, 1, 10)::date as date,
               kite_open, kite_high, kite_low, kite_close, kite_volume
        from dedup where rn = 1""")
    con.execute(f"""
        create or replace table scaled as
        with nse as (select date, symbol, close as nse_close from read_parquet([{cm}]) where series = 'EQ'),
             kd as (select date, symbol, close as kite_day_close from read_parquet([{kd}]))
        select b.*, n.nse_close, k.kite_day_close,
               case when n.nse_close > 0 and k.kite_day_close > 0 then n.nse_close / k.kite_day_close end as scale,
               b.kite_open * (n.nse_close / k.kite_day_close) as raw_open, b.kite_high * (n.nse_close / k.kite_day_close) as raw_high,
               b.kite_low * (n.nse_close / k.kite_day_close) as raw_low, b.kite_close * (n.nse_close / k.kite_day_close) as raw_close,
               'kite:' || b.token as source, now() as ingested_at
        from bars b left join nse n on n.symbol = b.symbol and n.date = b.date left join kd k on k.symbol = b.symbol and k.date = b.date""")
    years = [r[0] for r in con.execute("select distinct year(date) from scaled order by 1").fetchall()]
    out = {"rows": con.execute("select count(*) from scaled").fetchone()[0],
           "symbols": con.execute("select count(distinct symbol) from scaled").fetchone()[0],
           "unscaled_rows": con.execute("select count(*) from scaled where scale is null").fetchone()[0],
           "first": str(con.execute("select min(date) from scaled").fetchone()[0]), "years": years}
    hold = int(paths.HOLDOUT_START[:4])
    for y in years:
        target = (paths.sealed_dir() / "silver" if y >= hold else root / "silver") / "kite_5m" / f"year={y}" / "part.parquet"
        target.parent.mkdir(parents=True, exist_ok=True)
        con.execute(f"copy (select * from scaled where year(date) = {y} order by symbol, ts) to '{target}' (format parquet, compression zstd)")
    con.close()
    from india import catalog

    catalog.heartbeat("intraday.build", True, str(out))
    return out


if __name__ == "__main__":
    paths.ensure()
    print(build(), flush=True)
