"""Live-code reliability fixes (decision map of Oct 20, section 3; Madhav, Oct 21: "I approve all"): a paid AI result that cannot be
saved is logged and noted (one note per storm), a decision and the trades it opens are one transaction, the stance asks once more
when its reply cannot be read, the 15-minute jobs' errors are kept with their time, and the run checker dates three parts it
could not date before."""
import json
import sqlite3
import time
from pathlib import Path

import pytest

from jarvis.service import reliability

ROOT = Path(__file__).resolve().parents[1]
ASK_DDL = ("CREATE TABLE IF NOT EXISTS ask_messages (id TEXT PRIMARY KEY, thread TEXT, t INTEGER, role TEXT, text TEXT, reply TEXT, "
           "provider TEXT, model TEXT, ms INTEGER, tokens_in INTEGER, tokens_out INTEGER, tools TEXT, error TEXT, cost_usd REAL, "
           "mode TEXT, note TEXT)")
FAIL_TRIGGER = "CREATE TRIGGER fail_{t} BEFORE INSERT ON {t} BEGIN SELECT RAISE(ABORT, 'disk I/O error (simulated)'); END"


@pytest.fixture(autouse=True)
def _fresh(monkeypatch):
    from jarvis.service import health

    reliability.reset()
    pushed: list = []
    monkeypatch.setitem(health.STATE, "push", lambda t, b: pushed.append((t, b)))
    yield pushed
    reliability.reset()


def _take(monkeypatch):
    """A brain set up to TAKE one coin (with a random twin), as in test_brain_takes_with_a_random_twin_and_manages_live."""
    from jarvis.service import brain
    from tests.test_jarvis_brain import _brain_j, _fake_pack

    j, ex = _brain_j()
    px = dict(j.prices())
    coin = next(c for c in px if c != "BTC")
    p = px[coin]
    monkeypatch.setattr(brain, "pack", _fake_pack(p, atr=p * 0.04))
    monkeypatch.setattr(brain, "_atr", lambda j_, c: px[c] * 0.04)
    plan = {"action": "TAKE", "confidence": 62, "size_pct": 40, "stop": p * 0.94, "target": None, "trail_atr": 1.5, "days": 10,
            "thesis": "at a 200-day zone with the market allowed", "knowledge_used": ["REGIME", "ZONES"]}
    j.db.execute(ASK_DDL)
    brain._table(j)
    return j, coin, (lambda u: (json.dumps(plan), {"in": 5000, "out": 400, "model": "fake"}))


def _trades(j) -> list[tuple]:
    return j.db.execute("SELECT watch, coin FROM evidence_trades WHERE watch IN ('JARVIS', 'JARVIS_RANDOM')").fetchall()


# ---------------------------------------------------------------------------- 1. a failed save is logged and noted, once per storm
def test_a_brain_decision_that_cannot_be_saved_is_logged_noted_and_still_counted_as_paid(monkeypatch, capsys, _fresh):
    """Oct 14-15: 226 decisions paid for and not saved, with the error only in brain_queue.state. Now: a log line with the traceback,
    one note through the health watchdog's phone path, a SAVE_FAILED row in the feed, and the paid call still in ask_messages (what
    the run checker's brain_saved reconcile counts)."""
    from jarvis.service import brain

    j, coin, call = _take(monkeypatch)
    j.db.execute(FAIL_TRIGGER.format(t="brain_decisions"))
    with pytest.raises(sqlite3.Error):
        brain.decide(j, coin, {"zone_entry": {}}, call=call)
    err = capsys.readouterr().err
    assert "UTC ananta ERROR brain decision: paid for, NOT saved" in err and "disk I/O error (simulated)" in err
    assert "Traceback" in err and coin in err
    assert len(_fresh) == 1 and "paid for but not saved" in _fresh[0][0]
    ev = j.db.execute("SELECT kind, title, pushed FROM eye_events WHERE kind='SAVE_FAILED'").fetchall()
    assert len(ev) == 1 and ev[0][2] == 1
    assert j.db.execute("SELECT COUNT(*) FROM ask_messages WHERE thread='brain' AND note='decision brain'").fetchone()[0] == 1
    assert j.db.execute("SELECT COUNT(*) FROM brain_decisions").fetchone()[0] == 0
    assert _trades(j) == []                                        # 2. the trade it would have opened is rolled back with it


