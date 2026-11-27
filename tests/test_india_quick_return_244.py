"""Flag 244 (the replay's today check, night of 23 Nov): "I want to invest 1L INR after market opens tomorrow and want to generate a profit of
30k in 2weeks what stocks do I invest in" was answered with the rupee's exchange rate. "INR" in an amount of money is not a question about the
rupee, and a money target in a short time gets the honest answer first (answer_guide's HONEST FIRST line), never stock picks for the target."""
import pytest

from jarvis.india import answerguide as G
from jarvis.india import marketcontext as M

Q = "I want to invest 1L INR after market opens tomorrow and want to generate a profit of 30k in 2weeks what stocks do I invest in"
Q1 = "I wan to invest 1L INR and want to make 30k profit on it in the next two weeks, give me suggestions"


@pytest.fixture
def mc_ok(monkeypatch):
    """A market summary the flow could answer from, so a None below is the flow declining, not missing data."""
    monkeypatch.setattr(M.views, "readmodel", lambda: {})
    monkeypatch.setattr(M, "_mc", lambda rm: {"status": "ok", "rupee_same_day": {"status": "ok", "as_of": "2026-11-23", "value": 92.94,
                                                                                    "change_1": 0.3, "change_5": -1.1}, "macro": {}})


def test_the_exact_question_is_not_a_rupee_reading(mc_ok):
    assert M.market_context_flow(Q) is None
    assert M.market_context_flow("Should I put 50000 rupees in Nifty?") is None
    assert M.market_context_flow("What stocks can I buy with Rs 20,000?") is None


def test_a_real_rupee_question_still_gets_the_reading(mc_ok, monkeypatch):
    monkeypatch.setattr(M, "_chg", lambda rs: "+0.3% on the day", raising=False)
    monkeypatch.setattr(M, "_line", lambda x, *a: "", raising=False)
    r = M.market_context_flow("How is the rupee today?")
    assert r is not None and "92.94" in str(r)
    assert M.market_context_flow("What is USD/INR now?") is not None


def test_the_honest_first_line_leads_the_guide():
    for q in (Q, Q1, "how to double my money in a month", "I want 20% return in 10 days, what should I buy?"):
        assert G.quick_return(q), q
        g = G.guide(q, {})
        assert g["lines"][0].startswith("HONEST FIRST"), q
        assert "30%" in g["lines"][0] and "Name no stocks for the target, no exchange rate" in g["lines"][0]
        assert not any(x.startswith("CHANGE MY MIND") for x in g["lines"]), q


def test_ordinary_questions_get_no_honest_first_line():
    for q in ("What did the practice book make in 2 weeks?", "Start a SIP of 5k a month in an index fund?", "How is the Nifty doing?",
              "Should I hold TCS for 5 years?", "What is the 30k-foot view of the market?"):
        assert not any(x.startswith("HONEST FIRST") for x in G.guide(q, {})["lines"]), q
