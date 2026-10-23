"""FII/DII cash-market flows (D17): the daily provisional FII/FPI and DII buy, sell and net values (Rs crore, all exchanges) and the depositories'
confirmed FPI equity figures, captured every evening from the pages that publish them, typed into silver (2024+ under sealed/silver).

  python -m india.fiidii snapshot     MSE's FII/DII activity page (provisional, T day) and NSDL's latest FPI report (confirmed, custodian, to T-1)
                                      -> bronze/flows/fii_dii_cash/<year>/msei_<date>.json, bronze/flows/nsdl_fpi/<year>/nsdl_<date>.html;
                                         manifests/fii_dii_cash.jsonl (one line per source per capture: date, status, values)
  python -m india.fiidii build        silver/flows/fii_dii_cash.parquet (date, source, category, buy_cr, sell_cr, net_cr) ; manifests/fii_dii_build.json
  python -m india.fiidii coverage     sessions captured against the calendar, per year and source -> manifests/fii_dii_coverage.json

History (23 Oct 2026 probe from Toronto): NSE's www host (the FII/DII archive) answers "not accessible in your region"; NSDL and CDSL show one
day on their public pages; SEBI's statistics page shows one day. No free daily history was reachable, so this dataset builds forward from
today; the derivatives positioning (participant OI, india/flows.py) remains the only FII/DII history in the lake and is labelled apart.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import io
import json
import re
import sys

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import requests

from india import nse, paths

MSEI = "https://www.msei.in/downloads/equity-reports/fii-dii-activities"
NSDL = "https://www.fpi.nsdl.co.in/web/Reports/Latest.aspx"


def _man():
    return paths.manifest_dir() / "fii_dii_cash.jsonl"


def _num(x) -> float | None:
    try:
        return float(str(x).replace(",", ""))
    except ValueError:
        return None


def parse_msei(html: str) -> list[dict]:
    """The two tables (FII/FPI, DII): category, date, buy, sell, net in Rs crore."""
    out = []
    for t in pd.read_html(io.StringIO(html)):
        cols = [re.sub(r"\s+", " ", str(c)).strip() for c in t.columns]
        if "Category" not in cols or "Buy Value" not in cols:
            continue
        for r in t.itertuples(index=False):
            cat = str(r[0]).strip()
            if cat.startswith("As on") or cat not in ("FII/FPI", "DII"):
                continue
            d = pd.to_datetime(str(r[1]), format="%d-%b-%Y", errors="coerce")
            if d is pd.NaT or d != d:
                continue
            out.append({"date": d.date().isoformat(), "category": "FII" if cat.startswith("FII") else "DII", "buy_cr": _num(r[2]), "sell_cr": _num(r[3]), "net_cr": _num(r[4])})
    return out


def parse_nsdl(html: str) -> list[dict]:
    """NSDL's latest daily FPI table: the Equity 'Stock Exchange' and 'Primary market & others' rows (gross purchases, gross sales, net, Rs crore)."""
    t = re.sub(r"<script.*?</script>", " ", html, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"\((-?[\d,]+\.\d+)\)", r"-\1", t)          # NSDL writes negatives in parentheses
    m = re.search(r"Daily Trends in FPI Investments on (\d{2}-[A-Za-z]{3}-\d{4})", t)
    if not m:
        return []
    rep = pd.to_datetime(m.group(1), format="%d-%b-%Y").date().isoformat()
    num = r"(-?[\d,]+\.\d+)"
    out = []
    mm = re.search(r"Equity Stock Exchange\s+" + num + r"\s+" + num + r"\s+" + num + r".*?Primary market & others\s+" + num + r"\s+" + num + r"\s+" + num, t)
    if mm:
        out.append({"date": rep, "category": "FPI_equity_exchange", "buy_cr": _num(mm.group(1)), "sell_cr": _num(mm.group(2)), "net_cr": _num(mm.group(3))})
        out.append({"date": rep, "category": "FPI_equity_primary", "buy_cr": _num(mm.group(4)), "sell_cr": _num(mm.group(5)), "net_cr": _num(mm.group(6))})
    return out


