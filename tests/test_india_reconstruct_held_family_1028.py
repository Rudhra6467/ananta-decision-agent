"""28 Oct morning review: the held-into-fall finding named "The null family" (key HELD_INTO_FALL:null) because the card read each held
group's "campaign" while india.missed writes "family". Reporting only: no paper rule, no family's behaviour changes."""
from __future__ import annotations

import json

from india import reconstruct as rx


def test_held_into_fall_counts_by_the_family_missed_writes(tmp_path, monkeypatch):
    data = tmp_path / "india"
    (data / "manifests").mkdir(parents=True)
    (data / "paper").mkdir(parents=True)
    monkeypatch.setattr(rx.paths, "data_dir", lambda: data)
    held = [{"signal_date": "2026-10-22", "family": "PULL", "pnl_so_far": {}}, {"signal_date": "2026-10-26", "family": "CTL", "pnl_so_far": {}}]
    man = {"movers": [{"symbol": "AEGISLOG", "side": "down", "cc": -0.07, "status": "held_into_fall", "held": held},
                      {"symbol": "OLD", "side": "down", "cc": -0.05, "status": "held_into_fall", "held": [{"campaign": "REV"}]}],
           "summary": {"up": {}, "down": {"movers": 2, "held_into_fall": 2}}}
    (data / "manifests" / "missed_2026-10-27.json").write_text(json.dumps(man))
    out = rx.section_not_done("2026-10-27", {})
    assert out["held_into_fall_by_family"] == {"PULL": 1, "CTL": 1, "REV": 1}
    assert None not in out["held_into_fall_by_family"]
    assert out["held_into_fall"][0]["families"] == ["CTL", "PULL"]
