"""Send one twice-daily digest (src/intelligence/digest.py): everything routine that waited since the last digest, in one phone note.

  python scripts/send_digest.py morning      launchd com.ananta.digest.morning (09:30 Toronto)
  python scripts/send_digest.py night        launchd com.ananta.digest.night (09:12 IST, kept on Indian time by jarvis/india/schedule.py)
  python scripts/send_digest.py show         what is waiting, sent nothing

Runs from the live checkout with the service's environment rebuilt from the agent's .env (scripts/run_agent_exam.load_env), so the
phone topic is the one the service uses. Prints one line; a failed push leaves the notes waiting for the next digest."""
from __future__ import annotations

import sys
import time
from datetime import datetime, time as dtime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main(argv: list[str]) -> int:
    slot = argv[1] if len(argv) > 1 else "show"
    from scripts.run_agent_exam import load_env

    load_env()
    from src.intelligence import digest
    from src.intelligence.paper_watch import push_phone

    if slot == "show":
        p = digest.pending()
        print(f"{len(p)} waiting:", "; ".join(x["title"] for x in p) or "nothing")
        return 0
    if slot not in ("morning", "night"):
        print(__doc__)
        return 2
    if slot == "night":
        _wait_for_preopen(digest)
    for attempt in range(TRIES):                       # a Mac just awake may not have its network yet: try again a minute later
        r = digest.send(slot, lambda t, b: push_phone(t, b, level="EVENT"))
        print(r)
        if not r.startswith("not sent"):
            return 0
        if attempt < TRIES - 1:
            time.sleep(GAP_S)
    return 1


TRIES, GAP_S, PREOPEN_WAIT_S = 5, 60, 150


def _wait_for_preopen(digest) -> None:
    """On an Indian session day the pre-open read (09:09 IST) belongs in the night digest (09:12 IST). After the Mac wakes, launchd may
    start both at once: wait up to PREOPEN_WAIT_S for today's pre-open note, then send whatever there is."""
    ist = datetime.now(timezone(timedelta(hours=5, minutes=30)))
    if ist.weekday() >= 5:
        return
    tag = f"Pre-open · {ist.strftime('%m-%d')}"
    t0 = time.time()
    while time.time() - t0 < PREOPEN_WAIT_S:
        if any(x["title"].startswith(tag) for x in digest.pending()):
            return
        if _preopen_done_today(ist):                   # the job has written its log: give its note a moment to be queued
            time.sleep(15)
            return
        time.sleep(10)


def _preopen_done_today(ist) -> bool:
    log = Path.home() / "ananta_runs" / "india_preopen.log"
    try:
        return datetime.fromtimestamp(log.stat().st_mtime, ist.tzinfo).date() == ist.date() and \
            datetime.fromtimestamp(log.stat().st_mtime, ist.tzinfo).time() >= dtime(9, 0)
    except OSError:
        return False


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
