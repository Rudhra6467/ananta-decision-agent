"""The Evidence page, live (Madhav, 2026-10-05): the repair loop answered with live counts, in his order."""
import json
import os
import sqlite3
import types

DAY = 86400


def _j(tmp_path, now=2_000_000_000):
    return types.SimpleNamespace(dir=tmp_path, db=sqlite3.connect(":memory:"), now=lambda: now, _explorer=lambda: None, prices=lambda: {})


def test_page_builds_without_the_explorer_and_keeps_every_section(tmp_path):
    from jarvis.service import evidence_live as el

    d = el.build(_j(tmp_path))
    for k in ("as_of", "health", "clocks", "limits", "results", "rebuild", "misses", "board", "in_use", "loop", "headline"):
        assert d.get(k) is not None, (k, d.get("errors"))
    assert [x["key"] for x in d["loop"]] == ["looked", "spotted", "decided", "scored", "missed", "forwarded", "changed"]
    assert any(c["name"] == "Nightly rebuild" for c in d["clocks"])
    assert d["limits"][-1]["id"] == "SIZE"


def test_every_rebuild_is_kept_once_and_mismatches_are_counted(tmp_path):
    from jarvis.service import evidence_live as el

    j = _j(tmp_path)
    p = tmp_path / "explorer_reconstruct.json"
    p.write_text(json.dumps({"logged_real_events": 44, "rebuilt_real_events": 44, "match": True, "only_in_live": [], "only_in_rebuilt": []}))
    os.utime(p, (1_999_990_000, 1_999_990_000))
    assert el.record_rebuild(j)["source"] == "nightly"
    assert el.record_rebuild(j) is None                                  # the same file is kept once
    j.db.execute("CREATE TABLE jobs (id TEXT PRIMARY KEY, t INTEGER, kind TEXT, status TEXT, result TEXT, done_t INTEGER, by TEXT)")
    j.db.execute("INSERT INTO jobs VALUES ('a', ?, 'reconstruction', 'DONE', ?, ?, 'ananta (asked by owner)')",
                 (1_999_995_000, json.dumps({"match": False}), 1_999_995_000))
    p.write_text(json.dumps({"logged_real_events": 45, "rebuilt_real_events": 44, "match": False, "only_in_live": [["ORDER"]], "only_in_rebuilt": []}))
    os.utime(p, (1_999_995_010, 1_999_995_010))
    assert el.record_rebuild(j)["source"] == "asked"                     # a rebuild Madhav asked for is not a night
    r = el._rebuild(j, {"studies": [], "reviews": [], "modes": [], "tickets": []})
    assert r["nightly"]["runs"] == 1 and r["asked"]["runs"] == 1 and r["total"] == 2 and r["mismatches"] == 1
    assert r["last"]["match"] is False and r["last"]["checked"] == 45
    names = [b["book"] for b in r["books"]]                              # Fix 9: every book the nightly check covers has a row, even unrun
    assert names[0] == "the Explorer replayed from raw candles" and names[-1] == "the daily rules re-run on every tier"
    assert len(names) == len(el.REBUILD_PARTS) + 1
    assert r["books"][0]["runs"] == 1 and r["books"][1]["runs"] == 0 and r["books"][1]["last"] is None
    j.db.execute("INSERT INTO rebuild_log (t, source, match) VALUES (1999999000, 'trend30', 0)")
    j.db.execute("INSERT INTO rebuild_log (t, source, match) VALUES (1999999100, 'trend', 1)")
    t30 = next(b for b in el._rebuild(j, {})["books"] if "30-coin" in b["book"])
    assert t30["runs"] == 1 and t30["mismatches"] == 1 and t30["last_match"] is False   # 'trend' rows are not counted as 'trend30'


def test_board_puts_what_waits_for_madhav_first_and_counts_groups(tmp_path):
    from jarvis.service import evidence_live as el
    from jarvis.service import requests_log

    j = _j(tmp_path)
    requests_log.add(j, "data", "Show the timeframe that built a support zone", about="Hunter")
    L = {"tickets": [{"id": "TK1", "date": "2026-10-05", "what": "x", "status": "DONE"},
                     {"id": "TK2", "date": "2026-10-05", "what": "y", "status": "WAITING_FOR_YOU"}],
         "reviews": [{"id": "R1", "date": "2026-09-30", "status": "DONE", "verdict": "FAIL", "title": "t"},
                     {"id": "R19", "date": "2026-10-05", "status": "IN_PROGRESS", "verdict": "", "title": "u"}],
         "queue": [{"id": "Q1", "title": "q", "waiting_for": "30 trades", "metric": "closed_trades", "goal": 30}]}
    b = el._board(j, L, {})
    assert b["items"][0]["id"] == "TK2" and b["items"][0]["status_words"] == "Waiting for you"
    assert b["groups"] == {"you": 1, "us": 2, "evidence": 1, "done": 2}
    assert b["kinds"] == {"ticket": 2, "request": 1, "review": 2, "question": 1} and b["verdicts"] == {"FAIL": 1}


