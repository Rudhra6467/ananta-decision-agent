"""The due list: everything owed after the crypto lock, each with the date or the moment it falls due (docs/knowledge/due_list.json).

The lock parks every open audit item on a process that will come back to it (Madhav, Oct 15: "park it for daily reconstruction process
and updates reviews"). This file is where each one is written down with its date, so a parked item cannot go quiet:

  * the nightly watch reads it (`nightly`): an item whose date has passed and that nobody marked done becomes ONE repair-board request
    (by ananta-auto), once for that item and date; on the first night after the evidence window ends, the post-window list becomes one
    request; a list that disagrees with its own rules becomes one request;
  * the morning review lists what is due or overdue (`rows`);
  * docs/LOCK.md prints the post-window items and the decisions waiting for Madhav from here, and the audit register's SCHEDULED and
    PARKED_WINDOW rows must point at an item here (tests/test_audit_register.py).

The plan is the JSON file and does not change when work is done. Finishing is a record in the database (`mark_done`, engine_state key
kb:due_done:<id>:<n>), made by the script or the person who did the work:
  * once / evidence / post-window items: done once marked;
  * weekly / monthly / quarterly items: `due` is the FIRST date; marking done completes the earliest unfinished date and the next
    one becomes due (a month clamps to its last day). Missed dates stay overdue until marked.
Nothing here trades, changes a setting or runs a study.
"""
from __future__ import annotations

import calendar
import hashlib
import json
import re
import time
from pathlib import Path

DAY = 86400
SOON_DAYS = 7
CADENCES = ("once", "weekly", "monthly", "quarterly", "evidence")     # evidence = a count the ledger keeps, not a calendar date
RECURRING = {"weekly": 0, "monthly": 1, "quarterly": 3}               # months per step (weekly steps by 7 days)


def path(j=None) -> Path:
    from jarvis.service import core

    return core.docs_dir(getattr(j, "dir", ".")) / "knowledge" / "due_list.json"


def load(j=None, p: Path | None = None) -> dict:
    return json.loads((p or path(j)).read_text())


def _ts(s: str) -> int:
    return calendar.timegm(time.strptime(s, "%Y-%m-%d"))


def _fmt(t: float) -> str:
    return time.strftime("%Y-%m-%d", time.gmtime(t))


