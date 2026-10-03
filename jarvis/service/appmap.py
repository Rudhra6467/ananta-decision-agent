"""The app map: every place in the Jarvis app, what it shows, and how Ananta may move the owner there.

Ananta never touches the screen itself. It returns ui actions; the app performs them and reports whether they happened.
Targets: a screen key below, "coin:<SYM>" (coin page) or "trade:<id>" (trade page). This module validates targets against
live data so Ananta cannot send the app somewhere that does not exist.
"""
from __future__ import annotations

import re

SCREENS = {
    "home": {"name": "Home", "where": "Home tab (house icon)",
             "shows": "today's paper value and change, the one-line status, things waiting for your OK, the morning/evening brief, "
                      "the Explorer / Portfolio / Hourly-watch rows, and the activity feed of buys, sells, alerts and changes"},
    "markets": {"name": "Markets", "where": "Markets tab (candles icon)",
                "shows": "how many coins are in an uptrend, the BTC gate, and the watchlist of 10 coins with price, today's move, "
                         "1h/4h trend and how close each is to its nearest setup; above it, Ananta's reasoning: where each coin stops on the "
                         "decision chain (regime, trend, location, trigger, invalidation, risk, exposure); tap a coin for its page"},
    "portfolio": {"name": "Portfolio (T3)", "where": "Portfolio tab, first sub-tab",
                  "shows": "the T3 portfolio value chart, the Autopilot switch, suggested changes, holdings with value, return and rating, cash and costs"},
    "portfolio:explorer": {"name": "Explorer trades", "where": "Portfolio tab, Explorer sub-tab",
                           "shows": "the Explorer's paper book: open trades with P&L, orders waiting to fill, closed trades"},
    "portfolio:mine": {"name": "My trades", "where": "Portfolio tab, My trades sub-tab",
                       "shows": "the owner's own paper book: positions, orders with reasons, research jobs"},
    "ananta": {"name": "Ananta", "where": "Ananta tab (speech bubble)",
               "shows": "this conversation: type, dictate with the mic, or talk hands-free with the wave button; Sessions holds past conversations"},
    "evidence": {"name": "Evidence: being collected", "where": "Evidence tab (flask), first sub-tab",
                 "shows": "the evidence tracker (days, checks, setups seen, buys, closed trades, shadows, Hunter checks, replay match), "
                          "what we collected per setup, what was forwarded to the repair shop and why, and the repair shop status"},
    "evidence:forwarded": {"name": "Evidence: forwarded and in use", "where": "Evidence tab, second sub-tab",
                           "shows": "repairs that passed and run in paper (T3 vs buy-and-hold) and the safety changes"},
    "cockpit": {"name": "Cockpit", "where": "gauge icon at the top right of Home",
                "shows": "kill switch, portfolio autopilot, locked live-trading switch, your mandate, the test lab, Ask and Voice switches, "
                         "the daily Claude budget and spend, active alerts, system status and recent actions"},
    "mandate": {"name": "Your mandate", "where": "Cockpit > Your mandate", "shows": "your goals, markets, styles, setups, limits and how Ananta should talk"},
    "testlab": {"name": "Test lab", "where": "Cockpit > Test lab", "shows": "recorded test runs of Ananta with answers to mark Good / OK / Bad"},
}
ALIASES = {
    "home": "home", "home screen": "home", "main": "home", "start": "home", "dashboard": "home", "inbox": "home", "brief": "home", "activity": "home",
    "market": "markets", "markets": "markets", "watchlist": "markets", "watch list": "markets", "scan": "markets", "scanner": "markets",
    "portfolio": "portfolio", "t3": "portfolio", "holdings": "portfolio",
    "explorer": "portfolio:explorer", "explorer trades": "portfolio:explorer", "open trades": "portfolio:explorer", "trades": "portfolio:explorer",
    "my trades": "portfolio:mine", "my book": "portfolio:mine", "my paper book": "portfolio:mine", "manual book": "portfolio:mine",
    "ananta": "ananta", "chat": "ananta", "voice": "ananta", "conversation": "ananta",
    "evidence": "evidence", "repair shop": "evidence", "evidence tracker": "evidence", "forwarded": "evidence:forwarded",
    "cockpit": "cockpit", "settings": "cockpit", "controls": "cockpit", "kill switch": "cockpit", "budget": "cockpit", "alerts": "cockpit",
    "mandate": "mandate", "my mandate": "mandate", "goals": "mandate", "test lab": "testlab", "tests": "testlab", "test results": "testlab",
    "test runs": "testlab", "app tests": "testlab",
}
COINS = {"bitcoin": "BTC", "btc": "BTC", "ethereum": "ETH", "eth": "ETH", "ether": "ETH", "solana": "SOL", "sol": "SOL", "cardano": "ADA", "ada": "ADA",
         "dogecoin": "DOGE", "doge": "DOGE", "avalanche": "AVAX", "avax": "AVAX", "bitcoin cash": "BCH", "bch": "BCH", "chainlink": "LINK",
         "link": "LINK", "litecoin": "LTC", "ltc": "LTC", "xrp": "XRP", "ripple": "XRP"}


