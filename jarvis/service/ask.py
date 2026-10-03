"""Ask Ananta: the conversational layer over the Ananta system (phase 1: ask and explain, read-only).

How it works
  * The model never answers from its own head: it calls LOOKUPS (functions below) over Ananta's own data and
    answers only from what they return.
  * Providers are swappable: Gemini (free tier) and Claude (Anthropic API). Same lookups, same rules, so the
    two can be compared on real questions (feedback thumbs + latency are logged per provider).
  * Every answer comes in three layers at once: answer (just tell me), breakdown (break it down), evidence
    (show me the evidence), plus a stage label (observation ... learning).
  * Unclear question -> "Did you mean" options; after 2 failed tries -> says it did not understand + examples.
    Off-topic -> polite "not my area". Misunderstandings are logged for review.
  * Phase 1 has NO actions: requests to act get "I can't do that from chat yet" and point to the Cockpit.
"""
from __future__ import annotations

import json
import os
import re
import time
import uuid
from typing import Any, Callable

from jarvis.service import views

MAX_TOOL_ROUNDS = 10
HISTORY_TURNS = 8
DAILY_LIMIT = int(os.getenv("ASK_DAILY_LIMIT", "150"))
GEMINI_MODELS = [m.strip() for m in os.getenv("ASK_GEMINI_MODELS", "gemini-3.5-flash,gemini-3.1-flash-lite,gemini-flash-latest").split(",") if m.strip()]
GEMINI_MODEL = GEMINI_MODELS[0]       # free tier: when the first model is busy (503), the next one answers
CLAUDE_MODEL = os.getenv("ASK_CLAUDE_MODEL", "claude-sonnet-5-5")

SYSTEM = """You are Ananta (also called Jarvis), the trading assistant of one owner, Madhav. You are his trusted partner who knows trading well and talks with him like a close friend: warm, calm, honest, never salesy.

HOW TO TALK (most important)
- Very simple, easy English. Short sentences. Everyday words. No jargon; if a trading word is needed, explain it in a few words ("RSI, a gauge of how stretched the price is").
- Start "answer" with a short natural lead-in that shows you understood him, then the answer, then what it means for us. Example: "Sure, Madhav. You're asking whether we need to change anything. We don't: the portfolio is up about 2 percent and every coin is still in its uptrend, so nothing needs you right now."
- Use his name now and then, not in every answer. Greet warmly only when the conversation starts (by time of day: "Morning, Madhav.").
- Round numbers when talking ("about 2 percent", "around 86 thousand dollars"); exact figures go in breakdown and evidence.
- Explain like a friend sitting next to him: what is happening, why, and whether he needs to do anything.
- SIMPLE FIRST, DEEPER ON REQUEST: the first answer is the quick version (1-3 short sentences: the answer and what it means). When there is more worth knowing (the reasoning, numbers, gates, history), end with a short offer such as "Want the details?" or "I can go deeper into the setup if you want." Only when he asks to continue / go deeper / explain / show the details do you give the full technical version (all gates, numbers, evidence, which tier each statement comes from). Never dump everything at once.

WHAT ANANTA IS (use these words)
- Paper only. No real money, no exchange connected. Market: crypto spot, 10 coins (BTC ETH SOL ADA DOGE AVAX BCH LINK LTC XRP), buying only, NDAX costs (0.20% fee + spread per side).
- Watches (processes that keep running):
  * The 15-minute Explorer: checks 10 coins every 15 minutes for setups E1-E5 and trades them on paper ($100 each, own stop/target/warning bells). Trade types: Long-term (weeks), Short-term (days), Intraday (hours). Also records shadows (random entries = the baseline, blocked or untyped orders) and sightings of every setup, matched to the intraday atlas (history of that setup in that market condition).
  * The hourly watch: runs the strategies Hunter (reversal at support) and Squeeze (compression breakout) in the backend. Hunter is rare: about 2-8 times per coin per year. Its strategy book is called SD6.
- Strategies: Hunter and Squeeze (hourly watch); Continuation is benched (shadow only); Explorer setups E1 Pullback in an uptrend, E2 Breakout after a quiet period, E3 Bounce at support, E4 Momentum continuation, E5 Squeeze breakout; E6-E8 dip setups are watched, never traded; T3 is the portfolio trend strategy.
- Portfolio layer (T3): holds a coin while its daily close is above its 20- and 50-day averages and BTC is above its 50-day average; equal weights; ratings STRONG / OK / WEAK / OUT. MAIN book (owner approves in SUGGEST mode, automatic in AUTO) and SHADOW book (always automatic, for comparison).
- Repair shop: questions forwarded from evidence, pre-registered, tested on 2017-2023 then 2024-Jul 2026 data. Reviews 1-3 failed (no short-term entry beats costs), review 4 (T3) passed. The variable registry records what to KEEP / WATCH / DROP.
- Lifecycle words, always say which stage a thing is in: observation -> candidate setup (some conditions met) -> setup (all conditions met) -> decision (order placed or skipped) -> execution (filled) -> position -> outcome (closed) -> evaluation -> learning. Never let "interesting" sound like "bought".

HOW ANANTA REASONS (Madhav's framework; docs/knowledge/FRAMEWORK.md)
- The decision chain, fail-closed: REGIME (is the market allowed to be long?) -> TREND (is the coin in its own uptrend?) -> LOCATION (at a meaningful place: an area of value or the top of a base, not stretched) -> TRIGGER (did the signal actually happen?) -> INVALIDATION (where is the idea wrong?) -> RISK (can it be sized from that distance?) -> EXPOSURE (does it add to bets we already hold?). The first broken gate = no trade; missing data = no trade (a data gap, never "no setup"). Use the chain lookup for "should we buy X", "why no trade", "what is Ananta waiting for".
- Candles, volume, patterns and relative strength are EVIDENCE at a location inside a regime, never commands ("bullish engulfing, therefore buy" is wrong).
- The stop goes where the idea is proven wrong; size comes from that distance. Correlated alts are one bet with BTC.
- KNOWLEDGE TIERS: always make clear where a statement comes from: "our tested rule" (verified variables like V01, V02 or a passed repair-shop review), "Madhav's policy" (P01-P03), "a teacher's idea we have not tested yet" (hypotheses H01-H18 with their status: UNVERIFIED / FIRST_LOOK / PROMISING / NOT_SUPPORTED / SUPPORTED), or "what the data showed in your own trades" (the casebook). Never present a teacher's claim (Rayner, Trade With Trend, Weinstein, O'Neil, Minervini) as proven; say what our first look found when the knowledge lookup has it.

RULES
0. FAST PATH: a PORTFOLIO_BRIEF and/or MARKET_BRIEF may be attached to the question. They are live data. Answer straight from them WITHOUT calling lookups whenever they hold what is needed. Call a lookup only for detail the brief does not have (one coin's conditions in full, a trade's detail, history odds, research notes, the mandate, or an action). Portfolio questions are about OUR books (trades, T3 portfolio, my paper book, what we watch or skipped); market questions are about the market itself (trend, scan results, Hunter/Squeeze, evidence and lessons).
1. Facts only from the briefs and lookups. Call the lookups you need before answering (usually 1-4, at most 6; ask for several in one round when you can; never call the same lookup twice; after a propose_* lookup succeeds, answer straight away); use only the lookups listed, by their exact names. Never invent prices, trades, counts or history. If a lookup returns nothing, say the evidence is not there.
2. Setups: in the setups lookup, "complete" means all conditions were met at the last check. Report complete setups as complete even when no new trade was placed, and say why (already holding that coin's trade type, no trade type fits, caps). Never say "none are triggering" when the lookup shows complete ones.
2b. Keep separate: what the market is doing, what Ananta observed, which setup may be forming, which conditions are met or missing, what history says, what action (if any) is justified, whether anything was executed, the outcome, what was learned.
3. Uncertainty: small samples are small; say so (e.g. "1 day of live evidence"). No predictions or promises. Historical odds are odds, not forecasts.
4. Scope: trading, markets, the economy and news that moves markets, and Ananta itself. Anything else: kind "out_of_scope" with a one-line polite reply ("That's outside my area - I'm built for trading and markets.").
4b. OUTSIDE OUR SYSTEM: questions about a coin or token outside our 10-coin basket (BTC ETH SOL ADA DOGE AVAX BCH LINK LTC XRP), or about a coin's general facts (what it is, market cap, all-time high), are answered from outside our system: call outside_coin with the name he used, then answer from its live facts plus your general knowledge. Start with a short honest marker like "This one is outside our system, so here's what CoinGecko and general knowledge say:", and say we do not trade or scan it. Never mix these numbers into our portfolio or setups. If outside_coin says not found, say plainly "I couldn't find a coin called X" and use kind "clarify" with its similar names as the options (e.g. "Pepe (PEPE)"). Questions about OUR coins still come from our own data.
5. Actions you can PREPARE (the owner confirms each card in the app): paper orders in the owner's manual book (propose_paper_order), alerts (propose_alert), mandate changes (propose_mandate_change). You can START a read-only reconstruction (start_research). You cannot: place real orders (no exchange is connected; real orders come only after the live rules are approved), flip switches (kill switch and autopilot are in the Cockpit), or approve the portfolio's own suggestions (Portfolio screen). For those use kind "cannot_do_yet" and say exactly where to do it. If an order request is missing the amount, ask for it (clarify); check it against the mandate's limits and say if it conflicts.
6. Unclear: if the question could mean different things that lead to different answers, use kind "clarify" with 2-4 short "Did you mean" options. A message that does not say what it is about (e.g. "do the thing", "fix it", "that one") with no earlier topic in the conversation is unclear: clarify, never answer it with a status report. If one reading is clearly most likely, answer it and state the assumption. Follow-ups ("why?", "and before that?") refer to the last topic.
7. If the conversation note says clarification already failed twice, do not ask again: use kind "not_understood" with 3 example questions you can answer.
8. Money: $ with 2 decimals; percentages with 1-2 decimals; times in Toronto time if given.

9. Changes: use a propose_* lookup only when the owner explicitly asks for that action in this message (an order, an alert, a mandate change); never offer one unasked. You can only PREPARE changes (propose_* lookups). Say clearly that a confirmation card is waiting; never claim something was changed.
10. The owner's mandate (below) is the standing brief: follow its limits, use its goals to judge what matters, and point out when a request conflicts with it.
12. THE APP: you live inside the Jarvis app and can move the owner's screen with ui_go / ui_back. When he asks to go to, open, show or see something ("show me...", "open...", "take me...", "where can I see..."), you MUST CALL ui_go for the most relevant place (do not just describe it) and then talk as you show it ("Here's our Bitcoin trade..."). The screen context tells you the screen that is open right now: never claim he is on another screen, and never claim you moved the screen unless ui_go returned ok in this answer. For "where am I / what am I looking at", describe the open screen using app_map. Questions about the screen itself ("what's below this?", "what's at the bottom?", "what's above?") mean the parts of the open screen: call ui_scroll (down / bottom / up) and describe those parts using the spot list in order (not prices below). For "show me around" or a new user, explain the app tab by tab in simple words using app_map (open the first place with ui_go).
13. POINT AT WHAT YOU TALK ABOUT: add "points" so the app makes that thing glow (and scrolls to it) while that sentence is spoken: [{"spot": "<spot id>", "sentence": <index of the sentence in "answer", from 0>}]. Use spots of the screen that is open, or of the place you open with ui_go in this answer (if you point at a spot of another tab without ui_go, the app opens that tab for you). One spot per sentence at most; only point when it helps him find it. When you walk him through a screen or explain where something is, ALWAYS point at each part as you name it. Spot ids:
home.value | home.inbox | home.brief | home.books | home.activity ; markets.summary | markets.chain | markets.coin:<SYM> ; portfolio.value | portfolio.autopilot | portfolio.suggested | portfolio.holdings | portfolio.holding:<SYM> ; explorer.value | explorer.trade:<trade id> | explorer.closed ; mine.value | mine.position:<SYM> ; evidence.tracker | evidence.collected | evidence.forwarded | evidence.shop | evidence.ideas | evidence.in_use | evidence.safety ; cockpit.controls | cockpit.ai | cockpit.alerts | cockpit.systems ; on a coin page: coin.chart | coin.position | coin.market | coin.trades ; on a trade page: trade.pnl | trade.chart | trade.levels | trade.stop | trade.target | trade.why | trade.plan | trade.timeline ; on a coin page also coin.levels | coin.setup:<E1-E5> | coin.chain (the decision chain ladder).
14. PROVE IT: every number you give should be checkable in the app. In "evidence" items add "spot" (and "screen" when it is on another screen) for where that number is shown. When he asks "where did you get that?", "show me", "prove it" or "show me the trade you just mentioned", open that place with ui_go and point at it (points) while you explain; use the previous answer's evidence to know what "that" is. For a single trade, open the trade page (trade:<id>) and point at trade.pnl / trade.stop / trade.target; for a coin's setup, open the coin page and point at coin.setup:<E#>.
11. Screens: when it helps, add "show" items so the app can open the right screen: {"screen": "coin", "coin": "ETH"} | {"screen": "trade", "id": "<trade id>"} | {"screen": "markets"} | {"screen": "portfolio"} | {"screen": "evidence"} | {"screen": "cockpit"} | {"screen": "mandate"}, each with a short "label" like "Open ETH chart".

OUTPUT: reply with ONE JSON object and nothing else:
{"kind": "answer" | "clarify" | "not_understood" | "out_of_scope" | "cannot_do_yet",
 "stage": one lifecycle word or "" ,
 "answer": "the quick version: lead-in + direct answer + what it means, 1-3 short sentences in easy English, ending with a short offer to go deeper when there is more (on a continue/go-deeper request: the fuller version, up to 6 sentences)",
 "breakdown": ["at most 4 short bullets (max 15 words each): the reasoning"],
 "evidence": [{"label": "...", "value": "...", "source": "brief or lookup name", "time": "when, if known", "spot": "where it is shown, if anywhere", "screen": "place to open for it, if not the open screen"}] (at most 4),
 "assumption": "the reading you assumed, or empty",
 "options": ["for clarify only: short options"],
 "follow_ups": ["2 natural next questions he might ask"],
 "show": [{"screen": "...", "label": "..."}],
 "points": [{"spot": "...", "sentence": 0}]}"""

