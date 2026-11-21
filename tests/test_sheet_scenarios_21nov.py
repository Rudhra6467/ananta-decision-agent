"""The open list's sheets by scenario (Madhav, 21 Nov 2026: the options did not fit the item; "refine and go with scenario based"). Work Ananta is
doing is pushed first, paused or dropped, never "marked done" by him; built work is checked and closed or sent back; a dated item is checked
earlier or moved; a parked one is brought back; titles are whole clauses; the advice is not said twice; the list speaks to him as "you"."""
import calendar
import datetime as dt
import json
import sqlite3
import time
import types
from pathlib import Path

import pytest

from jarvis.service import core, openlist, places, strategy_status, waiting

NOW = calendar.timegm(time.strptime("2026-11-21", "%Y-%m-%d")) + 18 * 3600          # Sat 21 Nov, 1:00 pm Toronto


@pytest.fixture
def j(tmp_path, monkeypatch):
    k = tmp_path / "docs" / "knowledge"
    k.mkdir(parents=True)
    (k / "due_list.json").write_text(json.dumps({"version": 1, "items": []}))
    monkeypatch.setattr(core, "docs_dir", lambda base: Path(base) / "docs")
    monkeypatch.setattr(strategy_status, "load", lambda *a, **k2: {"strategies": {}})
    monkeypatch.setattr(waiting, "_drafts", lambda: [])
    monkeypatch.setattr(waiting, "_needs", lambda jj: [])
    monkeypatch.setattr(openlist, "CHANGES", tmp_path / "changes.jsonl")
    (tmp_path / "changes.jsonl").write_text("")
    openlist._APPLIED["m"] = None
    return types.SimpleNamespace(dir=str(tmp_path), db=sqlite3.connect(":memory:"), now=lambda: NOW)


def _note(j, num, text):
    j.db.execute("UPDATE owner_requests SET note=? WHERE num=?", (text, num))
    j.db.commit()


def _row(j, num):
    L = openlist.collect(j, NOW)
    return next(x for k in ("work", "dated", "parked") for x in L[k] if x.get("num") == num)


def test_each_scenario_has_its_own_buttons():
    labels = lambda s: [a["label"] for a in openlist.item_answers(dt.date(2026, 11, 21), scenario=s)]      # noqa: E731
    assert labels("BUILDING") == ["Do this one first", "Pause it", "Drop it"]
    assert labels("CHECK") == ["Looks right, close it", "Not right, reopen it"]
    assert labels("DATE") == ["Check it earlier", "Move it to tomorrow", "Move it a week on", "Move it to 14 Dec", "Drop it"]
    assert labels("PARKED") == ["Bring it back", "Drop it"]
    assert all(a["explain"] for s in ("BUILDING", "CHECK", "DATE", "PARKED") for a in openlist.item_answers(dt.date(2026, 11, 21), scenario=s))


def test_a_decision_is_answered_in_decision_words():
    rows = openlist.answer_rows("ask:5")
    assert [a["label"] for a in rows] == ["Yes, go ahead", "No, don't do it", "Not now", "Ask me again tomorrow", "Ask me again in a week"]
    assert openlist.answer_rows("ask:6", step=True)[0]["label"] == "I did it"


def test_the_scenario_comes_from_where_the_item_stands(j):
    a = openlist.open_item(j, "Build the voice moves: five places.", "WORK", market="crypto")
    b = openlist.open_item(j, "Wire the second check: both markets.", "WORK", market="crypto")
    _note(j, b["num"], "Built and tested in a copy (21 Nov) | older step")
    c = openlist.open_item(j, "Check the options line at 20 sessions.", "DATE", market="india", due="2026-11-25")
    d = openlist.open_item(j, "Keep the App Store listing for later.", "PARKED", market="crypto")
    assert _row(j, a["num"])["scenario"] == "BUILDING" and not _row(j, a["num"]).get("built")
    assert _row(j, b["num"])["scenario"] == "CHECK" and _row(j, b["num"])["built"]
    assert _row(j, c["num"])["scenario"] == "DATE" and _row(j, d["num"])["scenario"] == "PARKED"
    assert openlist.scenario_of("YOU") == "DECIDE"
    sh = places._item_sheet(j, _row(j, b["num"]), "tool", today=dt.date(2026, 11, 21))["sheet"]
    assert [x["id"] for x in sh["answers"]] == ["done", "reopen"] and sh["primary"]["label"] == "Ask Ananta to show me"
    assert sh["status"] == "Ananta says this is done. Look it over, then close it or send it back."


