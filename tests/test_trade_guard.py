"""The trade guard (Oct 15, acceptance gate ops_no_trade_unhealthy): every book that opens a paper position refuses a new one while
the kill switch is on or cannot be read, and on a stale price or daily candle, writing the block once a day in trade_guard_log;
on fresh inputs it still opens; exits, stops and sells never ask the guard."""
import json
import sqlite3
import time
import types

import pytest

from jarvis.service import trade_guard as tg

DAY = 86400
T0D = 1_700_000_000 - 1_700_000_000 % DAY


class Hands:
    """A kill switch the test sets, or one that cannot be read."""

    def __init__(self, kill=False, fail=False):
        self.kill, self.fail, self.calls = kill, fail, 0

    def kill_switch_on(self):
        self.calls += 1
        if self.fail:
            raise ConnectionError("Hands is not answering")
        return self.kill


def _log(db, book=None):
    tg._table(db)
    q = "SELECT book, coin, why FROM trade_guard_log" + (" WHERE book=?" if book else "")
    return [tuple(r) for r in db.execute(q, (book,) if book else ()).fetchall()]


def _up(n=260):
    """n closed daily candles in a gentle uptrend (every trend rule says hold)."""
    return [(T0D + k * DAY, c, c * 1.01, c * 0.99, c, 1.0) for k, c in enumerate(100 * 1.003 ** k for k in range(n))]


# ---------------------------------------------------------------------------
# the guard itself
# ---------------------------------------------------------------------------
def test_kill_switch_then_price_then_candle_and_each_block_logged_once_a_day():
    now = 1_800_000_000.0
    j = types.SimpleNamespace(db=sqlite3.connect(":memory:"), now=lambda: now, hands=Hands())
    assert tg.blocked(j, "X", "BTC", price_t=now - 60, max_age_s=tg.LIVE_PRICE_S, daily_t=now - DAY) is None
    assert tg.blocked(j, "X", "BTC", price_t=now - 6 * 60, max_age_s=tg.LIVE_PRICE_S) == "the price is more than 5 minutes old"
    assert tg.blocked(j, "X", "BTC", price_t=now - 14 * 60, max_age_s=tg.BAR_PRICE_S) is None
    assert tg.blocked(j, "X", "BTC", price_t=now - 21 * 60, max_age_s=tg.BAR_PRICE_S) == "the price is more than 20 minutes old"
    assert tg.blocked(j, "X", "BTC", daily_t=now - 2 * DAY - 2 * 3600) is None                 # yesterday's candle, late in the day
    assert tg.blocked(j, "X", "BTC", daily_t=now - 2 * DAY - 4 * 3600) == tg.DAILY_OLD
    assert tg.blocked(j, "X", "BTC", daily_t=0) == tg.NO_DAILY
    j.hands.kill = True
    assert tg.blocked(j, "X", "BTC", price_t=now) == tg.KILL_ON                                 # the kill switch comes first
    assert tg.blocked(j, "X", "BTC", price_t=now) == tg.KILL_ON
    rows = _log(j.db)
    assert len(rows) == 5 and rows.count(("X", "BTC", tg.KILL_ON)) == 1                        # once per book, coin, reason and day


def test_a_kill_switch_that_cannot_be_read_blocks_and_a_burst_does_not_wait_on_it_again():
    h = Hands(fail=True)
    j = types.SimpleNamespace(db=sqlite3.connect(":memory:"), now=time.time, hands=h)
    assert tg.blocked(j, "X", "ETH") == tg.KILL_UNREAD
    assert tg.blocked(j, "Y", "SOL") == tg.KILL_UNREAD and h.calls == 1                          # remembered for a minute
    h.fail = False
    tg.reset()
    assert tg.blocked(j, "X", "ETH") is None and h.calls == 2
    assert {r[2] for r in _log(j.db)} == {tg.KILL_UNREAD}


