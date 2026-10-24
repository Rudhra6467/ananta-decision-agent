"""The trader's discipline (Madhav, 24 Oct 2026, "Yes to all"): the protect rule, the dial's three states, the core targets, the
selection floor, the parked step of the trade guard, the BRK signal and the reconstruction card's tables."""
from __future__ import annotations

import json
import sqlite3
import time

import pytest

from jarvis.service import discipline, trade_guard, watch_engine


def test_rules_file_is_registered_with_madhavs_words():
    r = discipline.rules()
    assert r["version"].startswith("discipline-v1")
    assert "Yes to all" in r["decided"]
    assert len(r["items"]) == 10
    assert r["history"][0]["words"] == "Yes to all"


def test_protect_moves_only_up_and_only_past_the_bars():
    # entry 100, first stop 90: R = 10
    assert discipline.protect(100, 90, 110, 90) == (90, None)              # +1.0 R: nothing
    s, why = discipline.protect(100, 90, 115, 90)                           # +1.5 R: stop to the entry
    assert s == 100 and "entry" in why
    s, why = discipline.protect(100, 90, 125, 100)                          # +2.5 R: trail 1 R under the high
    assert s == 115 and "trail" in why
    assert discipline.protect(100, 90, 125, 118) == (118, None)             # never down
    assert discipline.protect(100, None, 150, None) == (None, None)         # no stop: untouched (DIP, H07, random)
    assert discipline.protect(100, 0.0, 150, 0.0) == (0.0, None)


def test_dial_states():
    up = [100.0] * 199 + [110.0]
    assert discipline.dial_state(up) == "CONFIRMED"
    flat = [100.0] * 200
    assert discipline.dial_state(flat) == "CLOSED"                          # not above both
    frag = [100.0] * 195 + [101.0] * 5
    assert discipline.dial_state(frag) == "FRAGILE"
    assert discipline.dial_state([1.0] * 50) is None


def test_core_targets_follow_the_cash_target():
    w = {"BTC": 0.40, "ETH": 0.20}
    c = discipline.core_targets("CLOSED", 500, w)
    assert c["target"] == {"BTC": 0, "ETH": 0} and c["next"] == {"BTC": 0, "ETH": 0} and c["cash_target"] == 0.70
    # FRAGILE with a core: hold it (no adds, no trim while under the 60% cap); the 24 Oct dry run: BTC 191, ETH 93 of a 484 book
    f = discipline.core_targets("FRAGILE", 484, w, 3, held={"BTC": 191.0, "ETH": 93.0})
    assert f["cash_target"] == 0.40 and f["next"] == {"BTC": 191.0, "ETH": 93.0}
    assert f["target"]["BTC"] >= 191 and f["target"]["ETH"] >= 93          # the cap: 60% of the book, so nothing is trimmed
    assert "hold" in f["words"]
    # FRAGILE with no core: a first buy of at most 20% of the book
    f0 = discipline.core_targets("FRAGILE", 600, w)
    assert abs(sum(f0["next"].values()) - 120) < 0.05
    # CONFIRMED: the first third at most 20% of the book; later thirds up to the full core
    k0 = discipline.core_targets("CONFIRMED", 600, w, tranches_done=0)
    assert abs(sum(k0["next"].values()) - 120) < 0.05 and k0["cash_target"] == 0.15
    k2 = discipline.core_targets("CONFIRMED", 600, w, tranches_done=2, held={"BTC": 160.0, "ETH": 80.0})
    assert k2["next"]["BTC"] == 240 and k2["next"]["ETH"] == 120
    # a core over its cap is trimmed back to it: FRAGILE cap is 60% of the book
    big = discipline.core_targets("FRAGILE", 500, w, 3, held={"BTC": 300.0, "ETH": 100.0})
    assert big["target"]["BTC"] == 200 and big["target"]["ETH"] == 100


def test_selection_floor():
    assert discipline.selection_floor("A", 100, 110, 95) == []
    assert any("tier C" in f for f in discipline.selection_floor("C", 100, 110, 95))
    assert any("top of its zone" in f for f in discipline.selection_floor("B", 100, 101, 95))
    assert any("8%" in f for f in discipline.selection_floor("A", 100, 120, 90))


def test_trade_guard_parks_zone_touch_and_lets_others_through(monkeypatch):
    assert trade_guard.parked("ZONE_TOUCH-UA") == trade_guard.PARKED
    assert trade_guard.parked("ZONE_TOUCH") == trade_guard.PARKED
    assert trade_guard.parked("H07-UA") is None
    assert trade_guard.parked("JARVIS") is None
    assert trade_guard.parked("BOOK500") is None
    assert trade_guard.parked("BRK-UA") is None


