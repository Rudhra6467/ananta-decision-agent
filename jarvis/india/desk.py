"""The trader's desk for the India Ask (3 Nov 2026: Madhav's chat at 08:46-09:01 Toronto, graded by an outside trader).

The Ask answered his session questions like a scheduler, not a trader: no previous high and low, no gap scenarios, no option-interest
levels, no "why did MARICO jump 10%" (its results came out the evening before, in data Ananta has), no stocks to watch, and "we have no
announcement dates" about data it fetches every evening. This block gives the model those facts, each from its one owner:

  feeds          each source's last day and fetch time (records india/desk.py)            "I restarted things, check the link"
  prep           the next session's levels, option-interest walls, expected move, expiries, holidays, results ahead, events
  moves          why each holding (and any stock he names) moved: its latest filings, or "no filing found"
  radar          names worth a look before Ananta's own picks at 08:00 IST (holdings with news or results, the day's biggest liquid moves)
  data_we_have   what data Ananta has, its years and size, and where it is thin (never "no X" when X is on file but partly parsed)
  basics         Indian-market facts every trader assumes (expiry days, pre-open, option-buyer arithmetic), labelled general knowledge

Read-only; the records repo writes manifests/desk.json, the read model, the option-chain summary and the quote book.
"""
from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

from jarvis.india import views

# General market knowledge (hand-written 3 Nov 2026, checked against NSE's circulars as Ananta knows them; not Ananta's own tests)
BASICS = {
    "expiries": ("Nifty's weekly options expire on Tuesday (since September 2025); when that Tuesday is a holiday they expire the trading day "
                 "before. Bank Nifty has monthly options only (its weeklies ended in November 2024), expiring on the last Tuesday of the month, "
                 "or the day before when that is a holiday. The options line buys the nearest expiry AFTER the day it trades, never the one "
                 "expiring that day."),
    "session": ("Pre-open 09:00-09:08 IST takes orders and finds the opening price (index options do not trade in pre-open); normal trading "
                "09:15-15:30 IST. In Toronto winter time that is 10:30 pm to 5:00 am; the options line's window 09:15-10:15 IST is 10:45 to "
                "11:45 pm Toronto in winter (trader_desk.ist_in_toronto has the day's own times)."),
    "momentum_vs_rsi": ("RSI(14) measures a short-term stretch over about three weeks; momentum in the trader's sense is months-long "
                        "strength (3-12 months, often against the index). Ananta's breakout rule (a one-month high on volume) and the managed "
                        "book's filters (above the 50- and 200-day averages) are trend and momentum rules; RSI over 70 is used only as a "
                        "do-not-chase filter. The relative-strength study RS1 came close to the strict bar, so a 20-session paper trial "
                        "of it runs now (rs_trial); nothing trades from it."),
    "option_buyer": ("A bought option is worth its intrinsic value plus time value; the time value melts every day (fastest in the last week) "
                     "and is higher when implied volatility is high (event days). A buyer needs the move to beat that melt plus costs "
                     "(brokerage, the spread, STT on the sale). Near-the-money options move about half as much as the index (delta near "
                     "0.5). Trend days pay buyers; range days, where the index chops inside the first hour's range, bleed them. On most "
                     "days the right decision for a buyer is no trade, which is what the options line does when no predicted move clears its bar."),
    "words": ("Say India VIX, not 'the fear gauge'. Say full company names (Marico, National Aluminium, Petronet LNG), not tickers. On the cut "
              "list say 'trim', 'halve' and 'a tiny stake to tidy up' in words, not TRIM / REDUCE / TIDY. The F&O ban stops new futures and options "
              "positions in that stock; its shares trade normally. A gap up helps a bought call and a gap down hurts it. The expected move for "
              "Bank Nifty from India VIX is an approximation (India VIX is built from Nifty options)."),
    "expected_move": ("A rule of thumb: India VIX divided by 16 is roughly the index's expected move in percent for one day (VIX 16 means "
                      "about 1% a day), up or down; it is a size, not a direction."),
    "oi_walls": ("The strike with the most call open interest is often read as resistance and the most put open interest as support; "
                 "Ananta's study F03 found the put-call ratio's extremes and the max-pain pin had no edge, so they are context, never a signal."),
    "routine": ("Before the open Ananta reads, in this order: the US close of the night (a day old) and VIX; the institutions' flows and "
                "their futures positions; results and filings for its names and his holdings; "
                "holidays and expiry days; the F&O ban list. At 09:15 it reads the gap against the previous close; at 09:15, 09:30, 09:45 and "
                "10:15 IST the options line decides from the move so far against the option's cost; the first 15-30 minutes' range tells a "
                "trend day from a range day. It has no live Asian feed; since 9 Nov it reads GIFT Nifty (the Nifty future that trades overnight) for the "
                "indicated gap in the 08:30 view, and since 5 Nov NSE's pre-open prices at 09:09 IST, a minute after the pre-open closes at 09:08 (the two "
                "indexes and ten heavy stocks), sent to the phone with what changed since the view and the options line's plan for that open. Say the Toronto "
                "times too (trader_desk.prep.toronto_times)."),
    "gaps": ("A gap above the previous high: wait for the first 15-30 minutes to see if it holds (gap-and-go) or fills; flat open: the first "
             "range decides; a gap below the previous low: the same, the other way. The options line reads the gap at 09:15 and decides at "
             "09:15, 09:30, 09:45 or 10:15."),
}

