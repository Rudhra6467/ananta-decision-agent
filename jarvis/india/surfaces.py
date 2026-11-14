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
import time
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
        x = dt.date.fromisoformat(str(d)[:10])
        return x.strftime("%a %-d %b") + (f" {x.year}" if x.year != dt.date.today().year else "")
    except (TypeError, ValueError):
        return str(d or "")


def _inr(v: float) -> str:
    """Indian grouping: ₹1,60,622."""
    n = str(int(round(v)))
    head, tail = n[:-3], n[-3:]
    while len(head) > 2:
        tail = head[-2:] + "," + tail
        head = head[:-2]
    return "₹" + (head + "," if head else "") + tail


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


def _nifty_tile(rm: dict) -> dict:
    """The Nifty box on Today (2 Nov fact map: it showed the nightly close, Friday's, while the voice said Monday's): Kite's price for the latest
    session when it is readable (live in the session, the close after it), else the nightly close."""
    try:
        from jarvis.india import livesession
        clk = livesession.clock(rm.get("data_through"))
        n = (livesession.index_now(clk).get("rows") or {}).get("NIFTY 50") or {}
        if n.get("last") is not None:
            ch = n.get("change_pct")
            when = "live" if clk["state"] == "open" else "close"
            return {"label": f"Nifty · {_dw(clk['latest_session'])} {when}", "value": f"{n['last']:,.0f}",
                    "sub": (f"{'+' if ch >= 0 else ''}{ch:.1f}% on the day" if ch is not None else "")}
    except Exception:  # noqa: BLE001
        pass
    nf = _nifty(rm)
    return {"label": "Nifty · " + _dw(nf.get("as_of")), "value": (f"{nf['close']:,.0f}" if isinstance(nf.get("close"), (int, float)) else "—"),
            "sub": nf["line"].split(" · ", 1)[-1] if " · " in nf["line"] else ""}


# ---- 4 Nov (Madhav): "Total 2 boxes shows 4 informations. 2 in each shown with slide inside the box." -------------------------------------
# Box 1: Nifty 50, swipe up for Bank Nifty. Box 2: the stocks' value, swipe up for the options line. One Kite call for both indexes and one
# for the open option; each page falls back to the nightly files when Kite cannot be read. The old "numbers" stay for the fact map (E1).

def _signed(x: float, nd: int = 0) -> str:
    return ("+" if x > 0 else "−" if x < 0 else "") + f"{abs(x):,.{nd}f}"


def _tone(x) -> str | None:
    return None if not isinstance(x, (int, float)) or x == 0 else ("good" if x > 0 else "bad")


def _index_page(name: str, last: float, prev: float | None, when: str) -> dict:
    pts = (last - prev) if isinstance(prev, (int, float)) and prev else None
    pct = 100 * pts / prev if pts is not None else None
    return {"label": name, "value": f"{last:,.0f}", "tone": _tone(pts), "focus": "options",
            "sub": (f"{_signed(pts)} ({_signed(pct, 1)}%)" if pts is not None else ""), "sub2": when}


def _shared_fetch(clk: dict | None):
    """One Kite call for the two indexes and the latest session's option contracts, shared by both boxes: two quote calls a few milliseconds
    apart hit Kite's rate limit and the second (the option's price) came back empty. Returns a fetch in Kite's own shape, or None."""
    if not clk:
        return None
    try:
        from jarvis.india import livesession
        syms = list(livesession.INDEX.values())
        for r in livesession._jsonl(DATA / "paper" / "sp1" / "decisions.jsonl"):
            opt = ((r.get("contracts") or {}).get("option") or {}) if r.get("date") == clk.get("latest_session") and r.get("choice") else {}
            if opt.get("tradingsymbol"):
                syms.append(f"NFO:{opt['tradingsymbol']}")
        q = livesession.quotes(syms)
        if q.get("error") or not q.get("rows"):
            return None
        got = q["rows"]
        return lambda want: {s: {"last_price": got[s].get("last"), "ohlc": {"open": got[s].get("open"), "high": got[s].get("high"), "low": got[s].get("low"),
                                                                           "close": got[s].get("prev_close")}} for s in want if s in got}
    except Exception:  # noqa: BLE001
        return None


def _index_tile(rm: dict, clk: dict | None, fetch=None) -> dict:
    pages, vix = {}, None
    if clk:
        try:
            from jarvis.india import livesession
            ix = livesession.index_now(clk, fetch)
            rows = ix.get("rows") or {}
            when = (f"Live · {dt.datetime.now(IST):%H:%M} IST" if clk["state"] == "open" else f"{_dw(clk['latest_session'])} close")
            sp = (ix.get("special_session") or {}).get("rows") or {}       # 8 Nov: a Muhurat-hour print is shown beside the close, named
            for key, name in (("NIFTY 50", "Nifty 50"), ("NIFTY BANK", "Bank Nifty")):
                r = rows.get(key) or {}
                if r.get("last") is not None:
                    pages[key] = _index_page(name, r["last"], r.get("prev_close"), when)
                    m = sp.get(key) or {}
                    if m.get("last") is not None:
                        mp = 100 * (m["last"] / r["last"] - 1)
                        pages[key]["sub2"] = f"{when} · Muhurat {m['last']:,.0f} ({_signed(mp, 1)}%)"
            # 12 Nov 2026, the keen outside audit (G-05): the fear gauge had three values for one close (Markets cut Monday's number out of
            # a sentence and showed it under Wednesday's date; its own page showed the last 5-minute candle; the exchange's close was a
            # third). It is now read here, in the same Kite read and under the same day as the two index boxes, and every surface uses this.
            v = rows.get("INDIA VIX") or {}
            if isinstance(v.get("last"), (int, float)):
                prev = v.get("prev_close")
                ch = v.get("change_pct") if isinstance(v.get("change_pct"), (int, float)) else (
                    100 * (v["last"] / prev - 1) if isinstance(prev, (int, float)) and prev else None)
                vix = {"value": f"{v['last']:.2f}", "when": when, "change_pct": round(ch, 2) if ch is not None else None}
                # 12 Nov evening (repair 2's outside check, N4): after the close Zerodha's last price (17.56 for 11 Nov) and the close in
                # the read model from the exchange's index file (17.53, which the India voice uses) were both shown as "<day> close" on one
                # evening. Which of the two is the exchange's official close is not settled here, so neither is swapped for the other: the
                # Zerodha number is named for what it is, its last price, and "close" is kept for the index file's (the closing-bars path).
                # 13 Nov (repair 2's confirm check, P1): the closing-bars rows (weekends, holidays, after midnight IST before the open,
                # Zerodha signed out) carry the index file's close; only a Zerodha read is renamed
                zerodha = "closing bars" not in str(ix.get("kind") or "")
                if clk["state"] != "open" and zerodha:
                    vix = dict(vix, when=f"{_dw(clk['latest_session'])} · last price", source="Zerodha's last price")
        except Exception:  # noqa: BLE001
            pass
    newer = (rm.get("market") or {}).get("newer_closes") or {}
    tech = ((rm.get("technicals") or {}).get("indices")) or {}
    for key, name in (("NIFTY 50", "Nifty 50"), ("NIFTY BANK", "Bank Nifty")):
        if key in pages:
            continue
        n, t = newer.get(key) or {}, tech.get(key) or {}
        close, d1, day = (n.get("close"), n.get("d1"), n.get("date")) if n.get("close") else (t.get("close"), t.get("change_1d"), t.get("as_of"))
        if isinstance(close, (int, float)):
            prev = close / (1 + d1) if isinstance(d1, (int, float)) else None
            pages[key] = _index_page(name, close, prev, f"{_dw(day)} close")
        else:
            pages[key] = {"label": name, "value": "—", "sub": "no price on file", "focus": "options"}
    return {"id": "market", "pages": [pages["NIFTY 50"], pages["NIFTY BANK"]], "vix": vix}


