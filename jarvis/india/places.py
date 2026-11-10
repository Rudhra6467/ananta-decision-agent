"""India's places for the redesign (Madhav, 10 Nov 2026: "yes for all your recommendations"; India screens included, his word on the 2 Nov
freeze for screens only: no new India feature or data file comes with this).

The same five places as crypto (Home, Markets, Ask, Activity, More) and the same building blocks (jarvis/placekit.py), written from what
India's screens already read (jarvis/india/surfaces.py: the managed book, the morning view, the account, the options line, the trials).
"Needs you" and the bell come from the one open list, which lives with the sign-in service: the app asks for it there (/v3/place/needs).
Read-only. Nothing here trades or writes a file."""
from __future__ import annotations

import datetime as dt
import json
import re

from jarvis import placekit as K
from jarvis.india import surfaces as IS
from jarvis.india import views

DAYS_BACK = 21
IDX = {"NIFTY": "Nifty", "BANKNIFTY": "Bank Nifty"}
ACTION = {"hold": "Hold", "watch": "Watch", "trim": "Trim", "reduce": "Reduce", "tidy": "Tidy up", "add": "Add"}
GRADE_TONE = {"A": "good", "C": "warn", "D": "bad"}


def _name(sym) -> str:
    try:
        from jarvis.india import askwords
        return askwords.spoken_names(str(sym)) or str(sym)
    except Exception:  # noqa: BLE001
        return str(sym)


def _jsonl(p) -> list[dict]:
    try:
        return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
    except Exception:  # noqa: BLE001
        return []


def _rs(v, sign: bool = False) -> str:
    if not isinstance(v, (int, float)):
        return "—"
    s = IS._inr(abs(v)) if hasattr(IS, "_inr") else f"₹{abs(v):,.0f}"
    s = s if s.startswith("₹") else "₹" + s.lstrip("₹")
    return ("−" if v < 0 else "+" if sign and v > 0 else "") + s


def _pct(p, nd: int = 2) -> str:
    return "—" if not isinstance(p, (int, float)) else f"{'+' if p > 0 else '−' if p < 0 else ''}{abs(p):.{nd}f}%"


def _tone(x):
    return None if not isinstance(x, (int, float)) or abs(x) < 1e-9 else "good" if x > 0 else "bad"


def _clk() -> dict:
    try:
        from jarvis.india import livesession
        return livesession.clock(views.readmodel().get("data_through"))
    except Exception:  # noqa: BLE001
        return {}


# ------------------------------------------------------------------------------------------------ pages
def holding_page(h: dict) -> dict:
    g = str(h.get("grade") or "").upper()
    act = ACTION.get(str(h.get("action") or "").lower(), str(h.get("action") or "").title())
    why = [IS._tidy(x) for x in re.split(r"(?<=[.:])\s+(?=[A-Z])", str(h.get("why") or "")) if x.strip()]
    pts = []
    if h.get("weight_pct") is not None:
        pts.append(f"It is {h['weight_pct']:.0f}% of your stocks")
    if h.get("suggest_inr") and str(h.get("action")).lower() not in ("hold", "watch"):
        pts.append(f"Ananta suggests: {act.lower()} about {_rs(h['suggest_inr'])}")
    if h.get("wrong_if"):
        pts.append({"text": "Ananta is wrong if " + str(h["wrong_if"]).rstrip("."), "icon": "info"})
    parts = [K.pill(f"Grade {g} · {act.lower()}" if g else act, tone=GRADE_TONE.get(g)),
             K.hero(_name(h.get("symbol")), _rs(h.get("value_inr")), change=_pct(h.get("pnl_pct"), 1) if h.get("pnl_pct") is not None else None,
                    tone=_tone(h.get("pnl_pct")), since="on what you paid"),
             K.line(K.clip(why[0], 20, 140) if why else "Graded by Ananta from its own studies."),
             K.points([why[0]]) if why and K.nwords(why[0]) > 20 else None,
             K.points(why[1:3] + pts),
             K.kv([K.kvrow("Share of your stocks", f"{h['weight_pct']:.1f}%" if h.get("weight_pct") is not None else "—"),
                   K.kvrow("Ananta's grade", g or "—"), K.kvrow("Suggestion", f"{act} {_rs(h['suggest_inr'])}" if h.get("suggest_inr") else act)]),
             K.trust("A suggestion is advice. The managed book acts on it on paper; nothing is placed.")]
    return K.page(_name(h.get("symbol")), parts, bar_kind="close", ask_q=f"Tell me about {_name(h.get('symbol'))} in my holdings: why grade {g or '—'}, and what would change your mind?",
                  second={"label": "What replaces it?", "ask": f"If {_name(h.get('symbol'))} is cut, what replaces it, and why?"} if str(h.get("action")).lower() in ("trim", "reduce", "tidy") else None)