# ---------------------------------------------------------------------------
# T3 trend books MAIN and SHADOW (inside the Explorer; AUTO, as Madhav runs them)
# ---------------------------------------------------------------------------
def _t3(monkeypatch, mode="AUTO"):
    from src.intelligence import portfolio_layer as pl
    from tests.test_explorer_live import _mk

    rule = {"hold": True}
    monkeypatch.setattr(pl, "rate", lambda coin, v, btc_on, mom_rank: ("STRONG", True, ["test"]) if rule["hold"] else ("OUT", False, ["test"]))
    d, clock, hands, ex, alerts = _mk()
    ex.start()
    if mode == "AUTO":
        pl.PortfolioLayer(d).set_mode("AUTO", by="test")
    return d, clock, hands, ex, alerts, rule


def _t3_fills(d):
    con = sqlite3.connect(d / "portfolio_book.sqlite")
    return [json.loads(j) for (j,) in con.execute("SELECT json FROM fills")], con


def test_t3_books_buy_nothing_while_the_kill_switch_is_on_and_still_sell(monkeypatch):
    from tests.test_explorer_live import _advance

    d, clock, hands, ex, alerts, rule = _t3(monkeypatch)
    hands.kill = True
    _advance(ex, clock, 4 * 24 * 2)
    fills, con = _t3_fills(d)
    assert fills == []                                                          # neither MAIN nor SHADOW bought
    assert {r[2] for r in _log(con)} == {tg.KILL_ON} and {r[0] for r in _log(con)} == {"T3-MAIN", "T3-SHADOW"}
    assert any("held back" in a[0] for a in alerts)
    j = types.SimpleNamespace(dir=d, db=sqlite3.connect(":memory:"), now=lambda: clock["now"])
    assert {r["book"] for r in tg.recent(j)} == {"T3-MAIN", "T3-SHADOW"}         # the Evidence page reads the Explorer's log too
    hands.kill = False                                                          # healthy again: the next daily close buys
    _advance(ex, clock, 4 * 24)
    fills, _ = _t3_fills(d)
    assert fills and {f["side"] for f in fills} == {"BUY"} and {f["book"] for f in fills} == {"MAIN", "SHADOW"}
    hands.kill, rule["hold"] = True, False                                      # kill switch on again, and the rule says sell all
    _advance(ex, clock, 4 * 24)
    fills, _ = _t3_fills(d)
    assert any(f["side"] == "SELL" for f in fills)                               # exits never ask the guard


def test_t3_books_do_not_buy_a_coin_whose_price_stopped(monkeypatch):
    from tests.test_explorer_live import _advance

    from jarvis.service import trade_guard as tg

    # This fixture steps every 15 minutes, so a coin whose candles stop is one step (15 min) old at the next decision: under the
    # live 20-minute threshold (Oct 15: the Explorer's close is up to ~16 minutes old in normal running). The T3 path itself is
    # what this test checks, with a 10-minute threshold; the threshold's value is checked in the first test.
    monkeypatch.setattr(tg, "BAR_PRICE_S", 10 * 60)
    d, clock, hands, ex, alerts, rule = _t3(monkeypatch)
    real = hands.candles

    def candles(coin, tf, limit):
        if coin == "ETH":
            raise RuntimeError("ETH candles are not coming")
        return real(coin, tf, limit)
    hands.candles = candles
    _advance(ex, clock, 4 * 24 * 2)
    fills, con = _t3_fills(d)
    assert fills and "ETH" not in {f["coin"] for f in fills}                     # every other coin is bought, ETH is not
    assert ("T3-MAIN", "ETH", "the price is more than 10 minutes old") in _log(con)


def test_t3_approval_is_held_back_while_unhealthy_and_the_suggestion_stays_open(monkeypatch):
    from jarvis.service import core
    from tests.test_explorer_live import _advance
    from tests.test_jarvis_core import FakeHands

    d, clock, hands, ex, alerts, rule = _t3(monkeypatch, mode="SUGGEST")
    _advance(ex, clock, 4)                                                      # the first close: ENTER suggestions wait for him
    j = core.Jarvis(d, owner_email="o@x.com", password_hash=core.hash_password("pw pw pw pw 1"), secret="k" * 40,
                    hands=FakeHands(), now=lambda: clock["now"])
    assert j.portfolio()["pending"]
    j.hands.kill = True
    with pytest.raises(ValueError, match="kill switch is on"):
        j.approve("o@x.com", "all")
    assert j.portfolio()["pending"]                                              # still open
    j.hands.kill = False
    clock["now"] += 25 * 60                                                     # the Explorer's last prices are 25 minutes old
    with pytest.raises(ValueError, match="more than 20 minutes old"):
        j.approve("o@x.com", "all")
    clock["now"] -= 25 * 60
    assert j.approve("o@x.com", "all") and not j.portfolio()["pending"]           # fresh: approved and bought
    assert {r[2] for r in _log(j.db, "T3-MAIN")} == {tg.KILL_ON, "the price is more than 20 minutes old"}


