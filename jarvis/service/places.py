"""Crypto's places for the redesign (Madhav, 10 Nov 2026: "yes for all your recommendations. lets complete it and test it as planned").

Five places replace the five tabs that mixed levels: Home, Markets, Ask (unchanged), Activity, More. Each place, and each page one tap
under it, is a short list of parts written here in plain words (jarvis/placekit.py has the parts and the eight rules). Everything is
read from what the surfaces already read (jarvis/service/surfaces.py): the $500 book, the dial, the setups scan, the nightly note, the
change book and the one open list. Nothing is lost: the old first-layer cards are now pages one tap down, in the same words.
Read-only. Nothing here trades, writes a rule or changes the book."""
from __future__ import annotations

import datetime as dt
import json
import re

from jarvis import placekit as K
from jarvis.service import surfaces as S

NAMES = {**S.COIN_NAME, "ADA": "Cardano", "DOGE": "Dogecoin", "AVAX": "Avalanche", "BCH": "Bitcoin Cash", "LINK": "Chainlink", "LTC": "Litecoin", "XRP": "XRP"}
AREA = {"app": "The app", "approvals": "Your decision", "ask": "Ask", "briefings": "Briefings", "crypto_books": "The book", "crypto_dial": "The dial",
        "data": "Data", "jobs": "Night jobs", "managed_book": "The managed book", "notes_and_flags": "Notes and the list", "options": "Options",
        "other": "A change", "people": "People", "reconstruction": "The evidence", "research": "Research", "rules": "Rules", "safety": "Safety",
        "self_knowledge": "Self-check", "signin": "Sign-in", "stocks": "Stocks", "today_screen": "Screens", "voice": "Voice", "watchdog": "The watchdog"}
STATUS = {"decided": "Your yes", "live": "Live", "built": "Built", "parked": "Parked", "reverted": "Undone"}
DAYS_BACK = 21


def _name(c) -> str:
    return NAMES.get(str(c), str(c))


def _day(t) -> str:
    return dt.datetime.fromtimestamp(float(t), S.UTC).strftime("%Y-%m-%d")


def _ctx(j) -> dict:
    """One read of everything the places share."""
    from jarvis.service import discipline, feed, health, openlist
    now = dt.datetime.now(S.TOR)
    b, dial = S._book(j), S._dial(j)
    return {"now": now, "b": b, "dial": dial, "pos": S._positions(b), "brake": S._brake(b, now), "open": (dial.get("dial") or 0) > 0,
            "closes": S._safe(feed.last_closes, j, default={}) or {}, "health": S._safe(health.status, j, default={}) or {},
            "plan": S._safe(discipline.plan_line, j, default={}) or {}, "list": S._safe(openlist.collect, j, default={}) or {}}


# ------------------------------------------------------------------------------------------------ what waits for Madhav (the open list)
def _rest(line, title: str) -> str:
    """An open-list line without the title the sheet already shows."""
    s = str(line or "").strip()
    if title and s.lower().startswith(title.lower().rstrip("…")):
        r = s[len(title.rstrip("…")):].lstrip(" :.,")
        return (r[:1].upper() + r[1:]) if r else s
    return s


def you_rows(col: dict, market: str = "crypto") -> list[dict]:
    """The open list's "needs your yes" as rows; a tap opens a bottom sheet with the whole line and the advice (one thing at a time)."""
    out = []
    for it in col.get("you") or []:
        if it.get("market") not in (market, "both", None):
            continue
        t, sub = K.title_sub(it.get("line") or "")
        adv = str(it.get("advice") or "")
        step = "step" in adv.lower() or "your step" in str(it.get("line") or "").lower()
        out.append(K.row(t, sub, right="Your step" if step else "Your yes", icon="you", tint="bronze", tag="you",
                         to=K.sheet(t, _rest(it.get("line"), t), advice=(adv[:1].upper() + adv[1:]) if adv else None, icon="you",
                                    primary={"label": "Talk to Ananta about it", "to": K.ask(f"About {it.get('id')}: {t}. What do I need to do, and what happens after?")})))
    return out


def openlist_page(j, c: dict | None = None, market: str = "crypto") -> dict:
    from jarvis.service import openlist
    col = (c or {}).get("list") or S._safe(openlist.collect, j, default={}) or {}
    def sec(title, key, right):
        items = [x for x in col.get(key) or [] if x.get("market") in (market, "both", None)]
        rs = []
        for it in items[:40]:
            t, sub = K.title_sub(it.get("line") or "")
            rs.append(K.row(t, sub, right=(S._dm(it["due"]) if it.get("due") else str(it.get("id") or "")), icon=right,
                            to=K.sheet(t, _rest(it.get("line"), t), advice=str(it.get("advice") or "")[:1].upper() + str(it.get("advice") or "")[1:] if it.get("advice") else None, icon=right,
                                       primary={"label": "Ask Ananta about it", "to": K.ask(f"Tell me about {it.get('id')} on the open list.")})))
        return K.rows(title, rs, count=len(items)) if rs else None
    n = col.get("counts") or {}
    parts = [K.hero("The open list", f"{n.get('YOU', 0)} need you", since=f"{n.get('WORK', 0)} to do · {n.get('DATE', 0)} wait for a date · {n.get('PARKED', 0)} parked"),
             sec("Needs you", "you", "you"), sec("Work to do", "work", "tool"), sec("Waiting for a date", "dated", "clock"), sec("Parked on purpose", "parked", "pause"),
             K.trust("This is the only place that says what is open. Something not on it is done or dropped.")]
    return K.page("The open list", parts, ask_q="What is on the open list today, and what needs me first?")


