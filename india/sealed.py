"""The sealed loader: the only code allowed to read rows dated 2024-01-01 or later.

A reader names its purpose; the request is checked against the purposes allowed below and written to manifests/sealed_access.jsonl (who, why,
what window, how many rows) before any row is returned. Nothing here lets a study score a rule on the holdout: the one allowed purpose today is
`paper_lookback`, which hands the live paper engine the last few hundred sessions so it can compute indicators (200-day average, 14-day range)
for a signal on today's close. It computes no performance from them. A request for more than LOOKBACK_DAYS calendar days is refused.

  from india import sealed
  df = sealed.read_cm("paper_lookback", since="2025-09-01")      raw series-EQ cash rows from sealed/silver + silver
Test: tests grep the repo for direct reads of the sealed folder outside this file (see india/leakcheck.py).
"""
from __future__ import annotations

import datetime as dt
import json

import duckdb
import pandas as pd

from india import paths

ALLOWED = {"paper_lookback"}
LOOKBACK_DAYS = 460


def _log(purpose: str, what: str, since: str, rows: int) -> None:
    line = {"at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "purpose": purpose, "what": what, "since": since, "rows": rows}
    with (paths.manifest_dir() / "sealed_access.jsonl").open("a") as fh:
        fh.write(json.dumps(line) + "\n")


def read_cm(purpose: str, since: str) -> pd.DataFrame:
    if purpose not in ALLOWED:
        raise PermissionError(f"sealed read refused: purpose {purpose!r} is not on the allowed list {sorted(ALLOWED)}")
    since_d = pd.Timestamp(since).date()
    if (dt.date.today() - since_d).days > LOOKBACK_DAYS:
        raise PermissionError(f"sealed read refused: window of {(dt.date.today() - since_d).days} days exceeds {LOOKBACK_DAYS}")
    root = paths.data_dir()
    files = [str(p) for p in list((root / "silver/cm_bhavcopy").glob("year=*/part.parquet")) + list((root / "sealed/silver/cm_bhavcopy").glob("year=*/part.parquet"))]
    con = duckdb.connect()
    df = con.execute(
        f"select date, symbol, series, open, high, low, close, prev_close, volume, turnover, isin from read_parquet({files!r}) where series = 'EQ' and close > 0 and date >= ?",
        [since_d]).df()
    con.close()
    _log(purpose, "cm_bhavcopy EQ", since, len(df))
    return df
