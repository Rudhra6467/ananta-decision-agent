"""The sealed loader: the only code allowed to read rows dated 2024-01-01 or later.

A reader names its purpose; the request is checked against the purposes allowed below and written to manifests/sealed_access.jsonl (who, why,
what window, how many rows) before any row is returned. Nothing here lets a study score a rule on the holdout. Allowed purposes:
  paper_lookback  the live paper engine's last few hundred sessions, to compute indicators (200-day average, 14-day range) for a signal on today's close
  paper_context   the engine's market context (Nifty 50 and India VIX against their averages) recorded with each decision
  integrity       selected columns for data checks (duplicates, mappings, stale files, calendar coverage); no returns are computed
  manifest        row counts, last date and file fingerprints for the dataset-version manifest
None of them computes rule performance. A lookback or context request for more than LOOKBACK_DAYS calendar days is refused.

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


def read_index(purpose: str, since: str, names: list[str]) -> pd.DataFrame:
    """Daily index closes for the paper engine's market context (Nifty against its averages, VIX). Same rules as read_cm; purpose paper_context."""
    if purpose not in ALLOWED_CONTEXT:
        raise PermissionError(f"sealed index read refused: purpose {purpose!r} is not on the allowed list {sorted(ALLOWED_CONTEXT)}")
    since_d = pd.Timestamp(since).date()
    if (dt.date.today() - since_d).days > LOOKBACK_DAYS:
        raise PermissionError(f"sealed read refused: window of {(dt.date.today() - since_d).days} days exceeds {LOOKBACK_DAYS}")
    root = paths.data_dir()
    files = [str(p) for p in (root / "silver/kite_index/day/day.parquet", root / "sealed/silver/kite_index/day/day.parquet") if p.exists()]
    con = duckdb.connect()
    df = con.execute(f"select index_name, date, close from read_parquet({files!r}, union_by_name=true) where date >= ? and list_contains(?, index_name)", [since_d, names]).df()
    con.close()
    _log(purpose, "kite_index day " + ",".join(names), since, len(df))
    return df.drop_duplicates(["index_name", "date"], keep="last")


ALLOWED_CONTEXT = {"paper_context"}


ALLOWED_INTEGRITY = {"integrity"}


def read_cols(purpose: str, folder: str, cols: list[str], since: str, where: str = "") -> pd.DataFrame:
    """Selected columns of a sealed silver dataset for data-integrity checks (duplicates, mappings, stale files, calendar). Purpose integrity; logged.
    The integrity checks compute no returns and no rule performance from these rows."""
    if purpose not in ALLOWED_INTEGRITY:
        raise PermissionError(f"sealed column read refused: purpose {purpose!r} is not on the allowed list {sorted(ALLOWED_INTEGRITY)}")
    base = paths.data_dir() / "sealed" / folder
    files = [str(p) for p in sorted(base.glob("**/*.parquet"))]
    if not files:
        return pd.DataFrame(columns=cols)
    con = duckdb.connect()
    df = con.execute(f"select {', '.join(cols)} from read_parquet({files!r}, union_by_name=true) where date >= ? {('and ' + where) if where else ''}", [pd.Timestamp(since).date()]).df()
    con.close()
    _log(purpose, f"{folder} cols {','.join(cols)}", since, len(df))
    return df


def metadata(folder: str, pattern: str, datecol: str | None) -> dict:
    """Row count, last date and a file fingerprint of the sealed copy of a silver dataset, for the dataset manifest. Reads the date column only, no prices."""
    import hashlib

    base = paths.data_dir() / "sealed" / folder
    files = sorted(p for p in base.glob(pattern) if p.is_file()) if base.exists() else []
    if not files:
        return {"files": 0}
    h = hashlib.sha256()
    for p in files:
        st = p.stat()
        h.update(f"{p.relative_to(paths.data_dir())}|{st.st_size}|{st.st_mtime_ns}\n".encode())
    out = {"files": len(files), "fingerprint": h.hexdigest()[:16]}
    pq = [str(p) for p in files if p.suffix == ".parquet"]
    if pq:
        con = duckdb.connect()
        if datecol:
            r = con.execute(f"select count(*), max({datecol}) from read_parquet({pq!r}, union_by_name=true)").fetchone()
            out.update({"rows": int(r[0]), "last": str(r[1])[:10] if r[1] is not None else None})
        else:
            out["rows"] = int(con.execute(f"select count(*) from read_parquet({pq!r}, union_by_name=true)").fetchone()[0])
        con.close()
    _log("manifest", f"metadata {folder}", "-", out.get("rows") or 0)
    return out