def test_a_storm_of_failed_saves_sends_one_note_then_counts_the_rest(_fresh, capsys):
    j = type("J", (), {})()
    j.db = sqlite3.connect(":memory:")
    j.now = lambda: 1_000
    for k in range(5):
        r = reliability.save_failed(j, "brain decision", RuntimeError("boom"), now=1_000 + k)
        assert r["logged"] and r["noted"] == (k == 0)
    assert len(_fresh) == 1
    assert capsys.readouterr().err.count("brain decision: paid for, NOT saved") == 5          # every failure is logged
    r = reliability.save_failed(j, "brain decision", RuntimeError("boom"), now=1_000 + reliability.ALERT_EVERY_S + 1)
    assert r["noted"] and "5 failed since the last note" in _fresh[-1][1]
    assert reliability.save_failed(j, "stance", RuntimeError("x"), now=1_010)["noted"]       # each kind has its own hour


def test_the_queue_row_is_no_longer_the_only_record_of_a_failure(monkeypatch, capsys):
    from jarvis.service import brain

    j, coin, call = _take(monkeypatch)
    monkeypatch.setattr(brain, "_monitor_only", lambda trig: "")
    monkeypatch.setattr(brain, "can_decide", lambda j_: (True, ""))
    monkeypatch.setattr(brain, "score", lambda *a: (99.0, ["test"]))
    monkeypatch.setattr(brain, "_dial", lambda j_: None)
    brain.wake(j, coin, "attention_high")
    j.db.execute(FAIL_TRIGGER.format(t="brain_decisions"))
    out = brain.process(j, call=call)
    assert out and "error" in out[0]
    assert j.db.execute("SELECT state FROM brain_queue").fetchone()[0].startswith("FAILED: ")
    assert "brain queue" in capsys.readouterr().err


# ---------------------------------------------------------------------------- 2. one transaction per decision
def test_a_take_saves_the_decision_and_both_trades_together(monkeypatch):
    from jarvis.service import brain

    j, coin, call = _take(monkeypatch)
    pushed = []
    r = brain.decide(j, coin, {"zone_entry": {}}, call=call, push=lambda t, b: pushed.append(t))
    row = j.db.execute("SELECT action, trade_id, random_id FROM brain_decisions WHERE id=?", (r["id"],)).fetchone()
    assert row[0] == "TAKE" and row[1] == r["trade"] and row[2]
    ids = {i: w for i, w in j.db.execute("SELECT id, watch FROM evidence_trades")}
    assert ids[row[1]] == "JARVIS" and ids[row[2]] == "JARVIS_RANDOM"
    twin = json.loads(j.db.execute("SELECT detail FROM evidence_trades WHERE id=?", (row[2],)).fetchone()[0])
    assert twin["twin_of"] == row[1] and twin["decision"] == r["id"]
    assert pushed == [f"Jarvis paper trade: {coin}"]


def test_a_trade_that_cannot_be_written_leaves_no_decision_and_no_phone_note_of_a_trade(monkeypatch, _fresh):
    """The other half: the twin's row fails after the decision's own trade was written. Nothing of the decision stays (no orphan
    trade, no decision pointing at a missing trade), the phone hears 'not saved', never 'paper trade'."""
    from jarvis.service import brain, watch_engine

    j, coin, call = _take(monkeypatch)
    real = watch_engine._insert

    def insert(jj, row):
        if row["watch"] == "JARVIS_RANDOM":
            raise sqlite3.OperationalError("database is locked (simulated)")
        real(jj, row)
    monkeypatch.setattr(watch_engine, "_insert", insert)
    pushed = []
    with pytest.raises(sqlite3.OperationalError):
        brain.decide(j, coin, {"zone_entry": {}}, call=call, push=lambda t, b: pushed.append(t))
    assert _trades(j) == [] and j.db.execute("SELECT COUNT(*) FROM brain_decisions").fetchone()[0] == 0
    assert pushed == [] and len(_fresh) == 1


def test_atomic_commits_what_was_pending_before_and_rolls_back_only_its_own(tmp_path):
    from tests.test_universe_live import J

    j = J(tmp_path, now=1)
    j.db.execute("CREATE TABLE x (v INTEGER)")
    j.db.execute("INSERT INTO x VALUES (1)")                       # someone else's write, not yet committed
    with pytest.raises(RuntimeError):
        with reliability.atomic(j):
            j.db.execute("INSERT INTO x VALUES (2)")
            raise RuntimeError("fail inside")
    assert [v for (v,) in j.db.execute("SELECT v FROM x")] == [1]
    with reliability.atomic(j):
        j.db.execute("INSERT INTO x VALUES (3)")
    other = sqlite3.connect(str(tmp_path / "jarvis.sqlite"))       # committed: another connection sees it
    assert [v for (v,) in other.execute("SELECT v FROM x ORDER BY v")] == [1, 3]


