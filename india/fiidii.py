"""FII/DII cash-market flows (D17): the daily provisional FII/FPI and DII buy, sell and net values (Rs crore, all exchanges) and the depositories'
confirmed FPI equity figures, captured every evening from the pages that publish them, typed into silver (2024+ under sealed/silver).

  python -m india.fiidii snapshot     MSE's FII/DII activity page (provisional, T day) and NSDL's latest FPI report (confirmed, custodian, to T-1)
                                      -> bronze/flows/fii_dii_cash/<year>/msei_<date>.json, bronze/flows/nsdl_fpi/<year>/nsdl_<date>.html;
                                         manifests/fii_dii_cash.jsonl (one line per source per capture: date, status, values)
  python -m india.fiidii build        silver/flows/fii_dii_cash.parquet (date, source, category, buy_cr, sell_cr, net_cr) ; manifests/fii_dii_build.json
  python -m india.fiidii coverage     sessions captured against the calendar, per year and source -> manifests/fii_dii_coverage.json

  python -m india.fiidii history      NSDL's archive (Archive.aspx: one form post per month returns every reporting day of that month), Jan 2000
                                      to last month -> bronze/flows/nsdl_archive/<year>/nsdl_archive_<YYYYMM>.html; manifests/fii_dii_history.jsonl

History (25 Oct 2026): FPI history is filled from NSDL's archive, daily from 3 Jan 2000: equity gross purchases, sales and net (Rs crore), all
routes together and, from about 2011, the stock-exchange route apart; plus debt net. These are CONFIRMED custodian figures by REPORTING date:
a reporting date's row covers trades up to the previous trading day(s) and is published after that day, so a study may use it from the
session after the reporting date. DII history has no free source (NSE's www FII/DII archive page is geo-blocked; its fiidiiTradeReact API
answers but shows only the latest day, so it is captured forward as a third source from 25 Oct 2026). The derivatives positioning
(participant OI, india/flows.py) stays labelled apart.
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
NSDL_ARCHIVE = "https://www.fpi.nsdl.co.in/web/Reports/Archive.aspx"
NSE_API = "https://www.nseindia.com/api/fiidiiTradeReact"
ARCHIVE_START = dt.date(2000, 1, 1)


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


_DATE = r"\d{2}-[A-Za-z]{3}-\d{4}"
_NUM = r"-?[\d,]+\.\d+"


def parse_nsdl_archive(html: str) -> list[dict]:
    """NSDL's archive page for one month: the 'Debt/Equity' table (the derivatives table after it is ignored). Per reporting date:
    FPI_equity (all routes: the Sub-total when the page splits routes, else the single Equity line), FPI_equity_exchange (the stock-exchange
    route, when split) and FPI_debt (every debt category's net added up: Debt, Debt-General Limit, Debt-VRR, Debt-FAR)."""
    t = re.sub(r"<script.*?</script>", " ", html, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"&nbsp;|&amp;", " ", t)
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"\((-?[\d,]+\.\d+)\)", r"-\1", t)
    t = re.sub(r"Rs\.? ?[\d.]+", " ", t)                      # the USD conversion rate column
    a = t.find("Reporting Date Debt/Equity")
    if a < 0:
        return []
    b = t.find("Reporting Date Derivative", a)
    seg = t[a: b if b > 0 else len(t)]
    # the month and year totals ("Total for April", "Total for 2018") and the notes follow the last day; they are not a day
    cut = min([x for x in (seg.find("Total for "), seg.find("The data presented")) if x > 0] or [len(seg)])
    seg = seg[:cut]
    marks = [(m.start(), m.group(0)) for m in re.finditer(_DATE, seg)]
    out = []
    for i, (pos, d) in enumerate(marks):
        block = seg[pos + len(d): marks[i + 1][0] if i + 1 < len(marks) else len(seg)]
        day = pd.to_datetime(d, format="%d-%b-%Y").date().isoformat()
        # Equity and Debt count only as FPI categories (followed by a route or a number), never the mutual funds' "Equity schemes"/"Debt schemes"
        lead = r"(?= Stock Exchange| -?[\d,]+\.\d)"
        cats = [(m.start(), m.group(1)) for m in re.finditer(r"\b(Equity" + lead + r"|Debt-[A-Za-z ]+?Limit|Debt-VRR|Debt-FAR|Debt" + lead + r"|Hybrid" + lead
                                                               + r"|Mutual Funds?|AIFs?|Total)\b", block)]
        for j, (cpos, cat) in enumerate(cats):
            part = block[cpos + len(cat): cats[j + 1][0] if j + 1 < len(cats) else len(block)]
            if "Sub-total" in part:
                nums = re.findall(_NUM, part.split("Sub-total", 1)[1])
            else:
                nums = re.findall(_NUM, part)
            if len(nums) < 3:
                continue
            buy, sell, net = (_num(x) for x in nums[:3])
            if cat == "Equity":
                out.append({"date": day, "category": "FPI_equity", "buy_cr": buy, "sell_cr": sell, "net_cr": net})
                if "Stock Exchange" in part and "Sub-total" in part:
                    ex = re.findall(_NUM, part.split("Stock Exchange", 1)[1])
                    if len(ex) >= 3:
                        out.append({"date": day, "category": "FPI_equity_exchange", "buy_cr": _num(ex[0]), "sell_cr": _num(ex[1]), "net_cr": _num(ex[2])})
            elif cat.startswith("Debt"):
                prev = next((r for r in out if r["date"] == day and r["category"] == "FPI_debt"), None)
                if prev:
                    prev["buy_cr"] += buy or 0
                    prev["sell_cr"] += sell or 0
                    prev["net_cr"] += net or 0
                else:
                    out.append({"date": day, "category": "FPI_debt", "buy_cr": buy or 0.0, "sell_cr": sell or 0.0, "net_cr": net or 0.0})
    for r in out:
        for k in ("buy_cr", "sell_cr", "net_cr"):
            r[k] = None if r[k] is None else round(r[k], 2)
    return out


