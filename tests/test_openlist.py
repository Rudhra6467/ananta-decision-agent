"""The one open list (Madhav, 10 Nov 2026: "how to completely comprehend this into a single set, like where we don't get into this confusion"):
seen again joins, a fix closes its item, the bar and the list say the same, and the list names its own problems."""
import calendar
import json
import sqlite3
import time
import types
from pathlib import Path

import pytest

from jarvis.service import core, fixflow, openlist, requests_log, strategy_status, waiting

NOW = calendar.timegm(time.strptime("2026-11-10", "%Y-%m-%d")) + 16 * 3600
DAY = 86400


@pytest.fixture
def j(tmp_path, monkeypatch):
    k = tmp_path / "docs" / "knowledge"
    k.mkdir(parents=True)
    (k / "due_list.json").write_text(json.dumps({"version": 1, "items": [
        {"id": "CHECKPOINT-30", "what": "Day-30 checkpoint: read every evidence count. More words follow here.", "how": "read the counts", "due": "2026-11-14"},
        {"id": "EV-Q6", "what": "The live record of the short dip trade", "how": "the ledger counts", "cadence": "evidence", "goal": "10 closed trades"},
        {"id": "PW-H1", "what": "Volume shock as a risk flag", "how": "write the test first", "after_window": True},
        {"id": "OD-X", "what": "Decide the worker Mac's alerts", "how": "say a or b", "due": "2026-11-12", "owner": "Madhav", "owner_decision": True},
        {"id": "DONE-1", "what": "finished", "how": "nothing", "due": "2026-10-01", "done": "2026-10-02"}]}))
    monkeypatch.setattr(core, "docs_dir", lambda base: Path(base) / "docs")
    monkeypatch.setattr(strategy_status, "load", lambda *a, **k2: {"evidence_window": {"start": "2026-10-15", "days": 60},
                                                                   "strategies": {"RBD": {"name": "Rebound off support", "status": "PARKED", "why": "43 closed, none won."},
                                                                                  "H07": {"name": "Short dip", "status": "EVIDENCE", "why": "x"}}})
    monkeypatch.setattr(waiting, "_drafts", lambda: [{"id": "india:drafts", "market": "india", "kind": "drafts", "count": 3, "title": "3 research drafts wait for your yes or skip",
                                                      "line": "Yes registers a study.", "route": "evidence", "say": "approve all drafts"}])
    monkeypatch.setattr(waiting, "_needs", lambda jj: [])
    monkeypatch.setattr(openlist, "CHANGES", tmp_path / "changes.jsonl")
    (tmp_path / "changes.jsonl").write_text("")
    openlist._APPLIED["m"] = None
    return types.SimpleNamespace(dir=str(tmp_path), db=sqlite3.connect(":memory:"), now=lambda: NOW)


def test_seen_again_joins_the_open_item_and_a_closed_topic_starts_a_new_one(j):
    a = requests_log.add(j, "bug", "Officer check idle_cash failed: cash is 90% for 5 days", by="owner", topic="officer:idle_cash")
    b = requests_log.add(j, "bug", "Officer check idle_cash failed: cash is 100% for 15 days", by="owner", topic="officer:idle_cash")
    assert b["num"] == a["num"] and b["joined"] and b["seen"] == 2 and "2nd time" in b["say"]
    assert j.db.execute("SELECT COUNT(*), MAX(seen) FROM owner_requests").fetchone() == (1, 2)
    assert "100% for 15 days" in json.loads(j.db.execute("SELECT sightings FROM owner_requests").fetchone()[0])[-1][1]
    other = requests_log.add(j, "bug", "Officer check core_gap failed", by="owner", topic="officer:core_gap")
    assert other["num"] != a["num"]                                           # another topic is another item
    openlist.close(j, a["num"], "The check now reads cash-by-rule as OK", by="commit d034d57", quiet=True)
    c = requests_log.add(j, "bug", "Officer check idle_cash failed again in December", by="owner", topic="officer:idle_cash")
    assert c["num"] not in (a["num"], other["num"]) and not c.get("joined")   # it came back after the fix: that is news, a new item


