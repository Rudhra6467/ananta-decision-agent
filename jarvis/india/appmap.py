"""The India app map: every place in the Indian-market app and how Ananta moves Madhav there by voice or chat (flags 96 and 97, 24 Oct;
Madhav, 25 Oct: "the voice navigation is not working in India, make sure the integration is smooth and voice has good command on the app").

Ananta never touches the screen itself: an answer carries ui actions and highlight points; the app performs them and reports whether
they happened (jarvis/app/src/uiagent.ts). The same action shapes as crypto (jarvis/service/appmap.py), with India's own places:
  go_to <screen>        home, markets, ananta, evidence, reconstruction, missed, flags, teachers, cockpit
  open sheet:<name>     on India Home: stocks, options (the two boxes), money (Your money · More), morning (the morning view · Read)
  market market:crypto  switch the app to the crypto market
  points                light a part of Home while the answer is spoken (spot ids below)
"""
from __future__ import annotations

import re

PLACES = {
    "home": {"name": "Home", "shows": "your account (total, gain or loss, the Stocks and Options boxes), the morning view, Ananta's decisions, Your money, activity"},
    "sheet:stocks": {"name": "your stocks", "shows": "every holding: quantity, price paid, price now, value, gain or loss, Ananta's grade and action, Ask"},
    "sheet:options": {"name": "your options", "shows": "the options money, sessions traded, open positions, the last session, the expiry-day practice book"},
    "sheet:money": {"name": "Your money", "shows": "how Ananta splits stocks, options and cash, the guardrails, the market call, every holding ranked"},
    "sheet:morning": {"name": "the morning view", "shows": "the market, Ananta's plan, the chances, what to watch, the reviewer's second opinion, yesterday's scorecard"},
    "markets": {"name": "Markets", "shows": "the Nifty and the market's health, the stocks Ananta watches and its research book"},
    "ananta": {"name": "Ask Ananta", "shows": "this conversation, voice and chat"},
    "evidence": {"name": "Evidence", "shows": "the research tracker, the repair board, what is collected and forwarded"},
    "reconstruction": {"name": "the nightly reconstruction", "shows": "last night's card: the market, what people did, what Ananta did and missed, findings"},
    "missed": {"name": "What we missed", "shows": "the day's biggest moves: caught, seen or missed, and why"},
    "flags": {"name": "My flags", "shows": "every flag with where its fix stands"},
    "teachers": {"name": "Teachers, tested", "shows": "every claim from the two YouTube teachers as a tested card: what held up, what came out the wrong way, what is tracked live"},
    "cockpit": {"name": "More", "shows": "switches, voice and model, the market switch, settings"},
    "market:crypto": {"name": "the crypto market", "shows": "the crypto app"},
}
SPOTS = {"home.value": "your account: total and the Stocks and Options boxes", "home.morning": "the morning view card",
         "home.decision": "the one-line decision at the top", "home.status": "whether every part is running",
         "home.books": "Ananta's recent decisions", "home.money": "Your money · Ananta manages it", "home.activity": "the activity list"}
