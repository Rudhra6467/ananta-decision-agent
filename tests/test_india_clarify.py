"""7 Nov 2026 (Madhav: "like ChatGPT ... only for some important questions and when it needs more information"): one clarifying question
with choices, in code, only where a wrong guess would cost something; his next message picks a choice and becomes the question."""
from __future__ import annotations

import time

import pytest

from jarvis.india import ask, clarify, views

DRAFTS2 = [{"n": 1, "key": "k1", "type": "exit study", "day": "2026-11-03", "words": "a faster exit after a gap down"},
           {"n": 2, "key": "k2", "type": "entry study", "day": "2026-11-05", "words": "buying the breakout of a tight base"}]


@pytest.fixture
def scratch(tmp_path, monkeypatch):
    monkeypatch.setattr(ask, "ASK_DIR", tmp_path / "ask")
    monkeypatch.setattr(ask, "DATA", tmp_path)
    monkeypatch.setattr(ask, "DRY_RUN", True)
    return tmp_path


def test_approve_it_with_two_drafts_asks_which_and_the_pick_becomes_the_question(scratch, monkeypatch):
    monkeypatch.setattr(views, "drafts", lambda: {"drafts": DRAFTS2})
    r = clarify.maybe("approve it", "t1")
    assert r and r["ask"]["kind"] == "clarify" and r["ask"]["options"] == ["draft 1: a faster exit after a gap down", "draft 2: buying the breakout of a tight base", "all of them"]
    assert clarify.pending("t1")["trigger"] == "approve"
    assert clarify.resolve("the second one", "t1") == "approve draft 2"
    assert clarify.pending("t1") is None                       # one round
    clarify.maybe("skip that one", "t1")
    assert clarify.resolve("all of them", "t1") == "skip all drafts"
    clarify.maybe("approve it", "t1")
    assert clarify.resolve("the tight base one", "t1") == "approve draft 2"      # the words of one choice
    clarify.maybe("approve it", "t1")
    assert clarify.resolve("how is the nifty?", "t1") is None and clarify.pending("t1") is None   # not an answer: the question is dropped


def test_one_draft_or_none_needs_no_question(scratch, monkeypatch):
    monkeypatch.setattr(views, "drafts", lambda: {"drafts": DRAFTS2[:1]})
    assert clarify.maybe("approve it", "t2") == {"resolved": "approve draft 1"}
    monkeypatch.setattr(views, "drafts", lambda: {"drafts": []})
    assert clarify.maybe("approve it", "t2") is None
    assert clarify.maybe("approve draft 2", "t2") is None and clarify.maybe("approve all drafts", "t2") is None


def test_the_book_with_no_name_asks_which_book(scratch):
    r = clarify.maybe("How is the book doing?", "t3")
    assert r and r["ask"]["kind"] == "clarify" and len(r["ask"]["options"]) == 4
    assert clarify.resolve("the managed book", "t3") == "How is the managed book doing?"       # a tapped chip sends its words
    clarify.maybe("how's the book?", "t3")
    assert clarify.resolve("2", "t3") == "How is the managed book doing?"
    clarify.maybe("how's the book?", "t3")
    assert clarify.resolve("options", "t3") == "How is the index options line doing?"
    for t in ("How is the research book doing?", "how is the managed book doing", "what is waiting for my yes?", "how is my account?"):
        assert clarify.maybe(t, "t4") is None, t


def test_flag_it_with_nothing_before_asks_what(scratch):
    r = clarify.maybe("flag it", "t5")
    assert r and r["ask"]["kind"] == "clarify" and r["ask"]["options"] == []
    assert clarify.resolve("the Nifty number on Today is yesterday's", "t5") == "flag this: the Nifty number on Today is yesterday's"
    clarify.maybe("flag it", "t5")
    assert clarify.resolve("what did we miss on Friday?", "t5") is None            # a question is not what to flag
    # with a message before it, the flag takes its subject from the conversation as before: no question
    ask._append("t6", {"role": "user", "text": "the Nifty number on Today is yesterday's", "t": int(time.time())})
    assert clarify.maybe("flag it", "t6") is None
    assert clarify.maybe("flag it", "t7", {"about": {"screen": "today"}}) is None  # the screen he is on is the subject


def test_an_old_question_is_forgotten(scratch):
    clarify.maybe("how is the book?", "t8")
    c = clarify.pending("t8")
    c["at"] = time.time() - clarify.PENDING_SECONDS - 1
    clarify.set_pending("t8", c)
    assert clarify.pending("t8") is None and clarify.resolve("2", "t8") is None


def test_the_ask_asks_and_then_approves_the_chosen_draft(scratch, monkeypatch):
    monkeypatch.setattr(views, "drafts", lambda: {"drafts": DRAFTS2})
    r = ask.ask("owner", "approve it", thread="t9")
    assert r["kind"] == "clarify" and "Which draft" in r["answer"] and "1. draft 1" in r["answer"] and r["options"][-1] == "all of them"
    r2 = ask.ask("owner", "the second one", thread="t9")
    assert r2["kind"] == "answer" and r2["answer"].startswith("Approved, sir: draft 2")
    assert (scratch / "ask" / "dry_decisions.jsonl").read_text().count('"APPROVED"') == 1


def test_the_facts_carry_the_count(scratch, monkeypatch):
    monkeypatch.setattr(ask, "DRY_RUN", False)
    clarify.maybe("how is the book?", "t10")
    clarify.resolve("1", "t10")
    s = clarify.summary()
    assert s["asked"] == 1 and s["answered"] == 1 and s["by_trigger"] == {"book": 1} and "asked which one Madhav meant 1 time" in s["words"]
    assert ask.facts(owner=True)["clarifying_questions"]["asked"] == 1
