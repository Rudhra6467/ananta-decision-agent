"""Oct 14: Home's "Needs you" lists the decisions waiting for Madhav: a rule that passed its forward test and may step up the ladder.
"Later" hides it for a week; "approve" moves it one step through the same door as the Evidence page (set_step). Nothing moves by itself."""
from jarvis.service import needs, universe_watch as U
from tests.test_universe_live import J


def test_needs_lists_passed_rules_and_decides(tmp_path, monkeypatch):
    j = J(tmp_path)
    rows = [{"watch": "M1a-UA", "rule": "M1a", "tier": "A", "step": "EVIDENCE", "next_allowed": True, "why": "ahead of random over 10 market days in both regimes"},
            {"watch": "H07-UA", "rule": "H07", "tier": "A", "step": "EVIDENCE", "next_allowed": False, "why": "too early"},
            {"watch": "H07-UC", "rule": "H07", "tier": "C", "step": "SHADOW", "next_allowed": True, "why": "tier C is never judged"}]
    monkeypatch.setattr(U, "ladder", lambda jj: {"rows": rows})
    items = needs.list_(j)
    assert [x["watch"] for x in items] == ["M1a-UA"]                      # only a rule the evidence allows up, from EVIDENCE or PROMOTED
    it = items[0]
    assert it["to"] == "PROMOTED" and it["kind"] == "push" and "M1a on tier A" in it["title"] and "edge sleeve" in it["note"]
    # Later: hidden for a week, then back
    assert needs.decide(j, it["id"], "later", "owner")["decision"] == "later"
    assert needs.list_(j) == []
    j.db.execute("DELETE FROM needs_snooze")
    j.db.commit()
    assert [x["id"] for x in needs.list_(j)] == [it["id"]]
    # approve: one step up, by Madhav, through set_step
    moved = []
    monkeypatch.setattr(U, "set_step", lambda jj, w, s, by: (moved.append((w, s, by)) or {"watch": w, "from": "EVIDENCE", "to": s, "by": by}))
    out = needs.decide(j, it["id"], "approve", "owner")
    assert moved == [("M1a-UA", "PROMOTED", "owner")] and out["decision"] == "approve" and out["to"] == "PROMOTED"
    # a decision that is no longer waiting, or an unknown word, is refused in plain words
    for nid, dec in (("push:H07-UA:EVIDENCE", "approve"), (it["id"], "maybe")):
        try:
            needs.decide(j, nid, dec, "owner")
            raise AssertionError("should refuse")
        except ValueError as exc:
            assert "waiting" in str(exc) or "approve or later" in str(exc)
