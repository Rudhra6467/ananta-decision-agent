"""Bulk and block deals (the blueprint's D3; tracker D31): what is public, pulled daily, typed into silver (2024+ under sealed/silver).

  python -m india.deals snapshot      today's bulk.csv and block.csv from NSE's archive host -> bronze/deals/snap/<kind>/<year>/<kind>_<date>.csv,
                                      one manifest line per file in manifests/deals_snapshot.jsonl (date, rows, sha); run from the evening job
  python -m india.deals history       the historical service (www.nseindia.com/api/historical/bulk-deals) in 30-day chunks -> bronze/deals/<kind>/...
                                      23 Oct 2026: NSE's www host answers "not accessible in your region" from Toronto and BSE's API refuses (403),
                                      so this records the refusal in manifests/deals_history.jsonl and pulls nothing; the history waits for a
                                      reachable source (a VPN exit in India, or Madhav downloading the report by hand)
  python -m india.deals build         silver/deals/bulk.parquet, block.parquet (+ sealed/silver/deals for 2024+) from every bronze file -> manifests/deals_build.json
  python -m india.deals coverage      days with rows and rows per day against the calendar, per year, from the manifests -> manifests/deals_coverage.json

A bulk deal is a single client's trades in a stock above 0.5% of its listed shares in a day (reported by the exchange after the close); a block
deal is a negotiated trade through the block window (Rs 10 crore or more since Jan 2018). Both are what the DEALS reference trader
(india/others.py) reads: the deal is known the evening of day T, so a trader that follows it enters at T+1's open.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import io
import json
import re
import sys
import time

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import requests

from india import nse, paths

SNAP = {"bulk": "https://nsearchives.nseindia.com/content/equities/bulk.csv", "block": "https://nsearchives.nseindia.com/content/equities/block.csv"}
API = {"bulk": "https://www.nseindia.com/api/historical/bulk-deals?from={a:%d-%m-%Y}&to={b:%d-%m-%Y}",
       "block": "https://www.nseindia.com/api/historical/block-deals?from={a:%d-%m-%Y}&to={b:%d-%m-%Y}"}
CHUNK_DAYS = 30
COLS = {"Date": "date", "Symbol": "symbol", "Security Name": "name", "Client Name": "client", "Buy/Sell": "side", "Quantity Traded": "qty",
        "Trade Price / Wght. Avg. Price": "price", "Remarks": "remarks"}


def _man(name: str):
    return paths.manifest_dir() / f"deals_{name}.jsonl"


def snapshot(log=print) -> dict:
    """Today's files. The date is read from the rows (the file carries the last session's deals), so a holiday re-download is recorded as the same
    date and the build de-duplicates it."""
    paths.ensure()
    f = nse.Fetcher(rate_s=1.5)
    out = {}
    for kind, url in SNAP.items():
        st, body, secs = f.get(url)
        row = {"kind": kind, "status": st, "bytes": len(body), "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "url": url}
        if st == 200 and body[:4] == b"Date":
            df = pd.read_csv(io.BytesIO(body))
            dates = sorted(pd.to_datetime(df["Date"], format="%d-%b-%Y", errors="coerce").dropna().dt.date.unique())
            d = dates[-1] if dates else dt.date.today()
            p = paths.bronze("deals") / "snap" / kind / str(d.year) / f"{kind}_{d:%Y%m%d}.csv"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(body)
            row.update(date=d.isoformat(), rows=int(len(df)), dates_in_file=[x.isoformat() for x in dates], path=str(p.relative_to(paths.data_dir())), sha256=hashlib.sha256(body).hexdigest())
        elif st == 200:
            row["status"] = 204
        with _man("snapshot").open("a") as fh:
            fh.write(json.dumps(row) + "\n")
        out[kind] = {k: row.get(k) for k in ("status", "date", "rows")}
        log(f"deals snapshot {kind}: {out[kind]}")
    return out


def history(from_year: int = 2004, to: dt.date | None = None, log=print) -> dict:
    """The historical service, in 30-day chunks with the site's cookies. Records every answer; a geo-block page (status 200 with HTML) is logged as
    status 451 (unavailable for legal/regional reasons) and the pull stops after three such answers in a row."""
    paths.ensure()
    to = to or (dt.date.today() - dt.timedelta(days=1))
    s = requests.Session()
    s.headers.update({**nse.HEADERS, "Accept": "application/json, text/plain, */*", "Referer": "https://www.nseindia.com/report-detail/display-bulk-and-block-deals"})
    try:
        s.get("https://www.nseindia.com/", timeout=30)
    except requests.RequestException:
        pass
    out = {}
    for kind, url in API.items():
        a, n, ok, blocked = dt.date(from_year, 1, 1), 0, 0, 0
        while a <= to and blocked < 3:
            b = min(a + dt.timedelta(days=CHUNK_DAYS - 1), to)
            try:
                r = s.get(url.format(a=a, b=b), timeout=40)
                st, body = r.status_code, r.content
            except requests.RequestException:
                st, body = 599, b""
            row = {"kind": kind, "from": a.isoformat(), "to": b.isoformat(), "status": st, "bytes": len(body), "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
            if st == 200 and body[:1] in (b"{", b"["):
                p = paths.bronze("deals") / kind / str(a.year) / f"deals_{kind}_{a:%Y%m%d}_{b:%Y%m%d}.json"
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(body)
                row.update(path=str(p.relative_to(paths.data_dir())))
                ok += 1
                blocked = 0
            elif st == 200:
                txt = re.sub(r"<[^>]+>", " ", body.decode(errors="ignore"))
                row["status"] = 451 if "not accessible in your region" in txt else 204
                row["note"] = "NSE: 'This site is not accessible in your region at the moment'" if row["status"] == 451 else "200 with a non-JSON body"
                blocked += 1
            else:
                blocked += 1
            with _man("history").open("a") as fh:
                fh.write(json.dumps(row) + "\n")
            n += 1
            a = b + dt.timedelta(days=1)
            time.sleep(2.0)
        out[kind] = {"chunks": n, "ok": ok, "stopped_geo_blocked": blocked >= 3}
        log(f"deals history {kind}: {out[kind]}")
    return out


def _frames(kind: str) -> list[pd.DataFrame]:
    frames = []
    for p in sorted((paths.bronze("deals") / "snap" / kind).glob("*/*.csv")):
        df = pd.read_csv(p).rename(columns=COLS)
        df["date"] = pd.to_datetime(df["date"], format="%d-%b-%Y", errors="coerce")
        frames.append(df)
    for p in sorted((paths.bronze("deals") / kind).glob("*/*.json")):
        j = json.loads(p.read_bytes())
        recs = j.get("data", j) if isinstance(j, dict) else j
        if recs:
            df = pd.DataFrame(recs).rename(columns={"BD_DT_DATE": "date", "BD_SYMBOL": "symbol", "BD_SCRIP_NAME": "name", "BD_CLIENT_NAME": "client", "BD_BUY_SELL": "side",
                                                    "BD_QTY_TRD": "qty", "BD_TP_WATP": "price", "BD_REMARKS": "remarks"})
            df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")
            frames.append(df)
    return frames


def build() -> dict:
    out = {}
    for kind in ("bulk", "block"):
        frames = _frames(kind)
        if not frames:
            out[kind] = {"rows": 0}
            continue
        df = pd.concat(frames, ignore_index=True)
        for c in ("qty", "price"):
            if c in df:
                df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", ""), errors="coerce")
        keep = [c for c in ("date", "symbol", "name", "client", "side", "qty", "price", "remarks") if c in df]
        df = df[keep].dropna(subset=["date", "symbol"]).drop_duplicates().sort_values(["date", "symbol"], kind="mergesort").reset_index(drop=True)
        hold = pd.Timestamp(paths.HOLDOUT_START)
        for part, sub in (("silver", df[df["date"] < hold]), ("sealed/silver", df[df["date"] >= hold])):
            t = paths.data_dir() / part / "deals" / f"{kind}.parquet"
            t.parent.mkdir(parents=True, exist_ok=True)
            pq.write_table(pa.Table.from_pandas(sub.reset_index(drop=True), preserve_index=False), t)
        out[kind] = {"rows": int(len(df)), "days": int(df["date"].nunique()), "first": str(df["date"].min().date()), "last": str(df["date"].max().date()),
                     "rows_pre_2024_silver": int((df["date"] < hold).sum()), "rows_2024_plus_sealed": int((df["date"] >= hold).sum()), "columns": keep}
    out["at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    (paths.manifest_dir() / "deals_build.json").write_text(json.dumps(out, indent=1, default=str))
    return out


def coverage() -> dict:
    """Coverage rows against the calendar, per year and kind, from the snapshot manifest (no data file is read): sessions with a file, sessions
    with at least one deal, rows per session; plus the history pull's state."""
    cal = pd.read_parquet(paths.data_dir() / "silver/calendar/calendar.parquet")
    cal = cal[cal["is_trading_day"]].copy()
    cal["date"] = pd.to_datetime(cal["date"]).dt.date
    sessions = set(cal["date"]) | {d for d in pd.date_range("2024-01-01", dt.date.today()).date if d.weekday() < 5}
    got: dict[str, dict[str, int]] = {"bulk": {}, "block": {}}
    p = _man("snapshot")
    if p.exists():
        for line in p.read_text().splitlines():
            r = json.loads(line)
            if r.get("status") == 200 and r.get("date"):
                got[r["kind"]][r["date"]] = max(got[r["kind"]].get(r["date"], 0), int(r.get("rows", 0)))
    out = {}
    for kind in ("bulk", "block"):
        rows = []
        by_year: dict[int, list] = {}
        for d, n in got[kind].items():
            by_year.setdefault(int(d[:4]), []).append(n)
        for y, ns in sorted(by_year.items()):
            sess_y = sum(1 for d in sessions if d.year == y and d <= dt.date.today())
            rows.append({"year": y, "sessions": sess_y, "sessions_with_file": len(ns), "share": round(len(ns) / max(sess_y, 1), 3),
                         "sessions_with_deals": sum(1 for n in ns if n > 0), "rows_per_session": round(sum(ns) / len(ns), 1)})
        out[kind] = rows
    hist = _man("history")
    out["history"] = {"state": "not pulled: NSE www host geo-blocked from Toronto (status 451 lines) and BSE API 403 (23 Oct 2026)", "lines": len(hist.read_text().splitlines()) if hist.exists() else 0}
    out["at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    (paths.manifest_dir() / "deals_coverage.json").write_text(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    paths.ensure()
    a = sys.argv[1:]
    if a[:1] == ["snapshot"]:
        print(json.dumps(snapshot(), indent=1))
    elif a[:1] == ["history"]:
        print(json.dumps(history(int(a[1]) if len(a) > 1 else 2004), indent=1))
    elif a[:1] == ["build"]:
        print(json.dumps(build(), indent=1, default=str))
    elif a[:1] == ["coverage"]:
        print(json.dumps(coverage(), indent=1))
    else:
        print(__doc__)