def test_waiting_gives_a_pace_and_a_date(tmp_path):
    from jarvis.service import evidence_live as el

    now = 2_000_000_000
    j = _j(tmp_path, now)
    P = {"shop": {"queue": [{"id": "Q3", "title": "E5", "metric": "e5_trades", "goal": 20, "have": 2},
                            {"id": "Q1", "title": "Explorer", "metric": "closed_trades", "goal": 30, "have": 63, "events": 2},
                            {"id": "Q6", "title": "H07", "metric": "h07_fires", "goal": 10, "have": 0}]}}
    ex = types.SimpleNamespace(st={"trade_from_t": now - 5 * DAY})
    w = {x["id"]: x for x in el._waiting(j, P, ex)}
    assert w["Q3"]["pace_per_day"] == 0.4 and w["Q3"]["eta_days"] == 45 and w["Q3"]["eta_date"]
    assert w["Q1"]["have"] == 2 and w["Q1"]["goal"] == 10 and w["Q1"]["unit"] == "market events" and "met" in w["Q1"]["also"]
    assert w["Q6"]["eta_note"] == "none yet in 5 days" and not w["Q6"]["done"]


def test_limit_verdict_reads_what_the_stopped_trades_did():
    from jarvis.service import evidence_live as el

    base = {"real": {"avg_usd": -2.72}, "random": {"avg_usd": -1.27}}
    v = el._limit_verdict(179, {"closed": 53, "avg_usd": -3.29, "events": 2}, base)
    assert "not hiding winners" in v and "too early" in v
    assert "did better" in el._limit_verdict(114, {"closed": 93, "avg_usd": -0.48, "events": 4}, base)
    assert el._limit_verdict(0, {"closed": 0}, base) == "Never reached so far."


def test_jarvis_speedup_follows_the_tk4_ticket():
    from jarvis.service import evidence_live as el

    assert "waits for you" in el._jarvis_speedup(8, 102, {"id": "TK4", "status": "OPEN"})
    assert "waits for you" in el._jarvis_speedup(8, 102, None)
    done = el._jarvis_speedup(120, 1270, {"id": "TK4", "status": "DONE"})
    assert "waits for you" not in done and "in use" in done and done.startswith("Jarvis decided 120 of 1270 wakes")


def test_missed_moves_list_never_drops_a_miss_for_newer_catches():
    from jarvis.service import evidence_live as el

    ms = [{"day": f"2026-10-{d:02d}", "coin": f"C{d}", "label": "CAUGHT"} for d in range(20, 10, -1)]
    ms += [{"day": "2026-10-05", "coin": "BCH", "label": "MISSED"}, {"day": "2026-10-04", "coin": "ADA", "label": "SEEN"}]
    shown = el._shown_moves(ms)
    assert len(shown) == 8 and [m["coin"] for m in shown][-2:] == ["BCH", "ADA"]
    assert [m["day"] for m in shown] == sorted((m["day"] for m in shown), reverse=True)      # still newest first
    assert el._shown_moves(ms[:3]) == ms[:3]


def test_open_queue_drops_items_whose_review_is_done():
    from jarvis.service import evidence_live as el

    L = {"reviews": [{"id": "R24", "status": "DONE"}, {"id": "R29", "status": "IN_PROGRESS"}]}
    queue = [{"id": "Q1"}, {"id": "R24"}, {"id": "R29"}]
    assert [q["id"] for q in el._open_queue(queue, L)] == ["Q1", "R29"]
    assert [q["id"] for q in el._open_queue(queue, None)] == ["Q1", "R24", "R29"]
    assert el._open_queue(None, L) == []


def test_the_page_counts_market_events_once():
    """Madhav, Oct 15: one event count. The headline said 9 ('no verdict before 10') while Q1 said 11 ('done')."""
    from jarvis.service import evidence_live as E

    out = {"results": {"events": 9, "items": [{"key": "real", "events": 11}, {"key": "random", "events": 15}, {"key": "jarvis", "events": 1}]},
           "waiting": [{"id": "Q1", "unit": "market events", "have": 11, "goal": 10, "done": True}, {"id": "Q2", "unit": "weeks", "have": 2}]}
    E._one_event_count(out)
    assert [i["events"] for i in out["results"]["items"]] == [9, 9, 1] and out["results"]["items"][0]["events_own"] == 11
    assert out["waiting"][0]["have"] == 9 and out["waiting"][0]["done"] is False and out["waiting"][1]["have"] == 2