def _option_open(x: dict, clk: dict) -> bool:
    """A trade the options line took on the latest session is still open: one held to the next open until that open; an intraday one until
    its exit time, during the session."""
    ex = str(x.get("exit") or "").upper()
    if ex == "NEXTOPEN":
        return True
    m = ex[1:] if ex.startswith("T") and ex[1:].isdigit() else ("1515" if ex in ("ATRSTOP", "ORSTOP", "TRAIL") else None)
    if x.get("closed"):                                 # the line's own scoring says it ended (a stop hit)
        return False
    if m and clk.get("state") == "open" and clk.get("latest_session") == clk.get("today_india"):
        return dt.datetime.now(IST).strftime("%H%M") < m
    return False


def _account_tile(mb: dict, acct: dict, clk: dict | None, fetch=None) -> dict:
    own = mb if mb.get("value_inr") else acct
    is_mb = own is mb
    n_st = mb.get("positions") if is_mb else len(acct.get("positions") or [])
    stocks, cash = own.get("stocks_inr"), own.get("cash_inr")
    p1 = {"label": "Stocks", "value": _inr(stocks) if isinstance(stocks, (int, float)) else "—", "focus": "holdings",
          "sub": f"{n_st} stocks" if n_st else ("managed book" if is_mb else "account"),
          "sub2": f"Cash {_inr(cash)}" if isinstance(cash, (int, float)) else ""}
    # 12 Nov (the outside check of repair 4, N8): the options part at the line's own value, as the total counts it (G-11), so the parts add up
    opt = (own.get("options_value_inr") if isinstance(own.get("options_value_inr"), (int, float)) else own.get("options_inr")) or 0
    p2 = {"label": "Options", "value": _inr(opt) if opt else "—", "focus": "options", "sub": "No open trade", "sub2": "One lot a trade"}
    if clk:
        try:
            from jarvis.india import livesession
            ot = livesession.options_today(clk, fetch)
            taken = ot.get("taken") or []
            live = [x for x in taken if _option_open(x, clk)]
            name = {"NIFTY": "Nifty", "BANKNIFTY": "Bank Nifty"}
            if live:
                # a half-width box holds about 17 characters a line: "Open · Bank Nifty" over "55800 CE · +₹534" (the move coloured)
                x = live[0]
                mv = sum(y.get("paper_move_inr_per_lot") or 0 for y in live) if any(y.get("paper_move_inr_per_lot") is not None for y in live) else None
                money = f"{_signed(mv)[0] if mv else ''}₹{abs(mv):,.0f}" if mv is not None else ""
                if len(live) == 1:
                    p2["sub"] = f"Open · {name.get(x.get('index'), x.get('index'))}"
                    p2["sub2"] = " · ".join(v for v in (x.get("option") or "", money) if v)
                else:
                    p2["sub"] = f"{len(live)} open trades"
                    p2["sub2"] = money or " and ".join(name.get(y.get("index"), str(y.get("index"))) for y in live)
                p2["tone2"] = _tone(mv)
            elif taken:
                p2["sub2"] = f"{len(taken)} closed today" if clk.get("latest_session") == clk.get("today_india") else f"{len(taken)} closed {_dw(clk.get('latest_session')).split(' ')[0]}"
        except Exception:  # noqa: BLE001
            pass
    return {"id": "account", "pages": [p1, p2]}


# ---- 4 Nov (Madhav): "I didn't want paragraphs. Only point to point. Simple readable points." --------------------------------------------
# The morning view and the cut list are written as sentences by their owners (records morningview.py, allocator.py); the screen says the same
# facts as short points. Each known sentence has a short form; anything unknown is split, never dropped.
import re as _re  # noqa: E402

_MINUS = _re.compile(r"(?<![\w.])-(?=\d)")


def _tidy(s: str) -> str:
    s = _MINUS.sub("−", s.strip().rstrip(".").strip())
    return s[:1].upper() + s[1:] if s else s


def _split_points(text: str) -> list[str]:
    """Sentences and top-level '; ' parts (not inside brackets), each a point."""
    out, buf, depth = [], "", 0
    t = str(text or "")
    i = 0
    while i < len(t):
        ch = t[i]
        depth += ch == "(" or ch == "["
        depth -= (ch == ")" or ch == "]") and depth > 0
        if depth == 0 and (t.startswith("; ", i) or (t.startswith(". ", i) and i + 2 < len(t) and (t[i + 2].isupper() or t[i + 2] in "₹"))):
            out.append(buf)
            buf, i = "", i + 2
            continue
        buf += ch
        i += 1
    out.append(buf)
    return [_tidy(x) for x in out if x.strip(" .")]


def _view_points(view: list[str]) -> list[str]:
    first, rest = [], []
    for s in view or []:
        s = str(s).strip()
        m = _re.match(r"US: the S&P 500 closed (\S+) \(([^)]*)\)(?:, the Nasdaq (\S+?))?\.?$", s)
        if m:
            first.append(_tidy(f"US: S&P 500 {m[1]}" + (f" · Nasdaq {m[3]}" if m[3] else "")))
            continue
        m = _re.match(r"Nifty closed at ([\d,]+) on ([^(]*?) ?\(([^)]*)\), (in an uptrend|in a downtrend|with no clear trend): (\S+) against its ten-week average, "
                      r"(\S+) against its long-term average; (\d+)% of the 250 most-traded stocks are above their long-term average\.?$", s)
        if m:
            trend = {"in an uptrend": "uptrend", "in a downtrend": "downtrend", "with no clear trend": "no clear trend"}[m[4]]
            first.insert(0, _tidy(f"Nifty closed {m[1]} ({m[3]}) on {m[2]} · {trend}"))
            rest.append(_tidy(f"{m[7]}% of the 250 most-traded stocks are above their long-term average"))
            rest.append(_tidy(f"Nifty is {m[5]} against its ten-week average, {m[6]} against its long-term average"))
            continue
        m = _re.match(r"The fear gauge is at ([\d.]+), (\S+) against its ten-week average( — options are pricing more movement than usual)?\.?$", s)
        if m:
            rest.insert(0, _tidy(f"India VIX {m[1]} ({m[2]} vs usual)" + (" · bigger swings priced in" if m[3] else "")))
            continue
        fl = _re.findall(r"(foreign|domestic) institutions (bought|sold) ₹([\d,]+) crore", s)
        if fl and s.startswith("Yesterday"):
            rest.insert(1 if rest else 0, _tidy(" · ".join(f"{'Foreign institutions' if w == 'foreign' and i == 0 else w} {v} ₹{a} cr" for i, (w, v, a) in enumerate(fl))))
            continue
        m = _re.match(r"Odds for today, from how Nifty has behaved since 2005: up (\d+)% \([^)]*\), down (\d+)% \([^)]*\), flat (\d+)%", s)
        if m:           # views written before 9 Nov 2026 only: the fixed odds are no longer in the view
            rest.append(f"History's odds for the day: up {m[1]}% · down {m[2]}% · flat {m[3]}% (base rates, not a forecast)")
            continue
        # 9 Nov 2026: GIFT Nifty's indicated open, as one short point
        m = _re.match(r"GIFT Nifty, the Nifty future that trades overnight, is (unchanged|up [\d.]+%|down [\d.]+%) from where it stood at the last NSE close "
                      r"\([\d,]+ at (\d\d:\d\d) IST [^)]*\): it points to (an open higher|an open lower|a flat open)(?:, the Nifty near ([\d,]+))?", s)
        if m:
            first.append(_tidy(f"GIFT Nifty {m[1]} since the last close: points to {m[3]}" + (f", Nifty near {m[4]}" if m[4] else "") + f" ({m[2]} IST, an indication)"))
            continue
        rest.extend(_split_points(s))
    return first + rest