def archive_month_check(html: str) -> dict:
    """The page's own 'Total for <month>' equity net against the sum of its daily equity rows (a parse check; equal to the paisa when clean)."""
    rows = parse_nsdl_archive(html)
    t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>", " ", html, flags=re.S)))
    t = re.sub(r"\((-?[\d,]+\.\d+)\)", r"-\1", t)
    m = re.search(r"Total for [A-Za-z]+ Equity (.*?)(?:Debt|Total|Reporting Date|$)", t)
    if not m:
        return {"checked": False}
    part = m.group(1)
    nums = re.findall(_NUM, part.split("Sub-total", 1)[1] if "Sub-total" in part else part)
    page = _num(nums[2]) if len(nums) >= 3 else None
    mine = round(sum(r["net_cr"] or 0 for r in rows if r["category"] == "FPI_equity"), 2)
    days = len({r["date"] for r in rows})
    tol = max(0.05, 0.05 * days)     # pages before about 2014 round each day to 0.1 crore, so their month total can differ by a few tenths
    return {"checked": page is not None, "page_total": page, "sum_of_days": mine, "match": page is not None and abs(page - mine) <= tol}


def parse_nse(text: str) -> list[dict]:
    """NSE's fiidiiTradeReact JSON (latest day only): FII and DII buy, sell, net in Rs crore."""
    out = []
    for r in json.loads(text):
        d = pd.to_datetime(str(r.get("date")), format="%d-%b-%Y", errors="coerce")
        if d is pd.NaT or d != d:
            continue
        cat = "FII" if str(r.get("category", "")).upper().startswith("FII") else "DII" if str(r.get("category", "")).upper().startswith("DII") else None
        if cat:
            out.append({"date": d.date().isoformat(), "category": cat, "buy_cr": _num(r.get("buyValue")), "sell_cr": _num(r.get("sellValue")), "net_cr": _num(r.get("netValue"))})
    return out


def _hist_man():
    return paths.manifest_dir() / "fii_dii_history.jsonl"


