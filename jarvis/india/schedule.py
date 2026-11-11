"""The India jobs keep Indian time across Toronto's clock changes (2 Nov 2026).

launchd fires on the Mac's local clock (Toronto). The India jobs were set on 23 Oct for Toronto summer time (9.5 h behind India); on Sunday 1 Nov
Toronto went to winter time (10.5 h behind) and every India job moved an hour later in India: Monday's morning view was written at 09:30 IST,
fifteen minutes AFTER the open (it is meant for 08:30), and the opening update came at 11:20 instead of 10:20. Nobody noticed.

TARGETS holds each job's Indian time. audit() says which plists are off for today's offset; fix() rewrites their times and reloads them.
It runs daily (com.ananta.india.schedulecheck, 15:00 and 18:00 Toronto, before the evening chain) and from the nightly replay, and it pushes to
the phone whenever it changes a job, so the next clock change (Sunday 14 Mar 2027) is handled the same day.

  python -m jarvis.india.schedule            audit only
  python -m jarvis.india.schedule fix        rewrite and reload the plists that are off
"""
from __future__ import annotations

import datetime as dt
import json
import os
import plistlib
import subprocess
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

from jarvis.india import askwords

IST = ZoneInfo("Asia/Kolkata")
TOR = ZoneInfo("America/Toronto")
AGENTS = Path(os.path.expanduser("~/Library/LaunchAgents"))
LOG = Path(os.path.expanduser("~/ananta_runs/india_schedule.log"))
WEEKDAYS = (0, 1, 2, 3, 4)          # Mon-Fri in India (Python weekday numbers)

# label: (Indian times, Indian weekdays or None for every day). The order of the morning chain matters: sign-in, the options plan, the practice
# book, spreads, the morning view (08:30), the shadow trader, the opening update after the first hour; then the post-close fetch.
TARGETS: dict[str, tuple[list[str], tuple[int, ...] | None]] = {
    # 2 Nov (Madhav: "yes"): the sign-in lapses at 06:00 IST; signing in at 06:05 closes the evening gap (7:30-8:40 pm Toronto) when live
    # prices failed. 06:20 retries; 07:10 is the old time, kept as a backup (the job skips when the token is still valid)
    "com.ananta.india.autologin": (["06:05", "06:20", "07:10"], None),
    # 3 Nov (Madhav: "Yes for all", the Map's change 8): the 47-step evening run is split. Its Zerodha steps (the account snapshot, the
    # options recorder, the SP1 replay, the index bars) run after the 06:05 sign-in; on 2 Nov they ran at 05:30 IST on a lapsing token and failed.
    # The rest of the evening run follows once they are in.
    "com.ananta.india.evening_zerodha": (["06:30"], None),
    "com.ananta.india.evening": (["06:50"], None),
    # 3 Nov (the Map's change 8): the studies and write-ups (trials, the tilt book, RX1 and RS trials, write-ups, the knowledge map) in their own job
    "com.ananta.india.studies": (["07:05"], None),
    "com.ananta.india.sp1paper": (["07:30"], None),
    "com.ananta.india.paper": (["08:00"], None),
    "com.ananta.india.spreads": (["08:05"], WEEKDAYS),
    # 3 Nov (Madhav: "Yes for all", the Map's changes 1 and 12): the findings job and the paid web notes are stopped; their plists are kept in
    # ~/Library/LaunchAgents/stripped-2026-11-03 so either can come back
    "com.ananta.india.morningview": (["08:30"], None),
    "com.ananta.india.shadowtrader": (["08:36"], None),
    # 5 Nov (Madhav: "yes to all"): the pre-open read, a minute after NSE's 09:00-09:08 IST pre-open has matched the opening prices
    "com.ananta.india.preopen": (["09:09"], WEEKDAYS),
    "com.ananta.india.openingview": (["10:20"], None),
    "com.ananta.india.postclose": (["15:50"], WEEKDAYS),
    # 2 Nov: the fact map at three moments - mid-session, after the close before the day's file, after the nightly build
    "com.ananta.india.factmap": (["00:05", "11:00", "16:10"], None),
}


