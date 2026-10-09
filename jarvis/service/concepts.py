"""Concepts when they matter (plan 4.5, rule 7): each idea is introduced once per account, at the moment it first means something.

  evidence    the first finding         -> what the Evidence is and where it lives (Cockpit)
  learned     the first losing trade    -> what Ananta learns from a loss (the repair shop)
  monitoring  the first manual trade    -> Ananta watches it and warns, but never sells it without a yes

due(j) returns the next one this account has not seen (or None); seen(j, id) records it.
"""
from __future__ import annotations

import json
from typing import Any

CONCEPTS: dict[str, dict[str, str]] = {
    "evidence": {"title": "New: the Evidence",
                 "text": "Ananta just recorded a finding. Every finding, and every question it raises, goes to the Evidence: a list of tests on "
                         "history that decide whether a trading rule changes. It lives in Cockpit.",
                 "open": "/evidence", "button": "Open the Evidence"},
    "learned": {"title": "New: learning from a loss",
                "text": "A trade closed at a loss. Losses are not hidden: each one is reviewed, and if a rule keeps losing, it goes to the repair "
                        "shop to be tested and fixed, never changed on a hunch.",
                "ask": "What did you learn from my losing trade?", "button": "Ask what Ananta learned"},
    "monitoring": {"title": "New: your own trades are watched",
                   "text": "You placed your first trade yourself. It carries your initials. Ananta watches it: near the stop, a close under its "
                           "zone or a turn in the trend, it warns you and offers an exit. It never sells it without your yes.",
                   "open": "/(tabs)/portfolio", "button": "See it in Books"},
}
ORDER = ("monitoring", "learned", "evidence")


def _seen(db) -> list[str]:
    try:
        db.execute("CREATE TABLE IF NOT EXISTS visitor_profile (k TEXT PRIMARY KEY, v TEXT)")
        r = db.execute("SELECT v FROM visitor_profile WHERE k='concepts_seen'").fetchone()
        return json.loads(r[0]) if r else []
    except Exception:  # noqa: BLE001
        return []


def seen(j, cid: str) -> dict[str, Any]:
    if cid not in CONCEPTS:
        raise ValueError("unknown concept")
    s = _seen(j.db)
    if cid not in s:
        s.append(cid)
        j.db.execute("INSERT OR REPLACE INTO visitor_profile VALUES ('concepts_seen', ?)", (json.dumps(s),))
        j.db.commit()
    return {"seen": s}


def _happened(j, cid: str) -> bool:
    from jarvis.service.manual import Manual

    try:
        if cid == "monitoring":
            return any(f.get("side") == "BUY" and f.get("trigger") in ("owner", "direct", None) for f in Manual(j.db, j.now).fills(50))
        if cid == "learned":
            if getattr(j, "sandbox", False):
                return float(Manual(j.db, j.now).state(j.prices()).get("realized") or 0) < 0
            r = j.db.execute("SELECT 1 FROM evidence_trades WHERE exit_t IS NOT NULL AND net_usd < 0 LIMIT 1").fetchone()
            return bool(r)
        if cid == "evidence":
            from jarvis.service import account, views

            if getattr(j, "sandbox", False):                 # a visitor's first finding: a market shift on their Home, once they trade
                return bool(account.profile(j.db).get("started_t")) and any(f["kind"] == "SHIFT" for f in views.findings(j))
            return bool(views.findings(j))
    except Exception:  # noqa: BLE001
        return False
    return False


def due(j) -> dict[str, Any] | None:
    s = _seen(j.db)
    for cid in ORDER:
        if cid not in s and _happened(j, cid):
            return {"id": cid, **CONCEPTS[cid]}
    return None