def describe() -> dict:
    return {"places": [{"target": k, **v, "spots": SPOTS.get(k, {})} for k, v in SCREENS.items()],
            "page_spots": {"coin page": SPOTS["coin"], "trade page": SPOTS["trade"]},
            "also": "coin:<SYM> opens a coin page (candle chart with averages, support/resistance, our trades, position, setup checklist); "
                    "trade:<id> opens a trade page (chart with bought/stop/target, why we bought, exit plan, timeline, what-if)."}


def resolve(j, target: str) -> tuple[str | None, str]:
    """-> (valid target or None, human label or error)."""
    t = (target or "").strip()
    low = t.lower()
    if low in SCREENS:
        return low, SCREENS[low]["name"]
    if low in ALIASES:
        k = ALIASES[low]
        return k, SCREENS[k]["name"]
    ex = j._explorer()
    if low.startswith("coin:"):
        sym = COINS.get(low[5:].strip(), low[5:].strip().upper())
        if ex and sym in ex.st["engines"]:
            return f"coin:{sym}", f"{sym} coin page"
        return None, f"Ananta does not watch {sym}"
    if low.startswith("trade:"):
        tid = t[6:].strip()
        if ex and re.fullmatch(r"[A-Za-z0-9_\-]{3,80}", tid):
            coin = tid.split("-")[0]
            eng = ex.st["engines"].get(coin)
            if eng and any(x.id == tid for x in list(eng.trades) + list(eng.actual_closed) + list(eng.closed)):
                return f"trade:{tid}", f"{coin} trade page"
        return None, "no such trade"
    return None, f"unknown place '{t}'"


NAV = re.compile(r"^\s*(?:hey\s+\w+[,.!]?\s*|ok(?:ay)?[,.!]?\s*|ananta[,.!]?\s*|jarvis[,.!]?\s*|please\s+)*"
                 r"(?:can you |could you |please )?(?:take me (?:back )?to|go (?:back )?to|bring me to|open(?: up)?|show me|switch to|navigate to|move to|let'?s go to)"
                 r"\s+(?:the )?(?P<what>[a-z0-9 ]+?)(?:\s+(?:screen|page|tab|chart))?\s*(?:please)?[.!?]*\s*$", re.I)
BACK = re.compile(r"^\s*(?:ok(?:ay)?[,.!]?\s*)?(?:please\s+)?(?:go back|take me back|back|previous (?:page|screen))(?: please)?[.!?]*\s*$", re.I)


HOME = re.compile(r"^\s*(?:please\s+)?(?:can you\s+|could you\s+)?(?:take me|go|bring me|head)\s+(?:back\s+)?home(?:\s+please)?[.!?]*\s*$", re.I)


