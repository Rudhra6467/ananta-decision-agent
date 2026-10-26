"""DII1 and the SEBI mutual fund history (Madhav's yes of 26 Oct 2026): the page parser and its month check, the timing (a trading-date row is
used only from the session after it), the frozen bar, and that no row from 2024 on reaches the study."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from india import diistudy, fiidii, registry

PAGE = """<html><head><title>SEBI | Mutual Funds Trends</title></head><body><table>
<tr><th>Trading Date</th><th>Debt/Equity</th><th>Gross Purchases(Rs Crore)</th><th>Gross Sales(Rs Crore)</th><th>Net Investment (Rs Crore)</th></tr>
<tr><td rowspan=2>02 Mar, 2010</td><td>Equity</td><td>782.68</td><td>962.37</td><td>(179.69)</td></tr>
<tr><td>Debt</td><td>2081.86</td><td>2071.47</td><td>10.39</td></tr>
<tr><td rowspan=2>03 Mar, 2010</td><td>Equity</td><td>701.62</td><td>619.06</td><td>82.56</td></tr>
<tr><td>Debt</td><td>1,614.62</td><td>1234.47</td><td>380.15</td></tr>
<tr><td rowspan=2>Total</td><td>Equity</td><td>1484.30</td><td>1581.43</td><td>(97.13)</td></tr>
<tr><td>Debt</td><td>3696.48</td><td>3305.94</td><td>390.54</td></tr>
</table><table><tr><th>Period</th><th>Debt/Equity</th><th>a</th><th>b</th><th>c</th></tr>
<tr><td>April 2008-Mar 2009</td><td>Equity</td><td>144068</td><td>137085</td><td>6983</td></tr></table></body></html>"""


def test_sebi_page_parses_brackets_commas_and_stops_at_the_total():
    rows = fiidii.parse_sebi_mf(PAGE)
    assert [(r["date"], r["category"]) for r in rows] == [("2010-03-02", "MF_equity"), ("2010-03-02", "MF_debt"), ("2010-03-03", "MF_equity"), ("2010-03-03", "MF_debt")]
    assert rows[0]["net_cr"] == -179.69 and rows[3]["buy_cr"] == 1614.62
    chk = fiidii.mf_month_check(PAGE)
    assert chk["checked"] and chk["match"] and chk["page_total"] == -97.13 and chk["days"] == 2


def test_a_trading_date_row_is_placed_on_the_next_session():
    sess = pd.DatetimeIndex(pd.bdate_range("2010-03-01", periods=6))
    flow = pd.Series([10.0, 20.0], index=pd.DatetimeIndex(["2010-03-02", "2010-03-06"]))    # a Tuesday and a Saturday
    mf = diistudy._place(flow, sess, after=True)
    assert mf.loc["2010-03-03"] == 10.0 and np.isnan(mf.loc["2010-03-02"]) and mf.loc["2010-03-08"] == 20.0
    fpi = diistudy._place(flow, sess, after=False)
    assert fpi.loc["2010-03-02"] == 10.0


def test_spec_bar_is_frozen_and_matches_the_plan():
    s = diistudy.spec()
    assert abs(registry.threshold(int(s["bar"]["union_k"])) - s["bar"]["z"]) < 0.01
    assert set(s["variants"]) == {f"{e}|{c}" for e, c, _h, _ok in diistudy.PLAN}
    assert s["family"] == "flows" and s["bar"]["union_k"] == 22


def test_the_frame_never_uses_2024_or_later():
    M = diistudy.frame()
    assert M.index.max() < pd.Timestamp("2024-01-01")
    assert {"neg1", "pos5", "diibuy_fiisell", "nfwd20"} <= set(M.columns)
