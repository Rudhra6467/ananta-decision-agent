"""Security master keyed by ISIN: which NSE symbol an ISIN traded under on each date, and which Kite symbol/token it maps to today.

A company that renames itself keeps its ISIN in the bhavcopy; a symbol can also be reused by a different company later (547 symbols
carry more than one ISIN). So prices are matched on ISIN and date, never on symbol alone.
  silver/security_master/names.parquet   entity, isin, symbol, first_date, last_date, rows           (one row per ISIN-symbol spell)
  silver/security_master/kite.parquet    kite_symbol, kite_token, isin, nse_symbol_now, last_seen   (Kite symbol -> ISIN through the latest cash row)
  python -m india.secmaster build
Kite's instruments file carries no ISIN, so the Kite link goes through the symbol Kite uses today, matched to the cash bhavcopy's latest
EQ row for that symbol. Symbols with no EQ row in the last 30 days of the cash data stay unlinked and are counted, not guessed.
"""
from __future__ import annotations

import json

import duckdb

from india import paths

CM = "silver/cm_bhavcopy/year=*/part.parquet", "sealed/silver/cm_bhavcopy/year=*/part.parquet"


def build() -> dict:
    root = paths.data_dir()
    out_dir = root / "silver" / "security_master"
    out_dir.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    cm = ", ".join(f"'{root / p}'" for p in CM)
    con.execute(f"create view cm as select date, symbol, series, isin from read_parquet([{cm}]) where series = 'EQ' and isin is not null")
    con.execute("""create table names as select isin, symbol, min(date) as first_date, max(date) as last_date, count(*) as rows
                   from cm group by 1, 2""")
    # one company can change ISIN (face-value change, merger share class) while keeping its symbol: link spells of the same symbol
    # that follow each other within 10 days, and spells that share an ISIN, into one entity
    df = con.execute("select * from names order by symbol, first_date").df()
    parent = {i: i for i in df["isin"].unique()}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for _, g in df.groupby("symbol"):
        g = g.sort_values("first_date")
        prev = None
        for r in g.itertuples():
            if prev is not None and (r.first_date - prev.last_date).days <= 10 and r.isin != prev.isin:
                parent[find(r.isin)] = find(prev.isin)
            prev = r
    df["entity"] = df["isin"].map(find)
    con.register("names_df", df)
    con.execute("create or replace table names as select * from names_df")
    con.execute(f"copy (select * from names order by entity, first_date) to '{out_dir / 'names.parquet'}' (format parquet, compression zstd)")
    latest = con.execute("select max(date) from cm").fetchone()[0]
    # Kite instruments: the newest dump, NSE equities only
    dumps = sorted((paths.bronze("kite_instruments")).glob("NSE_*.csv"))
    con.execute(f"""create table kite as select tradingsymbol as kite_symbol, instrument_token as kite_token
                    from read_csv_auto('{dumps[-1]}') where segment = 'NSE' and instrument_type = 'EQ'""")
    con.execute(f"""create table kite_link as
        select k.kite_symbol, k.kite_token, n.isin, n.entity, n.symbol as nse_symbol_now, n.last_date as last_seen
        from kite k left join (select *, row_number() over (partition by symbol order by last_date desc) rn from names) n
          on n.symbol = k.kite_symbol and n.rn = 1 and n.last_date >= date '{latest}' - interval 30 day""")
    con.execute(f"copy (select * from kite_link order by kite_symbol) to '{out_dir / 'kite.parquet'}' (format parquet, compression zstd)")
    res = {
        "isins": con.execute("select count(distinct isin) from names").fetchone()[0],
        "isin_symbol_spells": con.execute("select count(*) from names").fetchone()[0],
        "entities": con.execute("select count(distinct entity) from names").fetchone()[0],
        "isins_merged_into_entities": con.execute("select count(*) from (select entity from names group by 1 having count(distinct isin) > 1)").fetchone()[0],
        "isins_with_renames": con.execute("select count(*) from (select isin from names group by 1 having count(*) > 1)").fetchone()[0],
        "symbols_reused_by_other_isin": con.execute("select count(*) from (select symbol from names group by 1 having count(distinct isin) > 1)").fetchone()[0],
        "kite_equities": con.execute("select count(*) from kite_link").fetchone()[0],
        "kite_linked_to_isin": con.execute("select count(*) from kite_link where isin is not null").fetchone()[0],
        "kite_dump": dumps[-1].name,
    }
    con.close()
    from india import catalog

    catalog.heartbeat("secmaster.build", True, json.dumps(res))
    return res


if __name__ == "__main__":
    paths.ensure()
    print(json.dumps(build(), indent=1))
