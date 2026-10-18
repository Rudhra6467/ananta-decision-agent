"""Kite candles for the indices and India VIX into bronze/kite_index/<interval>/<NAME>.jsonl.gz.

  python -m india.kite_index          minute and 5-minute from 2015-02-02, daily from 2003-01-01
Indices: NIFTY 50, NIFTY BANK, NIFTY FIN SERVICE, NIFTY MIDCAP SELECT, NIFTY NEXT 50, NIFTY MIDCAP 100, NIFTY SMLCAP 100, INDIA VIX.
Windows already fetched (manifest status ok) are skipped except the last one. Stops with NeedLogin when the token dies.
"""
from __future__ import annotations

import csv
import datetime as dt
import gzip
import io
import json
import time

from india import kite, paths

NAMES = ["NIFTY 50", "NIFTY BANK", "NIFTY FIN SERVICE", "NIFTY MID SELECT", "NIFTY NEXT 50", "NIFTY MIDCAP 100", "NIFTY SMLCAP 100", "INDIA VIX"]
# daily-only extras: broad indices, sector and thematic indices (the sector relative-strength and breadth studies, D29)
DAILY_EXTRA = ["NIFTY 100", "NIFTY 200", "NIFTY 500", "NIFTY TOTAL MKT", "NIFTY MIDCAP 50", "NIFTY MIDCAP 150", "NIFTY SMLCAP 50", "NIFTY SMLCAP 250", "NIFTY MIDSML 400", "NIFTY LARGEMID250",
               "NIFTY IT", "NIFTY AUTO", "NIFTY PHARMA", "NIFTY FMCG", "NIFTY METAL", "NIFTY REALTY", "NIFTY ENERGY", "NIFTY INFRA", "NIFTY MEDIA", "NIFTY PSU BANK", "NIFTY PVT BANK",
               "NIFTY FINSRV25 50", "NIFTY HEALTHCARE", "NIFTY CONSR DURBL", "NIFTY OIL AND GAS", "NIFTY CPSE", "NIFTY PSE", "NIFTY MNC", "NIFTY SERV SECTOR", "NIFTY COMMODITIES",
               "NIFTY CONSUMPTION", "NIFTY INDIA MFG", "NIFTY CAPITAL MKT", "NIFTY CHEMICALS", "NIFTY HIGHBETA 50", "NIFTY LOW VOL 50", "NIFTY500 EQUAL WEIGHT", "NIFTY50 EQL WGT",
               "NIFTY100 LIQ 15", "NIFTY MID LIQ 15", "NIFTY IND DEFENCE", "NIFTY RAILWAYS PSU", "NIFTY HOUSING", "NIFTY EV", "NIFTY MOBILITY"]
PLAN = [("day", dt.date(2003, 1, 1), NAMES + DAILY_EXTRA), ("5minute", dt.date(2015, 1, 1), NAMES), ("minute", dt.date(2015, 1, 1), NAMES)]


