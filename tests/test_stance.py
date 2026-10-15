"""Fixes A2/A3 (Oct 15): the brain's written stance after each daily close, and its expectations written before the move, followed
every 15 minutes and scored like passes (a day and five days on) and by their exit plan against a random twin."""
import json

import pytest

from tests.test_universe_live import J

DAY = 86400
T0 = 1_760_000_000 - 1_760_000_000 % DAY          # "today", 00:00 UTC
T5 = T0 + 7800                                     # the 5-minute candle where SOL dips to its trigger


def _hist(last: float = 100.0) -> list[tuple]:
    """260 closed daily candles ending yesterday, a gentle uptrend that closes at `last`."""
    out, prev = [], None
    for k in range(260):
        c = last * 1.001 ** (k - 259)
        out.append((T0 - (260 - k) * DAY, prev or c, c * 1.01, c * 0.99, c, 1.0))
        prev = c
    return out


def _future(path: list[float]) -> list[tuple]:
    return [(T0 + k * DAY, c, c * 1.005, c * 0.995, c, 1.0) for k, c in enumerate(path)]


UP = [100 * 1.01 ** (k + 1) for k in range(15)]    # +1% a day from tonight on
DAILY = {"BTC": _hist() + _future(UP), "SOL": _hist() + _future(UP), "ADA": _hist() + _future(UP),
         "ETH": _hist() + _future([95.0] + UP[1:])}          # ETH closes under its invalidation on the first day
LIVE = {"BTC": 100.1, "SOL": 100.2, "ETH": 100.1, "ADA": 100.0}
BARS5 = {"SOL": [(T5, 96.0, 96.5, 94.5, 95.5, 1.0)], "BTC": [(T5, 100.0, 100.5, 99.5, 100.0, 1.0)],
         "ETH": [(T5, 100.0, 100.5, 99.5, 100.0, 1.0)]}       # ADA: no 5-minute candles (the live price decides)


def _fake(monkeypatch, tmp_path, now):
    from jarvis.service import brain, stance

    j = J(tmp_path, now=now)
    monkeypatch.setattr(stance, "candidates", lambda jj: ["BTC", "SOL", "ETH", "ADA"])
    monkeypatch.setattr(stance, "_closed_daily", lambda jj, c: [b for b in DAILY.get(c, []) if b[0] + DAY <= jj.now()])
    monkeypatch.setattr(stance, "_live", lambda jj, c: LIVE.get(c))
    monkeypatch.setattr(stance, "_bars5", lambda jj, c, since: [b for b in BARS5.get(c, []) if b[0] >= since and b[0] + 300 <= jj.now()])
    monkeypatch.setattr(stance, "_cost1", lambda c: 0.003)
    monkeypatch.setattr(stance, "_dial", lambda jj: {"dial": 1.0, "dial_words": "OPEN: buying allowed", "why": ["Bitcoin above both"],
                                                     "rule": "review #25"})
    monkeypatch.setattr(brain, "market_median_move", lambda jj, t0, days: 1.0)
    brain._table(j)
    return j


REPLY = {"view": "The dial is open and tier A is broad. I expect the uptrend to continue unless Bitcoin loses its 50-day.",
         "changed": "view changed from cautious to constructive because the dial opened",
         "positions": [],
         "expectations": [
             {"coin": "SOL", "plan": "DIP", "trigger": {"type": "touch_below", "price": 95}, "invalidation": 88, "horizon_days": 3,
              "size_pct": 50, "why": "a 5% dip in an uptrend", "knowledge_used": ["H07"]},
             {"coin": "ETH", "plan": "TREND", "trigger": {"type": "close_above", "price": 104}, "invalidation": 96, "horizon_days": 3,
              "size_pct": 60, "why": "a close above the range", "knowledge_used": ["T3"]},
             {"coin": "ADA", "plan": "ZONE", "trigger": {"type": "touch_below", "price": 91}, "invalidation": 85, "horizon_days": 1,
              "size_pct": 25, "why": "the 200-day zone", "knowledge_used": ["ZONES"]},
             {"coin": "DOGE", "plan": "DIP", "trigger": {"type": "touch_below", "price": 0.2}, "invalidation": 0.18, "horizon_days": 2},
             {"coin": "SOL", "plan": "TREND", "trigger": {"type": "close_above", "price": 104}, "invalidation": 97, "horizon_days": 2},
             {"coin": "BTC", "plan": "TREND", "trigger": {"type": "touch_above", "price": 104}, "invalidation": 105, "horizon_days": 2},
             {"coin": "BTC", "plan": "TREND", "trigger": {"type": "close_above", "price": 99}, "invalidation": 95, "horizon_days": 2}],
         "no_expectation_reason": ""}