def holding_row(h: dict) -> dict:
    g = str(h.get("grade") or "").upper()
    return K.row(_name(h.get("symbol")), ACTION.get(str(h.get("action") or "").lower(), str(h.get("action") or "").title()), right=_rs(h.get("value_inr")),
                 grade=g or None, to=K.to_page(holding_page(h)))


def holdings_page(hs: list[dict]) -> dict:
    by = sorted(hs, key=lambda h: -(h.get("value_inr") or 0))
    return K.page("Your holdings", [K.hero("Your holdings", str(len(by)), since="Graded by Ananta, biggest first"), K.rows(None, [holding_row(h) for h in by], plain=True),
                                    K.trust("Ranked by Ananta's grade; a suggestion is advice, the managed book acts on it on paper.")],
                  ask_q="Go through my holdings: which are strong, which are weak, and what would you change?")


def plan_page(money: dict | None = None, today: dict | None = None) -> dict:
    t = today or IS.today()
    m = money or IS.money()
    plan = m.get("plan") or {}
    pts = [IS._tidy(x) for x in IS._split_points(str(plan.get("words") or ""))] if plan.get("words") else []
    card = next((c for c in t.get("cards") or [] if c.get("kind") == "plan"), None)
    if card:
        pts = card.get("points") or pts
    clock = (m.get("clock") or {}).get("words")
    parts = [K.pill("No change" if plan.get("no_change") else f"{plan.get('cuts') or 0} cuts · {len(plan.get('buys') or [])} buys", icon="check"),
             K.heading(f"The plan for {IS._dw(plan.get('for_session'))}" if plan.get("for_session") else "The next session's plan"),
             K.line(str(plan.get("brief") or t.get("decision") or "No plan is written yet.")),
             K.points(pts[:6]) if pts and not plan.get("no_change") else None,
             K.trust(f"{t.get('decision_source') or ''}. {clock + ': nothing is judged before session 60.' if clock else ''}".strip(" ."))]
    return K.page("The plan", parts, bar_kind="close", ask_q="What will you change in my portfolio next session, and why?",
                  second={"label": "Why no change?" if plan.get("no_change") else "Why these?",
                          "ask": "Why is there no change for the next session? What was checked?" if plan.get("no_change") else "Why these cuts and replacements? What else passed the filters?"})


def morning_page(m: dict | None = None) -> dict:
    m = m or views.morning()
    pts = IS._view_points(m.get("view") or []) if m.get("view") else []
    ch = IS._split_points(" ".join(m.get("chances") or [])) if m.get("chances") else []
    w = IS._watch_points(m.get("watch") or []) if m.get("watch") else []
    parts = [K.heading(f"The morning view · before the {m.get('session_words') or 'last'} open"), K.points(pts),
             K.points(ch, title="Our chances, honestly") if ch else None, K.points(w, title="What to watch") if w else None,
             K.trust("Written before the open from the evening's data. Base rates, never a forecast.")]
    return K.page("Morning view", parts, ask_q="Walk me through this morning's view: what matters most, and what would change it?")


def _split_row(p: str) -> dict:
    s = str(p).strip().rstrip(".").replace("India VIX", "Fear gauge")      # the screens' own word for it (plain.scrub)
    if ": " in s[:24]:
        a, b = s.split(": ", 1)
    elif " · " in s:
        a, b = s.split(" · ", 1)
    else:
        a, b = K.title_sub(s)
    return K.row(K.clip(a[:1].upper() + a[1:], 6, 38), K.clip(b[:1].upper() + b[1:], 8, 44) if b else None)   # 5: plain words can lengthen a name (VIX: the fear gauge)


