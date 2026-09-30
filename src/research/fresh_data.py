"""Fresh test set: 5m history for 10 coins OUTSIDE the lab 10, from Binance's public archive.

Every study so far used BTC ETH SOL ADA DOGE AVAX BCH LINK LTC XRP, including the holdout.
These coins have never been looked at, so they are clean evidence for a pre-registered design.
Stored with the same schema as lab5_5m.sqlite so the research code runs unchanged.

    python -m src.research.fresh_data --out ~/ananta_runs/fresh10/fresh10_5m.sqlite
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import sqlite3
import time
import urllib.error
import urllib.request
import zipfile

FRESH10 = ["DOT", "ATOM", "ETC", "XLM", "TRX", "UNI", "FIL", "NEAR", "ALGO", "AAVE"]
URL = "https://data.binance.vision/data/spot/monthly/klines/{s}/5m/{s}-5m-{y}-{m:02d}.zip"


def months(start=(2019, 1), end=(2026, 8)):
    y, m = start
    while (y, m) <= end:
        yield y, m
        m += 1
        if m == 13:
            y, m = y + 1, 1


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.expanduser("~/ananta_runs/fresh10/fresh10_5m.sqlite"))
    a = ap.parse_args(argv)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    con = sqlite3.connect(a.out)
    con.execute("""CREATE TABLE IF NOT EXISTS bars (source_code TEXT, source_record_id TEXT PRIMARY KEY, instrument TEXT,
                   event_unix INTEGER, open REAL, high REAL, low REAL, close REAL, volume REAL, trades INTEGER,
                   fill_rule TEXT, quote TEXT)""")
    con.execute("CREATE TABLE IF NOT EXISTS fetched (coin TEXT, ym TEXT, status TEXT, PRIMARY KEY (coin, ym))")
    con.execute("CREATE INDEX IF NOT EXISTS ix_bars ON bars (instrument, event_unix)")
    for coin in FRESH10:
        s = f"{coin}USDT"
        for y, m in months():
            ym = f"{y}-{m:02d}"
            if con.execute("SELECT 1 FROM fetched WHERE coin=? AND ym=?", (coin, ym)).fetchone():
                continue
            try:
                raw = urllib.request.urlopen(URL.format(s=s, y=y, m=m), timeout=60).read()
            except urllib.error.HTTPError as e:
                status = "MISSING" if e.code == 404 else f"HTTP_{e.code}"
                con.execute("INSERT OR REPLACE INTO fetched VALUES (?,?,?)", (coin, ym, status))
                con.commit()
                continue
            rows = []
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                for name in z.namelist():
                    for r in csv.reader(io.TextIOWrapper(z.open(name))):
                        if not r or not r[0].isdigit():
                            continue
                        t = int(r[0])
                        t = t // 1_000_000 if t > 10**14 else t // 1000  # Binance switched to microseconds in 2025
                        rows.append(("binance.klines.5m", f"bn5:{coin}-USD-SPOT:{t}", f"{coin}-USD-SPOT", t,
                                     float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5]), int(r[8]), "binance_5m", "USDT"))
            con.executemany("INSERT OR IGNORE INTO bars VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", rows)
            con.execute("INSERT OR REPLACE INTO fetched VALUES (?,?,?)", (coin, ym, f"OK:{len(rows)}"))
            con.commit()
            time.sleep(0.2)
        n = con.execute("SELECT count(*), min(event_unix), max(event_unix) FROM bars WHERE instrument=?", (f"{coin}-USD-SPOT",)).fetchone()
        print(coin, n[0], time.strftime("%Y-%m-%d", time.gmtime(n[1] or 0)), time.strftime("%Y-%m-%d", time.gmtime(n[2] or 0)), flush=True)
    con.close()


if __name__ == "__main__":
    main()
