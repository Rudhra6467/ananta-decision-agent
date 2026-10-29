"""Madhav, 27 Oct: (1) answers short and in plain words by default, longer only when he asks ("When asked to explain more, we can add the
necessary details by also making sure we are converting the database language to human language"); (2) who is speaking: "I will ask Ananta
here to talk to a grader ... Ananta should understand when it's me. Even sometimes when I say Ananta it's me, it won't recognise me well"."""
from __future__ import annotations

import json

import pytest

from jarvis.india import ask as ia, askwords, speaker, views


@pytest.fixture
def lake(tmp_path, monkeypatch):
    rm = tmp_path / "readmodel"
    rm.mkdir()
    (tmp_path / "registrations").mkdir()
    (rm / "latest.json").write_text(json.dumps({"rules": "readmodel-v0", "data_through": "2026-10-27", "market": {"status": "ok", "nifty_close": 22749.75},
                                                 "stock_book": {"status": "ok", "open_positions": 72, "by_campaign": {}}, "brief": ["Nifty 22,750."], "missing": []}))
    monkeypatch.setattr(views, "DATA", tmp_path)
    monkeypatch.setattr(views, "REG", tmp_path / "registrations")
    monkeypatch.setattr(ia, "ASK_DIR", tmp_path / "ask")
    monkeypatch.setattr(ia, "ENV_FILE", tmp_path / "no.env")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    monkeypatch.setenv("PEOPLE_FILE", str(tmp_path / "people.json"))
    (tmp_path / "people.json").write_text(json.dumps({"people": [
        {"id": "mom", "names": ["Radha", "Amma"], "relations": ["mom", "my mom", "mother", "amma"], "group": "family", "language": "telugu",
         "call": "Amma garu", "relation": "Madhav's mother", "style": "gentle and respectful", "opener": "Namaskaram Amma garu! Nenu Ananta ni. Meeru ela unnaru?"}]}))
    monkeypatch.setattr(ia, "views", views)
    return tmp_path


class Model:
    """A stand-in for the model: records each message it is sent and answers with the given text."""

    def __init__(self):
        self.sent, self.answer = [], "RSI is a 0-100 gauge of recent rises against falls, sir."

    def __call__(self, url, headers, body):
        self.sent.append(body["messages"][-1]["content"])
        return {"content": [{"type": "text", "text": json.dumps({"kind": "answer", "answer": self.answer, "breakdown": [], "evidence": ["XO1"], "follow_ups": []})}],
                "usage": {"input_tokens": 10, "output_tokens": 10}}


# ---------------------------------------------------------------------------------------------------------------- plain words

def test_codes_and_field_names_become_words():
    k = {"TWT-H22": "A 7% stop loss"}
    out = askwords.words("A -7% stop lost against no stop (TWT-H22); the verdict is OPPOSITE; MACD was REJECTED (study XO1, 2000-2023); "
                         "it bought at decision point D3 with ATRSTOP for +48.4 bp, -1.05R; wrong_if and suggest_inr; teacher card TWT-H22 says so.", k)
    assert askwords.leaks(out) == [], out
    assert "(2000-2023)" in out and "the 10:15 decision" in out and "a stop at the usual daily swing" in out and "+0.48%" in out
    assert "times the risk taken" in out and "did not hold" in out and "the 'wrong if' line" in out and "stocks teacher" in out
    assert askwords.words(out, k) == out                                          # idempotent


def test_finish_puts_every_answer_into_words():
    r = ia.finish({"answer": "Sir, TS1 found trailing stops OPPOSITE and hold_20d trades lost.", "breakdown": ["XO1: REJECTED"], "follow_ups": ["Is GP1 tested?"]},
                  "q", model=True)
    assert askwords.leaks(r["answer"]) == [] and askwords.leaks(r["breakdown"][0]) == [] and askwords.leaks(r["follow_ups"][0]) == []
    assert "trailing-stop test" in r["answer"]


def test_short_by_default_and_expand_on_request(lake):
    m = Model()
    r = ia.ask("owner", "What is RSI?", post=m)
    assert "SHORT MODE: 2-4 short sentences" in m.sent[-1] and "EXPAND" not in m.sent[-1]
    assert r["talking_to"] == {"name": "Madhav", "role": "owner"}
    for ask_more in ("Explain more.", "okay, tell me more", "Why?", "go deeper", "can you break it down"):
        ia.ask("owner", ask_more, thread=r["thread"], post=m)
        assert "EXPAND: he asked for more on your previous answer" in m.sent[-1] and "0-100 gauge" in m.sent[-1], ask_more
    ia.ask("owner", "Why did the Nifty fall today?", thread=r["thread"], post=m)        # a new question, not "more"
    assert "SHORT MODE" in m.sent[-1]
    assert ("SHORT AND PLAIN" in ia.SYSTEM or "Short and plain" in ia.SYSTEM) and ("no study or card codes" in ia.SYSTEM or "No study or card codes" in ia.SYSTEM)


# ---------------------------------------------------------------------------------------------------------------- who is speaking