def quick_command(j, text: str) -> dict | None:
    """Plain navigation ("take me home", "open Ethereum", "show me my bitcoin trade", "go back", "scroll down") without a model call."""
    qs = quick_scroll(text)
    if qs:
        return qs
    if TOUR_ASK.search(text) and len(text.split()) <= 14:
        steps = tour(j)
        return {"ui": [], "tour": steps, "say": "Sure, Madhav. Let me show you around. I'll go tab by tab; say stop or tap Stop any time."}
    if HOME.match(text):
        return {"ui": [{"do": "go_to", "target": "home", "label": "Home"}], "say": "Sure, Madhav. Taking you home."}
    if BACK.match(text):
        return {"ui": [{"do": "back", "label": "Back"}], "say": "Sure, going back."}
    m = NAV.match(text)
    if not m:
        return None
    what = m.group("what").strip().lower()
    what = re.sub(r"\b(screen|page|tab)\b", "", what).strip()
    if what not in ALIASES and what not in SCREENS:
        what = re.sub(r"^(my|our|the)\s+", "", what)
    if what in ALIASES or what in SCREENS:
        k = ALIASES.get(what, what)
        return {"ui": [{"do": "go_to", "target": k, "label": SCREENS[k]["name"]}], "say": f"Sure, Madhav. Taking you to {SCREENS[k]['name']}."}
    trade = re.fullmatch(r"(?:(\w+(?: cash)?) )?(?:trade|position)", what) or re.fullmatch(r"(\w+(?: cash)?) trade", what)
    words = what.replace(" trade", "").replace(" position", "").replace(" chart", "").strip()
    sym = COINS.get(words)
    if sym and ("trade" in what or "position" in what):
        ex = j._explorer()
        open_t = [t for t in (ex.status()["open"] if ex else []) if t["coin"] == sym]
        if len(open_t) == 1:
            return {"ui": [{"do": "open", "target": f"trade:{open_t[0]['id']}", "label": f"{sym} trade"}],
                    "say": f"Sure. Opening our {sym} trade."}
        return None                                   # none or several: let the model explain
    if sym:
        return {"ui": [{"do": "open", "target": f"coin:{sym}", "label": f"{sym} coin page"}], "say": f"Sure. Opening {sym}."}
    _ = trade
    return None


CLAIM = re.compile(r"\b(showing you (?:the|our|your)|i'?m (?:now )?showing you|pulling up|here'?s the \w+ (?:screen|tab|page)|taking you|take you|i'?ve (?:opened|moved|pulled up|taken you|brought)|i have (?:opened|moved|pulled up)|i'?m (?:opening|taking you|moving)|"
                   r"let me (?:open|take you|show you)|opening (?:it|the|your|our|up)|i (?:opened|moved) )", re.I)
SHOW_INTENT = re.compile(r"\b(show me|take me|open|go to|bring me|where (?:can|do) i (?:see|find)|let'?s (?:go|move) to|next page|"
                         r"where did you get|where does (?:that|this|it) come from|prove it|highlight|point (?:at|to)|where is (?:that|it|this))\b", re.I)


def here_target(here: dict | None) -> str | None:
    if not here:
        return None
    sc = here.get("screen")
    if sc == "coin" and here.get("coin"):
        return f"coin:{here['coin']}"
    if sc == "trade" and here.get("id"):
        return f"trade:{here['id']}"
    if sc == "explorer_trades":
        return "portfolio:explorer"
    if sc == "manual_book":
        return "portfolio:mine"
    if sc == "evidence":
        return "evidence:forwarded" if here.get("tab") == "forwarded" else "evidence"
    return sc


def guess(text: str) -> str | None:
    """Best place in the app for a question, from its words (longest alias first)."""
    low = text.lower()
    for k in sorted(ALIASES, key=len, reverse=True):
        if re.search(r"\b" + re.escape(k) + r"\b", low):
            return ALIASES[k]
    for k in sorted(COINS, key=len, reverse=True):
        if re.search(r"\b" + re.escape(k) + r"\b", low):
            return f"coin:{COINS[k]}"
    return None


WHERE_AM_I = re.compile(r"\b(what am i (?:looking at|seeing)|where am i|what(?:'s| is) (?:this|on this) (?:screen|page)|what is this|explain this (?:screen|page))\b", re.I)


def dedupe(ui: list[dict]) -> list[dict]:
    out = []
    for u in ui:
        if not out or (u.get("do"), u.get("target"), u.get("dir")) != (out[-1].get("do"), out[-1].get("target"), out[-1].get("dir")):
            out.append(u)
    return out