# ------------------------------------------------------------------------------------------------ the information page: why buying is on or off
def why(j, c: dict | None = None) -> dict:
    c = c or _ctx(j)
    dial, now, is_open = c["dial"], c["now"], c["open"]
    pts = S._dial_points(dial, c["closes"], now)
    n = S._dial_numbers(dial)
    items = [{"text": p, "tone": ("bad" if " below its" in p else "good" if " above its" in p else None)} for p in pts[:4]]
    under = [k for k in ("50", "200") if n.get("side" + k) == "below"]
    one = (f"Bitcoin closed under its {' and '.join(u + '-day' for u in under)} average{'s' if len(under) > 1 else ''}, so cash is the position."
           if not is_open and under else "Bitcoin closed above both its averages, so buying is allowed." if is_open else "Buying is off: cash is the position.")
    ch = S._safe(S.coin_chart, j, "BTC", default={}) or {}
    cc = ch.get("chart") or {}
    lines = [{"values": K.thin((cc.get("sma200") or [])[-60:], 12), "style": "dot", "color": "dim"},
             {"values": K.thin((cc.get("sma50") or [])[-60:], 20), "style": "dash", "color": "dim"},
             {"values": K.thin((cc.get("closes") or [])[-60:], 60), "style": "main", "color": "ink"}]
    parts = [K.chart(lines, legend=[{"label": "Bitcoin", "style": "main"}, {"label": "50-day average", "style": "dash"}, {"label": "200-day", "style": "dot"}],
                     label="Bitcoin's daily closes for 60 days with its 50-day and 200-day averages") if cc.get("closes") else None,
             K.pill("Buying is on" if is_open else "Buying is off", icon="play" if is_open else "pause", tone="good" if is_open else None),
             K.heading("Why Ananta may buy" if is_open else "Why Ananta is not buying"),
             K.line(one), K.points(items),
             K.points([c["brake"][:1].upper() + c["brake"][1:]], title="Also") if c.get("brake") else None,
             K.trust(f"Checked again at the daily close, {S._next_close_words(now)}. Prices are in US dollars.")]
    state = "open" if is_open else "closed"
    return K.page("The dial", parts, bar_kind="close",
                  ask_q=f"Explain the dial in detail: what it reads, why it is {state} today, how close Bitcoin is to changing it, and what the $500 book does in each state.",
                  second={"label": "What would close it?" if is_open else "What would reopen it?",
                          "ask": "What exactly would close the dial, and how close is Bitcoin to it?" if is_open else "What exactly would reopen the dial, and how close is Bitcoin to it?"})


def coin_page(j, coin: str) -> dict:
    """Ethereum or Solana from Markets: the chart and the last close in a few lines (Bitcoin opens the dial's page)."""
    ch = S._safe(S.coin_chart, j, coin, default={}) or {}
    cc = ch.get("chart") or {}
    name = _name(coin)
    lines = [{"values": K.thin((cc.get("sma200") or [])[-60:], 12), "style": "dot", "color": "dim"},
             {"values": K.thin((cc.get("sma50") or [])[-60:], 20), "style": "dash", "color": "dim"},
             {"values": K.thin((cc.get("closes") or [])[-60:], 60), "style": "main", "color": "ink"}]
    pts = [S._plain(x) for x in S._sentences(ch.get("words") or "")][:4]
    parts = [K.chart(lines, legend=[{"label": name, "style": "main"}, {"label": "50-day average", "style": "dash"}, {"label": "200-day", "style": "dot"}],
                     label=f"{name}'s daily closes for 60 days with its two averages") if cc.get("closes") else None,
             K.heading(name), K.points(pts) if pts else K.line("No daily closes on file for this coin yet."),
             K.trust(str(ch.get("note") or "Daily closes in US dollars."))]
    return K.page(name, parts, bar_kind="close", ask_q=f"How is {name} doing, and does Ananta have a setup on it?")


# ------------------------------------------------------------------------------------------------ trades: rows and receipts
def _fills(j) -> list[dict]:
    try:
        rows = j.db.execute("SELECT t, coin, side, sleeve, qty, px, fee, why FROM book500_fills ORDER BY t").fetchall()
    except Exception:  # noqa: BLE001
        return []
    return [dict(zip(("t", "coin", "side", "sleeve", "qty", "px", "fee", "why"), tuple(r))) for r in rows]


def _buy_why(f: dict) -> str:
    w = str(f.get("why") or "")
    if str(f.get("sleeve") or "").upper() == "CORE" or w.startswith("core"):
        return "First buy of the core" if "tranche 1" in w else "The dial opened" if w == "dial open" else "A buy for the core"
    if "RSI" in w or "short dip" in S._plain(w):
        return "A short dip in an uptrend"
    return K.clip(S._tidy(S._why(w)), 6, 40)


def _sell_why(why) -> str:
    w = S._why(why)
    if re.match(r"^\d+ days$", w):
        return f"Held {w}"
    if "RSI" in w:
        return "Its exit rule fired"
    if w.startswith("a daily close under its own 50-day"):
        return "Closed under its own 50-day average"
    return K.clip(S._tidy(w), 7, 40)


