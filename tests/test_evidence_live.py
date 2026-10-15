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
