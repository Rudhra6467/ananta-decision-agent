"""The ten graduation gates, ported unchanged from the old app (research audit card APP-GRAD, Oct 15)."""
import sqlite3
import time
from types import SimpleNamespace

from jarvis.service import graduation as G

DAY = 86400
NOW = 1_792_000_000.0                       # a fixed "now" so the weekly windows are exact


def _t(i, n, span_days):
    return NOW - span_days * DAY + (span_days * DAY) * i / max(n - 1, 1) - 1


def _spread(n, pattern, regimes=("OPEN", "CLOSED"), span=40, sideways=None):
    return [{"pnl": pattern[i % len(pattern)], "t": _t(i, n, span), "regime": regimes[i % len(regimes)], "sideways": sideways} for i in range(n)]


def _gate(g, gid):
    return next(c for c in g["criteria"] if c["id"] == gid)


def test_the_thresholds_are_the_old_apps_and_a_change_needs_a_logged_reason():
    assert G.THRESHOLDS == {"round_trips": 50, "profit_factor": 1.3, "max_drawdown_pct": 15.0, "positive_regimes": 2, "top_regime_share_pct": 60.0,
                            "sideways_rate_multiple": 1.5, "observation_days": 30, "weeks_positive": 2, "ruin_line_pct": 20.0,
                            "single_trade_share_pct": 20.0}
    assert G.THRESHOLD_LOG[-1]["what"] == "none changed" and all(x["reason"] for x in G.THRESHOLD_LOG)


def test_nothing_traded_is_not_ready_and_there_are_ten_gates():
    g = G.score([], 500.0, now=NOW)
    assert g["total_gates"] == 10 and g["verdict"] == "NOT READY" and not g["all_passed"]
    assert _gate(g, "min_trades")["passed"] is False and _gate(g, "friction_accounted")["actual"] == "no trades yet"


def test_round_trips_profit_factor_and_expectancy():
    assert _gate(G.score(_spread(10, [2.0, -1.0]), 500.0, now=NOW), "min_trades")["passed"] is False
    g = G.score(_spread(60, [2.0, 2.0, -1.0]), 500.0, now=NOW)              # 40 wins of 2, 20 losses of 1: profit factor 4
    assert _gate(g, "min_trades")["passed"] and _gate(g, "profit_factor")["passed"] and _gate(g, "positive_expectancy")["passed"]
    assert g["metrics"]["profit_factor"] == 4.0
    only_wins = G.score(_spread(60, [2.0]), 500.0, now=NOW)
    assert _gate(only_wins, "profit_factor")["passed"] is False             # no losing trade: the old app printed n/a and did not pass it


def test_one_market_state_carrying_the_profit_fails_gate_5():
    one = [{"pnl": 3.0 if i % 2 == 0 else -0.5, "t": _t(i, 60, 40), "regime": "OPEN" if i % 2 == 0 else "CLOSED"} for i in range(60)]
    assert _gate(G.score(one, 500.0, now=NOW), "regime_diversification")["passed"] is False
    assert _gate(G.score(_spread(60, [2.0, 2.0, -1.0]), 500.0, now=NOW), "regime_diversification")["passed"] is True
    lopsided = [{"pnl": 9.0 if i % 2 == 0 else 1.0, "t": _t(i, 60, 40), "regime": "OPEN" if i % 2 == 0 else "CLOSED"} for i in range(60)]
    g = G.score(lopsided, 500.0, now=NOW)                                   # both pay, but OPEN makes 90% of the money
    assert _gate(g, "regime_diversification")["passed"] is False


def test_the_worst_fall_gates_use_the_closed_trade_equity():
    loss_run = [{"pnl": -20.0, "t": NOW - 60 * DAY + i * 3600, "regime": "OPEN"} for i in range(5)] + _spread(60, [3.0])    # the losses come first
    g = G.score(loss_run, 500.0, now=NOW)                                   # 100 lost of 500 at the bottom = 20%
    assert _gate(g, "max_drawdown")["passed"] is False and _gate(g, "account_survival")["passed"] is False
    mild = [{"pnl": -60.0, "t": _t(0, 2, 10), "regime": "OPEN"}, {"pnl": 10.0, "t": _t(1, 2, 10), "regime": "OPEN"}]
    g2 = G.score(mild, 500.0, now=NOW)                                      # 12% down: fails neither the 15% nor the 20% line
    assert _gate(g2, "max_drawdown")["passed"] and _gate(g2, "account_survival")["passed"]
    between = [{"pnl": -80.0, "t": _t(0, 2, 10), "regime": "OPEN"}]         # 16%: over the 15% gate, under the 20% ruin line
    g3 = G.score(between, 500.0, now=NOW)
    assert _gate(g3, "max_drawdown")["passed"] is False and _gate(g3, "account_survival")["passed"] is True


def test_one_trade_carrying_the_profit_fails_gate_10():
    g = G.score(_spread(60, [1.0]) + [{"pnl": 40.0, "t": NOW - 5 * DAY, "regime": "OPEN"}], 500.0, now=NOW)
    assert _gate(g, "risk_consistency")["passed"] is False                  # 40 of 100 = 40%
    assert _gate(G.score(_spread(60, [1.0, 1.2, 0.9]), 500.0, now=NOW), "risk_consistency")["passed"] is True