def history(start: dt.date = ARCHIVE_START, end: dt.date | None = None, log=print) -> dict:
    """One form post per month (the month's last day: the page lists every reporting day of that month up to it). Resumable: a month already
    saved with rows is skipped, except the current month. 1.5 s between posts and the global NSE-family limiter is not needed (NSDL host)."""
    import time

    paths.ensure()
    end = end or dt.date.today()
    done = set()
    if _hist_man().exists():
        for line in _hist_man().read_text().splitlines():
            r = json.loads(line)
            if r.get("status") == 200 and r.get("rows"):
                done.add(r["month"])
    s = requests.Session()
    s.headers.update(nse.HEADERS)
    hidden = {}
    months, m = [], dt.date(start.year, start.month, 1)
    while m <= end:
        months.append(m)
        m = dt.date(m.year + (m.month == 12), m.month % 12 + 1, 1)
    got = rows = 0
    cur = f"{end:%Y-%m}"
    for m in months:
        key = f"{m:%Y-%m}"
        if key in done and key != cur:
            continue
        last = min(dt.date(m.year + (m.month == 12), m.month % 12 + 1, 1) - dt.timedelta(days=1), end)
        try:
            if not hidden:
                r = s.get(NSDL_ARCHIVE, timeout=60)
                hidden = dict(re.findall(r'<input type="hidden" name="(__[A-Z]+)" id="__[A-Z]+" value="([^"]*)"', r.text))
                time.sleep(1.5)
            d = last.strftime("%d-%b-%Y")
            form = {**hidden, "__EVENTTARGET": "btnSubmit1", "__EVENTARGUMENT": "", "hdnDate": d, "hdnFlag": "", "txtDate": d}
            r = s.post(NSDL_ARCHIVE, data=form, timeout=90)
            st, body = r.status_code, r.content
            new_hidden = dict(re.findall(r'<input type="hidden" name="(__[A-Z]+)" id="__[A-Z]+" value="([^"]*)"', r.text))
            if new_hidden:
                hidden = new_hidden
        except requests.RequestException as e:
            st, body, hidden = 599, str(e).encode(), {}
        recs = parse_nsdl_archive(body.decode("utf-8", "ignore")) if st == 200 else []
        row = {"month": key, "asked": last.isoformat(), "status": st, "bytes": len(body), "rows": len(recs), "days": len({x["date"] for x in recs}),
               "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
        if recs:
            folder = paths.bronze("flows") / "nsdl_archive" / f"{m.year}"
            folder.mkdir(parents=True, exist_ok=True)
            p = folder / f"nsdl_archive_{m:%Y%m}.html"
            p.write_bytes(body)
            row.update(path=str(p.relative_to(paths.data_dir())), sha256=hashlib.sha256(body).hexdigest())
            got += 1
            rows += len(recs)
        with _hist_man().open("a") as fh:
            fh.write(json.dumps(row) + "\n")
        log(f"nsdl archive {key}: status {st}, {row['days']} reporting days")
        time.sleep(1.5)
    return {"months_saved": got, "rows": rows, "months_asked": len(months)}


def snapshot(log=print) -> dict:
    paths.ensure()
    s = requests.Session()
    s.headers.update(nse.HEADERS)
    out = {}
    for name, url, parse, ext in (("msei", MSEI, parse_msei, "json"), ("nsdl", NSDL, parse_nsdl, "html"), ("nse", NSE_API, parse_nse, "json")):
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
            folder = paths.bronze("flows") / ("nsdl_fpi" if name == "nsdl" else "fii_dii_cash") / d[:4]
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
        src = "NSE provisional (fiidiiTradeReact)" if p.name.startswith("nse_") else "MSEI provisional (all exchanges)"
        for x in json.loads(p.read_text()):
            recs.append({**x, "source": src})
    for p in sorted((paths.bronze("flows") / "nsdl_fpi").glob("*/*.html")):
        for x in parse_nsdl(p.read_text(errors="ignore")):
            recs.append({**x, "source": "NSDL confirmed (custodians)"})
    # 25 Oct 2026: NSDL's monthly archive pages, daily from 2000 by reporting date (confirmed custodian figures; usable the session after)
    for p in sorted((paths.bronze("flows") / "nsdl_archive").glob("*/*.html")):
        for x in parse_nsdl_archive(p.read_text(errors="ignore")):
            recs.append({**x, "source": "NSDL archive (custodians, by reporting date)"})
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
                got.setdefault(r["source"], set()).add(r["date"])
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
    # 25 Oct 2026: the NSDL archive history (FPI only, by reporting date), reporting days per year from the history manifest
    arch: dict[int, int] = {}
    if _hist_man().exists():
        best: dict[str, int] = {}
        for line in _hist_man().read_text().splitlines():
            r = json.loads(line)
            if r.get("status") == 200:
                best[r["month"]] = max(best.get(r["month"], 0), int(r.get("days") or 0))
        for mth, n in best.items():
            arch[int(mth[:4])] = arch.get(int(mth[:4]), 0) + n
    out["nsdl_archive"] = [{"year": y, "reporting_days": n} for y, n in sorted(arch.items())]
    out["history"] = ("FPI (FII) equity and debt: daily from 2000 via NSDL's archive (confirmed, by reporting date, usable the session after). "
                      "DII: no free history (NSE's archive page geo-blocked from Toronto): forward capture only, MSEI from 2026-10-23 and NSE's API from 2026-10-25")
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
    elif a[:1] == ["history"]:
        print(json.dumps(history(dt.date.fromisoformat(a[1]) if len(a) > 1 else ARCHIVE_START), indent=1))
    else:
        print(__doc__)
