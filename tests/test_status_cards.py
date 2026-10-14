"""Status cards and the acceptance gate (Madhav's acceptance framework, Oct 6): knowledge is not permission to trade."""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_every_brain_knowledge_line_has_a_card_and_the_values_are_valid():
    from jarvis.service import brain

    doc = json.loads((ROOT / "docs" / "knowledge" / "status_cards.json").read_text())
    cards = {c["id"]: c for c in doc["cards"]}
    assert len(cards) == len(doc["cards"])
    for k, _, _ in brain.KNOWLEDGE:
        assert k in cards, k
    for c in cards.values():
        assert c["evidence"] in doc["meaning"]["evidence"] and c["permission"] in doc["meaning"]["permission"], c["id"]
        assert c["reason"]
    assert cards["BUYING_PRESSURE"]["permission"] == "CONTEXT" and cards["T3"]["permission"] == "PAPER"


def test_a_take_resting_only_on_context_ideas_is_refused():
    from jarvis.service import brain

    bad, ok = brain.permission_check(["READS", "FUNDING"])
    assert bad == ["READS", "FUNDING"] and ok == []
    bad, ok = brain.permission_check(["ZONES", "REGIME", "READS"])
    assert bad == ["READS"] and ok == ["ZONES", "REGIME"]
    bad, ok = brain.permission_check(["LIVE_BOOKS", "MISSED", "ZONES"])      # evidence records are not ideas (Oct 8)
    assert bad == [] and ok == ["ZONES"]


def test_idea_status_lookup_finds_by_alias(tmp_path):
    import types
    from jarvis.service import ask

    L = ask.Lookups.__new__(ask.Lookups)
    r = L.t_idea_status("taker buy")
    assert r["cards"][0]["id"] == "BUYING_PRESSURE" and r["cards"][0]["evidence"] == "CONFLICTING"
    assert ask.Lookups.t_idea_status(L, "astrology")["cards"] == []


def test_gate_counts_and_live_checks(tmp_path):
    import sqlite3
    import types
    from jarvis.service import evidence_live as el

    j = types.SimpleNamespace(dir=ROOT, db=sqlite3.connect(":memory:"), now=lambda: 2_000_000_000)
    g = el._gate(j, {"results": {"items": [{"key": "real", "avg_usd": -1.0}], "events": 3, "random_avg_usd": -1.2}})
    assert g["of"] == 27 and g["passed"] == sum(1 for c in g["checks"] if c["status"] == "PASS")
    by = {c["id"]: c for c in g["checks"]}
    assert by["engine_reproducible"]["status"] == "PENDING" and by["strategy_baselines"]["status"] == "PENDING"
