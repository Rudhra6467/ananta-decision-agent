"""23 Nov 2026 (Madhav's cost review): the India answer replay runs weekly (Saturday), and on any night after the Ask's code changed."""
import datetime as dt

from jarvis.india import replay


def test_weekly_runs_on_saturday_over_the_week(monkeypatch):
    monkeypatch.setattr(replay, "cadence", lambda: {"replay": "weekly", "replay_day": 5, "replay_hours": 168})
    go, why, hrs = replay.due_tonight(dt.date(2026, 11, 28), last_t=0)
    assert go and hrs == 168


def test_weekly_skips_a_weekday_without_a_change(monkeypatch):
    monkeypatch.setattr(replay, "cadence", lambda: {"replay": "weekly", "replay_day": 5})
    monkeypatch.setattr(replay, "_ask_changed_since", lambda t: False)
    go, why, _ = replay.due_tonight(dt.date(2026, 11, 24), last_t=1e12)
    assert not go and "weekly" in why


def test_a_change_to_the_ask_runs_it(monkeypatch):
    monkeypatch.setattr(replay, "cadence", lambda: {"replay": "weekly", "replay_day": 5})
    monkeypatch.setattr(replay, "_ask_changed_since", lambda t: True)
    go, why, _ = replay.due_tonight(dt.date(2026, 11, 24), last_t=0)
    assert go and "changed" in why


def test_nightly_when_no_cadence(monkeypatch):
    monkeypatch.setattr(replay, "cadence", lambda: {})
    assert replay.due_tonight(dt.date(2026, 11, 24))[0]


def test_selfcheck_does_not_call_a_weekly_replay_late(tmp_path):
    import json
    from jarvis import selfcheck
    (tmp_path / "docs" / "repair_shop" / "replay").mkdir(parents=True)
    (tmp_path / "docs" / "knowledge").mkdir(parents=True)
    (tmp_path / "docs" / "repair_shop" / "replay" / "latest.json").write_text(json.dumps({"summary": {"night": "2026-11-21"}, "failures": []}))
    (tmp_path / "docs" / "knowledge" / "india_cadence.json").write_text(json.dumps({"replay": "weekly"}))
    out = selfcheck._answers(tmp_path, today=dt.date(2026, 11, 27))
    assert not [o for o in out if "has not finished" in o.get("what", "")]
    out = selfcheck._answers(tmp_path, today=dt.date(2026, 12, 2))
    assert [o for o in out if "has not finished" in o.get("what", "")]
