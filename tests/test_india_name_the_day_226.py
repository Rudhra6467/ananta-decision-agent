"""Flag 226 (the never-again replay of 21 and 23 Nov): "Hey Ananta, what happened today in the market and what did we do?" got the right
figures but never named the day ('today' was Monday 2 Nov). A day recap now names its session, in code, before the answer is spoken."""
from jarvis.india import ask
from jarvis.india import livesession as L
from tests.test_india_livesession import AT_0608_TORONTO

Q = "Hey Ananta, what happened today in the market and what did we do?"
A = ("Sir, the Nifty closed at 23,441, up 1.7%, and Bank Nifty at 55,002, up 0.6%.\nThe options line took two paper longs.\n"
     "Next is Tuesday 3 Nov, when both options trades close at the open.")


def _live():
    return {"clock": L.clock("2026-10-30", AT_0608_TORONTO)}


def test_the_replay_case_gets_its_day():
    live = _live()
    assert live["clock"]["latest_session"] == "2026-11-02"
    out = L.name_the_day(A, live, Q)
    assert out.startswith("Sir, on Monday 2 Nov, the Nifty closed at 23,441")
    assert out.endswith("close at the open.") and out.count("Monday 2 Nov") == 1


def test_an_answer_that_names_the_day_is_left_alone():
    live = _live()
    for a in ("Sir, on Monday the Nifty closed at 23,441.", "Sir, Monday 2 Nov: the Nifty closed at 23,441.", "Sir, 2 Nov was a good day."):
        assert L.name_the_day(a, live, Q) == a


def test_other_questions_and_other_days_are_left_alone():
    live = _live()
    assert L.name_the_day(A, live, "What is the Nifty's RSI?") == A
    assert L.name_the_day(A, live, "What happened yesterday in the market?") == A
    assert L.name_the_day(A, live, "What happened on Friday?") == A
    assert L.name_the_day(A, {}, Q) == A


def test_an_answer_not_starting_with_sir_gets_a_day_label():
    assert L.name_the_day("The Nifty rose 1.7%.", _live(), Q) == "Monday 2 Nov: The Nifty rose 1.7%."


def test_the_ask_calls_it_after_the_guard():
    src = open(ask.__file__).read()
    i, j = src.index("name_the_day("), src.index("reply = finish(reply, text, model=")
    assert i < j
