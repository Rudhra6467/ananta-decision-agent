"""Audit repair 3 (12 Nov 2026; the keen outside audit's G-24 to G-28, G-35 to G-38, G-63; open-list flag 119): the crypto nightly note
counts the night it describes, waits for the night's last decision, names the evening it was written on, carries later corrections in its
own words, sends the phone whole sentences, and reports the brake record without the two false fires of 28 Oct. Each check failed before."""
import calendar
import json
import sqlite3
import time
import types

import pytest

from jarvis.service import officer

NOV = lambda d, h=0, m=0, s=0: calendar.timegm((2026, 11, d, h, m, s))      # noqa: E731  UTC seconds


def _j(now: int):
    j = types.SimpleNamespace(db=sqlite3.connect(":memory:"), now=lambda: now, dir="/nonexistent")
    from jarvis.service import brain, ndax_book, watch_engine

    ndax_book._table(j)
    watch_engine._table(j)
    brain._table(j)
    j.db.execute("CREATE TABLE IF NOT EXISTS engine_state (k TEXT PRIMARY KEY, v TEXT)")
    officer._table(j)
    return j


def _state(j, **kw):
    from jarvis.service import ndax_book

    ndax_book._put(j, "state", {"started": "2026-10-11", "cash": 467.5, "value": 467.5, "pos": {}, "closed": [], "brakes": {}, **kw})
    j.db.commit()


def _trade(j, rid, watch, signal_t, exit_t=None):
    from jarvis.service import watch_engine as W

    row = {"id": rid, "watch": watch, "coin": "ETH", "source": "rules", "signal_t": signal_t, "signal_day": "x", "entry_t": signal_t,
           "entry_day": "x", "entry": 1.0, "status": "CLOSED" if exit_t else "OPEN", "exit_t": exit_t, "net_usd": 0.0 if exit_t else None}
    j.db.execute(f"INSERT INTO evidence_trades ({', '.join(W.COLS)}) VALUES ({', '.join('?' * len(W.COLS))})", tuple(row.get(c) for c in W.COLS))


# ---- G-25: the night is the candle the book stepped on, not the six minutes since midnight UTC ----

def test_the_night_counts_from_the_candle_the_book_stepped_on():
    j = _j(NOV(12, 0, 6))                                   # the note's time: 00:06 UTC on 12 Nov, 7:06 pm Toronto on 11 Nov
    _state(j, last_bar=NOV(11))                             # the book stepped on the 11 Nov candle at the 12 Nov 00:00 close
    _trade(j, "a", "H07-UA", NOV(11))                       # the step's signals and exits are stamped with the candle's open
    _trade(j, "b", "BRK-UA", NOV(10), exit_t=NOV(11))
    _trade(j, "old", "H07-UA", NOV(10))                     # the night before: not tonight's
    j.db.commit()
    bg = officer.facts(j)["background"]
    assert bg["signals_today_by_rule"] == {"H07-UA": 1}     # it said "no rule fired a signal" on 11 Nov, the night 3 were raised
    assert bg["closed_today_by_rule"]["BRK-UA"] == {"n": 1}  # counted, never summed in money: a breakout's result is held to 15 Dec
    assert "the 2026-11-11 candle" in bg["counted_from"]


def test_nothing_is_counted_on_two_nights_and_a_missed_step_does_not_repeat_a_night():
    """The outside check of 12 Nov: counted from the candle's open to the note, the step's own minutes (the bold book's 00:09 buy, brain
    decisions just after the close) were counted again the next night; and with the book's step missed, two candles were counted."""
    from jarvis.service import brain

    j = _j(NOV(12, 0, 20))
    _state(j, last_bar=NOV(10))                             # the book's step was missed: its last bar is a day older
    j.db.execute("INSERT INTO officer_notes VALUES ('2026-11-11', ?, 'x', '{}', 0)", (NOV(11, 0, 20),))
    _trade(j, "a", "H07-UA", NOV(11))                       # the 11 Nov candle's signal
    _trade(j, "old", "H07-UA", NOV(10))                     # the 10 Nov candle's: counted on the night before
    _trade(j, "bold", "JARVIS_BOLD", NOV(12, 0, 9, 42))     # the bold book's buy just after the close: this night
    _trade(j, "bold0", "JARVIS_BOLD", NOV(11, 0, 9))        # last night's, before the last note: not again
    j.db.executemany("INSERT INTO brain_decisions (t, coin, action) VALUES (?, 'ETH', ?)",
                     [(NOV(11, 0, 15), "PASS"), (NOV(11, 14), "PASS"), (NOV(12, 0, 10), "TAKE")])
    j.db.commit()
    bg = officer.facts(j)["background"]
    assert bg["signals_today_by_rule"] == {"H07-UA": 1, "JARVIS_BOLD": 1}, bg["signals_today_by_rule"]
    assert bg["brain_today"] == {"PASS": 1, "TAKE": 1}      # the decision at 00:15 on 11 Nov was the night before's
    j2 = _j(NOV(13, 0, 20))                                 # the next night: the 12 Nov note was written at 00:20
    brain._table(j2)
    _state(j2, last_bar=NOV(12))
    j2.db.execute("INSERT INTO officer_notes VALUES ('2026-11-12', ?, 'x', '{}', 0)", (NOV(12, 0, 20),))
    _trade(j2, "bold", "JARVIS_BOLD", NOV(12, 0, 9, 42))
    j2.db.execute("INSERT INTO brain_decisions (t, coin, action) VALUES (?, 'ETH', 'TAKE')", (NOV(12, 0, 10),))
    j2.db.commit()
    bg2 = officer.facts(j2)["background"]
    assert bg2["signals_today_by_rule"] == {} and bg2["brain_today"] == {}   # counted once, on the night it happened