def receipt(cl: dict, fills: list[dict]) -> dict:
    coin, name = cl.get("coin"), _name(cl.get("coin"))
    buys = [f for f in fills if f["coin"] == coin and f["side"] == "BUY" and _day(f["t"]) == cl.get("in")]
    sells = [f for f in fills if f["coin"] == coin and f["side"] == "SELL" and _day(f["t"]) == cl.get("out")]
    if cl.get("sleeve"):
        buys = [f for f in buys if str(f.get("sleeve")) == str(cl["sleeve"])] or buys
        sells = [f for f in sells if str(f.get("sleeve")) == str(cl["sleeve"])] or sells
    amt = lambda fs: sum((f.get("qty") or 0) * (f.get("px") or 0) for f in fs)   # noqa: E731
    pnl, pct = cl.get("pnl_cad"), cl.get("pct")
    tone = S._tone(pnl)
    g1 = []
    if buys:
        g1.append(K.kvrow("Bought", S._cad(amt(buys)), k_sub=S._dw(cl.get("in")), v_sub=f"at {S._cad(buys[-1]['px'])}"))
    else:
        g1.append(K.kvrow("Bought", S._dw(cl.get("in"))))
    if sells:
        g1.append(K.kvrow("Sold", S._cad(amt(sells)), k_sub=S._dw(cl.get("out")), v_sub=f"at {S._cad(sells[-1]['px'])}"))
    else:
        g1.append(K.kvrow("Sold", S._dw(cl.get("out"))))
    if buys and sells:
        g1.append(K.kvrow("Fees", S._cad(sum((f.get("fee") or 0) for f in buys + sells))))
    g1.append(K.kvrow("Result", S._cad(pnl), tone=tone, bold=True))
    g2 = [K.kvrow("Amount", f"{sum(f.get('qty') or 0 for f in buys):.8f}".rstrip("0").rstrip(".") + f" {coin}") if buys else None,
          K.kvrow("Why bought", _buy_why(buys[-1])) if buys else None,
          K.kvrow("Why sold", _sell_why(cl.get("why")))]
    parts = [K.hero(f"Sold {name} · {S._dw(cl.get('out'))}", S._cad(pnl), change=(S._pct(pct, 2) if isinstance(pct, (int, float)) else None), tone=tone, since="on paper"),
             K.kv(g1), K.kv(g2),
             K.link("Why did the dial close?", K.place("why")) if S._why(cl.get("why")) == "the dial closed" else None,
             K.trust("Paper only, at real NDAX prices.")]
    return K.page("Trade", parts, ask_q=f"Tell me about the {name} trade the $500 book closed on {S._dw(cl.get('out'))}: why it was bought, why it was sold, and what it taught.")


def trade_rows(j, c: dict) -> list[tuple]:
    """(day, order, row) for every sale (with its receipt) and every buy of the $500 book."""
    fills = _fills(j)
    out = []
    for cl in c["b"].get("closed") or []:
        pnl = cl.get("pnl_cad")
        out.append((str(cl.get("out")), 2, K.row(f"Sold {_name(cl.get('coin'))}", _sell_why(cl.get("why")), right=S._cad(pnl), right_tone=S._tone(pnl), icon="down",
                                                tag="trade", to=K.to_page(receipt(cl, fills)))))
    for f in fills:
        if f["side"] == "BUY":
            out.append((_day(f["t"]), 3, K.row(f"Bought {_name(f['coin'])}", _buy_why(f), right=S._cad((f.get("qty") or 0) * (f.get("px") or 0)), icon="up", tag="trade")))
    return out


# ------------------------------------------------------------------------------------------------ changes and notes
KEEP_CAPS = {"NDAX", "NIFTY", "BTC", "ETH", "SOL", "NSE", "TCS", "LICI", "IRFC", "JIOFIN"}


def _calm(s: str) -> str:
    """A line from the change book as a screen shows it: a word in capitals is said in small letters, a file name is left out."""
    s = re.sub(r"\b[A-Z][A-Z_]{4,}\b", lambda m: m.group(0) if m.group(0) in KEEP_CAPS else m.group(0).lower().replace("_", " "), str(s or ""))
    s = re.sub(r"\(?\b[\w./-]+\.(py|tsx|ts|json|jsonl|md)\b\)?", "", s)
    return re.sub(r"\s{2,}", " ", s).strip()


def change_rows(market: str, since: str) -> list[tuple]:
    from jarvis import selfknow
    out = []
    for i, ch in enumerate(selfknow.changes()):
        if str(ch.get("date") or "") < since or ch.get("market") not in (market, "both"):
            continue
        words = _calm(S._plain(str(ch.get("words") or "")))
        fix = bool(re.match(r"(?i)\s*(fixed|repaired|corrected|a fix)\b", words))
        title = str(ch.get("title") or AREA.get(ch.get("area"), "A change"))
        pg = K.page(title, [K.pill(STATUS.get(ch.get("status"), str(ch.get("status") or "")), icon="check"), K.heading(title),
                            K.points(S._sentences(words)),
                            K.points([_calm(x) for x in S._sentences(str(ch.get("why") or ""))[:3]], title="Why") if ch.get("why") else None,
                            K.trust(f"From the change book · {S._dw(ch.get('date'))}")],
                    ask_q=f"Tell me about this change of {S._dw(ch.get('date'))}: {K.clip(words, 16, 110)}")
        gist = re.sub(r"^(Decided( on Madhav's yes( to)?)?|Fixed|Repaired|Corrected|A fix)\s*[:,]?\s*", "", words, flags=re.I).strip() or words
        out.append((str(ch.get("date")), 1 - i / 100000.0, K.row(title, K.clip(gist[:1].upper() + gist[1:], 8, 46), right="Fixed" if fix and ch.get("status") == "live" else STATUS.get(ch.get("status")),
                                                                icon="pencil" if fix else "check",
                                                                tag="fix" if fix else "change", to=K.to_page(pg))))
    return out


def note_rows(j, c: dict) -> list[tuple]:
    from jarvis.service import nightcheck, officer
    out = []
    notes = S._safe(officer.latest, j, 7, default=[]) or []
    late = S._safe(S._repairs, j, default=[]) or []
    for i, n in enumerate(notes):
        text = re.sub(r"^(Good (morning|evening|afternoon),\s*)?[Ss]ir,\s*", "", str(n.get("note") or "")).strip()
        text = text[:1].upper() + text[1:]
        pts = [S._plain(x) for x in S._sentences(text)]
        b = c["b"]
        if i == 0 and isinstance(b.get("value_cad"), (int, float)) and [r for r in late if str(r.get("day") or "") >= str(n.get("day"))]:
            pts.insert(0, f"Corrected after this note was written: the account is {S._cad(b['value_cad'])} ({S._pct(b.get('return_pct'))}), not the figure in the note")
        pg = K.page("Nightly note", [K.heading(f"Ananta's nightly note · {S._dw(n.get('day'))}"), K.points(pts), K.trust("Written by Ananta after the daily close, from the book's own facts.")],
                    ask_q=f"Walk me through your nightly note of {S._dw(n.get('day'))}.")
        out.append((str(n.get("day")), 0, K.row("Nightly note", K.clip(next((x for x in pts if not x.startswith("Corrected")), ""), 7, 44),
                                               icon="note", tag="note", to=K.to_page(pg))))
    nt = S._safe(nightcheck.latest, default=None)
    if nt and nt.get("asked"):
        card = S._safe(S._night_test, default=None) or {}
        pg = K.page("Night test", [K.heading("Night test · Ananta asked and marked"), K.points(card.get("points") or []), K.trust(str(card.get("foot") or ""))],
                    ask_q="What did last night's test ask you, and what did you get wrong?")
        out.append((str(nt.get("day")), 0.5, K.row("Night test", f"{nt.get('right')} of {nt.get('asked')} answers right", right=("All right" if not nt.get("wrong") else f"{len(nt['wrong'])} wrong"),
                                                  right_tone=None if not nt.get("wrong") else "warn", icon="moon", tag="note", to=K.to_page(pg))))
    return out