OFF = {"type": "object", "properties": {}}


def _schema(props: dict, req: list | None = None) -> dict:
    return {"type": "object", "properties": props, **({"required": req} if req else {})}


COIN = {"type": "string", "description": "Coin symbol, e.g. ETH"}

TOOLS = [
    ("overview", "What Ananta is doing right now: watches, last checks, paper values, open trades, portfolio mode, kill switch, anything waiting for the owner.", OFF),
    ("market", "The market picture now for one coin or all 10: price, 1h/4h/daily trend, RSI, momentum, volume, support/resistance, BTC trend.", _schema({"coin": {**COIN, "description": "Optional coin; omit for all"}})),
    ("setups", "Explorer setups for a coin (or all coins): for each setup which conditions are met and which are missing right now, plus Hunter and Squeeze status from the hourly watch with the reasons they did not trigger.", _schema({"coin": {**COIN, "description": "Optional coin; omit for the closest candidates across all coins"}})),
    ("strategy", "Activity of a strategy over recent hours: hunter, squeeze, continuation, explorer (E1-E8) or t3/portfolio. Detections, near-misses, top reasons, trades.", _schema({"name": {"type": "string"}, "hours": {"type": "number"}}, ["name"])),
    ("trades", "Paper trades. status: open | closed | all. Optional coin. Includes entry, price, P&L, stop, target, exit reason, and what the shadow variants would have done.", _schema({"status": {"type": "string"}, "coin": COIN})),
    ("trade", "Full detail of one trade by its id (from trades): why it was bought, conditions at entry, exit plan, timeline, what-if variants.", _schema({"id": {"type": "string"}}, ["id"])),
    ("portfolio", "The T3 portfolio: value, return, holdings with cost and P&L, ratings and reasons, pending proposals, mode, comparison with buy-and-hold and the shadow book.", OFF),
    ("history", "What happened historically after a setup in the current market condition (intraday atlas, 2017-2026 5m data): odds of +3% before -1.5%, net after costs, typical 1h/4h/24h ranges. Give coin to use its current condition.", _schema({"setup": {"type": "string", "description": "E1-E8 or ANY"}, "coin": COIN})),
    ("evidence", "Evidence collected so far (counts, by setup, shadows, hourly looks, reconstruction match) and the repair shop: forwarded questions, verdicts, queue, repairs in use and how they are tracking.", OFF),
    ("knowledge", "Search Ananta's research and knowledge: repair shop reviews, rulebook, variable registry, studies, Madhav's framework, the teacher hypotheses (Rayner, Trade With Trend: claim, status, what our first look found) and the casebook of Madhav's own trades. Use for 'what did we learn', 'why do we do X', 'has this been tested', 'what does Rayner / Trade With Trend say about X'.", _schema({"query": {"type": "string"}}, ["query"])),
    ("chain", "Ananta's decision chain for one coin or all 10 (fail-closed): regime -> trend -> location -> trigger -> invalidation -> risk -> exposure; where each coin stops and why, the stop and size if it got that far, plus relative strength vs BTC, volume and setup family as evidence. Use for 'should we buy X', 'why no trade', 'what is Ananta waiting for', 'which coins are closest'.", _schema({"coin": {**COIN, "description": "Optional coin; omit for all"}})),
    ("changes", "What changed / happened in the last N hours: buys, sells, orders, portfolio moves, warnings, owner actions.", _schema({"hours": {"type": "number"}})),
    ("report", "The latest daily or weekly report text.", _schema({"kind": {"type": "string", "description": "daily | weekly"}})),
    ("alerts", "The owner's alerts: active ones, and recently fired ones with their messages.", OFF),
    ("propose_alert", "Prepare an alert when the owner asks to be told about something: kind price_above / price_below (value = price), "
     "move_pct (value = percent move in a day), setup (setup = E1-E5 or ANY: tells when that setup's conditions are all met). "
     "This does NOT create it: the owner confirms a card in the app. Alerts are checked every 15 minutes and cost nothing.",
     _schema({"kind": {"type": "string"}, "coin": COIN, "value": {"type": "number"}, "setup": {"type": "string"}, "note": {"type": "string"}}, ["kind", "coin"])),
    ("manual_book", "The owner's own manual paper book (orders the owner asked for, separate from the Explorer and the portfolio): cash, positions, P&L, recent fills with reasons, and the decision journal.", OFF),
    ("propose_paper_order", "Prepare a PAPER order in the owner's manual book when the owner asks to buy or sell. side buy | sell, coin, usd amount "
     "(for sell, omit usd to sell all), optional stop and target prices, and the owner's reason in their words. This does NOT trade: "
     "it shows a confirmation card (price now, size, exposure, cash after) that the owner must approve with Face ID. Never for real money.",
     _schema({"side": {"type": "string"}, "coin": COIN, "usd": {"type": "number"}, "stop": {"type": "number"}, "target": {"type": "number"},
              "reason": {"type": "string"}}, ["side", "coin"])),
    ("start_research", "Start a research job now (read-only, no cost): kind 'reconstruction' rebuilds every Explorer decision from raw candles "
     "and checks it matches the live log. The owner gets a phone note when done. Also returns recent jobs.",
     _schema({"kind": {"type": "string", "description": "reconstruction"}}, ["kind"])),
    ("outside_coin", "OUTSIDE OUR SYSTEM: live facts about any coin or token from CoinGecko (price, 24h/7d/30d move, market cap and rank, volume, "
     "all-time high, what it is). Use for coins outside our basket or general coin facts. Not found returns similar names to offer.",
     _schema({"name": {"type": "string", "description": "the coin name or symbol as the owner said it"}}, ["name"])),
    ("app_map", "The Jarvis app itself: every screen and tab, where it is, and what it shows. Use for 'where can I see X', 'what can I do here', 'show me around'.", OFF),
    ("ui_go", "Move the owner's screen: open a place in the app. target = a place from app_map (home, markets, portfolio, portfolio:explorer, "
     "portfolio:mine, ananta, evidence, evidence:forwarded, cockpit, mandate, testlab), coin:<SYM> for a coin page, or trade:<id> for a trade page. "
     "Use whenever the owner asks to go to, open, show or see something on screen, or when showing it makes the answer clearer. "
     "Returns ok or an error; the app then really opens it.", _schema({"target": {"type": "string"}}, ["target"])),
    ("ui_back", "Move the owner's screen back to the previous page.", OFF),
    ("ui_scroll", "Scroll the open screen: dir up | down | top | bottom.", _schema({"dir": {"type": "string"}}, ["dir"])),
    ("mandate", "The owner's mandate in full: goals, markets, styles, setups, limits, how to talk. Also any actions waiting for the owner.", OFF),
    ("propose_mandate_change", "Prepare a change to the owner's mandate when the owner asks to change their goals, limits, styles or preferences. "
     "This does NOT change anything: it creates a confirmation card the owner must approve in the app.",
     _schema({"section": {"type": "string", "description": "goal | markets_now | markets_later | styles | setups | limits | how_to_talk"},
              "op": {"type": "string", "description": "add | replace | remove"},
              "text": {"type": "string", "description": "the new sentence (add / replace)"},
              "old": {"type": "string", "description": "the existing sentence, exactly (replace / remove)"}}, ["section", "op"])),
]
TOOL_DESC = {n: d for n, d, _ in TOOLS}

HUNTER_REASONS = {
    "REJECTED_RSI_NOT_RESET": "RSI has not dropped enough to count as a reset",
    "REJECTED_NO_VCP_BASE": "no tight base (volatility contraction) under the price",
    "REJECTED_HTF_TREND_MISALIGNED": "the higher-timeframe trend points the other way",
    "REJECTED_NO_SUPPORT_ZONE": "no support zone nearby",
    "REJECTED_VOLUME_NOT_EXHAUSTED": "selling volume has not dried up yet",
    "REJECTED_CHASING_GREEN_CANDLE": "price already jumped (would be chasing a green candle)",
    "REJECTED_OUTSIDE_ATR_ZONE": "price is not close enough to the entry zone",
    "REGIME_FILTERED": "the market regime does not suit this strategy",
    "no_qualifying_setup": "no qualifying setup",
}


def _local_stt(audio_b64: str, mime: str) -> str | None:
    """Whisper on this Mac (free, ~1 s). None when the local voice server is not running, so Gemini is used instead."""
    if os.getenv("ANANTA_VOICE_LOCAL", "1") != "1":
        return None
    import requests

    try:
        r = requests.post(os.getenv("ANANTA_VOICE_URL", "http://127.0.0.1:8200") + "/stt", json={"audio_b64": audio_b64, "mime": mime}, timeout=30)
        return r.json()["text"] if r.status_code == 200 else None
    except Exception:  # noqa: BLE001
        return None


