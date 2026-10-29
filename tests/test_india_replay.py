"""29 Oct 2026: the nightly replay re-asks real messages dry, grades them and keeps a regression bank."""
import json

from jarvis.india import ask, replay


def test_dry_run_sends_approvals_to_scratch(tmp_path, monkeypatch):
    monkeypatch.setattr(ask, "ASK_DIR", tmp_path)
    monkeypatch.setattr(ask, "DRY_RUN", True)
    assert ask._dec_path() == tmp_path / "dry_decisions.jsonl" and ask._alloc_path() == tmp_path / "dry_allocation.json"
    monkeypatch.setattr(ask, "DRY_RUN", False)
    assert ask._dec_path().name == "decisions.jsonl" and "reconstruction" in str(ask._dec_path())


def test_run_grades_replays_and_banks_failures(tmp_path, monkeypatch):
    real = tmp_path / "real"
    real.mkdir()
    (real / "abc123.jsonl").write_text("\n".join(json.dumps(r) for r in (
        {"id": "u1", "role": "user", "text": "I approve all. Up or down tomorrow?", "t": 9e9 - 10, "voice": True},
        {"id": "a1", "role": "assistant", "answer": "Approved."})) + "\n")
    monkeypatch.setattr(ask, "ASK_DIR", real)
    monkeypatch.setattr(replay, "OUT", tmp_path / "out")
    monkeypatch.setattr(replay, "BANK", tmp_path / "out" / "bank.jsonl")
    monkeypatch.setattr(replay.time, "time", lambda: 9e9)
    seen = {}

    def fake_ask(who, text, thread=None, **k):
        seen["dir"], seen["dry"] = ask.ASK_DIR, ask.DRY_RUN
        return {"answer": "Approved, sir.", "thread": thread}
    monkeypatch.setattr(ask, "ask", fake_ask)
    monkeypatch.setattr(replay, "judge", lambda h, t, post=None: {"pass": False, "problems": [{"code": "PART_MISSED", "why": "the question was dropped"}]})
    s = replay.run(hours=1)
    assert seen["dry"] is True and seen["dir"] != real and ask.DRY_RUN is False and ask.ASK_DIR == real
    assert s["today_turns"] == 1 and s["today_failed"] == 1
    b = replay.bank()
    assert len(b) == 1 and b[0]["problems"][0]["code"] == "PART_MISSED" and b[0]["status"] == "open"
    monkeypatch.setattr(replay, "judge", lambda h, t, post=None: {"pass": True, "problems": []})
    for _ in range(3):
        replay.run(hours=0.0001)
    assert replay.bank()[0]["status"] == "fixed"