def _events(j, c: dict, market: str = "crypto") -> list[tuple]:
    since = (c["now"].date() - dt.timedelta(days=DAYS_BACK)).isoformat()
    ev = [e for e in (S._safe(trade_rows, j, c, default=[]) or []) if e[0] >= since]
    ev += S._safe(change_rows, market, since, default=[]) or []
    ev += [e for e in (S._safe(note_rows, j, c, default=[]) or []) if e[0] >= since]
    ev.sort(key=lambda e: (e[0], -e[1]), reverse=True)
    return ev


def activity(j, c: dict | None = None) -> dict:
    c = c or _ctx(j)
    ev = _events(j, c)
    you = you_rows(c["list"])
    parts = [K.chips([{"id": "all", "label": "All"}, {"id": "trade", "label": "Trades"}, {"id": "change", "label": "Changes"}, {"id": "note", "label": "Notes"},
                      {"id": "fix", "label": "Fixes"}, {"id": "you", "label": "For you", "count": len(you) or None}])]
    if you:
        parts.append(K.rows("Waiting for you", you, tags=["you"]))
    days: dict[str, list] = {}
    for d, _o, r in ev:
        days.setdefault(d, []).append(r)
    for d in list(days)[:14]:
        parts.append(K.rows(S._dw(d), days[d][:25]))
    if not ev:
        parts.append(K.line("Nothing has happened in the last three weeks."))
    return K.surface("activity", "crypto", parts, bell=len(you), title="Activity")


# ------------------------------------------------------------------------------------------------ Home
def _headline(c: dict) -> tuple[str, str]:
    h = S.headline(c["dial"], c["pos"], c["brake"])
    a, _, b2 = h.partition(": ")
    line = (a + (". " + b2[:1].upper() + b2[1:] if b2 else "")).rstrip(".") + "."
    if c["brake"]:
        sub = K.clip(c["brake"][:1].upper() + c["brake"][1:], 12, 80) + "."
    elif not c["open"]:
        sub = "The coins held stay until their own rules sell." if c["pos"] else "Buying is off until Bitcoin closes above both its averages."
    else:
        sub = "Buying is on: Bitcoin closed above both its averages."
    return line, sub


def home_notices(j, c: dict) -> list[dict]:
    from jarvis.service import nightcheck
    out = []
    run = S._running(c["health"])
    if not run.get("ok"):
        out.append(K.notice("run:" + c["now"].strftime("%Y-%m-%d"), K.clip(run.get("words"), 10, 70), K.ask("Is everything running? What is down, since when, and what does it affect?")))
    under = S.gap_words(S._safe(S.book_gap, j, c["b"], default=[]) or [])
    if under:
        out.append(K.notice("gap:" + c["now"].strftime("%Y-%m-%d"), "The book's trades and its coins do not agree", K.ask("The book's trades and holdings do not agree. What is the difference?")))
    nt = S._safe(nightcheck.latest, default=None)
    if nt and nt.get("asked"):
        out.append(K.notice("nt:" + str(nt.get("day")), f"Night test: {nt.get('right')} of {nt.get('asked')} answers right", K.tab("activity")))
    else:
        out.append(K.notice("nt:first", f"Night test: first run tonight, after {S._next_close_words(c['now']).replace(' Toronto', '')}", K.place("proof")))
    note = S._officer_note(j)
    late = [r for r in (S._safe(S._repairs, j, default=[]) or []) if note and str(r.get("day") or "") >= str(note["day"])]
    if late:
        out.append(K.notice("fix:" + str(note["day"]), "A figure in last night's note was corrected", K.tab("activity")))
    fails = [x for x in (c["plan"].get("checks") or []) if x.get("state") == "FAIL"]
    if fails:
        out.append(K.notice("chk:" + c["now"].strftime("%Y-%m-%d"), f"{len(fails)} check{'s' if len(fails) != 1 else ''} fail{'' if len(fails) != 1 else 's'} tonight", K.ask("Which of your checks fail today, and why?")))
    return out[:3]


def _coin_boxes(j, pages: list[dict]) -> list[dict]:
    """Home's first box: the three coins, each with its price now, its move since the daily close and its last 60 closes."""
    out = []
    for p in pages:
        chg, _, since = str(p.get("sub") or "").partition(" ")
        ok = chg[:1] in "+−-"
        cc = (S._safe(S.coin_chart, j, p.get("coin") or "BTC", default={}) or {}).get("chart") or {}
        out.append(K.box(p.get("label"), p.get("value") or "—", change=chg if ok else None, tone=p.get("tone"), since=since if ok else None,
                         caption=None if ok else K.clip(p.get("sub"), 4, 24), spark=K.thin((cc.get("closes") or [])[-60:], 30),
                         to=K.place("why") if p.get("coin") == "BTC" else K.place("coin:" + str(p.get("coin")))))
    return out


