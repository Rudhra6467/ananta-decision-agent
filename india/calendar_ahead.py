"""The one calendar of dated events ahead (9 Nov 2026; Madhav: "yes, lets complete" to the outsider readiness review, fix 4).

Before this there were two: a hand-kept list in the agent's desk (the voice only) and the event registry (the morning view and the options
line's event flag). The registry holds what has happened: a date after the trading calendar's last day is rejected, so on the day itself the
options line could never know it was an RBI day (its spec, sp1_v2.json: "scheduled event today (RBI MPC decision, Union Budget, election
counting) ... scheduled flag from the published calendars only"). The next RBI decision, Friday 4 Dec 2026, would have passed unseen.

One file now, india/registrations/calendar_ahead.json, kept by hand from each owner's published schedule, read here by everyone:

  rows()              every row, by date
  scheduled_ahead()   the dates the options line treats as an event day: kind rbi_policy / union_budget / election, status official, a
                      session day, public during the session (scenario.scheduled_dates() adds them to the registry's past dates)
  build()             manifests/calendar.json: the rows from yesterday on, each with the first Indian session that can trade it (worked out
                      from the date, the time and NSE's holiday list, never typed) and one plain sentence; what the voice and the view read

  python -m india.calendar_ahead        builds manifests/calendar.json and prints the next rows

Read-only on the registrations file; no network. A row never trades anything: it is context, and for the three scheduled kinds one input of
the options line as its study defined it.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

from india import paths

FILE = Path(__file__).resolve().parent / "registrations" / "calendar_ahead.json"
SCHEDULED = {"rbi_policy", "union_budget", "election"}          # scenario.SCHEDULED: the options line's scheduled-event kinds
CLOSE = dt.time(15, 30)
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))


def rows(file: Path | None = None) -> list[dict]:
    try:
        d = json.loads((file or FILE).read_text())
    except (OSError, ValueError):
        return []
    return sorted((r for r in d.get("rows") or [] if r.get("date") and r.get("what")), key=lambda r: (r["date"], r.get("time_ist") or "99:99"))


def _holidays() -> set[dt.date]:
    try:
        from india import dayplan
        return dayplan.holidays(refresh=False)
    except Exception:  # noqa: BLE001
        return set()


def _is_session(d: dt.date, hol: set) -> bool:
    return d.weekday() < 5 and d not in hol


def _time(r: dict) -> dt.time | None:
    try:
        hh, mm = map(int, str(r.get("time_ist") or "").split(":")[:2])
        return dt.time(hh, mm)
    except ValueError:
        return None


def first_session(r: dict, hol: set | None = None) -> dt.date:
    """The first Indian session that can trade the row: its own day when that is a session and the news is out before the 15:30 close (or the
    time is not known), else the next session."""
    hol = _holidays() if hol is None else hol
    d = dt.date.fromisoformat(r["date"])
    t = _time(r)
    if _is_session(d, hol) and (t is None or t < CLOSE):
        return d
    d += dt.timedelta(days=1)
    while not _is_session(d, hol):
        d += dt.timedelta(days=1)
    return d


def scheduled_ahead(file: Path | None = None, hol: set | None = None) -> set[dt.date]:
    """The options line's event days from the published calendars: official rows of the three scheduled kinds whose first session is the
    event's own day (the registry's rule: first tradable session = event date)."""
    hol = _holidays() if hol is None else hol
    out = set()
    for r in rows(file):
        if r.get("kind") in SCHEDULED and r.get("status") == "official":
            d = dt.date.fromisoformat(r["date"])
            if first_session(r, hol) == d:
                out.add(d)
    return out


def _dw(d: dt.date) -> str:
    return f"{d:%A} {d.day} {d:%b}"


def sentence(r: dict, hol: set | None = None) -> str:
    d = dt.date.fromisoformat(r["date"])
    fs = first_session(r, hol)
    when = _dw(d) + (f", {r['time_ist']} IST" if r.get("time_ist") else "")
    s = f"{r['what']}: {when}" + (f" ({r['time_note']})" if r.get("time_note") else "")
    s += "; it can move that session" if fs == d else f"; the first Indian session that can trade it is {_dw(fs)}"
    if r.get("kind") in SCHEDULED:
        s += ("; the options line treats that session as an event day" if r.get("status") == "official" and fs == d
              else "; not yet official, so the options line does not treat it as an event day")
    return s + "."


def ahead(today: dt.date | None = None, n: int = 8, file: Path | None = None, hol: set | None = None) -> list[dict]:
    hol = _holidays() if hol is None else hol
    today = today or dt.datetime.now(IST).date()
    since = (today - dt.timedelta(days=1)).isoformat()
    out = []
    for r in rows(file):
        if r["date"] < since:
            continue
        fs = first_session(r, hol)
        out.append({**r, "first_session": fs.isoformat(), "first_session_words": _dw(fs), "day_words": _dw(dt.date.fromisoformat(r["date"])),
                    "options_line_event_day": bool(r.get("kind") in SCHEDULED and r.get("status") == "official" and fs.isoformat() == r["date"]),
                    "words": sentence(r, hol)})
    return out[:n]


def for_session(session: str, file: Path | None = None, hol: set | None = None) -> dict:
    """What the calendar says for one session: what falls inside it, what comes out after its close (that evening, for the next session),
    what it is the first session to trade, and the next row after it."""
    hol = _holidays() if hol is None else hol
    d = dt.date.fromisoformat(session)
    during, tonight, digest, nxt = [], [], [], None
    for r in rows(file):
        fs, rd = first_session(r, hol), dt.date.fromisoformat(r["date"])
        row = {**r, "words": sentence(r, hol), "first_session": fs.isoformat()}
        if rd == d and fs == d:
            during.append(row)
        elif rd == d:
            tonight.append(row)
        elif fs == d and rd < d:
            digest.append(row)
        elif rd > d and nxt is None:
            nxt = row
    return {"session": session, "during": during, "after_close": tonight, "first_session_for": digest, "next": nxt,
            "options_line_event_day": d in scheduled_ahead(file, hol)}


def build(today: dt.date | None = None, write: bool = True) -> dict:
    out = {"built_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "owner": "india/registrations/calendar_ahead.json",
           "events": ahead(today, 10),
           "how": ("the dated events Ananta keeps from each owner's published schedule; say the event, its day and time in India, and the first Indian "
                   "session that can trade it. Only an official RBI decision, Budget or election-counting day is an event day for the options line; "
                   "no other rule trades on events")}
    if write:
        p = paths.manifest_dir() / "calendar.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    return out


if __name__ == "__main__":
    for e in build()["events"]:
        print(e["words"])
    sys.exit(0)
