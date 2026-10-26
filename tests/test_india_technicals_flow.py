"""The India technicals panel in Ask (jarvis/india/technicals.py; Madhav, 26 Oct: "moving-average crossovers ... RSI, MACD, support and
resistance, and volume ... it can't say whether a crossover has actually happened"): answered in code from the read model, with the as-of
date, nothing intraday, and whether the indicator was ever tested."""
import pytest

from jarvis.india import technicals, views

NIFTY = {"name": "NIFTY 50", "kind": "index", "status": "ok", "as_of": "2026-10-23", "close": 22600.0, "change_1d": -0.0039,
         "sma": {"20": 23000.0, "50": 23404.0, "200": 24119.0}, "vs_sma": {"20": -0.017, "50": -0.034, "200": -0.063},
         "cross_50_200": {"state": "below", "last_cross": None, "direction": None, "sessions_ago": None, "searched_from": "2026-05-20", "name": None},
         "cross_20_50": {"state": "below", "last_cross": "2026-09-07", "direction": "down", "sessions_ago": 34},
         "rsi14": 42.1, "rsi_zone": "neutral, leaning weak",
         "macd": {"line": -169.5, "signal": -222.6, "hist": 53.1, "state": "above", "last_signal_cross": "2026-10-13", "cross_direction": "up", "sessions_ago": 8},
         "high_52w": 26329.0, "low_52w": 22232.0, "vs_high_52w": -0.142, "vs_low_52w": 0.017,
         "support": {"swing_low": 22232.0, "swing_low_date": "2026-10-01", "round": 22500}, "resistance": {"swing_high": 23447.0, "swing_high_date": "2026-10-15", "round": 23000},
         "sr_basis": "daily highs and lows", "volume": {"note": "not available for an index (its volume is 0)"}, "words": "NIFTY 50 closed at 22,600.00 on Fri 23 Oct."}
BANK = {**NIFTY, "name": "NIFTY BANK", "close": 54287.35,
        "cross_50_200": {"state": "below", "last_cross": "2026-09-22", "direction": "down", "sessions_ago": 21, "searched_from": "2026-05-20", "name": "death cross"}}
JIOFIN = {**NIFTY, "name": "JIOFIN", "kind": "stock", "role": "holding", "close": 300.0, "volume": {"last": 19149171, "avg20": 13660005, "ratio": 1.40},
          "support": {"swing_low": None, "swing_low_date": None, "round": 290}, "resistance": {"swing_high": 320.0, "swing_high_date": "2026-10-10", "round": 310},
          "cross_50_200": {"state": "above", "last_cross": "2026-07-15", "direction": "up", "sessions_ago": 70, "searched_from": "2026-05-20", "name": "golden cross"}}
IDEA = {**JIOFIN, "name": "IDEA", "close": 9.0}
TATAPOWER = {**JIOFIN, "name": "TATAPOWER", "close": 348.1, "support": {"swing_low": 347.0, "swing_low_date": "2026-08-31", "round": 340}}
KNOW = {"status": "ok", "families": {
    "moving averages and crossovers": {"tested": [{"what": "bought more than 20% above the 50-day average", "verdict": "VALIDATED", "words": "bought more than 20% above the 50-day average: trades earned less: VALIDATED"}],
                                       "not_tested": "a moving-average crossover study (20/50, 50/200) is study XO1 (being tested: no ledger row yet)"},
    "RSI and stochastic": {"tested": [{"what": "RSI(14) over 70 when bought", "verdict": "VALIDATED", "words": "RSI(14) over 70 when bought: trades earned less: VALIDATED"}], "not_tested": None},
    "MACD": {"tested": [], "not_tested": "no MACD test has been registered yet"},
    "volume": {"tested": [{"what": "volume over 2x its average", "verdict": "INCONCLUSIVE", "words": "volume over 2x its average: INCONCLUSIVE"}], "not_tested": None},
    "support and resistance": {"tested": [{"what": "selling below the last 5-session swing low", "verdict": "REJECTED", "words": "swing-low exit: REJECTED"}],
                               "not_tested": "support and resistance as an ENTRY signal has not been tested"}}}
RM = {"technicals": {"status": "ok", "as_of": "2026-10-23", "basis": "daily closes", "indices": {"NIFTY 50": NIFTY, "NIFTY BANK": BANK},
                     "stocks": {"JIOFIN": JIOFIN, "IDEA": IDEA, "TATAPOWER": TATAPOWER}}, "indicator_knowledge": KNOW}


@pytest.fixture
def rm(monkeypatch):
    monkeypatch.setattr(views, "readmodel", lambda: RM)
    return RM


def _a(q):
    r = technicals.technicals_flow(q)
    return r["answer"] if r else None


def test_crossover_question_says_no_cross_since_window_start_and_untested(rm):
    r = technicals.technicals_flow("has the 50-day crossed the 200-day on Nifty?")
    assert r["kind"] == "answer" and r["route"] == "india" and set(r) >= {"answer", "follow_ups", "evidence", "ui", "points"}
    a = r["answer"]
    assert "Fri 23 Oct close" in a and "nothing intraday" in a
    assert "below the 200-day" in a and "since at least Wed 20 May" in a and "no golden cross since" in a
    assert "XO1" in a and "not a buy or sell signal" in a


