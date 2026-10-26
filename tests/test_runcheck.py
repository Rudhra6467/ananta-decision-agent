"""The run checker (jarvis/service/runcheck.py) on synthetic data: it must catch what the health watchdog and the morning review
missed in October (Oct 20 silent-failure audit), say "none" when nothing is missed, and never write anything."""
import calendar
import hashlib
import re
import sqlite3
from pathlib import Path

import pytest

from jarvis.service import runcheck
from jarvis.service.runcheck_parts import PARTS

ROOT = Path(__file__).resolve().parents[1]
DAY = 86400
NOW = calendar.timegm((2026, 10, 20, 14, 0, 0))          # Oct 20, 10:00 Toronto
D0 = NOW - NOW % DAY                                       # Oct 20 00:00 UTC


def _paths(tmp: Path) -> dict:
    p = {k: str(tmp / k) for k in ("agent", "runs", "repo", "worker", "backups", "india")}
    for v in p.values():
        Path(v).mkdir(parents=True, exist_ok=True)
    return p


def _db(path: str, ddl: list[str], rows: dict[str, list[tuple]] | None = None) -> None:
    con = sqlite3.connect(path)
    for d in ddl:
        con.execute(d)
    for table, rs in (rows or {}).items():
        if rs:
            con.executemany(f"INSERT INTO {table} VALUES ({','.join('?' * len(rs[0]))})", rs)
    con.commit()
    con.close()


def _part(pid: str, **over) -> dict:
    p = dict(next(x for x in PARTS if x["id"] == pid))
    p.update(over)
    return p


def _misses(res: dict, window: str = "7d", part: str | None = None) -> list[dict]:
    return [m for m in res["windows"][window]["misses"] if part is None or m["part"] == part]


BRAIN_DDL = ["CREATE TABLE ask_messages (id TEXT, thread TEXT, t INTEGER, note TEXT, ms INTEGER, cost_usd REAL)",
             "CREATE TABLE brain_decisions (id TEXT, t INTEGER, coin TEXT, action TEXT, note TEXT)",
             "CREATE TABLE brain_queue (id TEXT, t INTEGER, coin TEXT, trigger TEXT, detail TEXT, state TEXT)"]


def _brain(paths: dict, lost_day: int | None = None, n_lost: int = 207) -> None:
    """Six healthy days of 40 paid calls and 40 saved decisions; on lost_day every call is paid and nothing is saved (Oct 15)."""
    ask, dec, q = [], [], []
    for d in range(8):
        day = D0 - d * DAY
        n = n_lost if day == lost_day else 40
        for i in range(n):
            t = day + 300 + i * 120
            ask.append((f"a{d}-{i}", "brain", t, "decision brain", 4000, 0.0206))
            q.append((f"q{d}-{i}", t - 60, "ADA", "zone_entry", "{}",
                      "FAILED: table brain_decisions has 20 columns but 18 values were supplied" if day == lost_day else "DONE"))
            if day != lost_day:
                dec.append((f"d{d}-{i}", t + 5, "ADA", "PASS", None))
    _db(paths["agent"] + "/jarvis.sqlite", BRAIN_DDL, {"ask_messages": ask, "brain_decisions": dec, "brain_queue": q})


# ---------------------------------------------------------------------------- the schedule
def test_instants_follow_the_schedule_in_its_own_time_zone():
    every = runcheck.instants({"every": 900}, D0, D0 + 3600)
    assert every == [D0, D0 + 900, D0 + 1800, D0 + 2700, D0 + 3600]
    tor = runcheck.instants({"daily": "07:25", "tz": "America/Toronto"}, D0 - 2 * DAY, D0 + DAY)
    assert [calendar.timegm(time_t) % DAY for time_t in [__import__("time").gmtime(t) for t in tor]] == [11 * 3600 + 25 * 60] * 3   # EDT
    weekdays = runcheck.instants({"daily": "12:30", "tz": "America/Toronto", "days": "01234"}, D0 - 7 * DAY, D0)
    assert len(weekdays) == 5                                                    # Mon-Fri only
    sundays = runcheck.instants({"weekly": 6, "at": "00:00", "tz": "UTC"}, D0 - 14 * DAY, D0)
    assert all(__import__("time").gmtime(t).tm_wday == 6 for t in sundays) and len(sundays) == 2


