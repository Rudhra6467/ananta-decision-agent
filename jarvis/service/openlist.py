"""The open list: the one answer to "what is open, and what is it waiting for?" (Madhav, 10 Nov 2026: "how to completely comprehend this
into a single set, like where we don't get into this confusion" ... "yes, lets do it. we have to make it clear, simple and coherent").

Before this there were about ten places that each said what was open, in their own words, and none was closed when the work was done:
the repair board, the fix flow, the "waiting for your yes" bar, each morning page's own "Waiting for Madhav" list, the due list, and the
"still open" lists at the end of dated notes. On 10 Nov, 14 of the board's 20 "planned" items were finished, explained or repeats.

THE RULES (kept by code, not by memory)
  1. One list. Everything open is one line with a fixed name and one of four kinds:
       YOU     needs Madhav's yes, or something only he can do
       WORK    work to do
       DATE    waiting for a date or for evidence
       PARKED  parked on purpose
  2. Two kinds of source, and nothing else:
       the board (owner_requests): every item kept by hand, numbered ("flag 53"), with its kind in `waits`;
       registers that keep their own state and cannot go stale: the due list (dates, evidence, after-the-window items), India's research
       drafts, the crypto "Needs you" cards, the strategy list (what is switched off). They are read live, never copied.
  3. A dated note never holds an open list. A note says what was done and names the items it opened or closed.
  4. Seen again is not a new item: a filing with the same `topic` as an open item joins it (seen 2, seen 3 ...).
  5. A fix closes its item. The change book line of the fix names it in `closes`; apply_closes() closes it on the board and in the fix flow,
     with what closed it. Nothing is closed by words alone.
  6. Every reader reads this list: the app's bar (/v3/waiting), /v3/open, both Asks, the morning review page (printed, not written),
     the night test, and each work session.
  7. An item that has not moved in STALE_DAYS is named as stale: it is kept, parked or dropped, never left.
  8. What closed lately travels with the list (closed_lately: the last CLOSED_HOURS, newest first, each by its name with what closed it and
     the proof), so every reader can say what got done, not only what is open (11 Nov 2026, Madhav: "it also gets updates back when done
     and keeps a track of them as well").

  collect(j)        the list
  short(j)          a few lines of it for every turn of a conversation
  close(j, ...)     close an item on the board and in the fix flow (the only way to close)
  apply_closes(j)   the change book's `closes` applied (the 15-minute loop)
  open_item(j, ...) put a new hand-kept item on the board with its kind
  set_kind(j, ...)  set an item's kind, date or topic
  answer(j, ...)    his answer from the app: yes, no, done, or later (clears it from his notifications for a week); logged
  clear_all(j)      everything waiting cleared from his notifications for a week; it all stays on the list
  quiet_keys(j)     what is cleared from his notifications now (the bell, Home's Needs you, the phone reminders)
  problems(j)       what is wrong with the list itself
  text(j)           the list as plain lines (python scripts/open_list.py)
Read-only except close / apply_closes / open_item / set_kind / answer / clear_all. Nothing here trades or changes a rule."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHANGES = ROOT / "docs" / "knowledge" / "changes.jsonl"
KINDS = ("YOU", "WORK", "DATE", "PARKED")
KIND_WORDS = {"YOU": "needs your yes", "WORK": "work to do", "DATE": "waiting for a date or for evidence", "PARKED": "parked on purpose"}
STALE_DAYS = 14
FLOW_FINAL = ("deployed", "cancelled", "noted")
_APPLIED: dict = {"m": None}


def market_of(r: dict) -> str:
    about, text = str(r.get("about") or ""), str(r.get("text") or "")
    if about.endswith(":both") or text.startswith("[Both"):
        return "both"
    if about.startswith(("flag:india", "note:india", "list:india")) or text.startswith("[Indian market"):
        return "india"
    return "crypto"


def plain(text: str, n: int = 170) -> str:
    """One plain line: the bracket label goes, the first sentence or two stay, never cut inside a word."""
    s = re.sub(r"^\[[^\]]*\]\s*", "", " ".join(str(text or "").split()))
    if len(s) <= n:
        return s
    head = s[:n]
    k = head.rfind(". ")
    if k > 60:
        return head[:k + 1]
    return head.rsplit(" ", 1)[0].rstrip(" ,;:") + "…"


def advice_of(note: str | None) -> str | None:
    """The advice written on an item ("Advice: ..."), without the older note kept after it."""
    m = re.search(r"Advice:\s*(.+?)(?:\s\|\s|$)", " ".join(str(note or "").split()))
    return m.group(1).strip()[:240] if m else None


def _day(t) -> str:
    return time.strftime("%Y-%m-%d", time.gmtime(float(t or 0)))


_NOTE_PREFIX = re.compile(r"^(First answer[^:]*:|Morning review[^:]*:|Advice:)\s*", re.I)
_NOTE_DATE = re.compile(r"^\d{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*[:,]\s*")
_BUILT = re.compile(r"^(built|done|fixed and live|live|finished)\b", re.I)
_FIRST = re.compile(r"^do this first\b", re.I)


def whole_clip(text, n: int) -> str:
    """At most n characters, cut at the last full sentence, else the last whole word (a stored line was cut mid-word: "no sto", "stays fr")."""
    s = str(text or "")
    if len(s) <= n:
        return s
    head = s[:n]
    cut = max(head.rfind(". "), head.rfind("! "), head.rfind("? "))
    if cut >= n // 2:
        return head[: cut + 1]
    return head[: head.rfind(" ")].rstrip(",;:( ") + "…" if " " in head else head


def latest_step(note) -> str:
    """The newest step of an item's note: the first part before " | ", without its label or its date."""
    s = _NOTE_PREFIX.sub("", str(note or "").split(" | ")[0]).strip()
    return _NOTE_DATE.sub("", s).strip()