def home(j) -> dict:
    c = _ctx(j)
    b, pos, now = c["b"], c["pos"], c["now"]
    value, ret = b.get("value_cad"), b.get("return_pct")
    start = S._start_cad()
    run = S._running(c["health"])
    line, sub = _headline(c)
    pages = S._coin_pages(j, c["dial"], now, c["closes"])
    coins = sum(p["value"] or 0 for p in pos)
    you = you_rows(c["list"])
    ev = _events(j, c)
    did, seen = [], set()
    for _d, _o, r in ev:                                  # the newest note, change and trade: one of each kind
        if r.get("tag") in ("note", "change", "fix", "trade") and r["tag"] not in seen and not (r["tag"] == "fix" and "change" in seen):
            seen.add("change" if r["tag"] == "fix" else r["tag"])
            did.append({**r, "right": r.get("right") if r.get("tag") == "trade" else None, "right_sub": None})
        if len(did) == 3:
            break
    parts = [K.hero("Your paper account", S._cad(value), change=(f"{S._cad(value - start)} ({S._pct(ret)})" if isinstance(value, (int, float)) and isinstance(ret, (int, float)) else None),
                    tone=S._tone(ret), since=f"since {S._dw(b.get('started'))}" if b.get("started") else None,
                    status={"ok": bool(run.get("ok")), "words": "Running" if run.get("ok") else "Needs a look"}),
             K.today("Today", line, sub, to=K.place("why")),
             K.boxes([K.paged(_coin_boxes(j, pages)),
                      K.paged([K.box("In coins", S._cad(coins, 0), bar=[round(coins / value, 3) if value else 0],
                                     caption="All in cash" if not pos else f"{len(pos)} coin{'s' if len(pos) != 1 else ''}", to=K.place("account")),
                               K.box("Cash", S._cad(b.get("cash_cad"), 0), bar=[0, round((b.get("cash_cad") or 0) / value, 3) if value else 0],
                                     caption=f"{round(100 * (b.get('cash_cad') or 0) / value)}% of the book" if value else None, to=K.place("account"))])]),
             K.rows("Needs you", you[:3], count=len(you), badge=True, more=K.place("notices")) if you else None,
             K.rows("What Ananta did", did, more=K.tab("activity")) if did else None,
             K.notices(home_notices(j, c))]
    return K.surface("home", "crypto", parts, bell=len(you), title="Home")


# ------------------------------------------------------------------------------------------------ Markets
def _setups(parts: dict) -> dict:
    s = str(parts.get("Setups") or "")
    m = re.match(r"Scanned (\d+) coins: (\d+) setups? fired, (\d+) one step away", s)
    best = re.findall(r"\b([A-Z0-9]{2,12}) \(([^)]+)\)", s.split("Best:", 1)[-1]) if "Best:" in s else []
    hb = str(parts.get("Held back") or "")
    held = [re.sub(r"\s+(H07|BRK|PULL|RBD|ZONE_TOUCH)$", "", x.strip().rstrip(".")) for x in hb.rsplit(": ", 1)[-1].split(",")] if ": " in hb else []
    held_why = {x.strip().rstrip(".").split(" ")[0]: S.CODE_WORDS.get(x.strip().rstrip(".").split(" ")[-1], "") for x in hb.rsplit(": ", 1)[-1].split(",")} if ": " in hb else {}
    touched = re.findall(r"\b([A-Z0-9]{2,12}) \(([A-Z0-9_]+)\)", str(parts.get("Touched") or ""))
    st = str(parts.get("Strongest") or "")
    strong = [x.strip().rstrip(".") for x in st.rsplit(": ", 1)[-1].split(",")] if ": " in st else []
    days = (re.search(r"over (\d+) days", st) or [None, "20"])[1]
    return {"scanned": int(m.group(1)) if m else None, "fired": int(m.group(2)) if m else None, "near": int(m.group(3)) if m else None,
            "best": best, "held": [h for h in held if h], "held_why": held_why, "touched": touched, "strong": [x for x in strong if x], "days": days}


def markets(j) -> dict:
    c = _ctx(j)
    now, is_open = c["now"], c["open"]
    pages = S._coin_pages(j, c["dial"], now, c["closes"])
    cards = []
    for p in pages:
        chg, _, _since = str(p.get("sub") or "").partition(" ")
        cards.append(K.box(p.get("label"), p.get("value"), change=chg if chg[:1] in "+−-" else None, tone=p.get("tone"), caption=None if chg[:1] in "+−-" else K.clip(p.get("sub"), 4, 24),
                           to=K.place("why") if p.get("coin") == "BTC" else K.place("coin:" + str(p.get("coin")))))
    day, close_at = S._last_close(c["dial"])
    since = f"Since {S._clock(close_at)} Toronto" if close_at and (now - close_at) < dt.timedelta(hours=24, minutes=30) else (f"Since {S._dw(day)}" if day else "")
    n = S._dial_numbers(c["dial"])
    gap = lambda k: 100 * (n["close"] / n[k] - 1) if n.get("close") and n.get(k) else None   # noqa: E731
    g50, g200 = gap("avg50"), gap("avg200")
    worst = min([(g, k) for g, k in ((g50, "50-day"), (g200, "200-day")) if g is not None], default=(None, ""))
    state_sub = ((f"Bitcoin is {abs(worst[0]):.1f}% under its {worst[1]} average" if worst[0] is not None and worst[0] < 0 else "Bitcoin is under one of its averages") if not is_open
                 else (f"Bitcoin is {abs(worst[0]):.1f}% above its {worst[1]} average" if worst[0] is not None else "Bitcoin is above both its averages"))
    su = _setups(S._plan_parts(c["plan"].get("line") or ""))
    held = set(su["held"])
    chip = "Held back" if not is_open else None
    best = [K.row(sym, K.clip(S._tidy(S._plain(w).replace(" to the 20-day average", "")), 6, 40), letter=sym[:1], chip=chip if (sym in held or not is_open) else None) for sym, w in su["best"]]
    held_rows = [K.row(sym, S._tidy(su["held_why"].get(sym) or "A setup") + (" in an uptrend" if su["held_why"].get(sym) in ("short dip", "pullback") else ""), letter=sym[:1], chip="Held back") for sym in su["held"]]
    movers = [K.row(sym, f"Touched its {S.CODE_WORDS.get(code, 'trigger')} trigger today", letter=sym[:1]) for sym, code in su["touched"]]
    movers += [K.row(sym, ("Strongest" if i == 0 else "Strong") + f" against Bitcoin, {su['days']} days", letter=sym[:1]) for i, sym in enumerate(x for x in su["strong"] if x not in {s for s, _ in su["touched"]})]
    setup_pts = S._setup_points(S._plan_parts(c["plan"].get("line") or ""))
    all_setups = K.page("Coins being watched", [K.heading("Coins being watched"), K.points(setup_pts),
                                                 K.trust("Held back means seen and noted. Nothing is bought while buying is off." if not is_open else "A setup is a reason to look, never an order.")],
                        ask_q="Which coins show a buy setup today, which are one step away, and what would you do with them?") if setup_pts else None
    you = you_rows(c["list"])
    parts = [K.chips([{"id": "all", "label": "Watched"}, {"id": "setups", "label": "Buy setups", "count": su["fired"]},
                      {"id": "held", "label": "Held back", "count": len(su["held"]) or None}, {"id": "movers", "label": "Movers"}]),
             K.peek(cards, note=" · ".join(x for x in (since, "prices in US dollars") if x), tags=["all"]),
             {**K.rows(None, [K.row("Buying is on" if is_open else "Buying is off", state_sub, to=K.place("why"))], plain=True), "tags": ["all"]},
             K.rows("Buy setups", best[:3], count=su["fired"], more=K.to_page(all_setups), tags=["all", "setups"],
                    foot="Held back: seen and noted. Nothing is bought while buying is off." if not is_open else None) if best else None,
             K.rows("Held back", held_rows[:12], count=len(held_rows), tags=["held"], foot="The brain looks at these again when buying turns on.") if held_rows else None,
             K.rows("Movers", movers[:3], more=K.to_page(all_setups) if len(movers) > 3 else None, tags=["all", "movers"],
                    foot=f"{su['scanned']} coins checked today" if su["scanned"] else None) if movers else None]
    return K.surface("markets", "crypto", parts, bell=len(you), title="Markets", search={"hint": "Search a coin", "route": "/coin/"})


