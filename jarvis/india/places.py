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
    g = _letter(h)                                   # 12 Nov 2026 (G-17): "not graded" is said in words, never as a grade letter
    ungraded = not g and bool(h.get("grade"))
    act = ACTION.get(str(h.get("action") or "").lower(), str(h.get("action") or "").title())
    why = [IS._tidy(x) for x in re.split(r"(?<=[.:])\s+(?=[A-Z])", str(h.get("why") or "")) if x.strip()]
    pts = []
    if h.get("weight_pct") is not None:
        pts.append(f"It is {h['weight_pct']:.0f}% of your stocks")
    if h.get("suggest_inr") and str(h.get("action")).lower() not in ("hold", "watch"):
        pts.append(f"Ananta suggests: {act.lower()} about {_rs(h['suggest_inr'])}")
    if h.get("wrong_if"):
        # 12 Nov 2026 (audit repair 4, G-21; Madhav's yes: plainer words now, a stop rule waits for the review): "Ananta is wrong if it
        # closes under Rs X" read as a stop, while the holdings the managed book started with have none and leave only through the grade
        pts.append({"text": "Ananta's view changes if " + str(h["wrong_if"]).rstrip(".") + ". That is not a stop: in the managed book a "
                            "holding it started with leaves only through its grade", "icon": "info"})
    parts = [K.pill(f"Grade {g} · {act.lower()}" if g else (f"Not graded · {act.lower()}" if ungraded else act), tone=GRADE_TONE.get(g)),
             K.hero(_name(h.get("symbol")), _rs(h.get("value_inr")), change=_pct(h.get("pnl_pct"), 1) if h.get("pnl_pct") is not None else None,
                    tone=_tone(h.get("pnl_pct")), since="on what you paid"),
             K.line(K.clip(why[0], 20, 140) if why else "Graded by Ananta from its own studies."),
             K.points([why[0]]) if why and K.nwords(why[0]) > 20 else None,
             K.points(why[1:3] + pts),
             K.kv([K.kvrow("Share of your stocks", f"{h['weight_pct']:.1f}%" if h.get("weight_pct") is not None else "—"),
                   K.kvrow("Ananta's grade", g or ("not graded" if ungraded else "—")), K.kvrow("Suggestion", f"{act} {_rs(h['suggest_inr'])}" if h.get("suggest_inr") else act)]),
             K.trust("A suggestion is advice. The managed book acts on it on paper; nothing is placed.")]
    why_q = f"why grade {g}" if g else ("why it is not graded" if ungraded else "why grade —")
    return K.page(_name(h.get("symbol")), parts, bar_kind="close", ask_q=f"Tell me about {_name(h.get('symbol'))} in my holdings: {why_q}, and what would change your mind?",
                  second={"label": "What replaces it?", "ask": f"If {_name(h.get('symbol'))} is cut, what replaces it, and why?"} if str(h.get("action")).lower() in ("trim", "reduce", "tidy") else None)


def _letter(h: dict) -> str:
    """A grade letter, or "" for a holding Ananta does not grade (12 Nov 2026, G-17: no price study, so "not graded" and never cut)."""
    g = str(h.get("grade") or "").upper()
    return g if len(g) == 1 else ""


def holding_row(h: dict) -> dict:
    g = _letter(h)
    act = ACTION.get(str(h.get("action") or "").lower(), str(h.get("action") or "").title())
    return K.row(_name(h.get("symbol")), act if g or h.get("grade") is None else "Not graded · " + act.lower(), right=_rs(h.get("value_inr")),
                 grade=g or None, to=K.to_page(holding_page(h)))


def holdings_page(hs: list[dict]) -> dict:
    # 12 Nov 2026 (audit repair 4, G-06): these are the holdings in your Zerodha account as you have them, graded; the managed book's own
    # positions are a different list, at the book's own sizes (book_page)
    by = sorted(hs, key=lambda h: -(h.get("value_inr") or 0))
    return K.page("Your Zerodha holdings", [K.hero("Your Zerodha holdings", str(len(by)), since="As you have them, graded by Ananta, biggest first"),
                                            K.rows(None, [holding_row(h) for h in by], plain=True),
                                            K.trust("Your real account, read only. Ranked by Ananta's grade; a suggestion is advice, and the managed book acts on it on "
                                                    "paper, at its own sizes.")],
                  ask_q="Go through my holdings: which are strong, which are weak, and what would you change?")


