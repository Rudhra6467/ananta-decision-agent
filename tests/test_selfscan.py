"""Ananta scans itself (6 Nov 2026, Madhav: like it scans the market, it scans itself and tells us when something is off): the parts must
agree. Each check is written from a bug that already happened: wrong order or day; two places disagreeing; a number stuck at zero;
Ananta not seeing its own facts. A HIGH item reaches his phone once a day."""
from __future__ import annotations

import calendar
import json
import os
import sqlite3
import time

from jarvis import selfcheck, selfscan
from jarvis.india import selfparts

NOW = calendar.timegm(time.strptime("2026-11-08 02:00", "%Y-%m-%d %H:%M"))      # 8 Nov 02:00 UTC


def _crypto_db(tmp_path, cards, decisions=(), open_rows=()):
    db = tmp_path / "j.sqlite"
    db.unlink(missing_ok=True)
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE rx_cards (day TEXT PRIMARY KEY, t INTEGER, rules TEXT, card TEXT)")
    con.execute("CREATE TABLE rx_queue (id TEXT PRIMARY KEY, day TEXT, t INTEGER, kind TEXT, lane TEXT, key TEXT, words TEXT, evidence TEXT, state TEXT, decided_t INTEGER, decision TEXT)")
    con.execute("CREATE TABLE brain_decisions (id TEXT, t INTEGER, coin TEXT, action TEXT)")
    for day, card in cards:
        con.execute("INSERT INTO rx_cards VALUES (?,?,?,?)", (day, calendar.timegm(time.strptime(day, "%Y-%m-%d")) + 1800, "rx-cr-v2", json.dumps(card)))
    for i, t in enumerate(decisions):
        con.execute("INSERT INTO brain_decisions VALUES (?,?,?,?)", (f"d{i}", t, "BTC", "PASS"))
    for i, (day, t) in enumerate(open_rows):
        con.execute("INSERT INTO rx_queue VALUES (?,?,?,?,?,?,?,?,?,?,?)", (f"q{i}", day, t, "MISS_PATTERN", "DECISION", f"miss:{i}", "w", "{}", "OPEN", None, None))
    con.commit()
    con.close()
    return db


def test_crypto_scan_sees_the_wrong_day_a_count_mismatch_a_stuck_zero_and_an_old_question(tmp_path, monkeypatch):
    monkeypatch.setenv("ANANTA_SELFCHECK", str(tmp_path / "selfcheck.json"))
    (tmp_path / "selfcheck.json").write_text("{}")
    os.utime(tmp_path / "selfcheck.json", (NOW - 60, NOW - 60))
    good = {"about_day": "2026-11-07", "ananta": {"brain": {"n": 2}}, "value": {}, "wakes": {"n": 0}}
    t0 = calendar.timegm(time.strptime("2026-11-07", "%Y-%m-%d"))
    db = _crypto_db(tmp_path, [("2026-11-08", good)], decisions=(t0 + 10, t0 + 20))
    assert selfscan.crypto(db, now=NOW) == [], "a card about the closed day with matching counts is clean"
    bad = {"about_day": "2026-11-08", "ananta": {"brain": {"n": 0}}}                           # the window bug again, 0 against 2, no value line
    db = _crypto_db(tmp_path, [("2026-11-08", bad), ("2026-11-07", {"about_day": "2026-11-06", "ananta": {"brain": {"n": 0}}, "value": {}, "wakes": {}}),
                               ("2026-11-06", {"about_day": "2026-11-05", "ananta": {"brain": {"n": 0}}, "value": {}, "wakes": {}})],
                     decisions=(t0 + DAY_ + 10, t0 + DAY_ + 20), open_rows=(("2026-10-25", NOW - 14 * 86400),))
    whats = [x["what"] for x in selfscan.crypto(db, now=NOW)]
    assert any("not the day before it" in w for w in whats), whats
    assert any("two places disagree" in w and "counts 0 brain decisions" in w and "holds 2" in w for w in whats), whats
    assert any("stuck at zero" in w for w in whats), whats
    assert any("missing its value line" in w for w in whats), whats
    assert any("waited for Madhav's decision for more than a week" in w for w in whats), whats


DAY_ = 86400


