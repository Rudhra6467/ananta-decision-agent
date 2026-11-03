"""The data-set audit (flag 63; Madhav, 3 Nov 2026 09:00-09:01 Toronto: "we have to first take our time in evaluating and finding the best
research data sets that should give us scope ... it is not that we are trying to find a profitable trade").

Before any new research: what each data set covers, how complete it is year by year, where it is thin, and what to widen first. It reads
the research years only (to 2023) and the manifests other jobs write (the data inventory, the integrity checks); the sealed years are
counted by the sealed tree's own manifest, never opened here. No rule changes from it.

  python -m india.dataaudit        writes manifests/data_audit.json and registrations/data_audit_v1.md
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from collections import Counter
from pathlib import Path

from india import paths

REG = Path(__file__).parent / "registrations"


def _j(p: Path, default=None):
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return default


def results_parse() -> dict:
    """Company results: filings in the table by period year, companies, and how many carry revenue and EPS (the parse state)."""
    import pandas as pd
    p = paths.data_dir() / "silver" / "fundamentals" / "results.parquet"
    try:
        r = pd.read_parquet(p, columns=["isin", "period_end", "revenue", "eps_basic"])
    except Exception as e:  # noqa: BLE001
        return {"status": f"unreadable: {type(e).__name__}"}
    r["y"] = pd.to_datetime(r["period_end"], errors="coerce").dt.year
    r = r[r["y"] <= 2023]
    by = {}
    for y, g in r.groupby("y"):
        by[int(y)] = {"filings": int(len(g)), "companies": int(g["isin"].nunique()), "with_revenue": int(g["revenue"].notna().sum()),
                      "with_eps": int(g["eps_basic"].notna().sum()),
                      "companies_with_eps": int(g.loc[g["eps_basic"].notna(), "isin"].nunique())}
    return {"by_year": by, "first_year": min(by) if by else None}


def universe() -> dict:
    """How wide the research universe is each year: stocks with a liquidity rank (126+ sessions of history) and the names that were ever in
    the day's 250 most traded."""
    import pandas as pd
    p = paths.data_dir() / "gold" / "universe" / "u_liq_in.parquet"
    try:
        u = pd.read_parquet(p, columns=["date", "symbol", "top250", "top500"])
    except Exception as e:  # noqa: BLE001
        return {"status": f"unreadable: {type(e).__name__}"}
    u["y"] = pd.to_datetime(u["date"]).dt.year
    out = {}
    for y, g in u.groupby("y"):
        out[int(y)] = {"ranked_stocks": int(g["symbol"].nunique()), "ever_top250": int(g.loc[g["top250"], "symbol"].nunique()),
                       "ever_top500": int(g.loc[g["top500"], "symbol"].nunique())}
    return out


def xbrl_by_year() -> dict:
    c: Counter = Counter()
    p = paths.manifest_dir() / "xbrl.jsonl"
    try:
        for line in p.open():
            try:
                x = json.loads(line)
            except ValueError:
                continue
            if x.get("status") == 200:
                parts = str(x.get("path") or "").split("/")
                if len(parts) > 2 and parts[2].isdigit():
                    c[int(parts[2])] += 1
    except OSError:
        return {}
    return {y: n for y, n in sorted(c.items()) if y <= 2023}


