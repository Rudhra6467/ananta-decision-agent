"""What a test question leaves behind (the keen outside audit of 11-12 Nov 2026, finding G-55; open-list flag 117).

The guide claimed "a test question saves nothing". Half true: no order, card, flag or note was ever saved, but the auditors' dry questions
left suggestion chips, audit rows that said the owner asked, a row in the misunderstood table, and a test's news check could overwrite the
day's news verdict. Now a test question keeps only its own question and answer in the chat table, in a thread marked as a test (how every
reader tells them apart); the audit row says a test asked; and the news check is not run."""
import json

from jarvis.service import ask
from tests.test_ask_ananta import _jarvis


def _n(j, sql: str) -> int:
    try:
        return j.db.execute(sql).fetchone()[0]
    except Exception:  # noqa: BLE001 - a table that was never made holds nothing
        return 0


def _reply(answer: str, kind: str = "answer"):
    return lambda s, h, u, t, log: (json.dumps({"answer": answer, "kind": kind, "follow_ups": ["How is Bitcoin?", "What changed today?"]}),
                                    {"in": 1, "out": 1})


def test_a_test_question_leaves_no_chips_and_its_audit_row_says_a_test_asked():
    j, ex = _jarvis()
    A = ask.Ask(j, providers={"gemini": _reply("Bitcoin is steady.")})
    A.ask("owner", "how is btc", mode="everyday", source="eval")
    assert _n(j, "SELECT count(*) FROM ask_chips") == 0
    rows = j.db.execute("SELECT who FROM audit WHERE action='ask'").fetchall()
    assert rows and {w for (w,) in rows} == {"test"}                                  # never 'owner': he asked nothing
    assert _n(j, "SELECT count(*) FROM ask_messages WHERE role='user' AND mode LIKE 'eval:%'") == 1   # the thread is marked as a test


def test_his_own_question_still_keeps_its_chips_and_his_name():
    j, ex = _jarvis()
    A = ask.Ask(j, providers={"gemini": _reply("Bitcoin is steady.")})
    A.ask("owner", "how is btc", mode="everyday")
    assert _n(j, "SELECT count(*) FROM ask_chips") >= 1
    assert {w for (w,) in j.db.execute("SELECT who FROM audit WHERE action='ask'").fetchall()} == {"owner"}


def test_a_test_question_that_is_not_understood_is_not_filed_as_his():
    j, ex = _jarvis()
    A = ask.Ask(j, providers={"gemini": _reply("Which book do you mean?", kind="clarify")})
    A.ask("owner", "how are we doing", mode="everyday", source="eval")
    assert _n(j, "SELECT count(*) FROM ask_misunderstood") == 0
    A.ask("owner", "how are we doing", mode="everyday")
    assert _n(j, "SELECT count(*) FROM ask_misunderstood") == 1                         # his own is still kept


def test_a_test_does_not_run_the_news_check():
    assert "news_check" in ask.Lookups.TEST_WRITES
    j, ex = _jarvis()
    L = ask.Lookups(j, "evalthread", test=True)
    out = L.call("news_check", {"coin": next(iter(ex.st["engines"]))})
    assert out.get("test_run") and out["done"]["status"] == "TEST"


# ---- 12 Nov 2026, the outside check of that repair (G-55 partly, N6): the answer rows, and what old tests left behind ----

def test_a_test_questions_answer_and_error_rows_are_marked_too():
    j, ex = _jarvis()
    A = ask.Ask(j, providers={"gemini": _reply("Bitcoin is steady.")})
    A.ask("owner", "how is btc", mode="everyday", source="eval")

    def down(*a, **k):
        raise RuntimeError("the model is down")

    B = ask.Ask(j, providers={"gemini": down})
    assert "error" in B.ask("owner", "how is eth", mode="everyday", source="eval")
    rows = j.db.execute("SELECT COALESCE(mode, ''), error FROM ask_messages WHERE role='assistant'").fetchall()
    assert len(rows) == 2 and all(m.startswith("eval:") for m, _ in rows), rows      # only the thread showed it before
    A.ask("owner", "how is btc", mode="everyday")                                     # his own answer is not marked
    assert sum(not m.startswith("eval:") for (m,) in j.db.execute("SELECT COALESCE(mode, '') FROM ask_messages WHERE role='assistant'")) == 1


def test_old_test_leftovers_no_longer_feed_the_chip_ranking_or_the_misunderstood_list():
    j, ex = _jarvis()
    A = ask.Ask(j, providers={"gemini": _reply("Bitcoin is steady.")})
    A.ask("owner", "how is btc", mode="everyday", source="eval")
    (th,) = j.db.execute("SELECT thread FROM ask_messages WHERE role='user' AND mode LIKE 'eval:%'").fetchone()
    ask._chip_table(j)                                     # what a test left before the repair, in its own thread (nothing is deleted)
    j.db.execute("INSERT INTO ask_chips (reply_id, thread, t, kind, text, ask, picked) VALUES ('old', ?, ?, 'follow', 'Old test chip', "
                 "'Old test chip', 1)", (th, int(j.now())))
    j.db.execute("INSERT INTO ask_misunderstood (t, thread, question, kind, provider) VALUES (?, ?, 'an old test question', 'clarify', 'gemini')",
                 (int(j.now()), th))
    A.ask("owner", "how is btc", mode="everyday")                                     # his own question keeps its chips
    shown = {c["text"] for c in ask.chip_stats(j)}
    assert shown and "Old test chip" not in shown
    assert j.db.execute("SELECT count(*) FROM ask_chips WHERE text='Old test chip'").fetchone()[0] == 1   # kept, only not counted
    assert all(m["question"] != "an old test question" for m in A.stats()["misunderstood"])


def test_the_instant_answers_mark_a_test_question_too():
    """The third outside check (F3): the navigation answer, the planned-downtime answer and the grader's handover still wrote unmarked
    rows, so their threads were not seen as tests and their questions counted toward the day's limit."""
    j, ex = _jarvis()
    A = ask.Ask(j, providers={"gemini": _reply("not used")})
    for text in ("take me home", "I'm turning the laptop off for an hour", "Grader here."):
        out = A.ask("owner", text, mode="everyday", source="eval")
        assert out.get("model") == "instant", (text, out.get("model"))
        rows = j.db.execute("SELECT role, COALESCE(mode, '') FROM ask_messages WHERE thread=?", (out["thread"],)).fetchall()
        assert len(rows) == 2 and all(m.startswith("eval:") for _, m in rows), (text, rows)
    assert A.today_count() == 0                                                       # tests never use up his questions
    out = A.ask("owner", "take me home", mode="everyday")                             # his own stays unmarked
    assert {m for (m,) in j.db.execute("SELECT COALESCE(mode, '') FROM ask_messages WHERE thread=?", (out["thread"],))} == {"nav"}
