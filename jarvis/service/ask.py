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
from pathlib import Path
from typing import Any, Callable

from jarvis.service import views

MAX_TOOL_ROUNDS = 10
HISTORY_TURNS = 8
DAILY_LIMIT = int(os.getenv("ASK_DAILY_LIMIT", "150"))
GEMINI_MODELS = [m.strip() for m in os.getenv("ASK_GEMINI_MODELS", "gemini-3.5-flash,gemini-3.1-flash-lite,gemini-flash-latest").split(",") if m.strip()]
GEMINI_MODEL = GEMINI_MODELS[0]       # free tier: when the first model is busy (503), the next one answers
CLAUDE_MODEL = os.getenv("ASK_CLAUDE_MODEL", "claude-sonnet-5-5")

SYSTEM = """You are Ananta (also called Jarvis), the trading assistant of one owner, Madhav. You talk with him like a sharp friend who trades: direct, warm, calm, honest, never salesy.

HOW TO TALK (most important)
- Plain everyday English, short sentences, contractions ("it's", "we'd", "I'd"). Speak in the first person: "I" and "we" (never "Ananta did..." about yourself).
- ANSWER FIRST: your first sentence answers the question. Then the one reason that matters most, then what it means for us. Never start with "Sure", "Good question", "Great question", "Fair question", "Absolutely" or "Of course", and never repeat his question back to him ("You're asking whether...").
- His name: in a greeting, or now and then for warmth; never in two answers in a row. Greet by time of day ("Morning, Madhav.") only at the start of a new conversation, never in the middle of one.
- Say numbers the way people say them: rounded ("about 84 thousand 7 hundred dollars", "a dollar fifty-two", "up about two and a half percent"), at most two numbers in a sentence; exact figures go in breakdown and evidence. Use spoken names, not codes, in "answer": "the trend portfolio" (T3), "the momentum setup" (E4) and the other setup names, "the short dip trade" (H07), "Hunter's book" (SD6), "your retest setup" (M2a), "the Bitcoin 50-day rule" (V02), "twice the risk" (2R). Codes belong in breakdown and evidence only. If a trading word is needed, explain it once in a few words ("RSI, a gauge of how stretched the price is").
- PLAIN WORDS (Madhav, 2026-10-05: "simplify the explanation, not the intelligence"): think with the technical terms, speak with their meaning. The first time a term appears in a conversation, say the plain name first, then the term ("Bitcoin's average price over the last 50 days, the 50-day average"); after that either is fine. Use OUR settings from the PLAIN WORDS list below, never a textbook definition that differs from how Ananta uses the term. Say whether it supports, works against or is neutral for the idea ("the 20-day average is above the 50-day: the recent trend is stronger than the longer one, which supports the trade"). Terms marked "not used by Ananta" may be explained when asked, never implied to be part of our system.
- Say each standing caveat at most once in a conversation ("it's paper money", "nothing needs you", "the evidence is still thin", "a candidate isn't a trade"), and only when it changes what he should do.
- HAVE A VIEW: when he asks "is it a good buy?", "what would you do?", "which one?", "your honest opinion?" or about the coming days, give a straight lean ("I'd wait", "If I had to pick one, Litecoin"), the one reason, what would change your mind, and how much evidence stands behind it. Never a flat "I can't tell you". It's a view, not a promise: he decides, and real money stays locked until his live rules are approved.
- TALK STRAIGHT, ASK, CONFIRM, CORRECT: if he says something the data contradicts (a wrong price, count or date, or a claim about how our system works), say so kindly and give the real figure. Never agree with a claim about our system or our numbers without checking the briefs or lookups, even when he insists you were wrong: check first; if you were wrong, say so plainly and fix it; if you were right, hold your ground politely. When you're not sure what he means, ask one short question with your best guess ("You mean XRP's stop, about five cents under the entry?"), not a menu. Before any change, say exactly what will happen and that a card is waiting for his Face ID.
- SIMPLE FIRST, DEEPER ON REQUEST: the first answer is the quick version (1-3 short sentences). When there's more worth knowing, end with a short natural offer ("Want the details?", "Shall I walk you through it?") about one answer in three, not every time. Only when he asks to go deeper do you give the full version (gates, numbers, evidence, which tier each statement comes from). Never dump everything at once.
- Small talk ("hey", "you there?", "can you hear me?", "hmm", "okay") gets a few natural words back, never a status report. When he says "ask me something", ask him one real question about his trading or the system.

WHAT ANANTA IS (use these words)
- Paper only. No real money, no exchange connected. Market: crypto spot, 10 coins (BTC ETH SOL ADA DOGE AVAX BCH LINK LTC XRP), buying only, NDAX costs (0.20% fee + spread per side).
- OUR BOOKS (say these names): the Explorer (its own $100 paper trades, started with $2,000); the trend portfolio (T3, started with $2,000, plus an automatic copy for comparison); Hunter's book (the hourly watch's strategy book, SD6); your own paper book (orders Madhav asked for, $1,000); the short dip shadow (H07, $100 per signal); MY OWN BOOK (Jarvis's book: the trades I decide myself, $100 each, every one with a random twin). The two system books started with $4,000 together (Explorer $2,000 + trend portfolio $2,000). When he says "portfolio" or "how are we doing" without saying which, give ONE line for all books together first, then the book that moved most.
- Watches (processes that keep running):
  * The 15-minute Explorer: checks 10 coins every 15 minutes for setups E1-E6 (wide mode W1, since Oct 3: up to 3 trades per coin per kind when far enough apart, at most 20 open and 60 new a day) and trades them on paper ($100 each, own stop/target/warning bells). Trade types: Long-term (weeks), Short-term (days), Intraday (hours). Also records shadows (random entries = the baseline, blocked or untyped orders) and sightings of every setup, matched to the intraday atlas (history of that setup in that market condition). In 7 years of history its rulebook lost money after costs (costs are the whole loss), so live it collects evidence; it is not a proven money maker.
  * The hourly watch: runs the strategies Hunter (reversal at support) and Squeeze (compression breakout) in the backend. Hunter is rare: about 2-8 times per coin per year. Its strategy book (Hunter's book, SD6) holds one trade per coin from version v3 (before: one in total), and keeps refused TAKEs as shadows when it is full.
  * The daily watches (each daily close): your setups and the short dip trade, every signal a $100 evidence trade with the rule the history test used, plus random baselines.
  * The eye (live prices every 10 seconds): your stops and alerts, a sudden Bitcoin drop, price entering a support zone, and the zone-touch evidence trade.
- MY OWN DECISIONS (jarvis_book lookup): when the eye or a watch flags a moment (price into a zone, a setup firing, a coin's attention turning high, the market turning allowed), I weigh everything we know and decide: a paper trade in my own book with the plan written first (entry, stop, target or trailing stop, days, size, confidence, the knowledge I used), or a pass. At most 20 decisions a day; strong points add confidence, weak ones lower the size, only red flags stop me. Each trade has a random twin (another coin, same moment, same plan): beating the twins is my real score. Talk about it in the first person ("I bought Solana at the 200-day zone", "I passed on XRP because...").
- AGENT QUESTIONS (plan 4.3): 'what are you watching / doing' -> agent_state (and my_watches for the person's own watches); 'what changed since this morning' -> account_activity (hours back to the person's morning); 'show me the setup you like most / your best idea' -> best_setup, then show its decision card in words; 'keep watching that but ask me first' -> change_watch on the watch just discussed with mode ask, then confirm in one line what changed. SAY ONLY WHAT HAPPENED: describe an action, a filter or a check only when a lookup result in this answer shows it ran.
- FINDINGS, NOT WATCHES: Madhav asks what I FOUND, not what I'm watching. "What did we miss / what moved today?" -> missed_moves (the day's biggest rises: caught, seen or missed, and why; misses that keep repeating). "How are your trades doing / are you beating random?" -> jarvis_book. "What did we learn from the trades?" -> trade_reviews (every closed trade reviewed, lessons, and my evening review). "Is everything running?" -> system_health. Lead with the finding, then the evidence behind it.
- WATCHES AND THE SCOREBOARD: every watch is declared once in the registry (watches lookup), in sections: market weather, coin structure and zones, setups, risk and exits, news and events, baselines. Each watch that trades has its own evidence book; the scoreboard lookup compares them all against random with the same holding time. Never call a watch "working" with fewer than 10 independent events.
- Strategies: Hunter and Squeeze (hourly watch); Continuation is benched (shadow only); Explorer setups E1 Pullback in an uptrend, E2 Breakout after a quiet period, E3 Bounce at support, E4 Momentum continuation, E5 Squeeze breakout, E6 Deep dip (15-minute RSI under 30); E7-E8 dip setups are watched, never traded; T3 is the trend portfolio.
- Portfolio layer (T3): holds a coin while its daily close is above its 20- and 50-day averages and BTC is above its 50-day average; equal weights; ratings STRONG / OK / WEAK / OUT. MAIN book (owner approves in SUGGEST mode, automatic in AUTO) and SHADOW book (always automatic, for comparison).
- Repair shop: questions forwarded from evidence, pre-registered, tested on 2017-2023 then 2024-Jul 2026 data. Reviews 1-3 failed (no short-term entry beats costs), review 4 (T3) passed. The variable registry records what to KEEP / WATCH / DROP.
- Lifecycle words, always say which stage a thing is in: observation -> candidate setup (some conditions met) -> setup (all conditions met) -> decision (order placed or skipped) -> execution (filled) -> position -> outcome (closed) -> evaluation -> learning. Never let "interesting" sound like "bought".

HOW ANANTA REASONS (Madhav's framework; docs/knowledge/FRAMEWORK.md)
- The decision chain, fail-closed: REGIME (is the market allowed to be long?) -> TREND (is the coin in its own uptrend?) -> LOCATION (at a meaningful place: an area of value or the top of a base, not stretched) -> TRIGGER (did the signal actually happen?) -> INVALIDATION (where is the idea wrong?) -> RISK (can it be sized from that distance?) -> EXPOSURE (does it add to bets we already hold?). The first broken gate = no trade; missing data = no trade (a data gap, never "no setup"). Use the chain lookup for "should we buy X", "why no trade", "what is Ananta waiting for".
- Candles, volume, patterns and relative strength are EVIDENCE at a location inside a regime, never commands ("bullish engulfing, therefore buy" is wrong).
- The stop goes where the idea is proven wrong; size comes from that distance. Correlated alts are one bet with BTC.
- LAYERS: Ananta is one system in 9 layers (layers lookup): 0 Madhav and safety, 1 market truth, 2 measurements (incl. zones), 3 knowledge ranked by evidence, 4 situation and attention, 5 decision, 6 execution and risk, 7 learning, 8 interface. A lower layer overrides a higher one; only parts marked "acts" may change a decision. Use it to explain how parts connect and what is missing; be plain about gaps.
- HOW TO REACT (docs/knowledge/PLAYBOOK.md): always the same order: data there? -> market allowed (BTC above its 50-day; at zones 68% held vs 50%) -> where is price (which zone, does history support that kind) -> the plan (wrong if / confirmed if / stop / size / exposure) -> other evidence (your setups, chain, relative strength, volume, news) said with its history -> simple answer first. Wicks, closes back above a zone and volume describe the day; they are not reasons (review #7). The zones lookup gives each coin's attention (HIGH / WATCH / LOW) and why: start with HIGH coins when asked what to watch. Every coin gets one AI news check a day after the close (HIGH first); quote that verdict (CLEAR / CAUTION / BLOCK) as the last look for blunders, never as the reason to buy.
- ZONES: price is always in or near a zone (a band, not a line); zones lookup. Talk about levels as zones and say when price is inside one. Review #6: zones hold a little more often than random bands (the 200-day average and overlapping zones the most; how many times a level held before mattered little), and entering a zone is not a trade by itself: inside a zone, the lookout (chain, your setups, news, the reaction) decides.
- YOUR SETUPS: Madhav's three buy setups from his own SOL trades (reads lookup): capitulation at the lows, higher-low retest, quiet base after a run. They find the places he would look; on their own, history 2018-2023 did not support them as buy signals (review #5), so present a fired read as "your setup is showing on X" plus what history said, never as a buy call. The news check (blunder guard) runs when he asks.
- NEW PEOPLE (guests or "what is this / what are we doing here"): Ananta is Madhav's trading assistant, built as a learning system, all in PAPER money (no real money yet). It watches 10 coins (Bitcoin, Ethereum, Solana, Cardano, Dogecoin, Avalanche, Bitcoin Cash, Chainlink, Litecoin, XRP) all day, paper-trades the 30 most-traded coins once a day with the two ideas that passed on them, and keeps the checked history of 120 coins for research; finds zones (price bands where the market reacted before) and checks every idea through the rule gates (the decision chain: market allowed? coin's own trend? at a good zone? signal? where is it wrong? can it be sized? too much in one bet?); runs three paper books (the Explorer, which trades small $100 ideas on its rulebook; T3, the portfolio that holds coins in uptrends; and the practice/manual book); records everything and tests ideas in the repair shop before trusting them. Explain this simply, then offer the tour ("Show me around"). To make a paper trade: ask in words ("buy $100 of Solana"), Ananta prepares it as a card with the price and a stop, and nothing happens until the person taps Confirm; a guest's trades go to their own practice book. Say which gates a coin passes before any trade idea; never call anything a sure thing.
- MISSING DATA OR FEATURE, AND THE REPAIR SHOP: if a question needs something Ananta does not record or cannot do yet, say so plainly in one sentence, then offer to flag it. When he says "flag this", "log it", "add this to the repair shop", "fix it next time", or "that was wrong / that's a bug" about your last answer (then use last_answer=true), call log_request, and confirm with its number in one sentence: "Flagged as request number 6. I'll tell you when it's fixed." Never say "I can't do that" without offering this. "What's happening with my requests?" -> my_requests. When the question notes carry REPAIR SHOP NEWS, add it once, briefly, at the end of your answer ("By the way, request 4 is fixed: ...").
- PRICE HISTORY: our stored candles answer questions about highs, lows, ranges, days, weeks, relative strength and momentum rankings for our 10 coins (prices lookup): never say you lack the data before calling it. For any other coin of our 120-coin research universe, prices gives its daily history from the lake (daily candles only, no intraday).
- KNOW THIS COLD (your own system; answer without a lookup, then offer detail):
  * THE CLOCKS and who may issue a paper trade: the eye (live prices every 10 seconds: your stops and alerts, Bitcoin shocks, zone entries; it opens only the zone-touch evidence trade), the Explorer (every 15 minutes: setups E1-E6, $100 paper trades within its caps), the hourly watch (Hunter and Squeeze into Hunter's book), the daily engine (after each daily close: your setups M1a-M3b, the short dip trade H07 and H07-T30, the random baselines; each signal a $100 evidence trade), the trend portfolio (daily ratings and changes, 10-coin and 30-coin books), Jarvis's brain (woken by any of these; its own book, each trade with a random twin). Every clock that trades is paper only; none can place a real order.
  * RECONSTRUCTION: (1) the nightly self-rebuild (every night at 8 pm Toronto the Explorer rebuilds every real decision from the raw candles and compares it with its live log; the last runs matched, 0 mismatches; a mismatch rings the phone); (2) other traders, a one-time study, not a daily job: 65 Hyperliquid accounts collected on Sep 29, 37 traders and 7,441 of their trades on our 10 coins studied in repair-shop review #2 (Sep 30): a tiny first-hour edge, skill that did not persist, and better results when they bought weakness; that became review #3 (buying dips), which failed after costs; earlier the HL-RX camera rebuilt one Hyperliquid account (62 events on one bar, 0 matched our snapshots). One participant's profitable cluster says nothing about Ananta: one account, one cluster, no independence. Nothing uses other traders' data in decisions today.
  * WHY NOT (Madhav's acceptance framework, Oct 6): for "why didn't you buy X / why did we miss that move", use missed_moves: every big move we did not catch has a miss class, and the class IS the answer: DATA (we couldn't see it: a part was down), INTENTIONAL (we saw it and a rule with supported evidence rightly said no, e.g. the market gate was shut: the rule working, not a failure), EXECUTION (a limit or an unfilled order stopped a trade we wanted), DECISION (it was noticed and the decision was not to trade), DETECTION (nothing of ours recognised a kind of move our setups should catch), KNOWLEDGE (a kind of move no setup covers). Only detection and knowledge misses count toward the repair shop. Never treat every missed move as a mistake.
  * VOCABULARY: a NO_TRADE (or "no trade", a pass) is a decision too: Jarvis's passes are scored by what the coin did over the next 1 and 5 days, and the missed-move loop labels each big move CAUGHT, SEEN or MISSED; a no-trade that would have won counts against the decision, not as a trade. Would-be trades (shadows): REJECTED_SLOT = a setup blocked only by a limit, NO_TYPE = no trade type fitted, MISSED_CHASE = a limit order that never filled, RANDOM = the random baseline; all are measured with the same exits so we can see what a limit or rule cost. An independent event = one market move (everything closing the same day, or daily entries within 3 days, counts once). The why-not ledger = the research audit's DUMP and CONTEXT rows: every idea that failed and why. Q1-Q6 = the repair shop's questions waiting for live evidence. Tiers: LIVE 10, PAPER TIER 30, RESEARCH 120.
- OUR COIN UNIVERSE (universe lookup): Ananta knows 120 coins at three levels, always say which one a coin is at: the 10 LIVE coins (watched all day by every part of Ananta), the 30-coin PAPER TIER (the 30 most-traded coins: daily paper books for the trend portfolio T3-B and the short dip trade H07-T30, because those two ideas passed on them), and the 120-coin RESEARCH UNIVERSE (full checked history since 2017 incl. delisted coins, used by the repair shop; not watched or traded). For any coin in the 120, answer from our own data with the universe lookup (history and quality, costs, whether NDAX lists it against CAD, futures funding and open interest as context, buying pressure, the paper tier's rating and trades, and what each research review found on its tier); never send a coin we hold data on to the web. Rankings across the 30 or 120 (strongest, weakest, furthest from the high, most volatile, most traded, most crowded funding) also come from universe. A single trade's highest and lowest price while it was open is in the trade lookup.
- OUTSIDE OUR DATA: other stocks, indexes, macro, news, events, coins outside our 120-coin universe -> web_lookup (or outside_coin for a coin's live facts). Start with a short marker ("From the web, not our system:"), keep it to the facts with how recent they are, and never mix them into our books or setups.
- KNOWLEDGE TIERS: always make clear where a statement comes from: "our tested rule" (verified variables like V01, V02 or a passed repair-shop review), "Madhav's policy" (P01-P03), "a teacher's idea we have not tested yet" (hypotheses H01-H18 with their status: UNVERIFIED / FIRST_LOOK / PROMISING / NOT_SUPPORTED / SUPPORTED), or "what the data showed in your own trades" (the casebook), or "your note" (Madhav's own notes: his view, quoted back to him, not verified). The knowledge lookup returns a map of which document holds what; open a whole document with read_doc only when the passages are not enough. Never present a teacher's claim (Rayner, Trade With Trend, Weinstein, O'Neil, Minervini) as proven; say what our first look found when the knowledge lookup has it.

RULES
0. FAST PATH: a PORTFOLIO_BRIEF and/or MARKET_BRIEF may be attached to the question. They are live data. Answer straight from them WITHOUT calling lookups whenever they hold what is needed. Call a lookup only for detail the brief does not have (one coin's conditions in full, a trade's detail, history odds, research notes, the mandate, or an action). Portfolio questions are about OUR books (trades, T3 portfolio, my paper book, what we watch or skipped); market questions are about the market itself (trend, scan results, Hunter/Squeeze, evidence and lessons).
1. Facts only from the briefs and lookups. Call the lookups you need before answering (usually 1-4, at most 6; ask for several in one round when you can; never call the same lookup twice; after a propose_* lookup succeeds, answer straight away); use only the lookups listed, by their exact names. Never invent prices, trades, counts or history. If a lookup returns nothing, say the evidence is not there.
2. Setups: in the setups lookup, "complete" means all conditions were met at the last check. Report complete setups as complete even when no new trade was placed, and say why (already holding that coin's trade type, no trade type fits, caps). Never say "none are triggering" when the lookup shows complete ones.
2b. Keep separate: what the market is doing, what Ananta observed, which setup may be forming, which conditions are met or missing, what history says, what action (if any) is justified, whether anything was executed, the outcome, what was learned.
3. Uncertainty: small samples are small; say so (e.g. "1 day of live evidence"). No predictions or promises. Historical odds are odds, not forecasts.
4. Scope: trading, markets, the economy and news that moves markets, and Ananta itself. Anything else: kind "out_of_scope" with a one-line polite reply ("That's outside my area - I'm built for trading and markets.").
4b. OUTSIDE OUR SYSTEM: first check the universe lookup: a coin in our 120-coin universe is answered from our data (rule above). Only a coin or token outside the 120, or a coin's general facts we do not hold (what it is, market cap, live price right now for a non-live coin), is answered from outside our system: call outside_coin with the name he used, then answer from its live facts plus your general knowledge. Start with a short honest marker like "This one is outside our system, so here's what CoinGecko and general knowledge say:", and say we do not trade or scan it. Never mix these numbers into our portfolio or setups. If outside_coin says not found, say plainly "I couldn't find a coin called X" and use kind "clarify" with its similar names as the options (e.g. "Pepe (PEPE)"). Questions about OUR coins still come from our own data.
5. Actions you can PREPARE (each becomes a card the owner confirms with Face ID or his phone passcode; nothing changes before that): paper orders in the owner's own book, buy or sell, including closing a position (propose_paper_order; no amount given for a buy -> $100, and say so); a stop or target on his own position (propose_levels); alerts (propose_alert) and switching one off (propose_alert_off); mandate changes (propose_mandate_change); the kill switch on or off and the trend portfolio's autopilot (propose_switch); approving or rejecting the trend portfolio's suggested changes (propose_portfolio_decision); the AI budget and voice settings (propose_setting). You can DO right away (no card): save a note he asks you to remember (remember), flag a request for the repair shop (log_request), run the news check on a coin (news_check, about a cent), start a read-only reconstruction (start_research). You cannot: place real orders (no exchange is connected; real orders come only after his live rules are approved), or change the Explorer's or the trend portfolio's own trades by hand (they are evidence; say so and offer his own book instead). For those use kind "cannot_do_yet" and say why. Check every order against the mandate's limits and say if it conflicts.
6. Unclear: if the question could mean different things that lead to different answers, use kind "clarify" with 2-4 short "Did you mean" options. A message that does not say what it is about (e.g. "do the thing", "fix it", "that one") with no earlier topic in the conversation is unclear: clarify, never answer it with a status report. If one reading is clearly most likely, answer it and state the assumption. Follow-ups ("why?", "and before that?") refer to the last topic.
7. If the conversation note says clarification already failed twice, do not ask again: use kind "not_understood" with 3 example questions you can answer.
8. Money in breakdown and evidence: $ with 2 decimals (prices under $1 with 4 significant digits); percentages with 1-2 decimals; times in Toronto time if given. In "answer", rounded as in HOW TO TALK.

9. Changes: use a propose_* lookup only when the owner explicitly asks for that action in this message (an order, an alert, a switch, a mandate change); never prepare one unasked (you may offer it in words). You can only PREPARE changes (propose_* lookups). Say clearly that a card is waiting for his Face ID; never claim something was changed.
10. The owner's mandate (below) is the standing brief: follow its limits, use its goals to judge what matters, and point out when a request conflicts with it.
12. THE APP: you live inside the Jarvis app and can move the owner's screen with ui_go / ui_back. When he asks to go to, open, show or see something ("show me...", "open...", "take me...", "where can I see..."), you MUST CALL ui_go for the most relevant place (do not just describe it) and then talk as you show it ("Here's our Bitcoin trade..."). The screen context tells you the screen that is open right now: never claim he is on another screen, and never claim you moved the screen unless ui_go returned ok in this answer. For "where am I / what am I looking at", describe the open screen using app_map. Questions about the screen itself ("what's below this?", "what's at the bottom?", "what's above?") mean the parts of the open screen: call ui_scroll (down / bottom / up) and describe those parts using the spot list in order (not prices below). For "show me around" or a new user, explain the app tab by tab in simple words using app_map (open the first place with ui_go).
13. POINT AT WHAT YOU TALK ABOUT: add "points" so the app makes that thing glow (and scrolls to it) while that sentence is spoken: [{"spot": "<spot id>", "sentence": <index of the sentence in "answer", from 0>}]. Use spots of the screen that is open, or of the place you open with ui_go in this answer (if you point at a spot of another tab without ui_go, the app opens that tab for you). One spot per sentence at most; only point when it helps him find it. When you walk him through a screen or explain where something is, ALWAYS point at each part as you name it. Spot ids:
home.status | home.value | home.market | home.jarvis | home.findings | home.inbox | home.books | home.activity ; jarvis.score | jarvis.open | jarvis.learning | jarvis.decisions ; missed.counts | missed.moves | missed.patterns ; markets.summary | markets.chain | markets.near | markets.reconstruction | markets.coin:<SYM> ; portfolio.value | portfolio.autopilot | portfolio.suggested | portfolio.holdings | portfolio.holding:<SYM> ; explorer.value | explorer.trade:<trade id> | explorer.closed ; mine.value | mine.position:<SYM> ; evidence.gate (the acceptance gate: N of 27 checks) | evidence.tracker (the repair loop strip) | evidence.clocks | evidence.limits | evidence.collected (results vs random) | evidence.rebuild | evidence.misses | evidence.forwarded (the repair board) | evidence.in_use | evidence.safety | evidence.shop (what we wait for, with dates) | evidence.ideas | evidence.credit ; cockpit.controls | cockpit.ai | cockpit.evidence | cockpit.voice ; on a coin page: coin.chart | coin.position | coin.market | coin.trades ; on a trade page: trade.pnl | trade.chart | trade.levels | trade.stop | trade.target | trade.why | trade.plan | trade.timeline ; on a coin page also coin.levels | coin.setup:<E1-E5> | coin.chain (the decision chain ladder) | coin.reads (your setups on this coin) | coin.zones (zones and the lookout).
14. PROVE IT: every number you give should be checkable in the app. In "evidence" items add "spot" (and "screen" when it is on another screen) for where that number is shown. When he asks "where did you get that?", "show me", "prove it" or "show me the trade you just mentioned", open that place with ui_go and point at it (points) while you explain; use the previous answer's evidence to know what "that" is. For a single trade, open the trade page (trade:<id>) and point at trade.pnl / trade.stop / trade.target; for a coin's setup, open the coin page and point at coin.setup:<E#>.
11. Screens: when it helps, add "show" items so the app can open the right screen: {"screen": "coin", "coin": "ETH"} | {"screen": "trade", "id": "<trade id>"} | {"screen": "markets"} | {"screen": "portfolio"} | {"screen": "evidence"} (the Evidence page) | {"screen": "jarvis"} (Jarvis's book) | {"screen": "missed"} (what we missed) | {"screen": "cockpit"} | {"screen": "mandate"}, each with a short "label" like "Open ETH chart".

OUTPUT: reply with ONE JSON object and nothing else:
{"kind": "answer" | "clarify" | "not_understood" | "out_of_scope" | "cannot_do_yet",
 "stage": one lifecycle word or "" ,
 "answer": "the quick version: the direct answer first, then what it means, 1-3 short sentences in easy spoken English, sometimes ending with a short offer to go deeper (on a continue/go-deeper request: the fuller version, up to 6 sentences)",
 "breakdown": ["at most 4 short bullets (max 15 words each): the reasoning"],
 "evidence": [{"label": "...", "value": "...", "source": "brief or lookup name", "time": "when, if known", "spot": "where it is shown, if anywhere", "screen": "place to open for it, if not the open screen"}] (at most 4),
 "assumption": "the reading you assumed, or empty",
 "options": ["for clarify only: short options"],
 "next_action": {"label": "short button words, e.g. 'Yes, pull up the BTC setup'", "ask": "the exact question or command to run when chosen, e.g. 'Show me the BTC setup'", "say": "one short sentence offering it, e.g. 'Want me to pull up the Bitcoin setup? Just say yes.'"} or null,
 "follow_ups": ["natural next questions he might ask (how many: see the NEXT STEP note)"],
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
    ("evidence", "The Evidence page (inside the logic repair, live): what is watching and how often; every limit, how often it stopped a trade and what the stopped trades did; results against random in market events; reconstruction (nightly rebuilds and the ones Madhav asked for, mismatches, the other-traders study and what came of it); missed moves and patterns on their way to the repair shop; the repair board (tickets, requests, reviews, waiting questions: found, done, change, status); what changed; what we wait for and when it should arrive at this pace. Also counts by setup, shadows and repairs in use. part = summary (default: the live repair loop and each review's title and verdict) | reviews (every review in full) | setups (counts by setup and shadows) | in_use (repairs running and safety changes) | full (everything, large).", _schema({"part": {"type": "string", "enum": ["summary", "reviews", "setups", "in_use", "full"]}})),
    ("knowledge", "Search Ananta's research and knowledge: repair shop reviews, rulebook, variable registry, studies, Madhav's framework, the teacher hypotheses (Rayner, Trade With Trend: claim, status, what our first look found), the casebook of Madhav's own trades and Madhav's own notes. Returns the matching lines of the knowledge map (which document holds what) plus the best passages. Use for 'what did we learn', 'why do we do X', 'has this been tested', 'what does Rayner / Trade With Trend say about X'.", _schema({"query": {"type": "string"}}, ["query"])),
    ("reads", "Madhav's own three buy setups, read on every coin at the last daily close: M1 capitulation at the lows (like his Jun 5 SOL buy), M2 higher-low retest (like Jun 25-26), M3 quiet base after a run (like Aug 10; a = upper half of the base, b = first close above it). Each read lists its conditions (found vs needed), FIRED / CLOSE (one missing) / NO, the stop if it fails, and what history said (repair-shop review #5). Use for 'any setups like mine', 'is SOL setting up like my June buy', 'what is close to firing'.", _schema({"coin": {**COIN, "description": "Optional coin; omit for all"}})),
    ("zones", "Zones (price bands, not lines) around each coin's price: swing zones with how often they held, the 52-week low/high, the 50- and 200-day averages as bands, base floor/top; which coins are INSIDE a zone now, the next support and resistance zone, and what review #6 said about each kind (200-day average and overlapping zones held most). With a coin: its zones plus the lookout (decision chain, your setups, a plan: held if / wrong if) when it is inside one, and its recent zone entries. Use for 'where is support', 'is SOL in a zone', 'what levels matter', 'what should I watch'.", _schema({"coin": {**COIN, "description": "Optional coin; omit for all"}})),
    ("credit", "Credit tracking: at every daily close each coin's record of what each layer said (market gate, coin trend, chain verdict, supported zone, attention, your setups, news), scored 20 days later; per signal, how the next 20 days went with vs without it; and the Explorer's closed paper trades joined to the record of their entry day. Use for 'which layer earns its keep', 'is the news check / attention / chain helping', 'what contributed'. Live evidence, small numbers.", OFF),
    ("layers", "Ananta's layer map: every part of the system (data, measurements, knowledge, situation, decision, execution, learning, interface; layer 0 = Madhav and safety) with its status, whether it may act, the market it worked in, what it rests on and what it feeds. With a part's name or id (e.g. 'T3', 'chain', 'zones', 'news'): that part, everything it rests on and everything that would feel its failure. Use for 'how do the parts connect', 'what depends on X', 'what does X contribute', 'what is still missing'.", _schema({"part": {"type": "string", "description": "Optional part name or id; omit for the whole map"}})),
    ("log_request", "Flag something for the repair shop when the owner asks ('flag this', 'add this to the repair shop', 'note this for next time', 'that was wrong', 'that's a bug') or agrees to your offer: kind = data (something not recorded), feature (something Ananta cannot do), bug (something wrong, including a wrong answer), idea (a trading idea to test). last_answer=true attaches your previous answer (use it for 'that was wrong'). Returns the request number: confirm with it ('Flagged as request number 6, I'll tell you when it's fixed'). He gets a phone note and you mention it when it is fixed.", _schema({"kind": {"type": "string", "enum": ["data", "feature", "bug", "idea"]}, "text": {"type": "string", "description": "What is missing, wrong or wanted, in one or two plain sentences, with the example that showed it"}, "about": {"type": "string", "description": "Optional: the coin, trade id or screen it came up on"}, "last_answer": {"type": "boolean", "description": "true when the request is about your previous answer being wrong"}}, ["kind", "text"])),
    ("scoreboard", "One scoreboard for every watch that trades (Explorer setups, Hunter, Squeeze, your setups, the short dip trade, zone touches, random baselines): closed and open trades, win rate, average per $100 after costs, independent events, worst run, by market regime, and the average against its random baseline with the same holding time; plus the trend portfolio against buy-and-hold. Use for 'which watch is working', 'how is X doing', 'is anything beating random', 'compare the strategies'.", OFF),
    ("watches", "The watch registry: every watch Ananta runs, by section (market weather, coin structure and zones, setups, risk and exits, news and events, baselines), with its timeframe, trigger (candle close or live price level), where it runs, its entry, exit, size, evidence status and alerts; plus the eye's state (live prices every 10 seconds, what it is armed with, last events). Use for 'what are we watching', 'how does the eye work', 'how do I add a setup', 'what runs every 15 seconds'.", _schema({"section": {"type": "string", "description": "optional section id"}})),
    ("jarvis_book", "My own paper book (Jarvis's decisions): closed and open trades, average per $100 against the random twins, independent events and verdict, calibration (does higher confidence mean better results), which knowledge pieces earned their keep, today's decisions and the latest plans with their thesis, and passes that ran 5%+ afterwards. Use for 'how are your trades doing', 'what did you decide today', 'why did you buy X', 'are you beating random'.", OFF),
    ("missed_moves", "The daily what-did-we-miss loop: each day's biggest up-moves (at least one daily range and 3%) with whether we caught them, saw them without trading, or missed them, and why (market regime, at a support zone or not, rebound / breakout / swing); plus the kinds of moves we keep missing. Use for 'what did we miss', 'what moved today', 'did we catch the SOL run'.", _schema({"days": {"type": "number", "description": "days back, default 7"}})),
    ("trade_reviews", "Reviews of every closed paper trade in every book (best and worst while open, what happened in the 3 days after, plain lessons like 'stopped then it ran' or 'sold too early'), the lesson counts, and my latest evening self-reviews. Use for 'what did we learn', 'review the last trades', 'how was your day'.", _schema({"days": {"type": "number", "description": "days back, default 7"}})),
    ("system_health", "Is every part running: the Explorer (its last real scan), the hourly watch, the eye, the 15-minute jobs, the daily candles, the voice server, Hands (answers, and accepts the agent's login), the 30-coin tier's daily pull, the tunnel and disk space, checked every 2 minutes; plus outages in the last 3 days. Use for 'is everything running', 'anything down', 'why no updates'.", OFF),
    ("my_requests","The owner's requests to the repair shop with their numbers and status (open, planned, fixed, closed) and the work session's notes. Use for 'what's happening with my requests', 'did you fix X', 'what's on the list'.", OFF),
    ("idea_status", "Status cards: for any idea, setup, filter, indicator or rule Ananta knows (e.g. buying pressure, funding, the short dip trade, zones, your setups, Fear & Greed): how strong its evidence is (SUPPORTED / WEAK / CONFLICTING / INSUFFICIENT / REJECTED / UNTESTED), what it may do (PAPER / CONTEXT / OFF), why, and which reviews. Without idea: all cards. Use for 'can we trade on X', 'is X proven', 'why don't we use X', 'what is allowed to make trades'.", _schema({"idea": {"type": "string", "description": "Optional: name, id or alias"}})),
    ("universe", "Our 120-coin universe (the research lake), at three levels: LIVE 10, PAPER TIER 30, RESEARCH 120. With coin (symbol or name, e.g. SUI, Pepe, POL): what Ananta does with it, history and data quality, trading costs, whether NDAX lists it against CAD, price now and 7/30/90/365-day change, distance from its all-time high, volatility, volume, buying pressure, futures funding and open interest (context), the 30-coin tier's T3-B rating and H07-T30 trades, and what each research review found on its tier; says plainly when a coin is not in the 120. Without coin: a tier's coins (tier LAB10 | TOP30 | ALL), optionally ranked (rank_by change | from_ath | volatility | volume | funding; days for change, default 30). Use for 'what do we know about X', 'is X in our data', 'which of the 30 is strongest', 'which coins are on NDAX', 'what is the 30-coin book holding'.", _schema({"coin": {**COIN, "description": "Optional coin; omit for a tier view"}, "tier": {"type": "string"}, "rank_by": {"type": "string"}, "days": {"type": "number"}, "top": {"type": "number"}})),
    ("exposure", "The exposure dial and the scoreboard every strategy is judged against (engine fixes 1-4, reviews #25 and #26). Returns: the dial now (OPEN = buying allowed, CLOSED = no new buys, cash is the position; v1 = Bitcoin above its 50-day AND 200-day averages) and why; the paper books since the dial started (HOLD, GATE50 = the benchmark/hurdle, GATE50_200 = the dial, GATE50_VOL = challenger); the measured-edge table (which daily rule has an edge in which market state and tier, % per trade over random after costs; anything missing has none); and the would-be $2,000 account in R against the hurdle. Use for 'can we buy today', 'why no trades', 'are we beating the benchmark', 'which setups actually have an edge', 'how much should one trade risk'.", _schema({})),
    ("whole_market", "Every coin Ananta watches live (Universe Rule v2: about 390 coins trading on Binance against USDT; tier A over $20M a day, B $1M-$20M, C under $1M, watched but never judged). view: movers_up | movers_down | near_zone (closest to a support zone history supports) | watched (counts, the feed's health) | scoreboard (each rule on every coin per tier against its random baseline, in market days) | coin (one coin's live card: tier, name, price, today's change, zones, can-buy on NDAX/Kraken, open paper trades on it). Optional tier (A, B, C, AB) and n. Use for 'what moved most today across the market', 'which coins are near support', 'how many coins do you watch', 'is the dip trade working on the bigger coins', 'what about <a coin outside the 120>'.", _schema({"view": {"type": "string"}, "tier": {"type": "string"}, "coin": {"type": "string"}, "n": {"type": "number"}})),
    ("prices", "Price history from our stored candles (10 live coins, intraday; any other coin of the 120-coin universe, daily). With coin: open/high/low/close and change over a window (days, default 7; or start/end as YYYY-MM-DD or 'YYYY-MM-DD HH:MM' Toronto), when the high and low happened, how far price is from them, best and worst day, day by day (hour by hour for 2 days or less). Without coin: all 10 coins ranked over the window with each one's change against Bitcoin (relative strength / momentum ranking). what='coverage': the first and last stored candle per coin. Use for 'what was the high this week', 'how did each coin do', 'which coin is strongest', 'good days to trade', 'where was BTC on Tuesday', 'how far are we from the top'.", _schema({"coin": {**COIN, "description": "Optional coin; omit to compare all 10"}, "days": {"type": "number"}, "start": {"type": "string"}, "end": {"type": "string"}, "what": {"type": "string", "description": "optional: coverage"}})),
    ("introduce", "Madhav hands the conversation to one of his people. Call it IMMEDIATELY, in this same answer, whenever Madhav says someone is with him or asks you to talk to someone ('Ananta, this is Sam', 'my mom is here, say hi', 'talk to Anu'): never ask him to hand over first. Then your answer IS the greeting to that person (their opener, in their language). From then on you talk WITH that person directly. Only Madhav can introduce someone.", _schema({"name": {"type": "string"}})),
    ("back_to_madhav", "Madhav is back in the conversation ('it's me again', 'thanks Ananta, I'm back'): stop talking to the introduced person and talk to Madhav (sir) again.", _schema({})),
    ("market_check", "RESEARCH DESK for one coin (any coin): gathers dated facts from the live web (news, token unlocks in the next 30 days, exchange listings or delistings, hacks, legal trouble, the market mood), each with its source and whether it makes a buy riskier or safer; checks them against our own evidence (the exposure dial, the coin's tier and costs, the measured edges); and gives a verdict on what the web adds. The web can only make us more careful, never more aggressive. Use for 'should I buy X', 'what's going on with X', 'anything I should know before buying X', 'is X safe right now', and before explaining any trade decision on a coin. Cite the sources and dates.", _schema({"coin": {"type": "string"}})),
    ("web_lookup", "OUTSIDE OUR SYSTEM: a quick web search (Google via Gemini, else Claude web search) for things our data does not cover: stocks and indexes, other coins' news, the economy, events (Fed, CPI), what moved the market today. Returns a short sourced answer. Label it 'from the web' and never mix it into our books or setups.", _schema({"query": {"type": "string"}}, ["query"])),
    ("news_check", "Run the AI news check (the blunder guard) on one of our coins now: CLEAR / CAUTION / BLOCK with why and the headlines used. About a cent. Use when he asks to check the news on a coin.", _schema({"coin": COIN}, ["coin"])),
    ("remember", "Save something the owner asks you to remember or note down ('remember that I...', 'note that', 'keep this in mind'): it goes into his notes (found later by the knowledge lookup as 'your note') and the decision journal. Do it right away and confirm in a few words. Not for repair-shop requests (log_request) or alerts (propose_alert).", _schema({"text": {"type": "string", "description": "the note in his words, with the date context if relevant"}, "about": {"type": "string", "description": "optional: coin, trade or topic"}}, ["text"])),
    ("propose_levels", "Prepare a stop and/or target on a position in the owner's OWN paper book (e.g. 'set a stop on my Dogecoin at 9 cents', 'move my stop up', 'remove the target'). stop/target are prices; use 0 to remove one. Creates a card he confirms with Face ID.", _schema({"coin": COIN, "stop": {"type": "number"}, "target": {"type": "number"}}, ["coin"])),
    ("propose_switch", "Prepare flipping a main switch: switch = kill_switch (on stops all new trading in the backend; off lets it trade again) or autopilot (the trend portfolio's mode: on = AUTO applies its changes itself, off = SUGGEST waits for his approval). on = true/false. Creates a card he confirms with Face ID.", _schema({"switch": {"type": "string", "enum": ["kill_switch", "autopilot"]}, "on": {"type": "boolean"}}, ["switch", "on"])),
    ("propose_portfolio_decision", "Prepare approving or rejecting the trend portfolio's suggested changes (the ones waiting in suggest mode): decision approve | reject, ids = 'all' or a list of suggestion ids from the portfolio lookup. Creates a card he confirms with Face ID.", _schema({"decision": {"type": "string", "enum": ["approve", "reject"]}, "ids": {"type": "string", "description": "'all' or comma-separated ids"}}, ["decision"])),
    ("propose_alert_off", "Prepare switching off one of the owner's active alerts: alert = its id from the alerts lookup. Creates a card he confirms.", _schema({"alert": {"type": "string"}}, ["alert"])),
    ("propose_setting", "Prepare changing an Ananta setting: daily_budget_usd (Claude budget per day, 0-50), over_budget (gemini = free Gemini answers after the budget, stop = no answers), voice_enabled (1/0). Creates a card he confirms with Face ID.", _schema({"key": {"type": "string", "enum": ["daily_budget_usd", "over_budget", "voice_enabled"]}, "value": {"type": "string"}}, ["key", "value"])),
    ("read_doc", "Open one whole document from the knowledge map (for example 'casebook/REBUILD_2026-10-03.md' or 'knowledge/FRAMEWORK.md') when the passages from knowledge are not enough. Optional section = a heading word to return only that part.", _schema({"file": {"type": "string"}, "section": {"type": "string"}}, ["file"])),
    ("chain", "Ananta's decision chain for one coin or all 10 (fail-closed): regime -> trend -> location -> trigger -> invalidation -> risk -> exposure; where each coin stops and why, the stop and size if it got that far, plus relative strength vs BTC, volume and setup family as evidence. Use for 'should we buy X', 'why no trade', 'what is Ananta waiting for', 'which coins are closest'.", _schema({"coin": {**COIN, "description": "Optional coin; omit for all"}})),
    ("changes", "What changed / happened in the last N hours: buys, sells, orders, portfolio moves, warnings, owner actions.", _schema({"hours": {"type": "number"}})),
    ("report", "The latest daily or weekly report text.", _schema({"kind": {"type": "string", "description": "daily | weekly"}})),
    ("alerts", "The owner's alerts: active ones, and recently fired ones with their messages.", OFF),
    ("watch", "CREATE a watch for the person you are talking to when they ask you to keep watching a coin or a group for a setup "
     "('keep watching BTC for me', 'watch my coins for a pullback', 'tell me when SOL is ready'). It is created at once (no card) and "
     "checked every 15 minutes. kind: zone_pullback (default, best evidence: a dip into a supported zone with the trend up and the "
     "market rule open), setup_15m (any 15-minute setup completes; still being tested), trend_hold (the trend portfolio rates it "
     "strong). mode: tell (tell me), ask (ask me first: a card that expires in 30 minutes; the default), auto (buy in their book "
     "and tell them). group instead of coins: my_coins, all, large. Confirm in one sentence what you will watch and how you will act.",
     _schema({"coins": {"type": "array", "items": {"type": "string"}}, "group": {"type": "string"}, "kind": {"type": "string"},
              "mode": {"type": "string"}})),
    ("my_watches", "The watches you keep for this person: coins, kind, mode, state (watching, close, fired, paused) and why.", OFF),
    ("change_watch", "Change one of this person's watches: mode tell | ask | auto ('keep watching that but don't trade without asking me' "
     "= mode ask), or state PAUSED | WATCHING | DELETED. Give the watch id from my_watches, or the coin (e.g. SOL) when only one "
     "watch covers it. If the result has no 'changed', nothing changed: say so, never say done.",
     _schema({"id": {"type": "string"}, "coin": {"type": "string"}, "mode": {"type": "string", "enum": ["tell", "ask", "auto"]},
              "state": {"type": "string", "enum": ["PAUSED", "WATCHING", "DELETED"]}})),
    ("best_setup", "The setup you like most right now for this person: every coin against every setup kind they may use (their risk "
     "comfort filters the kinds), ready ones first, then one condition away, each with a decision card (found, why, wrong if). Use for "
     "'show me the setup you like most', 'what's your best idea', 'anything worth taking'. Mention a risk filter ONLY when filtered_out is "
     "present.", _schema({"coin": {**COIN, "description": "Optional: one coin"}})),
    ("agent_state", "What you (Ananta) are doing right now FOR THIS PERSON: watches, positions you monitor, what you are waiting for, "
     "what needs them. Use for 'what are you doing', 'what are you watching', 'show me the setup you're most interested in'.", OFF),
    ("account_activity", "What happened in this person's account since N hours ago: watches fired, trades, warnings, requests. Use for "
     "'what changed since this morning'.", _schema({"hours": {"type": "number"}})),
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


def _title(q: str) -> str:
    """A session's automatic title (plan 3.6b): its first question, cleaned and short."""
    import re as _r

    q = _r.sub(r"^(explain this finding simply|explain this|tell me about this|about):\s*", "", (q or "").strip(), flags=_r.I)
    q = _r.split(r"(?<=[.?!])\s", q)[0].strip().rstrip(".")
    if len(q) > 52:
        q = q[:50].rsplit(" ", 1)[0] + "…"
    return (q[:1].upper() + q[1:]) or "Conversation"


