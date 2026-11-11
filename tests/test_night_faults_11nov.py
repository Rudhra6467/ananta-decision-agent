"""The crypto faults the 10 Nov night test and the keen audit's register found, fixed from Ananta's own history on 11 Nov 2026 (Madhav,
10 Nov 21:22: "Why can't we fix them based on historical data and performance of Ananta instead of waiting?"). Words and checks only: no
book rule changes (the scorecard freeze allows repairing a fault)."""
import json
import re
from pathlib import Path

from jarvis.service import ask, nightcheck, officer

ROOT = Path(__file__).resolve().parents[1]


def test_our_book_means_the_500_book():
    # flag 101: the night test asked about "our book" and the answer described a measuring book
    s = ask.SYSTEM
    assert '"our book", "the book", "my book", "our account", "my portfolio", "my money", "how are we doing" also mean THE $500 book' in s
    assert 'are never "our book" unless named' in s


def test_no_coin_price_is_written_down_to_be_remembered():
    # 10 Nov night test: answers quoted "Bitcoin near C$112,000" from the prompt when it was near C$106,000
    for src in (ask.SYSTEM, (ROOT / "jarvis" / "service" / "officer.py").read_text(), (ROOT / "jarvis" / "service" / "ask.py").read_text()):
        assert not re.search(r"C\$1[0-9]{2},000", src), "a C$ coin price written into a prompt goes stale"
    assert "about C$447 now" not in ask.SYSTEM
    assert "times the day's exchange rate" in ask.SYSTEM


def test_a_coin_code_is_a_coin_in_the_note():
    # flag 106: the 11 Nov note said "a measuring book was in ERA", reading the coin ERA as a word
    words = officer._moves_in_words(["ERA CAUGHT", "SOL MISSED", "PEPE SEEN"])
    assert words == [{"coin": "ERA", "what": "a measuring book held the coin on paper (not the account)"},
                     {"coin": "SOL", "what": "no book saw the move in time"},
                     {"coin": "PEPE", "what": "seen; no book held the coin"}]
    assert officer._moves_in_words(None) is None and len(officer._moves_in_words([f"C{k} CAUGHT" for k in range(9)])) == 5
    assert "coin's code is a coin" in officer.NOTE_RULES and 'never "a measuring book was in\nERA"' in officer.NOTE_RULES


def test_the_night_test_asks_a_briefing_at_night_and_a_greeting_is_never_a_mistake():
    # flag 100: the 7 pm test asked for "my morning briefing" and the grader marked "Evening, sir" wrong
    qs = {q["id"]: q for q in json.loads((ROOT / "docs" / "knowledge" / "nightcheck_crypto.json").read_text())["questions"]}
    assert "morning" not in qs["brief3"]["q"].lower() and qs["brief3"]["changed"].startswith("11 Nov")
    assert "A greeting is never a mistake" in nightcheck.GRADER_RULES
    src = (ROOT / "jarvis" / "service" / "nightcheck.py").read_text()
    assert r"\bflag|waiting|wait for me|needs? me|open list" in src, "naming the open list's flags when asked what waits is not a stray flag"


def test_every_log_line_carries_its_time():
    # R-183: jarvis_service.log had no times ("INFO: 127.0.0.1 - GET /health 200"), so a night could not be rebuilt from it
    import logging

    from jarvis.service import app as A

    lg = logging.getLogger("uvicorn.access")
    h = logging.StreamHandler()
    lg.addHandler(h)
    try:
        A._times_in_the_log()
        rec = logging.LogRecord("uvicorn.access", logging.INFO, __file__, 1, '%s - "%s %s HTTP/%s" %d', ("127.0.0.1:1", "GET", "/health", "1.1", 200), None)
        line = h.format(rec)
        assert re.match(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}[+-]\d{4} INFO: +127\.0\.0\.1:1 - "GET /health HTTP/1\.1" 200', line), line
    finally:
        lg.removeHandler(h)


