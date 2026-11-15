"""15 Nov 2026, audit repair 6 (open-list flag 122), G-42: the nightly step had one chance a night. A night whose Bitcoin candle never came
was skipped in silence; a Bank of Canada outage stopped the step though the dial needs no rate; a sale with no NDAX quote was skipped and
the night closed. The two ndax_book.py parts went through the lock's change door (Madhav's yes of 14 Nov 2026, 09:59 Toronto)."""
import time

from tests.test_book500 import DAY, _bars
from tests.test_universe_live import J

COINS = {"coins": {"BTC": {"ndax": True, "tier": "A"}, "ETH": {"ndax": True, "tier": "A"}}}


def _get(fx_up=True, no_quote=()):
    def get(url):
        if "GetInstruments" in url:
            return [{"Product1Symbol": c, "Product2Symbol": "CAD", "InstrumentId": i, "MinimumQuantity": 1e-5, "QuantityIncrement": 1e-8}
                    for i, c in ((1, "BTC"), (2, "ETH"))]
        if "valet" in url:
            if not fx_up:
                raise ConnectionError("the Bank of Canada is down")
            return {"observations": [{"d": "2026-10-09", "FXUSDCAD": {"v": "1.40"}}]}
        if any(f"InstrumentId={i}" in url for i, c in ((1, "BTC"), (2, "ETH")) if c in no_quote):
            return {"BestBid": 0, "BestOffer": 0}
        return {"BestBid": 99.0, "BestOffer": 101.0}
    return get


def _start():
    s = int(time.time()) - 300 * DAY
    return s - s % DAY


def test_a_bank_of_canada_outage_uses_the_last_rate_and_says_so(tmp_path, monkeypatch):
    import pytest

    from jarvis.service import feed, ndax_book, registry

    start = _start()
    monkeypatch.setattr(registry, "load", lambda j: COINS)
    monkeypatch.setattr(feed, "daily", lambda j, c: _bars(300, start))
    ndax_book._CACHE.clear()
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    j = J(tmp_path / "a")
    assert ndax_book.step(j, get=_get()).get("bought")                         # a good night keeps its rate
    monkeypatch.setattr(feed, "daily", lambda j, c: _bars(301, start))
    ndax_book._CACHE.clear()
    out = ndax_book.step(j, get=_get(fx_up=False))                              # it stopped here before
    assert out["usdcad"] == 1.40 and "could not be read" in out["usdcad_note"] and out["bar"]
    ndax_book._CACHE.clear()
    with pytest.raises(Exception):                                              # no rate ever kept: it stops, as before
        ndax_book.step(J(tmp_path / "b"), get=_get(fx_up=False))


def test_a_sale_with_no_quote_waits_and_is_sold_first_at_the_next_step(tmp_path, monkeypatch):
    from jarvis.service import feed, ndax_book, officer, registry

    start = _start()
    monkeypatch.setattr(registry, "load", lambda j: COINS)
    monkeypatch.setattr(feed, "daily", lambda j, c: _bars(300, start))
    ndax_book._CACHE.clear()
    j = J(tmp_path)
    ndax_book.step(j, get=_get())
    assert set(ndax_book.status(j)["positions"]) == {"BTC", "ETH"}
    monkeypatch.setattr(feed, "daily", lambda j, c: _bars(340, start, fall_at=302))       # the dial closes: the whole core is sold
    out = ndax_book.step(j, get=_get(no_quote=("ETH",)))
    assert [x.split()[0] for x in out["sold"]] == ["BTC"] and any("ETH: no NDAX quote" in x for x in out["skipped"])
    st = ndax_book._get(j, "state")
    assert "ETH" in st["pos"] and st["sell_next"]["ETH"]["why"] == "dial closed"
    j.db.execute("CREATE TABLE IF NOT EXISTS engine_state (k TEXT PRIMARY KEY, v TEXT)")
    clean = officer.mark_clean_night(j, {"day": time.strftime("%Y-%m-%d", time.gmtime(st["last_bar"] + DAY)),
                                         "dial": {"candle": time.strftime("%Y-%m-%d", time.gmtime(st["last_bar"])),
                                                  "book_stepped_on": time.strftime("%Y-%m-%d", time.gmtime(st["last_bar"]))}})
    assert not clean["clean"] and any("waiting for an NDAX quote: ETH" in w for w in clean["why"])
    monkeypatch.setattr(feed, "daily", lambda j, c: _bars(341, start, fall_at=302))       # the next close, the quote is back
    out = ndax_book.step(j, get=_get())
    assert out["sold"] and out["sold"][0].startswith("ETH (dial closed (decided on the")
    st = ndax_book._get(j, "state")
    assert "ETH" not in st["pos"] and not st["sell_next"]


def test_the_daily_pull_tries_again_until_bitcoins_candle_is_in(tmp_path, monkeypatch):
    from jarvis.service import feed, registry

    now = (int(time.time()) // DAY) * DAY + 3600                               # 01:00 UTC
    j = J(tmp_path)
    monkeypatch.setattr(registry, "load", lambda j: {"built_at": now - 3000})     # the night's work already ran at 00:10
    monkeypatch.setattr(registry, "members", lambda j: ["BTC", "ETH"])
    monkeypatch.setattr(feed, "pull_5m", lambda *a, **k: {})
    monkeypatch.setattr(feed, "pull_hx", lambda *a, **k: {})
    pulls, nights = [], []

    def pull(j, coins, t):
        pulls.append(list(coins))
        if len(pulls) == 2:                                                     # the candle lands on the second try
            con = feed._con(j)
            con.execute("INSERT INTO d1 VALUES ('BTC', ?, 1, 1, 1, 1, 1, 1)", (now // DAY * DAY - DAY,))
            con.commit()
            con.close()
        return {"coins": len(coins)}

    monkeypatch.setattr(feed, "pull_daily", pull)
    assert feed._waiting_for_btc(j, now)
    feed.cycle(j, now=now, on_daily=lambda j: nights.append(1))
    assert pulls == [["BTC", "ETH"]] and not nights                              # it tried; still no candle; the night does not run twice
    feed.cycle(j, now=now + 300, on_daily=lambda j: nights.append(1))
    assert len(pulls) == 1                                                       # every 15 minutes, not every 5
    feed.cycle(j, now=now + 900, on_daily=lambda j: nights.append(1))
    assert len(pulls) == 2 and nights == [1] and not feed._waiting_for_btc(j, now + 900)
    feed.cycle(j, now=now + 1800, on_daily=lambda j: nights.append(1))
    assert len(pulls) == 2 and nights == [1]                                     # in: nothing more


def test_the_self_check_says_when_the_book_did_not_step_last_night(tmp_path):
    import json
    import sqlite3

    from jarvis import selfcheck

    old = (int(time.time()) // DAY - 3) * DAY
    db = tmp_path / "j.sqlite"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE book500_fills (t INTEGER, coin TEXT, side TEXT, qty REAL, px REAL, fee REAL)")
    con.execute("CREATE TABLE book500 (k TEXT PRIMARY KEY, v TEXT)")
    con.execute("INSERT INTO book500 VALUES ('state', ?)", (json.dumps({"cash": 500.0, "pos": {}, "last_bar": old,
                                                                        "sell_next": {"ETH": {"why": "dial closed", "day": "2026-11-12"}}}),))
    con.commit()
    con.close()
    whats = [x["what"] for x in selfcheck._book500(db)]
    if time.time() % DAY >= 7200:
        assert any("has not stepped on last night's candle" in w for w in whats), whats
    assert any("sale of ETH (dial closed) waits for an NDAX quote" in w for w in whats), whats
