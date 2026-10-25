"""Index valuation series (D30): daily P/E, P/B and dividend yield for the Nifty 50, Nifty Bank and Nifty 500, from NSE Indices.

  python -m india.valuation fetch [from_year]   one request per index per calendar year (1999 on; the current year is always fetched again)
                                                -> bronze/valuation/<INDEX>/<year>.json ; manifests/valuation.jsonl
  python -m india.valuation build               silver/valuation/index_pepb.parquet (date, index_name, pe, pb, div_yield), 2024+ under
                                                sealed/silver/valuation ; manifests/valuation_build.json

Source: niftyindices.com/BackPage/getpepbHistoricaldataDBtoString (the endpoint behind its historical-data page; 25 Oct 2026 it answers with the
path spelled BackPage, the 18 Oct probe used Backpage and got the site's HTML page instead). A day's values are published after that day's
close: a study may use them from the next session. Method break: from 31 Mar 2021 NSE computes the index P/E on consolidated earnings
(standalone before): the Nifty 50 P/E fell from 40.4 to 33.2 that day while P/B stayed at 4.2 (the largest one-day P/E move in the series,
7.2 points against 3.1 for the next largest) and the dividend yield stepped from 1.07 to 0.96; a study comparing P/E or yield levels across
2021 must allow for it (pe_basis column).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import requests

from india import nse, paths

URL = "https://www.niftyindices.com/BackPage/getpepbHistoricaldataDBtoString"
PAGE = "https://www.niftyindices.com/reports/historical-data"
INDICES = ("NIFTY 50", "NIFTY BANK", "NIFTY 500")
FIRST_YEAR = 1999
METHOD_BREAK = "2021-03-31"


def parse(text: str) -> list[dict]:
    """The endpoint's JSON (a list, or {'d': '<list as text>'}) -> date, index_name, pe, pb, div_yield. Blank or '-' values become None."""
    d = json.loads(text)
    if isinstance(d, dict) and "d" in d:
        d = json.loads(d["d"]) if isinstance(d["d"], str) else d["d"]
    out = []
    for r in d or []:
        day = pd.to_datetime(str(r.get("DATE", "")), format="%d %b %Y", errors="coerce")
        if day is pd.NaT or day != day:
            continue

        def num(x):
            try:
                return float(str(x).replace(",", ""))
            except (TypeError, ValueError):
                return None
        out.append({"date": day.date().isoformat(), "index_name": str(r.get("Index Name", "")).upper(), "pe": num(r.get("pe")), "pb": num(r.get("pb")),
                    "div_yield": num(r.get("divYield"))})
    return out


def _man():
    return paths.manifest_dir() / "valuation.jsonl"


def fetch(from_year: int = FIRST_YEAR, log=print) -> dict:
    paths.ensure()
    done = set()
    if _man().exists():
        for line in _man().read_text().splitlines():
            r = json.loads(line)
            if r.get("status") == 200 and r.get("rows"):
                done.add((r["index"], r["year"]))
    s = requests.Session()
    s.headers.update(nse.HEADERS)
    s.get(PAGE, timeout=40)
    this = dt.date.today().year
    got = rows = 0
    for name in INDICES:
        for y in range(from_year, this + 1):
            if (name, y) in done and y != this:
                continue
            a, b = f"01-Jan-{y}", (dt.date.today() if y == this else dt.date(y, 12, 31)).strftime("%d-%b-%Y")
            cinfo = "{'name':'" + name + "','startDate':'" + a + "','endDate':'" + b + "','indexName':'" + name + "'}"
            nse._global_slot(1.5)
            try:
                r = s.post(URL, data=json.dumps({"cinfo": cinfo}), timeout=60,
                           headers={"Content-Type": "application/json; charset=utf-8", "X-Requested-With": "XMLHttpRequest", "Referer": PAGE,
                                    "Origin": "https://www.niftyindices.com"})
                st, body = r.status_code, r.content
            except requests.RequestException as e:
                st, body = 599, str(e).encode()
            try:
                recs = parse(body.decode("utf-8", "ignore")) if st == 200 else []
            except ValueError:
                recs, st = [], 204          # the site's HTML page instead of data
            row = {"index": name, "year": y, "status": st, "rows": len(recs), "bytes": len(body), "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
            if recs:
                p = paths.bronze("valuation") / name.replace(" ", "_") / f"{y}.json"
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(body)
                row.update(path=str(p.relative_to(paths.data_dir())), sha256=hashlib.sha256(body).hexdigest())
                got += 1
                rows += len(recs)
            with _man().open("a") as fh:
                fh.write(json.dumps(row) + "\n")
            log(f"valuation {name} {y}: status {st}, {len(recs)} rows")
    return {"files": got, "rows": rows}


def build() -> dict:
    recs = []
    for p in sorted(paths.bronze("valuation").glob("*/*.json")):
        recs.extend(parse(p.read_text(errors="ignore")))
    if not recs:
        return {"rows": 0}
    df = pd.DataFrame(recs)
    df["date"] = pd.to_datetime(df["date"])
    df = df.drop_duplicates(["date", "index_name"], keep="last").sort_values(["index_name", "date"]).reset_index(drop=True)
    df["pe_basis"] = (df["date"] >= pd.Timestamp(METHOD_BREAK)).map({True: "consolidated", False: "standalone"})
    hold = pd.Timestamp(paths.HOLDOUT_START)
    for part, sub in (("silver", df[df["date"] < hold]), ("sealed/silver", df[df["date"] >= hold])):
        t = paths.data_dir() / part / "valuation" / "index_pepb.parquet"
        t.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(pa.Table.from_pandas(sub.reset_index(drop=True), preserve_index=False), t)
    by = {n: {"rows": int(len(g)), "first": str(g["date"].min().date()), "last": str(g["date"].max().date()), "pe_missing": int(g["pe"].isna().sum())}
          for n, g in df.groupby("index_name")}
    out = {"rows": int(len(df)), "by_index": by, "rows_2024_plus_sealed": int((df["date"] >= hold).sum()), "method_break": METHOD_BREAK,
           "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    (paths.manifest_dir() / "valuation_build.json").write_text(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    paths.ensure()
    a = sys.argv[1:]
    if a[:1] == ["fetch"]:
        print(json.dumps(fetch(int(a[1]) if len(a) > 1 else FIRST_YEAR), indent=1))
    elif a[:1] == ["build"]:
        print(json.dumps(build(), indent=1, default=str))
    else:
        print(__doc__)
