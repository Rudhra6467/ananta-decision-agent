"""5 Nov 2026 evening: the reverse-engineering audit of Ananta's self-knowledge (Madhav: "make sure the process is did well and integrated
well so that voice now has full information on backend and database as well"). What the audit found and fixed."""
import json
import signal
import time

from jarvis import selfcheck, selfknow
from jarvis.india import ask as india_ask


def test_the_database_is_in_the_book_about_itself_for_both_markets(tmp_path, monkeypatch):
    """Asked "what tables do you keep", the crypto Ask said none of its lookups expose the schema; India said its facts did not say where
    the files live. parts.database now says, with live counts."""
    import sqlite3

    db = tmp_path / "jarvis.sqlite"
    con = sqlite3.connect(db)
    con.executescript("CREATE TABLE ask_messages (id TEXT); INSERT INTO ask_messages VALUES ('a'), ('b'); CREATE TABLE owner_requests (id TEXT);"
                      "CREATE TABLE made_up (x INTEGER);")
    con.commit()
    con.close()
    monkeypatch.setattr(selfknow, "CRYPTO_DB", db)
    selfknow._DB_CACHE.clear()
    c = selfknow.database("crypto")
    assert "3 tables" in c["words"] and c["tables_by_group"]["conversations"]["ask_messages"].endswith("(2 rows)")
    assert "owner_requests" in c["tables_by_group"]["your requests and approvals"] and c["other_tables"] == ["made_up"]
    india = tmp_path / "india"
    (india / "ask").mkdir(parents=True)
    (india / "ask" / "t1.jsonl").write_text("{}\n")
    (india / "bronze").mkdir()
    from jarvis.india import selfparts

    monkeypatch.setattr(selfparts, "INDIA", india)
    selfknow._DB_CACHE.clear()
    i = selfknow.database("india")
    assert i["places"]["ask/"].endswith("(1 files, newest " + time.strftime("%d %b") + " " + time.strftime("%H") + ":" + time.strftime("%M") + ")") or "1 files" in i["places"]["ask/"]
    assert i["places"]["bronze/"].endswith("(empty)") and "readmodel/" not in i["places"], "only what exists is listed"
    assert "database" in selfknow.parts("crypto") and "database" in selfknow.parts("india")
    assert selfknow.database("india") is i, "cached: the India lake is 230,000 files"


def test_what_the_self_check_found_fine_is_said_too(tmp_path, monkeypatch):
    """An answer said "please check the credit was topped up" hours after it was: only the problems were in front of the model."""
    c = {"at": 1, "at_words": "5 Nov 19:59 Toronto", "items": [{"market": "india", "severity": "medium", "source": "watchdog", "what": "x"},
                                                              {"market": "both", "severity": "low", "source": "nightly replay", "what": "y"}]}
    fine = selfcheck.fine(c)
    assert len(fine) == 1 and fine[0].startswith("the same check (5 Nov 19:59 Toronto) found 2 items not right")
    assert "Claude answers" in fine[0] and "four services" in fine[0] and "no test card" in fine[0]
    assert "watchdog" not in fine[0] and "replay" not in fine[0]
    assert selfcheck.fine({"at_words": "now", "items": []})[0].count(";") == 12   # thirteen checks (12 Nov: Zerodha's refused reads joined). Before, twelve: the $500 book check joined on 10 Nov (after the Mac-load, gates, reconstruction-order and self-scan ones), India's book check on 11 Nov
    monkeypatch.setattr(selfcheck, "FILE", tmp_path / "selfcheck.json")
    (tmp_path / "selfcheck.json").write_text(json.dumps({"at": time.time(), "at_words": "now", "items": []}))
    a = selfknow.about_ananta("is anything wrong", "crypto")
    assert a["checked_fine"] and a["checked_fine"][0].startswith("checked now, all in order") and "Nothing is wrong" in a["not_right"][0]


