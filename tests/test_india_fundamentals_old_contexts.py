"""Older BSE result files (2018-2021) use OneD / FourD / OneI without defining them. The parser must still read their figures."""
from india import fundamentals as F

OLD = """<xbrli:xbrl>
<xbrli:context id="OneReportableSegmentRevenue01D"><xbrli:entity><xbrli:segment>x</xbrli:segment></xbrli:entity><xbrli:period><xbrli:startDate>2018-07-01</xbrli:startDate><xbrli:endDate>2018-09-30</xbrli:endDate></xbrli:period></xbrli:context>
<in-bse-fin:Symbol contextRef="OneD">ABC</in-bse-fin:Symbol>
<in-bse-fin:DateOfStartOfFinancialYear contextRef="OneD">2018-04-01</in-bse-fin:DateOfStartOfFinancialYear>
<in-bse-fin:DateOfStartOfReportingPeriod contextRef="OneD">2018-07-01</in-bse-fin:DateOfStartOfReportingPeriod>
<in-bse-fin:DateOfEndOfReportingPeriod contextRef="OneD">2018-09-30</in-bse-fin:DateOfEndOfReportingPeriod>
<in-bse-fin:RevenueFromOperations contextRef="OneD" unitRef="INR" decimals="-5">357136000.00</in-bse-fin:RevenueFromOperations>
<in-bse-fin:RevenueFromOperations contextRef="FourD" unitRef="INR" decimals="-5">700000000.00</in-bse-fin:RevenueFromOperations>
<in-bse-fin:PaidUpValueOfEquityShareCapital contextRef="OneI" unitRef="INR" decimals="-5">10000000.00</in-bse-fin:PaidUpValueOfEquityShareCapital>
<in-bse-fin:SegmentRevenue contextRef="OneReportableSegmentRevenue01D" unitRef="INR" decimals="-5">1.00</in-bse-fin:SegmentRevenue>
</xbrli:xbrl>"""

DEFINED = """<xbrli:xbrl>
<xbrli:context id="OneD"><xbrli:entity>e</xbrli:entity><xbrli:period><xbrli:startDate>2022-07-01</xbrli:startDate><xbrli:endDate>2022-09-30</xbrli:endDate></xbrli:period></xbrli:context>
<in-bse-fin:DateOfStartOfReportingPeriod contextRef="OneD">2022-07-01</in-bse-fin:DateOfStartOfReportingPeriod>
<in-bse-fin:DateOfEndOfReportingPeriod contextRef="OneD">2022-09-30</in-bse-fin:DateOfEndOfReportingPeriod>
<in-bse-fin:RevenueFromOperations contextRef="OneD" unitRef="INR" decimals="-5">5.00</in-bse-fin:RevenueFromOperations>
</xbrli:xbrl>"""


def _own(head, facts):
    return [f for f in facts if f["end"] == head["period_end"] and (f["instant"] or f["start"] == head["period_start"])]


def test_undefined_plain_contexts_are_read(tmp_path):
    p = tmp_path / "old.xml"
    p.write_text(OLD)
    head, facts = F.parse(str(p))
    assert head["fy_start"] == "2018-04-01"
    own = {f["tag"]: f["value"] for f in _own(head, facts)}
    assert own["RevenueFromOperations"] == 357136000.0          # the quarter, not the year-to-date figure
    assert own["PaidUpValueOfEquityShareCapital"] == 10000000.0
    assert "SegmentRevenue" not in own                          # segment facts stay out
    ytd = [f for f in facts if f["tag"] == "RevenueFromOperations" and f["start"] == "2018-04-01"]
    assert ytd and ytd[0]["value"] == 700000000.0


def test_defined_contexts_unchanged(tmp_path):
    p = tmp_path / "new.xml"
    p.write_text(DEFINED)
    head, facts = F.parse(str(p))
    own = {f["tag"]: f["value"] for f in _own(head, facts)}
    assert own == {"RevenueFromOperations": 5.0}
