"""Silver delivery: NSE's security-wise delivery position, two bronze formats into one table.

  MTO .DAT (2003 to 2019): header lines, then rows "20,<sr>,<symbol>,<series>,<traded qty>,<deliverable qty>,<pct>"
  sec_bhavdata_full (2020 on): a csv with prices too (PREV_CLOSE, OPEN, HIGH, LOW, LAST, CLOSE, AVG, qty, turnover in lakhs,
                               trades, DELIV_QTY, DELIV_PER); the prices are the raw second record for the cash bars' spot checks.
  python -m india.delivery build        every complete year; 2024 on goes to sealed/silver/delivery
"""
from __future__ import annotations

import datetime as dt
import io
import sys
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from india import nse, paths, silver

COLS = ["date", "symbol", "series", "traded_qty", "deliverable_qty", "deliv_pct", "prev_close", "open", "high", "low", "last", "close", "avg_price", "turnover", "trades"]
SCHEMA = pa.schema([("date", pa.date32()), ("symbol", pa.string()), ("series", pa.string()), ("traded_qty", pa.int64()), ("deliverable_qty", pa.int64()),
                    ("deliv_pct", pa.float64()), ("prev_close", pa.float64()), ("open", pa.float64()), ("high", pa.float64()), ("low", pa.float64()),
                    ("last", pa.float64()), ("close", pa.float64()), ("avg_price", pa.float64()), ("turnover", pa.float64()), ("trades", pa.int64()),
                    ("source", pa.string()), ("ingested_at", pa.timestamp("s", tz="UTC"))])


def _num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.strip().replace({"-": None, "": None}), errors="coerce")


def parse_delivery(path: Path, day: dt.date) -> pd.DataFrame:
    text = path.read_text(encoding="utf-8", errors="replace")
    head = text[:200]
    if head.startswith("SYMBOL"):
        df = pd.read_csv(io.StringIO(text), dtype=str, skipinitialspace=True)
        df.columns = [c.strip() for c in df.columns]
        out = pd.DataFrame({"date": day, "symbol": df["SYMBOL"].str.strip(), "series": df["SERIES"].str.strip(),
                            "traded_qty": _num(df["TTL_TRD_QNTY"]), "deliverable_qty": _num(df["DELIV_QTY"]), "deliv_pct": _num(df["DELIV_PER"]),
                            "prev_close": _num(df["PREV_CLOSE"]), "open": _num(df["OPEN_PRICE"]), "high": _num(df["HIGH_PRICE"]), "low": _num(df["LOW_PRICE"]),
                            "last": _num(df["LAST_PRICE"]), "close": _num(df["CLOSE_PRICE"]), "avg_price": _num(df["AVG_PRICE"]),
                            "turnover": _num(df["TURNOVER_LACS"]) * 1e5, "trades": _num(df["NO_OF_TRADES"])})
    else:
        rows = [l.split(",") for l in text.splitlines() if l.startswith("20,")]
        df = pd.DataFrame(rows, columns=["rt", "sr", "symbol", "series", "traded_qty", "deliverable_qty", "deliv_pct"][: len(rows[0])] if rows else [])
        if df.empty:
            return pd.DataFrame(columns=COLS)
        out = pd.DataFrame({"date": day, "symbol": df["symbol"].str.strip(), "series": df["series"].str.strip(), "traded_qty": _num(df["traded_qty"]),
                            "deliverable_qty": _num(df["deliverable_qty"]), "deliv_pct": _num(df["deliv_pct"])})
        for c in ("prev_close", "open", "high", "low", "last", "close", "avg_price", "turnover", "trades"):
            out[c] = None
    for c in ("traded_qty", "deliverable_qty", "trades"):
        out[c] = pd.to_numeric(out[c], errors="coerce").astype("Int64")
    for c in ("deliv_pct", "prev_close", "open", "high", "low", "last", "close", "avg_price", "turnover"):
        out[c] = pd.to_numeric(out[c], errors="coerce").astype("float64")
    return out[COLS]


def build_year(year: int) -> dict:
    rows = nse.manifest_rows("delivery")
    frames = []
    now = pd.Timestamp.now(tz="UTC").floor("s")
    for d, r in sorted(rows.items()):
        if r.get("status") != 200 or not d.startswith(str(year)):
            continue
        df = parse_delivery(paths.data_dir() / r["path"], dt.date.fromisoformat(d))
        if len(df):
            df["source"] = r["sha256"][:16]
            df["ingested_at"] = now
            frames.append(df)
    if not frames:
        return {"year": year, "rows": 0}
    full = pd.concat(frames, ignore_index=True)
    out = silver._year_target("delivery", year)
    out.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pandas(full, schema=SCHEMA, preserve_index=False), out, compression="zstd")
    return {"year": year, "rows": len(full), "files": len(frames), "with_prices": int(full["close"].notna().sum())}


def build(years: list[int] | None = None) -> list[dict]:
    years = years or silver.complete_years("delivery")
    out = []
    for y in years:
        r = build_year(y)
        print(r, flush=True)
        out.append(r)
    return out


if __name__ == "__main__":
    paths.ensure()
    build([int(y) for y in sys.argv[2:]] or None)