# ------------------------------------------------------------------------------------------------ the account page
def account(j) -> dict:
    c = _ctx(j)
    b, pos, now = c["b"], c["pos"], c["now"]
    m = S.money(j)
    value, ret, start = b.get("value_cad"), b.get("return_pct"), S._start_cad()
    ac = (S._safe(S.account_chart, j, default={}) or {}).get("chart") or {}
    yours = [x for x in (ac.get("yours") or []) if isinstance(x, (int, float))]
    corrected = bool(yours) and isinstance(value, (int, float)) and abs(yours[-1] - value) > 0.5
    lines = [{"values": [x for x in (ac.get("untouched") or []) if isinstance(x, (int, float))], "style": "dash", "color": "dim"},
             {"values": yours + ([round(value, 2)] if corrected else []), "style": "main", "color": "bronze", "last_dash": 1 if corrected else None}]
    fills = _fills(j)
    closed = list(b.get("closed") or [])[::-1]
    won = sum(1 for x in closed if (x.get("pnl_cad") or 0) > 0)
    crow = lambda cl: K.row(_name(cl.get("coin")), f"{S._dm(cl.get('in'))} to {S._dm(cl.get('out'))}", right=S._cad(cl.get("pnl_cad")), right_tone=S._tone(cl.get("pnl_cad")),   # noqa: E731
                            letter=str(cl.get("coin"))[:1], to=K.to_page(receipt(cl, fills)))
    all_closed = K.page("Closed trades", [K.hero("Closed trades", str(len(closed)), since=f"{won} won, {len(closed) - won} lost"), K.rows(None, [crow(x) for x in closed], plain=True),
                                          K.trust("Paper only, at real NDAX prices.")], ask_q="Walk me through the $500 book's closed trades: what worked, what did not, and why.") if closed else None
    coin_rows = [K.row(_name(p["symbol"]), K.clip(str(p.get("chip") or "held"), 7, 44), right=p.get("value_words"), right_sub=(S._pct(p.get("pnl_pct")) if p.get("pnl_pct") is not None else None),
                       right_tone=S._tone(p.get("pnl_pct")), letter=str(p["symbol"])[:1]) for p in pos]
    if not pos:
        coin_rows = [K.row("No coins held", "The whole book is cash")]
    coin_rows.append(K.row("Buying is on" if c["open"] else "Buying is off", f"Next check at {S._next_close_words(now)}", to=K.place("why")))
    win = S._window(now.date())
    books = m.get("books") or []
    parts = [K.hero("The $500 book · on paper", S._cad(value), change=(f"{S._cad(value - start)} ({S._pct(ret)})" if isinstance(value, (int, float)) and isinstance(ret, (int, float)) else None),
                    tone=S._tone(ret), since=f"since {S._dw(b.get('started'))}" if b.get("started") else None),
             K.chart(lines, left=f"{S._dm((ac.get('dates') or [None])[0])} · {S._cad(start, 0)}" if ac.get("dates") else None, right="Today" if corrected else S._dm((ac.get("dates") or [None])[-1]),
                     legend=[{"label": "The $500 book", "style": "main", "color": "bronze"}, {"label": "Bitcoin, just held", "style": "dash"}],
                     caption="One point a night." + (" Corrected on " + S._dw(now.date()) + "." if corrected else ""), baseline=start,
                     label="The account's value each night against Bitcoin just held") if yours else None,
             K.kv([K.kvrow(x.get("label"), S._pct(x.get("ret_pct")), tone=S._tone(x.get("ret_pct")), bold=(i == 0)) for i, x in enumerate(books)], title="How it compares",
                  foot="Nothing is read into the gap before 14 Dec."),
             K.rows("Your coins", coin_rows, plain=True),
             K.points([m["under_check"]], title="Being checked") if m.get("under_check") else None,
             K.rows("Closed trades", [crow(x) for x in closed[:3]], count=len(closed), sub=f"{won} won, {len(closed) - won} lost", more=K.to_page(all_closed)) if closed else None,
             K.bars([K.bar("Evidence window", win["day"], win["of"], right=f"Day {win['day']} of {win['of']}", note=f"No rule changes before {S._dw(S.RULE_B_END)}")])]
    return K.page("Your account", parts, ask_q=m.get("books_ask"), second={"label": "What happens at the next close?", "ask": "What will the $500 book do at the next daily close, and why?"})