def test_no_money_of_a_measuring_book_reaches_the_note_before_the_forward_test_ends():
    from jarvis.service import learning, shadow

    assert officer.HELD_UNTIL == shadow.SEALED_UNTIL == learning.SEALED_UNTIL_T       # one moment: 15 Dec 00:00 UTC
    for now, held in ((NOV(12, 0, 6), True), (calendar.timegm((2026, 12, 15, 0, 6, 0)), False)):
        j = _j(now)
        _state(j, last_bar=now - now % 86400 - 86400)
        _trade(j, "b", "BRK-UA", now - now % 86400 - 2 * 86400, exit_t=now - now % 86400 - 86400)
        day = time.strftime("%Y-%m-%d", time.gmtime(now))
        j.db.execute("INSERT INTO engine_state VALUES (?, ?)", ("late_closes:" + day, json.dumps({"n": 2, "books": {"BRK": 1, "H07": 1}, "net_usd": -3.5})))
        j.db.commit()
        bg = officer.facts(j)["background"]
        assert ("net_usd" in bg["closed_today_by_rule"]["BRK-UA"]) is not held
        assert ("net_usd" in bg["old_paper_trades_closed_late_tonight"]) is not held and bg["old_paper_trades_closed_late_tonight"]["n"] == 2
        assert ("closed_counts_only" in bg) is held
    assert "only when the facts\ngive it (before 15 Dec they never do" in officer.NOTE_RULES


# ---- G-26: the note waits for the night's last decision ----

def _ready(j, t):
    j.db.execute("INSERT OR REPLACE INTO engine_state VALUES (?,?)", ("officer_daily:2026-11-12", json.dumps({"t": t, "book500": {}})))
    j.db.commit()


def _model(seen):
    def call(rules, user):
        seen.append(user)
        return "The book stayed in cash. Nothing needs you.", {"in": 1, "out": 1}
    return call


def test_the_note_waits_for_the_brains_moments_and_the_bold_book_then_says_what_was_still_to_come(monkeypatch):
    from jarvis.service import bold, brain

    monkeypatch.setattr(brain, "_price", lambda usage: 0.0)
    monkeypatch.setattr(bold, "enabled", lambda: (True, ""))
    j = _j(NOV(12, 0, 15))
    _state(j, last_bar=NOV(11))
    assert officer.write_when_due(j, call=_model([])) is None                         # the nightly step has not run: nothing yet
    _ready(j, NOV(12, 0, 5))
    j.db.execute("INSERT INTO brain_queue VALUES ('q1', ?, 'ZEC', 'setup:H07', '{}', 'NEW')", (NOV(12, 0, 2),))
    j.db.commit()
    out = officer.write_when_due(j, call=_model([]))
    assert out["waiting"] == ["the bold measuring book had not decided yet", "1 moment the brain had not decided yet"]
    assert not j.db.execute("SELECT 1 FROM officer_notes").fetchone()                 # 11 Nov: the note went out 3.5 minutes before ZEC was bought
    j.db.execute("UPDATE brain_queue SET state='DONE'")
    bold._table(j)
    j.db.execute("INSERT INTO bold_decisions (id, day) VALUES ('d1', '2026-11-12')")
    j.db.commit()
    seen = []
    assert officer.write_when_due(j, call=_model(seen))["ok"] is True
    assert j.db.execute("SELECT COUNT(*) FROM officer_notes WHERE day='2026-11-12'").fetchone()[0] == 1
    assert officer.write_when_due(j, call=_model(seen)) is None                       # once a night
    # a night where something never comes: after NOTE_WAITS_S the note is written and names what was still waiting
    j2 = _j(NOV(12, 0, 5) + officer.NOTE_WAITS_S + 60)
    _state(j2, last_bar=NOV(11))
    _ready(j2, NOV(12, 0, 5))
    j2.db.execute("INSERT INTO brain_queue VALUES ('q2', ?, 'ZEC', 'setup:H07', '{}', 'NEW')", (NOV(12, 0, 2),))
    j2.db.commit()
    seen2 = []
    assert officer.write_when_due(j2, call=_model(seen2))["ok"] is True
    assert "still_waiting_when_written" in seen2[0] and "1 moment the brain had not decided yet" in seen2[0]


def test_the_nightly_step_leaves_the_note_to_the_loop_that_runs_after_the_bold_book():
    import inspect

    from jarvis.service import app, universe_watch

    daily = inspect.getsource(universe_watch.run_daily)
    assert "officer.night_ready(j, out)" in daily and "officer.write(" not in daily and "start_night_test(j)" not in daily
    jobs = inspect.getsource(app.background_jobs)
    assert jobs.index("bold.run(J())") < jobs.index("officer.write_when_due(J()")      # the bold book's step first, then the note


# ---- G-63: whole sentences to the phone, and the body kept ----

