"""27 Oct 2026 night, second outside review of the India Ask (Madhav: "be an outsider and analyze those answers ... and perform the fixes"):
total-return benchmarks to the fund's own date, a gold fund against its own fund house's ETF, ETF splits, the IPO calendar, the Nifty's
this-year change, the horizon-not-stated two lines, noise and length lines, the paper picks that broke the don't-chase filter, and plain words.
Fixture files only; the network is never touched."""
import datetime as dt
import json

import pytest

from jarvis.india import answerguide as G
from jarvis.india import askwords as W
from jarvis.india import lookup as L
from tests.test_india_lookup import _mfapi_body, _navs, data  # noqa: F401  (the shared fixture)


def _tri_file(cache, series):
    cache.mkdir(parents=True, exist_ok=True)
    (cache / "tri.json").write_text(json.dumps({"built_at": "2026-10-27", "source": "niftyindices",
                                                "series": {k: [[d.isoformat(), v] for d, v in s] for k, s in series.items()}}))


# ------------------------------------------------------------------------------------------------------------------------------ lookup
def test_fund_compared_with_total_return_index_to_its_own_date(data, monkeypatch):
    _tri_file(L.CACHE, {"NIFTY 500": _navs(growth=0.11, end="2026-10-27")})
    monkeypatch.setattr(L, "_fetch_nav", lambda code: _navs(growth=0.14))
    monkeypatch.setattr(L, "_with_amfi", lambda code, navs: navs)
    pp = L.fund_facts(L.find_funds("Parag Parikh Flexi Cap fund"))["funds"]["122639"]
    b = pp["benchmark"]
    assert b["name"] == "Nifty 500 total-return index" and b["end_date"] == "2026-10-26"      # cut to the fund's last NAV, not the index's
    assert b["cagr_3y"] == pytest.approx(0.11, abs=0.004)


def test_index_fund_gets_a_tracking_difference(data, monkeypatch):
    _tri_file(L.CACHE, {"NIFTY 50": _navs(growth=0.10)})
    monkeypatch.setattr(L, "_fetch_nav", lambda code: _navs(growth=0.098))
    monkeypatch.setattr(L, "_with_amfi", lambda code, navs: navs)
    u = L.fund_facts(L.find_funds("UTI Nifty 50 Index Fund"))["funds"]["120716"]
    assert u["tracking_difference_1y"] == pytest.approx(-0.002, abs=0.001)


def test_gold_fund_compared_with_its_own_houses_etf(data, monkeypatch):
    rows = json.loads((L.MAN / "mf_schemes.json").read_text())["rows"]
    rows.append({"code": 111954, "name": "SBI Gold ETF", "amc": "SBI Mutual Fund", "type": "Open Ended Schemes", "category": "Other Scheme - Gold ETF",
                 "plan": "", "option": "", "nav": 119.5, "date": "2026-10-27", "isin": "INF0"})
    (L.MAN / "mf_schemes.json").write_text(json.dumps({"rows": rows}))
    L._files.clear()
    seen = []

    def fetch(code):
        seen.append(code)
        return _navs(growth=0.12)
    monkeypatch.setattr(L, "_fetch_nav", fetch)
    monkeypatch.setattr(L, "_with_amfi", lambda code, navs: navs)
    sb = L.fund_facts(L.find_funds("Is SBI Gold Fund good to hold?"))["funds"]["119788"]
    assert 111954 in seen and "SBI Gold ETF" in sb["benchmark"]["name"]
    assert "24 months" in sb["words"]


def test_etf_split_is_not_a_crash():
    navs = [(dt.date(2020, 1, 1) + dt.timedelta(days=i), 4000.0 + i) for i in range(10)] + \
           [(dt.date(2020, 1, 11) + dt.timedelta(days=i), 40.1 + i / 100) for i in range(10)]
    out = L._split_adjust(navs)
    assert out[0][1] == pytest.approx(40.0, rel=0.01) and min(b / a for (_, a), (_, b) in zip(out, out[1:])) > 0.9
    assert L._split_adjust([(dt.date(2020, 3, 20), 10.0), (dt.date(2020, 3, 23), 6.0)])[0][1] == 10.0   # a 40% fall is a fall, not a split


