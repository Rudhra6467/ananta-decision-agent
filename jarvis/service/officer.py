"""The officer's note (Madhav, Oct 13): the brain's job is to watch the account and tell him what happened, not to pick trades.

Once a day, after the daily close and the $500 book's step, the code gathers the facts (the book, the dial, the brakes, the day's
fills, what the measuring books did in the background, what passed or was pushed) and the model writes 4-6 plain sentences for
Madhav: what the account did and why, what the engine recorded behind it, and what, if anything, needs him. One Sonnet call
(about 2 cents). Saved in officer_notes, pushed to the phone, shown on Home and in Ask (tool officer_note).

  facts(j, daily)     the day's facts, from code only
  write(j, daily)     facts -> the note -> saved and pushed; returns {"ok", "note", "facts"}
  latest(j, n)        the last notes
"""
from __future__ import annotations

import json
import time
from typing import Callable

NOTE_RULES = """You are Ananta, the trading assistant of one owner, Madhav. Write the day's officer's note about HIS account: the $500 NDAX
paper book. You are its risk officer and narrator, not a trader: the rules decide the trades; you explain and watch.
Write 4 to 6 short sentences in plain everyday English, first person, to "sir" once at most. Numbers rounded, at most two a sentence.
Order: (1) what the account did today and why (the dial, the sleeves, the brakes); (2) what the engine recorded in the background
(signals, measuring books, anything that passed or was pushed), in one or two sentences, without listing every book; (3) the checks:
the facts carry "checks" (idle cash, a core without an exit, a bleeding book, an explorer eaten by costs) and "layer_conflicts"; name every
FAIL and every conflict plainly in one sentence each, with its number, and say what the rule does about it ("the stance wins", "trimmed to
target"); if all pass, one short sentence says so; then what needs him, or "nothing needs you". Never write "nothing changed" when a check
fails. A check with state OK is not a failure, however high the cash is: when buying is off and no rule may trade, cash is what the rules want.
(4) the evidence window: do NOT close every note with its day; say it only when the learning loop did not run clean, or in the window's
last seven days. Never invent a number: every figure must come from the facts. No headings, no bullet points, no
greeting by time of day. If the facts say a brake fired or a strategy passed, lead with that. What fired at this close is
"account.brakes_today"; mention the brakes ONLY when it says one fired, and never write that no brake fired;
the "fired" numbers inside "brakes" are totals since the book started, never today's. If "account.corrections" is there, say the
correction once in plain words (what was put right and the money). If "dial.warning" is there, say it. If "background.old_paper_trades_closed_late_tonight" is there, say in one sentence
how many old paper trades of the measuring books were closed late tonight by their own rules, their net in US dollars, and that the
account itself is untouched. A "caught" move only means
some paper book held that coin, often a measuring book that may not trade for the account: say "a measuring book was in X", never
"caught" as if it were a win. In a check's words, the books after "Paused books still closing"
are different books from the ones before: never call a live book paused. A check with state DECIDED is one Madhav has already decided: say his decision, not a failure."""


def _table(j) -> None:
    j.db.execute("CREATE TABLE IF NOT EXISTS officer_notes (day TEXT PRIMARY KEY, t INTEGER, note TEXT, facts TEXT, cost_usd REAL)")