def snapshot(log=print) -> dict:
    paths.ensure()
    s = requests.Session()
    s.headers.update(nse.HEADERS)
    out = {}
    for name, url, parse, ext in (("msei", MSEI, parse_msei, "json"), ("nsdl", NSDL, parse_nsdl, "html")):
        try:
            r = s.get(url, timeout=40)
            st, body = r.status_code, r.content
        except requests.RequestException as e:
            st, body = 599, str(e).encode()
        row = {"source": name, "status": st, "bytes": len(body), "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "url": url}
        rows = []
        if st == 200:
            try:
                rows = parse(body.decode(errors="ignore"))
            except Exception as e:
                row["note"] = f"parse {type(e).__name__}: {str(e)[:80]}"
        if rows:
            d = max(x["date"] for x in rows)
            folder = paths.bronze("flows") / ("fii_dii_cash" if name == "msei" else "nsdl_fpi") / d[:4]
            folder.mkdir(parents=True, exist_ok=True)
            p = folder / f"{name}_{d.replace('-', '')}.{ext}"
            p.write_bytes(json.dumps(rows, indent=1).encode() if ext == "json" else body)
            row.update(date=d, rows=rows, path=str(p.relative_to(paths.data_dir())), sha256=hashlib.sha256(body).hexdigest())
        elif st == 200:
            row["status"] = 204
        with _man().open("a") as fh:
            fh.write(json.dumps(row) + "\n")
        out[name] = {"status": row["status"], "date": row.get("date"), "rows": rows}
        log(f"fii/dii snapshot {name}: status {row['status']} date {row.get('date')} {[(x['category'], x['net_cr']) for x in rows]}")
    return out


def build() -> dict:
    recs = []
    for p in sorted((paths.bronze("flows") / "fii_dii_cash").glob("*/*.json")):
        for x in json.loads(p.read_text()):
            recs.append({**x, "source": "MSEI provisional (all exchanges)"})
    for p in sorted((paths.bronze("flows") / "nsdl_fpi").glob("*/*.html")):
        for x in parse_nsdl(p.read_text(errors="ignore")):
            recs.append({**x, "source": "NSDL confirmed (custodians)"})
    if not recs:
        return {"rows": 0}
    df = pd.DataFrame(recs)
    df["date"] = pd.to_datetime(df["date"])
    df = df.drop_duplicates(["date", "source", "category"]).sort_values(["date", "source", "category"]).reset_index(drop=True)
    hold = pd.Timestamp(paths.HOLDOUT_START)
    for part, sub in (("silver", df[df["date"] < hold]), ("sealed/silver", df[df["date"] >= hold])):
        t = paths.data_dir() / part / "flows" / "fii_dii_cash.parquet"
        t.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(pa.Table.from_pandas(sub.reset_index(drop=True), preserve_index=False), t)
    out = {"rows": int(len(df)), "days": int(df["date"].nunique()), "first": str(df["date"].min().date()), "last": str(df["date"].max().date()),
           "rows_2024_plus_sealed": int((df["date"] >= hold).sum()), "categories": sorted(df["category"].unique()), "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    (paths.manifest_dir() / "fii_dii_build.json").write_text(json.dumps(out, indent=1, default=str))
    return out


def coverage() -> dict:
    got: dict[str, set] = {"msei": set(), "nsdl": set()}
    p = _man()
    if p.exists():
        for line in p.read_text().splitlines():
            r = json.loads(line)
            if r.get("status") == 200 and r.get("date"):
                got[r["source"]].add(r["date"])
    out = {}
    for src, ds in got.items():
        by_year: dict[int, int] = {}
        for d in ds:
            by_year[int(d[:4])] = by_year.get(int(d[:4]), 0) + 1
        rows = []
        for y, n in sorted(by_year.items()):
            sess = sum(1 for d in pd.date_range(f"{y}-01-01", min(dt.date.today(), dt.date(y, 12, 31))).date if d.weekday() < 5)
            rows.append({"year": y, "weekday_sessions_to_date": sess, "sessions_captured": n, "share": round(n / max(sess, 1), 3), "rows_per_session": 2 if src == "msei" else 2})
        out[src] = rows
    out["history"] = "none free from Toronto (NSE www geo-blocked; NSDL/CDSL/SEBI public pages show one day): forward capture from 2026-10-23"
    out["at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    (paths.manifest_dir() / "fii_dii_coverage.json").write_text(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    paths.ensure()
    a = sys.argv[1:]
    if a[:1] == ["snapshot"]:
        print(json.dumps(snapshot(), indent=1))
    elif a[:1] == ["build"]:
        print(json.dumps(build(), indent=1, default=str))
    elif a[:1] == ["coverage"]:
        print(json.dumps(coverage(), indent=1))
    else:
        print(__doc__)
