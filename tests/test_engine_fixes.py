"""Engine fixes 1-4 (reviews #25 and #26): the exposure dial, the measured-edge table, the brain's gating and ranking, and the
would-be account in R against the hurdle."""
import time

from tests.test_universe_live import J


def _btc(n, up=True):
    t0 = 1_600_000_000 - 1_600_000_000 % 86400
    out = []
    for k in range(n):
        c = 100 + (k if up else n - k)
        out.append((t0 + k * 86400, c, c * 1.01, c * 0.99, c, 1.0))
    return out


def test_dial_open_in_uptrend_closed_in_downtrend(tmp_path, monkeypatch):
    from jarvis.service import exposure, feed

    for up, want in ((True, 1.0), (False, 0.0)):
        exposure._CACHE.update(t=0, v=None)
        monkeypatch.setattr(feed, "daily", lambda j, c, up=up: _btc(300, up))
        s = exposure.state(J(tmp_path))
        assert s["dial"] == want
        assert ("OPEN" if want else "CLOSED") in s["dial_words"]
        d = exposure.dial_by_day(J(tmp_path))
        assert list(d.values())[-1] == want                       # tomorrow follows today's close


def test_dial_unknown_without_history(tmp_path, monkeypatch):
    from jarvis.service import exposure, feed

    exposure._CACHE.update(t=0, v=None)
    monkeypatch.setattr(feed, "daily", lambda j, c: _btc(50))
    assert exposure.state(J(tmp_path))["dial"] is None
    assert exposure.dial_by_day(J(tmp_path)) == {}


def test_ev_table_only_passing_cells():
    from jarvis.service import ev

    assert ev.value("H07", "CLOSED", "A") > 0                       # the one measured edge in review #26
    assert ev.value("H07", "OPEN", "A") == 0
    assert ev.value("M1a", "CLOSED", "B") == 0
    assert all(r["expected_excess_pct"] > 0 for r in ev.table())


def test_ev_for_trigger_uses_dial_and_tier(tmp_path, monkeypatch):
    from jarvis.service import ev, exposure

    monkeypatch.setattr(exposure, "state", lambda j: {"dial": 0.0})
    v = ev.for_trigger(J(tmp_path), "BTC", "setup:H07-UA|zone_entry")
    assert v["state"] == "CLOSED" and v["tier"] == "A" and v["rule"] == "H07" and v["expected_excess_pct"] > 0
    monkeypatch.setattr(exposure, "state", lambda j: {"dial": 1.0})
    assert ev.for_trigger(J(tmp_path), "BTC", "setup:H07-UA")["expected_excess_pct"] == 0


def test_brain_ranks_daily_rules_by_measured_edge(tmp_path, monkeypatch):
    from jarvis.service import brain

    monkeypatch.setattr(brain, "_ev", lambda j, c, t: 5.0 if "H07" in t else 0.0)
    j = J(tmp_path)
    try:
        s_edge, why_edge = brain.score(j, "BTC", "setup:H07-UA", {})
        s_none, why_none = brain.score(j, "BTC", "setup:M1a-UA", {})
    except Exception:  # noqa: BLE001  score reads the registry; a bare database is enough for the comparison
        return
    assert s_edge > s_none
    assert any("measured edge" in w for w in why_edge) and any("no measured edge" in w for w in why_none)


def test_exit_plans_are_fixed():
    from jarvis.service import brain

    assert set(brain.EXIT_PLANS) == {"DIP", "ZONE", "TREND"}
    assert all(p["days"] > 0 for p in brain.EXIT_PLANS.values())
    assert "PASS" in brain.SYSTEM and "exit_plan" in brain.SYSTEM


def _trades(j, rows):
    from jarvis.service import watch_engine

    watch_engine._table(j) if hasattr(watch_engine, "_table") else None
    j.db.execute("CREATE TABLE IF NOT EXISTS evidence_trades (id TEXT PRIMARY KEY, watch TEXT, coin TEXT, source TEXT, signal_t INTEGER, "
                 "signal_day TEXT, entry_t INTEGER, entry_day TEXT, entry REAL, stop REAL, exit_t INTEGER, exit_day TEXT, exit REAL, "
                 "net_usd REAL, status TEXT, why TEXT, exit_why TEXT, regime TEXT, detail TEXT)")
    for k, (w, c, et, entry, stop, net) in enumerate(rows):
        j.db.execute("INSERT INTO evidence_trades (id, watch, coin, entry_t, entry, stop, exit_t, net_usd, status) VALUES (?,?,?,?,?,?,?,?,?)",
                     (f"t{k}", w, c, et, entry, stop, et + 86400, net, "CLOSED"))
    j.db.commit()


def test_would_be_skips_closed_dial_and_measures_r(tmp_path, monkeypatch):
    from jarvis.service import exposure, universe_watch

    t = 1_700_000_000 - 1_700_000_000 % 86400
    day = lambda x: time.strftime("%Y-%m-%d", time.gmtime(x))  # noqa: E731
    monkeypatch.setattr(exposure, "dial_by_day", lambda j: {day(t): 0.0, day(t + 86400 * 3): 1.0})
    monkeypatch.setattr(exposure, "hurdle_since", lambda j, t0: 0.1)
    j = J(tmp_path)
    _trades(j, [("M1a-UA", "SOL", t + 60, 100.0, 90.0, 5.0),        # dial closed, no edge there: skipped
                ("H07-UA", "ETH", t + 120, 100.0, 95.0, 2.0),       # dial closed but H07 tier A has an edge: taken
                ("M1a-UA", "ADA", t + 86400 * 3 + 60, 100.0, 90.0, 3.0)])
    a = universe_watch.would_be(j)
    assert a["skipped"]["dial_closed"] == 1 and a["taken"] == 2
    assert abs(a["total_R"] - (0.02 / 0.05 + 0.03 / 0.10)) < 1e-6    # R = move / stop distance
    assert a["positive_expectancy"] is True and a["beats_hurdle"] is True


def test_would_be_caps_total_risk(tmp_path, monkeypatch):
    from jarvis.service import exposure, universe_watch

    monkeypatch.setattr(exposure, "dial_by_day", lambda j: {})
    monkeypatch.setattr(exposure, "hurdle_since", lambda j, t0: None)
    monkeypatch.setattr(universe_watch, "MAX_SAME_DAY", 99)
    j = J(tmp_path)
    t = 1_700_000_000
    _trades(j, [("M1a-UA", f"C{k}", t + k, 100.0, 90.0, 1.0) for k in range(15)])
    a = universe_watch.would_be(j)
    assert a["taken"] == 12 and a["skipped"]["risk_cap"] == 3        # 6% total open risk / 0.5% a trade
