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
    fee_in = 100.0 * sd6.SETTINGS.fee_entry_bp / 1e4
    assert abs(r1["ledger"]["cash"] - (900.0 - fee_in)) < 1e-6 and r1["ledger"]["exec"] is False

    # same cycle again, same coin: the same signal, nothing new opens (no shadow either), no bar is double-processed
    r1b = manage_cycle([_live_take(asset="BTC")], fetch_bars=lambda a: feed["BTC"], now_ms=now, book_path=book, proof_path=proof)
    assert r1b["refused"][0]["reason"] == "ASSET_ALREADY_OPEN" and r1b["shadow_opened"] == []
    assert r1b["managed"][0]["events"] == []

    # next bar breaks the hard stop -> closed by module A, cash returns net of the loss
    feed["BTC"] = hist + [_bar(n, 100.0, 100.1, 97.0, 97.5)]
    r2 = manage_cycle([], fetch_bars=fetch, now_ms=now + HOUR_MS, book_path=book, proof_path=proof)
    ev = r2["managed"][0]["events"]
    assert ev and ev[-1]["kind"] == "CLOSED" and ev[-1]["exit_reason"] == "STOP_LOSS"
    led = r2["ledger"]
    assert led["trade_count"] == 1 and led["losses"] == 1 and led["open_positions"] == []
    # -2.2% of $100, plus entry and exit fees at the profile rate, plus slippage both ways
    s = sd6.SETTINGS
    exit_mult = 0.978 * (1 - s.slippage_bp / 1e4)  # stop is 2.2% under the (slipped) entry fill, exit slips again
    expect_loss = 100 * (1 - exit_mult) + 100 * s.fee_entry_bp / 1e4 + 100 * exit_mult * s.fee_exit_bp / 1e4
    assert abs((1000.0 - led["cash"]) - expect_loss) < 1e-4, (led["cash"], expect_loss)
    assert led["fees_paid"] > 0 and led["cost_profile"] == s.cost_profile
    assert led["counts_for_m2"] is False


def test_one_trade_per_coin_and_shadows_when_the_book_is_full(tmp_path):
    """v3 (Madhav 2026-10-03): Hunter's book opens one trade per coin instead of one in total; when it is full, a refused
    TAKE is kept as a shadow (same exits, no cash), so its evidence is not lost."""
    from dataclasses import replace

    proof = tmp_path / "proof.json"
    run_fixtures(tmp_path / "fx", proof_path=proof)
    book = tmp_path / "book.sqlite"
    hist = _flat(60)
    n = len(hist)
    feed = {a: list(hist) for a in ("BTC", "ETH", "LTC")}
    now = hist[-1][0] + HOUR_MS + 60_000
    r = manage_cycle([_live_take(asset="BTC", core="hunter"), _live_take(asset="ETH", core="hunter")], fetch_bars=lambda a: feed[a],
                     now_ms=now, book_path=book, proof_path=proof)
    assert [o["asset"] for o in r["opened"]] == ["BTC", "ETH"] and len(r["ledger"]["open_positions"]) == 2   # one per coin
    small = replace(sd6.SETTINGS, max_open=2)
    r2 = manage_cycle([_live_take(asset="LTC", core="hunter")], fetch_bars=lambda a: feed[a], now_ms=now, book_path=book,
                      proof_path=proof, s=small)
    assert r2["refused"][0]["reason"] == "SLOT_FULL" and r2["shadow_opened"] == ["LTC"] and r2["shadow_book"]["open"] == 1
    cash = r2["ledger"]["cash"]
    for a in feed:                                                     # everything falls through its stop
        feed[a] = hist + [_bar(n, 100.0, 100.1, 97.0, 97.5)]
    r3 = manage_cycle([], fetch_bars=lambda a: feed[a], now_ms=now + HOUR_MS, book_path=book, proof_path=proof, s=small)
    assert [e["kind"] for m in r3["shadows_managed"] for e in m["events"]] == ["SHADOW_CLOSED"]
    assert r3["shadow_book"]["closed"] == 1 and r3["shadow_book"]["realized_pnl"] < 0
    assert r3["ledger"]["trade_count"] == 2 and r3["ledger"]["losses"] == 2   # the shadow is not in the book's ledger
    b = Book(book)
    try:
        real, shadow = b.all_positions(), b.shadow_positions()
        assert len(real) == 2 and len(shadow) == 1
        assert abs(r3["ledger"]["realized_pnl"] - sum(p["realized_pnl_usd"] for p in real)) < 1e-6   # cash moves only with real trades
        assert abs(r3["ledger"]["cash"] - (1000.0 + sum(p["realized_pnl_usd"] for p in real))) < 1e-6 and cash < r3["ledger"]["cash"]
    finally:
        b.close()


def test_unclosed_bar_is_never_used(tmp_path):
    proof = tmp_path / "proof.json"
    run_fixtures(tmp_path / "fx", proof_path=proof)
    hist = _flat(60)
    forming = [T0 + len(hist) * HOUR_MS, 100.0, 100.0, 50.0, 50.0, 1.0]  # still open bar with a crash in it
    now = forming[0] + HOUR_MS / 2
    r = manage_cycle([_live_take()], fetch_bars=lambda a: hist + [forming], now_ms=now, book_path=tmp_path / "b.sqlite", proof_path=proof)
    assert r["opened"][0]["status"] == "OPENED"
    assert abs(r["opened"][0]["entry_fill"] - 100.0 * (1 + sd6.SETTINGS.slippage_bp / 1e4)) < 1e-9


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


def test_cost_profiles_are_real_and_selectable():
    assert sd6.settings_for("KRAKEN_T1_TAKER").fee_entry_bp == 80.0  # Kraken Pro Canada Tier 1 taker since 2026-07-09
    assert sd6.settings_for("NDAX").fee_exit_bp == 20.0
    try:
        sd6.settings_for("NOPE")
    except ValueError:
        pass
    else:
        raise AssertionError("unknown profile accepted")


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