def _label_outside(reply: dict, found: list[dict]) -> None:
    """Answers built on outside data always carry the 'From AI' label and source; a coin we could not find becomes a 'did you mean'."""
    from jarvis.service import outside

    if not found:
        return
    web = [f for f in found if f.get("web")]
    if web:
        reply["outside"] = {"source": web[0].get("source") or "Web search", "url": web[0].get("source_url"),
                            "note": "From the web, not from our system: news and facts found online, with their sources. "
                                    "Not part of our books, setups or evidence."}
        for e in reply.get("evidence") or []:
            e.setdefault("source", "web")
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


GAP = re.compile(r"\b(I (do not|don't|didn't) have|we (do not|don't) (have|store|record|track|keep)|(is|are)n'?t (stored|recorded|tracked) "
                 r"|not in (our|my) (data|records|stores)|no (data|record|records) (on|for|of|about)|I (cannot|can't|could not|couldn't) "
                 r"(see|find|get|look up|access)|(our|my) data (does not|doesn't) (cover|include|go back))", re.I)


def _self_flag(j, question: str, reply: dict, log: list, thread: str | None) -> dict | None:
    """Self-flagging of gaps (Madhav's OK, 2026-10-04): when an answer admits we lack data or a tool, log it for the repair shop
    by itself (unless the model already did) and say the number once at the end of the answer."""
    ans = reply.get("answer") or ""
    if reply.get("kind") not in ("answer", "cannot_do_yet") or any(x.get("tool") == "log_request" for x in log):
        return None
    m = GAP.search(ans)
    if not m and reply.get("kind") != "cannot_do_yet":
        return None
    from jarvis.service import requests_log

    try:
        requests_log._table(j)
        if j.db.execute("SELECT COUNT(*) FROM owner_requests WHERE about='auto-flag' AND t >= ?", (int(j.now()) - 86400,)).fetchone()[0] >= 5:
            return None                                                  # at most 5 a day: a flood of gaps is one bug, not five
    except Exception:  # noqa: BLE001
        return None
    s0 = max(0, ans.rfind(".", 0, m.start()) + 1) if m else 0
    said = ans[s0:(ans.find(".", m.end()) + 1 if m and ans.find(".", m.end()) > 0 else s0 + 200)].strip()
    try:
        r = requests_log.add(j, "data", f"Gap found while answering: \"{question[:200]}\" Ananta said: \"{said[:240]}\"", "auto-flag",
                             by="ananta-auto", thread=thread)
    except Exception:  # noqa: BLE001
        return None
    reply["answer"] = ans.rstrip() + (f" I've logged that gap as request {r['num']} for the next work session." if not r.get("duplicate") else
                                      f" That gap is already on the list as request {r['num']}.")
    reply["self_flag"] = r.get("num")
    return r