# The dated events ahead (9 Nov 2026; Madhav: "yes, lets complete", the outsider readiness review's fix 4: one calendar). A hand-kept list
# lived here for the voice alone, while the morning view and the options line's event flag read the event registry, which had no row after
# 7 Oct 2026 (so no RBI decision of 4 Dec). The one owner is now the records repo's india/registrations/calendar_ahead.json, built into
# manifests/calendar.json (india/calendar_ahead.py) with each row's first Indian session worked out by code; the voice reads that file.
def calendar_events(n: int = 6) -> list[dict]:
    try:
        d = json.loads((views.DATA / "manifests" / "calendar.json").read_text())
    except (OSError, ValueError):
        return []
    since = (dt.date.today() - dt.timedelta(days=1)).isoformat()
    return [{"date": e.get("date"), "what": e.get("what"), "time_ist": e.get("time_ist"), "first_session": e.get("first_session_words"),
             "options_line_event_day": e.get("options_line_event_day"), "words": e.get("words"), "source": e.get("source")}
            for e in d.get("events") or [] if str(e.get("date") or "") >= since][:n]


def _json(p: Path, default=None):
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return default


def load() -> dict:
    return _json(views.DATA / "manifests" / "desk.json", {}) or {}


def _names() -> dict:
    """symbol -> name, from the quote book (to find 'Marico' in his words)."""
    q = _json(views.DATA / "manifests" / "quotebook.json", {}) or {}
    return {s: str(x.get("name") or "") for s, x in (q.get("quotes") or {}).items()}


STOP = {"THE", "AND", "FOR", "YOU", "ITS", "WHY", "WHAT", "HOW", "ANY", "NOW", "TODAY", "NIFTY", "BANK", "INDIA", "OPTIONS", "OPTION", "STOCK",
        "STOCKS", "MARKET", "SIR", "OKAY", "ANANTA", "CALL", "PUT", "HIGH", "LOW", "GOOD", "BEST", "VIX", "FII", "DII", "RSI", "PE", "EPS", "IT"}


def symbols_in(text: str, known: set, names: dict | None = None) -> list[str]:
    """Stock symbols he names: an exact symbol ("MARICO", "marico") or the first word of a company's name ("Tata Power" -> TATAPOWER)."""
    out = []
    words = re.findall(r"[A-Za-z][A-Za-z&-]{2,}", text or "")
    up = [w.upper() for w in words]
    for w in up:
        if w in known and w not in STOP and w not in out:
            out.append(w)
    if names:
        joined = " ".join(up)
        for sym, nm in names.items():
            first = " ".join(nm.upper().split()[:2]).replace(" LIMITED", "").replace(" LTD", "")
            if len(first) >= 6 and re.search(rf"\b{re.escape(first)}\b", joined) and sym not in out:
                out.append(sym)
    return out[:4]


def _news_words(items: list) -> str:
    """The filing that explains a move: the latest results filing if one came in the last few days, else the newest filing."""
    if not items:
        return "no company filing found in the fetched days"
    newest = items[0]["at"][:10]
    x = next((i for i in items if i.get("kind") == "results" and i["at"][:10] >= (dt.date.fromisoformat(newest) - dt.timedelta(days=3)).isoformat()), items[0]) \
        if re.match(r"\d{4}-\d\d-\d\d", newest) else items[0]
    return f"{x['at']} IST, {x['what']}: {x['text'][:170]}"