# ------------------------------------------------------------------------------------------------ Proof, People, the bell, More
def proof(j) -> dict:
    p = S.proof(j)
    now = dt.datetime.now(S.TOR)
    win = S._window(now.date())
    short = {"The evidence window (Rule A and B)": "Evidence window", "Round trips in the $500 book": "Closed trades", "Clean nights in a row (book, note and candle agree)": "Clean nights in a row"}
    fin = lambda x: S._tidy(K.clip(str(x.get("finish_words") or "").replace("; counted", " · counted"), 9, 60))   # noqa: E731
    bars = [K.bar(short.get(x.get("name"), K.clip(x.get("name"), 5, 30)), x.get("done") or 0, x.get("need") or 1, right=("done" if x.get("complete") else f"{x.get('done')} of {x.get('need')}"),
                  note=fin(x)) for x in p.get("clocks") or []]
    def explain(title, ex, q):
        if not ex or not ex.get("points"):
            return K.ask(q)
        return K.to_page(K.page(title, [K.heading(str(ex.get("title") or title)), K.points(ex["points"]), K.trust(f"From {ex.get('source')}" if ex.get("source") else "Written from the facts on file.")], ask_q=ex.get("ask") or q))
    st, ex = p.get("studies") or {}, p.get("exam") or {}
    rows = [K.row("Strategies", K.clip(str(st.get("sub") or "").replace(" only", ""), 9, 46), right=str(st.get("big") or "—"), icon="flask", tint="blue", to=explain("Strategies", st.get("explain"), st.get("ask") or S.STRAT_Q)),
            K.row("Weekly exam", K.clip(str(ex.get("words") or "Not run yet").split(" · ")[0].replace("/", " of ") + ((" · " + str(ex.get("words")).split(" · ")[-1]) if ex.get("words") else ""), 9, 46),
                  right=ex.get("grade") or "—", right_tone=("good" if ex.get("grade") == "Pass" else "bad" if ex.get("grade") == "Fail" else None), icon="exam", tint="blue",
                  to=explain("Weekly exam", ex.get("explain"), ex.get("ask") or S.EXAM_Q))]
    from jarvis.service import nightcheck
    nt = S._safe(nightcheck.latest, default=None)
    if nt and nt.get("asked"):
        card = S._safe(S._night_test, default=None) or {}
        rows.append(K.row("Night test", f"{nt.get('right')} of {nt.get('asked')} answers right · {S._dm(nt.get('day'))}", right="All right" if not nt.get("wrong") else f"{len(nt['wrong'])} wrong",
                          right_tone=None if not nt.get("wrong") else "warn", icon="moon", tint="blue",
                          to=K.to_page(K.page("Night test", [K.heading("Night test · Ananta asked and marked"), K.points(card.get("points") or []), K.trust(str(card.get("foot") or ""))],
                                              ask_q="What did last night's test ask you, and what did you get wrong?"))))
    else:
        rows.append(K.row("Night test", f"First run tonight, after {S._next_close_words(now).replace(' Toronto', '')}", right="Not yet", icon="moon", tint="blue"))
    try:
        sc = json.loads((S.REPO / "docs" / "knowledge" / "crypto_scorecard.json").read_text())
        lines = [str(x.get("line") or x.get("words") or x.get("name") or x) if isinstance(x, dict) else str(x) for x in (sc.get("lines") or [])]
        rows.append(K.row("Scorecard", f"{len(lines)} lines, read on review day", icon="list", tint="blue",
                          to=K.to_page(K.page("Scorecard", [K.heading("The crypto scorecard"), K.line(K.clip(sc.get("what"), 22, 150)), K.points(lines),
                                                            K.trust(f"Days are counted from {S._dw(sc.get('freeze_from'))}. {sc.get('clean_nights_needed')} clean nights are needed.")],
                                              ask_q="Explain the crypto scorecard: what the review day will read, and where each line stands today."))))
    except Exception:  # noqa: BLE001
        pass
    if p.get("missed"):
        mm = re.search(r"(\d+) big moves?.*?(\d+) missed", p["missed"]["words"] or "")
        rows.append(K.row("Missed moves", f"{mm.group(1)} big moves in 7 days" if mm else "The last 7 days", right=f"{mm.group(2)} missed" if mm else None, icon="eye", tint="blue", to=K.route("/missed")))
    links = [K.row(K.clip(x.get("label"), 5, 30), None, to=K.route(x.get("route"))) for x in p.get("links") or [] if x.get("route") != "/missed"]
    parts = [K.hero("The evidence window", f"Day {win['day']} of {win['of']}", since=f"No rule changes before {S._dw(S.RULE_B_END)}."),
             K.bars(bars), K.rows("Checks", rows), K.rows(None, links, plain=True) if links else None,
             K.points([S._plain(p["last_night"]["words"])], title="Last night's card") if p.get("last_night") else None]
    return K.page("Proof", parts, ask_q=p.get("clocks_ask") or "Explain every crypto clock: what each counts, where it stands, and what would count as a pass.")


def people(j, is_owner: bool = True) -> dict:
    p = S.people(j, is_owner=is_owner)
    rows = [K.row(x.get("name"), K.clip(x.get("can"), 8, 46), right=K.clip(x.get("relation"), 3, 18) or None, letter=str(x.get("name") or "?")[:1]) for x in p.get("people") or []]
    parts = [K.hero("People", f"{len(rows)}", since="Only Madhav decides. Everyone else can ask."), K.rows(None, rows, plain=True), K.trust(str(p.get("invite") or ""))]
    return K.page("People", parts, ask_q="Who can talk to you, and what can each of them do?", second={"label": "Invite someone", "route": "/people"})


