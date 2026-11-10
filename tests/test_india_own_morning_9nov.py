"""9 Nov 2026 (the outsider readiness review; Madhav: "yes, lets complete"): Monday's morning note was written and pushed on Saturday, Sunday
and Monday, and the shadow trader sealed Monday's plan on Saturday. One note, one push and one seal, on the session's own morning in India."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _never(*a, **k):
    raise AssertionError("the model must not be called on a skipped morning")


def test_no_note_and_no_push_before_the_sessions_own_morning(monkeypatch, capsys):
    mv = _load("india_morningview")
    monkeypatch.setattr(mv, "_get", lambda path: {"session": "2026-11-11", "lines": {"headline": "x"}})
    monkeypatch.setattr(mv, "_ist_today", lambda: "2026-11-10")
    monkeypatch.setattr(mv, "claude", _never)
    monkeypatch.setattr(mv, "_push", _never)
    assert mv.morning() == 0
    assert "written on its own morning" in capsys.readouterr().out


def test_one_note_a_session(monkeypatch, capsys):
    mv = _load("india_morningview")
    monkeypatch.setattr(mv, "_get", lambda path: {"session": "2026-11-11", "words_at": "2026-11-11T03:00:40+00:00", "lines": {"headline": "x"}})
    monkeypatch.setattr(mv, "_ist_today", lambda: "2026-11-11")
    monkeypatch.setattr(mv, "claude", _never)
    monkeypatch.setattr(mv, "_push", _never)
    monkeypatch.setattr(sys, "argv", ["india_morningview", "morning"])
    assert mv.morning() == 0
    assert "already written" in capsys.readouterr().out


def test_the_shadow_trader_seals_on_the_sessions_own_morning_only(monkeypatch, capsys):
    st = _load("india_shadow_trader")
    monkeypatch.setattr(st, "_get", lambda path: {"session": "2026-11-11"})
    monkeypatch.setattr(st, "_ist_today", lambda: "2026-11-10")
    monkeypatch.setattr(st, "claude", _never)
    assert st.main() == 0
    assert "sealed on its own morning" in capsys.readouterr().out


def test_the_reviewers_odds_survive_an_answer_that_is_cut_off():
    mv = _load("india_morningview")
    raw = '{"scenarios": {"bull": 0.38, "bear": 0.35, "neutral": 0.27}, "basis": "two US falls; a \\"stretched\\" Nifty", "verdict": "Mostly fair.", "corrections": ["\\"against a coin flip of 50%\\": the odds are three-way'
    assert mv._parse_review(raw) is None
    got = mv._salvage(raw)
    assert got["scenarios"] == {"bull": 0.38, "bear": 0.35, "neutral": 0.27}
    assert got["verdict"] == "Mostly fair." and got["basis"].startswith("two US falls")
    assert mv._salvage("I could not review this.") == {}


def test_the_writer_sees_the_plain_lines_whole():
    """9 Nov 2026: the facts for the writer were cut at 14,000 characters and the cut fell inside "lines", the last key."""
    mv = _load("india_morningview")
    f = {"session": "2026-11-11", "lines": {"holdings": ["TATACHEM: filed its results."], "watch": ["Guardrails: a 5% loss stops the day."]},
         "plan": {"filler": "x" * 15000}, "overnight": {}, "setup": {}, "scorecard": {}, "yesterday": {}}
    t = mv._facts_for_prompt(f)
    assert "TATACHEM: filed its results." in t and "Guardrails: a 5% loss stops the day." in t and t.index('"lines"') < t.index('"plan"')
