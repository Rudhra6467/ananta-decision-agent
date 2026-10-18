"""Macro series from FRED's public CSV downloads (no key, personal research use) into bronze/macro/<series>.csv and silver/macro/macro.parquet (long form).

  python -m india.macro pull        download every series (polite: one request every 2 seconds)
  python -m india.macro silver      build silver/macro/macro.parquet  (date, series, value)
Series (all daily unless noted): USD/INR (DEXINUS), Brent (DCOILBRENTEU), WTI (DCOILWTICO), US 10-year (DGS10), US 2-year (DGS2), S&P 500 (SP500), Nasdaq (NASDAQCOM),
broad dollar index (DTWEXBGS), VIX US (VIXCLS), gold fix (GOLDPMGBD228NLBM), US fed funds (DFF), India 10-year yield, monthly (INDIRLTLT01STM), India policy-rate proxy, monthly (INTDSRINM193N).
FRED terms: free for personal use, no redistribution of the raw series. Raw rows stay on the Mac; only derived columns go into shared outputs.
Series that FRED has retired return an error line in manifests/macro.jsonl and are skipped.
"""
from __future__ import annotations

import datetime as dt
import io
import json
import sys
import time
import urllib.request

import pandas as pd

from india import catalog, paths

SERIES = {
    "DEXINUS": "USD/INR", "DCOILBRENTEU": "Brent crude", "DCOILWTICO": "WTI crude", "DGS10": "US 10-year yield", "DGS2": "US 2-year yield", "SP500": "S&P 500",
    "NASDAQCOM": "Nasdaq composite", "DTWEXBGS": "Broad dollar index", "VIXCLS": "US VIX", "GOLDPMGBD228NLBM": "Gold London PM fix", "DFF": "US fed funds effective",
    "INDIRLTLT01STM": "India long-term govt yield (monthly)", "INTDSRINM193N": "India central bank discount rate (monthly)",
}


def pull() -> dict:
    paths.ensure()
    out = paths.data_dir() / "bronze" / "macro"
    out.mkdir(parents=True, exist_ok=True)
    res = {}
    man = paths.manifest_dir() / "macro.jsonl"
    for sid in SERIES:
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}&cosd=1990-01-01"
        line = {"series": sid, "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research; personal use)"})
            body = urllib.request.urlopen(req, timeout=60).read()
            (out / f"{sid}.csv").write_bytes(body)
            df = pd.read_csv(io.BytesIO(body))
            line.update({"status": "ok", "rows": len(df), "first": str(df.iloc[0, 0]), "last": str(df.iloc[-1, 0])})
        except Exception as e:
            line.update({"status": f"error {type(e).__name__}: {e}"})
        with man.open("a") as fh:
            fh.write(json.dumps(line) + "\n")
        res[sid] = line.get("status")
        print(line, flush=True)
        time.sleep(2)
    return res


def silver() -> dict:
    src = paths.data_dir() / "bronze" / "macro"
    frames = []
    for f in sorted(src.glob("*.csv")):
        df = pd.read_csv(f)
        df.columns = ["date", "value"]
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df = df.dropna()
        df["series"] = f.stem
        frames.append(df)
    full = pd.concat(frames, ignore_index=True)
    full["date"] = pd.to_datetime(full["date"])
    out = paths.data_dir() / "silver" / "macro"
    out.mkdir(parents=True, exist_ok=True)
    full[["date", "series", "value"]].to_parquet(out / "macro.parquet", index=False)
    return {"rows": len(full), "series": int(full["series"].nunique()), "first": str(full["date"].min()), "last": str(full["date"].max())}


if __name__ == "__main__":
    if sys.argv[1] == "pull":
        pull()
    else:
        print(silver())
        catalog.heartbeat("macro.silver", True, "")
