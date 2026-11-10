"""Save the day's records to git each morning (Madhav, 10 Nov 2026: "yes to all your recommendations", open-list flag 75: "The daily records
Ananta writes (review pages, replay and exam results) sit unsaved in the code folder").

Ananta's own jobs write records every night: the replay and the exam results, the night test, the maps, the other-traders and universe pages,
the India pages in the records branch. Nothing saved them, so they sat uncommitted for days and were lost if the folder was damaged.

Every morning at 06:50 Toronto (launchd com.ananta.records, scripts/launchd/com.ananta.records.plist) this:
  * commits ONLY the files on the allowlist below, each added by name (never `git add -A`), in each of the two checkouts;
  * never commits a file that a lock pins, code, or anything outside the allowlist; what it leaves out it names in the log;
  * skips a checkout that is on the wrong branch, in the middle of a merge or rebase, or locked by another git command;
  * pushes; a push that fails is said in the log and tried again the next morning (the commit is kept).
One line per checkout goes to ~/ananta_runs/records_commit.log, which the lost-runs check watches (runcheck_parts: records_commit).

  python scripts/commit_records.py            commit and push
  python scripts/commit_records.py --dry      say what would be committed, change nothing
Nothing here trades or changes a rule."""
from __future__ import annotations

import fnmatch
import json
import re
import subprocess
import sys
import time
from pathlib import Path

HOME = Path.home()
CHECKOUTS = [
    {"name": "agent", "dir": HOME / "code" / "ananta-agent-research", "branch": "jarvis-4", "lock": "docs/knowledge/crypto_lock.json",
     "allow": ["docs/repair_shop/daily/*.md", "docs/repair_shop/daily/*.jsonl", "docs/repair_shop/weekly/*.md", "docs/repair_shop/map/*.md",
               "docs/repair_shop/replay/*.json", "docs/repair_shop/replay/*.jsonl", "docs/repair_shop/exam/*.json", "docs/repair_shop/exam/*.jsonl",
               "docs/repair_shop/factmap/*", "docs/repair_shop/nightcheck/*", "docs/knowledge/india_map.json"]},
    {"name": "records", "dir": HOME / "code" / "ananta-records", "branch": "records", "lock": "india/registrations/india_lock.json",
     "allow": ["india/registrations/reviews/*.md", "india/registrations/data_audit_v1.md", "india/registrations/evidence_staircase.json",
               "india/registrations/india_morning.md", "india/registrations/india_readmodel.md", "india/registrations/ledger_results.md",
               "india/registrations/missed_drafts.jsonl", "india/registrations/missed_movers.md", "india/registrations/missing_inputs.md",
               "india/registrations/morningview.md", "india/registrations/options_realism.md", "india/registrations/others_league.md",
               "india/registrations/premarket_inputs.md", "india/registrations/reconstruction.md", "india/registrations/reconstruction_queue.jsonl",
               "india/registrations/selection_bias.md", "india/registrations/research_tracker.md"]},
]
LOG = HOME / "ananta_runs" / "records_commit.log"
# The family's names never go to git (the same check every scheduled task runs before a commit). A file whose new lines carry one is left
# out and named in the log; it stays on the Mac.
PRIVATE = re.compile(r"babji|murali|ramya|radha|mahira|nanu|nellore|atlanta|vimla|vamsi krishna", re.I)
NOT_PRIVATE = re.compile(r"baagunnanu", re.I)


def git(d: Path, *args: str, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=d, capture_output=True, text=True, timeout=timeout)


def pinned(c: dict) -> set[str]:
    """Every file a lock pins in this checkout (never committed here, whatever the allowlist says)."""
    try:
        d = json.loads((c["dir"] / c["lock"]).read_text())
    except (OSError, ValueError):
        return set()
    out = {c["lock"]}
    for v in (d.get("pins") or d).values():
        if isinstance(v, dict):
            for k in ("files", "file", "path", "paths"):
                x = v.get(k)
                out |= set(x) if isinstance(x, list) else ({x} if isinstance(x, str) else set())
    return out


def changed(c: dict) -> list[str]:
    r = git(c["dir"], "status", "--porcelain", "--untracked-files=all")
    return [ln[3:].strip().strip('"') for ln in r.stdout.splitlines() if ln.strip()]