def _watch_points(watch: list[str]) -> list[str]:
    out = []
    for s in watch or []:
        s = str(s).strip()
        m = _re.match(r"The lines that decide the day's label: above ([\d,]+) is an up day, below ([\d,]+) a down day", s)
        if m:
            out.append(f"Up day above {m[1]} · down day below {m[2]}")
            continue
        if s.startswith("Option chain"):
            walls = _re.findall(r"(Bank Nifty|Nifty): puts/calls open [\d.]+, max pain ([\d,]+), biggest call wall ([\d,]+), put wall ([\d,]+)", s)
            if walls:
                out += [f"{ix} options: most calls at {c}, most puts at {p} (context only)" for ix, _mp, c, p in walls]
                continue
        m = _re.match(r"Results today: ([^.]+)\.", s)
        if m:
            out.append(f"Results today: {m[1]}")
            continue
        m = _re.match(r"Results came out after yesterday's close for names held in the practice book or your account: ([^.]+)", s)
        if m:
            names = [x.strip() for x in m[1].split(",") if x.strip()]
            out.append("Results out for held names: " + ", ".join(names[:6]) + (f" and {len(names) - 6} more" if len(names) > 6 else ""))
            continue
        out.extend(_split_points(s))
    return out


_ACT = {"TRIM": "trim", "TIDY": "tidy up", "REDUCE": "halve", "CUT": "sell", "SELL": "sell", "EXIT": "sell", "HALVE": "halve"}


def _why_point(sym: str, act: str, why: str) -> str:
    w = str(why or "")
    tiny = _re.search(r"Only ₹(\d[\d,]*\d|\d)", w)
    if tiny:
        return f"{sym}: only ₹{tiny[1]}, too small to matter"
    wt = _re.search(r"(\d+)% of your stocks", w)
    pnl = _re.search(r"([+-]\d+)% on what you paid", w)
    to = _re.search(r"toward (\d+)%", w)
    bits = [f"{wt[1]}% of your stocks" if wt else None, f"{pnl[1]}% on cost" if pnl else None]
    tail = {"TRIM": f"trim to {to[1]}%" if to else "trim", "REDUCE": "halve it"}.get(act)
    body = ", ".join(b for b in bits if b)
    if body:
        return _tidy(f"{sym}: {body}" + (f" · {tail}" if tail else ""))
    return _tidy(f"{sym}: " + (_split_points(w) or [act.lower()])[0])


def _holdings_points(hs: list[dict], bench: dict) -> list[str]:
    groups: dict[str, list[str]] = {}
    for x in hs:
        if x.get("symbol"):
            groups.setdefault(_ACT.get(str(x.get("action") or "").upper(), str(x.get("action") or "review").lower()), []).append(x["symbol"])
    order = ["sell", "halve", "trim", "tidy up"]       # the bigger move first
    keys = sorted(groups, key=lambda a: order.index(a) if a in order else len(order))
    join = lambda xs: xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]   # noqa: E731
    pts = [_tidy("; ".join(f"{a} {join(groups[a])}" for a in keys))] if groups else []
    from jarvis.india import compare as _cmp
    sw = _cmp.same_window()                                   # 5 Nov: one window for all three (jarvis/india/compare.py)
    if sw.get("ready"):
        like = sw.get("managed_like_for_like_pct")              # 12 Nov (N2): the options line's result is in the managed figure
        lw = sw.get("left_out_words")                           # 12 Nov (the confirm check, C3): and the trade it leaves out
        pts.append(_tidy(f"Since {sw['since_words']}: managed {sw['managed_pct']:+.2f}%"
                         + (f" ({like:+.2f}% with its options flat, as yours" + (f"; {lw})" if lw else ")") if like is not None else (f" ({lw})" if lw else ""))
                         + f" · your holdings {sw['yours_pct']:+.2f}% · Nifty 500 {sw['nifty500_pct']:+.2f}%"))
    elif bench.get("frozen_ret_pct") is not None and bench.get("nifty500_ret_pct") is not None:
        pts.append(_tidy(f"Since {_dw(bench.get('frozen_day')).split(' ', 1)[-1]}: your holdings {bench['frozen_ret_pct']:+.2f}% · Nifty 500 {bench['nifty500_ret_pct']:+.2f}%"))
    pts += [_why_point(x["symbol"], str(x.get("action") or "").upper(), x.get("why")) for x in hs if x.get("symbol")]
    if sw.get("ready"):
        pts.append(_tidy(f"Managed book: session {sw['sessions']} of 60"))
    elif bench.get("managed_ret_pct") is not None:
        pts.append(_tidy(f"Managed book {bench['managed_ret_pct']:+.2f}% · session {bench.get('managed_sessions')} of 60"))
    if bench.get("sessions") is not None:
        pts.append("Nothing is judged before 60 sessions")
    return pts


def _plan_points(plan: dict) -> list[str]:
    cuts = plan.get("cuts") if isinstance(plan.get("cuts"), list) else []
    pts = []
    if cuts:
        freed = sum(float(c.get("inr") or 0) for c in cuts)
        pts.append(_tidy(f"Sell {', '.join(str(c.get('symbol')) for c in cuts if c.get('symbol'))}" + (f" · frees about {_inr(freed)}" if freed else "")))
    for b in plan.get("buys") or []:
        pts.append(_tidy(f"Buy {b.get('symbol')} for {str(b.get('for_cut')).replace('+', ', ')}" + (f" · about {_inr(float(b['inr']))}" if b.get("inr") else "")
                         + f" · {b.get('stop_pct') or 7}% stop"))
    return pts or _split_points(plan.get("words") or "")


def _day_ref(day: str | None, clk: dict) -> str:
    try:
        d = dt.date.fromisoformat(str(day)[:10])
        t = dt.date.fromisoformat(str(clk.get("today_india"))[:10])
    except (TypeError, ValueError):
        return "next session"
    return "today" if d == t else "tomorrow" if d == t + dt.timedelta(days=1) else "on " + d.strftime("%a")   # "on Wed": one line on a phone


def headline(plan: dict, clk: dict) -> str:
    """4 Nov (Madhav): "Like No change today … load more for details. One line." The full sentence is the Details."""
    if not plan.get("for_session") or plan.get("error"):
        return "No plan yet"
    ref = _day_ref(plan["for_session"], clk)
    buys = plan.get("buys") or []
    n_cuts = len(plan.get("cuts") or []) if isinstance(plan.get("cuts"), list) else int(plan.get("cuts") or 0)
    if plan.get("no_change") or not (buys or n_cuts):
        return f"No change {ref}"
    if buys:
        return f"{len(buys)} swap{'s' if len(buys) != 1 else ''} {ref}"
    return f"{n_cuts} cut{'s' if n_cuts != 1 else ''} {ref}, cash kept"


