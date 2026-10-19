"""NSE corporate announcements with exact dissemination times (19 Oct 2026). Replaces the PR-zip announcement files as the company-event
source: those files carry no time of day and thin out badly from mid-2021 to end-2022 (documented in india.integrity KNOWN_GAPS).

  python -m india.announce fetch [from_year]   one request per trading day, oldest first, resumable; raw JSON to
                                               bronze/announce_api/<year>/<yyyymmdd>.json.gz; manifest manifests/announce_api.jsonl
  python -m india.announce build               silver/announce/announcements.parquet (2024+ under sealed/silver): symbol, isin, industry,
                                               category (NSE's desc), subject text (first 400 chars), an_dt and exchdisstime as IST timestamps

Point in time: a study may use an announcement from its exchange dissemination time (exchdisstime); after 15:30 IST it is tradable the
next session. Personal-use data: raw rows stay on this Mac (bronze is not synced).
"""
from __future__ import annotations

import datetime as dt
import gzip
import json
import sys

import pandas as pd

from india import nse, paths

URL = "https://www.nseindia.com/api/corporate-announcements?index=equities&from_date={d:%d-%m-%Y}&to_date={d:%d-%m-%Y}"


def _days(from_year: int) -> list[dt.date]:
    cal = pd.read_parquet(paths.data_dir() / "silver/calendar/calendar.parquet")
    d = sorted(pd.to_datetime(cal.loc[cal["is_trading_day"], "date"]).dt.date)
    days = [x for x in d if x.year >= from_year]
    x = (days[-1] if days else dt.date(from_year, 1, 1)) + dt.timedelta(days=1)
    while x < dt.date.today():
        if x.weekday() < 5:
            days.append(x)
        x += dt.timedelta(days=1)
    return days


def fetch(from_year: int = 2010) -> dict:
    paths.ensure()
    man = paths.manifest_dir() / "announce_api.jsonl"
    done = set()
    if man.exists():
        for line in man.read_text().splitlines():
            r = json.loads(line)
            if r.get("status") == 200:
                done.add(r["date"])
    f = nse.Fetcher(rate_s=1.0)
    n = rows_total = 0
    for d in _days(from_year):
        if d.isoformat() in done:
            continue
        st, body, secs = f.get(URL.format(d=d))
        row = {"date": d.isoformat(), "status": st, "bytes": len(body), "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
        if st == 200:
            try:
                data = json.loads(body)
                row["rows"] = len(data) if isinstance(data, list) else None
                out = paths.bronze("announce_api") / str(d.year) / f"{d:%Y%m%d}.json.gz"
                out.parent.mkdir(parents=True, exist_ok=True)
                with gzip.open(out, "wb") as fh:
                    fh.write(body)
                rows_total += row["rows"] or 0
            except ValueError:
                row["status"] = 520  # an HTML page instead of JSON: retried on the next run
        with man.open("a") as fh:
            fh.write(json.dumps(row) + "\n")
        n += 1
        if n % 100 == 0:
            print(f"announce {d} days={n} rows={rows_total}", flush=True)
    return {"days": n, "rows": rows_total}


def build() -> dict:
    import pyarrow as pa
    import pyarrow.parquet as pq
    frames = []
    for p in sorted(paths.bronze("announce_api").glob("*/*.json.gz")):
        data = json.loads(gzip.open(p).read())
        if not data:
            continue
        df = pd.DataFrame(data)
        keep = [c for c in ("symbol", "sm_isin", "sm_name", "smIndustry", "desc", "attchmntText", "an_dt", "exchdisstime", "seq_id", "attchmntFile") if c in df]
        df = df[keep].rename(columns={"sm_isin": "isin", "sm_name": "company", "smIndustry": "industry", "desc": "category", "attchmntText": "text"})
        df["text"] = df["text"].astype(str).str[:400]
        for c in ("an_dt", "exchdisstime"):
            if c in df:
                df[c] = pd.to_datetime(df[c], format="%d-%b-%Y %H:%M:%S", errors="coerce")
        df["file_date"] = pd.to_datetime(p.name[:8])
        frames.append(df)
    if not frames:
        return {"rows": 0}
    df = pd.concat(frames, ignore_index=True).drop_duplicates("seq_id")
    t = df["exchdisstime"].fillna(df["an_dt"])
    df["tradable_from"] = t.where(t.dt.time < dt.time(15, 30), t.dt.normalize() + pd.Timedelta(days=1))  # refined to the next session by the studies
    hold = pd.Timestamp(paths.HOLDOUT_START)
    for part, sub in (("silver", df[df["file_date"] < hold]), ("sealed/silver", df[df["file_date"] >= hold])):
        out = paths.data_dir() / part / "announce" / "announcements.parquet"
        out.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(pa.Table.from_pandas(sub.reset_index(drop=True), preserve_index=False), out)
    return {"rows": len(df), "days": int(df["file_date"].nunique()), "with_time": int(t.notna().sum()), "categories": int(df["category"].nunique())}


if __name__ == "__main__":
    paths.ensure()
    if sys.argv[1] == "fetch":
        print(fetch(int(sys.argv[2]) if len(sys.argv) > 2 else 2010))
    else:
        print(json.dumps(build(), indent=1, default=str))