def facts(j, daily: dict | None = None) -> dict:
    from jarvis.service import exposure, ndax_book, strategy_status

    daily = daily or {}
    f: dict = {"day": time.strftime("%Y-%m-%d", time.gmtime(j.now())),
               "note_on_units": "Every figure under 'account' is in CANADIAN dollars (CAD): the book trades on NDAX in CAD, so Bitcoin near "
                                "C$118,000 is about US$83,000. Market prices elsewhere are US dollars. Never call a CAD price stale or wrong."}
    try:
        s = ndax_book.status(j)
        f["account"] = {"value_cad": s.get("value_cad"), "cash_cad": s.get("cash_cad"), "return_pct": s.get("return_pct"),
                        "positions": {c: {"sleeve": p.get("sleeve"), "paid_cad": round(p.get("paid", 0), 2), "last_price_cad": p.get("last"), "rule": p.get("rule")} for c, p in (s.get("positions") or {}).items()},
                        "brakes": s.get("brakes"), "last_step": s.get("last_step"), "started": s.get("started"),
                        "closed_recent": (s.get("closed") or [])[-3:]}
        # 25 Oct: the note said "the day-loss brake fired once today" when it had fired on 22 Oct ("fired" counts are totals since the start).
        # Say in words what fired today and when each brake last fired.
        # 10 Nov 2026 (the outsider's review): a brake's day is the candle it fired on, and the note is written on the UTC day after that
        # candle, so "today" never matched and the note said "no brake fired today" on the night two fired (29 Oct).
        log = (s.get("brakes") or {}).get("log") or []
        candle = _candle_day(j, f["day"])
        today = [x for x in log if x.get("day") == candle]
        last = {}
        for x in log:
            last[x.get("brake")] = x
        f["account"]["brakes_today"] = ("; ".join(f"the {x.get('brake', '').replace('_', '-')} brake fired at this close (no new buys until {x.get('until')})" for x in today)
                                        or "none fired at this close" + ("; last fired: " + ", ".join(f"{b.replace('_', '-')} on {x.get('day')} (blocked until {x.get('until')})" for b, x in last.items()) if last else ""))
        fixes = [r for r in ((ndax_book._get(j, "state") or {}).get("repairs") or []) if str(r.get("day") or "") >= time.strftime("%Y-%m-%d", time.gmtime(j.now() - 86400))]
        if fixes:                                             # a correction to the book is said once, in the note after it
            f["account"]["corrections"] = [{k: r.get(k) for k in ("day", "what", "cash_added")} for r in fixes]
    except Exception as exc:  # noqa: BLE001
        f["account_error"] = str(exc)[:120]
    try:
        # 10 Nov 2026 (the outsider's review): exposure.state keeps its answer for ten minutes, and one asked just before the close was
        # still in hand at 00:05, so the note read the dial from the candle before the one the book had just stepped on (every night;
        # on 26 Oct the note said open while the book sold for "dial closed"). The note asks afresh, and says which candle it read.
        exposure._CACHE.update(t=0, v=None)
        d = exposure.state(j)
        f["dial"] = {"state": d.get("dial_words"), "why": d.get("why"), "candle": d.get("as_of_day"), "book_stepped_on": _candle_day(j, f["day"])}
        if f["dial"]["candle"] != f["dial"]["book_stepped_on"]:
            f["dial"]["warning"] = "the dial was read from a different candle than the book stepped on: say so plainly"
    except Exception as exc:  # noqa: BLE001
        f["dial_error"] = str(exc)[:120]
    b5 = daily.get("book500") or {}
    f["today_in_the_account"] = {k: b5.get(k) for k in ("bought", "sold", "skipped") if b5.get(k)} or "no change"
    # the background, counted from the database itself (never trusted from the caller): today's signals per rule and tier,
    # the brain's decisions today, and what each measuring book closed today
    day0 = int(j.now()) - int(j.now()) % 86400
    bg: dict = {"signals_today_by_rule": {}, "closed_today_by_rule": {}, "brain_today": {}}
    try:
        for watch, n in j.db.execute("SELECT watch, COUNT(*) FROM evidence_trades WHERE signal_t >= ? GROUP BY watch", (day0,)):
            if not watch.startswith(("RANDOM", "JARVIS_RANDOM")):
                bg["signals_today_by_rule"][watch] = n
        for watch, n, net in j.db.execute("SELECT watch, COUNT(*), ROUND(SUM(net_usd), 2) FROM evidence_trades WHERE status='CLOSED' AND exit_t >= ? GROUP BY watch", (day0,)):
            bg["closed_today_by_rule"][watch] = {"n": n, "net_usd": net}
        for action, n in j.db.execute("SELECT action, COUNT(*) FROM brain_decisions WHERE t >= ? GROUP BY action", (day0,)):
            bg["brain_today"][action] = n
        bg["evidence_rows_open"] = j.db.execute("SELECT COUNT(*) FROM evidence_trades WHERE status IN ('OPEN','WAITING') AND watch NOT LIKE 'RANDOM%'").fetchone()[0]
    except Exception as exc:  # noqa: BLE001
        bg["error"] = str(exc)[:120]
    try:                                                  # 10 Nov 2026: paper trades closed tonight on a rule's day long past (a frozen row let go)
        row = j.db.execute("SELECT v FROM engine_state WHERE k=?", ("late_closes:" + f["day"],)).fetchone()
        if row:
            bg["old_paper_trades_closed_late_tonight"] = json.loads(row[0])
    except Exception:  # noqa: BLE001
        pass
    f["background"] = {**bg, "brain_woke": daily.get("brain_woke"), "pushed": daily.get("pushed") or [],
                       "missed_moves": (daily.get("missed") or [])[:5] if isinstance(daily.get("missed"), list) else daily.get("missed"),
                       "brain_rebuild": daily.get("brain_rebuild"), "weekly_review": daily.get("weekly_review")}
    try:
        st = strategy_status.load().get("strategies") or {}
        f["strategies"] = {k: v.get("status") for k, v in st.items()}
        f["pushed_rule"] = strategy_status.pushed_rule()
    except Exception:  # noqa: BLE001
        pass
    try:  # the 60-day evidence window (Madhav, Oct 14): the note says where the clock stands
        from jarvis.service import knowledge_build

        ew = knowledge_build.window(j)
        if ew:
            f["evidence_window"] = ew
    except Exception:  # noqa: BLE001
        pass
    try:  # discipline items 5 and 8 (Madhav, 24 Oct 2026): the officer's four checks and tonight's one plan line
        from jarvis.service import discipline

        pl = discipline.plan_line(j)
        f["checks"] = pl.get("checks") or discipline.officer_checks(j)
        f["plan_line"] = pl.get("line")
        f["layer_conflicts"] = pl.get("conflicts") or []
        f["wait_for_arrived"] = pl.get("arrived") or []
        f["core_plan"] = ((f.get("account") or {}) and (ndax_book._get(j, "state") or {}).get("core_plan")) or None
    except Exception as exc:  # noqa: BLE001
        f["checks_error"] = str(exc)[:120]
    return f


