"""Requests for the repair shop, logged from Ask Ananta or voice ("add this to the repair shop", "track this next time").

Madhav (2026-10-03): when Jarvis finds something it cannot answer or do, it should keep track of it and bring it back, so the next
work session fixes it. Each request has a kind (data, feature, bug, idea), the words, where it came up, and a status that the work
session updates (OPEN -> PLANNED -> DONE, with a note). Shown on the Evidence page; readable at /v3/requests.
"""
from __future__ import annotations

import uuid

KINDS = ("data", "feature", "bug", "idea")
STATUSES = ("OPEN", "PLANNED", "DONE", "WONT")


def _table(j) -> None:
    j.db.execute("CREATE TABLE IF NOT EXISTS owner_requests (id TEXT PRIMARY KEY, t INTEGER, by TEXT, kind TEXT, text TEXT, about TEXT, "
                 "thread TEXT, status TEXT, note TEXT)")


def add(j, kind: str, text: str, about: str | None = None, by: str = "owner", thread: str | None = None) -> dict:
    _table(j)
    kind = kind if kind in KINDS else "feature"
    rid = uuid.uuid4().hex[:8]
    j.db.execute("INSERT INTO owner_requests VALUES (?,?,?,?,?,?,?,?,?)",
                 (rid, int(j.now()), by, kind, (text or "").strip()[:600], (about or "")[:120], thread, "OPEN", ""))
    j.db.commit()
    return {"id": rid}


def list_(j, include_done: bool = True) -> list[dict]:
    _table(j)
    q = "SELECT id, t, by, kind, text, about, status, note FROM owner_requests" + ("" if include_done else " WHERE status IN ('OPEN','PLANNED')")
    return [dict(zip(("id", "t", "by", "kind", "text", "about", "status", "note"), r)) for r in j.db.execute(q + " ORDER BY t DESC")]


def set_status(j, rid: str, status: str, note: str = "") -> None:
    if status not in STATUSES:
        raise ValueError(f"status is one of {STATUSES}")
    _table(j)
    j.db.execute("UPDATE owner_requests SET status=?, note=? WHERE id=?", (status, note[:300], rid))
    j.db.commit()
