"""16 Nov 2026, audit repair 7, quiet and cheap (open-list flag 123): G-61 (the builder's own items pinged the phone), G-62 (the Explorer
sent its paper trades to the phone), G-64 (India's nightly check sent the same failures every night), G-65 (no brain decision counted as a
miss on days nothing woke it), G-66 (the briefs asked the paid model to say nothing happened), G-67 (India could not say what it costs),
G-74 (Activity sent the phone hundreds of KB), flag 130 (the sign-in failed note twice in 15 minutes), flag 97 (each note came twice)."""
import json
import sqlite3
import time

from tests.test_universe_live import J


def test_g61_only_madhavs_own_items_reach_the_phone(tmp_path):
    from jarvis.service import requests_log as R

    j = J(tmp_path)
    mine = R.add(j, "idea", "[Crypto · list] A thing Madhav asked for", by="owner")
    own = R.add(j, "idea", "[Crypto · list] A thing the builder filed for itself", by="claude")
    auto = R.add(j, "idea", "[Crypto · list] A thing Ananta filed", by="ananta-auto")
    for r in (mine, own, auto):
        R.set_status(j, r["id"], "PLANNED", "on it")
    sent = []
    R.notify(j, push=lambda t, b: sent.append(t))
    assert len(sent) == 1 and sent[0].startswith("Planned:")                    # it was three
    assert not R._select(j, "WHERE COALESCE(pushed, 1)=0")                      # all marked, so none waits to be sent later


def test_g62_the_explorers_paper_trades_are_kept_not_pushed():
    from tests.test_explorer_live import _mk

    d, clock, hands, ex, alerts = _mk()
    ex._on_event({"kind": "FILLED", "coin": "SOL", "setup": "S1", "type": "long", "entry": 1.0, "stop": 0.9})
    ex._on_event({"kind": "CLOSED", "coin": "SOL", "setup": "S1", "type": "long", "bell": "target", "net_usd": 1.0})
    assert not any(a[0].startswith("Ananta Explorer: paper") for a in alerts)    # it pushed both


def test_g64_the_nightly_check_tells_the_phone_only_of_a_new_failure(tmp_path, monkeypatch):
    from jarvis.india import replay

    monkeypatch.setattr(replay, "OUT", tmp_path)
    monkeypatch.setattr(replay, "real_turns", lambda since: [])
    monkeypatch.setattr(replay, "bank", lambda: [{"key": "k1", "text": "same old question", "status": "open"}])
    monkeypatch.setattr(replay, "_save_bank", lambda rows: None)
    monkeypatch.setattr(replay, "replay_conversation", lambda turns, tid: [{"text": turns[-1]["text"], "answer": "a"}])
    monkeypatch.setattr(replay, "judge", lambda prior, t: {"pass": False, "problems": [{"code": "X", "why": "wrong"}]})
    monkeypatch.setattr(replay, "exam_line", lambda: {"words": ""})
    import jarvis.india.neveragain as na
    monkeypatch.setattr(na, "run", lambda *a: [])
    sent = []
    replay.run(notify=lambda t, b: sent.append(b))
    replay.run(notify=lambda t, b: sent.append(b))                              # the same failure the next night
    assert len(sent) == 1 and sent[0].startswith("1 new since last night")