# ---------------------------------------------------------------------------- the Oct 14-15 incident
def test_paid_brain_calls_without_saved_decisions_are_reported_as_lost(tmp_path):
    """The exact failure: every decide() paid for its model call, then the INSERT raised; process() caught it. The brain loop stayed
    alive the whole time, so a liveness check sees nothing; the reconcile sees 207 paid calls and 0 saved decisions."""
    paths = _paths(tmp_path)
    lost = D0 - 5 * DAY
    _brain(paths, lost_day=lost)
    parts = [_part("brain_saved"), _part("brain_failed"), _part("brain_decides")]
    res = runcheck.run(paths, NOW, parts)
    lost_m = _misses(res, part="brain_saved")
    assert len(lost_m) == 1 and lost_m[0]["kind"] == "lost" and lost_m[0]["t"] == lost
    assert "207 paid calls, 0 saved decisions: 207 lost (that day's calls cost $4.26)" in lost_m[0]["detail"]
    failed = _misses(res, part="brain_failed")
    assert len(failed) == 1 and failed[0]["kind"] == "errored" and "20 columns but 18 values" in failed[0]["detail"]
    assert failed[0]["detail"].startswith("207x")
    empty = _misses(res, part="brain_decides")
    assert [m["kind"] for m in empty] == ["empty"]                               # no decision that day: ran, did nothing
    md = runcheck.markdown(res)
    assert "**high** Brain: every paid decision call has a saved decision: **lost**" in md
    assert not _misses(res, "24h")                                               # the incident is older than a day


def test_a_healthy_brain_is_not_flagged(tmp_path):
    paths = _paths(tmp_path)
    _brain(paths)
    res = runcheck.run(paths, NOW, [_part("brain_saved"), _part("brain_failed"), _part("brain_decides"), _part("brain_stuck")])
    assert _misses(res) == [] and _misses(res, "24h") == []
    assert res["windows"]["7d"]["ok"] == res["windows"]["7d"]["expected"] > 0


def test_a_retry_after_an_unreadable_reply_is_not_a_lost_decision(tmp_path):
    """decide() asks once more when a reply cannot be read and logs that second call with ms=0: one decision, two calls."""
    paths = _paths(tmp_path)
    _brain(paths)
    con = sqlite3.connect(paths["agent"] + "/jarvis.sqlite")
    con.execute("INSERT INTO ask_messages VALUES ('retry', 'brain', ?, 'decision brain', 0, 0.02)", (D0 - DAY + 400,))
    con.commit()
    con.close()
    assert _misses(runcheck.run(paths, NOW, [_part("brain_saved")])) == []


# ---------------------------------------------------------------------------- the Explorer: gaps, errors, empty scans
def _explorer_log(paths: dict, skip: set[int] = frozenset(), special: dict | None = None) -> None:
    lines = []
    t = NOW - 8 * DAY
    t -= t % 900
    while t <= NOW:
        if t not in skip:
            stamp = __import__("time").strftime("%Y-%m-%d %H:%M", __import__("time").gmtime(t + 60))
            scans, errs = (special or {}).get(t, (10, "[]"))
            lines.append(f"[{stamp}] scans={scans} open=0 pending=0 equity=1736.44 errors={errs}")
        t += 900
    Path(paths["runs"], "explorer_live.log").write_text("\n".join(lines) + "\n")


