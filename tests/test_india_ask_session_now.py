"""Flag 141 (2 Nov 2026): at 16:39 IST on Monday Ask said Monday's session was 'happening' although it had closed at 15:30 IST.
Ask's facts now carry the India clock and whether today's close is in the data."""
import datetime as dt

from jarvis.india import ask

RM = {"data_through": "2026-10-30", "next_session": "2026-11-02"}


def _at(y, m, d, hh, mm):
    return dt.datetime(y, m, d, hh, mm, tzinfo=ask.IST)


def test_monday_after_the_close_is_closed_and_not_in_data():
    s = ask.session_now(RM, _at(2026, 11, 2, 16, 39))
    assert s["state"] == "closed" and s["today_is_session"] and not s["today_in_data"]
    assert "closed at 15:30" in s["words"] and "not in my data yet" in s["words"] and "Fri 30 Oct" in s["words"]


def test_during_the_session_is_open():
    s = ask.session_now(RM, _at(2026, 11, 2, 11, 0))
    assert s["state"] == "open" and "open now" in s["words"]


def test_before_the_open_and_weekend():
    assert ask.session_now(RM, _at(2026, 11, 2, 8, 0))["state"] == "before_open"
    assert ask.session_now(RM, _at(2026, 11, 1, 12, 0))["state"] == "no_session"


def test_close_in_data_once_fetched():
    s = ask.session_now({"data_through": "2026-11-02"}, _at(2026, 11, 2, 23, 30))
    assert s["today_in_data"] and "already in my data" in s["words"]


def test_toronto_clock_is_converted():
    toronto = dt.datetime(2026, 11, 2, 6, 9, tzinfo=dt.timezone(dt.timedelta(hours=-5)))
    assert ask.session_now(RM, toronto)["state"] == "closed"