def scenario_of(kind: str, built: bool = False) -> str:
    """Where an item stands, which decides the sheet's words and buttons: DECIDE (waits for his yes), BUILDING (Ananta is doing it), CHECK
    (its latest step says it is built or done, so he looks it over), DATE (waits for a day or for evidence), PARKED."""
    return {"YOU": "DECIDE", "DATE": "DATE", "PARKED": "PARKED"}.get(kind) or ("CHECK" if built else "BUILDING")


def to_you(text) -> str:
    """The list is written for him: \"Madhav said yes\" reads \"You said yes\"."""
    s = re.sub(r"(^|[.:;|]\s+)Madhav's\b", r"\1Your", str(text or ""))
    s = re.sub(r"Madhav's\b", "your", s)
    s = re.sub(r"(^|[.:;|]\s+)Madhav\b", r"\1You", s)
    return re.sub(r"\bMadhav\b", "you", s)


def _board(j, now: float) -> list[dict]:
    from jarvis.service import requests_log

    out = []
    try:
        picks = {n for (n,) in j.db.execute("SELECT num FROM fix_flow WHERE state IN ('triaged','needs_decision') AND t >= ?", (now - 7 * 86400,))}
    except Exception:  # noqa: BLE001
        picks = set()
    for r in reversed(requests_log.list_(j, include_done=False)):
        # an item nobody gave a kind is work to do; except an old-style flag still offering him a fix this week, which the bar shows as his
        kind = r.get("waits") if r.get("waits") in KINDS else ("YOU" if r["num"] in picks and r["status"] == "OPEN" else "WORK")
        last = float(r.get("updated_t") or r.get("t") or now)
        it = {"id": r["label"], "num": r["num"], "kind": kind, "market": market_of(r), "line": r.get("line") or plain(r["text"]), "since": _day(r.get("t")),
              "days": int((now - float(r.get("t") or now)) // 86400), "source": "board"}
        if int(r.get("seen") or 1) > 1:
            it["seen"] = int(r["seen"])
        if r.get("due"):
            it["due"] = r["due"]
        note = str(r.get("note") or "")
        step = latest_step(note)
        if kind == "WORK":
            if _FIRST.match(step):
                it["first"] = True
            elif _BUILT.match(step):
                it["built"] = True
        it["scenario"] = scenario_of(kind, bool(it.get("built")))
        if advice_of(note):
            it["advice"] = advice_of(note)
        if kind in ("YOU", "WORK") and now - last > STALE_DAYS * 86400:
            it["stale"] = True
        if kind == "DATE" and r.get("due") and r["due"] < _day(now):
            it["overdue"] = True
        out.append(it)
    return out


def _due(j) -> list[dict]:
    """The due list's own rows (docs/knowledge/due_list.json): dated, waiting for evidence, and after-the-window items. Read live."""
    try:
        from jarvis.service import due_list

        rows = due_list.rows(j)
    except Exception:  # noqa: BLE001  a missing list never breaks the open list
        return []
    try:
        said = {i["id"]: i.get("plain") for i in due_list.load(j).get("items", [])}       # the item in one plain line, when the list gives one
    except Exception:  # noqa: BLE001
        said = {}
    out = []
    for r in rows:
        if r["state"] == "done":
            continue
        kind = "PARKED" if r["state"] == "post_window" else "DATE"
        if r.get("owner_decision") and r["state"] in ("overdue", "soon"):
            kind = "YOU"
        it = {"id": r["id"], "kind": kind, "market": "crypto", "line": said.get(r["id"]) or plain(r["what"], 150), "source": "due list",
              "state": {"post_window": "after the evidence window", "evidence": "waiting for evidence"}.get(r["state"], r["state"])}
        if r.get("due"):
            it["due"] = r["due"]
        if r["state"] == "overdue":
            it["overdue"] = True
        out.append(it)
    return out


def _strategies() -> list[dict]:
    try:
        from jarvis.service import strategy_status

        st = strategy_status.load().get("strategies") or {}
    except Exception:  # noqa: BLE001
        return []
    return [{"id": f"strategy {k}", "kind": "PARKED", "market": "crypto", "line": plain(f"{v.get('name') or k}: switched off. {v.get('why') or ''}", 150),
             "source": "strategy list"} for k, v in st.items() if v.get("status") == "PARKED"]


def collect(j, now: float | None = None) -> dict:
    """The whole list. `you` is exactly what the app's bar shows (waiting.collect), so the two can never disagree."""
    from jarvis.service import waiting

    now = now or time.time()
    try:
        apply_closes(j)
    except Exception:  # noqa: BLE001  the list is still read
        pass
    board = _board(j, now)
    due = _due(j)
    w = waiting.collect(j, now)
    low = lambda t: (t[:1].lower() + t[1:]) if str(t).lower().startswith(("flag ", "request ")) else t      # noqa: E731
    you = [{"id": low(x.get("title") or x["id"]), "key": x["id"], "kind": "YOU", "market": x.get("market") or "crypto", "line": plain(x.get("line") or x.get("title") or "", 190),
            "count": int(x.get("count") or 1), "source": {"drafts": "India research drafts", "needs": "crypto Needs you"}.get(x.get("kind"), "board"),
            **({"on_yes": x["on_yes"]} if x.get("on_yes") else {}),
            **({"advice": (x.get("review") or {}).get("proposal")} if (x.get("review") or {}).get("proposal") else {})} for x in w["items"]]
    work = sorted([x for x in board if x["kind"] == "WORK"], key=lambda x: not x.get("first"))        # his "do this first" items lead
    dated = sorted([x for x in board if x["kind"] == "DATE"] + [x for x in due if x["kind"] == "DATE"], key=lambda x: (x.get("due") or "9999", str(x["id"])))
    parked = [x for x in board if x["kind"] == "PARKED"] + [x for x in due if x["kind"] == "PARKED"] + _strategies()
    nxt = next((x for x in dated if x.get("due") and x["due"] >= _day(now)), None)
    counts = {"YOU": sum(x["count"] for x in you), "WORK": len(work), "DATE": len(dated), "PARKED": len(parked)}
    s = lambda n, one, many: f"{n} {one if n == 1 else many}"                          # noqa: E731
    line = (f"Open list: {s(counts['YOU'], 'thing needs', 'things need')} your yes, {s(counts['WORK'], 'is', 'are')} work to do, "
            f"{s(counts['DATE'], 'waits', 'wait')} for a date or for evidence" + (f" (next: {nxt['due']})" if nxt else "")
            + f", {s(counts['PARKED'], 'is', 'are')} parked on purpose.")
    stale = [x["id"] for x in work if x.get("stale")]
    return {"as_of": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(now)), "line": line, "counts": counts, "waiting_line": w.get("line") or "",
            "you": you, "work": work, "dated": dated, "parked": parked, "stale": stale, "problems": problems(j, board=board),
            "quiet": sorted(quiet_keys(j, now)),
            "closed_lately": closed_lately(j, now=now)[:12],
            "kinds": KIND_WORDS,
            "how": ("This is the only place that says what is open. Say an item by its name ('flag 53', 'CHECKPOINT-30'). Something not on this "
                    "list is not open: it is done, dropped or was never filed. A dated note or the morning page is history, not the list.")}


def short(j, market: str | None = None, now: float | None = None) -> dict:
    """A few lines for every turn: the count line, what needs his yes, this market's work, the next dates, and what closed lately."""
    d = collect(j, now)
    mine = lambda x: not market or x.get("market") in (market, "both")                   # noqa: E731
    return {"line": d["line"], "as_of": d["as_of"],
            "needs_your_yes": [{k: x.get(k) for k in ("id", "market", "line", "advice") if x.get(k)} for x in d["you"]][:8],
            # 11 Nov: with each item's advice, as the crypto lookup has it ("what did the re-grade score last time?": the 6.5 is in its advice)
            "work_to_do": [{k: x.get(k) for k in ("id", "line", "seen", "stale", "advice") if x.get(k)} for x in d["work"] if mine(x)][:8],
            "next_dates": [{k: x.get(k) for k in ("id", "due", "line", "advice") if x.get(k)} for x in d["dated"] if mine(x) and x.get("due")][:5],
            "closed_lately": [{k: x.get(k) for k in ("id", "line", "result", "how", "when") if x.get(k)} for x in d["closed_lately"] if mine(x)][:6],
            "parked": d["counts"]["PARKED"], "how": d["how"]}


CLOSED_HOURS = 48


def closed_lately(j, hours: float = CLOSED_HOURS, market: str | None = None, now: float | None = None) -> list[dict]:
    """What was finished or dropped in the last `hours`, newest first (rule 8). Each item by its name, with what closed it and the proof:
    close() and the change book's `closes` write both, and the scheduled checks close their own items when they run. So "what did we finish
    today?" and "is X done?" are answered from the list, never from memory."""
    from jarvis.service import requests_log

    now = now or time.time()
    try:
        rows = requests_log.list_(j, include_done=True)
    except Exception:  # noqa: BLE001  the closed part never breaks the open list
        return []
    out = []
    for r in rows:
        if r.get("status") not in ("DONE", "WONT"):
            continue
        t = float(r.get("updated_t") or r.get("t") or 0)
        if now - t > hours * 3600:
            continue
        m = market_of(r)
        if market and m not in (market, "both"):
            continue
        out.append({"id": r["label"], "num": r["num"], "market": m, "line": plain(r["text"], 150),
                    "result": "done" if r["status"] == "DONE" else "dropped", "how": plain(r.get("note") or "", 200),
                    "proof": str(r.get("closed_by") or "")[:160], "when": time.strftime("%a %d %b %H:%M", time.localtime(t)), "t": int(t)})
    try:                       # the due list's own dates marked done (a checkpoint, the monthly cost check): due_list.mark_done keeps them
        from jarvis.service import due_list

        said = {i["id"]: i.get("plain") or plain(i.get("what") or i["id"], 150) for i in due_list.load(j).get("items", [])}
        for k, v in j.db.execute("SELECT k, v FROM engine_state WHERE k LIKE 'kb:due_done:%'").fetchall():
            t_s, _, note = str(v).partition("|")
            t = float(t_s or 0)
            if now - t > hours * 3600 or (market and market not in ("crypto", "both")):
                continue
            item = str(k).split(":")[2]
            out.append({"id": item, "num": None, "market": "crypto", "line": said.get(item) or item, "result": "done",
                        "how": plain(note, 200) or "marked done", "proof": "the due list",
                        "when": time.strftime("%a %d %b %H:%M", time.localtime(t)), "t": int(t)})
    except Exception:  # noqa: BLE001  no due list or no marks yet
        pass
    out.sort(key=lambda x: -x["t"])
    return out


# ---------------------------------------------------------------- closing: the one way
def _get(j, num: int) -> dict | None:
    from jarvis.service import requests_log

    rows = requests_log._select(j, "WHERE num=?", (int(num),))
    return rows[0] if rows else None


def close(j, num: int, how: str, done: bool = True, by: str = "", quiet: bool = False) -> dict:
    """Close one board item by its stored number: the request, and its fix flow when it has one that is not finished. `how` says in plain
    words what closed it; `by` names the proof (a commit, a change-book line, his words). quiet: no phone note and no mention (a clean-up)."""
    r = _get(j, num)
    if not r:
        raise ValueError(f"no item {num}")
    if r["status"] in ("DONE", "WONT"):
        return {**r, "already": True}
    now = int(j.now())
    status = "DONE" if done else "WONT"
    j.db.execute("UPDATE owner_requests SET status=?, note=?, closed_by=?, updated_t=?, pushed=?, told=? WHERE id=?",
                 (status, (how or r["note"] or "")[:400], (by or "")[:240], now, 1 if quiet else 0, 1 if quiet else 0, r["id"]))
    try:
        f = j.db.execute("SELECT state, log FROM fix_flow WHERE num=?", (int(num),)).fetchone()
        if f and f[0] not in FLOW_FINAL:
            log = json.loads(f[1] or "[]") + [[now, f"closed with the item: {(how or '')[:160]}"]]
            j.db.execute("UPDATE fix_flow SET state=?, log=?, updated_t=? WHERE num=?", ("deployed" if done else "cancelled", json.dumps(log), now, int(num)))
    except Exception:  # noqa: BLE001  no fix flow table yet
        pass
    j.db.commit()
    return _get(j, num)


def apply_closes(j, path: Path | None = None, force: bool = False) -> list[int]:
    """Rule 5: the change book's `closes` close their items. Each entry is a stored number (134) or {"num": 134, "how": "...", "done": true,
    "quiet": true}. Cheap: the file is read again only when it has changed."""
    p = path or CHANGES
    try:
        m = p.stat().st_mtime
    except OSError:
        return []
    if not force and _APPLIED["m"] == (str(p), m):
        return []
    closed = []
    for ln in p.read_text().splitlines():
        if '"closes"' not in ln:
            continue
        try:
            c = json.loads(ln)
        except ValueError:
            continue
        for e in c.get("closes") or []:
            e = e if isinstance(e, dict) else {"num": e}
            try:
                r = _get(j, int(e["num"]))
            except (KeyError, TypeError, ValueError):
                continue
            if not r or r["status"] in ("DONE", "WONT"):
                continue
            by = f"change book {c.get('date')}" + (f", commit {', '.join(str(x)[:7] for x in (c.get('commits') or [])[:2])}" if c.get("commits") else "")
            close(j, int(e["num"]), e.get("how") or f"Fixed: {str(c.get('words') or '')[:300]}", done=e.get("done", True), by=e.get("by") or by,
                  quiet=bool(e.get("quiet")))
            closed.append(int(e["num"]))
    _APPLIED["m"] = (str(p), m)
    return closed


def open_item(j, text: str, waits: str, market: str = "crypto", due: str | None = None, topic: str | None = None, advice: str | None = None,
              by: str = "claude", on_yes: str | None = None) -> dict:
    """A new hand-kept item on the board with its kind. The same words or the same topic as an open item join it (no second copy)."""
    from jarvis.service import requests_log

    if waits not in KINDS:
        raise ValueError(f"kind is one of {KINDS}")
    market = market if market in ("crypto", "india", "both") else "crypto"
    where = {"india": "[Indian market · list] ", "crypto": "[Crypto · list] ", "both": "[Both markets · list] "}[market]
    r = requests_log.add(j, "idea", where + text.strip(), about=f"list:{market}", by=by, topic=topic, waits=waits, due=due)
    if advice and not r.get("duplicate"):
        j.db.execute("UPDATE owner_requests SET note=? WHERE num=?", (("Advice: " + advice)[:400], r["num"]))
        j.db.commit()
    if on_yes and not r.get("duplicate"):                # "done": his yes closes it (a look, a confirmation); otherwise a yes makes it work to do
        j.db.execute("UPDATE owner_requests SET on_yes=? WHERE num=?", (on_yes, r["num"]))
        j.db.commit()
    return r


# ---------------------------------------------------------------- his answers from the app (Madhav, 10 Nov 22:33)
# "Can I add something like ... after reading I can click on that, like it's get approved straight away instead of only asking Ananta";
# "Even if I click no, like not now, it is still there in the notification ... I should be able to still clear that notifications" while
# "this thing should be saved in the log and the flags list". A YOU item in the app's sheet offers Yes (or Done for his own step), No and
# Not now. Not now clears it from his notifications (the bell, Home's Needs you, the phone reminders) for QUIET_DAYS; it stays on the open
# list and comes back once after that. Every answer is kept in owner_answers.
QUIET_DAYS = 7
ANSWER_LABEL = {"yes": "Yes", "no": "No", "done": "Done", "later": "Not now", "postpone": "Postpone",
                "first": "Do this one first", "pause": "Pause it", "drop": "Drop it", "reopen": "Not right, reopen it",
                "check": "Check it earlier", "bring_back": "Bring it back"}
ITEM_ANSWERS = ("done", "postpone", "first", "pause", "drop", "reopen", "check", "bring_back")
# 11 Nov 2026 (Madhav, 07:51: "I couldn't get to know their status or. Mark it done or postpone it. I couldn't do anything here"): every item
# on the open list can be marked done or postponed from its sheet; a postponed item waits for its date and is due again that day. 14 Dec is
# the day the crypto scorecard freeze ends, when the rule questions open again.
POSTPONE = (("tomorrow", "Tomorrow", 1), ("week", "Next week", 7), ("2026-12-14", "On 14 Dec", None))


def postpone_options(today=None) -> list[dict]:
    import datetime as dt
    d = today or dt.date.today()
    return [{"id": i, "label": lab} for i, lab, days in POSTPONE if days is not None or str(d) < i]


POSTPONE_ROW = {"tomorrow": "Postpone to tomorrow", "week": "Postpone a week", "2026-12-14": "Postpone to 14 Dec"}
# 21 Nov 2026 (Madhav: the sheet's options did not fit the item; "refine and go with scenario based"): the sheet's buttons depend on where
# the item stands. A decision is answered Yes / No / ask me again; work Ananta is doing is pushed first, paused or dropped (never "marked
# done" by him); built work is checked by him and closed or sent back; a dated item is checked earlier or moved; a parked one is brought back.
ASK_ROW = {"tomorrow": "Ask me again tomorrow", "week": "Ask me again in a week", "2026-12-14": "Ask me again on 14 Dec"}
MOVE_ROW = {"tomorrow": "Move it to tomorrow", "week": "Move it a week on", "2026-12-14": "Move it to 14 Dec"}
DECIDE_LABEL = {"yes": "Yes, go ahead", "no": "No, don't do it", "done": "I did it", "later": "Not now"}
ANSWER_ICON = {"yes": "check", "no": "close", "done": "check", "later": "pause", "postpone": "clock",
               "first": "up", "pause": "pause", "drop": "close", "reopen": "flag", "check": "eye", "bring_back": "play"}


def answer_words(said: str, kind: str = "ask", on_yes: str | None = None, due: str | None = None, today=None) -> str:
    """What one answer does, in a few plain words, for the line under its row (Madhav, 11 Nov 2026, 08:13: "upon clicking, I can select
    any action, or ... have an explanation of the action"). kind: ask (a board item waiting for him), needs (a crypto card), item (an
    open-list item he marks done or postpones), drafts."""
    import datetime as dt
    if kind == "draft" and said == "yes":
        return "Ananta writes the study down first, then tests it on past years only. Nothing trades from it. Your yes is kept with the time."
    if kind == "draft" and said == "no":
        return "The draft closes as skipped and is not raised again. Your answer is kept with the time."
    if kind == "item" and said in ("first", "pause", "drop", "reopen", "check", "bring_back"):
        return {"first": "It moves to the top of the work list with your words on it. Nothing else is dropped.",
                "pause": "It moves to Parked and Ananta stops working on it. Nothing happens until you bring it back. Nothing is lost.",
                "drop": "It closes as dropped and leaves the list. Ananta does no more work on it. Your answer is kept with the time.",
                "reopen": "It goes back to work to do, marked not right, at the top of the list. Your words stay on it.",
                "check": "It leaves its wait and goes to the top of the work list now, so Ananta looks at it before its date.",
                "bring_back": "It moves back to work to do and Ananta takes it up again."}[said]
    if said == "postpone" and kind != "item":
        d = dt.date.fromisoformat(_postpone_to(due or "tomorrow", today))
        return f"It leaves your notifications until {d:%a} {d.day} {d:%b}, then comes back to ask you again. It stays on the open list. Nothing is lost."
    if said == "yes":
        if kind == "needs":
            return "Ananta does what the card asks, on paper, as if you had said yes in Ask. Your yes is kept with the time."
        return ("It closes as done. Your yes is kept with the time." if on_yes == "done" else
                "Ananta goes ahead. It becomes work to do and stays on the open list until it is done. Your yes is kept with the time.")
    if said == "no":
        return "It closes with your no, and Ananta does nothing more about it. Your answer is kept with the time."
    if said == "done":
        return ("It closes as done, checked by you, and leaves the open list. Your answer is kept with the time." if kind == "item"
                else "Your step is marked done and the item closes. Your answer is kept with the time.")
    if said == "later":
        return (f"It leaves your notifications for {QUIET_DAYS} days: the bell, Home and the phone reminders. It stays on the open list "
                f"and comes back once after the {QUIET_DAYS} days.")
    if said == "postpone":
        d = dt.date.fromisoformat(_postpone_to(due or "tomorrow", today))
        end = " That is the day the crypto scorecard freeze ends." if d.isoformat() == "2026-12-14" else ""
        return f"It waits on the open list until {d:%a} {d.day} {d:%b}, and that day it is due again. Nothing is lost.{end}"
    return ""


LATER_LABEL = ANSWER_LABEL["later"]
DRAFT_LABEL = {"yes": "Yes, study it", "no": "Skip it"}


def answer_rows(key: str | None, step: bool = False, on_yes: str | None = None, today=None) -> list[dict]:
    """A notification's answers as the sheet's rows: id, label, icon and what it does. Postpone is one row per day (one tap does it)."""
    kind = str(key or "").split(":", 1)[0]
    rows = []
    for a in answers_for(key, step):
        if a == "postpone":
            for o in postpone_options(today)[:2]:                       # tomorrow, next week
                rows.append({"id": "postpone", "due": o["id"], "label": ASK_ROW.get(o["id"], f"Ask me again: {o['label']}"), "icon": "clock",
                             "explain": answer_words("postpone", kind=kind, due=o["id"], today=today)})
            continue
        label = DRAFT_LABEL.get(a, DECIDE_LABEL[a]) if kind == "draft" else DECIDE_LABEL.get(a, ANSWER_LABEL[a])
        rows.append({"id": a, "label": label, "icon": ANSWER_ICON[a], "explain": answer_words(a, kind=kind, on_yes=on_yes)})
    return rows


def item_answers(today=None, after: str | None = None, scenario: str = "BUILDING") -> list[dict]:
    """An open-list item's answers as rows, by where it stands (scenario_of). BUILDING (Ananta is doing it): do it first, pause it, drop it.
    CHECK (Ananta says it is built): looks right, close it / not right, reopen it. DATE (waits for a day or evidence): check it earlier, move
    it (one row per day), drop it. PARKED: bring it back, drop it. after: the day a dated item already waits for; a day not later than that
    is not offered."""
    def row(i, label, **kw):
        return {"id": i, "label": label, "icon": ANSWER_ICON[i], "explain": answer_words(i, kind="item"), **kw}
    drop = row("drop", "Drop it")
    if scenario == "CHECK":
        return [row("done", "Looks right, close it"), row("reopen", "Not right, reopen it")]
    if scenario == "DATE":
        rows = [row("check", "Check it earlier")]
        for o in postpone_options(today):
            if after and _postpone_to(o["id"], today) <= str(after)[:10]:
                continue
            rows.append({"id": "postpone", "due": o["id"], "label": MOVE_ROW.get(o["id"], f"Move it: {o['label']}"), "icon": "clock",
                         "explain": answer_words("postpone", kind="item", due=o["id"], today=today)})
        return rows + [drop]
    if scenario == "PARKED":
        return [row("bring_back", "Bring it back"), drop]
    return [row("first", "Do this one first"), row("pause", "Pause it"), drop]


def _postpone_to(when: str, today=None) -> str:
    import datetime as dt
    d = today or dt.date.today()
    for i, _lab, days in POSTPONE:
        if when == i and days is not None:
            return (d + dt.timedelta(days=days)).isoformat()
    x = dt.date.fromisoformat(str(when)[:10])                 # a date of his own
    if x <= d:
        raise ValueError("postpone to a day after today")
    return x.isoformat()


def _answer_tables(j) -> None:
    j.db.execute("CREATE TABLE IF NOT EXISTS owner_answers (t INTEGER, key TEXT, answer TEXT, by TEXT, words TEXT)")
    j.db.execute("CREATE TABLE IF NOT EXISTS notice_quiet (key TEXT PRIMARY KEY, until INTEGER, t INTEGER, by TEXT)")


def quiet_keys(j, now: float | None = None) -> set:
    """The waiting items he cleared from his notifications, until they come back."""
    try:
        _answer_tables(j)
        return {k for (k,) in j.db.execute("SELECT key FROM notice_quiet WHERE until > ?", (int(now or j.now()),))}
    except Exception:  # noqa: BLE001  a missing table never hides the list
        return set()


def answers_for(key: str | None, step: bool = False) -> list[str]:
    """What the app's sheet offers for one waiting item. 14 Nov 2026 (Madhav: "only 2 action items are shown here, isn't it minimising the
    scope?"): every waiting item takes its full list. A board item: yes (done for his own step), no, later, postpone. A crypto ladder card:
    yes, later, postpone. One research draft ("draft:<key>"): yes (study it), no (skip it), later, postpone. Anything else (a flag's fixes,
    a due-list decision) is still answered in its own place, and can be put off here: later, postpone."""
    kind = str(key or "").split(":", 1)[0]
    if kind == "ask":
        return (["done", "later", "postpone"] if step else ["yes", "no", "later", "postpone"])
    if kind == "needs":
        return ["yes", "later", "postpone"]
    if kind == "draft":
        return ["yes", "no", "later", "postpone"]
    return ["later", "postpone"] if key else []


def _when(now: float) -> str:
    try:
        import datetime as dt
        from zoneinfo import ZoneInfo

        t = dt.datetime.fromtimestamp(now, ZoneInfo("America/Toronto"))
        return f"{t:%a} {t.day} {t:%b}, {t.hour % 12 or 12}:{t:%M} {'am' if t.hour < 12 else 'pm'} Toronto"
    except Exception:  # noqa: BLE001
        return time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(now))


