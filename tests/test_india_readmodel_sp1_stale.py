"""9 Nov 2026 (morning review): the SP1 day plan records stale inputs; the read model's SP1 line must carry the mark (Madhav, 25 Oct: marked,
never stopped). Mon 9 Nov: the cash-market file for Sunday's Muhurat session was missing at 07:30 IST and breadth read 0 names."""
from __future__ import annotations

import json

from india import readmodel


def _setup(tmp_path, monkeypatch, stale):
    d = tmp_path / "paper" / "sp1"
    d.mkdir(parents=True)
    rows = [{"kind": "plan", "date": "2026-11-09", "stale": stale},
            {"kind": "decision", "date": "2026-11-09", "index": "NIFTY", "point": "D0", "choice": {}}]
    (d / "decisions.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    monkeypatch.setattr(readmodel.paths, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(readmodel, "_options_capital", lambda: 50000)


def test_a_stale_plan_is_marked(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, {"us_qqq": False, "participant_oi": False, "cm_bhavcopy": True})
    s = readmodel.sp1("2026-11-09")
    assert s["inputs"]["marked"] is True
    assert "marked: planned on stale inputs: the previous session's cash-market file (market breadth)" in s["words"]


def test_a_fresh_plan_says_nothing(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, {"us_qqq": False, "participant_oi": False, "cm_bhavcopy": False})
    s = readmodel.sp1("2026-11-09")
    assert s["inputs"]["marked"] is False
    assert "marked" not in s["words"]
