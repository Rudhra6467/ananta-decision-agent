"""The catalog: india.duckdb, the one file every reader opens.

Views over silver/ (never over sealed/): cm (cash bars), calendar, record_a, record_b, factors; a table cm_adj with the
adjusted close (close divided by the product of every factor whose ex-date is later); a datasets table that says what exists
and how far it reaches; a heartbeats table every job appends to, so Ask Ananta can answer "is the tape alive?" from data.

  python -m india.catalog build
"""
from __future__ import annotations

import datetime as dt
import json
import sys

import duckdb

from india import nse, paths

VIEWS = {
    "cm": "silver/cm_bhavcopy/year=*/part.parquet",
    "calendar": "silver/calendar/calendar.parquet",
    "record_a": "silver/corporate_actions/record_a.parquet",
    "record_b": "silver/corporate_actions/record_b.parquet",
    "factors": "silver/corporate_actions/factors.parquet",
}


def connect(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(paths.catalog_path()), read_only=read_only)


def heartbeat(job: str, ok: bool, note: str = "") -> None:
    con = connect()
    con.execute("create table if not exists heartbeats (job varchar, run_at timestamptz, ok boolean, note varchar)")
    con.execute("insert into heartbeats values (?, ?, ?, ?)", [job, dt.datetime.now(dt.timezone.utc), ok, note[:500]])
    con.close()


def build() -> dict:
    root = paths.data_dir()
    con = connect()
    for name, rel in VIEWS.items():
        p = root / rel
        if "*" in rel or p.exists():
            con.execute(f"create or replace view {name} as select * from read_parquet('{root / rel}')")
    con.execute("""
        create or replace table cm_adj as
        with fx as (select symbol, ex_date, factor from factors where factor is not null and factor > 0)
        select c.date, c.symbol, c.series, c.close, c.volume, c.turnover,
               c.close / coalesce((select exp(sum(ln(f.factor))) from fx f where f.symbol = c.symbol and f.ex_date > c.date), 1.0) as adj_close,
               coalesce((select exp(sum(ln(f.factor))) from fx f where f.symbol = c.symbol and f.ex_date > c.date), 1.0) as cum_factor
        from cm c where c.series = 'EQ'""")
    con.execute("create table if not exists datasets (name varchar, description varchar, first_date date, last_date date, rows bigint, files bigint, built_at timestamptz)")
    con.execute("delete from datasets")
    now = dt.datetime.now(dt.timezone.utc)
    for ds, desc in paths.DATASETS.items():
        rows = nse.manifest_rows(ds) if (paths.manifest_dir() / f"{ds}.jsonl").exists() else {}
        files = [d for d, r in rows.items() if r.get("status") == 200]
        n = None
        if ds == "cm_bhavcopy":
            n = con.execute("select count(*) from cm").fetchone()[0]
        con.execute("insert into datasets values (?, ?, ?, ?, ?, ?, ?)",
                    [ds, desc, min(files) if files else None, max(files) if files else None, n, len(files) if files else None, now])
    out = {"cm_rows": con.execute("select count(*) from cm").fetchone()[0],
           "cm_adj_rows": con.execute("select count(*) from cm_adj").fetchone()[0],
           "cm_years": con.execute("select min(year(date)), max(year(date)) from cm").fetchone(),
           "factors": con.execute("select status, count(*) from factors group by 1 order by 1").fetchall(),
           "datasets": con.execute("select name, first_date, last_date, files from datasets where files is not null").fetchall()}
    con.close()
    heartbeat("catalog.build", True, json.dumps({k: str(v) for k, v in out.items()}))
    return out


if __name__ == "__main__":
    paths.ensure()
    print(json.dumps(build(), default=str, indent=1))
