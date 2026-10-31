"""27 Oct (Madhav, after the 25-question session): "it can't tell the difference between what it knows and what it has data for" (the
'general market knowledge, not from my data files' label on 17 of 25 answers; NSE vs BSE refused) and "it describes positions but doesn't
decide". The SYSTEM prompt's three kinds of answer and the decide-shape; the technicals flow no longer answers a stock it has no panel for."""
import pytest

from jarvis.india import ask, technicals, views


def test_system_has_three_kinds_and_forbids_the_label():
    s = ask.SYSTEM_V1                                           # 29 Oct: the old text, kept for ASK_PROMPT=v1 (askprompt.py has the live one)
    assert "THREE KINDS OF ANSWER" in s and "TEXTBOOK MARKET KNOWLEDGE" in s and "LIVE NUMBERS" in s and "DOES IT WORK" in s
    assert 'Do NOT label it "general knowledge"' in s and "not from my data files" in s      # named only as what not to say
    assert "never refuse a basic question" in s and "NSE is far larger by volume" in s
    assert "Ananta hasn't tested this" in s and "as far as I know" in s
    assert "If the facts do not hold the answer, say so plainly" not in s                     # the old line that made it refuse textbook questions


def test_system_has_the_decide_shape_and_hypotheticals():
    s = ask.SYSTEM_V1                                           # 29 Oct: the old text, kept for ASK_PROMPT=v1 (askprompt.py has the live one)
    assert "WHEN HE ASKS FOR A READ OR A DECISION" in s and "always decide" in s
    for part in ("your read in one sentence", "hold, trim, add, exit or wait", "what would change your mind", "tested, untested or against the tests",
                 "End on what to do", "HYPOTHETICAL", "Never stop at describing a position"):
        assert part in s, part
    assert 'never a "Decision:" label' in s                     # 27 Oct second review: decide in plain words, no stamp
    assert "TS1" in s and "TWT-H22" in s and "TWT-H15" in s and "wrong_if" in s


NIFTY = {"name": "NIFTY 50", "kind": "index", "status": "ok", "as_of": "2026-10-26", "close": 22753.2, "change_1d": 0.0068,
         "sma": {"20": 22700.0, "50": 23360.0, "200": 24100.0}, "vs_sma": {"20": 0.002, "50": -0.026, "200": -0.056},
         "cross_50_200": {"state": "below", "last_cross": "2026-03-16", "direction": "down", "sessions_ago": 150, "searched_from": "2026-05-20"},
         "cross_20_50": {"state": "below", "last_cross": "2026-09-07", "direction": "down", "sessions_ago": 35}, "rsi14": 46.0, "rsi_zone": "neutral",
         "macd": {"line": 1.0, "signal": 0.5, "hist": 0.5, "state": "above", "last_signal_cross": "2026-10-13"},
         "high_52w": 26329.0, "low_52w": 22232.0, "vs_high_52w": -0.136, "vs_low_52w": 0.023,
         "support": {"swing_low": 22232.0, "swing_low_date": "2026-10-08", "round": 22500}, "resistance": {"swing_high": 23146.0, "swing_high_date": "2026-10-16", "round": 23000},
         "volume": {"note": "not available"}, "words": "NIFTY 50 closed at 22,753.20."}
JIOFIN = {**NIFTY, "name": "JIOFIN", "kind": "stock", "close": 300.0, "volume": {"last": 1, "avg20": 1, "ratio": 1.0}}
FAM = {"candlestick patterns": {"tested": [], "not_tested": None, "headline": "Tested 27 Oct (study CP1): no candlestick pattern is a usable signal."}}
RM = {"technicals": {"status": "ok", "as_of": "2026-10-26", "indices": {"NIFTY 50": NIFTY}, "stocks": {"JIOFIN": JIOFIN}},
      "indicator_knowledge": {"status": "ok", "families": FAM}}


@pytest.fixture
def rm(monkeypatch):
    monkeypatch.setattr(views, "readmodel", lambda: RM)
    return RM