def test_a_bold_pick_and_its_trades_are_saved_together_or_not_at_all(tmp_path, monkeypatch, _fresh):
    from jarvis.service import bold
    from tests.test_bold import _ready, _reply

    j = _ready(tmp_path, monkeypatch, dial=1.0)
    j.db.execute(ASK_DDL)
    bold._table(j)
    j.db.execute(FAIL_TRIGGER.format(t="bold_decisions"))
    with pytest.raises(sqlite3.Error):
        bold.run(j, call=lambda u: _reply())
    assert j.db.execute("SELECT COUNT(*) FROM evidence_trades").fetchone()[0] == 0
    assert len(_fresh) == 1 and "bold pick" in _fresh[0][0]
    assert j.db.execute("SELECT COUNT(*) FROM ask_messages WHERE thread='bold'").fetchone()[0] == 1   # still counted as paid
    j.db.execute("DROP TRIGGER fail_bold_decisions")
    r = bold.run(j, call=lambda u: _reply())
    row = j.db.execute("SELECT trade_id, random_id FROM bold_decisions WHERE id=?", (r["id"],)).fetchone()
    got = dict(j.db.execute("SELECT id, watch FROM evidence_trades").fetchall())
    assert got[row[0]] == "JARVIS_BOLD" and got[row[1]] == "RANDOM_BOLD" and row == (r["trade_id"], r["random_id"])


# ---------------------------------------------------------------------------- 3. the stance asks once more
CUT_OFF = ('{"view":"Bitcoin is OPEN on the dial","changed":"unchanged","positions":[{"coin":"LINK","trade_id":"4e28c49214e8",'
           '"status":"WEAKER","why":"Price 12.03 is under"},{"coin":"PEPE","trade_id":"4218eb7383a0","status":"WEAKER","why":"Down 3.25%, '
           'now 1.2% under its 50-day. The stop at 3.55')            # Oct 18-19: cut off at MAX_TOKENS in the middle of positions


def _stance(monkeypatch, tmp_path):
    from jarvis.service import stance
    from tests.test_stance import T0, _fake

    j = _fake(monkeypatch, tmp_path, T0 + 600)
    j.db.execute(ASK_DDL)
    monkeypatch.setattr(stance, "_may_call", lambda jj: (True, ""))
    return j


def test_the_oct_18_reply_is_named_as_cut_off():
    from jarvis.service import stance

    with pytest.raises(ValueError, match=r"the reply has no view \(it was cut off\)"):
        stance._parse(CUT_OFF)


def test_an_unreadable_stance_is_asked_once_more_with_a_stricter_format(monkeypatch, tmp_path, capsys):
    from jarvis.service import stance
    from tests.test_stance import REPLY

    j = _stance(monkeypatch, tmp_path)
    asks = []

    def call(user):
        asks.append(user)
        return (CUT_OFF if len(asks) == 1 else json.dumps(REPLY)), {"in": 5000, "out": 800, "model": "fake"}
    r = stance.plan(j, call=call)
    assert len(asks) == 2 and "could not be read (the reply has no view (it was cut off))" in asks[1]
    assert "ONLY the JSON" in asks[1] and asks[1].startswith(asks[0])
    assert r["source"] == "brain" and r["view"].startswith("The dial is open") and len(r["expectations"]) == 3
    assert r["cost_usd"] == pytest.approx(0.036)                   # both calls are paid and counted
    assert j.db.execute("SELECT COUNT(*) FROM ask_messages WHERE thread='brain'").fetchone()[0] == 2   # inside the brain's day
    assert "asking once more" in capsys.readouterr().err


def test_a_second_unreadable_stance_keeps_the_facts_only_fallback_and_logs_it(monkeypatch, tmp_path, capsys):
    from jarvis.service import stance

    j = _stance(monkeypatch, tmp_path)
    asks = []
    r = stance.plan(j, call=lambda u: (asks.append(u), ("no json at all", {"in": 10, "out": 10, "model": "fake"}))[1])
    assert len(asks) == 2                                          # exactly one retry, never more
    assert r["source"] == "facts only" and r["note"].endswith("facts only (also after one retry)")
    assert stance.latest(j)["source"] == "facts only"
    assert "facts only (also after one retry)" in capsys.readouterr().err