def test_one_event_one_date(tmp_path, monkeypatch):
    # R-153 / flag 80: the short-dip rule (H07) was parked on 28 Oct (the status book's history); the reconstruction card said 26 Oct
    # (the night its finding was queued) and Ask said 29 Oct (the status card's note carried the day the knowledge build noticed it)
    from jarvis.service import reconstruct, strategy_status
    from tests.test_universe_live import J

    h07 = {"status": "PARKED", "history": [{"when": "2026-10-28", "from": "ACTIVE", "to": "PARKED"}]}
    assert strategy_status.status_since(h07, "PARKED") == "2026-10-28" and strategy_status.status_since({}, "PARKED") is None
    later = {"history": h07["history"] + [{"when": "2026-11-10", "from": "PARKED", "to": "EVIDENCE"}]}
    assert strategy_status.status_since(later, "EVIDENCE") == "2026-11-10" and strategy_status.status_since(later, "PARKED") == "2026-10-28"
    repo = tmp_path / "repo"
    (repo / "docs" / "knowledge").mkdir(parents=True)
    (repo / "docs" / "knowledge" / "strategy_status.json").write_text(json.dumps({"strategies": {"H07": h07, "RBD": {"status": "PARKED"}}}))
    monkeypatch.setattr(reconstruct, "REPO", repo)
    j = J(tmp_path)
    reconstruct._table(j)
    rows = [("b1", "2026-10-26", 1, "BOOK_BLEED", "DECISION", "bleed:H07", "w", "{}", "DECIDED", 1793222076, "owner: yes, from Needs you"),   # 28 Oct 21:14 UTC
            ("b2", "2026-10-29", 2, "BOOK_BLEED", "DECISION", "bleed:RBD", "w", "{}", "DECIDED", 1793372601, "owner: yes, pause RBD")]       # 30 Oct 15:03 UTC
    for r in rows:
        j.db.execute("INSERT INTO rx_queue VALUES (?,?,?,?,?,?,?,?,?,?,?)", r)
    words = reconstruct.value_line(j)["words"]
    assert "H07 parked (2026-10-28)" in words and "RBD parked (2026-10-30)" in words, words
    card = next(c for c in json.loads((ROOT / "docs" / "knowledge" / "status_cards.json").read_text())["cards"] if c["id"] == "H07")
    assert "H07 parked 2026-10-28" in card["reason"] and "2026-10-29" not in card["reason"]


def test_ananta_knows_when_we_last_spoke(monkeypatch):
    # R-199 / flag 6 (open since 24 Oct): "when did we speak last time? Do you remember the date?" got "I don't have the date of our last chat"
    monkeypatch.setenv("ANANTA_VOICE_LOCAL", "0")
    monkeypatch.setenv("ASK_LOCAL", "0")
    from tests.test_ask_ananta import _jarvis

    j, _ex = _jarvis()
    seen = {}

    def fake(s, h, u, t, log):
        seen["u"] = u
        return json.dumps({"kind": "answer", "answer": "We last spoke on Tuesday 3 November, sir."}), {"in": 1, "out": 1}

    A = ask.Ask(j, providers={"gemini": fake})
    T = 1793709142                                                     # Tue 3 Nov 2026, 12:32 UTC: 7:32 am in Toronto
    rows = [("m1", "4e32b85a5787", T, "user", "If we want to buy something crypto today, what would be your call?", "voice:auto"),
            ("m2", "4e32b85a5787", T + 258, "user", "Good Ananta. Nice. Good job. Thank you.", "voice:auto"),
            ("m3", "synef63bc3c", T + 4 * 86400, "user", "I'm turning the laptop off for an hour.", "people"),     # an audit run
            ("m4", "plain1", T + 5 * 86400, "user", "a test question", "eval:auto"),
            ("m5", "exam-1", T + 5 * 86400, "user", "an exam question", "auto"),
            ("m6", "brief:x", T + 5 * 86400, "user", "the morning briefing", "deep")]
    for r in rows:
        j.db.execute("INSERT INTO ask_messages (id, thread, t, role, text, mode) VALUES (?,?,?,?,?,?)", r)
    assert A._last_chat("now") == {"when": "Tue 3 Nov 2026, 7:36 am Toronto time", "by": "voice", "questions": 2,
                                   "first": "If we want to buy something crypto today, what would be your call?", "last": "Good Ananta. Nice. Good job. Thank you."}
    assert A.last_conversation()["thread"] == "4e32b85a5787", "an audit run is never the conversation to continue"
    A.ask("o", "Hey Ananta, I'm good. How are you? And when did we speak last time? Do you remember the date?", mode="everyday")
    assert "LAST CHAT" in seen["u"] and "Tue 3 Nov 2026, 7:36 am Toronto time" in seen["u"]
    A.ask("o", "How is the market?", mode="everyday")
    assert "LAST CHAT" not in seen["u"]
    assert [bool(ask.LAST_CHAT_Q.search(q)) for q in ("when did we last talk", "our last conversation", "did we chat yesterday", "talk me through the dial")] == [True, True, True, False]