def test_a_stock_without_a_panel_goes_to_the_model(rm):
    for q in ("Question 5. Ananta, TCS gapped up 4% after earnings. Is it too late to enter?",
              "TCS gapped up 4%, where is resistance?", "what's the RSI on Reliance?", "Where is support for INFY?",
              "Is it too late to enter JIOFIN?", "should I add on this RSI?"):
        assert technicals.technicals_flow(q) is None, q


def test_plain_readings_still_answer(rm):
    assert "support near 22,232" in technicals.technicals_flow("where is support for Nifty?")["answer"]
    assert "JIOFIN" in technicals.technicals_flow("what is the RSI on JIOFIN?")["answer"]
    assert "NIFTY 50" in technicals.technicals_flow("what's the RSI?")["answer"]               # no other name: the Nifty by default
    assert technicals.technicals_flow("did the Nifty gap down?") is None                       # a gap is not a panel reading


def test_new_families_answer_only_was_it_tested(rm):
    a = technicals.technicals_flow("is a hammer candle tested?")
    assert a and "CP1" in a["answer"]
    assert technicals.technicals_flow("what is a hammer candle?") is None                      # a definition: the model answers
    assert technicals.technicals_flow("has the P/E ratio been tested?") is None                # no family yet in the read model: the model answers
    assert technicals.FAMILY_OF["valuation"] == "valuation (P/E, P/B)" and technicals.FAMILY_OF["corp"] == "corporate actions"
    assert technicals.FAMILY_OF["beta"] == "beta and volatility" and technicals.FAMILY_OF["spread"] == "option spreads"


def test_a_question_about_the_close_is_not_an_order():
    """27 Oct live check: "How did the Nifty close today?" got the paper-only order refusal."""
    import inspect, re
    from jarvis.india import ask as ia
    src = inspect.getsource(ia.ask)
    assert "asks = " in src and "not asks" in src
    assert ia.ACT.search("How did the Nifty close today?")          # the word matches, so the question test is what keeps it out
    asks = lambda t: "?" in t or re.match(r"\s*(how|what|where|when|why|did|does|do|is|are|was|were|which|who|tell me)\b", t, re.I)
    assert asks("How did the Nifty close today?") and not asks("buy it now") and not asks("sell TATAPOWER today please")


def test_v2_keeps_every_principle_in_one_place():
    """29 Oct: the slimmed instructions (jarvis/india/askprompt.py) still carry what the old patches taught, said once."""
    s = ask.SYSTEM_V2
    for part in ("Answer every part of the message", "Textbook knowledge", "never a refusal", "ONLY from the FACTS", "Ananta hasn't tested this",
                 "Match the horizon", "always decide", "I'd reverse this if", 'never a "Decision:" label', "hypothetical",
                 "PREDICTION question", "drafts_waiting_total.count", "value_inr", "SAFETY (unconditional)", "SEBI Check", "@valid UPI",
                 "seller of a call delivers", "booked in the same year", "lottery ticket", "PLAIN WORDS", "ORSTOP", "The grader",
                 "approve all drafts", "Move the app only when he asks", "kind\":\"clarify\"".replace("\\", "")):
        assert part.replace('\\"', '"') in s or part in s, part
    assert len(s.split()) < 0.75 * len(ask.SYSTEM_V1.split())


def test_a_promised_list_left_in_the_breakdown_is_spoken():
    """31 Oct (outsider r5): "here are five lines ..." with the lines only in `breakdown` spoke no list at all."""
    from jarvis.india import ask
    r = {"answer": "Sir, here are five lines to run down each morning, in the order the view is written.",
         "breakdown": ["1) Headline: the close and the trend.", "2) Odds: base rates only.", "3) Plan: the books' moves.", "4) Chances: the scorecard.", "5) Watch: expiry and levels."]}
    a = ask.finish(r, "Give me a daily checklist, five lines, for reading your morning view.", True)["answer"]
    assert "1) Headline" in a and "5) Watch" in a
    r = {"answer": "Sir, here is a five-line routine: 1) Read the headline. 2) Check the odds. 3) Read the plan. 4) Read the chances. 5) Finish with the watch list.", "breakdown": ["1) a", "2) b", "3) c"]}
    assert ask.finish(r, "checklist", True)["answer"].count("1)") == 1          # a list already in the answer is not doubled