def test_explorer_gap_error_and_empty_scan_are_each_reported(tmp_path):
    paths = _paths(tmp_path)
    gap0 = D0 - 3 * DAY + 6 * 3600                                               # a 2-hour hole: 8 scans
    err_t, empty_t = D0 - 2 * DAY, D0 - DAY + 900
    _explorer_log(paths, skip={gap0 + i * 900 for i in range(8)},
                  special={err_t: (0, "['kill switch unreadable: LOGIN_FAILED']"), empty_t: (7, "[]")})
    res = runcheck.run(paths, NOW, [_part("explorer_scans")])
    by = {m["kind"]: m for m in _misses(res)}
    assert set(by) == {"no run", "errored", "empty"}
    assert by["no run"]["runs"] == 8 and by["no run"]["t"] == gap0                # merged into one line
    assert "LOGIN_FAILED" in by["errored"]["detail"]
    assert by["empty"]["found"] == 7 and by["empty"]["needed"] == 10
    assert "did 7 of at least 10" in runcheck.markdown(res)


# ---------------------------------------------------------------------------- a daily review that silently stopped
def test_missed_move_review_skipped_on_days_is_reported(tmp_path):
    """Oct 9-19: the universe review wrote its rows first and the live-10 review returned 'done before' on 9 of 11 days."""
    paths = _paths(tmp_path)
    keys = [(f"missed:{__import__('time').strftime('%Y-%m-%d', __import__('time').gmtime(D0 - d * DAY))}", "3") for d in (2, 7)]
    _db(paths["agent"] + "/jarvis.sqlite", ["CREATE TABLE engine_state (k TEXT PRIMARY KEY, v TEXT)"],
        {"engine_state": keys + [("missed:flag:breakout|no zone|ALLOWED:UNIV", "38")]})
    res = runcheck.run(paths, NOW, [_part("missed_live")])
    ms = _misses(res)
    # the reviews of Oct 13 and Oct 18 ran (at Oct 14 and Oct 19, 00:30 UTC); those due Oct 15-18 and Oct 20 did not
    assert [(m["kind"], m["runs"]) for m in sorted(ms, key=lambda m: m["t"])] == [("no run", 4), ("no run", 1)]


# ---------------------------------------------------------------------------- files: backups, review pages, the nightly page
def test_file_proofs_missing_small_and_failed_steps(tmp_path):
    paths = _paths(tmp_path)
    for d in range(0, 8):
        day = __import__("time").strftime("%Y-%m-%d", __import__("time").gmtime(D0 - d * DAY))
        if d != 3:                                                                # one night without a backup
            (Path(paths["backups"]) / day).mkdir()
            Path(paths["backups"], day, "jarvis.sqlite").write_bytes(b"\0" * (2_000_000 if d != 5 else 10))
        page = Path(paths["repo"], "docs/repair_shop/daily")
        page.mkdir(parents=True, exist_ok=True)
        steps = "book500, officer" if d == 1 else "none"
        (page / f"universe_{day}.md").write_text("# Universe round\n" + "x" * 300 + f"\n- steps that failed tonight: {steps}\n")
        (page / f"{day}.md").write_text("# Review\n\n## Overnight\nok\n" if d != 2 else "# Review\n\nhalf a page\n")
    res = runcheck.run(paths, NOW, [_part("backup"), _part("universe_page"), _part("morning_review")])
    got = {(m["part"], m["kind"]) for m in _misses(res)}
    assert ("backup", "no run") in got and ("backup", "empty") in got             # missing night, and a 10-byte copy
    assert ("universe_page", "errored") in got
    assert any("book500, officer" in m["detail"] for m in _misses(res, part="universe_page"))
    assert ("morning_review", "empty") in got                                     # no "## Overnight"


# ---------------------------------------------------------------------------- since, latest-only, outages, the worker's late days
def test_a_part_is_not_expected_before_its_first_day(tmp_path):
    paths = _paths(tmp_path)
    _db(paths["agent"] + "/jarvis.sqlite", ["CREATE TABLE bold_decisions (t INTEGER)"], {"bold_decisions": [(D0 + 600,), (D0 - DAY + 600,)]})
    since = __import__("time").strftime("%Y-%m-%d", __import__("time").gmtime(D0 - DAY))
    res = runcheck.run(paths, NOW, [_part("bold", since=since)])
    assert res["windows"]["7d"]["expected"] == 2 and _misses(res) == []