def test_agent_cites_is_the_weekly_spot_check_done_by_code(tmp_path):
    """Gate agent_cites (Oct 15): the newest 20 answers to Madhav that state a number; an item opens on screen when it names a
    spot or a screen. Background jobs, family questions and exam conversations never count; no conversations = pending."""
    from jarvis.service import evidence_live as el

    j = _j(tmp_path)
    assert el.cites(j) == (0, 0, 0)
    j.db.execute("CREATE TABLE ask_messages (id TEXT PRIMARY KEY, thread TEXT, t INTEGER, role TEXT, text TEXT, reply TEXT, mode TEXT, route TEXT)")
    now = j.now()

    def add(i, reply, thread="th", mode="auto", route="market"):
        j.db.execute("INSERT INTO ask_messages (id, thread, t, role, reply, mode, route) VALUES (?,?,?,?,?,?,?)",
                     (f"m{i}", thread, now - 100 - i, "assistant", json.dumps(reply), mode, route))
        j.db.execute("INSERT OR IGNORE INTO ask_messages (id, thread, t, role, text, mode) VALUES (?,?,?,?,?,?)",
                     (f"u-{thread}", thread, now - 1000, "user", "a question", "voice:auto"))     # Oct 21: a conversation has a person's question

    good = {"kind": "answer", "answer": "Bitcoin is 80,900.", "evidence": [{"label": "BTC", "value": "80,900", "source": "MARKET_BRIEF", "spot": "markets.btc"}]}
    for i in range(17):
        add(i, good)
    add(17, {"kind": "answer", "answer": "Dial open since Oct 10.", "evidence": [{"label": "Dial", "value": "OPEN", "source": "MARKET_BRIEF"}]})
    add(18, {"kind": "answer", "answer": "Zone 9.54 to 10.19.", "evidence": []})
    add(19, {"kind": "answer", "answer": "No numbers here, sir."})                      # no number: not a fact answer, skipped
    add(20, good, mode="worker")
    add(21, good, thread="exam-1-2")
    add(22, good, route="people")
    add(23, {"kind": "clarify", "answer": "Which 2 coins?"})
    assert el.cites(j) == (19, 17, 18)                                       # 19 fact answers so far: pending
    add(24, {"kind": "answer", "answer": "ETH 2.3% down.", "evidence": [{"label": "ETH", "value": "-2.3%", "source": "MARKET_BRIEF", "screen": "coin"}]})
    assert el.cites(j) == (20, 18, 19)
    by = {"agent_cites": {"id": "agent_cites"}, "agent_knows": {}, "agent_unknowns": {}, "ux_voice": {}}
    try:
        el._gate_measured(j, by)
    except Exception:  # noqa: BLE001  a later measure (exam files) may be missing here; cites has already been written
        pass
    assert by["agent_cites"]["status"] == "PASS" and "18 of the last 20" in by["agent_cites"]["note"]


def test_an_outage_seen_from_outside_must_have_been_alerted(tmp_path):
    """Oct 15 (worker S1): the worker saw the public page down 312 minutes from Oct 12 06:18 UTC while the main Mac slept and sent
    nothing; with no alert armed that fails ops_outages, and the main Mac's own note within 5 minutes only helps to PARTLY (nothing
    can report its sleep). Short blips (under 10 minutes) do not count."""
    from jarvis.service import evidence_live as el

    j = _j(tmp_path)
    o = {"windows": [{"from": "2026-10-12 06:18", "minutes": 312}, {"from": "2026-10-12 14:03", "minutes": 1}]}
    r = el.outages_seen_from_outside(j, o)
    assert r["status"] == "FAIL" and "Oct 12 02:18 Toronto, 312 min" in r["note"] and "1 outage of 10+" in r["note"]
    assert "not armed yet" in r["note"]
    from datetime import datetime, timezone

    t0 = int(datetime(2026, 10, 12, 6, 18, tzinfo=timezone.utc).timestamp())
    j.db.execute("CREATE TABLE eye_events (id TEXT, t INTEGER, kind TEXT, coin TEXT, price REAL, title TEXT, body TEXT, pushed INTEGER, detail TEXT)")
    j.db.execute("INSERT INTO eye_events (id, t, kind) VALUES ('e', ?, 'HEALTH_DOWN')", (t0 + 10 * 60,))   # 10 minutes late: still missed
    assert el.outages_seen_from_outside(j, o)["status"] == "FAIL"
    j.db.execute("UPDATE eye_events SET t=?", (t0 + 120,))
    assert el.outages_seen_from_outside(j, o)["status"] == "PARTLY"            # alerted by the main Mac itself, but no outside alert yet
    assert el.outages_seen_from_outside(j, {"windows": []})["status"] == "PARTLY"


def test_the_worker_alert_is_judged_from_the_day_it_is_armed_and_must_be_proven(tmp_path):
    """Madhav's yes (Oct 15): the worker sends a note when the page has been down 10 minutes. From the day it is armed every outage of
    10+ minutes needs that note by minute 15; earlier outages are listed, not counted against it; PASS needs a note on record."""
    from datetime import datetime, timezone

    from jarvis.service import evidence_live as el

    j = _j(tmp_path)

    def ts(*a):
        return int(datetime(*a, tzinfo=timezone.utc).timestamp())
    old = {"from": "2026-10-12 06:18", "t0": ts(2026, 10, 12, 6, 18), "minutes": 312}
    armed = ts(2026, 10, 15, 20, 0)
    new_t0 = ts(2026, 10, 16, 6, 0)
    new = {"from": "2026-10-16 06:00", "t0": new_t0, "minutes": 40}
    base = [{"t": armed, "kind": "armed", "result": "on"}]
    # armed, a test note sent, one earlier outage listed, no outage since
    r = el.outages_seen_from_outside(j, {"windows": [old], "alerts": base + [{"t": armed + 60, "kind": "test", "result": "sent"}]})
    assert r["status"] == "PASS" and "armed since Oct 15 16:00 Toronto" in r["note"] and "Oct 12 02:18 Toronto, 312 min" in r["note"]
    # armed but nothing was ever sent
    r = el.outages_seen_from_outside(j, {"windows": [], "alerts": base})
    assert r["status"] == "PARTLY" and "no note is on record" in r["note"]
    # a note that failed to send is not proof
    r = el.outages_seen_from_outside(j, {"windows": [], "alerts": base + [{"t": armed + 60, "kind": "test", "result": "failed: HTTP 403"}]})
    assert r["status"] == "PARTLY"
    # armed today according to the worker's status, its record not pulled yet
    r = el.outages_seen_from_outside(j, {"windows": [old]}, armed_live=True)
    assert r["status"] == "PARTLY" and "armed today" in r["note"]
    # an outage after arming: the note at minute 10 is in time (minute 15 at the latest), a later one is missed
    ok = base + [{"t": armed + 60, "kind": "test", "result": "sent"}, {"t": new_t0 + 10 * 60, "kind": "down", "result": "sent"}]
    r = el.outages_seen_from_outside(j, {"windows": [old, new], "alerts": ok})
    assert r["status"] == "PASS" and "every one alerted by minute 15" not in r["note"]            # the older one is listed, not alerted
    r = el.outages_seen_from_outside(j, {"windows": [new], "alerts": ok})
    assert r["status"] == "PASS" and "every one alerted by minute 15" in r["note"]
    late = base + [{"t": armed + 60, "kind": "test", "result": "sent"}, {"t": new_t0 + 16 * 60, "kind": "down", "result": "sent"}]
    r = el.outages_seen_from_outside(j, {"windows": [new], "alerts": late})
    assert r["status"] == "FAIL" and "NOT alerted by minute 15 although the alert was armed: Oct 16 02:00 Toronto, 40 min" in r["note"]
    failed = base + [{"t": armed + 60, "kind": "test", "result": "sent"}, {"t": new_t0 + 10 * 60, "kind": "down", "result": "failed: URLError"}]
    assert el.outages_seen_from_outside(j, {"windows": [new], "alerts": failed})["status"] == "FAIL"


