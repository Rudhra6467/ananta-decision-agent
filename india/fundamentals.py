"""Point-in-time fundamentals from the XBRL result filings (D20). Raw statements stay on this Mac; only ratios we derive are ever shown elsewhere.

  python -m india.fundamentals build      parse every downloaded XBRL file -> silver/fundamentals/facts.parquet (long) and results.parquet (one row per filing)
  python -m india.fundamentals coverage   filings, parsed share, companies, quarters, by year (the D20 coverage report)

Point in time: each filing row carries available_at = the exchange broadcast time from the results index (or the integrated-filing index from 2025).
A study may use a filing only on sessions after available_at (filed after 15:30 IST -> usable from the next session). Rows dated 2024 or later go to sealed/silver.
Facts kept: every non-dimensional numeric fact in the in-bse-fin namespace (so any ratio can be derived later), for the filing's own reporting period.
Key items in results.parquet: revenue, total income, expenses, profit before tax, profit, basic and diluted EPS, finance costs, depreciation, employee cost,
paid-up capital and face value (shares = paid-up / face value), standalone or consolidated, audited or not, quarter or year.
"""
from __future__ import annotations

import datetime as dt
import glob
import json
import re
import sys
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from india import paths

NS = "in-bse-fin:"
KEY = {"RevenueFromOperations": "revenue", "Income": "total_income", "Expenses": "expenses", "ProfitBeforeTax": "pbt", "ProfitLossForPeriod": "profit",
       "BasicEarningsLossPerShareFromContinuingAndDiscontinuedOperations": "eps_basic", "DilutedEarningsLossPerShareFromContinuingAndDiscontinuedOperations": "eps_diluted",
       "FinanceCosts": "finance_costs", "DepreciationDepletionAndAmortisationExpense": "depreciation", "EmployeeBenefitExpense": "employee_cost",
       "PaidUpValueOfEquityShareCapital": "paid_up_capital", "FaceValueOfEquityShareCapital": "face_value", "OtherIncome": "other_income",
       # banking taxonomy
       "InterestEarned": "interest_earned", "TotalIncome": "total_income_bank", "OperatingProfitBeforeProvisionAndContingencies": "operating_profit_bank",
       "ProvisionsOtherThanTaxAndContingencies": "provisions_bank", "GrossNonPerformingAssets": "gross_npa", "PercentageOfGrossNpa": "gross_npa_pct"}
TEXT = {"NatureOfReportStandaloneConsolidated": "nature", "WhetherResultsAreAuditedOrUnaudited": "audited", "Symbol": "symbol_x", "ReportingQuarter": "reporting_quarter",
        "DateOfStartOfReportingPeriod": "period_start", "DateOfEndOfReportingPeriod": "period_end", "LevelOfRoundingUsedInFinancialStatements": "rounding"}
_CTX = re.compile(r'<xbrli:context id="([^"]+)">(.*?)</xbrli:context>', re.S)
_FACT = re.compile(r'<in-bse-fin:([A-Za-z0-9]+)\s+([^>]*?)(?:/>|>(.*?)</in-bse-fin:\1>)', re.S)
_ATTR = re.compile(r'(\w+)="([^"]*)"')


def parse(path: str) -> tuple[dict, list[dict]]:
    txt = Path(path).read_text(errors="ignore")
    ctx = {}
    for cid, body in _CTX.findall(txt):
        dim = "<xbrli:scenario>" in body or "<xbrli:segment>" in body
        s = re.search(r"<xbrli:startDate>([^<]+)", body)
        e = re.search(r"<xbrli:endDate>([^<]+)", body)
        i = re.search(r"<xbrli:instant>([^<]+)", body)
        ctx[cid] = {"dim": dim, "start": s.group(1) if s else None, "end": e.group(1) if e else (i.group(1) if i else None), "instant": bool(i)}
    head, facts = {}, []
    for tag, attrs, val in _FACT.findall(txt):
        a = dict(_ATTR.findall(attrs))
        c = ctx.get(a.get("contextRef", ""), {})
        if tag in TEXT and val is not None and not c.get("dim"):
            head.setdefault(TEXT[tag], val.strip())
        if "unitRef" not in a or c.get("dim", True):
            continue
        try:
            v = float(val)
        except (TypeError, ValueError):
            continue
        facts.append({"tag": tag, "value": v, "start": c.get("start"), "end": c.get("end"), "instant": c.get("instant"), "unit": a.get("unitRef"), "decimals": a.get("decimals")})
    return head, facts