def answer(j, key: str, said: str, by: str = "Madhav", now: float | None = None, due: str | None = None) -> dict:
    """His answer to one waiting item (waiting.collect's id: "ask:<num>", "needs:<id>", ...). yes: a board item whose on_yes is "done" closes;
    any other turns into work to do with his yes written on it, so the work it allows stays on the list until it is done. no: closed with his
    no. done: his own step, closed. later: cleared from his notifications for QUIET_DAYS. An open-list item ("item:<num>", 11 Nov 2026) takes
    done (closed, by him) or postpone (dated: `due` is tomorrow, week or a day). Every answer is logged."""
    said = str(said or "").strip().lower()
    if said not in ANSWER_LABEL:
        raise ValueError("the answer is yes, no, done, later, postpone, first, pause, drop, reopen, check or bring_back")
    _answer_tables(j)
    now = int(now or j.now())
    when = _when(now)
    kind, _, ref = str(key or "").partition(":")
    out = {"key": key, "said": said}
    keep_quiet = False
    if said == "later":
        j.db.execute("INSERT OR REPLACE INTO notice_quiet VALUES (?,?,?,?)", (key, now + QUIET_DAYS * 86400, now, by))
        out["words"] = f"Cleared from your notifications for {QUIET_DAYS} days. It stays on your open list."
    elif said == "postpone" and key and kind != "item":
        import datetime as dt
        from zoneinfo import ZoneInfo

        tz = ZoneInfo("America/Toronto")
        d = dt.date.fromisoformat(_postpone_to(due or "tomorrow", dt.datetime.fromtimestamp(now, tz).date()))
        until = int(dt.datetime(d.year, d.month, d.day, 6, 0, tzinfo=tz).timestamp())
        j.db.execute("INSERT OR REPLACE INTO notice_quiet VALUES (?,?,?,?)", (key, until, now, by))
        out["words"] = f"Saved: it comes back on {d:%a} {d.day} {d:%b}. It stays on your open list until then."
        out["due"] = d.isoformat()
        keep_quiet = True
    elif kind == "ask" and ref.isdigit():
        num = int(ref)
        r = _get(j, num)
        if not r or r["status"] in ("DONE", "WONT"):
            raise ValueError("that one is already answered")
        if said == "no":
            close(j, num, f"You said no in the app ({when}).", done=False, by=f"{by}, in the app", quiet=True)
            out["words"] = "Saved: you said no. It is closed, and your answer is kept."
        elif said == "done" or str(r.get("on_yes") or "") == "done":
            close(j, num, f"You {'did it' if said == 'done' else 'said yes'} in the app ({when}).", done=True, by=f"{by}, in the app", quiet=True)
            out["words"] = f"Saved: {'done' if said == 'done' else 'you said yes'}. It is closed, and your answer is kept."
        else:
            note = f"You said yes in the app ({when})" + (" | " + r["note"] if r.get("note") else "")
            j.db.execute("UPDATE owner_requests SET waits='WORK', note=?, updated_t=? WHERE id=?", (note[:400], now, r["id"]))
            out["words"] = "Saved: you said yes. It is now work to do, and stays on the list until it is done."
    elif kind == "item" and ref.isdigit() and said in ITEM_ANSWERS:
        num = int(ref)
        r = _get(j, num)
        if not r or r["status"] in ("DONE", "WONT"):
            raise ValueError("that one is already closed")
        old = (" | " + r["note"]) if r.get("note") else ""

        def _note(text: str) -> None:
            j.db.execute("UPDATE owner_requests SET note=?, updated_t=? WHERE id=?", ((text + old)[:400], now, r["id"]))
        if said == "done":
            close(j, num, f"You checked it and closed it in the app ({when}).", done=True, by=f"{by}, in the app", quiet=True)
            out["words"] = "Saved: done. It is off the open list, and your answer is kept."
        elif said == "drop":
            close(j, num, f"You dropped it in the app ({when}). Ananta does no more work on it.", done=False, by=f"{by}, in the app", quiet=True)
            out["words"] = "Saved: dropped. It is off the open list, and your answer is kept."
        elif said == "pause":
            set_kind(j, num, "PARKED")
            _note(f"You paused it in the app ({when}). Nothing happens until you bring it back.")
            out["words"] = "Saved: paused. It is under Parked until you bring it back."
        elif said == "bring_back":
            set_kind(j, num, "WORK")
            _note(f"You brought it back in the app ({when}).")
            out["words"] = "Saved: it is work to do again."
        elif said in ("first", "check", "reopen"):
            set_kind(j, num, "WORK")
            j.db.execute("UPDATE owner_requests SET due=NULL WHERE id=?", (r["id"],))
            if said == "reopen":
                j.db.execute("UPDATE owner_requests SET status='OPEN' WHERE id=?", (r["id"],))
            _note({"first": f"Do this first: you asked for it in the app ({when}).",
                   "check": f"Do this first: you asked for an earlier look in the app ({when}).",
                   "reopen": f"Do this first: not right, you reopened it in the app ({when})."}[said])
            out["words"] = {"first": "Saved: it is at the top of the work list.", "check": "Saved: it is at the top of the work list now.",
                            "reopen": "Saved: it is back at the top of the work list, marked not right."}[said]
        else:
            import datetime as dt
            from zoneinfo import ZoneInfo
            d = _postpone_to(due or "tomorrow", dt.datetime.fromtimestamp(now, ZoneInfo("America/Toronto")).date())
            dd = dt.date.fromisoformat(d)
            set_kind(j, num, "DATE", due=d)
            note = f"You postponed it to {dd:%a} {dd.day} {dd:%b} in the app ({when})" + (" | " + r["note"] if r.get("note") else "")
            j.db.execute("UPDATE owner_requests SET note=?, updated_t=? WHERE id=?", (note[:400], now, r["id"]))
            out["words"] = f"Saved: postponed to {dd:%a} {dd.day} {dd:%b}. It stays on the open list and is due again that day."
            out["due"] = d
    elif kind == "draft" and said in ("yes", "no"):
        from jarvis.india import views as india_views

        try:
            india_views.decide_draft(ref, "APPROVED" if said == "yes" else "SKIPPED", "Madhav (owner)", "in the app, from the Needs-you sheet")
        except KeyError as exc:
            raise ValueError("that draft is already answered") from exc
        out["words"] = ("Saved: yes. Ananta will write the study down and test it on past years. Nothing trades from it." if said == "yes"
                        else "Saved: skipped. It is closed and will not be raised again.")
    elif kind == "needs" and said == "yes":
        from jarvis.service import needs

        out["result"] = needs.decide(j, ref, "approve", by)
        out["words"] = "Saved: you said yes."
    else:
        raise ValueError("this one is answered in its own place: tell Ananta, or open it")
    if not keep_quiet:
        j.db.execute("DELETE FROM notice_quiet WHERE key=? AND ?<>'later'", (key, said))
    j.db.execute("INSERT INTO owner_answers VALUES (?,?,?,?,?)", (now, key, said, by, out["words"]))
    j.db.commit()
    return out


