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
