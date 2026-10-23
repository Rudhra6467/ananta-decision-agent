"""RX-IN v1 (india/reconstruct.py): the card builds from fixture ledgers and says 'missing' where a source is absent; trade reviews tag by the fixed
rules from the trade's own marks and the sibling policy's close; findings fire only on the fixed counts and never re-file an open key; the staircase
admits nothing without Madhav's recorded yes; the module names no sealed path and no broker call."""
from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from india import reconstruct as rx

DAYS = ["2026-10-16", "2026-10-19", "2026-10-21", "2026-10-22", "2026-10-23"]


def _trade(sig, camp, sid, policy, status="open", entry=100.0, last=100.0, peak=100.0, exit_=None, reason=None, last_date=None, cost=120.0, risk_frac=0.05):
    t = {"id": f"{sig}|{camp}|{sid}|{policy}", "book": "exec", "campaign": camp, "sid": sid, "symbol": sid, "policy": policy, "signal_date": sig, "entry_date": "2026-10-19",
         "entry_adj": entry, "bar_low_raw": entry * 0.97, "risk_frac": risk_frac, "status": status, "last_close_adj": last, "last_date": last_date or "2026-10-23", "bars_seen": 3, "peak_adj": peak, "cost_inr": cost}
    if status == "closed":
        t.update({"exit_date": exit_, "exit_reason": reason, "exit_adj": last, "net_inr": (last - entry) * 500 - cost, "net_ret": (last / entry - 1) - cost / 50000})
    return t


@pytest.fixture
def lake(tmp_path, monkeypatch):
    data = tmp_path / "india"
    for d in ("paper/decisions", "paper/sp1", "manifests", "readmodel", "registrations"):
        (data / d).mkdir(parents=True)
    monkeypatch.setattr(rx.paths, "data_dir", lambda: data)
    monkeypatch.setattr(rx, "REG", tmp_path / "registrations")
    monkeypatch.setattr(rx, "QUEUE", tmp_path / "registrations" / "reconstruction_queue.jsonl")
    monkeypatch.setattr(rx, "STAIRS_FILE", tmp_path / "registrations" / "evidence_staircase.json")
    monkeypatch.setattr(rx, "PAGE", tmp_path / "registrations" / "reconstruction.md")
    (tmp_path / "registrations").mkdir()
    for d in DAYS:
        (data / "paper" / "decisions" / f"{d}.json").write_text(json.dumps({"data_through": d, "context": {"nifty_close": 22688.0, "nifty_vs_sma50": -0.03, "nifty_vs_sma200": -0.06, "breadth200_liq": 0.4, "vix_close": 15.7},
                                                                              "journal": [{"campaign": "PULL", "symbol": "AAA", "status": "chosen", "close": 10}, {"campaign": "REV", "symbol": "BBB", "status": "rejected", "reason": "cap_reached"}]}))
    (data / "paper" / "decisions" / "2026-10-23.universe.json").write_text(json.dumps({"rows": [{"symbol": "AAA"}, {"symbol": "BBB"}, {"symbol": "KEI"}]}))
    (data / "readmodel" / "latest.json").write_text(json.dumps({"data_through": "2026-10-23", "sp1": {"status": "lost", "errors": ["no Kite sign-in"]},
                                                               "jobs": {"jobs": [{"label": "spreads", "ok": False, "problems": ["0 depth snapshots"]}, {"label": "nightly", "ok": False, "problems": ["exit 1: disk"]}]}}))
    man = {"movers": [{"symbol": "KEI", "side": "down", "cc": -0.085, "status": "missed", "class": "b", "situation": "x", "situation_key": "down:breakdown"},
                      {"symbol": "AAA", "side": "up", "cc": 0.04, "status": "caught", "class": None, "situation": "y"}],
           "summary": {"up": {"movers": 1, "caught": 1, "a": 0, "b": 0, "c": 0}, "down": {"movers": 1, "held_into_fall": 0, "b": 1}, "b_situations": {"down:breakdown:intraday_selloff": ["KEI"]}}}
    for d in DAYS:
        (data / "manifests" / f"missed_{d}.json").write_text(json.dumps(man))
        (data / "manifests" / f"others_{d}.json").write_text(json.dumps({"by_h": {"1": {"hindsight_mean": 0.017, "market_mean": -0.012, "ananta_mean": -0.005, "ananta_n": 30, "ananta_pct_vs_random": 0.9,
                                                                                            "random": {"median": -0.012}, "coverage": {"TAKEN": 7, "PASSED": 1, "NOT_COVERED": 11}, "best": []}},
                                                                           "not_covered": {"others:H1:downtrend_rise": {"situation": "rising while below its 200-day average"}}}))
    trades = {}
    # a stop-out that then ran (sibling hold_60d still open, well above the entry), a clean win, a never-worked loss; all exited 3 sessions before the card day
    for t in (_trade("2026-10-16", "BRK", "RAN", "hold_20d", "closed", 100, 96, 101, "2026-10-19", "stop", "2026-10-19"), _trade("2026-10-16", "BRK", "RAN", "hold_60d", "open", 100, 108, 109),
              _trade("2026-10-16", "PULL", "WIN", "hold_20d", "closed", 100, 110, 112, "2026-10-19", "time", "2026-10-19"), _trade("2026-10-16", "PULL", "WIN", "hold_60d", "open", 100, 110, 112),
              _trade("2026-10-16", "REV", "DUD", "hold_20d", "closed", 100, 94, 100.5, "2026-10-19", "stop", "2026-10-19"), _trade("2026-10-16", "REV", "DUD", "hold_60d", "open", 100, 93, 100.5)):
        trades[t["id"]] = t
    (data / "paper" / "state.json").write_text(json.dumps({"trades": trades}))
    (data / "paper" / "sp1" / "book.json").write_text(json.dumps({"sessions": 0}))
    return data