def clear_all(j, by: str = "Madhav", now: float | None = None) -> dict:
    """Everything waiting for his yes, cleared from his notifications for QUIET_DAYS; it all stays on the open list."""
    from jarvis.service import waiting

    keys = [x["id"] for x in waiting.collect(j, now)["items"]]
    for k in keys:
        answer(j, k, "later", by=by, now=now)
    n = len(keys)
    return {"cleared": n, "words": (f"Cleared {n} from your notifications for {QUIET_DAYS} days. {'It stays' if n == 1 else 'They stay'} on your open list."
                                    if n else "Nothing to clear.")}


def set_kind(j, num: int, waits: str, due: str | None = None, topic: str | None = None, seen: int | None = None, advice: str | None = None,
             line: str | None = None, touch: bool = False) -> dict:
    """line: the item in one plain sentence. touch: it was looked at and kept today (rule 7: the 14 days start again)."""
    if waits not in KINDS:
        raise ValueError(f"kind is one of {KINDS}")
    r = _get(j, num)
    if not r:
        raise ValueError(f"no item {num}")
    j.db.execute("UPDATE owner_requests SET waits=?, due=COALESCE(?, due), topic=COALESCE(?, topic), seen=COALESCE(?, seen) WHERE id=?",
                 (waits, due, topic, seen, r["id"]))
    if advice:
        j.db.execute("UPDATE owner_requests SET note=? WHERE id=?", (("Advice: " + advice)[:400], r["id"]))
    if line:
        j.db.execute("UPDATE owner_requests SET line=? WHERE id=?", (whole_clip(line, 300), r["id"]))
    if touch:
        j.db.execute("UPDATE owner_requests SET updated_t=? WHERE id=?", (int(j.now()), r["id"]))
    j.db.commit()
    return _get(j, num)