def test_latest_only_parts_judge_the_current_value(tmp_path):
    paths = _paths(tmp_path)
    state = '{"last_step_t": %d, "cash": 199.4}' % (D0 - DAY + 300)               # stepped yesterday, not after today's close
    rules = [(f"last_t:H07,M1a,M2a,RANDOM_10D:C{i}", str(D0 - DAY if i < 9 else D0 - 4 * DAY)) for i in range(10)]
    _db(paths["agent"] + "/jarvis.sqlite", ["CREATE TABLE book500 (k TEXT PRIMARY KEY, v TEXT)", "CREATE TABLE engine_state (k TEXT, v TEXT)"],
        {"book500": [("state", state)], "engine_state": rules})
    res = runcheck.run(paths, NOW, [_part("book500"), _part("lab10_rules")])
    by = {m["part"]: m for m in _misses(res, "24h")}
    assert by["book500"]["kind"] == "no run"
    assert by["lab10_rules"]["kind"] == "empty" and by["lab10_rules"]["found"] == 9  # one coin's rules stopped 4 days ago



def test_lab10_rules_count_once_per_coin_whatever_watch_sorts_first(tmp_path):
    # Oct 25: BRK and RBD joined the lab watches on Oct 24, the key became 'last_t:BRK,H07,M1a,...,RBD:<coin>'
    # and the old proof (k LIKE 'last_t:H07,M1a,%') read a full night as 0 of 10.
    paths = _paths(tmp_path)
    rules = [(f"last_t:BRK,H07,M1a,M2a,RANDOM_10D,RBD:C{i}", str(D0 - DAY)) for i in range(10)]
    rules += [(f"last_t:BRK,H07,M1a,M2a,RANDOM_10D:C{i}", str(D0 - DAY)) for i in range(10)]        # an older key set, same night
    rules += [(f"last_t:H07,M1a,M2a,RANDOM_10D:C{i}", str(D0 - 9 * DAY)) for i in range(10)]        # stale, from before
    rules += [(f"last_t:BRK-UA,H07-UA,M1a-UA:X{i}", str(D0 - DAY)) for i in range(30)]             # tier A, not the lab 10
    _db(paths["agent"] + "/jarvis.sqlite", ["CREATE TABLE engine_state (k TEXT, v TEXT)"], {"engine_state": rules})
    res = runcheck.run(paths, NOW, [_part("lab10_rules")])
    assert "lab10_rules" not in {m["part"] for m in _misses(res, "24h")}

def test_outages_are_listed_with_their_minutes(tmp_path):
    paths = _paths(tmp_path)
    _db(paths["agent"] + "/jarvis.sqlite", ["CREATE TABLE health_log (id INTEGER, part TEXT, down_t INTEGER, up_t INTEGER, detail TEXT)"],
        {"health_log": [(1, "hands", D0 - 3 * DAY, D0 - 3 * DAY + 425 * 60, "no answer (ConnectionError)"),
                        (2, "worker", NOW - 1200, None, "ssh: Host is down"), (3, "tunnel", D0 - 30 * DAY, D0 - 30 * DAY + 60, "")]})
    res = runcheck.run(paths, NOW, [_part("health_outages")])
    ms = _misses(res)
    assert len(ms) == 2 and {m["kind"] for m in ms} == {"down"}
    assert any("hands: 425 min" in m["detail"] for m in ms) and any("still down" in m["detail"] for m in ms)


def test_many_outages_of_one_part_become_one_line(tmp_path):
    """Oct 16-20: the worker's SSH link dropped 14 times; one line per part keeps the rest of the list readable."""
    paths = _paths(tmp_path)
    rows = [(i, "worker", D0 - 5 * DAY + i * 7200, D0 - 5 * DAY + i * 7200 + (880 * 60 if i == 3 else 1200), "ssh: Host is down")
            for i in range(1, 6)] + [(9, "hands", D0 - 3 * DAY, D0 - 3 * DAY + 425 * 60, "no answer")]
    _db(paths["agent"] + "/jarvis.sqlite", ["CREATE TABLE health_log (id INTEGER, part TEXT, down_t INTEGER, up_t INTEGER, detail TEXT)"],
        {"health_log": rows})
    ms = _misses(runcheck.run(paths, NOW, [_part("health_outages")]))
    assert len(ms) == 2
    w = next(m for m in ms if m.get("sub") == "worker")
    assert w["runs"] == 5 and "5 outages, 960 min in all; the longest 880 min" in w["detail"]


