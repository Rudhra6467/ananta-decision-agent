"""The voices know the plan and what got done (Madhav, 11 Nov 2026, 10:13: "even the voice agent is like aware of all these dates and stuff,
like, you know, it knows what's happening"; 10:14: "and it also gets updates back when done and keeps a track of them as well").

The dry voice test of 11 Nov (9 questions) found: asked what we finished today, the crypto voice gave trades only; asked when the keen audit
is, it read the dated items only and guessed the India re-grade; the India voice filed a note for "how do you keep track of it?"; and India
said the options line's review reads on Fri 20 Nov evening, while that session's trades close only at the next open (Mon 23 Nov, the plan's
review day). Now: the open list carries closed_lately (each item finished or dropped in the last two days, by its name, with what closed it);
the crypto open_list lookup gives the work items with the dated ones; a question about how is answered, not filed; and the review day is the
open after the 20th session."""
import calendar
import json
import sqlite3
import time
import types
from pathlib import Path

import pytest

from jarvis.india import ask as india_ask
from jarvis.service import ask, core, openlist, strategy_status, waiting

NOW = calendar.timegm(time.strptime("2026-11-11", "%Y-%m-%d")) + 15 * 3600          # Wed 11 Nov, 10:00 am Toronto


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


def test_a_closed_item_travels_with_the_list_with_what_closed_it(j):
    it = openlist.open_item(j, "Check that the 12 Nov shadow plan was read whole.", "WORK", market="india")
    openlist.close(j, it["num"], "The 12 Nov plan was read whole.", by="the 12 Nov shadow log")
    d = openlist.collect(j, NOW + 60)
    row = next(x for x in d["closed_lately"] if x["num"] == it["num"])
    assert row["id"].startswith(("flag ", "request ")) and row["result"] == "done"          # its name, as the list says it
    assert row["how"] == "The 12 Nov plan was read whole." and row["proof"] == "the 12 Nov shadow log"
    assert it["num"] not in {x["num"] for x in d["work"]}                       # closed is not open
    s = openlist.short(j, market="india", now=NOW + 60)
    assert s["closed_lately"] == [{"id": row["id"], "line": row["line"], "result": "done", "how": "The 12 Nov plan was read whole.",
                                   "when": row["when"]}]


def test_closed_lately_keeps_to_its_market_says_dropped_and_ends_after_two_days(j):
    a = openlist.open_item(j, "A crypto chart label is a day late.", "WORK", market="crypto")
    b = openlist.open_item(j, "Phone notes come twice.", "WORK", market="both")
    c = openlist.open_item(j, "An idea nobody needs any more.", "WORK", market="india")
    openlist.close(j, a["num"], "Fixed the label.", by="commit abc")
    openlist.close(j, b["num"], "ntfy is off.", by="Madhav, in the app")
    openlist.close(j, c["num"], "Dropped: a repeat of another item.", done=False, by="claude")
    hows = {x["how"]: x for x in openlist.short(j, market="india", now=NOW + 60)["closed_lately"]}
    assert set(hows) == {"ntfy is off.", "Dropped: a repeat of another item."}      # India's and the shared one, not crypto's
    assert hows["Dropped: a repeat of another item."]["result"] == "dropped"
    assert {x["how"] for x in openlist.collect(j, NOW + 60)["closed_lately"]} >= {"Fixed the label.", "ntfy is off."}
    assert openlist.closed_lately(j, now=NOW + 3 * 86400) == []                     # two days, then it is history (my_requests)


def test_a_due_list_date_marked_done_is_in_closed_lately_too(j):
    from jarvis.service import due_list

    due_list.mark_done(j, "CHECKPOINT-30", "Every evidence count read; nothing stuck.")
    row = next(x for x in openlist.collect(j, NOW + 60)["closed_lately"] if x["id"] == "CHECKPOINT-30")
    assert row["how"] == "Every evidence count read; nothing stuck." and row["proof"] == "the due list" and row["market"] == "crypto"
    assert "CHECKPOINT-30" not in {x["id"] for x in openlist.short(j, market="india", now=NOW + 60)["closed_lately"]}
    assert "CHECKPOINT-30" in {x["id"] for x in openlist.short(j, market="crypto", now=NOW + 60)["closed_lately"]}


def test_the_crypto_lookup_gives_the_work_items_with_the_dates(j):
    w = openlist.open_item(j, "The keen outside audit: runs on Madhav's go, report the morning after.", "WORK", market="both")
    done = openlist.open_item(j, "Review 41's open-list item.", "WORK", market="crypto")
    openlist.close(j, done["num"], "Review 41 ran: FAIL.", by="5d6635c")
    me = types.SimpleNamespace(guest=False, j=j)
    out = ask.Lookups.t_open_list(me, kind="dated")
    assert "dated" in out and w["num"] in {x["num"] for x in out["work"]}      # "when is the keen audit?" finds the work item
    assert any(x["how"] == "Review 41 ran: FAIL." for x in out["closed_lately"])
    assert any(x["how"] == "Review 41 ran: FAIL." for x in ask.Lookups.t_open_list(me)["closed_lately"])
    assert "gives closed_lately (11 Nov)" in Path(ask.__file__).read_text()          # the lookup's own description says so


def test_the_ask_rules_say_what_got_done_how_it_is_tracked_and_what_research_means():
    assert "WHAT GOT DONE, AND HOW YOU KEEP TRACK" in ask.SYSTEM and "closed_lately" in ask.SYSTEM
    assert "RESEARCH (11 Nov)" in ask.SYSTEM and "research review" in ask.SYSTEM
    src = Path(india_ask.__file__).read_text()
    assert "closed_lately is what was finished or dropped" in src


@pytest.mark.parametrize("text", ["What got done for India today, and how do you keep track of it?", "How do I flag it?",
                                  "how would you keep track of that for me?"])
def test_a_question_about_how_is_answered_not_filed(text):
    assert india_ask.flag_intent(text) is None


@pytest.mark.parametrize("text", ["Keep track of it, please.", "Flag it.", "This one is also to be registered and somehow to be notified"])
def test_a_request_to_note_is_still_filed(text):
    assert india_ask.flag_intent(text) is not None


def test_the_options_line_review_day_is_the_open_after_the_20th_session(tmp_path, monkeypatch):
    rec, data = tmp_path / "records", tmp_path / "data"
    (rec / "india" / "registrations").mkdir(parents=True)
    (rec / "india" / "registrations" / "sp1r_v1.json").write_text(json.dumps({"questions": ["Is Bank Nifty's margin the cause?"], "why": "x"}))
    (data / "paper" / "sp1").mkdir(parents=True)
    (data / "paper" / "sp1" / "book.json").write_text(json.dumps({"sessions": 12}))
    (data / "paper" / "sp1" / "outcomes.jsonl").write_text(json.dumps({"kind": "outcome", "date": "2026-11-09"}) + "\n")
    monkeypatch.setattr(india_ask, "RECORDS", rec)
    monkeypatch.setattr(india_ask, "DATA", data)
    when = india_ask._options_review()["when"]
    assert "12 of 20 sessions are scored" in when
    assert "the 20th is Fri 20 Nov" in when and "close at the next open, Mon 23 Nov" in when
    assert "that evening" not in when
