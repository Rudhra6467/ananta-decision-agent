"""Lookup-only data for the India Ask (Madhav, 27 Oct 2026 night: outsider review, second round): total-return indices for fund comparisons
and NSE's IPO calendar. Public sources; written next to the fund caches the Ask already reads (DATA/mf_cache), not into the research lake:
nothing here is used by any study or rule.

  python -m india.lookupdata tri      Nifty 50 / Nifty 500 / Midcap 150 / Smallcap 250 total-return index (TRI) history from niftyindices.com
  python -m india.lookupdata ipo      NSE current and upcoming IPOs (public API)
  python -m india.lookupdata all
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import time

import requests

from india import nse, paths

TRI_INDICES = {"NIFTY 50": "Nifty 50", "NIFTY 500": "Nifty 500", "NIFTY MIDCAP 150": "Nifty Midcap 150", "NIFTY SMLCAP 250": "Nifty Smallcap 250"}
TRI_START = dt.date(2015, 1, 1)
NI = "https://www.niftyindices.com"


def _out_dir():
    d = paths.data_dir() / "mf_cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _ni_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(nse.HEADERS)
    s.get(f"{NI}/reports/historical-data", timeout=40)
    return s


def _tri_chunk(s: requests.Session, name: str, a: dt.date, b: dt.date) -> list[tuple[str, float]]:
    cinfo = "{'name':'" + name + "','startDate':'" + a.strftime("%d-%b-%Y") + "','endDate':'" + b.strftime("%d-%b-%Y") + "','indexName':'" + name + "'}"
    r = s.post(f"{NI}/BackPage/getTotalReturnIndexString", data=json.dumps({"cinfo": cinfo}), timeout=60,
               headers={"Content-Type": "application/json; charset=utf-8", "X-Requested-With": "XMLHttpRequest",
                        "Referer": f"{NI}/reports/historical-data", "Origin": NI})
    r.raise_for_status()
    j = r.json()
    rows = json.loads(j["d"]) if isinstance(j, dict) and "d" in j else j
    out = []
    for x in rows or []:
        try:
            out.append((dt.datetime.strptime(x["Date"], "%d %b %Y").date().isoformat(), float(str(x["TotalReturnsIndex"]).replace(",", ""))))
        except (KeyError, ValueError):
            continue
    return out


def tri(today: dt.date | None = None, log=print) -> dict:
    """Fill tri.json: {index: [[date, value], ...]} from TRI_START, fetching only what is missing (one-year chunks, 2 s apart)."""
    today = today or dt.date.today()
    p = _out_dir() / "tri.json"
    try:
        have = json.loads(p.read_text()).get("series") or {}
    except (OSError, ValueError):
        have = {}
    s = _ni_session()
    errors = []
    for key, name in TRI_INDICES.items():
        rows = dict(map(tuple, have.get(key) or []))
        start = (dt.date.fromisoformat(max(rows)) - dt.timedelta(days=7)) if rows else TRI_START
        a = start
        while a <= today:
            b = min(dt.date(a.year, 12, 31), today)
            try:
                rows.update(dict(_tri_chunk(s, name, a, b)))
            except Exception as e:  # noqa: BLE001  keep what we have; say what failed
                errors.append(f"{key} {a}..{b}: {type(e).__name__}")
            a = b + dt.timedelta(days=1)
            time.sleep(2)
        have[key] = sorted([d, v] for d, v in rows.items())
        log(f"{key}: {len(have[key])} days, last {have[key][-1][0] if have[key] else None}")
    j = {"built_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "source": f"{NI} total returns index (TRI), public",
         "series": have, "errors": errors}
    p.write_text(json.dumps(j))
    return {k: len(v) for k, v in have.items()} | {"errors": errors}


IPO_URLS = {"current": "https://www.nseindia.com/api/ipo-current-issue", "upcoming": "https://www.nseindia.com/api/all-upcoming-issues?category=ipo"}


def _ipo_rows(rows: list) -> list[dict]:
    keep = ("symbol", "companyName", "series", "issueStartDate", "issueEndDate", "issuePrice", "issueSize", "status", "noOfSharesOffered",
            "noOfsharesBid", "noOfTime", "isBse", "lotSize", "priceBand")
    out = []
    for x in rows or []:
        if isinstance(x, dict):
            out.append({k: x.get(k) for k in keep if x.get(k) not in (None, "", "-")})
    return out


def ipo(log=print) -> dict:
    s = requests.Session()
    s.headers.update(nse.HEADERS)
    try:
        old = json.loads((_out_dir() / "ipo.json").read_text())
    except (OSError, ValueError):
        old = {}
    j = {"built_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "source": "NSE public IPO API", "errors": []}
    for k, url in IPO_URLS.items():
        try:
            r = s.get(url, timeout=30)
            r.raise_for_status()
            d = r.json()
            j[k] = _ipo_rows(d if isinstance(d, list) else d.get("data") or [])
        except Exception as e:  # noqa: BLE001  a failed fetch keeps the last good list, marked stale
            j[k] = old.get(k) or []
            j["errors"].append(f"{k}: {type(e).__name__} (kept the list from {str(old.get('built_at', ''))[:10] or 'nowhere'})")
        time.sleep(1.5)
    (_out_dir() / "ipo.json").write_text(json.dumps(j, indent=1))
    log(f"IPO: {len(j['current'])} open now, {len(j['upcoming'])} upcoming; errors {j['errors']}")
    return {"current": len(j["current"]), "upcoming": len(j["upcoming"]), "errors": j["errors"]}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd in ("tri", "all"):
        print(json.dumps(tri()))
    if cmd in ("ipo", "all"):
        print(json.dumps(ipo()))