def test_a_flag_filed_again_by_the_machine_does_not_open_a_second_flow(j):
    a = fixflow.flag(j, "Officer check idle_cash failed: 5 days", market="crypto", screen="officer", use_ai=False, topic="officer:idle_cash")
    b = fixflow.flag(j, "Officer check idle_cash failed: 8 days", market="crypto", screen="officer", use_ai=False, topic="officer:idle_cash")
    assert b["num"] == a["num"] and b["joined"] and b["seen"] == 2
    assert j.db.execute("SELECT COUNT(*) FROM fix_flow").fetchone()[0] == 1


def test_one_list_four_kinds_and_the_bar_is_its_first_part(j):
    y = openlist.open_item(j, "Phone notes on the iPhone need your Apple sign-in once.", "YOU", market="both", advice="yes, it is one step")
    w = openlist.open_item(j, "Ananta cannot say when you last spoke.", "WORK", market="crypto")
    d = openlist.open_item(j, "Read the Muhurat hour's price file at the audit.", "DATE", market="india", due="2026-11-23")
    p = openlist.open_item(j, "A results-reaction study waits for the India lock to lift.", "PARKED", market="india")
    assert openlist.open_item(j, "Ananta cannot say when you last spoke.", "WORK", market="crypto")["num"] == w["num"]      # the same words: no second copy
    L = openlist.collect(j, NOW)
    assert L["counts"] == {"YOU": 5, "WORK": 1, "DATE": 3, "PARKED": 3}       # 3 drafts + his sign-in + the due list's decision; the audit, the checkpoint, the evidence item
    assert [x["id"] for x in L["dated"]] == ["CHECKPOINT-30", requests_log.label(d["num"]), "EV-Q6"]                         # by date; no date last
    assert {x["source"] for x in L["parked"]} == {"board", "due list", "strategy list"}
    assert L["line"] == ("Open list: 5 things need your yes, 1 is work to do, 3 wait for a date or for evidence (next: 2026-11-14), 3 are parked on purpose.")
    bar = waiting.collect(j, NOW)
    assert bar["count"] == L["counts"]["YOU"] and {x["kind"] for x in bar["items"]} == {"drafts", "ask"}
    ask = [x for x in bar["items"] if x["id"] == f"ask:{y['num']}"][0]
    assert ask["market"] == "both" and ask["review"]["proposal"] == "yes, it is one step" and ask["line"].startswith("Phone notes")
    assert "research drafts" in bar["line"] and bar["line"].endswith("waiting for your yes.")
    assert [x["id"] for x in openlist.short(j, market="india", now=NOW)["work_to_do"]] == []                              # the crypto work is not India's
    assert [x["line"] for x in openlist.short(j, market="crypto", now=NOW)["work_to_do"]] == ["Ananta cannot say when you last spoke."]
    assert p["num"] and openlist.market_of({"about": "list:india", "text": "x"}) == "india" and L["problems"] == []
    t = openlist.text(j, NOW)
    assert "## Needs your yes (3)" in t and "## Work to do (1)" in t and "due 2026-11-23" in t and "Advice: yes, it is one step" in t