def keep_honest(j, question: str, answer: str, ui: list[dict], here: dict | None) -> tuple[list[dict], str]:
    """Make what Ananta SAYS about the screen match what the app WILL do.
    - drop moves to the screen that is already open
    - a 'show me / take me' request, or an answer that claims a move, with no move: add the best-guess move if it resolves
    - still nothing to open but the answer claims a move: say plainly that the screen did not move."""
    cur = here_target(here)
    ui = dedupe([u for u in ui if not (u.get("do") != "back" and u.get("target") == cur)])
    if WHERE_AM_I.search(question or "") and not SHOW_INTENT.search(question or ""):
        return [u for u in ui if u.get("do") == "scroll"], answer       # he asked about THIS screen: never move away from it
    claims = bool(CLAIM.search(answer or ""))
    scroll_claim = re.search(r"\b(i'?ve scrolled|scrolling (?:down|up|to)|i scrolled)", answer or "", re.I)
    scroll_ask = re.search(r"\b(below this|what'?s below|bottom of|at the bottom|scroll (?:down|up))\b", question or "", re.I)
    if (scroll_claim or scroll_ask) and not any(u.get("do") == "scroll" for u in ui):
        d = "up" if re.search(r"\b(above|up|top)\b", question or "", re.I) and not scroll_ask else ("bottom" if re.search(r"bottom", (question or "") + (answer or ""), re.I) else "down")
        ui = ui + [{"do": "scroll", "dir": d, "label": f"Scroll {d}"}]
    if not ui and (claims or SHOW_INTENT.search(question or "")):
        t = guess(question) or (guess(answer) if claims else None)
        if t and t != cur:
            v, label = resolve(j, t)
            if v:
                ui = [{"do": "open" if v.split(":")[0] in ("coin", "trade") else "go_to", "target": v, "label": label}]
    if claims and not ui:
        answer = (answer or "").rstrip() + " (I couldn't move the screen for this one; it is still on the same page.)"
    ui = [u for u in ui if u.get("do") in ("go_to", "open", "back")] + [u for u in ui if u.get("do") == "scroll"]   # move first, then scroll
    return dedupe(ui), answer


def proof_target(evidence: list[dict], previous: dict | None, cur: str | None) -> tuple[dict | None, str | None]:
    """For 'show me / where did you get that': the place (and spot) behind this answer's evidence, else behind the previous answer."""
    for src in (evidence or [], (previous or {}).get("evidence") or []):
        for e in src:
            if e.get("screen") and e["screen"] != cur:
                v = e["screen"]
                return {"do": "open" if v.split(":")[0] in ("coin", "trade") else "go_to", "target": v, "label": e.get("label") or v}, e.get("spot")
    for u in (previous or {}).get("ui") or []:
        if u.get("do") in ("go_to", "open") and u.get("target") != cur:
            return u, None
    return None, None


# ---------------------------------------------------------------------------
# Spots: things on screen Ananta can point at while it talks (they glow and scroll into view)
# ---------------------------------------------------------------------------
SPOTS = {
    "home": {"home.value": "paper value and today's change", "home.inbox": "things waiting for your OK", "home.brief": "the morning / evening brief",
             "home.books": "Explorer, Portfolio and Hourly-watch rows", "home.activity": "the activity feed"},
    "markets": {"markets.summary": "how many coins are trending up and the BTC gate", "markets.chain": "Ananta's reasoning: where each coin stops on the decision chain",
                "markets.coin:<SYM>": "one coin's row: price, trend, closest setup"},
    "portfolio": {"portfolio.value": "portfolio value and its chart", "portfolio.autopilot": "the Autopilot switch",
                  "portfolio.suggested": "suggested changes waiting", "portfolio.holdings": "the holdings list header",
                  "portfolio.holding:<SYM>": "one holding: value, return, rating"},
    "portfolio:explorer": {"explorer.value": "Explorer book value", "explorer.trade:<trade id>": "one open Explorer trade", "explorer.closed": "closed trades"},
    "portfolio:mine": {"mine.value": "my paper book value", "mine.position:<SYM>": "one of my positions"},
    "evidence": {"evidence.tracker": "the evidence tracker", "evidence.collected": "what we collected by setup",
                 "evidence.forwarded": "what was forwarded to the repair shop", "evidence.shop": "repair shop status and queue"},
    "evidence:forwarded": {"evidence.in_use": "repairs running in paper (T3 vs buy-and-hold)", "evidence.safety": "safety changes"},
    "cockpit": {"cockpit.controls": "kill switch, autopilot, live trading", "cockpit.ai": "Ask / Voice switches and the Claude budget",
                "cockpit.alerts": "active alerts", "cockpit.systems": "system status"},
    "coin": {"coin.chart": "the candle chart", "coin.position": "our position in this coin", "coin.market": "market picture and setup checklist",
             "coin.levels": "next support and resistance", "coin.setup:<E1-E5>": "one setup's checklist (opens it)",
             "coin.chain": "the decision chain ladder for this coin: each gate passed or where it stops, plus evidence",
             "coin.trades": "Explorer trades on this coin"},
    "trade": {"trade.pnl": "the trade's profit or loss", "trade.chart": "the chart with bought / stop / target lines",
              "trade.levels": "stop, target and time limit", "trade.stop": "the stop-loss line", "trade.target": "the target line", "trade.why": "why we bought", "trade.plan": "the exit plan", "trade.timeline": "timeline"},
}


