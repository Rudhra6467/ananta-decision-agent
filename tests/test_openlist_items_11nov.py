"""Open-list items in the app (Madhav, 11 Nov 2026, 07:51): "in the open list page, I couldn't get to know their status or. Mark it done or
postpone it. I couldn't do anything here." Every board item's sheet says where it stands (a status line and small cards, the Usage sheet's
shape) and takes Mark done or Postpone; each answer is kept."""
import calendar
import datetime as dt
import json
import sqlite3
import time
import types
from pathlib import Path

import pytest

from jarvis.service import core, openlist, places, strategy_status, waiting

NOW = calendar.timegm(time.strptime("2026-11-10", "%Y-%m-%d")) + 16 * 3600          # Tue 10 Nov, 11:00 am Toronto


@pytest.fixture
def j(tmp_path, monkeypatch):
    k = tmp_path / "docs" / "knowledge"
    k.mkdir(parents=True)
    (k / "due_list.json").write_text(json.dumps({"version": 1, "items": [
        {"id": "CHECKPOINT-30", "what": "Day-30 checkpoint: read every evidence count.", "how": "read the counts", "due": "2026-11-14"}]}))
    monkeypatch.setattr(core, "docs_dir", lambda base: Path(base) / "docs")
    monkeypatch.setattr(strategy_status, "load", lambda *a, **k2: {"strategies": {}})
    monkeypatch.setattr(waiting, "_drafts", lambda: [])
    monkeypatch.setattr(waiting, "_needs", lambda jj: [])
    monkeypatch.setattr(openlist, "CHANGES", tmp_path / "changes.jsonl")
    (tmp_path / "changes.jsonl").write_text("")
    openlist._APPLIED["m"] = None
    return types.SimpleNamespace(dir=str(tmp_path), db=sqlite3.connect(":memory:"), now=lambda: NOW)


def test_mark_done_in_the_app_closes_the_item_and_keeps_his_answer(j):
    it = openlist.open_item(j, "Build the free-money checks of the managed book.", "WORK", market="india")
    out = openlist.answer(j, f"item:{it['num']}", "done")
    assert out["words"] == "Saved: done. It is off the open list, and your answer is kept."
    r = openlist._get(j, it["num"])
    assert r["status"] == "DONE" and r["closed_by"] == "Madhav, in the app"
    assert r["note"].startswith("You marked it done in the app (Tue 10 Nov, 11:00 am Toronto)")
    assert it["num"] not in {x["num"] for x in openlist.collect(j, NOW)["work"]}
    assert j.db.execute("SELECT key, answer FROM owner_answers").fetchall() == [(f"item:{it['num']}", "done")]
    with pytest.raises(ValueError):
        openlist.answer(j, f"item:{it['num']}", "done")                   # already closed
    with pytest.raises(ValueError):
        openlist.answer(j, f"item:{it['num']}", "yes")                    # an item takes done or postpone, not a yes


def test_postpone_dates_the_item_says_the_day_and_keeps_the_old_note(j):
    it = openlist.open_item(j, "Check the shadow plan for Thursday.", "WORK", market="india")
    j.db.execute("UPDATE owner_requests SET note='an earlier step' WHERE num=?", (it["num"],))
    out = openlist.answer(j, f"item:{it['num']}", "postpone", due="week")
    assert out["due"] == "2026-11-17" and out["words"] == "Saved: postponed to Tue 17 Nov. It stays on the open list and is due again that day."
    r = openlist._get(j, it["num"])
    assert r["status"] == "OPEN" and r["waits"] == "DATE" and r["due"] == "2026-11-17"
    assert r["note"].startswith("You postponed it to Tue 17 Nov in the app") and r["note"].endswith("| an earlier step")
    L = openlist.collect(j, NOW)
    assert it["num"] in {x.get("num") for x in L["dated"]} and it["num"] not in {x["num"] for x in L["work"]}
    assert openlist.answer(j, f"item:{it['num']}", "postpone")["due"] == "2026-11-11", "no day given: tomorrow"
    assert openlist.answer(j, f"item:{it['num']}", "postpone", due="2026-12-14")["due"] == "2026-12-14"
    with pytest.raises(ValueError):
        openlist.answer(j, f"item:{it['num']}", "postpone", due="2026-11-10")        # today is not later


def test_a_dated_item_is_offered_only_later_days():
    rows = openlist.item_answers(dt.date(2026, 11, 11), after="2026-11-12")
    assert [(a["id"], a.get("due")) for a in rows] == [("done", None), ("postpone", "week"), ("postpone", "2026-12-14")]
    assert [a["id"] for a in openlist.item_answers(dt.date(2026, 11, 11), after="2026-12-14")] == ["done"]