def test_the_phone_gets_whole_sentences_and_the_log_keeps_what_was_sent(monkeypatch):
    from jarvis.service import brain

    long = ("The book stayed all cash because the dial is closed and Bitcoin is under its 200-day average. An old ETH sale was recorded "
            "late, so its value was put right tonight. Nothing needs you, sir, and the checks all pass except the idle-cash one.")
    assert officer.phone_text(long) == ("The book stayed all cash because the dial is closed and Bitcoin is under its 200-day average. An "
                                        "old ETH sale was recorded late, so its value was put right tonight.")
    assert not officer.phone_text("x" * 30 + " " + "word " * 60).endswith(("wor", "wo"))       # never a cut word
    monkeypatch.setattr(brain, "_price", lambda usage: 0.0)
    j = _j(NOV(12, 0, 6))
    _state(j, last_bar=NOV(11))
    sent = []
    officer.write(j, {}, push=lambda title, body: sent.append(body) or "sent", call=lambda r, u: (long, {"in": 1, "out": 1}))
    kept = json.loads(j.db.execute("SELECT v FROM engine_state WHERE k='officer_push:2026-11-12'").fetchone()[0])
    assert sent == [kept["body"]] and kept["body"].endswith("tonight.") and kept["result"] == "sent"


# ---- G-28: a nightly record is named by the Toronto evening it was written on ----

def test_a_note_and_a_fill_are_named_by_the_toronto_evening():
    from jarvis.service import places, surfaces

    j = _j(NOV(12, 0, 6))
    j.db.execute("INSERT INTO officer_notes VALUES ('2026-11-11', ?, 'The book stayed in cash.', '{}', 0)", (NOV(11, 0, 5),))
    j.db.commit()
    n = officer.latest(j, 1)[0]
    assert n["evening"] == "Tue 10 Nov"                                                 # it was 'Wed 11 Nov' on Home
    assert surfaces._officer_note(j)["evening"] == "Tue 10 Nov"
    assert places._day(NOV(6, 0, 6, 30)) == "2026-11-05"                               # a fill on Thursday evening was 'Fri 6 Nov'
    cl = {"coin": "BTC", "out": "2026-11-06"}
    assert places._sold_day(cl, [{"t": NOV(6, 0, 6, 30), "side": "SELL", "coin": "BTC"}]) == "2026-11-05"
    assert places._sold_day(cl, []) == "2026-11-05"                                     # the step ran just after the UTC close


def test_the_app_names_a_crypto_daily_candle_by_its_own_day():
    from pathlib import Path

    src = (Path(__file__).resolve().parents[1] / "jarvis" / "app" / "src" / "place.tsx").read_text()
    assert "!intraday && t % 86400 === 0 ? 0 : tz * 60" in src                         # the 10 Nov candle was named Mon 9 Nov


# ---- G-27: one day of the evidence window, on the Toronto date ----

def test_the_evidence_window_has_one_day_everywhere(monkeypatch):
    import datetime as dt

    from jarvis.service import ask, knowledge_build, strategy_status, surfaces

    monkeypatch.setattr(strategy_status, "load", lambda *a, **k: {"evidence_window": {"start": "2026-10-15", "days": 60}})
    j = _j(NOV(12, 0, 6))                                                               # 7:06 pm Toronto, Wed 11 Nov
    w = knowledge_build.window(j)
    assert w["day"] == 28                                                               # the note said 29 that evening
    assert surfaces._window(dt.date(2026, 11, 11))["day"] == 28                         # the screens said 28
    assert "day 28 of 60" in ask._window_words(j)                                       # the Ask said 27, counting back from checkpoints


# ---- G-24, G-36, G-37, G-38: a stored note carries what was corrected later, in its own words ----

def test_a_stored_note_carries_its_later_corrections_everywhere_it_is_shown():
    j = _j(NOV(12, 0, 6))
    late = {"n": 41, "books": {"H07": 20, "RANDOM_10D": 10, "RBD": 5, "RANDOM_20D": 4, "BRK": 1, "RANDOM_30D": 1}}
    facts = {"background": {"old_paper_trades_closed_late_tonight": late}, "account": {"value_cad": 439.49}, "dial": {}}
    j.db.execute("INSERT INTO officer_notes VALUES ('2026-11-10', ?, ?, ?, 0)", (NOV(10, 0, 5), "One check fails: idle cash, since the book is all "
                 "cash against a 70% target and has been for 16 days. 41 old paper trades were closed late.", json.dumps(facts)))
    j.db.execute("INSERT INTO engine_state VALUES ('late_closes:2026-11-10', ?)",
                 (json.dumps({"n": 50, "books": {**late["books"], "ZONE_TOUCH": 9}, "corrected": True}),))
    j.db.execute("CREATE TABLE book500_night_fixes (day TEXT, add_cad REAL, in_coins INTEGER, why TEXT, t INTEGER, by TEXT)")
    j.db.execute("INSERT INTO book500_night_fixes VALUES ('2026-11-10', 28.06, 0, 'the ETH sale recorded late', 0, 'x')")
    j.db.executemany("INSERT INTO book500_fills (t, coin, side, qty) VALUES (?,?,?,?)",
                     [(NOV(1, 0, 5), "BTC", "BUY", 0.001), (NOV(6, 0, 6, 30), "BTC", "SELL", 0.001)])
    j.db.commit()
    n = officer.latest(j, 1)[0]
    fx = n["corrections"]
    assert any("50 old paper trades" in x and "not 41" in x and "9 of zone touch" in x for x in fx), fx          # G-24
    assert any("C$467.55 that night, not the C$439.49" in x for x in fx), fx                                      # G-37
    assert any("before 11 Nov" in x for x in fx), fx                                                              # G-36
    assert any("held coins until the evening of Thu 5 Nov" in x and "for 4 days" in x and "not 16" in x for x in fx), fx   # G-38
    assert n["as_written"].endswith("closed late.") and n["note"].startswith(n["as_written"]) and n["note"].endswith(fx[-1])
    from jarvis.service import places

    rows = places.note_rows(j, {"b": {}})                                               # Activity and Notices read the same words
    assert rows and rows[0][0] == "2026-11-09"


