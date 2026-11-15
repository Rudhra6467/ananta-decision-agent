"""15 Nov 2026, audit repair 6 (open-list flag 122): each kind the keen audit named gets its automatic check. G-14 (options scoring far from
the decision), G-22 (a day chart's thin close), G-33 (the night test graded against the same facts as the note), G-44 (fills checked only
against themselves), G-49 (the cost check saw ten coins), G-68 (the morning view's number check fired on every note), G-70 (nobody watched
the Mac's disk), G-73 (live change-book lines with no commit)."""
import datetime as dt
import importlib.util
import json
import sqlite3
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_g14_an_options_trade_scored_far_from_its_decision_is_said(tmp_path):
    from jarvis.india import selfparts

    sp1 = tmp_path / "sp1"
    sp1.mkdir()
    now = time.time()
    at = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(now - 86400)) + "+05:30"
    (sp1 / "decisions.jsonl").write_text("\n".join(json.dumps(x) for x in (
        {"hash": "a", "entry_estimate": 57086.7}, {"hash": "b", "entry_estimate": 25412.3})) + "\n")
    (sp1 / "outcomes.jsonl").write_text("\n".join(json.dumps(x) for x in (
        {"decision_hash": "a", "date": "2026-11-05", "index": "BANKNIFTY", "scored_at": at, "index_proxy": {"entry": 56887.45}},
        {"decision_hash": "b", "date": "2026-11-11", "index": "NIFTY", "scored_at": at, "index_proxy": {"entry": 25413.15}})) + "\n")
    found = selfparts.scoring_and_feed_checks(now=now, paper=tmp_path, manifests=tmp_path)
    assert len(found) == 1 and "1 options trade scored this week" in found[0]["what"] and "199 points apart" in found[0]["what"]


def test_g22_a_day_chart_that_holds_one_price_and_jumps_to_the_close_is_noticed(tmp_path, monkeypatch):
    from jarvis.india import livesession as L
    from jarvis.india import selfparts

    ist = L.IST
    day = dt.datetime(2026, 11, 11, 15, 0, tzinfo=ist)
    rows = [[int((day + dt.timedelta(minutes=m)).timestamp()), 1, 1, 1, 100.0 + m] for m in range(15)]          # 15:00-15:14 moving
    rows += [[int((day + dt.timedelta(minutes=m)).timestamp()), 1, 1, 1, 114.0] for m in range(15, 29)]        # 15:15-15:28 one price
    rows += [[int((day + dt.timedelta(minutes=29)).timestamp()), 1, 1, 1, 131.5]]                               # the official close
    assert L.thin_close(rows) == {"2026-11-11": "15:14"}
    healthy = rows[:15] + [[r[0], 1, 1, 1, 114.0 + i * 0.5] for i, r in enumerate(rows[15:])]
    assert L.thin_close(healthy) == {}
    five = [[int((day + dt.timedelta(minutes=m)).timestamp()), 1, 1, 1, c] for m, c in ((0, 100.0), (5, 101.0), (10, 102.0), (15, 103.5),
                                                                                       (20, 103.5), (25, 109.0))]   # the day charts' 5-minute bars
    assert L.thin_close(five) == {"2026-11-11": "15:15"}                         # the outside check: 8 flat bars could never be met
    assert L.thin_close(five[:4] + [[five[4][0], 1, 1, 1, 104.0], five[5]]) == {}
    f = tmp_path / "thin_close.jsonl"
    L.record_thin_close("NIFTY BANK", "2026-11-11", "15:14", f)
    L.record_thin_close("NIFTY BANK", "2026-11-11", "15:14", f)                                                 # once a day and index
    assert len(f.read_text().splitlines()) == 1
    found = selfparts.scoring_and_feed_checks(paper=tmp_path, manifests=tmp_path)
    assert found and "Bank Nifty day chart of 2026-11-11 held one price from 15:14" in found[0]["what"]


def test_g33_a_note_that_counts_fewer_signals_than_the_candle_is_not_a_clean_night(tmp_path):
    from jarvis.service import officer

    class J:
        db = sqlite3.connect(tmp_path / "jarvis.sqlite")

    j = J()
    j.db.execute("CREATE TABLE engine_state (k TEXT PRIMARY KEY, v TEXT)")
    j.db.execute("CREATE TABLE evidence_trades (watch TEXT, signal_t INTEGER, exit_t INTEGER, status TEXT)")
    c0 = int(dt.datetime(2026, 11, 11, tzinfo=dt.timezone.utc).timestamp())
    j.db.executemany("INSERT INTO evidence_trades VALUES (?,?,?,?)", [("BRK-UA", c0, None, "OPEN"), ("DIP-UB", c0, None, "OPEN"),
                                                                     ("BRK-UB", c0, None, "OPEN"), ("RANDOM_BRK", c0, None, "OPEN"),
                                                                     ("T3-UA", c0 - 9 * 86400, c0, "CLOSED")])
    dial = {"candle": "2026-11-11", "book_stepped_on": "2026-11-11"}
    said = officer.mark_clean_night(j, {"day": "2026-11-12", "dial": dial, "background": {"signals_today_by_rule": {}, "closed_today_by_rule": {}}})
    assert not said["clean"] and any("counted 0 rule signals on the 2026-11-11 candle, which holds 3" in w for w in said["why"])
    assert any("counted 0 closed measuring trades on the 2026-11-11 candle, which holds 1" in w for w in said["why"])
    ok = officer.mark_clean_night(j, {"day": "2026-11-12", "dial": dial, "background": {
        "signals_today_by_rule": {"BRK-UA": 1, "DIP-UB": 1, "BRK-UB": 1}, "closed_today_by_rule": {"T3-UA": {"n": 1}}}})
    assert ok["clean"], ok


