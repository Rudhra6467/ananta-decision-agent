"""26 Nov 2026: every options-line decision of the session was late and untradable (the Mac slept on battery), and the morning summary's
lost-runs section did not say so. india.morning.sp1_late_problems names such a session."""
import json

from india import morning


def _write(tmp_path, rows):
    p = tmp_path / "paper" / "sp1"
    p.mkdir(parents=True)
    (p / "decisions.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    return tmp_path


def _dec(day, tradable, late, at):
    return {"kind": "decision", "date": day, "index": "NIFTY", "point": "D0", "tradable": tradable, "late_s": late,
            "decided_at": f"{day}T{at}:00+05:30"}


def test_all_untradable_is_named(tmp_path):
    D = _write(tmp_path, [{"kind": "plan", "date": "2026-11-26"}, _dec("2026-11-25", True, 10, "09:15"),
                          _dec("2026-11-26", False, 5204.6, "10:41"), _dec("2026-11-26", False, 1701.6, "10:43")])
    out = morning.sp1_late_problems(D)
    assert len(out) == 1
    assert "2026-11-26" in out[0] and "no decision was tradable" in out[0] and "10:41 IST" in out[0] and "87 min late" in out[0]


def test_one_tradable_is_quiet(tmp_path):
    D = _write(tmp_path, [_dec("2026-11-26", False, 5204.6, "10:41"), _dec("2026-11-26", True, 40, "09:30")])
    assert morning.sp1_late_problems(D) == []


def test_no_file_is_quiet(tmp_path):
    assert morning.sp1_late_problems(tmp_path) == []