def test_the_gate_item_no_trade_when_unhealthy_reads_the_code_that_runs_and_counts_the_refusals(tmp_path):
    """Oct 15: PASS only when every path that opens a paper position asks the trade guard, judged from the files the service and the
    Explorer actually run (the Explorer's folder changes when main is merged and it restarts); the refusals of 7 days are counted."""
    from jarvis.service import evidence_live as el
    from jarvis.service import trade_guard as tg

    j = _j(tmp_path)
    by = {"ops_no_trade_unhealthy": {"id": "ops_no_trade_unhealthy", "status": "PARTLY", "note": "Explorer yes, others to check"}}
    el._gate_measured(j, by)
    c = by["ops_no_trade_unhealthy"]
    assert c["status"] == "PARTLY" and "9 of 11 paths" in c["note"] and "not live yet" in c["note"] and "no refusal in 7 days" in c["note"]
    folder = tmp_path / "src" / "intelligence"
    folder.mkdir(parents=True)
    (folder / "explorer_live.py").write_text("from jarvis.service import trade_guard\nKILL_SWITCH_UNREAD = 1\n")
    tg.refuse(j, "JARVIS", "BTC", tg.KILL_ON)
    el._gate_measured(j, by)
    c = by["ops_no_trade_unhealthy"]
    assert c["status"] == "PASS" and "11 of 11 paths" in c["note"] and "1 refusal in 7 days (1 x the kill switch is on)" in c["note"]


def _realism(measured: int, ok: int, median: float | None, books: dict | None = None, no_quote: int = 0) -> dict:
    return {"since": "2026-10-12", "fills": measured + no_quote, "measured": measured, "realistic": ok, "no_quote": no_quote,
            "realistic_share": round(ok / measured, 3) if measured else None, "median_optimism_bps": median,
            "books": books or {"BOOK500": {"fills": measured + no_quote, "measured": measured, "realistic": ok, "no_quote": no_quote,
                                           "realistic_share": round(ok / measured, 3) if measured else None, "median_optimism_bps": median,
                                           "worst_optimism_bps": median}}}


def test_engine_execution_is_judged_against_the_workers_independent_ndax_quote(tmp_path, monkeypatch):
    """Oct 20, Madhav "2. yes": every paper fill of every book against the worker's NDAX quote for that minute. PENDING under 20
    measured fills; FAIL under 90% achievable or a median optimism over 5 bp; else PASS."""
    from jarvis.service import evidence_live as el
    from jarvis.service import realism

    assert (el.EXEC_FILLS, el.EXEC_ACHIEVABLE, el.EXEC_MEDIAN_BPS, el.EXEC_SINCE) == (20, 0.90, 5.0, "2026-10-12")
    assert el.execution_reading(_realism(0, 0, None))["status"] == "PENDING"
    assert el.execution_reading(_realism(19, 19, -3.0))["status"] == "PENDING"            # too few, however good
    ok = el.execution_reading(_realism(20, 18, 4.9))
    assert ok["status"] == "PASS" and "18 of 20" in ok["note"] and "90%" in ok["note"]
    assert el.execution_reading(_realism(20, 17, 1.0))["status"] == "FAIL"                # 85% achievable
    assert el.execution_reading(_realism(40, 38, 5.1))["status"] == "FAIL"                # median over 5 bp
    books = {"BOOK500": {"fills": 10, "measured": 10, "realistic": 10, "no_quote": 0, "realistic_share": 1.0, "median_optimism_bps": -20.0},
             "T30": {"fills": 30, "measured": 26, "realistic": 12, "no_quote": 4, "realistic_share": 0.462, "median_optimism_bps": 9.5},
             "H07": {"fills": 3, "measured": 0, "realistic": 0, "no_quote": 3, "realistic_share": None, "median_optimism_bps": None},
             "TINY": {"fills": 2, "measured": 2, "realistic": 0, "no_quote": 0, "realistic_share": 0.0, "median_optimism_bps": 22.0}}
    bad = el.execution_reading(_realism(38, 22, 6.0, books, no_quote=7))
    assert bad["status"] == "FAIL" and "worst book T30: 12 of 26" in bad["note"] and "TINY" not in bad["note"]     # 2 fills: too few to name and "7 fills had no worker quote (T30 4, H07 3)" in bad["note"]

    j = _j(tmp_path)
    j.db.execute("CREATE TABLE book500_fills (t INTEGER, coin TEXT, side TEXT, qty REAL, px REAL, fee REAL, bid REAL, ask REAL)")
    j.db.execute("INSERT INTO book500_fills VALUES (1, 'BTC', 'BUY', 1, 100, 0.2, 99, 101)")
    asked = {}
    monkeypatch.setattr(realism, "report", lambda jj=None, since=None, **k: asked.update(since=since, **k) or _realism(20, 20, 0.5))
    by = {"engine_execution": {"id": "engine_execution", "status": "PENDING", "note": ""}}
    el._gate_measured(j, by)
    c = by["engine_execution"]
    assert asked["since"] == "2026-10-12" and asked["data"] == tmp_path
    assert c["status"] == "PASS" and "the $500 book's own count (the rule until Oct 20): 1 of 1 fills inside" in c["note"]

    def broken(*a, **k):
        raise FileNotFoundError("no worker data")
    monkeypatch.setattr(realism, "report", broken)
    el._gate_measured(j, by)
    assert by["engine_execution"]["status"] == "PENDING" and "could not measure" in by["engine_execution"]["note"]


