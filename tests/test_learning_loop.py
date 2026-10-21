"""The learning loop closed (Oct 21, decision map sections 3 and 5): lessons counted when they mature, weekly tickets filed by themselves
and never twice, the forward window's lessons sealed, the Oct 14 ticket in the ledger, and the ledger checked against the database."""
import calendar
import json
import time
from pathlib import Path

import pytest

from tests.test_universe_live import J

DAY = 86400
REPO = Path(__file__).resolve().parents[1]
SUN = calendar.timegm((2026, 10, 11, 0, 0, 0))            # a Sunday: the review of Oct 4-10 runs at this close
NOW = calendar.timegm((2026, 10, 20, 1, 0, 0))            # before the forward window opens


def _bars(n=120, end=None):
    t0 = (end or NOW) - n * DAY
    t0 -= t0 % DAY
    return [(t0 + k * DAY, 100.0, 101.0, 99.0, 100.0, 1.0) for k in range(n)]


@pytest.fixture()
def loop(tmp_path, monkeypatch):
    from jarvis.service import brain, feed, watch_engine as W
    from jarvis.service import learning as L

    monkeypatch.setattr(feed, "daily", lambda j, c: _bars())
    (tmp_path / "docs" / "repair_shop").mkdir(parents=True)
    (tmp_path / "docs" / "repair_shop" / "ledger.json").write_text(json.dumps({"tickets": [], "reviews": []}))
    monkeypatch.setattr(L, "ROOT", tmp_path)
    j = J(tmp_path, now=NOW)
    brain._table(j)
    W._table(j)
    return types_ns(j=j, L=L, W=W, n=[0])


class types_ns:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def _pair(s, t, net, twin_net, exit_after=DAY, coin="ETH", twin_status="CLOSED", status="CLOSED", action="TAKE"):
    """One brain TAKE with its trade and its random twin (or a PASS with its 5-day move when action is PASS)."""
    s.n[0] += 1
    k = s.n[0]
    if action == "PASS":
        s.j.db.execute("INSERT INTO brain_decisions (id, t, coin, action, price, plan, thesis, knowledge, after_5d_pct) VALUES (?,?,?,?,?,?,?,?,?)",
                       (f"D{k}", t, coin, "PASS", 1.0, "{}", "", "[]", net))
        s.j.db.commit()
        return f"D{k}"
    row = {c: None for c in s.W.COLS}
    row.update(id=f"T{k}", watch="JARVIS", coin=coin, source="brain", signal_t=t, signal_day=time.strftime("%Y-%m-%d", time.gmtime(t)), entry_t=t,
               entry=100.0, stop=95.0, exit_t=(t + exit_after) if status == "CLOSED" else None, exit=99.0 if status == "CLOSED" else None,
               status=status, net_usd=net if status == "CLOSED" else None, exit_why="target", detail="{}")
    s.W._insert(s.j, row)
    s.W._insert(s.j, dict(row, id=f"R{k}", watch="JARVIS_RANDOM", coin="SOL", status=twin_status, net_usd=twin_net if twin_status == "CLOSED" else None,
                          exit_t=(t + exit_after) if twin_status == "CLOSED" else None))
    s.j.db.execute("INSERT INTO brain_decisions (id, t, coin, action, price, plan, thesis, knowledge, trade_id, random_id) VALUES (?,?,?,?,?,?,?,?,?,?)",
                   (f"D{k}", t, coin, "TAKE", 100.0, "{}", "", "[]", f"T{k}", f"R{k}"))
    s.j.db.commit()
    return f"D{k}"


def _requests(s):
    return s.j.db.execute("SELECT num, text, about, by FROM owner_requests ORDER BY num").fetchall() \
        if s.j.db.execute("SELECT 1 FROM sqlite_master WHERE name='owner_requests'").fetchone() else []


# ---------------------------------------------------------------------------- 2. counted when they mature
def test_a_lesson_that_matures_after_its_weekly_review_is_counted_once_under_its_own_week(loop):
    s = loop
    d = _pair(s, SUN - 2 * DAY, -5.0, -1.0, exit_after=4 * DAY)               # bought Friday Oct 9, closed Oct 13: after the Sunday review
    s.j._now = SUN + 3 * DAY                                                  # not yet mature (needs 6 days after the last exit)
    assert s.L.count_lessons(s.j)["matured"] == 0
    s.j._now = SUN + 9 * DAY
    r = s.L.count_lessons(s.j)
    assert r["matured"] == 1 and r["late"] == 1 and r["by_kind"] == {"random beat the pick": 1}
    row = s.j.db.execute("SELECT week, lesson, late, sealed FROM learning_lessons WHERE decision_id=?", (d,)).fetchone()
    assert row == ("2026-10-11", "random beat the pick", 1, 0)                 # its own week, not the week it matured in
    assert s.L.count_lessons(s.j)["matured"] == 0                              # counted once, never again
    assert s.j.db.execute("SELECT COUNT(*) FROM engine_state WHERE k LIKE 'learning:count:%'").fetchone()[0] == 2   # one record a night


