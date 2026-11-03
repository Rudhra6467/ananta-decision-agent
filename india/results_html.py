"""D20b (data audit step 1, second half; Madhav, 3 Nov 2026: "yes to all your recommendations and next steps"): company results 2010-2017 from
NSE's old HTML result pages (the results index links one page per filing; XBRL starts in 2018).

  python -m india.results_html fetch [from_year] [to_year]   one page per filing (default 2010-2017), resumable; raw HTML to
                                                            bronze/results_html/<year>/<seq>.html.gz; manifest manifests/results_html.jsonl
  python -m india.results_html build                        silver/fundamentals/results_html.parquet (one row per filing, rupees)

Point in time: available_at = the exchange broadcast time from the results index, as for the XBRL rows. Amounts on the pages are in Rs lakhs
(or as the page states); they are converted to rupees so the rows line up with the XBRL table. Personal-use data: raw pages stay on this Mac.
"""
from __future__ import annotations

import datetime as dt
import glob
import gzip
import json
import re
import sys
from pathlib import Path

import pandas as pd

from india import nse, paths

# label on the page (lower case, spaces squeezed) -> key, first match wins per key
LABELS = [
    (r"^net sales ?/ ?income from operations?", "revenue"), (r"^revenue from operations", "revenue"), (r"^net income from operations", "revenue"),
    (r"^income from operations", "revenue"), (r"^total income from operations", "revenue_total"),
    (r"^other operating income", "other_operating_income"), (r"^other income", "other_income"),
    (r"^total expenditure", "expenses"), (r"^total expenses", "expenses"),
    (r"^employees? (?:benefit )?(?:cost|expense)", "employee_cost"), (r"^depreciation", "depreciation"),
    (r"^interest\b", "finance_costs"), (r"^finance costs?", "finance_costs"),
    (r"^profit ?\(\+\) ?/ ?loss ?\(-\) from ordinary activities before tax", "pbt"), (r"^profit (?:\(\+\) ?/ ?loss ?\(-\) )?before tax", "pbt"),
    (r"^tax expense", "tax"),
    (r"^net profit ?\(\+\) ?/ ?loss ?\(-\) for the period", "profit"), (r"^net profit ?/ ?\(?loss\)? for the period", "profit"),
    (r"^face value", "face_value"), (r"^paid-?up equity share capital", "paid_up_capital"),
    (r"^basic eps after extraordinary items", "eps_basic"), (r"^basic eps before extraordinary items", "eps_basic_before_xo"),
    (r"^diluted eps after extraordinary items", "eps_diluted"),
    # banks
    (r"^interest earned", "interest_earned"), (r"^total income", "total_income_bank"), (r"^gross npa", "gross_npa"),
    (r"^% of gross npa", "gross_npa_pct"), (r"^operating profit before provisions", "operating_profit_bank"),
]
PER_SHARE = {"face_value", "eps_basic", "eps_basic_before_xo", "eps_diluted", "gross_npa_pct"}
UNITS = [(r"lakh|lac", 1e5), (r"crore", 1e7), (r"million", 1e6), (r"thousand", 1e3)]


def _rows() -> pd.DataFrame:
    rows = []
    for fp in glob.glob(str(paths.bronze("results_index") / "*" / "*.json")):
        for x in json.loads(Path(fp).read_text()):
            link = x.get("resultDetailedDataLink")
            if not link or not str(link).endswith(".html"):
                continue
            rows.append({"url": link, "seq": str(x.get("seqNumber")), "isin": x.get("isin"), "symbol": x.get("symbol"), "broadcast": x.get("broadCastDate"),
                         "filed": x.get("filingDate"), "period": x.get("period"), "relating_to": x.get("relatingTo"), "from": x.get("fromDate"), "to": x.get("toDate"),
                         "consolidated": x.get("consolidated"), "audited": x.get("audited"), "cumulative": x.get("cumulative"), "bank": x.get("bank")})
    df = pd.DataFrame(rows).drop_duplicates("url")
    df["available_at"] = pd.to_datetime(df["broadcast"], format="%d-%b-%Y %H:%M:%S", errors="coerce")
    df["available_at"] = df["available_at"].fillna(pd.to_datetime(df["filed"], format="%d-%b-%Y %H:%M", errors="coerce"))
    df["year"] = df["available_at"].dt.year
    return df


def _man() -> Path:
    return paths.manifest_dir() / "results_html.jsonl"


