"""26 Oct, Madhav's India chat 10:50-11:17: 10 flags in 15 minutes. Each message below is his (or the room's) exact words from that chat."""
from jarvis.india import ask as A


def k(text):
    r = A.flag_intent(text)
    return r and r["kind"]


def test_remarks_and_refusals_are_not_flags():
    for t in ("That's the right shape. Flag 32 logged. And it offered to auto-write the detailed note rather than guessing. One line, correct. Question 9. "
              "If a stock in your book drops 15% in a day on no news, what's your move? Hold, trim, or exit?",
              "That's the right move. Flag 34 logged. Question 9 re-asked cleanly. Standing by for Ananta's answer.",
              "So Ananta, you are not answering the question 12. I don't need any information about the flagging now. Flag was done and I will fix "
              "this flagging issue in the backend. Now just answer me the question 12. Don't know about nothing about the flags.",
              "Ananta, you're not answering the question. You're again going back to the flagging conversations. I don't know.",
              "Tell it to Brock. Yeah, please. It belongs on flag 36, the rupee dollar note. That's the flag. Question 12 is still open.",
              "Is the answer wrong? Why did the call go wrong?", "Don't flag it, just answer."):
        assert A.flag_intent(t) is None, t


def test_research_requests_become_notes():
    for t in ("So I will tell you Ananta to flag this. We have to do research about this FIL and their influence on the stock prices as well. "
              "So flag it and don't give me any fixes here.",
              "No, like, Ananta, now you have to flag this issue that like we will be in the back end, we will be looking for dollar and rupee "
              "influence on the stock market as well. Flag it. Flag it.",
              "So done. You just need to flag the issue that FII needs to be researched. So I can go there and look at it in the back end.",
              "note this for research: moving average crossovers on Nifty"):
        assert k(t) == "research", t
    assert k("No, that's not how I want. I just want you to keep a detailed note on the issue. The issue is cross-crossover.") in ("research", "note")


def test_app_problems_stay_flags():
    assert k("Flag it as a UI issue. The flagging flow should accept a detailed note without forcing a fix or investigate choice.") == "bug"
    assert k("The voice button is not working on the Home screen, flag it") == "bug"
    assert A.flag_intent("Is the options line not working today?") is None          # a question, answered


def test_a_question_in_the_same_message_is_kept():
    q = A.other_question("Yes, flag that. Question 12 is still open. If FII flows turn sharply negative, what's your first move? Cut stocks, add cash or something else?")
    assert "FII flows turn sharply negative" in q
    assert A.other_question("So done. You just need to flag the issue that FII needs to be researched.") == ""


def test_research_note_is_saved_without_a_menu(monkeypatch, tmp_path):
    monkeypatch.setattr(A, "ASK_DIR", tmp_path)
    monkeypatch.setattr(A, "write_note", lambda text, thread, post=None: {"title": "FII flows and Nifty returns", "note": "QUESTION\n...", "by": "model"})
    sent = {}

    def post(url, body):
        sent.update(body)
        return {"num": 140, "label": "note 59", "noted": True}
    r = A.fix_flow("So flag it. We have to do research about FII influence on stock prices. No fixes.", "t1", "tok", {}, post=post, get=lambda u: {})
    assert sent.get("note") and "Fixes" not in r["answer"] and "Noted for research" in r["answer"]
    r2 = A.fix_flow("Flag this for research: rupee against dollar. Question 12: if FII flows turn sharply negative, what's your first move?", "t1", "tok", {},
                    post=post, get=lambda u: {})
    assert r2.get("_then") and "FII flows" in r2["_then"] and r2["_prefix"].startswith("Noted for research")


def test_garbled_recording_is_not_answered():
    assert A.garbled_flow(", ".join(["Nifty"] * 70))["answer"].startswith("Sorry sir, that recording")
    assert A.garbled_flow("What is the Nifty trend today and should I worry about it?") is None


def test_guardrails_and_the_whole_regime_table_are_in_the_facts():
    g = A.guardrail_facts({"guardrails": {"words": "w"}})
    assert "every position is closed" in (g.get("daily_5pct") or "") and "Madhav resumes" in (g.get("pause_22pct") or "")
    a = A.allocation_rule_facts()
    assert set(a["regime_table"]) == {"above_both", "mixed", "below_both"} and a["band_frac"] == 0.03 and a["max_shift_frac_per_move"] == 0.1
