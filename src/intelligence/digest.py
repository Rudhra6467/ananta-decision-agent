"""The twice-daily digest (Madhav, 15 Nov 2026: "let's sort this out beautifully without missing on anything important").

Before this, every routine note reached his phone the moment it was written: about 17 a day, with bursts of a dozen "Planned: flag N"
lines at once and four crypto end-of-day notes inside two and a half hours. Now:

  * ROUTINE notes (the briefs, the officer's note, the day in review, the night tests, the India morning view / pre-open / opening, and
    the "Planned:" / "Fixed:" acknowledgements of flags) are queued, not pushed, and arrive together in two digests a day:
      morning  09:30 Toronto              (com.ananta.digest.morning; after the crypto morning brief, usually 08:00-09:05)
      night    09:12 IST, after the India pre-open and before the 09:15 open (com.ananta.digest.night; jarvis/india/schedule.py keeps
               it on Indian time across Toronto's clock changes)
  * Everything else goes at once, as before: any WARN / ERROR / TEST, a part that went quiet or came back, the self-check's "something is
    not right", a new flag, the Kite sign-in, the outside watchdog, price alerts, anything not on the routine list. A note that is not
    recognised is never delayed.

Nothing is lost: every queued note is kept word for word in ~/ananta_runs/digest_queue.jsonl, each digest is written in full to
~/ananta_runs/digests/<date>-<slot>.md, and the notes themselves still live where they always did in the app. A queued note older than
MAX_HOLD_H (a digest job that did not run) is sent by the next digest or pushed at once by the next routine note. Standard library only.
Off with ANANTA_DIGEST=0 (then every note goes at once, exactly as before 15 Nov).
"""
from __future__ import annotations

import contextlib
import fcntl
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

RUNS = Path(os.path.expanduser(os.getenv("ANANTA_RUNS_DIR", "~/ananta_runs")))
QUEUE = RUNS / "digest_queue.jsonl"
SENT = RUNS / "digest_sent.jsonl"
DIGESTS = RUNS / "digests"
MAX_HOLD_H = 16
BODY_MAX = 480

ROUTINE = [
    r"^Ananta morning brief", r"^Ananta evening brief", r"^Ananta's note\b", r"^Jarvis: my day in review", r"^Ananta's night test",
    r"^Ananta nightly check", r"^Morning view ·", r"^Pre-open ·", r"^Planned: flag \d+", r"^Fixed: flag \d+",
]
# "Opening ·" (10:20 IST) is not routine: it comes after the night digest and would reach him after the India close.
_RX = [re.compile(p) for p in ROUTINE]
# A routine title whose words ask for him, or say something failed, goes at once (the fix flow's "Planned: flag N" carries
# "Needs your yes" or "Failed" when a fix waits for his decision or did not pass its checks).
FLAG = re.compile(r"^(Planned|Fixed): flag \d+")
URGENT_BODY = re.compile(r"needs your yes|your yes|your choice|waiting for you|did not pass|failed|decide", re.I)
# The tests' and checks' failure lines go first in a digest.
FIRST = re.compile(r"^(Ananta's night test|Ananta nightly check)")
LOCK = RUNS / ".digest.lock"


def enabled() -> bool:
    return os.getenv("ANANTA_DIGEST", "1") != "0"


def is_routine(title: str, level: str = "EVENT", body: str = "") -> bool:
    if level.upper() in ("WARN", "ERROR", "TEST") or not any(r.search(title or "") for r in _RX):
        return False
    return not (FLAG.match(title or "") and URGENT_BODY.search(body or ""))


@contextlib.contextmanager
def _locked():
    """One writer at a time: a note queued while a digest is being sent is neither lost nor sent twice."""
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    with LOCK.open("w") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _rows(p: Path) -> list[dict]:
    """Rows of a jsonl file; a line that is not a JSON object with a text "ts" is skipped (kept in the file, never read as a note)."""
    if not p.exists():
        return []
    out = []
    for line in p.read_text().splitlines():
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if isinstance(r, dict) and isinstance(r.get("ts", ""), str):
            out.append(r)
    return out


