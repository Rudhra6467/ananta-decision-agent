"""Requests for the repair shop, logged from Ask Ananta or voice ("add this to the repair shop", "that was wrong", "track this").

Madhav (2026-10-03): when Jarvis finds something it cannot answer or do, it should keep track of it and bring it back, so the next
work session fixes it. And it should REPORT BACK: "flagged as number 4, I'll tell you when it's fixed", then a phone note and a
mention in the next conversation when the work session changes its status.

Each request has a number (#1, #2, ... easy to say), a kind (data, feature, bug, idea), the words, where it came up, and a status
the work session updates (OPEN -> PLANNED -> DONE or WONT, with a note). Shown on the Evidence page's repair board and in the Home feed;
readable at /v3/requests. The work session starts by reading the OPEN ones (docs/BACKLOG.md says so).

  add()          log one (returns its number and the sentence to say)
  set_status()   the work session moves it on; the next 15-minute job pushes the news to the phone (notify)
  news()         status changes Madhav has not heard about yet in a conversation; Ananta mentions them once (mark_told)
"""
from __future__ import annotations

import uuid

KINDS = ("data", "feature", "bug", "idea")
STATUSES = ("OPEN", "PLANNED", "DONE", "WONT")
STATUS_WORDS = {"OPEN": "on the list", "PLANNED": "planned for the next work session", "DONE": "fixed", "WONT": "closed without a change"}
COLS = ("id", "num", "t", "by", "kind", "text", "about", "thread", "status", "note", "updated_t", "pushed", "told")


def _table(j) -> None:
    j.db.execute("CREATE TABLE IF NOT EXISTS owner_requests (id TEXT PRIMARY KEY, t INTEGER, by TEXT, kind TEXT, text TEXT, about TEXT, "
                 "thread TEXT, status TEXT, note TEXT)")
    have = {r[1] for r in j.db.execute("PRAGMA table_info(owner_requests)")}
    for c, typ in (("num", "INTEGER"), ("updated_t", "INTEGER"), ("pushed", "INTEGER"), ("told", "INTEGER")):
        if c not in have:
            j.db.execute(f"ALTER TABLE owner_requests ADD COLUMN {c} {typ}")
    if "num" not in have:                                    # number the requests logged before numbers existed, oldest first
        for n, (rid,) in enumerate(j.db.execute("SELECT id FROM owner_requests ORDER BY t, rowid").fetchall(), start=1):
            j.db.execute("UPDATE owner_requests SET num=?, pushed=1, told=1 WHERE id=?", (n, rid))
    j.db.commit()


def _row(r) -> dict:
    d = dict(zip(COLS, r))
    d["status_words"] = STATUS_WORDS.get(d["status"], d["status"])
    return d


def _select(j, where: str = "", args: tuple = ()) -> list[dict]:
    _table(j)
    return [_row(r) for r in j.db.execute(f"SELECT {', '.join(COLS)} FROM owner_requests {where} ORDER BY t DESC, rowid DESC", args)]


def get(j, ref: str | int) -> dict | None:
    """By id or by number ("4", "#4")."""
    s = str(ref).strip().lstrip("#")
    rows = _select(j, "WHERE id=? OR num=?", (s, int(s) if s.isdigit() else -1))
    return rows[0] if rows else None


def add(j, kind: str, text: str, about: str | None = None, by: str = "owner", thread: str | None = None) -> dict:
    _table(j)
    kind = kind if kind in KINDS else "feature"
    text = (text or "").strip()[:900]
    if not text:
        raise ValueError("say what is missing or wrong")
    dup = j.db.execute("SELECT id, num FROM owner_requests WHERE status IN ('OPEN','PLANNED') AND lower(text)=lower(?)", (text,)).fetchone()
    if dup:                                                  # the same words again: no second copy
        return {"id": dup[0], "num": dup[1], "status": "OPEN", "duplicate": True,
                "say": f"That's already on the list as request number {dup[1]}. I'll tell you when it's fixed."}
    num = (j.db.execute("SELECT COALESCE(MAX(num), 0) FROM owner_requests").fetchone()[0] or 0) + 1
    rid = uuid.uuid4().hex[:8]
    j.db.execute(f"INSERT INTO owner_requests ({', '.join(COLS)}) VALUES ({', '.join('?' * len(COLS))})",
                 (rid, num, int(j.now()), by, kind, text, (about or "")[:120], thread, "OPEN", "", int(j.now()), 1, 1))
    j.db.commit()
    return {"id": rid, "num": num, "kind": kind, "status": "OPEN",
            "say": f"Flagged as request number {num} for the repair shop. It's on the Evidence page's repair board, and I'll tell you when it's fixed."}


