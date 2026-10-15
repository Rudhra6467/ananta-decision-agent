"""The due list (docs/knowledge/due_list.json): nothing parked after the crypto lock can go quiet."""
import calendar
import json
import sqlite3
import time
import types
from pathlib import Path

import pytest

from jarvis.service import core, due_list, strategy_status

NOW = calendar.timegm(time.strptime("2026-10-20", "%Y-%m-%d")) + 3600
ROOT = Path(__file__).resolve().parents[1]


def _j(tmp):
    return types.SimpleNamespace(dir=str(tmp), db=sqlite3.connect(":memory:"), now=lambda: NOW)


def _list(tmp_path, monkeypatch, items, start="2026-10-15", days=60):
    k = tmp_path / "docs" / "knowledge"
    k.mkdir(parents=True)
    (k / "due_list.json").write_text(json.dumps({"version": 1, "items": items}))
    monkeypatch.setattr(core, "docs_dir", lambda base: Path(base) / "docs")
    monkeypatch.setattr(strategy_status, "load", lambda *a, **k2: {"evidence_window": {"start": start, "days": days}})


ITEMS = [
    {"id": "A-OVERDUE", "what": "check the first Sunday review", "how": "open docs/repair_shop/weekly", "due": "2026-10-19"},
    {"id": "B-SOON", "what": "worker stage S2", "how": "run the S2 script", "due": "2026-10-26"},
    {"id": "C-LATER", "what": "monthly spread refresh", "how": "compare the table", "due": "2026-11-01", "cadence": "monthly"},
    {"id": "D-DONE", "what": "already finished", "how": "nothing", "due": "2026-10-01", "done": "2026-10-02"},
    {"id": "E-EVIDENCE", "what": "Q1 answer", "how": "the ledger counts", "cadence": "evidence", "goal": "10 market events"},
    {"id": "PW-01", "what": "a re-test", "how": "write the pre-registration first", "after_window": True},
]


def test_check_sorts_items_by_what_they_need(tmp_path, monkeypatch):
    _list(tmp_path, monkeypatch, ITEMS)
    r = due_list.check(_j(tmp_path))
    assert r["overdue"] == ["A-OVERDUE"] and r["soon"] == ["B-SOON"] and r["waiting_for_evidence"] == ["E-EVIDENCE"]
    assert r["post_window"] == ["PW-01"] and r["done"] == ["D-DONE"] and r["problems"] == []
    assert r["window_end"] == "2026-12-14" and not r["window_over"]
    assert "1 overdue (A-OVERDUE)" in due_list.line(r) and "1 after the window" in due_list.line(r)


def test_an_overdue_item_becomes_one_request_once_and_a_done_item_none(tmp_path, monkeypatch):
    _list(tmp_path, monkeypatch, ITEMS)
    j = _j(tmp_path)
    first, again = due_list.nightly(j), due_list.nightly(j)
    rows = j.db.execute("SELECT by, kind, about, text FROM owner_requests").fetchall()
    assert first["flagged"] == ["A-OVERDUE"] and again["flagged"] == [] and len(rows) == 1
    assert rows[0][:3] == ("ananta-auto", "data", "due list") and "A-OVERDUE" in rows[0][3] and "D-DONE" not in rows[0][3]


def test_marking_done_ends_a_one_off_and_moves_a_recurring_item_to_its_next_date(tmp_path, monkeypatch):
    _list(tmp_path, monkeypatch, [ITEMS[0], {"id": "M", "what": "monthly look", "how": "open it", "due": "2026-08-31", "cadence": "monthly"}])
    j = _j(tmp_path)
    r = due_list.check(j)
    assert r["overdue"] == ["A-OVERDUE", "M"] and {x["id"]: x["due"] for x in r["rows"]}["M"] == "2026-08-31"
    assert due_list.mark_done(j, "A-OVERDUE", "looked")["marked"] == 0 and due_list.mark_done(j, "A-OVERDUE").get("already_done")
    assert due_list.mark_done(j, "M")["date"] == "2026-08-31"                                # a missed month stays overdue until marked
    r = due_list.check(j)
    assert r["overdue"] == ["M"] and {x["id"]: x["due"] for x in r["rows"]}["M"] == "2026-09-30"      # the 31st clamps to the 30th
    due_list.mark_done(j, "M")
    r = due_list.check(j)
    assert r["overdue"] == [] and {x["id"]: x["state"] for x in r["rows"]} == {"A-OVERDUE": "done", "M": "later"}
    assert {x["id"]: x["due"] for x in r["rows"]}["M"] == "2026-10-31"
    with pytest.raises(KeyError):
        due_list.mark_done(j, "NOT-AN-ITEM")


