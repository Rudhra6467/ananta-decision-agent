"""The next step, plain words and who Jarvis is talking to (Madhav, 2026-10-05: the first 4 answers always offer the obvious
next step plus 3 suggestions; 'just say yes'; 'sir' only for him; simplify the words, not the intelligence)."""
import json
import pathlib
import sqlite3
import types

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_next_step_is_kept_only_when_runnable_and_suggestions_are_short_and_distinct():
    from jarvis.service import ask

    r = {"next_action": {"label": "Yes, pull up the BTC setup", "ask": "Show me the BTC setup", "say": "Want me to pull it up? Just say yes."},
         "follow_ups": ["Show me the BTC setup", "What are we watching?", "What are we watching?", "x", "Show me today's trades", "Explain the strongest setup"]}
    ask._clean_next(r)
    assert r["next_action"]["ask"] == "Show me the BTC setup"
    assert r["follow_ups"] == ["What are we watching?", "Show me today's trades", "Explain the strongest setup"]
    r = {"next_action": {"label": "", "ask": "x"}, "follow_ups": []}
    ask._clean_next(r)
    assert r["next_action"] is None


def test_only_madhav_is_sir():
    from jarvis.service import ask

    assert ask.guest_address("Morning, sir. Bitcoin is up.") == "Morning. Bitcoin is up."
    assert ask.guest_address("It's above its 50-day average, Madhav.") == "It's above its 50-day average."
    assert ask.guest_address("Ananta is Madhav's paper trading system.") == "Ananta is Madhav's paper trading system."


def test_yes_runs_the_offered_step_and_marks_the_chip(tmp_path):
    from jarvis.service import ask

    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE ask_messages (id TEXT, thread TEXT, t INTEGER, role TEXT, text TEXT, reply TEXT)")
    j = types.SimpleNamespace(db=db, now=lambda: 1_000_000, dir=tmp_path)
    reply = {"answer": "Bitcoin is up 2%.", "next_action": {"label": "Yes, pull up BTC", "ask": "Show me the BTC setup", "say": "Just say yes."},
             "follow_ups": ["What are we watching?"]}
    db.execute("INSERT INTO ask_messages VALUES ('a1','th',999900,'assistant',NULL,?)", (json.dumps(reply),))
    ask._log_chips(j, "th", "a1", reply)
    a = ask.Ask.__new__(ask.Ask)
    a.j = j
    assert a._take_next_step("th", "yes please") == "Show me the BTC setup"
    assert a._take_next_step("th", "what are we watching?") == "what are we watching?"
    st = {x["text"]: x["picked"] for x in ask.chip_stats(j)}
    assert st == {"Show me the BTC setup": 1, "What are we watching?": 1}
    j.now = lambda: 1_100_000                                          # too late: "yes" is just a word again
    assert a._take_next_step("th", "yes") == "yes"


def test_glossary_covers_what_the_engine_uses_and_reaches_the_prompt():
    from jarvis.service import ask

    g = json.loads((ROOT / "docs" / "knowledge" / "glossary.json").read_text())
    ids = {t["id"] for t in g["terms"]}
    assert {"btc_gate", "ma20", "ma50", "sma200", "rsi", "atr", "zone", "stop", "independent_event", "costs"} <= ids
    for t in g["terms"]:
        assert t["plain"] and t["meaning"] and t["ours"] and t["say"]
    j = types.SimpleNamespace(dir=ROOT)
    block = ask._plain_words(j)
    assert "PLAIN WORDS" in block and "average price over the last 50 days" in block and "(not used by Ananta)" in block
