"""21 Nov 2026 (the outside lock review, G-09 partly fixed): the trials list said the options line finishes 23 Nov while it stood at 18 of
20 on Fri 20 Nov and 24 Nov is a holiday (the 20th session is Wed 25 Nov). Fails on the code before (no `through`, no holidays)."""
import datetime as dt

from india import trials

D = dt.date


def test_the_finish_counts_from_the_trials_own_count_not_from_its_start():
    days = [D(2026, 11, 16), D(2026, 11, 17), D(2026, 11, 18), D(2026, 11, 19), D(2026, 11, 20), D(2026, 11, 23), D(2026, 11, 25)]
    # a trial that started 16 Nov and needs 7 would end 25 Nov by the calendar; one that skipped two sessions is at 3 on 20 Nov
    assert trials._finish(days, D(2026, 11, 16), 3, 5, through=D(2026, 11, 20)) == D(2026, 11, 25)
    assert trials._finish(days, D(2026, 11, 16), 4, 5, through=D(2026, 11, 20)) == D(2026, 11, 23)


def test_without_a_through_day_it_counts_as_before():
    days = [D(2026, 11, 16), D(2026, 11, 17), D(2026, 11, 18)]
    assert trials._finish(days, D(2026, 11, 16), 0, 2) == D(2026, 11, 17)


def test_known_holidays_past_the_calendar_are_not_sessions(monkeypatch):
    from india import dayplan

    monkeypatch.setattr(dayplan, "holidays", lambda refresh=False: set())
    plain = trials._sessions()
    h = next(d for d in plain[-200:] if d.weekday() == 2)              # a Wednesday in the weekday extension
    monkeypatch.setattr(dayplan, "holidays", lambda refresh=False: {h})
    days = trials._sessions()
    assert h not in days and h + dt.timedelta(days=1) in days
