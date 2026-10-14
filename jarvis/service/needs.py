"""Needs you (Madhav, Oct 13-14): the decisions that wait for Madhav, in one list, so Home shows them as one card.

One kind today: a universe rule that passed its forward test and may step up the ladder (push_passed already sent the phone note
and opened a request). Madhav decides here: "Step up" moves it one step (universe_watch.set_step, the same door as the Evidence
page's ladder); "Later" hides it for a week (table needs_snooze). Nothing moves by itself. The trend portfolio's suggestions and
the mandate's actions keep their own cards (/v3/inbox). Paper only."""
from __future__ import annotations

LATER_S = 7 * 24 * 3600


def _table(j) -> None:
    j.db.execute("CREATE TABLE IF NOT EXISTS needs_snooze (id TEXT PRIMARY KEY, until_t INTEGER, by TEXT)")


def list_(j) -> list[dict]:
    from jarvis.service import universe_watch as U

    _table(j)
    now = int(j.now())
    snoozed = {i for (i, u) in j.db.execute("SELECT id, until_t FROM needs_snooze") if (u or 0) > now}
    try:
        rows = U.ladder(j)["rows"]
    except Exception:  # noqa: BLE001
        rows = []
    out = []
    for r in rows:
        if not r.get("next_allowed") or r.get("step") not in ("EVIDENCE", "PROMOTED"):
            continue
        nid = f"push:{r['watch']}:{r['step']}"
        if nid in snoozed:
            continue
        nxt = U.LADDER[U.LADDER.index(r["step"]) + 1]
        out.append({"id": nid, "kind": "push", "watch": r["watch"], "rule": r["rule"], "tier": r["tier"], "from": r["step"], "to": nxt,
                    "title": f"{r['rule']} on tier {r['tier']} passed its forward test",
                    "line": f"Step it up from {r['step'].lower()} to {nxt.lower().replace('_', ' ')}, or leave it measuring.",
                    "why": r.get("why"), "meaning": U.LADDER_WORDS.get(nxt, ""),
                    "note": ("A promoted rule with a passing measured cell enters the $500 book's edge sleeve, on paper." if nxt == "PROMOTED"
                             else "A live candidate may be proposed for real money, with your approval each time. Nothing is live today.")})
    return out


def decide(j, nid: str, decision: str, by: str) -> dict:
    """Madhav's tap: "approve" steps the rule up one rung; "later" hides the item for a week."""
    from jarvis.service import universe_watch as U

    _table(j)
    item = next((x for x in list_(j) if x["id"] == nid), None)
    if not item:
        raise ValueError("that decision is not waiting any more")
    if decision == "later":
        j.db.execute("INSERT OR REPLACE INTO needs_snooze VALUES (?,?,?)", (nid, int(j.now()) + LATER_S, by))
        j.db.commit()
        return {"id": nid, "decision": "later", "until_days": 7}
    if decision in ("approve", "step_up"):
        moved = U.set_step(j, item["watch"], item["to"], by)
        if hasattr(j, "audit"):
            try:
                j.audit(by, "needs", nid, f"step up {item['watch']} -> {item['to']}")
            except Exception:  # noqa: BLE001
                pass
        return {"id": nid, "decision": "approve", **moved}
    raise ValueError("decision is approve or later")
