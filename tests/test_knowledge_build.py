"""One truth registry: watches.json and status_cards.json are repaired from strategy_status.json, drift is reported."""
import json
import sqlite3
import time
import types
from pathlib import Path

from jarvis.service import knowledge_build, strategy_status

NOW = 1_018_000  # any fixed moment


def _j(tmp):
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE rebuild_log (t INTEGER PRIMARY KEY, source TEXT, match INTEGER, logged INTEGER, "
               "rebuilt INTEGER, only_live INTEGER, only_rebuilt INTEGER, detail TEXT)")
    db.execute("CREATE TABLE daily_reviews (day TEXT PRIMARY KEY, t INTEGER, text TEXT, json TEXT)")
    db.execute("INSERT INTO rebuild_log VALUES (?, 'brain', 1, 10, 10, 0, 0, '')", (NOW - 7200,))
    db.execute("INSERT INTO daily_reviews VALUES ('2026-10-14', 1, 'x', '{}')")
    return types.SimpleNamespace(dir=str(tmp), db=db, now=lambda: NOW)


def test_align_repairs_surfaces_and_window_counts(tmp_path, monkeypatch):
    k = tmp_path / "docs" / "knowledge"
    k.mkdir(parents=True)
    start = time.strftime("%Y-%m-%d", time.gmtime(NOW - 86_400))
    (k / "strategy_status.json").write_text(json.dumps({"strategies": {
        "H07": {"status": "ACTIVE", "watches": ["H07"], "cards": ["H07"]},
        "OLD": {"status": "RETIRED", "watches": ["OLD"], "cards": ["OLDCARD", "GONE"]}},
        "evidence_window": {"start": start, "days": 60}}))
    (k / "watches.json").write_text(json.dumps({"updated": "old", "watches": [
        {"id": "H07-T30", "status": "PAUSED"}, {"id": "OLD", "status": "ACTIVE"}, {"id": "UNRELATED", "status": "ACTIVE"}]}))
    (k / "status_cards.json").write_text(json.dumps({"updated": "old", "cards": [
        {"id": "H07", "permission": "PAPER", "reason": "r"}, {"id": "OLDCARD", "permission": "PAPER", "reason": "r"}]}))
    monkeypatch.setattr(knowledge_build, "docs_dir", lambda base: Path(base) / "docs")
    monkeypatch.setattr(strategy_status, "_path", lambda: k / "strategy_status.json")
    strategy_status._CACHE.update(m=None, v={})
    j = _j(tmp_path)
    out = knowledge_build.align(j)
    w = {x["id"]: x["status"] for x in json.loads((k / "watches.json").read_text())["watches"]}
    assert w["H07-T30"] == "ACTIVE" and w["OLD"] == "EVIDENCE_ONLY" and w["UNRELATED"] == "ACTIVE"
    cards = {c["id"]: c for c in json.loads((k / "status_cards.json").read_text())["cards"]}
    assert cards["OLDCARD"]["permission"] == "CONTEXT" and "no longer a reason to buy" in cards["OLDCARD"]["reason"]
    assert cards["H07"]["permission"] == "PAPER"
    assert any("GONE" in c for c in out["conflicts"]) and len(out["fixed"]) >= 3
    today = time.strftime("%Y-%m-%d", time.gmtime(NOW))
    assert json.loads((k / "watches.json").read_text())["updated"] == today
    assert json.loads((k / "status_cards.json").read_text())["updated"] == today
    ew = knowledge_build.window(j)
    assert ew and ew["day"] == 2 and ew["of"] == 60 and ew["started"] == start
    assert "clean" in ew["loop"]["brain_rebuild"] and ew["loop"]["daily_review"] == "2026-10-14"
    strategy_status._CACHE.update(m=None, v={})


def test_the_brains_own_knowledge_list_agrees_with_the_registry():
    """Oct 15: brain.KNOWLEDGE is a second truth surface the nightly align step does not regenerate; it had kept the legacy
    10-coin T3 pass and lacked review #26's dial-closed cell for H07 after the status cards were corrected (request #50)."""
    from jarvis.service import brain

    k = {i: (s, t) for i, s, t in brain.KNOWLEDGE}
    cards = {c["id"]: c for c in json.loads((Path(__file__).resolve().parents[1] / "docs" / "knowledge" / "status_cards.json").read_text())["cards"]}
    t3 = k["T3"][1]
    assert "10 coins and the 30" not in t3 and "legacy" in t3 and "#15" in t3 and "#15" in cards["T3"]["reason"]
    h07_status, h07 = k["H07"]
    assert h07_status == "MEASURED_CELL_ONLY" and "#26" in h07 and "CLOSED" in h07
    assert "#26" in cards["H07"]["reason"] and "CLOSED" in cards["H07"]["reason"]


