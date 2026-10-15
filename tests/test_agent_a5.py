"""Fix A5 (Oct 15): the wake mix follows the registry and the evidence. Zone touches and Explorer setups are logged and scored, not
decided (the registry keeps them from waking the brain); the brain's own plan (an expectation) and the dial opening go first, inside
the day's dollar; the last slots of the account are kept for priority moments."""
from tests.test_engine_fixes import _trades
from tests.test_universe_live import J


def _setup(tmp_path, monkeypatch):
    from jarvis.service import brain

    j = J(tmp_path)
    brain._table(j)
    _trades(j, [])
    monkeypatch.setattr(brain, "_dial", lambda jj: 1.0)
    monkeypatch.setattr(brain, "_live_px", lambda jj, c: 1.0)
    monkeypatch.setattr(brain, "can_decide", lambda jj: (True, ""))
    monkeypatch.setattr(brain, "score", lambda jj, c, t, d: (5.0, ["test"]))
    seen = []
    monkeypatch.setattr(brain, "decide", lambda jj, c, trig, call=None, push=None, noroom=False: seen.append((c, noroom)) or {"action": "PASS"})
    return j, seen


def test_the_registry_decides_which_kinds_wake_the_brain():
    from jarvis.service import brain

    assert brain._monitor_only("zone_entry").startswith("monitoring only") and "ZONE_TOUCH" in brain._monitor_only("zone_entry")
    assert "EXPLORER" in brain._monitor_only("explorer:E4|zone_entry")
    assert brain._monitor_only("hunter")                                     # the hourly watch is parked
    assert brain._monitor_only("setup:ZONE_TOUCH-UA")                        # a daily watch the registry keeps quiet
    assert brain._monitor_only("setup:H07-UA") == ""                         # the one measured edge always reaches the brain
    assert brain._monitor_only("zone_entry|setup:H07-UA") == ""              # one decidable kind is enough
    assert brain._monitor_only("attention_high") == "" and brain._monitor_only("expectation:abc") == ""
    assert brain._priority("zone_entry|expectation:abc") and brain._priority("dial_open") and not brain._priority("setup:H07-UA")


def test_the_brains_own_plan_and_the_dial_opening_rank_with_the_measured_rules(tmp_path):
    from jarvis.service import brain

    j = J(tmp_path)
    assert brain.moment(j, "SOL", "expectation:e1", {})[0] == 2.0
    assert brain.moment(j, "BTC", "dial_open", {})[0] == 2.0
    assert brain.moment(j, "SOL", "zone_entry", {})[0] < brain.PRIORITY_POINTS
    assert brain.moment(j, "SOL", "attention_high", {})[0] < brain.PRIORITY_POINTS


def test_monitoring_wakes_are_logged_once_per_coin_and_never_decided(tmp_path, monkeypatch):
    from jarvis.service import brain

    j, seen = _setup(tmp_path, monkeypatch)
    brain.wake(j, "SOL", "zone_entry")
    brain.process(j)
    brain.wake(j, "SOL", "explorer:E2")
    brain.process(j)
    assert seen == []
    rows = j.db.execute("SELECT coin, reason, price FROM brain_unreviewed").fetchall()
    assert len(rows) == 1 and rows[0][1].startswith("monitoring only") and rows[0][2] == 1.0   # priced, so it is scored later
    states = [s for (s,) in j.db.execute("SELECT state FROM brain_queue")]
    assert any(s.startswith("DROPPED: monitoring only") for s in states)


def test_the_brains_own_plan_skips_the_wait_and_the_pacing_but_never_the_days_dollar(tmp_path, monkeypatch):
    from jarvis.service import brain

    j, seen = _setup(tmp_path, monkeypatch)
    j.db.execute("INSERT INTO brain_decisions (id, t, coin, action, cost_usd) VALUES (?,?,?,?,?)", ("d1", int(j.now()) - 3600, "SOL", "PASS", 0.0))
    j.db.commit()
    brain.wake(j, "SOL", "attention_high")                                   # an ordinary wake waits 6 hours after a decision
    brain.process(j)
    assert seen == []
    brain.wake(j, "SOL", "expectation:e1")                                   # the brain's own plan does not
    brain.process(j)
    assert seen == [("SOL", False)]
    monkeypatch.setattr(brain, "paced_budget", lambda jj: 0.10)              # the paced budget is used
    monkeypatch.setattr(brain, "spent_today", lambda jj: 0.20)
    brain.wake(j, "ETH", "attention_high")
    brain.wake(j, "ADA", "expectation:e2")
    brain.process(j)
    assert [c for c, _ in seen] == ["SOL", "ADA"]
    assert j.db.execute("SELECT state FROM brain_queue WHERE coin='ETH'").fetchone()[0] == "NEW"   # waits for budget
    monkeypatch.setattr(brain, "spent_today", lambda jj: brain.DAILY_USD)   # the day's dollar is spent: nothing goes
    brain.wake(j, "XRP", "expectation:e3")
    brain.process(j)
    assert [c for c, _ in seen] == ["SOL", "ADA"]


def test_the_last_slots_are_kept_for_priority_moments(tmp_path, monkeypatch):
    from jarvis.service import brain

    j, seen = _setup(tmp_path, monkeypatch)
    for k in range(brain.MAX_OPEN - brain.RESERVED):
        j.db.execute("INSERT INTO evidence_trades (id, watch, coin, status, detail) VALUES (?,?,?,?,?)", (f"o{k}", "JARVIS", f"C{k}", "OPEN", "{}"))
    j.db.commit()
    brain.wake(j, "SOL", "attention_high")                                   # an ordinary moment: decided, a buy kept as evidence only
    brain.wake(j, "ETH", "expectation:e1")                                   # the brain's own plan: a real slot
    brain.process(j)
    got = dict(seen)
    assert isinstance(got["SOL"], str) and "kept for priority moments" in got["SOL"]
    assert got["ETH"] is False
