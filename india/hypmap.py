"""hypothesis_map: every teacher hypothesis (Trade With Trend 60, Optionables 60, Madhav's M-series 17) mapped to what it needs, what state it is in, and the study that tests it.

  python -m india.hypmap build        gold/hypothesis_map/hypothesis_map.{parquet,csv}, catalog table hypothesis_map, and a summary
Register-level, not statement-level: the libraries already merged ~3,870 extracted statements into these rows (each row lists its source videos), so mapping the rows maps the
statements. Mapping rules were written by hand from the row text (this file is the record); Madhav reviews a 50-row sample plus every INTRADAY and EVENTS row.

family     ENTRY, EXIT, CONTEXT (regime, breadth, VIX, intermarket), SECTOR_RS, RISK (sizing/portfolio rules), OPTIONS_EOD, OPTIONS_INTRADAY, FUNDAMENTALS, EVENTS, PROCESS, PORTFOLIO, METHOD
status     TESTABLE_NOW   data is in the lake and the lab tools exist
           NEEDS_BUILD    data is ours but a table must be built first (index daily/VIX silver, breadth, sector map)
           NEEDS_DATA     a dataset we do not have yet (sector indices and industry map, macro, flows, fundamentals, Nifty P/E)
           EOD_FO         testable on end-of-day F&O prices with Greeks (labelled estimate; intraday legs wait for the recorder)
           WAITS_RECORDER needs intraday option prices: synthetic until the recorder has history
           DEFERRED       sizing and capital rules, deferred by Madhav ("not about sizing")
           OUT_OF_SCOPE   needs data nobody gives us for free (tick order book) or another asset class
exit       1 if the hypothesis is about when to leave or how to manage a position (Madhav's priority)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

from india import catalog, paths

LIB = Path.home() / "code" / "ananta-decision-agent" / "docs" / "library"

# id -> (family, exit, data lots, status, study, priority 1 high .. 3 low)
M = {
    # Trade With Trend
    "TWT-H01": ("CONTEXT", 0, "D01 D07", "TESTABLE_NOW", "C08", 1), "TWT-H02": ("CONTEXT", 0, "D11", "NEEDS_BUILD", "E08", 1), "TWT-H03": ("RISK", 0, "D01", "DEFERRED", "-", 3),
    "TWT-H04": ("SECTOR_RS", 0, "D29", "NEEDS_DATA", "C07", 2), "TWT-H05": ("SECTOR_RS", 0, "D29", "NEEDS_DATA", "C07", 2), "TWT-H06": ("SECTOR_RS", 0, "D29", "NEEDS_DATA", "C07", 2),
    "TWT-H07": ("CONTEXT", 0, "D11 D29", "NEEDS_DATA", "E08", 2), "TWT-H08": ("SECTOR_RS", 0, "D29", "NEEDS_DATA", "C07", 2), "TWT-H09": ("ENTRY", 0, "D01 D29", "NEEDS_DATA", "E05", 2),
    "TWT-H10": ("ENTRY", 0, "D01", "TESTABLE_NOW", "E05", 1), "TWT-H11": ("ENTRY", 0, "D01", "TESTABLE_NOW", "C02", 1), "TWT-H12": ("ENTRY", 0, "D01", "TESTABLE_NOW", "C02", 2),
    "TWT-H13": ("ENTRY", 0, "D01 D11", "NEEDS_BUILD", "C07", 2), "TWT-H14": ("ENTRY", 0, "D01 D11", "NEEDS_BUILD", "C07", 3), "TWT-H15": ("ENTRY", 0, "D01", "TESTABLE_NOW", "C02", 2),
    "TWT-H16": ("SECTOR_RS", 0, "D29", "NEEDS_DATA", "C07", 3), "TWT-H17": ("EXIT", 1, "D01", "TESTABLE_NOW", "E03", 1), "TWT-H18": ("EXIT", 1, "D01", "TESTABLE_NOW", "E05", 1),
    "TWT-H19": ("EXIT", 1, "D01", "TESTABLE_NOW", "E07", 1), "TWT-H20": ("PROCESS", 0, "D01", "TESTABLE_NOW", "E09", 2), "TWT-H21": ("PROCESS", 0, "D01", "TESTABLE_NOW", "E09", 3),
    "TWT-H22": ("EXIT", 1, "D01", "TESTABLE_NOW", "E02", 1), "TWT-H23": ("EXIT", 1, "D01", "TESTABLE_NOW", "E07", 1), "TWT-H24": ("EXIT", 1, "D01", "TESTABLE_NOW", "E06", 1),
    "TWT-H25": ("EXIT", 1, "D01 paper", "TESTABLE_NOW", "E10", 1), "TWT-H26": ("EXIT", 1, "D01", "TESTABLE_NOW", "E06", 1), "TWT-H27": ("CONTEXT", 0, "D01", "TESTABLE_NOW", "C01", 2),
    "TWT-H28": ("CONTEXT", 0, "D01 D11", "NEEDS_BUILD", "C01", 3), "TWT-H29": ("SECTOR_RS", 0, "D29", "NEEDS_DATA", "C07", 3), "TWT-H30": ("CONTEXT", 0, "D01", "TESTABLE_NOW", "C08", 2),
    "TWT-H31": ("CONTEXT", 0, "D01 D11", "NEEDS_BUILD", "C08", 2), "TWT-H32": ("CONTEXT", 0, "D01", "TESTABLE_NOW", "C08", 3), "TWT-H33": ("CONTEXT", 0, "D01", "TESTABLE_NOW", "C08", 2),
    "TWT-H34": ("CONTEXT", 0, "D11", "NEEDS_BUILD", "C01", 3), "TWT-H35": ("CONTEXT", 0, "D11", "NEEDS_BUILD", "C01", 3), "TWT-H36": ("CONTEXT", 0, "D11", "NEEDS_BUILD", "C01", 2),
    "TWT-H37": ("CONTEXT", 0, "D11", "NEEDS_BUILD", "C05", 1), "TWT-H38": ("CONTEXT", 0, "D11", "NEEDS_BUILD", "C05", 1), "TWT-H39": ("CONTEXT", 0, "D11", "NEEDS_BUILD", "C07", 2),
    "TWT-H40": ("CONTEXT", 0, "D11", "NEEDS_BUILD", "C01", 3), "TWT-H41": ("CONTEXT", 0, "D01", "TESTABLE_NOW", "C01", 3), "TWT-H42": ("CONTEXT", 0, "D22", "NEEDS_DATA", "C09", 3),
    "TWT-H43": ("CONTEXT", 0, "D22", "NEEDS_DATA", "C09", 3), "TWT-H44": ("CONTEXT", 0, "D22", "NEEDS_DATA", "C09", 3), "TWT-H45": ("CONTEXT", 0, "D22", "NEEDS_DATA", "C09", 3),
    "TWT-H46": ("CONTEXT", 0, "D11", "NEEDS_BUILD", "C03", 2), "TWT-H47": ("CONTEXT", 0, "D22", "NEEDS_DATA", "C09", 3), "TWT-H48": ("CONTEXT", 0, "D17", "NEEDS_DATA", "C06", 2),
    "TWT-H49": ("ENTRY", 0, "D01", "TESTABLE_NOW", "P01", 3), "TWT-H50": ("ENTRY", 0, "D01", "TESTABLE_NOW", "P01", 3), "TWT-H51": ("ENTRY", 0, "D01", "TESTABLE_NOW", "P01", 3),
    "TWT-H52": ("ENTRY", 0, "D01", "TESTABLE_NOW", "P01", 3), "TWT-H53": ("ENTRY", 0, "D01", "TESTABLE_NOW", "P01", 3), "TWT-H54": ("ENTRY", 0, "D01", "TESTABLE_NOW", "P01", 3),
    "TWT-H55": ("PROCESS", 0, "D01 D04", "TESTABLE_NOW", "I06", 2), "TWT-H56": ("PROCESS", 0, "D01 D04", "TESTABLE_NOW", "I06", 3), "TWT-H57": ("RISK", 0, "D11", "DEFERRED", "-", 3),
    "TWT-H58": ("FUNDAMENTALS", 0, "D20", "NEEDS_DATA", "V05", 2), "TWT-H59": ("OPTIONS_INTRADAY", 0, "D04 D10", "NEEDS_BUILD", "I06", 3), "TWT-H60": ("OPTIONS_INTRADAY", 0, "D04 D10", "NEEDS_BUILD", "I06", 3),
    # Optionables
    "OPT-H01": ("OPTIONS_INTRADAY", 1, "D10 D12 D13 D14", "WAITS_RECORDER", "R02", 1), "OPT-H02": ("OPTIONS_INTRADAY", 1, "D10 D14", "WAITS_RECORDER", "R02", 1),
    "OPT-H03": ("OPTIONS_INTRADAY", 1, "D10 D14", "WAITS_RECORDER", "R02", 1), "OPT-H04": ("OPTIONS_INTRADAY", 1, "D10 D14 D11", "WAITS_RECORDER", "R02", 1),
    "OPT-H05": ("OPTIONS_INTRADAY", 0, "D10 D14", "WAITS_RECORDER", "R02", 2), "OPT-H06": ("OPTIONS_INTRADAY", 1, "D10 D14", "WAITS_RECORDER", "R02", 1),
    "OPT-H07": ("OPTIONS_INTRADAY", 1, "D10 D14", "WAITS_RECORDER", "R02", 1), "OPT-H08": ("OPTIONS_INTRADAY", 0, "D14", "WAITS_RECORDER", "R02", 3),
    "OPT-H09": ("OPTIONS_INTRADAY", 1, "D10 D14", "WAITS_RECORDER", "R02", 2), "OPT-H10": ("OPTIONS_INTRADAY", 1, "D10 D14", "WAITS_RECORDER", "R02", 1),
    "OPT-H11": ("OPTIONS_INTRADAY", 1, "D10 D14", "WAITS_RECORDER", "I05", 1), "OPT-H12": ("OPTIONS_INTRADAY", 1, "D10 D14", "WAITS_RECORDER", "R02", 1),
    "OPT-H13": ("RISK", 1, "D14", "WAITS_RECORDER", "R02", 2), "OPT-H14": ("RISK", 0, "D12", "DEFERRED", "-", 3), "OPT-H15": ("RISK", 0, "D12", "DEFERRED", "-", 3),
    "OPT-H16": ("OPTIONS_EOD", 0, "D12 D13", "EOD_FO", "F02", 2), "OPT-H17": ("OPTIONS_EOD", 1, "D12 D13", "EOD_FO", "F05", 1), "OPT-H18": ("CONTEXT", 0, "D11", "NEEDS_BUILD", "C05", 2),
    "OPT-H19": ("CONTEXT", 0, "D11", "NEEDS_BUILD", "C05", 2), "OPT-H20": ("OPTIONS_EOD", 0, "D11 D12 D13", "EOD_FO", "F01", 2), "OPT-H21": ("OPTIONS_EOD", 0, "D11 D12 D13", "EOD_FO", "F01", 2),
    "OPT-H22": ("EVENTS", 0, "D10 D22 D14", "WAITS_RECORDER", "R02", 3), "OPT-H23": ("EVENTS", 0, "D22 D14", "WAITS_RECORDER", "R02", 3), "OPT-H24": ("EVENTS", 1, "D12 D22", "EOD_FO", "F06", 2),
    "OPT-H25": ("OPTIONS_EOD", 0, "D12", "EOD_FO", "F03", 1), "OPT-H26": ("OPTIONS_EOD", 0, "D12", "EOD_FO", "F03", 1), "OPT-H27": ("OPTIONS_EOD", 0, "D12 D11", "EOD_FO", "F03", 2),
    "OPT-H28": ("OPTIONS_EOD", 0, "D12", "EOD_FO", "F04", 2), "OPT-H29": ("OPTIONS_EOD", 0, "D12", "EOD_FO", "F04", 3), "OPT-H30": ("OPTIONS_EOD", 0, "D12", "EOD_FO", "F04", 2),
    "OPT-H31": ("OPTIONS_EOD", 0, "D12", "EOD_FO", "F03", 2), "OPT-H32": ("OPTIONS_EOD", 0, "D12", "EOD_FO", "F03", 3), "OPT-H33": ("CONTEXT", 0, "D17", "NEEDS_DATA", "C06", 2),
    "OPT-H34": ("OPTIONS_INTRADAY", 1, "D14", "WAITS_RECORDER", "F06", 2), "OPT-H35": ("OPTIONS_INTRADAY", 1, "D14", "WAITS_RECORDER", "F06", 2), "OPT-H36": ("OPTIONS_INTRADAY", 1, "D14", "WAITS_RECORDER", "F06", 1),
    "OPT-H37": ("OPTIONS_EOD", 1, "D12 D13", "EOD_FO", "F06", 1), "OPT-H38": ("OPTIONS_INTRADAY", 1, "D14", "WAITS_RECORDER", "F06", 2), "OPT-H39": ("OPTIONS_EOD", 1, "D12 D13", "EOD_FO", "F06", 1),
    "OPT-H40": ("OPTIONS_EOD", 1, "D12 D13", "EOD_FO", "F06", 1), "OPT-H41": ("OPTIONS_EOD", 1, "D12 D13", "EOD_FO", "F05", 1), "OPT-H42": ("OPTIONS_EOD", 0, "D12 D13", "EOD_FO", "F02", 2),
    "OPT-H43": ("OPTIONS_EOD", 0, "D12 D13", "EOD_FO", "F02", 2), "OPT-H44": ("OPTIONS_INTRADAY", 0, "-", "OUT_OF_SCOPE", "-", 3), "OPT-H45": ("OPTIONS_EOD", 0, "D12", "EOD_FO", "F03", 3),
    "OPT-H46": ("OPTIONS_EOD", 0, "D12 D13", "EOD_FO", "F01", 2), "OPT-H47": ("OPTIONS_EOD", 0, "D12 D13 D11", "EOD_FO", "F01", 2), "OPT-H48": ("ENTRY", 0, "D01 D11", "TESTABLE_NOW", "C02", 2),
    "OPT-H49": ("EXIT", 1, "D01", "TESTABLE_NOW", "E03", 1), "OPT-H50": ("EXIT", 1, "D01", "TESTABLE_NOW", "E07", 1), "OPT-H51": ("ENTRY", 0, "D01 D11", "TESTABLE_NOW", "C02", 2),
    "OPT-H52": ("EXIT", 1, "D01 D04", "TESTABLE_NOW", "E07", 1), "OPT-H53": ("ENTRY", 0, "D01", "TESTABLE_NOW", "C03", 2), "OPT-H54": ("METHOD", 0, "ledger", "TESTABLE_NOW", "G01", 2),
    "OPT-H55": ("METHOD", 0, "D08", "TESTABLE_NOW", "cost model v1", 1), "OPT-H56": ("OPTIONS_INTRADAY", 1, "tick", "OUT_OF_SCOPE", "-", 3), "OPT-H57": ("OPTIONS_EOD", 0, "D12", "EOD_FO", "F01", 2),
    "OPT-H58": ("OPTIONS_EOD", 0, "D12 D13 D06", "EOD_FO", "F01", 2), "OPT-H59": ("OPTIONS_INTRADAY", 0, "D14", "WAITS_RECORDER", "R02", 3), "OPT-H60": ("CONTEXT", 0, "D30", "NEEDS_DATA", "C09", 3),
    # Madhav's method
    "M-01": ("ENTRY", 0, "D10 D11", "NEEDS_BUILD", "I01", 1), "M-02": ("ENTRY", 0, "D10 D11", "NEEDS_BUILD", "I01", 1), "M-03": ("EXIT", 1, "D01", "TESTABLE_NOW", "E04", 1),
    "M-04": ("EXIT", 1, "D01 D02", "TESTABLE_NOW", "E04", 1), "M-05": ("EXIT", 1, "D01", "TESTABLE_NOW", "E05", 1), "M-06": ("EXIT", 1, "D01 D04", "TESTABLE_NOW", "E01", 1),
    "M-07": ("OPTIONS_EOD", 1, "D12 D10 D11", "EOD_FO", "F03", 1), "M-08": ("OPTIONS_EOD", 1, "D12 D13", "EOD_FO", "F07", 1), "M-09": ("CONTEXT", 0, "D01 D22", "NEEDS_DATA", "C03", 2),
    "M-10": ("CONTEXT", 0, "D02 D12", "TESTABLE_NOW", "C04", 2), "M-11": ("METHOD", 0, "D24", "NEEDS_DATA", "K02", 2), "M-12": ("PORTFOLIO", 1, "D01", "TESTABLE_NOW", "E06", 1),
    "M-13": ("EXIT", 1, "D01", "TESTABLE_NOW", "E04", 1), "M-14": ("EVENTS", 0, "D21", "NEEDS_DATA", "V03", 2), "M-15": ("FUNDAMENTALS", 0, "D20", "NEEDS_DATA", "V05", 2),
    "M-16": ("PORTFOLIO", 0, "D16", "NEEDS_DATA", "V06", 2), "M-17": ("OPTIONS_EOD", 1, "D12 D13 D08", "EOD_FO", "F07", 1),
}


def _rows() -> list[dict]:
    out = []
    for teacher, f, pat in (("TWT", LIB / "trade_with_trend" / "14_testable_hypotheses.md", r"^\| TWT-H\d+"), ("OPT", LIB / "optionables" / "17_testable_hypotheses.md", r"^\| OPT-H\d+")):
        for line in f.read_text().splitlines():
            if re.match(pat, line):
                c = [x.strip() for x in line.strip().strip("|").split("|")]
                out.append({"id": c[0], "teacher": "Trade With Trend" if teacher == "TWT" else "Optionables", "topic": c[1], "text": c[2], "direction": c[3], "needs": c[4], "codable": c[6] if len(c) > 6 else ""})
    mf = (LIB / "madhav" / "01_method_2026-10-17.md").read_text()
    for line in mf.splitlines():
        m = re.match(r"^\| (M-\d+) \| (.*?) \| (.*?) \| (.*?) \|$", line)
        if m:
            out.append({"id": m.group(1), "teacher": "Madhav", "topic": "METHOD", "text": m.group(2), "direction": "", "needs": m.group(3), "codable": "YES"})
    return out


def build() -> dict:
    rows = _rows()
    missing = [r["id"] for r in rows if r["id"] not in M]
    extra = [k for k in M if k not in {r["id"] for r in rows}]
    for r in rows:
        fam, ex, data, status, study, pri = M.get(r["id"], ("UNMAPPED", 0, "", "NEEDS_REVIEW", "-", 3))
        r.update({"family": fam, "exit_related": ex, "data_lots": data, "status": status, "study": study, "priority": pri})
    df = pd.DataFrame(rows)
    out = paths.gold() / "hypothesis_map"
    out.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out / "hypothesis_map.parquet", index=False)
    df.to_csv(out / "hypothesis_map.csv", index=False)
    con = catalog.connect()
    con.register("hm", df)
    con.execute("create or replace table hypothesis_map as select * from hm")
    con.close()
    summ = {"rows": len(df), "unmapped": missing, "stale_keys": extra,
            "by_status": df["status"].value_counts().to_dict(), "by_family": df["family"].value_counts().to_dict(),
            "exit_related": int(df["exit_related"].sum()), "exit_testable_now": int(((df["exit_related"] == 1) & df["status"].isin(["TESTABLE_NOW", "EOD_FO"])).sum()),
            "studies_not_in_tracker": sorted(set(df["study"]) - {"-"})}
    catalog.heartbeat("hypmap.build", not missing, f"{len(df)} rows")
    return summ


if __name__ == "__main__":
    paths.ensure()
    if sys.argv[1] == "build":
        import json
        print(json.dumps(build(), indent=1))
