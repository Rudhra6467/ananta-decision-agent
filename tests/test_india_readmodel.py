"""V0 India read model: builds from fixture ledgers, every number traces to its file, missing sources are named and never guessed."""
from __future__ import annotations

import json

import pytest

from india import readmodel

DAY = "2026-10-21"


@pytest.fixture
def lake(tmp_path, monkeypatch):
    data = tmp_path / "india"
    (data / "paper" / "decisions").mkdir(parents=True)
    (data / "paper" / "sp1").mkdir()
    (data / "manifests").mkdir()
    monkeypatch.setattr(readmodel.paths, "data_dir", lambda: data)
    monkeypatch.setattr(readmodel.paths, "manifest_dir", lambda: data / "manifests")
    monkeypatch.setattr(readmodel, "REG", tmp_path / "reg")
    (tmp_path / "reg").mkdir()
    (data / "paper" / "decisions" / f"{DAY}.json").write_text(json.dumps({
        "rules": "paper-v1.2", "data_through": DAY, "decided_at": "2026-10-22T02:30:00+00:00", "sha256": "abc",
        "context": {"nifty_close": 22811.35, "nifty_vs_sma50": -0.028, "nifty_vs_sma200": -0.055, "vix_close": 15.7, "breadth200_liq": 0.412, "breadth50_liq": 0.164},
        "universe": {"with_features": 1981}, "candidates": {"BRK": {"chosen": 1}},
        "signals": [{"campaign": "BRK", "symbol": "MPHASIS", "close": 2575.0, "vol_ratio20": 2.08, "dist_sma20": 0.104, "liq_rank": 179}]}))
    (data / "paper" / "state.json").write_text(json.dumps({"version": "paper-v1", "trades": {
        "a": {"book": "exec", "campaign": "BRK", "sid": "S1", "symbol": "TECHM", "policy": "hold_20d", "status": "open", "entry_adj": 100.0, "last_close_adj": 104.0, "entry_date": "2026-10-19", "last_date": DAY},
        "b": {"book": "exec", "campaign": "BRK", "sid": "S1", "symbol": "TECHM", "policy": "hold_5d", "status": "closed", "entry_adj": 100.0, "last_close_adj": 101.0},
        "c": {"book": "baseline", "campaign": "BRK", "sid": "S2", "symbol": "X", "policy": "hold_20d", "status": "open", "entry_adj": 10.0, "last_close_adj": 9.0}}}))
    (data / "paper" / "marks.jsonl").write_text("\n".join(json.dumps(m) for m in [
        {"at": "t1", "book": "exec", "campaign": "BRK", "policy": "hold_20d", "closed": 0, "open": 1, "realised_inr": 0.0, "open_unrealised_inr": 100.0, "win_rate": None, "expectancy_R": None},
        {"at": "t2", "book": "exec", "campaign": "BRK", "policy": "hold_20d", "closed": 1, "open": 1, "realised_inr": -3899.0, "open_unrealised_inr": 2780.0, "win_rate": 0.0, "expectancy_R": -1.04},
        {"at": "t2", "book": "exec", "campaign": "BRK", "policy": "hold_5d", "closed": 1, "open": 0, "realised_inr": 500.0, "open_unrealised_inr": 0.0, "win_rate": 1.0, "expectancy_R": 0.5}]) + "\n")
    (data / "paper" / "calls.jsonl").write_text("\n".join(json.dumps(m) for m in [
        {"kind": "call", "rule": "call-v0", "data_through": "2026-10-20", "call": "BEARISH", "null_call": "BULLISH"},
        {"kind": "score", "data_through": "2026-10-20", "horizon": 1, "score": -1, "null_score": 1},
        {"kind": "call", "rule": "call-v0", "data_through": DAY, "call": "BULLISH", "null_call": "BEARISH"}]) + "\n")
    (data / "paper" / "sp1" / "decisions.jsonl").write_text(json.dumps({"kind": "error", "date": DAY, "error": "no Kite sign-in by 09:10 IST"}) + "\n")
    (data / "paper" / "sp1" / "book.json").write_text(json.dumps({"sessions": 0, "by_index": {}}))
    (data / "manifests" / f"others_{DAY}.json").write_text(json.dumps({"status": "ok", "by_h": {"1": {"hindsight_mean": 0.0169, "market_mean": -0.0217, "ananta_mean": -0.021, "ananta_n": 18,
                                                                        "ananta_pct_vs_random": 0.57, "coverage": {"TAKEN": 3, "CONTROL": 1, "PASSED": 1, "NOT_COVERED": 15}}}, "informed": {}, "league": {}}))
    monkeypatch.setattr(readmodel, "research", lambda: {"source": "stub", "studies": {"ready": 1}, "verdicts": {}, "exit_book": {"chosen": {}}})
    monkeypatch.setattr(readmodel, "jobs", lambda: {"status": "ok", "source": "stub", "jobs": [{"label": "paper", "ok": True, "problems": []}], "signin": "x", "lost": []})
    return data