def _date_ok(s) -> bool:
    if not (isinstance(s, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", s)):
        return False
    try:
        _ts(s)
    except ValueError:
        return False
    return True


def occurrence(first: str, cadence: str, k: int) -> str:
    """The k-th due date (0 = the first) of a recurring item."""
    if cadence == "weekly":
        return _fmt(_ts(first) + 7 * DAY * k)
    if cadence in RECURRING:
        y, m, d = (int(x) for x in first.split("-"))
        n = (m - 1) + RECURRING[cadence] * k
        y, m = y + n // 12, n % 12 + 1
        return f"{y:04d}-{m:02d}-{min(d, calendar.monthrange(y, m)[1]):02d}"
    return first


def problems(d: dict) -> list[str]:
    """What is wrong with the list itself (a duplicate id, an item with no date, a date that is not a date)."""
    out, seen = [], set()
    for it in d.get("items", []):
        i = it.get("id")
        if not i or i in seen:
            out.append(f"id missing or used twice: {i}")
        seen.add(i)
        cad = it.get("cadence", "once")
        if cad not in CADENCES:
            out.append(f"{i}: unknown cadence {cad}")
        if not (it.get("what") and it.get("how")):
            out.append(f"{i}: says neither what nor how")
        if it.get("after_window"):
            if it.get("due"):
                out.append(f"{i}: a post-window item has no date of its own")
            if cad != "once":
                out.append(f"{i}: a post-window item is one-off")
        elif cad == "evidence":
            if not it.get("goal"):
                out.append(f"{i}: an evidence item needs its goal written down")
            if it.get("due"):
                out.append(f"{i}: an evidence item has no date")
        elif not _date_ok(it.get("due")):
            out.append(f"{i}: due is not a date")
        if it.get("done") and not _date_ok(it["done"]):
            out.append(f"{i}: done is not a date")
    return out


def window_end(j=None) -> str | None:
    """The first day after the evidence window (strategy_status.evidence_window: start + days; crypto trades every day)."""
    from jarvis.service import strategy_status

    w = strategy_status.load().get("evidence_window") or {}
    if not w.get("start"):
        return None
    return _fmt(_ts(w["start"]) + int(w.get("days", 60)) * DAY)


# ---------- the record of finished work ----------
def _key(i: str, k: int) -> str:
    return f"kb:due_done:{i}:{k}"


def _state(j, key: str):
    j.db.execute("CREATE TABLE IF NOT EXISTS engine_state (k TEXT PRIMARY KEY, v TEXT)")
    r = j.db.execute("SELECT v FROM engine_state WHERE k=?", (key,)).fetchone()
    return r[0] if r else None


def _next_k(j, it: dict) -> int | None:
    """The earliest unfinished date of an item: 0 for a one-off, the n-th for a recurring one; None when a one-off is finished."""
    if it.get("done"):
        return None
    if it.get("cadence", "once") in RECURRING:
        return next(k for k in range(0, 4000) if _state(j, _key(it["id"], k)) is None)
    return None if _state(j, _key(it["id"], 0)) is not None else 0


def mark_done(j, item_id: str, note: str = "") -> dict:
    """Record that the earliest unfinished date of an item is done (a script calls this when its work finished)."""
    it = next((x for x in load(j).get("items", []) if x["id"] == item_id), None)
    if it is None:
        raise KeyError(f"no due-list item named {item_id}")
    k = _next_k(j, it)
    if k is None:
        return {"id": item_id, "already_done": True}
    j.db.execute("CREATE TABLE IF NOT EXISTS engine_state (k TEXT PRIMARY KEY, v TEXT)")
    j.db.execute("INSERT OR REPLACE INTO engine_state VALUES (?, ?)", (_key(item_id, k), f"{int(j.now())}|{note[:200]}"))
    j.db.commit()
    return {"id": item_id, "marked": k, "date": _date_of(it, k)}


def mark_done_through(j, item_id: str, note: str = "", today: str | None = None) -> dict:
    """For a weekly, monthly or quarterly job that just ran: mark every unfinished date up to today (a run stands for the weeks it covers;
    a date missed earlier has already become a request). A date still in the future is left alone."""
    it = next((x for x in load(j).get("items", []) if x["id"] == item_id), None)
    if it is None:
        raise KeyError(f"no due-list item named {item_id}")
    if it.get("cadence", "once") not in RECURRING:
        raise ValueError(f"{item_id} is not a recurring item; use mark_done")
    today = today or _fmt(j.now())
    marked = []
    while True:
        k = _next_k(j, it)
        if k is None or _date_of(it, k) > today:
            break
        mark_done(j, item_id, note)
        marked.append(_date_of(it, k))
    return {"id": item_id, "marked": marked}


def _date_of(it: dict, k: int | None) -> str | None:
    if it.get("after_window") or it.get("cadence") == "evidence" or k is None:
        return None
    return occurrence(it["due"], it.get("cadence", "once"), k) if it.get("cadence", "once") in RECURRING else it["due"]


# ---------- reading it ----------
def rows(j, today: str | None = None, d: dict | None = None) -> list[dict]:
    """Every item with its next date and its state: overdue | soon | later | evidence | post_window | done."""
    d = d or load(j)
    today = today or _fmt(j.now())
    soon_to = _fmt(_ts(today) + SOON_DAYS * DAY)
    out = []
    for it in d.get("items", []):
        k = _next_k(j, it)
        due = _date_of(it, k)
        if k is None:
            state = "done"
        elif it.get("after_window"):
            state = "post_window"
        elif it.get("cadence") == "evidence":
            state = "evidence"
        else:
            state = "overdue" if due < today else "soon" if due <= soon_to else "later"
        out.append({"id": it["id"], "what": it["what"], "how": it["how"], "due": due, "state": state, "cadence": it.get("cadence", "once"),
                    "owner": it.get("owner"), "goal": it.get("goal"), "owner_decision": bool(it.get("owner_decision"))})
    return out


def check(j, today: str | None = None, d: dict | None = None) -> dict:
    """Overdue (date passed, not done), due within a week, evidence items still waiting, and the post-window list."""
    d = d or load(j)
    today = today or _fmt(j.now())
    rs = rows(j, today, d)
    end = window_end(j)
    ids = lambda s: [r["id"] for r in rs if r["state"] == s]  # noqa: E731
    return {"today": today, "overdue": ids("overdue"), "soon": ids("soon"), "waiting_for_evidence": ids("evidence"),
            "post_window": ids("post_window"), "done": ids("done"), "window_end": end, "window_over": bool(end and today >= end),
            "problems": problems(d), "rows": rs}


def _flag(j, key: str, text: str, about: str) -> bool:
    """File one repair-board request, once for this key. True when it was filed now."""
    j.db.execute("CREATE TABLE IF NOT EXISTS engine_state (k TEXT PRIMARY KEY, v TEXT)")
    if j.db.execute("SELECT 1 FROM engine_state WHERE k=?", (key,)).fetchone():
        return False
    from jarvis.service import requests_log

    requests_log.add(j, "data", text, about=about, by="ananta-auto")
    j.db.execute("INSERT OR REPLACE INTO engine_state VALUES (?, ?)", (key, str(int(j.now()))))
    j.db.commit()
    return True


def nightly(j, today: str | None = None) -> dict:
    """The nightly run of check(): every overdue item becomes one request (once for that item and that date), a broken list becomes one
    request (once for that set of problems), and the first night after the window the post-window list becomes one request."""
    r = check(j, today)
    flagged = []
    for row in r["rows"]:
        if row["state"] == "overdue" and _flag(j, f"kb:due_flag:{row['id']}:{row['due']}",
                                               f"Due list: '{row['id']}' was due {row['due']} and is not marked done - {row['what']} "
                                               f"How: {row['how']}", "due list"):
            flagged.append(row["id"])
    if r["problems"]:
        k = "kb:due_list_problems:" + hashlib.sha1("\n".join(sorted(r["problems"])).encode()).hexdigest()[:12]
        if _flag(j, k, "The due list disagrees with its own rules: " + "; ".join(r["problems"][:6]) + ".", "due list"):
            flagged.append("problems")
    if r["window_over"] and r["post_window"]:
        if _flag(j, "kb:due_post_window",
                 f"The evidence window ended on {r['window_end']}: {len(r['post_window'])} post-window items are waiting "
                 f"({', '.join(r['post_window'][:8])}{', ...' if len(r['post_window']) > 8 else ''}). Decide their order; docs/LOCK.md lists them.",
                 "due list"):
            flagged.append("post-window")
    r["flagged"] = flagged
    return r


def line(r: dict) -> str:
    """One line for the nightly note."""
    bits = [f"{len(r['overdue'])} overdue" + (f" ({', '.join(r['overdue'][:4])})" if r["overdue"] else ""),
            f"{len(r['soon'])} due this week" + (f" ({', '.join(r['soon'][:4])})" if r["soon"] else ""),
            f"{len(r['waiting_for_evidence'])} waiting for evidence", f"{len(r['post_window'])} after the window"]
    return "due list: " + ", ".join(bits) + (f"; PROBLEMS: {'; '.join(r['problems'][:3])}" if r["problems"] else "")
