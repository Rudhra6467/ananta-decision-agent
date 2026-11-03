"""Flags in voice (2 Nov 2026, from Madhav's chats of 1-2 Nov): "Flag them issue. We will work it on the back end." filed a flag about
nothing; "what's waiting" could not say the fixes ("I don't have the wording in front of me") and cut a line mid-word; the opener pushed two
crypto flags the morning review had already settled."""
from jarvis.india import ask

CHAT = [
    {"role": "user", "text": "We should know about the current session. We should not always be talking about the last closed session."},
    {"role": "assistant", "answer": "You're right, sir: that is a real gap. Right now I work only from daily closing data, with nothing intraday, so "
                                    "during the session I can't see where the Nifty is trading. A live feed would have to be built."},
]


def test_a_pointing_back_flag_takes_its_subject_from_the_conversation(monkeypatch):
    t = "Flag them issue. We will work it on the back end."
    assert ask._refers_back(t) and ask._refers_back("Yeah, flag it.") and ask._refers_back("please log this")
    assert not ask._refers_back("Flag that the managed book bought CIPLA twice on 2 Nov although its plan had one buy for LICI and the 2% rule")
    monkeypatch.setattr(ask, "thread_messages", lambda thread: CHAT)
    body = ask._subject_from_context("th", t)
    assert "current session" in body and "real gap" in body


W = {"count": 3, "key": "k", "line": "Flag 58, flag 59 and flag 60 are waiting for your yes.", "items": [
    {"kind": "flag_pick", "title": "Flag 58: pick a fix", "market": "crypto", "count": 1,
     "line": "[Crypto · officer] Officer check idle_cash failed: cash is 90% of the book against a 70% target, for 8 days",
     "fixes": ["Fix it as I described", "Investigate and tell me first", "Leave it as it is"],
     "review": {"words": "90% cash is the rules working. No change in the window.", "proposal": None, "settled": True}},
    {"kind": "flag_pick", "title": "Flag 59: pick a fix", "market": "crypto", "count": 1, "line": "[Crypto · reconstruction] 10 trades gave it back",
     "fixes": ["Fix it as I described"], "review": {"words": "The rule held; the card misleads. Proposal: count only trades that reached +1.5 R.",
                                                     "proposal": "count only trades that reached +1.5 R.", "settled": True}},
    {"kind": "flag_pick", "title": "Flag 60: pick a fix", "market": "india", "count": 1, "line": "[Indian market · Ananta tab] live session data",
     "fixes": ["Read the live session"], "review": None},
]}


def test_the_opener_skips_flags_the_review_settled():
    u = ask._unsettled(W)
    assert [x["title"] for x in u["items"]] == ["Flag 60: pick a fix"] and u["line"] == "Flag 60 is waiting for your yes."
    assert ask._unsettled({**W, "items": W["items"][:2]})["items"] == []


def test_whats_waiting_gives_one_recommendation_and_no_fix_menu():
    # 3 Nov (Madhav's chat and the outside grade): India first, crypto apart, one plain recommendation each, no fix menu, no commands
    r = ask.waiting_flow("What's waiting for my yes?", W)
    a = r["answer"]
    assert a.startswith("For the Indian market") and "my advice:" in a
    assert "The fixes:" not in a and "approve draft 2" not in a and "show my flags" not in a.lower()
    assert "On the crypto side, separately" in a and a.index("Indian market") < a.index("crypto side")


def test_asking_about_an_earlier_flag_is_a_status_question_not_a_new_flag():
    """Independent audit, 2 Nov: 'Did you log the issue I flagged this morning? What number is it?' filed a new flag."""
    from jarvis.india import ask
    for q in ("Did you log the issue I flagged this morning? What number is it?", "did you flag it?", "what number is that flag?",
              "Is the problem I reported fixed?"):
        assert ask.STATUS.search(q), q
    assert not ask.STATUS.search("Flag this: the Money screen shows the wrong total")
