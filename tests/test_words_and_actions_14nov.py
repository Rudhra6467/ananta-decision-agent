"""14 Nov 2026 (Madhav, six screenshots: "what do you think of the language used ... why don't we have options ... only 2 action items are
shown here, isn't it minimising the scope?"). A research draft's sheet says what it is and takes yes, skip, not now and postpone; a waiting
item can be postponed without being answered; a change page carries no code, file or check name, and ends with what he can do."""
import json

import pytest

from jarvis import placekit as K
from jarvis.india import views
from jarvis.service import openlist, places

DRAFT = {"n": 1, "key": "EXIT_LESSON:PULL:GAVE_BACK", "type": "EXIT_LESSON", "day": "2026-11-12",
         "words": "7 closed pullback in an uptrend trades in the last 20 sessions were tagged GAVE_BACK: was up one and a half risk units at some point "
                  "and still closed at or under the entry (no plan to protect a winner). Question for the G01 exit book cell PULL: does the registered "
                  "exit that fixes this hold up on the development and validation years?"}


def test_a_draft_is_said_in_plain_words():
    w = views.draft_plain(DRAFT)
    assert w["title"] == "Study a better exit rule?"
    assert w["noticed"].startswith("In the last 20 sessions, 7 'pullback in an uptrend' trades went the same way")
    assert "GAVE_BACK" not in w["noticed"] and "G01" not in w["noticed"] and "risk unit" not in w["noticed"]


def test_a_drafts_sheet_takes_every_answer(monkeypatch):
    monkeypatch.setattr(views, "drafts", lambda: {"drafts": [DRAFT]})
    rows = places.you_rows({"you": [{"key": "india:drafts", "market": "india", "line": "x", "id": "1 research draft"}]}, "india")
    assert len(rows) == 1 and K.nwords(rows[0]["title"]) <= 6
    sh = rows[0]["to"]["sheet"]
    assert sh["key"] == "draft:EXIT_LESSON:PULL:GAVE_BACK" and not sh["title"].endswith("…")
    assert [(a["id"], a["label"]) for a in sh["answers"]][:3] == [("yes", "Yes, study it"), ("no", "Skip it"), ("later", "Not now")]
    assert [a.get("due") for a in sh["answers"][3:]] == ["tomorrow", "week"] and all(a["explain"] for a in sh["answers"])
    # one he put off leaves the rows
    assert places.you_rows({"you": [{"key": "india:drafts", "market": "india", "line": "x"}], "quiet": ["draft:EXIT_LESSON:PULL:GAVE_BACK"]}, "india") == []


def test_yes_and_skip_are_written_to_the_decisions(monkeypatch, tmp_path):
    monkeypatch.setattr(views, "DATA", tmp_path)
    monkeypatch.setattr(views, "_queue_rows", lambda: [{"key": DRAFT["key"], "lane": "DECISION", "state": "DRAFT"}])
    row = views.decide_draft(DRAFT["key"], "yes", "Madhav (owner)", "in the app")
    assert row["decision"] == "APPROVED"
    saved = [json.loads(x) for x in (tmp_path / "paper" / "reconstruction" / "decisions.jsonl").read_text().splitlines()]
    assert saved[-1]["key"] == DRAFT["key"] and saved[-1]["by"] == "Madhav (owner)"
    assert views.decide_draft(DRAFT["key"], "no", "Madhav (owner)")["decision"] == "SKIPPED"
    with pytest.raises(KeyError):
        views.decide_draft("NOPE", "yes", "Madhav (owner)")


def test_every_waiting_item_has_its_full_list():
    assert openlist.answers_for("ask:3") == ["yes", "no", "later", "postpone"]
    assert openlist.answers_for("ask:3", step=True) == ["done", "later", "postpone"]
    assert openlist.answers_for("needs:x") == ["yes", "later", "postpone"]
    assert openlist.answers_for("draft:K") == ["yes", "no", "later", "postpone"]
    assert openlist.answers_for("flag:9") == ["later", "postpone"]


def test_a_cut_title_is_never_shown_in_a_sheet():
    t, text = places._sheet_title("Yes registers a study (written down first, tested on 2000-2023 only); nothing trades from it.", "Yes registers a study (writte…")
    assert t == "Yes registers a study" and text.startswith("Yes registers a study (written down first")


LINE = {"date": "2026-11-14", "area": "india_books", "market": "india", "status": "live", "title": "The managed book",
        "plain": ["Your India account total now counts the options line's paper result."],
        "words": "India's account total counts the options line at its own value. It counted the options money at the flat Rs 50,000 set aside, so the "
                 "line's paper result was in no account figure. Now the book's value is the money set aside plus the line's result.",
        "why": "The keen outside audit of 11-12 Nov (~/ananta_runs/keen_audit/grade/verdict.md), audit repair 4 (open-list flag 120): G-11 (S2, a rule "
               "question). Madhav's yes of 12 Nov 01:52 (\"Yes to all your recommendations\"; claude/decision.md): the account total counts the options line."}


def test_a_change_page_reads_plainly_and_ends_with_actions():
    pg = places.change_page(LINE)
    titles = [p.get("title") for p in pg["parts"] if p.get("t") in ("points", "rows")]
    assert titles == ["What changed", "What was wrong before", "Who asked for it", "What happens next", "What you can do"]
    said = [i["text"] for p in pg["parts"] if p.get("t") == "points" for i in p["items"]]
    assert not any(places.JARGON.search(x) for x in said), said
    assert "You approved it on 12 Nov." in said and "Found in an outside review of Ananta's work." in said
    assert any(x.startswith("It counted the options money at the flat Rs 50,000") for x in said)
    assert K.problems("change", pg) == []