def test_a_note_with_nothing_corrected_is_left_as_written():
    j = _j(NOV(12, 0, 6))
    facts = {"account": {"value_cad": 467.5}, "dial": {"candle": "2026-11-11", "book_stepped_on": "2026-11-11"}}
    j.db.execute("INSERT INTO officer_notes VALUES ('2026-11-12', ?, 'The book stayed in cash.', ?, 0)", (NOV(12, 0, 6), json.dumps(facts)))
    j.db.commit()
    n = officer.latest(j, 1)[0]
    assert n["corrections"] == [] and n["note"] == "The book stayed in cash."


# ---- G-35: the brake record without the two false fires of 28 Oct ----

REPAIR = {"day": "2026-11-10", "what": ("the 26 Oct ETH trade's sale recorded at the 5 Nov step; the holding left the book on 28 Oct when the "
                                        "core bought ETH, so the value read C$27 too low from then to 10 Nov, and the day-loss and week-loss "
                                        "brakes of 28 Oct fired on that false fall, not on a real loss")}


def test_the_brake_record_counts_real_losses_only_and_marks_the_false_fires():
    log = [{"day": "2026-10-22", "brake": "day_loss"}, {"day": "2026-10-28", "brake": "day_loss"}, {"day": "2026-10-28", "brake": "week_loss"}]
    b = officer.brake_record({"fired": {"day_loss": 2, "week_loss": 1}, "log": log}, [REPAIR])
    assert b["fired"] == {"day_loss": 1, "week_loss": 0} and b["fired_as_recorded"] == {"day_loss": 2, "week_loss": 1}
    assert [bool(x.get("false_fall")) for x in b["log"]] == [False, True, True]
    assert officer.brake_record({"fired": {"day_loss": 2}, "log": log}, [])["fired"] == {"day_loss": 2}     # no repair note: as recorded
    j = _j(calendar.timegm((2026, 10, 29, 0, 6, 0)))                                    # the note of the 28 Oct close
    _state(j, last_bar=calendar.timegm((2026, 10, 28, 0, 0, 0)), brakes={"fired": {"day_loss": 2, "week_loss": 1}, "log": log}, repairs=[REPAIR])
    f = officer.facts(j)
    assert f["account"]["brakes"]["fired"] == {"day_loss": 1, "week_loss": 0}
    assert f["account"]["brakes_today"].startswith("none fired at this close")


def test_the_ask_reads_the_same_brake_record(monkeypatch):
    from jarvis.service import ask, ndax_book

    log = [{"day": "2026-10-28", "brake": "week_loss"}]
    monkeypatch.setattr(ndax_book, "status", lambda j: {"brakes": {"fired": {"week_loss": 1}}, "brake_log": log, "repairs": [REPAIR]})
    st = ask._book_status(None)
    assert st["brakes"]["fired"] == {"week_loss": 0} and st["brake_log"][0]["false_fall"]


def test_every_reader_of_the_book_reports_the_same_brake_record(monkeypatch):
    """The app's /v3/book500, the books list and the summary read the book through officer.book_status; the two other readers of the
    book's raw status report no brakes (the exam grades the value, cash and return; the night test's truth has no brakes)."""
    import ast
    from pathlib import Path

    from jarvis.service import ndax_book

    log = [{"day": "2026-10-28", "brake": "week_loss"}]
    monkeypatch.setattr(ndax_book, "status", lambda j: {"started": "2026-10-11", "brakes": {"fired": {"week_loss": 1}}, "brake_log": log,
                                                        "repairs": [REPAIR]})
    st = officer.book_status(None)
    assert st["brakes"]["fired"] == {"week_loss": 0} and st["brakes"]["fired_as_recorded"] == {"week_loss": 1} and st["brake_log"][0]["false_fall"]
    monkeypatch.setattr(ndax_book, "status", lambda j: {"started": False, "note": "the book starts at the next daily close"})
    assert officer.book_status(None) == {"started": False, "note": "the book starts at the next daily close"}
    root = Path(__file__).resolve().parents[1] / "jarvis"
    raw = set()
    for p in sorted(root.rglob("*.py")):
        if "node_modules" in p.parts:
            continue
        src = p.read_text(errors="ignore")
        if "ndax_book" not in src:
            continue
        for fn in (n for n in ast.walk(ast.parse(src)) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))):
            for n in ast.walk(fn):
                if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "status"
                        and isinstance(n.func.value, ast.Name) and n.func.value.id == "ndax_book"):
                    raw.add(f"{p.relative_to(root).as_posix()}:{fn.name}")
    assert raw == {"service/officer.py:book_status", "service/officer.py:facts", "service/exam.py:numbers", "service/nightcheck.py:truth"}, raw
    for f in ("service/exam.py", "service/nightcheck.py"):
        assert "brake_log" not in (root / f).read_text() and '"brakes"' not in (root / f).read_text()