def wanted(label: str, on: dt.date | None = None) -> list[dict]:
    """The launchd StartCalendarInterval entries (Toronto clock) that put the job at its Indian time, for the offset in force on the date."""
    times, days = TARGETS[label]
    on = on or dt.datetime.now(IST).date()
    out = []
    for hhmm in times:
        h, m = map(int, hhmm.split(":"))
        if days is None:
            t = dt.datetime.combine(on, dt.time(h, m), IST).astimezone(TOR)
            out.append({"Hour": t.hour, "Minute": t.minute})
            continue
        monday = on - dt.timedelta(days=on.weekday())
        for wd in days:
            t = dt.datetime.combine(monday + dt.timedelta(days=wd), dt.time(h, m), IST).astimezone(TOR)
            out.append({"Weekday": (t.weekday() + 1) % 7, "Hour": t.hour, "Minute": t.minute})    # launchd: 0 = Sunday
    return out


def _norm(x) -> list[dict]:
    xs = x if isinstance(x, list) else [x] if x else []
    return sorted(({k: int(v) for k, v in e.items()} for e in xs), key=lambda e: (e.get("Weekday", -1), e["Hour"], e["Minute"]))


def audit(on: dt.date | None = None) -> list[dict]:
    off = []
    for label in TARGETS:
        p = AGENTS / f"{label}.plist"
        if not p.exists():
            off.append({"label": label, "problem": "plist missing"})
            continue
        have = _norm(plistlib.loads(p.read_bytes()).get("StartCalendarInterval"))
        want = _norm(wanted(label, on))
        if have != want:
            off.append({"label": label, "have": have, "want": want})
    return off


def fix(on: dt.date | None = None, reload: bool = True) -> list[dict]:
    changed = []
    uid = os.getuid()
    for o in audit(on):
        if "want" not in o:
            continue
        p = AGENTS / f"{o['label']}.plist"
        d = plistlib.loads(p.read_bytes())
        d["StartCalendarInterval"] = o["want"] if len(o["want"]) > 1 else o["want"][0]
        p.write_bytes(plistlib.dumps(d))
        if reload:
            subprocess.run(["launchctl", "bootout", f"gui/{uid}", str(p)], capture_output=True)
            subprocess.run(["launchctl", "bootstrap", f"gui/{uid}", str(p)], capture_output=True)
        changed.append(o)
    if changed:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a") as fh:
            fh.write(json.dumps({"t": dt.datetime.now().isoformat(timespec="seconds"), "changed": changed}) + "\n")
    return changed


def words(changed: list[dict]) -> str:
    def first(es):
        return f"{es[0]['Hour']:02d}:{es[0]['Minute']:02d}" if es else "?"
    return "India jobs moved to keep Indian time after the clock change: " + "; ".join(
        f"{c['label'].rsplit('.', 1)[-1]} {first(c.get('have') or [])} -> {first(c['want'])} Toronto" for c in changed)


# ---- when things happen, in words, from the jobs themselves -------------------------------------------------------------------------------------
# Independent audit, 2 Nov: Ananta told Madhav "the picks come with the 7 pm run" (they come at 9:30 pm), "the day file lands at 7 pm" (12:45 pm),
# and Toronto times written by hand did not move with the clock change. Every time Ananta says is now read from the launchd jobs.
DAY = [   # (job, what it brings), in the order of Madhav's evening and night
    ("com.ananta.india.postclose", "the closing index bars, the chart readings, a first market summary and the day's company filings so far (what your stocks filed)"),
    ("com.ananta.india.sp1paper.score", "the options line's score for the session (once a day)"),
    ("com.ananta.india.recorder_noon", "the day's 1-minute options and currency bars and the Zerodha snapshot"),
    ("com.ananta.india.nightly", "the official NSE day file (every stock's close), the chart readings, the stock quote book and the market summary (P/E, futures positions); the one place the quote book and the market summary are built (3 Nov)"),
    ("com.ananta.india.autologin", "the morning sign-in to Zerodha"),
    ("com.ananta.india.evening_zerodha", "the Zerodha part of the evening: the account snapshot, the options recorder's second fetch, the options line's replay check and the index bars"),
    ("com.ananta.india.evening", "the evening run: FII/DII flows and big deals, the managed book's fills and its next plan, the teachers' forward checks"),
    ("com.ananta.india.studies", "the studies: the paper trials' clocks, the long-term tilt book, the write-ups and the knowledge map"),
    ("com.ananta.india.sp1paper", "the options line's plan for the session"),
    ("com.ananta.india.paper", "the practice book's picks for the session, the daily call, the missed moves, the comparison traders and the reconstruction (the coach's replay)"),
    ("com.ananta.india.morningview", "the morning view, written once on the session's own morning: your holdings' filings, GIFT Nifty's indicated open, the options line's plan, levels and events to watch, honest chances"),
    ("com.ananta.india.preopen", "the pre-open read sent to your phone: the indicated open, what changed since the morning view, and the options line's plan for that open"),
    ("com.ananta.india.openingview", "the opening update after the first hour, with the second look against the pre-open"),
]