def _candle_day(j, note_day: str) -> str:
    """The daily candle the $500 book last stepped on (its UTC day); the day before the note's day when the book has no step yet."""
    from jarvis.service import ndax_book

    try:
        t = (ndax_book._get(j, "state") or {}).get("last_bar")
        if t:
            return time.strftime("%Y-%m-%d", time.gmtime(int(t)))
    except Exception:  # noqa: BLE001
        pass
    import calendar
    return time.strftime("%Y-%m-%d", time.gmtime(calendar.timegm(time.strptime(note_day, "%Y-%m-%d")) - 86400))


def _numbers(x) -> list[float]:
    if isinstance(x, bool):
        return []
    if isinstance(x, (int, float)):
        return [float(x)]
    if isinstance(x, dict):
        return [n for v in x.values() for n in _numbers(v)]
    if isinstance(x, (list, tuple)):
        return [n for v in x for n in _numbers(v)]
    return []


def cad_labels(note: str, f: dict) -> str:
    """Oct 15 (audit OFFICER): an account figure written as "$498" becomes "C$498" by code, not by the prompt alone (the Oct 14
    note said "$498" for a CAD value). Only a figure that matches one of the account's CAD numbers (within 0.5%) is relabelled,
    and never when it also matches another number in the facts (a coin's US-dollar price can sit near the account's value);
    "US$" and "C$" are left alone."""
    import re

    cad = [n for n in _numbers(f.get("account") or {}) if n >= 1]
    other = [n for k, v in f.items() if k != "account" for n in _numbers(v) if n >= 1]

    def fix(m):
        x = float(m.group(2).replace(",", ""))
        near = lambda xs: any(abs(x - c) <= max(0.5, 0.005 * c) for c in xs)  # noqa: E731
        return m.group(1) + "C$" + m.group(2) if near(cad) and not near(other) else m.group(0)

    return re.sub(r"(^|[^A-Za-z$])\$(\d[\d,]*(?:\.\d+)?)", fix, note)