def spot_screen(spot: str) -> str | None:
    head = spot.split(":")[0]
    pre = head.split(".")[0]
    if pre == "explorer":
        return "portfolio:explorer"
    if pre == "mine":
        return "portfolio:mine"
    if head in ("evidence.in_use", "evidence.safety"):
        return "evidence:forwarded"
    return {"home": "home", "markets": "markets", "portfolio": "portfolio", "evidence": "evidence", "cockpit": "cockpit",
            "coin": "coin", "trade": "trade"}.get(pre)


def valid_spot(j, spot: str) -> bool:
    if not re.fullmatch(r"[a-z_]+\.[a-z_]+(?::[A-Za-z0-9_\-]{1,80})?", spot or ""):
        return False
    head, _, arg = spot.partition(":")
    scr = spot_screen(spot)
    names = SPOTS.get("coin" if scr == "coin" else "trade" if scr == "trade" else scr or "", {})
    if not any(k.split(":")[0] == head for k in names):
        return False
    ex = j._explorer()
    if head in ("markets.coin", "portfolio.holding", "mine.position"):
        return bool(ex and arg in ex.st["engines"])
    if head == "coin.setup":
        return arg in ("E1", "E2", "E3", "E4", "E5")
    if head == "explorer.trade":
        return bool(ex and any(t["id"] == arg for t in ex.status()["open"]))
    return not arg


def plan_points(j, points, ui: list[dict], here: dict | None, n_sentences: int, question: str = "") -> tuple[list[dict], list[dict]]:
    """Keep valid spots; add the screen move a spot needs when it is not on the open screen (and nothing else opens it)."""
    out = []
    cur = here_target(here)
    opened = [u.get("target") for u in ui if u.get("do") in ("go_to", "open")]
    land = opened[-1] if opened else cur
    for p in (points or [])[:8]:
        if not isinstance(p, dict):
            continue
        sp, k = str(p.get("spot", "")), p.get("sentence", 0)
        if not valid_spot(j, sp):
            continue
        need = spot_screen(sp)
        land_kind = (land or "").split(":")[0] if (land or "").startswith(("coin:", "trade:")) else land
        if need in ("coin", "trade"):
            if land_kind != need:
                continue                                  # coin / trade spots only on that page
        elif need != land:
            if opened or not SHOW_INTENT.search(question or ""):   # move only when he asked to see something, and only once
                continue
            v, label = resolve(j, need)
            if not v:
                continue
            ui = ui + [{"do": "go_to", "target": v, "label": label}]
            land = v
        try:
            k = max(0, min(int(k), max(0, n_sentences - 1)))
        except (TypeError, ValueError):
            k = 0
        out.append({"spot": sp, "sentence": k})
    return out, ui


