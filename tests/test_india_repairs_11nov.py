"""The India half of the night repairs (11 Nov 2026, after the close; Madhav, 10 Nov 21:22: "Why can't we fix them based on historical data
and performance of Ananta instead of waiting?"). Words, checks and bookkeeping only: no options-line or book rule changed."""
import inspect
from pathlib import Path

from jarvis.india import askwords, numcheck, schedule
from jarvis.service import requests_log

ROOT = Path(__file__).resolve().parents[1]


def test_a_points_figure_is_checked_against_the_moves_the_facts_hold():
    # R-042: "the index rose 624 points" passed, because a points figure was looked for among every number in the facts
    facts = {"index_now": {"rows": {"NIFTY 50": {"last": 25255.05, "prev_close": 25044.65, "open": 25337.8, "high": 25424.35, "low": 25095.35}}},
             "noise": [612, 620, 630, 640, 1.2], "words": "Bank Nifty rose 1,051.15 points on the day"}
    assert numcheck.figures(numcheck.check("The Nifty rose 624 points today.", facts)) == ["624"]
    for ok in ("The Nifty rose 210 points today.", "It is up about 210 points.", "It fell 82.45 points from the open.", "Bank Nifty rose 1,051 points."):
        assert numcheck.check(ok, facts) == [], ok
    assert numcheck.check("It moved 5 points in the last minute.", facts) == [], "a move under 10 points is not checked"


def test_a_flag_number_and_its_stored_number_come_from_one_place():
    # R-026: the India Ask added and took away a hand-written 81
    src = (ROOT / "jarvis" / "india" / "ask.py").read_text()
    assert "- 81" not in src and "+ 81" not in src
    assert requests_log.num_of_flag(15) == 96 and requests_log.label(96) == "flag 15" and requests_log.flag_no(96) == 15


def test_the_options_line_window_is_said_one_way():
    # R-024: 09:15 to 10:15 in some places, "09:15, 09:30 and 09:45" in others
    assert askwords.window_words() == "09:15, 09:30, 09:45 and 10:15"
    assert "09:15, 09:30, 09:45 and 10:15 IST" in schedule.day_words()
    src = (ROOT / "jarvis" / "india" / "ask.py").read_text()
    assert "09:15-09:45 IST: the options line" not in src


def test_the_fear_gauge_says_its_change_as_the_days():
    # board 190: "-5.63% the swing traders expect over 30 days" put the day's change beside what the gauge means
    src = (ROOT / "jarvis" / "india" / "places.py").read_text()
    assert 'since="the swing traders expect over 30 days"' not in src and 'since="on the day" if isinstance(pct, (int, float))' in src
    assert "how much traders expect the Nifty to swing over the next 30 days" in src


def test_the_shadow_trader_gives_its_answer_room():
    # board 191: on 11 Nov its answer was cut off at 1,500 tokens and could not be read, so it stood down with no forecast
    import runpy
    g = runpy.run_path(str(ROOT / "scripts" / "india_shadow_trader.py"), run_name="not_main")
    assert inspect.signature(g["claude"]).parameters["max_tokens"].default == 3000
    assert "under 350 words in all" in (ROOT / "scripts" / "india_shadow_trader.py").read_text()