def _index_rows() -> pd.DataFrame:
    rows = []
    for fp in glob.glob(str(paths.bronze("results_index") / "*" / "*.json")):
        for x in json.loads(Path(fp).read_text()):
            rows.append({"url": x.get("xbrl"), "isin": x.get("isin"), "symbol": x.get("symbol"), "broadcast": x.get("broadCastDate"), "period": x.get("period"),
                         "consolidated": x.get("consolidated"), "audited_flag": x.get("audited"), "source_index": "results"})
    for fp in glob.glob(str(paths.bronze("results_index_integrated") / "*" / "*.json")):
        for x in json.loads(Path(fp).read_text()):
            rows.append({"url": x.get("xbrl"), "isin": None, "symbol": x.get("symbol"), "broadcast": x.get("broadcast_Date"), "period": x.get("qe_Date"),
                         "consolidated": x.get("consolidated"), "audited_flag": x.get("audited"), "source_index": "integrated"})
    df = pd.DataFrame(rows)
    df = df[df["url"].notna() & ~df["url"].fillna("").str.endswith("/-")].drop_duplicates("url")
    df["available_at"] = pd.to_datetime(df["broadcast"], format="%d-%b-%Y %H:%M:%S", errors="coerce")
    return df


def build() -> dict:
    man = paths.manifest_dir() / "xbrl.jsonl"
    got = {}
    if man.exists():
        for line in man.read_text().splitlines():
            r = json.loads(line)
            if r.get("status") == 200 and r.get("path"):
                got[r["url"]] = r["path"]
    idx = _index_rows()
    idx = idx[idx["url"].isin(got)]
    names = pd.read_parquet(paths.data_dir() / "silver/security_master/names.parquet")
    sym_isin = names.dropna(subset=["isin"]).drop_duplicates("symbol", keep="last").set_index("symbol")["isin"] if "symbol" in names else pd.Series(dtype=str)
    res, facts, bad = [], [], 0
    for r in idx.itertuples():
        try:
            head, fx = parse(str(paths.data_dir() / got[r.url]))
        except Exception:
            bad += 1
            continue
        pe = head.get("period_end")
        # the filing's own period only: a quarter's file also carries year-to-date figures ending on the same date (different start), which are left out
        own = [f for f in fx if f["end"] == pe and (f["instant"] or f["start"] == head.get("period_start"))]
        row = {"url": r.url, "isin": r.isin or sym_isin.get(r.symbol), "symbol": r.symbol, "available_at": r.available_at, "index_period": r.period, "source_index": r.source_index,
               "consolidated": r.consolidated, **head, "n_facts": len(own)}
        for f in own:
            k = KEY.get(f["tag"])
            if k and not f["instant"] and k not in row:
                row[k] = f["value"]
            elif k and f["instant"] and k not in row:
                row[k] = f["value"]
        try:
            d0, d1 = pd.Timestamp(head.get("period_start")), pd.Timestamp(pe)
            row["months"] = round((d1 - d0).days / 30.4)
        except Exception:
            row["months"] = None
        res.append(row)
        for f in own:
            facts.append({"url": r.url, "isin": row["isin"], "available_at": r.available_at, "period_end": pe, **f})
    rdf = pd.DataFrame(res)
    fdf = pd.DataFrame(facts)
    if rdf.empty:
        return {"filings": 0}
    rdf["shares_est"] = rdf["paid_up_capital"] / rdf["face_value"] if {"paid_up_capital", "face_value"} <= set(rdf.columns) else None
    hold = pd.Timestamp(paths.HOLDOUT_START)
    out = {}
    for part, mask_r, mask_f in (("silver", rdf["available_at"] < hold, fdf["available_at"] < hold), ("sealed/silver", rdf["available_at"] >= hold, fdf["available_at"] >= hold)):
        d = paths.data_dir() / part / "fundamentals"
        d.mkdir(parents=True, exist_ok=True)
        pq.write_table(pa.Table.from_pandas(rdf[mask_r].reset_index(drop=True), preserve_index=False), d / "results.parquet")
        pq.write_table(pa.Table.from_pandas(fdf[mask_f].reset_index(drop=True), preserve_index=False), d / "facts.parquet")
        out[part] = {"filings": int(mask_r.sum()), "facts": int(mask_f.sum())}
    out.update({"parse_errors": bad, "with_revenue": int(rdf["revenue"].notna().sum()) if "revenue" in rdf else 0, "with_eps": int(rdf["eps_basic"].notna().sum()) if "eps_basic" in rdf else 0,
                "companies": int(rdf["isin"].nunique()), "no_available_at": int(rdf["available_at"].isna().sum())})
    return out


def coverage() -> pd.DataFrame:
    idx = _index_rows()
    idx["year"] = idx["available_at"].dt.year
    man = paths.manifest_dir() / "xbrl.jsonl"
    st = {}
    if man.exists():
        for line in man.read_text().splitlines():
            r = json.loads(line)
            st[r["url"]] = r.get("status")
    idx["fetched"] = idx["url"].map(lambda u: st.get(u) == 200)
    rep = idx.groupby("year").agg(filings_with_xbrl=("url", "size"), downloaded=("fetched", "sum"), companies=("symbol", "nunique")).reset_index()
    print(rep.to_string(index=False))
    return rep


if __name__ == "__main__":
    paths.ensure()
    w = sys.argv[1] if len(sys.argv) > 1 else "build"
    if w == "build":
        print(json.dumps(build(), default=str, indent=1))
    else:
        coverage()