def test_card_builds_and_names_missing_sources(lake):
    c = rx.evening("2026-10-23")
    assert c["market"]["status"] == "ok" and "downtrend" in c["market"]["words"]
    assert c["people"]["deals"]["status"] == "missing" and c["people"]["announcements"]["status"] == "missing" and c["people"]["league"]["status"] == "ok"
    assert c["ananta"]["chosen"][0]["symbol"] == "AAA" and c["ananta"]["rejected_by_reason"] == {"REV:cap_reached": 1}
    assert (lake / "paper" / "reconstruction" / "2026-10-23.json").exists() and (lake / "paper" / "reconstruction" / "latest.json").exists()
    assert "## A. The market" in rx.PAGE.read_text() and "## G. The staircase" in rx.PAGE.read_text()
    assert c["inputs_sha"]["decision"] and c["inputs_sha"]["others"]


def test_trade_reviews_tag_by_the_fixed_rules(lake):
    c = rx.build("2026-10-23")
    rv = c["reviews"]
    assert rv["reviewed_exit_date"] == "2026-10-19" and rv["count"] == 3
    tags = {t["symbol"]: t["tag"] for t in rv["trades"]}
    assert tags == {"RAN": "STOPPED_THEN_RAN", "WIN": "CLEAN", "DUD": "NEVER_WORKED"}, tags
    ran = next(t for t in rv["trades"] if t["symbol"] == "RAN")
    assert ran["after_policy"] == "hold_60d" and ran["after_close"] == 108 and ran["R"] == 5.0
    for t in rv["trades"]:
        assert t["words"] and "risk unit" in rx.TAG_WORDS[t["tag"]] or t["tag"] in ("CLEAN", "COSTS_ATE")


def test_findings_fire_on_counts_collapse_the_signin_and_never_refile_an_open_key(lake):
    c = rx.evening("2026-10-23")
    kinds = {f["type"]: f for f in c["findings"]}
    assert "SIGNIN_LOST" in kinds and "spreads" in kinds["SIGNIN_LOST"]["evidence"]["jobs"], "a job that ran empty for want of the sign-in is not its own finding"
    assert "JOB_FAIL" in kinds and kinds["JOB_FAIL"]["key"] == "JOB_FAIL:nightly"
    assert "DATA_GAP" in kinds and all(f["lane"] == "SAFE" and f["state"] == "to_file" for f in c["findings"] if f["type"] in ("DATA_GAP", "JOB_FAIL", "SIGNIN_LOST"))
    assert "MISS_PATTERN" not in kinds, "one card is one session: a pattern needs 3 of 7"
    # three more cards with the same class-(b) situation and the same uncovered league situation: the pattern rules fire once, as DECISION drafts
    for d in ("2026-10-26", "2026-10-27"):
        (lake / "paper" / "decisions" / f"{d}.json").write_text((lake / "paper" / "decisions" / "2026-10-23.json").read_text().replace("2026-10-23", d))
        (lake / "manifests" / f"missed_{d}.json").write_text((lake / "manifests" / "missed_2026-10-23.json").read_text())
        (lake / "manifests" / f"others_{d}.json").write_text((lake / "manifests" / "others_2026-10-23.json").read_text())
        c = rx.evening(d)
    kinds = {f["type"]: f for f in c["findings"]}
    assert kinds["MISS_PATTERN"]["lane"] == "DECISION" and kinds["MISS_PATTERN"]["state"] == "DRAFT" and len(kinds["MISS_PATTERN"]["evidence"]["days"]) >= 3
    assert kinds["LEAGUE_GAP"]["lane"] == "DECISION"
    q = rx.queue()
    assert sum(1 for r in q if r["key"] == kinds["MISS_PATTERN"]["key"]) == 1
    c2 = rx.evening("2026-10-27")
    assert not [f for f in c2["findings"] if f["key"] in {r["key"] for r in q}], "an open key is never filed twice"


def test_staircase_admits_nothing_without_madhav_and_the_allocator_obeys(lake, monkeypatch):
    s = rx.staircase()
    assert s["admitted"] == [] and all(r["step"] == "SHADOW" for r in s["rules"].values())
    assert s["rules"]["stock:BRK"]["shadow_sessions"] == 1 and s["rules"]["stock:BRK"]["independent_sessions_beating_random_and_market"] == 5
    assert rx.admitted() == set()
    rx.STAIRS_FILE.write_text(json.dumps({**s, "admitted": ["stock:BRK"], "history": [{"date": "2026-11-01", "approved_by": "Madhav", "note": "yes"}]}))
    assert rx.admitted() == {"stock:BRK"}
    assert rx.staircase()["rules"]["stock:BRK"]["step"] == "ADMITTED"


def test_the_module_reads_nothing_sealed_and_calls_no_broker():
    src = Path(rx.__file__).read_text()
    tree = ast.parse(src)
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    assert not names & {"Kite", "place_order", "requests", "read_review", "read_others"}
    strings = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    assert not any("sealed/" in s or "sealed_" in s for s in strings), "the reconstruction never names the sealed folder"
    assert rx.STAIRS["shadow_sessions"] == 20 and rx.STAIRS["admitted_independent_sessions"] == 10 and rx.BARS["safe_per_night"] == 3
