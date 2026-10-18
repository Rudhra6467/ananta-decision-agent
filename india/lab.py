"""Lab tables from silver (development and validation years only; sealed/ is never read here): the liquid universe and the daily features.

  python -m india.lab universe     gold/universe/u_liq_in.parquet
  python -m india.lab features     gold/features/daily.parquet   (needs the universe)
  python -m india.lab all
Security key `sid`: the company entity from the ISIN master where the cash row has an ISIN (2011 on), else the symbol. Prices are adjusted
with the catalog's cumulative corporate-action factor, so returns are continuous across splits and bonuses.

Data-quality rule: a bhavcopy row with zero open/high/low (no trade that day) keeps its close and takes the close as open, high and low (found by the exit harness: a zero low looked like a -100% stop-out).

Leak rule: every column on a row dated t uses data up to and including the close of t and nothing later. A study that acts on a row acts at the
next session's open (t+1). Forward returns and exits are never stored here; the exit harness computes them from prices after the entry.

Universe U_LIQ-IN: on each date, stocks ranked by the 60-session median of daily rupee turnover (series EQ), requiring at least 126 sessions of
history and a close above Rs 10; `rank` 1 is the most liquid. Flags: top50, top100, top250, top500.
"""
from __future__ import annotations

import sys

import duckdb

from india import catalog, paths

CM = "silver/cm_bhavcopy/year=*/part.parquet"
NAMES = "silver/security_master/names.parquet"
DELIV = "silver/delivery/year=*/part.parquet"


def _con() -> duckdb.DuckDBPyConnection:
    root = paths.data_dir()
    con = duckdb.connect()
    con.execute("set threads to 6")
    con.execute(f"""create view ent as select distinct isin, entity from read_parquet('{root / NAMES}')""")
    con.execute(f"""
        create view cm as select date, symbol, series,
               case when open > 0 then open else close end as open, case when high > 0 then high else close end as high, case when low > 0 then low else close end as low,
               close, prev_close, volume, turnover, isin from read_parquet('{root / CM}') where series = 'EQ' and close > 0
               and coalesce(isin, '') not like 'INF%'
               and symbol not in (select distinct symbol from read_parquet('{root / CM}') where isin like 'INF%')""")
    cat = catalog.connect(read_only=True)
    cf = cat.execute("select date, symbol, cum_factor from cm_adj").df()
    cat.close()
    con.register("cf_df", cf)
    con.execute("create table cf as select * from cf_df")
    con.execute("""
        create table base as
        select c.date, coalesce(e.entity, c.symbol) as sid, c.symbol, c.open / f.cum_factor as o, c.high / f.cum_factor as h, c.low / f.cum_factor as l,
               c.close / f.cum_factor as c, c.close as raw_close, c.volume, c.turnover
        from cm c join cf f on f.date = c.date and f.symbol = c.symbol left join ent e on e.isin = c.isin
        qualify row_number() over (partition by c.date, coalesce(e.entity, c.symbol) order by c.turnover desc) = 1""")
    return con


def build_universe(con=None) -> dict:
    con = con or _con()
    out = paths.gold() / "universe"
    out.mkdir(parents=True, exist_ok=True)
    con.execute("""
        create or replace table uni as
        with b as (select date, sid, symbol, raw_close, turnover, row_number() over (partition by sid order by date) as n from base),
             m as (select *, quantile_cont(turnover, 0.5) over (partition by sid order by date rows between 59 preceding and current row) as med60 from b)
        select date, sid, symbol, med60, n as sessions, rank() over (partition by date order by med60 desc) as rank
        from m where n >= 126 and raw_close > 10""")
    con.execute("alter table uni add column top50 boolean; alter table uni add column top100 boolean; alter table uni add column top250 boolean; alter table uni add column top500 boolean")
    con.execute("update uni set top50 = rank <= 50, top100 = rank <= 100, top250 = rank <= 250, top500 = rank <= 500")
    con.execute(f"copy (select * from uni order by date, rank) to '{out / 'u_liq_in.parquet'}' (format parquet, compression zstd)")
    res = {"rows": con.execute("select count(*) from uni").fetchone()[0], "dates": con.execute("select count(distinct date) from uni").fetchone()[0],
           "first": str(con.execute("select min(date) from uni").fetchone()[0]), "last": str(con.execute("select max(date) from uni").fetchone()[0]),
           "median_name_count_top500": con.execute("select median(k) from (select count(*) k from uni where top500 group by date)").fetchone()[0]}
    return res


