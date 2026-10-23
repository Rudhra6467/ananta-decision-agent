"""The repair worker (Madhav, 23 Oct 2026): picks up the fixes he chose with the app's Flag button, builds them, checks them and puts the
SAFE ones live, then reports back on the request (jarvis/service/fixflow.py explains the flow).

Run every two minutes by launchd (com.ananta.repairworker) through ~/ananta_runs/svc_env_run.py, one flag at a time (a lock file).

For each flag it takes:
  1. a fresh git worktree of jarvis-4 in ~/ananta_repair/<num> (no .env, no keys: those files are not in git);
  2. Claude Code, headless, with the flag, the chosen fix and the rules below; tools limited to reading, editing and running tests; a dollar
     cap per fix (FIX_BUDGET_USD) and a daily cap (WORKER_DAILY);
  3. its own checks, by code, never by the AI: every changed file is inside SAFE_PATHS and none is pinned by a lock; the lock tests, the
     tests of the touched area and the TypeScript check pass. A change outside the safe paths is not applied: the flag goes back to
     Madhav as "needs your yes" with the plan;
  4. deploy: fast-forward the live jarvis-4, push, then the web build (atomic swap, dist_prev kept) when app files changed, and a restart
     of the service whose files changed (crypto com.ananta.jarvis, India com.ananta.india.web) with a health check; a failed health
     check reverts the commit and restarts again;
  5. report: fixflow.report() -> the request turns DONE ("Fixed: request N" on the phone) or goes back to Madhav with the reason.

A flag in the DECISION lane gets step 2 with "write the plan only" and no code is kept.
"""
from __future__ import annotations

import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

LIVE = Path(os.getenv("ANANTA_LIVE_REPO", str(Path.home() / "code" / "ananta-agent-research")))
WORK = Path(os.getenv("ANANTA_REPAIR_DIR", str(Path.home() / "ananta_repair")))
CLAUDE = os.getenv("ANANTA_CLAUDE_CLI", str(Path.home() / "ananta_tools" / "node_modules" / ".bin" / "claude"))
PY = os.getenv("ANANTA_PY", str(Path.home() / "ananta_venvs" / "jarvis" / "bin" / "python"))
LOG = Path.home() / "ananta_runs" / "repair_worker.log"
FIX_BUDGET_USD = float(os.getenv("FIX_BUDGET_USD", "3"))
WORKER_DAILY = int(os.getenv("WORKER_DAILY", "6"))
MODEL = os.getenv("FIX_MODEL", "claude-opus-5-5")

# Where the worker may change files by itself. Everything else (trading code, the service's endpoints and sign-in, research, costs,
# the books, the gate, the locks) is a decision for Madhav.
SAFE_PATHS = (
    "jarvis/app/app/", "jarvis/app/src/",                       # screens and app code (both markets)
    "jarvis/india/views.py", "jarvis/india/voice.py", "jarvis/india/page.html",
    "jarvis/service/views.py", "jarvis/service/appmap.py", "jarvis/service/plain.py", "jarvis/service/sayshow.py",
    "jarvis/service/status_words.py", "jarvis/service/briefs.py", "jarvis/service/speech.py", "jarvis/service/concepts.py",
    "tests/", "docs/repair_shop/",
)
NEVER = ("jarvis/app/dist", ".env", "docs/knowledge/", "src/", "scripts/", "jarvis/service/app.py", "jarvis/india/service.py",
         "jarvis/app/src/api.ts", "jarvis/app/app.json", "jarvis/app/package.json", "jarvis/app/package-lock.json")


