"""Norgate trial coverage probe (C0 deliverable; run ONLY inside the Windows VM during the free trial).

UNTESTED against a live NDU: written from Norgate's documented Python API (pypi.org/project/norgatedata).
It records what exists (databases, index names, fields, membership counts, date ranges) and computes NO
returns, signals or performance numbers. Output: one JSON coverage report for the purchase decision.

Usage (inside Windows, NDU running):  python norgate_probe.py  C:\\shared\\norgate_coverage.json
"""
from __future__ import annotations

import json
import sys
import time

DATABASES = ["Canadian Equities", "Canadian Equities Delisted", "Canadian Indices", "Canadian ETFs"]
INDEXES = ["S&P/TSX Composite", "S&P/TSX 60", "S&P/TSX Capped Energy", "S&P/TSX Capped Materials",
           "S&P/TSX Capped Financials", "S&P/TSX Capped Industrials", "S&P/TSX Capped Information Technology",
           "S&P/TSX Capped Communication Services", "S&P/TSX Capped Utilities", "S&P/TSX Capped Real Estate",
           "S&P/TSX Capped Consumer Discretionary", "S&P/TSX Capped Consumer Staples", "S&P/TSX Capped Health Care"]


def _try(fn, *a, **k):
    try:
        return fn(*a, **k), None
    except Exception as exc:  # noqa: BLE001  a probe records failures, it never stops on one
        return None, f"{type(exc).__name__}: {str(exc)[:160]}"


def probe(nd) -> dict:
    out: dict = {"t_utc": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()), "ndu_running": None,
                 "databases": {}, "indexes": {}, "fields": {}, "sample": {}, "errors": []}
    out["ndu_running"], e = _try(nd.status)
    if e:
        out["errors"].append(f"status: {e}")
    symbols: list[str] = []
    for db in DATABASES:
        syms, e = _try(nd.database_symbols, db)
        out["databases"][db] = {"count": len(syms) if syms else 0, "error": e}
        if syms and "Indices" not in db and "ETF" not in db:
            symbols += list(syms)
    if symbols:
        s0 = symbols[0]
        for adj in ("NONE", "CAPITAL", "CAPITALSPECIAL", "TOTALRETURN"):
            df, e = _try(nd.price_timeseries, s0, stock_price_adjustment_setting=getattr(nd.StockPriceAdjustmentType, adj),
                         padding_setting=nd.PaddingType.NONE, timeseriesformat="pandas-dataframe")
            out["fields"][adj] = {"columns": list(df.columns) if df is not None else None, "rows": len(df) if df is not None else 0,
                                  "first": str(df.index.min()) if df is not None and len(df) else None, "error": e}
        for f in ("first_quoted_date", "last_quoted_date", "assetid", "security_name"):
            v, e = _try(getattr(nd, f), s0)
            out["sample"][f] = str(v) if v is not None else e
        for scheme in ("GICS", "TRBC"):
            v, e = _try(nd.classification, s0, scheme, "Name")
            out["sample"][f"classification_{scheme}"] = str(v) if v is not None else e
    for name in INDEXES:  # membership counts only: how many securities were ever in it, and on which dates
        members, first, last, err = 0, None, None, None
        for s in symbols:
            df, e = _try(nd.index_constituent_timeseries, s, name, padding_setting=nd.PaddingType.NONE,
                         timeseriesformat="pandas-dataframe")
            if e:
                err = e
                break
            if df is not None and len(df) and df.iloc[:, -1].sum() > 0:
                d = df[df.iloc[:, -1] > 0].index
                members += 1
                first = min(first, str(d.min())) if first else str(d.min())
                last = max(last, str(d.max())) if last else str(d.max())
        out["indexes"][name] = {"securities_ever_member": members, "first_member_day": first,
                                "last_member_day": last, "error": err}
    return out


if __name__ == "__main__":
    import norgatedata  # noqa: E402  only exists inside the Windows VM

    report = probe(norgatedata)
    path = sys.argv[1] if len(sys.argv) > 1 else "norgate_coverage.json"
    with open(path, "w") as fh:
        json.dump(report, fh, indent=1)
    print(f"wrote {path}: {sum(1 for v in report['indexes'].values() if v['securities_ever_member'])} of {len(INDEXES)} indexes found")
