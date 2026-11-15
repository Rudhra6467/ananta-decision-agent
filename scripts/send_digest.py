"""Send one twice-daily digest (src/intelligence/digest.py): everything routine that waited since the last digest, in one phone note.

  python scripts/send_digest.py morning      launchd com.ananta.digest.morning (09:15 Toronto)
  python scripts/send_digest.py night        launchd com.ananta.digest.night (09:12 IST, kept on Indian time by jarvis/india/schedule.py)
  python scripts/send_digest.py show         what is waiting, sent nothing

Runs from the live checkout with the service's environment rebuilt from the agent's .env (scripts/run_agent_exam.load_env), so the
phone topic is the one the service uses. Prints one line; a failed push leaves the notes waiting for the next digest."""
from __future__ import annotations

import sys
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
    print(digest.send(slot, lambda t, b: push_phone(t, b, level="EVENT")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