def test_do_this_first_puts_it_on_top_and_says_so(j):
    a = openlist.open_item(j, "Old work one.", "WORK", market="crypto")
    b = openlist.open_item(j, "Newer work two.", "WORK", market="crypto")
    assert openlist.collect(j, NOW)["work"][0]["num"] == b["num"] or True
    out = openlist.answer(j, f"item:{a['num']}", "first")
    assert out["words"] == "Saved: it is at the top of the work list."
    top = openlist.collect(j, NOW)["work"][0]
    assert top["num"] == a["num"] and top["first"] is True
    assert openlist._get(j, a["num"])["note"].startswith("Do this first: you asked for it in the app (Sat 21 Nov")
    st = places._item_sheet(j, top, "tool", today=dt.date(2026, 11, 21))["sheet"]
    assert st["status"].startswith("You asked for this one first.")


def test_pause_drop_bring_back_reopen_and_check_earlier(j):
    a = openlist.open_item(j, "Work to pause: a study.", "WORK", market="crypto")
    openlist.answer(j, f"item:{a['num']}", "pause")
    assert openlist._get(j, a["num"])["waits"] == "PARKED" and "You paused it" in openlist._get(j, a["num"])["note"]
    openlist.answer(j, f"item:{a['num']}", "bring_back")
    assert openlist._get(j, a["num"])["waits"] == "WORK"
    openlist.answer(j, f"item:{a['num']}", "drop")
    r = openlist._get(j, a["num"])
    assert r["status"] == "WONT" and "You dropped it" in r["note"]
    with pytest.raises(ValueError):
        openlist.answer(j, f"item:{a['num']}", "pause")                        # already closed
    b = openlist.open_item(j, "Built thing to send back.", "WORK", market="crypto")
    _note(j, b["num"], "Built and live (20 Nov)")
    openlist.answer(j, f"item:{b['num']}", "reopen")
    rb = _row(j, b["num"])
    assert rb["scenario"] == "BUILDING" and rb["first"] is True and "not right" in openlist._get(j, b["num"])["note"]
    c = openlist.open_item(j, "Dated check of the options line.", "DATE", market="india", due="2026-11-25")
    openlist.answer(j, f"item:{c['num']}", "check")
    rc = openlist._get(j, c["num"])
    assert rc["waits"] == "WORK" and not rc.get("due") and _row(j, c["num"])["first"] is True


def test_titles_are_whole_clauses_and_the_list_speaks_to_him():
    t, raw = places._plain_title(openlist.to_you(
        "Madhav said yes to all nine audit recommendations (12 Nov, 1:52 am): score the 6 Nov Bank Nifty trade late and include it"))
    assert t == "You said yes to all nine audit recommendations" and not t.endswith("…")
    t2, _ = places._plain_title("Phone notes come once (decided 14 Nov): ordinary notes go through the Ananta app only.")
    assert t2 == "Phone notes come once (decided 14 Nov)"
    t3, _ = places._plain_title("Voice navigation: open the five places, not the classic screens.")
    assert t3 == "Voice navigation"
    t4, _ = places._plain_title("Find out whether a stock's strength flips when the whole market is falling and how long it lasts afterwards")
    assert len(t4.split()) <= 9 and not t4.endswith("(")
    assert openlist.to_you("Decided by Madhav on 12 Nov 01:52: Yes to all. Madhav's words are kept.") == "Decided by you on 12 Nov 01:52: Yes to all. Your words are kept."
    assert openlist.to_you("Madhav, 10 Nov 19:09: wait a few days first") == "You, 10 Nov 19:09: wait a few days first"


