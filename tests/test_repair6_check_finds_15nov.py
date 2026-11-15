"""15 Nov 2026: the finds of audit repair 6's outside check (~/ananta_runs/keen_audit/recheck/pkg6_check.md), each with its test.
2: a step that ran after the night's note (a late candle) reached no note. 3: a night with no note did not break the clean-night run.
4: five more places in the book checks said nothing when they could not look. 7: a stale exchange rate had no age limit and was said only in
the step's raw output. 8: the step did not wait for Ether's candle. 10: the fills check was silent when it could not look."""
import json
import sqlite3
import time

from tests.test_book500 import DAY, _bars
from tests.test_repair6_one_chance_a_night_15nov import COINS, _get, _start
from tests.test_universe_live import J


def test_3_a_night_with_no_note_breaks_the_clean_night_run(tmp_path):
    from jarvis.service import officer

    class JJ:
        db = sqlite3.connect(tmp_path / "jarvis.sqlite")

        def now(self):
            return 1794830400.0                                               # 2026-11-16 12:00 UTC

    j = JJ()
    j.db.execute("CREATE TABLE engine_state (k TEXT PRIMARY KEY, v TEXT)")
    for d in ("2026-11-12", "2026-11-13", "2026-11-15", "2026-11-16"):          # no note on 14 Nov
        j.db.execute("INSERT INTO engine_state VALUES (?, ?)", ("clean_night:" + d, json.dumps({"clean": True})))
    cn = officer.clean_nights(j)
    assert cn["in_a_row"] == 2 and cn["last_break"]["day"] == "2026-11-14" and "no note" in cn["last_break"]["why"][0]   # it was 4


def test_4_the_book_checks_say_when_the_note_the_ledger_or_the_view_cannot_be_read(tmp_path):
    from jarvis import selfcheck
    from jarvis.india import selfparts

    db = tmp_path / "j.sqlite"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE book500_fills (t INTEGER, coin TEXT, side TEXT, qty REAL, px REAL, fee REAL)")
    con.execute("CREATE TABLE book500 (k TEXT PRIMARY KEY, v TEXT)")
    con.execute("INSERT INTO book500 VALUES ('state', ?)", (json.dumps({"cash": 500.0, "pos": {}}),))
    con.execute("CREATE TABLE officer_notes (day TEXT PRIMARY KEY, t INTEGER, note TEXT, facts TEXT, cost_usd REAL)")
    con.execute("INSERT INTO officer_notes VALUES ('2026-11-15', 0, '', '{cut off', 0)")
    con.commit()
    con.close()
    found = selfcheck._book500(db)
    assert any(x.get("cannot_look") and "could not read the nightly note" in x["what"] for x in found), found
    m = tmp_path / "managed"
    m.mkdir()
    (m / "state.json").write_text(json.dumps({"cash_inr": 1000.0, "positions": {}, "trades": [], "costs_inr": 0}))
    (m / "view.json").write_text("{cut")
    (m / "ledger.jsonl").write_text("{cut\n")
    whats = [x["what"] for x in selfparts.managed_book_check(tmp_path)]
    assert any("could not read the managed book's ledger" in w for w in whats) and any("could not read the managed book's view" in w for w in whats)


def test_7_a_stale_rate_is_said_in_the_state_and_is_not_used_after_three_days(tmp_path, monkeypatch):
    import pytest

    from jarvis.service import feed, ndax_book, registry

    start = _start()
    monkeypatch.setattr(registry, "load", lambda j: COINS)
    monkeypatch.setattr(feed, "daily", lambda j, c: _bars(300, start))
    ndax_book._CACHE.clear()
    j = J(tmp_path)
    ndax_book.step(j, get=_get())
    assert ndax_book._get(j, "state").get("usdcad_note") is None
    monkeypatch.setattr(feed, "daily", lambda j, c: _bars(301, start))
    ndax_book._CACHE.clear()
    ndax_book.step(j, get=_get(fx_up=False))
    assert "could not be read" in ndax_book._get(j, "state")["usdcad_note"]          # the note's facts and the self-check read it here
    ndax_book._put(j, "fx_last", {"rate": 1.4, "t": int(time.time()) - 4 * DAY})
    monkeypatch.setattr(feed, "daily", lambda j, c: _bars(302, start))
    ndax_book._CACHE.clear()
    with pytest.raises(Exception):
        ndax_book.step(j, get=_get(fx_up=False))


def test_8_the_step_waits_for_ethers_candle_until_six_and_then_says_so(tmp_path, monkeypatch):
    from jarvis.service import feed, ndax_book, registry

    start = _start()
    monkeypatch.setattr(registry, "load", lambda j: COINS)
    monkeypatch.setattr(feed, "daily", lambda j, c: _bars(300, start) if c == "BTC" else _bars(299, start))   # Ether's candle is late
    ndax_book._CACHE.clear()
    j = J(tmp_path)
    bar = start + 299 * DAY
    out = ndax_book.step(j, get=_get(), now=bar + DAY + 3600)                   # 01:00 UTC: it waits
    assert out.get("waiting", "").startswith("ETH") and not ndax_book._get(j, "state")
    out = ndax_book.step(j, get=_get(), now=bar + DAY + 7 * 3600)               # 07:00 UTC: it steps, and says so
    assert "ETH stepped on an older candle" in out["late_core"] and ndax_book._get(j, "state")["last_bar"] == bar


