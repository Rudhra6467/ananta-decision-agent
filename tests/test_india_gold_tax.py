"""28 Oct outsider (third grading): pf6 gave one 12-month holding period while recommending a gold fund (24 months). The answer guide now carries
the holding period by instrument whenever gold comes up."""
import json

from jarvis.india import answerguide as g


def test_gold_questions_get_the_holding_period_by_instrument():
    for q in ("Should I invest in gold or the Nifty for the next 5 years?", "Is SBI Gold Fund Direct Plan Growth a good fund to hold?"):
        s = json.dumps(g.guide(q))
        assert "24 months" in s and "12 months" in s, q


def test_no_gold_line_elsewhere():
    assert "24 months" not in json.dumps(g.guide("What is RSI?"))