def plan_sentence(plan: dict) -> str:
    """The managed plan as one sentence with company names (1 Nov: "a sentence, not a list of ten tickers")."""
    import re as _re
    try:
        from jarvis.india.voice import say_names
    except Exception:  # noqa: BLE001
        say_names = lambda x: x  # noqa: E731
    buys = plan.get("buys") or []
    n_cuts = len(plan.get("cuts") or []) if isinstance(plan.get("cuts"), list) else int(plan.get("cuts") or 0)
    freed = sum(float(c.get("inr") or 0) for c in plan.get("cuts") or []) if isinstance(plan.get("cuts"), list) else float(plan.get("freed_inr") or 0)
    day = dt.date.fromisoformat(plan["for_session"]).strftime("%A") if plan.get("for_session") else "the next session"
    if plan.get("no_change"):
        return f"No change on {day}: the managed book has nothing new to cut or buy."   # 3 Nov: not "nothing is on the cut list"
    if not buys:
        return f"On {day}, {n_cuts} cuts free about ₹{freed:,.0f}; the money stays in cash this time."
    swaps = ", ".join(f"{say_names(b['symbol'])} for {say_names(str(b.get('for_cut')).split('+')[0])}" + (" and the small stakes" if "+" in str(b.get("for_cut")) else "") for b in buys)
    swaps = _re.sub(r"\b([A-Z]) (?=[A-Z]\b)", r"\1", swaps)
    return f"On {day}, {n_cuts} cuts free about ₹{freed:,.0f}: {swaps}. Each with a 7% stop."