SPOT_WORDS = {
    "trade.pnl": r"profit|loss|\bup\b|\bdown\b|p&l|\$", "trade.chart": r"chart|line", "trade.levels": r"stop|target|time limit|levels",
    "trade.stop": r"stop", "trade.target": r"target|take.profit", "trade.why": r"why|because|bought|setup|signal",
    "trade.plan": r"plan|exit|sell|trail", "trade.timeline": r"timeline|opened|history",
    "coin.chart": r"chart|candle", "coin.position": r"position|we hold|our\b|bought", "coin.market": r"market|trend|checklist",
    "coin.levels": r"support|resistance|level", "coin.trades": r"trades?",
    "home.value": r"value|worth|today|\$", "home.inbox": r"inbox|waiting|approve|ok\b", "home.brief": r"brief|summary",
    "home.books": r"explorer|hourly|portfolio|books?|watch", "home.activity": r"activity|recent|happened",
    "markets.summary": r"trend|breadth|gate|coins? (?:are|is)|up\b", "portfolio.value": r"value|worth|\$|up\b|down\b",
    "portfolio.autopilot": r"autopilot", "portfolio.suggested": r"suggest|change|waiting", "portfolio.holdings": r"holding|coins",
    "explorer.value": r"value|worth|\$|explorer", "explorer.closed": r"closed", "mine.value": r"value|worth|\$",
    "evidence.tracker": r"tracker|progress|milestone", "evidence.collected": r"collected|setups?|signals?",
    "evidence.forwarded": r"forward|repair", "evidence.shop": r"repair|shop|queue", "evidence.in_use": r"running|in use|paper|buy.and.hold",
    "evidence.safety": r"safety", "cockpit.controls": r"kill|autopilot|live|switch", "cockpit.ai": r"ask|voice|budget|claude|gemini",
    "cockpit.alerts": r"alert", "cockpit.systems": r"system|status|running",
}


def _spot_rx(spot: str) -> str | None:
    head, _, arg = spot.partition(":")
    if arg and (head in ("markets.coin", "portfolio.holding", "mine.position") or head == "explorer.trade"):
        sym = arg.split("-")[0].upper()
        names = [k for k, v in COINS.items() if v == sym]
        return r"\b(" + "|".join(re.escape(n) for n in names + [sym.lower()]) + r")\b"
    if head == "coin.setup" and arg:
        try:
            from jarvis.service.views import SETUP
            nm = SETUP.get(arg, "")
        except Exception:  # noqa: BLE001
            nm = ""
        first = nm.split()[0].lower() if nm else ""
        return r"\b" + re.escape(arg.lower()) + r"\b" + (r"|\b" + re.escape(first) if first else "")
    return SPOT_WORDS.get(head)


def anchor_points(points: list[dict], answer: str) -> list[dict]:
    """Keep each highlight on the sentence that actually talks about it (models often count sentences wrong)."""
    sents = [x for x in re.split(r"(?<=[.!?])\s+", answer or "") if x.strip()]
    if not sents:
        return points
    used, out = set(), []
    for p in points:
        rx, k = _spot_rx(p["spot"]), p["sentence"]
        if rx and not re.search(rx, sents[min(k, len(sents) - 1)], re.I):
            hit = next((i for i, x in enumerate(sents) if i not in used and re.search(rx, x, re.I)), None)
            if hit is not None:
                k = hit
        used.add(k)
        out.append({**p, "sentence": k})
    seen, final = set(), []
    for p in sorted(out, key=lambda x: x["sentence"]):            # one highlight per sentence, in speaking order
        if p["sentence"] not in seen:
            seen.add(p["sentence"])
            final.append(p)
    return final


SCROLL = re.compile(r"^\s*(?:please\s+)?(?:can you\s+)?(scroll|go|move|take me|show me)\s*(?:to\s+)?(?:the\s+)?(up|down|top|bottom)(?:\s+of (?:the |this )?(?:page|screen))?(?:\s+please)?[.!?]*\s*$", re.I)


def quick_scroll(text: str) -> dict | None:
    m = SCROLL.match(text)
    if not m:
        return None
    d = m.group(2).lower()
    return {"ui": [{"do": "scroll", "dir": d, "label": f"Scroll {d}"}], "say": {"up": "Scrolling up.", "down": "Scrolling down.",
            "top": "Back to the top.", "bottom": "Here's the bottom of the page."}[d]}