def test_grader_handover_book_question_refused_yes_and_madhav_back(lake):
    m = Model()
    r = ia.ask("owner", "Ananta, talk to the grader.", post=m)
    th = r["thread"]
    assert r["answer"].startswith("Hello, grader.") and r["talking_to"]["role"] == "observer" and not m.sent        # instant, no model call
    m.answer = "Sir, the practice book has closed 29 trades and none won."
    r = ia.ask("owner", "Grader here: how is the practice book doing?", thread=th, post=m)
    assert "TALKING TO: you are now talking with the grader" in m.sent[-1] and "sir" not in r["answer"].lower()[:6]
    n = len(m.sent)
    r = ia.ask("owner", "Yes to all your recommendations.", thread=th, post=m)
    assert "needs Madhav's yes" in r["answer"] and "it's me" in r["answer"] and len(m.sent) == n and speaker.current(th)
    m.answer = "RSI is a 0-100 gauge of recent rises against falls, sir."
    r = ia.ask("owner", "Uh, Ananta, it's, it's me again. What is RSI?", thread=th, post=m)
    assert r["answer"].startswith("Welcome back, sir.") and "0-100 gauge" in r["answer"] and speaker.current(th) is None
    assert m.sent[-1].startswith("QUESTION: What is RSI?") and "TALKING TO" not in m.sent[-1]
    assert r["talking_to"]["name"] == "Madhav"


@pytest.mark.parametrize("back", ["it's me", "Ananta it's me", "ananta its me", "Madhav here", "this is Madhav", "I'm back", "Madhav again",
                                  "it's Vamsi", "thanks, I'll take it from here", "okay Ananta, back to me", "grader is done", "uh, Ananta, it's, it's me",
                                  "IT'S ME", "hey ananta, madhav here"])
def test_every_way_madhav_comes_back(lake, back):
    th = "t-" + str(abs(hash(back)))
    speaker.set_guest(th, {"id": "grader", "name": "the grader", "role": "observer", "call": "grader"})
    r = ia.ask("owner", back, thread=th, post=Model())
    assert r["answer"].startswith("Welcome back, sir.") and speaker.current(th) is None, back


def test_back_and_forth_twice_and_mom_keeps_family_style(lake):
    m = Model()
    r = ia.ask("owner", "Ananta, talk to the grader.", post=m)
    th = r["thread"]
    ia.ask("owner", "Madhav here", thread=th, post=m)
    assert speaker.current(th) is None
    r = ia.ask("owner", "My mom is here, say hi to her.", thread=th, post=m)
    assert r["answer"].startswith("Namaskaram Amma garu") and speaker.current(th)["role"] == "family"
    m.answer = "Sir, Nifty closed at 22,750."
    r = ia.ask("owner", "Nifty ela undi?", thread=th, post=m)
    assert "Telugu" in m.sent[-1] and "Amma garu" in m.sent[-1] and not r["answer"].lower().startswith("sir")
    r = ia.ask("owner", "Ananta it's me, how many trades are open?", thread=th, post=m)
    assert r["answer"].startswith("Welcome back, sir.") and speaker.current(th) is None and m.sent[-1].startswith("QUESTION: how many trades are open?")
    ia.ask("owner", "I'm handing you to the grader", thread=th, post=m)
    assert speaker.current(th)["id"] == "grader"
    ia.ask("owner", "it's me", thread=th, post=m)
    assert speaker.current(th) is None


def test_no_false_handovers_or_returns(lake):
    for t in ("This is a bad answer.", "TATAPOWER is here in the list?", "Ananta, talk to me about RSI", "Is it Madhav's account?",
              "Who is here?", "Speak to the market mood please"):
        assert speaker.route("t-none", t) is None, t
    assert speaker.route("t-none", "Ananta, it's me")["kind"] == "back"                 # a bare 'it's me' with nobody else here: "Yes, sir"


def test_a_guest_cannot_flag_and_unclear_owner_talk_is_asked(lake):
    th = "t-mom"
    speaker.set_guest(th, {"id": "mom", "name": "Radha", "role": "family", "call": "Amma garu"})
    r = ia.ask("owner", "flag this: the chart is broken", thread=th, post=Model())
    assert "needs Madhav's yes" in r["answer"]
    r = ia.ask("owner", "what is happening with my account", thread=th, post=Model())
    assert r["answer"].startswith("Who am I speaking with?")


def test_last_shows_who_ananta_is_talking_to(lake):
    r = ia.ask("owner", "Ananta, talk to the grader.", post=Model())
    assert ia.last()["last"]["talking_to"] == "the grader"


def test_welcome_back_is_said_once_and_definitions_go_to_the_model():
    """27 Oct live check: "Welcome back, sir. Sir, as of ..." and "What is RSI?" answered with the Nifty's RSI reading instead of the meaning."""
    assert ia.with_welcome("Welcome back, sir.", "Sir, as of the close RSI is 46.") == "Welcome back, sir. As of the close RSI is 46."
    from jarvis.india import technicals
    assert technicals.DEFINE_Q.search("What is RSI?") and technicals.DEFINE_Q.search("what is a golden cross and what does it signal?")
    assert not technicals.DEFINE_Q.search("What is Nifty's RSI?") and not technicals.DEFINE_Q.search("Has the 50-day crossed the 200-day on Nifty?")
    assert askwords.words("Tested: RSI(14) over 70 when bought (validated).") == "Tested: RSI over 70 when bought (held up)."
