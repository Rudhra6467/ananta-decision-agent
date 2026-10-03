"""Live Explorer: warm-up without trades, 15-minute steps, restart from saved state, kill switch, report, reconstruction."""
import json
import tempfile
from pathlib import Path

from src.intelligence import explorer_engine as xe
from src.intelligence import explorer_live as xl
from tests.test_explorer import T0, _series


class FakeHands:
    """Serves closed bars of synthetic 5m series (resampled per timeframe) up to the fake clock."""

    def __init__(self, clock, days=75):
        from src.research import explorer_replay as xr
        self.clock, self.kill = clock, False
        self.data = {}
        for k, coin in enumerate(xe.COINS):
            b5 = _series(days=days, seed=k + 11)
            self.data[coin] = {tf: (b5 if tf == "5m" else xr.resample(b5, xe.TF_S[tf])) for tf in xe.TF_S}
        self.calls = 0

    def candles(self, coin, tf, limit):
        self.calls += 1
        now = self.clock["now"]
        closed = [b for b in self.data[coin][tf] if b[0] + xe.TF_S[tf] <= now]
        return closed[-limit:]

    def kill_switch_on(self):
        return self.kill


def _mk(days=75, start_day=62):
    d = Path(tempfile.mkdtemp())
    clock = {"now": T0 + start_day * 86400 + 60}
    hands = FakeHands(clock, days)
    alerts = []
    ex = xl.Explorer(d, hands=hands, now=lambda: clock["now"], alert=lambda t, b, lv: alerts.append((t, b, lv)))
    return d, clock, hands, ex, alerts


def _advance(ex, clock, steps):
    for _ in range(steps):
        clock["now"] += 900
        ex.step()


def test_warm_up_places_no_trades_and_steps_scan_every_15_minutes():
    d, clock, hands, ex, alerts = _mk()
    info = ex.start()
    assert not info["resumed"] and all(info["ready"].values())
    assert not [e for e in ex.store.book.execute("SELECT kind FROM events").fetchall()]  # nothing before trade_from
    _advance(ex, clock, 4 * 24)  # one day
    n = sum(1 for _ in open(d / "explorer_decisions.jsonl"))
    assert n >= 10 * 90, n  # ten coins, about 96 scans each
    kinds = {k for (k,) in ex.store.book.execute("SELECT DISTINCT kind FROM events")}
    assert "ORDER" in kinds


def test_restart_resumes_state_and_matches_reconstruction():
    d, clock, hands, ex, alerts = _mk()
    ex.start()
    _advance(ex, clock, 4 * 12)
    ex2 = xl.Explorer(d, hands=hands, now=lambda: clock["now"], alert=lambda *a: None)  # "restart"
    assert ex2.start()["resumed"]
    _advance(ex2, clock, 4 * 24)
    rc = xl.reconstruct(d)
    assert rc["logged_real_events"] > 0 and rc["match"], rc


def test_catch_up_after_a_sleep_keeps_every_scan():
    d, clock, hands, ex, alerts = _mk()
    ex.start()
    _advance(ex, clock, 2)
    clock["now"] += 5 * 3600  # laptop asleep five hours
    ex.step()
    ts = [json.loads(x)["t"] for x in open(d / "explorer_decisions.jsonl") if json.loads(x)["coin"] == "ETH"]
    assert all(b - a == 900 for a, b in zip(ts, ts[1:])), "a scan was skipped during catch-up"


def test_kill_switch_exits_real_trades_and_blocks_entries():
    d, clock, hands, ex, alerts = _mk()
    ex.start()
    for _ in range(4 * 24 * 5):
        clock["now"] += 900
        ex.step()
        if any(t.shadow is None and not t.actual.done for e in ex.st["engines"].values() for t in e.trades):
            break
    assert any(t.shadow is None and not t.actual.done for e in ex.st["engines"].values() for t in e.trades), "fixture never opened a trade"
    hands.kill = True
    _advance(ex, clock, 2)
    assert not any(t.shadow is None and not t.actual.done for e in ex.st["engines"].values() for t in e.trades)
    bells = [json.loads(j)["bell"] for (j,) in ex.store.book.execute("SELECT json FROM events WHERE kind='CLOSED'")]
    assert "X2_KILL_SWITCH" in bells and any(a[0].endswith("KILL SWITCH") for a in alerts)
    _advance(ex, clock, 8)
    reals = [json.loads(j) for (j,) in ex.store.book.execute("SELECT json FROM events WHERE kind='ORDER'")]
    after = [e for e in reals if e["t"] > clock["now"] - 7200]
    assert all(e.get("shadow") for e in after), "no real entries while the kill switch is on"