ALIASES = {
    "home": "home", "home screen": "home", "main screen": "home", "account": "home", "my account": "home", "dashboard": "home",
    "stocks": "sheet:stocks", "my stocks": "sheet:stocks", "holdings": "sheet:stocks", "my holdings": "sheet:stocks", "positions": "sheet:stocks",
    "my positions": "sheet:stocks", "portfolio": "sheet:stocks", "my portfolio": "sheet:stocks", "stock positions": "sheet:stocks", "shares": "sheet:stocks",
    "options": "sheet:options", "my options": "sheet:options", "option positions": "sheet:options", "options book": "sheet:options", "options line": "sheet:options",
    "money": "sheet:money", "my money": "sheet:money", "your money": "sheet:money", "allocation": "sheet:money", "the split": "sheet:money",
    "guardrails": "sheet:money", "cash": "sheet:money", "suggested changes": "sheet:money", "ratings": "sheet:money", "rankings": "sheet:money",
    "morning view": "sheet:morning", "morning brief": "sheet:morning", "morning card": "sheet:morning", "todays view": "sheet:morning",
    "today's view": "sheet:morning", "the view": "sheet:morning", "brief": "sheet:morning", "plan for today": "sheet:morning",
    "markets": "markets", "market": "markets", "markets tab": "markets", "nifty": "markets", "watchlist": "markets", "watch list": "markets",
    "stock list": "markets", "scanner": "markets", "research book": "markets", "practice book": "markets",
    "ananta": "ananta", "chat": "ananta", "ask": "ananta", "ask ananta": "ananta", "conversation": "ananta", "voice": "ananta",
    "evidence": "evidence", "lab": "evidence", "research": "evidence", "tracker": "evidence", "research tracker": "evidence", "repair board": "evidence",
    "reconstruction": "reconstruction", "nightly reconstruction": "reconstruction", "last night": "reconstruction", "last nights card": "reconstruction",
    "last night's card": "reconstruction", "the card": "reconstruction", "nightly review": "reconstruction", "replay": "reconstruction",
    "missed": "missed", "missed moves": "missed", "what we missed": "missed", "biggest moves": "missed",
    "flags": "flags", "my flags": "flags", "flag requests": "flags", "my flag requests": "flags", "flag list": "flags", "requests": "flags",
    "my requests": "flags", "repair shop": "flags", "fixes": "flags",
    "teachers": "teachers", "teacher": "teachers", "the teachers": "teachers", "youtube teachers": "teachers", "teachers results": "teachers",
    "teachers' results": "teachers", "teacher results": "teachers", "teacher cards": "teachers", "professor": "teachers", "the professor": "teachers",
    "professor's strategies": "teachers", "professors strategies": "teachers", "youtube classes": "teachers", "the youtube classes": "teachers",
    "classes": "teachers", "optionables": "teachers", "trade with trend": "teachers", "teacher strategies": "teachers", "teachers strategies": "teachers",
    "more": "cockpit", "more tab": "cockpit", "settings": "cockpit", "controls": "cockpit", "voice settings": "cockpit",
    "crypto": "market:crypto", "crypto market": "market:crypto", "crypto app": "market:crypto", "the crypto side": "market:crypto",
    "decisions": "home.books", "ananta's decisions": "home.books", "recent decisions": "home.books", "picks": "home.books", "todays picks": "home.books",
    "activity": "home.activity", "the activity": "home.activity",
}

LEAD = (r"^\s*(?:(?:hey|hi|ok(?:ay)?|so|yeah|yes|right|now|and)\b[,.!]?\s*)*(?:ananta[,.!]?\s*)?(?:please\s+)?"
        r"(?:can you |could you |would you |will you |i want (?:you )?to |i'?d like to |let'?s )?(?:please\s+)?")
NAV = re.compile(LEAD + r"(?:take me (?:back )?to|go (?:back )?to|bring (?:me |up )?(?:to )?|open(?: up)?|show(?: me)?|pull up|switch (?:me )?to|navigate to|move to|jump to|"
                 r"head to|get me to|i want to see|let me see|display)\s+(?:the |my |our )?(?P<what>[a-z' ]+?)(?:\s+(?:screen|page|tab|sheet|card|section|box))?"
                 r"(?:\s+(?:please|now|for me))*[.!?]*\s*$", re.I)
BACK = re.compile(LEAD + r"(?:go back|take me back|back|previous (?:page|screen)|close (?:it|this|that))(?:\s+please)?[.!?]*\s*$", re.I)
HOME = re.compile(LEAD + r"(?:take me|go|bring me|head)\s+(?:back\s+)?home(?:\s+please)?[.!?]*\s*$", re.I)
SCROLL = re.compile(LEAD + r"scroll (?P<dir>up|down|to the top|to the bottom)(?:\s+please)?[.!?]*\s*$", re.I)
WHERE = re.compile(r"\bwhere (?:is|are|can i (?:see|find)|do i (?:see|find))\s+(?:the |my |our )?(?P<what>[a-z' ]+?)\s*\??\s*$", re.I)


