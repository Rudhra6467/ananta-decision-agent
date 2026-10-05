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