def test_the_retry_respects_the_daily_ai_cap(monkeypatch, tmp_path):
    from jarvis.service import stance

    j = _stance(monkeypatch, tmp_path)
    caps = iter([(True, ""), (False, "the brain's AI dollar for today is used ($0.95 of $1.00): facts only, nothing new spent")])
    monkeypatch.setattr(stance, "_may_call", lambda jj: next(caps))
    asks = []
    r = stance.plan(j, call=lambda u: (asks.append(u), (CUT_OFF, {"in": 10, "out": 10, "model": "fake"}))[1])
    assert len(asks) == 1 and r["source"] == "facts only" and "no retry: the brain's AI dollar for today is used" in r["note"]


def test_a_paid_stance_that_cannot_be_saved_is_noted(monkeypatch, tmp_path, _fresh):
    from jarvis.service import stance
    from tests.test_stance import REPLY

    j = _stance(monkeypatch, tmp_path)
    stance._table(j)
    j.db.execute(FAIL_TRIGGER.format(t="expectations"))
    with pytest.raises(sqlite3.Error):
        stance.plan(j, call=lambda u: (json.dumps(REPLY), {"in": 5000, "out": 800, "model": "fake"}))
    assert stance.latest(j) is None                                # the stance and its expectations: together or not at all
    assert len(_fresh) == 1 and "stance" in _fresh[0][0]


# ---------------------------------------------------------------------------- 4. the 15-minute jobs' errors are kept
import calendar  # noqa: E402

from jarvis.service import runcheck  # noqa: E402
from jarvis.service.runcheck_parts import PARTS  # noqa: E402

NOW = calendar.timegm((2026, 10, 22, 14, 0, 0))
D0 = NOW - NOW % 86400


def _paths(tmp: Path) -> dict:
    p = {k: str(tmp / k) for k in ("agent", "runs", "repo", "worker", "backups")}
    for v in p.values():
        Path(v).mkdir(parents=True, exist_ok=True)
    return p


def _part(pid: str) -> dict:
    return dict(next(x for x in PARTS if x["id"] == pid))


def test_every_non_empty_error_of_a_run_is_kept_with_its_utc_time(tmp_path):
    f = tmp_path / "jobs_steps.jsonl"
    out = {"fired": [], "zones": {}, "news_error": "HTTPError 503", "stance_error": "", "brain_error": None,
           "tier30_error": "database is locked"}
    line = reliability.record_job_errors(out, now=NOW, path=f)
    assert line == {"t": "2026-10-22 14:00:00", "n": 6, "errors": {"news_error": "HTTPError 503", "tier30_error": "database is locked"}}
    reliability.record_job_errors({"fired": []}, now=NOW + 900, path=f)
    rows = [json.loads(x) for x in f.read_text().splitlines()]
    assert [r["errors"] for r in rows] == [line["errors"], {}]


def test_the_loop_records_every_run_and_survives_a_failed_run():
    src = (ROOT / "jarvis" / "service" / "app.py").read_text()
    loop = src.split("def _snapshots")[1].split("@app.on_event")[0]
    assert "jobs_out = background_jobs()" in loop and "reliability.record_job_errors(jobs_out)" in loop
    assert '"background_jobs_error"' in loop


def _jobs_file(paths: dict, errs: dict[int, dict], skip_before: int) -> None:
    lines = []
    for t in range(skip_before, NOW + 1, 900):
        lines.append(json.dumps({"t": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(t + 20)), "n": 22, "errors": errs.get(t, {})}))
    Path(paths["runs"], "jobs_steps.jsonl").write_text("\n".join(lines) + "\n")


def test_the_run_checker_reports_15_minute_job_errors_and_only_from_the_first_record(tmp_path):
    paths = _paths(tmp_path)
    bad = D0 + 6 * 3600
    _jobs_file(paths, {bad: {"tier30_error": "database is locked"}, bad + 900: {"tier30_error": "database is locked"}},
               skip_before=D0 - 86400)
    res = runcheck.run(paths, NOW, [_part("jobs_steps")])
    ms = [m for m in res["windows"]["7d"]["misses"] if m["part"] == "jobs_steps"]
    assert len(ms) == 1 and ms[0]["kind"] == "errored" and ms[0]["runs"] == 2 and "tier30_error" in ms[0]["detail"]
    w7 = res["windows"]["7d"]
    assert w7["by_part"]["jobs_steps"]["expected"] < 7 * 96                  # nothing before the first line is judged
    assert "**high** Each step inside the 15-minute jobs" in runcheck.markdown(res)