# ---------------------------------------------------------------- the list checks itself
def problems(j, board: list[dict] | None = None) -> list[str]:
    """What is wrong with the list itself, in plain words (empty when it is in order)."""
    from jarvis.service import requests_log

    out = []
    now = time.time()
    board = board if board is not None else _board(j, now)
    try:
        for num, state, status in j.db.execute("SELECT f.num, f.state, r.status FROM fix_flow f JOIN owner_requests r ON r.num=f.num "
                                               "WHERE r.status IN ('DONE','WONT') AND f.state NOT IN ('deployed','cancelled','noted')").fetchall():
            out.append(f"{requests_log.label(num)} is closed but its fix flow still says '{state}'")
    except Exception:  # noqa: BLE001
        pass
    for x in board:
        if x.get("overdue"):
            out.append(f"{x['id']} was due on {x['due']} and is still open")
        if x.get("stale"):
            out.append(f"{x['id']} has not moved in {STALE_DAYS} days: keep, park or drop it")
    try:
        have = {r[0] for r in j.db.execute("SELECT num FROM owner_requests")}
        for ln in CHANGES.read_text().splitlines():
            if '"closes"' in ln:
                for e in json.loads(ln).get("closes") or []:
                    n = int(e["num"] if isinstance(e, dict) else e)
                    if n not in have:
                        out.append(f"the change book closes item {n}, which is not on the board")
    except Exception:  # noqa: BLE001
        pass
    return out