# ---------------------------------------------------------------------------
# T3-T30, the 30-coin trend book (AUTO)
# ---------------------------------------------------------------------------
def _t30(tmp_path, eth_bars):
    from jarvis.service import tier30
    from tests.test_reads import _fake_jarvis

    D = _up()
    tmp_path.mkdir(exist_ok=True)
    j = _fake_jarvis(tmp_path, {"BTC": D}, {})
    j.now = lambda: D[-1][0] + DAY + 3600                                         # an hour after the last candle closed
    con = tier30._con(j)
    for coin, bars in (("BTC", D), ("SOL", D), ("ETH", eth_bars(D))):
        con.executemany("INSERT INTO bars VALUES (?,?,?,?,?,?,?)", [(coin, *b) for b in bars])
    con.execute("INSERT INTO meta VALUES ('done_day', ?)", (str(10 ** 12),))     # nothing to pull from Binance
    con.commit()
    return j


def test_t30_book_needs_the_kill_switch_off_and_each_coins_own_fresh_candle(tmp_path):
    from jarvis.service import tier30

    j = _t30(tmp_path / "kill", lambda D: D)
    j.hands = Hands(kill=True)
    out = tier30.run(j)
    assert out["t3"]["held_back"] and not tier30._layer(j).status({})["books"]["MAIN"]["holdings"]
    assert {r[2] for r in _log(j.db, "T30-MAIN")} == {tg.KILL_ON}
    j = _t30(tmp_path / "stale", lambda D: D[:-2])                               # ETH's candles stopped two days ago (TK13 keeps it)
    out = tier30.run(j)
    held = tier30._layer(j).status({"BTC": 1.0, "SOL": 1.0, "ETH": 1.0})["books"]["MAIN"]["holdings"]
    assert set(held) == {"BTC", "SOL"} and "ETH" not in tier30.STALE             # fresh coins bought, ETH held back by the guard
    assert ("T30-MAIN", "ETH", tg.DAILY_OLD) in _log(j.db)


# ---------------------------------------------------------------------------
# the $500 NDAX book
# ---------------------------------------------------------------------------
def _book500(monkeypatch, bars_of):
    from jarvis.service import feed, ndax_book, registry

    monkeypatch.setattr(feed, "daily", lambda j, c: bars_of(c))
    monkeypatch.setattr(registry, "load", lambda j: {"coins": {"BTC": {"ndax": True, "tier": "A"}, "ETH": {"ndax": True, "tier": "A"}}})
    ndax_book._CACHE.clear()

    def get(url):
        if "GetInstruments" in url:
            return [{"Product1Symbol": c, "Product2Symbol": "CAD", "InstrumentId": i, "MinimumQuantity": 1e-5, "QuantityIncrement": 1e-8}
                    for i, c in ((1, "BTC"), (2, "ETH"))]
        if "valet" in url:
            return {"observations": [{"d": "2026-10-09", "FXUSDCAD": {"v": "1.40"}}]}
        return {"BestBid": 99.0, "BestOffer": 101.0}
    return get


def test_book500_buys_nothing_with_the_kill_switch_on_skips_a_stale_coin_and_still_sells(tmp_path, monkeypatch):
    from jarvis.service import ndax_book
    from tests.test_book500 import _bars
    from tests.test_universe_live import J

    start = int(time.time()) - 300 * DAY
    start -= start % DAY
    up = _bars(300, start)
    get = _book500(monkeypatch, lambda c: up)
    (tmp_path / "kill").mkdir()
    j = J(tmp_path / "kill")
    j.hands = Hands(kill=True)
    out = ndax_book.step(j, get=get)
    assert out["bought"] == [] and any("kill switch is on" in s for s in out["skipped"])
    assert {r[1] for r in _log(j.db, "BOOK500")} == {"BTC", "ETH"}
    get = _book500(monkeypatch, lambda c: up[:-3] if c == "ETH" else up)          # ETH's daily candles stopped three days ago
    (tmp_path / "stale").mkdir()
    j = J(tmp_path / "stale")
    out = ndax_book.step(j, get=get)
    assert [b.split()[0] for b in out["bought"]] == ["BTC"] and ("BOOK500", "ETH", tg.DAILY_OLD) in _log(j.db)
    get = _book500(monkeypatch, lambda c: _bars(301, start, fall_at=250))        # the next close: the dial closes ...
    j.hands = Hands(kill=True)                                                   # ... while the kill switch is on
    out = ndax_book.step(j, get=get)
    assert any(s.startswith("BTC") for s in out["sold"]) and out["bought"] == []  # the core still goes out


