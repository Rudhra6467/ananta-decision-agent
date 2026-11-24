"""India stress test (Madhav, 24 Nov 2026; registrations/stress_v1.md): the replay uses the book's own exit code, a stop is sold at the next real
open (below the stop on a gap), nothing is written back to the book, and the no-drop rule catches a drop. No data or network needed."""
import copy

import pandas as pd

from india import managed, stress

C = {"stop_pct": 7.0, "min_hold_sessions": 20, "slippage_pct": 0.1}


def _book():
    return {"cash_inr": 1000.0, "positions": {
        "AAA": {"qty": 10, "avg": 100.0, "last": 100.0, "source": "replacement", "stop": 93.0, "entered": "2026-11-20"},
        "BBB": {"qty": 10, "avg": 50.0, "last": 50.0, "source": "twin", "entered": "2026-10-22"}}}


def _days(n):
    return [pd.Timestamp("2020-03-20") + pd.Timedelta(days=i) for i in range(n)]


def test_a_crash_through_the_stop_is_sold_at_the_next_open_below_the_stop(monkeypatch):
    monkeypatch.setattr(managed, "holidays", lambda: set())
    d = _days(3)
    moves = {d[0]: {"AAA": {"ret": -0.10, "gap": 0.95, "src": "own"}, "BBB": {"ret": -0.10, "gap": 0.95, "src": "own"}},
             d[1]: {"AAA": {"ret": 0.0, "gap": 0.90, "src": "own"}, "BBB": {"ret": 0.0, "gap": 0.90, "src": "own"}},
             d[2]: {"AAA": {"ret": 0.0, "gap": 1.0, "src": "own"}, "BBB": {"ret": 0.0, "gap": 1.0, "src": "own"}}}
    book = _book()
    before = copy.deepcopy(book)
    r = stress.replay(book, d[:2], moves.get, C, after=d[2])
    assert book == before                                                    # the real book is never touched
    assert [s["symbol"] for s in r["stops"]] == ["AAA"]                      # 90 closed under its 93 stop; the twin's holding has no stop
    s = r["stops"][0]
    assert abs(s["fill"] - 90 * 0.90 * 0.999) < 0.01 and s["past_stop_pct"] < -12   # the gap took it well past the stop
    assert r["limit_days"] and r["limit_days"][0]["loss_pct"] < -5          # the 5% day is recorded
    assert r["deepest_fall_pct"] > 9


def test_no_stop_no_sale_and_no_next_open(monkeypatch):
    monkeypatch.setattr(managed, "holidays", lambda: set())
    d = _days(2)
    flat = {x: {"AAA": {"ret": 0.01, "gap": 1.0, "src": "own"}, "BBB": {"ret": 0.01, "gap": 1.0, "src": "own"}} for x in d}
    r = stress.replay(_book(), d[:1], flat.get, C, after=d[1])
    assert r["stops"] == [] and r["next_open"] is None and r["total_pct"] > 0


def test_a_long_call_loses_on_a_gap_down_and_keeps_some_value_when_fear_jumps():
    v0 = stress._bs(1.0, 1.0, 7 / 365, 0.15, True)
    calm = stress._bs(0.95, 1.0, 6 / 365, 0.15, True)
    scared = stress._bs(0.95, 1.0, 6 / 365, 0.25, True)
    assert 0 <= calm < scared and calm < v0 and scared < v0
    assert stress._bs(1.05, 1.0, 6 / 365, 0.15, False) < stress._bs(1.0, 1.0, 7 / 365, 0.15, False)


def test_a_split_like_jump_is_a_data_fault():
    x = pd.DataFrame({"date": pd.to_datetime(["2010-01-01", "2010-01-04", "2010-01-05"]), "o": [100, 50, 51], "c": [100, 50, 51]})
    out = stress._clean(x)
    assert pd.isna(out["ret"].iloc[1]) and abs(out["ret"].iloc[2] - 0.02) < 1e-9


def test_the_no_drop_rule():
    bench = {"money": {"H1": {"book_fall": 30.0}, "B1": {"book_fall_p99": 22.0}}, "marks": {"M1": True, "O1": False, "X": True},
             "options": {"O1_worst_night": 50000, "O2_worst_night": 40000}, "words": {"passed": 10}}
    same = copy.deepcopy(bench)
    assert stress.compare(bench, same) == []
    worse = copy.deepcopy(bench)
    worse["money"]["H1"]["book_fall"] = 31.0
    worse["marks"]["X"] = False
    worse["words"]["passed"] = 9
    drops = stress.compare(bench, worse)
    assert len(drops) == 3 and any("H1" in d for d in drops) and any("X:" in d for d in drops)
    better = copy.deepcopy(bench)
    better["money"]["H1"]["book_fall"] = 25.0
    better["marks"]["O1"] = True
    assert stress.compare(bench, better) == []