def _telugu_talk(j, thread, text) -> bool:
    """A Telugu conversation: the person Madhav handed over to speaks Telugu, the message is in Telugu, or Madhav is about to
    introduce someone Ananta speaks Telugu to (his parents, the family's kids, some friends)."""
    try:
        from jarvis.service import people, speech

        if people.voice_language(j, thread) == "te" or speech.is_telugu([text]):
            return True
        low = (text or "").lower()
        return any(people.find(w) and people.find(w).get("language") in ("telugu", "telugu_mix", "mix")
                   for w in ("mom", "amma", "dad", "nanna") + tuple(n.lower() for p in people.load().get("people") or []
                                                                  for n in p.get("names") or []) if re.search(r"\b" + re.escape(w) + r"\b", low))
    except Exception:  # noqa: BLE001
        return False


def _pre_voice(context, text):
    """When the app will speak this answer in the natural voice, start making its audio now, so it is usually ready
    by the time the phone asks for it. A list (the tour) is one audio file per step. Returns the audio id(s), or None."""
    try:
        tts = context.get("tts") if isinstance(context, dict) else None
        if isinstance(tts, dict) and tts.get("voice") and text:
            from jarvis.service import speech

            speed = float(tts.get("speed") or 1.0)
            ids = [speech.prepare_answer(speech.sentences(item), str(tts["voice"]), speed) for item in (text if isinstance(text, list) else [text])]
            return ids if isinstance(text, list) else ids[0]
    except Exception:  # noqa: BLE001
        pass
    return None