def build(write: bool = True) -> dict:
    inv = _j(paths.manifest_dir() / "data_inventory.json", {}) or {}
    integ = _j(paths.manifest_dir() / "integrity.json", {}) or {}
    cov = ((integ.get("coverage") or {}).get("metrics")) or {}
    res, uni, xb = results_parse(), universe(), xbrl_by_year()
    ann = (inv.get("announcements") or {}).get("per_year") or {}
    intr = (inv.get("intraday_stocks") or {}).get("by_year") or {}
    findings = []
    # the findings, each with its evidence
    by = res.get("by_year") or {}
    parsed_years = [y for y, v in by.items() if v["with_eps"] > 0.5 * max(v["filings"], 1)]
    findings.append({"area": "company results", "severity": "high",
                     "finding": (f"results with revenue and EPS are parsed for {', '.join(map(str, parsed_years)) or 'no year'} only; earlier years hold the "
                                 f"filing but not its numbers ({', '.join(f'{y}: {v['with_eps']} of {v['filings']}' for y, v in sorted(by.items()) if y < min(parsed_years or [2100]))}); "
                                 "the results index lists filings from 2007, but the parsed table starts in 2018, and the old HTML result pages before "
                                 "2018 are not parsed at all (D20b)"),
                     "so": "a per-stock P/E or results study can use 2022-2023 only today; that is too short for the registry's strict bar"})
    ys = sorted(ann)
    lows = {y: ann[y] for i, y in enumerate(ys) if 0 < i < len(ys) - 1 and ann[y] < 0.5 * (ann[ys[i - 1]] + ann[ys[i + 1]]) / 2}   # a hole between its neighbours
    if lows:
        findings.append({"area": "company announcements", "severity": "medium",
                         "finding": f"years with under half the count of the years either side: {', '.join(f'{y}: {n:,}' for y, n in sorted(lows.items()))} (2021: {ann.get('2021', 0):,}, 2023: {ann.get('2023', 0):,})",
                         "so": "any study of announcements must leave out or flag those years; refetch them first"})
    if intr:
        worst = min(intr.items(), key=lambda kv: kv[1].get("top250_covered") or 1)
        findings.append({"area": "intraday stock bars (5-minute)", "severity": "medium",
                         "finding": (f"coverage of the day's 250 most traded rises from {round(100 * (intr[min(intr)].get('top250_covered') or 0))}% in {min(intr)} "
                                     f"to {round(100 * (intr[max(intr)].get('top250_covered') or 0))}% in {max(intr)}; lowest {worst[0]}"),
                         "so": "intraday stock studies before about 2019 see only part of the liquid market; say so or start them in 2019"})
    if uni:
        y0, y1 = min(uni), max(uni)
        findings.append({"area": "the research universe", "severity": "medium",
                         "finding": (f"in {y1}, {uni[y1]['ranked_stocks']:,} stocks had a liquidity rank and {uni[y1]['ever_top250']} were in the day's 250 most "
                                     f"traded at some point; most studies use only those 250 of each day (chosen on that day, so delisted names are included)"),
                         "so": "a finding on the 250 most traded says nothing about the other 1,000+ stocks; widen to the top 500 for the ideas that pass"})
    findings.append({"area": "survivorship and adjustments", "severity": "low",
                     "finding": (f"{(integ.get('survivorship') or {}).get('note')}; {(integ.get('corporate_actions') or {}).get('note')}; "
                                 f"{(integ.get('stale_prices') or {}).get('note')}"),
                     "so": "delisted names are in; a few unexplained jumps remain, and the lab skips frozen prices"})
    findings.append({"area": "not on file", "severity": "medium",
                     "finding": ("NSE's board-meetings calendar (results dates ahead come only from filings that name them); analyst estimates (no "
                                 "'beat or miss'); GIFT Nifty and live Asian markets; bulk and block deals before 23 Oct 2026; competitor financials beyond the sector map"),
                     "so": "the board-meetings calendar is free and the cheapest to add; estimates are paid; GIFT Nifty has no free source"})
    widen = [
        "1. Parse the downloaded results (XBRL) for 2018-2021 so revenue and EPS cover six years, then the old HTML pages for 2010-2017 (D20b): "
        "the base for any results or P/E study.",
        "2. Refetch the announcement years that are under half the usual count, so studies of announcements do not have holes.",
        "3. Fetch NSE's board-meetings calendar each evening, so results days ahead are complete.",
        "4. Re-run the ideas that held up on the 250 most traded on the top 500, to see whether they carry to a wider market.",
        "5. Start intraday stock studies in 2019, when coverage of the liquid names is high, or report coverage beside each result.",
        "6. Check the liquid-stock falls of over 45% with no corporate action within 3 days: each is either a real crash or a missed split, "
        "bonus or demerger, and a missed one fakes a loss in every study that holds the stock.",
    ]
    out = {"built_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "rules": "dataaudit-v1-2026-11-03",
           "results": res, "xbrl_downloaded_by_year": xb, "universe_by_year": uni, "announcements_by_year": ann,
           "intraday_by_year": intr, "cash_rows_per_day": {y: v.get("rows_per_day") for y, v in (cov.get("cm_bhavcopy") or {}).items()},
           "datasets": inv.get("datasets"), "findings": findings, "widen_first": widen}
    if write:
        (paths.manifest_dir() / "data_audit.json").write_text(json.dumps(out, indent=1, default=str))
        (REG / "data_audit_v1.md").write_text(markdown(out))
    return out


def markdown(a: dict) -> str:
    L = ["# The data-set audit, first version (3 Nov 2026)", "",
         "Madhav asked for this before any new research (flag 63): how wide and how good each data set is. Research years only (to 2023); "
         "the sealed years are counted by their own manifest and not opened. Nothing trades from it.", "", "## What we have", "",
         "| data | rows | research years | live to |", "|---|---|---|---|"]
    for k, v in sorted((a.get("datasets") or {}).items()):
        if v.get("rows"):
            L.append(f"| {k} | {v['rows']:,} | {(v.get('first') or '')[:4]}-{(v.get('last') or '')[:4]} | {v.get('sealed_last') or '-'} |")
    L += ["", "## What the audit found", ""]
    for f in a["findings"]:
        L.append(f"- **{f['area']}** ({f['severity']}): {f['finding']}. So: {f['so']}.")
    L += ["", "## Company results, by period year (parsed = revenue and EPS read from the filing)", "", "| year | filings | companies | with EPS |", "|---|---|---|---|"]
    for y, v in sorted(((a.get("results") or {}).get("by_year") or {}).items()):
        L.append(f"| {y} | {v['filings']:,} | {v['companies']:,} | {v['with_eps']:,} |")
    L += ["", "## The research universe, by year", "", "| year | stocks ranked | ever in the top 250 | ever in the top 500 |", "|---|---|---|---|"]
    for y, v in sorted((a.get("universe_by_year") or {}).items()):
        if y >= 2010:
            L.append(f"| {y} | {v['ranked_stocks']:,} | {v['ever_top250']} | {v['ever_top500']} |")
    L += ["", "## What to widen first (in order)", ""] + a["widen_first"] + [""]
    return "\n".join(L)


if __name__ == "__main__":
    paths.ensure()
    r = build()
    print(json.dumps({"findings": [f["area"] + ": " + f["finding"][:140] for f in r["findings"]]}, indent=1))
    sys.exit(0)