def test_bank_nifty_death_cross_date_and_not_nifty_too(rm):
    a = _a("golden cross on bank nifty?")
    assert "NIFTY BANK" in a and "Tue 22 Sep, 21 sessions ago" in a and "death cross" in a
    assert "NIFTY 50" not in a


def test_rsi_macd_support_volume(rm):
    assert "RSI(14) is 42" in _a("what's Nifty's RSI?") and "(validated)" in _a("what's Nifty's RSI?")
    m = _a("what does MACD say for nifty")
    assert "above it since Tue 13 Oct" in m and "never tested" in m
    s = _a("where is support for Tata Power?")
    assert "TATAPOWER" in s and "support near 347" in s and "ENTRY signal has not been tested" in s
    v = _a("is volume high on JIOFIN?")
    assert "1.4 times its 20-day average" in v and "crore shares" in v
    assert "not available for an index" in _a("what's the volume on nifty?")
    j = _a("where is support for jiofin")
    assert "no swing low under the close" in j and "290" in j


def test_tested_questions_answer_from_the_registry(rm):
    assert "RSI(14) over 70 when bought: trades earned less: VALIDATED" in _a("has RSI ever been tested?")
    assert "never tested" in _a("is MACD tested?")


def test_what_it_leaves_to_the_model_or_other_flows(rm):
    for q in ("research the golden cross for me", "flag this: add MACD to the panel", "should I buy JIOFIN on this RSI?", "what's the weather",
              "what indicators do you use?", "why did Nifty cross below the 50-day?", "x" * 250 + " rsi"):
        assert technicals.technicals_flow(q) is None, q


def test_word_symbols_only_in_capitals(rm):
    assert "IDEA" not in (_a("any idea what Nifty's RSI is?") or "")
    assert "IDEA's RSI(14)" in _a("what is the RSI on IDEA?")


def test_missing_panel_hands_off(monkeypatch):
    monkeypatch.setattr(views, "readmodel", lambda: {"technicals": {"status": "unavailable"}})
    assert technicals.technicals_flow("what's Nifty's RSI?") is None
    assert "never read an indicator from memory" in technicals.facts_part({"technicals": {"status": "unavailable"}})["how_to_say_it"]


def test_facts_part_is_compact_and_says_how_to_speak(rm):
    f = technicals.facts_part(RM)
    assert f["as_of"] == "2026-10-23" and set(f["indices"]) == {"NIFTY 50", "NIFTY BANK"}
    assert set(f["holdings"]) == {"JIOFIN", "IDEA", "TATAPOWER"} and f["picks"] == {}
    assert f["indices"]["NIFTY 50"]["cross_50_200"]["searched_from"] == "2026-05-20"
    assert "nothing is intraday" in f["how_to_say_it"] and "MACD" in f["indicator_knowledge"]


def test_two_indicators_in_one_question_are_both_answered(rm):
    """26 Oct live check: "What's the RSI on Bank Nifty and where is its support?" answered only the RSI."""
    a = _a("What's the RSI on Bank Nifty and where is its support?")
    assert "NIFTY BANK's RSI(14)" in a and "support near 22,232" in a and "NIFTY 50" not in a
    assert "(validated)" in a and "ENTRY signal has not been tested" in a


def test_a_study_headline_is_said_first(monkeypatch):
    """Once XO1 is in the ledger the read model carries its headline: the short answer says it, the tested answer gives it in full."""
    head = ("Tested 26 Oct (study XO1, 2000-2023): no moving-average crossover is a usable buy or sell signal. On liquid-250 stocks the golden cross "
            "was followed by about 2.7% WORSE returns over 60 sessions.")
    know = {"status": "ok", "families": {**KNOW["families"],
            "moving averages and crossovers": {**KNOW["families"]["moving averages and crossovers"], "not_tested": None, "headline": head,
                                               "tested": KNOW["families"]["moving averages and crossovers"]["tested"]
                                               + [{"what": "study XO1", "study": "XO1", "verdict": {"OPPOSITE": 3}, "words": "study XO1 (27 versions): 3 OPPOSITE"}]},
            "MACD": {"tested": [{"what": "study XO1", "study": "XO1", "verdict": {"REJECTED": 4}, "words": "study XO1 (6 versions): 4 REJECTED"}], "not_tested": None,
                     "headline": "Tested 26 Oct (study XO1): MACD crossing its signal line is not a usable signal."}}}
    monkeypatch.setattr(views, "readmodel", lambda: {**RM, "indicator_knowledge": know})
    a = _a("has the 50-day crossed the 200-day on Nifty?")
    assert "no moving-average crossover is a usable buy or sell signal." in a and "2.7% WORSE" not in a and "being tested" not in a
    full = _a("does the golden cross work?")
    assert "2.7% WORSE" in full and "Other tests: bought more than 20% above the 50-day average" in full and "study XO1 (27" not in full
    assert "not a usable signal" in _a("is MACD tested?")
    f = technicals.facts_part({**RM, "indicator_knowledge": know})["indicator_knowledge"]
    assert f["MACD"]["tested_study"].startswith("Tested 26 Oct") and f["RSI and stochastic"]["tested_study"] is None
