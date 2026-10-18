"""NSE financial-results filings index, by date window (point-in-time: every filing carries its broadcast timestamp), then XBRL files.

  python -m india.results index [from_year]     weekly windows from from_year (default 2005) to today -> bronze/results_index/
  python -m india.results xbrl [first_filing_year]   XBRL files for filings that have one, newest first, resumable -> bronze/xbrl/
The index is the whole point-in-time table (symbol, ISIN, period, consolidated flag, audited flag, broadcast time, XBRL link). Raw statements
stay on this Mac; only ratios we derive are ever shown anywhere else. One polite session, 1.5 s between requests.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
import time

import requests

from india import nse, paths

API = "https://www.nseindia.com/api/corporates-financial-results"
REF = {"Referer": "https://www.nseindia.com/companies-listing/corporate-filings-financial-results"}


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({**nse.HEADERS, "Accept": "application/json, text/plain, */*", "Accept-Language": "en-US,en;q=0.9"})
    s.get("https://www.nseindia.com/", timeout=20)
    time.sleep(1)
    return s


def index(from_year: int = 2005) -> dict:
    paths.ensure()
    s = _session()
    man = paths.manifest_dir() / "results_index.jsonl"
    done = set()
    if man.exists():
        for line in man.read_text().splitlines():
            r = json.loads(line)
            if r.get("status") == 200:
                done.add((r["period"], r["from"]))
    d = dt.date(from_year, 1, 1)
    today = dt.date.today()
    n = rows = 0
    while d <= today:
        e = min(d + dt.timedelta(days=6), today)
        for period in ("Quarterly", "Annual"):
            key = (period, d.isoformat())
            if key in done and e < today - dt.timedelta(days=7):
                continue
            url = f"{API}?index=equities&period={period}&from_date={d:%d-%m-%Y}&to_date={e:%d-%m-%Y}"
            st, j = 0, None
            for k in range(3):
                try:
                    r = s.get(url, headers=REF, timeout=40)
                    st = r.status_code
                    if st == 200:
                        j = r.json()
                        break
                except (requests.RequestException, ValueError):
                    st = 599
                time.sleep(5 * (k + 1))
                s = _session()
            time.sleep(1.5)
            row = {"period": period, "from": d.isoformat(), "to": e.isoformat(), "status": st, "n": len(j) if isinstance(j, list) else 0,
                   "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
            if isinstance(j, list) and j:
                out = paths.bronze("results_index") / f"{d:%Y}" / f"{period}_{d.isoformat()}.json"
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(json.dumps(j))
                rows += len(j)
            with man.open("a") as fh:
                fh.write(json.dumps(row) + "\n")
            n += 1
        if d.day <= 7 and d.month in (1, 4, 7, 10):
            print(f"index {d} windows={n} filings={rows}", flush=True)
        d = e + dt.timedelta(days=1)
    return {"windows": n, "filings": rows}


IF_API = "https://www.nseindia.com/api/integrated-filing-results"
IF_REF = {"Referer": "https://www.nseindia.com/companies-listing/corporate-integrated-filing"}


def index_integrated(from_date: str = "2025-01-01") -> dict:
    """From early 2025 companies file results as SEBI's Integrated Filing (Financials); the old results API returns almost nothing after 2024 (found 18 Oct 2026:
    3,999 filings for 2025 against 17,902 for 2024). Same weekly windows, same point-in-time fields (broadcast_Date), saved to bronze/results_index_integrated/."""
    paths.ensure()
    s = _session()
    man = paths.manifest_dir() / "results_index_integrated.jsonl"
    done = set()
    if man.exists():
        for line in man.read_text().splitlines():
            r = json.loads(line)
            if r.get("status") == 200:
                done.add(r["from"])
    d = dt.date.fromisoformat(from_date)
    today = dt.date.today()
    n = rows = 0
    while d <= today:
        e = min(d + dt.timedelta(days=6), today)
        if d.isoformat() in done and e < today - dt.timedelta(days=7):
            d = e + dt.timedelta(days=1)
            continue
        url = f"{IF_API}?index=equities&type=Integrated%20Filing-%20Financials&from_date={d:%d-%m-%Y}&to_date={e:%d-%m-%Y}"
        st, j = 0, None
        for k in range(3):
            try:
                r = s.get(url, headers=IF_REF, timeout=40)
                st = r.status_code
                if st == 200:
                    j = r.json()
                    break
            except (requests.RequestException, ValueError):
                st = 599
            time.sleep(5 * (k + 1))
            s = _session()
        time.sleep(1.5)
        data = j.get("data", []) if isinstance(j, dict) else (j or [])
        row = {"from": d.isoformat(), "to": e.isoformat(), "status": st, "n": len(data), "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
        if data:
            out = paths.bronze("results_index_integrated") / f"{d:%Y}" / f"IF_{d.isoformat()}.json"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(data))
            rows += len(data)
        with man.open("a") as fh:
            fh.write(json.dumps(row) + "\n")
        n += 1
        d = e + dt.timedelta(days=1)
    return {"windows": n, "filings": rows}


def priority_isins() -> set:
    """ISINs of the companies that were ever among the 500 most liquid stocks from 2018 (lab universe, by company entity), so the names the research and the
    paper book use are fetched first; every other filing follows in a second pass."""
    import pandas as pd

    u = pd.read_parquet(paths.gold() / "universe" / "u_liq_in.parquet", columns=["date", "sid", "top500"])
    sids = set(u.loc[u["top500"] & (pd.to_datetime(u["date"]) >= "2018-01-01"), "sid"])
    names = pd.read_parquet(paths.data_dir() / "silver/security_master/names.parquet", columns=["isin", "entity"])
    return set(names.loc[names["entity"].isin(sids), "isin"]) | {s for s in sids if str(s).startswith("INE")}


def xbrl(first_year: int = 2018) -> dict:
    paths.ensure()
    f = nse.Fetcher(rate_s=1.0)
    man = paths.manifest_dir() / "xbrl.jsonl"
    done = set()
    if man.exists():
        for line in man.read_text().splitlines():
            r = json.loads(line)
            if r.get("status") in (200, 404):
                done.add(r["url"])
    n = ok = 0
    pri = priority_isins()
    print(f"priority ISINs (ever in the 500 most liquid since 2018): {len(pri)}", flush=True)
    files = sorted((paths.bronze("results_index")).glob("*/*.json"), reverse=True)
    passes = [("priority", lambda x: x.get("isin") in pri), ("rest", lambda x: x.get("isin") not in pri)]
    for pname, keep in passes:
      for fp in files:
        if int(fp.parent.name) < first_year:
            continue
        for x in json.loads(fp.read_text()):
            u = x.get("xbrl") or ""
            if not u or u.endswith("/-") or u in done or not keep(x):
                continue
            done.add(u)
            st, body, secs = f.get(u)
            row = {"url": u, "status": st, "bytes": len(body) if st == 200 else 0, "isin": x.get("isin"), "symbol": x.get("symbol")}
            if st == 200 and body[:5] == b"<?xml":
                out = paths.bronze("xbrl") / fp.parent.name / u.rsplit("/", 1)[-1]
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(body)
                row.update(path=str(out.relative_to(paths.data_dir())), sha256=hashlib.sha256(body).hexdigest())
                ok += 1
            with man.open("a") as fh:
                fh.write(json.dumps(row) + "\n")
            n += 1
            if n % 500 == 0:
                print(f"xbrl {fp.parent.name} fetched={n} files={ok} refusals={f.refusals}", flush=True)
    return {"fetched": n, "files": ok}


if __name__ == "__main__":
    paths.ensure()
    if sys.argv[1] == "index":
        print(index(int(sys.argv[2]) if len(sys.argv) > 2 else 2005))
    elif sys.argv[1] == "integrated":
        print(index_integrated(sys.argv[2] if len(sys.argv) > 2 else "2025-01-01"))
    else:
        print(xbrl(int(sys.argv[2]) if len(sys.argv) > 2 else 2018))