# ------------------------------------------------------------------------------------------------ activity
def _events(full: bool = True) -> list[tuple]:
    since = (dt.date.today() - dt.timedelta(days=DAYS_BACK)).isoformat()
    out = []
    for r in _jsonl(IS.DATA / "paper" / "managed" / "ledger.jsonl"):
        day = str(r.get("for_session") or "")[:10]
        if day < since:
            continue
        nm = _name(r.get("symbol"))
        if r.get("filled"):
            side = "Bought" if r.get("side") == "BUY" else "Sold"
            sub = f"For the {_name(r.get('for_cut'))} cut" if r.get("for_cut") else K.clip(IS._tidy(r.get("why")), 6, 40)
            pg = K.page("Trade", [K.hero(f"{side} {nm} · {IS._dw(day)}", _rs(r.get("value_inr")), since="the managed book, on paper"),
                                  K.kv([K.kvrow("Quantity", str(r.get("qty"))), K.kvrow("Price", _rs(r.get("price"))), K.kvrow("Costs", _rs(r.get("cost_inr"))),
                                        K.kvrow("Opened", f"{r['gap_pct']:+.1f}% from the close" if isinstance(r.get("gap_pct"), (int, float)) else "—"),
                                        K.kvrow("Safety stop", _rs(r.get("stop")))]),
                                  K.points([IS._tidy(r.get("why"))], title="Why"), K.trust("Paper only, at the NSE open.")],
                         ask_q=f"Why did the managed book {'buy' if r.get('side') == 'BUY' else 'sell'} {nm} on {IS._dw(day)}, and how is it doing?")
            out.append((day, 2, K.row(f"{side} {nm}", sub, right=_rs(r.get("value_inr")), icon="up" if r.get("side") == "BUY" else "down", tag="trade", to=K.to_page(pg))))
        else:
            out.append((day, 2, K.row(f"Skipped {nm}", K.clip(IS._tidy(r.get("skipped") or "Not filled"), 7, 44), icon="pause", tag="trade")))
    for r in _jsonl(IS.DATA / "paper" / "sp1" / "outcomes.jsonl"):
        day = str(r.get("date") or "")
        opt = (r.get("legs") or {}).get("option") or {}
        net = opt.get("net_rs_realistic")
        if day < since or net is None:
            continue
        name = IDX.get(str(r.get("index")), str(r.get("index")))
        dirw = "short" if (r.get("dir") or 0) < 0 else "long"
        pg = K.page("Options trade", [K.hero(f"Options · {name} {dirw} · {IS._dw(day)}", _rs(round(net)), tone=_tone(net), since="one lot, on paper, after costs"),
                                      K.kv([K.kvrow("Option", str(opt.get("tradingsymbol") or "—")), K.kvrow("In", _rs(opt.get("entry_realistic"))), K.kvrow("Out", _rs(opt.get("exit"))),
                                            K.kvrow("Lot", f"{opt.get('lot'):.0f}" if isinstance(opt.get("lot"), (int, float)) else "—"),
                                            K.kvrow("How it ended", {"ATRSTOP": "Its stop", "ORSTOP": "The range stop", "NEXTOPEN": "At the next open"}.get(str(r.get("exit")), str(r.get("exit") or "—"))),
                                            K.kvrow("Result", _rs(round(net)), tone=_tone(net), bold=True)]),
                                      K.trust("Paper only. Graded after 20 sessions.")],
                     ask_q=f"Tell me about the options trade on {name} on {IS._dw(day)}: why, how it ended, and what it taught.")
        out.append((day, 1.5, K.row(f"Options · {name} {dirw}", "Closed on paper", right=_rs(round(net)), right_tone=_tone(net), icon="down" if net < 0 else "up", tag="trade", to=K.to_page(pg))))
    for p in _jsonl(IS.DATA / "paper" / "managed" / "plans.jsonl"):
        day = str(p.get("written_day") or "")[:10]
        if day < since:
            continue
        sub = "No change" if p.get("no_change") else f"{len(p.get('cuts') or [])} cuts · {len(p.get('buys') or [])} buys"
        pg = K.page("The plan", [K.heading(f"The plan for {IS._dw(p.get('for_session'))}"), K.points([IS._tidy(x) for x in IS._split_points(str(p.get("words") or ""))]),
                                 K.trust(f"Written {IS._dw(day)} · {p.get('rules') or ''} · fills at the open · nothing is placed")],
                    ask_q=f"Tell me about the plan for {IS._dw(p.get('for_session'))}.")
        out.append((day, 0.5, K.row(f"Plan for {IS._dw(p.get('for_session'))}", sub, icon="check", tag="note", to=K.to_page(pg))))
    try:
        from jarvis.service import places as CP
        out += CP.change_rows("india", since)
    except Exception:  # noqa: BLE001
        pass
    out.sort(key=lambda e: (e[0], -e[1]), reverse=True)
    return out