def test_g65_no_brain_decision_is_no_miss_on_a_day_nothing_woke_it(tmp_path):
    from jarvis.service import runcheck

    db = tmp_path / "j.sqlite"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE brain_decisions (t INTEGER, action TEXT)")
    con.execute("CREATE TABLE brain_queue (t INTEGER)")
    day = (int(time.time()) // 86400 - 3) * 86400
    con.execute("INSERT INTO brain_queue VALUES (?)", (day + 3600,))                # day 1: woken, no decision -> a miss
    con.commit()
    con.close()
    part = {"id": "brain_decides", "name": "x", "job": "x", "severity": "medium", "since": "2026-10-04",
            "cadence": {"daily": "00:00", "tz": "UTC", "grace": 27 * 3600}, "min_work": 1, "zero_means": "empty",
            "proof": {"sql": str(db), "query": "SELECT t, 1 FROM brain_decisions WHERE action != 'ERROR' AND t >= :t0"},
            "expected_if": {"sql": str(db), "query": "SELECT t, 1 FROM brain_queue WHERE t >= :t0"}}
    res = runcheck.judge(part, {}, day + 4 * 86400, 4 * 86400)
    assert len(res["misses"]) == 1 and res["misses"][0]["t"] == day, res["misses"]   # only the day something woke it (it was every day)


def test_g66_a_quiet_days_brief_is_one_line_by_code(tmp_path):
    from jarvis.service.alerts import Alerts

    db = sqlite3.connect(tmp_path / "j.sqlite")
    a = Alerts(db, now=lambda: 1794730000.0)
    db.execute("CREATE TABLE book500 (k TEXT PRIMARY KEY, v TEXT)")
    db.execute("CREATE TABLE book500_fills (t INTEGER)")
    db.execute("CREATE TABLE owner_requests (num INTEGER, waits TEXT, status TEXT, text TEXT)")
    db.execute("INSERT INTO book500 VALUES ('state', ?)", (json.dumps({"cash": 487.2, "value": 487.2, "pos": {}, "dial": False}),))
    db.execute("INSERT INTO briefings VALUES ('B1', 1794700000, 'evening', '2026-11-15', 'x', ?)", (json.dumps({"dial_at_brief": False}),))
    db.commit()
    asked = []
    r = a.write_brief("morning", lambda q: asked.append(q) or {"kind": "answer", "answer": "x"})
    assert not asked and "C$487.20, all in cash" in r["text"]                     # no model asked on a quiet day
    db.execute("INSERT INTO book500_fills VALUES (1794730100)")                     # a fill since the last brief: the model writes it
    db.commit()
    a.write_brief("evening", lambda q: asked.append(q) or {"kind": "answer", "answer": "One. Two. Three."})
    assert len(asked) == 1


def test_g67_india_prices_cached_tokens_and_keeps_a_cost_line(tmp_path):
    from jarvis.india import costlog

    u = {"in": 1000, "out": 500, "cache_read": 20000, "cache_write": 4000, "model": "claude-sonnet-5-5"}
    fresh_only = (1000 * 2 + 500 * 10) / 1e6
    assert costlog.price("claude-sonnet-5-5", u) > fresh_only                       # cached tokens were free before
    log = tmp_path / "c.jsonl"
    costlog.record("morning view (3000)", "claude-sonnet-5-5", {"usage": {"input_tokens": 100, "output_tokens": 50}}, log=log, now=1794700000)
    costlog.record("answer", "claude-sonnet-5-5", u, log=log, now=1794700100)
    m = costlog.month(log=log, now=1794700200)
    assert m["calls"] == 2 and set(m["by_job"]) == {"morning view (3000)", "answer"} and m["usd"] > 0


def test_g74_older_activity_rows_open_their_sheet_by_name():
    from jarvis import placekit as K

    page = {"kind": "page", "title": "A change", "parts": [{"t": "line", "text": "x" * 2000}]}
    days = {f"2026-11-{d:02d}": [{"title": f"t{d}", "tag": "change", "to": {"page": page}}] for d in (15, 14, 13, 12)}
    lazy = K.lazy_days(days)
    assert "page" in lazy["2026-11-15"][0]["to"] and "page" in lazy["2026-11-14"][0]["to"]          # the newest two days keep it
    link = lazy["2026-11-12"][0]["to"]["place"]
    assert link.startswith("activity:") and len(json.dumps(lazy)) < len(json.dumps(days)) / 1.8
    assert K.find_sheet(days, link.split(":", 1)[1]) == page
    assert "page" in days["2026-11-12"][0]["to"]                                  # the caller's rows are not changed


def test_flag130_the_sign_in_failed_note_goes_once_in_30_minutes(tmp_path):
    from src.india import kite_auth

    stamp = tmp_path / "s.json"
    t0 = 1794700000.0
    assert kite_auth.failed_note_due(now=t0, stamp=stamp)
    assert not kite_auth.failed_note_due(now=t0 + 15 * 60, stamp=stamp)         # the 15-minute retry: no second note
    assert kite_auth.failed_note_due(now=t0 + 31 * 60, stamp=stamp)


def test_flag97_a_note_the_ananta_app_received_goes_nowhere_else(monkeypatch):
    from src.intelligence import paper_watch as W

    ntfy = []
    monkeypatch.setattr(W, "_ntfy_send", lambda *a, **k: ntfy.append(a) or "sent")
    monkeypatch.setattr(W, "apple_push", lambda *a, **k: "sent")
    assert W._send_now("t", "b", "EVENT", "topic", None) == "sent" and not ntfy     # it went to both
    monkeypatch.setattr(W, "apple_push", lambda *a, **k: "failed: no token")
    assert W._send_now("t", "b", "EVENT", "topic", None) == "sent" and len(ntfy) == 1   # ntfy when the app did not get it


# ---------------------------------------------------------------- its outside check's finds (~/ananta_runs/keen_audit/recheck/pkg7_check.md)
def test_check1_only_wakes_that_reached_the_brain_count(tmp_path):
    from jarvis.service import runcheck, runcheck_parts

    db = tmp_path / "j.sqlite"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE brain_decisions (t INTEGER, action TEXT)")
    con.execute("CREATE TABLE brain_queue (t INTEGER, state TEXT)")
    day = (int(time.time()) // 86400 - 3) * 86400
    con.executemany("INSERT INTO brain_queue VALUES (?, ?)", [(day + 60 * k, "DROPPED: monitoring only") for k in range(50)]
                    + [(day + 86400 + 60, "NOT_REVIEWED: monitoring only")] + [(day + 2 * 86400 + 60, "DONE")])
    con.commit()
    con.close()
    part = next(p for p in runcheck_parts.PARTS if p["id"] == "brain_decides")
    part = {**part, "proof": {**part["proof"], "sql": str(db)}, "expected_if": {**part["expected_if"], "sql": str(db)}}
    res = runcheck.judge(part, {}, day + 4 * 86400, 4 * 86400)
    assert [m["t"] for m in res["misses"]] == [day + 2 * 86400], res["misses"]       # only the day a wake reached the brain


def test_check2_rows_with_the_same_title_open_their_own_sheet():
    from jarvis import placekit as K

    days = {f"2026-11-{d:02d}": [{"title": "Rules", "tag": "change", "to": {"page": {"title": f"sheet {d}-{i}"}}} for i in range(3)]
            for d in (15, 14, 13)}
    lazy = K.lazy_days(days)
    links = [r["to"]["place"] for r in lazy["2026-11-13"]]
    assert len(set(links)) == 3
    assert [K.find_sheet(days, x.split(":", 1)[1])["title"] for x in links] == ["sheet 13-0", "sheet 13-1", "sheet 13-2"]


def test_check3_a_warning_keeps_both_roads(monkeypatch):
    from src.intelligence import paper_watch as W

    ntfy = []
    monkeypatch.setattr(W, "_ntfy_send", lambda *a, **k: ntfy.append(a[3]) or "sent")
    monkeypatch.setattr(W, "apple_push", lambda *a, **k: "sent")
    for lv in ("EVENT", "WARN", "ERROR"):
        W._send_now("t", "b", lv, "topic", None)
    assert ntfy == ["WARN", "ERROR"]


def test_check4_a_dial_change_or_an_item_for_his_yes_is_no_quiet_day(tmp_path):
    from jarvis.service.alerts import Alerts

    db = sqlite3.connect(tmp_path / "j.sqlite")
    a = Alerts(db, now=lambda: 1794730000.0)
    db.execute("CREATE TABLE book500 (k TEXT PRIMARY KEY, v TEXT)")
    db.execute("CREATE TABLE book500_fills (t INTEGER)")
    db.execute("CREATE TABLE owner_requests (num INTEGER, waits TEXT, status TEXT, text TEXT)")
    db.execute("INSERT INTO book500 VALUES ('state', ?)", (json.dumps({"cash": 487.2, "value": 487.2, "pos": {}, "dial": False}),))
    db.execute("INSERT INTO briefings VALUES ('B1', 1794700000, 'evening', '2026-11-15', 'x', ?)", (json.dumps({"dial_at_brief": False}),))
    db.commit()
    assert a.quiet_day()
    db.execute("UPDATE book500 SET v=? WHERE k='state'", (json.dumps({"cash": 487.2, "value": 487.2, "pos": {}, "dial": True}),))
    db.commit()
    assert a.quiet_day() is None                                                   # the dial opened since the last brief
    db.execute("UPDATE book500 SET v=? WHERE k='state'", (json.dumps({"cash": 487.2, "value": 487.2, "pos": {}, "dial": False}),))
    db.execute("INSERT INTO owner_requests VALUES (281, 'YOU', 'OPEN', '[Crypto · list] Re-run the agent exam once by hand now that the credit is back.')")
    db.commit()
    q = a.quiet_day()                                                              # 21 Nov: something waits for his yes, and the
    assert "Nothing needs you" not in q and "One thing waits for your yes: flag 200, Re-run the agent exam" in q   # code line names it


def test_check5_a_one_hour_cache_write_is_priced_at_twice_the_input():
    from jarvis.india import costlog

    five = costlog.price("claude-sonnet-5-5", {"usage": {"cache_creation_input_tokens": 1_000_000}})
    hour = costlog.price("claude-sonnet-5-5", {"usage": {"cache_creation_input_tokens": 1_000_000,
                                                         "cache_creation": {"ephemeral_1h_input_tokens": 1_000_000}}})
    assert round(hour / five, 2) == 1.6                                            # 2.0 x against 1.25 x


def test_check8_an_old_question_failing_for_a_new_reason_is_new():
    from jarvis.india import replay

    a = {"source": "bank", "text": "q", "problems": [{"code": "STALE"}]}
    b = {"source": "bank", "text": "q", "problems": [{"code": "WRONG_DAY"}]}
    assert replay._fkey(a) != replay._fkey(b) and replay._fkey(a) == replay._fkey(dict(a))


def test_check5b_an_india_answers_usage_carries_its_one_hour_cache_writes():
    from jarvis.india import ask

    reply = {"content": [{"type": "text", "text": "{}"}], "stop_reason": "end_turn",
             "usage": {"input_tokens": 10, "output_tokens": 5, "cache_creation_input_tokens": 100, "cache_creation": {"ephemeral_1h_input_tokens": 100}}}
    import pytest
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(ask, "_load_env_key", lambda: "test-key")
        _text, u = ask._claude("s", [], "u", post=lambda url, headers, body: reply)
    assert u.get("cache_write_1h") == 100
