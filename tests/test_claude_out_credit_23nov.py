"""23 Nov 2026 (morning review): with the Anthropic credit gone, the Ask said "ask me again in a few minutes", which was untrue."""
from jarvis.service import ask


def _planned_used():
    planned = next(k for k, v in ask.MODELS.items() if v["provider"] == "claude")
    used = next(k for k, v in ask.MODELS.items() if v["provider"] != "claude")
    return planned, used


def test_no_credit_says_so_and_where_it_is_topped_up():
    planned, used = _planned_used()
    r = {"answer": ""}
    note = "no Anthropic credit left (RuntimeError after 0 s); there is no backup model, so no other model was asked"
    assert ask.claude_is_out(r, planned, used, note) is True
    assert r["answer"] == ask.CLAUDE_OUT_CREDIT + " Nothing was saved or done."
    assert "few minutes" not in r["answer"] and "Plans & Billing" in r["answer"]


def test_a_visitor_is_not_told_about_billing():
    planned, used = _planned_used()
    r = {"answer": ""}
    assert ask.claude_is_out(r, planned, used, "no Anthropic credit left (RuntimeError after 0 s)", guest=True) is True
    assert r["answer"].startswith(ask.CLAUDE_OUT_LATER) and "Billing" not in r["answer"] and "credit" not in r["answer"]


def test_other_outages_keep_their_words():
    planned, used = _planned_used()
    r = {"answer": ""}
    assert ask.claude_is_out(r, planned, used, "Claude is unavailable right now (APIStatusError 529 after 3 s)") is True
    assert r["answer"] == ask.CLAUDE_OUT + " Nothing was saved or done."
    for said in (ask.CLAUDE_OUT_CREDIT, ask.CLAUDE_OUT_LATER):
        assert said.startswith("I can't answer that right now: ")