def activity(full: bool = True) -> dict:
    ev = _events(full)
    parts = [K.chips([{"id": "all", "label": "All"}, {"id": "trade", "label": "Trades"}, {"id": "change", "label": "Changes"}, {"id": "note", "label": "Plans"},
                      {"id": "fix", "label": "Fixes"}, {"id": "you", "label": "For you"}]),
             {"t": "needs", "title": "Waiting for you", "tags": ["you"]}]
    days: dict[str, list] = {}
    for d, _o, r in ev:
        days.setdefault(d, []).append(r)
    for d in list(days)[:14]:
        parts.append(K.rows(IS._dw(d), days[d][:25]))
    if not ev:
        parts.append(K.line("Nothing has happened in the last three weeks."))
    return K.surface("activity", "india", parts, title="Activity")


# ------------------------------------------------------------------------------------------------ Home
def _index_box(t: dict, name: str = "Nifty 50"):
    pages = (t.get("tiles") or [{}])[0].get("pages") or []
    p = next((x for x in pages if x.get("label") == name), pages[0] if pages else {})
    m = re.search(r"\(([+−-]?[\d.]+%)\)", str(p.get("sub") or ""))
    return p, (m.group(1).replace("-", "−") if m else None)


def _spark(key: str) -> list:
    try:
        j = json.loads((views.DATA / "manifests" / "technicals.json").read_text())
        return K.thin((((j.get("indices") or {}).get(key) or {}).get("chart") or {}).get("closes", [])[-60:], 30)
    except Exception:  # noqa: BLE001
        return []


def _index_boxes(t: dict) -> list[dict]:
    """Home's first box: the Nifty 50 and Bank Nifty, each with its day's change and its last 60 closes."""
    out = []
    for name, key in (("Nifty 50", "NIFTY 50"), ("Bank Nifty", "NIFTY BANK")):
        p, chg = _index_box(t, name)
        if p.get("label") != name:
            continue
        out.append(K.box(name, p.get("value") or "—", change=chg, tone=p.get("tone"), since=str(p.get("sub2") or "").replace(" close", "") or None,
                         spark=_spark(key), to=K.tab("markets")))
    return out


def _options_caption(t: dict, m: dict) -> str:
    """The old Options page's words: an open trade, or none, and the last one closed."""
    pages = ((t.get("tiles") or [{}, {}])[1:2] or [{}])[0].get("pages") or []
    p = next((x for x in pages if x.get("label") == "Options"), {})
    ob = m.get("options_book") or {}
    return K.clip(p.get("sub") or ("No open trade" if not ob.get("open") else f"{len(ob['open'])} open"), 6, 30)


def home_notices(t: dict, m: dict, clk: dict) -> list[dict]:
    out = []
    run = t.get("running") or {}
    if not run.get("ok"):
        out.append(K.notice("run:" + dt.date.today().isoformat(), K.clip(run.get("words"), 10, 70), K.ask("Is everything running? What is down, since when, and what does it affect?")))
    nxt = clk.get("next_session")
    if clk.get("state") in ("closed", "no_session") and nxt:
        today_in = clk.get("today_india")
        hol = today_in and dt.date.fromisoformat(today_in).weekday() < 5 and clk.get("state") == "no_session"
        out.append(K.notice("next:" + nxt, ("Market holiday today. " if hol else "") + f"Next session {IS._dw(nxt).split(' ')[0]}, 09:15 India time", K.place("plan")))
    hs = [h for h in m.get("holdings") or [] if str(h.get("action") or "").lower() not in ("hold", "watch", "")]
    if hs:
        out.append(K.notice("hs:" + str(t.get("session")), f"{len(hs)} suggestions on your holdings", K.place("holdings")))
    return out[:3]


