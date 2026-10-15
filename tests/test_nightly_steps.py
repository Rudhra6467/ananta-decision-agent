"""The nightly run is a list of separate steps (research audit, Oct 15): one failing step never skips the Sunday review or the due list,
and the night's note says which steps failed."""
import calendar
import json
import sqlite3
import time
import types
from pathlib import Path

from jarvis.service import core, due_list, strategy_status
from jarvis.service import universe_watch as U

SUNDAY = calendar.timegm(time.strptime("2026-10-18", "%Y-%m-%d")) + 300      # 00:05 UTC on a Sunday, when the daily candles have landed
MONDAY = SUNDAY + 86400


def _j(now):
    return types.SimpleNamespace(dir=str(Path("/nonexistent")), db=sqlite3.connect(":memory:"), now=lambda: now)


def _setup(tmp_path, monkeypatch):
    """A one-item due list, every heavy step replaced by a no-op, and the learning steps ready to be broken by the test."""
    from jarvis.service import ev, graduation, knowledge_build, learning, ndax_book, officer, tier30, universe_explorer

    k = tmp_path / "docs" / "knowledge"
    k.mkdir(parents=True)
    item = {"id": "SUNDAY-REVIEW", "what": "the weekly situation review is written", "how": "see docs/repair_shop/weekly", "due": "2026-10-18", "cadence": "weekly"}
    (k / "due_list.json").write_text(json.dumps({"version": 1, "items": [item]}))
    monkeypatch.setattr(core, "docs_dir", lambda base: tmp_path / "docs")
    monkeypatch.setattr(strategy_status, "load", lambda *a, **kw: {"evidence_window": {"start": "2026-10-15", "days": 60}})
    for n in ("run_rules", "arm", "rebuild", "wake_brain", "forward", "push_passed"):
        monkeypatch.setattr(U, n, lambda *a, **kw: {})
    monkeypatch.setattr(U, "missed", lambda j: [])
    monkeypatch.setattr(U, "_daily_file", lambda j, out: None)
    monkeypatch.setattr(U, "_phone_push", lambda: None)
    monkeypatch.setattr(universe_explorer, "compare_nightly", lambda j: {})
    monkeypatch.setattr(learning, "rebuild_brain", lambda j: {"rebuilt": 0})
    monkeypatch.setattr(learning, "close_counterfactuals", lambda j: {"closed": 0})
    monkeypatch.setattr(learning, "rebuild_trades", lambda j: {})
    monkeypatch.setattr(learning, "rebuild_t3", lambda *a, **kw: {})
    monkeypatch.setattr(learning, "weekly_review", lambda j: {"file": "docs/repair_shop/weekly/2026-10-18.md"})
    monkeypatch.setattr(knowledge_build, "align", lambda j: {})
    monkeypatch.setattr(knowledge_build, "ledger_nightly", lambda j: {"ok": True})
    monkeypatch.setattr(tier30, "T3_DB", "x", raising=False)
    monkeypatch.setattr(ndax_book, "step", lambda j: {})
    monkeypatch.setattr(ev, "fidelity_alert", lambda j, push: [])
    monkeypatch.setattr(ev, "retirement_watch", lambda j, push: [])
    monkeypatch.setattr(graduation, "book500_card", lambda j: {})
    monkeypatch.setattr(officer, "write", lambda j, out, push=None: {"ok": True})
    return learning


def _boom(*a, **kw):
    raise RuntimeError("table brain_decisions has 20 columns but 18 values were supplied")


def test_a_failing_learning_step_does_not_skip_the_sunday_review_or_the_due_list(tmp_path, monkeypatch):
    learning = _setup(tmp_path, monkeypatch)
    monkeypatch.setattr(learning, "rebuild_brain", _boom)
    out = U.run_daily(_j(SUNDAY))
    assert out["steps_failed"] == ["brain_rebuild"] and "20 columns" in out["brain_rebuild_error"]
    assert out["weekly_review"].endswith("2026-10-18.md")                                  # the review still ran
    assert out["sunday_review_ticked"]["marked"] == ["2026-10-18"]                         # and ticked its due-list item
    assert out["due_list"]["overdue"] == [] and "rows" not in out["due_list"]              # the due list was read after the failure


def test_the_review_is_not_run_or_ticked_on_other_days_and_a_missed_sunday_becomes_a_request(tmp_path, monkeypatch):
    learning = _setup(tmp_path, monkeypatch)
    calls = []
    monkeypatch.setattr(learning, "weekly_review", lambda j: calls.append(1) or {"file": "x"})
    j = _j(MONDAY)
    out = U.run_daily(j)
    assert calls == [] and "weekly_review" not in out and out["steps_failed"] == []
    assert out["due_list"]["overdue"] == ["SUNDAY-REVIEW"] and out["due_list"]["flagged"] == ["SUNDAY-REVIEW"]
    assert "SUNDAY-REVIEW" in j.db.execute("SELECT text FROM owner_requests").fetchone()[0]


def test_a_failing_first_group_step_is_named_too_and_a_failing_review_is_not_ticked(tmp_path, monkeypatch):
    learning = _setup(tmp_path, monkeypatch)
    monkeypatch.setattr(U, "run_rules", _boom)
    monkeypatch.setattr(learning, "weekly_review", _boom)
    out = U.run_daily(_j(SUNDAY))
    assert out["steps_failed"] == ["rules", "weekly_review"]
    assert "sunday_review_ticked" not in out and out["due_list"]["overdue"] == []         # due today, not yet late; a failed review stays unticked


def test_the_nights_note_says_which_steps_failed_and_prints_the_due_line(tmp_path, monkeypatch):
    monkeypatch.setattr(core, "docs_dir", lambda base: tmp_path / "docs")        # the real _daily_file, with only what it reads replaced
    monkeypatch.setattr(U, "scoreboard", lambda j: {"watches": []})
    monkeypatch.setattr(U, "status", lambda j: {"counts": {}})
    out = {"steps_failed": ["brain_rebuild"], "due_list": {"overdue": ["SUNDAY-REVIEW"], "soon": [], "waiting_for_evidence": ["EV-Q1"], "post_window": ["PW-X"], "problems": []}}
    U._daily_file(_j(MONDAY), out)
    text = (tmp_path / "docs" / "repair_shop" / "daily" / "universe_2026-10-19.md").read_text()
    assert "- steps that failed tonight: brain_rebuild" in text
    assert "- due list: 1 overdue (SUNDAY-REVIEW), 0 due this week, 1 waiting for evidence, 1 after the window" in text
    U._daily_file(_j(MONDAY), {})
    again = (tmp_path / "docs" / "repair_shop" / "daily" / "universe_2026-10-19.md").read_text()
    assert "- steps that failed tonight: none" in again and "due list: not checked tonight" in again