# ---- G-38 at its source: the idle-cash check says what its days count ----

def test_the_idle_cash_check_says_how_long_cash_was_over_its_target_and_since_when_it_was_all_cash(monkeypatch):
    from jarvis.service import discipline, ndax_book

    j = _j(NOV(10, 0, 6))
    _state(j, cash=467.5, value=467.5, core_plan={"state": "OPEN", "cash_target": 0.7}, cash_over_target_since=NOV(10, 0, 6) - 16 * 86400)
    j.db.executemany("INSERT INTO book500_fills (t, coin, side, qty) VALUES (?,?,?,?)",
                     [(NOV(1, 0, 5), "BTC", "BUY", 0.001), (NOV(6, 0, 6, 30), "BTC", "SELL", 0.001)])
    j.db.commit()
    monkeypatch.setattr(ndax_book, "passed_rules", lambda j, x: ["H07"])
    words = next(c["words"] for c in discipline.officer_checks(j) if c["id"] == "idle_cash")
    assert "over its target for 16 days" in words and "all cash since the evening of Thu 5 Nov" in words, words


@pytest.mark.parametrize("note, said", [("cash is 100% of the book against a 70% target, and has been for 12 days.", 12),
                                        ("The book is all cash. It has been that way for 13 days, but the stance wins.", 13)])
def test_the_ways_the_notes_said_all_cash_are_read(note, said):
    j = _j(NOV(12, 0, 6))
    j.db.executemany("INSERT INTO book500_fills (t, coin, side, qty) VALUES (?,?,?,?)",
                     [(NOV(1, 0, 5), "BTC", "BUY", 0.001), (NOV(6, 0, 6, 30), "BTC", "SELL", 0.001)])
    j.db.commit()
    fx = officer.corrections(j, "2026-11-08", note, {}, NOV(8, 0, 5))
    assert any(f"not {said}" in x for x in fx), fx


# ---- G-37 everywhere: every reader of a night's figures gets the repaired night ----

def _nights(j):
    for day, v, c in (("2026-11-09", 439.49, 0.25), ("2026-11-10", 439.49, 467.5)):
        j.db.execute("INSERT INTO officer_notes VALUES (?, ?, 'x', ?, 0)", (day, 0, json.dumps({"account": {"value_cad": v, "cash_cad": c}})))
    j.db.execute("CREATE TABLE book500_night_fixes (day TEXT, add_cad REAL, in_coins INTEGER, why TEXT, t INTEGER, by TEXT)")
    j.db.executemany("INSERT INTO book500_night_fixes VALUES (?, ?, ?, 'w', 0, 'x')", [("2026-11-09", 27.36, 1), ("2026-11-10", 28.06, 0)])
    j.db.commit()


def test_the_home_box_charts_draw_the_repaired_nights(monkeypatch):
    from jarvis.service import places, surfaces

    import datetime as dt

    j = _j(NOV(12, 0, 6))
    _nights(j)
    monkeypatch.setattr(places, "_ctx", lambda j: {"b": {"started": "2026-10-11"}, "now": dt.datetime(2026, 11, 12, 9, tzinfo=surfaces.TOR)})
    monkeypatch.setattr(surfaces, "_start_cad", lambda: 500.0)
    got = dict(places.book_points(j, "ACCOUNT"))
    assert got["2026-11-08"] == 466.85 and got["2026-11-09"] == 467.55, got              # they drew 439.49 on both nights
    assert dict(places.book_points(j, "COINS"))["2026-11-08"] == 466.6                   # the coins the ETH sale had left out
    assert surfaces.night_book(j) == {"2026-11-09": {"value_cad": 466.85, "cash_cad": 0.25, "add_cad": 27.36},
                                      "2026-11-10": {"value_cad": 467.55, "cash_cad": 495.56, "add_cad": 28.06}}


def test_no_other_code_reads_a_nights_figures_from_the_notes():
    """The check G-37 asked for: a new reader of the nights' value or cash outside surfaces.night_book would read the low nights."""
    import ast
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "jarvis"
    allowed = {("service/surfaces.py", "night_book"), ("selfcheck.py", "_book500")}       # the self-check applies the repair table itself
    funcs = (ast.FunctionDef, ast.AsyncFunctionDef)

    def own_strings(fn):                     # the function's own text constants: not its docstring, not a function inside it
        doc = fn.body[0] if fn.body and isinstance(fn.body[0], ast.Expr) and isinstance(getattr(fn.body[0], "value", None), ast.Constant) else None
        stack, out = [c for c in ast.iter_child_nodes(fn) if c is not doc], []
        while stack:
            n = stack.pop()
            if isinstance(n, funcs):
                continue
            if isinstance(n, ast.Constant) and isinstance(n.value, str):
                out.append(n.value)
            stack.extend(ast.iter_child_nodes(n))
        return out

    found, readers = [], []
    for p in sorted(root.rglob("*.py")):
        rel = p.relative_to(root).as_posix()
        if rel == "service/officer.py" or "node_modules" in p.parts:                       # the writer, and its corrections in words
            continue
        src = p.read_text(errors="ignore")
        if "officer_notes" not in src:
            continue
        for fn in (n for n in ast.walk(ast.parse(src)) if isinstance(n, funcs)):
            s = own_strings(fn)
            if any("from officer_notes" in x.lower() for x in s) and any(x in ("value_cad", "cash_cad") for x in s):
                readers.append((rel, fn.name))
                if (rel, fn.name) not in allowed:
                    found.append(f"{rel}:{fn.name}")
    assert not found, found
    assert ("service/surfaces.py", "night_book") in readers                               # the scan sees a reader when there is one
    assert "book500_night_fixes" in (root / "selfcheck.py").read_text()