def log(msg: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")


def pinned_files() -> set[str]:
    """Every file a crypto-lock pin names (docs/knowledge/crypto_lock.json) or the lock test reads."""
    out: set[str] = set()
    lock = json.loads((LIVE / "docs" / "knowledge" / "crypto_lock.json").read_text())
    for p in lock["pins"].values():
        out.update(p.get("files") or [])
    test = (LIVE / "tests" / "test_crypto_lock.py").read_text()
    out.update(re.findall(r'"((?:src|jarvis|docs)/[\w/.-]+\.(?:py|json|md))"', test))
    return out


def allowed(files: list[str], pinned: set[str]) -> tuple[bool, list[str]]:
    """(ok, refused): ok only when every changed file is in SAFE_PATHS, in no NEVER prefix, and pinned by no lock."""
    bad = [f for f in files if f in pinned or any(f.startswith(n) or f.endswith(n) for n in NEVER)
           or not any(f.startswith(s) or f == s for s in SAFE_PATHS)]
    return (not bad and bool(files)), bad


def sh(cmd: list[str], cwd: Path, timeout: int = 900, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout, env=env)


RULES = """You are fixing one flagged problem in Ananta, Madhav's paper-trading app. Work only inside this folder (a git worktree).
Rules that always hold:
- Change only screens, words, voice, reports and display code: files under jarvis/app/app/, jarvis/app/src/, jarvis/india/views.py,
  jarvis/india/voice.py, jarvis/service/views.py, appmap.py, plain.py, sayshow.py, status_words.py, briefs.py, speech.py, concepts.py,
  and tests/. Never touch trading code, sizes, costs, stops, exits, strategies, the gate, the locks, sign-in, endpoints, src/ or scripts/.
  If the fix needs any of those, change nothing and explain why in your final message.
- Never read or print .env files, keys, ~/ananta_private, ~/.ssh or anything outside this folder.
- Keep the change as small as the fix needs. Add or update a test that would have caught the problem when that is possible.
- Run the tests of the area you changed (for example: {py} -m pytest -q tests/test_<area>.py) and, for app files,
  "cd jarvis/app && npx tsc --noEmit". Do not commit; the worker commits.
- End with a short plain-English summary for Madhav (two or three sentences): what was wrong and what you changed.
"""


def run_claude(wt: Path, flag: dict, plan_only: bool) -> tuple[str, float]:
    o = flag["options"]["options"][flag["choice"]]
    task = (f"The flag ({flag['market']} market, screen \"{flag['screen']}\", route {flag['route']}):\n{flag.get('text', '')}\n\n"
            f"Madhav chose this fix: {o['title']}: {o['what']}\n\n"
            + ("WRITE A PLAN ONLY. Do not change any file. Find the cause, say which files a fix would touch and why it needs Madhav's "
               "decision, and propose the smallest change with how it would be tested." if plan_only else "Make this fix now."))
    cmd = [CLAUDE, "-p", task, "--append-system-prompt", RULES.format(py=PY), "--output-format", "json", "--model", MODEL,
           "--max-budget-usd", str(FIX_BUDGET_USD),
           "--allowedTools", "Read", "Glob", "Grep", *( [] if plan_only else ["Edit", "Write"]),
           "Bash(git diff:*)", "Bash(git status:*)", f"Bash({PY} -m pytest:*)", "Bash(npx tsc:*)", "Bash(cd jarvis/app && npx tsc:*)",
           "--disallowedTools", "Read(**/.env*)", "Read(~/ananta_private/**)", "Read(~/.ssh/**)", "WebFetch", "WebSearch"]
    r = sh(cmd, wt, timeout=1800)
    try:
        out = json.loads(r.stdout)
        return str(out.get("result") or "")[:1500], float(out.get("total_cost_usd") or 0.0)
    except (ValueError, TypeError):
        raise RuntimeError(f"Claude Code gave no result (rc {r.returncode}): {(r.stderr or r.stdout)[-300:]}")


def changed(wt: Path) -> list[str]:
    r = sh(["git", "status", "--porcelain", "--untracked-files=all"], wt)
    return sorted({line[3:].strip().strip('"') for line in r.stdout.splitlines() if line.strip()})


def checks(wt: Path, files: list[str]) -> tuple[bool, str]:
    tests = {"tests/test_crypto_lock.py", "tests/test_reads.py"}
    for f in files:
        if f.startswith("tests/") and f.endswith(".py"):
            tests.add(f)
    if any(f.startswith("jarvis/app/") for f in files):
        tests.add("tests/test_app_theme.py")
    if any(f.startswith("jarvis/service/briefs.py") or f.startswith("jarvis/service/appmap.py") or f.startswith("jarvis/service/sayshow.py")
           for f in files):
        tests.add("tests/test_ask_ananta.py")
    if any(f.startswith("jarvis/india/") for f in files):
        tests.update(str(p.relative_to(wt)) for p in (wt / "tests").glob("test_india*.py"))
    r = sh([PY, "-m", "pytest", "-q", "-x", *sorted(t for t in tests if (wt / t).exists())], wt, timeout=1200)
    if r.returncode != 0:
        return False, "tests failed: " + r.stdout[-400:]
    if any(f.startswith("jarvis/app/") for f in files):
        if not (wt / "jarvis/app/node_modules").exists():
            (wt / "jarvis/app/node_modules").symlink_to(LIVE / "jarvis/app/node_modules")
        r = sh(["npx", "tsc", "--noEmit"], wt / "jarvis/app", timeout=600)
        if r.returncode != 0:
            return False, "TypeScript check failed: " + (r.stdout or r.stderr)[-400:]
    return True, f"{len(tests)} test files and the checks passed"


def health(url: str, tries: int = 20) -> bool:
    import urllib.request

    for _ in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=5) as r:
                if r.status == 200:
                    return True
        except Exception:  # noqa: BLE001
            pass
        time.sleep(3)
    return False