def _append(p: Path, row: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def last_upto() -> str:
    s = _rows(SENT)
    return s[-1].get("upto", "") if s else ""


def pending() -> list[dict]:
    up = last_upto()
    return sorted((r for r in _rows(QUEUE) if r.get("ts", "") > up), key=lambda r: r["ts"])


def _age_h(ts: str) -> float:
    try:
        return (datetime.now(timezone.utc) - datetime.fromisoformat(ts)).total_seconds() / 3600
    except ValueError:
        return 0.0


def queue(title: str, body: str, level: str = "EVENT", flush: Callable[[str, str], str] | None = None) -> str:
    """Keep a routine note for the next digest. If the oldest waiting note is older than MAX_HOLD_H (a digest job missed its time),
    everything waiting goes now through `flush`, so a missed digest delays notes, never loses them."""
    with _locked():
        _append(QUEUE, {"ts": _now(), "title": title, "body": body, "level": level})
        p = pending()
    if flush and p and _age_h(p[0]["ts"]) > MAX_HOLD_H:
        return "queued; " + send("catch-up", flush)
    return "queued for the digest"


def _first(body: str, n: int = 140) -> str:
    b = " ".join((body or "").split())
    m = re.match(r"(.+?[.!?])(\s|$)", b)
    s = m.group(1) if m and len(m.group(1)) <= n else b
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def compose(items: list[dict], slot: str) -> tuple[str, str, str]:
    """(push title, push body, full markdown). Flag acknowledgements are grouped into one line each."""
    groups: dict[str, list[str]] = {}
    lines: list[str] = []
    items = sorted(items, key=lambda it: (0 if FIRST.match(it["title"]) else 1, it["ts"]))
    for it in items:
        m = re.match(r"^(Planned|Fixed): flag (\d+)", it["title"])
        if m:
            if m.group(1) not in groups:
                groups[m.group(1)] = []
                lines.append(f"@{m.group(1)}")
            groups[m.group(1)].append(m.group(2))
        else:
            lines.append(f"• {it['title']}: {_first(it.get('body', ''), 200 if FIRST.match(it['title']) else 140)}")
    out = []
    for ln in lines:
        if ln.startswith("@"):
            k = ln[1:]
            nums = sorted(set(groups[k]), key=int)
            out.append(f"• {k}: flag{'s' if len(nums) > 1 else ''} {', '.join(nums)}")
        else:
            out.append(ln)
    title = f"Ananta · {slot} digest ({len(items)} note{'s' if len(items) != 1 else ''})"
    more = "\n… and {} more: each is in Ananta as usual, and in full in the Mac's digest file"
    body = ""
    for i, ln in enumerate(out):
        rest = len(out) - i - 1
        tail = more.format(rest) if rest else ""
        if len(body) + 1 + len(ln) + len(tail) > BODY_MAX:
            body += more.format(len(out) - i)
            break
        body += ("\n" if body else "") + ln
    md = [f"# {title}", f"Sent {_now()} · {len(items)} notes", ""]
    for it in items:
        md += [f"## {it['title']}", f"_{it['ts']} · {it.get('level', 'EVENT')}_", "", it.get("body", ""), ""]
    return title, body, "\n".join(md)


def send(slot: str, push: Callable[[str, str], str]) -> str:
    """One digest: everything waiting since the last one, in one push; nothing waiting = no push. Marked sent only when the push did
    not fail, so a failed send is retried by the next digest."""
    with _locked():
        items = pending()
        if not items:
            _append(SENT, {"ts": _now(), "slot": slot, "n": 0, "upto": last_upto(), "push": "nothing new"})
            return "nothing new"
        title, body, md = compose(items, slot)
        res = push(title, body)
        if str(res).startswith("failed"):
            return f"not sent ({res}); {len(items)} notes still waiting"
        DIGESTS.mkdir(parents=True, exist_ok=True)
        (DIGESTS / f"{datetime.now().strftime('%Y-%m-%d_%H%M%S')}-{slot}.md").write_text(md)
        _append(SENT, {"ts": _now(), "slot": slot, "n": len(items), "upto": max(i["ts"] for i in items), "push": res})
    return f"sent {len(items)} notes ({res})"