def text(j, now: float | None = None) -> str:
    """The list as plain lines, for the morning page and for a work session."""
    d = collect(j, now)
    L = [d["line"], f"(as of {d['as_of']})", ""]

    def block(title: str, rows: list[dict], cap: int = 40) -> None:
        L.append(f"## {title} ({len(rows)})")
        for x in rows[:cap]:
            bits = [f"due {x['due']}" if x.get("due") else "", f"seen {x['seen']} times" if x.get("seen") else "", "STALE" if x.get("stale") else "",
                    "OVERDUE" if x.get("overdue") else "", x.get("state") or ""]
            tail = "; ".join(b for b in bits if b)
            L.append(f"- {x['id']} [{x.get('market')}] {x['line']}" + (f" ({tail})" if tail else "") + (f" Advice: {x['advice']}" if x.get("advice") else ""))
        if len(rows) > cap:
            L.append(f"- … and {len(rows) - cap} more")
        if not rows:
            L.append("- nothing")
        L.append("")

    block("Needs your yes", d["you"])
    block("Work to do", d["work"])
    block("Waiting for a date or for evidence", d["dated"])
    block("Parked on purpose", d["parked"], cap=12)
    if d["problems"]:
        L.append("## The list's own problems")
        L += [f"- {p}" for p in d["problems"]]
    return "\n".join(L)