def test_worker_days_are_judged_only_once_they_have_arrived(tmp_path):
    paths = _paths(tmp_path)
    for d in range(1, 8):                                                        # Oct 13-19: yesterday's day arrived with the 03:40 pull
        day0 = D0 - d * DAY
        n = 900 if d == 4 else 1440
        _db(f"{paths['worker']}/l1_{__import__('time').strftime('%Y-%m-%d', __import__('time').gmtime(day0))}.sqlite",
            ["CREATE TABLE ndax (t INTEGER, coin TEXT)", "CREATE TABLE site (t INTEGER, ok INTEGER)"],
            {"ndax": [(day0 + 60 * i, "BTC") for i in range(n)], "site": [(day0 + 60 * i, 1) for i in range(1440)]})
    res = runcheck.run(paths, NOW, [_part("worker_minutes"), _part("public_site")])
    assert res["windows"]["24h"]["misses"] == []
    assert any("worker" in n["name"].lower() for n in res["windows"]["24h"]["not_checked"])     # said, not silently skipped
    ms = _misses(res)
    assert len(ms) == 1 and ms[0]["part"] == "worker_minutes" and ms[0]["kind"] == "empty" and ms[0]["found"] == 900


def test_india_job_that_wrote_stderr_during_its_run_is_errored(tmp_path):
    import os
    paths = _paths(tmp_path)
    run_t = calendar.timegm((2026, 10, 19, 23, 0, 0))                             # Oct 19 19:00 Toronto
    log, err = Path(paths["runs"], "india_evening.log"), Path(paths["runs"], "india_evening.err")
    log.write_text("# Ananta India daily report\n")
    err.write_text("india.kite.NeedLogin: Kite token rejected (TokenException): sign in again\n")
    os.utime(log, (run_t + 78, run_t + 78))
    os.utime(err, (run_t + 6, run_t + 6))
    res = runcheck.run(paths, NOW, [_part("india_evening")])
    ms = _misses(res, "24h")
    assert len(ms) == 1 and ms[0]["kind"] == "errored" and ms[0]["area"] == "india"
    assert "**India, last 24 hours: 1 miss**" in runcheck.markdown(res) and "india_evening.err written during the run" in runcheck.markdown(res)


def test_india_job_whose_stderr_holds_only_its_own_start_line_is_not_errored(tmp_path):
    import os
    paths = _paths(tmp_path)
    run_t = calendar.timegm((2026, 10, 19, 23, 0, 0))                             # Oct 19 19:00 Toronto
    log, err = Path(paths["runs"], "india_evening.log"), Path(paths["runs"], "india_evening.err")
    log.write_text("# Ananta India daily report\n")
    err.write_text("=== 2026-10-18_19:00:04 evening\nTraceback (most recent call last):\nindia.kite.NeedLogin: old run\n=== 2026-10-19_19:00:04 evening\n")
    os.utime(log, (run_t + 78, run_t + 78))
    os.utime(err, (run_t + 4, run_t + 4))
    assert _misses(runcheck.run(paths, NOW, [_part("india_evening")]), "24h") == []
    err.write_text(err.read_text() + "TypeError: unsupported format string passed to NoneType.__format__\n")
    os.utime(err, (run_t + 6, run_t + 6))
    ms = _misses(runcheck.run(paths, NOW, [_part("india_evening")]), "24h")
    assert len(ms) == 1 and ms[0]["kind"] == "errored"


def _india_calendar(paths: dict, holidays: list[str]) -> None:
    import json
    p = Path(paths["india"], "manifests", "nse_holidays_2026.json")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"CM": [{"tradingDate": h, "weekDay": "", "description": "test"} for h in holidays]}))
    runcheck._HOLIDAYS.clear()


