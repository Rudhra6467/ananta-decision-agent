"""The India market-context feed in Ask (jarvis/india/marketcontext.py; Madhav, 26 Oct: rupee, dollar, crude, US yields and indices, fear gauges, FII/DII).
Short plain readings are answered in code with each reading's own as-of date and lag; "why" questions go to the model; nothing here predicts."""
import pytest

from jarvis.india import marketcontext, views

TESTED = ("Tested 26 Oct (studies XO1, FX1, FII1, DII1 and the crude card TWT-H43): none of these readings predicts what the Nifty does next. "
          "Use them to explain a move, never to trade.")


def _m(label, value, as_of, lag, c1, c5, unit=None, kind="pct", src="FRED"):
    return {"label": label, "status": "ok", "as_of": as_of, "lag_days": lag, "value": value, "unit": unit, "change_1": c1, "change_5": c5,
            "change_kind": kind, "source": src}


MC = {"status": "ok", "words": "w", "explains": "e", "tested": TESTED, "how_to_say_it": "h",
      "rupee_same_day": {**_m("USD/INR", 95.19, "2026-10-26", 0, 0.003, 0.001, src="Kite"), "contract": "USDINR26OCTFUT"},
      "macro": {"DEXINUS": _m("USD/INR, FRED", 95.05, "2026-10-23", 3, 0.001, 0.002),
                "SP500": _m("S&P 500", 7624.0, "2026-10-23", 3, -0.005, 0.01),
                "NASDAQCOM": _m("Nasdaq", 25955.0, "2026-10-23", 3, -0.002, 0.01),
                "DCOILBRENTEU": _m("Brent crude", 115.22, "2026-10-20", 6, -0.03, 0.02, unit="dollars a barrel"),
                "DGS10": _m("US 10-year yield", 5.00, "2026-10-23", 3, 0.04, 0.10, unit="%", kind="points"),
                "DTWEXBGS": _m("Dollar index", 121.32, "2026-10-23", 3, 0.001, 0.003),
                "VIXCLS": _m("US VIX", 19.45, "2026-10-23", 3, 0.02, 0.05)},
      "india_vix": _m("India VIX", 17.16, "2026-10-26", 0, 0.018, 0.03, src="NSE"),
      "flows": {"status": "ok", "as_of": "2026-10-26", "rows": {"FII": {"net_cr": -1462.0}, "DII": {"net_cr": 2610.0}}},
      "gift_nifty": "no free source"}
RM = {"market_context": MC}


@pytest.fixture
def rm(monkeypatch):
    monkeypatch.setattr(views, "readmodel", lambda: RM)
    return RM


def _a(q):
    r = marketcontext.market_context_flow(q)
    return r["answer"] if r else None


def test_rupee_same_day_with_as_of_and_the_tested_line(rm):
    r = marketcontext.market_context_flow("what is the rupee doing?")
    assert r["kind"] == "answer" and r["route"] == "india" and set(r) >= {"answer", "follow_ups", "evidence", "ui", "points"}
    a = r["answer"]
    assert "95.19" in a and "Mon 26 Oct" in a and "weaker" in a and "read the move, not the exact level" in a
    assert "never to trade" in a


def test_us_close_and_crude_say_their_lag(rm):
    us = _a("how did the US close?")
    assert "S&P 500 7,624" in us and "Nasdaq 25,955" in us and "Fri 23 Oct" in us and "3 days behind today" in us
    c = _a("what is Brent crude at?")
    assert "115.22" in c and "Tue 20 Oct" in c and "6 days behind today" in c


def test_flows_and_vix_and_gift(rm):
    f = _a("what did FII and DII do?")
    assert "FII -1,462 crore" in f and "DII +2,610 crore" in f and "Mon 26 Oct" in f
    v = _a("what is the VIX?")
    assert "India VIX 17.16" in v and "US VIX 19.45" in v
    assert "no free source" in _a("what is GIFT Nifty showing?")


def test_yield_and_dollar_index(rm):
    assert "US 10-year yield 5.00%" in _a("what is the US 10-year yield?")
    assert "Dollar index 121.32" in _a("how is the dollar index?")


def test_what_it_leaves_to_the_model_or_other_flows(rm):
    for q in ("why did Nifty gap down?", "should I buy because the rupee fell?", "research the rupee and the Nifty", "flag this: rupee card is wrong",
              "will crude affect the Nifty?", "is the rupee tested?", "what's the weather", "x" * 200 + " rupee"):
        assert marketcontext.market_context_flow(q) is None, q


def test_missing_feed_hands_off(monkeypatch):
    monkeypatch.setattr(views, "readmodel", lambda: {"market_context": {"status": "unavailable"}})
    assert marketcontext.market_context_flow("what is the rupee doing?") is None
    f = marketcontext.facts_part({"market_context": {"status": "unavailable"}})
    assert f["status"] == "unavailable" and "never state a rupee" in f["how_to_say_it"]


def test_facts_part_is_compact_and_carries_the_tested_line(rm):
    f = marketcontext.facts_part(RM)
    assert f["tested"] == TESTED and f["rupee_same_day"]["value"] == 95.19 and set(f["macro"]) >= {"DEXINUS", "SP500", "DCOILBRENTEU", "DGS10"}
    assert f["macro"]["DCOILBRENTEU"]["lag_days"] == 6 and f["gift_nifty"] == "no free source"