def test_8_the_feed_pulls_again_while_either_core_candle_is_missing(tmp_path):
    from jarvis.service import feed

    now = (int(time.time()) // DAY) * DAY + 3600
    j = J(tmp_path)
    con = feed._con(j)
    con.execute("INSERT INTO d1 VALUES ('BTC', ?, 1, 1, 1, 1, 1, 1)", (now // DAY * DAY - DAY,))
    con.commit()
    con.close()
    assert feed._waiting_for_btc(j, now)                                        # Bitcoin is in; Ether is not
    con = feed._con(j)
    con.execute("INSERT INTO d1 VALUES ('ETH', ?, 1, 1, 1, 1, 1, 1)", (now // DAY * DAY - DAY,))
    con.commit()
    con.close()
    assert not feed._waiting_for_btc(j, now)


def test_2_a_step_after_the_note_is_kept_for_the_next_note(tmp_path, monkeypatch):
    from jarvis.service import feed, ndax_book, officer, registry

    start = _start()
    monkeypatch.setattr(registry, "load", lambda j: COINS)
    monkeypatch.setattr(feed, "daily", lambda j, c: _bars(300, start))
    ndax_book._CACHE.clear()
    j = J(tmp_path)
    j.db.execute("CREATE TABLE IF NOT EXISTS engine_state (k TEXT PRIMARY KEY, v TEXT)")
    j.db.execute("CREATE TABLE IF NOT EXISTS officer_notes (day TEXT PRIMARY KEY, t INTEGER, note TEXT, facts TEXT, cost_usd REAL)")
    now = start + 300 * DAY + 2 * 3600                                         # the late step, at 02:00 UTC
    day = time.strftime("%Y-%m-%d", time.gmtime(now))
    j.db.execute("INSERT INTO officer_notes VALUES (?, ?, 'written on the old candle', '{}', 0)", (day, now - 6000))
    out = ndax_book.step(j, get=_get(), now=now)
    assert out["bought"]
    kept = json.loads(j.db.execute("SELECT v FROM engine_state WHERE k=?", ("late_step:" + day,)).fetchone()[0])
    assert kept["bought"] == out["bought"]
    j._now = now + DAY
    nxt = time.strftime("%Y-%m-%d", time.gmtime(now + DAY))
    f = officer.facts(j, {})
    assert f["day"] == nxt and f["account"]["after_the_last_note"]["bought"] == out["bought"]


def test_10_the_fills_check_says_when_it_cannot_look(tmp_path):
    from jarvis import selfcheck

    db = tmp_path / "jarvis.sqlite"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE book500_fills (t INTEGER, coin TEXT, side TEXT, sleeve TEXT, qty REAL, px REAL, bid REAL, ask REAL, fee REAL, why TEXT)")
    con.execute("CREATE TABLE book500 (k TEXT PRIMARY KEY, v TEXT)")
    con.execute("INSERT INTO book500_fills VALUES (?, 'BTC', 'BUY', 'CORE', 1, 1, 1, 1, 0, '')", (int(time.time()) - 60,))
    con.commit()
    con.close()
    found = selfcheck._fills_against_candles(db)
    assert found and found[0].get("cannot_look") and "candles" in found[0]["what"]
    sqlite3.connect(tmp_path / "universe_bars.sqlite").execute("CREATE TABLE m5 (coin TEXT, t INTEGER, l REAL, h REAL)").connection.commit()
    found = selfcheck._fills_against_candles(db)
    assert found and found[0].get("cannot_look") and "no Bank of Canada rate" in found[0]["what"]


def test_1_homes_heads_up_says_when_the_holdings_could_not_be_checked(monkeypatch):
    """Its outside check, find 1: Home's notices were rewritten on 14 Nov and still read an error as 'no gap'; carried into the new code."""
    import datetime as dt

    from jarvis.service import nightcheck, places

    monkeypatch.setattr(places.S, "_running", lambda h: {"ok": True})
    monkeypatch.setattr(places.S, "book_gap_checked", lambda j, b: None)
    monkeypatch.setattr(nightcheck, "latest", lambda *a, **k: None)
    c = {"now": dt.datetime(2026, 11, 15, 9, 0), "health": {}, "b": {}, "closes": {}, "dial": {}, "list": {}, "plan": {}, "pos": []}
    out = places.home_notices(None, c)
    assert any("could not be checked" in json.dumps(x) for x in out), out
    monkeypatch.setattr(places.S, "book_gap_checked", lambda j, b: [])
    src = places.home_notices.__code__.co_names
    assert "book_gap_checked" in src and "book_gap" not in src                # the old road (an error read as no gap) is gone