def test_india_sp1_session_lost_to_a_dead_token_is_a_high_errored_miss_named_by_its_ist_date(tmp_path):
    """Oct 21-23: three IST sessions wrote only an error row ("no Kite sign-in by 09:10 IST"). Before Oct 23 the checker saw the
    SP1 job's latest log only; now every session day needs decision rows, named by the session's IST date, and Oct 20 (an NSE
    holiday) is not expected."""
    paths = _paths(tmp_path)
    _india_calendar(paths, ["20-Oct-2026"])
    f = Path(paths["india"], "paper", "sp1", "decisions.jsonl")
    f.parent.mkdir(parents=True)
    rows = ['{"kind": "plan", "date": "2026-10-16", "at": "2026-10-16T09:15:00+05:30", "x": 1}',
            '{"kind": "decision", "date": "2026-10-16", "at": "2026-10-16T09:30:00+05:30", "x": 1}',
            '{"kind": "decision", "date": "2026-10-19", "at": "2026-10-19T09:15:00+05:30", "x": 1}',
            '{"kind": "error", "date": "2026-10-20", "at": "2026-10-20T09:10:07+05:30", "error": "no Kite sign-in by 09:10 IST: the Kite token expired at 6 am IST", "prev_hash": "a"}']
    f.write_text("\n".join(rows) + "\n")
    now = calendar.timegm((2026, 10, 20, 14, 0, 0))                                # Oct 20 10:00 Toronto = 19:30 IST
    res = runcheck.run(paths, now, [_part("india_sp1_session", since="2026-10-15")])
    ms = _misses(res)
    # Oct 15 (Thu) has no rows -> no run; Oct 16 and 19 are fine; Oct 20 is a holiday and its error row is not a session
    assert [(m["kind"], m["severity"]) for m in ms] == [("no run", "high")]
    assert res["windows"]["7d"]["by_area"]["india"] == {"expected": 3, "ok": 2}
    md = runcheck.markdown(res)
    assert "IST session Oct 15" in md and "**India, last 7 days: 1 miss**" in md and "**Last 7 days: none.**" in md

    _india_calendar(paths, [])                                                     # without the holiday, the error row is an errored session
    res = runcheck.run(paths, now, [_part("india_sp1_session", since="2026-10-15")])
    kinds = sorted(m["kind"] for m in _misses(res))
    assert kinds == ["errored", "no run"] and any("no Kite sign-in by 09:10 IST" in m["detail"] for m in _misses(res))


def test_india_session_files_are_judged_per_session_day(tmp_path):
    """The read model, the decision journal and the ledger snapshot are one dated file per session; a missing or thin file is a miss,
    a read model with a missing section is an empty run."""
    import json
    paths = _paths(tmp_path)
    _india_calendar(paths, [])
    rm = Path(paths["india"], "readmodel"); rm.mkdir(parents=True)
    led = Path(paths["india"], "bronze", "ledger"); led.mkdir(parents=True)
    for d in ("2026-10-15", "2026-10-16", "2026-10-19"):
        rm.joinpath(f"{d}.json").write_text(json.dumps({"data_through": d, "missing": [] if d != "2026-10-19" else ["sp1"], "pad": "x" * 2500}))
        led.joinpath(f"{d}.json").write_text(json.dumps({"holdings": [], "pad": "x" * 1200}))
    now = calendar.timegm((2026, 10, 20, 14, 0, 0))
    res = runcheck.run(paths, now, [_part("india_readmodel", since="2026-10-16"), _part("india_ledger", since="2026-10-16")])
    ms = _misses(res)
    assert [(m["part"], m["kind"]) for m in ms] == [("india_readmodel", "empty")]   # Oct 20's files are not due yet; Oct 19's read model misses a section
    assert any("no '\"missing\": []'" in m["detail"] for m in ms if m["part"] == "india_readmodel")
    assert res["windows"]["7d"]["by_area"]["india"]["ok"] == 4