def test_stability_needs_30_days_and_two_of_the_last_three_weeks_up():
    assert _gate(G.score(_spread(60, [2.0, -1.0], span=20), 500.0, now=NOW), "stability")["passed"] is False      # only 20 days
    down_weeks = [{"pnl": -1.0 if NOW - 21 * DAY < _t(i, 60, 40) else 1.0, "t": _t(i, 60, 40), "regime": "OPEN"} for i in range(60)]
    assert _gate(G.score(down_weeks, 500.0, now=NOW), "stability")["passed"] is False                           # the last 3 weeks all down
    assert _gate(G.score(_spread(60, [2.0, 2.0, -1.0], span=40), 500.0, now=NOW), "stability")["passed"] is True


def test_sideways_gate_is_not_measured_without_a_label_and_never_passes_quietly():
    g = G.score(_spread(60, [2.0, 2.0, -1.0]), 500.0, now=NOW)
    c = _gate(g, "no_sideways_overtrading")
    assert c["passed"] is False and c["measured"] is False and g["not_measured"] == ["no_sideways_overtrading"]
    labelled = G.score(_spread(60, [2.0, 2.0, -1.0], sideways=False), 500.0, now=NOW)
    assert _gate(labelled, "no_sideways_overtrading")["passed"] is True      # labelled, none sideways: nothing to overtrade
    chop = _spread(60, [2.0, 2.0, -1.0], sideways=False)
    for r in chop[-30:]:                                                    # 30 sideways trades squeezed into 30 hours: the rate is way over 1.5x
        r["sideways"] = True
    for k, r in enumerate(chop[-30:]):
        r["t"] = NOW - 5 * DAY + k * 3600
    assert _gate(G.score(chop, 500.0, now=NOW), "no_sideways_overtrading")["passed"] is False
    losing_chop = _spread(60, [2.0, 2.0, -1.0], sideways=False)
    for r in losing_chop[:6]:
        r["sideways"], r["pnl"] = True, -1.0
    assert _gate(G.score(losing_chop, 500.0, now=NOW), "no_sideways_overtrading")["passed"] is False            # sideways trades that lose


def test_ready_only_when_all_ten_pass():
    rows = _spread(60, [2.0, 2.0, -1.0, 2.0, -0.5], sideways=False)
    g = G.score(rows, 500.0, now=NOW)
    assert g["passed_count"] == 10 and g["verdict"] == "READY" and g["all_passed"], [c for c in g["criteria"] if not c["passed"]]
    assert G.score(rows, 500.0, now=NOW, costs_counted=False)["verdict"] == "NOT READY"


def test_sentence_says_what_still_stands_in_the_way():
    s = G.sentence(G.score(_spread(3, [1.0, -1.0, 1.0]), 500.0, now=NOW), "The $500 book")
    assert s.startswith("The $500 book: ") and "graduation gates passed, not ready" in s and "round trips (3, needs >= 50)" in s
    assert "sideways trading" in s and "not measured" in s


def _j_with_book(closed, started="2026-10-11"):
    import json

    db = sqlite3.connect(":memory:")
    j = SimpleNamespace(db=db, now=lambda: NOW)
    from jarvis.service import ndax_book

    ndax_book._table(j)
    db.execute("INSERT INTO book500 VALUES ('state', ?)", (json.dumps({"started": started, "closed": closed}),))
    return j


def test_book500_card_reads_the_books_closed_trades():
    closed = [{"coin": "SOL", "sleeve": "EDGE", "in": "2026-10-10", "out": "2026-10-12", "pnl_cad": 6.0, "dial": False},
              {"coin": "BTC", "sleeve": "CORE", "in": "2026-10-01", "out": "2026-10-13", "pnl_cad": 4.0, "dial": True},
              {"coin": "ADA", "sleeve": "EDGE", "in": "2026-10-11", "out": "2026-10-14", "pnl_cad": -2.0, "dial": False}]
    card = G.book500_card(_j_with_book(closed), now=time.mktime((2026, 10, 15, 12, 0, 0, 0, 0, 0)))
    assert card["closed_trades"] == 3 and card["of"] == 10 and card["verdict"] == "NOT READY"
    assert "min_trades" in card["failing"] and "no_sideways_overtrading" in card["failing"] and card["not_measured"] == ["no_sideways_overtrading"]
    rows, start = G.book500_trades(_j_with_book(closed))
    assert start == 500.0 and {r["regime"] for r in rows} == {"OPEN", "CLOSED"}
    assert G.book500_card(_j_with_book([]), now=NOW)["closed_trades"] == 0                 # an empty book is scored, not an error


def test_the_books_status_and_the_nightly_note_carry_the_scorecard():
    import json

    from jarvis.service import ndax_book, universe_watch

    j = _j_with_book([{"coin": "SOL", "sleeve": "EDGE", "in": "2026-10-10", "out": "2026-10-12", "pnl_cad": 6.0, "dial": False}])
    s = json.loads(j.db.execute("SELECT v FROM book500 WHERE k='state'").fetchone()[0])
    s.update({"cash": 500.0, "pos": {}, "brakes": {}, "value": 506.0})
    j.db.execute("UPDATE book500 SET v=? WHERE k='state'", (json.dumps(s),))
    st = ndax_book.status(j)
    assert st["graduation"]["of"] == 10 and st["graduation"]["closed_trades"] == 1 and st["graduation"]["verdict"] == "NOT READY"
    src = open(universe_watch.__file__).read()                                              # the nightly note prints it and the round computes it
    assert 'out["graduation"] = graduation.book500_card(j)' in src and "graduation gates (the old app's ten" in src
