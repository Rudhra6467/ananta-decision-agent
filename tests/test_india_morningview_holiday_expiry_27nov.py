"""Flag 252 (25 Nov: the view called Tue 24 Nov, an NSE holiday, a missing session) and flag 294 (pre-live T6, 27 Nov: the view said the next
options expiry is 29 Dec while Nifty's weekly expires Tue 1 Dec). Facts and words only; no rule, no model."""
import datetime as dt

import pandas as pd

from india import morningview as mv

HOL = {dt.date(2026, 11, 24), dt.date(2026, 12, 25)}


def test_holiday_is_no_session_not_missing_data():
    g = mv.since_last_session("2026-11-25", "2026-11-23", hol=HOL)
    assert g["complete"] is True and g["holidays"] == ["2026-11-24"] and g["missing_sessions"] == []
    assert "Tue 24 Nov was an NSE holiday" in g["words"] and "nothing is missing" in g["words"]
    assert "missing" not in g["words"].replace("nothing is missing", "")


def test_a_real_missing_session_is_still_said():
    g = mv.since_last_session("2026-11-27", "2026-11-25", hol=HOL)
    assert g["complete"] is False and g["missing_sessions"] == ["2026-11-26"]
    assert "a session behind" in g["words"]


def test_no_gap_no_line_and_weekend_is_not_a_gap():
    assert mv.since_last_session("2026-11-27", "2026-11-26", hol=HOL) is None
    assert mv.since_last_session("2026-11-30", "2026-11-27", hol=HOL) is None


def _ins():
    rows = [("NIFTY", "2026-12-01"), ("NIFTY", "2026-12-08"), ("NIFTY", "2026-12-29"), ("BANKNIFTY", "2026-12-29"), ("BANKNIFTY", "2027-01-26")]
    return pd.DataFrame([{"name": n, "expiry": e} for n, e in rows])


def test_each_index_gets_its_own_next_expiry():
    ex = mv.live_expiries("2026-11-27", ins=_ins())
    assert ex["by_index"]["NIFTY"] == {"date": "2026-12-01", "monthly": False}
    assert ex["by_index"]["BANKNIFTY"] == {"date": "2026-12-29", "monthly": True}
    assert ex["next"]["date"] == "2026-12-01" and ex["next"]["symbols"] == ["NIFTY"]


def test_watch_line_names_both_indices():
    ex = mv.live_expiries("2026-11-27", ins=_ins())
    f = {"overnight": {"us": {}, "india": {}}, "setup": {"expiry": ex, "events": {}}, "plan": {}, "scorecard": {}, "yesterday": {}}
    text = " ".join(mv.lines(f)["watch"])
    assert "Next options expiry: Nifty 1 Dec (weekly), Bank Nifty 29 Dec (monthly)." in text
    assert "29 Dec (BANKNIFTY" not in text


def test_view_line_says_the_holiday():
    f = {"overnight": {"us": {}, "india": {}, "since_last_session": mv.since_last_session("2026-11-25", "2026-11-23", hol=HOL)},
         "setup": {"expiry": {}, "events": {}}, "plan": {}, "scorecard": {}, "yesterday": {}}
    assert any("Tue 24 Nov was an NSE holiday" in x for x in mv.lines(f)["view"])


def test_expiry_day_is_named_and_not_repeated_as_next():
    ex = mv.live_expiries("2026-12-01", ins=_ins())
    assert ex["today"] == ["NIFTY"] and "NIFTY" in ex["by_index"]      # Nifty's following weekly is still known
    assert ex["by_index"]["NIFTY"]["date"] == "2026-12-08"


def test_unreadable_master_falls_back():
    assert mv.live_expiries("2026-11-27", ins=pd.DataFrame({"x": [1]})) is None