def test_stance_is_written_once_after_the_close_and_code_checks_every_expectation(tmp_path, monkeypatch):
    from jarvis.service import stance

    j = _fake(monkeypatch, tmp_path, T0 + 600)
    monkeypatch.setattr(stance, "_may_call", lambda jj: (True, ""))
    stance._table(j)                                            # yesterday's stance had the dial closed
    j.db.execute("INSERT INTO stance (day, t, dial, view, facts, source) VALUES (?,?,?,?,?,?)",
                 (stance._day(T0 - DAY), T0 - DAY + 600, 0.0, "cautious", json.dumps({"dial": {"dial": 0.0}}), "brain"))
    j.db.commit()
    assert stance.due(j)
    seen = {}

    def call(user):
        seen["user"] = user
        return json.dumps(REPLY), {"in": 5000, "out": 800, "model": "fake"}
    r = stance.plan(j, call=call)
    assert r["source"] == "brain" and r["view"].startswith("The dial is open") and r["cost_usd"] == pytest.approx(0.018)
    assert '"candidates"' in seen["user"] and '"H07"' in seen["user"] and "Yesterday's stance" in seen["user"]
    assert sorted(e["coin"] for e in r["expectations"]) == ["ADA", "ETH", "SOL"]
    why = " | ".join(r["rejected"])
    assert "DOGE: not a tier-A candidate" in why and "SOL: one expectation per coin" in why
    assert "BTC: the invalidation must be under the trigger" in why and "BTC: the trigger is already met tonight" in why
    assert "the exposure dial changed from CLOSED to OPEN" in r["facts_diff"]
    assert r.get("woke") == "dial_open"                                     # A5: the dial opening is a moment for the brain
    assert j.db.execute("SELECT trigger FROM brain_queue WHERE coin='BTC'").fetchone()[0] == "dial_open"
    assert not stance.due(j) and stance.plan(j, call=call) is None          # once a day
    rows = stance.expectations(j, stance._day(T0))
    assert {e["status"] for e in rows} == {"OPEN"} and all(e["trigger_price"] > e["invalidation"] for e in rows)
    b = stance.brief(j)
    assert b["view"] == r["view"] and len(b["expectations"]) == 3 and "Start a market answer" in b["say"]
    line = stance.evening_line(j, T0 - 4 * 3600)
    assert line.startswith("Tonight's stance: The dial is open") and "Expectations written: 3" in line


def test_facts_only_when_the_brains_dollar_is_used(tmp_path, monkeypatch):
    from jarvis.service import brain, stance

    j = _fake(monkeypatch, tmp_path, T0 + 600)
    monkeypatch.setenv("BRAIN_ENABLED", "1")
    monkeypatch.delenv("STANCE_AI", raising=False)
    monkeypatch.setattr(brain, "spent_today", lambda jj: 0.95)

    def never(user):
        raise AssertionError("no model call when the day's money is used")
    r = stance.plan(j, call=never)
    assert r["source"] == "facts only" and "facts only, nothing new spent" in r["note"] and r["expectations"] == []
    row = stance.latest(j)
    assert row["source"] == "facts only" and row["view"] is None
    assert "(no written view" in stance.brief(j)["view"]
    assert stance.evening_line(j, T0).startswith("Tonight's stance: facts only")