def list_(j, include_done: bool = True) -> list[dict]:
    return _select(j, "" if include_done else "WHERE status IN ('OPEN','PLANNED')")


def set_status(j, ref: str | int, status: str, note: str = "") -> dict:
    """The work session moves a request on. Pushing the news to the phone is left to notify() (every 15 minutes), so it works
    whoever changes the status: the app, a script, or a work session."""
    if status not in STATUSES:
        raise ValueError(f"status is one of {STATUSES}")
    r = get(j, ref)
    if not r:
        raise ValueError(f"no request {ref}")
    changed = r["status"] != status or (note and note != r["note"])
    j.db.execute("UPDATE owner_requests SET status=?, note=?, updated_t=?, pushed=?, told=? WHERE id=?",
                 (status, (note or r["note"] or "")[:400], int(j.now()), 0 if changed and status != "OPEN" else r["pushed"],
                  0 if changed and status != "OPEN" else r["told"], r["id"]))
    j.db.commit()
    return get(j, r["id"])


def _sentence(r: dict) -> str:
    what = r["text"].split(". ")[0][:140]
    s = f"Request {r['num']} ({what}) is {r['status_words']}"
    return s + (f": {r['note']}" if r.get("note") else ".")


def notify(j, push=None) -> list[dict]:
    """Phone notes for status changes not pushed yet (called by the 15-minute job)."""
    rows = _select(j, "WHERE COALESCE(pushed, 1)=0 AND status IN ('PLANNED','DONE','WONT')")
    out = []
    for r in rows:
        title = {"DONE": f"Fixed: request {r['num']}", "PLANNED": f"Planned: request {r['num']}", "WONT": f"Closed: request {r['num']}"}[r["status"]]
        try:
            if push:
                push(title, _sentence(r))
            j.db.execute("UPDATE owner_requests SET pushed=1 WHERE id=?", (r["id"],))
            out.append({"num": r["num"], "status": r["status"]})
        except Exception:  # noqa: BLE001  try again next time
            pass
    j.db.commit()
    return out


def news(j) -> list[dict]:
    """Status changes Madhav has not heard about in a conversation yet (newest first, at most 3)."""
    return [{"num": r["num"], "status": r["status"], "text": r["text"][:160], "note": r["note"], "say": _sentence(r)}
            for r in _select(j, "WHERE COALESCE(told, 1)=0 AND status IN ('PLANNED','DONE','WONT')")[:3]]


def mark_told(j, nums: list[int]) -> None:
    for n in nums:
        j.db.execute("UPDATE owner_requests SET told=1 WHERE num=?", (n,))
    j.db.commit()


def feed_items(j, since: int) -> list[dict]:
    """Home feed: requests logged and requests that changed status."""
    items = []
    for r in _select(j, "WHERE t >= ? OR COALESCE(updated_t, 0) >= ?", (since, since)):
        if r["t"] >= since:
            items.append({"t": r["t"], "kind": "request", "title": f"Flagged for the repair shop: request {r['num']}",
                          "body": r["text"][:200]})
        if r["status"] != "OPEN" and (r.get("updated_t") or 0) >= since:
            items.append({"t": r["updated_t"], "kind": "request", "good": r["status"] == "DONE",
                          "title": f"Request {r['num']}: {r['status_words']}", "body": (r["note"] or r["text"])[:200]})
    return items
