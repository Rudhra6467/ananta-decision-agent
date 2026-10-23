"""The two forward captures (bulk/block deals, FII/DII cash flows): parsers on captured page shapes."""
import pandas as pd

from india import fiidii

MSEI_HTML = """<html><body>
<table><tr><th>Category</th><th>Date</th><th>Buy&nbsp;Value</th><th>Sell Value</th><th>Net Value</th></tr>
<tr><td>FII/FPI</td><td>22-Oct-2026</td><td>13627.54</td><td>17086.24</td><td>-3458.70</td></tr>
<tr><td colspan=5>As on 22 Oct, 2026</td></tr></table>
<table><tr><th>Category</th><th>Date</th><th>Buy&nbsp;Value</th><th>Sell Value</th><th>Net Value</th></tr>
<tr><td>DII</td><td>22-Oct-2026</td><td>16242.83</td><td>13351.51</td><td>2891.32</td></tr>
<tr><td colspan=5>As on 22 Oct, 2026</td></tr></table></body></html>"""

NSDL_TEXT = """<html><body><script>var x = 1;</script><div>Daily Trends in FPI Investments on 23-Oct-2026</div>
<table><tr><td>23-Oct-2026</td><td>Equity</td><td>Stock Exchange</td><td>14875.82</td><td>17137.99</td><td>(2262.17)</td><td>(238.88)</td><td>Rs.94.6986</td></tr>
<tr><td></td><td></td><td>Primary market &amp; others</td><td>2417.14</td><td>0.00</td><td>2417.14</td><td>255.25</td></tr>
<tr><td></td><td></td><td>Sub-total</td><td>17292.96</td><td>17137.99</td><td>154.97</td><td>16.37</td></tr></table></body></html>"""


def test_parse_msei():
    rows = fiidii.parse_msei(MSEI_HTML)
    assert {r["category"] for r in rows} == {"FII", "DII"}
    fii = next(r for r in rows if r["category"] == "FII")
    assert fii["date"] == "2026-10-22" and fii["buy_cr"] == 13627.54 and fii["net_cr"] == -3458.70


def test_parse_nsdl_parentheses_are_negative():
    rows = fiidii.parse_nsdl(NSDL_TEXT.replace("&amp;", "&"))
    assert len(rows) == 2
    ex = rows[0]
    assert ex["category"] == "FPI_equity_exchange" and ex["date"] == "2026-10-23"
    assert ex["buy_cr"] == 14875.82 and ex["sell_cr"] == 17137.99 and ex["net_cr"] == -2262.17
    assert rows[1]["category"] == "FPI_equity_primary" and rows[1]["net_cr"] == 2417.14


def test_sealed_routing_rule():
    from india import paths
    assert pd.Timestamp("2026-10-22") >= pd.Timestamp(paths.HOLDOUT_START)   # every live capture lands under sealed/silver
