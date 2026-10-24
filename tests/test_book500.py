"""The $500 NDAX book (D9, D12, D13): sizing, NDAX minimums, the brakes, and the live paper step filling inside the bid and ask."""
import time

from src.research import book500 as B
from tests.test_universe_live import J

DAY = 86400


def test_size_follows_d9():
    v, risk, inv = B.size_setup(500, 100.0, 5.0, 0, B.EDGE_SLEEVE, 0)      # invalidation 10% under -> $25 value, $2.50 risk
    assert round(risk, 2) == 2.5 and round(v, 2) == 25.0 and inv == 90.0
    v, risk, _ = B.size_setup(500, 100.0, 0.5, 0, B.EDGE_SLEEVE, 0)         # tight invalidation: capped at 10% of the book
    assert round(v, 2) == 50.0 and risk < 2.5
    assert B.size_setup(500, 100.0, 5.0, 0, B.EDGE_SLEEVE, 29.0)[0] == 0    # 6% open risk ($30) would be passed


def test_ndax_minimum_and_step():
    inst = {"min_qty": 0.001, "qty_inc": 0.001}
    assert B.round_qty(10, 3.0, inst) == 3.333
    assert B.round_qty(0.002, 3.0, inst) == 0.0


def test_brakes_day_week_streak_and_pause():
    t = 1_700_000_000 - 1_700_000_000 % DAY
    b = B.Brakes(backtest=False)
    b.close(t, 500, [])
    b.close(t + DAY, 489, [])                                                  # -2.2% day
    assert not b.may_buy(t + 2 * DAY) and b.may_buy(t + 3 * DAY)
    b.close(t + 2 * DAY, 489, [-1, -1, -1, -1])                                # 4 losses in a row
    assert b.fired["losing_streak"] == 1 and not b.may_buy(t + 5 * DAY)
    b.close(t + 3 * DAY, 420, [])                                              # 16% under the peak
    assert b.paused and not b.may_buy(t + 60 * DAY)


def _bars(n, start, fall_at=None):
    out = []
    for k in range(n):
        c = 100 + k * 0.5
        if fall_at and k >= fall_at:
            c = 100 + fall_at * 0.5 - (k - fall_at) * 4
        out.append((start + k * DAY, c, c * 1.01, c * 0.99, c, 1.0))
    return out


def test_step_fills_inside_bid_and_ask(tmp_path, monkeypatch):
    from jarvis.service import feed, ndax_book, registry

    start = int(time.time()) - 300 * DAY
    start -= start % DAY
    monkeypatch.setattr(feed, "daily", lambda j, c: _bars(300, start))
    monkeypatch.setattr(registry, "load", lambda j: {"coins": {"BTC": {"ndax": True, "tier": "A"}, "ETH": {"ndax": True, "tier": "A"}}})
    ndax_book._CACHE.clear()

    def get(url):
        if "GetInstruments" in url:
            return [{"Product1Symbol": c, "Product2Symbol": "CAD", "InstrumentId": i, "MinimumQuantity": 1e-5, "QuantityIncrement": 1e-8}
                    for i, c in ((1, "BTC"), (2, "ETH"))]
        if "valet" in url:
            return {"observations": [{"d": "2026-10-09", "FXUSDCAD": {"v": "1.40"}}]}
        return {"BestBid": 99.0, "BestOffer": 101.0}

    j = J(tmp_path)
    out = ndax_book.step(j, get=get)
    assert {b.split()[0] for b in out["bought"]} == {"BTC", "ETH"}             # uptrend: the dial is open, the core goes in
    st = ndax_book.status(j)
    assert st["execution_check"]["fills"] == 2 and st["execution_check"]["inside_bid_ask"] == 2
    # core-v2 (Madhav, 24 Oct 2026, discipline item 4): the first fill is a third of the core (20% of the book), never the whole 60%
    assert st["core_plan"]["state"] == "CONFIRMED"
    assert abs(st["positions"]["BTC"]["paid"] - 200 / 3) < 1 and abs(st["positions"]["ETH"]["paid"] - 100 / 3) < 1
    assert st["positions"]["BTC"]["inv"] and "50-day" in st["positions"]["BTC"]["inv_rule"]   # the invalidation is written at entry
    assert st["tranches"]["done"] == 1
    assert ndax_book.step(j, get=get).get("skipped")                          # one step per daily close


def test_live_guard_brakes_and_limits(tmp_path, monkeypatch):
    from jarvis.service import live_guard as G, ndax_book

    j = J(tmp_path)
    assert not G.check_order(j, "BUY", "BTC", 10)["ok"]                        # no book yet
    ndax_book._table(j)
    s = {"cash": 200.0, "value": 500.0, "pos": {"BTC": {"sleeve": "CORE", "paid": 200, "qty": 0.001, "last": 120000.0}}, "brakes": {}}
    ndax_book._put(j, "state", s)
    assert G.check_order(j, "BUY", "SOL", 40, "EDGE")["ok"]
    assert not G.check_order(j, "BUY", "SOL", 60, "EDGE")["ok"]                # over 10% of the book
    assert not G.check_order(j, "BUY", "ETH", 150, "CORE")["ok"]               # core sleeve full (60%)
    assert G.check_order(j, "SELL", "BTC", 999)["ok"]                           # sells always pass
    s["brakes"] = {"paused": True}
    ndax_book._put(j, "state", s)
    assert "PAUSED" in G.check_order(j, "BUY", "SOL", 10)["why"]
    k = G.kill_plan(j)
    assert k["dry_run"] and "cancel" in k["steps"][0] and any("BTC" in x for x in k["steps"])