def home(full: bool = True) -> dict:
    t, m = IS.today(full), IS.money(full)
    clk = _clk()
    mb = IS._managed()
    value, ret, start = m.get("value_inr"), (m.get("managed") or {}).get("return_pct"), mb.get("start_inr")
    plan = m.get("plan") or {}
    brief = str(plan.get("brief") or t.get("decision") or "")
    a, _, b = brief.partition(": ")
    line = (a.rstrip(".") + ".") if b else K.clip(brief, 9, 60)
    sub = (b[:1].upper() + b[1:]).rstrip(".") + "." if b else ""
    nxt = clk.get("next_session") if clk.get("state") in ("closed", "no_session") else None
    st = clk.get("state")
    label = (f"Next session · {IS._dw(nxt)}" if nxt else f"Before the open · {IS._dw(clk.get('today_india'))}" if st in ("before_open", "pre_open") and clk.get("today_india")
             else "Today · market hours" if st == "open" else "Today")
    stocks, opts, cash = m.get("stocks_inr") or 0, m.get("options_inr") or 0, m.get("cash_inr") or 0
    tot = (stocks + opts + cash) or 1
    did = [r for _d, _o, r in _events(full)]
    seen, top = set(), []
    for r in did:
        k = "change" if r.get("tag") == "fix" else r.get("tag")
        if k not in seen:
            seen.add(k)
            top.append({**r, "right": r.get("right") if k == "trade" else None})
        if len(top) == 3:
            break
    parts = [K.hero("Your paper account", _rs(value), change=(f"{_rs(value - start, sign=True)} ({_pct(ret)})" if isinstance(value, (int, float)) and isinstance(start, (int, float)) and isinstance(ret, (int, float)) else _pct(ret) if ret is not None else None),
                    tone=_tone(ret), since=f"since {IS._dw(mb.get('start_day'))}" if mb.get("start_day") else None,
                    status={"ok": bool((t.get("running") or {}).get("ok")), "words": "Running" if (t.get("running") or {}).get("ok") else "Needs a look"}),
             K.today(label, line, sub, to=K.place("plan")),
             K.boxes([K.paged(_index_boxes(t)),
                      K.paged([K.box("In stocks", _rs(stocks), bar=[round(stocks / tot, 3), round(opts / tot, 3)], caption=f"{mb.get('positions') or len(m.get('holdings') or [])} stocks", to=K.place("account")),
                               K.box("Options", _rs(opts), bar=[0, round(opts / tot, 3)], caption=_options_caption(t, m), to=K.place("options"))])]),
             {"t": "needs", "title": "Needs you", "badge": True, "more": K.place("notices")},
             K.rows("What Ananta did", top, more=K.tab("activity")) if top else None,
             K.notices(home_notices(t, m, clk))]
    return K.surface("home", "india", parts, title="Home")


# ------------------------------------------------------------------------------------------------ Markets
def markets(full: bool = True) -> dict:
    t, m = IS.today(full), IS.money(full)
    mv = views.morning()
    pages = (t.get("tiles") or [{}])[0].get("pages") or []
    cards = []
    for p in pages:
        mm = re.search(r"\(([+−-]?[\d.]+%)\)", str(p.get("sub") or ""))
        cards.append(K.box(p.get("label"), p.get("value"), change=mm.group(1).replace("-", "−") if mm else None, tone=p.get("tone")))
    vix = None
    for c in t.get("cards") or []:
        for x in c.get("points") or []:
            v = re.search(r"VIX (\d+(?:\.\d+)?)", str(x))
            if v and not vix:
                vix = v.group(1)
    if vix:
        cards.append(K.box("Fear gauge", vix, caption="India VIX"))
    when = (pages[0].get("sub2") if pages else None) or ""
    view = mv.get("view") or []
    trend = next((x for x in view if "uptrend" in x or "downtrend" in x), "")
    up = "uptrend" in trend
    breadth = re.search(r"(\d+)% of the 250 most-traded stocks are above their long-term average", trend)
    vpts = IS._view_points(view) if view else []
    pick = [x for x in vpts if re.search(r"institutions|US:|VIX|fear", x)][:3] or vpts[:3]
    hs = sorted(m.get("holdings") or [], key=lambda h: -(h.get("value_inr") or 0))
    ob = m.get("options_book") or {}
    hp = holdings_page(hs) if hs else None
    parts = [K.chips([{"id": "all", "label": "Indices"}, {"id": "holdings", "label": "Holdings", "count": len(hs) or None}, {"id": "options", "label": "Options"},
                      {"id": "view", "label": "Morning view"}]),
             K.peek(cards, note=when, tags=["all"]),
             {**K.rows(None, [K.row("The Nifty is in an uptrend" if up else "The Nifty is not in an uptrend",
                                    (f"{round(int(breadth.group(1)) / 10)} in 10 big stocks above long-term average" if breadth else None), to=K.to_page(morning_page(mv)))], plain=True), "tags": ["all"]} if trend else None,
             K.rows("Morning view", [_split_row(x) for x in pick], sub=f"before the {mv.get('session_words') or 'last'} open", more=K.to_page(morning_page(mv)), tags=["all", "view"]) if pick else None,
             K.rows("Your holdings", [holding_row(h) for h in hs[:3]], count=len(hs), more=K.to_page(hp), tags=["all"]) if hs else None,
             K.rows("Your holdings", [holding_row(h) for h in hs], count=len(hs), tags=["holdings"]) if hs else None,
             K.rows("Options", [K.row(ob.get("open_words") and ("No open trade" if not ob.get("open") else f"{len(ob['open'])} open on paper") or "Options",
                                      f"{ob.get('sessions')} of 20 sessions on record" if ob.get("sessions") is not None else None, right=_rs(ob.get("pnl_inr"), sign=True),
                                      right_tone=_tone(ob.get("pnl_inr")), to=K.place("options"))], tags=["all", "options"]) if ob else None]
    return K.surface("markets", "india", parts, title="Markets", search={"hint": "Search a stock", "route": "/coin/"})


