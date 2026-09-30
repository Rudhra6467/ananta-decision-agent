"""Explorer engine (Rulebook v0): indicators, no lookahead, pessimistic execution, bells, replay + scorecard smoke."""
import math
import random
import sqlite3
import tempfile
from pathlib import Path

from src.intelligence import explorer_engine as xe

T0 = 1_600_000_000 - (1_600_000_000 % 86400)


def _series(days=80, seed=7, drift=0.0):
    rnd = random.Random(seed)
    out, px = [], 100.0
    for i in range(days * 288):
        regime = math.sin(i / 2500.0)  # slow up/down waves so trends, pullbacks and breakouts occur
        r = rnd.gauss(0.00012 * regime + drift, 0.0025)
        o = px
        c = px * math.exp(r)
        h = max(o, c) * (1 + abs(rnd.gauss(0, 0.0012)))
        lo = min(o, c) * (1 - abs(rnd.gauss(0, 0.0012)))
        out.append((T0 + 300 * i, o, h, lo, c, rnd.uniform(5, 15) * (3 if rnd.random() < 0.02 else 1)))
        px = c
    return out


def _run(b5, upto=None, coin="AAA"):
    from src.research import explorer_replay as xr
    bars = [b for b in b5 if upto is None or b[0] + 300 <= upto]
    events = []
    eng = xe.CoinEngine(coin, on_event=events.append)
    eng.random_rate = 0.0
    recs, ev = {}, xr.event_stream(bars)
    i = 0
    while i < len(ev):
        T = ev[i][0]
        while i < len(ev) and ev[i][0] == T:
            eng.on_bar(ev[i][2], ev[i][3])
            i += 1
        if T % 900 == 0:
            recs[T] = eng.scan(T)
    return eng, recs, events


def test_indicators_match_pandas():
    try:
        import numpy as np
        import pandas as pd

        from src.research import green_runs as gr
    except ImportError:
        return
    b = _series(days=3)
    c = np.array([x[4] for x in b])
    h, lo = np.array([x[2] for x in b]), np.array([x[3] for x in b])
    s = xe.TfState("5m")
    for x in b:
        s.add(*x)
    assert abs(s.e20h[-1] - pd.Series(c).ewm(span=20, adjust=False).mean().iloc[-1]) < 1e-9
    assert abs(s.atrh[-1] - gr.atr(h, lo, c)[-1]) < 1e-9
    assert abs(s.rsi - gr.rsi(c)[-1]) < 1e-6


