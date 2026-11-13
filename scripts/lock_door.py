"""The two doors of a lock (13 Nov 2026; docs/knowledge/LOCKS.md). Madhav, 13 Nov: the locks are there for the proof, and "when we
are working on the lock itself, the lock should not stop it". A lock file is never edited by hand: a change to a pinned thing goes
through one of two doors, and this tool writes the pin's history entry the same way every time.

  repair  a fault whose fix changes NO decision (a crash, a wrong record, wrong words). Fixed at once under Madhav's standing yes of
          13 Nov 2026; he is told after. Needs --what.
  change  anything that changes what Ananta buys, sells or sizes: a fault whose fix changes a decision, or a rule Madhav changes
          after seeing how it did. Needs his own yes for it (--yes, --when). The entry's date is the day the record is split at:
          results before it belong to the old rule, results from it to the new one.

    python3 scripts/lock_door.py status
    python3 scripts/lock_door.py repair <pin> --what "..."                                                       [--dry]
    python3 scripts/lock_door.py change <pin> --what "..." --yes "his words" --when "13 Nov 2026 09:00 Toronto"  [--dry]

What this tool cannot do: it cannot tell whether a change alters a decision. Calling a change a repair is the builder's word, and
the guard on that word is the one outside check every repair gets, which reads each entry this tool wrote against the commit it
names. So a door opens only on committed work (the entry names the commit), never on loose edits.

It works on the lock file of the checkout it sits in (the one *_lock.json with a test file of the same name that gives the current
hashes). It never opens a strict lock: real money, the broker account, the sealed years and the early looks have no door here."""
from __future__ import annotations

import argparse
import datetime as dt
import importlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STANDING = 'Madhav, 13 Nov 2026 07:06 Toronto: "Yes to all"'
DOORS = ("repair", "change")
LEADS = {"repair": "Repair, no rule change", "change": "A decision changes"}


class Refused(ValueError):
    """The door stays shut, and the words say why."""


def find_lock(root: Path = ROOT) -> tuple[Path, str]:
    """The checkout's lock file and the test module that gives its current hashes."""
    found = sorted(list((root / "docs" / "knowledge").glob("*_lock.json")) + list(root.glob("*/registrations/*_lock.json")))
    found = [p for p in found if (root / "tests" / f"test_{p.stem}.py").exists()]
    if len(found) != 1:
        raise Refused(f"expected one lock file with its test in {root}, found {len(found)}")
    return found[0], f"tests.test_{found[0].stem}"


def current_hashes(module: str, root: Path = ROOT) -> dict[str, str]:
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return importlib.import_module(module).current()


def committed_at(root: Path, lock_path: Path) -> str:
    """The commit a door would bless. Refused while any tracked file but the lock file itself has loose edits."""
    def git(*a: str) -> str:
        return subprocess.run(["git", "-C", str(root), *a], capture_output=True, text=True, check=True).stdout
    loose = [x[3:] for x in git("status", "--porcelain", "--untracked-files=no").splitlines() if x[3:] != str(lock_path.relative_to(root))]
    if loose:
        raise Refused(f"commit the change first: {len(loose)} tracked file(s) have loose edits ({', '.join(loose[:3])})")
    return git("rev-parse", "--short", "HEAD").strip()


def _end(lock: dict, name: str) -> tuple[str | None, str]:
    """A pin's end: (its day when the lock file gives one, the words it gives). Some ends are an event, not a day (a session count)."""
    ends = lock.get("ends") or {}
    text = str(ends.get(name) or next((v for k, v in ends.items() if k.startswith("all")), ""))
    m = re.search(r"\d{4}-\d{2}-\d{2}", text)
    return (m.group(0) if m else None), text.split(";")[0].strip()


def status(lock: dict, now: dict[str, str], today: str) -> list[dict]:
    """Each pin: as pinned or changed, its last entry's day, its end day, and whether the lock has run past it (said, never enforced)."""
    out = []
    for name, pin in lock["pins"].items():
        day, words = _end(lock, name)
        out.append({"pin": name, "state": "as pinned" if now.get(name) == pin["sha256"] else "CHANGED: it needs a door",
                    "last": (pin.get("history") or [{}])[-1].get("date"), "ends": day or words[:70], "lapsed": bool(day and today > day)})
    return out


def open_door(lock: dict, now: dict[str, str], name: str, door: str, what: str, yes: str | None = None, when: str | None = None,
              commit: str | None = None, today: str | None = None) -> dict:
    """Records one change to a pinned thing in `lock` (in place) and returns the history entry. Raises Refused with plain words."""
    today = today or dt.date.today().isoformat()
    if door not in DOORS:
        raise Refused(f"the doors are {' and '.join(DOORS)}")
    if name not in lock["pins"]:
        raise Refused(f"no pin named {name}; a strict lock (real money, the broker account, the sealed years, the early looks) has no door")
    pin = lock["pins"][name]
    if now.get(name) == pin["sha256"]:
        raise Refused(f"nothing in {name} changed: no door is needed")
    what = " ".join(str(what or "").split()).rstrip(".")
    if len(what) < 20:
        raise Refused("say what changed in a full sentence (--what)")
    if door == "repair":
        if not (lock.get("repair_door") or {}).get("since"):
            raise Refused("this lock file has no repair door (repair_door) recorded")
        note = f"{LEADS[door]}: {what}. Under the repair door: {STANDING} (docs/knowledge/LOCKS.md)."
    else:
        yes, when = " ".join(str(yes or "").split()).strip('"'), " ".join(str(when or "").split())
        if len(yes) < 2 or len(when) < 6:
            raise Refused("a change of decision needs Madhav's own yes for it: --yes with his words and --when with the day and time he said it")
        note = f'{LEADS[door]}, and the record is split at this day: {what}. Madhav, {when}: "{yes}"'
    entry = {"date": today, "approved_by": "Madhav (in chat)", "note": note, "sha256": now[name], "door": door}
    if commit:
        entry["commit"] = commit
    pin.setdefault("history", []).append(entry)
    pin["sha256"] = now[name]
    return entry


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    ap = argparse.ArgumentParser(description="The two doors of a lock (docs/knowledge/LOCKS.md).")
    ap.add_argument("door", choices=("status",) + DOORS)
    ap.add_argument("pin", nargs="?")
    ap.add_argument("--what")
    ap.add_argument("--yes")
    ap.add_argument("--when")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args(argv)
    try:
        path, module = find_lock(root)
        lock, now = json.loads(path.read_text()), current_hashes(module, root)
        if a.door == "status":
            for r in status(lock, now, dt.date.today().isoformat()):
                print(f"{r['pin']:<20} {r['state']:<28} last {r['last']}  ends {r['ends'] or 'no date'}"
                      + ("  PAST ITS END DAY: Madhav renews it or it is dropped; until then it stops nothing" if r["lapsed"] else ""))
            return 0
        entry = open_door(lock, now, a.pin or "", a.door, a.what or "", a.yes, a.when)
        entry["commit"] = committed_at(root, path)             # only committed work is blessed; the entry names it
    except Refused as e:
        print("refused:", e)
        return 1
    if a.dry:
        print("dry, nothing written:", entry["note"])
        return 0
    path.write_text(json.dumps(lock, indent=1, ensure_ascii=False) + "\n")
    print(f"recorded on {a.pin} ({a.door}, commit {entry['commit']}):", entry["note"])
    print("next: commit the lock file with a change-book line, and tell Madhav in the next message" if a.door == "repair" else
          f"next: commit the lock file with a change-book line; results are counted apart before and from {entry['date']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
