"""Flag 229 (audit 23 Nov, S2): with Tue 24 Nov 2026 an NSE holiday, India answers put the next picks, call or reconstruction card on the
holiday ("08:00 IST tomorrow, 9:30 pm Toronto tonight") and read 'tomorrow' as the next calendar day. The clock now carries the next session
by name, the days with no session before it, and the next morning run (08:00 IST on a session's own morning), and the rules say to use them."""
import datetime as dt
from zoneinfo import ZoneInfo

import pytest

from jarvis.india import askprompt
from jarvis.india import livesession as L

IST = ZoneInfo("Asia/Kolkata")


@pytest.fixture(autouse=True)
def _holiday_24nov(monkeypatch):
    monkeypatch.setattr(L, "_holidays", lambda: {dt.date(2026, 11, 24)})


def _at(y, m, d, hh, mm):
    return dt.datetime(y, m, d, hh, mm, tzinfo=IST)


def test_monday_evening_before_the_holiday():
    c = L.clock("2026-11-23", _at(2026, 11, 23, 19, 59))        # the audit's own moment (IA01-IA84)
    assert c["state"] == "closed" and c["next_session"] == "2026-11-25"
    assert c["no_session_before_next"] == ["Tuesday 24 Nov (NSE holiday)"]
    assert c["next_morning_run"] == "2026-11-25"
    assert c["next_morning_run_words"] == "08:00 IST on Wednesday 25 Nov (9:30 pm Toronto, Tuesday 24 Nov)"
    r = c["relative_days"]
    assert "'Tomorrow', 'the next session' and 'the next open' mean Wednesday 25 Nov" in r
    assert "No session before it: Tuesday 24 Nov (NSE holiday)" in r
    assert "the next run is 08:00 IST on Wednesday 25 Nov" in r


def test_on_the_holiday_itself():
    c = L.clock("2026-11-23", _at(2026, 11, 24, 10, 0))
    assert c["state"] == "no_session" and c["next_session"] == "2026-11-25"
    assert c["no_session_before_next"] == ["Tuesday 24 Nov (NSE holiday)"] and c["next_morning_run"] == "2026-11-25"


def test_session_morning_before_and_after_the_run():
    early = L.clock("2026-11-23", _at(2026, 11, 25, 7, 0))
    assert early["state"] == "before_open" and early["next_session"] == "2026-11-25" and early["next_morning_run"] == "2026-11-25"
    assert early["no_session_before_next"] == []
    late = L.clock("2026-11-23", _at(2026, 11, 25, 8, 30))      # the 08:00 run is done; the next is Thursday's own morning
    assert late["next_session"] == "2026-11-25" and late["next_morning_run"] == "2026-11-26"


def test_friday_evening_skips_the_weekend():
    c = L.clock("2026-11-27", _at(2026, 11, 27, 18, 0))
    assert c["next_session"] == "2026-11-30" and c["next_morning_run"] == "2026-11-30"
    assert c["no_session_before_next"] == ["Saturday 28 Nov (weekend)", "Sunday 29 Nov (weekend)"]
    assert "mean Monday 30 Nov" in c["relative_days"]


def test_an_ordinary_evening_names_no_gap():
    c = L.clock("2026-11-25", _at(2026, 11, 25, 20, 0))
    assert c["next_session"] == "2026-11-26" and c["no_session_before_next"] == []
    assert "No session before it" not in c["relative_days"]


def test_toronto_afternoon_case_keeps_one_tomorrow_line():
    c = L.clock("2026-11-23", dt.datetime(2026, 11, 23, 18, 40, tzinfo=dt.timezone.utc))     # 00:10 IST Tue (holiday), 1:40 pm Toronto Mon
    assert c["relative_days"].count("'tomorrow' means") + c["relative_days"].count("'Tomorrow', 'the next session'") == 1
    assert "Wednesday 25 Nov" in c["relative_days"]


def test_the_rules_use_the_clock():
    p = " ".join(askprompt.SYSTEM.split()) if hasattr(askprompt, "SYSTEM") else " ".join(open(askprompt.__file__).read().split())
    assert "clock.next_morning_run_words" in p and "clock.no_session_before_next" in p