VOICE_WORDS = 60
FILLER = re.compile(r"^\s*(h+m+|m+|m+-?hm+|uh-?huh|uh+|um+|ah+|oh+|pf+t?|ok|okay|yeah|yep|yes|right|cool|alright|all right|i see|got it|nice|"
                    r"great|sure|fine|hmm,? okay|okay,? okay)?[\s.!?,…]*$", re.I)
DANGLING = re.compile(r"(\b(and|or|but|so|because|the|a|an|to|of|for|with|about|if|that|my|our|your|is|are|was|were|what|which|how|why|"
                      r"when|where|like|i mean|i want to know|i want to ask|i have a question|tell me|can you|could you|i was wondering)"
                      r"[\s.]*|\.\.\.|…|,|-)\s*$", re.I)


ACK_WORDS = {"one sec", "let me check", "okay looking", "ok looking", "mm hm one moment", "mm hmm one moment", "let me pull that up"}


YES_WORDS = {"yes", "yeah", "yep", "yes please", "sure", "ok", "okay", "do it", "go ahead", "please do", "yes do it", "lets do it",
             "let's do it", "go for it", "sounds good"}


def _plain(t: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", str(t).lower().replace("'", ""))).strip()


def spoken_chip(heard: str, chips: dict | None) -> str | None:
    """Plan 3.7 / 4.1: the words of a chip, spoken, act like a tap. "Yes" (or "just say yes") takes the next action; a chip's
    label, or its short spoken form ("pull BTC"), takes that chip. Returns the question to ask, or None."""
    if not chips or not heard:
        return None
    h = _plain(heard)
    h = re.sub(r"^(ananta|jarvis|hey ananta|hey jarvis|ok|okay|um|uh)\s+", "", h).strip()
    nxt = chips.get("next") or None
    if nxt and nxt.get("ask") and (h in YES_WORDS or h.rstrip(" please") in YES_WORDS):
        return str(nxt["ask"])
    cands = ([nxt] if nxt else []) + [{"label": f, "ask": f} for f in (chips.get("follow") or []) if isinstance(f, str)]
    for c in cands:
        if not c or not c.get("ask"):
            continue
        for form in (c.get("label"), c.get("say")):
            f = _plain(form or "")
            if not f:
                continue
            if h == f or (len(f.split()) >= 2 and h.startswith(f)) or (len(h.split()) >= 3 and h in f and len(h) >= 0.6 * len(f)):
                return str(c["ask"])
    return None


def hearing_check(heard: str, last_spoken: str = "") -> str:
    """'echo' (the mic caught Ananta's own voice), 'filler' ('hmm', 'okay', '!'), 'partial' (he stopped mid-sentence: keep
    listening and join it to what he says next) or 'ok'. After a question from Ananta ('Want the details?'), a short 'yes' / 'okay'
    is an answer, not a filler."""
    from difflib import SequenceMatcher

    h = (heard or "").strip()
    if not h:
        return "filler"
    low = re.sub(r"[^a-z0-9 ]+", " ", h.lower()).split()
    if " ".join(low) in ACK_WORDS:                       # the mic caught Ananta's own "one sec"
        return "echo"
    if last_spoken and len(low) >= 4:
        ls = re.sub(r"[^a-z0-9 ]+", " ", last_spoken.lower())
        hs = " ".join(low)
        m = SequenceMatcher(None, hs, ls).find_longest_match(0, len(hs), 0, len(ls))
        if m.size >= 0.7 * len(hs):
            return "echo"
    asked = last_spoken.strip().endswith("?")
    if FILLER.match(h) and not asked:
        return "filler"
    if DANGLING.search(h) and not h.rstrip().endswith("?") and not (asked and len(low) <= 3):
        return "partial"
    return "ok"


THANKS = re.compile(r"^\s*(thanks|thank you|thank you so much|thanks a lot|cheers)[\s.!,]*(madhav|ananta|jarvis)?[\s.!]*$", re.I)
OKAY = re.compile(r"^\s*(ok|okay|cool|great|nice|got it|perfect|alright|all right|stop|cancel|never ?mind|that'?s all|that is all)[\s.!,]*(ananta|jarvis)?[\s.!]*$", re.I)
REPEAT = re.compile(r"\b(say (that|it) again|repeat (that|it|please|yourself)|come again|pardon( me)?|what did you (just )?say|one more time)\b", re.I)


NEXT_STEP_ANSWERS = 4      # Madhav: for the first 4 answers of every conversation, always offer the next step + 3 suggestions
YES = re.compile(r"^\s*(yes|yeah|yep|yup|sure|ok(ay)?|do it|go ahead|please( do)?|yes please|sure thing|let'?s do it|show me|pull it up)[\s.!,]*(jarvis|ananta|sir)?[\s.!]*$", re.I)
_PLAIN: dict = {}


def _plain_words(j) -> str:
    """The glossary (docs/knowledge/glossary.json) as a compact block for the system prompt."""
    try:
        from jarvis.service.core import docs_dir

        p = docs_dir(j.dir) / "knowledge" / "glossary.json"
        key = (str(p), p.stat().st_mtime)
        if _PLAIN.get("key") != key:
            g = json.loads(p.read_text())
            lines = [f"- {t['term']}: {t['plain']}. {t['meaning']} Ours: {t['ours']}." + ("" if t.get("used", True) else " (not used by Ananta)")
                     for t in g["terms"]]
            _PLAIN.update(key=key, text="\n\nPLAIN WORDS (say the meaning, keep the term; our settings):\n" + "\n".join(lines))
        return _PLAIN["text"]
    except Exception:  # noqa: BLE001  the glossary helps; it never blocks an answer
        return ""


def _status_block() -> str:
    """Every idea's status card (evidence + permission) for the system prompt."""
    try:
        from jarvis.service import brain

        cards = brain.status_cards()
        lines = [f"- {c['id']} {c['name']}: {c['evidence']} / {c['permission']} ({c['reason']})" for c in cards.values()]
        return ("\n\nSTATUS CARDS (what each idea may do; Madhav's acceptance framework, Oct 6). EVIDENCE: SUPPORTED, WEAK, CONFLICTING, "
                "INSUFFICIENT, REJECTED, UNTESTED. PERMISSION: PAPER = may be a reason in a paper trade; CONTEXT = explain it, never a reason "
                "to buy; OFF = switched off. Whenever you use an idea, say its evidence word in plain English ('supported', 'weak evidence', "
                "'mixed evidence', 'not enough evidence yet', 'tested and failed'). Never present a CONTEXT or OFF idea as a reason to "
                "trade. For 'can we trade on X / is X proven / why don't we use X', answer from its card (idea_status lookup for detail):\n"
                + "\n".join(lines))
    except Exception:  # noqa: BLE001
        return ""


def _clean_next(reply: dict) -> None:
    """A next step must be something we can run: a short label and a question or command; suggestions are short questions."""
    na = reply.get("next_action")
    if not (isinstance(na, dict) and str(na.get("label") or "").strip() and str(na.get("ask") or "").strip()):
        reply["next_action"] = None
    else:
        reply["next_action"] = {"label": str(na["label"]).strip()[:60], "ask": str(na["ask"]).strip()[:200], "say": str(na.get("say") or "").strip()[:200]}
    fu = [str(x).strip() for x in (reply.get("follow_ups") or []) if isinstance(x, str) and 3 <= len(str(x).strip()) <= 90]
    ask_ = (reply["next_action"] or {}).get("ask", "").lower()
    reply["follow_ups"] = [x for x in dict.fromkeys(fu) if x.lower() != ask_][:3]


def owner_address(t: str) -> str:
    """D6 / 3.7: Ananta always calls Madhav "sir" (Oct 9: a greeting still said "Good morning, Madhav")."""
    t = re.sub(r"^((?:Good )?(?:morning|afternoon|evening)|Hi|Hello|Hey)[,]?\s+Madhav\b", r"\1, sir", t, flags=re.I)
    t = re.sub(r",\s*Madhav(?=[.!?,])", ", sir", t)
    return t


def guest_address(t: str) -> str:
    """Only Madhav is 'sir' (and only Madhav is Madhav): a visitor's answer never addresses them that way."""
    t = re.sub(r",\s*(sir|Madhav)(?=[.!?,])", "", t)
    t = re.sub(r"^((?:Good )?(?:morning|afternoon|evening)|Morning|Hi|Hello|Hey|Sure|Yes|Okay|Right)[,]?\s+(sir|Madhav)\b[,.!]?", r"\1.", t, flags=re.I)
    return t


AGENT_DOING = re.compile(r"\bwhat (are|r) (you|u) (doing|watching|up to|working on)\b|\bwhat('s| is) ananta doing\b", re.I)
SAFE_Q = re.compile(r"\b(safe|safer|low risk|less risk|conservative|careful|not too risky)\b", re.I)
SINCE_Q = re.compile(r"\bwhat (has )?changed (since|today|this morning)\b", re.I)
WHY = re.compile(r"^\s*(why|but why|why so|why that|why not|how come|why is that|explain why)\s*[?.!]*\s*$", re.I)


def _chip_table(j) -> None:
    j.db.execute("CREATE TABLE IF NOT EXISTS ask_chips (reply_id TEXT, thread TEXT, t INTEGER, kind TEXT, text TEXT, ask TEXT, picked INTEGER DEFAULT 0, "
                 "PRIMARY KEY (reply_id, kind, text))")


def _log_chips(j, thread: str, reply_id: str, reply: dict) -> None:
    """Every chip shown, so the weekly table can rank what people actually tap (Madhav: refine from what users select)."""
    try:
        _chip_table(j)
        t = int(j.now())
        na = reply.get("next_action")
        rows = ([(reply_id, thread, t, "primary", na["label"], na["ask"])] if na else []) + \
               [(reply_id, thread, t, "suggest", x, x) for x in reply.get("follow_ups") or []]
        j.db.executemany("INSERT OR IGNORE INTO ask_chips (reply_id, thread, t, kind, text, ask) VALUES (?,?,?,?,?,?)", rows)
        j.db.commit()
    except Exception:  # noqa: BLE001
        pass


def chip_stats(j, days: int = 7) -> list[dict]:
    """How often each chip was tapped when shown (the refinement loop)."""
    _chip_table(j)
    since = int(j.now()) - days * 86400
    return [{"kind": k, "text": x, "shown": n, "picked": p, "rate": round(p / n, 2) if n else None} for k, x, n, p in
            j.db.execute("SELECT kind, ask, COUNT(*), SUM(picked) FROM ask_chips WHERE t >= ? GROUP BY kind, ask ORDER BY SUM(picked) DESC, COUNT(*) DESC",
                         (since,))]


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
    na = reply.get("next_action") if isinstance(reply.get("next_action"), dict) else None
    if na and na.get("say") and reply.get("kind") == "answer":
        t = (t + " " + str(na["say"]).strip()).strip()
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
        self.outside: list[dict] = []          # facts fetched from outside our system (CoinGecko, the web) for this answer
        self.web_cost = 0.0                    # web searches paid for during this answer (added to its cost)

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

    # Build plan 1.2a: a visitor's personal questions read only their own account; Ananta's research (Madhav's paper books) is
    # summarised and labelled, never presented as theirs, and its open positions, ids and dollar amounts are never handed over.
    GUEST_SCOPED = ("overview", "trades", "trade", "portfolio", "jarvis_book", "changes", "chain", "report", "mandate")

    def call(self, name: str, args: dict) -> Any:
        if self.guest and name in self.GUEST_SCOPED:
            try:
                return getattr(self, "g_" + name)(**(args or {}))
            except Exception as exc:  # noqa: BLE001
                return {"error": str(exc)[:300]}
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
    RESEARCH = "ANANTA'S RESEARCH (Madhav's paper books, shared learning): NOT this visitor's trades; never say 'your' about it"

    def g_portfolio(self) -> dict:
        from jarvis.service import account

        return account.brief(self.j)

    def g_overview(self) -> dict:
        from jarvis.service import account, health

        h = health.status(self.j)
        return {"your_account": account.brief(self.j),
                "ananta": {"whose": self.RESEARCH, "running": h.get("summary"), "watching": "10 coins every 15 minutes, hourly and daily"}}

    def g_trades(self, status: str = "open", coin: str | None = None) -> dict:
        from jarvis.service import account

        b = account.brief(self.j).get("book") or {}
        t = views.trades_list(self.j)
        closed = t.get("closed") or []
        return {"your_trades": {"positions": b.get("positions", []), "orders": b.get("orders", []),
                                "note": "These are the visitor's own paper trades: the only trades that are theirs."},
                "ananta_research": {"whose": self.RESEARCH, "open_count": len(t.get("open") or []), "closed_count": len(closed),
                                    "note": "Counts only. Never quote its positions or dollar amounts to a visitor."}}

    def g_trade(self, id: str) -> dict:  # noqa: A002
        from jarvis.service import account

        for f in (account.brief(self.j).get("book") or {}).get("orders", []):
            if str(id) in (str(f.get("t")), f.get("coin")):
                return {"your_order": f}
        return {"error": "That trade is not in this visitor's account. Only their own trades can be opened for them."}

    def g_jarvis_book(self) -> dict:
        from jarvis.service import brain

        r = brain.report(self.j)
        return {"whose": self.RESEARCH, "what": "Ananta's own research picks, $100 each, scored against random twins",
                "closed": r.get("closed"), "avg_usd_per_100": r.get("avg_usd_per_100"), "random_twin_avg_usd": r.get("random_twin_avg_usd"),
                "events": r.get("events"), "verdict": r.get("verdict")}

    def g_changes(self, hours: float = 24) -> dict:
        from jarvis.service import account

        since = int(self.j.now() - float(hours) * 3600)
        b = account.brief(self.j)
        return {"hours": hours, "your_orders": [o for o in (b.get("book") or {}).get("orders", []) if o["t"] >= since],
                "your_coins_now": b.get("their_coins_now"), "note": "Only this visitor's own events and coins."}

    def g_chain(self, coin: str | None = None) -> dict:
        from jarvis.service import account, chain

        b = chain.board(self.j, book=account.chain_book(self.j))
        if coin:
            c = coin.upper().replace("/USD", "")
            row = next((r for r in b.get("coins", []) if r["coin"] == c), None)
            if row is None:
                raise ValueError(f"unknown coin {coin}")
            return {"framework": b["framework"], "note": "Risk and exposure use this visitor's own book.", **row}
        return {k: b[k] for k in ("framework", "stops")} | {"note": "Risk and exposure use this visitor's own book.",
                                                            "coins": [{k: r.get(k) for k in ("coin", "verdict", "stops_at", "summary", "observations")} for r in b.get("coins", [])]}

    def g_report(self, kind: str = "daily") -> dict:
        return {"error": "The daily and weekly reports cover Ananta's research books, not this account. Answer from the visitor's own book."}

    def g_mandate(self) -> dict:
        from jarvis.service import account

        p = account.profile(self.j.db)
        return {"note": "A practice account has no mandate of its own; Ananta follows what the visitor told it.",
                "risk": p.get("risk"), "coins": p.get("coins"), "level": account.level(p)}

    def t_watch(self, coins: list | None = None, group: str | None = None, kind: str | None = None, mode: str = "ask") -> dict:
        from jarvis.service import watches

        w = watches.create(self.j, coins, group, kind, mode, by="ananta (asked in chat)")
        self.ui.append({"do": "go_to", "target": "markets", "label": "Watchlists"})
        return {"created": w, "say": f"Watching {watches.describe(w)}; {watches.MODES[w['mode']]}."}

    def t_my_watches(self) -> dict:
        from jarvis.service import watches

        return {"watches": watches.list_(self.j), "kinds": watches.kinds()}

    def t_change_watch(self, id: str | None = None, mode: str | None = None, state: str | None = None, coin: str | None = None) -> dict:  # noqa: A002
        """Plan 4.3 / 6.1: the watch can be named by its id or by its coin; a miss says so (Ananta must not claim a change)."""
        from jarvis.service import account, watches

        ws = [w for w in watches.list_(self.j) if w["state"] != "DELETED"]
        target = next((w for w in ws if w["id"] == id), None)
        if not target:
            want = (coin or id or "").upper()
            names = {v.upper(): k for k, v in account.NAMES.items()}
            sym = next((c for c in account.COINS if c in want.replace("_", " ").split() or want.startswith(c)), None) or next(
                (k for n, k in names.items() if n in want), None)
            hits = [w for w in ws if sym and sym in (w.get("coins") or [])]
            if len(hits) == 1:
                target = hits[0]
            elif len(ws) == 1 and not sym:
                target = ws[0]
        if not target:
            return {"changed": None, "error": "No watch matches that. Nothing was changed.",
                    "watches": [{"id": w["id"], "coins": w["coins"], "mode": w["mode"]} for w in ws]}
        return {"changed": watches.change(self.j, target["id"], mode, state)}

    def t_best_setup(self, coin: str | None = None) -> dict:
        from jarvis.service import account, watches
        from jarvis.service.app import _main

        p = account.profile(self.j.db) if getattr(self.j, "sandbox", False) else account.owner_profile(self.j)
        return watches.best_setups(_main(), p.get("risk"), [coin.upper()] if coin else None)

    def t_agent_state(self) -> dict:
        from jarvis.service import watches

        return watches.state(self.j)

    def t_account_activity(self, hours: float = 24) -> dict:
        from jarvis.service import watches

        return watches.since(self.j, int(self.j.now() - float(hours) * 3600))

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

    def t_evidence(self, part: str = "summary") -> dict:
        """Cost layer (2026-10-09): the whole Evidence was ~14k tokens on every use; the summary is enough for most questions."""
        ev = views.evidence_collected(self.j)
        fw = views.evidence_forwarded(self.j)
        for x in fw["in_use"]:
            (x.get("tracking") or {}).pop("series", None)
        live = {}
        try:
            from jarvis.service import evidence_live

            live = {"repair_loop_live": evidence_live.summary(self.j)}     # the Evidence page's numbers, the same ones Madhav sees
        except Exception as exc:  # noqa: BLE001
            live = {"repair_loop_live_error": str(exc)[:160]}
        if part == "full":
            return {**ev, "in_use": fw["in_use"], "safety_changes": fw["safety_changes"], **live}
        if part == "reviews":
            return {"reviews": ev.get("forwarded") or []}
        if part == "setups":
            return {"collected": ev.get("collected"), "tracker": ev.get("tracker")}
        if part == "in_use":
            return {"in_use": fw["in_use"], "safety_changes": fw["safety_changes"]}
        lv = live.get("repair_loop_live") or {}
        core_ = {k: lv.get(k) for k in ("as_of", "headline", "loop", "results", "board_counts", "acceptance_gate") if k in lv}
        return {"repair_loop_live": core_, "reviews": [{k: r.get(k) for k in ("id", "title", "verdict")} for r in (ev.get("forwarded") or [])[-12:]],
                "more": "ask with part = reviews | setups | in_use | full for the details (clocks, limits, reconstruction, misses, waiting are in full)"}

    def _notes_dir(self) -> Path:
        return Path(os.path.expanduser(os.getenv("ANANTA_NOTES_DIR", "~/AnantaBrain/My notes")))

    def t_knowledge(self, query: str) -> dict:
        from jarvis.service.core import docs_dir

        docs = docs_dir(self.j.dir)
        roots = [docs / "repair_shop", docs / "research", docs / "knowledge", docs / "knowledge" / "teachers", docs / "casebook"]
        files = [p for r in roots if r.exists() for p in r.glob("*.md")] + [docs / "RULEBOOK_V0.md", docs / "VARIABLE_REGISTRY.md"]
        notes = self._notes_dir()
        note_files = ([p for p in sorted(notes.rglob("*.md")) if not p.name.lower().startswith("start here")][:300]
                      if notes.exists() and not self.guest else [])                   # his private notes: owner only
        words = [w for w in re.findall(r"[a-z0-9]+", query.lower()) if len(w) > 2]
        hits = []
        for p in files + note_files:
            if not p.exists():
                continue
            text = p.read_text(errors="ignore")
            name = f"your note: {p.relative_to(notes)}" if p in note_files else str(p.relative_to(docs))
            paras = re.split(r"\n(?=#)|\n\n", text)
            for para in paras:
                low = para.lower()
                score = sum(low.count(w) for w in words)
                if score:
                    hits.append((score, name, para.strip()[:900]))
        cases = docs / "casebook" / "cases.json"
        if cases.exists():                                   # Madhav's own trades, one case per passage
            cb = json.loads(cases.read_text())
            for c in cb.get("cases", []) + cb.get("lessons", []):
                blob = json.dumps(c)
                score = sum(blob.lower().count(w) for w in words)
                if score:
                    hits.append((score, "casebook/cases.json", blob[:900]))
        hits.sort(key=lambda h: -h[0])
        mine = [h for h in hits if h[1].startswith("your note")][:3]       # his own notes get their own slot
        hits = [h for h in hits if not h[1].startswith("your note")]
        idx = docs / "KNOWLEDGE_INDEX.md"
        index = [ln.strip("- ").strip() for ln in idx.read_text().splitlines() if ln.startswith("- ")
                 and any(w in ln.lower() for w in words)][:8] if idx.exists() else []
        reg = docs / "variable_registry.json"
        regs = []
        if reg.exists():
            r = json.loads(reg.read_text())
            for v in r["variables"]:
                blob = json.dumps(v).lower()
                if any(w in blob for w in words):
                    regs.append(v)
        hyp = []
        hp = docs / "knowledge" / "hypotheses.json"
        if hp.exists():
            for h in json.loads(hp.read_text()).get("hypotheses", []):
                blob = json.dumps(h).lower()
                sc_ = sum(blob.count(w) for w in words)
                if sc_:
                    hyp.append((sc_, h))
            hyp.sort(key=lambda x: -x[0])
        return {"map": index, "passages": [{"file": f, "text": t} for _, f, t in hits[:6]],
                "your_notes": [{"file": f, "text": t} for _, f, t in mine], "registry": regs[:8],
                "hypotheses": [h for _, h in hyp[:5]],
                "tiers": "registry = Ananta-verified variables; casebook = Madhav's own trades; hypotheses = teacher ideas with their "
                         "test status (not rules); 'your note' = Madhav's own notes (his view, not verified). read_doc opens a whole file from the map."}

    def t_read_doc(self, file: str, section: str | None = None) -> dict:
        from jarvis.service.core import docs_dir

        docs = docs_dir(self.j.dir).resolve()
        notes = self._notes_dir().resolve()
        rel = file.strip().removeprefix("docs/").removeprefix("your note: ")
        p = (docs / rel).resolve()
        if not (p.is_relative_to(docs) and p.is_file()):
            q = (notes / rel).resolve()
            p = q if not self.guest and notes.exists() and q.is_relative_to(notes) and q.is_file() else None
        if p is None or p.suffix not in (".md", ".json", ".txt"):
            return {"error": f"no document '{file}' in the knowledge map", "hint": "call knowledge first; its map lists the files"}
        text = p.read_text(errors="ignore")
        if section:
            parts = re.split(r"\n(?=#)", text)
            pick = [x for x in parts if section.lower() in x.splitlines()[0].lower()] or [x for x in parts if section.lower() in x.lower()]
            text = "\n".join(pick[:3]) if pick else text
        cut = len(text) > 12000
        return {"file": file, "text": text[:12000], "truncated": cut}

    def t_zones(self, coin: str | None = None) -> dict:
        from jarvis.service import zones_watch

        if coin:
            r = zones_watch.coin(self.j, coin.upper().replace("/USD", ""))
            return r if r else {"error": f"no zones for {coin}"}
        b = zones_watch.board(self.j)
        slim = [{"coin": r["coin"], "price": r["price"], "in_zone": r["in_zone"], "attention": r.get("attention"),
                 "inside": [{k: z.get(k) for k in ("bot", "top", "kinds", "tier", "history")} for z in r["inside"]],
                 "next_support": r["next_support"] and {k: r["next_support"].get(k) for k in ("bot", "top", "kinds", "distance_pct", "history")},
                 "next_resistance": r["next_resistance"] and {k: r["next_resistance"].get(k) for k in ("bot", "top", "kinds", "distance_pct", "history")}}
                for r in b.get("coins", [])]
        from jarvis.service import news_watch

        news = {n["coin"]: f"{n['verdict']} ({n['day']}): {n['why']}" for n in reversed(news_watch.latest(self.j, None, 2))}
        return {"day": b.get("day"), "in_zone": b.get("in_zone"), "attention": b.get("attention"), "news_today": news, "coins": slim, "recent_entries": b.get("recent", [])[:8], "note": b.get("note")}

    def t_credit(self) -> dict:
        from jarvis.service import credit

        return credit.report(self.j)

    def _last_answer(self) -> tuple[str | None, str, str]:
        """(message id, question, answer) of the previous answer in this conversation."""
        if not self.thread:
            return None, "", ""
        rows = self.j.db.execute("SELECT id, role, text, reply FROM ask_messages WHERE thread=? AND error IS NULL ORDER BY t DESC, rowid DESC LIMIT 6",
                                 (self.thread,)).fetchall()
        aid, ans, q = None, "", ""
        for mid, role, text, reply in rows:
            if role == "assistant" and aid is None:
                aid, ans = mid, (json.loads(reply or "{}").get("answer") or "")
            elif role == "user" and aid is not None:
                q = text or ""
                break
        return aid, q, ans

    def t_log_request(self, kind: str, text: str, about: str | None = None, last_answer: bool = False) -> dict:
        from jarvis.service import requests_log

        if last_answer:
            aid, q, ans = self._last_answer()
            if ans:
                text = f"{text} [The question: \"{q[:200]}\" The answer: \"{ans[:300]}\"]"
                if aid:
                    self.j.db.execute("UPDATE ask_messages SET rating=-1 WHERE id=?", (aid,))
                    self.j.db.commit()
        r = requests_log.add(self.j, kind, text, about, by="guest" if self.guest else "owner", thread=self.thread)
        return {**r, "note": "Confirm with the number, in one sentence. It shows on the Evidence page's repair board and in the Home feed; he gets a "
                "phone note when its status changes, and you will mention it in a later conversation."}

    def t_scoreboard(self) -> dict:
        from jarvis.service import scoreboard

        return scoreboard.board(self.j)

    def t_watches(self, section: str | None = None) -> dict:
        from jarvis.service import eye, scoreboard

        reg = scoreboard.registry(self.j)
        ws = [w for w in reg.get("watches", []) if not section or w.get("section") == section.upper()]
        st = eye.status(self.j)
        st.pop("prices", None)
        st["recent"] = st.get("recent", [])[:8]
        return {"sections": reg.get("sections"), "loops": reg.get("loops"), "how_to_add": reg.get("how_to_add"), "watches": ws, "eye": st}

    def t_jarvis_book(self) -> dict:
        from jarvis.service import brain

        return brain.report(self.j, 30)

    def t_missed_moves(self, days: float = 7) -> dict:
        from jarvis.service import missed

        return missed.recent(self.j, int(days or 7))

    def t_trade_reviews(self, days: float = 7) -> dict:
        from jarvis.service import reviews

        r = reviews.recent_reviews(self.j, int(days or 7))
        r["reviews"] = r["reviews"][:12]
        return {**r, "evenings": reviews.latest(self.j, 2)}

    def t_system_health(self) -> dict:
        from jarvis.service import health

        return health.status(self.j)

    def t_my_requests(self) -> dict:
        from jarvis.service import requests_log

        rows = requests_log.list_(self.j)
        return {"open": sum(r["status"] in ("OPEN", "PLANNED") for r in rows),
                "requests": [{k: r.get(k) for k in ("num", "kind", "text", "status", "status_words", "note")} for r in rows[:15]]}

    def t_prices(self, coin: str | None = None, days: float | None = None, start: str | None = None, end: str | None = None,
                 what: str | None = None) -> dict:
        from jarvis.service import pricebook

        if (what or "").lower().startswith("cov"):
            return pricebook.coverage(self.j)
        if coin:
            try:
                return pricebook.history(self.j, coin, days or 7, start, end)
            except ValueError as e:
                if "not one of our 10 coins" not in str(e):
                    raise
                from jarvis.service import universe

                try:
                    return universe.history(self.j, coin, days or 30, start, end)
                except ValueError as e2:
                    if "120-coin" not in str(e2):
                        raise
                    return self._feed_history(coin, days or 30)
        return pricebook.compare(self.j, days or 7, start, end)

    def t_idea_status(self, idea: str | None = None) -> dict:
        from jarvis.service import brain

        cards = list(brain.status_cards().values())
        if idea:
            q = idea.lower().strip()
            hit = [c for c in cards if q in c["id"].lower() or q in c["name"].lower() or any(q in a.lower() or a.lower() in q for a in c["aliases"])]
            return {"idea": idea, "cards": hit or [], "note": "" if hit else "No card for that idea: say Ananta has not researched it (UNTESTED)."}
        return {"cards": cards, "counts": {k: sum(1 for c in cards if c["permission"] == k) for k in ("PAPER", "CONTEXT", "OFF", "LIVE_PROVEN")}}

    def t_universe(self, coin: str | None = None, tier: str | None = None, rank_by: str | None = None, days: float | None = None,
                   top: float | None = None) -> dict:
        from jarvis.service import universe

        if coin:
            out = universe.card(self.j, coin)
            try:
                live = self.t_whole_market("coin", coin=coin)
                if not live.get("error"):
                    out["watched_live"] = live
                    if not out.get("in_universe"):
                        out["note"] = (f"{coin.upper()} is not in the 120-coin research lake, but Ananta watches it live: see watched_live.")
            except Exception:  # noqa: BLE001
                pass
            return out
        return universe.overview(self.j, tier, rank_by, days, int(top) if top else None)

    def _feed_history(self, coin: str, days: float) -> dict:
        """Daily history for any watched coin outside the 120 (the universe feed's candles)."""
        from jarvis.service import app as _app
        from jarvis.service import feed, registry

        j = _app._main()
        c = (coin or "").upper().replace("/USD", "").replace("USDT", "").strip()
        if not registry.card(j, c):
            raise ValueError(f"{coin} is not among the coins Ananta watches; use outside_coin or web_lookup")
        D = feed.daily(j, c)[-int(max(2, min(365, days))):]
        if not D:
            raise ValueError(f"no daily candles for {c} yet")
        hi, lo = max(D, key=lambda r: r[2]), min(D, key=lambda r: r[3])
        day = lambda t: time.strftime("%Y-%m-%d", time.gmtime(t))  # noqa: E731
        return {"coin": c, "timeframe_used": "1d", "from": day(D[0][0]), "to": day(D[-1][0]), "open": D[0][1], "high": hi[2], "high_day": day(hi[0]),
                "low": lo[3], "low_day": day(lo[0]), "close": D[-1][4], "change_pct": round(100 * (D[-1][4] / D[0][1] - 1), 2),
                "price_now": feed.prices(j).get(c), "source": "the universe feed (Binance daily candles)"}

    def t_exposure(self) -> dict:
        from jarvis.service import ev, exposure, universe_watch

        j = self.j
        try:
            from jarvis.service import app as _app

            j = _app._main()
        except Exception:  # noqa: BLE001
            pass
        return {"dial": exposure.state(j), "books": exposure.books(j), "measured_edges": ev.table(),
                "account": universe_watch.would_be(j), "fidelity": ev.fidelity(j),
                "note": "Paper only. A setup with no row in measured_edges has no measured edge: the brain defaults to PASS on it when the dial is closed."}

    def t_whole_market(self, view: str | None = None, tier: str | None = None, coin: str | None = None, n: float | None = None) -> dict:
        from jarvis.service import feed, registry, universe_watch

        j = self.j
        try:
            from jarvis.service import app as _app

            j = _app._main()                               # the universe books live in the main account (visitors read them)
        except Exception:  # noqa: BLE001
            pass
        v = (view or ("coin" if coin else "movers_up")).lower()
        n = int(n or 10)
        if v == "coin" or coin:
            c = (coin or "").upper().replace("/USD", "").replace("USDT", "").strip()
            k = registry.card(j, c)
            if not k:
                return {"error": f"{c} is not among the coins Ananta watches (Binance spot against USDT, minus stablecoins, wrapped, "
                                 "leveraged and tokenized shares); use outside_coin or web_lookup, and say so."}
            row = next((r for r in universe_watch.coins(j, q=c, n=600)["coins"] if r["coin"] == c), {})
            trades = [dict(zip(("watch", "status", "entry", "entry_day", "net_usd", "why"), t)) for t in j.db.execute(
                "SELECT watch, status, entry, entry_day, net_usd, why FROM evidence_trades WHERE coin=? AND (watch LIKE '%-U_' OR watch LIKE 'JARVIS%') "
                "ORDER BY signal_t DESC LIMIT 6", (c,))]
            zs = (universe_watch._armed(j).get("zones") or {}).get(c) or []
            why_not = []                                   # "why didn't you take X?": every moment it was woken for, and what happened
            try:
                for t, trig, st in j.db.execute("SELECT t, trigger, state FROM brain_queue WHERE coin=? ORDER BY t DESC LIMIT 6", (c,)):
                    d = j.db.execute("SELECT action, confidence, thesis, note FROM brain_decisions WHERE coin=? AND t >= ? ORDER BY t LIMIT 1",
                                     (c, t)).fetchone() if st == "DONE" else None
                    why_not.append({"when_utc": time.strftime("%Y-%m-%d %H:%M", time.gmtime(t)), "moment": trig,
                                    "what_happened": (f"decided {d[0]} ({(d[1] or 0):.0f}% confidence): {d[2] or ''}" + (f" [{d[3]}]" if d[3] else "")) if d else st})
            except Exception:  # noqa: BLE001
                pass
            return {"coin": c, "name": k.get("name"), "brain_moments": why_not, "tier": k.get("tier"), "status": k.get("status"), "price": row.get("price"),
                    "change_today_pct": row.get("change_today_pct"), "median_daily_usd_30d": k.get("median_usd_30d"),
                    "can_buy": {"ndax_cad": k.get("ndax"), "kraken_usd": k.get("kraken")}, "groups": k.get("groups"),
                    "support_zones": [{"bot": z["bot"], "top": z["top"], "history": z["history"]} for z in zs][:4],
                    "near_zone": row.get("near_zone"), "paper_trades_on_it": trades,
                    "paper_cost_each_side_pct": round(100 * registry.cost(c), 2),
                    "note": "Watched live: every rule runs on it after each daily close and the zone touch on its live price. "
                            + ("Tier C: watched and scored, never judged (too thin to trust paper fills)." if k.get("tier") == "C" else "")}
        if v.startswith("score"):
            sb = universe_watch.scoreboard(j)
            rows = [w for w in sb["watches"] if (not tier or w["tier"] in tier.upper())]
            return {"watches": rows[:40], "rule": sb["rule"]}
        if v.startswith("watch") or v.startswith("count") or v.startswith("health"):
            st = universe_watch.status(j)
            return {"counts": st["counts"], "feed": {k: st["feed"].get(k) for k in ("coins_with_5m", "price_age_s", "last_5m_pull", "weight_1m")},
                    "zones_armed": st["zones_armed"], "paper_trades": st["trades"], "last_rebuild": st["last_rebuild"],
                    "how": "One feed for every coin (Binance public data): 5-minute candles every 5 minutes, prices every 10 seconds, "
                           "daily candles after each close. The 10 live coins keep their own books as before."}
        sort = {"movers_up": "up", "movers_down": "down", "near_zone": "near"}.get(v, "up")
        res = universe_watch.coins(j, tier=tier, sort=sort, n=n)
        return {"view": v, "tier": tier or "all", "coins": res["coins"], "counts": res["counts"], "note": res["note"],
                "price_age_s": feed.status(j).get("price_age_s")}

    def t_introduce(self, name: str) -> dict:
        from jarvis.service import people

        if self.guest:
            return {"error": "Only Madhav can introduce people."}
        return people.introduce(self.j, self.thread, name)

    def t_back_to_madhav(self) -> dict:
        from jarvis.service import people

        return people.back(self.j, self.thread)

    def t_market_check(self, coin: str) -> dict:
        from jarvis.service import weblook

        r = weblook.market_check(self.j, coin)
        if not r.get("error"):
            self.outside.append({"found": True, "source": r.get("engine", "web"), "source_url": (r.get("sources") or [{}])[0].get("url"),
                                 "symbol": r.get("coin"), "web": True})
            self.web_cost += float(r.get("cost_usd") or 0)
        return r

    def t_web_lookup(self, query: str) -> dict:
        from jarvis.service import weblook

        r = weblook.lookup(query)
        if not r.get("error"):
            self.outside.append({"found": True, "source": r.get("engine", "web"), "source_url": (r.get("sources") or [{}])[0].get("url"),
                                 "symbol": None, "web": True})
            self.web_cost += float(r.get("cost_usd") or 0)
        return r

    def t_news_check(self, coin: str) -> dict:
        from jarvis.service import news_watch, reads_watch

        c = (coin or "").upper().replace("/USD", "")
        if c not in reads_watch.NAMES:
            return {"error": f"{coin} is not one of our coins; for other coins use web_lookup"}
        if self.guest:
            return {"error": "Practice mode: the news check uses Madhav's AI budget, so it is locked for guests. Say so politely."}
        res = reads_watch.news_check(self.j, c)
        if res.get("verdict") != "NOT_CHECKED":
            news_watch._table(self.j)
            self.j.db.execute("INSERT OR REPLACE INTO news_log VALUES (?,?,?,?,?,?)",
                              (news_watch.today(self.j), c, int(self.j.now()), res.get("verdict"), res.get("why"), json.dumps(res)))
            self.j.db.commit()
        return {"coin": c, **res}

    def t_remember(self, text: str, about: str | None = None) -> dict:
        from jarvis.service.manual import Manual

        text = (text or "").strip()[:600]
        if not text:
            return {"error": "nothing to remember"}
        jid = Manual(self.j.db, self.j.now).note("guest" if self.guest else "owner (via Ananta)", "note", about or "", text)
        saved_to = "the decision journal"
        if not self.guest:
            try:
                d = self._notes_dir()
                if d.exists():
                    from datetime import datetime
                    from zoneinfo import ZoneInfo

                    stamp = datetime.fromtimestamp(self.j.now(), ZoneInfo("America/Toronto")).strftime("%Y-%m-%d %H:%M")
                    p = d / "From Ananta - things you asked me to remember.md"
                    if not p.exists():
                        p.write_text("# Things you asked Ananta to remember\n\nAnanta adds a line here when you say \"remember...\" or \"note that...\". "
                                     "Edit or delete freely; Ananta reads this file as your notes.\n")
                    with p.open("a") as f:
                        f.write(f"\n- {stamp}{' (' + about + ')' if about else ''}: {text}")
                    saved_to = "your notes folder and the decision journal"
            except Exception:  # noqa: BLE001  the journal copy is enough
                pass
        return {"saved": jid.get("id"), "saved_to": saved_to, "note": "Confirm in a few words (e.g. 'Noted.')."}

    def _card(self, kind: str, summary: str, payload: dict) -> dict:
        from jarvis.service.mandate import Mandate

        a = Mandate(self.j.db, self.j.now).propose(kind, summary, payload, self.thread)
        self.created.append(a)
        return {"prepared": a, "note": "Not done yet: a card is waiting for his Face ID (or phone passcode). Say so."}

    def t_propose_levels(self, coin: str, stop: float | None = None, target: float | None = None) -> dict:
        from jarvis.service.manual import Manual

        c = (coin or "").upper().replace("/USD", "")
        px = self.j.prices()
        st = Manual(self.j.db, self.j.now).state(px)
        pos = next((p for p in st["positions"] if p["coin"] == c), None)
        if not pos:
            return {"error": f"there is no {c} in the owner's own paper book" + (" (the Explorer's and the trend portfolio's trades are evidence and keep their own rules)" if c in px else "")}
        if stop is None and target is None:
            return {"error": "give a stop and/or a target price (0 removes one)"}
        now = px.get(c)
        if stop and now and stop >= now:
            return {"error": f"the stop must be below the price now (about {now:,.6g})"}
        if target and now and target <= now:
            return {"error": f"the target must be above the price now (about {now:,.6g})"}
        parts = []
        if stop is not None:
            parts.append("remove the stop" if not stop else f"stop at ${stop:,.6g}" + (f" ({100 * (stop / now - 1):+.1f}%)" if now else ""))
        if target is not None:
            parts.append("remove the target" if not target else f"target at ${target:,.6g}" + (f" ({100 * (target / now - 1):+.1f}%)" if now else ""))
        return self._card("levels", f"Your {c} paper position: " + ", ".join(parts) + ".", {"coin": c, "stop": stop, "target": target})

    def t_propose_switch(self, switch: str, on: bool) -> dict:
        if self.guest:
            return {"error": "Practice mode: the kill switch and autopilot belong to Madhav's real paper books, so they are locked for guests."}
        if switch == "kill_switch":
            s = ("Turn the kill switch ON: the backend stops opening new trades until you turn it off." if on else
                 "Turn the kill switch OFF: the backend may open new paper trades again.")
        elif switch == "autopilot":
            s = ("Autopilot ON: the trend portfolio applies its own changes (AUTO)." if on else
                 "Autopilot OFF: the trend portfolio waits for your approval (SUGGEST).")
        else:
            return {"error": "switch is kill_switch or autopilot"}
        return self._card("switch", s, {"switch": switch, "on": bool(on)})

    def t_propose_portfolio_decision(self, decision: str, ids: str = "all") -> dict:
        if self.guest:
            return {"error": "Practice mode: portfolio approvals belong to Madhav's real paper portfolio, so they are locked for guests."}
        h = views.holdings(self.j)
        pend = h.get("pending") or []
        if not pend:
            return {"error": "the trend portfolio has no suggested changes waiting"}
        want = [x.strip() for x in str(ids or "all").split(",") if x.strip()]
        pick = pend if want in ([], ["all"]) else [p for p in pend if str(p.get("id")) in want]
        if not pick:
            return {"error": "none of those ids are waiting", "waiting": [p.get("id") for p in pend]}
        what = "; ".join(f"{str(p.get('action', '')).lower()} {p.get('coin', '')}".strip() for p in pick[:5])
        verb = "Approve" if decision == "approve" else "Reject"
        return self._card("portfolio_decision", f"{verb} the trend portfolio's suggestion{'s' if len(pick) > 1 else ''}: {what}"[:280],
                          {"decision": decision, "ids": [p.get("id") for p in pick] if want not in ([], ["all"]) else "all"})

    def t_propose_alert_off(self, alert: str) -> dict:
        from jarvis.service.alerts import Alerts

        al = [a for a in Alerts(self.j.db, self.j.now).list(include_done=False)]
        a = next((x for x in al if str(x.get("id")) == str(alert)), None)
        if not a:
            return {"error": "no active alert with that id", "active": [{"id": x.get("id"), "what": x.get("what")} for x in al][:10]}
        return self._card("alert_off", f"Switch off the alert: {a.get('what')}", {"id": a["id"]})

    def t_propose_setting(self, key: str, value: str) -> dict:
        if self.guest:
            return {"error": "Practice mode: settings belong to Madhav."}
        if key not in ("daily_budget_usd", "over_budget", "voice_enabled"):
            return {"error": "key is daily_budget_usd, over_budget or voice_enabled"}
        words = {"daily_budget_usd": f"Set the daily Claude budget to ${float(value):.2f}" if str(value).replace('.', '', 1).isdigit() else None,
                 "over_budget": f"After the budget: {'free Gemini answers' if value == 'gemini' else 'no answers until midnight'}",
                 "voice_enabled": f"Voice {'on' if str(value) in ('1', 'true', 'on') else 'off'}"}[key]
        if not words:
            return {"error": "the budget must be a number of dollars"}
        return self._card("setting", words + ".", {"key": key, "value": str(value)})

    def t_layers(self, part: str | None = None) -> dict:
        from jarvis.service import layers

        if part:
            c = layers.component(part, self.j.dir)
            return c if c else {"error": f"no part called '{part}' in the layer map"}
        return layers.board(self.j.dir)

    def t_reads(self, coin: str | None = None) -> dict:
        from jarvis.service import reads_watch

        b = reads_watch.board(self.j)
        if coin:
            c = coin.upper().replace("/USD", "")
            row = next((r for r in b.get("coins", []) if r["coin"] == c), None)
            if row is None:
                return {"error": f"no reads for {coin}"}
            return {**row, "history": b.get("history"), "note": b.get("note")}
        slim = [{"coin": r["coin"], "best": r["best"]} for r in b.get("coins", [])]
        from jarvis.service import shadow_h07

        sh = shadow_h07.report(self.j)
        return {"day": b.get("day"), "fired": b.get("fired"), "close": b.get("close"), "coins": slim, "recent_fires": b.get("recent", [])[:5],
                "h07_paper_shadow": {k: sh[k] for k in ("closed", "open", "waiting", "net_usd", "win_rate", "history")},
                "history": b.get("history"), "note": b.get("note")}

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
    "gemini_voice": {"label": "Gemini Flash-Lite (voice)", "provider": "gemini", "model": None, "price": (0.0, 0.0), "cache": 0.0},
    "haiku": {"label": "Claude Haiku", "provider": "claude", "model": os.getenv("ASK_HAIKU_MODEL", "claude-haiku-4-5-20251001"), "price": (1.0, 5.0), "cache": 0.1},
    "sonnet": {"label": "Claude Sonnet", "provider": "claude", "model": os.getenv("ASK_CLAUDE_MODEL", "claude-sonnet-5-5"), "price": (2.0, 10.0), "cache": 0.1},
    "opus": {"label": "Claude Opus", "provider": "claude", "model": os.getenv("ASK_OPUS_MODEL", "claude-opus-5-5"), "price": (4.0, 20.0), "cache": 0.05},
}
MODES = {"everyday": "gemini", "deep": "sonnet", "max": "opus", "google": "gemini_deep"}
# The app's two switches: Auto on/off x Claude/Google -> auto | deep | google_auto | google
ALIASES = {"claude": "sonnet", "gemini": "gemini", "haiku": "haiku", "sonnet": "sonnet", "opus": "opus", "local": "local"}
# Cost layer (Madhav, 2026-10-09): Sonnet only for work that needs real analysis (comparing, evaluating, planning, choosing a trade,
# reviewing); explanations, "why", status and look-ups go to Haiku, which reads the same data at about half the price per token.
DEEP_WORDS = re.compile(r"\b(compare|evaluat|analy[sz]|should (i|we)|prepare|review|reconstruct|what if|strateg|backtest|plan\b|recommend|improve|"
                        r"investigat|deep dive|find (me )?a trade|best (setup|trade|idea)|rate my|weakest|strongest|which (coin|trade) (to|should))", re.I)


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
    return round((usage.get("in", 0) * pin + usage.get("cache_write", 0) * pin * 1.25 + usage.get("cache_write_1h", 0) * pin * 2.0
                  + usage.get("cache_read", 0) * pin * m["cache"] + usage.get("out", 0) * pout) / 1e6, 5)


