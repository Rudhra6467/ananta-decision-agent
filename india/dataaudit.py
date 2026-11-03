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


def announcements_api() -> dict:
    """The timestamped NSE announcements (silver/announce, the source for new studies) by year, to 2023, with how many carry NSE's
    dissemination time (from mid-2020) besides the announcement time."""
    import pandas as pd
    p = paths.data_dir() / "silver" / "announce" / "announcements.parquet"
    try:
        a = pd.read_parquet(p, columns=["file_date", "exchdisstime"])
    except Exception as e:  # noqa: BLE001
        return {"status": f"unreadable: {type(e).__name__}"}
    a = a[a["file_date"].dt.year <= 2023]
    return {int(y): {"rows": int(len(g)), "with_dissemination_time": int(g["exchdisstime"].notna().sum())} for y, g in a.groupby(a["file_date"].dt.year)}


def board_meetings() -> dict:
    """NSE board meetings on file by meeting year, to 2023 ({} when the calendar has not been fetched)."""
    import pandas as pd
    p = paths.data_dir() / "silver" / "board_meetings" / "meetings.parquet"
    try:
        m = pd.read_parquet(p, columns=["meeting_date"])
    except Exception:  # noqa: BLE001
        return {}
    y = m["meeting_date"].dt.year
    return {int(k): int(v) for k, v in y[y <= 2023].value_counts().sort_index().items()}


def _holes(per_year: dict) -> dict:
    ys = sorted(per_year)
    return {y: per_year[y] for i, y in enumerate(ys) if 0 < i < len(ys) - 1 and per_year[y] < 0.5 * (per_year[ys[i - 1]] + per_year[ys[i + 1]]) / 2}


# 3 Nov 2026 (audit step 4): the stock universe each study with a VALIDATED variant used, read from its code (most use the 500, not the 250)
STUDY_UNIVERSES = {"OC1": "the 100 most traded (india/ocstudy.py)", "IB1": "Nifty, Bank Nifty and the 50 most traded (india/lab4.py)",
                   "GP1": "the 250 most traded (india/gaplab.py)", "V01": "the 500 most traded (india/vstudies.py)",
                   "E04, P01, CL1": "the lab features table, the 500 most traded (india/lab.py)",
                   "T-TWT H10/H12/H18": "the teachers' stock panel, the 500 most traded (india/teachers_stock.py)", "DR1": "index options only"}

# studies that read the old PR-zip announcement files (frozen specs; their source is not switched here)
PR_READERS = {"V02": "india/vstudies.py v02 (announcement reactions)", "HFN1": "the FinBERT reading of announcements (HFN1 spec)"}