def test_no_lookahead_decisions_and_orders():
    b5 = _series()
    _, full, ev_full = _run(b5)
    fired = [T for T, r in full.items() if r.get("setups")]
    assert len(fired) >= 5, "fixture must trigger setups for this test to mean anything"
    picks = [fired[0], fired[len(fired) // 2], fired[-1]] + [T for T in list(full)[-300::97] if "state" in full[T]]
    for T in picks:
        _, cut, ev_cut = _run(b5, upto=T)
        assert cut[T].get("state") == full[T].get("state"), T
        assert cut[T].get("setups") == full[T].get("setups"), T
        orders = lambda evs: sorted((e["setup"], e["type"], round(e["limit"], 9), e["shadow"]) for e in evs  # noqa: E731
                                    if e["kind"] == "ORDER" and e["t"] == T)
        assert orders(ev_cut) == orders(ev_full), T


def _engine_with_trade(typ="SHORT_TERM", entry=100.0, atr1h=1.0, atr15=0.5):
    eng = xe.CoinEngine("BTC")
    od = xe.Order("o1", "BTC", "E1", typ, entry, T0, T0 + 7200, {}, atr15, atr1h, 2.0, None, None)
    tr = eng._open(od, entry, T0, "LIMIT", False)
    return eng, tr


def test_stop_first_when_both_touched_and_gap_fills_at_open():
    eng, tr = _engine_with_trade()  # SHORT_TERM: stop 98, target 104
    eng._execute((T0 + 300, 100, 104.5, 97.5, 101, 1))
    assert tr.actual.exit_bell == "X1_STOP" and tr.actual.exit_px == 98.0
    eng, tr = _engine_with_trade()
    eng._execute((T0 + 300, 96.0, 96.5, 95.0, 96.2, 1))
    assert tr.actual.exit_bell == "X1_STOP_GAP" and tr.actual.exit_px == 96.0


def test_limit_fill_bar_cannot_take_the_target():
    eng = xe.CoinEngine("BTC")
    od = xe.Order("o2", "BTC", "E1", "INTRADAY", 99.0, T0, T0 + 3600, {}, 0.5, 1.0, 2.0, None, None)
    eng.orders.append(od)
    eng._execute((T0, 100.0, 105.0, 98.9, 104.0, 1))  # fills at 99 intrabar, reaches the target in the same bar
    tr = eng.trades[0]
    assert tr.entry == 99.0 and tr.fill_intrabar and tr.actual.exit_px is None
    eng._execute((T0 + 300, 104.0, 105.0, 103.9, 104.5, 1))
    assert tr.actual.exit_bell in ("X4_TARGET_GAP", "X4_TARGET")


def test_order_placed_at_T_ignores_the_bar_that_closed_at_T():
    eng = xe.CoinEngine("BTC")
    od = xe.Order("o3", "BTC", "E1", "SHORT_TERM", 99.0, T0 + 300, T0 + 300 + 7200, {}, 0.5, 1.0, 2.0, None, None)
    eng.orders.append(od)
    eng._execute((T0, 100.0, 100.5, 98.0, 100.0, 1))  # opened before placement: must not fill
    assert not eng.trades and eng.orders
    eng._execute((T0 + 300, 100.0, 100.5, 98.5, 99.5, 1))
    assert eng.trades and eng.trades[0].entry == 99.0


def test_unfilled_order_is_missed_and_its_chase_is_followed():
    eng = xe.CoinEngine("BTC")
    od = xe.Order("o4", "BTC", "E1", "INTRADAY", 90.0, T0, T0 + 3600, {}, 0.5, 1.0, 2.0, None, None)
    od.chase = "PENDING"
    eng.orders.append(od)
    for k in range(12):
        eng._execute((T0 + 300 * k, 100.0, 100.3, 99.8, 100.1, 1))
    assert not eng.orders and eng.missed and eng.missed[0].id == "o4"
    assert any(t.shadow == "MISSED_CHASE" and t.entry == 100.0 for t in eng.trades)


def test_pending_market_exit_and_time_cap():
    eng, tr = _engine_with_trade(typ="INTRADAY")
    tr.actual.pending_market = "X5_TIME"
    eng._execute((T0 + 600, 100.4, 100.6, 100.2, 100.5, 1))
    assert tr.actual.exit_bell == "X5_TIME" and tr.actual.exit_px == 100.4 and tr.actual.exit_kind == "MARKET"


def test_slot_frees_and_exit_is_reported_when_the_real_exit_happens():
    events = []
    eng, tr = _engine_with_trade(typ="SHORT_TERM")
    eng.attach(on_event=events.append)
    eng._execute((T0 + 300, 100, 100.5, 97.5, 98.2, 1))  # the real stop (98) hits; HOLD (no stop) keeps running
    assert tr.actual.done and not tr.variants["HOLD"].done
    assert not eng._busy("SHORT_TERM"), "a finished real trade must not block the slot"
    assert [e["kind"] for e in events] == ["CLOSED"] and events[0]["bell"] == "X1_STOP"
    assert eng.actual_closed == [tr] and eng.closed == []


def test_costs_net():
    eng, tr = _engine_with_trade()
    v = tr.actual
    v.exit_px, v.exit_kind = 104.0, "LIMIT"
    assert abs(xe.net_usd(tr, v) - 100 * (0.04 - 0.002 - 1.04 * 0.002)) < 1e-9
    v.exit_kind = "MARKET"
    assert abs(xe.net_usd(tr, v) - 100 * (0.04 - 0.002 - 1.04 * (0.002 + 0.00178))) < 1e-9


def test_replay_and_scorecard_smoke():
    from src.research import explorer_replay as xr
    d = Path(tempfile.mkdtemp())
    db = d / "x.sqlite"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE bars (instrument TEXT, event_unix INTEGER, open REAL, high REAL, low REAL, close REAL, volume REAL)")
    for coin, seed in (("BTC", 1), ("ETH", 2)):
        con.executemany("INSERT INTO bars VALUES (?,?,?,?,?,?,?)", [(f"{coin}-USD-SPOT", *b) for b in _series(days=75, seed=seed)])
    con.commit()
    con.close()
    for coin in ("BTC", "ETH"):
        r = xr.run_coin(str(db), coin, str(d))
        assert r["scans"] > 0 and r["closed_rows"] > 0, r
    sc = xr.score(str(d))
    assert sc["DISCOVERY"]["all_real"]["n"] >= 1 and "exit_comparison" in sc["DISCOVERY"]


if __name__ == "__main__":
    import inspect

    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn) and not inspect.signature(fn).parameters:
            fn()
            print("ok", name)
