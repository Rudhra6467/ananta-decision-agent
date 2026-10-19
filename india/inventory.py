"""Data inventory against the Market Brain spec (19 Oct 2026): what is present, how far back, at what resolution, with what timestamps,
and what is missing, paid or forward-only. Re-run any time; nothing here scores a rule.

  python -m india.inventory        writes manifests/data_inventory.json and registrations/data_inventory.md

Counts come from the lake itself (research side, pre-2024 rows; holdout rows are counted through sealed.metadata only, never read).
"""
from __future__ import annotations

import datetime as dt
import glob
import gzip
import json
from pathlib import Path

import duckdb
import pandas as pd

from india import lineage, paths

D = paths.data_dir()


def _q(sql: str):
    con = duckdb.connect()
    try:
        return con.execute(sql).fetchall()
    finally:
        con.close()


def intraday_stocks() -> dict:
    """5-minute stock bars (Kite): symbols per year, and how much of each year's point-in-time liquid top 250 they cover.
    Kite serves only instruments listed today, so names delisted or renamed before the pull are missing: that is survivorship in the
    intraday set (daily bhavcopy keeps them)."""
    f5 = str(D / "silver/kite_5m/year=*/part.parquet")
    per = _q(f"select year, count(distinct symbol), count(*) from read_parquet('{f5}') group by year order by year")
    syms = {r[0]: set() for r in per}
    for y, s in _q(f"select distinct year, symbol from read_parquet('{f5}')"):
        syms[y].add(s)
    u = pd.read_parquet(D / "gold/universe/u_liq_in.parquet", columns=["date", "symbol", "top50", "top250"])
    u["year"] = pd.to_datetime(u["date"]).dt.year
    cov = {}
    for y in sorted(syms):
        x = u[u["year"] == y]
        t250 = set(x.loc[x["top250"], "symbol"])
        t50 = set(x.loc[x["top50"], "symbol"])
        cov[int(y)] = {"symbols": len(syms[y]), "top250_names_that_year": len(t250), "top250_covered": round(len(t250 & syms[y]) / max(len(t250), 1), 3),
                       "top50_covered": round(len(t50 & syms[y]) / max(len(t50), 1), 3)}
    return {"by_year": cov, "bars": int(sum(r[2] for r in per)), "resolution": "5 minute, with volume", "first": "2015-02-02", "last_research": "2023-12-29"}


def index_minutes() -> dict:
    f = str(D / "silver/kite_index/minute/**/*.parquet")
    rows = _q(f"select index_name, min(ts), max(ts), count(distinct cast(ts as date)) from read_parquet('{f}', union_by_name=true) group by index_name order by index_name")
    return {r[0]: {"first": str(r[1])[:10], "last_research": str(r[2])[:10], "days": int(r[3])} for r in rows}


def announcements_timestamps() -> dict:
    a = pd.read_parquet(D / "silver/pr/announcements.parquet", columns=["date", "category"])
    has_time = pd.api.types.is_datetime64_any_dtype(a["date"]) and (pd.to_datetime(a["date"]).dt.time.astype(str) != "00:00:00").any()
    a = a[a["category"] != "nav"]
    yr = pd.to_datetime(a["date"]).dt.year
    return {"rows_ex_nav": int(len(a)), "first": str(pd.to_datetime(a["date"]).min().date()), "last": str(pd.to_datetime(a["date"]).max().date()),
            "time_of_day": bool(has_time), "per_year": {int(k): int(v) for k, v in yr.value_counts().sort_index().items()},
            "categories": a["category"].value_counts().to_dict()}


def results_timestamps() -> dict:
    fs = sorted(glob.glob(str(D / "bronze/results_index/*/*.json")))
    sample = {}
    for f in fs[-3:]:
        try:
            raw = json.loads(Path(f).read_text())
            rows = raw.get("data", raw) if isinstance(raw, dict) else raw
            if rows:
                sample = {k: v for k, v in rows[0].items() if any(t in k.lower() for t in ("dt", "date", "time"))}
                break
        except Exception:
            continue
    return {"files": len(fs), "timestamp_fields_sample": sample}


def recorder() -> dict:
    base = D / "bronze/kite_1m_fo"
    exp = sorted(p.name for p in base.iterdir() if p.is_dir()) if base.exists() else []
    n = sum(1 for _ in base.glob("*/*.jsonl.gz")) if base.exists() else 0
    depth = sorted({p.parent.name for p in (D / "bronze/kite_depth").glob("date=*/*.jsonl.gz")}) if (D / "bronze/kite_depth").exists() else []
    return {"expiry_folders": exp, "contract_files": n, "depth_days": depth}


def run() -> dict:
    vers = lineage._latest_versions()
    ds = {k: {x: v.get(x) for x in ("files", "rows", "first", "last", "sealed_files", "sealed_last")} for k, v in vers.items()}
    out = {"at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "datasets": ds, "intraday_stocks": intraday_stocks(),
           "index_minutes": index_minutes(), "announcements": announcements_timestamps(), "results_index": results_timestamps(), "recorder": recorder()}
    (paths.manifest_dir() / "data_inventory.json").write_text(json.dumps(out, indent=1, default=str))
    return out


if __name__ == "__main__":
    r = run()
    print(json.dumps({k: v for k, v in r.items() if k != "datasets"}, indent=1, default=str)[:6000])
