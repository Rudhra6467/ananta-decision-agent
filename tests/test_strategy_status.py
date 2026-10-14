"""Oct 13 (Madhav): the $500 book is the account; every measuring book keeps recording in the background (EVIDENCE: never holdings,
never in the headline); a failed idea never wakes the brain; only what passes is pushed; every losing trade carries its strategy's verdict."""
import json
import time

from jarvis.service import strategy_status as S
from tests.test_universe_live import J


def test_status_file_is_consistent():
    d = S.load()
    assert d["strategies"]["ZONE_TOUCH"]["status"] == "EVIDENCE" and d["strategies"]["EXPLORER"]["status"] == "EVIDENCE"
    assert d["strategies"]["ZONE_TOUCH"]["wakes_brain"] is False and d["account"] == "BOOK500"
    for sid, s in d["strategies"].items():
        assert s["status"] in ("ACTIVE", "UNDER_REVIEW", "RETIRED", "PARKED", "EVIDENCE"), sid
        assert s["verdict"] in S.VERDICT_WORDS, sid
        assert s.get("why"), sid
    assert S.of_watch("ZONE_TOUCH-UB")[0] == "ZONE_TOUCH" and S.of_watch("H07-T30")[0] == "H07" and S.of_watch("JARVIS_RANDOM")[0] == "RANDOM"
    assert S.trades("ZONE_TOUCH-UC") and S.trades("H07-UA") and S.trades("JARVIS") and not S.trades("HOURLY-UA") if S.of_watch("HOURLY-UA") else True
    assert not S.counts_book("15-minute Explorer") and S.counts_book("Trend portfolio") and not S.counts_watch("JARVIS") and not S.counts_watch("M2a-UC")


def test_background_rule_records_but_never_wakes_and_losses_are_classified(tmp_path, monkeypatch):
    from jarvis.service import universe_watch as U, watch_engine as W

    j = J(tmp_path)
    W._table(j)
    now = int(time.time())
    for i, (watch, net) in enumerate([("ZONE_TOUCH-UB", -9.0), ("ZONE_TOUCH-UB", -4.0), ("JARVIS", -3.0), ("JARVIS_RANDOM", -2.0), ("H07-UA", 5.0)]):
        row = {c: None for c in W.COLS}
        row.update(id=f"x{i}", watch=watch, coin="SOL", source="t", signal_t=now - 86400, signal_day="2026-10-10", entry_t=now - 86400, entry=100.0,
                   exit_t=now, exit_day="2026-10-11", exit=100 + net, status="CLOSED", net_usd=net, exit_why="stop", detail="{}")
        W._insert(j, row)
    j.db.commit()
    seen = {}
    monkeypatch.setattr(W, "run", lambda jj, watches=None, coins=None, daily_fn=None, live_trades=True: seen.setdefault("w", list(watches)) and {"opened": []})
    from jarvis.service import registry
    monkeypatch.setattr(registry, "members", lambda jj, tier: ["BTC", "SOL"])
    U.run_rules(j)
    assert any(w.startswith("H07") for w in seen["w"]) and any(w.startswith("RANDOM_20D") for w in seen["w"]) and S.trades("ZONE_TOUCH-UA")   # still recording
    woke = []
    from jarvis.service import brain
    monkeypatch.setattr(brain, "wake", lambda jj, coin, trig, det: woke.append(trig))
    U.wake_brain(j, [{"watch": "ZONE_TOUCH-UA", "coin": "SOL"}, {"watch": "H07-UA", "coin": "SOL"}])
    assert woke == ["setup:H07-UA"]
    r = S.losing_trades(j)
    by = {x["strategy"]: x for x in r["by_strategy"]}
    assert by["ZONE_TOUCH"]["verdict"] == "wont_take_again" and by["ZONE_TOUCH"]["lost"] == 2
    assert by["JARVIS"]["verdict"] == "modify_rules" and by["H07"]["lost"] == 0
    assert r["totals"]["won't take again"]["lost_usd"] == -13.0 and "evidence only" in by["RANDOM"]["verdict_words"]


def test_background_books_record_but_failed_ideas_never_wake_the_brain():
    assert S.trades("ZONE_TOUCH-UB") and not S.wakes("ZONE_TOUCH-UB")          # measures in the background, no decisions on it
    assert S.trades("H07-UA") and S.wakes("H07-UA")
    assert not S.trades("HOURLY") or S.of_watch("HOURLY") is None
    assert not S.counts_watch("JARVIS") and not S.counts_book("15-minute Explorer") and S.counts_book("The $500 NDAX book")
    assert S.account() == "BOOK500" and "ladder" in S.pushed_rule()


def test_push_pipe_notes_once_and_edge_sleeve_takes_passed_rules(tmp_path, monkeypatch):
    from jarvis.service import ndax_book, universe_watch as U

    j = J(tmp_path)
    rows = [{"watch": "M1a-UA", "rule": "M1a", "tier": "A", "step": "EVIDENCE", "next_allowed": True, "why": "ahead of random over 10 market days in both regimes"},
            {"watch": "H07-UA", "rule": "H07", "tier": "A", "step": "EVIDENCE", "next_allowed": False, "why": "too early"}]
    monkeypatch.setattr(U, "ladder", lambda jj: {"rows": rows})
    pushes = []
    out = U.push_passed(j, lambda t, b: pushes.append((t, b)))
    assert len(out) == 1 and out[0]["watch"] == "M1a-UA" and out[0]["to"] == "PROMOTED" and len(pushes) == 1
    assert U.push_passed(j, lambda t, b: pushes.append((t, b))) == [] and len(pushes) == 1    # once per rule and step
    # the edge sleeve: H07 (ACTIVE, passing cell CLOSED/A) when the dial is closed; a PROMOTED rule joins once it has a passing cell
    monkeypatch.setattr(U, "promoted", lambda jj: {"M1a-UA"})
    assert ndax_book.passed_rules(j, False) == ["H07"] and ndax_book.passed_rules(j, True) == []
    from jarvis.service import ev
    monkeypatch.setattr(ev, "table", lambda: [{"rule": "H07", "state": "CLOSED", "tier": "A"}, {"rule": "M1a", "state": "OPEN", "tier": "A"}])
    assert ndax_book.passed_rules(j, True) == ["M1a"]
