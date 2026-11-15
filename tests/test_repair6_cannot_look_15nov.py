"""15 Nov 2026, audit repair 6 (open-list flag 122). G-43: a money check that cannot look said "nothing to report", and that night was
counted clean; a self-check part that raised was filed low, never pushed. G-42 (its calendar part): a night whose candle never came read
the same old candle twice and still counted clean."""
import json
import sqlite3


def _db(path, state='{"cash": 500.0, "pos": {}}'):
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE book500_fills (t INTEGER, coin TEXT, side TEXT, qty REAL, px REAL, fee REAL)")
    con.execute("CREATE TABLE book500 (k TEXT PRIMARY KEY, v TEXT)")
    con.execute("INSERT INTO book500 VALUES ('state', ?)", (state,))
    con.commit()
    con.close()
    return path


def test_the_book_check_says_when_it_cannot_read_the_book(tmp_path):
    from jarvis import selfcheck

    assert selfcheck._book500(_db(tmp_path / "ok.sqlite")) == []                    # a book that agrees: nothing to report
    empty = tmp_path / "empty.sqlite"
    sqlite3.connect(empty).close()
    assert selfcheck._book500(empty) == []                                         # no book in it yet: nothing to check
    broken = _db(tmp_path / "broken.sqlite", state="{not json")
    found = selfcheck._book500(broken)
    assert found and found[0]["severity"] == "high" and "could not read" in found[0]["what"]
    junk = tmp_path / "junk.sqlite"
    junk.write_bytes(b"this is not a database at all" * 50)
    found = selfcheck._book500(junk)
    assert found and found[0]["severity"] == "high" and "could not read the book" in found[0]["what"]


def test_the_india_book_check_says_when_it_cannot_read_the_book(tmp_path):
    from jarvis.india import selfparts

    assert selfparts.managed_book_check(tmp_path) == []                            # no managed book yet
    (tmp_path / "managed").mkdir()
    (tmp_path / "managed" / "state.json").write_text("{cut off")
    found = selfparts.managed_book_check(tmp_path)
    assert found and found[0]["severity"] == "high" and "could not read" in found[0]["what"]


def test_a_part_that_raises_is_said_and_a_money_part_alarms(monkeypatch, tmp_path):
    from jarvis import selfcheck

    def boom(*a, **k):
        raise RuntimeError("cannot look")

    monkeypatch.setattr(selfcheck, "TOLD", tmp_path / "told.json")
    for name in ("_runs", "_services", "_answers", "_leftovers", "_restarts", "_credit", "_mac", "_gates", "_rx_order", "_agree",
                 "_kite_refusals"):
        monkeypatch.setattr(selfcheck, name, lambda *a, **k: [])
    monkeypatch.setattr(selfcheck, "_book500", boom)
    monkeypatch.setattr(selfcheck, "_india_book", boom)
    out = selfcheck.refresh(now=1794700000.0, write=False, push=lambda *a: None)
    items = out.get("items") if isinstance(out, dict) else out
    mine = {x["source"]: x for x in items if x.get("source") in ("book500", "india_book")}
    assert mine["book500"]["severity"] == "high" and mine["india_book"]["severity"] == "high"     # it was "low": never pushed
    assert "not checked" in mine["book500"]["what"]


def test_a_night_that_read_an_old_candle_is_not_clean(tmp_path):
    from jarvis.service import officer

    class J:
        db = sqlite3.connect(tmp_path / "jarvis.sqlite")

    j = J()
    j.db.execute("CREATE TABLE engine_state (k TEXT PRIMARY KEY, v TEXT)")
    ok = officer.mark_clean_night(j, {"day": "2026-11-15", "dial": {"candle": "2026-11-14", "book_stepped_on": "2026-11-14"}})
    assert ok["clean"], ok
    stale = officer.mark_clean_night(j, {"day": "2026-11-16", "dial": {"candle": "2026-11-14", "book_stepped_on": "2026-11-14"}})
    assert not stale["clean"] and "not last night's (2026-11-15)" in stale["why"][0]
    assert json.loads(j.db.execute("SELECT v FROM engine_state WHERE k='clean_night:2026-11-16'").fetchone()[0])["clean"] is False


def test_the_home_gap_notice_says_when_the_holdings_could_not_be_checked(monkeypatch):
    """12 Nov 2026 (G-43, the Home part): Home's book-gap notice read any error as 'no gap'."""
    from jarvis.service import surfaces as S

    def boom(j, b):
        raise OSError("the database is busy")

    monkeypatch.setattr(S, "book_gap", boom)
    assert S.book_gap_checked(None, {}) is None
    assert S.gap_words(None).startswith("The book's holdings could not be checked")
    monkeypatch.setattr(S, "book_gap", lambda j, b: [])
    assert S.book_gap_checked(None, {}) == [] and S.gap_words([]) is None
