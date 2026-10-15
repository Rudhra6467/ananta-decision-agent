"""The 'why' questions of the agent exam (gate check ux_why, added at the Oct 15 crypto lock) and the age limit on exam passes."""
from datetime import datetime, timedelta

from jarvis.service import evidence_live as el
from jarvis.service import exam

GOOD = {
    "why_dial": "Bitcoin is above its 50-day and 200-day averages, so the dial is open.",
    "why_h07": "It is bought only when the dial is closed because review 26 measured an edge there and none when it is open.",
    "why_cash": "The 500 dollar book holds cash when the dial is closed to protect it while Bitcoin trends down.",
    "why_pause": "Four losing trades in a row pause buying: it is a risk brake after a losing streak.",
    "why_nostop": "A stop made dip buys worse in review 27, so they exit by time only.",
}


def test_each_why_question_is_judged_by_facts():
    ids = [c[0] for c in exam.WHY]
    assert ids == list(GOOD) and len(exam.WHY) == 5 and exam.WHY_PASS == 4
    for cid, _, groups in exam.WHY:
        assert exam.judge_known(GOOD[cid], groups), cid
        assert not exam.judge_known("I am not sure what you mean.", groups), cid
    assert not exam.judge_known("Because the market is strange.", dict((c[0], c[2]) for c in exam.WHY)["why_dial"])


def _fake(answers):
    class Fake:
        def ask(self, who, q, thread=None, mode=None, source=None):
            for cid, question, _ in exam.WHY:
                if q == question:
                    return {"answer": answers.get(cid, "I don't know.")}
            return {"answer": "I don't know."}
    return Fake()


def test_a_run_counts_the_why_answers_and_passes_at_four_of_five(tmp_path, monkeypatch):
    monkeypatch.setattr(exam, "OUT", tmp_path)                       # never touch the real exam files
    out = exam.run(None, ask=_fake(GOOD))
    assert out["why"] == 5 and out["why_of"] == 5 and out["why_pass"] is True
    assert sum(1 for r in out["rows"] if r["kind"] == "why") == 5
    four = dict(GOOD, why_pause="Because it is a rule.")
    out = exam.run(None, ask=_fake(four))
    assert out["why"] == 4 and out["why_pass"] is True
    three = dict(four, why_cash="No idea.")
    out = exam.run(None, ask=_fake(three))
    assert out["why"] == 3 and out["why_pass"] is False
    assert out["exam_pass"] in (True, False) and "knows_pass" in out      # the older verdicts keep their own fields


def test_rejudge_recounts_the_why_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(exam, "OUT", tmp_path)
    exam.run(None, ask=_fake(dict(GOOD, why_dial="It is open.")))
    out = exam.rejudge()
    assert out["why"] == 4 and out["why_pass"] is True


def test_the_gate_reads_the_why_questions():
    c = {"status": "PARTLY", "note": ""}
    el._gate_why(c, None)
    assert c["status"] == "NOT_MEASURED" and "why" in c["note"]
    c = {}
    el._gate_why(c, {"day": datetime.now().strftime("%Y-%m-%d"), "why": 4, "why_of": 5, "why_pass": True})
    assert c["status"] == "PASS" and "4 of 5" in c["note"]
    c = {}
    el._gate_why(c, {"day": datetime.now().strftime("%Y-%m-%d"), "why": 2, "why_of": 5, "why_pass": False})
    assert c["status"] == "FAIL"
    c = {}
    el._gate_why(c, {"day": "2026-10-01", "known": 1})                  # an older run that never asked the questions
    assert c["status"] == "NOT_MEASURED"


def test_a_pass_older_than_eight_days_reads_partly_and_a_fail_stays_a_fail():
    today = datetime.now()
    fresh = (today - timedelta(days=el.EXAM_FRESH_DAYS)).strftime("%Y-%m-%d")
    old = (today - timedelta(days=el.EXAM_FRESH_DAYS + 1)).strftime("%Y-%m-%d")
    c = {"status": "PASS", "note": "20 of 20"}
    el._exam_age(c, fresh)
    assert c == {"status": "PASS", "note": "20 of 20"}
    el._exam_age(c, old)
    assert c["status"] == "PARTLY" and "9 days old" in c["note"] and c["note"].startswith("20 of 20")
    f = {"status": "FAIL", "note": "11 of 20"}
    el._exam_age(f, old)
    assert f["status"] == "FAIL"
    n = {"status": "NOT_MEASURED", "note": "exam not run yet"}
    el._exam_age(n, None)
    assert n["status"] == "NOT_MEASURED"
    el._exam_age(n, "not a date")
    assert n["status"] == "NOT_MEASURED"
