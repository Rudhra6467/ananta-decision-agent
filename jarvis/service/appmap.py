"""The app map: every place in the Jarvis app, what it shows, and how Ananta may move the owner there.

Ananta never touches the screen itself. It returns ui actions; the app performs them and reports whether they happened.
Targets: a screen key below, "coin:<SYM>" (coin page) or "trade:<id>" (trade page). This module validates targets against
live data so Ananta cannot send the app somewhere that does not exist.
"""
from __future__ import annotations

import re

SCREENS = {
    "home": {"name": "Home", "where": "Home tab (house icon, first of four tabs since Oct 15)",
             "shows": "how the account is doing, what it traded, and whether anything needs you: the greeting with the Ananta button at the top "
                      "right (Ananta's mark; it shows a number when something waits), whether every part is running, the account card (the $500 "
                      "NDAX book in Canadian dollars: value since the start, holdings, cash, the dial and brakes), the account's trades (the old "
                      "Books tab), and the activity feed. The Ananta button opens Ananta's space: Needs you (a rule that passed and may step up, "
                      "portfolio changes, the mandate's actions), Ananta's note (the day in plain words), one line for the lab, and findings "
                      "(moves we missed or only saw, lessons), each as a row that opens to the full item; the More tab holds the switches and settings"},
    "markets": {"name": "Markets", "where": "Markets tab (trend-line icon, third tab; it was called Watchlists until Oct 14); its first page",
                "shows": "the trend dial first (OPEN or CLOSED, with why, and the brakes), then the watches, the coins with price, today's move, "
                         "1h/4h trend and how close each is to its nearest setup; above it, Ananta's reasoning: where each coin stops on the "
                         "decision chain (regime, trend, location, trigger, invalidation, risk, exposure); tap a coin for its page"},
    "portfolio": {"name": "Ananta market: trend portfolio (T3)", "where": "Markets tab, second page 'Ananta market', Trend sub-tab (Ananta's book is the row above; the Books tab folded in here on Oct 15)",
                  "shows": "the T3 portfolio value chart, the Autopilot switch, suggested changes, holdings with value, return and rating, cash and costs. "
                           "Not the $500 NDAX account: that account and what it holds are on Home (spot home.value)"},
    "portfolio:explorer": {"name": "Explorer trades", "where": "Markets tab, second page 'Ananta market', Explorer sub-tab",
                           "shows": "the Explorer's paper book: open trades with P&L, orders waiting to fill, closed trades"},
    "portfolio:mine": {"name": "My trades", "where": "Markets tab, second page 'Ananta market', Mine sub-tab",
                       "shows": "the owner's own paper book: positions, orders with reasons, research jobs"},
    "ananta": {"name": "Ask Ananta", "where": "Ask Ananta tab (the yellow voice wave, second tab)",
               "shows": "this conversation: type, dictate with the mic, or talk hands-free with the wave button; Sessions holds past conversations"},
    "evidence": {"name": "Evidence: inside the logic repair", "where": "the Evidence page (Home's Lab switch, then the Evidence row)",
                 "shows": "the repair loop live, in Madhav's order: looked, spotted, decided, scored, misses checked, sent to the repair "
                          "shop, changed; what is watching and how often; every limit with what it stopped and what those trades did; "
                          "results against random in market events; reconstruction (nightly rebuilds, the ones he asked for, mismatches, "
                          "the other-traders study and its chain); missed moves and patterns; the repair board (found, done, change, "
                          "status); what changed; what we wait for with dates at this pace. The older research cards fold below."},
    "evidence:forwarded": {"name": "Evidence: forwarded and in use", "where": "the Evidence page, lower part",
                           "shows": "repairs that passed and run in paper (T3 vs buy-and-hold) and the safety changes"},
    "jarvis": {"name": "Ananta's book", "where": "the Ananta button on Home, or the top row of Markets > Ananta market",
               "shows": "Ananta's own paper trades: the score against its random twins (running line, events to a verdict), open trades with "
                        "the room left to the stop, what its plans leaned on and the confidence check, and recent decisions with their thesis"},
    "missed": {"name": "What we missed", "where": "Home > the Ananta button > Findings > Missed moves",
               "shows": "each day's biggest rises: caught, seen or missed, and why; and the misses that keep coming back"},
    "cockpit": {"name": "More", "where": "More tab (sliders icon, fourth and last tab; it was called Cockpit until Oct 14). The menu button at the top left of every tab opens the side drawer with every tab and its parts",
                "shows": "the controls (kill switch, portfolio autopilot, locked live-trading switch, Ask and Voice switches), Voice and model "
                         "(who answers, the voice, the Claude budget), Evidence (the reviews, the repair loop, strategy status), System (every part "
                         "running, recent actions, costs), your mandate, the test lab, active alerts"},
    "mandate": {"name": "Your mandate", "where": "More > Additional features > Your mandate", "shows": "your goals, markets, styles, setups, limits and how Ananta should talk"},
    "testlab": {"name": "Test lab", "where": "More > Voice and model > Test lab", "shows": "recorded test runs of Ananta with answers to mark Good / OK / Bad"},
}
ALIASES = {
    "home": "home", "home screen": "home", "main": "home", "start": "home", "dashboard": "home", "inbox": "home", "brief": "home", "activity": "home",
    "market": "markets", "markets": "markets", "watchlists": "markets", "watchlist": "markets", "watch list": "markets", "scan": "markets", "scanner": "markets",
    "portfolio": "portfolio", "t3": "portfolio", "holdings": "portfolio", "trend portfolio": "portfolio",
    # request #73 (Oct 20): "that $500 we are holding" is the NDAX account on Home, never the trend portfolio (T3)
    "$500": "home", "500 book": "home", "500 dollar book": "home", "five hundred": "home", "ndax": "home", "the account": "home",
    "our account": "home", "my account": "home", "account": "home", "positions we hold": "home", "current positions": "home",
    "what we are holding": "home", "what we're holding": "home",
    "explorer": "portfolio:explorer", "explorer trades": "portfolio:explorer", "open trades": "portfolio:explorer", "trades": "portfolio:explorer",
    "my trades": "portfolio:mine", "my book": "portfolio:mine", "my paper book": "portfolio:mine", "manual book": "portfolio:mine",
    "ananta": "ananta", "chat": "ananta", "voice": "ananta", "conversation": "ananta",
    "evidence": "evidence", "lab": "evidence", "repair shop": "evidence", "repair board": "evidence", "evidence tracker": "evidence", "forwarded": "evidence:forwarded",
    "jarvis": "jarvis", "jarvis's book": "jarvis", "jarvis book": "jarvis", "your book": "jarvis", "your trades": "jarvis", "books": "home",
    "ananta market": "portfolio", "the lab": "portfolio", "lab books": "portfolio", "needs you": "home", "your note": "home", "ananta's note": "home", "the note": "home",
    "missed": "missed", "missed moves": "missed", "what we missed": "missed", "findings": "missed",
    "cockpit": "cockpit", "more tab": "cockpit", "the more tab": "cockpit", "settings": "cockpit", "controls": "cockpit", "kill switch": "cockpit", "budget": "cockpit", "alerts": "cockpit",
    "dial": "markets", "trend dial": "markets", "brakes": "markets",
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
    if low.startswith("jtrade:"):
        tid = t[7:].strip()
        try:
            r = j.db.execute("SELECT coin FROM evidence_trades WHERE id=?", (tid,)).fetchone()
        except Exception:  # noqa: BLE001
            r = None
        return (f"jtrade:{tid}", f"{r[0]} evidence trade") if r else (None, "no such trade")
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
    if what in ("more", "the more"):                 # "open More" is the last tab (Oct 14); "tell me more" never is, so no alias
        what = "cockpit"
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
    if sc == "jtrade" and here.get("id"):
        return f"jtrade:{here['id']}"
    if sc == "explorer_trades":
        return "portfolio:explorer"
    if sc == "manual_book":
        return "portfolio:mine"
    if sc == "evidence":
        return "evidence:forwarded" if here.get("tab") == "forwarded" else "evidence"
    return sc


def _has(word: str, low: str) -> bool:
    """The alias as a whole word (also "$500", which starts with a symbol, so a plain \\b cannot frame it)."""
    return bool(re.search(r"(?<!\w)" + re.escape(word) + r"(?!\w)", low))


def guess(text: str) -> str | None:
    """Best place in the app for a question, from its words (longest alias first)."""
    low = text.lower()
    for k in sorted(ALIASES, key=len, reverse=True):
        if _has(k, low):
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
    "home": {"home.decision": "the decision line: what Ananta is doing with the account, in one sentence", "home.status": "whether every part is running (the health strip)", "home.value": "the account: the $500 NDAX book, its value since the start, holdings, cash, the dial",
             "home.books": "the account's trades (Ananta today before the account started); since Oct 15 Needs you, Ananta's note, the lab and findings are inside the Ananta button, not spots on the page",
             "books.trades": "the account's trades with their stamps", "home.activity": "the activity feed"},
    "jarvis": {"jarvis.decision": "the decision line: the verdict so far against the twins", "jarvis.score": "the score against the random twins", "jarvis.open": "Ananta's open trades", "jarvis.learning": "what its plans leaned on and the confidence check",
               "jarvis.decisions": "recent decisions with their thesis"},
    "missed": {"missed.counts": "caught / seen / missed counts", "missed.moves": "the biggest moves and why", "missed.patterns": "misses that keep coming back"},
    "markets": {"markets.decision": "the decision line: buying allowed or not, and how many coins are ready", "markets.summary": "how many coins are trending up and the BTC gate", "markets.dial": "the trend dial: OPEN or CLOSED, why, the brakes",
                "markets.watches": "his watches: coins or a group, the setup, the mode, how close", "markets.coins": "the coins Ananta watches: price, change, 1h trend",
                "markets.whole": "the whole market: every coin watched live by tier, movers, near support", "markets.chain": "Ananta's reasoning: where each coin stops on the decision chain", "markets.near": "nearing a trade: coins closest to every condition, with what is missing", "markets.reconstruction": "reconstruction: rebuilds, mismatches, findings",
                "markets.coin:<SYM>": "one coin's row: price, trend, closest setup"},
    "portfolio": {"portfolio.value": "portfolio value and its chart", "portfolio.autopilot": "the Autopilot switch",
                  "portfolio.suggested": "suggested changes waiting", "portfolio.holdings": "the holdings list header",
                  "portfolio.holding:<SYM>": "one holding: value, return, rating"},
    "portfolio:explorer": {"explorer.value": "Explorer book value", "explorer.trade:<trade id>": "one open Explorer trade", "explorer.closed": "closed trades"},
    "portfolio:mine": {"mine.value": "my paper book value", "mine.position:<SYM>": "one of my positions"},
    "evidence": {"evidence.gate": "the Engine Acceptance Gate: how many of the 27 checks pass, by area",
                 "evidence.tracker": "the repair loop strip: looked, spotted, decided, scored, missed, sent, changed",
                 "evidence.clocks": "what is watching and how often", "evidence.limits": "every limit and what it stopped",
                 "evidence.collected": "results against random (and by setup)", "evidence.rebuild": "reconstruction: rebuilds and other traders",
                 "evidence.misses": "missed moves and patterns", "evidence.forwarded": "the repair board: found, done, change, status",
                 "evidence.shop": "what we wait for and when, at this pace",
                 "evidence.ideas": "ideas from the teachers (Rayner, Trade With Trend) with their test status",
                 "evidence.credit": "credit tracking: what each layer contributed, live"},
    "evidence:forwarded": {"evidence.in_use": "repairs running in paper (T3 vs buy-and-hold)", "evidence.safety": "safety changes"},
    "cockpit": {"cockpit.controls": "kill switch, autopilot, live trading", "cockpit.ai": "the Ask Ananta and Voice Assist switches",
                "cockpit.evidence": "the Evidence: every repair-shop review with a human name"},
    "coin": {"coin.chart": "the candle chart", "coin.position": "our position in this coin", "coin.market": "market picture and setup checklist",
             "coin.levels": "next support and resistance", "coin.setup:<E1-E5>": "one setup's checklist (opens it)",
             "coin.chain": "the decision chain ladder for this coin: each gate passed or where it stops, plus evidence",
             "coin.reads": "your setups on this coin: capitulation, higher-low retest, quiet base, with the news check",
             "coin.zones": "zones around this coin's price: inside / next support / next resistance, the lookout and plan",
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
    if pre == "books":                       # Oct 15: the account's trades sit on Home
        return "home"
    if head in ("evidence.in_use", "evidence.safety"):
        return "evidence:forwarded"
    return {"home": "home", "markets": "markets", "portfolio": "portfolio", "evidence": "evidence", "cockpit": "cockpit",
            "coin": "coin", "trade": "trade", "jarvis": "jarvis", "missed": "missed"}.get(pre)


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
    "home.value": r"value|worth|today|\$|inbox|waiting|approve|ok\b|jarvis|decision|miss|seen|lesson|finding|note", "home.books": r"explorer|hourly|portfolio|books?|watch|my trades|i took",
    "home.activity": r"activity|recent|happened", "home.status": r"running|health|parts?|down\b", "jarvis.score": r"random|twins?|beat|score", "jarvis.open": r"open|holding|stop",
    "jarvis.learning": r"knowledge|learn|confidence", "jarvis.decisions": r"decid|pass|bought", "missed.moves": r"miss|move|rise",
    "missed.patterns": r"keep|again|pattern", "missed.counts": r"caught|seen|missed",
    "markets.summary": r"trend|breadth|gate|coins? (?:are|is)|up\b", "portfolio.value": r"value|worth|\$|up\b|down\b",
    "portfolio.autopilot": r"autopilot", "portfolio.suggested": r"suggest|change|waiting", "portfolio.holdings": r"holding|coins",
    "explorer.value": r"value|worth|\$|explorer", "explorer.closed": r"closed", "mine.value": r"value|worth|\$",
    "evidence.tracker": r"tracker|progress|milestone", "evidence.collected": r"collected|setups?|signals?",
    "evidence.forwarded": r"forward|repair|ticket|board", "evidence.shop": r"wait|queue|how long|when",
    "evidence.clocks": r"watch|scan|how often|every", "evidence.gate": r"gate|ready|accept|lock|checks? pass", "evidence.limits": r"limit|gate|block|stopp|cap",
    "evidence.rebuild": r"rebuild|reconstruct|mismatch|other traders|hyperliquid", "evidence.misses": r"miss|caught|seen", "evidence.in_use": r"running|in use|paper|buy.and.hold",
    "evidence.safety": r"safety", "cockpit.controls": r"kill|autopilot|live|switch", "cockpit.ai": r"ask|voice|budget|claude|gemini",
    "cockpit.evidence": r"evidence|review|repair",
    "markets.near": r"near|close|almost|missing", "markets.reconstruction": r"rebuild|reconstruct|mismatch",
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


def fill_list_points(points: list[dict], answer: str) -> list[dict]:
    """When Jarvis points at coins in a list ('Bitcoin is up... Solana is down...') but not at every one, each sentence that
    names exactly one coin of the same list gets its own highlight, so the glow follows the item being read out."""
    heads = {p["spot"].partition(":")[0] for p in points if ":" in p.get("spot", "")}
    heads &= {"markets.coin", "portfolio.holding", "mine.position"}
    if len(heads) != 1:
        return points
    head = heads.pop()
    sents = [x for x in re.split(r"(?<=[.!?])\s+", answer or "") if x.strip()]
    have = {p["sentence"] for p in points}
    out = list(points)
    for i, x in enumerate(sents):
        if i in have:
            continue
        hits = {sym for name, sym in COINS.items() if re.search(r"\b" + re.escape(name) + r"\b", x, re.I)}
        if len(hits) == 1:
            out.append({"spot": f"{head}:{hits.pop()}", "sentence": i})
    return sorted(out, key=lambda p: p["sentence"])


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
         "say": "Welcome, Madhav. This is Home: how the account is doing, what it traded, and whether anything needs you. Three lines per card; More opens the rest."},
    ]
    steps += [
        {"spot": "home.status", "say": "This strip says whether every part of me is running. I check them every two minutes and ping your phone if one goes quiet."},
        {"spot": "home.value", "say": "This is the account: the 500-dollar NDAX book, its value since the start, its holdings and cash, and the dial."},
        {"spot": "books.trades", "say": "Below it are the account's trades, every one with its stamp. The lab's books live under Markets, on the Ananta market page."},
        {"spot": "home.activity", "say": "And this is the activity feed: every buy, sell, alert and change, in plain words. Tap a trade to open it."},
        {"spot": "home.value", "say": ("My mark at the top right is the Ananta button. It shows a number when something waits for you" + (f": {inbox} right now" if inbox else "")
                                       + ". Inside are what needs you, my note of the day, the lab in one line, and findings: moves we missed and lessons.")},
        {"ui": {"do": "go_to", "target": "markets", "label": "Markets"}, "spot": "markets.summary",
         "say": f"This is Markets. The trend dial comes first, then our watches. Right now {up} of our {n} coins are in a one-hour uptrend."},
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
         "say": "This is the Evidence page: the repair loop, live. From what we looked at, to what we traded, to what we fixed. It lives under More now. Tap any row and it explains itself."},
        {"spot": "evidence.forwarded", "say": "This is the repair board: everything sent to the repair shop, what we found, what we did, the change and its status."},
        {"ui": {"do": "go_to", "target": "cockpit", "label": "More"}, "spot": "cockpit.controls",
         "say": "This is More, the last tab. The kill switch and Autopilot live here, live trading stays locked, and below are voice and model, evidence and system."},
        {"spot": "cockpit.ai", "say": "Here you can switch me on or off and set a daily budget for Claude, so I never run up costs."},
        {"ui": {"do": "go_to", "target": "ananta", "label": "Ask Ananta"},
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
        return {"screen": "cockpit", "spot": "cockpit.controls"}
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


# ---------------------------------------------------------------------------
# Say = show (request #73, Oct 20): the screen an answer opens is the book the voice talks about.
# Madhav asked about "that $500 we are holding"; the voice spoke about the $500 NDAX book (Home) while the screen opened the trend
# portfolio (T3): the move was picked from keywords ("portfolio", "holdings") on paths apart from the words read aloud.
# say_show() reads the SPOKEN words and keeps, retargets or drops each move to a book.
# ---------------------------------------------------------------------------
BOOKS = [  # words that name a book or place out loud -> the screen that shows it. Ananta is the one speaking: "my book" is Ananta's,
    # "your book" is Madhav's. The dial, the market gate and the brakes are on Home AND Markets, so they name neither (only the
    # "trend dial", Markets' own name for it, names Markets).
    ("home", r"\$\s?500\b|\b500[- ]dollars?\b|\b500 book\b|\bfive[- ]hundred[- ]dollars?\b|\bndax\b|\b(?:the|our|your) account\b|"
             r"\baccount's\b|\breal book\b|\bhome\b"),
    ("portfolio", r"\btrend portfolio\b|\bt3\b|\bautopilot\b"),
    ("portfolio:explorer", r"\bexplorer\b"),
    ("portfolio:mine", r"\byour (?:own )?(?:paper |practice )?(?:book|trades|orders)\b|\bmanual book\b"),
    ("jarvis", r"\bmy (?:own )?(?:paper )?book\b|\b(?:ananta|jarvis)'?s (?:own )?book\b|\brandom twins?\b"),
    ("evidence", r"\bevidence\b|\brepair (?:shop|board|loop)\b|\bacceptance gate\b|\bchecks? pass|\bbacktests?\b|"
                 r"\b(?:the|our|a) (?:\w+ ){0,2}(?:review|study)\b"),
    ("evidence:forwarded", r"\bforwarded\b|\bsafety changes?\b"),
    ("markets", r"\bmarkets (?:tab|page|screen)\b|\bwatch ?lists?\b|\bour watches\b|\bdecision chain\b|\btrend dial\b"),
    ("missed", r"\bmissed moves?\b|\bwhat we missed\b|\bmoves we (?:missed|only saw)\b"),
    ("cockpit", r"\bcockpit\b|\bmore tab\b|\bkill switch\b|\bthe controls\b|\bsettings\b"),
]
BOOK_SCREENS = {s for s, _ in BOOKS}         # the Ask tab, the mandate, the test lab, coin and trade pages: never touched
SAME_PAGE = {"evidence:forwarded": "evidence"}  # the forwarded list is the lower part of the Evidence page
MAIN_SPOT = {"home": "home.value", "portfolio": "portfolio.value", "portfolio:explorer": "explorer.value", "portfolio:mine": "mine.value",
             "jarvis": "jarvis.score", "evidence": "evidence.tracker", "evidence:forwarded": "evidence.in_use", "markets": "markets.summary",
             "missed": "missed.moves", "cockpit": "cockpit.controls"}
VAGUE = {"portfolio", "holdings", "trades", "open trades", "books", "lab", "the lab", "lab books", "ananta market"}   # Madhav says "portfolio" for the $500 account too
BACK_ASK = re.compile(r"\b(?:go|going|take me|bring me|head|come) back\b|\bback to\b|\bprevious (?:page|screen)\b|^\W*back\b", re.I)


def books_named(text: str) -> list[str]:
    """The books and places these spoken words name, in the order they are first named."""
    hits = [(m.start(), s) for s, rx in BOOKS for m in [re.search(rx, text or "", re.I)] if m]
    return [s for _, s in sorted(hits)]


def _page(t: str | None) -> str:
    return SAME_PAGE.get(t or "", t or "")


def _on(p: dict, target: str | None) -> bool:
    """This highlight sits on that screen."""
    return _page(spot_screen(str(p.get("spot", "")))) == _page(target)


def asked_for(question: str, target: str, vague_ok: bool = True) -> bool:
    """He asked to SEE this place: a show-me request that names it ("show me the Explorer"). The vague words ("portfolio",
    "holdings", "trades") count only when vague_ok. "Open" as in "our open trades" is not a request to open anything."""
    if not SHOW_INTENT.search(re.sub(r"\bopen (?=(?:trades?|positions?|orders?)\b)", "", question or "", flags=re.I)):
        return False
    low = (question or "").lower()
    return any(_page(v) == _page(target) and (vague_ok or k not in VAGUE) and _has(k, low) for k, v in ALIASES.items())


def _move_points(points: list[dict], old: str, new: str, spoken: str) -> list[dict]:
    """The highlights on the old screen go; the new screen's main spot glows on the first sentence that names its book."""
    out = [p for p in points if not _on(p, old)]
    if MAIN_SPOT.get(new) and not any(_on(p, new) for p in out):
        sents = [x for x in re.split(r"(?<=[.!?])\s+", spoken or "") if x.strip()]
        k = next((i for i, x in enumerate(sents) if re.search(dict(BOOKS)[new], x, re.I)), 0)
        if not any(p.get("sentence") == k for p in out):            # one highlight per sentence
            out = sorted(out + [{"spot": MAIN_SPOT[new], "sentence": k}], key=lambda p: p.get("sentence", 0))
    return out


def say_show(j, spoken: str, ui: list[dict], points: list[dict], question: str = "", here: dict | None = None) -> tuple[list[dict], list[dict], str]:
    """Make the screen show the book the voice SAYS (request #73). spoken = the words read aloud (speak_text). Each move to a book:
    - its book is named in the spoken words: keep it
    - he asked for this very place ("show me the Explorer"): keep it
    - exactly one other book is named: move there instead, with the highlights
    - he asked with a vague word ("show me the portfolio") and no book is named: keep it
    - otherwise drop it and its highlights: better no move than a wrong move.
    A go_to undone by a back in the same answer only flashes a screen: both go, unless he asked to go back.
    -> (ui, points, note for the reply's meta: 'kept X' / 'retargeted X->Y' / 'dropped X', joined with '; ')."""
    ui = [dict(u) for u in ui or [] if isinstance(u, dict)]
    points = [dict(p) for p in points or [] if isinstance(p, dict)]
    notes: list[str] = []
    if not BACK_ASK.search(question or ""):
        kept: list[dict] = []
        for u in ui:
            last = next((i for i in range(len(kept) - 1, -1, -1) if kept[i].get("do") in ("go_to", "open", "back")), None)
            if u.get("do") == "back" and last is not None and kept[last].get("do") == "go_to":
                gone = kept.pop(last)
                points = [p for p in points if not _on(p, gone.get("target"))]
                notes.append(f"dropped {gone.get('target')}+back")
                continue
            kept.append(u)
        ui = kept
    said = books_named(spoken)
    cur = here_target(here)
    out: list[dict] = []
    for u in ui:
        t = u.get("target") or ""
        if u.get("do") not in ("go_to", "open") or t not in BOOK_SCREENS:
            out.append(u)
            continue
        others = [s for s in said if _page(s) != _page(t)]
        if len(others) < len(said):
            notes.append(f"kept {t}")
            out.append(u)
        elif asked_for(question, t, vague_ok=False):
            notes.append(f"kept {t} (asked)")
            out.append(u)
        elif len({_page(s) for s in others}) == 1:
            new = others[0]
            points = _move_points(points, t, new, spoken)
            notes.append(f"retargeted {t}->{new}" + (" (already open)" if new == cur else ""))
            if new != cur:
                out.append({"do": "go_to", "target": new, "label": SCREENS[new]["name"]})
        elif not others and asked_for(question, t):
            notes.append(f"kept {t} (asked)")
            out.append(u)
        else:
            points = [p for p in points if not _on(p, t)]
            notes.append(f"dropped {t}")
    return dedupe(out), points, "; ".join(notes)
