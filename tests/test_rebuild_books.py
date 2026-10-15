"""Gate ops_reconstructable (Oct 15): every book re-checked nightly against the candles it decides on."""
import json
import sqlite3
import types

DAY = 86400
NOW = 1_792_022_400 + 3600                       # 2026-10-14 01:00 UTC: Oct 13 is the last complete day
D0 = 1_792_022_400 - 5 * DAY                     # 2026-10-09


def _j(tmp_path):
    from jarvis.service import core

    return types.SimpleNamespace(dir=tmp_path, db=core.SafeDB(sqlite3.connect(":memory:")), now=lambda: NOW)


def _bars(lows: dict, hi: float = 1.40, close: float = 1.38, n: int = 5) -> list[tuple]:
    return [(D0 + k * DAY, 1.38, hi, lows.get(k, 1.37), close, 1.0) for k in range(n)]


def test_every_trade_is_checked_on_the_candles_its_book_used(tmp_path, monkeypatch):
    """XRP Oct 14 (live case): Binance's low 1.319 never reached the twin's 1.303 stop, the Explorer's 1.302 did. Either source
    may confirm a price; outside both is a mismatch; a leg on today's still-moving candle is not checked."""
    from jarvis.service import learning
    from jarvis.service import watch_engine as W

    j = _j(tmp_path)
    W._table(j)
    monkeypatch.setattr(learning, "_daily", lambda j, c: _bars({3: 1.319}))         # Binance
    monkeypatch.setattr(W, "_daily", lambda j, c: _bars({3: 1.302}))                # the Explorer's candles
    rows = [("a", "JARVIS_RANDOM", D0 + 600, 1.38, 1.303, D0 + 3 * DAY, 1.303, "stop", "CLOSED"),   # stop touched on the Explorer's
            ("b", "H07", D0 + DAY, 1.38, None, D0 + 2 * DAY, 1.39, "RSI back over 40", "CLOSED"),
            ("c", "ZONE_TOUCH", D0 + 700, 1.50, 1.2, None, None, None, "OPEN"),                   # 1.50 is above both highs
            ("d", "H07-UA", NOW - 60, 1.38, None, None, None, None, "OPEN")]                      # today: not yet checkable
    for i, w, et, e, st, xt, x, why, s in rows:
        j.db.execute("INSERT INTO evidence_trades (id, watch, coin, source, entry_t, entry, stop, exit_t, exit, exit_why, status) "
                     "VALUES (?,?,?,?,?,?,?,?,?,?,?)", (i, w, "XRP", "daily", et, e, st, xt, x, why, s))
    out = learning.rebuild_trades(j)
    assert out["checked"] == 5 and out["today_not_checked"] == 1 and out["mismatches"] == 1
    assert out["list"][0]["id"] == "c" and out["list"][0]["leg"] == "entry"
    assert j.db.execute("SELECT source, match, only_live FROM rebuild_log").fetchall() == [("trades", 0, 1)]
    # the brain's own re-check reads the same two sources, so the twin's stop is no longer a false alarm
    assert learning.rebuild_brain(j)["mismatches"] == 0


def test_trend_book_decisions_follow_the_rule_on_their_candles(tmp_path, monkeypatch):
    from jarvis.service import learning
    from jarvis.service import watch_engine as W

    j = _j(tmp_path)
    up = [(D0 - (60 - k) * DAY, 1.0 + k / 100, 1.02 + k / 100, 0.98 + k / 100, 1.0 + k / 100, 1.0) for k in range(61)]   # rising
    monkeypatch.setattr(W, "_daily", lambda j, c: up)
    monkeypatch.setattr(learning, "_daily", lambda j, c: up)
    con = sqlite3.connect(tmp_path / "portfolio_book.sqlite")
    con.execute("CREATE TABLE decisions (day_t INTEGER PRIMARY KEY, json TEXT)")
    con.execute("CREATE TABLE fills (seq INTEGER PRIMARY KEY AUTOINCREMENT, t INTEGER, json TEXT)")
    day_t = up[-2][0] + DAY                      # decided on the close of the day before the last candle; filled on that last day
    close = up[-2][4]
    con.execute("INSERT INTO decisions VALUES (?,?)", (day_t, json.dumps({"ratings": {"BTC": {"hold": True, "close": close},
                                                                                     "ETH": {"hold": True, "close": close}}})))
    con.execute("INSERT INTO fills (t, json) VALUES (?,?)", (day_t + 60, json.dumps({"t": day_t + 60, "coin": "ETH", "px": close, "book": "MAIN"})))
    con.commit()
    out = learning.rebuild_t3(j)
    assert out["match"] and out["checked"] == 2 and out["fills_checked"] == 1
    con.execute("UPDATE decisions SET json=?", (json.dumps({"ratings": {"BTC": {"hold": True, "close": close}, "ETH": {"hold": False, "close": close}}}),))
    con.commit()
    out = learning.rebuild_t3(j)
    assert not out["match"] and out["list"][0]["coin"] == "ETH" and out["list"][0]["rebuilt_hold"] is True
    assert [r[0] for r in j.db.execute("SELECT source FROM rebuild_log ORDER BY t")] == ["trend", "trend"]


