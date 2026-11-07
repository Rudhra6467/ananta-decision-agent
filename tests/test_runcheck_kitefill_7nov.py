"""7 Nov 2026 morning review: the Kite fill part was judged at 10:00 IST although its plist fires at 10:00 Saturday on the
Mac's own (Toronto) clock, so the self-check said it "did not run at 6 Nov 23:30 Toronto" hours before it was due."""
from jarvis.india.schedule import TARGETS
from jarvis.service.runcheck_parts import PARTS, TOR


def _part():
    return next(p for p in PARTS if p["id"] == "india_kite_fill")


def test_kite_fill_is_judged_on_the_macs_clock():
    cad = _part()["cadence"]
    assert cad["tz"] == TOR
    assert cad["at"] == "10:00" and cad["weekly"] == 5          # Saturday (Monday is 0); launchd Weekday 6


def test_kite_fill_is_not_an_indian_time_job():
    # if it ever moves onto Indian time, schedule.py owns its time and this part must follow it
    assert "com.ananta.india.kitefill" not in TARGETS