# ---------------------------------------------------------------------------
# Jarvis's own book (JARVIS) and its random twin (JARVIS_RANDOM)
# ---------------------------------------------------------------------------
def test_brain_opens_only_on_healthy_inputs_its_twin_needs_its_own_fresh_price_and_exits_always_work(monkeypatch):
    from jarvis.service import brain, eye, watch_engine
    from tests.test_jarvis_brain import _brain_j

    eye.STATE.update(prices={}, prices_t={}, armed={}, ticks=0, last_t=None)
    j, ex = _brain_j()
    px = dict(j.prices())
    coin = next(c for c in px if c != "BTC")
    p = px[coin]
    age = {"price": 60.0, "daily": DAY}
    monkeypatch.setattr(brain, "pack", lambda jj, c, trig: {
        "coin": c, "price": p, "daily": {"atr": p * 0.04}, "market": {"regime": "ALLOWED"}, "news": {"verdict": "CLEAR"},
        "price_t": jj.now() - age["price"], "price_max_age_s": tg.LIVE_PRICE_S, "daily_t": jj.now() - age["daily"]})
    monkeypatch.setattr(brain, "_atr", lambda jj, c: px[c] * 0.04)
    plan = {"action": "TAKE", "confidence": 62, "size_pct": 40, "stop": p * 0.94, "target": None, "trail_atr": 1.5, "days": 10,
            "thesis": "test", "knowledge_used": ["REGIME", "ZONES"]}
    call = lambda u: (json.dumps(plan), {"in": 10, "out": 10, "model": "fake"})  # noqa: E731

    def mine():
        return [t for t in watch_engine.trades(j) if t["watch"] in ("JARVIS", "JARVIS_RANDOM") and t["status"] == "OPEN"]

    j.hands.kill = True
    r = brain.decide(j, coin, {}, call=call)
    assert r["action"] == "PASS" and r["trade"] is None and not mine()
    j.hands.kill = False
    age["price"] = 10 * 60                                                      # the eye has not looked for ten minutes
    assert brain.decide(j, coin, {}, call=call)["action"] == "PASS" and not mine()
    age.update(price=60.0, daily=3 * DAY)                                       # the coin's daily candles stopped
    assert brain.decide(j, coin, {}, call=call)["action"] == "PASS" and not mine()
    notes = [n for (n,) in j.db.execute("SELECT note FROM brain_decisions ORDER BY t")]
    assert len(notes) == 3 and all(n and "trade guard: " in n for n in notes)
    assert {r[2] for r in _log(j.db, "JARVIS")} == {tg.KILL_ON, "the price is more than 5 minutes old", tg.DAILY_OLD}
    age["daily"] = DAY
    r = brain.decide(j, coin, {}, call=call)                                    # healthy: the trade and its twin
    assert r["action"] == "TAKE" and r["trade"] and r["random_twin"] and len(mine()) == 2
    clock_now = j.now
    j.now = lambda: clock_now() + 25 * 60                                       # the twin's price (the Explorer's close) is now old
    r = brain.decide(j, coin, {}, call=call)
    assert r["action"] == "TAKE" and r["trade"] and r["random_twin"] is None
    assert [x[2] for x in _log(j.db, "JARVIS_RANDOM")] == ["the price is more than 20 minutes old"]
    j.hands.kill = True                                                         # exits never ask: the stop still sells
    closed = brain.manage_live(j, {coin: p * 0.5})
    assert closed and all(x["coin"] == coin for x in closed)