def test_crypto_scan_notices_when_the_self_check_itself_has_stopped(tmp_path, monkeypatch):
    p = tmp_path / "selfcheck.json"
    p.write_text("{}")
    monkeypatch.setenv("ANANTA_SELFCHECK", str(p))
    db = _crypto_db(tmp_path, [])
    items = selfscan.crypto(db, now=p.stat().st_mtime + 2 * 3600)
    assert len(items) == 1 and items[0]["severity"] == "high" and "15-minute loop" in items[0]["what"]


def _india(tmp_path, monkeypatch, cards, newest="2026-11-06", through="2026-11-06", drafts=()):
    data = tmp_path / "india"
    import shutil

    shutil.rmtree(data, ignore_errors=True)
    for d in ("paper/decisions", "paper/reconstruction", "readmodel"):
        (data / d).mkdir(parents=True)
    (data / "paper" / "decisions" / f"{newest}.json").write_text("{}")
    for c in cards:
        (data / "paper" / "reconstruction" / f"{c['day']}.json").write_text(json.dumps(c))
    (data / "readmodel" / "latest.json").write_text(json.dumps({"data_through": through}))
    monkeypatch.setattr(selfparts, "INDIA", data)
    from jarvis.india import views

    monkeypatch.setattr(views, "drafts", lambda: {"drafts": [{"n": i + 1, "key": k, "day": d} for i, (k, d) in enumerate(drafts)]})


def test_india_scan_sees_a_card_behind_the_book_a_disagreeing_headline_a_stale_read_model_and_a_stuck_zero(tmp_path, monkeypatch):
    now = calendar.timegm(time.strptime("2026-11-09 03:00", "%Y-%m-%d %H:%M"))
    monkeypatch.setenv("ANANTA_SELFCHECK", str(tmp_path / "sc.json"))
    card = lambda day, head, movers=25, chosen=3: {"day": day, "headline": head, "market": {}, "not_done": {"summary": {"up": {"movers": movers}}},
                                                   "ananta": {"chosen": [{"symbol": "A"}] * chosen}}
    _india(tmp_path, monkeypatch, [card("2026-11-06", "6 Nov: ... ; nothing waits for you.")], newest="2026-11-06", through="2026-11-06")
    assert selfparts.scan(now=now) == []
    _india(tmp_path, monkeypatch, [card("2026-11-05", "5 Nov: ... ; 1 draft waits for your yes or skip.", movers=0, chosen=0),
                                   card("2026-11-04", "x", movers=0, chosen=0), card("2026-11-03", "x", movers=0, chosen=0), card("2026-11-02", "x", movers=0, chosen=0)],
           newest="2026-11-06", through="2026-11-05", drafts=(("MISS_PATTERN:a", "2026-10-28"), ("CALL_DRIFT:K02", "2026-11-04")))
    items = selfparts.scan(now=now)
    whats = [x["what"] for x in items]
    assert any("the card is a session behind" in w for w in whats), whats
    assert any("says 1 draft wait for Madhav but the queue holds 2" in w for w in whats), whats
    assert any("stuck at zero" in w and "movers" in w for w in whats) and any("stuck at zero" in w and "picks" in w for w in whats), whats
    assert [x for x in items if x["severity"] == "high" and "read model" in x["what"]], whats
    assert any("waited for Madhav's yes or skip for more than a week (oldest 28 Oct)" in w for w in whats), whats


def test_a_high_item_reaches_the_phone_once_a_day_and_the_scan_is_in_the_self_check(tmp_path):
    sent = []
    state = tmp_path / "told.json"
    items = [{"market": "both", "severity": "high", "source": "self-scan", "what": "the read model stops at 5 Nov"},
             {"market": "india", "severity": "medium", "source": "self-scan", "what": "two places disagree"}]
    assert len(selfcheck.tell(items, lambda t, b: sent.append((t, b)), NOW, state)) == 1
    assert sent[0][0].startswith("Ananta: something is not right") and "read model" in sent[0][1] and "Ask me what's wrong" in sent[0][1]
    assert selfcheck.tell(items, lambda t, b: sent.append((t, b)), NOW + 3600, state) == [] and len(sent) == 1, "not twice in a day"
    assert len(selfcheck.tell(items, lambda t, b: sent.append((t, b)), NOW + 90000, state)) == 1, "again the next day if still wrong"
    assert "agree" in [k for k, _ in selfcheck.CHECKS] and selfcheck.SOURCE_CHECK["self-scan"] == "agree"
