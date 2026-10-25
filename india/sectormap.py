"""Stock-to-sector map (25 Oct 2026 audit; teacher cards and sector studies need it): NSE's industry label per stock, from dated snapshots of
the index constituent lists, kept forward so the map becomes point in time from the first snapshot on.

  python -m india.sectormap snapshot   today's lists from NSE's archive host -> bronze/indices/<list>_<YYYYMMDD>.csv (manifests/sectormap.jsonl)
  python -m india.sectormap build      silver/reference/industry_labels.parquet (symbol, isin, company, industry, first_seen, last_seen)
                                       sealed/silver/reference/index_membership.parquet (snapshot_date, list, symbol, isin) ; manifests/sectormap_build.json
  python -m india.sectormap coverage   the share of the lab's liquid 250 (last research day) with a label -> manifests/sectormap_coverage.json

NOT POINT IN TIME BEFORE THE FIRST SNAPSHOT (2026-10-17 for the Nifty 500 list, 2026-10-25 for the rest). The industry is NSE's label as
published on the snapshot day: a label used on an older date is a later classification, and a stock that left every list before the snapshot
has no label at all (it reads 'unknown', never dropped: dropping it would keep only survivors). Which list a stock sits in on a snapshot day
says how it did up to that day (2026, inside the holdout), so the membership table lives under sealed/silver and no reader is allowed yet;
the labels table carries only the industry text. as_of() returns the label with a flag saying whether it is point in time.
Source: nsearchives.nseindia.com/content/indices (the quote API with NSE's finer basic-industry field answers 403 from Toronto, 25 Oct).
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import json
import sys

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from india import nse, paths

LISTS = {"nifty50": "ind_nifty50list.csv", "nifty100": "ind_nifty100list.csv", "nifty500": "ind_nifty500list.csv",
         "niftymidcap150": "ind_niftymidcap150list.csv", "niftysmallcap250": "ind_niftysmallcap250list.csv",
         "niftymicrocap250": "ind_niftymicrocap250_list.csv", "niftytotalmarket": "ind_niftytotalmarket_list.csv"}


def parse_list(text: str) -> list[dict]:
    """One NSE constituent CSV -> rows of symbol, isin, company, industry (header: Company Name, Industry, Symbol, Series, ISIN Code)."""
    out = []
    for r in csv.DictReader(io.StringIO(text.lstrip("﻿"))):
        r = {(k or "").strip(): (v or "").strip() for k, v in r.items()}
        if not r.get("Symbol"):
            continue
        out.append({"symbol": r["Symbol"], "isin": r.get("ISIN Code", ""), "company": r.get("Company Name", ""), "industry": r.get("Industry", "") or "unknown"})
    return out


def snapshot(log=print) -> dict:
    paths.ensure()
    f = nse.Fetcher(rate_s=1.0)
    day = dt.date.today()
    out = {}
    for key, fn in LISTS.items():
        status, body, _ = f.get(f"{nse.ARCH}/content/indices/{fn}")
        row = {"list": key, "date": day.isoformat(), "status": status, "bytes": len(body), "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
        rows = parse_list(body.decode("utf-8", "replace")) if status == 200 else []
        if rows:
            p = paths.bronze("indices") / f"{key}_{day:%Y%m%d}.csv"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(body)
            row.update(rows=len(rows), sha256=hashlib.sha256(body).hexdigest(), path=str(p.relative_to(paths.data_dir())))
        with (paths.manifest_dir() / "sectormap.jsonl").open("a") as fh:
            fh.write(json.dumps(row) + "\n")
        out[key] = row.get("rows", f"status {status}")
        log(f"sector map snapshot {key}: {out[key]}")
    return out


def _snapshots() -> pd.DataFrame:
    recs = []
    for key in LISTS:
        for p in sorted(paths.bronze("indices").glob(f"{key}_*.csv")):
            d = pd.to_datetime(p.stem.rsplit("_", 1)[1], format="%Y%m%d")
            for r in parse_list(p.read_text(encoding="utf-8", errors="replace")):
                recs.append({**r, "list": key, "snapshot_date": d})
    return pd.DataFrame(recs)


def build() -> dict:
    df = _snapshots()
    if df.empty:
        return {"rows": 0}
    df = df.sort_values(["snapshot_date", "list", "symbol"])
    lab = (df.groupby(["symbol", "isin"], as_index=False)
             .agg(company=("company", "last"), industry=("industry", "last"), first_seen=("snapshot_date", "min"), last_seen=("snapshot_date", "max"),
                  industries_seen=("industry", lambda s: "|".join(sorted(set(s))))))
    lab["point_in_time_from"] = lab["first_seen"]
    t = paths.data_dir() / "silver" / "reference" / "industry_labels.parquet"
    t.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pandas(lab, preserve_index=False), t)
    mem = df[["snapshot_date", "list", "symbol", "isin"]].drop_duplicates().reset_index(drop=True)
    m = paths.sealed_dir() / "silver" / "reference" / "index_membership.parquet"
    m.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pandas(mem, preserve_index=False), m)
    out = {"labels": int(len(lab)), "industries": int(lab["industry"].nunique()), "snapshots": sorted({str(x.date()) for x in df["snapshot_date"]}),
           "first_snapshot": str(df["snapshot_date"].min().date()), "membership_rows_sealed": int(len(mem)),
           "label_changes_between_snapshots": int((lab["industries_seen"].str.contains("|", regex=False)).sum()),
           "note": "not point in time before first_seen; membership sealed (2026 lists encode holdout survivorship)",
           "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    (paths.manifest_dir() / "sectormap_build.json").write_text(json.dumps(out, indent=1))
    return out


def as_of(day, symbols=None) -> pd.DataFrame:
    """Labels for `day`: symbol, isin, industry and point_in_time (True only when the label was published on or before `day`). Symbols with no
    label come back as 'unknown' so a join never drops them."""
    lab = pd.read_parquet(paths.data_dir() / "silver" / "reference" / "industry_labels.parquet")
    d = pd.Timestamp(day)
    lab = lab.sort_values("first_seen").drop_duplicates("symbol", keep="last")
    lab["point_in_time"] = lab["first_seen"] <= d
    out = lab[["symbol", "isin", "industry", "point_in_time"]]
    if symbols is not None:
        out = pd.DataFrame({"symbol": list(symbols)}).merge(out, on="symbol", how="left")
        out["industry"] = out["industry"].fillna("unknown")
        out["point_in_time"] = out["point_in_time"].fillna(False).astype(bool)
    return out.reset_index(drop=True)


def coverage() -> dict:
    """How much of the lab's liquid universe (top 250 on the last research day, 2023-12-29) and of every stock that was ever in it has a label."""
    u = pd.read_parquet(paths.gold() / "universe" / "u_liq_in.parquet")
    cols = set(u.columns)
    sym = "symbol" if "symbol" in cols else ("sid" if "sid" in cols else None)
    rank = next((c for c in ("liq_rank", "rank") if c in cols), None)
    lab = pd.read_parquet(paths.data_dir() / "silver" / "reference" / "industry_labels.parquet")
    have_sym, have_isin = set(lab["symbol"]), set(lab["isin"])
    last = u["date"].max()
    top = u[(u["date"] == last) & ((u[rank] <= 250) if rank else True)]
    def hit(df):
        keys = df[sym].astype(str)
        return int(sum((k in have_sym) or (k in have_isin) for k in keys))
    ever = u[(u[rank] <= 250)] if rank else u
    ever = ever.drop_duplicates(sym)
    out = {"last_research_day": str(pd.Timestamp(last).date()), "top250_on_that_day": int(len(top)), "top250_labelled": hit(top),
           "ever_in_top250": int(len(ever)), "ever_in_top250_labelled": hit(ever),
           "note": "labels are 2026 snapshots: history before the first snapshot is not point in time, and stocks gone before it are 'unknown'",
           "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    (paths.manifest_dir() / "sectormap_coverage.json").write_text(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    paths.ensure()
    a = sys.argv[1:]
    if a[:1] == ["snapshot"]:
        print(json.dumps(snapshot(), indent=1))
    elif a[:1] == ["build"]:
        print(json.dumps(build(), indent=1, default=str))
    elif a[:1] == ["coverage"]:
        print(json.dumps(coverage(), indent=1, default=str))
    else:
        print(__doc__)