def toronto_times(label: str) -> list[str]:
    """The job's actual Toronto times from its launchd file ('HH:MM'), whatever the season."""
    try:
        d = plistlib.loads((AGENTS / f"{label}.plist").read_bytes())
    except Exception:  # noqa: BLE001
        return []
    sci = d.get("StartCalendarInterval")
    sci = sci if isinstance(sci, list) else ([sci] if sci else [])
    return sorted({f"{int(x.get('Hour', 0)):02d}:{int(x.get('Minute', 0)):02d}" for x in sci})


def _say(hhmm: str) -> str:
    h, m = map(int, hhmm.split(":"))
    return f"{(h % 12) or 12}{':%02d' % m if m else ''} {'am' if h < 12 else 'pm'}"


def toronto_of(ist_hhmm: str, on: dt.date) -> str:
    """'3:50 am' Toronto for an IST clock time on a given Indian date (7 Nov 2026: the Muhurat session's hours, never hand-written)."""
    h, m = map(int, ist_hhmm.split(":"))
    return _say(dt.datetime.combine(on, dt.time(h, m), IST).astimezone(TOR).strftime("%H:%M"))


def ist_of(hhmm: str, on: dt.date | None = None) -> str:
    on = on or dt.datetime.now(TOR).date()
    h, m = map(int, hhmm.split(":"))
    return dt.datetime.combine(on, dt.time(h, m), TOR).astimezone(IST).strftime("%H:%M IST")


def at(label: str) -> str:
    """'9:30 pm Toronto (08:00 IST)' for a job; the first time when it runs more than once ('' when the job is missing)."""
    ts = toronto_times(label)
    if label == "com.ananta.india.nightly":
        ts = [t for t in ts if t >= "06:00"] or ts         # its 02:30 run is a catch-up
    return f"{_say(ts[0])} Toronto ({ist_of(ts[0])})" if ts else ""


def day_words() -> str:
    """The evening-and-night chain in Toronto time, read from the jobs."""
    parts = [f"{at(job)}: {what}" for job, what in DAY if at(job)]
    return ("When things land (Toronto time, read from the jobs themselves): live index and stock prices from Zerodha any time during the "
            "session (09:15-15:30 IST) and the closing prices minutes after the close; " + "; ".join(parts) + ". The options line decides live at "
            f"{askwords.window_words()} IST, in its ledger the moment it decides.")


def main() -> int:
    if (sys.argv[1:] or ["audit"])[0] == "fix":
        ch = fix()
        print(words(ch) if ch else "India schedule: every job is on its Indian time.")
        if ch:
            try:
                from jarvis.india import replay
                replay._ntfy("Ananta schedule", words(ch))
            except Exception as exc:  # noqa: BLE001
                print(f"push skipped: {exc}")
        return 0
    off = audit()
    print(json.dumps(off, indent=1) if off else "India schedule: every job is on its Indian time.")
    return 1 if off else 0


if __name__ == "__main__":
    raise SystemExit(main())
