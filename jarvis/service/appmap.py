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
                         "1h/4h trend and how close each is to its nearest setup; tap a coin for its page"},
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
    return {"places": [{"target": k, **v} for k, v in SCREENS.items()],
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
    """Plain navigation ("take me home", "open Ethereum", "show me my bitcoin trade", "go back") without a model call."""
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


CLAIM = re.compile(r"\b(taking you|take you|i'?ve (?:opened|moved|pulled up|taken you|brought)|i have (?:opened|moved|pulled up)|i'?m (?:opening|taking you|moving)|"
                   r"let me (?:open|take you|show you)|opening (?:it|the|your|our|up)|i (?:opened|moved) )", re.I)
SHOW_INTENT = re.compile(r"\b(show me|take me|open|go to|bring me|where (?:can|do) i (?:see|find)|let'?s (?:go|move) to|next page)\b", re.I)


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


def keep_honest(j, question: str, answer: str, ui: list[dict], here: dict | None) -> tuple[list[dict], str]:
    """Make what Ananta SAYS about the screen match what the app WILL do.
    - drop moves to the screen that is already open
    - a 'show me / take me' request, or an answer that claims a move, with no move: add the best-guess move if it resolves
    - still nothing to open but the answer claims a move: say plainly that the screen did not move."""
    cur = here_target(here)
    ui = [u for u in ui if not (u.get("do") != "back" and u.get("target") == cur)]
    claims = bool(CLAIM.search(answer or ""))
    if not ui and (claims or SHOW_INTENT.search(question or "")):
        t = guess(question) or (guess(answer) if claims else None)
        if t and t != cur:
            v, label = resolve(j, t)
            if v:
                ui = [{"do": "open" if v.split(":")[0] in ("coin", "trade") else "go_to", "target": v, "label": label}]
    if claims and not ui:
        answer = (answer or "").rstrip() + " (I couldn't move the screen for this one; it is still on the same page.)"
    return ui, answer
