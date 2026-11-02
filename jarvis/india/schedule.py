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

IST = ZoneInfo("Asia/Kolkata")
TOR = ZoneInfo("America/Toronto")
AGENTS = Path(os.path.expanduser("~/Library/LaunchAgents"))
LOG = Path(os.path.expanduser("~/ananta_runs/india_schedule.log"))
WEEKDAYS = (0, 1, 2, 3, 4)          # Mon-Fri in India (Python weekday numbers)

# label: (Indian times, Indian weekdays or None for every day). The order of the morning chain matters: sign-in, the options plan, the practice
# book, spreads, net notes, findings, the morning view (08:30), the shadow trader, the opening update after the first hour; then the post-close fetch.
TARGETS: dict[str, tuple[list[str], tuple[int, ...] | None]] = {
    # 2 Nov (Madhav: "yes"): the sign-in lapses at 06:00 IST; signing in at 06:05 closes the evening gap (7:30-8:40 pm Toronto) when live
    # prices failed. 06:20 retries; 07:10 is the old time, kept as a backup (the job skips when the token is still valid)
    "com.ananta.india.autologin": (["06:05", "06:20", "07:10"], None),
    "com.ananta.india.sp1paper": (["07:30"], None),
    "com.ananta.india.paper": (["08:00"], None),
    "com.ananta.india.spreads": (["08:05"], WEEKDAYS),
    "com.ananta.india.netnotes": (["08:10"], None),
    "com.ananta.india.findings": (["08:20"], None),
    "com.ananta.india.morningview": (["08:30"], None),
    "com.ananta.india.shadowtrader": (["08:36"], None),
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
    ("com.ananta.india.postclose", "the closing index bars, the chart readings and a first market summary"),
    ("com.ananta.india.recorder_noon", "the day's 1-minute options and currency bars"),
    ("com.ananta.india.nightly", "the official NSE day file (every stock's close), the chart readings, the stock quote book and the market summary (P/E, futures positions)"),
    ("com.ananta.india.evening", "the big evening run: FII/DII flows and big deals, the Zerodha snapshot, the managed book's fills and its next plan, the options line's score, the teachers' forward checks"),
    ("com.ananta.india.autologin", "the morning sign-in to Zerodha"),
    ("com.ananta.india.sp1paper", "the options line's plan for the session"),
    ("com.ananta.india.paper", "the practice book's picks for the session, the daily call, the missed moves, the comparison traders and the reconstruction (the coach's replay)"),
    ("com.ananta.india.findings", "the night's findings"),
    ("com.ananta.india.morningview", "the morning view (plan, levels to watch, honest chances)"),
    ("com.ananta.india.openingview", "the opening update after the first hour"),
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
            "09:15, 09:30 and 09:45 IST, in its ledger the moment it decides.")


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
