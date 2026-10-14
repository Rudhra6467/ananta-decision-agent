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
(signals, measuring books, anything that passed or was pushed), in one or two sentences, without listing every book; (3) what needs
him, or "nothing needs you". Never invent a number: every figure must come from the facts. No headings, no bullet points, no
greeting by time of day. If the facts say a brake fired or a strategy passed, lead with that."""


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
    except Exception as exc:  # noqa: BLE001
        f["account_error"] = str(exc)[:120]
    try:
        d = exposure.state(j)
        f["dial"] = {"state": d.get("dial_words"), "why": d.get("why")}
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
    f["background"] = {**bg, "brain_woke": daily.get("brain_woke"), "pushed": daily.get("pushed") or [],
                       "missed_moves": (daily.get("missed") or [])[:5] if isinstance(daily.get("missed"), list) else daily.get("missed"),
                       "brain_rebuild": daily.get("brain_rebuild"), "weekly_review": daily.get("weekly_review")}
    try:
        st = strategy_status.load().get("strategies") or {}
        f["strategies"] = {k: v.get("status") for k, v in st.items()}
        f["pushed_rule"] = strategy_status.pushed_rule()
    except Exception:  # noqa: BLE001
        pass
    return f


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
    note = " ".join(text.strip().split())
    if not note:
        return {"ok": False, "error": "empty note", "facts": f}
    j.db.execute("INSERT OR REPLACE INTO officer_notes VALUES (?,?,?,?,?)", (day, int(j.now()), note, json.dumps(f, default=str)[:20000], cost))
    j.db.commit()
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