def test_an_ai_switch_or_budget_check_that_errors_is_a_no_for_the_brain_and_the_bold_book(tmp_path, monkeypatch):
    import jarvis.service.ask as ask_mod
    from jarvis.service import bold, brain
    from tests.test_universe_live import J

    def broken(j):
        raise RuntimeError("database is locked")
    monkeypatch.setattr(ask_mod, "Ask", broken)
    j = J(tmp_path)
    brain._table(j)
    ok, why = brain.can_decide(j)
    assert not ok and "could not be read" in why
    ok, why = bold._ai_ok(j)
    assert not ok and "could not be read" in why


def test_the_brain_pays_for_no_decision_while_the_kill_switch_is_on_or_cannot_be_read(tmp_path, monkeypatch):
    """Oct 15: with the kill switch on no trade can open, so a paid decision would be money for nothing. Everything else is open:
    the AI switch on, the day's budget left, the limit not reached."""
    import jarvis.service.ask as ask_mod
    from jarvis.service import brain
    from tests.test_universe_live import J

    class Open:
        def __init__(self, j):
            pass

        def setting(self, key):
            return "1"

        def spend(self):
            return {"left_usd": 5.0}
    monkeypatch.setattr(ask_mod, "Ask", Open)
    j = J(tmp_path)
    brain._table(j)
    j.hands = Hands()
    assert brain.can_decide(j) == (True, "")
    j.hands = Hands(kill=True)
    ok, why = brain.can_decide(j)
    assert not ok and "kill switch is on" in why
    j.hands = Hands(fail=True)
    ok, why = brain.can_decide(j)
    assert not ok and "kill switch could not be read" in why


# ---------------------------------------------------------------------------
# the bold book (JARVIS_BOLD) and its twin (RANDOM_BOLD)
# ---------------------------------------------------------------------------
def test_bold_book_waits_while_the_kill_switch_is_on_and_needs_fresh_prices_for_both_trades(tmp_path, monkeypatch):
    from jarvis.service import bold, brain
    from tests.test_bold import PX, _ready, _reply

    def never(u):
        raise AssertionError("no model call while the kill switch is on")
    (tmp_path / "kill").mkdir()
    j = _ready(tmp_path / "kill", monkeypatch, dial=1.0)
    j.hands = Hands(kill=True)
    assert bold.run(j, call=never) == {"blocked": tg.KILL_ON}
    assert not j.db.execute("SELECT 1 FROM bold_decisions").fetchone()           # not decided: it tries again at the next run
    assert _log(j.db, "JARVIS_BOLD") == [("JARVIS_BOLD", "", tg.KILL_ON)]
    j.hands = Hands()
    age = {"SOL": 20 * 60}                                                      # the pick's price is 20 minutes old
    monkeypatch.setattr(brain, "_live_quote", lambda jj, c: (PX.get(c), jj.now() - age.get(c, 30), tg.LIVE_PRICE_S))
    r = bold.run(j, call=lambda u: _reply())
    assert r["action"] == "BLOCKED" and "more than 5 minutes old" in r["note"]
    assert not j.db.execute("SELECT 1 FROM evidence_trades").fetchone()
    (tmp_path / "twin").mkdir()
    j = _ready(tmp_path / "twin", monkeypatch, dial=1.0)
    monkeypatch.setattr(brain, "_live_quote", lambda jj, c: (PX.get(c), jj.now() - (30 if c == "SOL" else 20 * 60), tg.LIVE_PRICE_S))
    r = bold.run(j, call=lambda u: _reply())
    assert r["action"] == "TAKE" and r["coin"] == "SOL" and r["random_id"] is None        # the pick opens, its stale twin does not
    rows = dict(j.db.execute("SELECT watch, coin FROM evidence_trades WHERE status='OPEN'").fetchall())
    assert rows == {"JARVIS_BOLD": "SOL"} and {x[0] for x in _log(j.db)} == {"RANDOM_BOLD"}


