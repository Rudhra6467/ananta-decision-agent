"""Madhav's 27 Oct afternoon session (chat 14:40, the grader's voice 16:36-17:17): the fixes, each from a real line of that session."""
import json
import re

import pytest

from jarvis.india import ask as ia, speaker, voiceid

OTHER = {"speaker": "not_madhav", "score": 0.1, "enrolled": True}
MAD = {"speaker": "madhav", "score": 0.85, "enrolled": True}
Q3 = ("Good. The mechanics are right and the intraday sell before delivery point is the practical detail most people miss. Question three, research "
      "knowledge. Ananta, you want to study whether a momentum strategy works on Nifty 50 stocks. Walk me through how you design that study so the "
      "result is trustworthy.")


@pytest.fixture
def lake(tmp_path, monkeypatch):
    monkeypatch.setattr(ia, "ASK_DIR", tmp_path / "ask")
    monkeypatch.setattr(speaker, "_path", lambda: tmp_path / "speakers.json")
    monkeypatch.setattr(ia, "facts", lambda owner=True: {"data_through": "2026-10-26"})
    seen = {"users": []}

    def fake(system, hist, user, post=None, max_tokens=3000):
        seen["users"].append(user)
        nums = re.findall(r"(?m)^(\d{1,2})\. ", user.split("FACTS")[0])
        if nums:
            return json.dumps({"answer": "\n".join(f"{n}. answer {n}." for n in nums)}), {"model": "fake", "in": 1, "out": 1}
        return json.dumps({"answer": "Sir, a plain answer."}), {"model": "fake", "in": 1, "out": 1}
    monkeypatch.setattr(ia, "_claude", fake)
    return seen


# 1. a word inside a quiz question or a remark is not an owner request
@pytest.mark.parametrize("t", [Q3, "HDFC Bank's RSI is 78. Is it overbought, and does that mean I should sell?", "Should I buy Reliance now?",
                               "A stock you hold is down 15% in two days. Do you sell, hold or add?", "How do you fix a strategy that keeps losing?",
                               "When should you trim a winner?", "My portfolio is up 12% this month, mostly in one stock. What do you think?"])
def test_quiz_words_are_not_owner_requests(t):
    assert not voiceid.needs_owner_check(t, OTHER, False)


@pytest.mark.parametrize("t", ["Yes to all your recommendations.", "Sell TATAPOWER for me now.", "flag this: the chart is broken", "Show me my holdings",
                               "use fix 2", "Approve it."])
def test_real_owner_requests_still_ask_who(t):
    assert voiceid.needs_owner_check(t, OTHER, False)


def test_the_exact_grader_question_is_answered_not_asked_who(lake):
    r = ia.ask("madhav", Q3, thread="g1", voice=True, context={"voice_id": OTHER})
    assert "Who am I speaking with" not in r["answer"]


# 2. the grader introduces itself, in Whisper's spellings too
@pytest.mark.parametrize("t", ["No, you're talking to the greater. Understood. I'm the greater and Ananta's the one.", "I'm the grader", "This is the grader.",
                               "you're talking with the examiner now", "Grader here."])
def test_self_introductions_set_the_observer(t, lake):
    r = speaker.route("x", t)
    assert r and r["kind"] == "handover" and r["person"]["role"] == "observer" and r.get("self_intro")


@pytest.mark.parametrize("t", ["A greater chance of loss", "What is a greater risk, futures or options?"])
def test_greater_as_an_english_word_is_not_a_person(t, lake):
    assert speaker.route("x", t) is None


def test_typed_intro_then_a_question_is_answered_to_the_grader(lake):
    r = ia.ask("madhav", "I'm the grader", thread="g2")
    assert r["answer"].startswith("Hello, grader") and r["talking_to"]["name"] == "the grader"
    r = ia.ask("madhav", "What is RSI?", thread="g2")
    assert not re.search(r"\bsir\b", r["answer"], re.I)
    r = ia.ask("madhav", "Grader here: how is the practice book doing?", thread="g3")     # intro and question in one message: answered
    assert speaker.current("g3")["id"] == "grader" and "Hello" not in r["answer"]


def test_madhavs_voice_saying_grader_words_is_still_madhav(lake):
    ia.ask("madhav", "I'm the grader", thread="g4", voice=True, context={"voice_id": MAD})
    assert speaker.current("g4") is None


