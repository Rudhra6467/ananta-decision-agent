"""25 Oct 2026 data gaps: NSDL archive parser (FPI history), NSE FII/DII API parser, NSE Indices valuation parser, sector lists, and the
Kite fill driver's quiet windows."""
import datetime as dt
import json

from india import fiidii, kite_fill, sectormap, valuation

OLD = """<div id="dvArchiveData"><table><tr><td>Reporting Date</td><td>Debt/Equity</td><td>Gross Purchases (Rs Crore)</td></tr>
<tr><td>04-Jan-2000</td><td>Equity</td><td>148.40</td><td>59.30</td><td>89.10</td><td>20.50</td><td>Rs. 43.52</td></tr>
<tr><td></td><td>Debt</td><td>16.90</td><td>0.00</td><td>16.90</td><td>3.90</td></tr>
<tr><td>06-Jan-2000</td><td>Equity</td><td>250.30</td><td>528.30</td><td>(278.00)</td><td>(63.90)</td><td>Rs. 43.52</td></tr>
<tr><td></td><td>Debt</td><td>0.00</td><td>0.00</td><td>0.00</td><td>0.00</td></tr>
<tr><td>Total for January</td><td>Equity</td><td>398.70</td><td>587.60</td><td>(188.90)</td><td>(43.40)</td></tr></table>
<p>Reporting Date Derivative Products 04-Jan-2000 Index Futures 1.00 2.00 3.00</p></div>"""

NEW = """<div>Reporting Date Debt/Equity Investment Route Gross Purchases(Rs Crore)
01-Sep-2026 Equity Stock Exchange 65512.88 71652.44 (6139.56) (643.22) Rs.95.4509 Primary market &amp; others 706.73 0.00 706.73 74.04
Sub-total 66219.61 71652.44 (5432.83) (569.18) Debt-General Limit Stock Exchange 368.85 329.14 39.71 4.16 Primary market & others 176.36 197.58 (21.22) (2.22)
Sub-total 545.21 526.72 18.49 1.94 Debt-VRR Stock Exchange 35.42 74.65 (39.23) (4.11) Primary market & others 0.00 30.56 (30.56) (3.20)
Sub-total 35.42 105.21 (69.79) (7.31) Hybrid Stock Exchange 68.74 47.17 21.57 2.26 Primary market & others 220.62 0.00 220.62 23.11 Sub-total 289.36 47.17 242.19 25.37
Mutual Funds Equity schemes 42.48 18.22 24.26 2.54 Debt schemes 70.00 0.00 70.00 7.33 Sub-total 113.42 18.91 94.51 9.89 Total 68961.71 74336.62 (5374.91) (563.12)
Total for September Equity Stock Exchange 1.00 2.00 3.00 4.00 Sub-total 9.00 9.00 9.00 9.00
Reporting Date Derivative Products 01-Sep-2026 Index Futures 11853.00 1915.47 18599.00</div>"""


def test_nsdl_archive_old_layout_one_row_per_day_and_negatives():
    rows = fiidii.parse_nsdl_archive(OLD)
    eq = [r for r in rows if r["category"] == "FPI_equity"]
    assert [r["date"] for r in eq] == ["2000-01-04", "2000-01-06"]
    assert eq[0] == {"date": "2000-01-04", "category": "FPI_equity", "buy_cr": 148.4, "sell_cr": 59.3, "net_cr": 89.1}
    assert eq[1]["net_cr"] == -278.0                                   # parentheses are negatives
    assert not any(r["category"] == "FPI_equity_exchange" for r in rows)  # no route split before about 2011
    assert {r["date"] for r in rows if r["category"] == "FPI_debt"} == {"2000-01-04", "2000-01-06"}
    chk = fiidii.archive_month_check(OLD)
    assert chk["checked"] and chk["match"] and chk["page_total"] == -188.9


def test_nsdl_archive_new_layout_subtotals_and_mutual_funds_excluded():
    rows = {r["category"]: r for r in fiidii.parse_nsdl_archive(NEW)}
    assert set(rows) == {"FPI_equity", "FPI_equity_exchange", "FPI_debt"}     # the month total and derivatives tables are not days
    assert rows["FPI_equity"]["net_cr"] == -5432.83 and rows["FPI_equity_exchange"]["net_cr"] == -6139.56
    assert rows["FPI_debt"]["buy_cr"] == round(545.21 + 35.42, 2)             # Debt-General Limit + Debt-VRR; the funds' "Debt schemes" stay out
    assert rows["FPI_debt"]["net_cr"] == round(18.49 - 69.79, 2)


def test_nse_fii_dii_api():
    txt = json.dumps([{"buyValue": "19232.31", "category": "DII", "date": "23-Oct-2026", "netValue": "3235.36", "sellValue": "15996.95"},
                      {"buyValue": "14445.54", "category": "FII/FPI", "date": "23-Oct-2026", "netValue": "887.65", "sellValue": "13557.89"}])
    r = {x["category"]: x for x in fiidii.parse_nse(txt)}
    assert r["DII"]["net_cr"] == 3235.36 and r["FII"]["buy_cr"] == 14445.54 and r["FII"]["date"] == "2026-10-23"


def test_valuation_parser_both_shapes():
    rows = [{"RequestNumber": "x", "Index Name": "Nifty 50", "pe": "19.20", "pb": "4.14", "divYield": "1.24", "DATE": "29 Dec 2000"},
            {"RequestNumber": "x", "Index Name": "Nifty 50", "pe": "-", "pb": "4.1", "divYield": "", "DATE": "28 Dec 2000"}]
    a = valuation.parse(json.dumps(rows))
    b = valuation.parse(json.dumps({"d": json.dumps(rows)}))
    assert a == b and a[0] == {"date": "2000-12-29", "index_name": "NIFTY 50", "pe": 19.2, "pb": 4.14, "div_yield": 1.24}
    assert a[1]["pe"] is None and a[1]["div_yield"] is None


def test_sector_list_parser():
    txt = "﻿Company Name,Industry,Symbol,Series,ISIN Code\n360 ONE WAM Ltd.,Financial Services,360ONE,EQ,INE466L01038\nX Ltd.,,XLTD,EQ,INE000X01010\n"
    rows = sectormap.parse_list(txt)
    assert rows[0] == {"symbol": "360ONE", "isin": "INE466L01038", "company": "360 ONE WAM Ltd.", "industry": "Financial Services"}
    assert rows[1]["industry"] == "unknown"


def test_kite_fill_keeps_out_of_live_windows():
    t = lambda h, m: dt.datetime(2026, 10, 26, h, m, tzinfo=kite_fill.TOR)
    assert kite_fill.in_quiet(t(12, 30)) and kite_fill.in_quiet(t(19, 0)) and kite_fill.in_quiet(t(23, 50)) and kite_fill.in_quiet(t(1, 0))
    assert not kite_fill.in_quiet(t(3, 0)) and not kite_fill.in_quiet(t(10, 0)) and not kite_fill.in_quiet(t(15, 0))
    busy = "PID\tStatus\tLabel\n123\t0\tcom.ananta.india.paper\n53541\t-15\tcom.ananta.india.web\n"
    idle = "PID\tStatus\tLabel\n-\t0\tcom.ananta.india.paper\n53541\t-15\tcom.ananta.india.web\n49120\t-15\tcom.ananta.explorer\n"
    assert kite_fill.india_job_running(busy) and not kite_fill.india_job_running(idle)
