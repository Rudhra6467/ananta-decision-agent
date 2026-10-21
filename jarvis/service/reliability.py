"""Live-code reliability fixes (decision map of Oct 20, section 3 and "The 227 lost brain wake-ups"; Madhav, 2026-10-21 09:41 Toronto:
"Complete all pending tasks and all that are waiting for me. I approve all.").

On Oct 14-15 the brain paid for 226 decisions and saved none: process() caught the error and wrote it only into brain_queue.state.
No log line, no alert. This module gives every such failure a voice, and keeps what a decision writes together:

  atomic(j)            one transaction: a decision row and the paper trades it opens commit together or not at all. The paper
                       trades of the brain and the bold book are rows in evidence_trades (the same database), never an order sent
                       to Hands, so they can share the decision's transaction; Hands is only read (the kill switch) before it.
  save_failed(...)     a paid AI result (a brain decision, the stance, the bold pick) that could not be saved: a log line with the
                       traceback every time, and one note through the health watchdog's own path (the feed and the phone) per kind
                       per hour, so a storm of failures sends one note, not two hundred.
  record_job_errors()  every *_error a run of the 15-minute jobs returns, written with its UTC time to {runs}/jobs_steps.jsonl
                       (one line per run, "errors": {} when none), which the run checker's jobs_steps part reads.

The paid-but-not-saved reconcile in runcheck (brain_saved) keeps working: the model call is logged in ask_messages, and committed,
before the decision's transaction starts, so a decision that fails to save still shows as paid and not saved.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import threading
import time
from contextlib import contextmanager, nullcontext
from pathlib import Path
from typing import Any

LOG = logging.getLogger("ananta.reliability")
ALERT_EVERY_S = 3600
JOBS_FILE = "jobs_steps.jsonl"
_LAST: dict[str, dict] = {}
_lock = threading.Lock()


def reset() -> None:
    """Forget when each kind last sent a note (tests)."""
    with _lock:
        _LAST.clear()


class _Stderr(logging.StreamHandler):
    """Writes to whatever sys.stderr is at the moment of writing (launchd's log file, or a test's capture)."""

    @property
    def stream(self):
        return sys.stderr

    @stream.setter
    def stream(self, _v):
        pass


def _logger() -> logging.Logger:
    """The service log (launchd sends stderr to ~/ananta_runs/jarvis_service.log): one dated line per failure, with its traceback."""
    if not LOG.handlers:
        h = _Stderr()
        f = logging.Formatter("%(asctime)s UTC ananta %(levelname)s %(message)s", "%Y-%m-%d %H:%M:%S")
        f.converter = time.gmtime
        h.setFormatter(f)
        LOG.addHandler(h)
        LOG.setLevel(logging.INFO)
        LOG.propagate = False
    return LOG


@contextmanager
def atomic(j):
    """One transaction for everything written inside the block: commit at the end, roll back on any error (and re-raise).
    The shared connection's lock (core.SafeDB) is held for the whole block, so no other thread's commit can land half of it;
    keep the block to database writes only (no network calls inside)."""
    db = j.db
    con = getattr(db, "con", db)
    with getattr(db, "lock", None) or nullcontext():
        con.commit()                                     # whatever was pending before is not ours to roll back
        try:
            yield
            con.commit()
        except BaseException:
            con.rollback()
            raise


def _push():
    """The health watchdog's own phone path (app.py starts it with the WARN-level ntfy push). Before it starts, or with it switched
    off, the same WARN-level push it would use (paper_watch.push_phone, off without ANANTA_NTFY_TOPIC, which tests clear)."""
    from jarvis.service import health

    if health.STATE.get("push"):
        return health.STATE["push"]

    def warn(title: str, body: str):
        from src.intelligence.paper_watch import push_phone

        return push_phone(title, body, level="WARN")
    return warn


def save_failed(j, kind: str, exc: BaseException, detail: str = "", now: float | None = None) -> dict:
    """A paid AI result that was not saved: a log line every time; a note (feed + phone) at most once an hour per kind, which then
    says how many more failed since the last note. Never raises. Returns {"logged": True, "noted": bool}."""
    now = time.time() if now is None else now
    msg = f"{kind}: paid for, NOT saved ({type(exc).__name__}: {str(exc)[:300]})" + (f" [{detail[:200]}]" if detail else "")
    try:
        _logger().error(msg, exc_info=(type(exc), exc, exc.__traceback__))
    except Exception:  # noqa: BLE001
        pass
    with _lock:
        st = _LAST.setdefault(kind, {"t": None, "n": 0})
        st["n"] += 1
        if st["t"] is not None and now - st["t"] < ALERT_EVERY_S:
            return {"logged": True, "noted": False}
        n, st["t"], st["n"] = st["n"], now, 0
    title = f"Ananta: a {kind} was paid for but not saved"
    body = (f"{type(exc).__name__}: {str(exc)[:200]}." + (f" {detail[:120]}." if detail else "")
            + (f" {n} failed since the last note." if n > 1 else "")
            + " Further failures of this kind in the next hour are logged only (jarvis_service.log). The run checker's 'Brain: every paid "
              "decision call has a saved decision' counts them.")
    push = _push()
    try:
        from jarvis.service import eye

        eye._table(j)
        eye._event(j, "SAVE_FAILED", None, None, title, body, push, {"kind": kind, "error": str(exc)[:300], "count": n})
    except Exception as e2:  # noqa: BLE001  the database may be what failed: the phone still hears
        _logger().error(f"{kind}: the note could not be written to the feed ({type(e2).__name__}: {str(e2)[:160]})")
        if push:
            try:
                push(title, body)
            except Exception:  # noqa: BLE001
                pass
    return {"logged": True, "noted": True}


def runs_dir() -> Path:
    return Path(os.path.expanduser(os.getenv("ANANTA_RUNS_DIR", str(Path.home() / "ananta_runs"))))


def record_job_errors(out: Any, now: float | None = None, path: Path | None = None) -> dict:
    """One line per run of the 15-minute jobs: its UTC time, how many steps it returned and every non-empty *_error. Never raises."""
    now = time.time() if now is None else now
    errs = {k: str(v)[:300] for k, v in (out.items() if isinstance(out, dict) else []) if k.endswith("_error") and v}
    line = {"t": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(now)), "n": len(out) if isinstance(out, dict) else 0, "errors": errs}
    try:
        p = path or runs_dir() / JOBS_FILE
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a") as f:
            f.write(json.dumps(line) + "\n")
    except Exception as exc:  # noqa: BLE001
        _logger().error(f"15-minute jobs: their errors could not be recorded ({exc}): {json.dumps(errs)[:400]}")
    if errs:
        _logger().warning("15-minute jobs: " + json.dumps(errs)[:1000])
    return line