def test_a_clearly_other_voice_is_not_called_sir_and_is_asked_once(lake):
    r1 = ia.ask("madhav", "What is MACD and when does it give false signals?", thread="g5", voice=True, context={"voice_id": OTHER})
    assert not re.search(r"\bsir\b", r1["answer"], re.I) and "grader?" not in r1["answer"]
    r2 = ia.ask("madhav", "What is a limit order versus a stop order?", thread="g5", voice=True, context={"voice_id": OTHER})
    assert r2["answer"].endswith("Am I speaking with the grader?")
    r3 = ia.ask("madhav", "What is beta?", thread="g5", voice=True, context={"voice_id": OTHER})
    assert "grader?" not in r3["answer"]                      # asked once only
    r4 = ia.ask("madhav", "Yes.", thread="g5", voice=True, context={"voice_id": OTHER})
    assert r4["answer"].startswith("Thank you, grader") and speaker.current("g5")["id"] == "grader"


# 3. long lists: 6 at a time; never an empty answer
def test_a_long_numbered_list_is_answered_six_at_a_time(lake):
    lst = "Your test\n" + "\n".join(f"{i}. What is question number {i} about?" for i in range(1, 13))
    r = ia.ask("madhav", lst, thread="b1")
    assert "1. answer 1." in r["answer"] and "6. answer 6." in r["answer"] and "7. answer" not in r["answer"]
    assert r["answer"].rstrip().endswith('Say "next" for 7 to 12.')
    r = ia.ask("madhav", "next", thread="b1")
    assert "7. answer 7." in r["answer"] and "12. answer 12." in r["answer"] and "Say \"next\"" not in r["answer"]


def test_an_empty_model_answer_is_retried_then_never_empty(lake, monkeypatch):
    calls = []

    def empty_then_good(system, hist, user, post=None, max_tokens=3000):
        calls.append(max_tokens)
        return (json.dumps({"answer": ""}) if len(calls) == 1 else json.dumps({"answer": "Sir, the short answer."})), {"model": "fake", "in": 1, "out": 3000}
    monkeypatch.setattr(ia, "_claude", empty_then_good)
    r = ia.ask("madhav", "What is T+1 settlement?", thread="e1")
    assert r["answer"] == "Sir, the short answer." and len(calls) == 2 and calls[1] >= 6000
    monkeypatch.setattr(ia, "_claude", lambda system, hist, user, post=None, max_tokens=3000: ("", {"model": "fake", "in": 1, "out": 3000}))
    r = ia.ask("madhav", "What is T+1 settlement?", thread="e2")
    assert r["answer"] == ia.EMPTY_FALLBACK


# 4. a bare "Flag it" files the message before it
def test_bare_flag_it_files_the_previous_message(lake):
    ia._append("f1", {"id": "u1", "role": "user", "text": "For the failed to load questions here in chat , we need to add a retry button . Only for failed ones", "t": 1})
    ia._append("f1", {"id": "a1", "role": "assistant", "answer": "Understood, sir.", "t": 2})
    sent = {}

    def post(url, body):
        sent.update(body)
        return {"num": 128, "label": "flag 47", "options": [{"title": "Add a retry button", "lane": "SAFE"}]}
    r = ia.fix_flow("Flag it", "f1", "tok", {}, post=post, get=lambda u: {})
    assert r and "Flagged as flag 47" in r["answer"] and "retry button" in sent["text"] and sent["market"] == "india"


# 6. 'today' uses the newest dated close
def test_latest_closes_prefer_the_newest_date():
    rm = {"data_through": "2026-10-26", "market": {"data_through": "2026-10-26", "nifty_close": 22753.2, "vix_close": 17.16,
                                                   "newer_closes": {"NIFTY 50": {"date": "2026-10-27", "close": 22749.75, "d1": -0.0002},
                                                                    "INDIA VIX": {"date": "2026-10-27", "close": 16.36, "d1": -0.047}}}}
    lc = ia.latest_closes(rm)
    assert lc["closes"]["NIFTY 50"] == {"date": "2026-10-27", "close": 22749.75, "change_1d": -0.0002, "source": "newer closes"}
    assert lc["newest_date"] == "2026-10-27" and "latest_closes" in ia.SYSTEM
