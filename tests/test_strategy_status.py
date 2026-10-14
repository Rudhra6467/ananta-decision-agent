"""Oct 13 (Madhav): a useless strategy is marked, not deleted. Retired strategies open no new paper trades, never wake the brain,
and leave the headline; their records stay as evidence; every losing trade carries its strategy's verdict."""
import json
import time

from jarvis.service import strategy_status as S
from tests.test_universe_live import J


def test_status_file_is_consistent():
    d = S.load()
    assert d["strategies"]["ZONE_TOUCH"]["status"] == "RETIRED" and d["strategies"]["EXPLORER"]["status"] == "RETIRED"
    for sid, s in d["strategies"].items():
        assert s["status"] in ("ACTIVE", "UNDER_REVIEW", "RETIRED", "PARKED", "EVIDENCE"), sid
        assert s["verdict"] in S.VERDICT_WORDS, sid
        assert s.get("why"), sid
    assert S.of_watch("ZONE_TOUCH-UB")[0] == "ZONE_TOUCH" and S.of_watch("H07-T30")[0] == "H07" and S.of_watch("JARVIS_RANDOM")[0] == "RANDOM"
    assert not S.trades("ZONE_TOUCH-UC") and S.trades("H07-UA") and S.trades("JARVIS")
    assert not S.counts_book("15-minute Explorer") and S.counts_book("Trend portfolio") and S.counts_watch("JARVIS") and not S.counts_watch("M2a-UC")


def test_retired_rule_sits_out_and_losses_are_classified(tmp_path, monkeypatch):
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
    assert not any(w.startswith("ZONE_TOUCH") for w in seen["w"]) and any(w.startswith("H07") for w in seen["w"]) and any(w.startswith("RANDOM_20D") for w in seen["w"])
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
