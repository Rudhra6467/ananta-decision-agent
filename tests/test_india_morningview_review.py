"""The morning reviewer's answer is read tolerantly (29 Oct 2026 audit): one malformed JSON answer had lost the whole review for a session."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("india_morningview", Path(__file__).resolve().parents[1] / "scripts" / "india_morningview.py")
mv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mv)


def test_fenced_json_with_trailing_comma_parses():
    raw = 'Here:\n```json\n{"corrections": ["a",], "missing": [], "verdict": "Fair.", "scenarios": {"bull": 0.3, "bear": 0.4, "neutral": 0.3}, "basis": "b"}\n```'
    out = mv._parse_review(raw)
    assert out["verdict"] == "Fair." and out["scenarios"]["bear"] == 0.4


def test_smart_quotes_inside_strings_become_apostrophes():
    raw = '{"corrections": ["note says “up 1%”, facts say 0.9%"], "missing": [], "verdict": "mostly fair", "scenarios": null, "basis": ""}'
    assert mv._parse_review(raw)["corrections"] == ["note says 'up 1%', facts say 0.9%"]


def test_unreadable_answer_returns_none():
    assert mv._parse_review('{"corrections": ["it says "weak" wrongly"], "verdict": "ok"}') is None
    assert mv._parse_review("no json here") is None