def test_before_their_first_record_the_new_parts_say_why_they_cannot_be_checked(tmp_path):
    paths = _paths(tmp_path)
    md = runcheck.markdown(runcheck.run(paths, NOW, [_part("jobs_steps"), _part("outside_watchdog")]))
    assert "Cannot be checked (no dated proof):**" in md and "jobs_steps.jsonl not written yet" in md
    assert "watchdog.log has no dated line yet" in md


# ---------------------------------------------------------------------------- 5. the outside watchdog and the health loop, dated
def _wd():
    import importlib.util

    spec = importlib.util.spec_from_file_location("wd", ROOT / "scripts" / "jarvis_watchdog.py")
    wd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wd)
    return wd


def test_watchdog_log_lines_carry_their_utc_time_and_the_checker_dates_them(tmp_path):
    wd = _wd()
    ln = wd.line({"result": "ok", "detail": "answers", "sent": None}, now=NOW)
    assert ln == '[2026-10-22 14:00:00 UTC] {"result": "ok", "detail": "answers", "sent": null}'
    paths = _paths(tmp_path)
    looks = [t for t in range(NOW - 2 * 86400, NOW + 1, 300) if not (D0 + 3600 <= t < D0 + 3 * 3600)]   # 2 hours with no look
    Path(paths["runs"], "watchdog.log").write_text(
        '{"result": "ok", "detail": "answers", "sent": null}\n' * 3                     # the old undated lines are ignored
        + "\n".join(wd.line({"result": "ok"}, now=t + 7) for t in looks) + "\n")
    res = runcheck.run(paths, NOW, [_part("outside_watchdog")])
    ms = [m for m in res["windows"]["7d"]["misses"] if m["part"] == "outside_watchdog"]
    assert len(ms) == 1 and ms[0]["kind"] == "no run" and ms[0]["runs"] == 12 and ms[0]["t"] == D0 + 3600
    assert res["windows"]["7d"]["by_part"]["outside_watchdog"]["expected"] < 7 * 144


def test_the_health_watchdog_records_its_last_round_and_the_checker_reads_it(tmp_path):
    from jarvis.service import health
    from tests.test_jarvis_brain import _j

    now = {"t": NOW - 120}
    j = _j(tmp_path, now)
    health.watch(j, push=None, get=lambda url, timeout=5: (200, {"ok": True}), now=now["t"])
    row = j.db.execute("SELECT ok, fails, last_push, detail FROM health_state WHERE part='_last_check'").fetchone()
    assert row[2] == NOW - 120 and row[1] >= 1 and row[3] == "2026-10-22 13:58:00 UTC"
    assert "_last_check" not in health.status(j)["parts"]                       # not a part of Ananta: never shown as one
    paths = _paths(tmp_path)
    con = sqlite3.connect(paths["agent"] + "/jarvis.sqlite")
    con.execute("CREATE TABLE health_state (part TEXT PRIMARY KEY, ok INTEGER, fails INTEGER, down_t INTEGER, last_push INTEGER, detail TEXT)")
    con.execute("INSERT INTO health_state VALUES (?,?,?,?,?,?)", ("_last_check", *row[:2], None, *row[2:]))
    con.commit()
    assert runcheck.run(paths, NOW, [_part("health_loop")])["windows"]["24h"]["misses"] == []
    con.execute("UPDATE health_state SET last_push=? WHERE part='_last_check'", (NOW - 3600,))     # silent for an hour
    con.commit()
    ms = runcheck.run(paths, NOW, [_part("health_loop")])["windows"]["24h"]["misses"]
    assert len(ms) == 1 and ms[0]["kind"] == "no run"


def test_the_three_parts_are_no_longer_listed_as_without_dated_proof():
    ids = {p["id"]: p for p in PARTS}
    for pid in ("outside_watchdog", "health_loop", "jobs_steps"):
        assert "none" not in ids[pid]["proof"] and ids[pid]["from_first"]