def test_postpone_offers_only_days_still_ahead():
    assert [o["id"] for o in openlist.postpone_options(dt.date(2026, 11, 11))] == ["tomorrow", "week", "2026-12-14"]
    assert [o["label"] for o in openlist.postpone_options(dt.date(2026, 11, 11))] == ["Tomorrow", "Next week", "On 14 Dec"]
    assert [o["id"] for o in openlist.postpone_options(dt.date(2026, 12, 20))] == ["tomorrow", "week"]


def test_the_sheet_says_where_an_item_stands():
    d = dt.date(2026, 11, 11)
    w = places.item_sheet_parts({"kind": "WORK", "since": "2026-11-08"},
                                {"note": "11 Nov: 1 of 3 parts built: the checks run in the self-check (cc682e4) | 10 Nov: started"}, today=d)
    assert w["label"] == "Work to do" and w["status"] == "Ananta is working on it. Nothing is needed from you."
    assert w["cards"][0] == {"label": "Open since", "value": "Sun 8 Nov", "sub": "3 days"}
    assert w["cards"][1] == {"label": "Latest", "value": "1 of 3 parts built: the checks run in the self-check", "sub": "11 Nov", "progress": [1, 3]}
    dd = places.item_sheet_parts({"kind": "DATE", "since": "2026-11-11", "due": "2026-11-12"}, {}, today=d)
    assert dd["status"] == "It waits until Thu 12 Nov. That day it is due again."
    assert dd["cards"] == [{"label": "Open since", "value": "Wed 11 Nov", "sub": "today"}, {"label": "Comes back", "value": "Thu 12 Nov", "sub": "tomorrow"}]
    p = places.item_sheet_parts({"kind": "PARKED"}, {"note": "Waits for the India lock to lift."}, today=d)
    assert p["status"] == "Parked on purpose. Nothing happens until someone opens it again." and "progress" not in p["cards"][0]


def test_a_board_item_takes_done_and_postpone_and_a_due_list_item_does_not(j):
    it = openlist.open_item(j, "Study the rupee against flows: 3 parts.", "WORK", market="india")
    row = next(x for x in openlist.collect(j, NOW)["work"] if x["num"] == it["num"])
    sh = places._item_sheet(j, row, "tool", today=dt.date(2026, 11, 10))["sheet"]
    assert sh["key"] == f"item:{it['num']}" and [a["id"] for a in sh["answers"]] == ["done", "postpone", "postpone", "postpone"]
    assert [a.get("due") for a in sh["answers"]] == [None, "tomorrow", "week", "2026-12-14"]
    assert [a["label"] for a in sh["answers"]] == ["Mark done", "Postpone to tomorrow", "Postpone a week", "Postpone to 14 Dec"]
    # Madhav, 11 Nov 08:13: each choice says what it does under its arrow
    assert sh["answers"][1]["explain"] == "It waits on the open list until Wed 11 Nov, and that day it is due again. Nothing is lost."
    assert sh["answers"][3]["explain"].endswith("That is the day the crypto scorecard freeze ends.")
    assert sh["answers"][0]["explain"].startswith("It comes off the open list as done") and sh["primary"]["explain"]
    assert sh["label"].startswith("Work to do · ") and sh["status"] and sh["cards"][0]["label"] == "Open since"
    due = next(x for x in openlist.collect(j, NOW)["dated"] if x["id"] == "CHECKPOINT-30")
    sd = places._item_sheet(j, due, "clock", today=dt.date(2026, 11, 10))["sheet"]
    assert "answers" not in sd and "key" not in sd, "a due-list item is answered in its own place"
    page = places.openlist_page(j, {"list": openlist.collect(j, NOW)}, "india")
    sheets = [r["to"]["sheet"] for p in page["parts"] if p and p.get("t") == "rows" for r in p["rows"] if r.get("to")]
    assert any(s.get("key") == f"item:{it['num']}" for s in sheets)


def test_every_notification_answer_says_what_it_does():
    """Madhav, 11 Nov 08:13: "I can even have an explanation of the action ... a down arrow towards the end"."""
    look = openlist.answer_rows("ask:5", on_yes="done")
    assert [a["id"] for a in look] == ["yes", "no", "later"] and look[0]["explain"] == "It closes as done. Your yes is kept with the time."
    dec = openlist.answer_rows("ask:6")
    assert dec[0]["explain"].startswith("Ananta goes ahead. It becomes work to do") and dec[1]["icon"] == "close"
    assert dec[2]["label"] == "Not now" and "for 7 days" in dec[2]["explain"] and "stays on the open list" in dec[2]["explain"]
    assert openlist.answer_rows("ask:7", step=True)[0] == {"id": "done", "label": "Done", "icon": "check",
                                                           "explain": "Your step is marked done and the item closes. Your answer is kept with the time."}
    assert openlist.answer_rows("needs:x")[0]["explain"].startswith("Ananta does what the card asks, on paper")
    assert all(a["explain"] for a in openlist.answer_rows("india:drafts"))