def book_row(x: dict) -> dict:
    """One position of the managed book, at the book's own size (12 Nov 2026, G-06)."""
    # G-21: a replacement carries a stop; a holding the book started with has none and leaves only through its grade
    return K.row(_name(x.get("symbol")), f"{x.get('qty')} share{'s' if x.get('qty') != 1 else ''}"
                 + (" · bought on paper, with a stop" if x.get("source") == "replacement" else " · no stop, leaves by its grade"),
                 right=_rs(x.get("value_inr")), right_sub=_pct(x.get("pnl_pct"), 1) if x.get("pnl_pct") is not None else None, right_tone=_tone(x.get("pnl_pct")))


def book_page(own: list[dict], marks: list[dict] | None = None) -> dict:
    """The managed book's own positions (12 Nov 2026, G-06: they were shown nowhere), with the marks on its past rows (G-07, G-17)."""
    pts = [IS._tidy(str(x.get("mark") or "")) for x in marks or [] if x.get("mark")]
    return K.page("In the managed book", [K.hero("In the managed book", str(len(own)), since="On paper, at the book's own sizes, biggest first"),
                                          K.rows(None, [book_row(x) for x in own], plain=True),
                                          K.points(pts) if pts else None,
                                          K.trust("Paper only. The book started from your account's positions and changes them by its own rules.")],
                  ask_q="What does the managed book hold now, and how is each position doing?")


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
    for r in IS._safe(IS._sp1_outcomes) or []:              # 12 Nov (G-01): one row per trade, a late score marked
        day = str(r.get("date") or "")
        opt = (r.get("legs") or {}).get("option") or {}
        net = opt.get("net_rs_realistic")
        if day < since or net is None:
            continue
        name = IDX.get(str(r.get("index")), str(r.get("index")))
        dirw = "short" if (r.get("dir") or 0) < 0 else "long"
        late = bool(r.get("scored_late"))
        ended = {"ATRSTOP": "Its stop", "ORSTOP": "The range stop", "NEXTOPEN": "At the next open"}.get(str(r.get("exit")), str(r.get("exit") or "—"))
        if late and str(r.get("exit")) == "NEXTOPEN":
            ended = "At the next regular open, scored late"
        pg = K.page("Options trade", [K.hero(f"Options · {name} {dirw} · {IS._dw(day)}", _rs(round(net)), tone=_tone(net), since="one lot, on paper, after costs"),
                                      K.kv([K.kvrow("Option", str(opt.get("tradingsymbol") or "—")), K.kvrow("In", _rs(opt.get("entry_realistic"))), K.kvrow("Out", _rs(opt.get("exit"))),
                                            K.kvrow("Lot", f"{opt.get('lot'):.0f}" if isinstance(opt.get("lot"), (int, float)) else "—"),
                                            K.kvrow("How it ended", ended),
                                            K.kvrow("Result", _rs(round(net)), tone=_tone(net), bold=True)]),
                                      K.points([IS._tidy(str(r.get("late_why") or ""))], title="Scored late") if late and r.get("late_why") else None,
                                      K.trust("Paper only. Graded after 20 sessions.")],
                     ask_q=f"Tell me about the options trade on {name} on {IS._dw(day)}: why, how it ended, and what it taught.")
        out.append((day, 1.5, K.row(f"Options · {name} {dirw}", "Closed on paper" + (", scored late" if late else ""), right=_rs(round(net)), right_tone=_tone(net),
                                    icon="down" if net < 0 else "up", tag="trade", to=K.to_page(pg))))
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
                         spark=_spark(key), to=K.place({"NIFTY 50": "nifty", "NIFTY BANK": "banknifty"}[key])))
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