# ---------------------------------------------------------------------------
# Tour: a scripted walk through the app (no model call, free, instant), with a few live numbers
# ---------------------------------------------------------------------------
TOUR_ASK = re.compile(r"\b(show me around|give me a tour|take me on a tour|app tour|tour of the app|i'?m new( here)?|new user|"
                      r"how does (this|the) app work|walk me through (the|this) app|explain (the|this) app)\b", re.I)


def tour(j) -> list[dict]:
    from jarvis.service import views

    s = views.day_summary(j)
    m = views.markets(j)
    h = views.holdings(j)
    t = views.trades_list(j)
    up, n = m["breadth"]["up_1h"], m["breadth"]["of"]
    inbox = 0
    try:
        from jarvis.service.mandate import Mandate

        inbox = len(Mandate(j.db, j.now).pending())
    except Exception:  # noqa: BLE001
        pass
    steps = [
        {"ui": {"do": "go_to", "target": "home", "label": "Home"}, "spot": "home.value",
         "say": f"Welcome, Madhav. This is Home, your one-page summary. At the top is all our paper money together: about {round(s['paper_value']):,} dollars today."},
    ]
    if inbox:
        steps.append({"spot": "home.inbox", "say": "Here is the inbox. Anything I prepare for you, like an order or an alert, waits here until you confirm it."})
    steps += [
        {"spot": "home.brief", "say": "This is the daily brief. I write one in the morning and one in the evening, and you can ask for one any time."},
        {"spot": "home.books", "say": "These rows are our three engines: the Explorer, the trend portfolio, and the hourly watch with Hunter and Squeeze."},
        {"spot": "home.activity", "say": "And this is the activity feed: every buy, sell, alert and change, in plain words. Tap a trade to open it."},
        {"ui": {"do": "go_to", "target": "markets", "label": "Markets"}, "spot": "markets.summary",
         "say": f"This is Markets. Right now {up} of our {n} coins are in a one-hour uptrend."},
        {"spot": "markets.coin:BTC", "say": "Each row is one coin: its price, its trend, and how close it is to one of our setups. Tap a coin for its chart."},
        {"ui": {"do": "go_to", "target": "portfolio", "label": "Portfolio"}, "spot": "portfolio.value",
         "say": f"This is the trend portfolio. It holds coins while they trend up and goes to cash when they fall. It is worth about {round(h['value']):,} dollars."},
        {"spot": "portfolio.autopilot", "say": "This switch is Autopilot. Off means I suggest changes and wait for you. On means the portfolio rebalances by itself."},
        {"spot": "portfolio.holdings", "say": "Below are the holdings, each with its value, return and rating: strong, steady or weak."},
        {"ui": {"do": "go_to", "target": "portfolio:explorer", "label": "Explorer trades"}, "spot": "explorer.value",
         "say": f"This is the Explorer. It checks ten coins every fifteen minutes and trades on paper, 100 dollars each. It has {len(t['open'])} trades open."},
        {"ui": {"do": "go_to", "target": "portfolio:mine", "label": "My trades"}, "spot": "mine.value",
         "say": "And this is your own paper book. Orders you ask me for land here, kept apart from the agent's trades."},
        {"ui": {"do": "go_to", "target": "evidence", "label": "Evidence"}, "spot": "evidence.tracker",
         "say": "This is Evidence: everything we collect to learn what works. Tap any row and it explains itself."},
        {"spot": "evidence.forwarded", "say": "These are the questions we sent to the repair shop, why we sent them, and what we found."},
        {"ui": {"do": "go_to", "target": "cockpit", "label": "Cockpit"}, "spot": "cockpit.controls",
         "say": "This is the Cockpit, behind the gauge icon on Home. The kill switch and Autopilot live here, and live trading stays locked."},
        {"spot": "cockpit.ai", "say": "Here you can switch me on or off and set a daily budget for Claude, so I never run up costs."},
        {"ui": {"do": "go_to", "target": "ananta", "label": "Ananta"},
         "say": "And this is me. Type, tap the mic, or tap the wave and just talk. Ask me anything about our portfolio or the market, or ask me to show you something. That's the tour."},
    ]
    return steps