def test_a_missed_date_is_flagged_once_for_that_date_and_again_for_the_next(tmp_path, monkeypatch):
    _list(tmp_path, monkeypatch, [{"id": "W", "what": "weekly look", "how": "open it", "due": "2026-10-05", "cadence": "weekly"}])
    j = _j(tmp_path)
    assert due_list.nightly(j)["flagged"] == ["W"] and due_list.nightly(j)["flagged"] == []
    due_list.mark_done(j, "W")                                                              # 10-05 done; 10-12 is next and also missed
    assert due_list.nightly(j)["flagged"] == ["W"]
    assert len(j.db.execute("SELECT * FROM owner_requests").fetchall()) == 2


def test_occurrence_dates():
    assert [due_list.occurrence("2026-10-26", "weekly", k) for k in (0, 1, 2)] == ["2026-10-26", "2026-11-02", "2026-11-09"]
    assert [due_list.occurrence("2026-11-01", "monthly", k) for k in (0, 1, 2)] == ["2026-11-01", "2026-12-01", "2027-01-01"]
    assert due_list.occurrence("2027-01-31", "monthly", 1) == "2027-02-28" and due_list.occurrence("2026-11-30", "quarterly", 1) == "2027-02-28"
    assert due_list.occurrence("2027-01-01", "quarterly", 3) == "2027-10-01"


def test_the_post_window_list_is_raised_once_after_the_window_ends(tmp_path, monkeypatch):
    _list(tmp_path, monkeypatch, [ITEMS[5], ITEMS[3]], start="2026-08-01", days=60)         # the window ended on 2026-09-30
    j = _j(tmp_path)
    assert due_list.nightly(j)["flagged"] == ["post-window"] and due_list.nightly(j)["flagged"] == []
    assert "post-window items are waiting (PW-01)" in j.db.execute("SELECT text FROM owner_requests").fetchone()[0]


def test_a_broken_list_is_reported_not_trusted(tmp_path, monkeypatch):
    bad = {"items": [{"id": "X", "what": "w", "how": "h", "due": "next week"}, {"id": "X", "what": "w", "how": "h", "due": "2026-10-01"},
                     {"id": "Y", "what": "w", "how": "h", "after_window": True, "due": "2026-10-01"}, {"id": "Z", "what": "", "how": "h", "due": "2026-10-01"},
                     {"id": "V", "what": "w", "how": "h", "due": "2026-13-45"}, {"id": "U", "what": "w", "how": "h", "due": "2026-10-01", "cadence": "daily"}]}
    text = " | ".join(due_list.problems(bad))
    for part in ("X: due is not a date", "used twice: X", "Y: a post-window item has no date", "Z: says neither", "V: due is not a date", "U: unknown cadence daily"):
        assert part in text, part
    _list(tmp_path, monkeypatch, bad["items"])
    j = _j(tmp_path)
    assert "problems" in due_list.nightly(j)["flagged"] and "problems" not in due_list.nightly(j)["flagged"]


def test_the_shipped_list_is_sound_and_every_post_window_item_has_a_reason():
    d = json.loads((ROOT / "docs" / "knowledge" / "due_list.json").read_text())
    assert due_list.problems(d) == []
    ids = [i["id"] for i in d["items"]]
    assert len(ids) == len(set(ids)) and any(i.get("after_window") for i in d["items"]) and any(i.get("due") for i in d["items"])
    for i in d["items"]:
        assert len(i["what"]) >= 20 and len(i["how"]) >= 20, i["id"]


def test_a_weekly_job_marks_every_date_up_to_today_and_leaves_the_future_alone(tmp_path, monkeypatch):
    import pytest

    items = [{"id": "W", "what": "the weekly review is written", "how": "see the weekly folder", "due": "2026-10-04", "cadence": "weekly"},
             {"id": "ONE", "what": "a one-off job", "how": "do the job once", "due": "2026-10-10"}]
    _list(tmp_path, monkeypatch, items)
    j = _j(tmp_path)                                                       # today is 2026-10-20
    assert due_list.mark_done_through(j, "W", "file")["marked"] == ["2026-10-04", "2026-10-11", "2026-10-18"]
    assert due_list.check(j)["overdue"] == ["ONE"] and [r["due"] for r in due_list.rows(j) if r["id"] == "W"] == ["2026-10-25"]
    assert due_list.mark_done_through(j, "W")["marked"] == []              # run twice on one day: the next week is not pre-marked
    with pytest.raises(ValueError):
        due_list.mark_done_through(j, "ONE")
    with pytest.raises(KeyError):
        due_list.mark_done_through(j, "NOPE")