# ---------------------------------------------------------------------------
# Oct 21 gate bundle (Madhav, 2026-10-21 09:41 Toronto: "I approve all"; decision map section 4)
# ---------------------------------------------------------------------------
NOW21 = 1792594431                      # 2026-10-21 14:53 UTC


def _ev_table(j):
    j.db.execute("CREATE TABLE evidence_trades (id TEXT, watch TEXT, coin TEXT, entry_t INTEGER, entry_day TEXT, exit_day TEXT, "
                 "net_usd REAL, status TEXT)")


def _trade(j, watch, et, net, i=[0]):
    from datetime import datetime, timezone

    i[0] += 1
    day = datetime.fromtimestamp(et, timezone.utc).strftime("%Y-%m-%d")
    j.db.execute("INSERT INTO evidence_trades VALUES (?,?,?,?,?,?,?,?)", (f"t{i[0]}", watch, "BTC", et, day, day, net, "CLOSED"))


def test_cites_counts_conversations_only_never_briefs_or_the_stance(tmp_path):
    """agent_cites (Oct 21): the scheduled morning and evening briefs ('brief:...'), the brain's own thread (the stance) and the bold
    book's, the news reads and test runs never count; a person's conversation does."""
    from jarvis.service import evidence_live as el

    j = _j(tmp_path, NOW21)
    j.db.execute("CREATE TABLE ask_messages (id TEXT PRIMARY KEY, thread TEXT, t INTEGER, role TEXT, text TEXT, reply TEXT, mode TEXT, route TEXT)")
    good = {"kind": "answer", "answer": "Bitcoin is 80,900.", "evidence": [{"label": "BTC", "source": "MARKET_BRIEF", "spot": "markets.btc"}]}
    bare = {"kind": "answer", "answer": "Bitcoin is 80,900.", "evidence": [{"label": "BTC", "source": "MARKET_BRIEF"}]}
    k = [0]

    def say(thread, reply, umode="voice:auto", amode="auto", ask=True):
        k[0] += 1
        if ask:
            j.db.execute("INSERT OR IGNORE INTO ask_messages (id, thread, t, role, text, mode) VALUES (?,?,?,?,?,?)",
                         (f"u{thread}", thread, NOW21 - 5000, "user", "q", umode))
        j.db.execute("INSERT INTO ask_messages (id, thread, t, role, reply, mode, route) VALUES (?,?,?,?,?,?,?)",
                     (f"a{k[0]}", thread, NOW21 - 100 - k[0], "assistant", json.dumps(reply), amode, "market"))
    for n in range(25):
        say(f"brief:{n:012d}", good, umode="deep", amode="deep")                    # scheduled briefs: never counted
    say("brain", good, umode="worker", amode="auto")                               # the stance's thread
    say("bold", good, amode="worker")
    say("reads:news", good, amode="worker")
    say("evalthread01", good, umode="eval:lab")                                    # a test run
    say("noquestion01", good, ask=False)                                           # no question a person asked
    assert el.cites(j) == (0, 0, 0)
    by = {"agent_cites": {"id": "agent_cites"}, "agent_knows": {}, "agent_unknowns": {}, "ux_voice": {}}
    try:
        el._gate_measured(j, by)
    except Exception:  # noqa: BLE001  the exam files may be missing here; cites is written first
        pass
    assert by["agent_cites"]["status"] == "PENDING"                               # 25 good briefs once made this a PASS
    for n in range(17):
        say("a1b2c3d4e5f6", good)
    for n in range(3):
        say("a1b2c3d4e5f6", bare)
    assert el.cites(j) == (20, 17, 20)
    try:
        el._gate_measured(j, by)
    except Exception:  # noqa: BLE001
        pass
    assert by["agent_cites"]["status"] == "FAIL" and "17 of the last 20" in by["agent_cites"]["note"]