def _running(health: dict) -> dict:
    """The status line: the 15-minute self-check first (9 Nov, the outsider round: "Everything was running ... checked 328 min ago" while
    Claude's credit had run out), the nightly jobs' health after it."""
    try:
        from jarvis import selfcheck
        c = selfcheck.check("india")
        top = [x for x in c.get("items") or [] if x.get("severity") == "high" and x.get("source") != "self-check"]
        if top and c.get("at"):
            mins = int((time.time() - float(c["at"])) // 60)
            what = selfcheck.spoken(str(top[0]["what"]))
            return {"ok": False, "words": what[:1].upper() + what[1:120] + ("…" if len(what) > 120 else ""), "checked": f"checked {mins} min ago",
                    "more": len(top) - 1}
    except Exception:  # noqa: BLE001
        pass
    return {"ok": bool(health.get("all_ok")), "words": ("Everything was running at the last check" if (health.get("checked_s_ago") or 0) > 3600 else "Everything is running") if health.get("all_ok") else f"{len(health.get('down') or [])} part{'s' if len(health.get('down') or []) != 1 else ''} down",
            "checked": f"checked {int((health.get('checked_s_ago') or 0) // 60)} min ago" if health.get("checked_s_ago") is not None else ""}


def today(full: bool = True) -> dict:
    rm = views.readmodel()
    m = views.morning()
    mb = _managed()
    plan = mb.get("plan") or {}
    acct = _account_view()
    now = dt.datetime.now(IST)
    session = m.get("session")
    # independent audit, 2 Nov: from IST midnight to 08:30 IST this said "market hours" (it tested only the clock time); the state now comes from
    # the same market clock the voice uses
    try:
        from jarvis.india import livesession
        clk = livesession.clock(rm.get("data_through"))
        state = clk["state"]
    except Exception:  # noqa: BLE001
        clk, state = {}, ("closed" if now.time() >= dt.time(15, 30) or now.weekday() >= 5 else "open")
    view_is_current = bool(session) and session == clk.get("today_india", session) and state in ("before_open", "pre_open", "open")
    # the decision line: the managed book's brief for the next session, else the morning view's headline
    decision = plan.get("brief") if plan.get("for_session") == session and not plan.get("error") else None
    if not decision and plan.get("brief"):
        decision = plan["brief"]
    if plan.get("buys") is not None and not plan.get("error") and plan.get("brief"):
        decision = plan_sentence(plan)
    if not decision:
        decision = m.get("headline") or "No plan is written yet."
    source = (f"From the plan written {_dw(plan.get('written_day'))} · fills at the open · nothing is placed" if plan.get("brief")
              else "From the morning view · nothing is placed")
    health = views._health(rm) if hasattr(views, "_health") else {}
    waiting = m.get("waiting") or views._waiting_count()
    # 4 Nov (Madhav): every card is short points; the screen shows two and "Show more" opens the rest. "text" stays for older app builds.
    cards = []
    if plan.get("words") and not plan.get("no_change"):   # a no-change plan is the headline itself; its card only repeated it
        cards.append({"kind": "plan", "label": f"{_dw(plan.get('for_session'))}'s plan · managed book", "text": plan["words"], "accent": True,
                      "points": _plan_points(plan),
                      "foot": f"{len(plan.get('cuts') or [])} cuts · {len(plan.get('buys') or [])} buys · a buy opening over 2% up is skipped"})
    if m.get("view"):
        label = "The market" if view_is_current else f"The morning view written before the {m.get('session_words') or 'last'} open"
        cards.append({"kind": "market", "label": label, "text": " ".join(m["view"][:2]), "points": _view_points(m["view"])})
    hs = m.get("holdings_suggestions") or []
    if hs:
        cards.append({"kind": "holdings", "label": "Your holdings · the cut list", "text": "Cut list: " + ", ".join(x.get("symbol") for x in hs if x.get("symbol")),
                      "points": _holdings_points(hs, acct.get("benchmark") or {})})
    # 9 Nov (the outsider round): after the session the morning view was for, its chances and what-to-watch ("expiry day", "results today")
    # are over; an after-the-close card from today's own numbers leads instead, with the next session (and a holiday before it) named
    traded = bool(session) and bool(clk) and session <= clk.get("latest_session", "") and state in ("closed", "no_session")
    if traded:
        try:
            from jarvis.india import livesession as _ls2
            lt = _ls2.today(rm)
            pts = []
            ix = (lt.get("index_now") or {}).get("rows") or {}
            n, b, v = ix.get("NIFTY 50") or {}, ix.get("NIFTY BANK") or {}, ix.get("INDIA VIX") or {}
            if n.get("last") is not None:
                pts.append(f"Nifty {n['last']:,.0f}" + (f" ({n['change_pct']:+.1f}%)" if n.get("change_pct") is not None else "")
                           + (f" · Bank Nifty {b['last']:,.0f}" + (f" ({b['change_pct']:+.1f}%)" if b.get("change_pct") is not None else "") if b.get("last") is not None else "")
                           + (f" · VIX {v['last']:.1f}" if v.get("last") is not None else ""))
            h = lt.get("holdings_today") or {}
            if h.get("move_inr") is not None:
                pts.append(f"Your holdings {'+' if h['move_inr'] >= 0 else '−'}₹{abs(h['move_inr']):,} ({h.get('move_pct', 0):+.2f}%)")
            o = lt.get("options_today") or {}
            for x in (o.get("taken") or [])[:2]:
                name = {"BANKNIFTY": "Bank Nifty", "NIFTY": "Nifty"}.get(str(x.get("index")), str(x.get("index")))
                res = (x.get("result") or {}).get("net_inr")
                pts.append(f"Options line: {name} {'short' if x.get('direction') == 'short' else 'long'} at {x.get('at')} IST"
                           + (f", closed {'+' if res >= 0 else '−'}₹{abs(res):,.0f} on paper" if isinstance(res, (int, float)) and x.get("closed") else ", still open on paper"))
            if o.get("decisions") and not o.get("taken"):
                pts.append("Options line: passed at every decision point")
            nxt = clk.get("next_session")
            if nxt:
                d0, d1 = dt.date.fromisoformat(clk["latest_session"]), dt.date.fromisoformat(nxt)
                shut = [d0 + dt.timedelta(days=k) for k in range(1, (d1 - d0).days) if (d0 + dt.timedelta(days=k)).weekday() < 5]
                pts.append(f"Next session {_dw(nxt)}, 09:15 IST" + (f" ({', '.join(_dw(x) for x in shut)} {'is a market holiday' if len(shut) == 1 else 'are market holidays'})" if shut else ""))
            if pts:
                cards.insert(0, {"kind": "close", "label": f"How {_dw(clk['latest_session'])} went", "text": "; ".join(pts), "points": pts, "accent": True})
        except Exception:  # noqa: BLE001  the morning cards stand
            pass
    # 9 Nov 2026 (Madhav: "yes, lets complete", the readiness review): holdings first (what each of his stocks filed since the last close), and
    # above it the second look once the 09:09 pre-open read is in (what changed since the 08:30 view; jarvis/india/recheck.py)
    if m.get("holdings") and not traded and session and session >= clk.get("today_india", session):
        cards.insert(0, {"kind": "holdings_news", "label": "Your holdings · since the last close", "text": " ".join(m["holdings"][:2]), "points": list(m["holdings"])})
    try:
        if view_is_current or (state == "open" and session == clk.get("today_india")):
            from jarvis.india import preopen as _po
            pre = json.loads((_po.OUT / f"{clk.get('today_india')}.json").read_text())
            pts = list((pre.get("recheck") or {}).get("points") or []) + list((pre.get("opening_look") or {}).get("points") or [])
            if pts:
                turned = bool((pre.get("recheck") or {}).get("changed") or (pre.get("opening_look") or {}).get("changed"))
                cards.insert(0, {"kind": "second_look", "label": "Second look · " + ("this changes the 08:30 view" if turned else "the 08:30 view stands"),
                                 "text": " ".join(pts[:2]), "points": pts, "accent": turned})
    except Exception:  # noqa: BLE001  no pre-open read yet: the morning cards stand
        pass
    op = ((m.get("options_line") or {}).get("plan") or {}) if view_is_current else {}
    if op.get("by_index"):                   # 9 Nov 2026 (fix 2): the options line's own plan for this open, as it wrote it at 07:30 IST
        pts = list(op["by_index"].values()) + ["It looks again at 09:30, 09:45 and 10:15 IST; a pass at the open is not a pass for the day"]
        pts += [f"Missing when it was planned: {x}" for x in op.get("missing") or []] or ["No input was stale when it was planned"]
        cards.append({"kind": "options_plan", "label": "Options line · its plan for the 09:15 open", "text": op.get("short") or " ".join(pts[:2]), "points": pts})
    if m.get("chances") and not traded:
        cards.append({"kind": "chances", "label": "Our chances, honestly", "text": " ".join(m["chances"][:1]), "points": _split_points(" ".join(m["chances"]))})
    if m.get("watch") and not traded:
        cards.append({"kind": "watch", "label": "What to watch", "text": " ".join(m["watch"][:2]), "points": _watch_points(m["watch"])})
    try:                                     # 9 Nov (the outsider round): company names on the cards too, as the voice says them
        from jarvis.india import askwords as _aw
        for c in cards:
            if c.get("kind") in ("plan", "holdings", "close", "holdings_news", "second_look"):      # each card's kind is unique: the app keys on it
                c["text"] = _aw.spoken_names(str(c.get("text") or ""))
                c["points"] = [_aw.spoken_names(str(x)) for x in c.get("points") or []]
    except Exception:  # noqa: BLE001
        pass
    fills = mb.get("filled_today") or []
    evening = None
    if fills:
        fill_words = [(f"{'Bought' if t.get('side') == 'BUY' else 'Sold'} {t.get('qty')} {t.get('symbol')} at ₹{t.get('price'):,.2f}" if t.get("filled")
                       else f"Skipped {t.get('symbol')} ({t.get('skipped')})") for t in fills]
        evening = {"label": f"What the managed book did on {_dw(mb.get('day'))}", "text": "; ".join(w[:1].lower() + w[1:] for w in fill_words), "points": fill_words}
    when = {"before_open": "before the open", "pre_open": "before the open", "open": "market hours", "closed": "after the close",
            "no_session": "no session today"}.get(state, "after the close")
    fetch = _shared_fetch(clk or None)
    tiles = [_index_tile(rm, clk or None, fetch), _account_tile(mb, acct, clk or None, fetch)]
    nifty = tiles[0]["pages"][0]
    return {"ready": True, "session": session, "session_words": m.get("session_words"), "when": when, "now_words": now.strftime("%A %-d %b, %H:%M IST"),
            "decision": decision, "decision_source": source,
            "headline": headline(plan, clk) if plan.get("brief") else ("No plan yet" if not m.get("headline") else "Today's morning view"),
            "tiles": tiles,
            "numbers": [{"label": "Nifty · " + str(nifty.get("sub2") or ""), "value": nifty.get("value"), "sub": nifty.get("sub")},
                        # 3 Nov (the Map's change 3): the account's value has one owner, the managed book (the twin is folded into it)
                        ({"label": "Your account", "value": _inr(mb["value_inr"]),
                          "sub": f"managed book · {mb.get('positions')} stocks, ₹{(mb.get('options_value_inr') if isinstance(mb.get('options_value_inr'), (int, float)) else mb.get('options_inr')) or 0:,.0f} options"
                                 # 12 Nov evening (repair 2's outside check, N7): a holding with no close that day is said, not hidden
                                 + (f" · {len(mb['kept_old_price'])} at an older price" if mb.get("kept_old_price") else "")} if mb.get("value_inr") else   # N8
                         {"label": "Your account", "value": (_inr(acct["value_inr"]) if acct.get("value_inr") else "—"),
                          "sub": f"NSE close · {acct.get('positions') and len(acct['positions'])} stocks, ₹{acct.get('options_inr', 0):,.0f} options" if acct else "no snapshot yet"})],
            "waiting": {"count": waiting.get("count") or 0, "words": waiting.get("words")},
            # independent audit, 2 Nov: "Everything is running" beside "checked 234 min ago"; an old check now says it is old
            "running": _running(health),
            "cards": cards, "evening": evening, "clock": (mb.get("clock") or {}).get("words"),
            "suggested": ["What replaces Jio Financial?", "What is the plan for today?", "What's waiting for my yes?"],   # 3 Nov (the Map change 13): the trials are on Proof, asked for there
            "next_view": f"The morning view arrives at {views._sched().at('com.ananta.india.morningview')}." if not m.get("ready") else None, "paper": True}


def money(full: bool = True) -> dict:
    alloc = views.allocation_plan(full=full)
    acct = _account_view()
    bm = acct.get("benchmark") or {}
    mb = _managed()
    plan = mb.get("plan") or {}
    # 3 Nov (Madhav: "Yes for all", the Map's change 3): the twin is folded into the managed book, the one book that manages the account;
    # Money shows three lines (as you have it, managed, Nifty 500) and the account's value is the managed book's
    books = [{"id": "yours", "label": "As you have it", "ret_pct": bm.get("frozen_ret_pct")},
             {"id": "managed", "label": "Managed", "ret_pct": mb.get("return_pct") if (mb.get("clock") or {}).get("sessions") else None, "words": None if (mb.get("clock") or {}).get("sessions") else f"starts {_dw(plan.get('for_session')).split(' ')[0]}"},
             {"id": "index", "label": "Nifty 500", "ret_pct": bm.get("nifty500_ret_pct")}]
    # 5 Nov (synopsis): the three lines had three different start days under a note saying "same start"; now all from the managed start
    from jarvis.india import compare as _cmp
    sw = _cmp.same_window()
    books_note = "Nothing is read into the gap before session 60."
    books_exposure = sw.get("exposure_words") if sw.get("ready") else None    # 12 Nov (G-12): how much of each line is in stocks
    books_options = (sw.get("options_words") or None) if sw.get("ready") else None   # 12 Nov (N2): the options line's result, said beside
    clock = {"sessions": bm.get("sessions"), "of": 60, "finish_words": None, "words": f"Session {bm.get('sessions')} of 60" if bm.get("sessions") is not None else None, "since": bm.get("frozen_day")}
    if sw.get("ready"):
        books[0]["ret_pct"], books[1]["ret_pct"], books[2]["ret_pct"] = sw["yours_pct"], sw["managed_pct"], sw["nifty500_pct"]
        books_note = f"All three from the {sw['since_words']} close, when the managed book started, at the same prices. Nothing is read into the gap before session 60."
        clock = {"sessions": sw["sessions"], "of": 60, "finish_words": None, "words": f"Session {sw['sessions']} of 60", "since": sw["since"]}
    holdings = []
    for x in (alloc.get("holdings") or []) if full else []:
        holdings.append({"symbol": x.get("symbol"), "value_inr": x.get("value_inr"), "weight_pct": x.get("weight_pct"), "pnl_pct": x.get("pnl_pct"), "grade": x.get("grade"),
                         "action": (x.get("action") or "").lower(), "suggest_inr": x.get("suggest_inr"), "why": x.get("why"), "wrong_if": x.get("wrong_if")})
    own = mb if mb.get("value_inr") else acct
    # 12 Nov 2026, the keen outside audit (G-03): the value came from the managed book and its "as of" from the account book's marks, two
    # books marked at different times; the big number carried no date on Home at all. The day now comes from the book the value comes from.
    asof_day = str((mb.get("day") if own is mb else (acct.get("marks") or {}).get("last_session")) or "")[:10] or None
    return {"ready": True, "paper": True, "value_inr": own.get("value_inr"), "stocks_inr": own.get("stocks_inr"), "options_inr": own.get("options_inr"), "cash_inr": own.get("cash_inr"),
            # 12 Nov 2026 (the keen audit, G-11; Madhav's yes of 12 Nov 01:52): the account counts the options money at the options line's own
            # value (the managed book's view works it out, one place), with the sentence that says so
            "options_value_inr": own.get("options_value_inr"), "options_result_inr": own.get("options_result_inr"), "options_counted": own.get("options_counted"),
            "value_owner": "the managed book" if own is mb else "the account book (the managed book has no value yet)",
            "as_of": f"NSE close {_dw(asof_day)}" if asof_day else None, "as_of_day": asof_day,
            "books": books, "clock": clock,
            "books_note": books_note, "books_exposure": books_exposure, "books_options": books_options,
            # 12 Nov evening (repair 2's outside check, N1): the comparison and its chart run to the evening run's close, which can be a
            # session behind the big number (marked in the nightly job); the day they run to is said beside them
            "books_through": (sw.get("through") if sw.get("ready") else None),
            # 13 Nov (repair 2's confirm check, P3): a holding of "as you have them" at an older close, or with none, is said beside it
            "yours_note": "; ".join([f"{s} at the {_dw(d)} close" for s, d in sorted((bm.get("frozen_older_close") or {}).items())]
                                    + [f"{s} with no close on file" for s in sorted(bm.get("frozen_stale") or [])]) or None,
            "plan": {"for_session": plan.get("for_session"), "brief": plan_sentence(plan) if not plan.get("error") else plan.get("brief"), "words": plan.get("words"), "cuts": len(plan.get("cuts") or []), "buys": [{"symbol": b.get("symbol"), "for_cut": b.get("for_cut"), "inr": b.get("inr"), "reasons": b.get("reasons")} for b in plan.get("buys") or []],
                     "no_change": plan.get("no_change"), "error": plan.get("error")} if plan else None,
            "managed": {"value_inr": mb.get("value_inr"), "return_pct": mb.get("return_pct"), "clock": (mb.get("clock") or {}).get("words"), "replacements": mb.get("replacements") or []},
            "options_book": _options_block(acct),
            "holdings": holdings, "holdings_note": "Ranked by Ananta's grade; a suggestion is advice, the managed book acts on it on paper.", "options": alloc.get("options"), "headline": alloc.get("headline")}


def _options_block(acct: dict) -> dict:
    """The options side for Money (1 Nov: the Nifty box on Today opens here): the money set aside, the options line's record by index,
    what it decided on the last session and what is open now."""
    try:
        o = views.options()
    except Exception:  # noqa: BLE001
        o = {}
    by = o.get("by_index") or {}
    last = [x for x in (o.get("decisions_today") or []) if x.get("action")]
    open_now = [{"index": x.get("index"), "point": x.get("point"), "exit": x.get("exit"), "lots": 1} for x in last if str(x.get("exit") or "").upper() == "NEXTOPEN"]
    rows = [{"index": k, "sessions": v.get("sessions"), "trades": v.get("trades"), "rupees": v.get("option_1lot_rs_realistic_fill")} for k, v in by.items()]
    return {"set_aside_inr": acct.get("options_inr"), "book_value_inr": o.get("value_inr"), "book_capital_inr": o.get("capital_inr"), "pnl_inr": o.get("pnl_inr"),
            "sessions": o.get("sessions"), "by_index": rows, "open": open_now,
            "open_words": (f"{len(open_now)} position{'s' if len(open_now) != 1 else ''} open, closing at the next open" if open_now else "No open option positions"),
            "words": f"At most one index option lot per index a session on paper (so up to two: Nifty and Bank Nifty), decided between 09:15 and 10:15 Indian time. {o.get('sessions') or 0} sessions so far; graded after 20."}


def _sp1_clock(clocks: list[dict]) -> None:
    """9 Nov (the outsider round): Proof said 10 sessions and Bank Nifty +Rs 802 while Money and the voice said 11 and -Rs 5,252. One owner for
    the options line's record: its own book (paper/sp1/book.json, scored at 17:30 IST); the trials file is rebuilt only at night."""
    b = _json(DATA / "paper" / "sp1" / "book.json", {}) or {}
    if not b.get("sessions"):
        return
    for c in clocks:
        if "options line" in str(c.get("name") or "") and int(b["sessions"]) >= int(c.get("done") or 0):
            c["done"] = int(b["sessions"])
            parts = [f"{ {'NIFTY': 'Nifty', 'BANKNIFTY': 'Bank Nifty'}.get(k, k) }: {v.get('trades')} trade{'s' if v.get('trades') != 1 else ''}, "
                     f"{'+' if (v.get('option_1lot_rs_realistic_fill') or 0) >= 0 else '−'}₹{abs(v.get('option_1lot_rs_realistic_fill') or 0):,.0f} on one option lot"
                     for k, v in (b.get("by_index") or {}).items()]
            c["so_far"] = f"Over {b['sessions']} sessions, scored to {_dw(str(b.get('updated'))[:10])} with realistic fills: " + "; ".join(parts) + "."
            un = _sp1_unscored()
            if un:                                       # C4: in the same words as every total, never "no result yet" after the expiry
                exp = _sp1_expiries()
                waiting = [r for r in un if not (exp.get((str(r.get("date")), str(r.get("index")))) or "9") < _today_ist()]
                c["so_far"] += (f" Not in these figures: {len(un)} trade{'s' if len(un) != 1 else ''}, "
                                + "; ".join(_sp1_left_one(r, exp) for r in un[:3]) + "."
                                # E1 (the third confirm check): a stop-exit trade is tried again too, the evening after, not at an open
                                + (" A trade left without a result is tried again each evening while its option trades, and marked "
                                   "scored late (Madhav's decision of 12 Nov)." if waiting else ""))


def _sp1_outcomes(data: Path | None = None) -> list[dict]:
    """The options line's outcomes, one row per trade (date and index), in the ledger's order: the scored row when there is one, else the
    note. 12 Nov 2026 (the keen audit, G-01; Madhav's yes of 12 Nov 01:52): a trade the scorer first noted 'not defined' is scored late,
    and the ledger is append-only, so its note stays and the scored row follows it; no reader may list or count the trade twice."""
    out: dict = {}
    try:
        for line in (Path(data or DATA) / "paper" / "sp1" / "outcomes.jsonl").read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("kind", "outcome") != "outcome":
                continue
            k = (str(r.get("date")), str(r.get("index")))
            if k not in out or "index_proxy" in r or "index_proxy" not in out[k]:
                out[k] = r
    except (OSError, ValueError):
        return []
    return list(out.values())


def _sp1_unscored(data: Path | None = None) -> list[dict]:
    """The options line's trades with no result in its totals: a note and no score, or a score whose option had no price. Madhav decided on
    9 Nov that the 6 Nov Bank Nifty trade stays unscored and shown; on 12 Nov (G-01) that it is scored late at the next regular open and
    included, and until then every total says it leaves the trade out."""
    out = []
    for r in _sp1_outcomes(data):
        opt = (r.get("legs") or {}).get("option")
        if (r.get("note") and not r.get("index_proxy")) or (isinstance(opt, dict) and opt.get("net_rs_realistic") is None and opt.get("note")):
            out.append(r)
    return out


def _sp1_expiries() -> dict:
    """(date, index) -> the option contract's expiry day of each decided trade, from the options line's decisions ledger."""
    out: dict = {}
    try:
        for line in (DATA / "paper" / "sp1" / "decisions.jsonl").read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            exp = str(((r.get("contracts") or {}).get("option") or {}).get("expiry") or "")[:10]
            if r.get("kind") == "decision" and exp:
                out[(str(r.get("date")), str(r.get("index")))] = exp
    except (OSError, ValueError):
        pass
    return out


def sp1_left_out_words() -> str:
    """'1 trade left out: Fri 6 Nov Bank Nifty, not scored yet', or '' (G-01): the one sentence every options total carries while it leaves
    a trade out (the Options page, its By index, Account, Markets; Proof says it in its own words). 12 Nov (the outside check of repair 4,
    N12): once a left-out trade's option contract has expired it can never be scored (Kite serves no candles for it), and it says so."""
    un = _sp1_unscored()
    if not un:
        return ""
    exp = _sp1_expiries()
    return f"{len(un)} trade{'s' if len(un) != 1 else ''} left out: " + "; ".join(_sp1_left_one(r, exp) for r in un[:3])


def _today_ist() -> str:
    return dt.datetime.now(IST).date().isoformat()


def _sp1_left_one(r: dict, exp: dict) -> str:
    """'Fri 6 Nov Bank Nifty, not scored yet', or '..., never scored (its option expired Mon 23 Nov)' once its option has expired (Kite
    serves no candles for an expired contract). 12 Nov (the confirm check of repair 4, C4): one set of words for every sentence that names
    a left-out trade, so none still promises a score after the expiry."""
    e = exp.get((str(r.get("date")), str(r.get("index"))))
    what = f"{_dw(r.get('date'))} {({'NIFTY': 'Nifty', 'BANKNIFTY': 'Bank Nifty'}).get(r.get('index'), r.get('index'))}"
    return f"{what}, never scored (its option expired {_dw(e)})" if e and _today_ist() > e else f"{what}, not scored yet"


def proof(full: bool = True) -> dict:
    rm = views.readmodel()
    trials = (_json(DATA / "manifests" / "trials.json", {}) or {}).get("trials") or []
    clocks = [{"name": t.get("name"), "done": t.get("done"), "need": t.get("need"), "unit": t.get("unit"), "finish": t.get("expected_finish"),
               "finish_words": _dw(t.get("expected_finish")),        # 9 Nov: _dw now carries another year itself ("2027 2027" on Proof)
               "complete": t.get("complete"), "so_far": t.get("so_far")} for t in trials]
    _sp1_clock(clocks)
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
                        "words": f"{research.get('versions_tested')} versions tested; {(research.get('verdicts') or {}).get('VALIDATED')} held up, {(research.get('verdicts') or {}).get('CONDITIONAL')} with conditions", "basis": "2000–2023 only; 2024 on is sealed",
                        "explain": _safe(studies_explain, rm)},      # 7 Nov (Madhav): the card opens an explanation, updated nightly, with an Ask Ananta button
            "exam": {"grade": (exam.get("outsider_r5") or exam.get("outsider_r4") or {}).get("overall") if isinstance(exam.get("outsider_r5") or exam.get("outsider_r4"), dict) else None, "words": replay.get("words") if replay else None,
                     "explain": _safe(exam_explain, replay, research)},
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
# 1 Nov: both markets' new screens read /v3/surface/<name> (crypto's /v3/people already means something else)
views.ROUTES.update({"surface/today": today, "surface/money": money, "surface/proof": proof, "surface/people": people})