def deploy(files: list[str]) -> tuple[bool, str]:
    uid = os.getuid()
    did = []
    if any(f.startswith("jarvis/app/") for f in files):
        app = LIVE / "jarvis" / "app"
        shutil.rmtree(app / "dist_new", ignore_errors=True)
        r = sh(["npx", "expo", "export", "--platform", "web", "--output-dir", "dist_new"], app, timeout=900)
        if r.returncode != 0 or not (app / "dist_new" / "index.html").exists():
            return False, "the web build failed: " + (r.stderr or r.stdout)[-300:]
        shutil.rmtree(app / "dist_prev", ignore_errors=True)
        (app / "dist").rename(app / "dist_prev")
        (app / "dist_new").rename(app / "dist")
        did.append("web build swapped (dist_prev kept)")
    restart = []
    if any(f.startswith("jarvis/service/") for f in files):
        restart.append(("com.ananta.jarvis", "http://127.0.0.1:8100/health"))
    if any(f.startswith("jarvis/india/") for f in files):
        restart.append(("com.ananta.india.web", "http://127.0.0.1:8110/health"))
    for label, url in restart:
        sh(["launchctl", "kickstart", "-k", f"gui/{uid}/{label}"], LIVE, timeout=60)
        if not health(url):
            return False, f"{label} did not answer its health check after the restart"
        did.append(f"{label} restarted and healthy")
    return True, "; ".join(did) or "no restart needed"