def moves(desk: dict, holdings_today: dict, named: list[str], nifty_pct: float | None = None) -> dict:
    news = desk.get("news") or {}
    rows = []
    for h in (holdings_today or {}).get("rows") or []:
        if abs(h.get("change_pct") or 0) >= 3:
            sym = str(h.get("symbol")).upper()
            rows.append({"symbol": sym, "change_pct": h.get("change_pct"), "held": True, "latest_filings": news.get(sym, [])[:3], "why": _news_words(news.get(sym, []))})
    for sym in named:
        if not any(r["symbol"] == sym for r in rows):
            rows.append({"symbol": sym, "held": False, "latest_filings": news.get(sym, [])[:3], "why": _news_words(news.get(sym, []))})
    hv = holdings_today or {}
    return {"news_days_fetched": desk.get("news_days"), "rows": rows,
            "holdings_vs_nifty": ({"holdings_pct": hv.get("move_pct"), "holdings_inr": hv.get("move_inr"), "nifty_pct": nifty_pct,
                                   "words": (f"your holdings {hv.get('move_pct'):+.1f}% against the Nifty {nifty_pct:+.1f}%"
                                             + (" (they lagged)" if hv.get("move_pct") < nifty_pct else " (they kept up)"))}
                                  if hv.get("move_pct") is not None and nifty_pct is not None else None),
            "rule": ("a move is explained only by a filing on file, with its time; results published after one close move the next session; "
                     "with no filing, say 'no company filing found up to <last fetched day>' and name the sector or the market move instead"),
            "index_move_note": ("for the index's own move there is no filing; the day's FII/DII figures come with the evening run and breadth and "
                                "sector moves with NSE's day file in the nightly build (times in schedule words), so before those say they are not in yet")}


def expiry_words(day: str | None, hol: dict) -> dict | None:
    """'Monday 9 Nov (moved from Tuesday 10 Nov, a holiday: Diwali-Balipratipada)': the weekday said, and why when it is not a Tuesday."""
    if not day:
        return None
    d = dt.date.fromisoformat(day)
    w = {"date": day, "words": f"{d:%A} {d.day} {d:%b}"}
    if d.weekday() != 1:
        nxt = next((d + dt.timedelta(days=k) for k in range(1, 7) if (d + dt.timedelta(days=k)).weekday() == 1), None)
        if nxt and nxt.isoformat() in hol:
            w["words"] += f" (moved from Tuesday {nxt.day} {nxt:%b}, a holiday: {hol[nxt.isoformat()]})"
    return w


OPTIONS_RULE = ("The options line's frozen rule (SP1 v2, 19 Oct): at 09:15, 09:30, 09:45 and 10:15 IST, for each index that has no trade yet, "
                "its model (fitted on earlier years) predicts how far each possible trade would move from the situation of the moment (the gap, "
                "the trend, India VIX, the US close, the first minutes' move, breadth). It takes the best trade only if that predicted move, after "
                "costs of about 6 basis points of the index (about 14 Nifty points, 33 Bank Nifty points), is above zero and above c times its "
                "own uncertainty (c is 2.5 for Nifty and 0.5 for Bank Nifty, so Bank Nifty's margin is five times looser); otherwise it waits, and nothing by 10:15 means no trade. At most "
                "one trade per index per day, so a Nifty and a Bank Nifty trade on one day is the rule, not a break. It does not look at the "
                "option's own price or implied volatility when it decides; the one-lot option is how the decision is booked on paper.")


