"""NSE public files: where each daily file lives, how it is fetched politely, and how it lands in bronze.

Patterns (TradingQnA thread on the July 2024 change; the probe confirms them):
  cash bhavcopy, old   https://nsearchives.nseindia.com/content/historical/EQUITIES/2024/JUL/cm05JUL2024bhav.csv.zip
  cash bhavcopy, UDiFF https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_20240708_F_0000.csv.zip
  F&O bhavcopy, old    https://nsearchives.nseindia.com/content/historical/DERIVATIVES/2024/JUL/fo05JUL2024bhav.csv.zip
  F&O bhavcopy, UDiFF  https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_20240708_F_0000.csv.zip
  delivery (full)      https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_08072024.csv
  delivery (MTO)       https://nsearchives.nseindia.com/archives/equities/mto/MTO_08072024.DAT
NSE's servers refuse bare scripts, so every request carries browser headers, keeps a minimum gap, and backs off on
403, 429 and 5xx. A 404 on a weekday is recorded as "no file" (holiday) and never retried blindly.
Nothing here edits a downloaded file; bronze is append-only and each fetch is a manifest line.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import time
from pathlib import Path

import requests

from india import paths

ARCH = "https://nsearchives.nseindia.com"
UDIFF_FROM = dt.date(2024, 7, 8)
MON = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
    "Connection": "keep-alive",
}


def _ymd(d: dt.date) -> str:
    return d.strftime("%Y%m%d")


def _dmy(d: dt.date) -> str:
    return d.strftime("%d%m%Y")


def _old(d: dt.date) -> str:
    return f"{d:%d}{MON[d.month - 1]}{d:%Y}"


def cm_urls(d: dt.date) -> list[str]:
    """Cash bhavcopy candidates, most likely first."""
    new = f"{ARCH}/content/cm/BhavCopy_NSE_CM_0_0_0_{_ymd(d)}_F_0000.csv.zip"
    old = f"{ARCH}/content/historical/EQUITIES/{d:%Y}/{MON[d.month - 1]}/cm{_old(d)}bhav.csv.zip"
    return [new, old] if d >= UDIFF_FROM else [old, new]


def fo_urls(d: dt.date) -> list[str]:
    new = f"{ARCH}/content/fo/BhavCopy_NSE_FO_0_0_0_{_ymd(d)}_F_0000.csv.zip"
    old = f"{ARCH}/content/historical/DERIVATIVES/{d:%Y}/{MON[d.month - 1]}/fo{_old(d)}bhav.csv.zip"
    return [new, old] if d >= UDIFF_FROM else [old, new]


def delivery_urls(d: dt.date) -> list[str]:
    full = f"{ARCH}/products/content/sec_bhavdata_full_{_dmy(d)}.csv"
    mto = f"{ARCH}/archives/equities/mto/MTO_{_dmy(d)}.DAT"
    return [full, mto]


URLS = {"cm_bhavcopy": cm_urls, "fo_bhavcopy": fo_urls, "delivery": delivery_urls}
EXT = {"cm_bhavcopy": ".csv.zip", "fo_bhavcopy": ".csv.zip", "delivery": ".csv"}


class Fetcher:
    """One polite session: a minimum gap between requests and a backoff that grows on refusals."""

    def __init__(self, rate_s: float = 1.0, timeout: int = 40):
        self.s = requests.Session()
        self.s.headers.update(HEADERS)
        self.rate_s = rate_s
        self.timeout = timeout
        self._last = 0.0
        self.calls = 0
        self.refusals = 0

    def _wait(self) -> None:
        gap = self.rate_s - (time.time() - self._last)
        if gap > 0:
            time.sleep(gap)

    def get(self, url: str) -> tuple[int, bytes, float]:
        """(status, body, seconds). 404 comes back as is; 403/429/5xx are retried three times with growing sleeps."""
        for k in range(4):
            self._wait()
            t0 = time.time()
            try:
                r = self.s.get(url, timeout=self.timeout)
                status, body = r.status_code, r.content
            except requests.RequestException:
                status, body = 599, b""
            self._last = time.time()
            self.calls += 1
            if status == 200 or status == 404:
                return status, body, round(self._last - t0, 2)
            self.refusals += 1
            if k < 3:
                time.sleep(5 * (3 ** k))
        return status, body, round(self._last - t0, 2)


def _manifest(dataset: str) -> Path:
    paths.manifest_dir().mkdir(parents=True, exist_ok=True)
    return paths.manifest_dir() / f"{dataset}.jsonl"


def manifest_rows(dataset: str) -> dict[str, dict]:
    """Latest manifest line per date."""
    p = _manifest(dataset)
    out: dict[str, dict] = {}
    if p.exists():
        for line in p.read_text().splitlines():
            if line.strip():
                row = json.loads(line)
                out[row["date"]] = row
    return out


def bronze_file(dataset: str, d: dt.date) -> Path:
    return paths.bronze(dataset) / f"{d:%Y}" / f"{dataset}_{_ymd(d)}{EXT[dataset]}"


def fetch_day(f: Fetcher, dataset: str, d: dt.date) -> dict:
    """Try each candidate URL for the day; write the first 200 to bronze; always append one manifest line."""
    row: dict = {"date": d.isoformat(), "dataset": dataset, "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    status, body, secs, url, got = 404, b"", 0.0, "", False
    for url in URLS[dataset](d):
        status, body, secs = f.get(url)
        if status != 200 or not body:
            continue
        # NSE answers some missing days with an HTML page and status 200; a real file is a zip or a csv
        if body[:2] == b"PK" or (b"," in body[:200] and b"<html" not in body[:200].lower()):
            got = True
            break
        status = 204   # a page, not a file: try the other pattern
    row.update(url=url, status=status, seconds=secs, bytes=len(body) if got else 0)
    if got:
        out = bronze_file(dataset, d)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(body)
        row.update(path=str(out.relative_to(paths.data_dir())), sha256=hashlib.sha256(body).hexdigest())
    elif status == 204:
        row["note"] = "200 with a non-file body"
    with _manifest(dataset).open("a") as fh:
        fh.write(json.dumps(row) + "\n")
    return row


def weekdays(start: dt.date, end: dt.date):
    d = start
    while d <= end:
        if d.weekday() < 5:
            yield d
        d += dt.timedelta(days=1)