def _label_outside(reply: dict, found: list[dict]) -> None:
    """Answers built on outside data always carry the 'From AI' label and source; a coin we could not find becomes a 'did you mean'."""
    from jarvis.service import outside

    if not found:
        return
    hits = [f for f in found if f.get("found")]
    if hits:
        reply["outside"] = {"source": "CoinGecko + AI", "note": outside.NOTE, "url": hits[0].get("source_url"),
                            "coins": [h.get("symbol") for h in hits]}
        for e in reply.get("evidence") or []:
            e.setdefault("source", "CoinGecko")
        return
    miss = found[-1]
    if reply.get("kind") not in ("clarify", "out_of_scope"):
        reply["kind"] = "clarify"
    if not reply.get("options"):
        reply["options"] = [str(x) for x in (miss.get("similar") or [])[:4]]
    if "couldn't find" not in (reply.get("answer") or "").lower():
        reply["answer"] = f"I couldn't find a coin called '{miss.get('query', '')}'." + (" Did you mean one of these?" if reply["options"] else " Could you spell it another way?")
    reply["outside"] = {"source": "CoinGecko", "note": "Searched outside our system and found no exact match."}


def _pre_voice(context, text):
    """When the app will speak this answer in the natural voice, start making its audio now, so it is usually ready
    by the time the phone asks for it. A list (the tour) is one audio file per step. Returns the audio id(s), or None."""
    try:
        tts = context.get("tts") if isinstance(context, dict) else None
        if isinstance(tts, dict) and tts.get("voice") and text:
            from jarvis.service import speech

            speed = float(tts.get("speed") or 0.9)
            ids = [speech.prepare_answer(speech.sentences(item), str(tts["voice"]), speed) for item in (text if isinstance(text, list) else [text])]
            return ids if isinstance(text, list) else ids[0]
    except Exception:  # noqa: BLE001
        pass
    return None


VOICE_WORDS = 60
THANKS = re.compile(r"^\s*(thanks|thank you|thank you so much|thanks a lot|cheers)[\s.!,]*(madhav|ananta|jarvis)?[\s.!]*$", re.I)
OKAY = re.compile(r"^\s*(ok|okay|cool|great|nice|got it|perfect|alright|all right|stop|cancel|never ?mind|that'?s all|that is all)[\s.!,]*(ananta|jarvis)?[\s.!]*$", re.I)
REPEAT = re.compile(r"\b(say (that|it) again|repeat (that|it|please|yourself)|come again|pardon( me)?|what did you (just )?say|one more time)\b", re.I)


def speak_text(reply: dict) -> str:
    """What Ananta says aloud: the answer's first sentences (about 60 words at most; the rest stays on screen) and, for a
    'did you mean', the choices, so he can just say which one."""
    from jarvis.service import speech

    out, n = [], 0
    for x in speech.sentences(reply.get("answer") or ""):
        w = len(x.split())
        if out and n + w > VOICE_WORDS:
            break
        out.append(x)
        n += w
    t = " ".join(out)
    opts = [str(o) for o in (reply.get("options") or [])][:4] if reply.get("kind") == "clarify" else []
    if opts and not all(o.lower() in t.lower() for o in opts):
        t += " Did you mean " + (", ".join(opts[:-1]) + ", or " if len(opts) > 1 else "") + opts[-1] + "?"
    return t


class Lookups:
    """Read-only functions over Ananta's data. Each returns plain JSON-able data."""

    def __init__(self, j, thread: str | None = None, here_t: str | None = None, guest: bool = False):
        self.j = j
        self.guest = guest                    # a friend's read-only view: may ask, may not prepare anything
        self.here_t = here_t                  # the place open on his screen right now
        self._ex = None
        self.thread = thread
        self.created: list[dict] = []          # pending actions prepared during this answer
        self.ui: list[dict] = []               # screen moves the app performs after this answer
        self.outside: list[dict] = []          # facts fetched from outside our system (CoinGecko) for this answer

    @property
    def ex(self):
        if self._ex is None:
            self._ex = self.j._explorer()
        return self._ex

    def _eng(self, coin: str):
        if not self.ex:
            raise ValueError("the Explorer is not running")
        c = (coin or "").upper().replace("/USD", "")
        if c not in self.ex.st["engines"]:
            raise ValueError(f"unknown coin {coin}; Ananta watches {', '.join(self.ex.st['engines'])}")
        return c, self.ex.st["engines"][c]

    def _state(self, eng):
        T = eng.last_scan
        if T is None or not eng.ready():
            raise ValueError("this coin's engine is still warming up")
        return eng.state(T)

    def call(self, name: str, args: dict) -> Any:
        fn = getattr(self, "t_" + name, None)
        if self.guest and name == "start_research":
            return {"error": "Practice mode: research jobs run on Madhav's real evidence, so guests cannot start them. Explain that politely."}
        if fn is None:
            return {"error": f"There is no lookup named '{name}'. Use only the listed lookups. To answer, write the JSON object as plain text, not as a tool call."}
        try:
            return fn(**(args or {}))
        except Exception as exc:  # noqa: BLE001
            return {"error": str(exc)[:300]}

    # ---- lookups ----
    def t_overview(self) -> dict:
        s = views.day_summary(self.j)
        c = views.cockpit(self.j)
        xs = self.ex.status() if self.ex else None
        return {"now_utc": time.strftime("%Y-%m-%d %H:%M", time.gmtime(self.j.now())), "summary": s, "systems": c["systems"],
                "switches": {w["key"]: w["on"] for w in c["switches"]},
                "open_trades": [{k: t[k] for k in ("id", "coin", "setup", "type", "entry", "price", "pnl_usd", "suggestion", "why")} for t in (xs["open"] if xs else [])],
                "pending_orders": xs["pending_orders"] if xs else []}

    def t_market(self, coin: str | None = None) -> dict:
        coins = [coin] if coin else list(self.ex.st["engines"]) if self.ex else []
        out = {}
        for c in coins:
            cc, eng = self._eng(c)
            st = self._state(eng)
            d = views.sc.describe_state(st)
            d1 = list(eng.tf["1d"].bars)
            if len(d1) >= 2:
                d["change_24h_pct"] = round(100 * (eng.tf["5m"].last[4] / d1[-1][4] - 1), 2)
                d["change_7d_pct"] = round(100 * (eng.tf["5m"].last[4] / d1[-7][4] - 1), 2) if len(d1) >= 7 else None
            d["as_of_utc"] = time.strftime("%H:%M", time.gmtime(eng.last_scan))
            out[cc] = d
        return out

    def t_setups(self, coin: str | None = None) -> dict:
        hourly = views._hourly_strategies(self.j, hours=3)
        res: dict[str, Any] = {}
        coins = [coin] if coin else list(self.ex.st["engines"]) if self.ex else []
        for c in coins:
            cc, eng = self._eng(c)
            rows = views.sc.checklist(eng, self._state(eng))
            if not coin:
                rows = [r for r in rows if r["traded"] and r["met"] >= r["of"] - 1]
            res[cc] = {"explorer": [{"setup": r["setup"], "name": r["name"], "traded_by_explorer": r["traded"], "met": f"{r['met']}/{r['of']}",
                                     "complete": r["complete"], "missing": r["missing"],
                                     **({"conditions": r["conditions"]} if coin else {})} for r in rows],
                       "hourly_watch": {s: {**(v["latest"].get(cc) or {}),
                                            "reasons_plain": [HUNTER_REASONS.get(x, x) for x in ((v["latest"].get(cc) or {}).get("reasons") or []) if x]}
                                        for s, v in hourly.items()}}
        return {"note": "met = conditions true at the last 15-minute check. A setup is only traded when ALL are met (and a trade type fits).", "coins": res}

    def t_strategy(self, name: str, hours: float = 24) -> dict:
        n = name.lower()
        if n in ("hunter", "squeeze", "continuation", "trend_rider", "vcp"):
            hs = views._hourly_strategies(self.j, hours=hours)
            key = {"continuation": "trend_rider"}.get(n, n)
            s = hs.get(key) or hs.get(n)
            if not s:
                return {"strategy": n, "note": "no hourly-watch records for this strategy in the window", "available": list(hs)}
            s = dict(s)
            s["top_reasons_plain"] = {HUNTER_REASONS.get(k, k): v for k, v in s["top_reasons"].items()}
            return {"strategy": n, "hours": hours, **s, "paper_book_SD6": self._sd6()}
        if n in ("t3", "portfolio"):
            return self.t_portfolio()
        ev = views.evidence_collected(self.j)
        return {"strategy": "explorer", "by_setup": ev["collected"], "tracker": ev["tracker"][:7]}

    def _sd6(self) -> dict:
        hb = [h for h in views._jsonl(self.j.dir / "watch_heartbeat.jsonl", 50) if h.get("ok")]
        return (hb[-1].get("book") if hb else {}) or {}

    def t_trades(self, status: str = "open", coin: str | None = None) -> dict:
        out: dict[str, Any] = {}
        if not self.ex:
            return {"error": "Explorer not running"}
        if status in ("open", "all"):
            out["open"] = [t for t in self.ex.status()["open"] if not coin or t["coin"] == coin.upper()]
        if status in ("closed", "all"):
            rows = []
            for (js,) in self.ex.store.book.execute("SELECT json FROM events WHERE kind='CLOSED' ORDER BY seq DESC LIMIT 50"):
                e = json.loads(js)
                if coin and e["coin"] != coin.upper():
                    continue
                rows.append({"id": e["id"], "coin": e["coin"], "setup": e["setup"], "type": e["type"], "net_usd": e.get("net_usd"),
                             "exit": views.exit_text(e.get("bell")), "time": views._local(e["t"])})
            out["closed"] = rows
        out["hourly_watch_SD6_book"] = self._sd6()
        return out

    def t_trade(self, id: str) -> dict:  # noqa: A002
        d = views.trade_detail(self.j, id)
        d["chart"] = {"points": len(d["chart"]["points"])}
        return d

    def t_portfolio(self) -> dict:
        h = views.holdings(self.j)
        f = views.evidence_forwarded(self.j)
        t3 = next((x for x in f["in_use"] if x["id"] == "T3"), {})
        tr = dict(t3.get("tracking") or {})
        tr.pop("series", None)
        return {**h, "tracking_vs_buy_hold": tr, "expectation": t3.get("expect")}

    def t_history(self, setup: str = "ANY", coin: str | None = None) -> dict:
        p = self.j.dir / "intraday_atlas.json"
        if not p.exists():
            return {"error": "the intraday atlas is not available"}
        from src.research.intraday_atlas import lookup

        at = json.loads(p.read_text())
        s1 = b1 = None
        if coin:
            _, eng = self._eng(coin)
            st = self._state(eng)
            s1, b1 = st["S1"], st.get("btc_S1")
        hit = lookup(at, setup.upper(), s1, b1)
        if not hit:
            return {"error": f"no history for {setup}"}
        return {"setup": setup.upper(), "condition": {"coin_1h_trend": s1, "btc_1h_trend": b1}, "level": hit["level"],
                "history_2024_2026": hit["recent"], "positive_after_costs_in_both_periods": hit["stable_positive_after_costs"],
                "how_to_read": "p_target = share that reached the target before the stop; net_pct = average result after NDAX costs; ranges are 10th/50th/90th percentile moves in %. Brackets: e.g. '3/1.5_24h' = +3% target, -1.5% stop, 24 hours."}

    def t_evidence(self) -> dict:
        ev = views.evidence_collected(self.j)
        fw = views.evidence_forwarded(self.j)
        for x in fw["in_use"]:
            (x.get("tracking") or {}).pop("series", None)
        return {**ev, "in_use": fw["in_use"], "safety_changes": fw["safety_changes"]}

    def t_knowledge(self, query: str) -> dict:
        roots = [self.j.dir / "docs" / "repair_shop", self.j.dir / "docs" / "research", self.j.dir / "docs" / "knowledge",
                 self.j.dir / "docs" / "knowledge" / "teachers", self.j.dir / "docs" / "casebook"]
        files = [p for r in roots if r.exists() for p in r.glob("*.md")] + [self.j.dir / "docs" / "RULEBOOK_V0.md", self.j.dir / "docs" / "VARIABLE_REGISTRY.md"]
        words = [w for w in re.findall(r"[a-z0-9]+", query.lower()) if len(w) > 2]
        hits = []
        for p in files:
            if not p.exists():
                continue
            text = p.read_text()
            paras = re.split(r"\n(?=#)|\n\n", text)
            for para in paras:
                low = para.lower()
                score = sum(low.count(w) for w in words)
                if score:
                    hits.append((score, p.name, para.strip()[:900]))
        hits.sort(key=lambda h: -h[0])
        reg = self.j.dir / "docs" / "variable_registry.json"
        regs = []
        if reg.exists():
            r = json.loads(reg.read_text())
            for v in r["variables"]:
                blob = json.dumps(v).lower()
                if any(w in blob for w in words):
                    regs.append(v)
        hyp = []
        hp = self.j.dir / "docs" / "knowledge" / "hypotheses.json"
        if hp.exists():
            for h in json.loads(hp.read_text()).get("hypotheses", []):
                blob = json.dumps(h).lower()
                sc_ = sum(blob.count(w) for w in words)
                if sc_:
                    hyp.append((sc_, h))
            hyp.sort(key=lambda x: -x[0])
        return {"passages": [{"file": f, "text": t} for _, f, t in hits[:6]], "registry": regs[:8],
                "hypotheses": [h for _, h in hyp[:5]],
                "tiers": "registry = Ananta-verified variables; hypotheses = teacher ideas with their test status (not rules); casebook = Madhav's own trades"}

    def t_chain(self, coin: str | None = None) -> dict:
        from jarvis.service import chain

        b = chain.board(self.j)
        if coin:
            c = coin.upper().replace("/USD", "")
            row = next((r for r in b.get("coins", []) if r["coin"] == c), None)
            if row is None:
                raise ValueError(f"unknown coin {coin}")
            return {"framework": b["framework"], "note": b["note"], **row}
        return {k: b[k] for k in ("framework", "stops", "note")} | {"coins": [{k: r.get(k) for k in ("coin", "verdict", "stops_at", "summary", "observations")} for r in b.get("coins", [])]}

    def t_changes(self, hours: float = 24) -> dict:
        return {"hours": hours, "events": [{k: it.get(k) for k in ("time", "kind", "title", "body")} for it in views.feed(self.j, hours=hours, limit=40)]}

    def t_outside_coin(self, name: str) -> dict:
        from jarvis.service import outside

        r = outside.coin(name)
        self.outside.append(r)
        return r

    def t_app_map(self) -> dict:
        from jarvis.service import appmap

        return appmap.describe()

    def t_ui_go(self, target: str) -> dict:
        from jarvis.service import appmap

        t, label = appmap.resolve(self.j, target)
        if not t:
            return {"ok": False, "error": label}
        if t == self.here_t:
            return {"ok": True, "already_open": True, "note": "He is already on this screen. Do not move; answer about what he sees now."}
        if any(u.get("target") == t for u in self.ui):
            return {"ok": True, "already_queued": True, "note": "Already opening. Do not call ui_go again; write your answer now."}
        self.ui.append({"do": "open" if ":" in t and t.split(":")[0] in ("coin", "trade") else "go_to", "target": t, "label": label})
        return {"ok": True, "will_open": label, "note": "The app opens it as soon as you answer. Say 'here is ...' / 'taking you to ...'."}

    def t_ui_scroll(self, dir: str) -> dict:  # noqa: A002
        d = (dir or "").lower()
        if d not in ("up", "down", "top", "bottom"):
            return {"ok": False, "error": "dir is up, down, top or bottom"}
        self.ui.append({"do": "scroll", "dir": d, "label": f"Scroll {d}"})
        return {"ok": True}

    def t_ui_back(self) -> dict:
        self.ui.append({"do": "back", "label": "Back"})
        return {"ok": True}

    def t_mandate(self) -> dict:
        from jarvis.service.mandate import Mandate

        M = Mandate(self.j.db, self.j.now)
        return {**M.get(), "pending_actions": M.pending()}

    def t_propose_mandate_change(self, section: str, op: str, text: str = "", old: str = "") -> dict:
        from jarvis.service.mandate import SECTION_NAMES, Mandate

        if section not in SECTION_NAMES:
            return {"error": f"section must be one of {', '.join(SECTION_NAMES)}"}
        if op not in ("add", "replace", "remove") or (op != "remove" and not text.strip()):
            return {"error": "op is add / replace / remove, and add or replace needs text"}
        verb = {"add": "Add to", "replace": "Change in", "remove": "Remove from"}[op]
        summary = f"{verb} \"{SECTION_NAMES[section]}\": {text or old}"
        a = Mandate(self.j.db, self.j.now).propose("mandate", summary, {"section": section, "op": op, "text": text, "old": old}, self.thread)
        self.created.append(a)
        return {"prepared": a, "note": "Not applied. The owner sees a confirmation card and must approve it."}

    def t_alerts(self) -> dict:
        from jarvis.service.alerts import Alerts

        return {"alerts": Alerts(self.j.db, self.j.now).list()[:30]}

    def t_propose_alert(self, kind: str, coin: str, value: float | None = None, setup: str | None = None, note: str = "") -> dict:
        from jarvis.service.alerts import Alerts
        from jarvis.service.mandate import Mandate

        try:
            v = Alerts.validate({"kind": kind, "coin": coin, "value": value, "setup": setup, "note": note})
        except ValueError as exc:
            return {"error": str(exc)}
        if self.ex and v["coin"] not in self.ex.st["engines"]:
            return {"error": f"Ananta only watches {', '.join(self.ex.st['engines'])}"}
        summary = "Alert me when " + Alerts.describe(v["kind"], v["coin"], v["value"], v["setup"])
        a = Mandate(self.j.db, self.j.now).propose("alert", summary, v, self.thread)
        self.created.append(a)
        return {"prepared": a, "note": "Not active yet. The owner confirms the card in the app."}

    def t_manual_book(self) -> dict:
        from jarvis.service.manual import Manual

        Mn = Manual(self.j.db, self.j.now)
        return {**Mn.state(self.j.prices()), "fills": Mn.fills(15), "journal": Mn.journal(15)}

    def t_propose_paper_order(self, side: str, coin: str, usd: float | None = None, stop: float | None = None,
                              target: float | None = None, reason: str = "") -> dict:
        from jarvis.service.manual import Manual
        from jarvis.service.mandate import Mandate

        try:
            pv = Manual(self.j.db, self.j.now).preview({"side": side, "coin": coin, "usd": usd, "stop": stop, "target": target, "reason": reason},
                                                      self.j.prices())
        except ValueError as exc:
            return {"error": str(exc)}
        a = Mandate(self.j.db, self.j.now).propose("paper_order", pv["summary"], pv["order"], self.thread)
        self.created.append(a)
        return {"prepared": a, "preview": pv, "note": "Not executed. The owner confirms the card (Face ID); it fills at the price at that moment."}

    def t_start_research(self, kind: str) -> dict:
        from jarvis.service.manual import Manual

        Mn = Manual(self.j.db, self.j.now)
        if kind != "reconstruction":
            return {"error": "available research jobs: reconstruction", "recent": Mn.jobs(5)}
        from src.intelligence import explorer_live as xl

        def push(t, b):
            from src.intelligence.paper_watch import push_phone

            return push_phone(t, b, level="EVENT")
        j = Mn.start_job("ananta (asked by owner)", "reconstruction", lambda: xl.reconstruct(self.j.dir), push=push,
                         background=os.getenv("ASK_JOBS_INLINE") != "1")
        return {"started": j, "note": "Running in the background; takes a minute or two. The owner gets a phone note when done.", "recent": Mn.jobs(5)}

    def t_report(self, kind: str = "daily") -> dict:
        r = self.j._latest("explorer_weekly" if kind.startswith("w") else "explorer_daily")
        return r or {"error": f"no {kind} report yet"}