def options_page(full: bool = True) -> dict:
    m = IS.money(full)
    ob, op = m.get("options_book") or {}, m.get("options") or {}
    rows = [K.kvrow(IDX.get(r.get("index"), r.get("index")), _rs(r.get("rupees"), sign=True), k_sub=f"{r.get('trades')} trades", tone=_tone(r.get("rupees"))) for r in ob.get("by_index") or []]
    parts = [K.hero("Options, set aside", _rs(ob.get("set_aside_inr")), change=_rs(ob.get("pnl_inr"), sign=True) if ob.get("pnl_inr") is not None else None, tone=_tone(ob.get("pnl_inr")),
                    since=f"over {ob.get('sessions')} sessions, on paper"),
             K.line(str(ob.get("open_words") or "")), K.kv(rows, title="By index"),
             K.bars([K.bar("Sessions on record", ob.get("sessions") or 0, 20, right=f"{ob.get('sessions') or 0} of 20", note="It earns a bigger share only after 20")]),
             K.points([IS._tidy(op.get("words"))]) if op.get("words") else None,
             K.trust(str(ob.get("words") or ""))]
    return K.page("Options", parts, ask_q="How is the options line doing, and what does it decide each morning?")


# ------------------------------------------------------------------------------------------------ the account page
def account(full: bool = True) -> dict:
    m = IS.money(full)
    mb = IS._managed()
    value, start = m.get("value_inr"), mb.get("start_inr")
    ret = (m.get("managed") or {}).get("return_pct")
    pc = (IS._safe(IS.portfolio_chart) or {}).get("chart") or {}
    ml = [x for x in (pc.get("managed") or []) if isinstance(x, (int, float))]
    dates = [d for d, x in zip(pc.get("dates") or [], pc.get("managed") or []) if isinstance(x, (int, float))]
    stocks, opts, cash = m.get("stocks_inr") or 0, m.get("options_inr") or 0, m.get("cash_inr") or 0
    tot = (stocks + opts + cash) or 1
    hs = sorted(m.get("holdings") or [], key=lambda h: -(h.get("value_inr") or 0))
    reps = (m.get("managed") or {}).get("replacements") or []
    clock = m.get("clock") or {}
    books = m.get("books") or []
    order = {"managed": 0, "yours": 1, "index": 2}
    label = {"managed": "The managed book", "yours": "Your holdings, as you have them", "index": "Nifty 500"}
    parts = [K.hero("The managed book · on paper", _rs(value), change=(f"{_rs(value - start, sign=True)} ({_pct(ret)})" if isinstance(value, (int, float)) and isinstance(start, (int, float)) and isinstance(ret, (int, float)) else None),
                    tone=_tone(ret), since=f"since {IS._dw(mb.get('start_day'))}" if mb.get("start_day") else None),
             K.chart([{"values": ml, "style": "main", "color": "bronze"}], left=IS._dw(dates[0]) if dates else None, right=IS._dw(dates[-1]) if dates else None,
                     caption="One point a session, at the close.", label="The managed book's value at each close") if len(ml) > 1 else None,
             K.split([{"label": f"Stocks · {mb.get('positions') or len(hs)}", "value": _rs(stocks), "share": round(stocks / tot, 3), "shade": "ink"},
                      {"label": "Options, set aside", "value": _rs(opts), "share": round(opts / tot, 3), "shade": "dim"},
                      {"label": "Cash", "value": _rs(cash), "share": round(cash / tot, 3), "shade": "faint"}], title="Where it sits"),
             K.kv([K.kvrow(label.get(b.get("id"), b.get("label")), _pct(b.get("ret_pct")) if b.get("ret_pct") is not None else (b.get("words") or "—"), tone=_tone(b.get("ret_pct")), bold=(b.get("id") == "managed"))
                   for b in sorted(books, key=lambda b: order.get(b.get("id"), 9))], title="How it compares",
                  foot=(f"All from the {IS._dw(clock.get('since'))} close. {clock.get('words')}: too early to judge." if clock.get("since") and clock.get("words") else m.get("books_note"))),
             K.rows("Your holdings", [holding_row(h) for h in hs[:3]], count=len(hs), sub=f"{len(hs)} · graded", more=K.to_page(holdings_page(hs))) if hs else None,
             K.rows("Bought on paper", [K.row(_name(r.get("symbol")), f"For the {_name(r.get('for_cut'))} cut", right=_rs(r.get("value_inr")), right_sub=_pct(r.get("pnl_pct"), 1),
                                              right_tone=_tone(r.get("pnl_pct"))) for r in reps[:3]], count=len(reps)) if reps else None,
             K.rows(None, [K.row("Options", "One lot at a time, on paper", right=_rs((m.get("options_book") or {}).get("pnl_inr"), sign=True), right_tone=_tone((m.get("options_book") or {}).get("pnl_inr")), to=K.place("options")),
                           K.row("The next session's plan", "No change" if (m.get("plan") or {}).get("no_change") else "Cuts and buys", to=K.place("plan"))], plain=True)]
    return K.page("Your account", parts, ask_q="Explain my account: the managed book, how it compares, what it holds and what happens next session.",
                  second={"label": "What changes next session?", "ask": "What will you change in my portfolio next session, and why?"})


