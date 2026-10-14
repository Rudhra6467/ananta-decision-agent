"""Binance Data Vision (data.binance.vision): free monthly candle files, no key, back to 2017.

  months(symbol)     what Binance publishes for a symbol (from the public bucket listing)
  pull(symbol)       download every month not yet held, then the daily files after the last month (to yesterday), each checked
                     against Binance's SHA-256 checksum file
  build(symbol)      raw zips -> clean Parquet (symbol=X/year=Y), timestamps in UTC seconds, numbers as numbers

Notes: from 2025 Binance writes spot timestamps in microseconds (before: milliseconds); both become seconds here. Some files
carry a header row; it is dropped. A month whose checksum does not match is deleted and counted as an error, never used.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Callable

from src.lake import root

BUCKET = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
FILES = "https://data.binance.vision"
COLS = ["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_volume", "trades", "taker_buy_base", "taker_buy_quote", "ignore"]


def _get(url: str, params: dict | None = None, timeout: int = 60):
    import requests

    for wait in (0, 3, 10, 30):
        if wait:
            time.sleep(wait)
        try:
            r = requests.get(url, params=params, timeout=timeout)
            if r.status_code == 200:
                return r
            if r.status_code == 404:
                return r
        except requests.RequestException:
            continue
    raise RuntimeError(f"could not fetch {url}")


def list_keys(prefix: str, get: Callable = _get) -> list[tuple[str, int]]:
    """All (key, size) under a prefix of the public bucket (follows pagination)."""
    out, marker = [], ""
    while True:
        r = get(BUCKET, {"prefix": prefix, "marker": marker} if marker else {"prefix": prefix})
        xml = r.text
        items = re.findall(r"<Key>([^<]+)</Key>.*?<Size>(\d+)</Size>", xml, re.S)
        out += [(k, int(s)) for k, s in items]
        if "<IsTruncated>true</IsTruncated>" not in xml or not items:
            return out
        marker = items[-1][0]


def raw_dir(symbol: str, interval: str = "1m", market: str = "spot") -> Path:
    return root() / "raw" / "binance" / market / interval / symbol


def clean_dir(interval: str = "1m", market: str = "spot") -> Path:
    return root() / "clean" / "binance" / market / interval


def months(symbol: str, interval: str = "1m", market: str = "spot", get: Callable = _get) -> list[dict]:
    keys = dict(list_keys(f"data/{market}/monthly/klines/{symbol}/{interval}/", get))
    out = []
    for k, size in keys.items():
        m = re.search(r"-(\d{4}-\d{2})\.zip$", k)
        if m and k + ".CHECKSUM" in keys:
            out.append({"month": m.group(1), "key": k, "size": size})
    return sorted(out, key=lambda x: x["month"])


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def pull(symbol: str, interval: str = "1m", market: str = "spot", get: Callable = _get, log: Callable = print, daily: bool = True,
         workers: int = 6) -> dict:
    """Download every published month not yet held and verified. Returns counts."""
    d = raw_dir(symbol, interval, market)
    d.mkdir(parents=True, exist_ok=True)
    man_p = d / "_verified.json"
    man = json.loads(man_p.read_text()) if man_p.exists() else {}
    got = skipped = bad = 0
    ms = months(symbol, interval, market, get)

    def fetch(m: dict) -> tuple[str, str | None]:
        """-> (file name, sha256) or (file name, None) on any failure; a mismatched file is deleted."""
        name = Path(m["key"]).name
        f = d / name
        r = get(f"{FILES}/{m['key']}", timeout=300)
        if r.status_code != 200:
            return name, None
        f.write_bytes(r.content)
        want = get(f"{FILES}/{m['key']}.CHECKSUM").text.split()[0].strip()
        have = _sha(f)
        if have != want:
            f.unlink()
            log(f"{name}: checksum mismatch, removed")
            return name, None
        return name, have

    todo = []
    for m in ms:
        name = Path(m["key"]).name
        f = d / name
        if man.get(name) and f.exists() and f.stat().st_size == m["size"]:
            skipped += 1
        else:
            todo.append(m)
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=workers) as pool:          # a few files at once: Binance's file server is a CDN
        for name, have in pool.map(fetch, todo):
            if have is None:
                bad += 1
                continue
            man[name] = {"sha256": have, "bytes": (d / name).stat().st_size, "at": int(time.time())}
            got += 1
    man_p.write_text(json.dumps(man, indent=0, sort_keys=True))
    # the days after the last monthly file (Binance publishes a month's file a few days after it ends)
    days = 0
    if ms and daily:
        last_m = ms[-1]["month"]
        keys = dict(list_keys(f"data/{market}/daily/klines/{symbol}/{interval}/", get))
        for k, size in sorted(keys.items()):
            m = re.search(r"-(\d{4}-\d{2})-(\d{2})\.zip$", k)
            if not m or m.group(1) <= last_m or k + ".CHECKSUM" not in keys:
                continue
            name = Path(k).name
            f = d / name
            if man.get(name) and f.exists() and f.stat().st_size == size:
                continue
            r = get(f"{FILES}/{k}", timeout=120)
            if r.status_code != 200:
                bad += 1
                continue
            f.write_bytes(r.content)
            if _sha(f) != get(f"{FILES}/{k}.CHECKSUM").text.split()[0].strip():
                f.unlink()
                bad += 1
                continue
            man[name] = {"sha256": _sha(f), "bytes": f.stat().st_size, "at": int(time.time())}
            days += 1
        man_p.write_text(json.dumps(man, indent=0, sort_keys=True))
    return {"symbol": symbol, "months": len(ms), "downloaded": got, "already_held": skipped, "errors": bad, "days": days,
            "first": ms[0]["month"] if ms else None, "last": ms[-1]["month"] if ms else None}


def build(symbol: str, interval: str = "1m", market: str = "spot", con=None) -> dict:
    """Raw zips -> clean Parquet for one symbol (rebuilt whole, so a re-run is the same result)."""
    import duckdb

    d = raw_dir(symbol, interval, market)
    zips = sorted(d.glob(f"{symbol}-{interval}-*.zip"))
    if not zips:
        return {"symbol": symbol, "rows": 0, "note": "nothing downloaded"}
    out = clean_dir(interval, market) / f"symbol={symbol}"
    tmp = Path(tempfile.mkdtemp(prefix=f"lake_{symbol}_"))
    con = con or duckdb.connect()
    con.execute("SET TimeZone='UTC'")                            # years and days are UTC, whatever the Mac's zone
    try:
        for z in zips:
            with zipfile.ZipFile(z) as zf:
                for n in zf.namelist():
                    if n.endswith(".csv"):
                        zf.extract(n, tmp)
        csvs = sorted(str(p) for p in tmp.rglob("*.csv"))
        cols = "{" + ", ".join(f"'{c}': 'VARCHAR'" for c in COLS) + "}"
        con.execute(f"""
            CREATE OR REPLACE TEMP TABLE k AS
            WITH r AS (SELECT * FROM read_csv({csvs!r}, header=false, columns={cols}, null_padding=true, ignore_errors=true))
            SELECT
              CAST(CASE WHEN TRY_CAST(open_time AS BIGINT) > 100000000000000 THEN TRY_CAST(open_time AS BIGINT) // 1000000
                        ELSE TRY_CAST(open_time AS BIGINT) // 1000 END AS BIGINT) AS t,
              CAST(open AS DOUBLE) AS o, CAST(high AS DOUBLE) AS h, CAST(low AS DOUBLE) AS l, CAST(close AS DOUBLE) AS c,
              CAST(volume AS DOUBLE) AS v, CAST(quote_volume AS DOUBLE) AS qv, CAST(trades AS BIGINT) AS n,
              CAST(taker_buy_base AS DOUBLE) AS tbv
            FROM r WHERE TRY_CAST(open_time AS BIGINT) IS NOT NULL
        """)
        con.execute("CREATE OR REPLACE TEMP TABLE k2 AS SELECT DISTINCT ON (t) *, year(to_timestamp(t)) AS year FROM k ORDER BY t")
        if out.exists():
            shutil.rmtree(out)                                   # our own generated output, rebuilt whole
        out.mkdir(parents=True, exist_ok=True)
        con.execute(f"COPY (SELECT * FROM k2 ORDER BY t) TO '{out}' (FORMAT parquet, PARTITION_BY (year), COMPRESSION zstd, OVERWRITE_OR_IGNORE)")
        n, t0, t1 = con.execute("SELECT count(*), min(t), max(t) FROM k2").fetchone()
        raw_n = con.execute("SELECT count(*) FROM k").fetchone()[0]
        size = sum(p.stat().st_size for p in out.rglob("*.parquet"))
        return {"symbol": symbol, "rows": n, "duplicates_dropped": raw_n - n, "first_t": t0, "last_t": t1, "parquet_mb": round(size / 1e6, 1),
                "months": len(zips)}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