# ---------------------------------------------------------------------------
# providers (plain HTTPS, no SDKs)
# ---------------------------------------------------------------------------
def _post(url: str, headers: dict, body: dict, timeout: int = 60, retry: bool = True) -> dict:
    import requests

    for wait in ((2, 6, 0) if retry else (0,)):     # busy / rate-limited: retry twice
        try:
            r = requests.post(url, headers=headers, json=body, timeout=timeout)
        except requests.RequestException as exc:
            raise RuntimeError(f"503 network/timeout: {str(exc)[:120]}") from exc
        if r.status_code not in (429, 500, 502, 503, 529) or not wait:
            break
        time.sleep(wait)
    if r.status_code >= 400:
        raise RuntimeError(f"{r.status_code}: {r.text[:300]}")
    return r.json()


MODELS = {   # key: provider, API model, price per million tokens (input, output), cache-read multiplier
    "local": {"label": "Local (Mac)", "provider": "local", "model": os.getenv("ASK_LOCAL_MODEL", "qwen3.5:9b"), "price": (0.0, 0.0), "cache": 0.0},
    "gemini": {"label": "Gemini Flash", "provider": "gemini", "model": None, "price": (0.0, 0.0), "cache": 0.0},
    "gemini_deep": {"label": "Gemini Flash (thinking)", "provider": "gemini", "model": None, "price": (0.0, 0.0), "cache": 0.0},
    "haiku": {"label": "Claude Haiku", "provider": "claude", "model": os.getenv("ASK_HAIKU_MODEL", "claude-haiku-4-5-20251001"), "price": (1.0, 5.0), "cache": 0.1},
    "sonnet": {"label": "Claude Sonnet", "provider": "claude", "model": os.getenv("ASK_CLAUDE_MODEL", "claude-sonnet-5-5"), "price": (2.0, 10.0), "cache": 0.1},
    "opus": {"label": "Claude Opus", "provider": "claude", "model": os.getenv("ASK_OPUS_MODEL", "claude-opus-5-5"), "price": (4.0, 20.0), "cache": 0.05},
}
MODES = {"everyday": "gemini", "deep": "sonnet", "max": "opus", "google": "gemini_deep"}
# The app's two switches: Auto on/off x Claude/Google -> auto | deep | google_auto | google
ALIASES = {"claude": "sonnet", "gemini": "gemini", "haiku": "haiku", "sonnet": "sonnet", "opus": "opus", "local": "local"}
DEEP_WORDS = re.compile(r"\b(why|explain|compare|evaluat|analy[sz]|should|prepare|review|learn|history|histor|reconstruct|what if|strategy|strateg|backtest|"
                        r"evidence|break it down|reason|plan|risk|recommend|better|worse|improve|test)", re.I)


_LOCAL_UP = {"t": 0.0, "ok": False}


def local_up() -> bool:
    """Is the Mac's model server running? (checked at most once a minute)"""
    if os.getenv("ASK_LOCAL", "1") != "1":
        return False
    if time.time() - _LOCAL_UP["t"] > 60:
        import requests

        try:
            _LOCAL_UP["ok"] = requests.get(LOCAL_URL + "/api/version", timeout=1.5).status_code == 200
        except Exception:  # noqa: BLE001
            _LOCAL_UP["ok"] = False
        _LOCAL_UP["t"] = time.time()
    return _LOCAL_UP["ok"]


def route(text: str) -> tuple[str, str]:
    """Auto mode, cheapest level that can do it well and fast: investigations to Claude Sonnet, routine questions to Claude Haiku
    (about 0.5 cents). The Mac's model is too slow for live answers on a MacBook Air (20-80 s), so it does background jobs (mode
    "worker"). Over budget, Haiku/Sonnet fall back to Gemini like before."""
    if len(text) > 160 or DEEP_WORDS.search(text):
        return "sonnet", "Auto: Claude Sonnet, this needs investigation"
    if os.getenv("ANTHROPIC_API_KEY"):
        return "haiku", "Auto: Claude Haiku, routine question"
    return "gemini", "Auto: Gemini, everyday question"