def _evening_at() -> str:
    """When the evening run writes the next session's plan, from the jobs themselves ('8:20 pm Toronto (06:50 IST)'), or ''."""
    try:
        from jarvis.india import schedule
        return schedule.at("com.ananta.india.evening")
    except Exception:  # noqa: BLE001
        return ""


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
    # 12 Nov 2026, the keen outside audit (G-04): from the Indian day's turn (1:30 pm Toronto) to the evening run, Home headed this block
    # "Before the open · Thu 12 Nov" and filled it with Wednesday's plan ("No change on Wednesday"): the next plan is written only by the
    # evening run. The block now names the plan's own day; a plan for a session that has passed says so, and when the next one comes.
    fs = str(plan.get("for_session") or "")[:10]
    upcoming = str(nxt or (clk.get("today_india") if st in ("before_open", "pre_open", "open") else "") or "")[:10]
    if fs and upcoming and fs < upcoming:
        label = f"Last plan · {IS._dw(fs)}"
        at = _evening_at()
        sub = f"The plan for {IS._dw(upcoming)} is written at {at}." if at else f"The plan for {IS._dw(upcoming)} is not written yet."
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
    day = m.get("as_of_day") or mb.get("day")          # 12 Nov (G-03): the close the big number is marked at, from the book it comes from
    parts = [K.hero(f"Your paper account · {IS._dw(day)} close" if day else "Your paper account", _rs(value), change=(f"{_rs(value - start, sign=True)} ({_pct(ret)})" if isinstance(value, (int, float)) and isinstance(start, (int, float)) and isinstance(ret, (int, float)) else _pct(ret) if ret is not None else None),
                    tone=_tone(ret), since=f"since {IS._dw(mb.get('start_day'))}" if mb.get("start_day") else None,
                    status={"ok": bool((t.get("running") or {}).get("ok")), "words": "Running" if (t.get("running") or {}).get("ok") else "Needs a look"}),
             K.today(label, line, sub, to=K.place("plan")),
             K.boxes([K.paged(_index_boxes(t)),
                      K.paged([K.box("In stocks", _rs(stocks), bar=[round(stocks / tot, 3), round(opts / tot, 3)], caption=f"{mb.get('positions') or len(m.get('holdings') or [])} stocks", to=K.place("stocks")),
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
        cards.append(K.box(p.get("label"), p.get("value"), change=mm.group(1).replace("-", "−") if mm else None, tone=p.get("tone"),
                           to=K.place({"Nifty 50": "nifty", "Bank Nifty": "banknifty"}.get(p.get("label"), "nifty"))))
    vx = _vix(t)                              # 12 Nov (G-05): the same read and the same day as the Nifty boxes, never a number cut from a sentence
    if vx:
        cards.append(K.box("Fear gauge", vx["value"], change=_vix_change(vx), caption="India VIX", to=K.place("vix")))
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
                                      (f"{ob.get('sessions')} of 20 sessions on record" + ("; one trade left out" if _left_out() else "")) if ob.get("sessions") is not None else None,
                                      right=_rs(ob.get("pnl_inr"), sign=True),
                                      right_tone=_tone(ob.get("pnl_inr")), to=K.place("options"))], tags=["all", "options"]) if ob else None]
    return K.surface("markets", "india", parts, title="Markets", search={"hint": "Search a stock", "route": "/coin/"})


def options_page(full: bool = True) -> dict:
    m = IS.money(full)
    ob, op = m.get("options_book") or {}, m.get("options") or {}
    rows = [K.kvrow(IDX.get(r.get("index"), r.get("index")), _rs(r.get("rupees"), sign=True), k_sub=f"{r.get('trades')} trades", tone=_tone(r.get("rupees"))) for r in ob.get("by_index") or []]
    trades = (IS._safe(IS._sp1_outcomes) or [])[::-1]      # 12 Nov (G-01): one row per trade; a late score follows its note in the ledger
    left = _left_out()                       # 12 Nov 2026 (audit repair 4, G-01): until it is scored late, every total says what it leaves out
    parts = [K.hero("Options, set aside", _rs(ob.get("set_aside_inr")), change=_rs(ob.get("pnl_inr"), sign=True) if ob.get("pnl_inr") is not None else None, tone=_tone(ob.get("pnl_inr")),
                    since=f"over {ob.get('sessions')} sessions, on paper" + (f"; {left}" if left else "")),
             K.pricechart("OPTIONS", "The options line", kind="line", private=True),
             K.line(str(ob.get("open_words") or "")), K.kv(rows, title="By index", foot=(left[:1].upper() + left[1:] + ".") if left else None),
             K.rows("Trades on paper", [_trade_row(r) for r in trades[:3]], count=len(trades), more=K.to_page(option_trades_page(trades)) if len(trades) > 3 else None) if trades and full else None,
             K.bars([K.bar("Sessions on record", ob.get("sessions") or 0, 20, right=f"{ob.get('sessions') or 0} of 20", note="It earns a bigger share only after 20")]),
             K.points([IS._tidy(op.get("words"))]) if op.get("words") else None,
             K.trust(str(ob.get("words") or ""))]
    return K.page("Options", parts, ask_q="How is the options line doing, and what does it decide each morning?",
                  second={"label": "Show the portfolio", "to": K.place("account")} if full else None)


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
    own = sorted(mb.get("holdings") or [], key=lambda x: -(x.get("value_inr") or 0))
    reps = (m.get("managed") or {}).get("replacements") or []
    clock = m.get("clock") or {}
    books = m.get("books") or []
    order = {"managed": 0, "yours": 1, "index": 2}
    label = {"managed": "The managed book", "yours": "Your holdings, as you have them", "index": "Nifty 500"}
    day = m.get("as_of_day") or mb.get("day")          # 12 Nov (G-03): the hero says which close it is marked at
    parts = [K.hero("The managed book · on paper", _rs(value), change=(f"{_rs(value - start, sign=True)} ({_pct(ret)})" if isinstance(value, (int, float)) and isinstance(start, (int, float)) and isinstance(ret, (int, float)) else None),
                    tone=_tone(ret), since=(f"since {IS._dw(mb.get('start_day'))}" + (f", at the {IS._dw(day)} close" if day else "")) if mb.get("start_day") else None),
             K.chart([{"values": ml, "style": "main", "color": "bronze"}], left=IS._dw(dates[0]) if dates else None, right=IS._dw(dates[-1]) if dates else None,
                     caption="One point a session, at the close.", label="The managed book's value at each close") if len(ml) > 1 else None,
             K.split([{"label": f"Stocks · {mb.get('positions') or len(hs)}", "value": _rs(stocks), "share": round(stocks / tot, 3), "shade": "ink"},
                      {"label": "Options, set aside", "value": _rs(opts), "share": round(opts / tot, 3), "shade": "dim"},
                      {"label": "Cash", "value": _rs(cash), "share": round(cash / tot, 3), "shade": "faint"}], title="Where it sits"),
             K.kv([K.kvrow(label.get(b.get("id"), b.get("label")), _pct(b.get("ret_pct")) if b.get("ret_pct") is not None else (b.get("words") or "—"), tone=_tone(b.get("ret_pct")), bold=(b.get("id") == "managed"))
                   for b in sorted(books, key=lambda b: order.get(b.get("id"), 9))], title="How it compares",
                  # 11 Nov 2026 (R-027, flag 93): the hero said "since Fri 30 Oct" and this foot "All from the Thu 29 Oct close" for one start
                  foot=((f"All since {IS._dw(mb.get('start_day'))}, the same start as above (counted from the {IS._dw(clock.get('since'))} close). "
                         if mb.get("start_day") and str(clock.get("since") or "") < str(mb.get("start_day")) else f"All from the {IS._dw(clock.get('since'))} close. ")
                        + f"{clock.get('words')}: too early to judge." if clock.get("since") and clock.get("words") else m.get("books_note"))),
             # 12 Nov 2026 (audit repair 4, G-06): the book's own positions under its own total; your Zerodha holdings, as you have them, apart
             K.rows("In the managed book", [book_row(x) for x in own[:3]], count=len(own), sub=f"{len(own)} · on paper, at its own sizes",
                    more=K.to_page(book_page(own, mb.get("marks")))) if own else None,
             K.rows("Your Zerodha holdings", [holding_row(h) for h in hs[:3]], count=len(hs), sub=f"{len(hs)} · as you have them, graded", more=K.to_page(holdings_page(hs))) if hs else None,
             K.rows("Bought on paper", [K.row(_name(r.get("symbol")), f"For the {_name(r.get('for_cut'))} cut", right=_rs(r.get("value_inr")), right_sub=_pct(r.get("pnl_pct"), 1),
                                              right_tone=_tone(r.get("pnl_pct"))) for r in reps[:3]], count=len(reps)) if reps else None,
             K.rows(None, [K.row("Options", "One lot at a time, on paper" + ("; one trade left out" if _left_out() else ""), right=_rs((m.get("options_book") or {}).get("pnl_inr"), sign=True), right_tone=_tone((m.get("options_book") or {}).get("pnl_inr")), to=K.place("options")),
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


# ------------------------------------------------------------------------------------------------ charts behind a tap
# Madhav, 10 Nov 2026 19:09 Toronto: "the 4 objects in 2 boxes from home tab has to show their respective charts ... with more filters like
# 1D,5D,1M,3M,6M and timeframes of 5M,15M,30M,1H,4H,1D. for stocks and options in the second box, it should show their own respective graphs
# representing their historical performance with an option there to show the portfolio and ask ananta about it" and "In the markets tab, the
# boxes nifty 50, bank nifty and fear gauge should also be clickable and show their historical details". His request covers these India
# screens and the candles they draw (read from Kite, read-only, kept in memory; no new data file).
IDX_PAGES = {"nifty": ("NIFTY 50", "Nifty 50"), "banknifty": ("NIFTY BANK", "Bank Nifty"), "vix": ("INDIA VIX", "Fear gauge")}
CHART_KEYS = {"NIFTY": "NIFTY 50", "NIFTY50": "NIFTY 50", "BANKNIFTY": "NIFTY BANK", "NIFTYBANK": "NIFTY BANK", "BANK": "NIFTY BANK", "VIX": "INDIA VIX", "INDIAVIX": "INDIA VIX"}
KEY_NAME = {k: n for k, n in IDX_PAGES.values()}
KITE_TF = {"5M": "5minute", "15M": "15minute", "30M": "30minute", "1H": "60minute", "4H": "60minute", "1D": "day"}
BACK_DAYS = {"1D": 7, "5D": 12, "1M": 31, "3M": 92, "6M": 183}
FEED_NOTE = "From Zerodha's feed, read-only, in India time. A description, never a rule."


def _tech() -> dict:
    try:
        return json.loads((views.DATA / "manifests" / "technicals.json").read_text()).get("indices") or {}
    except Exception:  # noqa: BLE001
        return {}


def index_candles(key: str, rng: str | None = None, tf: str | None = None, fetch=None) -> dict:
    """One index's candles for a range and timeframe (jarvis/chartkit.py). Kite's 4-hour candles are built from its hourly ones (09:15 to
    13:15, then to the close). When Kite cannot answer (signed out until the morning sign-in), the daily closes on file are drawn as a line."""
    from jarvis import chartkit as CK
    from jarvis.india import livesession as L

    r, t, ok = CK.pick("india", rng, tf)
    end = dt.datetime.now(L.IST).date()
    name = KEY_NAME[key]
    day = lambda b: dt.datetime.fromtimestamp(b[0], L.IST).date()                                 # noqa: E731
    try:
        allb = L.index_bars(key, KITE_TF[t], end - dt.timedelta(days=BACK_DAYS[r]), end, fetch=fetch)
        if t == "4H":
            allb = CK.agg(allb, key=lambda b: (day(b), dt.datetime.fromtimestamp(b[0], L.IST).strftime("%H%M") >= "1315"))
        if t == "1D":
            bars = allb[-CK.SESSIONS[r]:]
        else:
            keep = set(sorted({day(b) for b in allb})[-CK.SESSIONS[r]:])
            bars = [b for b in allb if day(b) in keep]
        if not bars:
            raise ValueError("no candles came back")
        out = CK.shape(name, "india", r, t, ok, bars, tz_min=330, live=day(bars[-1]) == end, note=FEED_NOTE, base=CK.before(allb, bars))
        if key == "INDIA VIX":                        # a falling fear gauge is calmer, not a loss: no green or red on its change
            out["neutral"] = True
        return out
    except Exception as e:  # noqa: BLE001
        why = str(e)
        panel = (_tech().get(key) or {}).get("chart") or {}
        closes = list(zip(panel.get("dates") or [], panel.get("closes") or []))
        n = max(6, CK.SESSIONS[r] + 1)
        bars = [[CK.day_t(d, 15, 330), c, c, c, c] for d, c in closes[-n:] if isinstance(c, (int, float))]
        words = ("Zerodha's feed is signed out until the morning sign-in (06:05 India time)" if ("403" in why or "Login" in why or "token" in why.lower())
                 else "Zerodha's feed did not answer just now")
        out = CK.shape(name, "india", r, "1D", ok, bars, kind="line", tz_min=330, ranges=CK.RANGES, note="The daily closes on file, from Zerodha's daily candles.",
                       fell_back=words + (", so these are the daily closes on file." if bars else "; no closes on file for this one yet."))
        if len(bars) > 1:
            out["over"] = f"over the last {len(bars) - 1} sessions"
        return out


def stock_points() -> list[tuple[str, float]]:
    """Your stocks at each close since the managed book started: the book's value less the money set aside for options and the cash, the
    cash at each close rebuilt from the book's own fills (a sale adds its value less costs, a buy takes its value and costs)."""
    try:
        rows = [json.loads(x) for x in (views.DATA / "paper" / "account" / "benchmark.jsonl").read_text().splitlines() if x.strip()]
        fills = [json.loads(x) for x in (views.DATA / "paper" / "managed" / "ledger.jsonl").read_text().splitlines() if x.strip()]
    except (OSError, ValueError):
        return []
    mb = IS._managed()
    cash_now, opts = mb.get("cash_inr"), mb.get("options_inr") or 0
    if not isinstance(cash_now, (int, float)):
        return []
    fills = [f for f in fills if f.get("filled") and isinstance(f.get("value_inr"), (int, float))]
    delta = lambda f: (f["value_inr"] - (f.get("cost_inr") or 0)) if str(f.get("side")).upper() == "SELL" else (-f["value_inr"] - (f.get("cost_inr") or 0))  # noqa: E731
    out = []
    for r in rows:
        d, v = str(r.get("day") or ""), r.get("managed_inr")
        if not d or not isinstance(v, (int, float)):
            continue
        cash = cash_now - sum(delta(f) for f in fills if str(f.get("for_session") or "") > d)
        out.append((d, round(v - opts - cash)))
    stocks_now = mb.get("stocks_inr")
    if out and isinstance(stocks_now, (int, float)) and str(mb.get("day") or "") >= out[-1][0]:
        out[-1] = (out[-1][0], stocks_now)                                           # the book's own figure for its last close
    return out


def stock_return(values: list[tuple[str, float]] | None = None) -> list[tuple[str, float]]:
    """The stocks' own return since the book started, in %, one point a close: a session's sales and buys are taken out first, so selling a
    cut stock into cash is not counted as a loss (2 Nov: ₹43,412 sold, ₹29,058 bought)."""
    vals = values if values is not None else stock_points()
    try:
        fills = [json.loads(x) for x in (views.DATA / "paper" / "managed" / "ledger.jsonl").read_text().splitlines() if x.strip()]
    except (OSError, ValueError):
        fills = []
    flow: dict[str, float] = {}
    for f in fills:
        if f.get("filled") and isinstance(f.get("value_inr"), (int, float)):
            d = str(f.get("for_session") or "")
            flow[d] = flow.get(d, 0.0) + (f["value_inr"] if str(f.get("side")).upper() == "BUY" else -f["value_inr"])
    out, g = [], 1.0
    for i, (d, v) in enumerate(vals):
        if i and vals[i - 1][1]:
            g *= (v - flow.get(d, 0.0)) / vals[i - 1][1]
        out.append((d, round(100 * (g - 1), 2)))
    return out


def option_points() -> list[tuple[str, float]]:
    """The options line at each scored session: the money set aside plus its running result on one option lot (realistic fills)."""
    o = IS._safe(views.options) or {}
    cap = o.get("capital_inr") or 50000
    rows = IS._safe(IS._sp1_outcomes) or []                  # 12 Nov (G-01): one row per trade, never counted twice
    by: dict[str, float] = {}
    for r in rows:
        net = ((r.get("legs") or {}).get("option") or {}).get("net_rs_realistic")
        if r.get("date"):
            by[str(r["date"])] = by.get(str(r["date"]), 0.0) + (net if isinstance(net, (int, float)) else 0.0)
    if not by:
        return []
    days = sorted(by)
    out, run = [((dt.date.fromisoformat(days[0]) - dt.timedelta(days=1)).isoformat(), float(cap))], 0.0
    for d in days:
        run += by[d]
        out.append((d, round(cap + run)))
    return out


def candles(name: str, rng: str | None = None, tf: str | None = None, full: bool = True, fetch=None) -> dict:
    """/india/v3/candles/<name>: NIFTY, BANKNIFTY or VIX (candles), STOCKS or OPTIONS (Madhav's history, the owner only)."""
    from jarvis import chartkit as CK
    key = str(name or "").upper().replace("%20", " ").strip()
    if key in ("STOCKS", "OPTIONS"):
        if not full:
            raise PermissionError("This chart shows Madhav's account.")
        if key == "STOCKS":
            return CK.history("Your stocks", "india", stock_return(), rng, ccy="%", tz_min=330,
                              note="The stocks' own return since the book started, one point a session at the close. Sales and buys are taken out, "
                                   "so selling a cut stock into cash is not a loss.")
        return CK.history("The options line", "india", option_points(), rng, ccy="₹", tz_min=330,
                          note="One point a scored session: the money set aside plus the line's result on one option lot, on paper.")
    key = CHART_KEYS.get(key.replace(" ", ""), key)
    if key not in KEY_NAME:
        raise KeyError(name)
    return index_candles(key, rng, tf, fetch=fetch)


def _num(x) -> str:
    return f"{x:,.2f}" if isinstance(x, (int, float)) else "—"


def _vix(t: dict) -> dict | None:
    """The fear gauge as every surface shows it (12 Nov 2026, the keen outside audit, G-05): from the same Kite read and under the same day
    as the Nifty boxes (surfaces._index_tile), or None when that read had no value."""
    v = ((t.get("tiles") or [{}])[0] or {}).get("vix") or {}
    return v if v.get("value") else None


def _vix_change(v: dict) -> str | None:
    """The gauge's change on the day, signed, with no good or bad colour: a falling gauge is calmer, not a loss."""
    c = v.get("change_pct")
    return (("+" if c > 0 else "−" if c < 0 else "") + f"{abs(c):.1f}%") if isinstance(c, (int, float)) else None


def index_page(slug: str, full: bool = True) -> dict:
    """Nifty 50, Bank Nifty or the fear gauge: the number, its chart with ranges and timeframes, its levels and what it says."""
    key, name = IDX_PAGES[slug]
    t = IS.today(full)
    tech = _tech().get(key) or {}
    sym = {"NIFTY 50": "NIFTY", "NIFTY BANK": "BANKNIFTY", "INDIA VIX": "VIX"}[key]
    if slug == "vix":
        vx = _vix(t)
        if vx:                                    # 12 Nov (G-05): the same value and day as Markets and the Nifty boxes
            hero = K.hero(name, vx["value"], change=_vix_change(vx), since=vx.get("when"))
        else:                                     # no Kite read on the tile: the day's candles, or a dash, never a number cut from a sentence
            c = IS._safe(index_candles, key, "1D", None) or {}
            last, pct = c.get("last"), c.get("change_pct")
            ok = isinstance(last, (int, float)) and not c.get("fell_back")
            hero = K.hero(name, f"{last:.2f}" if ok else "—", change=_pct(pct) if ok and isinstance(pct, (int, float)) else None,
                          since="on the day" if ok and isinstance(pct, (int, float)) else None)   # 11 Nov (board 190): it read
                          # "-5.63% the swing traders expect over 30 days", the day's change beside what the gauge means
        pts = ["The fear gauge measures how much traders expect the Nifty to swing over the next 30 days, as a yearly percentage",
               "Higher means traders expect bigger swings; lower means calm",
               {"text": "Ananta reads it before the open: a high reading makes the options line more careful", "icon": "info"}]
        kv = []
    else:
        p, chg = _index_box(t, name)
        hero = K.hero(name, p.get("value") or "—", change=chg, tone=p.get("tone"), since=str(p.get("sub2") or "") or None)
        sma = tech.get("sma") or {}
        sup, res = tech.get("support") or {}, tech.get("resistance") or {}
        kv = [K.kvrow("Last close", _num(tech.get("close")), v_sub=IS._dw(tech.get("as_of")) if tech.get("as_of") else None),
              K.kvrow("50-day average", _num(sma.get("50"))), K.kvrow("200-day average", _num(sma.get("200"))),
              K.kvrow("52-week high", _num(tech.get("high_52w"))), K.kvrow("52-week low", _num(tech.get("low_52w"))),
              K.kvrow("Support", _num(sup.get("swing_low") or sup.get("round"))), K.kvrow("Resistance", _num(res.get("swing_high") or res.get("round"))),
              K.kvrow("RSI, 14 days", f"{tech['rsi14']:.0f}" if isinstance(tech.get("rsi14"), (int, float)) else "—", v_sub=tech.get("rsi_zone"))] if tech else []
        words = re.sub(r"^NIFTY (50|BANK) ", "", str(tech.get("words") or ""))
        pts = [K.clip(x[:1].upper() + x[1:], 22, 160) for x in re.split(r";\s+|:\s+(?=above|below)", words.rstrip(".")) if x.strip()][:4]
    parts = [hero, K.pricechart(sym, name),
             K.kv(kv, title="Levels") if kv else None,
             K.points(pts, title="What it says") if pts else None,
             K.trust("Candles from Zerodha's feed, read-only. Levels from the daily closes on file. A description, never a rule.")]
    return K.page(name, parts, bar_kind="close", ask_q=f"Tell me about the {name} now: its trend, its levels and what would change your view.")


def stocks_page(full: bool = True) -> dict:
    """Home's In stocks box: your stocks over time, the biggest holdings, and the whole portfolio one tap away."""
    m = IS.money(full)
    ret = stock_return()
    now = m.get("stocks_inr")
    last = ret[-1][1] if ret else None
    hs = sorted(m.get("holdings") or [], key=lambda h: -(h.get("value_inr") or 0))
    mb = IS._managed()
    own = sorted(mb.get("holdings") or [], key=lambda x: -(x.get("value_inr") or 0))
    parts = [K.hero("Your stocks · on paper", _rs(now), change=_pct(last) if last is not None else None, tone=_tone(last),
                    since=f"since {IS._dw(ret[0][0])}, sales and buys taken out" if ret else None),
             K.pricechart("STOCKS", "Your stocks", kind="line", private=True),
             # 12 Nov 2026 (audit repair 4, G-06): the book's own positions under the book's total (the real holdings were listed here)
             K.rows("In the managed book", [book_row(x) for x in own[:5]], count=len(own), sub="on paper, biggest first",
                    more=K.to_page(book_page(own, mb.get("marks")))) if own else None,
             K.rows(None, [K.row("Your Zerodha holdings", f"{len(hs)} · as you have them, graded", to=K.to_page(holdings_page(hs)))], plain=True) if hs else None,
             K.trust("Stocks only: the money set aside for options and the cash are not in this line. Paper only.")]
    return K.page("Your stocks", parts, ask_q="How are my stocks doing since the managed book started, and which holdings carry it?",
                  second={"label": "Show the portfolio", "to": K.place("account")})


def _left_out() -> str:
    """The options line's trades with no result yet, in words ("1 trade left out: Fri 6 Nov Bank Nifty, not scored yet"), or "".
    12 Nov 2026 (audit repair 4, G-01; Madhav's yes of 12 Nov 01:52): the 6 Nov Bank Nifty trade is scored at the next regular open and
    marked scored late; until then no total may leave it out without saying so (the Options hero and By index said nothing)."""
    return IS._safe(IS.sp1_left_out_words) or ""


def option_trades_page(rows: list[dict]) -> dict:
    return K.page("Options trades", [K.hero("Options trades", str(len(rows)), since="on paper, one option lot each"),
                                     K.rows(None, [_trade_row(r) for r in rows], plain=True),
                                     K.trust("Realistic fills. A trade with no result stays in the list, marked.")],
                  ask_q="Walk me through the options line's trades: what worked, what did not, and why.")


def _trade_row(r: dict) -> dict:
    net = ((r.get("legs") or {}).get("option") or {}).get("net_rs_realistic")
    side = "short" if r.get("dir") == -1 else "long"
    return K.row(f"{IDX.get(r.get('index'), r.get('index'))} · {side}", IS._dw(r.get("date")) + (" · scored late" if r.get("scored_late") else ""),
                 right=_rs(net, sign=True) if isinstance(net, (int, float)) else "No result",
                 right_tone=_tone(net) if isinstance(net, (int, float)) else None, icon="bars")



PLACES = {"home": home, "markets": markets, "activity": activity, "more": more, "account": account, "proof": proof, "plan": lambda full=True: plan_page(IS.money(full), IS.today(full)),
          "holdings": lambda full=True: holdings_page(sorted(IS.money(full).get("holdings") or [], key=lambda h: -(h.get("value_inr") or 0))),
          "options": options_page, "people": people, "morning": lambda full=True: morning_page(), "stocks": stocks_page,
          "nifty": lambda full=True: index_page("nifty", full), "banknifty": lambda full=True: index_page("banknifty", full),
          "vix": lambda full=True: index_page("vix", full)}


# 12 Nov 2026 (the keen audit, G-51): a guest was refused seven pages by name and got the rest (the options record, Proof, More, the people
# list, the morning view). The list now says what a guest MAY open, the three index pages, so a new page is closed to guests by default.
GUEST_PLACES = ("nifty", "banknifty", "vix")


def _guest(name):
    def f(full: bool = True):
        if not full and name not in GUEST_PLACES:
            return {"ready": False, "kind": "place", "name": name, "words": "This page shows Madhav's account. A guest's own book is on the practice screens."}
        return PLACES[name](full=full)
    return f


for _n in PLACES:
    views.ROUTES[f"place/{_n}"] = _guest(_n)