# ---- G-27 at the checkpoints: each says which day of the window it falls on ----

def test_each_checkpoint_says_which_day_of_the_window_it_is():
    import datetime as dt
    import re
    from pathlib import Path

    from jarvis.service import knowledge_build

    docs = Path(__file__).resolve().parents[1] / "docs" / "knowledge"
    start = dt.date.fromisoformat(json.loads((docs / "strategy_status.json").read_text())["evidence_window"]["start"])
    seen = 0
    for it in json.loads((docs / "due_list.json").read_text())["items"]:
        m = re.fullmatch(r"CHECKPOINT-(\d+)", it["id"])
        if not m:
            continue
        n, due = int(m.group(1)), dt.date.fromisoformat(it["due"])
        day_n = start + dt.timedelta(days=n - 1)
        j = types.SimpleNamespace(db=sqlite3.connect(":memory:"), now=lambda: calendar.timegm((due.year, due.month, due.day, 17, 0, 0)))
        w = knowledge_build.window(j)                                                      # the check reads N whole days: it is the day after
        assert (w["day"], bool(w.get("ended"))) == ((n + 1, False) if n + 1 <= w["of"] else (w["of"], True)), w
        said = it["plain"]
        assert f"day {n}" in said.lower() and f"{day_n:%a} {day_n.day} {day_n:%b}" in said, said
        assert (f"day {n + 1}" in said) if n + 1 <= w["of"] else ("the last" in said and f"day {n + 1}" not in said), said
        seen += 1
    assert seen == 2                                                                       # 'Day 30' on 14 Nov was day 31 by the screens


# ---- what the fresh outside check of 12 Nov found (recheck/pkg3_check.md) ----

def test_the_phone_text_never_passes_its_limit():
    note = ("The book stayed in cash tonight because the dial is closed. " * 3 + "x" * 5)[:221] + ". And more words follow here."
    assert len(officer.phone_text(note)) <= officer.PHONE_CHARS                          # one came out at 221


def test_a_trades_own_page_names_the_toronto_evening_like_its_row():
    from jarvis.service import places

    cl = {"coin": "ETH", "in": "2026-10-27", "out": "2026-11-06", "pnl_cad": -1.0, "why": "the dial closed"}
    fills = [{"t": NOV(6, 0, 6, 30), "side": "SELL", "coin": "ETH", "qty": 0.01, "px": 4900.0, "fee": 0.1}]
    page = places.receipt(cl, fills)
    hero = next(p for p in page["parts"] if p.get("t") == "hero")
    assert "Thu 5 Nov" in hero["label"] and "Fri 6 Nov" not in str(page)                 # Activity said Thu 5 Nov, the page Fri 6 Nov


def test_the_bleeding_book_check_neither_sums_nor_judges_the_held_books_before_15_dec():
    from jarvis.service import discipline

    for now, held in ((NOV(12, 0, 6), True), (calendar.timegm((2026, 12, 16, 0, 6, 0)), False)):
        j = _j(now)
        _state(j)
        for i in range(6):
            _trade(j, f"b{i}", "BRK-UA", now - 3 * 86400, exit_t=now - 2 * 86400)
            j.db.execute("UPDATE evidence_trades SET net_usd=-20 WHERE id=?", (f"b{i}",))
        j.db.commit()
        c = next(x for x in discipline.officer_checks(j) if x["id"] == "book_bleed")
        assert ("BRK" in c["words"]) is not held and all(b["book"] != "BRK" for b in c.get("books") or []) is held


def test_every_note_before_the_dial_fix_says_its_dial_may_be_a_day_behind():
    j = _j(NOV(12, 0, 6))
    fx = officer.corrections(j, "2026-10-26", "The dial is open.", {"dial": {}}, calendar.timegm((2026, 10, 26, 0, 5, 0)))
    assert any("a day behind" in x for x in fx) and not any("12 of the 14" in x for x in fx)


def test_over_two_weeks_of_all_cash_is_read_and_corrected():
    j = _j(NOV(12, 0, 6))
    j.db.executemany("INSERT INTO book500_fills (t, coin, side, qty) VALUES (?,?,?,?)",
                     [(NOV(1, 0, 5), "BTC", "BUY", 0.001), (NOV(6, 0, 6, 30), "BTC", "SELL", 0.001)])
    j.db.commit()
    fx = officer.corrections(j, "2026-11-09", "The book is all cash and has been for over two weeks.", {}, NOV(9, 0, 5))
    assert any("not over two weeks" in x and "for 3 days" in x for x in fx), fx