def _local_doubt(raw: str, context: str) -> str:
    """Reasons not to trust a local answer: not valid JSON, empty, or numbers that appear nowhere in its data."""
    try:
        r = parse(raw)
    except Exception:  # noqa: BLE001
        return "no valid answer"
    if r.get("kind") not in ("answer", "clarify", "not_understood", "out_of_scope", "cannot_do_yet") or not (r.get("answer") or "").strip():
        return "empty answer"
    miss = grounded(r.get("answer", "") + " " + " ".join(str(e.get("value", "")) for e in r.get("evidence") or [] if isinstance(e, dict)), context)
    if miss:
        return "numbers not in its data: " + ", ".join(miss[:3])
    return ""


def cost_usd(key: str, usage: dict) -> float:
    m = MODELS.get(key) or MODELS["gemini"]
    pin, pout = m["price"]
    return round((usage.get("in", 0) * pin + usage.get("cache_write", 0) * pin * 1.25 + usage.get("cache_read", 0) * pin * m["cache"]
                  + usage.get("out", 0) * pout) / 1e6, 5)


def _strip_cache(msgs: list) -> None:
    for m in msgs:
        if isinstance(m.get("content"), list):
            for b in m["content"]:
                if isinstance(b, dict):
                    b.pop("cache_control", None)


FAST = {"claude_effort": os.getenv("ASK_CLAUDE_EFFORT", "low"), "gemini_thinking": os.getenv("ASK_GEMINI_THINKING", "low")}


def _post_opt(post, url, headers, body, opt_key: str, field_path: list[str]):
    """Post with a speed option; if the API rejects that option (400 naming it), drop it for good and post again."""
    try:
        return post(url, headers, body)
    except RuntimeError as exc:
        msg = str(exc)
        if msg.startswith("400") and any(f in msg for f in field_path):
            d = body
            path = [f for f in field_path if f in json.dumps(body)][:2] or field_path
            if opt_key == "claude_effort":
                body.pop("output_config", None)
            else:
                for f in path[:-1]:
                    d = d.get(f, {})
                d.pop(path[-1], None)
            return post(url, headers, body)
        raise


def run_claude(system: str, history: list[dict], user: str, tools: Lookups, log: list, post=_post, model: str | None = None) -> tuple[str, dict]:
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    model = model or CLAUDE_MODEL
    msgs = [{"role": m["role"], "content": m["text"]} for m in history] + [{"role": "user", "content": [{"type": "text", "text": user}]}]
    tdefs = [{"name": n, "description": d, "input_schema": s} for n, d, s in TOOLS]
    tdefs[-1] = {**tdefs[-1], "cache_control": {"type": "ephemeral"}}          # cache: tools + system
    sysb = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
    usage = {"in": 0, "out": 0, "cache_read": 0, "cache_write": 0}
    rnd = -1
    for _ in range(MAX_TOOL_ROUNDS + 3):
        rnd = min(rnd + 1, MAX_TOOL_ROUNDS)
        _strip_cache(msgs)                       # one moving breakpoint on the newest message (max 4 in total)
        last = msgs[-1]["content"]
        if isinstance(last, list) and last:
            last[-1]["cache_control"] = {"type": "ephemeral"}
        body = {"model": model, "max_tokens": 3000, "system": sysb, "tools": tdefs, "messages": msgs,
                **({"tool_choice": {"type": "none"}} if rnd == MAX_TOOL_ROUNDS else {})}   # last round: answer with what you have
        if FAST["claude_effort"] and "haiku" not in model:
            body["output_config"] = {"effort": FAST["claude_effort"]}               # less thinking = faster answers
        r = _post_opt(post, "https://api.anthropic.com/v1/messages",
                      {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"}, body, "claude_effort",
                      ["output_config", "effort"])
        usage["rounds"] = usage.get("rounds", 0) + 1
        u = r.get("usage") or {}
        usage["in"] += u.get("input_tokens", 0)
        usage["out"] += u.get("output_tokens", 0)
        usage["cache_read"] += u.get("cache_read_input_tokens", 0) or 0
        usage["cache_write"] += u.get("cache_creation_input_tokens", 0) or 0
        content = r.get("content") or []
        calls = [c for c in content if c.get("type") == "tool_use"]
        if not calls:
            text = "".join(c.get("text", "") for c in content if c.get("type") == "text")
            if not text.strip() and usage.get("nudged", 0) < 2:      # ended without words (only thinking): ask for the answer
                usage["nudged"] = usage.get("nudged", 0) + 1
                rnd = MAX_TOOL_ROUNDS - 1                           # the next round must answer
                msgs.append({"role": "assistant", "content": content or [{"type": "text", "text": "(no answer)"}]})
                msgs.append({"role": "user", "content": [{"type": "text", "text": "Please give your final answer now, as the JSON object."}]})
                continue
            usage["model"] = model
            return text, usage
        msgs.append({"role": "assistant", "content": content})
        results = []
        for c in calls:
            out = tools.call(c["name"], c.get("input") or {})
            log.append({"tool": c["name"], "args": c.get("input")})
            results.append({"type": "tool_result", "tool_use_id": c["id"], "content": json.dumps(out, default=str)[:20000]})
        msgs.append({"role": "user", "content": results})
    raise RuntimeError("too many lookup rounds")


def _gemini_schema(s: dict) -> dict:
    if not s.get("properties"):
        return None
    return s


_COOL: dict[str, float] = {}      # Gemini model -> time until which it is skipped (busy)


def run_gemini(system: str, history: list[dict], user: str, tools: Lookups, log: list, post=_post, thinking: str | None = None) -> tuple[str, dict]:
    """Free tier: a busy model (503/429) is skipped for 5 minutes and the next one answers at once (no waiting)."""
    err = None
    fast = (lambda u, h, b, timeout=45: _post(u, h, b, timeout, retry=False)) if post is _post else post
    models = [m for m in GEMINI_MODELS if _COOL.get(m, 0) < time.time()] or GEMINI_MODELS[-1:]
    for m in models:
        try:
            text, usage = _gemini_once(m, system, history, user, tools, log, fast, thinking)
            usage["model"] = m
            return text, usage
        except RuntimeError as exc:
            err = exc
            if not str(exc)[:3] in ("503", "429", "500", "404"):
                raise
            _COOL[m] = time.time() + (3600 if "quota" in str(exc).lower() else 90)   # daily free quota used up: skip for an hour
            log.clear()
    try:                                   # every model busy: one patient try on the main model before giving up
        text, usage = _gemini_once(GEMINI_MODELS[0], system, history, user, tools, log, post, thinking)
        usage["model"] = GEMINI_MODELS[0]
        return text, usage
    except RuntimeError as exc:
        err = exc
    raise RuntimeError(f"Gemini's free service is busy right now. Try again in a minute, or switch to Claude. ({str(err)[:80]})")


def _gemini_once(model: str, system: str, history: list[dict], user: str, tools: Lookups, log: list, post=_post, thinking: str | None = None) -> tuple[str, dict]:
    key = os.getenv("GEMINI_API_KEY", "")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    contents = [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["text"]}]} for m in history]
    contents.append({"role": "user", "parts": [{"text": user}]})
    decls = []
    for n, d, s in TOOLS:
        x = {"name": n, "description": d}
        if _gemini_schema(s):
            x["parameters"] = s
        decls.append(x)
    usage = {"in": 0, "out": 0}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    for rnd in range(MAX_TOOL_ROUNDS + 1):
        gc = {"temperature": 0.2, "maxOutputTokens": 4000}
        if FAST["gemini_thinking"]:            # (cleared by _post_opt when a model rejects thinking settings)
            gc["thinkingConfig"] = {"thinkingLevel": thinking or FAST["gemini_thinking"]}
        r = _post_opt(post, url, {"x-goog-api-key": key, "content-type": "application/json"},
                      {"systemInstruction": {"parts": [{"text": system}]}, "contents": contents,
                       "tools": [{"functionDeclarations": decls}], "generationConfig": gc,
                       **({"toolConfig": {"functionCallingConfig": {"mode": "NONE"}}} if rnd == MAX_TOOL_ROUNDS else {})},
                      "gemini_thinking", ["generationConfig", "thinkingConfig", "thinking"])
        usage["rounds"] = usage.get("rounds", 0) + 1
        u = r.get("usageMetadata") or {}
        usage["in"] += u.get("promptTokenCount", 0)
        usage["out"] += u.get("candidatesTokenCount", 0)
        cand = (r.get("candidates") or [{}])[0]
        content = cand.get("content") or {"role": "model", "parts": []}
        parts = content.get("parts") or []
        calls = [p["functionCall"] for p in parts if "functionCall" in p]
        if not calls:
            return "".join(p.get("text", "") for p in parts if not p.get("thought")), usage
        contents.append(content)          # returned as-is (keeps any thought signatures)
        resp = []
        for c in calls:
            out = tools.call(c["name"], c.get("args") or {})
            log.append({"tool": c["name"], "args": c.get("args")})
            js = json.dumps(out, default=str)
            res = json.loads(js) if len(js) <= 20000 else {"truncated": js[:20000]}
            resp.append({"functionResponse": {"name": c["name"], "response": {"result": res}}})
        contents.append({"role": "user", "parts": resp})
    raise RuntimeError("too many lookup rounds")


LOCAL_URL = os.getenv("ASK_LOCAL_URL", "http://127.0.0.1:11434")
LOCAL_ROUNDS = 3


def run_local(system: str, history: list[dict], user: str, tools: Lookups, log: list, post=None, model: str | None = None) -> tuple[str, dict]:
    """A model running on this Mac (Ollama). Free and unlimited; used for routine questions. Same lookups as the cloud models."""
    import requests

    model = model or MODELS["local"]["model"]
    msgs = [{"role": "system", "content": system}] + [{"role": m["role"], "content": m["text"]} for m in history] + [{"role": "user", "content": user}]
    defs = [{"type": "function", "function": {"name": n, "description": d, "parameters": s}} for n, d, s in TOOLS]
    usage = {"in": 0, "out": 0, "rounds": 0, "model": model}

    def chat(body):
        if post:
            return post(body)
        r = requests.post(LOCAL_URL + "/api/chat", json=body, timeout=180)
        if r.status_code >= 400:
            raise RuntimeError(f"local model: HTTP {r.status_code} {r.text[:120]}")
        return r.json()

    for rnd in range(LOCAL_ROUNDS + 1):
        last = rnd == LOCAL_ROUNDS
        body = {"model": model, "messages": msgs, "stream": False, "think": False, "keep_alive": "60m",
                "options": {"num_ctx": 24576, "temperature": 0.2}}
        if last:
            body["format"] = "json"
        else:
            body["tools"] = defs
        r = chat(body)
        usage["rounds"] += 1
        usage["in"] += r.get("prompt_eval_count", 0)
        usage["out"] += r.get("eval_count", 0)
        m = r.get("message") or {}
        calls = m.get("tool_calls") or []
        if not calls:
            text = m.get("content") or ""
            if text.strip() or last:
                return text, usage
            msgs.append({"role": "user", "content": "Now write the answer as the JSON object."})
            continue
        msgs.append({"role": "assistant", "content": m.get("content") or "", "tool_calls": calls})
        for c in calls[:6]:
            f = c.get("function") or {}
            args = f.get("arguments") or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except ValueError:
                    args = {}
            out = tools.call(f.get("name", ""), args)
            log.append({"tool": f.get("name"), "args": args})
            js = json.dumps(out, default=str)
            usage["seen"] = (usage.get("seen", "") + js)[:400000]
            msgs.append({"role": "tool", "tool_name": f.get("name"), "content": js[:20000]})
    raise RuntimeError("too many lookup rounds")


_NUM = re.compile(r"(?<![\w.])\$?\d[\d,]*(?:\.\d+)?%?")


