"""Execution realism report (20 Oct 2026): fills are judged against the worker's independent NDAX quote, read-only."""
import json
import sqlite3
import time
import calendar

from jarvis.service import realism


def _worker(tmp, day, t, coin, bid, ask, usdcad=1.40):
    f = tmp / f"l1_{day}.sqlite"
    con = sqlite3.connect(f)
    con.execute("CREATE TABLE IF NOT EXISTS ndax (t INTEGER, coin TEXT, bid REAL, ask REAL, last REAL, notional24_cad REAL, ex_ms INTEGER)")
    con.execute("CREATE TABLE IF NOT EXISTS fx (t INTEGER, usdcad REAL, obs_day TEXT)")
    con.execute("INSERT INTO ndax VALUES (?,?,?,?,0,0,0)", (t, coin, bid, ask))
    con.execute("INSERT INTO fx VALUES (?,?,?)", (t - 3600, usdcad, day))
    con.commit()
    con.close()


def _data(tmp, t):
    con = sqlite3.connect(tmp / "jarvis.sqlite")
    con.execute("CREATE TABLE book500_fills (t, coin, side, sleeve, qty, px, bid, ask, fee, why)")
    con.execute("CREATE TABLE evidence_trades (id, watch, coin, source, signal_t, signal_day, entry_t, entry_day, entry, stop, exit_t, exit_day, exit, net_usd, status, why, exit_why, regime, detail)")
    con.execute("INSERT INTO book500_fills VALUES (?,?,?,?,?,?,?,?,?,?)", (t, "BTC", "BUY", "CORE", 0.001, 140000.0, 139800.0, 140000.0, 0.28, "dial open"))
    # a USD book that assumed a 0.284% side cost on ETH while NDAX's real ask is far above its price: optimistic
    con.execute("INSERT INTO evidence_trades (watch, coin, entry_t, entry, exit_t, exit) VALUES (?,?,?,?,?,?)", ("JARVIS", "ETH", t, 4000.0, None, None))
    con.commit()
    con.close()
    con = sqlite3.connect(tmp / "portfolio_book.sqlite")
    con.execute("CREATE TABLE fills (seq INTEGER PRIMARY KEY, t INTEGER, json TEXT)")
    con.execute("INSERT INTO fills (t, json) VALUES (?,?)", (t, json.dumps({"book": "MAIN", "coin": "BTC", "side": "SELL", "usd": 100.0, "px": 99000.0, "cost": 0.4})))
    con.commit()
    con.close()


def test_optimism_sign():
    assert realism.optimism_bps("BUY", 101.0, 99.0, 100.0) < 0              # paid more than ask + fee: realistic
    assert realism.optimism_bps("BUY", 99.0, 99.0, 100.0) > 0               # paid less than NDAX allowed: optimistic
    assert realism.optimism_bps("SELL", 98.0, 99.0, 100.0) < 0
    assert realism.optimism_bps("SELL", 100.0, 99.0, 100.0) > 0


def test_report_judges_each_book_against_the_worker_quote(tmp_path):
    day = "2026-10-15"
    t = calendar.timegm(time.strptime(day, "%Y-%m-%d")) + 3600 * 12
    w = tmp_path / "w"
    w.mkdir()
    d = tmp_path / "d"
    d.mkdir()
    _worker(w, day, t + 30, "BTC", 139800.0, 140000.0)
    _worker(w, day, t + 30, "ETH", 5640.0, 5660.0)                          # ask 5660 CAD = 4042.9 USD at 1.40
    _data(d, t)
    r = realism.report(since="2026-10-12", dest=w, data=d, cost_fn=lambda c: 0.00284)
    b = r["books"]
    assert b["BOOK500"]["realistic"] == 1                                   # it paid the ask plus its fee: exactly achievable
    assert b["JARVIS"]["realistic"] == 0 and b["JARVIS"]["median_optimism_bps"] > 50
    assert b["T3"]["measured"] == 1
    assert r["measured"] == 3 and "of 3 paper fills" in r["line"]


def test_no_quote_is_counted_not_guessed(tmp_path):
    day = "2026-10-15"
    t = calendar.timegm(time.strptime(day, "%Y-%m-%d")) + 3600 * 12
    w = tmp_path / "w"
    w.mkdir()
    d = tmp_path / "d"
    d.mkdir()
    _worker(w, day, t + 900, "BTC", 139800.0, 140000.0)                     # 15 minutes away: too far
    _data(d, t)
    r = realism.report(since="2026-10-12", dest=w, data=d, cost_fn=lambda c: 0.00284)
    assert r["measured"] == 0 and r["books"]["BOOK500"]["no_quote"] == 1


def test_report_never_writes(tmp_path):
    src = open(realism.__file__).read()
    for bad in ("INSERT", "UPDATE ", "DELETE", "CREATE TABLE", ".commit("):
        assert bad not in src, bad