def test_holiday_calendar_is_read_from_the_lake_and_absent_means_weekdays(tmp_path):
    paths = _paths(tmp_path)
    runcheck._HOLIDAYS.clear()
    assert runcheck.holidays(paths) == frozenset()                                 # no file: nothing skipped, nothing raised
    _india_calendar(paths, ["20-Oct-2026", "08-Nov-2026"])
    assert runcheck.holidays(paths) == {"2026-10-20", "2026-11-08"}
    cad = {"daily": "09:15", "tz": "Asia/Kolkata", "days": "01234", "skip": runcheck.holidays(paths)}
    days = runcheck.instants(cad, calendar.timegm((2026, 10, 18, 0, 0, 0)), calendar.timegm((2026, 10, 23, 0, 0, 0)))
    assert len(days) == 3                                                          # Mon 19, Wed 21, Thu 22: Tue 20 is the holiday


# ---------------------------------------------------------------------------- the review section, read-only, a missing source
def test_the_section_is_never_omitted_and_says_none(tmp_path):
    paths = _paths(tmp_path)
    _brain(paths)
    md = runcheck.markdown(runcheck.run(paths, NOW, [_part("brain_saved"), _part("outside_watchdog")]))
    assert md.startswith("## Lost or empty runs\n")
    assert "**Last 24 hours: none.**" in md and "**Last 7 days: none.**" in md
    assert "Cannot be checked (no dated proof):** Outside watchdog" in md          # listed every time, never dropped
    assert "**India, last 24 hours: none.**" in md and "**India, last 7 days: none.**" in md


def test_the_checker_never_writes(tmp_path):
    paths = _paths(tmp_path)
    _brain(paths, lost_day=D0 - 2 * DAY)
    db = Path(paths["agent"], "jarvis.sqlite")
    before = (hashlib.sha256(db.read_bytes()).hexdigest(), db.stat().st_mtime_ns, sorted(p.name for p in db.parent.iterdir()))
    runcheck.run(paths, NOW)                                                      # every part, most of them without their files
    assert (hashlib.sha256(db.read_bytes()).hexdigest(), db.stat().st_mtime_ns, sorted(p.name for p in db.parent.iterdir())) == before
    con = runcheck._ro(str(db))
    with pytest.raises(sqlite3.OperationalError):
        con.execute("INSERT INTO brain_decisions VALUES ('x', 1, 'BTC', 'PASS', NULL)")
    with pytest.raises(FileNotFoundError):
        runcheck._ro(str(tmp_path / "nothing_here.sqlite"))
    assert not (tmp_path / "nothing_here.sqlite").exists()                        # mode=ro never creates a database


def test_a_missing_proof_source_is_one_clear_line_not_hundreds(tmp_path):
    paths = _paths(tmp_path)
    res = runcheck.run(paths, NOW, [_part("universe_5m")])
    ms = _misses(res)
    assert len(ms) == 1 and ms[0]["kind"] == "no proof" and "no database" in ms[0]["detail"]


# ---------------------------------------------------------------------------- the list itself
LAUNCHD = ["com.ananta.jarvis", "com.ananta.explorer", "com.ananta.website", "com.ananta.voice", "com.ananta.telugu", "com.ananta.tunnel",
           "com.ananta.awake", "com.ananta.watchdog", "com.ananta.backup", "com.ananta.mongoarchive", "com.ananta.lake",
           "com.ananta.india.evening", "com.ananta.india.nightly", "com.ananta.india.paper", "com.ananta.india.recorder_noon",
           "com.ananta.india.sp1paper", "com.ananta.india.sp1paper.score", "com.ananta.india.spreads", "com.ananta.india.autologin"]


def test_every_part_is_well_formed():
    ids = [p["id"] for p in PARTS]
    assert len(ids) == len(set(ids))
    for p in PARTS:
        assert p["name"] and p["job"] and p["severity"] in ("high", "medium", "low"), p["id"]
        assert set(p["cadence"]) & {"every", "daily", "weekly"}, p["id"]
        pr = p["proof"]
        assert len(set(pr) & {"sql", "log", "files", "sqlite_files", "reconcile", "outages", "mtime", "none"}) == 1, p["id"]
        if set(pr) & {"sql", "log", "sqlite_files"} and not p.get("errors_only"):
            assert p.get("min_work", 0) >= 1, f"{p['id']}: a proof must name the least work a run does"
        if "log" in pr:
            assert re.compile(pr["regex"]).groupindex.keys() & {"t", "d"}, p["id"]