def sp1_reasons(tl: dict) -> list[dict]:
    """Why each of today's trades was taken, in the rule's own numbers (the predicted move and the bar it cleared, in index points)."""
    rows = []
    try:
        led = [json.loads(x) for x in (views.DATA / "paper" / "sp1" / "decisions.jsonl").read_text().splitlines() if x.strip()]
    except (OSError, ValueError):
        return rows
    day = ((tl.get("options_today") or {}).get("day")) or (led[-1].get("date") if led else None)
    for r in led:
        if r.get("kind") != "decision" or r.get("date") != day:
            continue
        ch, lvl = r.get("choice"), r.get("entry_estimate") or 0
        pts = lambda bp: round((bp or 0) * lvl / 10000) if lvl else None  # noqa: E731
        if ch:
            rows.append({"index": r.get("index"), "at": str(r.get("decided_at") or "")[11:16], "took": True, "exit": ch.get("exit"),
                         "predicted_move_pts": pts(ch.get("pred_gross")), "cost_pts": pts(ch.get("pcost")), "net_pts": pts(ch.get("pred_net")),
                         "bar_pts": pts((r.get("c") or 0) * (ch.get("se") or 0)), "c": r.get("c")})
        else:
            best = max((c for c in r.get("candidates") or []), key=lambda c: c.get("pred_net") or -1e9, default=None)
            rows.append({"index": r.get("index"), "at": str(r.get("decided_at") or "")[11:16], "took": False,
                         "best_net_pts": pts(best.get("pred_net")) if best else None, "bar_pts": pts((r.get("c") or 0) * (best.get("se") or 0)) if best else None})
    return rows


def scorecard(f: dict, mv: dict) -> dict:
    """'How are we doing', in one place: the daily call against a coin flip, the options line's paper result per index, holdings vs the Nifty."""
    dc = f.get("daily_call") or {}
    try:
        book = (views.sp1_live(views.readmodel()).get("book") or {})
    except Exception:  # noqa: BLE001
        book = {}
    per = {k: {"sessions": v.get("sessions"), "trades": v.get("trades"), "result_inr_one_lot": v.get("option_1lot_rs_realistic_fill")}
           for k, v in (book.get("by_index") or {}).items()}
    return {"daily_call": {"right": dc.get("hits"), "of": dc.get("scored"), "coin_flip": dc.get("null_hits"), "below_coin_flip": dc.get("below_coin_flip")},
            "options_line": {"sessions": book.get("sessions"), "of_needed": 20, "per_index": per,
                             "note": "paper, one lot, realistic fills, scored trades only (the open trades are marked separately)"},
            "holdings_vs_nifty": mv.get("holdings_vs_nifty")}


def ist_in_toronto(on: dt.date | None = None) -> dict:
    """IST clock times Ananta says, with the Toronto time beside each (worked out here, never by the model)."""
    from zoneinfo import ZoneInfo
    ist, tor = ZoneInfo("Asia/Kolkata"), ZoneInfo("America/Toronto")
    on = on or dt.date.today() + dt.timedelta(days=1)
    out = {}
    for hhmm in ("06:05", "06:30", "06:50", "07:05", "07:30", "08:00", "08:30", "09:00", "09:15", "09:30", "09:45", "10:15", "10:20", "15:30", "15:50", "22:15", "23:15"):
        h, m = map(int, hhmm.split(":"))
        t = dt.datetime.combine(on, dt.time(h, m), ist).astimezone(tor)
        out[f"{hhmm} IST"] = t.strftime("%-I:%M %p").lower() + " Toronto" + ("" if t.date() == on else " (the evening before)")
    return out


def toronto_times(on: dt.date | None = None) -> dict:
    """The Indian session in Toronto time for the date (winter or summer time)."""
    from zoneinfo import ZoneInfo
    ist, tor = ZoneInfo("Asia/Kolkata"), ZoneInfo("America/Toronto")
    on = on or dt.date.today() + dt.timedelta(days=1)
    t = lambda hh, mm: dt.datetime.combine(on, dt.time(hh, mm), ist).astimezone(tor).strftime("%-I:%M %p").lower()  # noqa: E731
    return {"pre_open": f"09:00 IST = {t(9, 0)} Toronto", "open": f"09:15 IST = {t(9, 15)} Toronto",
            "options_line_window": f"09:15-10:15 IST = {t(9, 15)} to {t(10, 15)} Toronto", "close": f"15:30 IST = {t(15, 30)} Toronto",
            "note": "the Indian session is overnight in Toronto; Toronto times are the evening before the Indian date until midnight"}