def grounded(answer: str, context: str) -> list[str]:
    """Numbers in the answer that appear nowhere in what the model was given (a sign it made them up). Small counts and years are ignored."""
    ctx = re.sub(r"[,$]", "", context)
    nums = set(re.findall(r"-?\d+(?:\.\d+)?", ctx))
    vals = []
    for x in nums:
        try:
            vals.append(float(x))
        except ValueError:
            pass
    missing = []
    for tok in _NUM.findall(answer or ""):
        raw = tok.strip("$%").replace(",", "")
        try:
            v = float(raw)
        except ValueError:
            continue
        if v <= 12 and "." not in raw or 2000 <= v <= 2100 and "." not in raw:
            continue
        if raw in nums:
            continue
        tol = max(abs(v) * 0.006, 0.051)                       # rounding: 76,412.37 -> 76,400 or 76.4k; 2.43% -> 2.4%
        if any(abs(v - c) <= tol or abs(v - abs(c)) <= tol for c in vals):
            continue
        missing.append(tok)
    return missing


PROVIDERS: dict[str, Callable] = {
    "local": run_local,
    "gemini": run_gemini,
    "gemini_deep": lambda *a, **k: run_gemini(*a, thinking="medium", **k),
    "haiku": lambda *a, **k: run_claude(*a, model=MODELS["haiku"]["model"], **k),
    "sonnet": lambda *a, **k: run_claude(*a, model=MODELS["sonnet"]["model"], **k),
    "opus": lambda *a, **k: run_claude(*a, model=MODELS["opus"]["model"], **k),
}
SETTINGS_DEFAULT = {"ask_enabled": "1", "voice_enabled": "1", "daily_budget_usd": "2", "over_budget": "gemini", "eval_budget_usd": "3"}


def parse(text: str) -> dict:
    """The model's JSON reply; lenient (code fences, text around it). Falls back to plain text."""
    t = (text or "").strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    m = re.search(r"\{.*\}", t, re.S)
    if m:
        try:
            d = json.loads(m.group(0))
            if isinstance(d, dict) and d.get("answer"):
                d.setdefault("kind", "answer")
                for k, default in (("breakdown", []), ("evidence", []), ("options", []), ("follow_ups", []), ("stage", ""), ("assumption", "")):
                    d.setdefault(k, default)
                if isinstance(d["breakdown"], str):
                    d["breakdown"] = [d["breakdown"]]
                return d
        except json.JSONDecodeError:
            pass
    a = re.search(r'"answer"\s*:\s*"((?:[^"\\]|\\.)*)"', t)          # cut-off JSON: keep the answer at least
    if a:
        return {"kind": "answer", "stage": "", "answer": json.loads('"' + a.group(1) + '"'), "breakdown": [], "evidence": [],
                "assumption": "", "options": [], "follow_ups": []}
    if not t:
        raise RuntimeError("the model returned an empty answer; please ask again")
    return {"kind": "answer", "stage": "", "answer": t, "breakdown": [], "evidence": [],
            "assumption": "", "options": [], "follow_ups": []}


SCREENS = {"coin", "trade", "markets", "portfolio", "evidence", "cockpit", "mandate", "home"}


def _clean_show(items) -> list[dict]:
    out = []
    for it in (items or [])[:4]:
        if not isinstance(it, dict) or it.get("screen") not in SCREENS:
            continue
        x = {"screen": it["screen"], "label": str(it.get("label") or it["screen"].capitalize())[:40]}
        if it["screen"] == "coin":
            if not str(it.get("coin", "")).isalnum():
                continue
            x["coin"] = str(it["coin"]).upper()[:6]
        if it["screen"] == "trade":
            if not re.fullmatch(r"[A-Za-z0-9_\-]{3,80}", str(it.get("id", ""))):
                continue
            x["id"] = str(it["id"])
        out.append(x)
    return out


EXAMPLES = ["How is the market right now?", "What setups are close on ETH?", "How is the portfolio doing?", "What has Hunter been doing today?", "What did we learn from the repair shop?"]


