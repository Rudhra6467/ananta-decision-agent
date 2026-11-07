"""Today's India session as it is right now: the clock, the live index, today's own decisions, today's plan at the open.

Why (Madhav, 2 Nov 2026, "these are huge mistakes ... make sure these things don't repeat again"): at 16:38 IST on Monday the Ask said
"Monday's session is happening" an hour after the close, said it had "no record" of what the options line decided although the decisions had
been written at 09:15-09:45 IST, and said it could not see the live market although the read-only Kite connection reads it. The opening update
at 11:20 IST said "no record" too. The facts only carried the nightly read model, so anything that happened today was invisible.

This module reads today directly:
  clock        India time and Toronto time, whether today is a session, before/open/closed, the latest session that has started, and how
               Madhav's Toronto 'today'/'yesterday' maps onto Indian sessions
  index_now    Nifty, Bank Nifty and India VIX from Kite (read-only GET /quote/ohlc), cached for 60 seconds
  options      today's decisions from the options line's own ledger (paper/sp1/decisions.jsonl), with the option's price now
  holdings     Madhav's holdings as he has them (frozen.json, Money's 'As you have it') moved by today's prices
  managed      today's managed-book plan against today's opening prices (fills are booked by the 19:00 Toronto job)
  data_timing  when each kind of data lands

Read-only: Kite is used through the records repo's GET-only client (india.kite), quotes only; nothing here places, changes or cancels anything.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
import threading
import time
from pathlib import Path
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
TOR = ZoneInfo("America/Toronto")
DATA = Path(os.getenv("ANANTA_INDIA_DATA", os.path.expanduser("~/ananta_data/india")))
RECORDS = Path(os.getenv("ANANTA_RECORDS", os.path.expanduser("~/code/ananta-records")))
INDEX = {"NIFTY 50": "NSE:NIFTY 50", "NIFTY BANK": "NSE:NIFTY BANK", "INDIA VIX": "NSE:INDIA VIX"}
_CACHE: dict = {}
_LOCK = threading.Lock()
TTL_S = 60


def _holidays() -> set:
    try:
        from jarvis.india import answerguide
        return set(answerguide._holidays())
    except Exception:  # noqa: BLE001
        return set()


def is_session(d: dt.date, hol: set | None = None) -> bool:
    hol = _holidays() if hol is None else hol
    return d.weekday() < 5 and d not in hol and d.isoformat() not in hol


def prev_session(d: dt.date, hol: set | None = None) -> dt.date:
    hol = _holidays() if hol is None else hol
    x = d - dt.timedelta(days=1)
    while not is_session(x, hol):
        x -= dt.timedelta(days=1)
    return x


def _dw(d: dt.date) -> str:
    return d.strftime("%A %-d %b")


def clock(data_through: str | None, now: dt.datetime | None = None) -> dict:
    """Where the NSE day stands. data_through is the newest finished day in the nightly data (the read model)."""
    now = (now or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc)
    ist, tor = now.astimezone(IST), now.astimezone(TOR)
    hol = _holidays()
    today = ist.date()
    session_day = is_session(today, hol)
    minute = ist.hour * 60 + ist.minute
    if not session_day:
        state = "no_session"
    elif minute < 9 * 60:
        state = "before_open"
    elif minute < 9 * 60 + 15:
        state = "pre_open"            # NSE's pre-open order collection, 09:00-09:08, matching to 09:15
    elif minute < 15 * 60 + 30:
        state = "open"
    else:
        state = "closed"
    # the latest session that has started: today once 09:15 has passed on a session day, else the previous session
    latest = today if (session_day and state in ("open", "closed")) else prev_session(today, hol)
    nxt = today if (session_day and state in ("before_open", "pre_open")) else None
    if nxt is None:
        nxt = today + dt.timedelta(days=1)
        while not is_session(nxt, hol):
            nxt += dt.timedelta(days=1)
    through = str(data_through or "")[:10]
    latest_in_nightly = bool(through) and through >= latest.isoformat()
    said = {"no_session": f"there is no NSE session today ({_dw(today)} is a weekend or exchange holiday)",
            "before_open": "today's NSE session has not started; it opens at 09:15 IST (pre-open from 09:00)",
            "pre_open": "NSE is in its pre-open (09:00-09:15 IST); trading starts at 09:15",
            "open": "today's NSE session is OPEN now (09:15 to 15:30 IST)",
            "closed": "today's NSE session has CLOSED (it closed at 15:30 IST)"}[state]
    if state in ("before_open", "pre_open"):
        to_open = 9 * 60 + 15 - minute
        said += f" ({to_open // 60} h {to_open % 60} min from now)" if to_open >= 60 else f" ({to_open} min from now)"
    if state == "closed":
        mins = minute - (15 * 60 + 30)
        said += f", {mins // 60} h {mins % 60} min ago" if mins >= 60 else f", {mins} min ago"
    tor_words = tor.strftime("%A %-d %b, %-I:%M %p").replace("AM", "am").replace("PM", "pm")
    ist_words = ist.strftime("%A %-d %b, %H:%M")
    tail = (f"{_dw(latest)}, today in India ({'still trading' if state == 'open' else 'finished'})" if latest == today else _dw(latest))
    rel = (f"Madhav is in Toronto ({tor_words}). When he says 'today', 'yesterday', 'this morning' or 'the market' about India, he means the "
           f"latest Indian session that has started: {tail}. Never answer with an older session without saying why.")
    tor_day = tor.date()
    if tor_day == latest and latest != today:
        # 2 Nov round (13:30 Toronto = 00:00 IST Tuesday): it is past midnight in India but still that afternoon/evening in Toronto, so his
        # 'today' is the session that just finished and 'tomorrow' is the next one
        rel = (f"Madhav is in Toronto ({tor_words}). It is already {_dw(today)} in India, but for him 'today' and 'the market today' still mean "
               f"{_dw(latest)}'s session, which has finished; 'tomorrow' means {_dw(nxt)} (opens 09:15 IST). Never answer with an older session "
               "without saying why.")
    elif session_day and state in ("before_open", "pre_open"):
        rel += (f" Today's session ({_dw(today)}) has not started yet: 'today' and 'now' are about what is coming at 09:15 IST "
                f"(the plan, the levels to watch, what happened overnight), and the last finished session is {_dw(latest)}.")
    return {"ts": now.timestamp(), "ist_now": ist_words + " IST", "toronto_now": tor_words, "today_india": today.isoformat(), "today_is_session": session_day, "state": state,
            "latest_session": latest.isoformat(), "latest_session_words": _dw(latest), "next_session": nxt.isoformat(), "next_session_words": _dw(nxt),
            "nightly_data_through": through or None, "latest_session_in_nightly_data": latest_in_nightly,
            "words": f"It is {ist_words} in India ({tor_words} in Toronto): {said}.",
            "relative_days": rel}


def _sched_at(label: str) -> str:
    from jarvis.india import schedule
    return schedule.at(label)


def data_timing(clk: dict) -> str:
    """Independent audit, 2 Nov: the hand-written version had the picks and the day file at 7 pm (they land at 9:30 pm and 12:45 pm).
    Now read from the launchd jobs, so it is right in every season."""
    from jarvis.india import schedule
    return schedule.day_words()


def _kite():
    if str(RECORDS) not in sys.path:
        sys.path.append(str(RECORDS))
    from india import kite          # the records repo's GET-only client; it never prints or returns the token
    return kite.Kite(rate_per_s=5.0)


def quotes(symbols: list[str], fetch=None) -> dict:
    """GET /quote/ohlc for up to 500 instruments (e.g. 'NSE:NIFTY 50', 'NSE:TCS', 'NFO:...'): last price, open, high, low and the previous
    close. Cached for TTL_S; a failure returns {'error': ...} and is never raised into an answer."""
    syms = sorted({s for s in symbols if s})
    if not syms:
        return {}
    key = tuple(syms)
    with _LOCK:
        hit = _CACHE.get(key)
        if hit and time.time() - hit[0] < TTL_S:
            return hit[1]
    try:
        raw = fetch(syms) if fetch else _kite().get("/quote/ohlc", params={"i": syms[:500]})
        out = {s: {"last": v.get("last_price"), "open": (v.get("ohlc") or {}).get("open"), "high": (v.get("ohlc") or {}).get("high"),
                   "low": (v.get("ohlc") or {}).get("low"), "prev_close": (v.get("ohlc") or {}).get("close")} for s, v in (raw or {}).items()}
        out = {"rows": out, "at": time.time()}
    except Exception as exc:  # noqa: BLE001
        out = {"error": f"{type(exc).__name__}: {str(exc)[:120]}", "rows": {}, "at": time.time()}
    with _LOCK:
        _CACHE[key] = (time.time(), out)
    return out


def _pct(a, b):
    return round(100 * (a / b - 1), 2) if isinstance(a, (int, float)) and isinstance(b, (int, float)) and b else None


def _kind(clk: dict, fetched_at: float) -> tuple[str, str]:
    """What a Kite price is at this moment: live, pre-open, today's close or the last session's close."""
    ts = fetched_at if abs(fetched_at - clk.get("ts", fetched_at)) < 300 else clk["ts"]     # a replayed moment keeps its own time
    at = dt.datetime.fromtimestamp(ts, IST).strftime("%H:%M IST")
    if clk["state"] == "open":
        return at, f"live at {at}"
    if clk["state"] == "pre_open":
        return at, f"in the pre-open at {at} (indicative; trading starts 09:15 IST)"
    if clk["latest_session"] == clk["today_india"]:
        return at, "at today's close (Kite's closing price; the official NSE file lands later the same day)"
    return at, f"at the close of {clk['latest_session_words']}, the last session (the next opens {clk['next_session_words']} 09:15 IST)"


def stocks_now(clk: dict, symbols: list[str], fetch=None) -> dict:
    """Independent audit, 2 Nov: 'what is Cipla at now?' gave Friday's close all Monday, because the stock lookup read only the nightly
    quotebook. This is the stock's Kite price now (or at the latest session's close), read-only, for the stocks the question names."""
    syms = [s for s in symbols if s][:20]
    if not syms:
        return {}
    q = quotes([f"NSE:{s}" for s in syms], fetch)
    if q.get("error"):
        return {"error": q["error"], "words": "I could not reach today's stock prices from Kite just now; quote the nightly close with its date and say so."}
    at, kind = _kind(clk, q["at"])
    rows, parts = {}, []
    for s in syms:
        r = (q.get("rows") or {}).get(f"NSE:{s}") or {}
        if r.get("last") is None:
            continue
        ch = _pct(r["last"], r.get("prev_close"))
        rows[s] = {**r, "change_pct": ch}
        rng = f"; day's range {r['low']:,.2f}-{r['high']:,.2f}" if r.get("low") and r.get("high") else ""
        parts.append(f"{s} Rs {r['last']:,.2f}" + (f" ({ch:+.2f}% on the previous close Rs {r['prev_close']:,.2f}{rng})" if ch is not None else ""))
    if not parts:
        return {"words": None}
    return {"as_of": at, "kind": kind, "rows": rows,
            "words": f"{clk['latest_session_words']}, {kind}: " + "; ".join(parts) + ". This is newer than the nightly 'closed ... on' lines; lead with it."}


def _closing_bars(clk: dict) -> dict | None:
    """Independent audit, 2 Nov: Zerodha's sign-in lapses at 06:00 IST and the automatic sign-in ran at 07:10 IST, so from 7:30 to 8:40 pm Toronto
    (winter) live prices failed. It runs at 06:05 IST from 2 Nov; this still covers a failed sign-in. Outside the session the closing bars already on disk (manifests/technicals.json, from Kite's index bars after the
    close) give the same closes, so say those, with their date."""
    if clk["state"] == "open":
        return None
    try:
        idx = json.loads((DATA / "manifests" / "technicals.json").read_text()).get("indices") or {}
    except Exception:  # noqa: BLE001
        return None
    rows = {}
    for name in INDEX:
        r = idx.get(name) or {}
        if r.get("close") is None or r.get("as_of") != clk["latest_session"]:
            continue
        rows[name] = {"last": r["close"], "prev_close": r.get("prev_close"), "open": None, "high": None, "low": None,
                      "change_pct": _pct(r["close"], r.get("prev_close")), "from_open_pct": None}
    if "NIFTY 50" not in rows:
        return None
    parts = [f"{ {'NIFTY 50': 'Nifty', 'NIFTY BANK': 'Bank Nifty', 'INDIA VIX': 'India VIX'}[n] } {r['last']:,.2f}"
             + (f" ({r['change_pct']:+.2f}% on the previous close {r['prev_close']:,.2f})" if r["change_pct"] is not None else "") for n, r in rows.items()]
    return {"live": False, "as_of": None, "kind": f"at the close of {clk['latest_session_words']} (from the closing bars on file; Zerodha's live feed is "
            "signed out until the morning sign-in)", "rows": rows,
            "words": f"{clk['latest_session_words']}, at the close (from the closing bars on file; the live feed is signed out until the morning sign-in, "
                     "so the day's open, high and low are not in this line): " + "; ".join(parts) + "."}


def index_now(clk: dict, fetch=None) -> dict:
    # 2 Nov round: before the open (and on a day with no session) Kite still gives the latest session's close, high and low; only the label
    # changes ("no live prices" before the open made Ananta say it had no high or low for the day that had just finished)
    q = quotes(list(INDEX.values()), fetch)
    if q.get("error"):
        fb = _closing_bars(clk)
        if fb:
            return fb | {"error": q["error"]}
        return {"live": False, "error": q["error"], "words": "I could not reach the live prices from Kite just now (" + q["error"][:60] + "); say so, do not guess."}
    rows = {}
    for name, sym in INDEX.items():
        r = q["rows"].get(sym) or {}
        if r.get("last") is None:
            continue
        rows[name] = {**r, "change_pct": _pct(r["last"], r.get("prev_close")), "from_open_pct": _pct(r["last"], r.get("open"))}
    at, kind = _kind(clk, q["at"])
    parts = []
    for name, r in rows.items():
        label = {"NIFTY 50": "Nifty", "NIFTY BANK": "Bank Nifty", "INDIA VIX": "India VIX"}[name]
        ch = r.get("change_pct")
        # 2 Nov moment harness: one turn said 23,440 and the next 23,441 for 23,440.80; give the one rounded figure to say
        say = f", say {round(r['last']):,}" if label != "India VIX" else ""
        parts.append(f"{label} {r['last']:,.2f}{say}" + (f" ({'+' if ch >= 0 else ''}{ch:.2f}% on the previous close {r['prev_close']:,.2f}; opened {r['open']:,.2f})" if ch is not None else ""))
    return {"live": clk["state"] == "open", "as_of": at, "kind": kind, "rows": rows,
            "words": f"{clk['latest_session_words']}, {kind}: " + "; ".join(parts) + "." if parts else "No index prices came back from Kite."}


def _jsonl(p: Path) -> list[dict]:
    try:
        return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
    except Exception:  # noqa: BLE001
        return []


EXIT_WORDS = {"NEXTOPEN": "closing at the next session's open", "T1130": "closing at 11:30 IST", "T1515": "closing at 15:15 IST",
              # 5 Nov 2026 (Madhav's chat): "ATRSTOP" was said as a code, and a trade its stop had already closed was described as still open
              "ATRSTOP": "with a stop half a day's average range against it, else closing at 15:15 IST",
              "ORSTOP": "with a stop at the far side of the opening range, else closing at 15:15 IST",
              "TRAIL": "with a trailing stop, else closing at 15:15 IST"}


def _scored(day: str) -> dict:
    """The options line's own scoring of a session (paper/sp1/outcomes.jsonl, written at 17:30 IST): how each trade actually ended."""
    out = {}
    for r in _jsonl(DATA / "paper" / "sp1" / "outcomes.jsonl"):
        if r.get("date") == day:
            out[(r.get("index"), r.get("point"))] = r
    return out


