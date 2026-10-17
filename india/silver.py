"""Silver: typed point-in-time tables from bronze, one Parquet file per year, plus the trading calendar (corporate actions: india/actions.py).

  python -m india.silver cm            every complete year of cash bhavcopy (old and UDiFF files share one schema)
  python -m india.silver calendar      trading days from the cash manifest: a file = a trading day, no file = holiday
  python -m india.silver all
Rows dated 2024-01-01 or later are holdout: they go under sealed/silver/, never under silver/, and the catalog's views
read silver/ only (india/catalog.py). Every row carries source (the bronze file's sha256) and ingested_at.
"""
from __future__ import annotations

import datetime as dt
import io
import json
import sys
import zipfile
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from india import nse, paths

CM_COLS = ["date", "symbol", "series", "open", "high", "low", "close", "last", "prev_close", "volume", "turnover", "trades", "isin"]
OLD = {"SYMBOL": "symbol", "SERIES": "series", "OPEN": "open", "HIGH": "high", "LOW": "low", "CLOSE": "close", "LAST": "last",
       "PREVCLOSE": "prev_close", "TOTTRDQTY": "volume", "TOTTRDVAL": "turnover", "TOTALTRADES": "trades", "ISIN": "isin", "TIMESTAMP": "date"}
UDIFF = {"TckrSymb": "symbol", "SctySrs": "series", "OpnPric": "open", "HghPric": "high", "LwPric": "low", "ClsPric": "close",
         "LastPric": "last", "PrvsClsgPric": "prev_close", "TtlTradgVol": "volume", "TtlTrfVal": "turnover", "TtlNbOfTxsExctd": "trades",
         "ISIN": "isin", "TradDt": "date"}
SCHEMA = pa.schema([("date", pa.date32()), ("symbol", pa.string()), ("series", pa.string()), ("open", pa.float64()), ("high", pa.float64()),
                    ("low", pa.float64()), ("close", pa.float64()), ("last", pa.float64()), ("prev_close", pa.float64()),
                    ("volume", pa.int64()), ("turnover", pa.float64()), ("trades", pa.int64()), ("isin", pa.string()),
                    ("source", pa.string()), ("ingested_at", pa.timestamp("s", tz="UTC"))])


def _old_date(s: str) -> dt.date:
    """Old files write 3-NOV-1994 or 05-JUL-2024; a few 2020 files write 13-Jul-20."""
    d, m, y = s.split("-")
    y = int(y)
    return dt.datetime.strptime(f"{d}-{m}-{y + 2000 if y < 100 else y}", "%d-%b-%Y").date()


def parse_cm(path: Path) -> pd.DataFrame:
    """One bronze cash file (old or UDiFF) to the common schema. Rows with no trade (volume 0 and no close) are kept as they came."""
    raw = path.read_bytes()
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        name = z.namelist()[0]
        df = pd.read_csv(io.BytesIO(z.read(name)), dtype=str, keep_default_na=False)
    df.columns = [c.strip() for c in df.columns]
    if "TckrSymb" in df.columns:
        if "Sgmt" in df.columns:
            df = df[df["Sgmt"].str.strip() == "CM"]
        df = df.rename(columns=UDIFF)
        df["date"] = pd.to_datetime(df["date"].str.strip(), format="%Y-%m-%d").dt.date
    else:
        df = df.rename(columns=OLD)
        df["date"] = df["date"].str.strip().map(_old_date)
    for c in CM_COLS:
        if c not in df.columns:
            df[c] = ""
    df = df[CM_COLS].copy()
    for c in ("symbol", "series", "isin"):
        df[c] = df[c].str.strip()
    for c in ("open", "high", "low", "close", "last", "prev_close", "turnover"):
        df[c] = pd.to_numeric(df[c].str.strip().replace("", None), errors="coerce")
    for c in ("volume", "trades"):
        df[c] = pd.to_numeric(df[c].str.strip().replace("", None), errors="coerce").astype("Int64")
    df["isin"] = df["isin"].replace("", None)
    return df


def complete_years(dataset: str = "cm_bhavcopy", until: dt.date | None = None) -> list[int]:
    """Years where every weekday has a manifest line with a file or a recorded no-file."""
    rows = nse.manifest_rows(dataset)
    until = until or dt.date.today() - dt.timedelta(days=1)
    years = sorted({int(d[:4]) for d in rows})
    out = []
    for y in years:
        end = min(dt.date(y, 12, 31), until)
        need = [d.isoformat() for d in nse.weekdays(dt.date(y, 1, 1), end)]
        if need and all(rows.get(d, {}).get("status") in (200, 404) for d in need):
            out.append(y)
    return out


def _year_target(dataset: str, year: int) -> Path:
    root = paths.sealed_dir() / "silver" if year >= int(paths.HOLDOUT_START[:4]) else paths.data_dir() / "silver"
    return root / dataset / f"year={year}" / "part.parquet"


def build_cm_year(year: int) -> dict:
    rows = nse.manifest_rows("cm_bhavcopy")
    frames = []
    now = pd.Timestamp.now(tz="UTC").floor("s")
    for d, r in sorted(rows.items()):
        if r.get("status") != 200 or not d.startswith(str(year)):
            continue
        p = paths.data_dir() / r["path"]
        df = parse_cm(p)
        df["source"] = r["sha256"][:16]
        df["ingested_at"] = now
        frames.append(df)
    if not frames:
        return {"year": year, "rows": 0}
    full = pd.concat(frames, ignore_index=True)
    # the holdout rule by row, not just by year: a 2023 file never holds 2024 rows, but the check is cheap
    if year >= int(paths.HOLDOUT_START[:4]):
        assert (pd.to_datetime(full["date"]) >= pd.Timestamp(paths.HOLDOUT_START)).all()
    out = _year_target("cm_bhavcopy", year)
    out.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pandas(full, schema=SCHEMA, preserve_index=False), out, compression="zstd")
    return {"year": year, "rows": len(full), "files": len(frames), "path": str(out)}


def build_cm(years: list[int] | None = None) -> list[dict]:
    years = years or complete_years()
    out = []
    for y in years:
        r = build_cm_year(y)
        print(r, flush=True)
        out.append(r)
    return out


def build_calendar() -> dict:
    """date, is_trading_day, source for every weekday the cash manifest covers; weekends are not rows."""
    rows = nse.manifest_rows("cm_bhavcopy")
    recs = [{"date": dt.date.fromisoformat(d), "is_trading_day": r.get("status") == 200, "status": r.get("status"), "source": "cm_bhavcopy manifest"}
            for d, r in sorted(rows.items()) if r.get("status") in (200, 404)]
    df = pd.DataFrame(recs)
    out = paths.data_dir() / "silver" / "calendar" / "calendar.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pandas(df, preserve_index=False), out)
    return {"days": len(df), "trading": int(df["is_trading_day"].sum()), "path": str(out)}


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    paths.ensure()
    if what in ("cm", "all"):
        build_cm([int(y) for y in sys.argv[2:]] or None)
    if what in ("calendar", "all"):
        print(build_calendar(), flush=True)
