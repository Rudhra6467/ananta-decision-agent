"""9 Nov 2026 (the outsider round): Claude's silence is said plainly; one record for the options line; spoken self-check items; a compound
question is not answered by the waiting rule alone."""
from __future__ import annotations

import json

from jarvis import selfcheck
from jarvis.india import ask, surfaces


def test_a_refused_call_is_said_first_in_plain_words():
    f = {"brief": ["Through 2026-11-06: Nifty 25,030."], "today_live": {"clock": {"words": "It is Monday 9 Nov, 23:20 in India."},
                                                                        "index_now": {"words": "Monday 9 Nov, at today's close: Nifty 25,044.65."}}}
    r = ask._offline("how did today go", f, "Your credit balance is too low to access the Anthropic API.")
    assert r["answer"].startswith("Sir, I can't think through your question right now: Claude's API credit has run out")
    assert "Nifty 25,044.65" in r["answer"] and "25,030" not in r["answer"] and "read model only" in r["note"]
    r2 = ask._offline("x", {"brief": ["Through 6 Nov."]}, "Overloaded")
    assert r2["answer"].startswith("Sir, Claude is busy right now") and "Through 6 Nov." in r2["answer"]


def test_a_question_that_asks_more_than_waiting_goes_to_the_model():
    assert ask.waiting_flow("what's running right now, what changed, and what do you need from me", {"items": []}) is None
    assert ask.waiting_flow("what is waiting for my yes?", {"items": []})["answer"].startswith("Nothing is waiting")


def test_the_options_line_has_one_record(tmp_path, monkeypatch):
    monkeypatch.setattr(surfaces, "DATA", tmp_path)
    (tmp_path / "paper" / "sp1").mkdir(parents=True)
    (tmp_path / "paper" / "sp1" / "book.json").write_text(json.dumps({"updated": "2026-11-09T17:30:07+05:30", "sessions": 11, "by_index": {
        "NIFTY": {"trades": 2, "option_1lot_rs_realistic_fill": 12406.0}, "BANKNIFTY": {"trades": 10, "option_1lot_rs_realistic_fill": -5252.0}}}))
    cl = [{"name": "the options line", "done": 10, "so_far": "BANKNIFTY ... Rs 802"}, {"name": "the shadow trader", "done": 7, "so_far": "x"}]
    surfaces._sp1_clock(cl)
    assert cl[0]["done"] == 11 and "Bank Nifty: 10 trades, −₹5,252" in cl[0]["so_far"] and "802" not in cl[0]["so_far"] and cl[1]["done"] == 7


def test_self_check_items_are_said_to_him():
    s = selfcheck.spoken("the card of 6 Nov says 1 draft waits for Madhav's yes; planned: Madhav said about 1 h; Brain: did too little")
    assert "Madhav" not in s and "your yes" in s and "you said about 1 h" in s and "the crypto brain:" in s
