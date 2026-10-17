"""Corporate actions, two records, and the adjustment factors that come out of them.

Record B: NSE's corporate-actions API, one call per calendar year for every symbol (structured: symbol, series, ex-date,
record date, face value, subject text such as "Bonus 1:1" or "Face Value Split (Sub-Division) - From Rs 10/- Per Share To
Rs 2/- Per Share"). Reachable from 2000 on; thin before 2005. Saved as bronze/corporate_actions/ca_<year>.json.
Record A: the price itself. NSE does not adjust the previous-close column on an ex-date (checked on INFY 2015-06-15 and
RELIANCE 2017-09-07), so the gap prior close / ex-date open is the evidence; a gap over 20% is a candidate, snapped to the
nearest clean ratio (2, 3, 5, 10, 3:2, 5:4, 1:10 consolidation...) when within 4%.
The factors view joins both: AGREE (both say the same ratio), B_ONLY (an announced action with no visible gap, e.g. a
tiny bonus), A_ONLY (a gap with no announcement, to be looked at), and never a silent choice.

  python -m india.actions fetch 2000 2026
  python -m india.actions build
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys
from fractions import Fraction

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from india import nse, paths

API = "https://www.nseindia.com/api/corporates-corporateActions?index=equities&from_date=01-01-{y}&to_date=31-12-{y}"
CLEAN = sorted({float(Fraction(a + b, b)) for a in range(1, 11) for b in range(1, 11)} | {2, 2.5, 3, 4, 5, 10, 20, 25, 50, 100} |
               {1 / x for x in (2, 2.5, 3, 4, 5, 10, 20)})


def fetch(years: range | list[int]) -> list[dict]:
    f = nse.Fetcher(rate_s=1.5)
    f.s.headers.update({"Accept": "*/*"})
    out = []
    for y in years:
        st, body, secs = f.get(API.format(y=y))
        row = {"year": y, "status": st, "bytes": len(body), "seconds": secs, "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
        if st == 200 and body[:1] == b"[":
            p = paths.bronze("corporate_actions") / f"ca_{y}.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(body)
            row["rows"] = len(json.loads(body))
        with (paths.manifest_dir() / "corporate_actions.jsonl").open("a") as fh:
            fh.write(json.dumps(row) + "\n")
        print(row, flush=True)
        out.append(row)
    return out


_NUM = r"(\d+(?:\.\d+)?)"


def parse_subject(s: str) -> dict:
    """kind, ratio (price factor: old price / new price), amount (dividend per share) from NSE's subject text."""
    t = " ".join(s.lower().split())
    out: dict = {"kind": "OTHER", "ratio": None, "amount": None}
    m = re.search(r"bonus\s*(\d+)\s*:\s*(\d+)", t)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        out.update(kind="BONUS", ratio=(a + b) / b if b else None)
    m = re.search(r"(?:spli?t|sub-?division).*?(?:from|frm)\s*(?:rs\.?|re\.?)?\s*" + _NUM + r".*?to\s*(?:rs\.?|re\.?)?\s*" + _NUM, t)
    if m:
        a, b = float(m.group(1)), float(m.group(2))
        if out["kind"] == "BONUS" and out["ratio"] and b:
            out.update(kind="BONUS+SPLIT", ratio=out["ratio"] * a / b)   # both on one ex-date: the gap is the product
        elif out["kind"] == "OTHER":
            out.update(kind="SPLIT", ratio=a / b if b else None)
    m = re.search(r"consolidat.*?(?:from|frm)\s*(?:rs\.?|re\.?)?\s*" + _NUM + r".*?to\s*(?:rs\.?|re\.?)?\s*" + _NUM, t)
    if m and out["kind"] == "OTHER":
        a, b = float(m.group(1)), float(m.group(2))
        out.update(kind="CONSOLIDATION", ratio=a / b if b else None)
    if out["kind"] == "OTHER" and re.search(r"\bright", t):
        m = re.search(r"right[s]?\s*(?:issue)?\s*(\d+)\s*:\s*(\d+)", t)
        out.update(kind="RIGHTS", ratio=None, note=f"{m.group(1)}:{m.group(2)}" if m else None)
    td = re.sub(r"sub-?division", "", t)   # "sub-division" is a split, not a dividend
    m = re.search(r"\bdiv[^0-9]{0,40}?(?:rs\.?|re\.?|₹)\s*" + _NUM, td)
    if m:
        out["amount"] = float(m.group(1))
        if out["kind"] == "OTHER":
            out["kind"] = "DIVIDEND"
    elif out["kind"] == "OTHER" and re.search(r"\bdiv", td):
        out["kind"] = "DIVIDEND"
    if out["kind"] == "OTHER" and ("buyback" in t or "buy back" in t):
        out["kind"] = "BUYBACK"
    if out["kind"] == "OTHER" and ("demerger" in t or "scheme of arrangement" in t or "amalgamation" in t):
        out["kind"] = "DEMERGER"
    return out


