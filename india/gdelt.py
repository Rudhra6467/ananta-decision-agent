"""World unrest and conflict, measured: daily GDELT event counts by country and type (19 Oct 2026, Market Brain stream A).

  python -m india.gdelt check          downloads one daily file and checks the column layout before anything else runs
  python -m india.gdelt fetch [from]   daily GDELT 1.0 event files (events/YYYYMMDD.export.CSV.zip, from 2013-04-01), aggregated on arrival;
                                       the raw file is deleted after aggregation (about 5-10 MB each); manifest manifests/gdelt.jsonl
  python -m india.gdelt build          silver/world/gdelt_daily.parquet (2024+ under sealed/silver) and the daily indices

What is kept per (file date, country): all events, and for CAMEO roots 14 protest, 17 coerce, 18 assault, 19 fight, 20 mass violence, plus
event code 145 (violent protest, riot): event count, mentions, articles, mean Goldstein score, mean tone. Countries are FIPS codes of the
action location (IN India, UK, FR France, PO Portugal, IR Iran, UP Ukraine, RS Russia, US, ...), plus WORLD.
Point in time: the file for date D holds events GDELT added on D (UTC), so a study may use it from the IST session of D+1.
Indices (per country and WORLD): unrest share = (14 + 145) events / all events; conflict share = (18 + 19 + 20) / all; tone. Shares, not counts,
because GDELT's total volume changes over the years.
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import json
import sys
import time
import zipfile

import pandas as pd
import requests

from india import paths

URL = "http://data.gdeltproject.org/events/{d:%Y%m%d}.export.CSV.zip"
COUNTRIES = {"IN", "PK", "CH", "US", "UK", "FR", "GM", "IT", "SP", "PO", "BE", "GR", "RS", "UP", "IR", "IZ", "IS", "SA", "AE", "QA", "YM", "LE", "SY",
             "TU", "EG", "JA", "KS", "TW", "BG", "CE", "NP", "AF", "BR", "MX", "CA", "AS", "ID", "VM", "NI", "SF", "AL", "KU", "MU"}
ROOTS = {"14": "protest", "17": "coerce", "18": "assault", "19": "fight", "20": "mass_violence"}
# GDELT 1.0 event table (58 columns from 2013-04-01): positions used here
C_ROOT, C_CODE, C_GOLD, C_MENT, C_ART, C_TONE, C_GEO, C_ADDED = 28, 26, 30, 31, 33, 34, 51, 56


def _aggregate(raw: bytes) -> list[dict]:
    z = zipfile.ZipFile(io.BytesIO(raw))
    txt = z.read(z.namelist()[0]).decode("utf-8", errors="ignore")
    acc = {}
    for row in csv.reader(io.StringIO(txt), delimiter="\t"):
        if len(row) < 58:
            continue
        geo = row[C_GEO] or "??"
        root, code = row[C_ROOT], row[C_CODE]
        keys = ["all"] + ([ROOTS[root]] if root in ROOTS else []) + (["riot"] if code == "145" else [])
        try:
            g, m, a, t = float(row[C_GOLD] or 0), int(row[C_MENT] or 0), int(row[C_ART] or 0), float(row[C_TONE] or 0)
        except ValueError:
            continue
        for c in ("WORLD", geo if geo in COUNTRIES else None):
            if c is None:
                continue
            for k in keys:
                x = acc.setdefault((c, k), [0, 0, 0, 0.0, 0.0])
                x[0] += 1; x[1] += m; x[2] += a; x[3] += g; x[4] += t
    return [{"country": c, "kind": k, "events": v[0], "mentions": v[1], "articles": v[2], "goldstein_mean": v[3] / v[0], "tone_mean": v[4] / v[0]}
            for (c, k), v in acc.items()]


def check() -> dict:
    d = dt.date(2016, 1, 1)
    r = requests.get(URL.format(d=d), timeout=60)
    z = zipfile.ZipFile(io.BytesIO(r.content))
    first = next(csv.reader(io.StringIO(z.read(z.namelist()[0]).decode("utf-8", "ignore")), delimiter="\t"))
    roots_ok = first[C_ROOT].isdigit() and 1 <= int(first[C_ROOT]) <= 20
    added_ok = first[C_ADDED].startswith("2016")
    agg = _aggregate(r.content)
    w = {a["kind"]: a["events"] for a in agg if a["country"] == "WORLD"}
    return {"columns": len(first), "root_code_sample": first[C_ROOT], "dateadded_sample": first[C_ADDED], "geo_sample": first[C_GEO],
            "layout_ok": bool(len(first) == 58 and roots_ok and added_ok), "world_counts": w, "countries_seen": len({a["country"] for a in agg})}


def fetch(start: str = "2013-04-01") -> dict:
    paths.ensure()
    man = paths.manifest_dir() / "gdelt.jsonl"
    done = set()
    if man.exists():
        done = {json.loads(x)["date"] for x in man.read_text().splitlines() if '"status": 200' in x}
    out = paths.bronze("gdelt_agg")
    out.mkdir(parents=True, exist_ok=True)
    d, n = dt.date.fromisoformat(start), 0
    end = dt.date.today() - dt.timedelta(days=1)
    s = requests.Session()
    while d <= end:
        if d.isoformat() not in done:
            row = {"date": d.isoformat(), "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
            try:
                r = s.get(URL.format(d=d), timeout=120)
                row["status"], row["bytes"] = r.status_code, len(r.content)
                if r.status_code == 200:
                    agg = _aggregate(r.content)
                    for a in agg:
                        a["date"] = d.isoformat()
                    (out / f"{d:%Y%m%d}.json").write_text(json.dumps(agg))
                    row["rows"] = len(agg)
            except Exception as e:
                row["status"], row["error"] = 0, f"{type(e).__name__}: {str(e)[:100]}"
            with man.open("a") as fh:
                fh.write(json.dumps(row) + "\n")
            n += 1
            if n % 100 == 0:
                print(f"gdelt {d} files={n}", flush=True)
            time.sleep(1.0)
        d += dt.timedelta(days=1)
    return {"files": n}


def build() -> dict:
    import pyarrow as pa
    import pyarrow.parquet as pq
    rows = []
    for p in sorted(paths.bronze("gdelt_agg").glob("*.json")):
        rows += json.loads(p.read_text())
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    hold = pd.Timestamp(paths.HOLDOUT_START)
    for part, sub in (("silver", df[df["date"] < hold]), ("sealed/silver", df[df["date"] >= hold])):
        t = paths.data_dir() / part / "world" / "gdelt_daily.parquet"
        t.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(pa.Table.from_pandas(sub.reset_index(drop=True), preserve_index=False), t)
    return {"rows": len(df), "days": int(df["date"].nunique()), "first": str(df["date"].min().date()), "last": str(df["date"].max().date())}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "check":
        print(json.dumps(check(), indent=1))
    elif cmd == "fetch":
        print(fetch(sys.argv[2] if len(sys.argv) > 2 else "2013-04-01"))
    else:
        print(json.dumps(build(), indent=1, default=str))
