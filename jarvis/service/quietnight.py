"""Quiet nights for the crypto night test (jarvis/service/nightcheck.py). Kept apart from the night test itself, whose truth carries no
brakes (tests/test_nightly_note_12nov.py): this reads the book's raw state only to decide whether anything happened."""
from __future__ import annotations

import json
import os
import time

from jarvis.service import nightcheck as N

ROOT, OUT = N.ROOT, N.OUT
# Madhav, 20 Nov 2026 20:21: "As the crypto market is pale and not moving, until we trade and do something in this crypto market, is it
# needed to run all audits and tests on daily basis" ... "how can we modify the crypto market audits and reports so that we don't have to
# waste usage until something happens". 20:22: "Yes please", 20:27: "Let's get this done". The paid night test (about US$0.42 a night)
# asked the same questions about the same all-cash book every night. Now it runs when something happened since the last tested night, and
# at least once a week; the free code checks (the clean night, the self-check, the backups) still run every night.
QUIET_MAX_DAYS = 7
QUIET = OUT / "crypto_quiet.json"
latest = N.latest
CRYPTO_CODE = ("jarvis/service", "jarvis/selfcheck.py", "jarvis/placekit.py", "src", "docs/knowledge/nightcheck_crypto.json",
               "docs/knowledge/discipline.json", "docs/knowledge/strategy_status.json")


def dial(j):
    """The $500 book's dial as stored, kept with each tested night."""
    return (_book(j) or {}).get("dial")


def _book(j) -> dict | None:
    try:
        row = j.db.execute("SELECT v FROM book500 WHERE k='state'").fetchone()
        return json.loads(row[0]) if row else None
    except Exception:  # noqa: BLE001
        return None


def _code_changed_since(t0: float) -> bool | None:
    """True when a commit touching the crypto side's code or its question bank landed after t0 (None when git cannot be read)."""
    import subprocess

    try:
        r = subprocess.run(["git", "log", f"--since=@{int(t0)}", "--format=%h", "--", *CRYPTO_CODE], cwd=str(ROOT), capture_output=True,
                           text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    return bool(r.stdout.strip()) if r.returncode == 0 else None


def quiet_night(j, now: float | None = None) -> str | None:
    """Why tonight needs no paid test, in one sentence; None when tonight is tested. Tested when: no tested night is on file, the last one is
    six and a half days old or more, the $500 book holds a coin, bought or sold, an alert fired, a brake is on, the dial moved, the crypto code
    or the question bank changed, or tonight's clean-night check found something. When anything cannot be read, tonight is tested."""
    if os.getenv("NIGHTCHECK_EVERY_NIGHT") == "1":
        return None
    now = j.now() if now is None else now
    last = latest()
    if not last or not last.get("t") or not last.get("asked"):
        return None
    t0 = float(last["t"])
    if now - t0 >= (QUIET_MAX_DAYS - 0.5) * 86400:
        return None
    bk = _book(j)
    try:
        fills = j.db.execute("SELECT COUNT(*) FROM book500_fills WHERE t > ?", (t0,)).fetchone()[0]
        fired = j.db.execute("SELECT COUNT(*) FROM alerts WHERE fired_t > ?", (t0,)).fetchone()[0]
    except Exception:  # noqa: BLE001
        return None
    if not bk or bk.get("pos") or fills or fired:
        return None
    br = bk.get("brakes") or {}
    if br.get("paused") or float(br.get("block_until") or 0) > now:
        return None
    if last.get("dial") is None or last.get("dial") != bk.get("dial"):
        return None
    if _code_changed_since(t0) is not False:
        return None
    try:                                                   # tonight's free check of the note (officer.mark_clean_night)
        day = time.strftime("%Y-%m-%d", time.gmtime(now))
        row = j.db.execute("SELECT v FROM engine_state WHERE k=?", ("clean_night:" + day,)).fetchone()
        if row and not (json.loads(row[0]) or {}).get("clean"):
            return None
    except Exception:  # noqa: BLE001
        return None
    nxt = time.strftime("%a %d %b", time.localtime(t0 + QUIET_MAX_DAYS * 86400))
    return ("A quiet night: the $500 book is all in cash, nothing was bought or sold, no alert fired, the dial did not move and no crypto code "
            f"changed since the last test, so no paid test was run. The next full test is by {nxt}, or sooner when anything happens.")


def record_quiet(why: str, now: float | None = None) -> dict:
    """Keep the quiet night: crypto_quiet.json (the last one and the count since the last test) and a line in crypto_history.jsonl."""
    now = time.time() if now is None else now
    day = time.strftime("%Y-%m-%d", time.gmtime(now))
    last = latest() or {}
    try:
        q = json.loads(QUIET.read_text())
    except (OSError, ValueError):
        q = {}
    n = (int(q.get("since_test") or 0) + 1) if q.get("after_t") == last.get("t") else 1
    q = {"day": day, "t": int(now), "why": why, "after_t": last.get("t"), "since_test": n, "saved_usd_about": round(n * 0.42, 2)}
    OUT.mkdir(parents=True, exist_ok=True)
    QUIET.write_text(json.dumps(q, indent=1, ensure_ascii=False))
    with (OUT / "crypto_history.jsonl").open("a") as f:
        f.write(json.dumps({"day": day, "t": int(now), "quiet": True, "asked": 0, "cost_usd": 0.0}) + "\n")
    return q


def quiet() -> dict | None:
    """The last quiet night when it came after the last tested night, else None."""
    try:
        q = json.loads(QUIET.read_text())
    except (OSError, ValueError):
        return None
    last = latest() or {}
    return q if q.get("after_t") == last.get("t") else None