def prep(f: dict, desk: dict) -> dict:
    tl = f.get("today_live") or {}
    idx = (tl.get("index_now") or {}).get("rows") or {}
    chain = _json(views.DATA / "manifests" / "premarket_chain.json", {}) or {}
    ban = _json(views.DATA / "manifests" / "fo_ban.json", {}) or {}
    vix = (idx.get("INDIA VIX") or {}).get("last")
    out = {"as_of": (tl.get("index_now") or {}).get("as_of"), "indices": {}}
    for name, key in (("NIFTY 50", "NIFTY"), ("NIFTY BANK", "BANKNIFTY")):
        r = idx.get(name) or {}
        c = (chain.get("indices") or {}).get(key) or {}
        last = r.get("last")
        out["indices"][name] = {
            "previous_session": {"open": r.get("open"), "high": r.get("high"), "low": r.get("low"), "close": last, "change_pct": r.get("change_pct")},
            "expected_move_points": round(last * vix / 16 / 100) if last and vix else None,
            "option_interest": ({"of_session": chain.get("day"), "nearest_expiry": c.get("nearest_expiry"), "call_walls": [w["strike"] for w in c.get("call_walls", [])],
                                 "put_walls": [w["strike"] for w in c.get("put_walls", [])], "pcr": c.get("pcr_oi"), "max_pain": c.get("max_pain"),
                                 "note": "end of the session named; today's open interest arrives with the evening F&O file and is in the 08:30 IST morning view"}
                                if c else None)}
    opt = (tl.get("options_today") or {}).get("taken") or []
    out["options_line_rule"] = OPTIONS_RULE
    out["options_line_today"] = sp1_reasons(tl)
    out["open_option_trades"] = [{"index": t.get("index"), "contract": t.get("option"), "expiry": t.get("expiry"), "lot": t.get("lot"),
                                  "bought_at": t.get("option_price_at_decision"), "now": t.get("option_price_now"), "paper_move_inr_per_lot": t.get("paper_move_inr_per_lot"),
                                  "premium_paid_inr_per_lot": round(t["option_price_at_decision"] * t["lot"]) if t.get("option_price_at_decision") and t.get("lot") else None,
                                  "max_loss": "the premium paid (premium_paid_inr_per_lot): quote that number, never work it out again",
                                  "index_since_entry_pts": t.get("index_since_entry_pts"),
                                  "state": ("open, marked at Zerodha's last price after the close, not a result; it closes at the next session's open. "
                                            "Option prices after the close are noisy (a lot can swing a few hundred rupees in the last minute), and a "
                                            "bought call can be down while the index is up when implied volatility and time value fall through the day")}
                                 for t in opt if t.get("exit") == "NEXTOPEN"]
    hol = {h.get("date"): h.get("what") for h in ((tl.get("holidays_ahead") or {}).get("rows") or [])}
    out["expiries"] = {"nifty_next_weekly": expiry_words(next((t.get("expiry") for t in opt if t.get("index") == "NIFTY"), None), hol),
                       "banknifty_monthly": expiry_words(next((t.get("expiry") for t in opt if t.get("index") == "BANKNIFTY"), None), hol),
                       "source": "the options line's own contracts (the nearest expiry after the day it traded)", "rule": BASICS["expiries"]}
    out["holidays_ahead"] = [h.get("words") for h in ((tl.get("holidays_ahead") or {}).get("rows") or [])[:3]]
    out["results_ahead"] = {"by_session": desk.get("results_ahead"), "note": desk.get("results_ahead_note")}
    out["fo_ban"] = ban.get("words")
    today = dt.date.today().isoformat()
    # 5 Nov (C): the next six dated events (macro releases, central banks, the budget), each with its source; 9 Nov: from the one calendar
    out["events"] = calendar_events(6)
    out["events_how"] = ("these are the dated events Ananta keeps from each owner's published schedule (one calendar: the same rows the morning view "
                         "and the options line read); say the event, its day and time in India and the first Indian session that can trade it. Only "
                         "an official RBI decision, Budget or election-counting day is an event day for the options line (options_line_event_day); "
                         "no other Ananta rule trades on events")
    out["toronto_times"] = toronto_times()
    us = next((x for x in desk.get("feeds") or [] if x.get("feed", "").startswith("US close")), {})
    out["overnight_cues"] = (f"the US close on file is for {us.get('last_day') or 'an earlier day'} (fetched {str(us.get('fetched_at') or '')[:16]} UTC); there "
                             "is no live Asian feed; from 9 Nov the overnight read is GIFT Nifty, the Nifty future that trades through the night, read against its own level at the "
                             "last NSE close (today_live.gift; in the 08:30 IST morning view); from 5 Nov the first Indian prices of the day are the pre-open read at 09:09 IST, a minute after "
                             "NSE's pre-open closes at 09:08 (today_live.preopen, the two indexes and ten heavy stocks, sent to the phone with what changed since the view); "
                             "crude, the dollar and the rupee readings lag several days")
    out["how_to_use"] = ("say tomorrow's plan as scenarios, not orders: the previous high, low and close; what a gap up, flat or gap down open would "
                         "mean (BASICS gaps); the expected move from VIX; the open option trades with "
                         "contract, expiry and that they are marked, not closed; the expiries, holidays, results ahead and events; then what the "
                         "options line itself will do. Moving averages are one level among these, not the plan.")
    out["today"] = today
    return out


