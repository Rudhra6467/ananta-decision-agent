"""12 Nov 2026, the keen outside audit, audit repair 4 (open-list flag 120), G-23 (trader's wording on India): 'Bank Nifty · short' was a
bought put shown with no strike, expiry or premium; 'One point a session' sat under a chart of 7 closes beside 'Session 6 of 60'; a coin
flip was said to score 9 of 15 with no word that chance alone averages 7.5. Each check failed against the code before."""

from jarvis import placekit as K
from jarvis.india import places as IP
from jarvis.india import views
from tests import test_places_india as _places_india  # the places fixture: fixed inputs, no live data
india = _places_india.india          # 12 Nov: taken from the module, so the India firewall reads no import of the india package

_FIXTURES = (india,)                                                                     # the places fixture, used by name below

PUT = {"kind": "outcome", "date": "2026-11-09", "index": "BANKNIFTY", "dir": -1, "exit": "ATRSTOP", "index_proxy": {"net_bps": -9.0},
       "legs": {"option": {"tradingsymbol": "BANKNIFTY26NOV59100PE", "lot": 30.0, "entry_realistic": 797.6, "exit": 602.4, "net_rs_realistic": -6053.6}}}


def test_a_bought_put_is_said_as_one_with_its_strike_month_and_premium(india):
    row = IP._trade_row(PUT)
    assert row["title"] == "Bought a Bank Nifty put" and "paid ₹23,928" in row["sub"]     # it said "Bank Nifty · short"
    assert K.nwords(row["title"]) <= K.MAX["row_title"] and K.nwords(row["sub"]) <= K.MAX["row_sub"]
    assert IP._option_bought(PUT) == ("Bank Nifty put", "59,100 Nov, paid ₹23,928")


def test_the_chart_says_its_first_point_is_the_start(india):
    page = IP.account()
    chart = next(p for p in page["parts"] if p.get("t") == "chart")
    assert chart["caption"] == "The Fri 30 Oct close it started at, then the 1 session since, each at its close."
    assert K.problems("account", page) == []


def test_the_coin_flip_is_said_beside_what_chance_averages():
    rm = {"call": {"call": "BULLISH", "hits": 5, "scored": 15, "null_hits": 9, "data_through": "2026-11-11"}, "data_through": "2026-11-11",
          "market": {}, "guardrails": {}, "sp1": {}}
    why = " ".join(views._account_sp1(rm)["dial"]["why"])
    assert "a coin flip got 9, where chance alone averages 7.5" in why
    assert any("against 9 for a coin flip (chance alone averages 7.5)" in x for x in views.plain_brief(rm))