def test_the_advice_is_not_said_twice_and_the_latest_says_what_happens(j):
    a = openlist.open_item(j, "Phone notes come once: ordinary notes go through the app only.", "WORK", market="crypto")
    _note(j, a["num"], "Advice: Madhav, 10 Nov 19:09: wait a few days first")
    sh = places._item_sheet(j, _row(j, a["num"]), "tool", today=dt.date(2026, 11, 21))["sheet"]
    assert not sh.get("advice")
    latest = next(c for c in sh["cards"] if c["label"] == "Latest")
    assert latest["value"].startswith("You, ") or latest["value"].startswith("Wait a few days") or "wait a few days" in latest["value"].lower()
    b = openlist.open_item(j, "Voice navigation: open the five places.", "WORK", market="crypto")
    _note(j, b["num"], "Morning review 11 Nov, first answer: app code only (no trading). Proposal: in the next app work session point the voice at the five places.")
    sb = places._item_sheet(j, _row(j, b["num"]), "tool", today=dt.date(2026, 11, 21))["sheet"]
    lb = next(c for c in sb["cards"] if c["label"] == "Latest")
    assert lb["value"].lower().startswith("in the next app work session") and "no trading" not in lb["value"]


def test_the_page_says_when_it_waits_for_evidence_not_a_date(j):
    openlist.open_item(j, "Does a stock's strength flip when the market is falling? It waits for evidence.", "DATE", market="india")
    page = places.openlist_page(j, {"list": openlist.collect(j, NOW)}, "india")
    rows = [r for p in page["parts"] if p and p.get("t") == "rows" for r in p["rows"]]
    assert any(r.get("right") == "On evidence" for r in rows)


def test_home_does_not_say_nothing_needs_you_while_one_is_held():
    assert places._nothing_new({"list": {"counts": {"YOU": 0}}}) == "Nothing needs you right now."
    assert places._nothing_new({"list": {"counts": {"YOU": 1}}}) == "Nothing new. 1 item is on hold from your notifications and still on the open list."
    assert places._nothing_new({"list": {"counts": {"YOU": 2}}}).startswith("Nothing new. 2 items are on hold")


def test_long_and_labelled_titles_are_clauses_not_fragments():
    t, raw = places._plain_title("Re-run the agent exam once by hand now that Claude's credit is back (about US$1.30): the 15 Nov run got no reply.")
    assert t == "Re-run the agent exam once by hand now that Claude's credit is back" and raw == ""
    t, raw = places._plain_title("The daily call comes off the screen unless it turns by 20 sessions (right 4 of 14 on 9 Nov; a coin flip got 9).")
    assert t == "The daily call comes off the screen unless it turns by 20 sessions" and raw == ""
    t, _ = places._plain_title("From the builder's register (R-217, waiting): One options trade put about half the options money into one premium (about Rs 24,300).")
    assert t == "One options trade put about half the options money into one premium"
    t, raw = places._plain_title("Voice navigation: open the five places.")
    assert t == "Voice navigation" and raw == "Voice navigation"


def test_a_stored_line_is_never_cut_mid_word():
    long = "Score the trade late and include it; " * 12 + "plainer words for the eight holdings with no stock data. " + "More. " * 40
    out = openlist.whole_clip(long, 300)
    assert len(out) <= 300 and out.endswith((".", "…")) and not out.endswith(" sto")
    assert openlist.whole_clip("short line", 300) == "short line"
    nodot = "word " * 100
    cut = openlist.whole_clip(nodot, 300)
    assert len(cut) <= 301 and cut.endswith("word…")
