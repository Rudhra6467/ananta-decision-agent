"""The officer's note (Madhav, Oct 13): the brain's job is to watch the account and tell him what happened, not to pick trades.

Once a day, after the daily close and the $500 book's step, the code gathers the facts (the book, the dial, the brakes, the day's
fills, what the measuring books did in the background, what passed or was pushed) and the model writes 4-6 plain sentences for
Madhav: what the account did and why, what the engine recorded behind it, and what, if anything, needs him. One Sonnet call
(about 2 cents). Saved in officer_notes, pushed to the phone, shown on Home and in Ask (tool officer_note).

  facts(j, daily)     the day's facts, from code only
  write(j, daily)     facts -> the note -> saved and pushed; returns {"ok", "note", "facts"}
  write_when_due(j)   12 Nov 2026 (audit repair 3): the note is written once the night's last decision is in (see below)
  latest(j, n)        the last notes, each with the Toronto evening it belongs to and any later correction in its own words

12 Nov 2026, audit repair 3 (the keen outside audit's G-24 to G-28, G-35 to G-38, G-63). The night is counted from the open of the daily
candle the book stepped on, not from midnight UTC six minutes before the note (G-25). The note waits for the night's last decision: the
daily step stashes what the note needs, and the 15-minute loop writes it after the bold measuring book's own step, once no new moment
waits for the brain (G-26). A note is named by the Toronto evening it was written on (G-28). A stored note whose figure the book's own
records later corrected carries the correction in its own words wherever it is shown (G-24, G-36, G-37, G-38). The phone gets whole
sentences, and the body sent is kept (G-63).
"""
from __future__ import annotations

import datetime as _dt
import json
import re
import time
from typing import Callable
from zoneinfo import ZoneInfo