def test_the_voice_print_words_count_the_added_sentences(tmp_path, monkeypatch):
    v = tmp_path / "voice"
    v.mkdir()
    (v / "speaker_profile.json").write_text(json.dumps({"count": 12, "enrolled_at": "2026-11-05T21:10:06+00:00", "added_at": "2026-11-06T00:50:20+00:00",
                                                        "thresholds": {"accept": 0.59, "reject": 0.23, "added_loo": [0.7] * 6}}))
    monkeypatch.setattr(selfknow, "VOICE", v)
    w = selfknow._voice_print(now=time.time())["words"]
    assert "12 clips (6 read on 5 Nov, 6 more added with 'Add more of my voice' on 5 Nov)" in w, w   # Toronto days, not UTC


def test_india_questions_about_itself_reach_the_book():
    """Before: "what happens if the India service freezes" and "how did my six voice sentences get added, what went wrong" reached the model
    with no book about itself, and "did you fix the problem where a flag could not be found" got the flag board instead."""
    for q in ("What happens if the India service freezes at night?", "How did my six new voice sentences get added today, and what went wrong the first time?",
              "What do you keep in your database, and where does my data live?", "Did you fix the problem where a flag could not be found by its id?",
              "What is the change book?"):
        assert india_ask.SELF_TOPIC.search(q) or india_ask.SYS_TOPIC.search(q), q
    assert india_ask.STATUS.search("did you fix it?") and india_ask.STATUS.search("Did you fix the problem where a flag could not be found by its id?")


def test_the_india_freeze_guard_counts_the_services_own_cpu_time(monkeypatch):
    """At 19:34 on 5 Nov the wall-clock guard ended the service with every thread idle (the Mac was swapping): a starved process is not a
    stuck one. The timer is now the process's CPU time, re-armed by the heartbeat."""
    from jarvis.india import service

    armed = []
    monkeypatch.setattr(signal, "setitimer", lambda which, s, *a: armed.append((which, s)))
    service._arm_stall_timer()
    assert armed == [(signal.ITIMER_PROF, service.STALL_S)]
    registered = []
    monkeypatch.setattr(service.faulthandler, "register", lambda sig, **k: registered.append((sig, k)))
    monkeypatch.setattr(signal, "signal", lambda sig, h: registered.append(("default", sig, h)))
    service._install_stall_guard()
    assert ("default", signal.SIGPROF, signal.SIG_DFL) in registered
    assert registered[-1][0] == signal.SIGPROF and registered[-1][1]["all_threads"] and registered[-1][1]["chain"], "dump every thread, then end"


def test_both_sides_see_the_whole_self_check_own_market_first(tmp_path, monkeypatch):
    """The blind grade: the crypto voice said "one item" and the India voice "two things" about the same check (each saw only its own side),
    and "found everything fine" was computed from that filtered list. Ananta is one system: every item on both sides, this market's first."""
    monkeypatch.setattr(selfcheck, "FILE", tmp_path / "selfcheck.json")
    (tmp_path / "selfcheck.json").write_text(json.dumps({"at": time.time(), "at_words": "now", "items": [
        {"market": "crypto", "severity": "medium", "source": "lost-runs check", "what": "a part was down"},
        {"market": "india", "severity": "medium", "source": "watchdog", "what": "the India service froze"},
        {"market": "india", "severity": "low", "source": "nightly replay", "what": "2 answers wrong"}]}))
    c = selfcheck.check("crypto")
    assert [x["market"] for x in c["items"]] == ["crypto", "india", "india"]
    assert selfcheck.words(c)[0].startswith("crypto side: a part was down") and selfcheck.words(c)[1].startswith("India side: the India service froze")
    i = selfcheck.check("india")
    assert [x["market"] for x in i["items"]] == ["india", "india", "crypto"]
    f = selfcheck.fine(c)[0]
    assert f.startswith("the same check (now) found 3 items not right") and "no watchdog restart" not in f and "Claude answers" in f
    assert selfcheck.fine({"at_words": "now", "items": []})[0].startswith("checked now, all in order: ")


