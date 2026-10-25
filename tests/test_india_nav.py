"""India voice and chat navigation (flags 96/97; Madhav, 25 Oct), the flag numbers after the reset, and the time a fix needs."""
import json
import time

from jarvis.india import appmap, ask
from jarvis.service import core, fixflow, requests_log


def test_plain_navigation_is_done_in_code():
    q = appmap.quick_command("show me my stocks")
    assert q["ui"] == [{"do": "open", "target": "sheet:stocks", "label": "your stocks"}]
    assert appmap.quick_command("Ananta, take me to my flags please")["ui"][0]["target"] == "flags"
    assert appmap.quick_command("open the morning view")["ui"][0]["target"] == "sheet:morning"
    assert appmap.quick_command("where are my options?")["ui"][0]["target"] == "sheet:options"
    assert appmap.quick_command("switch to crypto")["ui"][0] == {"do": "market", "target": "market:crypto", "label": "the crypto market"}
    assert appmap.quick_command("go back")["ui"][0]["do"] == "back"
    assert appmap.quick_command("take me home")["ui"][0]["target"] == "home"
    assert appmap.quick_command("scroll down")["ui"][0] == {"do": "scroll", "dir": "down", "label": "Scroll down"}
    d = appmap.quick_command("show me Ananta's decisions")
    assert d["ui"][0]["target"] == "home" and d["points"] == [{"spot": "home.books", "sentence": 0}]


def test_questions_are_not_navigation():
    assert appmap.quick_command("show me why TATAPOWER is rated C") is None
    assert appmap.quick_command("What is the Nifty doing today?") is None
    assert appmap.quick_command("Analyze my whole portfolio") is None


def test_nav_reply_runs_at_once_in_the_app():
    r = ask.nav_flow("open my options")
    assert r["mode"] == "nav" and r["ui"][0]["target"] == "sheet:options" and r["answer"] == "Opening your options, sir."


def test_model_ui_is_checked():
    assert appmap.valid_ui([{"do": "go_to", "target": "markets"}, {"do": "go_to", "target": "coin:BTC"}, {"do": "open", "target": "my stocks"}]) == [
        {"do": "go_to", "target": "markets", "label": "Markets"}, {"do": "open", "target": "sheet:stocks", "label": "your stocks"}]
    assert appmap.valid_points([{"spot": "home.money", "sentence": 1}, {"spot": "nowhere", "sentence": 0}]) == [{"spot": "home.money", "sentence": 1}]


def test_flag_numbers_restart_after_the_reset():
    assert requests_log.label(96) == "flag 15" and requests_log.label(40) == "request 40" and requests_log.flag_no(82) == 1


def test_pick_says_the_time_and_lookups_take_the_flag_number(tmp_path):
    import sqlite3
    import types

    j = types.SimpleNamespace(dir=tmp_path, db=core.SafeDB(sqlite3.connect(":memory:", check_same_thread=False)), now=lambda: time.time())
    requests_log._table(j)
    for n in range(1, 97):                                       # requests 1..96 exist; 96 is flag 15
        j.db.execute("INSERT INTO owner_requests (id, t, by, kind, text, about, thread, status, note, num, updated_t, pushed, told) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                     (f"r{n}", n, "owner", "bug", f"thing {n}", "", None, "OPEN" if n > 81 else "DONE", "", n, n, 1, 1))
    j.db.commit()
    assert requests_log.get(j, "flag 15")["num"] == 96 and requests_log.get(j, 15)["num"] == 96 and requests_log.get(j, "request 15")["num"] == 15
    fixflow._table(j)
    now = int(time.time())
    j.db.execute(f"INSERT INTO fix_flow ({', '.join(fixflow.COLS)}) VALUES ({', '.join('?' * len(fixflow.COLS))})",
                 (96, "india", "ask", "", "SAFE", json.dumps({"diagnosis": "", "options": [{"title": "Let the agent open screens", "what": "x", "lane": "SAFE"}]}),
                  None, "triaged", "[]", 0, None, None, now, now))
    j.db.commit()
    r = fixflow.choose(j, 96, 0, "the first")
    assert r["state"] == "queued" and r["label"] == "flag 15" and r["eta_minutes"] >= 4
    assert "minutes" in r["say"] and "Fixed: flag 15" in r["say"]