class Ask:
    def __init__(self, j, providers: dict[str, Callable] | None = None):
        self.j = j
        self.providers = providers or PROVIDERS
        j.db.executescript("""
            CREATE TABLE IF NOT EXISTS ask_messages (id TEXT PRIMARY KEY, thread TEXT, t INTEGER, role TEXT, text TEXT, reply TEXT,
                provider TEXT, model TEXT, ms INTEGER, tokens_in INTEGER, tokens_out INTEGER, tools TEXT, error TEXT, rating INTEGER);
            CREATE TABLE IF NOT EXISTS ask_misunderstood (t INTEGER, thread TEXT, question TEXT, kind TEXT, provider TEXT);
            CREATE TABLE IF NOT EXISTS settings (k TEXT PRIMARY KEY, v TEXT);
        """)
        cols = {r[1] for r in j.db.execute("PRAGMA table_info(ask_messages)")}
        for c, typ in (("cost_usd", "REAL"), ("mode", "TEXT"), ("note", "TEXT"), ("route", "TEXT"), ("timing", "TEXT")):
            if c not in cols:
                j.db.execute(f"ALTER TABLE ask_messages ADD COLUMN {c} {typ}")
        j.db.commit()

    # ---- settings and spend ----
    def setting(self, k: str) -> str:
        row = self.j.db.execute("SELECT v FROM settings WHERE k=?", (k,)).fetchone()
        return row[0] if row else SETTINGS_DEFAULT.get(k, "")

    def settings(self) -> dict:
        return {k: self.setting(k) for k in SETTINGS_DEFAULT}

    def set_setting(self, who: str, k: str, v: str) -> dict:
        if k not in SETTINGS_DEFAULT:
            raise ValueError(f"unknown setting {k}")
        if k in ("daily_budget_usd", "eval_budget_usd"):
            x = float(v)
            if not 0 <= x <= 50:
                raise ValueError("budget must be between $0 and $50 a day")
            v = str(round(x, 2))
        if k in ("ask_enabled", "voice_enabled"):
            v = "1" if str(v).lower() in ("1", "true", "on", "yes") else "0"
        if k == "over_budget" and v not in ("gemini", "stop"):
            raise ValueError("over_budget is gemini or stop")
        self.j.db.execute("INSERT OR REPLACE INTO settings VALUES (?,?)", (k, v))
        self.j.db.commit()
        self.j.audit(who, "settings", f"{k}={v}", "OK")
        return self.settings()

    def _day_start(self) -> int:
        from datetime import datetime
        from zoneinfo import ZoneInfo

        tz = ZoneInfo("America/Toronto")
        return int(datetime.fromtimestamp(self.j.now(), tz).replace(hour=0, minute=0, second=0, microsecond=0).timestamp())

    def spend(self) -> dict:
        from datetime import datetime
        from zoneinfo import ZoneInfo

        tz = ZoneInfo("America/Toronto")
        d0 = self._day_start()
        m0 = int(datetime.fromtimestamp(self.j.now(), tz).replace(day=1, hour=0, minute=0, second=0, microsecond=0).timestamp())
        evals = "SELECT thread FROM ask_messages WHERE role='user' AND mode LIKE 'eval:%'"
        def tot(since, tests=False):
            rows = self.j.db.execute("SELECT provider, COUNT(*), COALESCE(SUM(cost_usd),0) FROM ask_messages WHERE role='assistant' AND error IS NULL AND t >= ? "
                                     f"AND thread {'IN' if tests else 'NOT IN'} ({evals}) GROUP BY 1", (since,)).fetchall()
            out: dict = {}
            for k, n, c in rows:
                lab = MODELS.get(ALIASES.get(k, k), {}).get("label", k)
                o = out.setdefault(lab, {"answers": 0, "usd": 0.0})
                o["answers"] += n
                o["usd"] = round(o["usd"] + c, 4)
            return out
        today, month = tot(d0), tot(m0)
        spent = sum(v["usd"] for v in today.values())
        budget = float(self.setting("daily_budget_usd"))
        t_today, t_month = tot(d0, True), tot(m0, True)            # Test Lab runs have their own budget, never eat the owner's
        t_spent = sum(v["usd"] for v in t_today.values())
        t_budget = float(self.setting("eval_budget_usd"))
        return {"today_usd": round(spent, 4), "month_usd": round(sum(v["usd"] for v in month.values()), 4), "budget_usd": budget,
                "left_usd": round(max(0.0, budget - spent), 4), "today": today, "month": month,
                "tests": {"today_usd": round(t_spent, 4), "month_usd": round(sum(v["usd"] for v in t_month.values()), 4),
                          "budget_usd": t_budget, "left_usd": round(max(0.0, t_budget - t_spent), 4), "today": t_today},
                "settings": self.settings()}

    def _history(self, thread: str) -> list[dict]:
        rows = self.j.db.execute("SELECT role, text, reply FROM ask_messages WHERE thread=? AND error IS NULL ORDER BY t DESC, rowid DESC LIMIT ?",
                                 (thread, HISTORY_TURNS * 2)).fetchall()[::-1]
        out = []
        for role, text, reply in rows:
            if role == "user":
                if out and out[-1]["role"] == "user":
                    out.pop()
                out.append({"role": "user", "text": text})
            else:
                r = json.loads(reply) if reply else {}
                brief = {k: r.get(k) for k in ("kind", "answer", "breakdown", "evidence", "options", "ui", "points") if r.get(k)}
                if out and out[-1]["role"] == "assistant":
                    out.pop()
                out.append({"role": "assistant", "text": json.dumps(brief)[:4000]})
        while out and out[0]["role"] != "user":
            out.pop(0)
        if out and out[-1]["role"] == "user":
            out.pop()
        return out

    def _failed_clarifies(self, thread: str) -> int:
        n = 0
        for (reply,) in self.j.db.execute("SELECT reply FROM ask_messages WHERE thread=? AND role='assistant' AND error IS NULL ORDER BY t DESC, rowid DESC LIMIT 4", (thread,)):
            k = (json.loads(reply or "{}")).get("kind")
            if k == "clarify":
                n += 1
            else:
                break
        return n

    def today_count(self) -> int:
        return self.j.db.execute("SELECT count(*) FROM ask_messages WHERE role='user' AND COALESCE(mode,'') NOT LIKE 'eval:%' AND t >= ?",
                                 (int(self.j.now() - 86400),)).fetchone()[0]

    def _next_level(self) -> str:
        """Above the Mac: Claude Haiku while today's budget lasts, else free Gemini."""
        if "haiku" in self.providers and os.getenv("ANTHROPIC_API_KEY") and self.spend()["left_usd"] > 0.02:
            return "haiku"
        return "gemini"

    def _pick(self, text: str, mode: str | None, provider: str | None) -> tuple[str, str, str]:
        """-> (model key, mode label, note)."""
        if provider:                                            # old clients: provider gemini / claude
            key = ALIASES.get(provider.lower())
            if not key:
                raise ValueError(f"unknown provider {provider}")
            return key, provider.lower(), ""
        mode = (mode or "auto").lower()
        if mode == "worker":                                    # background jobs (briefs): the Mac's model, escalating if unsure
            return ("local", "auto", "Background job on the Mac's model") if local_up() else ("gemini", "everyday", "")
        if mode == "auto":
            key, note = route(text)
            return key, "auto", note
        if mode == "google_auto":                               # Google, Auto on: quick answers fast, investigations with more thinking
            if len(text) > 160 or DEEP_WORDS.search(text):
                return "gemini_deep", "google_auto", "Auto: Gemini with more thinking, this needs investigation"
            return "gemini", "google_auto", "Auto: Gemini, quick question"
        if mode in MODES:
            return MODES[mode], mode, ""
        if mode in MODELS:
            return mode, mode, ""
        raise ValueError(f"unknown mode {mode}")

    def ask(self, who: str, text: str, thread: str | None = None, provider: str | None = None, mode: str | None = None,
            second_of: str | None = None, context: dict | None = None, voice: bool = False, source: str = "") -> dict:
        text = (text or "").strip()[:2000]
        if not text:
            raise ValueError("empty question")
        if self.setting("ask_enabled") != "1":
            raise ValueError("Ask Ananta is switched off in the Cockpit")
        thread = thread or uuid.uuid4().hex[:12]
        quick = self._quick(who, text, thread, voice, source, context)
        if quick:
            return quick
        key, mode_label, note = self._pick(text, mode, provider)
        if voice and mode_label == "auto" and key == "haiku":   # talking: speed matters most; Sonnet answers in ~5 s, Haiku took 10-15 s
            key, note = "sonnet", "Auto: Claude Sonnet for voice (fastest to answer)"
        if source != "eval" and self.today_count() >= DAILY_LIMIT:
            raise ValueError(f"daily question limit reached ({DAILY_LIMIT}); it resets in 24 hours")
        if MODELS[key]["provider"] == "claude" and source == "eval":
            tb = self.spend()["tests"]
            if tb["today_usd"] >= tb["budget_usd"]:
                raise ValueError(f"today's Test Lab budget (${tb['budget_usd']:.2f}) is used up; tests stop here so your own budget is untouched")
        elif MODELS[key]["provider"] == "claude":
            sp = self.spend()
            if sp["today_usd"] >= sp["budget_usd"]:
                if self.setting("over_budget") == "stop":
                    raise ValueError(f"today's Claude budget (${sp['budget_usd']:.2f}) is used up; raise it in the Cockpit or use Everyday")
                key, note = "gemini", f"Claude budget for today (${sp['budget_usd']:.2f}) is used up, so Gemini answered"
        history = self._history(thread)
        tries = self._failed_clarifies(thread)
        now = int(self.j.now())
        uid = uuid.uuid4().hex[:12]
        self.j.db.execute("INSERT INTO ask_messages (id, thread, t, role, text, provider, mode) VALUES (?,?,?,?,?,?,?)",
                          (uid, thread, now, "user", text, key, ("eval:" if source == "eval" else "") + ("voice:" if voice else "") + mode_label))
        self.j.db.commit()
        notes = []
        if tries:
            notes.append(f"[conversation note: clarification has failed {tries} time(s) in a row]")
        if second_of:
            notes.append("[conversation note: the owner asked for a second opinion on this question; answer it independently from the data]")
        if voice:
            notes.append("[voice session: the 'answer' is SPOKEN aloud, so keep it short like talking: at most 3 short sentences and about 40 words "
                         "in total (a greeting counts), the most important thing first. Rounded numbers; no symbols, tables or abbreviations "
                         "(say 'percent', 'dollars', 'Bitcoin'). Details go in 'breakdown' (shown on screen, not spoken). Keep the JSON small so it arrives "
                         "fast: breakdown at most 2 bullets, evidence at most 2 items, follow_ups at most 2. Only move the screen (ui_go) when he asks to see something]")
        prev = self.j.db.execute("SELECT route FROM ask_messages WHERE thread=? AND role='assistant' AND route IS NOT NULL ORDER BY t DESC, rowid DESC LIMIT 1",
                                 (thread,)).fetchone()
        from jarvis.service import briefs as B

        tb = time.time()
        route_name = B.route(text, prev[0] if prev else None)
        brief = {}
        try:
            brief = B.briefs_for(self.j, route_name)
        except Exception as exc:  # noqa: BLE001  the brief is a shortcut, never a blocker
            brief = {"BRIEF_ERROR": str(exc)[:200]}
        brief_ms = int(1000 * (time.time() - tb))
        if not history:
            from datetime import datetime
            from zoneinfo import ZoneInfo

            hr = datetime.fromtimestamp(now, ZoneInfo("America/Toronto")).hour
            part = "morning" if 4 <= hr < 12 else "afternoon" if hr < 17 else "evening"
            notes.append(f"[this is the first message of a new conversation; it is {part} in Toronto: greet Madhav warmly in a few words first]")
        if str(who).startswith("guest:"):
            notes.append("[GUEST: this is a friend of Madhav trying the app in practice mode. Do not call them Madhav; greet them as a guest. "
                         "Explain Madhav's system as 'Madhav's paper trading system'. Everything works for them as it does for Madhav: they can ask for "
                         "paper orders, alerts and mandate changes, and those go to THEIR OWN practice book (separate cash, never Madhav's books). "
                         "Say 'your practice book' for their manual book. The kill switch, autopilot and portfolio approvals are locked in practice mode.]")
        if context:
            here = context.get("here") if isinstance(context, dict) and ("here" in context or "about" in context) else context
            about = context.get("about") if isinstance(context, dict) and "about" in context else None
            if here:
                notes.append("[screen context: the screen open right now is " + json.dumps(here, default=str)[:300] + "]")
            if about:
                notes.append("[the owner pointed at this item (long-press): " + json.dumps(about, default=str)[:400] + "]")
        user_msg = (f"[now: {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime(now))}] [question type: {route_name}]" + ("\n" + "\n".join(notes) if notes else "")
                    + ("\n" + "\n".join(f"{k} (live):\n" + json.dumps(v, default=str, separators=(",", ":")) for k, v in brief.items()) if brief else "")
                    + f"\n\nQUESTION: {text}")
        log: list = []
        t0 = time.time()
        aid = uuid.uuid4().hex[:12]
        from jarvis.service import appmap as _amh
        _ht = _amh.here_target(here if context else None)
        used = key
        from jarvis.service.mandate import Mandate

        system = SYSTEM + "\n\nOWNER'S MANDATE (current)\n" + Mandate(self.j.db, self.j.now).text()
        try:
            can_escalate = key == "local" and mode_label == "auto"      # the router picked the Mac: a weak answer goes one level up
            try:
                L = Lookups(self.j, thread, _ht, str(who).startswith("guest:"))
                raw, usage = self.providers[key](system, history, user_msg, L, log)
                if can_escalate:
                    why = _local_doubt(raw, user_msg + " ".join(m["text"] for m in history) + usage.get("seen", ""))
                    if why:
                        raise RuntimeError("local doubt: " + why)
            except Exception as exc:  # noqa: BLE001
                if can_escalate:
                    used = self._next_level()
                    note = (note + "; " if note else "") + f"The Mac's model wasn't sure ({str(exc)[:60]}), so {MODELS[used]['label']} answered"
                    log.clear()
                    L = Lookups(self.j, thread, _ht, str(who).startswith("guest:"))
                    raw, usage = self.providers[used](system, history, user_msg, L, log)
                # free Gemini busy: escalate once to Claude Haiku if allowed and within budget
                elif key == "gemini" and "haiku" in self.providers and self.spend()["left_usd"] > 0.02 and os.getenv("ANTHROPIC_API_KEY"):
                    used = "haiku"
                    note = (note + "; " if note else "") + "Gemini was busy, so Claude Haiku answered"
                    log.clear()
                    L = Lookups(self.j, thread, _ht, str(who).startswith("guest:"))
                    raw, usage = self.providers["haiku"](system, history, user_msg, L, log)
                else:
                    raise exc
            try:
                reply = parse(raw)
            except RuntimeError:
                if not L.created and MODELS[used]["provider"] == "claude" and "gemini" in self.providers:
                    # Claude occasionally ends with thinking only; answer this one with Gemini instead of failing
                    note = (note + "; " if note else "") + "Claude gave no words this time, so Gemini answered"
                    used = "gemini"
                    log.clear()
                    L = Lookups(self.j, thread, _ht, str(who).startswith("guest:"))
                    raw, usage = self.providers["gemini"](system, history, user_msg, L, log)
                    reply = parse(raw)
                elif not L.created:
                    raise
                else:
                    reply = {"kind": "answer", "stage": "decision", "evidence": [], "assumption": "", "options": [], "follow_ups": [],
                         "answer": "I've prepared this for you; nothing happens until you confirm the card: " + "; ".join(a["summary"] for a in L.created),
                         "breakdown": []}
        except Exception as exc:  # noqa: BLE001
            ms = int(1000 * (time.time() - t0))
            if "budget" in (note or "") and "429" in str(exc):          # say the real reason, not just "busy"
                exc = RuntimeError(f"Today's Claude budget is used up and Gemini's free quota is used up too. Raise the daily budget in "
                                   f"Cockpit → AI, or wait: the budget resets at midnight Toronto time.")
            self.j.db.execute("INSERT INTO ask_messages (id, thread, t, role, provider, mode, ms, tools, error) VALUES (?,?,?,?,?,?,?,?,?)",
                              (aid, thread, now + 1, "assistant", used, mode_label, ms, json.dumps(log), str(exc)[:500]))
            self.j.db.commit()
            return {"id": aid, "thread": thread, "provider": used, "error": str(exc)[:240]}
        model = usage.get("model") or MODELS[used]["model"] or GEMINI_MODEL
        cost = cost_usd(used, usage)
        if reply["kind"] == "clarify" and tries >= 2:
            reply = {**reply, "kind": "not_understood", "options": [],
                     "answer": "Sorry, I still don't understand what you're asking. Here are things I can answer:", "follow_ups": EXAMPLES[:3]}
        if reply["kind"] in ("clarify", "not_understood"):
            self.j.db.execute("INSERT INTO ask_misunderstood VALUES (?,?,?,?,?)", (now, thread, text, reply["kind"], used))
        ms = int(1000 * (time.time() - t0))
        reply["show"] = _clean_show(reply.get("show"))
        reply["actions"] = L.created
        try:
            from jarvis.service import appmap as _am

            _here = context.get("here") if isinstance(context, dict) and "here" in context else (context if isinstance(context, dict) else None)
            reply["ui"], reply["answer"] = _am.keep_honest(self.j, text, reply.get("answer", ""), L.ui, _here)
            n_sent = len([x for x in re.split(r"(?<=[.!?])\s+", reply.get("answer") or "") if x.strip()])
            reply["points"], reply["ui"] = _am.plan_points(self.j, reply.get("points"), reply["ui"], _here, n_sent, text)
            reply["points"] = _am.anchor_points(reply["points"], reply.get("answer") or "")
            reply["evidence"] = _am.clean_evidence(self.j, reply.get("evidence"))
            _label_outside(reply, L.outside)
            if not reply["ui"] and _am.SHOW_INTENT.search(text):           # "show me / where did you get that": open where the proof is
                prev = None
                if history and history[-1]["role"] == "assistant":
                    try:
                        prev = json.loads(history[-1]["text"])
                    except (ValueError, TypeError):
                        prev = None
                u, sp = _am.proof_target(reply["evidence"], prev, _am.here_target(_here))
                if u:
                    v, label = _am.resolve(self.j, u["target"])
                    if v:
                        reply["ui"] = [{**u, "target": v, "label": label}]
                        if sp and not reply["points"]:
                            reply["points"] = [{"spot": sp, "sentence": 0}]
        except Exception:  # noqa: BLE001
            reply["ui"] = L.ui
        timing = {"brief_ms": brief_ms, "model_ms": max(0, ms - brief_ms), "rounds": usage.get("rounds"), "lookups": len(log),
                  "out_tokens": usage.get("out", 0)}
        meta = {"model_label": MODELS[used]["label"], "mode": mode_label, "cost_usd": cost, "note": note, "second_of": second_of,
                "route": route_name, "timing": timing}
        self.j.db.execute("INSERT INTO ask_messages (id, thread, t, role, reply, provider, model, ms, tokens_in, tokens_out, tools, cost_usd, mode, note, route, timing) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                          (aid, thread, now + 1, "assistant", json.dumps({**reply, **meta}), used, model, ms,
                           usage.get("in", 0) + usage.get("cache_read", 0) + usage.get("cache_write", 0), usage.get("out", 0), json.dumps(log), cost, mode_label, note,
                           route_name, json.dumps(timing)))
        self.j.db.commit()
        self.j.audit(who, "ask", text[:200], f"{used} {reply['kind']} {ms}ms ${cost:.4f}")
        if voice:
            reply["speak"] = speak_text(reply)                       # what is said aloud (the full answer stays on screen)
        vid = _pre_voice(context, reply.get("speak") or reply.get("answer"))
        if vid:
            reply["voice_id"] = vid                                  # its audio is already being made: the phone fetches it directly
        return {"id": aid, "thread": thread, "provider": used, "model": model, "ms": ms, "lookups": [x["tool"] for x in log], **reply, **meta}

    def _small_talk(self, text: str, thread: str) -> dict | None:
        """Instant replies that need no model: thanks / okay / stop, and "say that again"."""
        t = (text or "").strip()
        if REPEAT.search(t) and len(t.split()) <= 8:
            row = self.j.db.execute("SELECT reply FROM ask_messages WHERE thread=? AND role='assistant' AND reply IS NOT NULL ORDER BY t DESC, rowid DESC LIMIT 1",
                                    (thread,)).fetchone()
            prev = json.loads(row[0]) if row and row[0] else {}
            said = prev.get("speak") or prev.get("answer")
            return {"ui": [], "say": said or "I haven't said anything yet in this conversation."}
        if THANKS.match(t):
            return {"ui": [], "say": "You're welcome, Madhav."}
        if OKAY.match(t):
            return {"ui": [], "say": "Okay."}
        return None

    def _quick(self, who: str, text: str, thread: str, voice: bool, source: str, context=None) -> dict | None:
        """Plain navigation commands are done instantly, with no model call."""
        from jarvis.service import appmap

        try:
            q = self._small_talk(text, thread) or appmap.quick_command(self.j, text)
        except Exception:  # noqa: BLE001
            q = None
        if not q:
            return None
        now = int(self.j.now())
        uid, aid = uuid.uuid4().hex[:12], uuid.uuid4().hex[:12]
        reply = {"kind": "answer", "stage": "", "answer": q["say"], "breakdown": [], "evidence": [], "assumption": "", "options": [],
                 "follow_ups": [], "show": [], "actions": [], "ui": q["ui"], "tour": q.get("tour"), "model_label": "Instant", "mode": "nav", "cost_usd": 0.0,
                 "note": "", "route": "app", "timing": {"brief_ms": 0, "model_ms": 0, "rounds": 0, "lookups": 0, "out_tokens": 0}}
        self.j.db.execute("INSERT INTO ask_messages (id, thread, t, role, text, provider, mode) VALUES (?,?,?,?,?,?,?)",
                          (uid, thread, now, "user", text, "local", ("eval:" if source == "eval" else "") + ("voice:" if voice else "") + "nav"))
        self.j.db.execute("INSERT INTO ask_messages (id, thread, t, role, reply, provider, model, ms, tokens_in, tokens_out, tools, cost_usd, mode, route) "
                          "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (aid, thread, now + 1, "assistant", json.dumps(reply), "local", "instant", 0, 0, 0, "[]", 0.0, "nav", "app"))
        self.j.db.commit()
        vid = _pre_voice(context, q["say"] if not q.get("tour") else [st["say"] for st in q["tour"]])
        if vid and not q.get("tour"):
            reply["speak"], reply["voice_id"] = q["say"], vid
        return {"id": aid, "thread": thread, "provider": "local", "model": "instant", "ms": 0, "lookups": [], **reply}

    # ---- voice ----
    def transcribe(self, audio_b64: str, mime: str = "audio/wav", post=_post) -> str:
        """Speech to text with Gemini (free tier). Audio is not stored."""
        if self.setting("voice_enabled") != "1":
            raise ValueError("Voice is switched off in the Cockpit")
        if not audio_b64 or len(audio_b64) > 12_000_000:
            raise ValueError("audio missing or too long (about 2 minutes at most)")
        local = _local_stt(audio_b64, mime)
        if local is not None:
            return local
        key = os.getenv("GEMINI_API_KEY", "")
        if not key:
            raise RuntimeError("GEMINI_API_KEY is not set")
        prompt = ("Transcribe this spoken message exactly, in English. It is the owner talking to Ananta, a crypto trading assistant "
                  "(the owner is Madhav; he may say 'hey there', 'hi Jarvis', 'Ananta'; coins: Bitcoin BTC, Ethereum ETH, Solana SOL, ADA, DOGE, AVAX, BCH, LINK, LTC, XRP; "
                  "words: Hunter, Squeeze, Explorer, setup, scan, portfolio, mandate, evidence, repair shop). "
                  "Return only the words spoken. If there is no speech, return an empty string.")
        err = None
        order = ["gemini-3.1-flash-lite"] + [m for m in GEMINI_MODELS if m != "gemini-3.1-flash-lite"]     # fastest first for speech
        for m in order:
            try:
                r = post(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent",
                         {"x-goog-api-key": key, "content-type": "application/json"},
                         {"contents": [{"role": "user", "parts": [{"inlineData": {"mimeType": mime, "data": audio_b64}}, {"text": prompt}]}],
                          "generationConfig": {"temperature": 0.0, "maxOutputTokens": 600}})
                parts = ((r.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
                return "".join(p.get("text", "") for p in parts if not p.get("thought")).strip().strip('"')
            except RuntimeError as exc:
                err = exc
        raise RuntimeError(f"could not transcribe right now ({str(err)[:80]})")

    def voice_turn(self, who: str, audio_b64: str, mime: str, thread: str | None, mode: str | None, context: dict | None, source: str = "") -> dict:
        heard = self.transcribe(audio_b64, mime)
        if not heard:
            return {"heard": "", "thread": thread, "error": "I didn't catch any words. Try again a little closer to the phone."}
        out = self.ask(who, heard, thread=thread, mode=mode, context=context, voice=True, source=source)
        return {"heard": heard, **out}

    def second(self, who: str, msg_id: str) -> dict:
        row = self.j.db.execute("SELECT thread, t, provider FROM ask_messages WHERE id=? AND role='assistant'", (msg_id,)).fetchone()
        if not row:
            raise ValueError("unknown answer")
        thread, t, prov = row
        q = self.j.db.execute("SELECT text FROM ask_messages WHERE thread=? AND role='user' AND t <= ? ORDER BY t DESC, rowid DESC LIMIT 1", (thread, t)).fetchone()
        if not q:
            raise ValueError("question not found")
        other = "sonnet" if MODELS.get(prov, MODELS["gemini"])["provider"] == "gemini" else "gemini"
        return self.ask(who, q[0], thread=thread, mode=other, second_of=msg_id)

    def rate(self, msg_id: str, rating: int) -> None:
        self.j.db.execute("UPDATE ask_messages SET rating=? WHERE id=? AND role='assistant'", (1 if rating > 0 else -1, msg_id))
        self.j.db.commit()

    def threads(self, n: int = 20) -> list[dict]:
        rows = self.j.db.execute("""SELECT thread, MIN(t), MAX(t), COUNT(*) FROM ask_messages WHERE thread NOT IN
                (SELECT thread FROM ask_messages WHERE role='user' AND COALESCE(mode,'') LIKE 'eval:%')
                GROUP BY thread ORDER BY MAX(t) DESC LIMIT ?""", (n,)).fetchall()
        out = []
        for th, t0, t1, cnt in rows:
            first = self.j.db.execute("SELECT text, mode FROM ask_messages WHERE thread=? AND role='user' ORDER BY t LIMIT 1", (th,)).fetchone()
            out.append({"thread": th, "title": (first[0] if first else "")[:80], "time": views._local(t1), "messages": cnt,
                        "voice": bool(first and (first[1] or "").startswith("voice:"))})
        return out

    def thread(self, thread: str) -> list[dict]:
        out = []
        for mid, t, role, text, reply, prov, ms, err, rating, mode in self.j.db.execute(
                "SELECT id, t, role, text, reply, provider, ms, error, rating, mode FROM ask_messages WHERE thread=? ORDER BY t, rowid", (thread,)):
            if role == "user":
                out.append({"id": mid, "role": "user", "text": text, "voice": (mode or "").startswith("voice:")})
            else:
                out.append({"id": mid, "role": "assistant", "provider": prov, "ms": ms, "rating": rating,
                            **({"error": err} if err else json.loads(reply or "{}"))})
        return out

    def export(self, thread: str) -> str:
        """The whole session as plain text, for sharing and analysis: what was asked, what was answered, how fast,
        which model, what was looked up, what the screen did and what was highlighted."""
        rows = self.thread(thread)
        if not rows:
            raise ValueError("unknown session")
        tm = self.j.db.execute("SELECT MIN(t) FROM ask_messages WHERE thread=?", (thread,)).fetchone()[0] or 0
        lines = [f"ANANTA SESSION {thread} · started {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime(tm))} · {sum(r['role'] == 'user' for r in rows)} question(s)", ""]
        for n, r in enumerate(rows):
            if r["role"] == "user":
                lines.append(f"Q{sum(x['role'] == 'user' for x in rows[:n + 1])} MADHAV{' (voice)' if r.get('voice') else ''}: {r.get('text')}")
                continue
            if r.get("error"):
                lines += [f"   ANANTA ERROR: {r['error']}", ""]
                continue
            head = " · ".join(x for x in [r.get("model_label") or r.get("provider") or "", f"{(r.get('ms') or 0) / 1000:.1f}s",
                                          f"${r.get('cost_usd') or 0:.4f}", r.get("route") or "", r.get("kind") or ""] if x)
            lines.append(f"   ANANTA [{head}]: {r.get('answer', '')}")
            if r.get("outside"):
                lines.append(f"   source: {r['outside'].get('source')} — {r['outside'].get('note')}")
            for b in r.get("breakdown") or []:
                lines.append(f"     - {b}")
            for e in r.get("evidence") or []:
                lines.append(f"     evidence: {e.get('label')} = {e.get('value')} ({e.get('source', '')}{' → ' + e['screen'] if e.get('screen') else ''})")
            if r.get("ui"):
                lines.append("     screen: " + " → ".join(u.get("label") or u.get("target") or u.get("do", "") for u in r["ui"]))
            if r.get("points"):
                lines.append("     highlighted: " + ", ".join(f"{p['spot']} @sentence {p['sentence']}" for p in r["points"]))
            if r.get("rating"):
                lines.append(f"     rated: {'good' if r['rating'] > 0 else 'bad'}")
            if r.get("note"):
                lines.append(f"     note: {r['note']}")
            lines.append("")
        return "\n".join(lines)

    def stats(self) -> dict:
        out = {}
        for prov, n, ms, tin, tout, up, down, errs, cost in self.j.db.execute("""
                SELECT provider, COUNT(*), AVG(ms), SUM(tokens_in), SUM(tokens_out), SUM(rating=1), SUM(rating=-1), SUM(error IS NOT NULL), SUM(cost_usd)
                FROM ask_messages WHERE role='assistant' GROUP BY provider"""):
            out[prov] = {"answers": n, "avg_seconds": round((ms or 0) / 1000, 1), "tokens_in": tin, "tokens_out": tout,
                         "thumbs_up": up or 0, "thumbs_down": down or 0, "errors": errs or 0, "usd": round(cost or 0, 4),
                         "usd_per_answer": round((cost or 0) / max(1, n - (errs or 0)), 4)}
        mis = [dict(zip(("t", "thread", "question", "kind", "provider"), r)) for r in
               self.j.db.execute("SELECT * FROM ask_misunderstood ORDER BY t DESC LIMIT 30")]
        return {"providers": out, "misunderstood": mis, "today": self.today_count(), "daily_limit": DAILY_LIMIT, "spend": self.spend()}