def options_today(clk: dict, fetch=None, path: Path | None = None) -> dict:
    """The options line's decisions for the latest session, straight from its ledger, with the chosen option's price now."""
    day = clk["latest_session"]
    rows = [r for r in _jsonl(path or DATA / "paper" / "sp1" / "decisions.jsonl") if r.get("date") == day]
    plan = next((r for r in rows if r.get("kind") == "plan"), None)
    dec = [r for r in rows if r.get("kind") == "decision"]
    if not dec:
        if clk["state"] in ("open", "closed") and clk["latest_session"] == clk["today_india"]:
            w = (f"The options line has a plan for today (made {str(plan.get('made_at'))[11:16]} IST) but no decision is in its ledger yet."
                 if plan else "The options line has no plan and no decision in its ledger for today: it did not run; say so.")
        else:
            w = f"No options decisions in the ledger for {clk['latest_session_words']}."
        return {"day": day, "decisions": [], "taken": [], "words": w}
    taken, passed = [], []
    for r in dec:
        ch = r.get("choice")
        t = str(r.get("decided_at") or "")[11:16]
        if ch:
            opt = ((r.get("contracts") or {}).get("option") or {})
            qd = r.get("quotes_at_decision") or {}
            osym = f"NFO:{opt.get('tradingsymbol')}" if opt.get("tradingsymbol") else None
            taken.append({"index": r.get("index"), "point": r.get("point"), "at": t, "direction": "long" if ch.get("dir", 1) > 0 else "short",
                          "exit": ch.get("exit"), "exit_words": EXIT_WORDS.get(str(ch.get("exit")), str(ch.get("exit"))), "index_level": r.get("entry_estimate"),
                          "option": (f"{opt.get('strike'):.0f} {opt.get('type')}" if opt.get("strike") else None), "option_symbol": osym,
                          "option_price_at_decision": qd.get(osym) if osym else None, "lot": opt.get("lot"), "expiry": opt.get("expiry")})
        else:
            passed.append(f"{ {'NIFTY': 'Nifty', 'BANKNIFTY': 'Bank Nifty'}.get(r.get('index'), r.get('index')) } at {t}")
    idx_sym = {"NIFTY": "NSE:NIFTY 50", "BANKNIFTY": "NSE:NIFTY BANK"}
    if taken:
        q = quotes([x["option_symbol"] for x in taken if x["option_symbol"]] + sorted({idx_sym[x["index"]] for x in taken if x["index"] in idx_sym}), fetch)
        rows = q.get("rows") or {}
        for x in taken:
            now = (rows.get(x["option_symbol"]) or {}).get("last") if x["option_symbol"] else None
            x["option_price_now"] = now
            if now is not None and x["option_price_at_decision"] and x["lot"]:
                x["paper_move_inr_per_lot"] = round((now - x["option_price_at_decision"]) * x["lot"])
            # 2 Nov moment harness: the model said "both indexes are up since entry" while Bank Nifty was below its entry; say it here, in code
            lvl = (rows.get(idx_sym.get(x["index"], "")) or {}).get("last")
            if lvl is not None and x["index_level"]:
                pts = lvl - x["index_level"]
                x["index_now"], x["index_since_entry_pts"] = lvl, round(pts)
                x["index_since_entry_words"] = (f"the index is {abs(pts):,.0f} points {'above' if pts >= 0 else 'below'} where it was taken"
                                                f" ({lvl:,.0f} against {x['index_level']:,.0f}), which is {'for' if (pts >= 0) == (x['direction'] == 'long') else 'against'} the trade")
    name = {"NIFTY": "Nifty", "BANKNIFTY": "Bank Nifty"}
    # 5 Nov 2026 (Madhav's chat at 10:44 Toronto): the Bank Nifty short had been closed by its stop at 11:30 IST (option sold near Rs 577, about
    # Rs -7,253 after costs), but Ananta said "the option is at Rs 478 now, about Rs -8,782 on paper", marking a closed trade at the close.
    # Once the line has scored the session, a trade's real ending is said, not today's price.
    scored = _scored(day) if path is None else {}
    for x in taken:
        sc = scored.get((x["index"], x["point"]))
        if not sc:
            continue
        ip, opt = sc.get("index_proxy") or {}, ((sc.get("legs") or {}).get("option") or {})
        x["closed"] = bool(ip.get("stopped")) or str(x.get("exit")).upper() != "NEXTOPEN"
        if x["closed"]:
            x["result"] = {"stopped": bool(ip.get("stopped")), "option_entry": opt.get("entry_realistic"), "option_exit": opt.get("exit"),
                           "net_inr": round(opt["net_rs_realistic"]) if opt.get("net_rs_realistic") is not None else None,
                           "index_net_bps": ip.get("net_bps"), "how": opt.get("exit_rule")}
            for k in ("paper_move_inr_per_lot", "option_price_now", "index_since_entry_words"):
                x.pop(k, None)
    tw = []
    for x in taken:
        s = f"{name.get(x['index'], x['index'])} {x['direction']} at {x['at']} IST (index near {x['index_level']:,.0f}"
        if x["option"]:
            s += f"; the {x['option']} option at about Rs {x['option_price_at_decision']}" if x["option_price_at_decision"] else f"; the {x['option']} option"
        s += f"), {x['exit_words']}"
        res = x.get("result")
        if res:
            s += ("; it is CLOSED: " + ("its stop was hit" if res["stopped"] else "it closed by its rule")
                  + (f", the option sold near Rs {res['option_exit']:,.2f} (bought near Rs {res['option_entry']:,.2f} at the next minute's fill)"
                     if res.get("option_exit") and res.get("option_entry") else "")
                  + (f", a paper result of about Rs {res['net_inr']:+,} for the lot after costs" if res.get("net_inr") is not None else "")
                  + "; say it as a closed trade with this result, never today's option price")
        if x.get("paper_move_inr_per_lot") is not None:
            s += (f"; the option is at Rs {x['option_price_now']} now, about Rs {x['paper_move_inr_per_lot']:+,} a lot on paper"
                  f" ({'in profit' if x['paper_move_inr_per_lot'] > 0 else 'in loss' if x['paper_move_inr_per_lot'] < 0 else 'flat'})")
        if x.get("index_since_entry_words"):
            s += f"; {x['index_since_entry_words']}"
        tw.append(s)
    words = (f"The options line on {clk['latest_session_words']} decided at {len(dec)} points: " + ("took " + "; ".join(tw) if tw else "took nothing")
             + (f"; passed on {', '.join(passed)}" if passed else "") + ". Paper only; one lot each.")
    return {"day": day, "decisions": len(dec), "taken": taken, "passed": passed, "words": words}