def live(full: bool = True) -> dict:
    """Today's session as it is right now (jarvis/india/livesession.py, 2 Nov 2026): the clock, the live index, today's options decisions,
    the holdings and the managed plan at today's prices. A guest gets the clock, the index and the options line, not the account."""
    from jarvis.india import livesession
    t = livesession.today(views.readmodel())
    if not full:
        t = {k: v for k, v in t.items() if k not in ("holdings_today", "managed_today")}
        t["words"] = " ".join(x for x in (t["clock"]["words"], t["index_now"].get("words"), t["options_today"].get("words")) if x)
    return t


views.ROUTES.update({"live": live})




# ------------------------------------------------------------------------------------------ 7 Nov 2026 (Madhav): charts and explanations
# "The Nifty 50 and Bank Nifty will be clickable into charts ... Same with our portfolio values box, it shows our portfolio performance
# over time." The index chart is /v3/chart/NIFTY (the technicals panel); the portfolio chart is this, from the account benchmark the
# nightly job writes (paper/account/benchmark.jsonl): your holdings on paper, the untouched original, the managed book, the Nifty 500.

def portfolio_chart(data: Path | None = None) -> dict:
    data = data or DATA
    try:
        rows = [json.loads(x) for x in (data / "paper" / "account" / "benchmark.jsonl").read_text().splitlines() if x.strip()]
    except (OSError, ValueError):
        rows = []
    rows = [r for r in rows if r.get("day")]
    if not rows:
        return {"name": "Your portfolio", "kind": "portfolio", "as_of": None, "chart": {"dates": [], "yours": [], "untouched": [], "managed": [], "nifty500": []},
                "words": "The portfolio record starts with the first nightly benchmark; nothing to draw yet.", "note": "paper only; the values are the nightly closes"}
    start = float(rows[0].get("start_inr") or rows[0].get("twin_inr") or 0) or None
    dates = [str(r["day"]) for r in rows]
    yours = [r.get("twin_inr") for r in rows]
    untouched = [r.get("frozen_inr") for r in rows]
    managed = [r.get("managed_inr") for r in rows]
    n500 = [round(start * (1 + float(r["nifty500_ret_pct"]) / 100)) if start and r.get("nifty500_ret_pct") is not None else None for r in rows]
    last = rows[-1]
    pct = lambda k: float(last.get(k) or 0)                       # a partial last row (a key missing or null) still reads
    try:                                                          # the returns count from the account's starting snapshot, not the first drawn point
        since = str(json.loads((data / "paper" / "account" / "frozen.json").read_text()).get("day") or "")
    except (OSError, ValueError):
        since = ""
    # 8 Nov (the outside audit, "two accounts on paper"): one owner for "my account on paper" is the managed book (the Map's change 3, 3 Nov);
    # the twin is folded into it and is not drawn as a second "you". The lines: the managed book, the same holdings left alone, the Nifty 500.
    m0 = next((r.get("day") for r in rows if r.get("managed_inr")), None)
    # 12 Nov 2026 (the confirm check of repair 4, C2): from G-11 the managed figure holds the options line's paper result (about 12.9 of
    # its +15.87 points on 12 Nov) and leaves a trade out; the chart's words said neither. Said as How it compares says it (compare.py).
    from jarvis.india import compare as _cmp
    sw = _safe(_cmp.same_window, data) or {}
    lw = sw.get("left_out_words") if sw.get("ready") else ""
    if sw.get("ready") and sw.get("managed_options_inr") and sw.get("managed_like_for_like_pct") is not None:
        pts_ = sw["managed_pct"] - sw["managed_like_for_like_pct"]
        ow = (f"Of that, about {abs(pts_):.1f} points are the options line's paper {'result' if pts_ >= 0 else 'loss'}; with its options flat, "
              f"like the untouched holdings, {sw['managed_like_for_like_pct']:+.2f}%".replace("-", "−") + (f"; {lw}" if lw else "") + ". ")
    else:
        ow = f"{lw}. " if lw else ""
    words = (f"Drawn from {_dw(dates[0])} to {_dw(dates[-1])}. "
             + (f"Your account on paper, the managed book, {_inr(last.get('managed_inr') or 0)}: {pct('managed_ret_pct'):+.2f}% since it started on {_dw(m0)} "
                f"({last.get('managed_sessions') or 0} sessions). " + ow if last.get("managed_inr") else "The managed book has not started. ")
             + "From the snapshot" + (f" of {_dw(since)} ({_inr(start)})" if since and start else "") + ": "
             + f"the same holdings left untouched {_inr(last.get('frozen_inr') or 0)} ({pct('frozen_ret_pct'):+.2f}%)"
             + (f"; the Nifty 500 {pct('nifty500_ret_pct'):+.2f}% on its own path." if last.get("nifty500_ret_pct") is not None else "."))
    words = _re.sub(r"(?<![\w.])-(?=\d)", "−", words)           # 12 Nov (the second confirm check, D4): a minus sign, as the money beside it
    return {"name": "Your account on paper", "kind": "portfolio", "as_of": dates[-1], "start_inr": start, "sessions": len(rows),
            "chart": {"dates": dates, "yours": managed, "untouched": untouched, "managed": managed, "nifty500": n500, "twin": yours},
            "legend": {"yours": "your account on paper (the managed book)", "untouched": "the same holdings left alone", "nifty500": "the Nifty 500, same rupees at its reference day"},
            "words": words, "note": "paper only, one point per session at the close; the managed book starts on its own first day"}


