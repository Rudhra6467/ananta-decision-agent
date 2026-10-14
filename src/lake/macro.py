"""The outside world, daily (review #23): FRED series and the crypto Fear & Greed index -> clean/macro/<id>.parquet (t, value).

  pull()          all series (re-run any time; each file is replaced)
  load(id)        DataFrame (t = UTC day start, value)
  asof(id, t)     the last value dated on or before day t
"""
from __future__ import annotations

import io

from src.lake import root

FRED = {"NASDAQCOM": "Nasdaq Composite", "DTWEXBGS": "US dollar index (broad)", "DGS10": "US 10-year Treasury yield %", "VIXCLS": "VIX"}
FNG = "FNG"


def _dir():
    d = root() / "clean" / "macro"
    d.mkdir(parents=True, exist_ok=True)
    return d


def pull() -> dict:
    import pandas as pd
    import requests

    out = {}
    for sid in FRED:
        r = requests.get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}", timeout=60)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        df.columns = ["date", "value"]
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df = df.dropna()
        df["t"] = ((pd.to_datetime(df["date"]) - pd.Timestamp("1970-01-01")) // pd.Timedelta(seconds=1)).astype("int64")   # any resolution
        df[["t", "value"]].to_parquet(_dir() / f"{sid}.parquet", index=False)
        out[sid] = {"rows": len(df), "first": str(df["date"].iloc[0]), "last": str(df["date"].iloc[-1])}
    d = requests.get("https://api.alternative.me/fng/?limit=0&format=json", timeout=60).json()["data"]
    df = pd.DataFrame([(int(x["timestamp"]), float(x["value"])) for x in d], columns=["t", "value"]).sort_values("t")
    df.to_parquet(_dir() / f"{FNG}.parquet", index=False)
    out[FNG] = {"rows": len(df)}
    return out


def load(sid: str):
    import pandas as pd

    p = _dir() / f"{sid}.parquet"
    return pd.read_parquet(p) if p.exists() else None