def _coin_in(text: str) -> str | None:
    low = text.lower()
    for k in sorted(COINS, key=len, reverse=True):
        if re.search(r"\b" + re.escape(k) + r"\b", low):
            return COINS[k]
    return None


def infer_link(j, e: dict) -> dict:
    """Most evidence rows come without a place: work out where that number is shown in the app, so 'Show me' works for it."""
    txt = f"{e.get('label', '')} {e.get('value', '')} {e.get('source', '')}"
    low = txt.lower()
    sym = _coin_in(txt)
    ex = j._explorer() if hasattr(j, "_explorer") else None
    trade = None
    if sym and ex:
        try:
            trade = next((t for t in ex.status()["open"] if t.get("coin") == sym), None)
        except Exception:  # noqa: BLE001
            trade = None
    setup = re.search(r"\b(E[1-5])\b", txt)
    if sym and setup:
        return {"screen": f"coin:{sym}", "spot": f"coin.setup:{setup.group(1)}"}
    if sym and re.search(r"support|resistance", low):
        return {"screen": f"coin:{sym}", "spot": "coin.levels"}
    if trade and re.search(r"\bstop\b", low):
        return {"screen": f"trade:{trade['id']}", "spot": "trade.stop"}
    if trade and re.search(r"target", low):
        return {"screen": f"trade:{trade['id']}", "spot": "trade.target"}
    if trade and re.search(r"trade|p&l|profit|loss|entry|bought", low):
        return {"screen": f"trade:{trade['id']}", "spot": "trade.pnl"}
    if sym and re.search(r"holding|portfolio|t3|weight", low):
        return {"screen": "portfolio", "spot": f"portfolio.holding:{sym}"}
    if re.search(r"explorer", low):
        return {"screen": "portfolio:explorer", "spot": "explorer.value"}
    if re.search(r"portfolio|t3|buy.and.hold", low):
        return {"screen": "portfolio", "spot": "portfolio.value"}
    if re.search(r"my (paper )?book|manual", low):
        return {"screen": "portfolio:mine", "spot": "mine.value"}
    if re.search(r"repair|forwarded", low):
        return {"screen": "evidence", "spot": "evidence.shop"}
    if re.search(r"evidence|collected|milestone|signals? seen", low):
        return {"screen": "evidence", "spot": "evidence.tracker"}
    if re.search(r"trending|breadth|coins up|btc gate|uptrend", low) and not sym:
        return {"screen": "markets", "spot": "markets.summary"}
    if sym and re.search(r"price|trend|move|%|chart", low):
        return {"screen": f"coin:{sym}", "spot": "coin.chart"}
    if re.search(r"alert", low):
        return {"screen": "cockpit", "spot": "cockpit.alerts"}
    return {}


def clean_evidence(j, items) -> list[dict]:
    """Evidence rows keep a 'spot' (and the place to open for it) only when both are real, so 'Show me' always works."""
    out = []
    for e in (items or [])[:6]:
        if not isinstance(e, dict):
            continue
        e = {k: e.get(k) for k in ("label", "value", "source", "time", "spot", "screen") if e.get(k) not in (None, "")}
        if not e.get("spot") and not e.get("screen") and "coingecko" not in str(e.get("source", "")).lower():
            try:
                e.update(infer_link(j, e))
            except Exception:  # noqa: BLE001
                pass
        sp = str(e.get("spot", ""))
        if sp and valid_spot(j, sp):
            need = spot_screen(sp)
            scr = e.get("screen")
            if need in ("coin", "trade"):
                v, _ = resolve(j, str(scr or "")) if scr else (None, "")
                if not v or not v.startswith(need + ":"):
                    e.pop("spot", None)
                    e.pop("screen", None)
                else:
                    e["screen"] = v
            else:
                e["screen"] = need
        else:
            e.pop("spot", None)
            if e.get("screen"):
                v, _ = resolve(j, str(e["screen"]))
                if v:
                    e["screen"] = v
                else:
                    e.pop("screen", None)
        out.append(e)
    return out
