"""9 Nov 2026 (the outsider readiness review; Madhav: "yes, lets complete"): the day plan, the morning view and the shadow trader's plan for
Monday 9 Nov were written on Saturday morning and the view was pushed three times. They are written once, on the session's own morning in India."""
import datetime as dt
import json

from india import dayplan, morning


def _setup(monkeypatch, tmp_path, today: dt.date, nxt: dt.date):
    monkeypatch.setattr(dayplan, "D", tmp_path)
    monkeypatch.setattr(dayplan, "ist_today", lambda: today)
    monkeypatch.setattr(dayplan, "next_session", lambda after=None: nxt)
    monkeypatch.setattr(dayplan, "overnight", lambda: {"NIFTY 50": {"date": "2026-11-09", "close": 25000.0}})
    monkeypatch.setattr(dayplan, "climatology", lambda band=0.003: {"bull": 0.4, "bear": 0.33, "neutral": 0.27, "sessions": 4700})
    monkeypatch.setattr(dayplan.forecast, "write", lambda *a, **k: {"made_at": "2026-11-11T01:20:00+00:00", "forecast_id": "FC-test"})


def test_no_plan_is_written_on_a_holiday_morning(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path, dt.date(2026, 11, 10), dt.date(2026, 11, 11))       # Tuesday 10 Nov, a market holiday; next session Wednesday
    r = dayplan.run()
    assert r["written"] is False and "own morning" in r["note"]
    assert not (tmp_path / "paper" / "dayplans" / "2026-11-11.json").exists()
    assert dayplan.own_morning() is None


def test_the_plan_is_written_on_the_sessions_own_morning(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path, dt.date(2026, 11, 11), dt.date(2026, 11, 11))
    r = dayplan.run()
    p = tmp_path / "paper" / "dayplans" / "2026-11-11.json"
    assert p.exists() and r["forecast_id"] == "FC-test"
    assert json.loads(p.read_text())["session"] == "2026-11-11"
    assert dayplan.own_morning() == dt.date(2026, 11, 11)
    assert dayplan.run()["note"] == "already written"          # a second run the same morning changes nothing


def test_the_evening_jobs_proof_owes_no_plan_on_a_non_session_morning(tmp_path):
    hol = {dt.date(2026, 11, 10)}
    ctx = {"data": tmp_path, "hol": hol, "out_lines": []}
    tor = dt.timezone(dt.timedelta(hours=-5))
    ok, words = morning.proof(morning.PREFIX + "evening", dt.datetime(2026, 11, 9, 20, 20, tzinfo=tor), ctx)     # 06:50 IST on Tue 10 Nov, a holiday
    assert ok is None and "no session" in words and "2026-11-11" in words
    ok, words = morning.proof(morning.PREFIX + "evening", dt.datetime(2026, 11, 10, 20, 20, tzinfo=tor), ctx)    # 06:50 IST on Wed 11 Nov, a session
    assert ok is False and "2026-11-11" in words
    (tmp_path / "paper" / "dayplans").mkdir(parents=True)
    (tmp_path / "paper" / "dayplans" / "2026-11-11.json").write_text("{}")
    ok, _ = morning.proof(morning.PREFIX + "evening", dt.datetime(2026, 11, 10, 20, 20, tzinfo=tor), ctx)
    assert ok is True
