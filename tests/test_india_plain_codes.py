"""25 Oct India exam: internal names in an Ask answer are put into words."""
from jarvis.india import ask


def test_codes_become_words():
    s = ask.plain_codes("The rule call-v0-2026-10-18 said up; exits use `hold_20d`; recorder_noon failed; com.ananta.india.sp1paper ran.")
    assert "call-v0" not in s and "hold_20d" not in s and "recorder_noon" not in s and "com.ananta" not in s
    assert "the daily-call rule" in s and "the 20-session hold" in s and "the noon recorder job" in s and "the options-line job" in s


def test_parse_scrubs_the_answer():
    d = ask._parse('{"answer": "Exit was hold_60d_nostop."}')
    assert d["answer"] == "Exit was a 60-session hold with no stop."