def test_a_late_close_correction_says_no_money():
    j = _j(NOV(12, 0, 6))
    j.db.execute("INSERT INTO engine_state VALUES ('late_closes:2026-11-11', ?)", (json.dumps({"n": 50, "books": {"H07": 50}}),))
    j.db.commit()
    fx = officer.corrections(j, "2026-11-11", "x", {"background": {"old_paper_trades_closed_late_tonight": {"n": 41, "books": {"H07": 41}}}})
    assert fx and "dollar" not in fx[0] and "50 old paper trades" in fx[0]          # this note gave no figure: none is mentioned
    fx = officer.corrections(j, "2026-11-11", "x", {"background": {"old_paper_trades_closed_late_tonight": {"n": 41, "books": {"H07": 41},
                                                                                                          "net_usd": -1.0}}})
    assert "out of its dollar figure too" in fx[0] and "$" not in fx[0] and "1.0" not in fx[0]   # the 11 Nov note gave one: said, never summed


def test_the_note_waits_for_a_moment_being_decided_not_for_a_blocked_bold_book_and_stops_after_three_tries(monkeypatch):
    from jarvis.service import bold
    from jarvis.service import trade_guard as tg

    j = _j(NOV(12, 0, 6))
    j.db.execute("CREATE TABLE IF NOT EXISTS brain_queue (id INTEGER PRIMARY KEY, t INTEGER, coin TEXT, trigger TEXT, detail TEXT, state TEXT)")
    j.db.execute("INSERT INTO brain_queue (t, coin, state) VALUES (?, 'ETH', 'DECIDING')", (NOV(12, 0, 5),))
    j.db.commit()
    monkeypatch.setattr(bold, "enabled", lambda: (True, "on"))
    monkeypatch.setattr(tg, "blocked", lambda j, watch, *a, **k: "the kill switch is on")
    left = officer.waiting_for(j, "2026-11-12", NOV(12))
    assert left == ["1 moment the brain had not decided yet"]                           # deciding counts; a blocked bold book does not
    _ready(j, NOV(11, 23))                                                               # the step ran long ago: no more waiting
    j.db.execute("UPDATE brain_queue SET state='DONE'")
    j.db.commit()
    calls = []
    monkeypatch.setattr("jarvis.service.universe_watch.start_night_test", lambda j: calls.append(1) or True)
    for _ in range(5):
        officer.write_when_due(j, call=lambda r, u: (_ for _ in ()).throw(RuntimeError("model down")))
    tries = json.loads(j.db.execute("SELECT v FROM engine_state WHERE k='officer_tries:2026-11-12'").fetchone()[0])
    assert tries["n"] == 3 and calls == [1]                                              # three tries, then the night test once


def test_after_the_window_the_note_and_the_ask_stop_at_its_last_day_like_the_screens(monkeypatch):
    import datetime as dt

    from jarvis.service import ask, knowledge_build, strategy_status, surfaces

    monkeypatch.setattr(strategy_status, "load", lambda *a, **k: {"evidence_window": {"start": "2026-10-15", "days": 60}})
    j = _j(calendar.timegm((2026, 12, 15, 17, 0, 0)))
    w = knowledge_build.window(j)
    assert w["day"] == 60 and w["ended"] and surfaces._window(dt.date(2026, 12, 15))["day"] == 60
    assert "day 60 of 60 (it has ended)" in ask._window_words(j)


# ---- what the confirm check of 12 Nov found (recheck/pkg3_confirm.md) ----

def test_the_account_lists_closed_trades_by_the_toronto_evenings_like_the_page_they_open():
    from pathlib import Path

    src = (Path(__file__).resolve().parents[1] / "jarvis" / "service" / "places.py").read_text()
    assert "S._dm(_sold_day(cl, fills, 'BUY'))} to {S._dm(_sold_day(cl, fills))}" in src        # it said S._dm(cl['in']) to S._dm(cl['out'])
    assert "S._dm(cl.get('in'))} to {S._dm(cl.get('out'))}" not in src


def test_a_failure_raised_after_the_paid_call_counts_as_a_try_too(monkeypatch):
    j = _j(NOV(12, 0, 6))
    _ready(j, NOV(11, 23))
    calls = []
    monkeypatch.setattr("jarvis.service.universe_watch.start_night_test", lambda j: calls.append(1) or True)
    monkeypatch.setattr(officer, "write", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("saving the note failed")))
    for _ in range(5):
        officer.write_when_due(j)
    tries = json.loads(j.db.execute("SELECT v FROM engine_state WHERE k='officer_tries:2026-11-12'").fetchone()[0])
    assert tries["n"] == 3 and "saving the note failed" in tries["error"] and calls == [1]


def test_the_minutes_of_the_model_call_fall_on_the_next_night_not_on_none():
    j = _j(NOV(13, 0, 20))
    _state(j, last_bar=NOV(12))
    facts = {"background": {"counted_to": NOV(12, 0, 6)}}                                # counted at 00:06, saved at 00:07
    j.db.execute("INSERT INTO officer_notes VALUES ('2026-11-12', ?, 'x', ?, 0)", (NOV(12, 0, 7), json.dumps(facts)))
    j.db.execute("INSERT INTO brain_decisions (t, coin, action) VALUES (?, 'ETH', 'PASS')", (NOV(12, 0, 6, 30),))
    j.db.commit()
    assert officer.facts(j)["background"]["brain_today"] == {"PASS": 1}
    assert officer.night_window(j)[2] == NOV(12, 0, 6)


