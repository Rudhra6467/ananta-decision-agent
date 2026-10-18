"""Surveillance lists (ASM, GSM) and the past-IPO list from NSE (D19, D21).

  python -m india.surveil snapshot     today's ASM and GSM lists -> bronze/surveillance/<date>_{asm,gsm}.json (run nightly: the history starts now)
  python -m india.surveil ipo          the past-issues list -> bronze/ipo/past_issues_<date>.json and silver/ipo/past_issues.parquet
  python -m india.surveil build        silver/surveillance/lists.parquet from every snapshot

NSE serves only the current surveillance lists; no free history was found, so the point-in-time record is built forward from 18 Oct 2026 and labelled so.
"""
from __future__ import annotations

import datetime as dt
import json
import sys

import pandas as pd

from india import nse, paths, results

REF = {"Referer": "https://www.nseindia.com/reports/asm"}


def _get(url: str):
    s = results._session()
    nse._global_slot()
    r = s.get(url, headers=REF, timeout=40)
    r.raise_for_status()
    return r.json()


def snapshot() -> dict:
    d = dt.date.today().isoformat()
    out = {}
    for k, u in (("asm", "https://www.nseindia.com/api/reportASM"), ("gsm", "https://www.nseindia.com/api/reportGSM")):
        j = _get(u)
        p = paths.bronze("surveillance") / f"{d}_{k}.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(j))
        out[k] = sum(len(v.get("data", [])) for v in j.values()) if isinstance(j, dict) else len(j)
    return out


def build() -> dict:
    rows = []
    for p in sorted(paths.bronze("surveillance").glob("*_*.json")):
        d, k = p.stem.split("_")
        j = json.loads(p.read_text())
        items = [(grp, x) for grp, v in j.items() for x in v.get("data", [])] if isinstance(j, dict) else [("gsm", x) for x in j]
        for grp, x in items:
            rows.append({"snapshot": d, "list": k, "group": grp, "symbol": x.get("symbol"), "isin": x.get("isin"), "stage": x.get("asmSurvIndicator") or x.get("gsmStage"),
                         "code": x.get("survCode"), "since": x.get("asmTime") or x.get("gsmTime")})
    df = pd.DataFrame(rows)
    t = paths.data_dir() / "sealed/silver/surveillance/lists.parquet"  # every snapshot is 2026: holdout years
    t.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(t, index=False)
    return {"rows": len(df), "snapshots": int(df["snapshot"].nunique()) if len(df) else 0}


def ipo() -> dict:
    j = _get("https://www.nseindia.com/api/public-past-issues")
    d = dt.date.today().isoformat()
    p = paths.bronze("ipo") / f"past_issues_{d}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(j))
    df = pd.DataFrame(j)
    for c in ("ipoStartDate", "ipoEndDate", "listingDate"):
        if c in df:
            df[c] = pd.to_datetime(df[c], format="%d-%b-%Y", errors="coerce")
    df["issue_price"] = pd.to_numeric(df.get("issuePrice"), errors="coerce")
    hold = pd.Timestamp(paths.HOLDOUT_START)
    for part, sub in (("silver", df[df["listingDate"] < hold]), ("sealed/silver", df[~(df["listingDate"] < hold)])):
        t = paths.data_dir() / part / "ipo" / "past_issues.parquet"
        t.parent.mkdir(parents=True, exist_ok=True)
        sub.to_parquet(t, index=False)
    return {"issues": len(df), "with_issue_price": int(df["issue_price"].notna().sum()), "first_listing": str(df["listingDate"].min()), "last_listing": str(df["listingDate"].max()),
            "types": df.get("securityType", pd.Series(dtype=str)).value_counts().head(5).to_dict()}


if __name__ == "__main__":
    paths.ensure()
    w = sys.argv[1]
    print(json.dumps({"snapshot": snapshot, "build": build, "ipo": ipo}[w](), indent=1, default=str))
