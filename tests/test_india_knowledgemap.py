"""29 Oct 2026 (Phase 1 of the reverse-engineering pass): the one map reads every record and lists the mismatches between layers."""
import json

from jarvis.india import knowledgemap as km


def _setup(tmp_path, monkeypatch):
    rec = tmp_path / "records"
    reg = rec / "india" / "registrations"
    reg.mkdir(parents=True)
    data = tmp_path / "data"
    (data / "manifests").mkdir(parents=True)
    (data / "readmodel").mkdir()
    (data / "paper" / "reconstruction").mkdir(parents=True)
    rows = [
        {"kind": "registration", "study": "ZZ1", "family": "f", "title": "Zed one: a thing that held up", "at": "2026-10-20T00:00:00"},
        {"kind": "result", "study": "ZZ1", "family": "f", "variant": "a", "verdict": "VALIDATED", "dev": [0.01, 4.0, 40], "val": [0.01, 3.9, 20], "at": "2026-10-20T01:00:00"},
        {"kind": "registration", "study": "ZZ2", "family": "f", "title": "Zed two: thin data", "at": "2026-10-20T00:00:00"},
        {"kind": "result", "study": "ZZ2", "family": "f", "variant": "a", "verdict": "INCONCLUSIVE", "dev": [0.0, 0.1, 5], "val": [0.0, 0.1, 4], "at": "2026-10-20T01:00:00"},
        {"kind": "registration", "study": "ZZ3", "family": "f", "title": "Zed three: registered, never run", "at": "2026-10-21T00:00:00"},
    ]
    (data / "manifests" / "test_ledger.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (reg / "zz1_results_v1.md").write_text("# ZZ1 results\nIt held up.\n")
    (reg / "india_lock.json").write_text(json.dumps({"pins": {}}))
    (reg / "india_exam_v1.json").write_text(json.dumps({"questions": []}))
    (rec / "india" / "paper_config.json").write_text(json.dumps({"stock": {"liq_top": 250}}))
    (data / "readmodel" / "latest.json").write_text(json.dumps({"research": {"studies": ["ZZ1"]}}))
    (data / "paper" / "reconstruction" / "decisions.jsonl").write_text(json.dumps({"key": "MISS_PATTERN:x", "decision": "APPROVED"}) + "\n")
    monkeypatch.setattr(km, "RECORDS", rec)
    monkeypatch.setattr(km, "REG", reg)
    monkeypatch.setattr(km, "DATA", data)
    monkeypatch.setattr(km, "OUT_JSON", tmp_path / "out" / "india_map.json")
    monkeypatch.setattr(km, "OUT_DIR", tmp_path / "out" / "map")
    monkeypatch.setattr(km, "_facts_text", lambda: json.dumps({"research": {"studies": ["ZZ1", "ZZ2"]}, "note": "the 250 most traded stocks; 50,000; 60,000; re-entry 14; 2 ATR; 20 sessions; random control; cap"}))
    monkeypatch.setattr(km, "_plain_names", lambda: {"ZZ1": "the zed-one test"})


def test_the_map_rows_and_gap_classes(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    m = km.build()
    by = {r["id"]: r for r in m["rows"]}
    assert by["ZZ1"]["best_verdict"] == "VALIDATED" and by["ZZ1"]["scale"] == "full" and by["ZZ1"]["results_page"] and by["ZZ1"]["in_facts"] and by["ZZ1"]["in_readmodel"]
    assert by["ZZ2"]["scale"] == "thin" and by["ZZ3"]["variants"] == 0
    classes = {(g["class"], g["id"]) for g in m["gaps"]}
    assert ("C", "ZZ1") in classes          # proved, not in the paper rules (needs Madhav's yes)
    assert ("E", "ZZ2") in classes and ("F", "ZZ2") in classes
    assert ("A", "ZZ3") in classes and ("A", "MISS_PATTERN:x") in classes
    assert all(g["lane"] == "DECISION" for g in m["gaps"] if g["class"] == "C")
    p = km.write(m)
    assert p.exists() and "| C proved, not in the paper rules | ZZ1 |" in p.read_text()
    assert km.gaps()["C proved, not in the paper rules"] == 1
    rows = km.lookup("Did you test the zed one thing that held up?")
    assert rows and rows[0]["id"] == "ZZ1" and rows[0]["name"] == "the zed-one test" and rows[0]["verdict"] == "VALIDATED"