def test_every_job_in_the_lock_and_in_launchd_has_a_part():
    lock = (ROOT / "docs" / "LOCK.md").read_text()
    sec2 = lock.split("## 2.")[1].split("## 3.")[0]
    named = set(re.findall(r"com\.ananta\.[a-z0-9_.]*[a-z0-9]", sec2)) | set(LAUNCHD)
    jobs = " ".join(p["job"] for p in PARTS)
    missing = sorted(n for n in named if not re.search(re.escape(n) + r"(?![a-z0-9_.])", jobs))
    assert not missing, f"no part checks: {missing}"
    for words in ("worker Mac", "07:25", "15-minute", "daily close"):
        assert words.lower() in (lock.lower()), words                            # the moments LOCK section 2 lists


def test_every_query_runs_against_the_live_column_names(tmp_path):
    """The columns below are the live ones (read from the Mac on Oct 20); a typo in a proof query would show as 'no proof'."""
    paths = _paths(tmp_path)
    _db(paths["agent"] + "/jarvis.sqlite", BRAIN_DDL + [
        "CREATE TABLE stance (day TEXT, t INTEGER, dial REAL, view TEXT, changed TEXT, facts_diff TEXT, positions TEXT, facts TEXT, source TEXT, "
        "model TEXT, cost_usd REAL, note TEXT)",
        "CREATE TABLE bold_decisions (id TEXT, day TEXT, t INTEGER)", "CREATE TABLE snapshots (t INTEGER, v TEXT)",
        "CREATE TABLE engine_state (k TEXT PRIMARY KEY, v TEXT)", "CREATE TABLE universe_rebuilds (t INTEGER, json TEXT)",
        "CREATE TABLE rebuild_log (t INTEGER, source TEXT, match INTEGER, logged INTEGER, rebuilt INTEGER, only_live INTEGER, "
        "only_rebuilt INTEGER, detail TEXT)",
        "CREATE TABLE explorer_compare (t INTEGER)", "CREATE TABLE book500 (k TEXT PRIMARY KEY, v TEXT)",
        "CREATE TABLE daily_reviews (day TEXT, t INTEGER, text TEXT, json TEXT)", "CREATE TABLE officer_notes (day TEXT, t INTEGER, text TEXT)",
        "CREATE TABLE news_log (day TEXT, coin TEXT, t INTEGER, verdict TEXT, why TEXT, json TEXT)",
        "CREATE TABLE credit_records (day TEXT, coin TEXT, t INTEGER, close REAL, signals TEXT, detail TEXT, fwd20 REAL)",
        "CREATE TABLE briefings (id TEXT, t INTEGER, kind TEXT, day TEXT, text TEXT, json TEXT)",
        "CREATE TABLE health_log (id INTEGER, part TEXT, down_t INTEGER, up_t INTEGER, detail TEXT)",
        "CREATE TABLE health_state (part TEXT PRIMARY KEY, ok INTEGER, fails INTEGER, down_t INTEGER, last_push INTEGER, detail TEXT)"])
    _db(paths["agent"] + "/universe_bars.sqlite", ["CREATE TABLE m5 (coin TEXT, t INTEGER, o, h, l, c, v)",
                                                   "CREATE TABLE d1 (coin TEXT, t INTEGER, o, h, l, c, v, q)"])
    _db(paths["agent"] + "/tier30_bars.sqlite", ["CREATE TABLE bars (coin TEXT, t INTEGER, o, h, l, c, v)"])
    _db(paths["agent"] + "/universe_explorer.sqlite", ["CREATE TABLE events (seq INTEGER, t INTEGER, kind TEXT, coin TEXT, id TEXT, json TEXT)"])
    res = runcheck.run(paths, NOW)
    bad = [m for w in ("24h", "7d") for m in res["windows"][w]["misses"] if m["kind"] == "no proof" and "database" not in m["detail"]
           and "log at" not in m["detail"]]
    assert not bad, bad