def test_brk_fires_on_a_20_session_high_with_volume():
    from src.research import reads as R

    bars = []
    t0 = 1_700_000_000
    for i in range(60):
        c = 100.0 + (i % 5)                                                  # chop under 105
        bars.append((t0 + i * 86400, c, c + 1, c - 1, c, 1000.0))
    bars.append((t0 + 60 * 86400, 105.0, 112.0, 104.0, 111.0, 2000.0))       # a close over every close of the last 20 on 2x volume
    S = R.Series(bars)
    ok, stop, why = watch_engine._fires(watch_engine.DAILY["BRK"], S, S, len(bars) - 1, R.rsi(S.c, 10))
    assert ok and stop is None and "20-session high" in why
    bars2 = bars[:-1] + [(t0 + 60 * 86400, 105.0, 112.0, 104.0, 111.0, 1100.0)]   # same close, thin volume: no
    S2 = R.Series(bars2)
    assert watch_engine._fires(watch_engine.DAILY["BRK"], S2, S2, len(bars2) - 1, R.rsi(S2.c, 10))[0] is False


def test_brk_registered_on_tiers_a_and_b_only():
    from jarvis.service import universe_watch

    assert "BRK-UA" in watch_engine.DAILY and "BRK-UB" in watch_engine.DAILY and "BRK-UC" not in watch_engine.DAILY
    assert universe_watch.BASELINE_OF["BRK"] == "RANDOM_20D"