# ---------------------------------------------------------------------------
# ZONE_TOUCH from the eye (the 10), including the Explorer-price fallback when Kraken is down
# ---------------------------------------------------------------------------
def test_eye_zone_touch_needs_a_healthy_look_and_its_stops_always_work(monkeypatch):
    from jarvis.service import eye, watch_engine
    from jarvis.service.manual import Manual
    from src.intelligence import explorer_live
    from tests.test_ask_ananta import _jarvis

    j, ex = _jarvis()
    px = dict(j.prices())
    coin = next(c for c in px if c != "BTC")
    now = j.now()
    zone = {"bot": px[coin] * 0.93, "top": px[coin] * 0.97, "kinds": ["AVERAGE-200"], "history": "SUPPORTED", "side": "support"}
    armed = {"zones": {coin: [zone]}, "atr": {coin: px[coin] * 0.02}, "attention": {coin: "LOW"}, "regime": "ALLOWED",
             "prev_close": {}, "daily_t": {coin: now - DAY}}
    inside = {**px, coin: px[coin] * 0.96}

    def cross(p2, arm=armed, source="kraken"):                                 # one look above the zone, the next inside it
        eye.STATE.update(prices={}, prices_t={}, armed={}, ticks=0)
        eye._cool.clear()
        eye.tick(j, px, armed=arm)
        return [e["kind"] for e in eye.tick(j, p2, armed=arm, source=source)]

    def opened():
        return [t for t in watch_engine.trades(j, "ZONE_TOUCH") if t["status"] == "OPEN"]

    j.hands.kill = True
    assert "ZONE_ENTRY" in cross(inside) and not opened()
    j.hands.kill = False
    stale = tg.Prices(inside, {c: now - 25 * 60 for c in inside})                 # Kraken down: the Explorer's closes, 25 minutes old
    assert "ZONE_ENTRY" in cross(stale, source="explorer 5m (ticker down)") and not opened()
    assert "ZONE_ENTRY" in cross(inside, arm={**armed, "daily_t": {coin: now - 3 * DAY}}) and not opened()
    assert {r[2] for r in _log(j.db, "ZONE_TOUCH")} == {tg.KILL_ON, "the price is more than 20 minutes old", tg.DAILY_OLD}
    assert "ZONE_TOUCH" in cross(inside) and len(opened()) == 1                   # healthy: it opens
    Manual(j.db, j.now).execute("o", {"side": "buy", "coin": coin, "usd": 100, "stop": round(px[coin] * 0.95, 8)}, px)
    j.hands.kill = True                                                         # the kill switch on everywhere ...
    monkeypatch.setattr(explorer_live.Hands, "kill_switch_on", lambda self: True)
    kinds = [e["kind"] for e in eye.tick(j, {**inside, coin: px[coin] * 0.90}, armed=armed)]
    assert "EVIDENCE_EXIT" in kinds and "MY_STOP" in kinds and not opened()     # ... and both stops still sell


# ---------------------------------------------------------------------------
# ZONE_TOUCH-U<tier> from the universe feed (every coin)
# ---------------------------------------------------------------------------
def test_universe_zone_touch_needs_fresh_zones_a_fresh_feed_price_and_candle(tmp_path, monkeypatch):
    from jarvis.service import universe_watch as U
    from jarvis.service import watch_engine
    from tests.test_universe_live import J

    now = 1_800_000_000
    j = J(tmp_path, now=now)
    watch_engine._table(j)
    coin, zone = "PEPE", {"bot": 0.93, "top": 0.97, "kinds": ["SWING"], "history": "SUPPORTED"}

    def cross(armed_t=now - 3600, daily_t=now - DAY, seen=now):
        armed = {"zones": {coin: [zone]}, "atr": {coin: 0.02}, "tier": {coin: "C"}, "daily_t": {coin: daily_t}, "regime": "ALLOWED",
                 "t": armed_t}
        monkeypatch.setitem(U.STATE, "armed", armed)
        monkeypatch.setitem(U.STATE, "prev", {coin: 1.0})
        return U.tick(j, tg.Prices({coin: 0.96}, {coin: seen}))["opened"]

    j.hands = Hands(kill=True)
    assert cross() == []
    j.hands = Hands()
    assert cross(armed_t=now - 3 * DAY) == []                                    # the zones and regime come from an old arm
    assert cross(seen=now - 10 * 60) == []                                       # the feed's price is ten minutes old
    assert cross(daily_t=now - 3 * DAY) == []                                    # the coin's daily candles stopped
    assert {r[2] for r in _log(j.db, "ZONE_TOUCH-UC")} == {tg.KILL_ON, tg.ZONES_OLD, "the price is more than 5 minutes old", tg.DAILY_OLD}
    assert cross() == [{"watch": "ZONE_TOUCH-UC", "coin": coin}]                 # healthy: it opens