# ------------------------------------------------------------------------------------------------ Proof, People, More
def proof(full: bool = True) -> dict:
    p = IS.proof(full)
    m = IS.money(full)
    clock = m.get("clock") or {}
    cl = p.get("clocks") or []
    bars = [K.bar(IS._tidy(K.clip(x.get("name"), 6, 40)), x.get("done") or 0, x.get("need") or 1, right=("done" if x.get("complete") else f"{x.get('done')} of {x.get('need')}"),
                  note=x.get("finish_words") or None) for x in cl]
    st, ex = p.get("studies") or {}, p.get("exam") or {}
    words = str(ex.get("words") or "")
    grade = "Fail" if re.search(r"\bFAIL\b", words) else "Pass" if re.search(r"\bPASS\b", words) else None
    when = re.search(r"last run (\d{4}-\d\d-\d\d)", words)
    def explain(title, e, q):
        if not e or not e.get("points"):
            return K.ask(q)
        return K.to_page(K.page(title, [K.heading(str(e.get("title") or title)), K.points(e["points"]), K.trust(f"From {e.get('source')}" if e.get("source") else "Written from the facts on file.")], ask_q=e.get("ask") or q))
    rows = [K.row("Studies", f"{st.get('held_up')} held up, {st.get('conditional')} with conditions", right=f"{st.get('run'):,}" if isinstance(st.get("run"), int) else None, icon="flask", tint="blue",
                  to=explain("Studies", st.get("explain"), "Explain the versions tested: what a version is, how many held up and on what data, and what was rejected.")),
            K.row("India exam", f"Weekly · last run {IS._dw(when.group(1))}" if when else "Weekly", right=grade, right_tone={"Pass": "good", "Fail": "bad"}.get(grade), icon="exam", tint="blue",
                  to=explain("India exam", ex.get("explain"), "Explain the India exam: what it asks, how it is graded, what failed and what is still open.")),
            K.row("Night test", "Not built for India yet", right="Planned", icon="moon", tint="blue", to=K.ask("When does India get its own night test, like crypto's?"))]
    if (p.get("missed") or {}).get("words"):
        rows.append(K.row("What we missed", K.clip(p["missed"]["words"], 8, 44), icon="eye", tint="blue", to=K.route("/missed")))
    links = [K.row(K.clip(x.get("label"), 5, 30), None, to=K.route(x.get("route"))) for x in p.get("links") or [] if x.get("route") != "/missed"]
    parts = [K.hero("The managed book", clock.get("words") or "—", since="Nothing is judged before session 60."),
             K.bars(bars), K.rows("Checks", rows), K.rows(None, links, plain=True) if links else None,
             K.points([IS._tidy(p["last_night"]["words"])], title="Last night's card") if (p.get("last_night") or {}).get("words") else None]
    return K.page("Proof", parts, ask_q="Explain every clock in detail: what each trial is testing, where it stands today, when it finishes, and what would count as a pass.")


