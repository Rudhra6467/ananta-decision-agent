# Knowledge index: the map of Ananta's brain

Ananta reads this map first, then opens only the documents a question needs (the `read_doc` lookup), so answers come from
the right source without loading everything. One line per document: what it holds and when to open it.
A test keeps this map complete: every document in these folders must have a line here.

Evidence classes, strongest first: **verified variables** (Ananta's own tests) > **casebook** (Madhav's real trades) >
**hypotheses** (teacher ideas, labelled with their test status) > **notes** (Madhav's own notes, opinions until tested).

## How Ananta is built
- `SYSTEM_MAP.md`: the whole system in plain words: what runs (Hands, Explorer, hourly watch, trend portfolio, Jarvis, voice), which database each part keeps, our paper books by name, the flow scan > setup > tracking > performance > repair shop > evidence use, what Ananta can do / prepare / cannot do, the requests loop, and the proposed next steps (evidence books per watch, watch registry, the eye). Open for "how is it built", "where does X live", "what happens after a setup fires", "what can you do".

## How Ananta reasons
- `knowledge/FRAMEWORK.md`: Madhav's framework: decision chain Regime > Location > Trigger > Invalidation > Risk > Exposure, fail-closed, structural stops, signals as evidence, how to talk (simple first). Open for any "why no trade / how do you decide" question.
- `knowledge/PLAYBOOK.md`: how Ananta reacts: the order of questions (data, market allowed, zone, plan, evidence, simple answer) and what to do when a coin enters a zone, a zone breaks or holds, your setup shows, or Madhav asks 'should I buy'. Open for 'what should we do now'.
- `knowledge/layers.json`: the layer map: every part of Ananta in 9 layers (0 Madhav and safety ... 8 interface) with status, whether it may act, what it rests on and feeds, and the known gaps. Open for "how do the parts connect".
- `knowledge/hypotheses.json`: every teacher idea (H01-H18) and policy (P01-P03) with its source, test status and what our data said. Open for "is X true / does X work".
- `VARIABLE_REGISTRY.md`: variables Ananta tested itself (KEEP / WATCH / DROP / UNTESTED), the strongest evidence class. Open for "what do we know for sure".
- `knowledge/READS.md`: Madhav's three buy setups (capitulation at the lows, higher-low retest, quiet base) as live reads, and what history said about each.
- `knowledge/reads_status.json`: the review #5 numbers and status for every read variant (the app shows these).

## Madhav's own trades
- `casebook/cases.json`: his SOL buys C1-C4 (prices, dates, his reasons, lots) and lesson L1 (Yes Bank: check news before buying).
- `casebook/REBUILD_2026-10-03.md`: each buy rebuilt from candles: what he saw, what Ananta did at the same moment, what happened after, the base story and the news-check results.

## Teachers (source-derived hypotheses, never rules)
- `knowledge/teachers/trade_with_trend.md`: Raunak (Trade With Trend): regime, stage analysis, relative strength, bases, pullbacks, breadth, risk.
- `knowledge/teachers/rayner_teo.md`: Rayner Teo: execution, trend following, pullbacks, breakouts, stops and sizing, and what was tested on our coins.

## The Explorer (paper trading engine)
- `RULEBOOK_V0.md`: every Explorer rule with its ID (setups, entries, exits, guards). Open for "why did it buy/sell".
- `research/EXPLORER_V0_SCORECARD.md`: history replay of rulebook v0, 2017-July 2026, vs random entries.
- `SCOREBOARD.md`: strategy scoreboard summary.
- `PAPER_LAB_LOCK.md`: paper lab rules ($1000 book, limits).
- `RISK_PROFILES_LOCK.md`: SAFE / MODERATE / AGGRESSIVE profiles.

## Repair shop (changes tested before they go in)
- `repair_shop/REVIEW_1.md`, `repair_shop/REVIEW_1_RESULTS.md`: rule changes v0.2: none passed, rulebook v0 stays.
- `repair_shop/REVIEW_2.md`, `repair_shop/REVIEW_2_RESULTS.md`: learning from 37 other traders' 7,441 trades.
- `repair_shop/REVIEW_3.md`, `repair_shop/REVIEW_3_RESULTS.md`: "buy weakness" variants: all lost after costs.
- `repair_shop/REVIEW_4.md`, `repair_shop/REVIEW_4_RESULTS.md`: portfolio trend exposure with crash protection: T3 passed.
- `repair_shop/REVIEW_5.md`, `repair_shop/REVIEW_5_RESULTS.md`: Madhav's reads (capitulation, higher-low retest, quiet base): they caught all four of his buys, but none beat a random day on its own in 2018-2023.
- `repair_shop/REVIEW_8.md`, `repair_shop/REVIEW_8_RESULTS.md`: your setups again with zones and the market gate: no pass; the higher-low retest with the market allowed is the most promising (11 of 12 up after 30 days, +20%) but one event short of the bar.
- `repair_shop/REVIEW_9.md`, `repair_shop/REVIEW_9_RESULTS.md`: the Explorer's entries split by zone and market: zones do not rescue its hours-long trades; the market gate helps but they still lose.

## Research studies (pre-registered, then results)
- `research/ENTRY_STUDY_V2.md`, `research/ENTRY_STUDY_V2_RESULTS.md`: 4h/1d setups with 5m timing: 0 of 36 passed.
- `research/MTF_ENTRY_STUDY_V1.md`, `research/MTF_ENTRY_STUDY_V1_RESULTS.md`: multi-timeframe entries: 0 of 108 passed.
- `research/GREEN_RUNS_STUDY_V1.md`, `research/GREEN_RUNS_STUDY_V1_RESULTS.md`: what follows runs of green candles.
- `research/CANDIDATE_V3.md`, `research/CANDIDATE_V3_HOLDOUT_RESULT.md`: frozen trend-dip candidate: failed the one-time holdout.
- `research/STUDY_V3_FRESH.md`, `research/STUDY_V3_FRESH_RESULTS.md`: regime-adaptive exits on 10 fresh coins.
- `research/STUDY_V4.md`, `research/STUDY_V4_RESULTS.md`: BTC market filter on fresh set #2: no variant passed.

## Plans
- `BACKLOG.md`: everything still to do, in priority order (layers, zones, untested ideas, path to live). Open for 'what's next / what's pending'.
- `research/ZONES_PROGRAM.md`: what a zone is, zone strength and states, review #6 pre-registration, and the list of studies to redo with zones.
- `research/REVIEW_6_RESULTS.md`, `research/zones_status.json`: do zones hold? A little more often than random bands; the 200-day average, overlapping zones and new swing zones pass; entering a zone is not a trade by itself.
- `research/REVIEW_7_RESULTS.md`, `research/lookout_status.json`: the lookout: inside a support zone, only the market regime (BTC above its 50-day) separated held from broken (68% vs 50%); wicks, closes back above, volume, divergence and relative strength added nothing beyond arithmetic.
- `research/REVIEW_10.md`, `research/REVIEW_10_RESULTS.md`: exits at zones: selling at the next zone cut the winners; gains come from a few big moves, so the stop goes beyond the zone and the next zone is a review point, not a target.
- `research/REVIEW_11.md`, `research/REVIEW_11_RESULTS.md`: teacher ideas as zones: a dip into the 50-day zone did worse than an average uptrend day; breakouts through zones on volume were positive in both periods but not reliable; the market regime does the work.
- `research/REVIEW_12.md`, `research/REVIEW_12_RESULTS.md`: T3's exit vs trailing stops: looser exits won big in 2018-23 and lost in 2024-26; T3's 20-day exit survives both.
- `research/REVIEW_13.md`, `research/REVIEW_13_RESULTS.md`: the remaining teacher ideas: H07's short RSI dip trade promising (+4% per trade, 70% wins, both periods); first pullback, false break, book stop add nothing; breadth too few samples.
- `research/REVIEW_14.md`, `research/REVIEW_14_RESULTS.md`: the short dip trade (H07) beat ordinary uptrend days traded the same way in both periods (+3.9%, +5.6% per trade, about 70% wins), a few events short of the bar; the most consistent result so far.

## Safety and operations
- `GUEST_GUIDE.md`: a guide for a friend trying the app: how to open it, the tabs, the coins, first questions, the rule gates, making a paper trade, what practice mode locks.
- `RUNBOOK_SAFETY.md`: stop, flatten, roll back, resume (copy-paste commands).
- `SAFETY_GATES_LOCK.md`: safety gates that live outside the AI.
- `JARVIS_TEST_PLAN.md`: how Jarvis / Ask Ananta is tested (automatic suite + hands-on checks).
- `LOCAL_LOOP.md`: running the agent locally without the website.

## Project history and locks (background; rarely needed in answers)
- `README.md`: list of lab documents.
- `ROADMAP.md`, `NORTH_STAR_LOCK.md`, `LABORATORY_CHARTER.md`: goals, roadmap, lab charter.
- `AGENT_CONTRACT_V0.md`: what the Agent (brain) may ask the App (hands).
- `MARKET_TRUTH_LOCK.md`, `STAGE4_REPLAY_LOCK.md`, `LIVE_VS_HISTORICAL_COMPARE.md`: evidence engine, replay and live-vs-history comparison.
- `DECISION_INTELLIGENCE_LOCK.md`, `DECISION_QUALITY_V0.md`, `S5_HYPOTHESES.md`: decision quality baseline and early hypotheses.
- `OPPORTUNITY_ENGINE_LOCK.md`, `STRATEGY_EVIDENCE_ENGINE.md`, `STRATEGY_INTEL_AUDIT.md`, `STRATEGY_UNIVERSE_V1.md`: strategy research design (August 2026).
- `FEATURE_COMPLETE_NOW.md`, `BLUEPRINT_V2.2_AMENDMENT.md`, `TRADINGAGENTS_REFERENCE_AUDIT.md`: older design notes.

## Madhav's notes (optional)
- Notes Madhav writes himself (for example in Obsidian) in the folder `ANANTA_NOTES_DIR` (default `~/AnantaBrain/My notes`). Ananta searches them too and quotes them as "your note", never as verified fact.