def test_open_legs_hold_the_lesson_back_and_an_unfilled_leg_lets_go_after_30_days(loop):
    s = loop
    _pair(s, SUN - 3 * DAY, -5.0, -1.0, twin_status="OPEN")
    _pair(s, SUN - 3 * DAY, -5.0, -1.0, twin_status="WAITING")
    s.j._now = SUN + 20 * DAY
    assert s.L.count_lessons(s.j)["matured"] == 0
    s.j._now = SUN + 28 * DAY
    r = s.L.count_lessons(s.j)
    assert r["matured"] == 1 and r["by_kind"] == {"none drawn": 1}             # the unfilled twin: no pair, so no pair lesson


def test_a_pass_matures_with_its_five_day_move(loop):
    s = loop
    _pair(s, SUN - 3 * DAY, 7.5, None, action="PASS")
    _pair(s, SUN - 3 * DAY, None, None, action="PASS")                        # its 5-day move not settled yet
    s.j._now = SUN + DAY
    r = s.L.count_lessons(s.j)
    assert r["matured"] == 1 and r["by_kind"] == {"missed winner": 1}


# ---------------------------------------------------------------------------- 1. tickets filed by themselves, never twice
def test_three_in_a_week_file_one_ticket_with_its_evidence_and_never_twice(loop):
    s = loop
    for k in range(3):
        _pair(s, SUN - 3 * DAY + k * 3600, -5.0 - k, -1.0, coin=["DOGE", "XRP", "LINK"][k])
    s.j._now = SUN + 9 * DAY
    r = s.L.count_lessons(s.j)
    assert [t["filed"] for t in r["tickets"]] == [True]
    reqs = _requests(s)
    assert len(reqs) == 1 and reqs[0][2] == "weekly lessons" and reqs[0][3] == "ananta-auto"
    text = reqs[0][1]
    assert "random beat the pick" in text and "DOGE" in text and "XRP" in text and "LINK" in text and "$-5.0 against the random SOL $-1.0" in text
    assert "#33" in text and "Rule B" in text
    # a fourth case matures later (same week): it joins the ticket instead of filing another
    _pair(s, SUN - 2 * DAY, -9.0, -1.0, coin="FLOKI", exit_after=3 * DAY)
    s.j._now = SUN + 12 * DAY
    r = s.L.count_lessons(s.j)
    assert r["tickets"] == [{"kind": "random beat the pick", "request": str(reqs[0][0]), "cases": 1, "weeks": {"2026-10-11": 1}, "filed": False}]
    # three more in a LATER week while the ticket is still open: they join it too (one open ticket per kind)
    for k in range(3):
        _pair(s, SUN + 4 * DAY + k * 3600, -3.0, 0.0)
    s.j._now = SUN + 20 * DAY
    s.L.count_lessons(s.j)
    assert len(_requests(s)) == 1
    assert s.j.db.execute("SELECT COUNT(*) FROM learning_lessons WHERE ticket=?", (str(reqs[0][0]),)).fetchone()[0] == 7
    assert s.L.count_lessons(s.j)["tickets"] == []                              # nothing left without a ticket


def test_after_the_ticket_is_closed_a_new_week_reaching_three_files_again(loop):
    from jarvis.service import requests_log

    s = loop
    for k in range(3):
        _pair(s, SUN - 3 * DAY + k, -5.0, -1.0)
    s.j._now = SUN + 9 * DAY
    s.L.count_lessons(s.j)
    requests_log.set_status(s.j, 1, "WONT", "pre-registered in #33")
    _pair(s, SUN + 4 * DAY, -5.0, -1.0)                                         # one case, below the bar: joins nothing, files nothing
    s.j._now = SUN + 13 * DAY
    assert s.L.count_lessons(s.j)["tickets"] == [] and len(_requests(s)) == 1
    for k in range(2):
        _pair(s, SUN + 4 * DAY + 10 + k, -5.0, -1.0)
    s.j._now = SUN + 14 * DAY
    r = s.L.count_lessons(s.j)
    assert [t["filed"] for t in r["tickets"]] == [True] and len(_requests(s)) == 2


def test_two_of_a_kind_file_nothing_and_kinds_not_in_the_ticket_list_never_file(loop):
    s = loop
    for k in range(2):
        _pair(s, SUN - 3 * DAY + k, -5.0, -1.0)
    for k in range(4):
        _pair(s, SUN - 3 * DAY + 10 + k, 5.0, -1.0)                              # pick beat random x4: not a ticket kind
    s.j._now = SUN + 9 * DAY
    r = s.L.count_lessons(s.j)
    assert r["by_kind"] == {"random beat the pick": 2, "pick beat random": 4} and r["tickets"] == [] and _requests(s) == []