def test_a_fix_closes_its_item_through_the_change_book_and_the_flow_follows(j, tmp_path):
    a = fixflow.flag(j, "The dial readout was a day behind at 00:06", market="crypto", screen="reconstruction", use_ai=False)
    b = requests_log.add(j, "data", "Lost runs: the Mac slept", by="claude")
    assert fixflow.get(j, a["num"])["state"] == "triaged"
    line = {"date": "2026-11-10", "words": "The dial's kept answer is dropped when the night's candles land.", "commits": ["9c9708cabc"],
            "closes": [a["num"], {"num": b["num"], "how": "Explained: a planned sleep, nothing to change.", "done": False, "quiet": True}, 9999]}
    (tmp_path / "changes.jsonl").write_text(json.dumps(line) + "\n")
    assert openlist.apply_closes(j) == [a["num"], b["num"]]
    ra, rb = openlist._get(j, a["num"]), openlist._get(j, b["num"])
    assert ra["status"] == "DONE" and ra["note"].startswith("Fixed: The dial's kept answer") and ra["closed_by"] == "change book 2026-11-10, commit 9c9708c"
    assert (ra["pushed"], ra["told"]) == (0, 0)                                # a fix is news: the phone and the next conversation hear it
    assert rb["status"] == "WONT" and (rb["pushed"], rb["told"]) == (1, 1)     # a quiet clean-up is not
    assert fixflow.get(j, a["num"])["state"] == "deployed"                     # the fix flow no longer says "waiting for your choice"
    assert openlist.apply_closes(j) == [] and openlist.apply_closes(j, force=True) == []      # once
    assert openlist.problems(j) == ["the change book closes item 9999, which is not on the board"]
    assert openlist.collect(j, NOW)["counts"]["WORK"] == 0


def test_the_list_names_its_own_problems(j):
    a = requests_log.add(j, "bug", "An item nobody gave a kind", by="ananta-auto")     # it is work to do until someone says otherwise
    old = openlist.open_item(j, "Work that has not moved.", "WORK")
    due = openlist.open_item(j, "A check that was due.", "DATE", due="2026-11-01")
    j.db.execute("UPDATE owner_requests SET t=?, updated_t=? WHERE num=?", (NOW - 20 * DAY, NOW - 20 * DAY, old["num"]))
    f = fixflow.flag(j, "A flag closed outside the list", market="crypto", screen="x", use_ai=False)
    requests_log.set_status(j, f"request {f['num']}", "DONE", "done by hand")      # the old way of closing: the flow now closes with it
    assert fixflow.get(j, f["num"])["state"] == "deployed"
    g = fixflow.flag(j, "A flag whose flow was left behind", market="crypto", screen="x", use_ai=False)
    j.db.execute("UPDATE owner_requests SET status='WONT' WHERE num=?", (g["num"],))                  # written past every function
    L = openlist.collect(j, NOW)
    said = " | ".join(L["problems"])
    assert a["num"] in [x["num"] for x in L["work"]] and "was due on 2026-11-01 and is still open" in said
    assert "has not moved in 14 days" in said and "is closed but its fix flow still says 'triaged'" in said
    assert L["stale"] == [requests_log.label(old["num"])] and [x for x in L["dated"] if x.get("overdue")][0]["id"] == requests_log.label(due["num"])
    with pytest.raises(ValueError):
        openlist.open_item(j, "x", "SOMEDAY")


def test_a_finding_ananta_files_by_itself_is_work_and_is_never_put_to_him_as_pick_a_fix(j):
    """10 Nov: an officer check filed by the machine sat in the bar as "Flag N: pick a fix" beside the morning review's "the rule held"."""
    f = fixflow.flag(j, "Officer check core_gap failed", market="crypto", screen="officer", use_ai=False, topic="officer:core_gap", waits="WORK")
    assert fixflow.get(j, f["num"])["state"] == "noted" and openlist._get(j, f["num"])["waits"] == "WORK"
    L, bar = openlist.collect(j, NOW), waiting.collect(j, NOW)
    assert [x["num"] for x in L["work"]] == [f["num"]] and all(x["kind"] != "flag_pick" for x in bar["items"]) and L["problems"] == []
    old = fixflow.flag(j, "A flag from before the list, with no kind", market="crypto", screen="x", use_ai=False)       # the old path still shows
    assert any(x["id"] == f"flag:{old['num']}" for x in waiting.collect(j, NOW)["items"])