def build_features(con=None) -> dict:
    con = con or _con()
    root = paths.data_dir()
    if con.execute("select count(*) from information_schema.tables where table_name = 'uni'").fetchone()[0] == 0:
        con.execute(f"create table uni as select * from read_parquet('{paths.gold() / 'universe' / 'u_liq_in.parquet'}')")
    con.execute(f"create view dl as select date, symbol, deliv_pct from read_parquet('{root / DELIV}') where series = 'EQ' qualify row_number() over (partition by date, symbol order by traded_qty desc) = 1")
    out = paths.gold() / "features"
    out.mkdir(parents=True, exist_ok=True)
    con.execute("""
        create or replace table feat as
        with w as (
          select date, sid, symbol, o, h, l, c, volume, turnover,
                 lag(c) over s as pc,
                 c / lag(c, 1) over s - 1 as ret_1, c / lag(c, 5) over s - 1 as ret_5, c / lag(c, 20) over s - 1 as ret_20, c / lag(c, 60) over s - 1 as ret_60,
                 greatest(h - l, abs(h - lag(c) over s), abs(l - lag(c) over s)) as tr,
                 avg(c) over (partition by sid order by date rows between 19 preceding and current row) as sma20,
                 avg(c) over (partition by sid order by date rows between 49 preceding and current row) as sma50,
                 avg(c) over (partition by sid order by date rows between 199 preceding and current row) as sma200,
                 max(h) over (partition by sid order by date rows between 20 preceding and 1 preceding) as hh20,
                 min(l) over (partition by sid order by date rows between 20 preceding and 1 preceding) as ll20,
                 avg(volume) over (partition by sid order by date rows between 20 preceding and 1 preceding) as vol_avg20 
          from base window s as (partition by sid order by date)),
        x as (select *, avg(tr) over (partition by sid order by date rows between 13 preceding and current row) as atr14,
                     stddev_samp(ret_1) over (partition by sid order by date rows between 19 preceding and current row) as rv20 from w)
        select x.date, x.sid, x.symbol, u.rank as liq_rank, o, h, l, c, volume, turnover, ret_1, ret_5, ret_20, ret_60,
               o / pc - 1 as gap_pct, (h - l) / c as range_pct, atr14, atr14 / c as atr_pct, rv20,
               volume / nullif(vol_avg20, 0) as vol_ratio20, c / sma20 - 1 as dist_sma20, c / sma50 - 1 as dist_sma50, c / sma200 - 1 as dist_sma200,
               c > hh20 as breakout20, c < ll20 as breakdown20, (c - ll20) / nullif(hh20 - ll20, 0) as pos20, d.deliv_pct
        from x join uni u on u.date = x.date and u.sid = x.sid and u.top500
        left join dl d on d.date = x.date and d.symbol = x.symbol""")
    con.execute(f"copy (select * from feat order by date, liq_rank) to '{out / 'daily.parquet'}' (format parquet, compression zstd)")
    dup = con.execute("select count(*) - count(distinct (date, sid)) from feat").fetchone()[0]
    assert dup == 0, f"{dup} duplicate (date, sid) rows in features"
    return {"rows": con.execute("select count(*) from feat").fetchone()[0], "first": str(con.execute("select min(date) from feat").fetchone()[0]),
            "last": str(con.execute("select max(date) from feat").fetchone()[0]),
            "null_share": {c: round(con.execute(f"select avg(({c} is null)::int) from feat").fetchone()[0], 4) for c in ("ret_60", "atr14", "dist_sma200", "vol_ratio20", "deliv_pct")}}


