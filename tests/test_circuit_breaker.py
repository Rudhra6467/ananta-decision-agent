"""Circuit breaker: forced loss streak, drawdown trip, human-only resume, watch integration."""
import json
import os
from pathlib import Path

from src.intelligence import candidate_paper as cp
from src.intelligence import circuit_breaker as cb
from src.intelligence import paper_watch as w

H = 3_600_000


def _t(i, net):
    return {"id": f"t{i}", "coin": "BTC", "net_usd": net, "exit_reason": "STOP", "exit_ms": 1_790_000_000_000 + i * H}


def test_forced_loss_streak_trips_at_4(tmp_path):
    p = tmp_path / "b.json"
    trades = [_t(0, +5.0)] + [_t(i, -2.0) for i in range(1, 4)]
    r = cb.evaluate("v1", trades, 1000.0, path=p)
    assert r["status"] == "ARMED" and r["consecutive_losses"] == 3
    trades.append(_t(4, -2.0))
    r = cb.evaluate("v1", trades, 1000.0, path=p)
    assert r["status"] == "TRIPPED" and r["newly_tripped"] and "4 losses in a row" in r["reason"]
    assert len(r["evidence"]) == 4
    r = cb.evaluate("v1", trades + [_t(5, +50.0)], 1000.0, path=p)  # a win does NOT auto-resume
    assert r["status"] == "TRIPPED" and not r["newly_tripped"]
    assert cb.is_tripped("v1", p)


def test_drawdown_trips_before_streak(tmp_path):
    p = tmp_path / "b.json"
    trades = [_t(0, -120.0), _t(1, +1.0), _t(2, -90.0)]  # $209 peak-to-trough on $1000 start >= 20%
    r = cb.evaluate("v1", trades, 1000.0, path=p)
    assert r["status"] == "TRIPPED" and "drawdown" in r["reason"]


def test_only_a_named_human_can_resume_and_the_count_restarts(tmp_path):
    p = tmp_path / "b.json"
    trades = [_t(i, -2.0) for i in range(4)]
    cb.evaluate("v1", trades, 1000.0, path=p)
    try:
        cb.resume("v1", "   ", path=p)
    except ValueError:
        pass
    else:
        raise AssertionError("resume without a name must fail")
    out = cb.resume("v1", "Vamsi", path=p)
    assert out["status"] == "ARMED"
    st = json.loads(p.read_text())["v1"]
    assert st["history"][-1]["resumed_by"] == "Vamsi"
    # the old losses do not count again after a human resume
    r = cb.evaluate("v1", trades, 1000.0, path=p)
    assert r["status"] == "ARMED" and r["consecutive_losses"] == 0


def test_watch_blocks_new_v1_entries_when_tripped(tmp_path, monkeypatch=None):
    os.chdir(tmp_path)
    os.environ["ANANTA_WATCH_NOTIFY"] = "0"
    os.environ["ANANTA_NTFY_TOPIC"] = ""
    w.ENVELOPE = tmp_path / "cycle_all.json"
    breaker = tmp_path / "breaker.json"
    cb.evaluate("v1.sqlite", [_t(i, -2.0) for i in range(4)], 1000.0, path=breaker)
    calls = []
    real = cp.tick

    def spy(**kw):
        calls.append((kw.get("rules"), kw.get("new_entries")))
        return {"events": [], "errors": [], "ledger": {"cash": 1000.0}}

    cp.tick = spy
    try:
        from tests.test_paper_watch import _env
        fetch = lambda a: (_ for _ in ()).throw(AssertionError("no fetch"))  # noqa: E731
        r = w.tick(cycle=lambda: _env(1_790_683_200_000.0, "cb1"), sd6_kw={"fetch_bars": fetch, "book_path": tmp_path / "s.sqlite"},
                   candidate=True, cand_kw={"book_path": tmp_path / "v0.sqlite", "v1_book_path": tmp_path / "v1.sqlite",
                                            "breaker_path": breaker})
    finally:
        cp.tick = real
    assert ("V1_RIDE", False) in calls and ("V0_TRAIL", False) in calls
    assert r["candidate_v1"]["breaker"]["status"] == "TRIPPED"


if __name__ == "__main__":
    import inspect
    import tempfile

    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn(*([Path(tempfile.mkdtemp())] if "tmp_path" in inspect.signature(fn).parameters else []))
            print("ok", name)