def action(target: str) -> dict:
    if target.startswith("market:"):
        return {"do": "market", "target": target, "label": PLACES[target]["name"]}
    if target.startswith("sheet:"):
        return {"do": "open", "target": target, "label": PLACES[target]["name"]}
    return {"do": "go_to", "target": target, "label": PLACES[target]["name"]}


def resolve(what: str) -> str | None:
    w = re.sub(r"\s+", " ", (what or "").strip().lower().replace("’", "'"))
    w = re.sub(r"^(?:the|my|our|your)\s+", "", w) if w not in ALIASES else w
    if w in ALIASES:
        return ALIASES[w]
    if w in PLACES:
        return w
    return None


def plan(target: str) -> dict:
    """The ui actions and highlight for a place or a Home spot, and the sentence to say."""
    if target in SPOTS:                                    # a part of Home: go there and light it
        return {"ui": [action("home")], "points": [{"spot": target, "sentence": 0}], "say": f"Here is {SPOTS[target]}, sir."}
    p = PLACES[target]
    if target == "market:crypto":
        return {"ui": [action(target)], "points": [], "say": "Switching you to the crypto market, sir."}
    if target.startswith("sheet:"):
        return {"ui": [action(target)], "points": [], "say": f"Opening {p['name']}, sir."}
    return {"ui": [action(target)], "points": [], "say": f"Taking you to {p['name']}, sir."}


def quick_command(text: str) -> dict | None:
    """Plain navigation, done in code with no model call: "take me home", "show my stocks", "open my flags", "go back", "switch to crypto",
    "scroll down", "where are my options?"."""
    t = (text or "").strip()
    if not t or len(t) > 90:
        return None
    m = SCROLL.match(t)
    if m:
        d = {"up": "up", "down": "down", "to the top": "top", "to the bottom": "bottom"}[m.group("dir").lower()]
        return {"ui": [{"do": "scroll", "dir": d, "label": f"Scroll {d}"}], "points": [], "say": "Sure."}
    if HOME.match(t):
        return plan("home")
    if BACK.match(t):
        return {"ui": [{"do": "back", "label": "Back"}], "points": [], "say": "Going back, sir."}
    m = NAV.match(t) or WHERE.search(t)
    if not m:
        return None
    target = resolve(m.group("what"))
    return plan(target) if target else None


def valid_ui(ui: list | None) -> list[dict]:
    """The model's ui actions, kept only when they name a real India place (it cannot send the app somewhere that does not exist)."""
    out = []
    for a in ui or []:
        if not isinstance(a, dict):
            continue
        if a.get("do") in ("back", "scroll"):
            out.append({k: a[k] for k in ("do", "dir", "label") if k in a})
            continue
        t = resolve(str(a.get("target") or "")) or (a.get("target") if a.get("target") in PLACES else None)
        if t and t in PLACES:
            out.append(action(t))
        elif t in SPOTS:
            out.append(action("home"))
    return out[:3]


def valid_points(points: list | None, n_sentences: int = 8) -> list[dict]:
    out = []
    for p in points or []:
        if isinstance(p, dict) and p.get("spot") in SPOTS:
            try:
                out.append({"spot": p["spot"], "sentence": max(0, min(n_sentences, int(p.get("sentence") or 0)))})
            except (TypeError, ValueError):
                continue
    return out[:4]


def for_prompt() -> str:
    return ("PLACES you can move the app to (ui target): " + "; ".join(f"{k} = {v['name']} ({v['shows']})" for k, v in PLACES.items())
            + ". SPOTS on Home you can light while you speak (points): " + "; ".join(f"{k} = {v}" for k, v in SPOTS.items()) + ".")
