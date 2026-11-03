"""3 Nov 2026 (big-falls review): the corporate-action subject parser, the manual review file, the timestamped-announcement timing (V02T,
HFN1T) and the old HTML results pages (D20b)."""
import csv
from pathlib import Path

import pandas as pd

from india import actions, annstudies, results_html

REG = Path(__file__).resolve().parents[1] / "india" / "registrations"


def test_subjects():
    p = actions.parse_subject
    assert p("Bonus - 1:1 And Face Value Split From Rs. 10 To Rs. 2") == {"kind": "BONUS+SPLIT", "ratio": 10.0, "amount": None}
    assert p("Fv Spl-Rs10tors5/Bon-2:1")["ratio"] == 6.0
    assert p("Bonus Issue 1 : 1")["ratio"] == 2.0 and p("Bonus Shares In The Ratio Of 1:1")["ratio"] == 2.0
    assert p("Bonus 3:2")["ratio"] == 2.5 and p("Bonus 1:1")["ratio"] == 2.0
    assert p("Face Value Split (Sub-Division) - From Rs 10/- Per Share To Rs 2/- Per Share")["ratio"] == 5.0
    for s in ("Sch Of Agmt- Bonus Deb1:1", "Bonus Debentures 1:1", "Bonus Ncrps 1:116", "Scheme Of Arrangement - Bonus Ncrps 4:1", "Bonus Preference Shares 1:1"):
        assert p(s)["ratio"] is None, s                     # not equity: no factor


def test_manual_review_file():
    rows = list(csv.DictReader((REG / "ca_manual_v1.csv").open()))
    assert rows and all(r["decision"] in ("apply", "price", "flag") and r["evidence"].strip() for r in rows)
    assert all(float(r["factor"]) > 1 for r in rows if r["decision"] == "apply")
    assert all(not r["factor"] for r in rows if r["decision"] != "apply")
    assert len({(r["symbol"], r["ex_date"]) for r in rows}) == len(rows)


def test_known_session():
    s = pd.DatetimeIndex(pd.to_datetime(["2020-01-02", "2020-01-03", "2020-01-06"]))
    t = pd.Series(pd.to_datetime(["2020-01-02 10:00", "2020-01-02 15:30", "2020-01-02 15:31", "2020-01-04 11:00", "2020-01-06 18:00"]))
    got = annstudies.known_session(t, s)
    assert [x.date().isoformat() if pd.notna(x) else None for x in got] == ["2020-01-02", "2020-01-02", "2020-01-03", "2020-01-06", None]


PAGE = """<html><body><table><tr><td>Description</td><td>Amount(Rs. in lakhs)</td></tr>
<tr><td>Net Sales/Income from Operation</td><td>30,444.98</td></tr><tr><td>Total Expenditure</td><td>29602.25</td></tr>
<tr><td>Interest</td><td>559.87</td></tr><tr><td>Net Profit (+) / Loss (-) for the period </td><td>287.59</td></tr>
<tr><td>Face Value (in Rs.)</td><td>10.00</td></tr><tr><td>Basic EPS after Extraordinary items (in Rs.)</td><td>2.84</td></tr></table></body></html>"""


def test_results_page():
    p = results_html.parse(PAGE)
    assert p["unit"] == 1e5 and round(p["revenue"]) == 3_044_498_000 and round(p["profit"]) == 28_759_000
    assert p["finance_costs"] > 0 and p["face_value"] == 10.0 and p["eps_basic"] == 2.84
    assert results_html.parse(PAGE.replace("lakhs", "crores"))["revenue"] == 30444.98 * 1e7