def test_etf_label_says_no_direct_plan(data, monkeypatch):
    monkeypatch.setattr(L, "_fetch_nav", lambda code: _navs(growth=0.12))
    monkeypatch.setattr(L, "_with_amfi", lambda code, navs: navs)
    g = L.fund_facts(L.find_funds("Nippon India ETF Gold BeES fund"))["funds"]["140088"]
    assert "ETFs have no Direct or Regular plan" in g["words"]


def test_generic_nifty_50_index_fund_gets_an_example(data, monkeypatch):
    monkeypatch.setattr(L, "_fetch_nav", lambda code: _navs(growth=0.10))
    r = L.facts_for("Nifty BeES ETF or a Nifty 50 index fund for a monthly SIP?")
    assert "120716" in r["mutual_funds"]["funds"]


def test_ipo_facts(data):
    assert L.facts_for("Any IPOs this week?")["ipo"]["status"] == "missing"
    L.CACHE.mkdir(parents=True, exist_ok=True)
    (L.CACHE / "ipo.json").write_text(json.dumps({"built_at": "2026-10-27T20:00", "current": [
        {"companyName": "BLS Polymers Limited", "issueStartDate": "27-Oct-2026", "issueEndDate": "29-Oct-2026", "priceBand": "Rs.142 to Rs.150",
         "noOfTime": "5.021756"}], "upcoming": []}))
    w = L.facts_for("Any good IPOs open this week?")["ipo"]["words"]
    assert "BLS Polymers Limited" in w and "subscribed 5.02 times" in w and "none listed" in w
    assert "ipo" not in L.facts_for("What is a golden cross?")


def test_quote_words_carry_this_year_against_the_nifty(data):
    qb = json.loads((L.MAN / "quotebook.json").read_text())
    qb["nifty"].update({"close": 22749.75, "as_of": "2026-10-27", "chg_ytd": -0.129})
    (L.MAN / "quotebook.json").write_text(json.dumps(qb))
    L._files.clear()
    r = L.facts_for("How has TCS done this year compared with the Nifty?")
    assert "behind the Nifty (-12.9% this year) by 9.2 points" in r["stocks"]["TCS"]["words"]
    assert "this year -12.9%" in r["nifty"]["words"]


def test_sector_words_state_the_window(data):
    _tri_file(L.CACHE, {"NIFTY SMLCAP 250": [(dt.date(2024, 9, 1) + dt.timedelta(days=i), 100 + i if i < 200 else 300 - i)
                                             for i in range(400)]})
    w = L.sector_facts()["words"]
    assert "52-week high" in w and "small caps" in w and "below their peak of" in w and "since 2015" in w


# ------------------------------------------------------------------------------------------------------------------------------ answer guide
def _lines(text, f=None):
    return " | ".join(G.guide(text, f or {})["lines"])


def test_horizon_not_stated_gets_two_lines():
    s = _lines("What's the current price of TCS and is it a good buy now?")
    assert "HORIZON NOT STATED" in s and "As a trade (weeks):" in s and "As a long-term holding (years):" in s
    assert "HORIZON NOT STATED" in _lines("My friend says buy small caps now because they've fallen 30%. What's your view?")
    assert "HORIZON NOT STATED" not in _lines("How has Reliance done this year compared with the Nifty?")            # no decision asked
    assert "HORIZON NOT STATED" not in _lines("A stock you hold is down 15% in two days on heavy volume. Do you sell, hold or add?")
    assert "HORIZON NOT STATED" not in _lines("Should I continue my SIP in a Nifty 50 index fund?")                   # long term


def test_long_term_decision_is_not_timed():
    s = _lines("Is SBI Gold Fund Direct Plan Growth a good fund to hold?")
    assert "NO TIMING" in s and "52-week high" in s


def test_worry_question_is_short_and_has_no_book_or_levels():
    g = G.guide("uh Ananta what's uh the, the Nifty doing today and uh should I worry", {})
    s = " | ".join(g["lines"])
    assert "WORRY QUESTION" in s and "LENGTH: at most 3 sentences." in s and "no cash target" in s