def _safe(fn, *a):
    """An explanation that cannot be built leaves the card without one (the app shows the card alone) instead of blanking Proof."""
    try:
        return fn(*a)
    except Exception:
        return None


def studies_explain(rm: dict) -> dict:
    """The 'Versions tested' card's explanation, from the read model (updated with it every night): what a version is, the counts, what
    held up and what did not, in plain words, with the question the Ask Ananta button sends."""
    research = rm.get("research") or {}
    v = research.get("verdicts") or {}
    ik = rm.get("indicator_knowledge") or {}
    held, failed = [], []

    def _verdicts(t: dict) -> set:
        v = t.get("verdict")
        return set(v.keys()) if isinstance(v, dict) else ({str(v)} if v else set())

    for fam, blk in (ik.get("families") or {}).items():
        tested = blk.get("tested") or [] if isinstance(blk, dict) else []
        ok = [t.get("what") for t in tested if _verdicts(t) & {"VALIDATED", "CONDITIONAL"} and t.get("what") and not str(t.get("what")).startswith("study ")]
        seen = set().union(*[_verdicts(t) for t in tested]) if tested else set()
        if ok:
            held.append(ok[0])
        elif seen and not (seen & {"VALIDATED", "CONDITIONAL"}) and (seen & {"REJECTED", "OPPOSITE"}):
            failed.append(fam)
    points = ["A version is one exact way of stating an idea, such as 'RSI over 70' against 'RSI over 80'; one idea can have several versions.",
              # 12 Nov 2026 (the keen audit, G-50): "never looked at" was not so: the sealed years were opened on 20 Oct for another study
              f"{research.get('versions_tested') or 0} versions were tested on 2000-2017 and then checked on 2018-2023, never on 2024 onward. "
              "The years from 2024 are kept sealed from research; they were opened on 20 Oct 2026 for another study, the index options line.",
              f"{v.get('VALIDATED', 0)} held up in both periods, {v.get('CONDITIONAL', 0)} held with conditions, {v.get('REJECTED', 0)} did not hold, "
              f"{v.get('OPPOSITE', 0)} showed the opposite of the claim, {v.get('INCONCLUSIVE', 0)} had too little data to judge."]
    if held:
        points.append("What held up and matters for your money, as filters on what to avoid rather than buy signals: " + "; ".join(held[:4]) + ".")
    if failed:
        points.append("What did not hold, so nothing trades on it: " + ", ".join(failed[:5]) + ".")
    points.append("A result that held is evidence, not a rule: a rule changes only with Madhav's yes, and nothing here trades by itself.")
    return {"points": points, "updated": _dw(rm.get("data_through")) + " close" if rm.get("data_through") else "", "source": "the nightly research files and the test ledger",
            "ask": "Explain the versions tested: what a version is, how many held up and on what data, which ones matter for my money, and what was rejected."}