class _J:
    def __init__(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = None
        self._t = 1_760_000_000.0

    def now(self):
        return self._t


def test_protect_on_daily_candles_moves_the_stop_and_closes_on_it():
    j = _J()
    watch_engine._table(j)
    t0 = 1_700_000_000
    D = [(t0 + i * 86400, 100.0, 101.0, 99.0, 100.0, 1000.0) for i in range(30)]
    D[11] = (t0 + 11 * 86400, 100.0, 120.0, 99.5, 118.0, 1000.0)             # day after entry: +2 R high (R = 10)
    D[12] = (t0 + 12 * 86400, 118.0, 119.0, 100.5, 101.0, 1000.0)             # then a fall to 100.5: the protected stop (100) holds
    D[13] = (t0 + 13 * 86400, 101.0, 102.0, 95.0, 96.0, 1000.0)               # then under it: closed at 100, not at 90
    row = {"id": "x1", "watch": "M2a", "coin": "SOL", "source": "daily", "signal_t": D[9][0], "signal_day": "d", "entry_t": D[10][0],
           "entry_day": "d", "entry": 100.0, "stop": 90.0, "status": "OPEN", "why": "", "regime": None, "detail": json.dumps({"close": 100})}
    watch_engine._insert(j, row)
    from src.research import reads as R

    S = R.Series(D)
    rows = j.db.execute(f"SELECT {', '.join(watch_engine.COLS)} FROM evidence_trades").fetchall()
    out = watch_engine._manage(j, "SOL", D, S, R.rsi(S.c, 10), rows)
    r = j.db.execute("SELECT status, exit, exit_why, stop, detail FROM evidence_trades WHERE id='x1'").fetchone()
    assert r[0] == "CLOSED" and r[1] == 100.0 and r[2] == "protect stop" and r[3] == 100.0
    det = json.loads(r[4])
    assert det["stop0"] == 90.0 and det["stop_moves"][0]["rule"].startswith("protect")
    assert out and out[-1]["event"] == "closed"


def test_reconstruction_tables_and_queue_decide():
    from jarvis.service import reconstruct

    j = _J()
    reconstruct._table(j)
    j.db.execute("INSERT INTO rx_queue VALUES (?,?,?,?,?,?,?,?,?,?,?)", ("q1", "2026-10-24", 1, "MISS_PATTERN", "DECISION", "miss:x", "words", "{}", "OPEN", None, None))
    q = reconstruct.queue(j)
    assert q[0]["id"] == "q1" and q[0]["kind_words"].startswith("a kind of move")
    assert reconstruct.decide(j, "q1", "yes, draft it")["state"] == "DECIDED"
    with pytest.raises(KeyError):
        reconstruct.decide(j, "nope", "x")


def test_reconstruction_decisions_reach_needs_you():
    from jarvis.service import needs, reconstruct

    j = _J()
    reconstruct._table(j)
    j.db.execute("INSERT INTO rx_queue VALUES (?,?,?,?,?,?,?,?,?,?,?)", ("q9", "2026-10-24", 1, "BOOK_BLEED", "DECISION", "bleed:JARVIS",
                                                                      "JARVIS: 8 closed, net $-29 in 7 days", "{}", "OPEN", None, None))
    j.db.execute("INSERT INTO rx_queue VALUES (?,?,?,?,?,?,?,?,?,?,?)", ("q8", "2026-10-24", 1, "GAVE_BACK", "SAFE", "gave_back:x", "w", "{}", "FILED", None, None))
    items = needs.list_(j)
    rx = [i for i in items if i["kind"] == "rx"]
    assert [i["id"] for i in rx] == ["rx:q9"] and "pauses this book" in rx[0]["meaning"]
    assert needs.decide(j, "rx:q9", "later", "owner")["until_days"] == 7
    assert not [i for i in needs.list_(j) if i["kind"] == "rx"]


def _series(n, start=1_700_000_000, base=100.0, step=0.0, vol=1000.0):
    return [(start + k * 86400, base + step * k, base + step * k + 1, base + step * k - 1, base + step * k, vol) for k in range(n)]


def test_setups_board_finds_a_breakout_ranks_it_and_wakes_the_brain(monkeypatch):
    from jarvis.service import brain, feed, registry, setups

    j = _J()
    btc = _series(300, base=100.0, step=0.1)
    j._t = btc[-1][0] + 3600
    up = _series(300, base=50.0, step=0.01)                                # a slow uptrend
    up[-1] = (up[-1][0], 53.0, 56.0, 52.9, 55.9, 4000.0)                     # a 20-session closing high on 4x volume: BRK fires
    flat = _series(300, base=10.0)                                           # nothing on it
    data = {"BTC": btc, "UPC": up, "FLAT": flat}
    monkeypatch.setattr(registry, "members", lambda jj, t=None: {"A": ["BTC", "UPC"], "B": ["FLAT"]}.get(t, []))
    monkeypatch.setattr(feed, "daily", lambda jj, c: data[c])
    woke = []
    monkeypatch.setattr(brain, "wake", lambda jj, c, trig, det=None: woke.append((c, trig)) or True)
    b = setups.build(j)
    assert b["scanned"] == 3
    rows = setups.latest(j)["rows"]
    brk = [r for r in rows if r["coin"] == "UPC" and r["family"] == "BRK"]
    assert brk and brk[0]["state"] == "FIRED" and abs(brk[0]["stop_pct"] - 0.08) < 1e-9
    assert ("UPC", "board:BRK") in woke and "UPC" in b["words"]
    assert all(r["coin"] != "FLAT" or r["family"] != "BRK" for r in rows if r["state"] == "FIRED")


def test_setups_board_never_wakes_a_coin_the_brain_holds(monkeypatch):
    from jarvis.service import brain, feed, registry, setups

    j = _J()
    watch_engine._table(j)
    j.db.execute("INSERT INTO evidence_trades (id, watch, coin, status) VALUES ('h1','JARVIS','UPC','OPEN')")
    btc = _series(300, base=100.0, step=0.1)
    j._t = btc[-1][0] + 3600
    up = _series(300, base=50.0, step=0.01)
    up[-1] = (up[-1][0], 53.0, 56.0, 52.9, 55.9, 4000.0)
    monkeypatch.setattr(registry, "members", lambda jj, t=None: {"A": ["BTC", "UPC"]}.get(t, []))
    monkeypatch.setattr(feed, "daily", lambda jj, c: {"BTC": btc, "UPC": up}[c])
    woke = []
    monkeypatch.setattr(brain, "wake", lambda jj, c, trig, det=None: woke.append(c) or True)
    setups.build(j)
    assert "UPC" not in woke


def test_rbd_rule_needs_a_closed_reversal_candle(monkeypatch):
    from src.research import reads as R
    from src.research import zones as Z

    bars = _series(300, base=100.0)
    t = bars[-1][0]
    bars[-1] = (t, 96.0, 99.5, 95.0, 99.0, 1000.0)                            # low is the 5-day low, green, closes in the top of the day
    monkeypatch.setattr(Z, "live_zones", lambda D, near_atr=3.0: {"zones": [{"bot": 94.5, "top": 96.0, "kinds": ["SWING"]}]})
    S = R.Series(bars)
    B = R.Series(_series(300, base=100.0, step=0.1))                         # Bitcoin above its 50-day: market allowed
    ok, stop, why = watch_engine._fires(watch_engine.DAILY["RBD"], S, B, len(bars) - 1, R.rsi(S.c, 10))
    assert ok and stop < 95.0 and "reversal candle" in why
    bars[-1] = (t, 99.0, 99.5, 95.0, 95.5, 1000.0)                            # the same low, a red close: no
    S2 = R.Series(bars)
    assert watch_engine._fires(watch_engine.DAILY["RBD"], S2, B, len(bars) - 1, R.rsi(S2.c, 10))[0] is False