def _frozen_positions() -> list[dict]:
    """Madhav's holdings as they stood when the twin opened, never traded (paper/account/frozen.json): the Money screen's 'As you have it'."""
    try:
        z = json.loads((DATA / "paper" / "account" / "frozen.json").read_text())
    except Exception:  # noqa: BLE001
        return []
    pos = z.get("positions") or {}
    return [{"symbol": s, "qty": v.get("qty")} for s, v in pos.items()] if isinstance(pos, dict) else list(pos)


def holdings_today(clk: dict, positions: list[dict], fetch=None) -> dict:
    """Madhav's holdings as he has them (the frozen copy, the Money screen's 'As you have it'), moved by today's prices."""
    if not positions or clk["state"] == "pre_open":
        return {"words": None}
    q = quotes([f"NSE:{p['symbol']}" for p in positions if p.get("symbol")], fetch)
    if q.get("error"):
        return {"error": q["error"], "words": "I could not reach today's prices for the holdings just now."}
    move, base, rows = 0.0, 0.0, []
    for p in positions:
        r = (q.get("rows") or {}).get(f"NSE:{p.get('symbol')}") or {}
        if r.get("last") is None or not r.get("prev_close") or not p.get("qty"):
            continue
        d = p["qty"] * (r["last"] - r["prev_close"])
        move += d
        base += p["qty"] * r["prev_close"]
        rows.append({"symbol": p["symbol"], "change_pct": _pct(r["last"], r["prev_close"]), "move_inr": round(d)})
    if not rows:
        return {"words": None}
    rows.sort(key=lambda x: x["move_inr"])
    pct = 100 * move / base if base else 0
    up = [f"{x['symbol']} {x['change_pct']:+.1f}%" for x in rows[::-1][:3] if x["move_inr"] > 0]
    dn = [f"{x['symbol']} {x['change_pct']:+.1f}%" for x in rows[:3] if x["move_inr"] < 0]
    when = ("so far today" if clk["state"] == "open" else "today" if clk["latest_session"] == clk["today_india"] else f"on {clk['latest_session_words']}")
    return {"move_inr": round(move), "move_pct": round(pct, 2), "rows": rows,
            "words": f"Your holdings as you have them (the 'As you have it' book on Money, not the twin) are {'up' if move >= 0 else 'down'} about Rs {abs(move):,.0f} ({pct:+.2f}%) {when}"
                     + (f"; best {', '.join(up)}" if up else "") + (f"; worst {', '.join(dn)}" if dn else "") + "."}