def exam_explain(replay: dict | None, research: dict) -> dict:
    """The 'Nightly check' card's explanation: what is re-asked every night, how it is graded, last night's result, the weekly exam."""
    s = replay or {}
    ex = (research.get("exam") or {}).get("last") or {}
    points = ["Every night Ananta re-asks the real questions of the day and a bank of past questions, and grades each answer against that day's facts: "
              "a wrong day, a wrong number, a missing part or jargon counts as a fail."]
    if s.get("night"):
        points.append(f"Last night ({_dw(s['night'])}): {(s.get('today_turns') or 0) - (s.get('today_failed') or 0)} of {s.get('today_turns') or 0} of the day's answers passed; "
                      f"the bank of past questions {(s.get('bank_checked') or 0) - (s.get('bank_failed') or 0)} of {s.get('bank_checked') or 0} ({s.get('bank_fixed') or 0} fixed for good, {s.get('bank_open') or 0} still open); "
                      f"the never-again cases {(s.get('never_again_checked') or 0) - (s.get('never_again_failed') or 0)} of {s.get('never_again_checked') or 0}.")
    else:
        points.append("The nightly check has not written a result yet.")
    if ex.get("day"):
        points.append(f"The weekly India exam ({_dw(ex['day'])}): knows {ex.get('known')} of {ex.get('known_of')}, says 'I don't know' when it should {ex.get('unknown')} of {ex.get('unknown_of')}, "
                      f"explains why {ex.get('why')} of {ex.get('why_of')}, safety {ex.get('safety')} of {ex.get('of')}, plain words {ex.get('plain')} of {ex.get('of')}: "
                      f"{'PASS' if ex.get('exam_pass') else 'FAIL'}; {research.get('exam', {}).get('passed', 0)} of {research.get('exam', {}).get('runs', 0)} runs passed so far.")
    if s.get("bank_open"):
        points.append(f"Still open: {s['bank_open']} past answers that failed again last night; each is on the repair board until it passes.")
    points.append("A failed check changes an answer, never a trade: the paper books decide by their rules whatever the check says.")
    return {"points": points, "updated": (_dw(s["night"]) + " night") if s.get("night") else "", "source": "the nightly replay record and the weekly exam",
            "ask": "Explain the nightly check: what it re-asks every night, how it is graded, what failed recently and what is still open."}


views.ROUTES["chart/portfolio"] = portfolio_chart   # 7 Nov: also reachable as a plain view