def radar(desk: dict, mv: dict) -> dict:
    """Names worth a look before Ananta's own picks (08:00 IST): not picks, not advice."""
    rows = [{"symbol": r["symbol"], "why": f"your holding moved {r['change_pct']:+.1f}% today; {r['why']}"} for r in mv["rows"] if r.get("held")]
    held = {r["symbol"] for r in rows}
    for d, syms in (desk.get("results_ahead") or {}).items():
        for s in syms[:4]:
            if s not in held:
                rows.append({"symbol": s, "why": f"results board meeting on {d}"})
    m = desk.get("movers") or {}
    for side in ("up", "down"):
        for r in (m.get(side) or [])[:3]:
            rows.append({"symbol": r["symbol"], "why": f"{r['chg_1d_pct']:+.1f}% on {m.get('as_of')} among liquid stocks; {r['why'][:140]}"})
    return {"rows": rows[:10], "note": ("names to look at, not picks: Ananta's practice picks for the session are written at 08:00 IST by its rules; "
                                        "this list is holdings with news, results meetings ahead and the biggest liquid moves of the last quote book")}


def data_we_have(desk: dict) -> dict:
    inv = desk.get("inventory") or {}
    rows = {r["id"]: r for r in inv.get("tracker_rows") or []}
    def note(i):
        r = rows.get(i) or {}
        return f"{r.get('item')}: {r.get('state')}; {r.get('note')}" if r else None
    audit = _json(views.DATA / "manifests" / "data_audit.json", {}) or {}
    res = ((audit.get("results") or {}).get("by_year")) or {}
    # a year counts when it has a real number of filings (2017 holds 12 late filers) and most carry EPS
    parsed = [y for y, v in sorted(res.items(), key=lambda kv: int(kv[0])) if (v.get("filings") or 0) >= 500 and (v.get("with_eps") or 0) > 0.5 * v["filings"]]
    return {"source": "records india/desk.py inventory and india/dataaudit.py (manifests/data_audit.json, registrations/data_audit_v1.md)",
            "audit": {"built_at": audit.get("built_at"), "findings": [f"{x['area']}: {x['finding']} So: {x['so']}" for x in audit.get("findings") or []],
                      "widen_first": audit.get("widen_first"), "flag": "flag 63 (Madhav, 3 Nov: the data-set audit first)"} if audit else None,
            "results_parsed_years": parsed,
            "have": {
                "every stock's daily price and volume": "NSE cash day file 1994 onward (research to 2023; 2024 onward sealed, live days read for the paper books)",
                "delivery share": "2003 onward",
                "futures and options with open interest": "NSE F&O day files 2000 onward, option greeks and implied volatility from settlement prices 2001 onward",
                "index prices": "53 indices daily from 2003; 8 indices in 1- and 5-minute bars from 2015; India VIX",
                "intraday stock bars (5-minute)": (f"2015 onward, about {inv['intraday_stocks'].get('symbols')} stocks in {inv['intraday_stocks'].get('latest_year')} "
                                                   f"({round(100 * (inv['intraday_stocks'].get('top250_covered') or 0))}% of the 250 most traded that year)") if inv.get("intraday_stocks") else "2015 onward",
                "company announcements": (f"{(inv.get('announcements') or {}).get('research_rows'):,} company announcements 2010-2023 in the research set "
                                          "(results, board meetings, dividends, orders, ratings, deals, management), plus NSE's daily file of about 8.7 million rows "
                                          "that also holds price-band hits and book closures, plus the live announcements feed every evening"
                                          if (inv.get("announcements") or {}).get("research_rows") else "from 2010, plus the live feed"),
                "company results": note("D20") or "a results index of filings 2007 onward; parsing into revenue and EPS is partly done",
                "institutions' flows": "FII/FPI equity and debt daily from 2000; DII from NSE daily; participant-wise futures and options positions from 2012",
                "index valuation": "Nifty 50, Nifty Bank and Nifty 500 P/E, P/B and dividend yield from 1999",
                "sector map, IPOs, corporate actions, F&O ban list, bulk and block deals (forward from 23 Oct 2026)": "yes",
                "live": "Zerodha read-only quotes in the session, the 1-minute options recorder since 18 Oct 2026, option bid-ask depth samples"},
            "thin_or_missing": [
                (f"company results: revenue and EPS are read for {parsed[0]}-{parsed[-1]}; before 2018 the filings are HTML pages, not read yet; "
                 "no analyst estimates, so no 'beat or miss'" if parsed else
                 "company results: filed and indexed, but revenue and EPS are parsed for only part of the companies, so per-stock P/E history is not a "
                 "ready series yet; no analyst estimates, so no 'beat or miss'"),
                "competitors: only the sector map; no peer financial comparison",
                ("NSE's board-meetings calendar: fetched every night for the next 60 days, with history from 2010"
                 if str(desk.get("results_ahead_note") or "").startswith("NSE's board-meetings calendar (fetched") else
                 "NSE's board-meetings calendar is not fetched, so results dates ahead come only from filings that name them"),
                "live Asian markets: no free feed (GIFT Nifty is read since 9 Nov, through Zerodha); the US close is a day old and crude, dollar and rupee lag several days",
                "bulk and block deals: no history before 23 Oct 2026",
                "most research uses the 250 most traded stocks of each day (chosen on that day, so delisted names are included), not the whole market",
                "2024 onward is sealed for the one confirmatory test of each idea"],
            "rule": ("answer 'do we have X' from 'have' and 'thin_or_missing': say what is on file, its years and how complete it is; never say "
                     "'no X' when X is on file but partly parsed or not yet used by a rule; results carry revenue and EPS only for results_parsed_years; "
                     "for 'how good is our data' lead with audit.findings and audit.widen_first (the data-set audit, flag 63); quote these numbers and years exactly, the same in every "
                     "answer (daily prices from 1994, F&O from 2000, indices from 2003, intraday stock bars from 2015, announcements as written here)")}