def _zone_row(j, W, rid: str, t0: int) -> None:
    row = {"id": rid, "watch": "ZONE_TOUCH-UC", "coin": "AAA", "source": "eye", "signal_t": t0 + 3600, "signal_day": "2026-10-13",
           "entry_t": t0 + 3600, "entry_day": "2026-10-13", "entry": 1.0, "status": "OPEN", "why": "zone touch", "detail": json.dumps({"days": 5, "tier": "C"})}
    j.db.execute(f"INSERT INTO evidence_trades ({', '.join(W.COLS)}) VALUES ({', '.join('?' * len(W.COLS))})", tuple(row.get(c) for c in W.COLS))


def test_a_late_close_says_so_on_its_row_and_counts_in_the_note(tmp_path, monkeypatch):
    # R-169: the 50 old paper trades closed late on 10 Nov carried no mark, and the note counted 41 (net about -US$96): the 9 zone touches
    # closed by manage_live_rows (net -US$132.07) were left out of the count
    from jarvis.service import universe_watch as U, watch_engine as W
    from tests.test_universe_live import J

    T0 = 1791849600                                                        # 13 Oct 2026, 00:00 UTC
    D = [(T0 + k * 86400, 1.0, 1.0, 1.0, 1.0, 1000.0) for k in range(31)]
    monkeypatch.setattr(U, "_daily", lambda j, c: D)
    j = J(tmp_path, now=T0 + 30 * 86400 + 300)                             # 12 Nov, 00:05 UTC: the nightly round
    W._table(j)
    _zone_row(j, W, "z1", T0)
    assert U.manage_live_rows(j, "C", ["AAA"]) == 1
    exit_day, detail = j.db.execute("SELECT exit_day, detail FROM evidence_trades WHERE id='z1'").fetchone()
    assert exit_day == "2026-10-19" and json.loads(detail)["recorded_late"] == "2026-11-12" and json.loads(detail)["tier"] == "C"
    late = json.loads(j.db.execute("SELECT v FROM engine_state WHERE k='late_closes:2026-11-12'").fetchone()[0])
    assert late["n"] == 1 and late["books"] == {"ZONE_TOUCH": 1}, "the zone touches count in the night's late closes"
    # a close written on time carries no mark and no late count
    (tmp_path / "b").mkdir()
    j2 = J(tmp_path / "b", now=T0 + 7 * 86400 + 300)                       # 20 Oct, 00:05 UTC: the night after its rule's day
    W._table(j2)
    _zone_row(j2, W, "z2", T0)
    assert U.manage_live_rows(j2, "C", ["AAA"]) == 1
    assert "recorded_late" not in json.loads(j2.db.execute("SELECT detail FROM evidence_trades WHERE id='z2'").fetchone()[0])
    assert (not j2.db.execute("SELECT 1 FROM sqlite_master WHERE name='engine_state'").fetchone()
            or not j2.db.execute("SELECT 1 FROM engine_state WHERE k LIKE 'late_closes:%'").fetchone())


def test_a_timing_line_written_in_a_test_stays_in_the_test(tmp_path, monkeypatch):
    # R-041: the test suite wrote its own rows into the real India timing log (the self-scan reads it for slow answers)
    from jarvis.india import ask as india_ask

    monkeypatch.setattr(india_ask, "DRY_RUN", False)
    india_ask._timing_log("t-test", "a test question", False, {"total_ms": 1})
    rows = (tmp_path / "india_data" / "reports" / "ask_timing.jsonl").read_text().splitlines()
    assert len(rows) == 1 and json.loads(rows[0])["thread"] == "t-test"


def test_a_lean_is_one_answer():
    # R-192 (1, 8 and 9 Nov): "where is Bitcoin going?" got "I can't predict" and then a lean; HAVE A VIEW (Madhav's) keeps the lean
    s = ask.SYSTEM
    assert 'the lean IS the answer: give it as your lean, never "I can\'t predict" first and a lean after it' in s
    assert "No predictions or promises" not in s and "a lean (HAVE A VIEW) is a view with its odds, never said as what will happen" in s