def mark_clean_night(j, f: dict) -> dict:
    """A clean night: the book stepped on tonight's candle, the note read the dial from the same candle, and the book check is silent.
    Kept in engine_state as clean_night:<day>; the Proof screen counts the nights in a row."""
    from pathlib import Path

    from jarvis import selfcheck

    dial = f.get("dial") or {}
    why = []
    if not dial.get("candle") or dial.get("candle") != dial.get("book_stepped_on"):
        why.append(f"the note read the dial at {dial.get('candle')}, the book stepped on {dial.get('book_stepped_on')}")
    try:
        db = [r[2] for r in j.db.execute("PRAGMA database_list").fetchall() if r[1] == "main"][0]
        found = selfcheck._book500(Path(db)) if db else []
    except Exception as exc:  # noqa: BLE001
        found = [{"what": f"the book check could not run: {str(exc)[:80]}"}]
    why += [str(x.get("what"))[:160] for x in found]
    out = {"clean": not why, "why": why}
    j.db.execute("INSERT OR REPLACE INTO engine_state VALUES (?,?)", ("clean_night:" + str(f["day"]), json.dumps(out)))
    j.db.commit()
    return out


def clean_nights(j) -> dict:
    """Clean nights in a row up to the latest marked night, from the scorecard's freeze day."""
    from pathlib import Path

    p = Path(__file__).resolve().parents[2] / "docs" / "knowledge" / "crypto_scorecard.json"
    try:
        card = json.loads(p.read_text())
    except (OSError, ValueError):
        return {}
    start = str(card.get("freeze_from") or "")
    rows = j.db.execute("SELECT k, v FROM engine_state WHERE k LIKE 'clean_night:%' AND k >= ? ORDER BY k DESC", ("clean_night:" + start,)).fetchall()
    run, broke = 0, None
    for k, v in rows:
        d = json.loads(v)
        if not d.get("clean"):
            broke = {"day": k.split(":", 1)[1], "why": d.get("why")}
            break
        run += 1
    return {"in_a_row": run, "need": int(card.get("clean_nights_needed") or 30), "since": start, "nights_marked": len(rows), "last_break": broke}


def write(j, daily: dict | None = None, push: Callable | None = None, call: Callable | None = None) -> dict:
    from jarvis.service import brain

    _table(j)
    f = facts(j, daily)
    day = f["day"]
    if j.db.execute("SELECT 1 FROM officer_notes WHERE day=?", (day,)).fetchone():
        return {"ok": True, "note": latest(j, 1)[0]["note"], "facts": f, "already": True}
    user = "FACTS (JSON):\n" + json.dumps(f, ensure_ascii=False, default=str)[:12000] + "\n\nWrite the officer's note."
    try:
        text, usage = (call or brain._call_claude)(NOTE_RULES, user)
        cost = brain._price(usage)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)[:200], "facts": f}
    note = cad_labels(" ".join(text.strip().split()), f)
    if not note:
        return {"ok": False, "error": "empty note", "facts": f}
    j.db.execute("INSERT OR REPLACE INTO officer_notes VALUES (?,?,?,?,?)", (day, int(j.now()), note, json.dumps(f, default=str)[:20000], cost))
    j.db.commit()
    try:  # 10 Nov 2026: the scorecard's clean nights (docs/knowledge/crypto_scorecard.json)
        f["clean_night"] = mark_clean_night(j, f)
    except Exception:  # noqa: BLE001
        pass
    try:  # discipline item 8: a failed check is filed on the repair board, once a week per check
        from jarvis.service import discipline

        f["checks_filed"] = discipline.file_failed_checks(j, f.get("checks") or [])
    except Exception:  # noqa: BLE001
        pass
    if push:
        try:
            push("Ananta's note", note[:220])
        except Exception:  # noqa: BLE001
            pass
    return {"ok": True, "note": note, "facts": f, "cost_usd": cost}


def latest(j, n: int = 3) -> list[dict]:
    _table(j)
    return [{"day": d, "t": t, "note": note, "cost_usd": c} for d, t, note, c in
            j.db.execute("SELECT day, t, note, cost_usd FROM officer_notes ORDER BY day DESC LIMIT ?", (n,)).fetchall()]
