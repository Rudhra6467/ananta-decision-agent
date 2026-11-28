"""US market holidays (NYSE and Nasdaq full closes), used only to judge whether the US close an India plan read is the latest one (flag 293,
Madhav 27 Nov 2026 in chat: 'yes to adding the list of holidays as well'). On Fri 27 Nov the options plan called the Wed 25 Nov close stale,
though the US market was shut on Thu 26 Nov for Thanksgiving. This list feeds the staleness mark and its words only; no decision reads it.

Source: the NYSE holiday calendar for 2026 and 2027 (a Saturday holiday closes the Friday before, a Sunday holiday the Monday after,
except New Year's Day on a Saturday). Extend it before 2028; a missing year makes the check fall back to weekdays only, as before."""
from __future__ import annotations

import datetime as dt

US_HOLIDAYS = {dt.date.fromisoformat(d) for d in (
    # 2026
    "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25", "2026-06-19", "2026-07-03", "2026-09-07", "2026-11-26", "2026-12-25",
    # 2027
    "2027-01-01", "2027-01-18", "2027-02-15", "2027-03-26", "2027-05-31", "2027-06-18", "2027-07-05", "2027-09-06", "2027-11-25", "2027-12-24",
)}
COVERED_YEARS = {2026, 2027}


def is_us_session(d: dt.date) -> bool:
    return d.weekday() < 5 and d not in US_HOLIDAYS


def last_us_session_before(day: dt.date) -> dt.date:
    """The latest US session strictly before `day` (an India session's date): its close is the newest one the plan can have read."""
    d = day - dt.timedelta(days=1)
    while not is_us_session(d):
        d -= dt.timedelta(days=1)
    return d