def test_daily_report_is_written_and_pushed():
    d, clock, hands, ex, alerts = _mk()
    ex.start()
    _advance(ex, clock, 8)
    p = ex.report("2020-01-01")
    assert p.exists() and "Open trades and suggestions" in p.read_text()
    assert any(a[0] == "Ananta daily report" for a in alerts)


def test_weekly_evidence_report():
    d, clock, hands, ex, alerts = _mk()
    ex.start()
    _advance(ex, clock, 4 * 24 * 3)
    p = xl.weekly(d, now=clock["now"])
    txt = p.read_text()
    assert "By setup" in txt and "Shadows" in txt and "Same real trades, other exits" in txt


def test_portfolio_manager_runs_daily_inside_the_explorer():
    import sqlite3
    d, clock, hands, ex, alerts = _mk()
    ex.start()
    _advance(ex, clock, 4 * 24 * 2)
    n = sqlite3.connect(d / "portfolio_book.sqlite").execute("SELECT count(*) FROM decisions").fetchone()[0]
    assert n >= 1
    txt = ex.report("2020-01-01").read_text()
    assert "Portfolio manager (T3, mode SUGGEST)" in txt and "| Coin | Rating | Why |" in txt


def test_intraday_sightings_get_atlas_odds_and_only_reliable_ones_alert():
    import json as _j
    d, clock, hands, ex, alerts = _mk()
    entry = {"CONFIRM": {"n": 500, "3/1.5_24h": {"p_target": 0.3, "net_pct": -0.9}, "cl_4h_p10_p50_p90": [-2, 0, 2]}}
    atlas = {"contexts": {}, "setups": {s: dict(entry, stable_positive_after_costs=(["2/1_24h"] if s == "E8" else []))
                                         for s in ("E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8")}}
    (d / "intraday_atlas.json").write_text(_j.dumps(atlas))
    ex.start()
    _advance(ex, clock, 4 * 24)
    rows = [_j.loads(j) for (j,) in ex.store.book.execute("SELECT json FROM events WHERE kind='SIGHTING'")]
    assert rows, "setups were seen but no sightings were logged"
    intraday_alerts = [a for a in alerts if a[0].startswith("Ananta intraday")]
    assert all(" E8" in a[0] for a in intraday_alerts)
    if any(r["setup"] == "E8" for r in rows):
        assert intraday_alerts
    txt = ex.report(__import__("datetime").datetime.fromtimestamp(clock["now"] - 3600).strftime("%Y-%m-%d")).read_text()
    assert "Intraday setups seen today" in txt


if __name__ == "__main__":
    import inspect

    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn) and not inspect.signature(fn).parameters:
            fn()
            print("ok", name)


def test_widen_switches_rules_from_the_next_scan_and_rebuild_still_matches():
    import json as _json
    d, clock, hands, ex, alerts = _mk()
    ex.start()
    _advance(ex, clock, 4 * 12)
    info = xl.widen("W1", d, now=clock["now"])
    assert info["rules"] == "W1"
    ex2 = xl.Explorer(d, hands=hands, now=lambda: clock["now"], alert=lambda *a: None)   # restart, as live
    assert ex2.start()["resumed"]
    _advance(ex2, clock, 4 * 36)
    recs = [_json.loads(x) for x in open(d / "explorer_decisions.jsonl")]
    assert {"v0", "W1"} <= {r.get("rules") for r in recs}
    assert all(r.get("rules") == "v0" for r in recs if r["t"] < info_t(info))
    rc = xl.reconstruct(d)
    assert rc["logged_real_events"] > 0 and rc["match"], rc
    assert ex2.status()["rules_log"][0]["rules"] == "W1"


def info_t(info):
    from datetime import datetime, timezone
    return int(datetime.strptime(info["from"], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).timestamp()) if ":" in info["from"] else 0
