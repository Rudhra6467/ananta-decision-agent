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
    "com.ananta.india.autologin": (["07:10", "07:22"], None),
    "com.ananta.india.sp1paper": (["07:30"], None),
    "com.ananta.india.paper": (["08:00"], None),
    "com.ananta.india.spreads": (["08:05"], WEEKDAYS),
    "com.ananta.india.netnotes": (["08:10"], None),
    "com.ananta.india.findings": (["08:20"], None),
    "com.ananta.india.morningview": (["08:30"], None),
    "com.ananta.india.shadowtrader": (["08:36"], None),
    "com.ananta.india.openingview": (["10:20"], None),
    "com.ananta.india.postclose": (["15:50"], WEEKDAYS),
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