def test_g44_a_fill_far_outside_its_candle_is_said(tmp_path):
    from jarvis import selfcheck

    db, bars = tmp_path / "jarvis.sqlite", tmp_path / "universe_bars.sqlite"
    t = int(time.time()) - 3600
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE book500_fills (t INTEGER, coin TEXT, side TEXT, sleeve TEXT, qty REAL, px REAL, bid REAL, ask REAL, fee REAL, why TEXT)")
    con.execute("CREATE TABLE book500 (k TEXT PRIMARY KEY, v TEXT)")
    con.execute("INSERT INTO book500 VALUES ('fx_last', ?)", (json.dumps({"rate": 1.4, "t": t}),))
    con.executemany("INSERT INTO book500_fills VALUES (?,?,?,?,?,?,?,?,?,?)", [(t, "BTC", "BUY", "CORE", 0.001, 141.0, 140.0, 141.0, 0, ""),
                                                                              (t, "ETH", "BUY", "CORE", 0.01, 200.0, 199.0, 200.0, 0, "")])
    con.commit()
    con.close()
    con = sqlite3.connect(bars)
    con.execute("CREATE TABLE m5 (coin TEXT, t INTEGER, o REAL, h REAL, l REAL, c REAL, v REAL, PRIMARY KEY (coin, t))")
    con.executemany("INSERT INTO m5 VALUES (?,?,?,?,?,?,?)", [("BTC", t - 120, 100, 101, 99, 100, 1), ("ETH", t - 120, 100, 101, 99, 100, 1)])
    con.commit()
    con.close()
    found = selfcheck._fills_against_candles(db)
    assert len(found) == 1 and "1 of the $500 book's fills" in found[0]["what"] and "buy ETH" in found[0]["what"]   # BTC at 141 is inside 99-101 x 1.4


def test_g49_the_cost_check_reads_every_ndax_coin(monkeypatch):
    from jarvis import selfcheck
    from jarvis.service import ndax_spreads

    monkeypatch.setattr(ndax_spreads, "summary", lambda days, cost_fn=None: {
        "days_measured": 14, "dearer_than_assumed": ["MOODENG", "XDC", "BTC"],
        "dear_detail": {"MOODENG": [0.86, 0.6], "XDC": [0.69, 0.6], "BTC": [0.12, 0.1]}})
    selfcheck._COSTS.clear()
    found = selfcheck._costs_all_coins()
    assert found and found[0]["what"].startswith("3 NDAX coins cost more a side") and "MOODENG 0.86% against 0.6%" in found[0]["what"]
    monkeypatch.setattr(ndax_spreads, "summary", lambda days, cost_fn=None: {"days_measured": 0})
    assert selfcheck._costs_all_coins() == found                                  # read once in six hours, not every 15 minutes
    selfcheck._COSTS.clear()
    none = selfcheck._costs_all_coins()                                           # no worker day: it says it cannot look
    assert none and none[0].get("cannot_look") and "not checked" in none[0]["what"]
    selfcheck._COSTS.clear()


def test_g68_the_morning_view_number_check_matches_rounded_figures():
    spec = importlib.util.spec_from_file_location("mv", ROOT / "scripts" / "india_morningview.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    facts = {"value_inr": 253346.12, "change_pct": 14.07, "lots": 100, "nifty": 25413.15}
    note = "The account is Rs 2,53,346, up 14.1%. All 100. Nifty 25,413."
    assert m.stray_numbers(note, facts) == []                                   # each of these fired before
    assert m.stray_numbers(note + " It made Rs 9,999 today.", facts) == ["9999"]
    assert m.stray_numbers("VIX up 0.8%, the book 4.5%.", {"vix_pct": 0.83}) == ["4.5"]        # small figures are checked too


def test_g70_the_disk_is_watched_and_a_record_is_kept(tmp_path):
    from jarvis import selfcheck

    f = tmp_path / "mac.jsonl"
    st = {"free_pct": 40, "swap_gb": 1.0, "load5": 2.0}
    assert selfcheck._disk_and_record(st, now=1000.0, path=f, disk=(460e9, 300e9, 160e9)) == []
    low = selfcheck._disk_and_record(st, now=2000.0, path=f, disk=(460e9, 427e9, 33e9))
    assert low[0]["severity"] == "medium" and "33 GB free" in low[0]["what"]
    assert selfcheck._disk_and_record(st, now=3000.0, path=f, disk=(460e9, 440e9, 20e9))[0]["severity"] == "high"
    rows = [json.loads(x) for x in f.read_text().splitlines()]
    assert [r["free_gb"] for r in rows] == [160.0, 33.0, 20.0] and rows[0]["swap_gb"] == 1.0
    selfcheck._disk_and_record(st, now=3000.0 + 8 * 86400, path=f, disk=(460e9, 300e9, 160e9))
    assert len(f.read_text().splitlines()) == 1                                   # seven days kept


def test_g73_a_live_change_book_line_with_no_commit_is_said(tmp_path):
    from jarvis import selfcheck

    f = tmp_path / "changes.jsonl"
    f.write_text("\n".join(json.dumps(x) for x in (
        {"date": "2026-11-10", "status": "live", "commits": [], "words": "older, before the rule"},
        {"date": "2026-11-14", "status": "live", "commits": ["abc1234"], "words": "named"},
        {"date": "2026-11-14", "status": "built", "commits": [], "words": "built, not live"})) + "\n")
    assert selfcheck._changes_name_commits(f) == []
    with f.open("a") as h:
        h.write(json.dumps({"date": "2026-11-15", "status": "live", "commits": [], "words": "A fix with no commit named"}) + "\n")
    found = selfcheck._changes_name_commits(f)
    assert found and found[0]["what"].startswith("1 change-book line set live since 2026-11-12 names no commit")
