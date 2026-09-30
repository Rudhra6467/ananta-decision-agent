"""Unattended paper watch: one tick = Hands cycle -> ingest -> SD6 -> heartbeat -> alerts."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from src.intelligence import paper_watch as w

NAMES = ["BTC", "ETH", "SOL", "ADA", "DOGE", "AVAX", "BCH", "LINK", "LTC", "XRP"]


def _env(bar_ms: float, cid: str):
    def row(a):
        return {"symbol": f"{a}/USD", "snapshot": {"price": 100.0}, "kill_switches": {"manual_kill": False},
                "regime": {"market": "BULL", "asset": "RANGE"},
                "strategy_observations": [{"strategy": "hunter", "ran": True, "regime": "RANGE", "setup_detected": False, "decision": "WAIT"}],
                "bar_tf": "1h", "last_bar_open": str(bar_ms)}
    return {"contract": "ananta.shared.v0.1", "cycle_id": cid, "as_of_time": "2026-09-29T12:02:00+00:00",
            "results": [row(a) for a in NAMES], "bar_tf": "1h", "last_bar_open": str(bar_ms)}


def _in(tmp_path):
    os.chdir(tmp_path)
    w.ENVELOPE = tmp_path / "cycle_all.json"
    os.environ["ANANTA_WATCH_NOTIFY"] = "0"
    os.environ["ANANTA_CANDIDATE_PAPER"] = "0"


def test_tick_heartbeat_and_gap(tmp_path):
    _in(tmp_path)
    fetch = lambda a: (_ for _ in ()).throw(AssertionError("no fetch without a position"))  # noqa: E731
    b0 = 1_790_683_200_000.0
    r1 = w.tick(cycle=lambda: _env(b0, "c1"), sd6_kw={"fetch_bars": fetch, "book_path": tmp_path / "b.sqlite"})
    assert r1["ok"] and r1["missed_bars_since_previous"] == 0 and r1["takes"] == []
    assert len(r1["regimes"]) == 10 and r1["counts_for_m2"] is False
    # three hours later: two bars were never looked at
    r2 = w.tick(cycle=lambda: _env(b0 + 3 * 3_600_000, "c2"), sd6_kw={"fetch_bars": fetch, "book_path": tmp_path / "b.sqlite"})
    assert r2["missed_bars_since_previous"] == 2
    alerts = [json.loads(x) for x in (tmp_path / "watch_alerts.jsonl").read_text().splitlines()]
    assert any(a["title"].endswith("gap") for a in alerts)
    assert (tmp_path / "watch_runs" / "c2.json").exists()


def test_hands_down_is_recorded_not_guessed(tmp_path):
    _in(tmp_path)

    def down():
        raise RuntimeError("connection refused")

    r = w.tick(cycle=down)
    assert r["ok"] is False and "connection refused" in r["error"]
    assert w._last_heartbeat() is None  # a failed look never becomes the gap baseline
    alerts = (tmp_path / "watch_alerts.jsonl").read_text()
    assert "Hands unreachable" in alerts


def test_candidate_runs_inside_the_watch_and_errors_are_contained(tmp_path):
    _in(tmp_path)
    fetch = lambda a: (_ for _ in ()).throw(AssertionError("no fetch without a position"))  # noqa: E731

    def cand_fetch(coin, tf, limit):
        raise RuntimeError("hands candles down")

    r = w.tick(cycle=lambda: _env(1_790_683_200_000.0, "c9"), sd6_kw={"fetch_bars": fetch, "book_path": tmp_path / "b.sqlite"},
               candidate=True, cand_kw={"fetch": cand_fetch, "book_path": tmp_path / "cand.sqlite"})
    assert r["ok"] is True  # the watch survives a candidate failure
    assert len(r["candidate"]["errors"]) == 10 and r["candidate"]["book"]["cash"] == 1000.0


def test_schedule_is_two_minutes_after_close():
    t = datetime(2026, 9, 29, 15, 26, 54, tzinfo=timezone.utc)
    assert round(w.seconds_to_next_look(t)) == (60 - 26) * 60 - 54 + 120
    t2 = datetime(2026, 9, 29, 15, 1, 0, tzinfo=timezone.utc)
    assert round(w.seconds_to_next_look(t2)) == 60


if __name__ == "__main__":
    import inspect
    import tempfile

    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn(*([Path(tempfile.mkdtemp())] if inspect.signature(fn).parameters else []))
            print("ok", name)
