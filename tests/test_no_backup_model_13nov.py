"""13 Nov 2026 (the keen outside audit, G-34; Madhav, 13 Nov 08:50 Toronto: "A: no backup model"). On 11 Nov the free backup model,
standing in for Claude, said "no review 42 exists in our system" minutes after another answer described review 42. Five outside checks
then beat every word list that tried to say which questions and replies the backup could be trusted with. So there is no backup model:
when Claude was meant to answer and cannot, no other model is asked, nothing is done, and Ananta says so in plain words. What Claude did
before it failed stands and is said. An answer the person chose to get from the everyday model is not touched."""
import inspect
import json
from pathlib import Path

from jarvis.service import appmap, ask

# every kind of question the five outside checks used: everyday ones, ones about a record, advice, an action, a greeting, a follow-up
QUESTIONS = ["How is my book doing?", "What's the price of Bitcoin?", "Did we buy anything tonight?", "What did review 42 find?",
             "Have we tested buying after drops?", "Should I buy this dip?", "Set a watch on ETH under 3,000.", "Remember that I like ETH.",
             "Good morning", "Did it run?"]


def _claude_down(*a, **k):
    raise TimeoutError("the call took too long")


def _world():
    from tests.test_ask_ananta import _jarvis
    return _jarvis()[0]                                                                 # slow to build: a test builds it once


def _ask(question, who="owner", budget=None, calls=None, claude=_claude_down, mode="deep", j=None):
    j = j or _world()

    def gemini(s, h, u, t, log):
        if calls is not None:
            calls.append(u)
        log.append({"tool": "watch", "args": {}, "ok": True})                               # if it were asked, it would act too
        return json.dumps({"answer": "We never ran review 42. Done, I set a watch.", "kind": "answer", "follow_ups": ["Shall I start it?"],
                           "next_action": {"label": "Start review 42", "ask": "Start review 42 for me", "say": "Shall I start review 42?"}}), {"in": 1, "out": 1}

    a = ask.Ask(j, providers={"sonnet": claude, "gemini": gemini})                         # makes the settings table
    if who.startswith("guest:"):
        j.name_of = lambda w: None                                                          # this test copy keeps no people list
    if budget is not None:
        j.db.execute("INSERT OR REPLACE INTO settings VALUES (?,?)", ("daily_budget_usd", str(budget)))
        j.db.commit()
    out = a.ask(who, question, mode=mode)
    row = j.db.execute("SELECT note, model, provider FROM ask_messages WHERE role='assistant' ORDER BY t DESC, rowid DESC LIMIT 1").fetchone()
    assert row[2] == out["provider"]                                                        # what is stored is what is shown
    return out, row[0] or "", row[1]


def test_when_claude_fails_no_other_model_is_asked_whatever_the_question():
    j = _world()
    for q in QUESTIONS:
        calls = []
        out, note, model = _ask(q, calls=calls, j=j)
        assert calls == [], q                                                               # the backup is asked nothing, so it does nothing
        assert out["answer"] == ask.CLAUDE_OUT + " Nothing was saved or done.", q
        assert not out.get("next_action") and out.get("follow_ups") == [] and not out.get("show") and not out.get("actions"), q
        assert "Claude is unavailable right now (TimeoutError after" in note and "there is no backup model, so no other model was asked" in note
        assert "the call took too long" not in note and "Gemini answered" not in note      # the failure's kind, never its text
        assert model == "none" and out["provider"] == "none" and out["model_label"] == "No model", (q, model)   # no model is named for it
    calls = []                                                                              # what needs no model still works
    out, _, _ = _ask("Show me the Bitcoin chart.", calls=calls, j=j)
    assert calls == [] and out["answer"] == "Sure. Opening BTC."


def test_when_claude_gives_no_words_no_other_model_is_asked():
    calls = []
    out, note, _ = _ask("How is my book doing?", calls=calls, claude=lambda s, h, u, t, log, **k: ("", {"in": 5, "out": 0}))
    assert calls == [] and out["answer"] == ask.CLAUDE_OUT + " Nothing was saved or done."
    assert "Claude gave no words this time; there is no backup model, so no other model was asked" in note