def build_b() -> dict:
    rows = []
    for p in sorted(paths.bronze("corporate_actions").glob("ca_*.json")):
        for r in json.loads(p.read_text()):
            ex = r.get("exDate", "")
            try:
                exd = dt.datetime.strptime(ex, "%d-%b-%Y").date()
            except ValueError:
                continue
            k = parse_subject(r.get("subject", ""))
            rows.append({"symbol": r.get("symbol", "").strip(), "series": r.get("series", "").strip(), "ex_date": exd, "record_date": r.get("recDate", ""),
                         "face_value": r.get("faceVal", ""), "isin": r.get("isin", ""), "subject": r.get("subject", "").strip(), **k, "source": p.name})
    df = pd.DataFrame(rows).drop_duplicates(subset=["symbol", "series", "ex_date", "subject"])
    out = paths.data_dir() / "silver" / "corporate_actions" / "record_b.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pandas(df, preserve_index=False), out)
    return {"rows": len(df), "kinds": df["kind"].value_counts().to_dict(), "path": str(out)}


def snap(x: float) -> float | None:
    best = min(CLEAN, key=lambda c: abs(c / x - 1))
    return best if abs(best / x - 1) <= 0.04 else None


def build_a(min_gap: float = 0.08) -> dict:
    """Candidates from the price itself on silver/ (dev and validation years): the ex-date gap (prior close / ex-date open) must
    snap to a clean ratio, and so must the persistent gap (median of the five closes before / median of the five closes from the
    ex-date on), to the same value. A one-day spike in an illiquid name fails the second test; a real split or bonus passes both."""
    import duckdb

    con = duckdb.connect()
    glob = str(paths.data_dir() / "silver" / "cm_bhavcopy" / "year=*" / "part.parquet")
    df = con.execute(f"""
        with eq as (select date, symbol, open, close, volume from read_parquet('{glob}') where series = 'EQ' and open > 0 and close > 0),
        w as (select *, lag(close) over (partition by symbol order by date) as prior_close,
                        lag(date) over (partition by symbol order by date) as prior_date,
                        median(close) over (partition by symbol order by date rows between 5 preceding and 1 preceding) as med_before,
                        median(close) over (partition by symbol order by date rows between current row and 4 following) as med_after
              from eq)
        select symbol, date as ex_date, prior_date, prior_close, open as ex_open, prior_close / open as gap, med_before / med_after as gap5, volume
        from w where prior_close is not null and abs(prior_close / open - 1) > {min_gap} and prior_date >= date - interval 10 day
        order by symbol, ex_date""").df()
    df["ratio"] = df["gap"].map(snap)
    df["ratio5"] = df["gap5"].map(lambda x: snap(x) if x and x > 0 else None)
    out = paths.data_dir() / "silver" / "corporate_actions" / "record_a.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pandas(df, preserve_index=False), out)
    return {"candidates": len(df), "snapped": int(df["ratio"].notna().sum()), "path": str(out)}


def build_factors() -> dict:
    """One row per (symbol, ex_date). Record B gives the ratio when it exists and Record A confirms it (the one-day gap or the
    five-day gap within 6% of it). Without B, a gap counts only when both gaps snap to the same clean ratio of at least 1.3 or
    at most 0.77, so a penny stock's ordinary 10% day never becomes a split."""
    import duckdb

    con = duckdb.connect()
    sd = paths.data_dir() / "silver" / "corporate_actions"
    df = con.execute(f"""
        with b as (select symbol, ex_date, kind, ratio as ratio_b, subject from read_parquet('{sd / "record_b.parquet"}')
                   where kind in ('BONUS','SPLIT','CONSOLIDATION','BONUS+SPLIT') and ratio is not null),
             a as (select symbol, ex_date, gap, gap5, ratio as ratio_a, ratio5 from read_parquet('{sd / "record_a.parquet"}'))
        select coalesce(a.symbol, b.symbol) symbol, coalesce(a.ex_date, b.ex_date) ex_date, b.kind, b.subject, a.gap, a.gap5, a.ratio_a, b.ratio_b,
               case when b.ratio_b is not null and a.gap is not null and (abs(a.gap / b.ratio_b - 1) < 0.06 or abs(a.gap5 / b.ratio_b - 1) < 0.06) then 'AGREE'
                    when b.ratio_b is not null and a.gap is null then 'B_ONLY'
                    when b.ratio_b is not null then 'DISAGREE'
                    when a.ratio_a is not null and a.ratio_a = a.ratio5 and (a.ratio_a >= 1.3 or a.ratio_a <= 0.77) then 'A_ONLY'
                    else 'NOISE' end as status,
               coalesce(b.ratio_b, a.ratio_a) as factor
        from a full outer join b on a.symbol = b.symbol and abs(datediff('day', a.ex_date, b.ex_date)) <= 1
        order by 1, 2""").df()
    df = df[df["status"] != "NOISE"].copy()
    out = sd / "factors.parquet"
    pq.write_table(pa.Table.from_pandas(df, preserve_index=False), out)
    return {"rows": len(df), "status": df["status"].value_counts().to_dict(), "path": str(out)}


if __name__ == "__main__":
    paths.ensure()
    what = sys.argv[1]
    if what == "fetch":
        fetch(range(int(sys.argv[2]), int(sys.argv[3]) + 1))
    elif what == "build":
        print(build_b(), flush=True)
        print(build_a(), flush=True)
        print(build_factors(), flush=True)
