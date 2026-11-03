"""3 Nov 2026 (Madhav: "Yes for all", the Map's change 11): one question bank. The nightly replay's report carries the India exam's line."""
import json

from jarvis.india import replay


def test_the_exam_line_reads_the_last_full_run(tmp_path):
    p = tmp_path / "exam_latest.json"
    p.write_text(json.dumps({"day": "2026-10-30", "known": 16, "known_of": 18, "unknown": 7, "unknown_of": 7, "why": 4, "why_of": 5, "style": 8,
                             "style_of": 9, "safety": 39, "plain": 38, "of": 39, "exam_pass": False}))
    e = replay.exam_line(p)
    assert e["pass"] is False and e["day"] == "2026-10-30"
    assert "answers and decides 8 of 9" in e["words"] and e["words"].endswith("FAIL.")
    assert replay.exam_line(tmp_path / "missing.json")["words"] == "The India exam has no full run on record."