def notices(j, market: str = "crypto", c: dict | None = None) -> dict:
    c = c or _ctx(j)
    if market != "crypto":
        you = you_rows(c["list"], market)
        n = c["list"].get("counts") or {}
        return K.page("Notices", [K.rows("For you", you, count=len(you), badge=True) if you else K.line("Nothing needs you right now."),
                                  K.counts("The open list", [{"n": n.get("YOU", 0), "label": "Need you", "accent": True}, {"n": n.get("WORK", 0), "label": "To do"},
                                                             {"n": n.get("DATE", 0), "label": "Wait for a date"}, {"n": n.get("PARKED", 0), "label": "Parked"}], to=K.place("openlist"))],
                      bar_kind="close", ask_q="What needs me today, in order?")
    you = you_rows(c["list"], market)
    new = [K.row(K.clip(n["line"].split(":")[0], 5, 30), K.clip(n["line"].split(": ", 1)[-1] if ": " in n["line"] else "", 8, 44) or None, right="Today", icon="bell", to=n.get("to")) for n in home_notices(j, c)] if market == "crypto" else []
    ev = [r for _d, _o, r in _events(j, c)[:3]]
    n = c["list"].get("counts") or {}
    parts = [K.rows("For you", you, count=len(you), badge=True) if you else K.line("Nothing needs you right now."),
             K.rows("New", new) if new else None,
             K.rows("Latest", ev, more=K.tab("activity")) if ev else None,
             K.counts("The open list", [{"n": n.get("YOU", 0), "label": "Need you", "accent": True}, {"n": n.get("WORK", 0), "label": "To do"},
                                        {"n": n.get("DATE", 0), "label": "Wait for a date"}, {"n": n.get("PARKED", 0), "label": "Parked"}], to=K.place("openlist"))]
    return K.page("Notices", parts, bar_kind="close", ask_q="What needs me today, in order?")


def more(j) -> dict:
    c = _ctx(j)
    p = S.proof(j)
    now = c["now"]
    win = S._window(now.date())
    from jarvis.service import nightcheck
    nt = S._safe(nightcheck.latest, default=None)
    n = c["list"].get("counts") or {}
    ex = p.get("exam") or {}
    mm = re.search(r"(\d+) big moves?.*?(\d+) missed", ((p.get("missed") or {}).get("words") or ""))
    ppl = S.people(j, is_owner=True)
    you = you_rows(c["list"])
    push = next((r for r in you if "phone notes" in str(r.get("title")).lower()), None)
    parts = [K.identity("Paper only. It never places an order."),
             K.tiles("Proof", [K.tile("Strategies", f"{(p.get('studies') or {}).get('big', '—')} on record", "flask", "blue", K.place("proof")),
                               K.tile("Weekly exam", " · ".join(x for x in (ex.get("grade"), S._dm(ex.get("day")) if ex.get("day") else None) if x) or "Not run yet", "exam", "blue", K.place("proof")),
                               K.tile("Night test", (f"{nt.get('right')} of {nt.get('asked')} right" if nt and nt.get("asked") else "Starts tonight"), "moon", "blue", K.place("proof")),
                               K.tile("Clocks", f"Day {win['day']} of {win['of']}", "clock", "blue", K.place("proof")),
                               K.tile("Missed", f"{mm.group(2)} of {mm.group(1)} moves" if mm else "Last 7 days", "eye", "blue", K.route("/missed")),
                               K.tile("The evidence", "Live", "bars", "blue", K.route("/reconstruction"))]),
             K.tiles("You and others", [K.tile("People", f"{len(ppl.get('people') or [])} on the list", "people", "violet", K.place("people")),
                                        K.tile("The open list", f"{n.get('YOU', 0)} need you", "list", "violet", K.place("openlist")),
                                        K.tile("Repair board", f"{n.get('WORK', 0)} to do", "flag", "violet", K.route("/flags"))]),
             K.tiles("Settings", [K.tile("Phone notes", "Not set up yet", "phone", None, push.get("to") if push else K.ask("How do I turn on phone notes?"), quiet=True) if push else K.tile("Phone notes", "Ask how", "phone", None, K.ask("Are phone notes on for my iPhone?")),
                                  K.tile("Appearance", "Dark or light", "sun", None, {"action": "theme"}),
                                  K.tile("All settings", "Voice, sign-out", "person", None, K.route("/more"))])]
    return K.surface("more", "crypto", parts, bell=len(you), title="More")


PLACES = {"home": home, "markets": markets, "activity": activity, "more": more, "account": account, "proof": proof, "why": why, "notices": notices,
          "openlist": openlist_page, "people": people}


def needs(j, market: str = "crypto") -> dict:
    """/v3/place/needs: the open list's "needs your yes" for one market, for the bell, Home's "Needs you" and More's tiles (both markets ask
    the sign-in service, where the open list lives)."""
    from jarvis.service import openlist
    col = S._safe(openlist.collect, j, default={}) or {}
    you = you_rows(col, market)
    push = next((r for r in you if "phone notes" in str(r.get("title")).lower() or "push" in str(r.get("sub")).lower()), None)
    n = col.get("counts") or {}
    return {"ready": True, "market": market, "count": len(you), "rows": you, "counts": n,
            "push": {"on": push is None, "to": (push or {}).get("to")}, "list_value": f"{len(you)} need you", "board_value": f"{n.get('WORK', 0)} to do"}


def get(j, name: str, is_owner: bool = True, market: str = "crypto") -> dict:
    if name == "needs":
        return needs(j, market)
    if name == "notices":
        return notices(j, market)
    if name == "openlist":
        return openlist_page(j, None, market)
    if name.startswith("coin:"):
        coin = name.split(":", 1)[1].upper()
        if coin not in S.COIN_NAME:
            raise KeyError(name)
        return coin_page(j, coin)
    if name not in PLACES:
        raise KeyError(name)
    if name == "people":
        return people(j, is_owner=is_owner)
    return PLACES[name](j)