def private(d: Path, f: str) -> bool:
    """True when the file's new lines name a family member (a tracked file: its added lines; a new file: all of it)."""
    tracked = git(d, "ls-files", "--error-unmatch", "--", f).returncode == 0
    text = git(d, "diff", "-U0", "--", f).stdout if tracked else ""
    if tracked:
        text = "\n".join(ln[1:] for ln in text.splitlines() if ln.startswith("+") and not ln.startswith("+++"))
    else:
        try:
            text = (d / f).read_text(errors="ignore")
        except OSError:
            return False
    return any(not NOT_PRIVATE.search(m.string[max(0, m.start() - 6): m.end() + 6]) for m in PRIVATE.finditer(text))


def plan(c: dict) -> dict:
    """What would be committed in one checkout, and why anything is not."""
    d = c["dir"]
    if not d.exists():
        return {"skip": "the checkout is not there"}
    gitdir = Path(git(d, "rev-parse", "--git-dir").stdout.strip() or ".git")
    gitdir = gitdir if gitdir.is_absolute() else d / gitdir
    common = Path(git(d, "rev-parse", "--git-common-dir").stdout.strip() or ".git")
    common = common if common.is_absolute() else d / common
    if (gitdir / "index.lock").exists():
        return {"skip": "another git command holds the lock"}
    if any((gitdir / x).exists() for x in ("MERGE_HEAD", "rebase-merge", "rebase-apply", "CHERRY_PICK_HEAD")):
        return {"skip": "a merge or rebase is in progress"}
    br = git(d, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    if br != c["branch"]:
        return {"skip": f"on branch {br}, not {c['branch']}"}
    pins = pinned(c)
    take, left = [], []
    for f in changed(c):
        if f in pins:
            left.append(f"{f} (pinned)")
        elif any(fnmatch.fnmatch(f, p) for p in c["allow"]):
            if private(d, f):
                left.append(f"{f} (names family; kept on the Mac)")
            else:
                take.append(f)
        else:
            left.append(f)
    return {"take": sorted(take), "left": sorted(left), "common": str(common)}


def run(dry: bool = False) -> list[dict]:
    out = []
    day = time.strftime("%Y-%m-%d")
    for c in CHECKOUTS:
        p = plan(c)
        row = {"checkout": c["name"], **{k: v for k, v in p.items() if k != "common"}}
        if p.get("skip") or not p.get("take") or dry:
            out.append(row)
            continue
        d = c["dir"]
        a = git(d, "add", "--", *p["take"])
        if a.returncode:
            row["error"] = "add failed: " + (a.stderr or a.stdout).strip()[:200]
            out.append(row)
            continue
        msg = (f"Daily records {day}: {len(p['take'])} file{'s' if len(p['take']) != 1 else ''} written by Ananta's own nightly jobs\n\n"
               "Saved by scripts/commit_records.py (Madhav's yes of 10 Nov 2026, open-list flag 75). Only allowlisted record files, each by name;\n"
               "no code, no pinned file.\n\nNo-change-line: generated records only")
        cm = git(d, "commit", "-q", "-m", msg, timeout=300)
        if cm.returncode:
            git(d, "reset", "-q", "--", *p["take"])                 # leave the index as it was
            row["error"] = "commit failed: " + (cm.stderr or cm.stdout).strip()[-300:]
            out.append(row)
            continue
        row["commit"] = git(d, "rev-parse", "--short", "HEAD").stdout.strip()
        ps = git(d, "push", "-q", "origin", c["branch"], timeout=180)
        row["pushed"] = ps.returncode == 0
        if ps.returncode:
            row["push_error"] = (ps.stderr or ps.stdout).strip()[-200:]
        out.append(row)
    return out


def main() -> int:
    dry = "--dry" in sys.argv
    rows = run(dry=dry)
    stamp = time.strftime("%Y-%m-%d %H:%M")
    for r in rows:
        bits = [f"{stamp} {r['checkout']}:"]
        if r.get("skip"):
            bits.append(f"skipped ({r['skip']})")
        elif r.get("error"):
            bits.append(f"FAILED: {r['error']}")
        elif not r.get("take"):
            bits.append("nothing new to save")
        elif dry:
            bits.append(f"would save {len(r['take'])}: {', '.join(r['take'][:12])}" + (" …" if len(r["take"]) > 12 else ""))
        else:
            bits.append(f"saved {len(r['take'])} in {r['commit']}" + ("; pushed" if r.get("pushed") else f"; PUSH FAILED: {r.get('push_error')}"))
        if r.get("left"):
            bits.append(f"| left out ({len(r['left'])}): {', '.join(r['left'][:8])}" + (" …" if len(r["left"]) > 8 else ""))
        print(" ".join(bits), flush=True)
    return 1 if any(r.get("error") for r in rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