# ---- the second confirm check of 12 Nov (recheck/pkg3_confirm2.md) ----

def test_a_try_cut_short_still_starts_the_night_test(monkeypatch):
    """S4: the service stopping during the third try (a restart, the Mac asleep or off) left the tries used up, no note and no night
    test, and every later loop returned at once."""
    j = _j(NOV(12, 3))
    _ready(j, NOV(11, 23))
    j.db.execute("INSERT OR REPLACE INTO engine_state VALUES (?,?)", ("officer_tries:2026-11-12", json.dumps({"n": 3, "t": NOV(12, 1)})))
    j.db.commit()
    calls = []

    def start(j):
        calls.append(1)
        j.db.execute("INSERT OR REPLACE INTO engine_state VALUES ('nightcheck_started:2026-11-12', '1')")
        return True

    monkeypatch.setattr("jarvis.service.universe_watch.start_night_test", start)
    out = officer.write_when_due(j, call=lambda r, u: pytest.fail("no fourth try of the paid call"))
    assert out["night_test_started"] is True and calls == [1]
    assert officer.write_when_due(j) is None and calls == [1]                            # once: the night test's own stamp is there


def test_a_note_whose_facts_do_not_parse_never_starts_the_night_at_midnight():
    """S5: the facts are saved cut at 20,000 characters; facts that did not parse started the next night at midnight UTC."""
    j = _j(NOV(13, 0, 20))
    _state(j, last_bar=NOV(12))
    cut = json.dumps({"background": {"counted_to": NOV(12, 0, 6)}, "rest": "x" * 50})[:-20]           # cut short: no longer JSON
    j.db.execute("INSERT INTO officer_notes VALUES ('2026-11-12', ?, 'x', ?, 0)", (NOV(12, 0, 7), cut))
    j.db.commit()
    assert officer.night_window(j)[2] == NOV(12, 0, 6)                                   # the moment it counted to, read from the text
    j.db.execute("UPDATE officer_notes SET facts=?", ('{"account": {"x": "' + "y" * 100,))
    j.db.commit()
    assert officer.night_window(j)[2] == NOV(12, 0, 7)                                   # else the note's save time, never 00:00 UTC


def test_the_ask_and_the_note_give_a_closed_trades_toronto_days():
    """A sibling of G-28: the Ask's book tool (officer.book_status) and the note's facts gave only the book's UTC days, unlabelled (the
    Solana trade 'in 2026-10-27, out 2026-11-06', on every screen Mon 26 Oct to Thu 5 Nov)."""
    j = _j(NOV(12, 0, 6))
    sol = {"coin": "SOL", "sleeve": "CORE", "in": "2026-10-27", "out": "2026-11-06", "pnl_cad": 1.0}
    _state(j, last_bar=NOV(11), closed=[sol], brakes={"fired": {}})
    j.db.executemany("INSERT INTO book500_fills (t, coin, side, sleeve, qty, px, bid, ask, fee, why) VALUES (?, 'SOL', ?, 'CORE', 1, 1, 1, 1, 0, 'x')",
                     [(calendar.timegm((2026, 10, 27, 0, 6, 0)), "BUY"), (NOV(6, 0, 6), "SELL")])
    j.db.commit()
    st = officer.book_status(j)
    assert (st["closed"][-1]["bought"], st["closed"][-1]["sold"]) == ("Mon 26 Oct", "Thu 5 Nov") and "UTC" in st["closed_days_note"]
    acct = officer.facts(j)["account"]
    assert (acct["closed_recent"][-1]["bought"], acct["closed_recent"][-1]["sold"]) == ("Mon 26 Oct", "Thu 5 Nov")
    assert "Toronto" in acct["closed_days_note"]


# ---- the third confirm check of 12 Nov (recheck/pkg3_confirm3.md) ----

def test_a_stop_just_after_the_note_still_starts_the_night_test(monkeypatch):
    """S4: the service stopping after the note was saved and before the night test started (the phone note being sent, say) left the
    night with a note and no night test; every later loop saw the note and returned."""
    j = _j(NOV(12, 0, 40))
    _ready(j, NOV(12, 0, 5))
    j.db.execute("INSERT INTO officer_notes VALUES ('2026-11-12', ?, 'The book stayed in cash.', '{}', 0)", (NOV(12, 0, 30),))
    j.db.commit()
    calls = []
    monkeypatch.setattr("jarvis.service.universe_watch.start_night_test", lambda j: calls.append(1) or True)
    assert officer.write_when_due(j)["night_test_started"] is True and calls == [1]
    assert officer.write_when_due(j) is None and calls == [1]                            # once a night


def test_facts_cut_inside_the_moment_never_start_the_night_at_midnight():
    """S5: a cut falling inside the counted_to number read a small number and started the night at midnight UTC."""
    j = _j(NOV(13, 0, 20))
    _state(j, last_bar=NOV(12))
    cut = '{"background": {"counted_to": ' + str(NOV(12, 0, 6))[:5]                       # cut inside the number
    j.db.execute("INSERT INTO officer_notes VALUES ('2026-11-12', ?, 'x', ?, 0)", (NOV(12, 0, 7), cut))
    j.db.commit()
    assert officer.night_window(j)[2] == NOV(12, 0, 7)                                   # the note's save time
