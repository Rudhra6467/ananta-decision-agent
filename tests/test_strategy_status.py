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


# ---------------------------------------------------------------------------
# Oct 15 (research audit): LOSSES judged a trade by today's verdict; STATUS froze its numbers in the file; the Explorer was counted from
# the last 30 trades only
# ---------------------------------------------------------------------------
def _lost_trade(W, j, i, watch, net, entry_t):
    row = {c: None for c in W.COLS}
    row.update(id=f"v{i}", watch=watch, coin="SOL", source="t", signal_t=entry_t, signal_day="2026-10-10", entry_t=entry_t, entry=100.0,
               exit_t=entry_t + 3600, exit_day="2026-10-11", exit=100 + net, status="CLOSED", net_usd=net, exit_why="stop", detail="{}")
    W._insert(j, row)


def test_a_loss_keeps_the_verdict_that_was_in_force_when_the_trade_was_entered(tmp_path, monkeypatch):
    from jarvis.service import watch_engine as W

    reg = {"strategies": {"ZONE_TOUCH": {"name": "Zone touch", "status": "EVIDENCE", "verdict": "will_try_again", "watches": ["ZONE_TOUCH"], "why": "{lost} of {closed} lost"}}}
    monkeypatch.setattr(S, "load", lambda: reg)
    j = J(tmp_path, now=1000)
    W._table(j)
    assert S.record_verdicts(j) == 1 and S.record_verdicts(j) == 0                  # stamped once; nothing changed, nothing added
    _lost_trade(W, j, 1, "ZONE_TOUCH-UB", -5.0, 500)                                 # entered before the register: its first verdict
    reg["strategies"]["ZONE_TOUCH"]["verdict"] = "wont_take_again"                   # Madhav changes the verdict at t=1200
    j._now = 1200
    assert S.record_verdicts(j) == 1
    _lost_trade(W, j, 2, "ZONE_TOUCH-UB", -7.0, 1500)                                # entered under the new verdict
    j.db.commit()
    r = S.losing_trades(j)
    z = {x["strategy"]: x for x in r["by_strategy"]}["ZONE_TOUCH"]
    assert z["verdict"] == "wont_take_again" and z["verdict_changed_since"] is True and z["lost_before_register"] == 1
    assert z["lost_by_verdict_at_entry"] == {"will try again": {"lost": 1, "lost_usd": -5.0}, "won't take again": {"lost": 1, "lost_usd": -7.0}}
    assert r["totals"]["will try again"]["lost_usd"] == -5.0 and r["totals"]["won't take again"]["lost_usd"] == -7.0
    assert z["why"] == "2 of 2 lost" and [t["verdict_at_entry"] for t in z["trades"]] == ["wont_take_again", "will_try_again"]       # newest first
    assert S.strategies_live(r["by_strategy"])["ZONE_TOUCH"]["why"] == "2 of 2 lost"


def test_reasons_in_the_file_carry_no_frozen_numbers_and_render_from_the_live_record():
    import re

    assert S.render_why("{lost} of {closed} closed paper trades lost ({lost_usd}); {won} won, net {net}",
                        {"closed": 115, "won": 0, "lost": 115, "net_usd": -1317.54, "lost_usd": -1317.54}) == \
        "115 of 115 closed paper trades lost (-$1,317.54); 0 won, net -$1,317.54"
    assert S.render_why("{closed} closed ({net})", None) == "0 closed (+$0.00)" and S.render_why("no tokens here", {"closed": 3}) == "no tokens here"
    for sid, s in S.load()["strategies"].items():
        assert not re.search(r"as of oct", s["why"], re.I), f"{sid}: a date-stamped count is frozen in the file; use {{closed}} {{won}} {{net}}"
        left = re.sub(r"\{(closed|won|lost|net|lost_usd)\}", "", s["why"])
        assert "{" not in left and "}" not in left, f"{sid}: an unknown token"


def test_the_explorer_is_counted_from_its_whole_closed_book_not_the_last_30(tmp_path, monkeypatch):
    import sqlite3
    import types

    reg = {"strategies": {"EXPLORER": {"name": "Explorer", "status": "EVIDENCE", "verdict": "wont_take_again", "home_book": "15-minute Explorer", "why": "{closed} closed, {won} won"}}}
    monkeypatch.setattr(S, "load", lambda: reg)
    book = sqlite3.connect(":memory:")
    book.execute("CREATE TABLE events (seq INTEGER PRIMARY KEY AUTOINCREMENT, t INTEGER, kind TEXT, coin TEXT, id TEXT, json TEXT)")
    for i in range(40):                                                              # 40 closed trades: 3 wins, 37 losses
        tid = f"BTC-{i}"
        net = 1.0 if i < 3 else -0.5
        for kind, t, body in (("FILLED", 1000 + i, {"kind": "FILLED", "t": 1000 + i, "coin": "BTC", "id": tid, "setup": "E4"}),
                              ("CLOSED", 2000 + i, {"kind": "CLOSED", "t": 2000 + i, "coin": "BTC", "id": tid, "setup": "E4", "bell": "X3_1H_EMA50", "net_usd": net})):
            book.execute("INSERT INTO events (t, kind, coin, id, json) VALUES (?,?,?,?,?)", (t, kind, "BTC", tid, json.dumps(body)))
    j = J(tmp_path, now=5000)

    class WithExplorer(type(j)):
        def _explorer(self):
            return types.SimpleNamespace(store=types.SimpleNamespace(book=book))
    j.__class__ = WithExplorer
    from jarvis.service import watch_engine as W
    W._table(j)
    r = S.losing_trades(j)
    x = {y["strategy"]: y for y in r["by_strategy"]}["EXPLORER"]
    assert (x["closed"], x["won"], x["lost"]) == (40, 3, 37) and x["net_usd"] == round(3 - 37 * 0.5, 2)
    assert x["why"] == "40 closed, 3 won" and len(x["trades"]) == 37 and x["trades"][0]["day"]