def test_expectations_trigger_invalidate_expire_and_get_scored(tmp_path, monkeypatch):
    from jarvis.service import stance

    j = _fake(monkeypatch, tmp_path, T0 + 600)
    monkeypatch.setattr(stance, "_may_call", lambda jj: (True, ""))
    stance.plan(j, call=lambda u: (json.dumps(REPLY), {"in": 1, "out": 1, "model": "fake"}))
    # ten minutes after SOL's 5-minute candle touched 95: triggered at 95, a twin drawn, the brain woken with the plan
    j._now = T5 + 300 + 600
    out = stance.watch(j)
    assert out["triggered"] == ["SOL"]
    sol = next(e for e in stance.expectations(j) if e["coin"] == "SOL")
    assert sol["status"] == "TRIGGERED" and sol["fill"] == 95 and sol["woke"] == 1 and sol["twin_coin"] in ("ADA", "BTC", "ETH")
    trig, detail = j.db.execute("SELECT trigger, detail FROM brain_queue WHERE coin='SOL'").fetchone()
    assert trig.startswith("expectation:") and json.loads(detail)[trig]["plan"] == "DIP"
    # the next day: ETH closed under its invalidation before its trigger; ADA's one day ran out with no touch
    j._now = T0 + DAY + 600
    out = stance.watch(j)
    assert out["invalidated"] == ["ETH"] and out["expired"] == ["ADA"]
    # twelve days on: SOL scored a day and five days later (and over the market median), and after its 10-day dip plan
    j._now = T0 + 12 * DAY
    stance.watch(j)
    sol = next(e for e in stance.expectations(j) if e["coin"] == "SOL")
    assert sol["status"] == "SCORED"
    assert sol["after_1d_pct"] == pytest.approx(100 * (UP[1] / 95 - 1), abs=0.06)
    assert sol["after_5d_pct"] == pytest.approx(100 * (UP[5] / 95 - 1), abs=0.06)
    assert sol["after_5d_ex"] == pytest.approx(sol["after_5d_pct"] - 1.0, abs=0.06)
    assert sol["plan_pct"] == pytest.approx(100 * (UP[10] / 95 - 1) - 0.6, abs=0.02)   # out at the close of day 10, net of 0.6%
    assert sol["twin_plan_pct"] is not None
    rec = stance.record(j)
    assert rec["written"] == 3 and rec["triggered"] == 1 and rec["invalidated"] == 1 and rec["expired"] == 1 and rec["plans_done"] == 1


def test_validate_keeps_at_most_five_and_never_repairs():
    from jarvis.service import stance

    coins = ["A1", "A2", "A3", "A4", "A5", "A6", "A7"]
    f = {"candidates": [{"coin": c, "close": 10.0, "live": 10.0} for c in coins]}
    raw = [{"coin": c, "plan": "DIP", "trigger": {"type": "touch_below", "price": 9.5}, "invalidation": 9.0, "horizon_days": 2} for c in coins]
    raw.append({"coin": "A1", "plan": "SWING", "trigger": {"type": "touch_below", "price": 9.5}, "invalidation": 9.0, "horizon_days": 2})
    out, rejected = stance.validate(raw, f)
    assert [e["coin"] for e in out] == coins[:5] and len(rejected) == 3
    bad = [{"coin": "A1", "plan": "DIP", "trigger": {"type": "touch_below", "price": 8.0}, "invalidation": 7.0, "horizon_days": 2},   # 20% away
           {"coin": "A2", "plan": "DIP", "trigger": {"type": "touch_below", "price": 9.5}, "invalidation": 7.5, "horizon_days": 2},   # stop 21% away
           {"coin": "A3", "plan": "DIP", "trigger": {"type": "touch_below", "price": 9.5}, "invalidation": 9.0, "horizon_days": 9},   # waits too long
           {"coin": "A4", "plan": "DIP", "trigger": {"type": "buy_now", "price": 9.5}, "invalidation": 9.0, "horizon_days": 2}]
    assert stance.validate(bad, f)[0] == []


def test_exit_plans_on_daily_candles():
    from jarvis.service import stance

    D = [(T0 + k * DAY, 100.0, 101.0, 90.0 if k == 3 else 99.0, 100.0 + k, 1.0) for k in range(25)]
    assert stance.simulate(D, T0, 100.0, "DIP", 95.0) == pytest.approx(9.0)        # no stop: out at the first close 10 days on
    assert stance.simulate(D, T0, 100.0, "ZONE", 95.0) == pytest.approx(-5.0)      # the stop is hit on day 3
    assert stance.simulate(D[:12], T0, 100.0, "TREND", 80.0) is None               # 20 days have not run yet