# ---- 5 Nov evening, Madhav: "Yes to all your recommendations" ----

def test_the_self_check_watches_the_macs_memory_and_load():
    """The 19:34 false restart came from a starved Mac and nothing watched that."""
    assert selfcheck._mac({"free_pct": 40, "swap_gb": 2.0, "load5": 3.0, "cores": 10}) == []
    low = selfcheck._mac({"free_pct": 26, "swap_gb": 14.3, "load5": 2.5, "cores": 10})
    assert low[0]["severity"] == "low" and "14.3 GB of swap" in low[0]["what"] and low[0]["source"] == "Mac load"
    med = selfcheck._mac({"free_pct": 8, "swap_gb": 13.5, "load5": 21.0, "cores": 10})
    assert med[0]["severity"] == "medium" and "8% of memory free" in med[0]["what"] and "load 21.0 on 10 cores" in med[0]["what"]
    assert selfcheck._mac({"cores": 10}) == [], "nothing readable: no finding"
    fine = selfcheck.fine({"at_words": "now", "items": med})
    assert "memory and CPU to spare" not in fine[0] and "Claude answers" in fine[0]
    assert "memory and CPU to spare" in selfcheck.fine({"at_words": "now", "items": []})[0]


def test_the_saturday_kite_fill_is_on_the_watch_list():
    from jarvis.service import runcheck_parts as RP

    p = [x for x in RP.PARTS if x["id"] == "india_kite_fill"]
    assert p and p[0]["job"] == "com.ananta.india.kitefill" and p[0]["cadence"]["weekly"] == 5 and p[0]["cadence"]["tz"] == "America/Toronto"   # 7 Nov: the job runs at 10:00 Saturday on the Mac's clock
    assert p[0]["proof"] == {"mtime": "{runs}/kite_fill_weekly.log", "err_file": "{runs}/kite_fill_weekly.err"}


def test_the_india_side_gets_the_book_in_short_on_every_turn(tmp_path, monkeypatch):
    monkeypatch.setattr(selfcheck, "FILE", tmp_path / "selfcheck.json")
    (tmp_path / "selfcheck.json").write_text(json.dumps({"at": time.time(), "at_words": "now", "items": []}))
    b = selfknow.brief("india")
    assert set(b) == {"how", "changes_last_3_days", "not_right", "checked_fine", "parts_in_one_line", "audits_and_reviews_last_7_days", "morning_review"}
    assert b["changes_last_3_days"] and all(len(x) <= 160 for x in b["changes_last_3_days"])
    assert "Nothing is wrong" in b["not_right"][0] and set(b["parts_in_one_line"]) == {"voice", "voice_print", "watchdog", "database"}
    assert len(json.dumps(b)) < 5600, "small enough for every turn (7 Nov: the audits list and the morning review in short were added)"
    src = open(india_ask.__file__).read()
    assert 'f["ananta_brief"] = selfknow.brief("india")' in src and '"ananta_brief")' in src


def test_no_nudge_when_the_answer_already_says_it(tmp_path, monkeypatch):
    monkeypatch.setattr(selfcheck, "FILE", tmp_path / "selfcheck.json")
    (tmp_path / "selfcheck.json").write_text(json.dumps({"at": time.time(), "at_words": "now", "items": [
        {"market": "india", "severity": "medium", "source": "watchdog", "what": "the India service froze and the watchdog restarted it at 5 Nov 19:34 Toronto"}]}))
    said = "Sir, the India service froze and the watchdog restarted it at 7:34 pm Toronto tonight; it is running again."
    assert selfcheck.nudge("india", tmp_path / "told.json", "t1", answer=said) == ""
    assert selfcheck.nudge("india", tmp_path / "told.json", "t1", answer="The Nifty closed at 24,537.") != ""