def managed_today(clk: dict, plan: dict, fetch=None) -> dict:
    """Today's managed-book plan against today's opening prices. The fills themselves are booked by the 19:00 Toronto job from the official day file."""
    if not plan or plan.get("for_session") != clk["latest_session"]:
        return {"words": None}
    buys = [b for b in plan.get("buys") or [] if b.get("symbol")]
    cuts = [c for c in plan.get("cuts") or [] if c.get("symbol")]
    q = quotes([f"NSE:{x['symbol']}" for x in buys + cuts], fetch)
    if q.get("error"):
        return {"words": "The managed book's plan for today is written; I could not reach today's opening prices just now."}
    pairs = "; ".join(f"{b.get('for_cut')} -> {b['symbol']}" for b in buys if b.get("for_cut"))
    skip, ok = [], []
    for b in buys:
        r = (q.get("rows") or {}).get(f"NSE:{b['symbol']}") or {}
        g = _pct(r.get("open"), r.get("prev_close"))
        if g is None:
            continue
        (skip if g > 2.0 else ok).append(f"{b['symbol']} opened {g:+.1f}%")
    return {"buys_opening": ok, "buys_skipped_by_rule": skip,
            "pairs": pairs,
            "words": (f"The managed book's plan for {clk['latest_session_words']}: {len(cuts)} cuts and {len(buys)} buys at the open, each buy replacing a cut ({pairs}). At today's opening prices "
                      + (f"these buys stay in ({'; '.join(ok)})" if ok else "no buy stays in")
                      + (f" and these are skipped by the 2% rule ({'; '.join(skip)})" if skip else "")
                      + f". The fills are booked from the official NSE day file by the evening run at {_sched_at('com.ananta.india.evening')}, so the book's result arrives then.")}


