"""Print the one open list (jarvis/service/openlist.py): what needs Madhav's yes, the work to do, what waits for a date or for evidence, and
what is parked on purpose. The morning review prints its "Waiting for Madhav" and "Board" from this; a work session reads it first.

  python scripts/open_list.py            the list as plain lines
  python scripts/open_list.py --json     the list as JSON
  python scripts/open_list.py --close 134 "what closed it" [--wont] [--by "commit abc1234"]    close one item (the only way to close)
Run it in the service's environment (the same way the exam and the night test run)."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> int:
    if not os.getenv("JARVIS_DB") and not os.getenv("ANTHROPIC_API_KEY"):
        from scripts.run_agent_exam import load_env

        load_env()
    from jarvis.service import core, openlist

    j = core.from_env()
    a = sys.argv[1:]
    if "--close" in a:
        i = a.index("--close")
        by = a[a.index("--by") + 1] if "--by" in a else "a work session"
        r = openlist.close(j, int(a[i + 1]), a[i + 2], done="--wont" not in a, by=by)
        print("closed", r["label"], "as", r["status"], "|", r["note"])
        return 0
    print(json.dumps(openlist.collect(j), indent=1, default=str) if "--json" in a else openlist.text(j))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