def test_strategy_regimes_counts_independent_market_events_not_closing_days(tmp_path):
    """strategy_regimes (Oct 21): 'the stricter event count': entries within 3 days of each other are one event (the scoreboard's
    daily rule, as Jarvis's book and Q7 count), split by the dial on the entry day. The old count (one per closing day) said 9 for
    Jarvis's book on Oct 21; the stricter count says 1."""
    from datetime import datetime, timezone

    from jarvis.service import evidence_live as el

    j = _j(tmp_path, NOW21)
    _ev_table(j)
    t0 = NOW21 - 60 * DAY
    for k in range(12):                                   # 12 trades, entered 6 hours apart: one market event
        _trade(j, "JARVIS", t0 + k * 6 * 3600, -1.0)
    dial = {datetime.fromtimestamp(t0 + d * DAY, timezone.utc).strftime("%Y-%m-%d"): 1.0 for d in range(-1, 61)}
    r = el.regimes_reading(j, dial)
    assert r["status"] == "PENDING" and "Jarvis's book: 1 independent event dial open, 0 dial closed (12 closed trades)" in r["note"]
    assert "H07 tier A: 0 independent events dial open" in r["note"]
    # entries 4 days apart, the first 10 with the dial open and the next 10 closed: 10 events in each state for both ideas: PASS
    j.db.execute("DELETE FROM evidence_trades")
    dial = {}
    for watch in ("JARVIS", "H07-UA"):
        for k in range(20):
            et = t0 + k * 4 * DAY
            _trade(j, watch, et, 1.0)
            dial[datetime.fromtimestamp(et, timezone.utc).strftime("%Y-%m-%d")] = 1.0 if k < 10 else 0.0
    r = el.regimes_reading(j, dial)
    assert r["status"] == "PASS" and r["note"].count("10 independent events dial open, 10 dial closed") == 2
    j.db.execute("DELETE FROM evidence_trades WHERE watch='H07-UA' AND entry_t > ?", (t0 + 15 * 4 * DAY,))   # H07 now 6 closed events
    assert el.regimes_reading(j, dial)["status"] == "PENDING"
    assert el.REGIME_EVENTS == 10


def test_agent_no_failed_rules_counts_the_bold_books_buys(tmp_path):
    """agent_no_failed_rules (Oct 21): the bold book is added. A bold TAKE whose recorded knowledge list holds a context-only or
    switched-off idea is counted (the bold book is never blocked); a bold buy from before the list was recorded is named, not counted."""
    from jarvis.service import evidence_live as el

    j = _j(tmp_path, NOW21)
    assert el.no_failed_rules_reading(j)["status"] == "PENDING"                    # no tables at all
    j.db.execute("CREATE TABLE brain_decisions (t INTEGER, action TEXT, note TEXT)")
    j.db.execute("CREATE TABLE bold_decisions (id TEXT, t INTEGER, action TEXT, knowledge_used TEXT)")
    j.db.execute("INSERT INTO bold_decisions VALUES ('a', ?, 'TAKE', NULL)", (NOW21 - 3 * DAY,))       # before Oct 20: no list
    j.db.execute("INSERT INTO bold_decisions VALUES ('b', ?, 'WOULD_ADD', ?)", (NOW21 - DAY, json.dumps(["FILTERS"])))
    r = el.no_failed_rules_reading(j)
    assert r["status"] == "PENDING" and "1 bold buy with no recorded knowledge list" in r["note"]
    j.db.execute("INSERT INTO bold_decisions VALUES ('c', ?, 'TAKE', ?)", (NOW21 - DAY, json.dumps(["T3", "REGIME", "STOPS"])))
    r = el.no_failed_rules_reading(j)
    assert r["status"] == "PASS" and "bold book: 0 of 1 buys" in r["note"] and "1 bold buy from before" in r["note"]
    j.db.execute("INSERT INTO bold_decisions VALUES ('d', ?, 'TAKE', ?)", (NOW21 - 3600, json.dumps(["T3", "FILTERS"])))
    r = el.no_failed_rules_reading(j)
    assert r["status"] == "FAIL" and "bold book: 1 of 2 buys cited a context-only or switched-off idea (FILTERS)" in r["note"]
    j.db.execute("DELETE FROM bold_decisions WHERE id='d'")
    j.db.execute("INSERT INTO brain_decisions VALUES (?, 'TAKE', 'cited context-only ideas: FILTERS')", (NOW21 - 3600,))
    assert el.no_failed_rules_reading(j)["status"] == "FAIL"                       # the brain's own rule is unchanged
    j.db.execute("DELETE FROM brain_decisions")
    j.db.execute("INSERT INTO bold_decisions VALUES ('e', ?, 'TAKE', ?)", (NOW21 - 9 * DAY, json.dumps(["FILTERS"])))
    assert el.no_failed_rules_reading(j)["status"] == "PASS"                       # older than 7 days: out of the window