def fetch(from_year: int = 2010, to_year: int = 2017, limit: int | None = None) -> dict:
    paths.ensure()
    done = set()
    if _man().exists():
        for line in _man().read_text().splitlines():
            r = json.loads(line)
            if r.get("status") in (200, 404):
                done.add(r["url"])
    df = _rows()
    df = df[(df["year"] >= from_year) & (df["year"] <= to_year) & ~df["url"].isin(done)].sort_values("available_at")
    if limit:
        df = df.head(limit)
    f = nse.Fetcher(rate_s=1.0)
    n = 0
    with _man().open("a") as fh:
        for r in df.itertuples():
            st, body, secs = f.get(r.url)
            row = {"url": r.url, "seq": r.seq, "status": st, "bytes": len(body), "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
            if st == 200 and b"Financial Results" in body:
                out = paths.bronze("results_html") / str(int(r.year)) / f"{r.seq}.html.gz"
                out.parent.mkdir(parents=True, exist_ok=True)
                with gzip.open(out, "wb") as g:
                    g.write(body)
                row["path"] = str(out.relative_to(paths.data_dir()))
            elif st == 200:
                row["status"] = 520            # not a results page (an error page): retried next time
            fh.write(json.dumps(row) + "\n")
            fh.flush()
            n += 1
            if n % 500 == 0:
                print(f"results_html {r.year} pages={n} left={len(df) - n}", flush=True)
    return {"pages": n}


def _num(s: str) -> float | None:
    s = s.replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def parse(html: str) -> dict:
    """{key: value} from one result page; amounts in rupees, per-share items as printed; 'unit' is the multiplier read from the page."""
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", html, flags=re.S | re.I)
    cells = [re.sub(r"\s+", " ", re.sub(r"&nbsp;|&amp;", " ", c)).strip() for c in re.split(r"<[^>]+>", t)]
    cells = [c for c in cells if c]
    unit = 1e5
    for c in cells:
        if c.lower().startswith("amount"):
            for pat, mult in UNITS:
                if re.search(pat, c.lower()):
                    unit = mult
                    break
            break
    out: dict = {"unit": unit}
    for i, c in enumerate(cells[:-1]):
        lab = c.lower()
        if lab in ("period", "relating to", "period ended", "financial year", "audited / un-audited", "consolidated / non-consolidated") and "head_" + lab not in out:
            out["head_" + lab] = cells[i + 1]
            continue
        for pat, key in LABELS:
            if key not in out and re.search(pat, lab):
                v = _num(cells[i + 1])
                if v is not None:
                    out[key] = v if key in PER_SHARE else v * unit
                break
    return out


def build() -> dict:
    import pyarrow as pa
    import pyarrow.parquet as pq
    got = {}
    if _man().exists():
        for line in _man().read_text().splitlines():
            r = json.loads(line)
            if r.get("status") == 200 and r.get("path"):
                got[r["url"]] = r["path"]
    idx = _rows()
    idx = idx[idx["url"].isin(got)]
    res, bad = [], 0
    for r in idx.to_dict("records"):
        try:
            p = parse(gzip.open(paths.data_dir() / got[r["url"]]).read().decode("utf-8", "ignore"))
        except Exception:  # noqa: BLE001
            bad += 1
            continue
        pe = pd.to_datetime(r["to"], format="%d-%b-%Y", errors="coerce")
        frm = pd.to_datetime(r["from"], format="%d-%b-%Y", errors="coerce")
        row = {"url": r["url"], "isin": r["isin"], "symbol": r["symbol"], "available_at": r["available_at"], "index_period": r["period"], "source_index": "results_html",
               "consolidated": r["consolidated"], "nature": r["consolidated"], "audited": r["audited"], "period_end": pe.date().isoformat() if pd.notna(pe) else None,
               "relating_to": r["relating_to"], "cumulative": r["cumulative"], **{k: v for k, v in p.items() if not k.startswith("head_")}}
        row["period_start"] = frm.date().isoformat() if pd.notna(frm) else None
        row["months"] = round((pe - frm).days / 30.4) if pd.notna(pe) and pd.notna(frm) else None
        res.append(row)
    df = pd.DataFrame(res)
    if df.empty:
        return {"filings": 0}
    if {"paid_up_capital", "face_value"} <= set(df.columns):
        df["shares_est"] = df["paid_up_capital"] / df["face_value"]
    hold = pd.Timestamp(paths.HOLDOUT_START)
    df = df[df["available_at"] < hold]                    # research years only; the HTML pages end in 2018 anyway
    out = paths.data_dir() / "silver" / "fundamentals" / "results_html.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pandas(df.reset_index(drop=True), preserve_index=False), out)
    y = pd.to_datetime(df["period_end"], errors="coerce").dt.year
    return {"filings": int(len(df)), "parse_errors": bad, "with_revenue": int(df.get("revenue", pd.Series(dtype=float)).notna().sum()),
            "with_eps": int(df.get("eps_basic", pd.Series(dtype=float)).notna().sum()), "by_year": {int(k): int(v) for k, v in y.value_counts().sort_index().items()}}


if __name__ == "__main__":
    paths.ensure()
    w = sys.argv[1] if len(sys.argv) > 1 else "build"
    if w == "fetch":
        a = int(sys.argv[2]) if len(sys.argv) > 2 else 2010
        b = int(sys.argv[3]) if len(sys.argv) > 3 else 2017
        print(fetch(a, b, int(sys.argv[4]) if len(sys.argv) > 4 else None))
    else:
        print(json.dumps(build(), default=str))