def people(full: bool = True) -> dict:
    p = IS.people(full)
    rows = [K.row(x.get("name"), K.clip(x.get("can"), 8, 46), right=K.clip(x.get("relation"), 3, 18) or None, letter=str(x.get("name") or "?")[:1]) for x in p.get("people") or []]
    parts = [K.hero("People", str(len(rows)), since="Only Madhav decides. Everyone else can ask."), K.rows(None, rows, plain=True), K.trust(str(p.get("invite") or ""))]
    return K.page("People", parts, ask_q="Who can talk to you, and what can each of them do?", second={"label": "Invite someone", "route": "/people"})


def more(full: bool = True) -> dict:
    p, m = IS.proof(full), IS.money(full)
    st, ex = p.get("studies") or {}, p.get("exam") or {}
    words = str(ex.get("words") or "")
    grade = "Fail" if re.search(r"\bFAIL\b", words) else "Pass" if re.search(r"\bPASS\b", words) else None
    when = re.search(r"last run (\d{4}-\d\d-\d\d)", words)
    ppl = IS.people(full).get("people") or []
    clock = (m.get("clock") or {}).get("words")
    parts = [K.identity("Paper only. It never places an order."),
             K.tiles("Proof", [K.tile("Studies", f"{st.get('run'):,} tested" if isinstance(st.get("run"), int) else "—", "flask", "blue", K.place("proof")),
                               K.tile("India exam", " · ".join(x for x in (grade, IS._dw(when.group(1)).split(" ", 1)[-1] if when else None) if x) or "Weekly", "exam", "blue", K.place("proof")),
                               K.tile("Night test", "Planned", "moon", "blue", K.place("proof")),
                               K.tile("Clocks", clock or "—", "clock", "blue", K.place("proof")),
                               K.tile("Missed", "Last session", "eye", "blue", K.route("/missed")),
                               K.tile("Teachers", "Tested", "bars", "blue", K.route("/teachers"))]),
             K.tiles("You and others", [K.tile("People", f"{len(ppl)} on the list", "people", "violet", K.place("people")),
                                        {"t": "needs_tile", "label": "The open list", "icon": "list", "tint": "violet", "to": K.place("openlist")},
                                        K.tile("Repair board", "Your flags", "flag", "violet", K.route("/flags"))]),
             K.tiles("Settings", [{"t": "push_tile", "label": "Phone notes", "icon": "phone"},
                                  K.tile("Appearance", "Dark or light", "sun", None, {"action": "theme"}),
                                  K.tile("All settings", "Voice, sign-out", "person", None, K.route("/more"))])]
    return K.surface("more", "india", parts, title="More")


PLACES = {"home": home, "markets": markets, "activity": activity, "more": more, "account": account, "proof": proof, "plan": lambda full=True: plan_page(IS.money(full), IS.today(full)),
          "holdings": lambda full=True: holdings_page(sorted(IS.money(full).get("holdings") or [], key=lambda h: -(h.get("value_inr") or 0))),
          "options": options_page, "people": people, "morning": lambda full=True: morning_page()}


def _guest(name):
    def f(full: bool = True):
        if not full and name in ("home", "account", "holdings", "plan", "activity", "markets"):
            return {"ready": False, "kind": "place", "name": name, "words": "This page shows Madhav's account. A guest's own book is on the practice screens."}
        return PLACES[name](full=full)
    return f


for _n in PLACES:
    views.ROUTES[f"place/{_n}"] = _guest(_n)