def _stream(tmp_path, times):
    """An explorer_decisions.jsonl with one row per 15-minute bar time (the `t` field is the bar time)."""
    (tmp_path / "explorer_decisions.jsonl").write_text("".join(json.dumps({"t": t, "coin": "BTC"}) + "\n" for t in times))


def test_the_15_minute_stream_must_have_no_hole_over_35_minutes(tmp_path):
    """Reconstruction Fix 4: a book can rebuild perfectly and still miss the hours the Explorer was down."""
    from jarvis.service import evidence_live as el

    j = _j(tmp_path)
    assert not el._stream_ok(j, NOW)                                                  # no file at all
    _stream(tmp_path, [NOW - 2 * DAY + 900 * k for k in range(0, 2 * 96 + 1)])
    assert el._stream_ok(j, NOW)                                                      # every 15 minutes
    _stream(tmp_path, [NOW - 2 * DAY + 900 * k for k in range(0, 2 * 96 + 1) if not 40 <= k <= 43])
    assert not el._stream_ok(j, NOW)                                                  # a one-hour hole
    _stream(tmp_path, [NOW - 2 * DAY + 900 * k for k in range(0, 2 * 96 + 1) if k != 40])
    assert el._stream_ok(j, NOW)                                                      # one missed bar (30 min) is inside the 35-minute bar
    _stream(tmp_path, [NOW - 2 * DAY + 900 * k for k in range(0, 2 * 96 - 8)])
    assert not el._stream_ok(j, NOW)                                                  # the stream stopped two hours ago
    _stream(tmp_path, [NOW - 5 * DAY + 900 * k for k in range(0, 2 * 96)] + [NOW - 2 * DAY + 900 * k for k in range(0, 2 * 96 + 1)])
    assert el._stream_ok(j, NOW)                                                      # an old hole outside the last 2 days does not count


def test_the_gate_goes_partly_when_the_stream_has_a_hole(tmp_path):
    from jarvis.service import evidence_live as el
    from jarvis.service import ndax_book

    j = _j(tmp_path)
    el._rebuild_table(j)
    ndax_book._table(j)
    for k, (src, _) in enumerate(el.REBUILD_PARTS):
        j.db.execute("INSERT INTO rebuild_log (t, source, match) VALUES (?,?,1)", (NOW - 3600 + k, src))
    j.db.execute("CREATE TABLE universe_rebuilds (t INTEGER PRIMARY KEY, json TEXT)")
    j.db.execute("INSERT INTO universe_rebuilds VALUES (?,?)", (NOW - 3600, json.dumps({"t": NOW - 3600, "match": True})))
    _stream(tmp_path, [NOW - 2 * DAY + 900 * k for k in range(0, 2 * 96 + 1) if not 40 <= k <= 43])
    r = el.reconstructable(j)
    assert r["status"] == "PARTLY" and "15-minute snapshot stream" in r["note"]


def test_the_gate_check_passes_only_when_every_part_is_fresh_and_matching(tmp_path):
    from jarvis.service import evidence_live as el
    from jarvis.service import ndax_book

    j = _j(tmp_path)
    el._rebuild_table(j)
    ndax_book._table(j)
    for k, (src, _) in enumerate(el.REBUILD_PARTS):
        j.db.execute("INSERT INTO rebuild_log (t, source, match) VALUES (?,?,1)", (NOW - 3600 + k, src))
    j.db.execute("CREATE TABLE universe_rebuilds (t INTEGER PRIMARY KEY, json TEXT)")
    j.db.execute("INSERT INTO universe_rebuilds VALUES (?,?)", (NOW - 3600, json.dumps({"t": NOW - 3600, "match": True})))
    j.db.execute("INSERT INTO book500_fills (t, coin, side, px, bid, ask) VALUES (?, 'BTC', 'BUY', 100.0, 99.9, 100.1)", (NOW - 7200,))
    _stream(tmp_path, [NOW - 2 * DAY + 900 * k for k in range(0, 2 * 96 + 1)])
    assert el.reconstructable(j)["status"] == "PASS"
    j.db.execute("INSERT INTO rebuild_log (t, source, match) VALUES (?, 'trades', 0)", (NOW - 60,))
    r = el.reconstructable(j)
    assert r["status"] == "FAIL" and "MISMATCH: every evidence trade" in r["note"]
    j.db.execute("DELETE FROM rebuild_log WHERE source IN ('trades', 'trend30')")
    r = el.reconstructable(j)
    assert r["status"] == "PARTLY" and "not re-checked in the last 2 days" in r["note"]
