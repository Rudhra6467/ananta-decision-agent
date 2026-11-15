"""Install the two digest jobs (src/intelligence/digest.py) into ~/Library/LaunchAgents and load them.

  python scripts/install_digest_jobs.py           write both plists and (re)load them
  python scripts/install_digest_jobs.py --print   show the plists, change nothing

com.ananta.digest.morning  09:30 Toronto every day
com.ananta.digest.night    09:12 IST every day (jarvis/india/schedule.py TARGETS keeps it on Indian time across Toronto's clock changes)
Both run scripts/send_digest.py from the live checkout with the jarvis environment, like the weekly exam."""
from __future__ import annotations

import os
import plistlib
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
LIVE = "/Users/vamsie/code/ananta-agent-research"
PY = "/Users/vamsie/ananta_venvs/jarvis/bin/python"
AGENTS = Path.home() / "Library" / "LaunchAgents"


def plist(slot: str, when) -> dict:
    return {"Label": f"com.ananta.digest.{slot}", "WorkingDirectory": LIVE, "EnvironmentVariables": {"PYTHONPATH": "."},
            "ProgramArguments": [PY, "scripts/send_digest.py", slot], "StartCalendarInterval": when,
            "StandardOutPath": f"/Users/vamsie/ananta_runs/digest_{slot}.log", "StandardErrorPath": f"/Users/vamsie/ananta_runs/digest_{slot}.log"}


def main(argv: list[str]) -> int:
    from jarvis.india import schedule

    night = schedule.wanted("com.ananta.digest.night")
    jobs = {"morning": plist("morning", {"Hour": 9, "Minute": 30}), "night": plist("night", night[0] if len(night) == 1 else night)}
    for slot, d in jobs.items():
        if "--print" in argv:
            print(plistlib.dumps(d).decode())
            continue
        p = AGENTS / f"{d['Label']}.plist"
        p.write_bytes(plistlib.dumps(d))
        uid = os.getuid()
        subprocess.run(["launchctl", "bootout", f"gui/{uid}", str(p)], capture_output=True)
        r = subprocess.run(["launchctl", "bootstrap", f"gui/{uid}", str(p)], capture_output=True, text=True)
        print(d["Label"], "loaded" if r.returncode == 0 else f"load failed: {r.stderr.strip()}", d["StartCalendarInterval"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