def run() -> dict:
    paths.ensure()
    k = kite.Kite()
    p = paths.bronze("kite_instruments") / f"NSE_{dt.date.today():%Y%m%d}.csv"
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(k.instruments("NSE"))
    idx = {r["tradingsymbol"]: int(r["instrument_token"]) for r in csv.DictReader(io.StringIO(p.read_text())) if r.get("segment") == "INDICES"}
    man = paths.manifest_dir() / "kite_index.jsonl"
    done = set()
    if man.exists():
        for line in man.read_text().splitlines():
            r = json.loads(line)
            if r.get("status") == "ok":
                done.add((r["symbol"], r["interval"], r["start"]))
    today = dt.date.today()
    n = rows = 0
    t0 = time.time()
    for interval, start, names in PLAN:
        step = dt.timedelta(days=kite.DAYS_PER_REQUEST[interval] - 1)
        for name in names:
            tok = idx.get(name)
            if not tok:
                print("no token for", name, flush=True)
                continue
            out = paths.bronze("kite_index") / interval / f"{name}.jsonl.gz"
            out.parent.mkdir(parents=True, exist_ok=True)
            a = start
            while a <= today:
                b = min(a + step, today)
                if (name, interval, a.isoformat()) in done and b < today:
                    a = b + dt.timedelta(days=1)
                    continue
                try:
                    candles = k.historical(tok, interval, a, b)
                except kite.NeedLogin as exc:
                    print("stopped:", exc, flush=True)
                    return {"stopped": str(exc), "windows": n, "rows": rows}
                rec = {"symbol": name, "token": tok, "interval": interval, "start": a.isoformat(), "end": b.isoformat(),
                       "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "n": len(candles), "status": "ok"}
                if candles:
                    with gzip.open(out, "at") as gz:
                        gz.write(json.dumps({**rec, "candles": candles}) + "\n")
                with man.open("a") as fh:
                    fh.write(json.dumps(rec) + "\n")
                n += 1
                rows += len(candles)
                a = b + dt.timedelta(days=1)
            print(f"{interval:8} {name:22} windows={n} rows={rows} calls={k.calls} {round(time.time() - t0)}s", flush=True)
    return {"windows": n, "rows": rows, "calls": k.calls, "seconds": round(time.time() - t0)}


def silver() -> dict:
    """bronze/kite_index -> silver/kite_index/<interval>/ (daily: one file; 5-minute and 1-minute: one per year). 2024+ rows go under sealed/silver. Index times are IST, stored as naive IST."""
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq

    out_n = {}
    hold = pd.Timestamp(paths.HOLDOUT_START)
    for interval in ("day", "5minute", "minute"):
        frames = []
        for f in sorted((paths.bronze("kite_index") / interval).glob("*.jsonl.gz")):
            rows = []
            with gzip.open(f, "rt") as gz:
                for line in gz:
                    r = json.loads(line)
                    for c in r["candles"]:
                        rows.append((r["symbol"], c[0][:19], c[1], c[2], c[3], c[4], c[5]))
            if rows:
                frames.append(pd.DataFrame(rows, columns=["index_name", "ts", "open", "high", "low", "close", "volume"]))
        if not frames:
            continue
        df = pd.concat(frames, ignore_index=True)
        df["ts"] = pd.to_datetime(df["ts"])
        df = df.drop_duplicates(["index_name", "ts"], keep="last").sort_values(["index_name", "ts"]).reset_index(drop=True)
        df["date"] = df["ts"].dt.date
        if interval == "day":
            # Kite answers some older days twice (a 00:00 bar with open=high=low=close and a 09:15 bar with the real range); keep one bar per index-day,
            # the one with a range (integrity check 18 Oct 2026 found 7,992 such pairs, NIFTY 100 / 200 / AUTO and others; closes agree)
            df["_rng"] = (df["high"] > df["low"]).astype(int)
            df = df.sort_values(["index_name", "date", "_rng", "ts"]).drop_duplicates(["index_name", "date"], keep="last").drop(columns="_rng").reset_index(drop=True)
        base = paths.data_dir()
        if interval == "day":
            for part, sub in (("silver", df[df["ts"] < hold]), ("sealed/silver", df[df["ts"] >= hold])):
                if len(sub):
                    t = base / part / "kite_index" / "day" / "day.parquet"
                    t.parent.mkdir(parents=True, exist_ok=True)
                    pq.write_table(pa.Table.from_pandas(sub, preserve_index=False), t, compression="zstd")
        else:
            for y, sub in df.groupby(df["ts"].dt.year):
                part = "sealed/silver" if y >= hold.year else "silver"
                t = base / part / "kite_index" / interval / f"year={y}" / "part.parquet"
                t.parent.mkdir(parents=True, exist_ok=True)
                pq.write_table(pa.Table.from_pandas(sub, preserve_index=False), t, compression="zstd")
        out_n[interval] = {"rows": len(df), "indices": int(df["index_name"].nunique()), "first": str(df["ts"].min()), "last": str(df["ts"].max())}
    return out_n


if __name__ == "__main__":
    import sys

    print(silver() if len(sys.argv) > 1 and sys.argv[1] == "silver" else run())
