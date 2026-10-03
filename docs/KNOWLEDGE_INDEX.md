# Knowledge index: the map of Ananta's brain

Ananta reads this map first, then opens only the documents a question needs (the `read_doc` lookup), so answers come from
the right source without loading everything. One line per document: what it holds and when to open it.
A test keeps this map complete: every document in these folders must have a line here.

Evidence classes, strongest first: **verified variables** (Ananta's own tests) > **casebook** (Madhav's real trades) >
**hypotheses** (teacher ideas, labelled with their test status) > **notes** (Madhav's own notes, opinions until tested).

## How Ananta reasons
- `knowledge/FRAMEWORK.md`: Madhav's framework: decision chain Regime > Location > Trigger > Invalidation > Risk > Exposure, fail-closed, structural stops, signals as evidence, how to talk (simple first). Open for any "why no trade / how do you decide" question.
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

## Safety and operations
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
