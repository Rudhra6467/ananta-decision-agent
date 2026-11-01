"""The five surfaces of the redesign (Madhav, 31 Oct 2026: "Time to give it a proper, premium and precise look"; gate 1 "yes" to
Today · Money · Ask · Proof · People; gate 2 "all looks good"). One thin view per surface, built from the files the existing views already
read, so a screen draws one call and shows exactly what the design says (claude/design-2026-10-31-phase2-3-design-system-and-screens.md).

  /india/v3/today    the decision line, two dated numbers, what waits, everything running, the morning cards (before the open) or the evening (after)
  /india/v3/money    the account, the four books with their clock, the managed plan, every holding ranked with its grade and action
  /india/v3/proof    studies run, the nightly exam, the clocks, what we missed, last night's card
  /india/v3/people   who can talk to Ananta and what each may do (names and relations only; nothing else from the private list)
Everything is paper; nothing here places anything.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from jarvis.india import views

DATA = views.DATA
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))


def _json(p: Path, default=None):
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return default


def _dw(d: str | None) -> str:
    try:
        return dt.date.fromisoformat(str(d)[:10]).strftime("%a %-d %b")
    except (TypeError, ValueError):
        return str(d or "")


def _nifty(rm: dict) -> dict:
    p = ((rm.get("technicals") or {}).get("indices") or {}).get("NIFTY 50") or {}
    m = rm.get("market") or {}
    close = p.get("close") or m.get("nifty_close")
    d1 = p.get("change_1d")
    trend = {"below_both": "downtrend", "above_both": "uptrend", "mixed": "no clear trend"}.get(((rm.get("regime") or {}).get("trend")) or "", "")
    v50 = m.get("nifty_vs_sma50")
    return {"close": close, "change_1d_pct": round(100 * d1, 1) if isinstance(d1, (int, float)) else None, "as_of": p.get("as_of") or rm.get("data_through"),
            "trend": trend, "vs_sma50_pct": round(100 * v50, 1) if isinstance(v50, (int, float)) else None,
            "line": (f"{close:,.0f}" if isinstance(close, (int, float)) else "—") + (f" · {100 * d1:+.1f}%" if isinstance(d1, (int, float)) else "")
                    + (f" · {trend}" if trend else "") + (f", {100 * v50:+.1f}% vs 50-day" if isinstance(v50, (int, float)) else "")}


def _managed() -> dict:
    return _json(DATA / "paper" / "managed" / "view.json", {}) or {}


def _account_view() -> dict:
    return _json(DATA / "paper" / "account" / "view.json", {}) or {}


def today(full: bool = True) -> dict:
    rm = views.readmodel()
    m = views.morning()
    mb = _managed()
    plan = mb.get("plan") or {}
    acct = _account_view()
    now = dt.datetime.now(IST)
    session = m.get("session")
    before_open = bool(session) and (now.date() < dt.date.fromisoformat(session) or (now.date() == dt.date.fromisoformat(session) and now.time() < dt.time(9, 15)))
    after_close = now.time() >= dt.time(15, 30) or now.weekday() >= 5
    # the decision line: the managed book's brief for the next session, else the morning view's headline
    decision = plan.get("brief") if plan.get("for_session") == session and not plan.get("error") else None
    if not decision and plan.get("brief"):
        decision = plan["brief"]
    if not decision:
        decision = m.get("headline") or "No plan is written yet."
    source = (f"From the plan written {_dw(plan.get('written_day'))} · fills at the open · nothing is placed" if plan.get("brief")
              else "From the morning view · nothing is placed")
    health = views._health(rm) if hasattr(views, "_health") else {}
    waiting = m.get("waiting") or views._waiting_count()
    cards = []
    if plan.get("words"):
        cards.append({"kind": "plan", "label": f"{_dw(plan.get('for_session'))}'s plan · managed book", "text": plan["words"], "accent": True,
                      "foot": f"{len(plan.get('cuts') or [])} cuts · {len(plan.get('buys') or [])} buys · a buy opening over 2% up is skipped"})
    if m.get("view"):
        cards.append({"kind": "market", "label": "The market", "text": " ".join(m["view"][:2])})
    hs = m.get("holdings_suggestions") or []
    if hs:
        cards.append({"kind": "holdings", "label": "Your holdings", "text": "Cut list: " + ", ".join(x.get("symbol") for x in hs if x.get("symbol")),
                      "foot": (acct.get("benchmark") or {}).get("words")})
    if m.get("chances"):
        cards.append({"kind": "chances", "label": "Our chances, honestly", "text": " ".join(m["chances"][:1])})
    if m.get("watch"):
        cards.append({"kind": "watch", "label": "What to watch", "text": " ".join(m["watch"][:2])})
    fills = mb.get("filled_today") or []
    evening = None
    if fills:
        evening = {"label": f"What the managed book did on {_dw(mb.get('day'))}",
                   "text": "; ".join((f"{'bought' if t.get('side') == 'BUY' else 'sold'} {t.get('qty')} {t.get('symbol')} at ₹{t.get('price'):,.2f}" if t.get("filled")
                                      else f"skipped {t.get('symbol')} ({t.get('skipped')})") for t in fills)}
    when = ("before the open" if before_open else "after the close" if after_close else "market hours")
    return {"ready": True, "session": session, "session_words": m.get("session_words"), "when": when, "now_words": now.strftime("%A %-d %b, %H:%M IST"),
            "decision": decision, "decision_source": source,
            "numbers": [{"label": "Nifty · " + _dw(_nifty(rm).get("as_of")), "value": (f"{_nifty(rm)['close']:,.0f}" if isinstance(_nifty(rm).get("close"), (int, float)) else "—"),
                         "sub": _nifty(rm)["line"].split(" · ", 1)[-1] if " · " in _nifty(rm)["line"] else ""},
                        {"label": "Your account", "value": (f"₹{acct['value_inr']:,.0f}" if acct.get("value_inr") else "—"),
                         "sub": f"NSE close · {acct.get('positions') and len(acct['positions'])} stocks, ₹{acct.get('options_inr', 0):,.0f} options" if acct else "no snapshot yet"}],
            "waiting": {"count": waiting.get("count") or 0, "words": waiting.get("words")},
            "running": {"ok": bool(health.get("all_ok")), "words": "Everything is running" if health.get("all_ok") else f"{len(health.get('down') or [])} part{'s' if len(health.get('down') or []) != 1 else ''} down",
                        "checked": f"checked {int((health.get('checked_s_ago') or 0) // 60)} min ago" if health.get("checked_s_ago") is not None else ""},
            "cards": cards, "evening": evening, "clock": (mb.get("clock") or {}).get("words"),
            "suggested": ["What replaces Jio Financial?", "How are the trials going?", "What's waiting for my yes?"],
            "next_view": "The morning view arrives at 08:30 Indian time (23:00 Toronto)." if not m.get("ready") else None, "paper": True}


def money(full: bool = True) -> dict:
    alloc = views.allocation_plan(full=full)
    acct = _account_view()
    bm = acct.get("benchmark") or {}
    mb = _managed()
    plan = mb.get("plan") or {}
    books = [{"id": "yours", "label": "As you have it", "ret_pct": bm.get("frozen_ret_pct")}, {"id": "twin", "label": "The twin", "ret_pct": bm.get("twin_ret_pct")},
             {"id": "managed", "label": "Managed", "ret_pct": mb.get("return_pct") if (mb.get("clock") or {}).get("sessions") else None, "words": None if (mb.get("clock") or {}).get("sessions") else f"starts {_dw(plan.get('for_session'))}"},
             {"id": "index", "label": "Nifty 500", "ret_pct": bm.get("nifty500_ret_pct")}]
    holdings = []
    for x in (alloc.get("holdings") or []) if full else []:
        holdings.append({"symbol": x.get("symbol"), "value_inr": x.get("value_inr"), "weight_pct": x.get("weight_pct"), "pnl_pct": x.get("pnl_pct"), "grade": x.get("grade"),
                         "action": (x.get("action") or "").lower(), "suggest_inr": x.get("suggest_inr"), "why": x.get("why"), "wrong_if": x.get("wrong_if")})
    return {"ready": True, "paper": True, "value_inr": acct.get("value_inr"), "stocks_inr": acct.get("stocks_inr"), "options_inr": acct.get("options_inr"), "cash_inr": acct.get("cash_inr"),
            "as_of": f"NSE close {_dw((acct.get('marks') or {}).get('last_session'))}" if acct.get("marks") else None,
            "books": books, "clock": {"sessions": bm.get("sessions"), "of": 60, "finish_words": None, "words": f"Session {bm.get('sessions')} of 60" if bm.get("sessions") is not None else None, "since": bm.get("frozen_day")},
            "books_note": "Same start, same prices for all four. Nothing is read into the gap before session 60.",
            "plan": {"for_session": plan.get("for_session"), "brief": plan.get("brief"), "words": plan.get("words"), "cuts": len(plan.get("cuts") or []), "buys": [{"symbol": b.get("symbol"), "for_cut": b.get("for_cut"), "inr": b.get("inr"), "reasons": b.get("reasons")} for b in plan.get("buys") or []],
                     "no_change": plan.get("no_change"), "error": plan.get("error")} if plan else None,
            "managed": {"value_inr": mb.get("value_inr"), "return_pct": mb.get("return_pct"), "clock": (mb.get("clock") or {}).get("words"), "replacements": mb.get("replacements") or []},
            "holdings": holdings, "holdings_note": "Ranked by Ananta's grade; a suggestion is advice, the managed book acts on it on paper.", "options": alloc.get("options"), "headline": alloc.get("headline")}


def proof(full: bool = True) -> dict:
    rm = views.readmodel()
    trials = (_json(DATA / "manifests" / "trials.json", {}) or {}).get("trials") or []
    clocks = [{"name": t.get("name"), "done": t.get("done"), "need": t.get("need"), "unit": t.get("unit"), "finish": t.get("expected_finish"),
               "finish_words": _dw(t.get("expected_finish")) + (f" {str(t.get('expected_finish'))[:4]}" if str(t.get("expected_finish"))[:4] != str(dt.date.today().year) else ""),
               "complete": t.get("complete"), "so_far": t.get("so_far")} for t in trials]
    research = rm.get("research") or {}
    exam = _json(DATA.parent / "ananta_runs" / "benchmark_20261030" / "scorecard.json", {}) or {}
    replay = None
    try:
        from jarvis.india import replay as rp
        replay = _json(rp.OUT / "latest.json", {}).get("summary") if (rp.OUT / "latest.json").exists() else None
    except Exception:  # noqa: BLE001
        replay = None
    missed = None
    try:
        missed = views.ROUTES["missed"]() if "missed" in views.ROUTES else None
    except Exception:  # noqa: BLE001
        missed = None
    recon = None
    try:
        recon = views.reconstruction() if hasattr(views, "reconstruction") else None
    except Exception:  # noqa: BLE001
        recon = None
    return {"ready": True, "paper": True,
            "studies": {"run": research.get("versions_tested"), "held_up": (research.get("verdicts") or {}).get("VALIDATED"), "conditional": (research.get("verdicts") or {}).get("CONDITIONAL"),
                        "words": f"{research.get('versions_tested')} versions tested; {(research.get('verdicts') or {}).get('VALIDATED')} held up, {(research.get('verdicts') or {}).get('CONDITIONAL')} with conditions", "basis": "2000–2023 only; 2024 on is sealed"},
            "exam": {"grade": (exam.get("outsider_r5") or exam.get("outsider_r4") or {}).get("overall") if isinstance(exam.get("outsider_r5") or exam.get("outsider_r4"), dict) else None, "words": replay.get("words") if replay else None},
            "clocks": clocks, "missed": {"words": (missed or {}).get("words") or (missed or {}).get("headline"), "day": (missed or {}).get("day")} if missed else None,
            "last_night": {"words": (recon or {}).get("words") or (recon or {}).get("headline")} if recon else None,
            "links": [{"label": "Teachers, tested", "route": "/teachers"}, {"label": "The repair board", "route": "/flags"}, {"label": "Last night's card", "route": "/reconstruction"}, {"label": "What we missed", "route": "/missed"}]}


def people(full: bool = True) -> dict:
    from jarvis.india import speaker
    rows = [{"id": "madhav", "name": "Madhav", "relation": "owner", "can": "decides everything", "voice": None}]
    try:
        from jarvis.india import voiceid
        st = voiceid.status() if hasattr(voiceid, "status") else {}
        rows[0]["voice"] = "voice taught" if (st or {}).get("enrolled") else "voice not taught yet"
    except Exception:  # noqa: BLE001
        pass
    try:
        from jarvis.service import people as ppl
        for p in (ppl.load() or {}).get("people") or []:
            nm = (p.get("names") or [None])[0] if isinstance(p, dict) else None
            if not nm:
                continue
            rows.append({"id": str(p.get("id") or nm).lower(), "name": nm, "relation": p.get("relation") or "", "can": "can ask; can't approve or change anything", "voice": None})
    except Exception:  # noqa: BLE001
        pass
    rows.append({"id": "grader", "name": "The grader", "relation": "tests Ananta", "can": "no 'sir'; nothing needs its yes", "voice": None})
    return {"ready": True, "people": rows, "rule": "Only Madhav decides; everyone else can ask. A guest is greeted by name and never 'sir'.",
            "invite": "An invited person is onboarded by Ananta in two minutes: who they are to you, what they can do, their voice if they like, and a short tour in its own voice."}


views.ROUTES.update({"today": today, "money": money, "proof": proof, "people": people})
