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

  collect(j)        the list
  short(j)          a few lines of it for every turn of a conversation
  close(j, ...)     close an item on the board and in the fix flow (the only way to close)
  apply_closes(j)   the change book's `closes` applied (the 15-minute loop)
  open_item(j, ...) put a new hand-kept item on the board with its kind
  set_kind(j, ...)  set an item's kind, date or topic
  problems(j)       what is wrong with the list itself
  text(j)           the list as plain lines (python scripts/open_list.py)
Read-only except close / apply_closes / open_item / set_kind. Nothing here trades or changes a rule."""
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
    you = [{"id": low(x.get("title") or x["id"]), "kind": "YOU", "market": x.get("market") or "crypto", "line": plain(x.get("line") or x.get("title") or "", 190),
            "count": int(x.get("count") or 1), "source": {"drafts": "India research drafts", "needs": "crypto Needs you"}.get(x.get("kind"), "board"),
            **({"advice": (x.get("review") or {}).get("proposal")} if (x.get("review") or {}).get("proposal") else {})} for x in w["items"]]
    work = [x for x in board if x["kind"] == "WORK"]
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
            "kinds": KIND_WORDS,
            "how": ("This is the only place that says what is open. Say an item by its name ('flag 53', 'CHECKPOINT-30'). Something not on this "
                    "list is not open: it is done, dropped or was never filed. A dated note or the morning page is history, not the list.")}


def short(j, market: str | None = None, now: float | None = None) -> dict:
    """A few lines for every turn: the count line, what needs his yes, this market's work, the next dates."""
    d = collect(j, now)
    mine = lambda x: not market or x.get("market") in (market, "both")                   # noqa: E731
    return {"line": d["line"], "as_of": d["as_of"],
            "needs_your_yes": [{k: x.get(k) for k in ("id", "market", "line", "advice") if x.get(k)} for x in d["you"]][:8],
            "work_to_do": [{k: x.get(k) for k in ("id", "line", "seen", "stale") if x.get(k)} for x in d["work"] if mine(x)][:8],
            "next_dates": [{k: x.get(k) for k in ("id", "due", "line") if x.get(k)} for x in d["dated"] if mine(x) and x.get("due")][:5],
            "parked": d["counts"]["PARKED"], "how": d["how"]}


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
              by: str = "claude") -> dict:
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
    return r


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
        j.db.execute("UPDATE owner_requests SET line=? WHERE id=?", (line[:300], r["id"]))
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