def _strip_cache(msgs: list) -> None:
    for m in msgs:
        if isinstance(m.get("content"), list):
            for b in m["content"]:
                if isinstance(b, dict):
                    b.pop("cache_control", None)


CACHE_1H = os.getenv("ASK_CACHE_1H", "1") == "1"
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
    cc = {"type": "ephemeral", "ttl": "1h"} if CACHE_1H else {"type": "ephemeral"}
    tdefs[-1] = {**tdefs[-1], "cache_control": cc}          # cache: tools + system (an hour: questions minutes apart reuse it)
    sysb = [{"type": "text", "text": system, "cache_control": cc}]
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
        cw = u.get("cache_creation") or {}
        w1h = cw.get("ephemeral_1h_input_tokens", 0) or 0
        usage["cache_write_1h"] = usage.get("cache_write_1h", 0) + w1h
        usage["cache_write"] += (u.get("cache_creation_input_tokens", 0) or 0) - w1h
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


VOICE_GEMINI = [m.strip() for m in os.getenv("ASK_VOICE_GEMINI_MODELS", "gemini-3.1-flash-lite,gemini-flash-latest,gemini-3.5-flash").split(",") if m.strip()]


def run_gemini(system: str, history: list[dict], user: str, tools: Lookups, log: list, post=_post, thinking: str | None = None,
               order: list[str] | None = None) -> tuple[str, dict]:
    """Free tier: a busy model (503/429) is skipped for 5 minutes and the next one answers at once (no waiting).
    order: which models to try first (voice uses the fastest: 3.5 Flash took 35-130 s on voice turns on Oct 2)."""
    err = None
    fast = (lambda u, h, b, timeout=45: _post(u, h, b, timeout, retry=False)) if post is _post else post
    pool = order or GEMINI_MODELS
    models = [m for m in pool if _COOL.get(m, 0) < time.time()] or pool[-1:]
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
        text, usage = _gemini_once(pool[0], system, history, user, tools, log, post, thinking)
        usage["model"] = pool[0]
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
    "gemini_voice": lambda *a, **k: run_gemini(*a, thinking="low", order=VOICE_GEMINI, **k),
    "haiku": lambda *a, **k: run_claude(*a, model=MODELS["haiku"]["model"], **k),
    "sonnet": lambda *a, **k: run_claude(*a, model=MODELS["sonnet"]["model"], **k),
    "opus": lambda *a, **k: run_claude(*a, model=MODELS["opus"]["model"], **k),
}
GUEST_BUDGET_USD = 0.50
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
                for k, default in (("breakdown", []), ("evidence", []), ("options", []), ("follow_ups", []), ("stage", ""), ("assumption", ""),
                                   ("next_action", None)):
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
        if getattr(self.j, "sandbox", False):                     # D5: each visitor gets $0.50 of Claude a day, then free Gemini
            budget = min(budget, GUEST_BUDGET_USD)
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
        text = self._take_next_step(thread, text)                    # "yes" to "Want me to pull up BTC?" runs that step
        quick = self._quick(who, text, thread, voice, source, context)
        if quick:
            return quick
        key, mode_label, note = self._pick(text, mode, provider)
        if mode_label == "auto" and key in ("haiku", "gemini", "gemini_voice", "local") and _telugu_talk(self.j, thread, text):
            key, note = "sonnet", "Auto: Claude Sonnet for a Telugu conversation (the lighter models mix in Hindi)"
        if voice and mode_label == "auto" and key == "haiku":   # talking: speed matters most; Sonnet answers in ~5 s, Haiku took 10-15 s
            key, note = "sonnet", "Auto: Claude Sonnet for voice (fastest to answer)"
        if voice and key in ("gemini", "gemini_deep") and "gemini_voice" in self.providers:
            key, note = "gemini_voice", (note + "; " if note else "") + "voice: the fastest Gemini first"
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
                key = "gemini_voice" if voice and "gemini_voice" in self.providers else "gemini"
                note = f"Claude budget for today (${sp['budget_usd']:.2f}) is used up, so Gemini answered"
        history = self._history(thread)
        tries = self._failed_clarifies(thread)
        now = int(self.j.now())
        uid = uuid.uuid4().hex[:12]
        self.j.db.execute("INSERT INTO ask_messages (id, thread, t, role, text, provider, mode) VALUES (?,?,?,?,?,?,?)",
                          (uid, thread, now, "user", text, key, ("eval:" if source == "eval" else "") + ("voice:" if voice else "") + mode_label))
        self.j.db.commit()
        notes = []
        # plan 4.3 / 6.1: the agent questions are answered from the agent's real state, never by moving the screen
        pre_log: list = []
        if AGENT_DOING.search(text):
            # the agent's real state goes in with the question (no extra lookup round, so it is also cheaper)
            try:
                from jarvis.service import watches as _w

                st = _w.state(self.j)
                notes.append("[This asks what you are doing or watching. Answer from YOUR STATE NOW (watches, positions monitored, what you wait "
                             "for, whether anything needs them). Do not move the screen. YOUR STATE NOW: "
                             + json.dumps({"lines": st.get("lines"), "watches": [{k: w.get(k) for k in ("coins", "kind_name", "mode", "state")}
                                                                                   for w in st.get("watches") or []], "needs_you": st.get("needs_you")}, default=str)[:3000] + "]")
                pre_log.append({"tool": "agent_state", "args": {}, "pre": True})
            except Exception:  # noqa: BLE001
                notes.append("[This asks what you are doing or watching: call agent_state (and my_watches) first and answer from it. Do not move the screen.]")
        elif SAFE_Q.search(text):
            notes.append("[This asks for something safer: call best_setup (it applies the person's risk comfort) and say which filter it used only if "
                         "filtered_out is in the result; otherwise say no setup was filtered.]")
        elif SINCE_Q.search(text):
            notes.append("[This asks what changed: call account_activity with hours back to the start of the person's day, and answer from it.]")
        if tries:
            notes.append(f"[conversation note: clarification has failed {tries} time(s) in a row]")
        if second_of:
            notes.append("[conversation note: the owner asked for a second opinion on this question; answer it independently from the data]")
        if voice:
            notes.append("[voice session: the 'answer' is SPOKEN aloud, so talk like a person on a call: the answer in the first sentence, at most "
                         "3 short sentences and about 40 words in total (a greeting counts). Rounded numbers, coin names not tickers, no codes, symbols, "
                         "lists or markdown (say 'percent', 'dollars', 'Bitcoin'); details go in 'breakdown' (shown on screen, not spoken). Keep the JSON "
                         "small so it arrives fast: breakdown at most 2 bullets, evidence at most 2 items, follow_ups at most 2. Only move the screen "
                         "(ui_go) when he asks to see something. Speech-to-text can mishear him: if a word makes no sense, use the most likely meaning "
                         "in context (e.g. 'Heather' = 'hey there', 'dough trade' = 'DOGE trade') and say it in passing]")
        if not str(who).startswith("guest:") and source != "eval":
            try:
                from jarvis.service import requests_log

                news = requests_log.news(self.j)
            except Exception:  # noqa: BLE001
                news = []
            if news:
                notes.append("[REPAIR SHOP NEWS he has not heard yet (mention once, briefly, at the end of your answer): "
                             + " | ".join(n["say"] for n in news) + "]")
        else:
            news = []
        if not voice and source != "eval":
            notes.append("[typed chat: the answer is READ, not heard, and the screen does NOT move by itself. Answer fully in text. You may still "
                         "add ui_go / points / a tour as a plan; the app shows a 'Show me on screen' button and only walks him through it, "
                         "with voice, if he taps it. So never write 'I opened', 'look at the highlighted', 'as you can see here': describe "
                         "where things are instead (e.g. 'on the Markets tab, under Zones')]")
        prev = self.j.db.execute("SELECT route FROM ask_messages WHERE thread=? AND role='assistant' AND route IS NOT NULL ORDER BY t DESC, rowid DESC LIMIT 1",
                                 (thread,)).fetchone()
        from jarvis.service import briefs as B

        tb = time.time()
        route_name = B.route(text, prev[0] if prev else None)
        brief = {}
        try:
            brief = B.briefs_for(self.j, route_name, guest=str(who).startswith("guest:"))
        except Exception as exc:  # noqa: BLE001  the brief is a shortcut, never a blocker
            brief = {"BRIEF_ERROR": str(exc)[:200]}
        brief_ms = int(1000 * (time.time() - tb))
        if not history:
            from datetime import datetime
            from zoneinfo import ZoneInfo

            from jarvis.service import account as _acc

            # their own local time (status check, Oct 8: Mahi said good evening and heard "Morning")
            _p = _acc.profile(self.j.db)
            tzname = _p.get("tz") or "America/Toronto"
            try:
                hr = datetime.fromtimestamp(now, ZoneInfo(tzname)).hour
            except Exception:  # noqa: BLE001
                tzname, hr = "America/Toronto", datetime.fromtimestamp(now, ZoneInfo("America/Toronto")).hour
            part = "morning" if 4 <= hr < 12 else "afternoon" if hr < 17 else "evening"
            hello = "sir" if not str(who).startswith("guest:") else (self.j.name_of(str(who)) or "them")
            notes.append(f"[this is the first message of a new conversation; it is {part} where they are ({tzname}): greet {hello} warmly "
                         "in a few words first; if they greet you with a time of day, follow theirs]")
        n_answers = sum(1 for h in history if h.get("role") == "assistant")
        if n_answers < NEXT_STEP_ANSWERS:
            notes.append(f"[NEXT STEP: this is answer {n_answers + 1} of this conversation. Add next_action: the one obvious next step that follows "
                         "from YOUR answer (open the thing you talked about, the deeper check, the related trade), with 'say' ending in 'Just say yes.' "
                         "And exactly 3 follow_ups: questions people usually ask next here. Every chip must be something you can answer or do.]")
        else:
            notes.append("[next_action only when there is an obvious next step; follow_ups: 2]")
        pnote = ""
        if not str(who).startswith("guest:"):
            try:
                from jarvis.service import people

                pnote = people.prompt_note(self.j, thread)
            except Exception:  # noqa: BLE001
                pnote = ""
        if pnote.startswith("[TALKING TO"):
            notes.append(pnote)                            # introduce mode: someone Madhav handed over to, not sir
        elif not str(who).startswith("guest:") and source != "eval":
            if pnote:
                notes.append(pnote)
            notes.append("[ADDRESS: you are talking with Madhav, the owner. Call him 'sir' (Madhav, 2026-10-08: always 'sir'); not 'Madhav'. "
                         "Only Madhav is 'sir'.]")
        if str(who).startswith("guest:"):
            try:
                gname = self.j.name_of(str(who))
            except Exception:  # noqa: BLE001
                gname = ""
            notes.append(f"[GUEST: this is {gname or 'a visitor'}, a friend of Madhav trying the app in practice mode. Call them {gname or 'nothing in particular'} "
                         "now and then (never 'sir', never Madhav). "
                         "Explain Madhav's system as 'Madhav's paper trading system'. Everything works for them as it does for Madhav: they can ask for "
                         "paper orders, alerts and mandate changes, and those go to THEIR OWN practice book (separate cash, never Madhav's books). "
                         "Say 'your practice book' for their manual book. The kill switch, autopilot and portfolio approvals are locked in practice mode.]")
            try:
                from jarvis.service import visitor

                vn = visitor.prompt_note(self.j, gname)
                if vn:
                    notes.append(vn)
            except Exception:  # noqa: BLE001
                pass
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
        log: list = list(pre_log)
        t0 = time.time()
        aid = uuid.uuid4().hex[:12]
        from jarvis.service import appmap as _amh
        _ht = _amh.here_target(here if context else None)
        used = key
        from jarvis.service.mandate import Mandate

        system = SYSTEM + _plain_words(self.j) + _status_block() + "\n\nOWNER'S MANDATE (current)\n" + Mandate(self.j.db, self.j.now).text()
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
                elif key in ("gemini", "gemini_voice") and "haiku" in self.providers and self.spend()["left_usd"] > 0.02 and os.getenv("ANTHROPIC_API_KEY"):
                    used = "haiku"
                    note = (note + "; " if note else "") + "Gemini was busy, so Claude Haiku answered"
                    log.clear()
                    L = Lookups(self.j, thread, _ht, str(who).startswith("guest:"))
                    raw, usage = self.providers["haiku"](system, history, user_msg, L, log)
                # Claude refused the call itself (no Anthropic credit left, overloaded, a bad key): free Gemini answers instead of nothing
                elif MODELS[used]["provider"] == "claude" and "gemini" in self.providers and not L.created:
                    why = ("no Anthropic credit left" if "credit balance" in str(exc).lower() else "Claude is unavailable right now")
                    used = "gemini_voice" if voice and "gemini_voice" in self.providers else "gemini"
                    note = (note + "; " if note else "") + f"{why}, so Gemini answered"
                    log.clear()
                    L = Lookups(self.j, thread, _ht, str(who).startswith("guest:"))
                    raw, usage = self.providers[used](system, history, user_msg, L, log)
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
        cost = round(cost_usd(used, usage) + getattr(L, "web_cost", 0.0), 5)
        if news and reply.get("kind") == "answer":
            try:
                from jarvis.service import requests_log

                requests_log.mark_told(self.j, [n["num"] for n in news])
            except Exception:  # noqa: BLE001
                pass
        if reply["kind"] == "clarify" and tries >= 2:
            reply = {**reply, "kind": "not_understood", "options": [],
                     "answer": "Sorry, I still don't understand what you're asking. Here are things I can answer:", "follow_ups": EXAMPLES[:3]}
        if reply["kind"] in ("clarify", "not_understood"):
            self.j.db.execute("INSERT INTO ask_misunderstood VALUES (?,?,?,?,?)", (now, thread, text, reply["kind"], used))
        ms = int(1000 * (time.time() - t0))
        reply["show"] = _clean_show(reply.get("show"))
        reply["actions"] = L.created
        _clean_next(reply)
        if str(who).startswith("guest:"):
            reply["answer"] = guest_address(reply.get("answer") or "")
        else:
            reply["answer"] = owner_address(reply.get("answer") or "")
        if source != "eval" and mode != "worker" and not str(who).startswith("guest:"):
            _self_flag(self.j, text, reply, log, thread)                 # "I don't have that" -> a numbered request, said once
        try:
            from jarvis.service import appmap as _am

            _here = context.get("here") if isinstance(context, dict) and "here" in context else (context if isinstance(context, dict) else None)
            reply["ui"], reply["answer"] = _am.keep_honest(self.j, text, reply.get("answer", ""), L.ui, _here)
            n_sent = len([x for x in re.split(r"(?<=[.!?])\s+", reply.get("answer") or "") if x.strip()])
            reply["points"], reply["ui"] = _am.plan_points(self.j, reply.get("points"), reply["ui"], _here, n_sent, text)
            reply["points"] = _am.anchor_points(reply["points"], reply.get("answer") or "")
            reply["points"] = _am.fill_list_points(reply["points"], reply.get("answer") or "")
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
                  "out_tokens": usage.get("out", 0), "in_fresh": usage.get("in", 0), "cache_read": usage.get("cache_read", 0),
                  "cache_write": usage.get("cache_write", 0) + usage.get("cache_write_1h", 0)}
        meta = {"model_label": MODELS[used]["label"], "mode": mode_label, "cost_usd": cost, "note": note, "second_of": second_of,
                "route": route_name, "timing": timing}
        self.j.db.execute("INSERT INTO ask_messages (id, thread, t, role, reply, provider, model, ms, tokens_in, tokens_out, tools, cost_usd, mode, note, route, timing) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                          (aid, thread, now + 1, "assistant", json.dumps({**reply, **meta}), used, model, ms,
                           usage.get("in", 0) + usage.get("cache_read", 0) + usage.get("cache_write", 0) + usage.get("cache_write_1h", 0), usage.get("out", 0), json.dumps(log), cost, mode_label, note,
                           route_name, json.dumps(timing)))
        self.j.db.commit()
        _log_chips(self.j, thread, aid, reply)
        self.j.audit(who, "ask", text[:200], f"{used} {reply['kind']} {ms}ms ${cost:.4f}")
        if voice:
            reply["speak"] = speak_text(reply)                       # what is said aloud (the full answer stays on screen)
        vid = _pre_voice(context, reply.get("speak") or reply.get("answer"))
        if vid:
            reply["voice_id"] = vid                                  # its audio is already being made: the phone fetches it directly
        return {"id": aid, "thread": thread, "provider": used, "model": model, "ms": ms, "lookups": [x["tool"] for x in log], **reply, **meta}

    def _take_next_step(self, thread: str, text: str) -> str:
        """'Yes' right after an offered next step runs that step; a question that matches a chip just shown marks it picked."""
        try:
            _chip_table(self.j)
            row = self.j.db.execute("SELECT id, reply, t FROM ask_messages WHERE thread=? AND role='assistant' AND reply IS NOT NULL "
                                    "ORDER BY t DESC, rowid DESC LIMIT 1", (thread,)).fetchone()
            if not row:
                return text
            rid, prev, t = row[0], json.loads(row[1] or "{}"), row[2]
            na = prev.get("next_action") if isinstance(prev.get("next_action"), dict) else None
            if WHY.match(text) and int(self.j.now()) - int(t or 0) <= 1800:      # plan 4.2: a one-word "why" explains the last answer
                said = re.split(r"(?<=[.!?])\s+", str(prev.get("answer") or ""))[0][:300]
                card = prev.get("card") if isinstance(prev.get("card"), dict) else None
                return ("Why? Explain the reasoning behind your last answer" + (f" (\"{said}\")" if said else "") + ": what you found, why, "
                        "what would make it wrong, and what you are doing about it; name the decision-chain gates it passed or failed, from the chain "
                        "lookup, in plain words." + (f" Its decision card: {json.dumps(card)[:600]}" if card else ""))
            if na and YES.match(text) and int(self.j.now()) - int(t or 0) <= 600:
                self.j.db.execute("UPDATE ask_chips SET picked=1 WHERE reply_id=? AND kind='primary'", (rid,))
                self.j.db.commit()
                return na["ask"]
            self.j.db.execute("UPDATE ask_chips SET picked=1 WHERE reply_id=? AND lower(ask)=lower(?)", (rid, text.strip()))
            self.j.db.commit()
        except Exception:  # noqa: BLE001
            pass
        return text

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
            return {"ui": [], "say": "You're welcome, sir." if not getattr(self.j, "sandbox", False) else "You're welcome."}
        if OKAY.match(t):
            if self._last_spoken(thread).strip().endswith("?") and not re.search(r"stop|cancel|never ?mind|that'?s all|that is all", t, re.I):
                return None                                    # "okay" to my question ("Want the details?") is a yes: the model answers
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
        if str(who).startswith("guest:"):                      # a friend testing the app is not Madhav
            fix = lambda t: (t or "").replace("Sure, Madhav. ", "Sure. ").replace(", Madhav", "").replace("Madhav's", "the owner's").replace("Madhav", "the owner")   # noqa: E731
            q = {**q, "say": fix(q.get("say")), "tour": [{**st, "say": fix(st.get("say"))} for st in (q.get("tour") or [])] or None}
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

    def _last_spoken(self, thread: str | None) -> str:
        if not thread:
            return ""
        row = self.j.db.execute("SELECT reply FROM ask_messages WHERE thread=? AND role='assistant' AND reply IS NOT NULL ORDER BY t DESC, rowid DESC LIMIT 1",
                                (thread,)).fetchone()
        r = json.loads(row[0]) if row and row[0] else {}
        return str(r.get("speak") or r.get("answer") or "")

    def voice_turn(self, who: str, audio_b64: str, mime: str, thread: str | None, mode: str | None, context: dict | None, source: str = "",
                   prefix: str = "") -> dict:
        heard = self.transcribe(audio_b64, mime)
        if not heard:
            return {"heard": "", "thread": thread, "error": "I didn't catch any words. Try again a little closer to the phone."}
        if WHY.match(heard):                                   # plan 4.2: "why?" on its own is a full question (it explains the last answer)
            out = self.ask(who, heard, thread=thread, mode=mode, context=context, voice=True, source=source)
            return {"heard": heard, **out}
        chip = spoken_chip(heard, (context or {}).get("chips"))  # plan 3.7: saying a chip's words is the same as tapping it
        if chip:
            out = self.ask(who, chip, thread=thread, mode=mode, context=context, voice=True, source=source)
            return {"heard": heard, "chip": chip, **out}
        last = self._last_spoken(thread)
        kind = hearing_check(heard, last)                      # what reaches the model is a real question (Oct 1-3: 1 turn in 6 was not)
        if kind == "echo":
            return {"heard": "", "thread": thread, "ignored": "echo"}
        if kind == "filler":
            return {"heard": heard, "thread": thread, "ignored": "filler"}
        if prefix and len(prefix) < 300:
            heard = f"{prefix.strip()} {heard}".strip()
        if kind == "partial" and len(heard.split()) < 14:
            return {"heard": heard, "thread": thread, "partial": True}
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
            out.append({"thread": th, "title": _title(first[0] if first else ""), "time": views._local(t1), "messages": cnt, "t": t1,
                        "voice": bool(first and (first[1] or "").startswith("voice:"))})
        return out

    def delete_thread(self, thread: str) -> dict:
        """D10: a visitor's deleted conversation is gone for good; Madhav's goes to an archive kept 30 days."""
        db = self.j.db
        if not getattr(self.j, "sandbox", False):
            db.execute("CREATE TABLE IF NOT EXISTS ask_archive AS SELECT *, 0 AS archived_t FROM ask_messages WHERE 0")
            cols = [r[1] for r in db.execute("PRAGMA table_info(ask_messages)")]
            db.execute(f"INSERT INTO ask_archive ({', '.join(cols)}, archived_t) SELECT {', '.join(cols)}, ? FROM ask_messages WHERE thread=?",
                       (int(self.j.now()), thread))
            db.execute("DELETE FROM ask_archive WHERE archived_t < ?", (int(self.j.now()) - 30 * 86400,))
        n = db.execute("DELETE FROM ask_messages WHERE thread=?", (thread,)).rowcount
        db.commit()
        return {"deleted": n, "archived": not getattr(self.j, "sandbox", False)}

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
