"""23 Nov 2026 (Madhav: "Yes, let's do it"): India's research drafts ask for his yes on Sundays only (the weekly check-up)."""
import datetime as dt
from zoneinfo import ZoneInfo

from jarvis.service import waiting

TZ = ZoneInfo("America/Toronto")


def test_drafts_ask_only_on_sunday(monkeypatch):
    monkeypatch.setenv("DRAFTS_WEEKLY_IN_TESTS", "1")
    assert waiting.drafts_day(dt.datetime(2026, 11, 29, 9, 0, tzinfo=TZ).timestamp())        # Sunday
    assert not waiting.drafts_day(dt.datetime(2026, 11, 24, 9, 0, tzinfo=TZ).timestamp())    # Tuesday


def test_other_tests_see_the_drafts_every_day():
    assert waiting.drafts_day(dt.datetime(2026, 11, 24, 9, 0, tzinfo=TZ).timestamp())
