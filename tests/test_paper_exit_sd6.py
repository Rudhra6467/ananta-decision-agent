"""SD6 paper exit manager — fixtures, gates, cycle integration."""
import json
from pathlib import Path

from src.intelligence import paper_exit as sd6
from src.intelligence.cycle_ingest import _manual_kill, _take_for_sd6
from src.intelligence.paper_exit import HOUR_MS, T0, Book, _bar, _flat, manage_cycle, run_fixtures


def test_fixtures_pass_and_write_proof(tmp_path):
    proof = tmp_path / "proof.json"
    rep = run_fixtures(tmp_path / "fx", proof_path=proof)
    assert rep["status"] == "FIXTURE_PASS", {k: v for k, v in rep["cases"].items() if not v["ok"]}
    saved = json.loads(proof.read_text())
    assert saved["version"] == sd6.VERSION and saved["exec"] is False and saved["counts_for_m2"] is False


def test_committed_proof_matches_version():
    assert sd6.fixture_proven(), "run: python -m src.intelligence.paper_exit fixture"


def _live_take(asset="BTC", core="squeeze", **kw):
    return {"asset": asset, "core": core, "card": f"card.{core}.r3.v1", "direction": "NONE", "evidence_class": "LIVE_PAPER", **kw}


def test_manage_cycle_opens_then_manages_then_closes(tmp_path):
    proof = tmp_path / "proof.json"
    run_fixtures(tmp_path / "fx", proof_path=proof)
    book = tmp_path / "book.sqlite"
    hist = _flat(60)
    n = len(hist)
    feed = {"BTC": list(hist)}
    fetch = lambda a: feed[a]  # noqa: E731

    now = hist[-1][0] + HOUR_MS + 60_000
    r1 = manage_cycle([_live_take(decision_bar_open_ms=hist[-1][0])], fetch_bars=fetch, now_ms=now, book_path=book, proof_path=proof)
    assert [o["status"] for o in r1["opened"]] == ["OPENED"]
    assert r1["ledger"]["cash"] == 900.0 and r1["ledger"]["exec"] is False

    # same cycle again: slot is full, nothing new opens, no bar is double-processed
    r1b = manage_cycle([_live_take(asset="ETH")], fetch_bars=lambda a: feed["BTC"], now_ms=now, book_path=book, proof_path=proof)
    assert r1b["refused"][0]["reason"] == "SLOT_FULL"
    assert r1b["managed"][0]["events"] == []

    # next bar breaks the hard stop -> closed by module A, cash returns net of the loss
    feed["BTC"] = hist + [_bar(n, 100.0, 100.1, 97.0, 97.5)]
    r2 = manage_cycle([], fetch_bars=fetch, now_ms=now + HOUR_MS, book_path=book, proof_path=proof)
    ev = r2["managed"][0]["events"]
    assert ev and ev[-1]["kind"] == "CLOSED" and ev[-1]["exit_reason"] == "STOP_LOSS"
    led = r2["ledger"]
    assert led["trade_count"] == 1 and led["losses"] == 1 and led["open_positions"] == []
    assert 997.0 < led["cash"] < 998.0  # -2.2% of $100 plus two 8bp haircuts
    assert led["counts_for_m2"] is False


def test_unclosed_bar_is_never_used(tmp_path):
    proof = tmp_path / "proof.json"
    run_fixtures(tmp_path / "fx", proof_path=proof)
    hist = _flat(60)
    forming = [T0 + len(hist) * HOUR_MS, 100.0, 100.0, 50.0, 50.0, 1.0]  # still open bar with a crash in it
    now = forming[0] + HOUR_MS / 2
    r = manage_cycle([_live_take()], fetch_bars=lambda a: hist + [forming], now_ms=now, book_path=tmp_path / "b.sqlite", proof_path=proof)
    assert r["opened"][0]["status"] == "OPENED"
    assert abs(r["opened"][0]["entry_fill"] - 100.08) < 1e-9


def test_live_book_refuses_fixture_and_book_kind_is_sticky(tmp_path):
    path = tmp_path / "live.sqlite"
    b = Book(path)
    b.close()
    try:
        Book(path, fixture=True)
    except ValueError as exc:
        assert "BOOK_KIND_MISMATCH" in str(exc)
    else:
        raise AssertionError("fixture book opened on a live book file")


def test_fetch_error_is_reported_not_hidden(tmp_path):
    proof = tmp_path / "proof.json"
    run_fixtures(tmp_path / "fx", proof_path=proof)

    def boom(_asset):
        raise RuntimeError("hands unreachable")

    r = manage_cycle([_live_take()], fetch_bars=boom, now_ms=T0, book_path=tmp_path / "b.sqlite", proof_path=proof)
    assert r["opened"] == [] and "hands unreachable" in r["refused"][0]["reason"]


def test_ingest_maps_only_paper_path_takes():
    item = {"symbol": "BTC/USD", "last_bar_open": "1790683200000.0", "kill_switches": {"manual_kill": True},
            "strategy_observations": [{"strategy": "squeeze", "structural_stop": "95.5"}]}
    out = {"issued": "TAKE", "paper_path": {"core": "squeeze", "best_id": "card.squeeze.r3.v1", "evidence_class": "LIVE_PAPER"},
           "l2_state": {"direction": "LONG"}, "decision_store": {"id": "d1"}}
    t = _take_for_sd6(item, out, "BTC", "c1")
    assert t["core"] == "squeeze" and t["structural_stop"] == 95.5 and t["decision_bar_open_ms"] == "1790683200000.0"
    assert _take_for_sd6(item, {**out, "issued": "WAIT"}, "BTC", "c1") is None
    assert _manual_kill(item) is True and _manual_kill({"kill_switches": {"manual_kill": False}}) is False


if __name__ == "__main__":  # runnable without pytest
    import inspect
    import tempfile

    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            args = [Path(tempfile.mkdtemp())] if inspect.signature(fn).parameters else []
            fn(*args)
            print("ok", name)