def build_ca_flags(con=None) -> dict:
    """gold/ca_flags.parquet: (sid, date) of corporate-action events that were NOT applied because the price does not confirm them (india.actions.confirm).
    The exit harness skips any window that crosses one, and counts it."""
    con = con or _con()
    fx = str(paths.data_dir() / "silver/corporate_actions/factors.parquet")
    out = paths.gold() / "ca_flags"
    out.mkdir(parents=True, exist_ok=True)
    con.execute(f"""create or replace table caf as
        select distinct b.sid, f.ex_date as date, f.status, f.factor, f.raw_gap_cc from read_parquet('{fx}') f
        join (select distinct sid, symbol from base) b on b.symbol = f.symbol where f.inside and not f.apply""")
    con.execute(f"copy (select * from caf order by sid, date) to '{out / 'ca_flags.parquet'}' (format parquet)")
    return {"ambiguous_events": con.execute("select count(*) from caf").fetchone()[0]}


def build_bars(con=None) -> dict:
    """Adjusted daily bars for every stock that was ever in the top 500, all dates (the exit harness needs the days after a signal too)."""
    con = con or _con()
    if con.execute("select count(*) from information_schema.tables where table_name = 'uni'").fetchone()[0] == 0:
        con.execute(f"create table uni as select * from read_parquet('{paths.gold() / 'universe' / 'u_liq_in.parquet'}')")
    out = paths.gold() / "bars"
    out.mkdir(parents=True, exist_ok=True)
    con.execute("create or replace table bars as select b.date, b.sid, b.o, b.h, b.l, b.c, b.volume from base b where b.sid in (select distinct sid from uni where top500)")
    con.execute(f"copy (select * from bars order by sid, date) to '{out / 'adj_daily.parquet'}' (format parquet, compression zstd)")
    return {"rows": con.execute("select count(*) from bars").fetchone()[0], "sids": con.execute("select count(distinct sid) from bars").fetchone()[0],
            "last": str(con.execute("select max(date) from bars").fetchone()[0])}


def audit() -> dict:
    """Sanity counts on the adjusted bars the studies stand on. Anything non-zero is listed in the study notes, never silently fixed."""
    con = duckdb.connect()
    b = paths.gold() / "bars" / "adj_daily.parquet"
    q = lambda sql: con.execute(sql).fetchone()[0]
    src = f"read_parquet('{b}')"
    res = {
        "rows": q(f"select count(*) from {src}"),
        "low_gt_high": q(f"select count(*) from {src} where l > h + 1e-9"),
        "open_or_close_outside_range": q(f"select count(*) from {src} where o > h + 1e-9 or o < l - 1e-9 or c > h + 1e-9 or c < l - 1e-9"),
        "nonpositive_price": q(f"select count(*) from {src} where o <= 0 or h <= 0 or l <= 0 or c <= 0"),
        "close_to_close_move_over_40pct": q(f"select count(*) from (select c / lag(c) over (partition by sid order by date) - 1 as r from {src}) where abs(r) > 0.4"),
        "close_to_close_move_over_90pct": q(f"select count(*) from (select c / lag(c) over (partition by sid order by date) - 1 as r from {src}) where abs(r) > 0.9"),
    }
    con.close()
    return res


if __name__ == "__main__":
    paths.ensure()
    what = sys.argv[1]
    con = _con()
    if what in ("universe", "all"):
        print(build_universe(con), flush=True)
    if what in ("features", "all"):
        print(build_features(con), flush=True)
    if what == "audit":
        print(audit(), flush=True)
        sys.exit(0)
    if what in ("bars", "all"):
        print(build_bars(con), flush=True)
    if what in ("ca_flags", "all"):
        print(build_ca_flags(con), flush=True)
    catalog.heartbeat("lab." + what, True, "")