def _baselines_setup(tmp_path, monkeypatch, n_events, mine, twin, books, bench):
    import sqlite3 as sq
    import types as ty

    from jarvis.service import evidence_live as el

    j = _j(tmp_path, NOW21)
    _ev_table(j)
    t0 = NOW21 - 50 * DAY
    for k in range(n_events):                            # entries 4 days apart: each its own event
        _trade(j, "H07-UA", t0 + k * 4 * DAY, mine)
        _trade(j, "RANDOM_10D-UA", t0 + k * 4 * DAY, twin)
        _trade(j, "ZONE_TOUCH-UB", t0 + k * 4 * DAY + 3600, 50.0)          # 'won't take again': never counted
        _trade(j, "E1", t0 + k * 4 * DAY + 7200, 50.0)                    # the retired Explorer's setups: never counted
    j.db.execute("CREATE TABLE book500 (k TEXT PRIMARY KEY, v TEXT)")
    j.db.execute("INSERT INTO book500 VALUES ('state', ?)", (json.dumps({"started": "2026-10-11", "value": books["b500"]}),))
    lay = sq.connect(":memory:")
    lay.execute("CREATE TABLE decisions (day_t INTEGER, json TEXT)")
    lay.execute("INSERT INTO decisions VALUES (?, '{}')", (NOW21 - 21 * DAY,))
    j._layer = lambda: ty.SimpleNamespace(con=lay)
    t30 = sq.connect(str(tmp_path / "portfolio_book_t30.sqlite"))
    t30.execute("CREATE TABLE decisions (day_t INTEGER, json TEXT)")
    t30.execute("INSERT INTO decisions VALUES (?, '{}')", (NOW21 - 16 * DAY,))
    t30.commit()
    t30.close()
    monkeypatch.setattr(el, "_btc_bench", lambda jj, start: dict(bench))
    out = {"results": {"books": [{"key": "t3", "pct": books["t3"], "vs_pct": books["t3_hold"]},
                                 {"key": "t30", "pct": books["t30"], "vs_pct": books["t30_hold"]}]}}
    return el, j, out


GOOD = {"b500": 520.0, "t3": 3.0, "t3_hold": 1.0, "t30": 2.0, "t30_hold": 1.0}


def test_strategy_baselines_reads_the_accounts_books_with_buy_and_hold_and_the_btc_50_day(tmp_path, monkeypatch):
    """strategy_baselines (Oct 21): not the retired Explorer. The books allowed to trade against their own random twins, in
    independent market events, and the $500 book and both trend books against buy-and-hold and the BTC 50-day benchmark."""
    bench = {"HOLD": 1.0, "GATE50": 0.5}
    el, j, out = _baselines_setup(tmp_path, monkeypatch, 9, 2.0, -1.0, GOOD, bench)
    r = el.baselines_reading(j, out)
    assert r["status"] == "PENDING" and "9 closed trades, 9 of 10 independent market events" in r["note"]   # ZONE_TOUCH and E1 left out
    assert "+$3.00 per $100" in r["note"] and "the retired Explorer no longer counts" in r["note"]
    (tmp_path / "p").mkdir()
    el, j, out = _baselines_setup(tmp_path / "p", monkeypatch, 10, 2.0, -1.0, GOOD, bench)
    r = el.baselines_reading(j, out)
    assert r["status"] == "PASS" and "the $500 book +4.00% since 2026-10-11" in r["note"] and "Bitcoin held +1.0%" in r["note"]
    assert "the 10-coin trend book +3.00%" in r["note"] and "50-day benchmark +0.5%" in r["note"]


def test_strategy_baselines_fails_when_a_book_trails_a_benchmark_or_its_twin(tmp_path, monkeypatch):
    bench = {"HOLD": 1.0, "GATE50": 0.5}
    (tmp_path / "a").mkdir()
    el, j, out = _baselines_setup(tmp_path / "a", monkeypatch, 10, -2.0, -1.0, GOOD, bench)          # behind its random twin
    r = el.baselines_reading(j, out)
    assert r["status"] == "FAIL" and "behind: the allowed books against their twins" in r["note"]
    (tmp_path / "b").mkdir()
    el, j, out = _baselines_setup(tmp_path / "b", monkeypatch, 10, 2.0, -1.0, dict(GOOD, b500=490.0), bench)   # $500 book -2%
    r = el.baselines_reading(j, out)
    assert r["status"] == "FAIL" and "behind: the $500 book" in r["note"]
    (tmp_path / "c").mkdir()
    el, j, out = _baselines_setup(tmp_path / "c", monkeypatch, 10, 2.0, -1.0, GOOD, {"HOLD": 1.0, "GATE50": 2.5})  # +2.0% under the 50-day's +2.5%
    r = el.baselines_reading(j, out)
    assert r["status"] == "FAIL" and r["note"].split("behind:")[1].strip() == "the 30-coin trend book"   # the 10-coin book (+3.0%) is ahead
    (tmp_path / "d").mkdir()
    el, j, out = _baselines_setup(tmp_path / "d", monkeypatch, 10, 2.0, -1.0, GOOD, bench)
    r = el.baselines_reading(j, {})                                                                   # trend books not read: not a pass
    assert r["status"] == "FAIL" and "the 10-coin trend book (not read)" in r["note"]