# 7 Nov 2026 (Ananta asked Madhav for it): the special sessions NSE has announced, by date, in plain words
MUHURAT = {"2026-11-08": "the special Muhurat session: pre-open 14:05, normal market 14:20 to 15:30 IST, 3:50 to 5:00 am Toronto; "
                         "Ananta's paper books and the options line trade regular sessions only, so it watches and records"}

def holidays_ahead(clk: dict, days: int = 45) -> dict:
    """Independent audit, 2 Nov: Ananta said "the facts hold no holiday calendar" although NSE's holiday master is on disk. The NSE cash-market
    holidays in the next weeks, from manifests/nse_holidays.json; an asterisk in NSE's text means a special (Muhurat) session is announced later."""
    for name in ("nse_holidays.json", "nse_holidays_2026.json"):
        try:
            d = json.loads((DATA / "manifests" / name).read_text())
            break
        except Exception:  # noqa: BLE001
            d = None
    if not d:
        return {"words": "The NSE holiday list could not be read."}
    start = dt.date.fromisoformat(clk["today_india"])
    rows = []
    for x in d.get("CM", []):
        try:
            day = dt.datetime.strptime(x["tradingDate"], "%d-%b-%Y").date()
        except (KeyError, ValueError):
            continue
        if start <= day <= start + dt.timedelta(days=days):
            desc = str(x.get("description") or "").strip()
            note = ((" (" + MUHURAT[day.isoformat()] + ")") if day.isoformat() in MUHURAT else
                    " (NSE will announce a special Muhurat trading session; the time comes in its circular)") if desc.endswith("*") else ""
            rows.append({"date": day.isoformat(), "what": desc.rstrip("*").strip(), "words": f"{_dw(day)}: {desc.rstrip('*').strip()}{note}"
                         + (" (a weekend anyway)" if day.weekday() >= 5 else "")})
    return {"rows": rows, "words": ("NSE holidays in the next weeks (cash market): " + "; ".join(r["words"] for r in rows) + ".") if rows
            else f"No NSE holiday in the next {days} days."}