def work_one(j, fixflow, flag: dict) -> None:
    from jarvis.service import requests_log

    num, plan_only = flag["num"], flag["state"] == "plan"
    req = requests_log.get(j, num) or {}
    flag["text"] = req.get("text", "")
    fixflow.report(j, num, "working", "the repair worker started" + (" (plan only: near trading)" if plan_only else ""))
    wt, branch = WORK / str(num), f"repair/{num}"
    sh(["git", "worktree", "remove", "--force", str(wt)], LIVE)
    sh(["git", "branch", "-D", branch], LIVE)
    r = sh(["git", "worktree", "add", "-b", branch, str(wt), "jarvis-4"], LIVE)
    if r.returncode != 0:
        fixflow.report(j, num, "failed", f"could not make a work copy: {r.stderr[-200:]}")
        return
    try:
        summary, cost = run_claude(wt, flag, plan_only)
        files = changed(wt)
        if plan_only or not files:
            fixflow.report(j, num, "needs_decision", (summary or "no change was needed or possible") + " Nothing was changed.", cost=cost)
            return
        ok, refused = allowed(files, pinned_files())
        if not ok:
            fixflow.report(j, num, "needs_decision", f"The fix would touch files the worker may not change by itself ({', '.join(refused[:5])}); "
                           f"nothing was applied. Its plan: {summary}", cost=cost)
            return
        good, why = checks(wt, files)
        if not good:
            fixflow.report(j, num, "failed", f"{why}. Nothing went live.", cost=cost)
            return
        sh(["git", "add", "--", *files], wt)
        msg = (f"Repair #{num} (flagged from the app): {flag['options']['options'][flag['choice']]['title']}\n\n{summary}\n\n"
               "Built by the repair worker (scripts/repair_worker.py) on Madhav's choice; checks passed before deploy.\n\n"
               "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n")
        r = sh(["git", "commit", "-q", "-m", msg], wt)
        if r.returncode != 0:
            fixflow.report(j, num, "failed", f"commit failed: {r.stderr[-200:]}", cost=cost)
            return
        sha = sh(["git", "rev-parse", "HEAD"], wt).stdout.strip()
        if sh(["git", "merge", "--ff-only", branch], LIVE).returncode != 0:          # jarvis-4 moved meanwhile: rebase once, re-check
            sh(["git", "rebase", "jarvis-4"], wt)
            good, why = checks(wt, files)
            sha = sh(["git", "rev-parse", "HEAD"], wt).stdout.strip()
            if not good or sh(["git", "merge", "--ff-only", branch], LIVE).returncode != 0:
                fixflow.report(j, num, "failed", "jarvis-4 changed while the fix was built and it no longer applies cleanly; nothing went live.", cost=cost)
                return
        ok, how = deploy(files)
        if not ok:
            sh(["git", "revert", "--no-edit", sha], LIVE)
            deploy(files)
            fixflow.report(j, num, "failed", f"{how}; the change was reverted and the service is back as it was.", commit=sha, cost=cost)
            return
        sh(["git", "push", "-q", "origin", "jarvis-4"], LIVE, timeout=120)
        fixflow.report(j, num, "deployed", f"{summary} ({how}).", commit=sha, cost=cost, branch=branch)
    except Exception as exc:  # noqa: BLE001 - every failure goes back to Madhav, never silently
        fixflow.report(j, num, "failed", f"the worker stopped: {str(exc)[:300]}. Nothing went live.")
    finally:
        sh(["git", "worktree", "remove", "--force", str(wt)], LIVE)


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    lk = open(WORK / ".lock", "w")
    try:
        fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return 0                                                      # another run is still working
    sys.path.insert(0, str(LIVE))
    from jarvis.service import core, fixflow, requests_log

    j = core.from_env()
    todo = fixflow.pending(j)
    if not todo:
        return 0
    day0 = int(time.mktime(time.strptime(time.strftime("%Y-%m-%d"), "%Y-%m-%d")))
    done_today = j.db.execute("SELECT COUNT(*) FROM fix_flow WHERE updated_t>=? AND choice IS NOT NULL "
                              "AND state IN ('deployed','needs_decision','failed')", (day0,)).fetchone()[0]
    if done_today >= WORKER_DAILY:
        log(f"daily cap reached ({WORKER_DAILY}); {len(todo)} waiting")
        return 0
    flag = todo[0]
    log(f"#{flag['num']} {flag['state']} start")
    work_one(j, fixflow, flag)
    requests_log.notify(j, push=_push)
    log(f"#{flag['num']} -> {fixflow.get(j, flag['num'])['state']}")
    return 0


def _push(title: str, body: str):
    try:
        from src.intelligence.paper_watch import push_phone

        return push_phone(title, body, level="EVENT")
    except Exception:  # noqa: BLE001 - the 15-minute job pushes it later
        raise


if __name__ == "__main__":
    sys.exit(main())