def _l1(dest, day, minutes, alerts=()):
    import sqlite3 as sq
    from datetime import datetime, timezone

    d0 = int(datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
    con = sq.connect(str(dest / f"l1_{day}.sqlite"))
    con.execute("CREATE TABLE site (t INTEGER, ok INTEGER, ms INTEGER, detail TEXT)")
    con.executemany("INSERT INTO site VALUES (?,1,100,NULL)", [(d0 + 60 * m + 5,) for m in minutes])
    con.commit()
    con.close()
    return d0


def _health(j):
    j.db.execute("CREATE TABLE health_log (id INTEGER PRIMARY KEY AUTOINCREMENT, part TEXT, down_t INTEGER, up_t INTEGER, detail TEXT)")
    j.db.execute("CREATE TABLE eye_events (id TEXT, t INTEGER, kind TEXT, coin TEXT, price REAL, title TEXT, body TEXT, pushed INTEGER, detail TEXT)")


def test_ops_outages_counts_part_outages_and_their_phone_notes(tmp_path):
    """ops_outages (Oct 21): it stayed green through the 426-minute Hands outage of Oct 16-17. A part outage of 10+ minutes needs its
    phone note within 5 minutes and must end within 60; a short blip counts for nothing."""
    from jarvis.service import evidence_live as el

    dest = tmp_path / "w"
    dest.mkdir()
    for d in range(7, -1, -1):
        from datetime import datetime, timezone

        _l1(dest, datetime.fromtimestamp(NOW21 - d * DAY, timezone.utc).strftime("%Y-%m-%d"), range(1440))
    j = _j(tmp_path, NOW21)
    _health(j)
    ok = {"status": "PASS", "note": "worker alert armed; outside view fine"}
    r = el.outages_reading(j, ok, dest)
    assert r["status"] == "PASS" and "0 of 10+ minutes" in r["note"] and "outside view fine" in r["note"]
    assert el.outages_reading(j, {"status": "PARTLY", "note": "alert not proven"}, dest)["status"] == "PARTLY"
    assert el.outages_reading(j, {"status": "PENDING"}, dest)["status"] == "PENDING"
    t0 = NOW21 - 4 * DAY
    j.db.execute("INSERT INTO health_log (part, down_t, up_t) VALUES ('hands', ?, ?)", (t0, t0 + 426 * 60))
    j.db.execute("INSERT INTO eye_events (id, t, kind, pushed, detail) VALUES ('e', ?, 'HEALTH_DOWN', 1, '{\"part\": \"hands\"}')", (t0,))
    r = el.outages_reading(j, ok, dest)
    assert r["status"] == "FAIL" and "down more than 60 minutes: hands" in r["note"] and "426 min" in r["note"]
    j.db.execute("UPDATE health_log SET up_t=?", (t0 + 20 * 60,))
    assert el.outages_reading(j, ok, dest)["status"] == "PASS"                     # 20 minutes, noted at once
    j.db.execute("UPDATE eye_events SET t=?", (t0 + 6 * 60,))                       # noted 6 minutes late
    r = el.outages_reading(j, ok, dest)
    assert r["status"] == "FAIL" and "NO phone note for: hands" in r["note"]
    j.db.execute("UPDATE eye_events SET t=?, pushed=0", (t0,))                      # recorded but never reached the phone
    assert el.outages_reading(j, ok, dest)["status"] == "FAIL"
    j.db.execute("UPDATE health_log SET up_t=?", (t0 + 8 * 60,))                    # an 8-minute blip: not an outage
    assert el.outages_reading(j, ok, dest)["status"] == "PASS"
    assert el.outages_reading(j, {"status": "FAIL", "note": "outside outage not alerted"}, dest)["status"] == "FAIL"


def test_ops_outages_counts_the_minutes_the_worker_could_not_see(tmp_path):
    """The worker's blind time: on a pulled day its own minute record decides (Oct 18-19: SSH down while it recorded every minute,
    not blind); on a day not pulled yet, the minutes the main Mac could not reach it. Over 420 minutes in 7 days fails."""
    from datetime import datetime, timezone

    from jarvis.service import evidence_live as el

    dest = tmp_path / "w"
    dest.mkdir()
    days = [datetime.fromtimestamp(NOW21 - d * DAY, timezone.utc).strftime("%Y-%m-%d") for d in range(7, 0, -1)]   # today not pulled
    starts = [_l1(dest, d, range(1440)) for d in days]
    j = _j(tmp_path, NOW21)
    _health(j)
    ok = {"status": "PASS", "note": "outside fine"}
    j.db.execute("INSERT INTO health_log (part, down_t, up_t) VALUES ('worker', ?, ?)", (starts[-2] + 3600, starts[-2] + 15 * 3600))
    r = el.outages_reading(j, ok, dest)
    assert r["status"] == "PASS" and "could not see for 0 minutes" in r["note"] and "could not reach it for 840 minutes" in r["note"]
    today0 = NOW21 - NOW21 % DAY
    j.db.execute("INSERT INTO health_log (part, down_t, up_t) VALUES ('worker', ?, NULL)", (today0 + 3600,))   # still unreachable today
    r = el.outages_reading(j, ok, dest)
    blind = el.worker_blind_minutes(j, NOW21 - 7 * DAY, NOW21, dest, el._part_outages(j, NOW21 - 7 * DAY, NOW21))
    assert blind["unreachable_not_pulled"] == (NOW21 - today0 - 3600) // 60 and r["status"] == ("FAIL" if blind["minutes"] > 420 else "PASS")
    j.db.execute("DELETE FROM health_log")
    (dest / f"l1_{days[2]}.sqlite").unlink()
    _l1(dest, days[2], range(0, 1440 - 500))                                       # a pulled day with 500 minutes not looking
    r = el.outages_reading(j, ok, dest)
    assert r["status"] == "FAIL" and "the worker blind 500 minutes (over 420)" in r["note"]
    assert el.WORKER_BLIND_MAX_MIN == 420 and el.PART_OUTAGE_MAX_MIN == 60 and el.OUTAGE_DAYS == 7
    j2 = _j(tmp_path, NOW21)
    _health(j2)
    r = el.outages_reading(j2, ok, tmp_path / "none")                            # no worker on this machine: not a pass
    assert r["status"] == "PARTLY" and "not measured" in r["note"]
