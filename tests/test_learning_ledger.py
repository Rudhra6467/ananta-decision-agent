"""The repair-shop ledger (Oct 21): the Oct 14 weekly ticket filed at last (TK19), and the hand-written ledger checked against the
database as a warning in the morning review (the full generator, PW-LEDGER-GENERATE, waits for after the window)."""
import json
import time
from pathlib import Path

from tests.test_learning_loop import NOW, SUN, DAY, _pair, loop  # noqa: F401  (the fixture)

REPO = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------- 3. the Oct 14 ticket, filed
def test_the_oct_14_random_beat_the_pick_ticket_is_in_the_ledger():
    led = json.loads((REPO / "docs" / "repair_shop" / "ledger.json").read_text())
    tk = [t for t in led["tickets"] if t.get("lesson") == "random beat the pick"]
    assert len(tk) == 1 and tk[0]["id"] == "TK19" and tk[0]["review"] == "R33"
    assert tk[0]["decisions"] == ["2fa79120821d", "450cfffaeac5", "58058e45d50b"]
    assert "weekly/2026-10-14.md" in tk[0]["from"] and "DOGE" in tk[0]["what"] and "I approve all" in tk[0]["did"]
    assert tk[0]["status"] in ("OPEN", "WAITING_FOR_EVIDENCE") and led["updated"] >= tk[0]["date"]
    assert "random beat the pick" in (REPO / "docs" / "repair_shop" / "weekly" / "2026-10-14.md").read_text()


# ---------------------------------------------------------------------------- 4. the ledger against the database, warnings only
def test_ledger_warnings_name_missing_requests_and_unknown_decisions(loop, tmp_path):
    from jarvis.service import requests_log

    s = loop
    d = _pair(s, SUN - 3 * DAY, -5.0, -1.0)
    requests_log.add(s.j, "idea", "one", by="owner")
    (tmp_path / "docs" / "repair_shop" / "ledger.json").write_text(json.dumps({"tickets": [
        {"id": "TK1", "what": "See request #1 and Requests #7/#8."},
        {"id": "TK19", "lesson": "random beat the pick", "decisions": [d, "nope"]}]}))
    w = s.L.ledger_warnings(s.j)
    assert w["checked"] == 5
    assert w["warnings"] == ["the ledger cites requests that are not on the repair board: #7, #8",
                             "lesson tickets name decisions the database does not have: TK19 nope"]
    before = s.j.db.execute("SELECT COUNT(*) FROM owner_requests").fetchone()[0]
    md = "\n".join(s.L.morning_lines(s.j))
    assert "Ledger against the database (warning only): the ledger cites requests" in md
    assert s.j.db.execute("SELECT COUNT(*) FROM owner_requests").fetchone()[0] == before          # warnings only: nothing filed


def test_a_loop_ticket_with_no_ledger_row_is_a_warning_and_the_morning_flags_a_missed_count(loop):
    s = loop
    for k in range(3):
        _pair(s, SUN - 3 * DAY + k, -5.0, -1.0)
    s.j._now = SUN + 9 * DAY
    s.L.count_lessons(s.j)
    md = "\n".join(s.L.morning_lines(s.j))
    assert "request #1 (filed by the learning loop: random beat the pick) has no row in the ledger yet" in md
    assert "Filed by themselves, last 7 days: #1 (weekly lessons, OPEN)" in md and "WARNING" not in md
    s.j._now = SUN + 12 * DAY
    assert "WARNING: the last count was 2026-10-20" in "\n".join(s.L.morning_lines(s.j))


def test_the_ledger_on_this_branch_agrees_with_itself():
    from jarvis.service import knowledge_build

    j = type("J", (), {"dir": str(REPO), "now": lambda self: time.time()})()
    assert knowledge_build.ledger(j)["problems"] == []