def test_build_traces_every_number_and_names_the_missing(lake):
    rm = readmodel.build(DAY)
    assert rm["market"]["nifty_close"] == 22811.35 and rm["market"]["trend_state"] == "below_both"
    assert rm["market"]["source"].endswith(f"decisions/{DAY}.json")
    assert rm["call"]["call"] == "BULLISH" and rm["call"]["scored"] == 1 and rm["call"]["hits"] == 0 and rm["call"]["null_hits"] == 1
    sb = rm["stock_book"]
    assert sb["open_positions"] == 1 and sb["positions"][0]["symbol"] == "TECHM" and abs(sb["positions"][0]["pnl_pct"] - 0.04) < 1e-9
    assert sb["by_campaign"]["BRK"]["realised_inr"] == -3899.0 and sb["by_campaign"]["BRK"]["policy_shown"] == "hold_20d"   # latest mark, reference policy only
    assert rm["decisions_today"]["chosen"][0]["why"].startswith("20-session breakout on volume: volume 2.1x")
    assert rm["sp1"]["status"] == "lost" and "no Kite sign-in" in rm["sp1"]["words"]
    assert rm["learning"]["missed"]["status"] == "missing" and rm["learning"]["league"]["h1"]["coverage"]["TAKEN"] == 3
    assert "missing" not in rm["missing"] and rm["learning"]["missed"]["source"].endswith(f"missed_{DAY}.json")
    assert any("Nifty 22,811" in s for s in rm["brief"]) and any("session lost" in s for s in rm["brief"])
    assert (lake / "readmodel" / "latest.json").exists() and (lake / "readmodel" / f"{DAY}.json").exists()
    md = (readmodel.REG / "india_readmodel.md").read_text()
    assert "MPHASIS" in md and "hold_20d" in md


def test_build_without_a_decision_file_is_a_plain_error(lake):
    (lake / "paper" / "decisions" / f"{DAY}.json").unlink()
    with pytest.raises(RuntimeError, match="no stock-book decision file"):
        readmodel.latest_day()
    rm = readmodel.build(DAY)
    assert rm["market"]["status"] == "missing" and "market" in rm["missing"] and "decisions_today" in rm["missing"]
    assert any(s.startswith("Not available for this session") for s in rm["brief"])


def test_sp1_shows_the_newest_session_by_date(lake):
    """26 Oct: the read model (data through 23 Oct) said "session lost" while the 26 Oct SP1 session had run and been scored."""
    d = readmodel.paths.data_dir() / "paper" / "sp1"
    rows = [{"kind": "error", "date": "2026-10-23", "error": "no Kite sign-in by 09:10 IST"},
            {"kind": "decision", "date": "2026-10-26", "index": "NIFTY", "point": "D0", "choice": None},
            {"kind": "decision", "date": "2026-10-26", "index": "BANKNIFTY", "point": "D2", "choice": {"action": 6, "exit": "ATRSTOP", "dir": 1}}]
    (d / "decisions.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    (d / "book.json").write_text(json.dumps({"sessions": 1, "by_index": {"BANKNIFTY": {"trades": 1, "index_proxy_sum_bps": 48.4, "option_1lot_rs_realistic_fill": 1078.0}}}))
    s = readmodel.sp1("2026-10-23")
    assert s["date"] == "2026-10-26" and s["status"] == "ok"
    assert s["words"].startswith("Mon 26 Oct: 2 index decisions recorded, traded BANKNIFTY at D2 (long, exit ATRSTOP)")
    assert "+48 bp" in s["words"] and "Rs 1,078" in s["words"]
    (d / "decisions.jsonl").write_text(json.dumps(rows[0]) + "\n")
    assert readmodel.sp1("2026-10-23")["words"].startswith("Fri 23 Oct: session lost: no Kite sign-in")


def test_newer_closes_say_the_index_is_ahead_of_the_decision_day(lake, monkeypatch):
    """26 Oct: the index closes land at 12:30, the stock-book decision at 22:30; the read model names the newer closes and keeps the decided numbers."""
    from india import technicals
    monkeypatch.setattr(technicals, "latest_index", lambda names: {"NIFTY 50": {"date": "2026-10-23", "close": 22600.0, "d1": -0.004}, "INDIA VIX": {"date": DAY, "close": 15.7, "d1": 0.0}})
    nc = readmodel.newer_closes(DAY)
    assert set(nc) == {"NIFTY 50", "words", "meaning"} and "22,600.00 on 2026-10-23" in nc["words"]       # the same-day VIX row is not "newer"
    monkeypatch.setattr(technicals, "latest_index", lambda names: {})
    assert readmodel.newer_closes(DAY) == {}


def test_stock_book_counts_closed_and_open_apart_flag_44(lake):
    rm = readmodel.build(DAY)
    cvo = rm["stock_book"]["closed_vs_open"]
    assert cvo["total"]["open"]["n"] == 1 and cvo["total"]["open"]["winners"] == 1 and cvo["total"]["closed"]["n"] == 0
    assert cvo["words"].startswith("win rate counts closed trades only: 0 of 0 closed won")
    assert rm["book_stats"]["status"] == "ok" and rm["book_stats"]["sharpe"]["words"].startswith("only ")