def test_paper_rules_stay_with_the_book_and_account():
    assert "no cash target" in _lines("Is TCS a good buy?")
    assert "no cash target" not in _lines("What should I do with my holdings this week?")
    assert "no cash target" not in _lines("How is the practice book doing?")


def test_noise_lines_and_no_assumed_sip():
    s = _lines("What does open interest tell you in Nifty options?")
    assert "put-call ratio" in s and "LEVELS" in s and "'Decision:'" in s
    assert "Do not assume he (or his friend) has a SIP" in _lines("Is Parag Parikh Flexi Cap a good fund?")
    assert "Do not assume he (or his friend) has a SIP" not in _lines("My friend has a Parag Parikh SIP for 3 years. Should he continue?")
    assert "LENGTH: at most 5 sentences." in _lines("Should I buy Infosys?")


def test_tax_answer_gives_the_conditions():
    f = {"lookup": {"rules": [{"id": "equity_cg_conditions"}]}}
    assert "STT paid" in _lines("How is long-term capital gains on equity taxed in India now?", f)
    assert "TAX:" not in _lines("How is long-term capital gains on equity taxed in India now?", {})


def test_options_line_is_too_early_to_grade():
    assert "too early to grade" in _lines("How is the options line doing so far?")


def test_chase_picks_are_reported(tmp_path, monkeypatch):
    d = tmp_path / "paper" / "decisions"
    d.mkdir(parents=True)
    (d / "2026-10-27.universe.json").write_text("{}")
    (d / "2026-10-27.json").write_text(json.dumps({"data_through": "2026-10-27", "journal": [
        {"symbol": "ACUTAAS", "status": "chosen", "rsi14": 70.8, "dist_sma50": 0.169},
        {"symbol": "CALM", "status": "chosen", "rsi14": 55.0, "dist_sma50": 0.02},
        {"symbol": "HOT", "status": "passed", "rsi14": 80.0, "dist_sma50": 0.3}]}))
    monkeypatch.setattr(G, "DATA", tmp_path)
    assert G.chase_picks() == [{"symbol": "ACUTAAS", "decided_for": "2026-10-27", "rsi": 71, "above_50day_pct": 17}]
    s = _lines("How is the practice book doing?")
    assert "ACUTAAS at RSI 71, 17% above its 50-day average" in s and "don't chase" in s
    assert "SELF-CHECK" not in _lines("Is TCS a good buy?")


# ------------------------------------------------------------------------------------------------------------------------------ plain words
def test_plain_words_fix_the_fund_name_and_the_stamp():
    assert W.words("Buy a flexi-cap index fund for the long run.", known={}) == "Buy a Nifty 500 index fund for the long run."
    assert W.words("It bounced. Decision: wait for a pullback.", known={}) == "It bounced. Wait for a pullback."
    assert W.words("The decision: hold", known={}) == "The decision: hold"                     # only a sentence-start label goes


def test_decision_answer_owns_up_to_a_chase_pick(tmp_path, monkeypatch):
    from jarvis.india import ask as A
    from tests.test_india_review_fixes import RM
    d = tmp_path / "paper" / "decisions"
    d.mkdir(parents=True)
    (d / "2026-10-26.json").write_text(json.dumps({"data_through": "2026-10-26", "journal": [
        {"symbol": "AAA", "status": "chosen", "rsi14": 72.4, "dist_sma50": 0.15}, {"symbol": "BBB", "status": "chosen", "rsi14": 40.0}]}))
    monkeypatch.setattr(G, "DATA", tmp_path)
    monkeypatch.setattr(G, "_holidays", lambda: set())
    monkeypatch.setattr(A.views, "readmodel", lambda: RM)
    a = A.decide_flow("What did you decide for the next session, and why?")["answer"]
    assert "AAA was bought at RSI 72 (a 0-100 gauge; over 70 means stretched), 15% above its 50-day average" in a and "BBB was bought" not in a