def test_a_ticket_already_in_the_ledger_is_never_filed_again(loop, tmp_path):
    s = loop
    ids = [_pair(s, SUN - 3 * DAY + k, -5.0, -1.0) for k in range(3)]
    (tmp_path / "docs" / "repair_shop" / "ledger.json").write_text(json.dumps({"tickets": [
        {"id": "TK19", "lesson": "random beat the pick", "decisions": ids, "status": "WAITING_FOR_EVIDENCE"}]}))
    late = _pair(s, SUN - 2 * DAY, -7.0, -1.0, exit_after=4 * DAY)
    s.j._now = SUN + 12 * DAY
    r = s.L.count_lessons(s.j)
    assert _requests(s) == [] and r["tickets"] == [{"kind": "random beat the pick", "request": "TK19", "cases": 1, "weeks": {"2026-10-11": 1}, "filed": False}]
    assert s.j.db.execute("SELECT ticket FROM learning_lessons WHERE decision_id=?", (late,)).fetchone()[0] == "TK19"


# ---------------------------------------------------------------------------- the forward window stays blind (reviews #31, #33, #34)
def test_window_lessons_are_counted_but_not_labelled_until_the_seal_lifts(loop, monkeypatch):
    s = loop
    seen = []
    real = s.L.card
    monkeypatch.setattr(s.L, "card", lambda j, d, light=False: seen.append(d["id"]) or real(j, d, light))
    w0 = calendar.timegm((2026, 10, 21, 1, 0, 0))
    for k in range(3):
        _pair(s, w0 + k, -5.0, -1.0)                                            # decided inside the window
    old = _pair(s, SUN - 3 * DAY, -5.0, -1.0, exit_after=14 * DAY)             # decided Oct 8, exited Oct 22 inside the window (#31, #33)
    s.j._now = calendar.timegm((2026, 11, 1, 1, 0, 0))
    r = s.L.count_lessons(s.j)
    assert r["matured"] == 4 and r["sealed"] == 4 and r["by_kind"] == {} and r["tickets"] == []
    assert seen == [] and _requests(s) == []                                    # no pair compared, nothing filed
    assert s.j.db.execute("SELECT COUNT(*) FROM learning_lessons WHERE sealed=1 AND lesson IS NULL AND evidence IS NULL").fetchone()[0] == 4
    sm = s.L.lessons_summary(s.j, 0)
    assert sm["sealed_waiting"] == 4 and sm["kinds"] == {}
    s.j._now = calendar.timegm((2026, 12, 15, 0, 30, 0))                        # after the seal: labelled once, then ticketed
    r = s.L.count_lessons(s.j)
    assert r["unsealed"] == 4 and r["by_kind"] == {"random beat the pick": 4} and len(_requests(s)) == 1
    assert old in seen


# ---------------------------------------------------------------------------- the weekly review shows what matured; the nightly step
def test_the_weekly_review_lists_matured_lessons_and_tickets_filed_by_themselves(loop):
    s = loop
    for k in range(3):
        _pair(s, SUN - 3 * DAY + k, -5.0, -1.0)
    s.j._now = SUN + 9 * DAY
    s.L.count_lessons(s.j)
    r = s.L.weekly_review(s.j, write=False)
    md = s.L._markdown(r)
    assert "## Lessons that matured since the last review" in md
    assert "3 decisions' lessons matured and were counted under their own week (3 after that week's review had run): random beat the pick x3" in md
    assert "#1 (weekly lessons, OPEN)" in md


def test_the_nightly_run_counts_lessons_before_the_sunday_review(tmp_path, monkeypatch):
    from tests import test_nightly_steps as N

    learning = N._setup(tmp_path, monkeypatch)
    order = []
    monkeypatch.setattr(learning, "count_lessons", lambda j: order.append("count") or {"matured": 2, "by_kind": {}, "tickets": []})
    monkeypatch.setattr(learning, "weekly_review", lambda j: order.append("review") or {"file": "docs/repair_shop/weekly/2026-10-18.md"})
    out = N.U.run_daily(N._j(N.SUNDAY))
    assert order == ["count", "review"] and out["lessons"] == {"matured": 2, "tickets": []} and out["steps_failed"] == []
    monkeypatch.setattr(learning, "count_lessons", N._boom)
    out = N.U.run_daily(N._j(N.SUNDAY))
    assert out["steps_failed"] == ["lessons"] and out["weekly_review"].endswith("2026-10-18.md")   # a failing count never skips the review


# ---------------------------------------------------------------------------- a night the count does not run is a lost run
def test_the_run_checker_reports_a_night_without_a_lesson_count(tmp_path):
    import json as _json

    from jarvis.service import runcheck
    from tests.test_runcheck import _db, _part, _paths

    paths = _paths(tmp_path)
    now = calendar.timegm((2026, 10, 27, 14, 0, 0))
    recs = [(f"learning:count:2026-10-{d:02d}", _json.dumps({"matured": 0, "t": calendar.timegm((2026, 10, d, 0, 5, 0))})) for d in (22, 23, 25, 26, 27)]
    _db(paths["agent"] + "/jarvis.sqlite", ["CREATE TABLE engine_state (k TEXT PRIMARY KEY, v TEXT)"], {"engine_state": recs})
    ms = [m for m in runcheck.run(paths, now, [_part("lesson_count")])["windows"]["7d"]["misses"]]
    assert [(m["kind"], m["runs"]) for m in ms] == [("no run", 1)]                                   # Oct 24's count is missing