DATA_TOPIC = re.compile(r"\b(data ?sets?|data|research|results|fundamental\w*|earnings|p/?e|eps|announce\w*|filings?|competitors?|inventory|have we got|do we have)\b", re.I)
BASICS_TOPIC = re.compile(r"\b(indicators?|momentum|rsi|macd|signal|buy|option\w*|expir\w*|premium|vix|volume|trend|gap|open(?:ing)?|pre-?open|strategy|decay|"
                          r"before the market|market starts|plan|ready|routine|watch|levels?|tomorrow|next session)\b", re.I)


def block(f: dict, text: str = "") -> dict:
    """The desk's facts for one turn (the data list and the basics only when the question or the last turns touch them)."""
    desk = load()
    names = _names()
    known = set(desk.get("news") or {}) | set(names)
    named = symbols_in(text, known, names)
    tl = f.get("today_live") or {}
    nifty = (((tl.get("index_now") or {}).get("rows") or {}).get("NIFTY 50") or {}).get("change_pct")
    mv = moves(desk, tl.get("holdings_today") or {}, named, nifty)
    out = {"built_at": desk.get("built_at"), "feeds": desk.get("feeds"), "prep": prep(f, desk), "moves": mv, "radar": radar(desk, mv), "named_symbols": named,
           "scorecard": scorecard(f, mv), "ist_in_toronto": ist_in_toronto()}
    hn = desk.get("holdings_news") or {}            # 9 Nov 2026: what each holding filed since the last close (weekends included), one line each
    if hn.get("lines"):
        out["holdings_news"] = {"since": hn.get("since"), "lines": hn.get("lines"), "note": hn.get("note"),
                                "how_to_say_it": "for 'any news on my stocks': these lines, with full company names; what was filed and when, never the figures inside a filing"}
    if DATA_TOPIC.search(text or ""):
        out["data_we_have"] = data_we_have(desk)
    if BASICS_TOPIC.search(text or ""):
        out["basics"] = BASICS
    return out
