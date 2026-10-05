"""Binance USD-M futures context from Data Vision (free, no key): funding rates and open interest, daily, per coin.

  resolve(coin)          the futures symbol (BTCUSDT, or 1000PEPEUSDT for coins Binance quotes per 1,000)
  pull_funding(coin)     monthly funding files -> clean/binance/futures/funding_daily/<coin>.parquet (mean rate per UTC day)
  pull_metrics(coin)     daily metrics files (5-minute open interest and long/short ratios) -> clean/binance/futures/
                         metrics_daily/<coin>.parquet (open interest at the day's last reading; mean ratios over the day)
Every zip is opened and CRC-checked before use; a bad file is skipped and counted as an error. Re-running only fetches what is
new. Context only: these are not prices and never replace the spot candles.
"""
from __future__ import annotations

import io
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

from src.lake import root
from src.lake import binance_vision as bv

PREFIX = "data/futures/um"


def out_dir(kind: str):
    d = root() / "clean" / "binance" / "futures" / kind
    d.mkdir(parents=True, exist_ok=True)
    return d


def resolve(coin: str, get=bv._get) -> str | None:
    for s in (f"{coin}USDT", f"1000{coin}USDT", f"1000000{coin}USDT"):
        if any(k.endswith(".zip") for k, _ in bv.list_keys(f"{PREFIX}/monthly/fundingRate/{s}/", get=get)):
            return s
    return None


def _zip_rows(content: bytes) -> list[list[str]]:
    z = zipfile.ZipFile(io.BytesIO(content))
    if z.testzip() is not None:
        raise ValueError("bad zip")
    rows = []
    for name in z.namelist():
        for line in z.read(name).decode().splitlines():
            parts = line.split(",")
            if parts and parts[0] and parts[0][0].isdigit():
                rows.append(parts)
    return rows


def pull_funding(coin: str, get=bv._get) -> dict:
    import pandas as pd

    sym = resolve(coin, get=get)
    if not sym:
        return {"coin": coin, "symbol": None, "note": "no futures market"}
    keys = [k for k, _ in bv.list_keys(f"{PREFIX}/monthly/fundingRate/{sym}/", get=get) if k.endswith(".zip")]
    rows, errors = [], 0

    def one(k):
        try:
            return [(int(r[0]) // 1000, float(r[2])) for r in _zip_rows(get(f"{bv.FILES}/{k}").content)]
        except Exception:  # noqa: BLE001
            return None

    with ThreadPoolExecutor(max_workers=8) as pool:
        for got in pool.map(one, keys):
            if got is None:
                errors += 1
            else:
                rows += got
    df = pd.DataFrame(rows, columns=["t", "rate"]).drop_duplicates("t")
    df["day"] = df["t"] // 86400 * 86400
    daily = df.groupby("day").agg(funding=("rate", "mean"), n=("rate", "size")).reset_index().rename(columns={"day": "t"})
    daily.to_parquet(out_dir("funding_daily") / f"{coin}.parquet", index=False)
    return {"coin": coin, "symbol": sym, "months": len(keys), "errors": errors, "days": len(daily),
            "first": str(pd.to_datetime(daily["t"].min(), unit="s").date()) if len(daily) else None}


def _metrics_day(sym: str, d: date, get) -> list[tuple] | None:
    k = f"{PREFIX}/daily/metrics/{sym}/{sym}-metrics-{d.isoformat()}.zip"
    r = get(f"{bv.FILES}/{k}")
    if r.status_code == 404:
        return None
    out = []
    for p in _zip_rows(r.content):
        try:
            t = int(time.mktime(time.strptime(p[0], "%Y-%m-%d %H:%M:%S")) - time.timezone)
            f = [float(x) if x not in ("", None) else float("nan") for x in p[2:8]]
            out.append((t, *f))
        except (ValueError, IndexError):
            continue
    return out


def pull_metrics(coin: str, until: date | None = None, get=bv._get, workers: int = 8) -> dict:
    import pandas as pd

    sym = resolve(coin, get=get)
    if not sym:
        return {"coin": coin, "symbol": None, "note": "no futures market"}
    path = out_dir("metrics_daily") / f"{coin}.parquet"
    old = pd.read_parquet(path) if path.exists() else None
    keys = [k for k, _ in bv.list_keys(f"{PREFIX}/daily/metrics/{sym}/", get=get) if k.endswith(".zip")]
    days = sorted(date.fromisoformat(k[-14:-4]) for k in keys)
    if old is not None and len(old):
        have = set(pd.to_datetime(old["t"], unit="s").dt.date)
        days = [d for d in days if d not in have]
    until = until or (date.today() - timedelta(days=1))
    days = [d for d in days if d <= until]
    errors = 0

    def one(d):
        nonlocal errors
        try:
            rows = _metrics_day(sym, d, get)
        except Exception:  # noqa: BLE001
            errors += 1
            return None
        if not rows:
            return None
        df = pd.DataFrame(rows, columns=["t", "oi", "oi_value", "top_ls_count", "top_ls_sum", "ls_count", "taker_ls_vol"])
        last = df.sort_values("t").iloc[-1]
        return {"t": int(pd.Timestamp(d).timestamp()), "oi": last["oi"], "oi_value": last["oi_value"],
                "top_ls": df["top_ls_sum"].mean(), "ls": df["ls_count"].mean(), "taker_ls": df["taker_ls_vol"].mean(), "readings": len(df)}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        new = [x for x in pool.map(one, days) if x]
    df = pd.DataFrame(new)
    if old is not None and len(old):
        df = pd.concat([old, df], ignore_index=True) if len(df) else old
    if len(df):
        df = df.drop_duplicates("t").sort_values("t")
        df.to_parquet(path, index=False)
    return {"coin": coin, "symbol": sym, "new_days": len(new), "errors": errors, "days": len(df)}


def load(kind: str, coin: str):
    import pandas as pd

    p = out_dir(kind) / f"{coin}.parquet"
    return pd.read_parquet(p) if p.exists() else None