PRACTICE_POLICY = "hold_20d"     # the one exit the read model shows per campaign (records india/readmodel.py REF_POLICY)


def practice_today(clk: dict, fetch=None, path: Path | None = None) -> dict:
    """Independent audit, 2 Nov: after the close Ananta could not say how the practice book did today, because the paper engine books the session
    only at 08:00 IST the next morning. This prices it with Kite now: the open trades by today's move, and the picks that were bought at today's
    open (every chosen signal fills at the open, fixed size) from the open to now. Paper only; the random control picks (CTL) are left out."""
    if clk["state"] in ("pre_open",):
        return {"words": None}
    try:
        st = json.loads((path or DATA / "paper" / "state.json").read_text())
    except Exception:  # noqa: BLE001
        return {"words": None}
    day = clk["latest_session"]
    trades = [t for t in (st.get("trades") or {}).values() if t.get("book") == "exec" and t.get("policy") == PRACTICE_POLICY
              and t.get("status") == "open" and t.get("campaign") != "CTL" and str(t.get("last_date") or "") < day]
    sizes = sorted(t.get("notional") or 0 for t in trades if t.get("notional"))
    size = sizes[len(sizes) // 2] if sizes else 50000.0
    picks = []
    for key, meta in sorted((st.get("decisions") or {}).items()):
        if meta.get("status") == "pending" and key < day:
            try:
                body = json.loads(((path.parent if path else DATA / "paper") / "decisions" / f"{key}.json").read_text())
            except Exception:  # noqa: BLE001
                continue
            picks += [{"symbol": s.get("symbol"), "campaign": s.get("campaign"), "decided_on": key} for s in body.get("signals") or [] if s.get("campaign") != "CTL"]
    if not trades and not picks:
        return {"words": None}
    q = quotes([f"NSE:{t['symbol']}" for t in trades if t.get("symbol")] + [f"NSE:{p['symbol']}" for p in picks if p.get("symbol")], fetch)
    if q.get("error"):
        return {"error": q["error"], "words": "I could not reach today's prices for the practice book just now."}
    rows = q.get("rows") or {}
    held_move = held_base = 0.0
    n_held = 0
    for t in trades:
        r = rows.get(f"NSE:{t.get('symbol')}") or {}
        if r.get("last") is None or not r.get("prev_close") or not t.get("entry_adj"):
            continue
        value = (t.get("notional") or size) * (t.get("last_close_adj") or t["entry_adj"]) / t["entry_adj"]
        held_move += value * (r["last"] / r["prev_close"] - 1)
        held_base += value
        n_held += 1
    new_move, filled = 0.0, []
    for p in picks:
        r = rows.get(f"NSE:{p.get('symbol')}") or {}
        if r.get("last") is None or not r.get("open"):
            continue
        mv = size * (r["last"] / r["open"] - 1)
        new_move += mv
        filled.append({**p, "open": r["open"], "last": r["last"], "move_inr": round(mv), "change_pct": _pct(r["last"], r["open"])})
    if not n_held and not filled:
        return {"words": None}
    filled.sort(key=lambda x: x["move_inr"])
    when = "so far today" if clk["state"] == "open" else ("today" if day == clk["today_india"] else f"on {clk['latest_session_words']}")
    total = held_move + new_move
    w = (f"The practice book (paper, Rs {size:,.0f} a trade) is {'up' if total >= 0 else 'down'} about Rs {abs(total):,.0f} {when} on Kite's prices: "
         f"its {n_held} open trades moved Rs {held_move:+,.0f} ({100 * held_move / held_base:+.2f}%)" if held_base else
         f"The practice book (paper, Rs {size:,.0f} a trade) is {'up' if total >= 0 else 'down'} about Rs {abs(total):,.0f} {when} on Kite's prices")
    if filled:
        uniq = list({x["symbol"]: x for x in filled}.values())          # one stock picked by two rules is one name here
        uniq.sort(key=lambda x: x["move_inr"])
        best = [f"{x['symbol']} {x['change_pct']:+.1f}%" for x in uniq[::-1][:2] if x["move_inr"] > 0]
        worst = [f"{x['symbol']} {x['change_pct']:+.1f}%" for x in uniq[:2] if x["move_inr"] < 0]
        w += (f"; the {len(filled)} picks bought at the open (decided on {_dw(dt.date.fromisoformat(filled[0]['decided_on']))}) are Rs {new_move:+,.0f} since the open"
              + (f", best {', '.join(best)}" if best else "") + (f", worst {', '.join(worst)}" if worst else ""))
    w += f". The engine books it officially at {_sched_at('com.ananta.india.paper')}; the random control picks are left out."
    return {"held": n_held, "held_move_inr": round(held_move), "picks_filled": filled, "picks_move_inr": round(new_move), "size_inr": size, "words": w}


def today(rm: dict | None = None, now: dt.datetime | None = None, fetch=None, positions: list | None = None, plan: dict | None = None) -> dict:
    """Everything above in one block, for the Ask's facts, the opening update and /v3/live."""
    if rm is None:
        from jarvis.india import views
        rm = views.readmodel()
    clk = clock(rm.get("data_through"), now)
    if positions is None or plan is None:
        try:
            from jarvis.india import surfaces
            # independent audit, 2 Nov: this read the twin's positions (view.json) but called them "your stocks"; the Money screen's "As you have
            # it" is the frozen holdings, so read those here and say which book it is
            positions = _frozen_positions() if positions is None else positions
            plan = (surfaces._managed().get("plan") or {}) if plan is None else plan
        except Exception:  # noqa: BLE001
            positions, plan = positions or [], plan or {}
    out = {"clock": clk, "data_timing": data_timing(clk), "index_now": index_now(clk, fetch), "options_today": options_today(clk, fetch),
           "holdings_today": holdings_today(clk, positions, fetch), "managed_today": managed_today(clk, plan, fetch),
           "practice_today": practice_today(clk, fetch), "holidays_ahead": holidays_ahead(clk)}
    try:                                    # 5 Nov 2026 (Madhav: yes): the 09:08 IST pre-open read, until an hour after the open
        from jarvis.india import preopen
        po = preopen.today(clk)
        if po:
            out["preopen"] = po
    except Exception:  # noqa: BLE001
        pass
    out["words"] = " ".join(x for x in (clk["words"], (out.get("preopen") or {}).get("words"), out["index_now"].get("words"), out["options_today"].get("words"),
                                        out["holdings_today"].get("words"), out["practice_today"].get("words"), out["managed_today"].get("words")) if x)
    out["how_to_say_it"] = ("This block is the truth about today. For any question about today, now, this morning, 'yesterday' (from Toronto) or "
                            "'the market', answer about clock.latest_session using index_now, options_today, holdings_today and managed_today. "
                            "Never say a session is open after 15:30 IST or not yet open after 09:15 IST; never say there is 'no record' of what the "
                            "options line decided when options_today lists decisions; never say you cannot see today's prices when index_now has rows. "
                            "Breadth, the research book and the reconstruction are on nightly_data_through: say that date when you use them. "
                            "'What did we do / what did you do' means all of Ananta's own books: the options line (options_today), the managed book "
                            "(managed_today: what it sold and what it bought in its place, and when its fills are booked) and the practice book; never "
                            "only one of them. A question about the managed book names its pairs (sold -> bought) and where each stands today. Before "
                            "the open, say how long until 09:15 IST.")
    return out



# ---- the answer guard (2 Nov 2026): every answer is checked against today's block before it is spoken -------------------------------------

SAYS_OPEN = re.compile(r"\b(?:session|market|trading)\s+(?:is|'s)\s+(?:still\s+)?(?:happening|going on|open|underway|in progress|live|running)\b"
                       r"|\b(?:is|are)\s+still\s+(?:open|trading|going on|happening)\b|\bhas(?:n't| not)\s+(?:closed|finished|ended)\b|\bno close yet\b"
                       r"|\bclose\s+(?:arrives|comes|lands)\b[^.]{0,40}\bafter 15:30\b|\bwhile the market (?:is|was) still open\b(?![^.]{0,40}\bearlier\b)", re.I)
SAYS_NOT_OPENED = re.compile(r"\b(?:has(?:n't| not)|did(?:n't| not))\s+(?:opened|started)\b|\bnot (?:yet )?open(?:ed)?\b", re.I)
SAYS_OPEN_BEFORE = re.compile(r"\b(?:market|session)\s+is\s+(?:open|trading)\b|\bhas opened\b|\bso far today\b", re.I)
SAYS_NO_RECORD = re.compile(r"\bno record of what\b|\b(?:don't|do not|haven't|have not)\s+(?:got |have )?(?:a |any )?record of (?:what|the options)"
                            r"|\bno record of (?:either|the options line|its decision)|\b(?:can't|cannot) tell (?:you )?what the options line", re.I)
# 2 Nov (Madhav-style round): "nothing intraday" / "daily closing data" are true of the studies and the indicator panel, so they are not claims
# about today's prices; only a claim that today's or the live session's prices cannot be seen is caught
SAYS_NO_PRICES = re.compile(r"\b(?:can't|cannot|can not|don't|do not|unable to)\s+(?:see|have|get|access|tell you)\s+(?:the\s+)?(?:any\s+)?(?:live|today's|current|real-time)\s+"
                            r"(?:prices?|market|session|numbers?|feed|level)|\b(?:can't|cannot)\s+see\s+where\s+the\s+(?:nifty|market|index)\b"
                            r"|\bno live (?:prices|feed)\b|\b(?:session|market) is invisible\b|\bno (?:monday|tuesday|wednesday|thursday|friday|today's) prices\b"
                            r"|\b(?:can't|cannot) tell you how (?:monday|tuesday|wednesday|thursday|friday|today)'?s? market went\b", re.I)
TODAY_Q = re.compile(r"\b(?:today|now|right now|yesterday|this morning|tonight|what happened|how did (?:the )?market|market (?:today|now)|how is (?:it|the market) going)\b", re.I)
# Words that put an answer in today's session even when it names an older day as the base ("+1.2% on Friday's close, as of 11:30 IST").
TODAY_MARK = re.compile(r"\b(?:right now|this (?:morning|afternoon|session)|as of \d{1,2}:\d{2}|at \d{1,2}:\d{2}\s*ist)\b", re.I)
WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


def check(answer: str, live: dict | None, question: str = "") -> list[str]:
    """What the answer says that today's block contradicts. Empty = fine."""
    if not answer or not isinstance(live, dict) or "clock" not in live:
        return []
    clk, out = live["clock"], []
    state = clk.get("state")
    if state == "closed" and SAYS_OPEN.search(answer):
        out.append(f"It said the session is still going, but {clk['words']}")
    if state == "open" and SAYS_NOT_OPENED.search(answer):
        out.append(f"It said the session has not opened, but {clk['words']}")
    if state in ("before_open", "pre_open", "no_session") and SAYS_OPEN_BEFORE.search(answer):
        out.append(f"It spoke as if a session were trading, but {clk['words']}")
    if (live.get("options_today") or {}).get("decisions") and SAYS_NO_RECORD.search(answer):
        out.append("It said it has no record of the options line's decisions, but options_today lists them: " + live["options_today"]["words"])
    if ((live.get("index_now") or {}).get("rows")) and SAYS_NO_PRICES.search(answer):
        out.append("It said it cannot see today's prices, but index_now has them: " + live["index_now"]["words"])
    # independent audit, 2 Nov: this check slept from IST midnight to the open (13:30-22:45 Toronto in winter), when Madhav mostly talks and his
    # "today" still means the session India just finished; it now also runs then
    try:
        tor_day_is_latest = dt.datetime.fromtimestamp(clk["ts"], TOR).date().isoformat() == clk.get("latest_session")
    except Exception:  # noqa: BLE001
        tor_day_is_latest = False
    today_is_latest = ((clk.get("latest_session") == clk.get("today_india") and state in ("open", "closed"))
                       or (state in ("before_open", "pre_open", "no_session") and tor_day_is_latest))
    if question and TODAY_Q.search(question) and today_is_latest:
        latest_wd = clk.get("latest_session_words", "").split(" ")[0].lower()
        low = answer.lower()
        try:                                       # only the sessions BEFORE today count as "an older session" ("tomorrow, Tuesday" is fine)
            lt = dt.date.fromisoformat(clk["latest_session"])
            before = {(lt - dt.timedelta(days=k)).strftime("%A").lower() for k in range(1, 5)} - {latest_wd}
        except Exception:  # noqa: BLE001
            before = set(WEEKDAYS) - {latest_wd}
        older = [w for w in WEEKDAYS if w in before and re.search(rf"\b{w}\b", low)]
        # "+1.2% on Friday's close, live as of 11:30 IST" IS about today: Friday is only the base (moment harness, 2 Nov)
        try:
            day_tag = re.search(rf"\b{lt.day}\s+{lt.strftime('%b').lower()}", low)
        except Exception:  # noqa: BLE001
            day_tag = None
        if older and latest_wd not in low and "today" not in low and not TODAY_MARK.search(low) and not day_tag:
            out.append(f"He asked about today; it answered about {older[0].title()} and never about today, {clk['latest_session_words']}.")
    return out


def correction_note(problems: list[str], live: dict) -> str:
    return ("CORRECTION (your draft answer was wrong and was not shown): " + " ".join(problems)
            + " Answer the question again from FACTS.today_live first. Today's block in short: " + str(live.get("words") or "")[:1500])


def scrub(answer: str, live: dict) -> str:
    """Last resort when a re-answer is still wrong: drop the sentences that contradict today and put the right fact in their place, only the
    fact that was contradicted (2 Nov round: a whole status block in front of a good answer read as a data dump)."""
    sents = re.split(r"(?<=[.!?])\s+", str(answer or ""))
    pats = {"clock": (SAYS_OPEN, SAYS_NOT_OPENED, SAYS_OPEN_BEFORE), "options": (SAYS_NO_RECORD,), "index": (SAYS_NO_PRICES,)}
    hit, keep = set(), []
    for s in sents:
        which = [k for k, ps in pats.items() if any(p.search(s) for p in ps)]
        hit.update(which)
        if not which:
            keep.append(s)
    if not hit:
        return str(answer or "")
    lead = []
    if "clock" in hit:
        lead.append((live.get("clock") or {}).get("words"))
    if "index" in hit:
        lead.append((live.get("index_now") or {}).get("words"))
    if "options" in hit:
        lead.append((live.get("options_today") or {}).get("words"))
    return (" ".join(x for x in lead if x) + " " + " ".join(keep)).strip()