TOR = ZoneInfo("America/Toronto")
PHONE_CHARS = 220
NOTE_WAITS_S = 45 * 60          # the note waits at most this long after the close for the brain's moments of the night
NOTE_TRIES = 3                  # a note that fails is tried this many times a night, then the night test runs without it
# Until this moment the note counts the measuring books' closes and never sums their money: eight crypto findings (breakouts and the bold
# book among them) are pre-registered for a forward test that ends 14 Dec (the audit's rule 9). The same moment as shadow.SEALED_UNTIL
# and learning.SEALED_UNTIL_T (tests/test_nightly_note_12nov.py keeps the three equal).
HELD_UNTIL = int(_dt.datetime(2026, 12, 15, tzinfo=_dt.timezone.utc).timestamp())

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
the "fired" numbers inside "brakes" are totals since the book started, never today's, and count fires on real losses only: a log entry
marked "false_fall" came from a value read too low and is never a real fire. "background" counts the night as "counted_from" says (the
rules' signals and closes of the candle that just closed, and what the brain and the bold book did since the last note); if
"background.still_waiting_when_written" is there, say in one short sentence what had not happened yet when you
wrote (never that it will come). If "account.corrections" is there, say the
correction once in plain words (what was put right and the money). If "dial.warning" is there, say it. If "background.old_paper_trades_closed_late_tonight" is there, say in one sentence
how many old paper trades of the measuring books were closed late tonight by their own rules, their net in US dollars only when the facts
give it (before 15 Dec they never do), and that the account itself is untouched. Before 15 Dec the night's closes are counts only, and the
results of breakouts and the bold book are never in the facts: never guess or add one. "background.missed_moves" lists the day's big moves by coin, each with what happened in plain words; a
coin's code is a coin, never a word ("ERA" is a coin): write "a measuring book held the coin ERA on paper", never "a measuring book was in
ERA" and never "caught" as if it were a win (11 Nov note). Mention them in one short sentence at most, and only if one touches the account. In a check's words, the books after "Paused books still closing"
are different books from the ones before: never call a live book paused. A check with state DECIDED is one Madhav has already decided: say his decision, not a failure."""


MOVE_WORDS = {"CAUGHT": "a measuring book held the coin on paper (not the account)", "SEEN": "seen; no book held the coin",
              "MISSED": "no book saw the move in time"}


def _moves_in_words(missed) -> list | None:
    """The day's big moves for the note, coin by coin in plain words: "ERA CAUGHT" became "a measuring book was in ERA" on 11 Nov."""
    if not isinstance(missed, list):
        return missed
    out = []
    for m in missed[:5]:
        coin, _, what = str(m).strip().partition(" ")
        out.append({"coin": coin, "what": MOVE_WORDS.get(what.strip().upper(), what.strip().lower() or "a big move")})
    return out


def _table(j) -> None:
    j.db.execute("CREATE TABLE IF NOT EXISTS officer_notes (day TEXT PRIMARY KEY, t INTEGER, note TEXT, facts TEXT, cost_usd REAL)")


def evening(t) -> str:
    """The Toronto day a nightly record belongs to ("Tue 10 Nov"): the note written at 00:05 UTC on 11 Nov is Tuesday evening's (G-28)."""
    try:
        d = _dt.datetime.fromtimestamp(int(t), TOR)
    except (TypeError, ValueError, OverflowError, OSError):
        return ""
    return f"{d:%a} {d.day} {d:%b}"


def night_window(j) -> tuple[int, int, int, int]:
    """The night the note counts (G-25), as (candle_open, candle_close, since, now). The measuring books stamp a rule's signal and exit with
    the daily candle's open (exactly 00:00 UTC); the brain and the bold book stamp the moment they act. A night counted from midnight UTC,
    six minutes before the note, was empty; counted from the candle's open to the note, it counted the step's own minutes again the next
    night (the outside check of 12 Nov: the bold book's 00:09 buy, 77 brain decisions since 14 Oct). So: the candle-stamped rows of the
    candle that has just closed (the one before the note's UTC day, whatever the book's step did), and the rows stamped at a moment after
    the last note and up to now."""
    now = int(j.now())
    close = now - now % 86400
    since = close - 86400
    try:
        # from the moment the last note COUNTED to (the confirm check: counted to its save time, the model call's minutes fell on no night)
        r = j.db.execute("SELECT t, facts FROM officer_notes WHERE day < ? ORDER BY day DESC LIMIT 1",
                         (time.strftime("%Y-%m-%d", time.gmtime(now)),)).fetchone()
        if r:
            try:
                upto = ((json.loads(r[1] or "{}") or {}).get("background") or {}).get("counted_to") if r[1] else None
            except ValueError:
                # the second confirm check (S5): facts saved cut at 20,000 characters do not parse, and the night then started at midnight
                # UTC; the moment is read from the text, else the note's save time
                m = re.search(r'"counted_to":\s*(\d+)\s*[,}]', r[1] or "")      # a whole number (the third confirm check): never one cut short
                upto = int(m.group(1)) if m else None
            last = int(upto) if isinstance(upto, (int, float)) else int(r[0] or 0)
            since = max(since, last)
    except Exception:  # noqa: BLE001  no notes table yet: the candle's own day
        pass
    return close - 86400, close, since, now


NIGHT_SQL = "((%(c)s %% 86400 = 0 AND %(c)s >= ? AND %(c)s < ?) OR (%(c)s %% 86400 != 0 AND %(c)s > ? AND %(c)s <= ?))"


def _night(col: str) -> str:
    """The WHERE part for a column stamped either at a candle's open or at the moment something acted (see night_window)."""
    return NIGHT_SQL % {"c": col}


def phone_text(note: str, limit: int = PHONE_CHARS) -> str:
    """The note for the phone: whole sentences up to the limit, never a cut word (G-63: '...an old ETH sale was recorded late, s')."""
    note = " ".join(str(note or "").split())
    if len(note) <= limit:
        return note
    ends = [m.end() for m in re.finditer(r"[.!?](?=\s|$)", note) if m.end() <= limit]     # 12 Nov check: one came out at 221
    if ends and ends[-1] > 20:
        return note[:ends[-1]]
    return note[:limit].rsplit(" ", 1)[0].rstrip(",;:") + "…"


def facts(j, daily: dict | None = None) -> dict:
    from jarvis.service import exposure, ndax_book, strategy_status

    daily = daily or {}
    f: dict = {"day": time.strftime("%Y-%m-%d", time.gmtime(j.now())),
               "note_on_units": "Every figure under 'account' is in CANADIAN dollars (CAD): the book trades on NDAX in CAD, so a coin's C$ price "
                                "is its US$ price times the day's exchange rate (about 1.4); never quote a C$ price from memory. Market prices "
                                "elsewhere are US dollars. Never call a CAD price stale or wrong."}   # 11 Nov: a fixed Bitcoin figure written here went stale
    try:
        s = ndax_book.status(j)
        f["account"] = {"value_cad": s.get("value_cad"), "cash_cad": s.get("cash_cad"), "return_pct": s.get("return_pct"),
                        "positions": {c: {"sleeve": p.get("sleeve"), "paid_cad": round(p.get("paid", 0), 2), "last_price_cad": p.get("last"), "rule": p.get("rule")} for c, p in (s.get("positions") or {}).items()},
                        "brakes": brake_record({**(s.get("brakes") or {}), "log": (s.get("brakes") or {}).get("log") or s.get("brake_log") or []},
                                               s.get("repairs")),
                        "last_step": s.get("last_step"), "started": s.get("started"),
                        "closed_recent": toronto_days(j, (s.get("closed") or [])[-3:]), "closed_days_note": CLOSED_DAYS_NOTE}
        # 25 Oct: the note said "the day-loss brake fired once today" when it had fired on 22 Oct ("fired" counts are totals since the start).
        # Say in words what fired today and when each brake last fired.
        # 10 Nov 2026 (the outsider's review): a brake's day is the candle it fired on, and the note is written on the UTC day after that
        # candle, so "today" never matched and the note said "no brake fired today" on the night two fired (29 Oct).
        log = [x for x in (f["account"]["brakes"].get("log") or []) if not x.get("false_fall")]   # 12 Nov (G-35): real fires only
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
    win = night_window(j)                          # 12 Nov (G-25): was midnight UTC, six minutes before the note
    held = int(j.now()) < HELD_UNTIL
    bg: dict = {"signals_today_by_rule": {}, "closed_today_by_rule": {}, "brain_today": {}, "counted_to": win[3],
                "counted_from": (f"the rules' signals and closes of the {time.strftime('%Y-%m-%d', time.gmtime(win[0]))} candle, and what the "
                                 f"brain and the bold book did after {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime(win[2]))} (the last note)")}
    if held:
        bg["closed_counts_only"] = ("the measuring books' closes are counted, never summed in money, before 15 Dec: eight findings are under "
                                    "a pre-registered forward test to 14 Dec (breakouts and the bold book among them)")
    try:
        for watch, n in j.db.execute(f"SELECT watch, COUNT(*) FROM evidence_trades WHERE {_night('signal_t')} GROUP BY watch", win):
            if not watch.startswith(("RANDOM", "JARVIS_RANDOM")):
                bg["signals_today_by_rule"][watch] = n
        # 12 Nov 2026 (audit repair 3): counted by the night, the closes are now found every night; until 15 Dec their money is left
        # out, since a breakout's or the bold book's result would be an early look (the audit's rule 9). Counting is fine.
        for watch, n, net in j.db.execute(f"SELECT watch, COUNT(*), ROUND(SUM(net_usd), 2) FROM evidence_trades WHERE status='CLOSED' AND "
                                          f"{_night('exit_t')} GROUP BY watch", win):
            bg["closed_today_by_rule"][watch] = {"n": n} if held else {"n": n, "net_usd": net}
        for action, n in j.db.execute("SELECT action, COUNT(*) FROM brain_decisions WHERE t > ? AND t <= ? GROUP BY action", win[2:]):
            bg["brain_today"][action] = n
        bg["evidence_rows_open"] = j.db.execute("SELECT COUNT(*) FROM evidence_trades WHERE status IN ('OPEN','WAITING') AND watch NOT LIKE 'RANDOM%'").fetchone()[0]
    except Exception as exc:  # noqa: BLE001
        bg["error"] = str(exc)[:120]
    try:                                                  # 10 Nov 2026: paper trades closed tonight on a rule's day long past (a frozen row let go)
        row = j.db.execute("SELECT v FROM engine_state WHERE k=?", ("late_closes:" + f["day"],)).fetchone()
        if row:
            late = json.loads(row[0])
            if held and isinstance(late, dict) and "net_usd" in late:       # 12 Nov 2026: their total holds breakout results (rule 9)
                late.pop("net_usd")
                late["money"] = "not given before 15 Dec: the total would hold results of the findings held for the forward test"
            bg["old_paper_trades_closed_late_tonight"] = late
    except Exception:  # noqa: BLE001
        pass
    if daily.get("still_waiting_when_written"):          # 12 Nov (G-26): say what was still to come when the note was written
        bg["still_waiting_when_written"] = daily["still_waiting_when_written"]
    f["background"] = {**bg, "brain_woke": daily.get("brain_woke"), "pushed": daily.get("pushed") or [],
                       "missed_moves": _moves_in_words(daily.get("missed")),
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
        f["_plan"] = pl                       # the whole plan: write() saves it beside the note (11 Nov 2026, R-182), and pops it first
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
    plan = f.pop("_plan", None)
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
    try:  # 11 Nov 2026 (R-182): the plan this note was written from is saved with it, and only here; pages and questions only read it
        from jarvis.service import discipline

        f["plan_saved"] = discipline.save_plan(j, plan)
    except Exception:  # noqa: BLE001
        pass
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
        body = phone_text(note)
        try:
            sent = push("Ananta's note", body)
        except Exception as exc:  # noqa: BLE001
            sent = f"failed: {str(exc)[:80]}"
        try:                                              # 12 Nov (G-63): the log kept no body; now the body sent is kept with the note's day
            j.db.execute("INSERT OR REPLACE INTO engine_state VALUES (?,?)", ("officer_push:" + day, json.dumps(
                {"t": int(j.now()), "title": "Ananta's note", "body": body, "result": str(sent)[:80] if sent is not None else None})))
            j.db.commit()
        except Exception:  # noqa: BLE001
            pass
    return {"ok": True, "note": note, "facts": f, "cost_usd": cost}


# 12 Nov 2026 (audit repair 3, G-35): brake fires that the book's own repair notes say came from a false fall, not a real loss (10 Nov:
# "the day-loss and week-loss brakes of 28 Oct fired on that false fall, not on a real loss"). The book's state keeps its record; every
# report marks them and counts them apart.
BRAKE_WORDS = {"day-loss": "day_loss", "week-loss": "week_loss", "losing-streak": "losing_streak", "fall-from-peak": "fall_from_peak"}
MONTH = {m: i for i, m in enumerate(("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"), 1)}


def false_brakes(repairs: list | None) -> dict:
    """(day, brake) -> the repair's day, for each brake fire a repair note of the book names as caused by a false fall."""
    out: dict = {}
    for r in repairs or []:
        what, day = str((r or {}).get("what") or ""), str((r or {}).get("day") or "")
        if "false fall" not in what or not re.fullmatch(r"20\d\d-\d\d-\d\d", day[:10]):
            continue
        brakes = [v for k, v in BRAKE_WORDS.items() if k in what]
        for d, mon in re.findall(r"\bbrakes? of (\d{1,2}) (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b", what):
            when = _dt.date(int(day[:4]), MONTH[mon], int(d))
            if when > _dt.date.fromisoformat(day[:10]):
                when = when.replace(year=when.year - 1)
            for b in brakes:
                out[(when.isoformat(), b)] = day[:10]
    return out


def brake_record(brakes: dict | None, repairs: list | None = None) -> dict:
    """The brakes as reported: each log entry a false fall caused is marked, and the fires are counted on real losses only (the totals
    as the book recorded them stay beside them, as "fired_as_recorded")."""
    b = dict(brakes or {})
    false = false_brakes(repairs)
    log = [dict(x) for x in (b.get("log") or [])]
    for x in log:
        fixed = false.get((str(x.get("day")), str(x.get("brake"))))
        if fixed:
            x["false_fall"] = f"fired on a value that read too low, not on a real loss (the book's repair note of {fixed})"
    if "log" in b:
        b["log"] = log
    fired = b.get("fired")
    if isinstance(fired, dict) and any(x.get("false_fall") for x in log):
        real = dict(fired)
        for x in log:
            if x.get("false_fall") and isinstance(real.get(x.get("brake")), int):
                real[x["brake"]] = max(0, real[x["brake"]] - 1)
        b["fired"], b["fired_as_recorded"] = real, fired
    return b


def book_status(j) -> dict:
    """The $500 book's status as every reader reports it (the Ask, the app's /v3/book500, the books list, the summary's mission):
    ndax_book.status with its brake record as brake_record reports it. 12 Nov 2026 (audit repair 3, G-35): the two fires of 28 Oct that
    the book's own repair note says a false fall caused are marked and not counted; the book's state keeps its own record."""
    from jarvis.service import ndax_book

    st = dict(ndax_book.status(j))
    if st.get("brakes") is None and not st.get("brake_log"):
        return st                                         # the book has not started: nothing to report
    br = brake_record({**(st.get("brakes") or {}), "log": st.get("brake_log") or []}, st.get("repairs"))
    st["brake_log"] = br.pop("log", [])
    st["brakes"] = br
    st["closed"] = toronto_days(j, st.get("closed") or [])
    st["closed_days_note"] = CLOSED_DAYS_NOTE
    return st


CLOSED_DAYS_NOTE = ("A closed trade's 'in' and 'out' are the book's UTC days (its step runs at the 00:00 UTC close, the evening before in "
                    "Toronto); say its days as 'bought' and 'sold', Madhav's Toronto days, as every screen does")


def toronto_days(j, closed: list[dict]) -> list[dict]:
    """Each closed trade with the Toronto days of its buy and its sale ('bought', 'sold': 'Mon 26 Oct'), the screens' own rule
    (places._sold_day). 12 Nov 2026 (the second confirm check, a sibling of G-28): the Ask's book tool and the note's facts gave only the
    book's UTC days, unlabelled (the Solana trade 'in 2026-10-27, out 2026-11-06', which the screens show as Mon 26 Oct to Thu 5 Nov)."""
    try:
        from jarvis.service import places

        fills = places._fills(j)
        words = lambda d: _dt.date.fromisoformat(d[:10]).strftime("%a %-d %b") if re.match(r"\d{4}-\d\d-\d\d", str(d or "")) else d  # noqa: E731
        return [dict(c, bought=words(places._sold_day(c, fills, "BUY")), sold=words(places._sold_day(c, fills))) for c in closed]
    except Exception:  # noqa: BLE001  the UTC days stay, with the note that says what they are
        return [dict(c) for c in closed]


NOTE_DAILY_KEYS = ("book500", "brain_woke", "pushed", "missed", "brain_rebuild", "weekly_review", "steps_failed")


def _state_table(j) -> None:
    j.db.execute("CREATE TABLE IF NOT EXISTS engine_state (k TEXT PRIMARY KEY, v TEXT)")


def night_ready(j, daily: dict) -> dict:
    """Called by the nightly step (universe_watch.run_daily) instead of writing the note there (G-26): it keeps what the note needs from
    the night's steps; write_when_due writes the note once the night's last decision is in."""
    _state_table(j)
    day = time.strftime("%Y-%m-%d", time.gmtime(j.now()))
    keep = {k: daily.get(k) for k in NOTE_DAILY_KEYS if daily.get(k) is not None}
    j.db.execute("INSERT OR REPLACE INTO engine_state VALUES (?,?)", ("officer_daily:" + day, json.dumps({"t": int(j.now()), **keep}, default=str)))
    j.db.commit()
    return {"ready": day}


def waiting_for(j, day: str, since: int) -> list[str]:
    """What the night's note still waits for: the bold measuring book's decision of the night (when the book is on) and the moments the
    brain has not decided yet. 11 Nov: 3.5 minutes after the note, the bold book bought ZEC on paper and no screen or note said so."""
    out = []
    try:
        from jarvis.service import bold
        from jarvis.service import trade_guard as tg

        # a bold book held by the kill switch decides nothing tonight: nothing to wait for, and nothing "still to come" (12 Nov check)
        if bold.enabled()[0] and not tg.blocked(j, bold.WATCH):
            bold._table(j)
            if not j.db.execute("SELECT 1 FROM bold_decisions WHERE day=?", (day,)).fetchone():
                out.append("the bold measuring book had not decided yet")     # a fact at the time of writing, not a promise (confirm check)
    except Exception:  # noqa: BLE001
        pass
    try:                                              # a moment the brain is deciding right now waits too (12 Nov check)
        n = j.db.execute("SELECT COUNT(*) FROM brain_queue WHERE state IN ('NEW', 'DECIDING') AND t >= ?", (int(since),)).fetchone()[0]
        if n:
            out.append(f"{n} moment{'s' if n != 1 else ''} the brain had not decided yet")
    except Exception:  # noqa: BLE001  no queue table yet: nothing waits
        pass
    return out


def _night_test_once(j, day: str) -> dict:
    """The night test, started by this loop once a night whatever happened to the note. The second and third confirm checks of 12 Nov: a
    try cut short (the service stopping mid-try), or a stop just after the note was saved, left the night with no night test, and every
    later loop returned early. start_night_test keeps its own once-a-UTC-day stamp as well."""
    key = "officer_night_test:" + day
    if j.db.execute("SELECT 1 FROM engine_state WHERE k=?", (key,)).fetchone():
        return {}
    out: dict = {}
    try:
        from jarvis.service import universe_watch

        out["night_test_started"] = universe_watch.start_night_test(j)
    except Exception as exc:  # noqa: BLE001
        out["night_test_error"] = str(exc)[:120]
    j.db.execute("INSERT OR REPLACE INTO engine_state VALUES (?,?)", (key, str(int(j.now()))))
    j.db.commit()
    return out


def write_when_due(j, push: Callable | None = None, call: Callable | None = None) -> dict | None:
    """From the 15-minute loop, after the bold book's own step: the night's note once the nightly step has run and nothing of the night is
    still to be decided (or NOTE_WAITS_S after the step, whatever is still waiting, which the note then names). Then the night test."""
    _table(j)
    _state_table(j)
    day = time.strftime("%Y-%m-%d", time.gmtime(j.now()))
    if j.db.execute("SELECT 1 FROM officer_notes WHERE day=?", (day,)).fetchone():
        return _night_test_once(j, day) or None          # the note is there: the night test too (a stop just after the note left none)
    row = j.db.execute("SELECT v FROM engine_state WHERE k=?", ("officer_daily:" + day,)).fetchone()
    if not row:
        return None                                       # tonight's step has not run yet
    daily = json.loads(row[0] or "{}")
    stepped = int(daily.pop("t", 0) or 0)
    left = waiting_for(j, day, int(j.now()) - int(j.now()) % 86400)
    if left and int(j.now()) - stepped < NOTE_WAITS_S:
        return {"waiting": left}
    if left:
        daily["still_waiting_when_written"] = left
    tries = json.loads((j.db.execute("SELECT v FROM engine_state WHERE k=?", ("officer_tries:" + day,)).fetchone() or ["{}"])[0] or "{}")
    if int(tries.get("n") or 0) >= NOTE_TRIES:          # 12 Nov check: a failing note was tried every 15 minutes all day, the night test waiting
        # the second confirm check (S4): a try cut short (a restart, the Mac asleep or off) never reached the step below that starts the
        # night test, and every later loop returned here, so the night had no note and no night test. With the tries used up and no note,
        # the night test starts here, once.
        started = _night_test_once(j, day)
        return {"ok": False, "error": "the note's tries were used up and no note was saved", **started} if started else None
    # the try is counted before the paid call, so a failure raised anywhere after it (saving the note, say) counts too (the confirm check)
    tries = {"n": int(tries.get("n") or 0) + 1, "t": int(j.now())}
    j.db.execute("INSERT OR REPLACE INTO engine_state VALUES (?,?)", ("officer_tries:" + day, json.dumps(tries)))
    j.db.commit()
    try:
        out = write(j, daily, push=push, call=call)
    except Exception as exc:  # noqa: BLE001
        out = {"ok": False, "error": f"{type(exc).__name__}: {str(exc)[:100]}"}
    if not out.get("ok"):
        tries["error"] = str(out.get("error") or "")[:120]
        j.db.execute("INSERT OR REPLACE INTO engine_state VALUES (?,?)", ("officer_tries:" + day, json.dumps(tries)))
        j.db.commit()
        if tries["n"] >= NOTE_TRIES:                    # the last try: the night test runs without the note; the run check shows it missing
            out.update(_night_test_once(j, day))
    if out.get("ok") and not out.get("already"):
        out.update(_night_test_once(j, day))
    return {k: v for k, v in out.items() if k != "facts"}


def latest(j, n: int = 3) -> list[dict]:
    """The last notes. 12 Nov 2026 (audit repair 3): each carries the Toronto evening it was written on ("evening", G-28) and, when the
    book's own records later corrected one of its figures, the correction in plain words: "corrections", and appended to "note" so every
    screen, the phone app and the Ask show the same (G-24, G-36, G-37, G-38). "as_written" keeps the note as it was."""
    _table(j)
    out = []
    for d, t, note, c, facts in j.db.execute("SELECT day, t, note, cost_usd, facts FROM officer_notes ORDER BY day DESC LIMIT ?", (n,)).fetchall():
        try:
            fx = corrections(j, str(d), str(note or ""), json.loads(facts or "{}") or {}, int(t or 0))
        except Exception:  # noqa: BLE001  a correction that cannot be worked out never hides the note
            fx = []
        out.append({"day": d, "t": t, "evening": evening(t), "note": " ".join([str(note or "")] + fx).strip(), "as_written": note,
                    "corrections": fx, "cost_usd": c})
    return out


def _cad(x: float) -> str:
    return f"C${x:,.2f}"


def corrections(j, day: str, note: str, facts: dict, t: int = 0) -> list[str]:
    """What the book's own records later corrected in one stored note, each in one plain sentence beginning "Corrected later:"."""
    from jarvis.service import surfaces

    out: list[str] = []
    bg = facts.get("background") or {}
    late = bg.get("old_paper_trades_closed_late_tonight")
    if isinstance(late, dict) and isinstance(late.get("n"), int):                  # G-24: 41 in the note, 50 in the corrected record
        row = j.db.execute("SELECT v FROM engine_state WHERE k=?", ("late_closes:" + day,)).fetchone()
        rec = json.loads(row[0]) if row else {}
        if isinstance(rec.get("n"), int) and rec["n"] != late["n"]:
            left = {b: n - int((late.get("books") or {}).get(b) or 0) for b, n in (rec.get("books") or {}).items()
                    if n > int((late.get("books") or {}).get(b) or 0)}
            names = ", ".join(f"{n} of {b.replace('_', ' ').lower()}" for b, n in sorted(left.items())) or "some"
            fig = ", and so out of its dollar figure too" if "net_usd" in late else ""      # said only when the note gave one; never the sum
            out.append(f"Corrected later: {rec['n']} old paper trades of the measuring books were closed late that night, not {late['n']} "
                       f"({names} were left out of the count{fig}); the account was untouched.")   # no money of the measuring books (rule 9)
    acct = facts.get("account") or {}
    fix = (surfaces._night_fixes(j) or {}).get(day) or {}
    v, add = acct.get("value_cad"), float(fix.get("add_cad") or 0)
    if isinstance(v, (int, float)) and abs(add) >= 0.5:                             # G-37: the recorded value was C$26-28 low
        out.append(f"Corrected later: the account was {_cad(v + add)} that night, not the {_cad(v)} recorded; the book's own fills were "
                   "repaired afterwards.")
    dial = facts.get("dial") or {}
    if dial.get("candle") and dial.get("book_stepped_on") and dial["candle"] != dial["book_stepped_on"]:
        out.append(f"Corrected later: this note read Bitcoin's {dial['candle']} candle, not the {dial['book_stepped_on']} candle the book "
                   "stepped on, so its dial words describe the day before.")
    elif not dial.get("candle") and day <= "2026-11-10":                             # G-36: every note before the 10 Nov fix
        out.append("Corrected later: notes written before 11 Nov read Bitcoin's daily candle a day behind the one the book stepped on on "
                   "most nights, so this note's dial words may describe the day before.")
    m = re.search(r"\b(?:all[- ]cash\b|cash is 100%|100% (?:of the book )?(?:in )?cash\b)[^.]{0,90}?\b(\d+)\s+days\b|"
                  r"\b(\d+)\s+days\b[^.]{0,60}?\ball[- ]cash\b|\b(?:all[- ]cash|100%)[^.]*\.\s*It has been that way for (\d+) days\b", note, re.I)
    weeks = None if m else re.search(r"\b(?:all[- ]cash|cash is 100%|100%)[^.]{0,120}?\bfor over (two|three|four|\d+) weeks\b", note, re.I)
    if weeks and t:                                                                 # 9 Nov: "for over two weeks" (the 12 Nov check)
        n = {"two": 2, "three": 3, "four": 4}.get(weeks.group(1).lower()) or int(weeks.group(1))
        since = all_cash_since(j, t)
        real = (_dt.datetime.fromtimestamp(t, TOR).date() - since).days if since else None
        if real is not None and real < 7 * n:
            out.append(f"Corrected later: the book held coins until the evening of {since:%a} {since.day} {since:%b}, so it had been all cash "
                       f"for {real} day{'s' if real != 1 else ''} at this note, not over {weeks.group(1)} weeks.")
    if m and t:                                                                     # G-38: "all cash for 12 to 16 days"
        said = int(next(g for g in m.groups() if g))
        since = all_cash_since(j, t)
        if since:
            real = (_dt.datetime.fromtimestamp(t, TOR).date() - since).days
            if real != said:
                held = f"Corrected later: the book held coins until the evening of {since:%a} {since.day} {since:%b}"
                out.append(held + (", when it became all cash, not " + f"{said} days before." if real <= 0 else
                                   f", so it had been all cash for {real} day{'s' if real != 1 else ''} at this note, not {said}."))
    return out


def all_cash_since(j, t: int) -> _dt.date | None:
    """The Toronto evening of the step whose sales emptied the book, before time t, from the book's own fills (None when it held a coin)."""
    try:
        rows = j.db.execute("SELECT t, coin, side, qty FROM book500_fills WHERE t <= ? ORDER BY t", (int(t),)).fetchall()
    except Exception:  # noqa: BLE001
        return None
    held: dict = {}
    emptied = None
    for ft, coin, side, qty in rows:
        q = float(qty or 0)
        held[coin] = held.get(coin, 0.0) + (q if str(side).upper() == "BUY" else -q)
        if any(v > 1e-9 for v in held.values()):
            emptied = None
        elif emptied is None:
            emptied = ft
    return _dt.datetime.fromtimestamp(emptied, TOR).date() if emptied else None