def test_the_self_check_reads_the_india_gates(tmp_path):
    """6 Nov: the firewall's static scan failed from the evening of 5 Nov to the morning of 6 Nov and nothing said so."""
    (tmp_path / "firewall.json").write_text(json.dumps({"static_scan": {"ok": False, "note": "2 references outside the allowlist"}, "canary": {"ok": True}, "_at": "2026-11-05T17:57:35"}))
    (tmp_path / "leakcheck.json").write_text(json.dumps({"sealed_files": {"ok": True}, "_at": "2026-11-05"}))
    items = selfcheck._gates(tmp_path)
    assert len(items) == 1 and items[0]["severity"] == "high" and items[0]["source"] == "firewall" and "static_scan" in items[0]["what"]
    assert "gates" in [k for k, _ in selfcheck.CHECKS] and selfcheck.SOURCE_CHECK["firewall"] == "gates"
    (tmp_path / "firewall.json").write_text(json.dumps({"static_scan": {"ok": True}, "_at": "x"}))
    assert selfcheck._gates(tmp_path) == []
    assert selfcheck.fine({"at_words": "now", "items": []})[0].count(";") == 12      # 11 Nov: India's book check joined; 12 Nov: Zerodha's refused reads


# ---- 6 Nov: the reconstruction audit ----

def test_the_india_ask_has_the_reconstructions_whole_record_in_counts(tmp_path, monkeypatch):
    import json as _json

    from jarvis.india import views

    data = tmp_path / "india"
    (data / "paper" / "reconstruction").mkdir(parents=True)
    reg = tmp_path / "reg"
    reg.mkdir()
    (data / "paper" / "reconstruction" / "2026-11-04.json").write_text(_json.dumps({"findings": [
        {"type": "MISS_PATTERN", "lane": "DECISION", "key": "a"}, {"type": "JOB_FAIL", "lane": "SAFE", "key": "b"}]}))
    (data / "paper" / "reconstruction" / "2026-11-05.json").write_text(_json.dumps({"findings": []}))
    (reg / "reconstruction_queue.jsonl").write_text("\n".join(_json.dumps(r) for r in [
        {"type": "MISS_PATTERN", "lane": "DECISION", "key": "a", "state": "DRAFT", "day": "2026-11-04"},
        {"type": "JOB_FAIL", "lane": "SAFE", "key": "b", "state": "to_file", "day": "2026-11-04"}]) + "\n")
    (data / "paper" / "reconstruction" / "forwarded.jsonl").write_text(_json.dumps({"key": "b", "num": 7, "note": "filed"}) + "\n")
    (data / "paper" / "reconstruction" / "decisions.jsonl").write_text("")
    monkeypatch.setattr(views, "DATA", data)
    monkeypatch.setattr(views, "REG", reg)
    h = views.rx_history()
    assert h["cards"] == 2 and h["findings_total"] == 2 and h["by_lane"] == {"DECISION": 1, "SAFE": 1}
    assert h["safe_to_repair_board"]["filed_as_flags"] == 1 and h["decision_rows"]["waiting"] == 1
    assert h["words"].startswith("2 nightly cards (2026-11-04 to 2026-11-05): 2 findings, 1 operational")


def test_a_trials_question_is_not_a_moving_average_reading():
    """RI4: "how are the two paper trials going, the one about falls under the 200-day ..." got the Nifty crossover reading (0.0 s)."""
    from jarvis.india import technicals

    assert technicals.technicals_flow("How are the two paper trials going, the one about falls under the 200-day and the relative strength one?") is None