def build(write: bool = True) -> dict:
    inv = _j(paths.manifest_dir() / "data_inventory.json", {}) or {}
    integ = _j(paths.manifest_dir() / "integrity.json", {}) or {}
    cov = ((integ.get("coverage") or {}).get("metrics")) or {}
    res, uni, xb = results_parse(), universe(), xbrl_by_year()
    ann = (inv.get("announcements") or {}).get("per_year") or {}          # the PR-zip files (no time of day)
    api = announcements_api()
    intr = (inv.get("intraday_stocks") or {}).get("by_year") or {}
    findings = []
    # the findings, each with its evidence
    by = res.get("by_year") or {}
    # a year counts when it has a real number of filings (2017 holds 12 late filers) and most carry EPS
    parsed_years = sorted(y for y, v in by.items() if v["filings"] >= 500 and v["with_eps"] > 0.5 * v["filings"])
    findings.append({"area": "company results", "severity": "high",
                     "finding": (f"results with revenue and EPS are parsed for {', '.join(map(str, parsed_years)) or 'no year'}"
                                 + (f"; earlier years hold the filing but not its numbers ({', '.join(f'{y}: {v['with_eps']} of {v['filings']}' for y, v in sorted(by.items()) if y < min(parsed_years))})"
                                    if parsed_years and any(y < min(parsed_years) and v['filings'] > 50 for y, v in by.items()) else "")
                                 + "; the results index lists filings from 2007, but before 2018 they are HTML pages with no XBRL, which are not parsed (D20b)"),
                     "so": (f"a per-stock P/E or results study can use {min(parsed_years)}-{max(parsed_years)} today" if parsed_years else "no results study is possible yet")
                           + ("; that is too short for the registry's strict bar" if len(parsed_years) < 5 else "; the 2010-2017 years still need the HTML pages")})
    api_rows = {str(y): v["rows"] for y, v in api.items()} if isinstance(api, dict) and "status" not in api else {}
    api_lows, pr_lows = _holes(api_rows), _holes({str(k): v for k, v in ann.items()})
    if api_lows:
        findings.append({"area": "company announcements", "severity": "medium",
                         "finding": f"timestamped announcements: years with under half the count of the years either side: {', '.join(f'{y}: {n:,}' for y, n in sorted(api_lows.items()))}",
                         "so": "any study of announcements must leave out or flag those years; refetch them first"})
    if pr_lows:
        findings.append({"area": "company announcements (old PR files)", "severity": "medium",
                         "finding": (f"the old PR-zip files thin out: {', '.join(f'{y}: {n:,}' for y, n in sorted(pr_lows.items()))} lines, while the timestamped "
                                     f"source is complete ({', '.join(f'{y}: {api_rows.get(y, 0):,}' for y in sorted(pr_lows))}); "
                                     f"{' and '.join(PR_READERS)} read the PR files"),
                         "so": ("new announcement studies use the timestamped source; V02's and HFN1's 2021-2022 years carry the hole, and re-running them on "
                                "the timestamped source would be a new registration (Madhav's decision), not a change to the frozen ones")})
    if intr:
        worst = min(intr.items(), key=lambda kv: kv[1].get("top250_covered") or 1)
        findings.append({"area": "intraday stock bars (5-minute)", "severity": "medium",
                         "finding": (f"coverage of the day's 250 most traded rises from {round(100 * (intr[min(intr)].get('top250_covered') or 0))}% in {min(intr)} "
                                     f"to {round(100 * (intr[max(intr)].get('top250_covered') or 0))}% in {max(intr)}; lowest {worst[0]}"),
                         "so": "intraday stock studies before about 2019 see only part of the liquid market; say so or start them in 2019"})
    if uni:
        y0, y1 = min(uni), max(uni)
        findings.append({"area": "the research universe", "severity": "medium",
                         "finding": (f"in {y1}, {uni[y1]['ranked_stocks']:,} stocks had a liquidity rank, {uni[y1]['ever_top250']} were in the day's 250 most "
                                     f"traded and {uni[y1]['ever_top500']} in the 500 most traded at some point (chosen each day, so delisted names are included). "
                                     "The studies that held up use: " + "; ".join(f"{k} {v}" for k, v in STUDY_UNIVERSES.items())),
                         "so": ("a finding says nothing about stocks outside its own universe; the narrow ones (OC1, IB1, GP1) are the ones to re-test on "
                                "the next band of stocks, registered before the run (registrations/w500_v1_draft.md)")})
    findings.append({"area": "survivorship and adjustments", "severity": "low",
                     "finding": (f"{(integ.get('survivorship') or {}).get('note')}; {(integ.get('corporate_actions') or {}).get('note')}; "
                                 f"{(integ.get('stale_prices') or {}).get('note')}"),
                     "so": "delisted names are in; a few unexplained jumps remain, and the lab skips frozen prices"})
    bm = board_meetings()
    findings.append({"area": "not on file", "severity": "medium",
                     "finding": (("" if bm else "NSE's board-meetings calendar (results dates ahead come only from filings that name them); ")
                                 + "analyst estimates (no 'beat or miss'); GIFT Nifty and live Asian markets; bulk and block deals before 23 Oct 2026; "
                                   "competitor financials beyond the sector map"),
                     "so": ("" if bm else "the board-meetings calendar is free and the cheapest to add; ") + "estimates are paid; GIFT Nifty has no free source"})
    falls = _j(paths.manifest_dir() / "big_falls.json", {}) or {}
    xbrl_done = bool(parsed_years) and min(parsed_years) <= 2018
    widen = [
        ("1. Done 3 Nov 2026 for 2018-2023 (the XBRL files). The old HTML result pages for 2010-2017 (D20b) are being fetched "
         "(india.results_html, about 85,000 pages at NSE's polite rate) and parsed into silver/fundamentals/results_html.parquet." if xbrl_done else
         "1. Parse the downloaded results (XBRL) for 2018-2021 so revenue and EPS cover six years, then the old HTML pages for 2010-2017 (D20b): "
         "the base for any results or P/E study."),
        ("2. Refetch the announcement years that are under half the usual count, so studies of announcements do not have holes." if api_lows else
         "2. Done 3 Nov 2026: the timestamped announcements are complete for 2010-2023 (the 2022 hole is in the old PR files only, and the "
         "2010-2012 rows lost to a de-duplication bug are back). V02T and HFN1T re-ran V02 and HFN1 on the timestamped source: the same verdicts "
         "(registrations/v02t_results_v1.md, hfn1t_results_v1.md)."),
        (f"3. Done 3 Nov 2026: NSE's board-meetings calendar is fetched every night (60 days ahead) with history from 2010 "
         f"({sum(bm.values()):,} meetings to 2023)." if bm else "3. Fetch NSE's board-meetings calendar each evening, so results days ahead are complete."),
        ("4. Done 3 Nov 2026: most studies that held up already use the 500 most traded; the narrow ones (OC1, IB1, GP1) were re-tested on the "
         "next band (W500): all 11 variants carry, as relative results only (registrations/w500_results_v1.md)."),
        ("5. Done 3 Nov 2026: each intraday stock study's write-up now carries the 5-minute coverage of its own universe by year "
         "(registrations/intraday_coverage.md). Left: whether new intraday stock studies start in 2019 is Madhav's choice."),
        (f"6. Checked 3 Nov 2026 (registrations/big_falls_v1.md): of {falls['falls']} unexplained falls, "
         f"{sum(v for k, v in falls['labels'].items() if k != 'no_evidence_found')} look like a split, bonus or demerger left out of the adjustment "
         f"({sum(v for k, v in falls['labels_since_2010'].items() if k != 'no_evidence_found')} since 2010); {falls['labels'].get('no_evidence_found', 0)} "
         "show no action nearby and need a look. The 2010-2023 cases were reviewed by hand and fixed on 3 Nov 2026 (registrations/ca_manual_v1.csv, "
         "the subject parser, and factors carried across renames); before 2010 the rest are left for a later look."
         if falls else
         "6. Check the liquid-stock falls of over 45% with no corporate action within 3 days: each is either a real crash or a missed split, "
         "bonus or demerger, and a missed one fakes a loss in every study that holds the stock."),
    ]
    out = {"built_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "rules": "dataaudit-v1-2026-11-03",
           "results": res, "xbrl_downloaded_by_year": xb, "universe_by_year": uni, "announcements_by_year": ann, "announcements_timestamped_by_year": api, "board_meetings_by_year": bm,
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
