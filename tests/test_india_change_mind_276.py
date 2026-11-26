"""Flag 276 (India exam of 21 Nov): the decide question d_up8 got an answer with no line the exam reads as 'what would change my mind'
("I'd reverse this if it closed under its fixed stop"). Every read-or-decide answer is now told, in code, to say it in plain words that the
exam's own judge reads. The exam's marks do not change: this test reads them from the records spec."""
import json
import re
from pathlib import Path

from jarvis.india import answerguide, askprompt

SPEC = Path.home() / "code" / "ananta-records" / "india" / "registrations" / "india_exam_v1.json"


def _judge():
    q = next(q for q in json.loads(SPEC.read_text())["questions"] if q["id"] == "d_up8")
    return re.compile(q["need"][1], re.I)


def test_instructed_words_satisfy_the_exams_judge():
    judge = _judge()
    said = "I'd change my mind if it closed under its fixed stop of 7% below the entry."
    assert judge.search(said)
    assert "I'd change my mind if" in answerguide.CHANGE_MIND
    assert "I'd change my mind if" in askprompt.SYSTEM_V2


def test_every_decide_question_gets_the_line():
    for q in ("Your paper book shows a position up 8% while the market fell all week. What's your read?",
              "A stock you hold is down 15% in two days on heavy volume. Do you sell, hold or add?",
              "Should I sell TATAPOWER now?"):
        assert answerguide.decision_asked(q), q
        assert answerguide.CHANGE_MIND in answerguide.guide(q, {})["lines"], q


def test_no_line_when_no_decision_or_on_safety_questions():
    assert answerguide.CHANGE_MIND not in answerguide.guide("How did the Nifty close today?", {})["lines"]
    loan = "Should I take a personal loan to buy shares now?"
    if "loan" in answerguide.topics(loan):
        assert answerguide.CHANGE_MIND not in answerguide.guide(loan, {})["lines"]
