"""US market closes for the overnight read: QQQ (Nasdaq-100) and SPY (S&P 500) daily from Tiingo (free plan, personal use), with FRED kept
as the next-day cross-check. Chosen 19 Oct 2026 (Madhav): FRED posts a US close only the next US morning, after the Indian session; Tiingo
has it about 1.5 hours after the US close (17:30 New York), i.e. 03:00-04:00 IST, before Ananta's 09:00 IST read.

  python -m india.usclose history     QQQ and SPY from 2003 (one request each), bronze raw + silver/us/us_close.parquet
  python -m india.usclose update      the last 15 calendar days (evening job, before the day plan)
  python -m india.usclose check       QQQ vs FRED NASDAQCOM and SPY vs FRED SP500: return correlation and +/-0.5% bucket agreement

The key lives in ~/ananta_private/tiingo.env (TIINGO_API_KEY=...), written by Madhav, mode 600; it is read here and never printed or logged.
A US date's close is usable for an Indian session dated strictly after it (the US close is 01:30 IST next day in US summer, 02:30 in winter).
US market data is not India performance data, so like silver/macro it is not split into sealed/.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
import time
import urllib.request
from pathlib import Path

import pandas as pd

from india import paths

SYMBOLS = ("QQQ", "SPY")
BASE = "https://api.tiingo.com/tiingo/daily"
KEYFILE = Path.home() / "ananta_private" / "tiingo.env"


def _key() -> str:
    for line in KEYFILE.read_text().splitlines():
        if line.startswith("TIINGO_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit(f"no TIINGO_API_KEY in {KEYFILE}")


def _get(symbol: str, start: dt.date, end: dt.date) -> list[dict]:
    url = f"{BASE}/{symbol}/prices?startDate={start.isoformat()}&endDate={end.isoformat()}&format=json"
    req = urllib.request.Request(url, headers={"Authorization": "Token " + _key(), "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def _store(symbol: str, rows: list[dict], start: dt.date, end: dt.date) -> Path:
    now = dt.datetime.now(dt.timezone.utc)
    out = paths.bronze("us_close") / symbol / f"{symbol}_{start:%Y%m%d}_{end:%Y%m%d}_{now:%Y%m%dT%H%M%S}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(rows)
    out.write_text(body)
    with (paths.manifest_dir() / "us_close.jsonl").open("a") as fh:
        fh.write(json.dumps({"symbol": symbol, "start": start.isoformat(), "end": end.isoformat(), "rows": len(rows),
                             "fetched_at": now.isoformat(timespec="seconds"), "path": str(out.relative_to(paths.data_dir())),
                             "sha256": hashlib.sha256(body.encode()).hexdigest()}) + "\n")
    return out


def build_silver() -> dict:
    """All bronze files, the latest fetch winning per (symbol, date)."""
    rows = []
    for f in sorted(paths.bronze("us_close").glob("*/*.json")):
        sym = f.parent.name
        for r in json.loads(f.read_text()):
            rows.append({"symbol": sym, "date": r["date"][:10], "close": r["close"], "adj_close": r.get("adjClose"), "volume": r.get("volume"),
                         "fetched": f.name})
    df = pd.DataFrame(rows)
    df = df.sort_values("fetched").drop_duplicates(["symbol", "date"], keep="last").drop(columns="fetched")
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df = df.sort_values(["symbol", "date"])
    df["ret"] = df.groupby("symbol")["adj_close"].pct_change()
    out = paths.data_dir() / "silver" / "us"
    out.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out / "us_close.parquet", index=False)
    return {s: {"rows": int((df.symbol == s).sum()), "first": str(df.loc[df.symbol == s, "date"].min()), "last": str(df.loc[df.symbol == s, "date"].max())}
            for s in SYMBOLS}


def history(start: dt.date = dt.date(2003, 1, 1)) -> dict:
    end = dt.date.today()
    for s in SYMBOLS:
        _store(s, _get(s, start, end), start, end)
        time.sleep(2)
    return build_silver()


def update(days: int = 15) -> dict:
    end = dt.date.today()
    start = end - dt.timedelta(days=days)
    for s in SYMBOLS:
        _store(s, _get(s, start, end), start, end)
        time.sleep(2)
    res = build_silver()
    try:
        from india import catalog

        catalog.heartbeat("usclose.update", True, json.dumps(res))
    except Exception:
        pass
    return res


def latest_before(day: dt.date, symbol: str = "QQQ") -> tuple[float | None, dt.date | None]:
    """The return of the last US session strictly before an Indian session date (what Ananta can know at 09:00 IST)."""
    df = pd.read_parquet(paths.data_dir() / "silver/us/us_close.parquet")
    x = df[(df.symbol == symbol) & (df.date < day)].dropna(subset=["ret"])
    if x.empty:
        return None, None
    return float(x["ret"].iloc[-1]), x["date"].iloc[-1]


def check() -> dict:
    D = paths.data_dir()
    us = pd.read_parquet(D / "silver/us/us_close.parquet")
    f = next(p for p in (D / "silver/macro").iterdir() if p.suffix == ".parquet")
    m = pd.read_parquet(f)
    m["date"] = pd.to_datetime(m["date"]).dt.date
    out = {}
    for sym, series in (("QQQ", "NASDAQCOM"), ("SPY", "SP500")):
        fr = m[m.series == series].sort_values("date").set_index("date")["value"].pct_change().rename("fred")
        t = us[us.symbol == sym].set_index("date")["ret"].rename("tiingo")
        j = pd.concat([t, fr], axis=1).dropna()

        def b(x):
            return (x >= 0.005).astype(int) - (x <= -0.005).astype(int)

        out[f"{sym}_vs_{series}"] = {"days": int(len(j)), "first": str(j.index.min()), "last": str(j.index.max()),
                                     "corr": round(float(j.corr().iloc[0, 1]), 4),
                                     "bucket_agreement": round(float((b(j.tiingo) == b(j.fred)).mean()), 4)}
    out["at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    (D / "manifests/us_close_check.json").write_text(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    paths.ensure()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "update"
    fn = {"history": history, "update": update, "check": check}[cmd]
    print(json.dumps(fn(), indent=1, default=str))