# ---------------------------------------------------------------------------
# the daily watches (H07, the reads, the random baselines, every -U<tier> rule, H07-T30)
# ---------------------------------------------------------------------------
def test_daily_signals_open_only_while_the_kill_switch_is_readable_and_off(tmp_path):
    from jarvis.service import watch_engine as W
    from tests.test_reads import _fake_jarvis

    def run(name, hands):
        (tmp_path / name).mkdir()
        j = _fake_jarvis(tmp_path / name, {"BTC": _up(), "ETH": _up()}, {})
        j.hands = hands
        W.run(j, watches=("RANDOM_10D",))
        return j

    j = run("kill", Hands(kill=True))
    assert not W.trades(j, "RANDOM_10D") and {r[2] for r in _log(j.db, "RANDOM_10D")} == {tg.KILL_ON}
    j = run("unread", Hands(fail=True))
    assert not W.trades(j, "RANDOM_10D") and {r[2] for r in _log(j.db, "RANDOM_10D")} == {tg.KILL_UNREAD}
    j = run("healthy", Hands())
    assert [t["status"] for t in W.trades(j, "RANDOM_10D")] == ["WAITING"]
    W.run(j, watches=("RANDOM_10D",))                                           # no new closed candle: no new signal (by construction)
    assert len(W.trades(j, "RANDOM_10D")) == 1


# ---------------------------------------------------------------------------
# the manual book (owner and guests) and watches in auto mode
# ---------------------------------------------------------------------------
def test_manual_and_auto_watch_buys_need_the_guard_and_sells_never_do(monkeypatch):
    from jarvis.service import watches
    from jarvis.service.manual import Manual
    from src.intelligence import explorer_live
    from tests.test_account_watches import _g, _snap

    clock = {"t": 1_800_000_000}
    g = _g(clock)
    now = clock["t"]
    fresh = tg.Prices({"BTC": 100.0, "SOL": 50.0}, {"BTC": now - 60, "SOL": now - 60})
    stale = tg.Prices({"BTC": 100.0, "SOL": 50.0}, {"BTC": now - 25 * 60, "SOL": now - 25 * 60})
    M = Manual(g.db, g.now)
    with pytest.raises(ValueError, match="more than 20 minutes old"):
        M.execute("guest:asha@x.com", {"side": "buy", "coin": "BTC", "usd": 100}, stale)
    assert M.execute("guest:asha@x.com", {"side": "buy", "coin": "BTC", "usd": 100}, fresh)["side"] == "buy"
    g.prices = lambda: stale                                                     # an auto watch on stale prices buys nothing
    w = watches.create(g, ["BTC"], mode="auto")
    watches.check_account(g, _snap(fire=True))
    assert "more than 20 minutes old" in watches.activity(g)[0]["body"]
    monkeypatch.setattr(explorer_live.Hands, "kill_switch_on", lambda self: True)   # the kill switch is on
    with pytest.raises(ValueError, match="kill switch is on"):
        M.execute("guest:asha@x.com", {"side": "buy", "coin": "SOL", "usd": 100}, fresh)
    assert M.execute("guest:asha@x.com", {"side": "sell", "coin": "BTC"}, fresh)["side"] == "sell"   # a sale always goes
    assert not M.state(fresh)["positions"]
    g.prices = lambda: fresh
    g.db.execute("UPDATE account_watches SET state='WATCHING', fired_t=NULL WHERE id=?", (w["id"],))
    g.db.commit()
    watches.check_account(g, _snap(fire=True))
    assert "kill switch is on" in watches.activity(g)[0]["body"] and not M.state(fresh)["positions"]
    assert {(r[0], r[2]) for r in _log(g.db)} == {("MANUAL", "the price is more than 20 minutes old"), ("MANUAL", tg.KILL_ON),
                                                 ("ACCOUNT_WATCH", "the price is more than 20 minutes old"), ("ACCOUNT_WATCH", tg.KILL_ON)}