def test_over_budget_no_other_model_is_asked_and_the_words_say_when_to_ask_again():
    calls, asked = [], []

    def claude(s, h, u, t, log, **k):
        asked.append(u)
        return json.dumps({"answer": "x", "kind": "answer"}), {"in": 1, "out": 1}

    out, note, _ = _ask("How is my book doing?", calls=calls, claude=claude, budget=0)
    assert calls == [] and asked == []                                                      # neither model is asked
    assert out["answer"] == ask.CLAUDE_OUT_BUDGET + " Nothing was saved or done."
    assert "until midnight Toronto time" in out["answer"] and "More › Voice and model" in out["answer"]
    assert "is used up" in note and "there is no backup model, so no other model was asked" in note and "Gemini answered" not in note
    # a visitor cannot raise a budget, and is never told to (D7)
    out, _, _ = _ask("Why is Bitcoin down today?", calls=calls, claude=claude, budget=0, who="guest:zz-nobody")
    assert calls == [] and out["answer"].startswith(ask.CLAUDE_OUT_GUEST)
    assert "Voice and model" not in out["answer"] and "your Claude allowance for today is used up" in out["answer"]


def test_what_claude_did_before_it_failed_is_said_and_nothing_is_done_twice():
    # the fifth confirm check's N1 and N2: Claude set a watch and timed out; the backup set another, or the reply said nothing was done
    j = _world()
    for question in ("Set a watch on SOL.", "Keep an eye on SOL for me."):
        calls = []

        def claude(s, h, u, t, log, **k):
            log.append({"tool": "watch", "args": {}, "ok": True})
            raise TimeoutError("the call took too long")

        out, note, _ = _ask(question, calls=calls, claude=claude, j=j)
        assert calls == [], question
        assert out["answer"] == (ask.CLAUDE_OUT + " Before it failed, the main model set up a watch; that stands, so there is no need to "
                                 "ask for it again."), question
        assert "Nothing was saved or done" not in out["answer"]
        assert "Claude had already acted before it failed; there is no backup model, so no other model was asked" in note
    assert ask.DONE_WORDS["change_watch"] == "changed a watch" and ask.DONE_WORDS["remember"] == "saved your note"


def test_an_answer_the_person_chose_from_the_everyday_model_is_not_touched():
    calls = []
    out, note, model = _ask("How is my book doing?", calls=calls, mode="everyday")
    assert len(calls) == 1 and out["answer"].startswith("We never ran review 42.") and model != "none"     # his choice: not a fallback
    said = {"kind": "answer", "answer": "Your book is flat today.", "next_action": {"label": "x"}, "follow_ups": ["y"]}
    assert ask.claude_is_out(dict(said), "gemini", "gemini") is False and ask.claude_is_out(dict(said), "sonnet", "sonnet") is False
    r = dict(said)
    assert ask.claude_is_out(r, "sonnet", "gemini") is True and r["answer"] == ask.CLAUDE_OUT + " Nothing was saved or done."
    assert r["next_action"] is None and r["follow_ups"] == [] and r["backup_withheld_why"] == "no backup model: the main model was not available"
    r = dict(said)
    assert ask.claude_is_out(r, "sonnet", "gemini", "Claude budget for today ($2.00) is used up", guest=True) and r["answer"].startswith(ask.CLAUDE_OUT_GUEST)
    assert ask.claude_is_out(dict(said), "no-such-model", "gemini") is False


def test_the_word_lists_and_the_old_choice_after_the_budget_are_gone():
    for name in ("backup_may_answer", "backup_cannot_deny", "asks_about_a_record", "speaks_of_a_record", "denies_a_record",
                 "BACKUP_CANNOT_DENY", "GEMINI_QUOTA_TOO", "_EVERYDAY", "_DENIALS", "_MENTIONS"):
        assert not hasattr(ask, name), name
    src = inspect.getsource(ask.Ask.ask)
    assert "so Gemini answered" not in src and 'self.setting("over_budget")' not in src
    for said in (ask.CLAUDE_OUT, ask.CLAUDE_OUT_BUDGET, ask.CLAUDE_OUT_GUEST):
        assert said.startswith("I can't answer that right now: ") and "vouch" not in said and "backup model can't" not in said
    tool = next(t[1] for t in ask.TOOLS if t[0] == "propose_setting")
    assert "over_budget" not in tool and "free Gemini" not in tool and "no model answers until midnight Toronto time" in tool
    page = (Path(ask.__file__).resolve().parents[1] / "app" / "src" / "voicesettings.tsx").read_text()
    assert "Gemini (free) answers instead" not in page and "It has no backup model." in page