def test_the_self_check_watches_the_reconstruction_order(tmp_path):
    """6 Nov (Madhav's yes, E4): the India card after its trials are scored; the crypto card about the closed day, from 00:30 UTC."""
    import sqlite3 as _sq

    paper = tmp_path / "paper"
    (paper / "reconstruction").mkdir(parents=True)
    (paper / "reconstruction" / "latest.json").write_text(json.dumps({"day": "2026-11-06"}))
    (paper / "rx1_trial.json").write_text(json.dumps({"start": "2026-10-28", "complete": False, "sessions": [{"day": "2026-11-04", "scored_on": "2026-11-05"}]}))
    (paper / "rs_trial.json").write_text(json.dumps({"start": "2026-11-02", "complete": False, "sessions": [{"day": "2026-11-06"}]}))
    db = tmp_path / "j.sqlite"
    con = _sq.connect(db)
    con.execute("CREATE TABLE rx_cards (day TEXT PRIMARY KEY, t INTEGER, rules TEXT, card TEXT)")
    con.execute("INSERT INTO rx_cards VALUES ('2026-11-07', ?, 'rx-cr-v2', ?)", (1762473900, json.dumps({"about_day": "2026-11-06"})))   # 00:05 UTC on 7 Nov
    con.commit(); con.close()
    items = selfcheck._rx_order(paper, db)
    assert [i["market"] for i in items] == ["india", "crypto"] and "RX1" in items[0]["what"] and "RS" not in items[0]["what"] and "00:05 UTC" in items[1]["what"]
    (paper / "rx1_trial.json").write_text(json.dumps({"start": "2026-10-28", "complete": False, "sessions": [{"day": "2026-11-05", "scored_on": "2026-11-06"}]}))
    con = _sq.connect(db)
    con.execute("UPDATE rx_cards SET t=?", (1762475400,))        # 00:30 UTC
    con.commit(); con.close()
    assert selfcheck._rx_order(paper, db) == []
    assert "rx_order" in [k for k, _ in selfcheck.CHECKS] and selfcheck.SOURCE_CHECK["reconstruction order"] == "rx_order"


# ---- 6 Nov evening: the extra check Madhav asked for ("ask a question about the auditing ... see if there are any leaks") ----

def test_the_book_tells_the_audits_apart_and_fits_under_the_tool_cap(tmp_path, monkeypatch):
    """The crypto voice, asked about 'yesterday's audit of your own knowledge', answered with the reconstruction audit, and its self-check
    was cut off: the about-Ananta block ran past the Ask's 20,000-character tool cap. One line per audit or review; the self-check first."""
    import json as _json
    import time as _time

    from jarvis import selfknow

    book = tmp_path / "changes.jsonl"
    rows = [{"date": "2026-11-05", "market": "both", "area": "self_knowledge", "words": "w1", "why": "the reverse-engineering audit of the self-knowledge work, 5 Nov evening", "status": "live"},
            {"date": "2026-11-05", "market": "india", "area": "ask", "words": "w2", "why": "the self-knowledge audit: 3 of 12 India questions missed the book", "status": "live"},
            {"date": "2026-11-05", "market": "both", "area": "watchdog", "words": "w3", "why": "Madhav's yes to the audit's recommendations, 5 Nov 21:37", "status": "live"},
            {"date": "2026-11-06", "market": "crypto", "area": "reconstruction", "words": "w4", "why": "the reconstruction audit, 6 Nov", "status": "live"},
            {"date": "2026-11-06", "market": "both", "area": "ask", "words": "w5", "why": "nothing to do with a review", "status": "live"}]
    book.write_text("".join(_json.dumps(r) + "\n" for r in rows))
    monkeypatch.setattr(selfknow, "CHANGES", book)
    selfknow._CACHE.clear()
    now = _time.mktime(_time.strptime("2026-11-06 17:00", "%Y-%m-%d %H:%M"))
    rv = selfknow.reviews(7, now=now)
    assert rv == ["5 Nov: the self-knowledge audit (3 changes: ask, self knowledge, watchdog)", "6 Nov: the reconstruction audit (1 change: reconstruction)"]
    b = selfknow.brief("crypto", now=now)
    assert b["audits_and_reviews_last_7_days"] == rv
    o = selfknow.about_ananta("what did yesterday's audit of your own knowledge find", "crypto", check=False)
    keys = list(o.keys())
    assert keys.index("audits_and_reviews_last_7_days") < keys.index("parts") and "changes_on_this" in o
    assert len(_json.dumps(o, default=str)) < 20000, "the whole block must fit the Ask's tool cap with room to spare"