def _ledger_tree(tmp_path, monkeypatch, **over):
    docs = tmp_path / "docs"
    (docs / "repair_shop").mkdir(parents=True)
    (docs / "research").mkdir()
    (docs / "research" / "REVIEW_1.md").write_text("x")
    led = {"updated": "2026-10-15", "reviews": [{"id": "R1", "date": "2026-10-15", "status": "DONE", "files": ["docs/research/REVIEW_1.md"]}],
           "queue": [{"id": "Q1"}], "tickets": [{"id": "TK1", "date": "2026-10-15"}], "in_use": [], "studies": [], "changes": []}
    led.update(over)
    (docs / "repair_shop" / "ledger.json").write_text(json.dumps(led))
    monkeypatch.setattr(knowledge_build, "docs_dir", lambda base: Path(base) / "docs")
    return docs


def test_ledger_check_is_clean_on_a_consistent_ledger(tmp_path, monkeypatch):
    """Reconstruction Fix 10 (Oct 15): the repair ledger is checked against its own files every night."""
    _ledger_tree(tmp_path, monkeypatch)
    r = knowledge_build.ledger(_j(tmp_path))
    assert r["ok"] and r["problems"] == [] and r["checked"] >= 4


def test_ledger_check_finds_each_kind_of_drift(tmp_path, monkeypatch):
    docs = _ledger_tree(tmp_path, monkeypatch, updated="2026-10-01",
                        reviews=[{"id": "R1", "date": "2026-10-15", "status": "DONE", "files": ["docs/research/REVIEW_1.md", "docs/research/GONE.md"]},
                                 {"id": "R1", "date": "2026-10-14", "status": "DONE"}],
                        queue=[{"id": "R1"}])
    (docs / "research" / "REVIEW_7_RESULTS.md").write_text("a review nobody wrote into the ledger")
    text = " | ".join(knowledge_build.ledger(_j(tmp_path))["problems"])
    assert "id used twice: R1" in text and "GONE.md does not exist" in text and "queue R1 is also a DONE review" in text
    assert "review 7 has a document on disk but no row" in text and "older than the newest row (2026-10-15)" in text


def test_ledger_nightly_files_one_request_for_one_set_of_problems(tmp_path, monkeypatch):
    _ledger_tree(tmp_path, monkeypatch, updated="2026-10-01")
    j = _j(tmp_path)
    first = knowledge_build.ledger_nightly(j)
    again = knowledge_build.ledger_nightly(j)
    rows = j.db.execute("SELECT by, kind, about FROM owner_requests").fetchall()
    assert first.get("flagged") is True and "flagged" not in again and rows == [("ananta-auto", "data", "ledger check")]


BRAIN_WORD = {"PASSED": "SUPPORTED", "SUPPORTED": "SUPPORTED", "FACT": "SUPPORTED", "MEASURED_CELL_ONLY": "SUPPORTED",
              "FAILED": "REJECTED", "DROPPED": "REJECTED", "NOT_BETTER": "REJECTED", "LESSON": "WEAK", "MIXED": "CONFLICTING",
              "RULE": "UNTESTED", "CANDIDATE": "INSUFFICIENT", "FORWARD": "INSUFFICIENT"}


def test_the_brains_status_words_say_what_the_status_cards_say():
    """Research audit FRAMEWORK (Oct 15): brain.KNOWLEDGE keeps plain labels; each must mean its card's evidence word."""
    from jarvis.service import brain

    root = Path(__file__).resolve().parents[1] / "docs" / "knowledge"
    cards = {c["id"]: c for c in json.loads((root / "status_cards.json").read_text())["cards"]}
    for kid, word, _ in brain.KNOWLEDGE:
        assert kid in cards, f"brain item {kid} has no status card"
        assert BRAIN_WORD.get(word) == cards[kid]["evidence"], f"{kid}: brain {word}, card {cards[kid]['evidence']}"
    hyp = {h["id"]: h["status"] for h in json.loads((root / "hypotheses.json").read_text())["hypotheses"]}
    assert hyp["H07"] == cards["H07"]["evidence"] and hyp["H14"] == cards["STOPS"]["evidence"]