def test_a_brief_that_could_not_be_written_waits_an_hour_then_says_so_once():
    # F2 (12 Nov): a withheld brief was saved as the day's brief. 13 Nov: with no backup model it waits, and from an hour after it was due
    # the day gets one plain line, so the wait is said and the asking stops
    import datetime as dt
    from zoneinfo import ZoneInfo

    from jarvis.service.alerts import Alerts
    from tests.test_ask_ananta import _jarvis
    for kind, early, late in (("morning", (8, 30), (9, 5)), ("evening", (21, 45), (22, 35))):
        j, _ = _jarvis()
        clock = {"t": dt.datetime(2026, 10, 2, *early, tzinfo=ZoneInfo("America/Toronto")).timestamp()}
        AB, pushed = Alerts(j.db, lambda: clock["t"]), []
        held = {"kind": "answer", "answer": ask.CLAUDE_OUT + " Nothing was saved or done.",
                "backup_withheld_why": "no backup model: the main model was not available"}
        assert AB.due_brief() == kind
        assert AB.write_brief(kind, lambda q: dict(held), push=lambda t, x: pushed.append(x)) is None
        assert AB.due_brief() == kind and j.db.execute("SELECT COUNT(*) FROM briefings").fetchone()[0] == 0 and pushed == []
        assert AB.write_brief(kind, lambda q: {"error": "boom"}, push=lambda t, x: pushed.append(x)) is None       # another failure: it waits
        clock["t"] = dt.datetime(2026, 10, 2, *late, tzinfo=ZoneInfo("America/Toronto")).timestamp()
        assert AB.write_brief(kind, lambda q: {"error": "boom"}, push=lambda t, x: pushed.append(x)) is None       # still not Claude being out
        b = AB.write_brief(kind, lambda q: dict(held), push=lambda t, x: pushed.append(x))
        assert b["text"] == (f"No {kind} brief today: the main model was not available when it was due, and Ananta has no backup model. "
                             "Ask me for a brief when you want one.")
        assert pushed == [b["text"]] and AB.due_brief() is None                              # said once; the asking stops
        assert "can't answer" not in b["text"]                                              # never the cannot-answer words as a brief
    j, _ = _jarvis()
    t9 = dt.datetime(2026, 10, 2, 9, 0, tzinfo=ZoneInfo("America/Toronto")).timestamp()
    AB = Alerts(j.db, lambda: t9)
    b = AB.write_brief("morning", lambda q: {"answer": "Quiet night.", "kind": "answer"}, push=lambda t, x: None)   # Claude answered: as before
    assert b["text"] == "Quiet night." and AB.due_brief() is None


def test_the_manual_book_the_stop_line_and_the_rebuild_hour_are_said_right():
    # kept from tests/test_backup_guard_12nov.py (repair 5's confirm checks, D4 to D6 and E4), which this file replaces
    from jarvis.service import chain
    # D4 (S5) and E4 (S5): four server lines and the manual book's own lookup called it his own book; the Ask reads all of them
    rule5 = next(line for line in ask.SYSTEM.splitlines() if line.startswith("5. Actions you can PREPARE"))
    assert "owner's own book" not in rule5 and "paper orders in the manual book" in rule5 and "offer the manual book instead" in rule5
    assert "owner's own paper book" not in next(t[1] for t in ask.TOOLS if t[0] == "last_week")
    book = next(t[1] for t in ask.TOOLS if t[0] == "manual_book")
    assert "own manual paper book" not in book and "kept apart from his $500 account" in book
    assert "there is no {c} in the manual book" in inspect.getsource(ask.Lookups.t_propose_levels)
    assert appmap.SPOTS["portfolio:mine"]["mine.value"] == "the manual book's value"
    assert not any("my paper book" in v for p in appmap.describe()["places"] for v in p["spots"].values())
    # D5 (S5): the chain's stop line names the same exponential line its trend line names
    src = inspect.getsource(chain)
    assert "'the 50-day exponential average'} with a 1-ATR buffer" in src and "'the 50-day average'} with a 1-ATR" not in src
    # D6 (S5): the self-rebuild runs after the daily close, which is 7 pm Toronto in winter
    assert "the nightly self-rebuild (8 pm Toronto" not in ask.SYSTEM
    assert "the nightly self-rebuild (after each daily close, 7 pm Toronto in winter and 8 pm in summer" in ask.SYSTEM
