# Research audit v2 (2026-10-15): every analysis, with its final status

Audit v1 (`audit_v1.json`, frozen 2026-10-05, 165 rows) rated the basic-lab and Claude-era analyses. It had no rows for the Grok-era research of September 2026 or for reviews #16-#30. On 2026-10-14 and 2026-10-15 the whole record was audited again, one card for each idea, study, file or build, and each card got a 'Do now' verdict. This page closes every one of them: **398 cards and reconstruction items, and 43 follow-up doubts**, each with a final word, the evidence for it, and a pointer to whatever still has an owner.

It is written from `docs/knowledge/audit_register.json`, so the two cannot disagree; `tests/test_audit_register.py` checks that every row is here, that every pointer exists and that nothing is left open. Neither `audit_v1.json` nor the Grok-era files are edited: corrections to v1 are in section 3 and corrections to Grok-era files are in `GROK_ERA_ERRATA.md`. The live status of a strategy, card or hypothesis is in `docs/knowledge/strategy_status.json`, `status_cards.json` and `hypotheses.json`. What is still owed, and when, is in `docs/knowledge/due_list.json` and `docs/LOCK.md`.

## 1. How to read the words

The card audit used five verdict words; v1 used five different ones. They map like this:

| Card verdict | Closest v1 word | Meaning |
|---|---|---|
| RETIRE | DUMP | Stop using it. Keep the record and the lesson. |
| PARK | UNTESTED | Set aside. Not proven bad, not in use. |
| RE-TEST | RE-TEST | Worth one more look under a written pass rule. |
| KEEP | KEEP or CONTEXT | Still true or useful, as the record or as context. |
| MODIFY | KEEP with a stated fix | Keep it, but change what the card says to change. |

Every card also ends with one **final status**:

| Status | Meaning |
|---|---|
| `DONE` | The action was carried out. The evidence names the commit or file, and a test pins it where one could. |
| `RECORDED` | A standing decision; nothing is owed. The verdict is the record, or the rule is already written in RESEARCH_RULES.md or another document. |
| `ERRATA` | What needs correcting lives in frozen Grok-era files that are never edited. The correction is an entry in docs/research/GROK_ERA_ERRATA.md. |
| `SCHEDULED` | Owned by a dated or recurring step on the due list (docs/knowledge/due_list.json): nightly, weekly, monthly, quarterly, a checkpoint or a ledger question. |
| `PARKED_WINDOW` | New research, a re-test or a build. Rule B and the sealed holdout say it waits until after the 60-market-day evidence window, so it is on the post-window list. |
| `OWNER_DECISION` | Only Madhav can decide (spending, retiring or resuming a book, changing a rule). It is on the due list with its options and a recommendation. |
| `SUPERSEDED` | Later work replaced the item. The refs name what replaced it. |
| `ALREADY_FIXED` | Used for the follow-up doubts only: the problem was real but an earlier change had already fixed it. |

## 2. Where things stand

| Status | Rows |
|---|---|
| `DONE` | 60 |
| `RECORDED` | 267 |
| `ERRATA` | 16 |
| `SCHEDULED` | 18 |
| `PARKED_WINDOW` | 30 |
| `OWNER_DECISION` | 2 |
| `SUPERSEDED` | 5 |
| **All rows** | **398** |

By card verdict: RETIRE 152, KEEP 144, PARK 46, MODIFY 29, RE-TEST 12, none 15. ('none' marks the reconstruction items and one descriptive card.)

| Group | Rows | `DONE` | `RECORDED` | `ERRATA` | `SCHEDULED` | `PARKED_WINDOW` | `OWNER_DECISION` | `SUPERSEDED` |
|---|---|---|---|---|---|---|---|---|
| Basic lab and the old app (cards-1) | 54 | 3 | 46 | 0 | 1 | 4 | 0 | 0 |
| Grok era: relationships H1-H6 and the first lab (cards-2) | 34 | 0 | 27 | 3 | 1 | 3 | 0 | 0 |
| Grok era: the SET campaigns, PD cards and S2 logs (cards-3) | 33 | 1 | 24 | 6 | 0 | 2 | 0 | 0 |
| Grok era: market states, MRD and the agent packs (cards-4) | 40 | 0 | 28 | 6 | 0 | 4 | 0 | 2 |
| Grok era: N3/N4, the fade, exit maps and the 5-minute record (cards-5) | 17 | 4 | 12 | 1 | 0 | 0 | 0 | 0 |
| Claude era, first studies and the Explorer (cards-6) | 59 | 1 | 54 | 0 | 4 | 0 | 0 | 0 |
| Claude era: zones, reads, teachers and hypotheses (cards-7) | 72 | 14 | 41 | 0 | 7 | 7 | 1 | 2 |
| Claude era: the lake, reviews #15-#30 and the queue (cards-8) | 43 | 14 | 22 | 0 | 2 | 4 | 0 | 1 |
| Claude era: the $500 book, the engine and the evidence record (cards-9) | 32 | 16 | 10 | 0 | 2 | 3 | 1 | 0 |
| Reconstruction fixes (the 11 fixes, P10 and bugs 4-5) | 14 | 7 | 3 | 0 | 1 | 3 | 0 | 0 |

Nothing in the register is open. What is left is owned: the `SCHEDULED` rows run by themselves on the due list, the `PARKED_WINDOW` rows are on the post-window list in `docs/LOCK.md`, and the `OWNER_DECISION` rows wait for Madhav, each with its options on the due list.

## 3. Corrections to v1 rows

`audit_v1.json` stays as it was frozen. These are the places where a v1 row says something that is no longer true, or never was.

| Row | What v1 says | What is true |
|---|---|---|
| `STRAT:HUNTER` | v1 says 'live 5 closed -$1.93'. | Live paper 2026-09-29 to 10-09 (paper_book.sqlite): 19 closed, 3 won, -$29.58. That is 18 counted trades (-$28.73) plus one trade from before a fix (-$0.85) that is kept out of the evidence. Parked by Madhav on Oct 11 (decision D6). |
| `STRAT:SQUEEZE` | v1 says 'no live fires yet'. | 3 live paper trades, all lost (-$2.93). Parked on Oct 11 (D6). The watch text was already corrected in acdd3fd. |
| `R15` | v1 says 'Not run yet (pre-registration only)' with status PRE-REGISTERED. | It ran on 2026-10-04 (REVIEW_15_RESULTS.md). T3 and H07 pass on the 30 most-traded coins but not on all 120; M2a and M3a fail on every tier; M2a-G fails on the wider tiers; M1a's pass on 120 coins sits on the bar (10 events, t 1.51 against 1.5; 3 confirm events). Nothing was promoted automatically. |
| `H:H14` | v1 (a frozen snapshot) says UNVERIFIED. | hypotheses.json says SUPPORTED. Review #18 (2026-10-05, every tier): a stop 1 ATR under the 10-day low beat a 3% stop on dip trades in both periods. Review #27 later found that for the dip trade no stop with a 10-day time exit beat both, so a stop applies only where one is required. |
| `SETUP:E5 / Q3` | v1 rates E5 DUMP; the card said 'on probation until 20 live trades (Q3)'; the ledger said WAITING. | Q3 left the queue in 7ef1188 (ledger TK17): E5's probation ended on 2026-10-15 when the Explorer was retired as a trading book. The status card, the ledger and this register now agree. |
| `STRAT:T3-B` | v1's T3-B row does not carry the survivorship checks (reviews #22 and #30). | Review #22 (point-in-time top 30): 2024-Jul 2026 T3-B -22.5% against holding -76.0%, and it fell about half as far; it fails T3's rule there. Review #30 (point-in-time top 10, the coins the books can trade): T3-B +3.7% against holding -31.9% (worst fall 39.0% vs 68.5%); it passes. On today's top 10 the same period showed +15.1%, so the old figure was survivorship-flattered. Read T3-B as 'lose much less in slides, make a little', never as an edge. |
| `STUDY:HL_RX` | v1 says the result is 'NO_SNAPSHOT_AT_T / 57 insufficient, 5 detected' and cites the owner's notes. | Camera result from the Status document of 2026-09-27: window 2026-09-22 to 09-25, 2,079 fills, 1,593 episodes, 62 eligible events, all NO_SNAPSHOT_AT_T, 0 matched. The 57 insufficient / 5 detected figures come from a later sandbox replay known only from the owner's notes; it was never compared with the live Hands engine. The full record is docs/research/HL_RX_RESULT.md. |
| `V07 and STUDY:INTRADAY_ATLAS` | v1 lists the V07 cell as '+0.17% / +0.07%'. | The atlas reads the other way round: +0.07% in discovery and +0.17% in confirm (3% target, 1.5% stop, 24h), and -0.91% / -0.86% after costs. VARIABLE_REGISTRY.md and variable_registry.json are corrected; audit_v1.json lines stay frozen. |
| `The v1 counts` | AUDIT_V1.md said 164 rows (KEEP 16, RE-TEST 15, CONTEXT 23, UNTESTED 8, DUMP 102). | The frozen JSON has 165 rows: KEEP 22, RE-TEST 5, CONTEXT 28, UNTESTED 3, DUMP 107 (STRAT:T3-B was added in 614ac5b). |

### The 27 rows that shared one reason

In v1, 27 rows carry the same reason: *"August legacy lab: 1-hour horizon, no written pass rule, superseded by the daily-horizon program"*. That is true of most of them but it explains none of them, and it is wrong for the one July row. Here is each row's own reason, taken from its own result.

| v1 row | What it was | Why it is out (from its own result) |
|---|---|---|
| `EXP-001` | Donchian breakout in an uptrend vs sitting out (1h) | It hurt AVAX, LINK, ARB and RENDER, was a wash on ETH, SOL, XRP, AAVE and PAXG, and was thin on BTC. Closed: do not promote. |
| `EXP-002` | Bollinger in a compression vs sitting out (1h) | A wash wherever the books were adequate, and no live take. Closed: do not promote. |
| `EXP-003` | Hunter in uptrend takes under Wave A | Hunter took no trade in an uptrend on the history books or live (0 takes). Closed: do not enable. |
| `EXP-004` | BTC 15-minute year check | It could not be run as a year: the data covered 15.5 days (161 rows). Result: NOT_A_YEAR. |
| `EXP-005` | ATR breakout in an uptrend vs sitting out (1h) | It hurt AAVE and RENDER only. Closed: do not kill the family, do not promote. |
| `EXP-006` | Health-sweep roster vs the observation families | The sweep's roster did not match the agent's books (ROSTER_MISMATCH). Closed: do not ingest it as configuration. |
| `EXP-007` | HAVE-window phase mix | It counted the window's phases: 1,878 of 2,514 were in the drawdown phase. A description of the data, not a result about any trade. |
| `EXP-008` | BTC 1h take vs skip by phase | In drawdowns, taking Bollinger lost 0.07 against +0.07 for skipping; no take reached the peak phase. Closed: do not promote. |
| `EXP-009` | ETH 1h phase slice | BTC's ranking did not carry over to ETH (Bollinger drawdown take +0.19 vs skip -0.05; Donchian drawdown take hurt). Conditional boards only. |
| `EXP-010` | Donchian lookback sweep (reserved) | Never run: it was reserved until the lab honoured the entry-lookback setting. |
| `EXP-011` | SOL 1h phase slice | Breakouts hurt in drawdowns (Donchian drawdown take n=18, +1h -0.09% vs skip +0.12%; lead-in n=12, -0.35% vs +0.34%; Bollinger drawdown n=44, -0.12% vs +0.06%). Its one lesson is repeated by later daily-horizon tests. |
| `H:S5-H1` | S5-H1 Hunter uptrend filter contradiction | Contradiction confirmed; the live enable was refused by the human lock on 2026-08-25. Hunter took 0 uptrend trades. |
| `H:S5-H2` | S5-H2 Hunter reversal silence (gate histogram) | Approved as a measurement only. The tool prints and saves nothing, so there are no H2 numbers (ROADMAP.md now says so). |
| `H:S5-H3` | S5-H3 take-equivalent split by strategy | The +1h mean after a take-equivalent (-0.056%) was almost all Bollinger; the per-strategy split is now reported. An attribution measurement, not a trade rule. |
| `H:S5-H4` | S5-H4 Squeeze scarcity | Working as designed; no experiment was run. |
| `H:S5-H5` | S5-H5 audit clock (regime misclassified) | Proposed only ('optional, after H2/H3'); never run. |
| `STUDY:S3_LIVE_AUDIT` | S3 regime and decision audit of live observations | 43 observations: 0 takes (19 skip, 24 wait). It suggested the market label may lag overnight changes. Evidence, not a verdict. |
| `STUDY:APP_RECOMMENDED_MATRIX` | The Ananta app's own Recommended Matrix (pre-agent, July) | Not an August lab result: it is the July app's matrix, written before the agent existed, so the blanket reason cannot apply. It benched all three Wave A strategies (Hunter no material trades, Squeeze 0% win, Bollinger negative in every regime). Kept as history. |
| `STUDY:BTC_ETH_CELL_COMPARE` | BTC vs ETH cell compare (git only) | Only a commit message survives ('Finding, not KEEP'); no numbers were saved. |
| `STUDY:DQ_V0` | Decision-quality meter v0.0/v0.1 baseline | No live take on any strategy. Hunter skips: +1h +0.00% (wash), +4h -0.26% (slight protective). The Sep 1 re-run found +4h a wash too (note added to DECISION_QUALITY_V0.md). Readiness not earned. |
| `STUDY:FINDINGS_GRID` | Findings card v0.8 / knowledge grid (10 one-hour books) | SUITABLE=0: nothing qualified. Donchian in uptrends hurt AVAX, LINK, ARB, RENDER; ATR hurt AAVE, RENDER; Hunter took nothing on all 10. Archived. |
| `STUDY:I2_HIST_BASELINE` | I2 history breakout baseline (Donchian, ATR, Keltner shadows) | A baseline that was scored on history and locked; it fed EXP-001 and EXP-005. Infrastructure for those tests, not a result. |
| `STUDY:LAB_COMPARE` | Live vs historical observation compare (S4 replay) | Live: 0 takes. History: 55 take-equivalents (47 Bollinger); Hunter had 108 setups and 104 were filtered. Reviewed as evidence, not a verdict. |
| `STUDY:SETUP_MEMORY` | Setup memory v0 and market-state fingerprints | Infrastructure and cross-tabs with no numeric result recorded ('n=7 take-equivalents is still anecdote'). Archived. |
| `STUDY:UNIVERSE_V1` | Strategy Research Universe v1 (strategy x asset x timeframe x regime cells) | A scaffold; its findings card says SUITABLE=0. |
| `STUDY:WAVE_A` | Wave A live paper lab (Hunter, Squeeze, Bollinger) | All three stayed on WATCH with 0 paper take marks; the Strategy Intel Audit said partly (operations) and no (ranking the full universe). The lab was archived. |
| `STUDY:WAVE_A_1Y_BACKTEST` | Wave A one-year app backtest | The roadmap records 'done (mixed symbol results; not KEEP)'. No numbers were kept in the documents. |

## 4. The register, group by group

Columns: the card's key, what it is, the card verdict, what the card said to do, and where it stands now. The same rows, with their full evidence, are in `docs/knowledge/audit_register.json`.

### Basic lab and the old app (cards-1)

Rated in v1 as well; this is the final status of each. 54 rows.

| Row | What | Verdict | Standing | Now |
|---|---|---|---|---|
| `cards-1:APP-GRAD` | Graduation Readiness scorecard (old app) | KEEP | KEEP as a template. Next step: turn the 10 gates into code and run them unchanged on the SD6 book at 50… | DONE: d0c45bc jarvis/service/graduation.py: ten gates, thresholds and expectancy identical to old app analytics.graduation_readiness; THRESHOLD_LOG; wired… |
| `cards-1:APP-SANDBOX` | Strategy Sandbox and Strategy Research Laboratory (old app) | RETIRE | RETIRE the sandbox (superseded by the backtester and later labs); keep only the habit of shadow-testing… | Recorded. Nothing owed. |
| `cards-1:APP-LABMACH` | Research Lab machinery: backtester, walk-forward, sensitivity, deep history, ap… | KEEP | KEEP the design rules (next-bar entry, pessimistic exits, costs in) as the checklist for any new engine. | RECORDED: 3505615 docs/research/RESEARCH_RULES.md section 5 'Costs': 'Before testing any new exchange, replace the cost default with that venue's schedule and state the date it… |
| `cards-1:APP-LIBRARY` | Strategy Library "from the market" with placeholder results (old app) | RETIRE | RETIRE the placeholder numbers (never cite them). | PARKED_WINDOW (`PW-LIBRARY`): Rule B: re-tests wait. Post-window list item: the 13 outside ideas (ema-cross ... time-series-momentum); each pass rule written in its own pre-registration… |
| `cards-1:APP-DEEP` | Deep Strategy Analysis of Hunter, Squeeze and Continuation (old app) | RETIRE | RETIRE as a result (exits were rewritten later); KEEP the habit of reporting capture and exit-by-exit results. | Recorded. Nothing owed. |
| `cards-1:APP-SWEEP` | Optimization sweep and the Squeeze paper deploy (old app) | RETIRE | RETIRE the claim "Squeeze is profitable". | Recorded. Nothing owed. |
| `cards-1:STUDY:APP_RECOMMENDED_MATRIX` | The app's Recommended Matrix (which strategy may trade in which market state) | PARK | PARK as history. The audit's blanket reason text ("August legacy lab...") does not fit this July item. | Recorded. Nothing owed. |
| `cards-1:APP-REGVAL` | Regime-enforcement re-validation (old app) | KEEP | KEEP as the baseline for any new cost model; next step: re-run on the daily horizon with NDAX-type costs. | PARKED_WINDOW (`PW-LIBRARY`): Rule B: a re-test of old strategies waits for the window. |
| `cards-1:AGT-V1` | Multi-agent V1 and the first regime detection | RETIRE | RETIRE (already archived). | Recorded. Nothing owed. |
| `cards-1:AGT-MEM` | Decision memory and "learning from outcomes" | RETIRE | RETIRE the nudge rule. Keep the idea only when a mark is tied to a measured forward return. | Recorded. Nothing owed. |
| `cards-1:AGT-RANK` | Ranking, WAIT logic, portfolio awareness and cleanup | RETIRE | RETIRE; the position-limit idea lives on in the paper book rules. | Recorded. Nothing owed. |
| `cards-1:AGT-PAPER` | Paper execution, cycle ledger and opportunity ledger | RETIRE | RETIRE the legacy ledger files (archived). | Recorded. Nothing owed. |
| `cards-1:LAB-CHARTER` | Laboratory Charter, Scoreboard and Journal | MODIFY | MODIFY: keep the human gate and "no auto-KEEP"; replace day-count promotion with a written pass rule… | DONE: LABORATORY_CHARTER.md section 11 changelog now carries the 2026-10-15 row for the section 7 amendment. |
| `cards-1:STRAT:HUNTER` | Hunter (buy a reversal at support) | PARK | PARK (owner decision D6, Oct 11). Keep the shadow log; revisit only with a pre-written rule at the daily… | Recorded. Nothing owed. |
| `cards-1:STRAT:SQUEEZE` | Squeeze (compression breakout) | PARK | PARK (owner decision D6). No further hourly work. | Recorded. Nothing owed. |
| `cards-1:STRAT:CONTINUATION` | Continuation (pullback inside an uptrend; the third native core) | RE-TEST | RE-TEST once, on a daily horizon, before any decision; until then PARK. | PARKED_WINDOW (`PW-LIBRARY`): Rule B: one pre-registered daily-horizon re-test at NDAX costs after the window. |
| `cards-1:STRAT:BOLLINGER_MR` | Bollinger mean reversion (extra, the third Wave A member) | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-1:STUDY:WAVE_A` | Wave A (Hunter, Squeeze, Bollinger) as the lab's first test set, and the Strate… | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-1:STUDY:WAVE_A_1Y_BACKTEST` | One-year hourly backtest of Wave A on 10 coins | KEEP | KEEP as the baseline row for any redesign; no further Wave A work. | Recorded. Nothing owed. |
| `cards-1:LAB-TRUTH` | Market Truth, the continuous observer and outcome truth (stages S1-S2) | RETIRE | RETIRE the code; KEEP the principle. | Recorded. Nothing owed. |
| `cards-1:STUDY:S3_LIVE_AUDIT` | First live regime and decision audit (S3) | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-1:LAB-S4` | Stage 4 replay: a year of hourly bars through the same observation schema | RETIRE | RETIRE; keep the schema idea. | Recorded. Nothing owed. |
| `cards-1:STUDY:LAB_COMPARE` | Live paper versus the one-year replay (`lab compare`) | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-1:LAB-TA` | TradingAgents reference audit (an outside project read for ideas) | PARK | PARK as a reference. | Recorded. Nothing owed. |
| `cards-1:LAB-DI` | Decision Intelligence foundation (typed decisions, behaviour profiles, hard gat… | KEEP | KEEP the principle; RETIRE the August module. | Recorded. Nothing owed. |
| `cards-1:S5-H1` | Hunter's TREND_UP contradiction (audit id H:S5-H1) | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-1:S5-H2` | Hunter's silence in REVERSAL: which gate blocks it? (audit id H:S5-H2) | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-1:S5-H3` | Split TAKE-equivalents by strategy (audit id H:S5-H3) | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-1:S5-H4` | Squeeze scarcity (audit id H:S5-H4) | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-1:S5-H5` | The audit clock: a slow label against fast flags (audit id H:S5-H5) | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-1:STUDY:DQ_V0` | Decision Quality meter v0.0 / v0.1 (and its Sep 1 re-run) | RETIRE | RETIRE the meter; KEEP the bands and the SKIP_SETUP/FILTERED_IDLE split as vocabulary. | Recorded. Nothing owed. |
| `cards-1:STUDY:UNIVERSE_V1` | Strategy Research Universe v1 (strategy x asset x timeframe x regime cells) | RETIRE | RETIRE this copy; the daily universe replaced it. | Recorded. Nothing owed. |
| `cards-1:STUDY:SETUP_MEMORY` | Setup Memory v0 and market-state fingerprints (COSTLY/PROTECTIVE stamps) | RETIRE | RETIRE the module; KEEP the stamp vocabulary. | Recorded. Nothing owed. |
| `cards-1:STUDY:I2_HIST_BASELINE` | Breakout families as history-only shadows (Donchian, ATR, Keltner) | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-1:LAB-CONSULT` | Knowledge consult v0.1 and consult-dq (memory may be asked; memory may not TAKE) | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-1:LAB-PIPE` | Process locks: research pipeline, four tracks, protocol, lab objects, config bu… | KEEP | KEEP the rules (they already migrated); RETIRE the August files. | Recorded. Nothing owed. |
| `cards-1:STUDY:BTC_ETH_CELL_COMPARE` | One cell compared across coins (books compare) | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-1:STUDY:FINDINGS_GRID` | Findings card v0.8 and the 10-book knowledge grid — the August lab's capstone | KEEP | KEEP the file as the record that closes the hourly chapter; run nothing from it. | Recorded. Nothing owed. |
| `cards-1:EXP-001` | Donchian x TREND_UP against sitting out (1h, 10 coins) | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-1:EXP-002` | Bollinger x COMPRESSION against sitting out (1h, 10 coins) | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-1:EXP-003` | Hunter x TREND_UP: does it ever TAKE? (closes S5-H1) | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-1:EXP-004` | Is the BTC 15-minute replay a year of data? | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-1:EXP-005` | ATR breakout x TREND_UP against sitting out (1h, 10 coins) | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-1:EXP-006` | Does the app's daily health sweep match the lab's books? | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-1:EXP-007` | What phases does our data actually contain? | KEEP | KEEP the lesson (state the phase mix of any dataset); RETIRE the code. | Recorded. Nothing owed. |
| `cards-1:EXP-008` | EXP-008 / EXP-009 / EXP-011 · TAKE versus SKIP by phase on BTC, ETH and SOL (on… | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-1:EXP-010` | Donchian lookback sweep (reserved, never run) | RETIRE | RETIRE the ticket; KEEP the rule. | Recorded. Nothing owed. |
| `cards-1:LAB-5Y` | The five-year book: the August lab's last act | KEEP | KEEP as the recorded negative; no action. | Recorded. Nothing owed. |
| `cards-1:G-LAB` | The G1-G7 paper laboratory and the L2 pathway | KEEP | KEEP (it is the live decision store's foundation). | Recorded. Nothing owed. |
| `cards-1:AGT-P1` | P1 ingest: the app's 10-coin cycle envelope, honestly counted | KEEP | KEEP. | Recorded. Nothing owed. |
| `cards-1:G8-GRANT` | The G8 paper authority grant ($1,000 paper, $100 a trade, one position) | KEEP | KEEP the grant pattern; MODIFY the record-keeping — a grant should have its own dated document, not a test… | DONE: 3505615 docs/GRANTS.md ('Written 2026-10-15'): row 'G8 paper ledger / 2026-09-24' with source, limits ($1,000 paper, $100 per position, 8 bp haircut) and state… |
| `cards-1:G8-IDLE` | Four days of authority with zero trades: fixtures, allowlists and the brake-bui… | KEEP | KEEP the safety rails; MODIFY the expectation — pair any future grant with a minimum-activity plan so… | RECORDED: 3505615 docs/GRANTS.md 'What every future grant must carry', item 3: a minimum-activity plan (what runs, how much evidence by when, review date); every grant row has a… |
| `cards-1:STUDY:HL_RX` | The HL-RX reconstruction camera (pointer card) | RE-TEST | RE-TEST per RECONSTRUCTION.md's recommendation (re-pull fills over the snapshot-covered period). | PARKED_WINDOW (`PW-HL-RX`): A new study (Rule B): post-window. The snapshot stream keeps growing, so any later fill window works; it can share the first quarterly R2 fill re-pull (2027-01-01). |
| `cards-1:STUDY:HL_BENCH` | The Hyperliquid population benchmark (pointer card) | KEEP | KEEP as benchmark; refresh on schedule. | SCHEDULED (`Q-R2-HL`): docs/repair_shop/ledger.json studies R2 schedule: every quarter, next_due 2027-01-01, how: re-pull Hyperliquid fills + review2_traders analyze (D8). learning._due()… |

### Grok era: relationships H1-H6 and the first lab (cards-2)

No v1 rows existed for this work. 34 rows.

| Row | What | Verdict | Standing | Now |
|---|---|---|---|---|
| `cards-2:P3-SCREEN` | Phase-3 screen: 11 simple measures on 15-minute bars | RETIRE | RETIRE as a standalone item; keep the file as the record. | Recorded. Nothing owed. |
| `cards-2:P3-REL660` | Relationship hunt v0: 660 trials | RETIRE | RETIRE the hunt; carry its 660-look count to anything born from it. | RECORDED: 3505615 docs/research/RESEARCH_RULES.md section 1 'One question at a time': 'the 660 looks of the first relationship hunt are carried by anything born from it'. |
| `cards-2:P4-EVENTS-V0` | Event lab v0: loose "unusual bar" events | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-2:P4-EVENTS-V1` | Event lab v1: 26,387 very large 15-minute moves | KEEP | KEEP the definition as a tool. | Recorded. Nothing owed. |
| `cards-2:P4-CANDIDATE` | Candidate: "volume is already high before a large move" | RETIRE | RETIRE as a standalone item (merged into H1 and P4-YEARSPLIT). | Recorded. Nothing owed. |
| `cards-2:P4-YEARSPLIT` | Year split of the candidate (before 2022 vs 2022 on) | KEEP | KEEP as a record; RETIRE the fade claim. | Recorded. Nothing owed. |
| `cards-2:P4-H1-PREDICT` | Does a raised volume reading predict a big next bar? (gate vz 0.40) | KEEP | KEEP (merged into H1). | Recorded. Nothing owed. |
| `cards-2:P4-H1-BINS` | Five volume bins and the chance of a big next bar | KEEP | KEEP as the base table for H1. | Recorded. Nothing owed. |
| `cards-2:H2` | Volume heat plus rising volatility (`rel.volume_z_and_rv_change.v1`) | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-2:P3-VOTE` | Sign vote across eras: 53 of 66 pairs promoted | RETIRE | RETIRE the rule; keep the list as a record. | Recorded. Nothing owed. |
| `cards-2:P3-FILTER` | Size floor: 53 promoted pairs shrink to 23 survivors | KEEP | KEEP as the record of the 15-minute story. | Recorded. Nothing owed. |
| `cards-2:P3-H1CI` | Error bars on the H1 volume bins | MODIFY | MODIFY: recompute with day-level blocks and add the sealed window. | PARKED_WINDOW (`PW-H1`): A re-test of H1 (Rule B): post-window, folded into the H1 re-test item. |
| `cards-2:H3` | Snap-back from the 20-bar average (`rel.ma_distance_20.fwd_1h.v1`) | PARK | PARK. Reopen only for a venue whose all-in costs are a small fraction of 2 to 10 bp. | Recorded. Nothing owed. |
| `cards-2:H4` | Does BTC's last hour lead the other coins? (`rel.btc_ret_1h.alt_fwd_1h.v1`) | RETIRE | RETIRE (merged into H3). | Recorded. Nothing owed. |
| `cards-2:COST-TEST` | Do the H3 and H4 spreads survive a fee? | MODIFY | MODIFY: every cost test should use the venue's measured all-in cost, not 0 to 10 bp. | RECORDED: 3505615 RESEARCH_RULES.md section 5 'Costs': the venue's all-in cost (NDAX 0.20% a side + the coin's half-spread, dated table in ndax_costs.py); 'Never a 0 to 10… |
| `cards-2:OOS-1` | Sealed September 2026 test of H1, H3 and H4 | KEEP | KEEP as a record, do not cite it as proof; RE-TEST H1 as in the H1 card. | ERRATA (`E-007`, `E-008`): Not cited live: knowledge_catalog card.h1.volume_shock.v1 oos 'NA'; no H1 '2.69' in docs/src/jarvis. |
| `cards-2:REGISTRY` | relationship_registry.sqlite (the status store) | PARK | PARK as the Grok-era record. For new markets, keep one live results table (the Claude-era… | RECORDED: 3505615 RESEARCH_RULES.md section 6: a strategy's status comes from one file, docs/knowledge/strategy_status.json (13 entries, updated 2026-10-15); section 2: one count… |
| `cards-2:H1` | Volume shock: a burst of volume warns of a big next bar, with no direction (`re… | RE-TEST | RE-TEST as above, then MODIFY its use: a risk flag (skip or shrink entries on the bar after a burst), never… | PARKED_WINDOW (`PW-H1`): Rule B: post-window; count events once per coin-day. |
| `cards-2:P4-H1-DIRECTION` | Does a volume burst say which way the next big move goes? | KEEP | KEEP the conclusion. | Recorded. Nothing owed. |
| `cards-2:H5` | Absorption: heavy volume with a quiet price bar (`rel.absorb_quiet_high_vol.v1`) | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-2:SET2-H1-INTERACT` | 11 slices of the hot bars: does direction depend on the hot bar itself? | PARK | PARK. | Recorded. Nothing owed. |
| `cards-2:H6` | Hot-bar continuation (`rel.h1_heat_same_bar_continuation.v1`) | RETIRE | RETIRE: a neighbouring test (SET15) was rejected and ten coins cannot test H6 itself; re-test only on a… | Recorded. Nothing owed. |
| `cards-2:OOS-2` | Sealed September test of H6 (continuation) | RETIRE | RETIRE as a test. | Recorded. Nothing owed. |
| `cards-2:SET1` | Campaign: basic measure to forward move, 15-minute Lab-10 | RETIRE | RETIRE (close the row); keep the 660-look count as a reminder. | ERRATA (`E-009`): relationship_registry.sqlite (untracked), table campaign, SET1: status ACTIVE, keep 0, updated_utc 2026-09-12T13:02:12Z, notes '660→23. |
| `cards-2:SET2` | Campaign: H1 direction, continuation, absorption | RETIRE | RETIRE (close the row). | ERRATA (`E-009`): relationship_registry.sqlite, table campaign, SET2: status ACTIVE, keep 0, updated_utc 2026-09-12T13:02:12Z, notes 'Direction none. |
| `cards-2:LAW` | research_law table, Two-Layer Lock, Parameter Discovery Law, blueprint rules | KEEP | KEEP the principles; MODIFY the numbers: use the venue's real cost, count independent events and not bars… | RECORDED: 3505615 RESEARCH_RULES.md section 2 'Counting': independent market events, not bars; 'Every script logs the date range it read and the number of days it dropped'… |
| `cards-2:H1-AGENT` | What the agent did with H1 (Sep 12 to Oct 11 2026) | MODIFY | MODIFY: compute vz on each closed 15m bar, store it in the decision snapshot, cite H1 only when it is 2 or… | PARKED_WINDOW (`PW-H1`): Not done: h1_watch.py never scheduled (untracked, 2-line ledger, no launchd/cron). |
| `cards-2:ME1` | How often do coins move 0.5%, 1% or 2% in 5 minutes to 4 hours? | KEEP | KEEP: refresh quarterly as the base-rate sheet for sizing stops and targets. | SCHEDULED (`Q-ME1`): Frozen me1_move_freq_v0.py/.json (research-db, untracked, Sep 13). |
| `cards-2:ME2` | Which comes first within 30 minutes, +1% or -1%? | PARK | PARK. | Recorded. Nothing owed. |
| `cards-2:ME3` | What did the market look like at the start of a 1%-in-30-minutes move? | PARK | PARK. | Recorded. Nothing owed. |
| `cards-2:ME4` | After the 1% hit, which comes first: +50 bp more or -50 bp back? | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-2:ME-CLOSE` | Movement-event close note (ME1 to ME4) | KEEP | KEEP as a record of what is closed. | Recorded. Nothing owed. |
| `cards-2:ME5` | Does a start from a quiet bar behave differently from a noisy start? | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-2:CJ1-CJ4` | Conjunction frequency counts (never computed) | RETIRE | RETIRE (or redefine on the 120-coin lake if conjunctions are wanted; ME3 already answers part of CJ2: H1… | Recorded. Nothing owed. |

### Grok era: the SET campaigns, PD cards and S2 logs (cards-3)

No v1 rows existed for this work. 33 rows.

| Row | What | Verdict | Standing | Now |
|---|---|---|---|---|
| `cards-3:SET3` | Constructed combinations of existing 15-minute variables | RETIRE | RETIRE as a trade idea. KEEP the pre-registered pass rule as a template. | Recorded. Nothing owed. |
| `cards-3:SET4` | 16-cell state table (two cells VALIDATING) | RETIRE | RETIRE the "validating" label (no direction or fee test exists). | ERRATA (`E-006`): Registry campaign SET4 'READ_STRICT', note '2 cells VALIDATING; 14-wide OOS_PASS retracted'; candidates SET4-vz0_mo1_st0_rv0 and SET4-vz1_mo1_st1_rv1 VALIDATING (30 /… |
| `cards-3:SET5` | BTC volume shock to alt lag (18 coin-direction pairs) | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-3:SET6` | Coiled spring (tight range, heavy volume, then a 5% move?) | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-3:SET7` | 7-day high/low break: hold or reject (sweep)? | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-3:SET8` | Volume spike by time of day (session) | RE-TEST | RE-TEST cheaply on the lake as a description only. | PARKED_WINDOW (`PW-FEE-SCREEN`): A lake re-test (Rule B): post-window, as a description only, events counted per coin-day. |
| `cards-3:SET9` | How long does a volume spike's extra chance last (path to a 4x bar or a 5% move… | KEEP | KEEP as a fact. | Recorded. Nothing owed. |
| `cards-3:SET10` | How long does a volume spike last (persistence)? | KEEP | KEEP as a fact. | Recorded. Nothing owed. |
| `cards-3:SET11` | Effort versus result (did the volume move the price?) | PARK | PARK as a descriptive fact. | Recorded. Nothing owed. |
| `cards-3:SET12` | Breadth: isolated shock versus crowd shock | RE-TEST | RE-TEST on the lake (read-only, cheap). | PARKED_WINDOW (`PW-FEE-SCREEN`): A lake re-test (Rule B): post-window. |
| `cards-3:SET13` | Sigma displacement from the 20-bar average (3-sigma fade) | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-3:SET14` | Residual versus Bitcoin: does a lagging alt catch up? | KEEP | KEEP as knowledge only ("not economic"). | Recorded. Nothing owed. |
| `cards-3:SET15` | First-passage path after the lag (+50 bp before -50 bp) | KEEP | KEEP the method, PARK the result. | Recorded. Nothing owed. |
| `cards-3:SET16` | Combo: the lag split by heat and motion (four cells) | PARK | PARK (superseded by the frozen slice). | Recorded. Nothing owed. |
| `cards-3:SET14-DEDUP` | Non-overlapping lag events (`set14_events_dedup`) | KEEP | KEEP as the reference count for any lag work. | Recorded. Nothing owed. |
| `cards-3:SET14-LAGBIRTH` | Lag birth path (`set14_lag_birth`) | KEEP | KEEP as knowledge only. | Recorded. Nothing owed. |
| `cards-3:SET14-LAGBIRTH-FEE` | Fee table on the lag-birth means (`set14_lag_birth_fee`) | RETIRE | RETIRE as a trade; keep the verdict. | Recorded. Nothing owed. |
| `cards-3:SET16-MOVELAG` | MOVE_COLD plus lag birth (`set16_move_lag`, the frozen SET16) | PARK | PARK. Do not count live matches until a 15-minute feed runs again and each match gets an outcome record; the… | Recorded. Nothing owed. |
| `cards-3:SET16-MOVELAG-FEE` | Fee audit of the frozen SET16 (`set16_move_lag_fee`) | MODIFY | MODIFY: re-run the fee screen with the real venue cost and a single long leg. | ERRATA (`E-001`): set16_move_lag_fee_v1.json (untracked, 2026-09-12): 0/4/8/10 bp off gross 34/10/22 bp; oos_8bp SURVIVES_FEE, late_8bp MARGINAL. src/intelligence/ndax_costs.py… |
| `cards-3:CATALOG` | Research catalog v1 and the agent research record | KEEP | KEEP; when any card here changes status, change it in both copies. | DONE (`PW-HOURLY-RESUME`): knowledge_catalog_v1.json carries a dated note that strategy_status.json decides status and that its Hunter/Squeeze entries are stale while the hourly watch is parked… |
| `cards-3:HISTEXP` | History-expand lock and the candle-run sequence (never run) | PARK | PARK; revive only with the old data on disk, inventoried and hashed. | Recorded. Nothing owed. |
| `cards-3:SEQ-10M` | Two same-sign 10-minute candles: does the run continue? | KEEP | KEEP the null as a fact. | Recorded. Nothing owed. |
| `cards-3:SEQ2` | Inside the two-candle event: 5-minute shapes (characterize) | RETIRE | RETIRE as a predictor; KEEP the "candles are mixed inside" fact. | Recorded. Nothing owed. |
| `cards-3:PDLAW` | Parameter Discovery Law (Layer 9) | KEEP | KEEP; apply it to every parameter the new engine plan touches. | RECORDED: docs/research/RESEARCH_RULES.md §3 'Parameters: the parameter-discovery law (PDLAW, BESTPF)', items 1-5 (3505615); the file applies to every crypto review from #31 on.… |
| `cards-3:PD-1` | Where does the volume gate 2.0 sit in the real distribution? | MODIFY | MODIFY: re-run with the catalog's vz formula and era cuts, then re-freeze. | ERRATA (`E-005`): pd1_vz_dist_v0.py:21-22 EARLY=1625097600 (2021-07-01), LATE=1754006400 (2025-08-01); vz20=(v-mean)/sd; no instrument filter; merged 15m file has 11 instruments incl… |
| `cards-3:PD-2` | Where does the lag cut -1% sit? (residual distribution) | KEEP | KEEP; feed it into any future lag object. | Recorded. Nothing owed. |
| `cards-3:PD-3` | Where do range and ATR sit? (and what the $2-$5 stops really were) | KEEP | KEEP; any new exit design must start from these fractions, not dollars. | Recorded. Nothing owed. |
| `cards-3:GUARD` | Runtime guardrails and the load pack (wiring that never wired) | MODIFY | MODIFY: either wire the load pack or delete the claim that it is loaded, so the record stops overstating the… | ERRATA (`E-013`): runtime_guardrails_v1.json untracked in research-db and main worktree root (both md5 fed882264861be7c410a9fbc60ea153d); load_pack lists 7 files; git grep HEAD of both… |
| `cards-3:DISC-1` | Discovery pass 1: can anything before a volume-surge birth pick the winners? | KEEP | KEEP the null; stop hunting on these fields. | Recorded. Nothing owed. |
| `cards-3:DISC-2` | Discovery pass 2: the same question on lag births (and the SET16 flag re-checke… | KEEP | KEEP with SET16's PARK verdict; the two must move together. | Recorded. Nothing owed. |
| `cards-3:DISC-3` | Discovery pass 3 and the three-pass close | KEEP | KEEP the close memo as the standing "do not reopen" list. | Recorded. Nothing owed. |
| `cards-3:S2-LOGS` | Hunter and Squeeze trade logs dumped from the Lab | KEEP | KEEP the logs as the strategies' evidence base; fix the squeeze file's id and the watches line. | ERRATA (`E-023`): Done: watches.json SQUEEZE 'no live fires yet' replaced in acdd3fd (3 paper trades, -$2.93); paper_book.sqlite: squeeze 3 trades, 0 wins, -2.93. |
| `cards-3:S2-SPLITS` | Joining those trades with market state (sync and volatility bands) | RETIRE | RETIRE the three split files (or rename them with the right strategy and counts); keep the closed verdict. | ERRATA (`E-023`): Verdict kept: knowledge_catalog_v1.json 4 CLOSED s2.* rows (a3ad674); cite_allowlist.py denies s2.hunter/s2.squeeze/card.s2. |

### Grok era: market states, MRD and the agent packs (cards-4)

No v1 rows existed for this work. 40 rows.

| Row | What | Verdict | Standing | Now |
|---|---|---|---|---|
| `cards-4:MSM-1` | Market stamp: one reading of the whole 10-coin book | KEEP | KEEP as a background fact; do not rerun. | Recorded. Nothing owed. |
| `cards-4:MSM-2` | Residual stamp: who lags or leads BTC and the rest of the book | KEEP | KEEP as description. | Recorded. Nothing owed. |
| `cards-4:MSM-3` | Lifecycle tagger: nine one-label tags | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-4:MSM-4` | Transition table and the one "after failed heat" test (catalog id msm4.exhaust.… | RETIRE | RETIRE the test; KEEP the transition table as description. | Recorded. Nothing owed. |
| `cards-4:Ananta_MSM_Construction_Close_v1` | MSM-1 to MSM-4 closing record (docx) | KEEP | KEEP as the record. | Recorded. Nothing owed. |
| `cards-4:msm_tag_hygiene_v1` | Tag hygiene: fixing the COOLING leak | KEEP | KEEP as the record of the fix. | Recorded. Nothing owed. |
| `cards-4:msm_tag_v11_stamp_v1` | Tag v1.1: the 12-tag stamp (with Ananta_Tag_V11_Lock_v1.docx) | PARK | PARK; if a label is ever needed, use MSM v1. | Recorded. Nothing owed. |
| `cards-4:watch_score_v0` | Research Watch Score v0 (with Ananta_Watch_Score_v0.docx) | RETIRE | RETIRE the score; keep the plain status words. | Recorded. Nothing owed. |
| `cards-4:msm_tag_v11_now_v1` | "Now" stamp: the Tag v1.1 label of each coin on the latest bar | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-4:Ananta_Research_Frames_MSM_to_TagV11_v1` | "What we actually asked" (docx) | KEEP | KEEP as the story document. | Recorded. Nothing owed. |
| `cards-4:Ananta_MSM_v1_Freeze_v1` | "State = lifecycle, flags = conditions" (docx) | KEEP | KEEP; reuse the A/B/C split. | Recorded. Nothing owed. |
| `cards-4:msm_v1_stamp_v1` | MSM v1: lifecycle column plus seven flag columns | MODIFY | MODIFY before any use: prefer this over Tag v1.1, restamp on the lake, and cap how long COOLING can run on. | PARKED_WINDOW (`PW-MSM`): Re-stamping on the lake and a COOLING cap are new analysis (Rule B); needed only if MSM states are ever proposed for use. |
| `cards-4:MSM` | MSM lifecycle states · QUIET, WARMING, HOT, EXTENDING, STALLED, COOLING, GAP (g… | KEEP | KEEP the definitions as the record; PARK any use. | Recorded. Nothing owed. |
| `cards-4:msm_v1_transition_v1` | What follows what in the 7-state lifecycle | KEEP | KEEP as description. | Recorded. Nothing owed. |
| `cards-4:msm_v1_hot_birth_path_v1` | HOT birth on the SET15 clock (catalog id hot.birth.set15.v1, REJECTED) | RETIRE | RETIRE as an entry idea; KEEP the written reason. | Recorded. Nothing owed. |
| `cards-4:research_catalog_v1.json` | the four entries of this scope (msm.lifecycle.v1, watch.score.v0, hot.birth.set… | MODIFY | MODIFY: plain words instead of 1-to-10 quality; add the items to the registry. | ERRATA (`E-026`): research_catalog_v1.json untracked (as_of 2026-09-12): evidence_quality h1 7, set14 6, set16 4, msm.lifecycle 8, watch.score 5, hot.birth.set15 8; msm4.exhaust none… |
| `cards-4:msm_v1_observer_v1` | Live observer snapshot (v1) | RETIRE | RETIRE (stale; superseded by v1.1). | Recorded. Nothing owed. |
| `cards-4:msm_v1_observer_v11` | Live observer snapshot (v1.1), re-run Sep 22 | PARK | PARK; if live context is wanted, rebuild it inside the agent with logged values. | Recorded. Nothing owed. |
| `cards-4:MRR-1` | Book field on 10-minute bars (mrr1_book_field_v0) | KEEP | KEEP as background. | Recorded. Nothing owed. |
| `cards-4:Ananta_Market_Regime_Research_Lock_v1` | "10-year 5m/10m spine" lock (docx) | KEEP | KEEP. | Recorded. Nothing owed. |
| `cards-4:MRR-2` | Book regime: 3 x 3 mix (mrr2_book_regime_v0) | KEEP | KEEP as background; do not read share drift as regime change. | Recorded. Nothing owed. |
| `cards-4:MRR-3` | Volatility transition table (mrr3_vol_transition_v0) | MODIFY | MODIFY the Foundation Map wording to "quiet became common"; keep the table. | ERRATA (`E-025`): Foundation Map docx §3: 'Quiet became absorbing (10m L→L 0.40 → 0.70)'; 5m Research Record docx: 'Quiet absorbs.' mrr2 Low share 0.33/0.471/0.613, High 0.33/0.196/0.11… |
| `cards-4:Ananta_Market_Regime_Dynamics_Lock_v1` | "5m is the spine" lock (docx) | KEEP | KEEP; fill the fingerprints if the 5-minute data is reused. | ERRATA (`E-027`): Condition met: 13 files under src/research name lab5_5m.sqlite (default --db in 4). freeze_5m_manifest_v1.json sha256_5m/_10m = 'OPERATOR_FILL'. openssl sha256 on… |
| `cards-4:MRD-1` | 5-minute market features (mrd1_5m_features_v0) | KEEP | KEEP. | Recorded. Nothing owed. |
| `cards-4:agent_context_stack_v0` | How research feeds the agent (rule file) | KEEP | KEEP. | Recorded. Nothing owed. |
| `cards-4:MRD-2` | Size after volatility (mrd2_vol_size_v0) | KEEP | KEEP; MODIFY the wiring (see size_after_vol). | PARKED_WINDOW (`PW-HOURLY-RESUME`): Catalog cards now record the OOS bar counts (n_split). LIVE_5 is left as it is because its only citing writer, the hourly watch, is parked; wire-or-drop is decided… |
| `cards-4:MRD-3` | Liquidity proxy (mrd3_liq_proxy_v0), "leading /ret//volume" REJECTED | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-4:MRD-4` | Market statistics (mrd4_market_statistics_v0) | KEEP | KEEP. | Recorded. Nothing owed. |
| `cards-4:Ananta_MRD_Foundation_Map_v1` | Foundation map (docx) | MODIFY | MODIFY: fix the "absorbing" sentence. | ERRATA (`E-024`, `E-025`): Ananta_MRD_Foundation_Map_v1.docx untracked (2026-09-12 22:33), §3 'Volatility persistence': 'Quiet became absorbing (10m L→L 0.40 → 0.70). |
| `cards-4:MRD-5` | Lead-lag in High-volatility versus Low-volatility bars (mrd5_leadlag_hl_v0; "HL… | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-4:MRD-6` | Block bootstrap intervals for size and sync (mrd6_block_ci_v0) | KEEP | KEEP the method. | Recorded. Nothing owed. |
| `cards-4:agent_context_rules_mrd_v0` | The three MRD rules and the rejected list | MODIFY | MODIFY: add how to compute the band live; fix the ordering note. | ERRATA (`E-024`): agent_context_rules_mrd_v0.json untracked, birth=mod 2026-09-12 22:47:35, rejects '5m lag-1 transfer-entropy candidate'; mrd7_te_hl_v0.py born 23:04:06, json 23:04:20… |
| `cards-4:size_after_vol` | "Expect a fatter next hour after a big BTC 5-minute move" (context item mrd.siz… | MODIFY | MODIFY: wire a live check against a band recomputed on the last year, or stop citing it; today it is a label… | PARKED_WINDOW (`PW-HOURLY-RESUME`): Catalog card records n_split; cite_allowlist comments corrected (the flag gates nothing). LIVE_5 unchanged: the only citing writer (hourly watch) is parked; decide… |
| `cards-4:sync_after_vol` | "Alts herd when BTC moves big" (context item mrd.sync_after_vol.v0) | MODIFY | MODIFY: rename it to same-bar herding and compute it live on a better band, or retire the claim; keep the… | PARKED_WINDOW (`PW-HOURLY-RESUME`): Catalog card records n_split; the one-book-bet rule lives on as P02 (chain.py). LIVE_5 unchanged while the hourly watch is parked; decide before it resumes. |
| `cards-4:MRD-7` | Transfer entropy by volatility band (mrd7_te_hl_v0; "HL" = High/Low) | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-4:agent_research_record_v1` | Official research record for the agent (extra) | KEEP | KEEP; refresh it with the Claude-era studies. | SUPERSEDED (strategy_status.json, hypotheses.json, status_cards.json and RESEARCH_RULES.md): agent_research_record_v1.json untracked, unchanged since 2026-09-13, named by no tracked file (git grep HEAD). |
| `cards-4:agent_setup_discrimination_v0` | Can entry-like events be told apart before the outcome? (rule file) | KEEP | KEEP. | Recorded. Nothing owed. |
| `cards-4:disc_pass1_hot_h1_v0` | Can HOT births be told apart before the outcome? (extra) | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-4:agent_progress_pack_v1` | Map of finished questions (extra) | PARK | PARK (stale since Sep 14); generate a new one from the ledger. | SUPERSEDED (docs/repair_shop/ledger.json (nightly check)): agent_progress_pack_v1.json untracked (as_of 2026-09-14), named by no tracked file. |
| `cards-4:s2_join_sync_v0` | s2_join_sync_v0 and s2_join_size_v0 · MRD bands joined onto hunter and squeeze… | PARK | PARK; fix the file labels before any reuse. | ERRATA (`E-023`): s2_join_sync_v0.py:9 OUT=s2_hunter_sync_split_v0.json, :92 id s2.hunter.sync_split.v0 + fixed window '1y_from_2025-09-19_not_three_era'; s2_join_size_v0.py:9… |

### Grok era: N3/N4, the fade, exit maps and the 5-minute record (cards-5)

No v1 rows existed for this work. 17 rows.

| Row | What | Verdict | Standing | Now |
|---|---|---|---|---|
| `cards-5:BUILD-G3b` | What was built (research-db, Sep 1–6) | - | - | RECORDED: Descriptive card (what the research-db repo built on Sep 1-6); nothing to act on. |
| `cards-5:N3-A` | N3 Phase A feature screen (170 trials) | RETIRE | RETIRE as a finding; keep the ledger and the "bar too loose" lesson. | Recorded. Nothing owed. |
| `cards-5:N3-B` | N3 Phase B: bb_bandwidth on three windows (the first refusal) | RETIRE | RETIRE the feature; KEEP the deny rule and the replication requirement. | Recorded. Nothing owed. |
| `cards-5:N3-REG` | Evidence Registry v1 and Ingest-Bar-Contract grant | KEEP | KEEP as process documents. | Recorded. Nothing owed. |
| `cards-5:CONTRACT` | Shared Contract v0.1 (what the app must tell the agent) | KEEP | KEEP; version it (v0.2 outcome-truth fields were planned, never shipped). | DONE: cycle_contract_v01.py docstring now says outcomes were never shipped as v0.2 and that no code imports the module; outcome_truth.py fills them. |
| `cards-5:N4` | N4 campaign: regime-sliced features (600 trials) | RETIRE | RETIRE the candidate list; keep the regime-slicing method with a stricter bar (independent-block counts… | Recorded. Nothing owed. |
| `cards-5:FADE` | fade.n4.ma8 — spec, catalog grant, and the live watch | RETIRE | RETIRE. Delete the dead hook from lab_watch.py (one line, cosmetic). | DONE: 0f0dfcf (2026-10-15) removed the try/except 'from fade_watch import' block from src/lab_watch.py _print_tick (5 lines). |
| `cards-5:EXIT-1H` | Engine exit map, 1h pass 1 and split | KEEP | KEEP as a closed map (as the record says: "Do not retune"); nothing to run. | Recorded. Nothing owed. |
| `cards-5:BESTPF` | Official Research Record — Fade to Best PF | KEEP | KEEP as the Grok-era closing statement; fold its law text into the Claude-era docs so it isn't only in an… | DONE: 3505615: docs/research/RESEARCH_RULES.md §3 'Parameters: the parameter-discovery law (PDLAW, BESTPF)': 1 no textbook default (ATR 2.5, 14-bar, $3); 2 measure, freeze… |
| `cards-5:5M-SPINE` | The 5-minute data lot (inventory, constructed 10m and 1h, freezes) | KEEP | KEEP; record the 10m row count and fill the SHA fields (10 minutes of work). | ERRATA (`E-027`): sqlite3 -readonly count(*): lab10m_derived.sqlite bars 4,064,010; lab5_5m.sqlite 8,128,104. openssl sha256: 5m 707c4e7c...ba69, 10m f96bc904...64ef =… |
| `cards-5:5M-RECORD` | 5m Research Record v1 (the 12-object map) | KEEP | KEEP. | Recorded. Nothing owed. |
| `cards-5:5M-FREEZE` | 5m Foundation Freeze and the two agent rules | KEEP | KEEP; add a measurement of whether the cards ever changed a decision (an A/B or counterfactual log), since… | RECORDED: RESEARCH_RULES.md §6 'Reading a result' (3505615): citation is not influence; log the decision with and without a card before claiming it mattered. |
| `cards-5:GUARD` | Runtime Guardrails v1 | MODIFY | MODIFY — port the still-unimplemented lines (friction UNKNOWN handling, human-only WASTE flips) into the… | DONE: Unknown cost never zero: RESEARCH_RULES.md s5 + ndax_costs.py (3505615), registry.cost() tier floor (registry.py:101-112); stale input = no trade: 604ad4c… |
| `cards-5:PROGRESS` | Agent Progress Pack v1 + Progress Against North Star | RETIRE | RETIRE both as live documents; keep as historical record. | Recorded. Nothing owed. |
| `cards-5:BLUEPRINT` | Agent Master Blueprint v1 | RETIRE | RETIRE (superseded). | Recorded. Nothing owed. |
| `cards-5:EXIT-15M` | Engine exit map, 15m A2 run | PARK | PARK — rerun on the long tape only if a 15m execution clock is ever actually proposed. | Recorded. Nothing owed. |
| `cards-5:P0CYC` | p0_cycle_ETH.json / p0_cycle_SOL.json | KEEP | KEEP (historical fixtures). | Recorded. Nothing owed. |

### Claude era, first studies and the Explorer (cards-6)

Rated in v1 as well; this is the final status of each. 59 rows.

| Row | What | Verdict | Standing | Now |
|---|---|---|---|---|
| `cards-6:STUDY:HL_BENCH` | Our rules next to Hyperliquid accounts and vaults | PARK | PARK as a reference. | Recorded. Nothing owed. |
| `cards-6:STUDY:MTF_ENTRY_V1` | Multi-timeframe entry study v1 (108 variants) | RETIRE | RETIRE as a signal; keep as the cost lesson. | Recorded. Nothing owed. |
| `cards-6:STUDY:ENTRY_V2` | Entry study v2 (36 variants: trend, dip buy, trailing stop) | RETIRE | RETIRE; keep as the lineage of V1_RIDE and T3. | Recorded. Nothing owed. |
| `cards-6:STUDY:CANDIDATE_V3` | One-time holdout test of the frozen trend-dip candidate | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-6:STRAT:CANDIDATE_TRENDDIP` | The frozen v2 trend-dip rule as a paper book | RETIRE | RETIRE the book; keep the template. | Recorded. Nothing owed. |
| `cards-6:STUDY:V3_FRESH` | Study v3: ride the trend on 10 fresh coins | RETIRE | RETIRE as a strategy; keep the exit idea inside T3. | Recorded. Nothing owed. |
| `cards-6:STUDY:V3_POSTHOC` | What the V3 "passes" look like inside | KEEP | KEEP as a checklist. | Recorded. Nothing owed. |
| `cards-6:STRAT:V1_RIDE` | V1_RIDE paper book with loss-streak breaker | RETIRE | RETIRE the book; keep the breaker. | Recorded. Nothing owed. |
| `cards-6:STUDY:V4_FRESH2` | Study v4: BTC market filter on 12 randomly picked coins | RETIRE | RETIRE the strategies; KEEP the gate (V02). | Recorded. Nothing owed. |
| `cards-6:STUDY:V4_POSTHOC` | What the V4 numbers hide | KEEP | KEEP as a record. | Recorded. Nothing owed. |
| `cards-6:STUDY:GREEN_RUNS` | Green-run journal: does a streak of up candles predict the next move? | RETIRE | RETIRE as a signal; keep the limit-order saving. | Recorded. Nothing owed. |
| `cards-6:STUDY:EXPLORER_V0_SCORECARD` | History replay of the Explorer's Rulebook v0 | RETIRE | RETIRE the setups; keep the replay engine. | Recorded. Nothing owed. |
| `cards-6:EXPLORER` | The 15-minute Explorer (Rulebook v0) and its live paper book | RETIRE | RETIRE as a trading book (done Oct 13); PARK the scanner. | Recorded. Nothing owed. |
| `cards-6:SETUP:E1` | Trend pullback | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-6:SETUP:E2` | Breakout retest | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-6:SETUP:E3` | Bounce from support (counter-trend) | RETIRE | RETIRE (no further test). | Recorded. Nothing owed. |
| `cards-6:SETUP:E4` | Momentum continuation | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-6:SETUP:E5` | Squeeze release | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-6:STUDY:CRISIS_R6` | Crisis replays: would the Explorer's exit bells have saved money in six crashes? | KEEP | KEEP as a standard test. | Recorded. Nothing owed. |
| `cards-6:R1` | Repair-shop review #1: three fixes proposed by the scorecard | RETIRE | RETIRE (record). | Recorded. Nothing owed. |
| `cards-6:R1-P1` | Market entry versus limit entry | KEEP | KEEP. | Recorded. Nothing owed. |
| `cards-6:R1-P2` | No warning bells | KEEP | KEEP the guard; revisit sizing instead. | Recorded. Nothing owed. |
| `cards-6:R1-P3` | Drop setup E5 | RETIRE | RETIRE E5. | Recorded. Nothing owed. |
| `cards-6:R1-HOLD` | Random-hold baseline: is it the setups or the market? | KEEP | KEEP. | Recorded. Nothing owed. |
| `cards-6:R2` | Repair-shop review #2: what can we learn from other traders' entries? | PARK | PARK (quarterly refresh only). | SCHEDULED (`Q-R2-HL`): ledger.json studies[R2].schedule: every quarter, next_due 2027-01-01, how = re-pull HL fills + review2_traders analyze; learning._due() prints it in the weekly review… |
| `cards-6:R2-D2` | "Traders did better buying weakness" (the one clear pattern) | PARK | PARK. | Recorded. Nothing owed. |
| `cards-6:R3` | Repair-shop review #3: the dip-buying setups E6, E7, E8 | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-6:SETUP:E6` | Deep dip (15-minute RSI under 30) | RETIRE | RETIRE (done as a trading book Oct 13); keep recording sightings. | Recorded. Nothing owed. |
| `cards-6:SETUP:E7` | Dip in a falling 4-hour trend (1-hour RSI under 40) | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-6:SETUP:E8` | Dip below the daily 50-day with weak momentum | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-6:R4` | Repair-shop review #4: portfolio trend rules T1-T4 against buy-and-hold | KEEP | KEEP (paper); see STRAT:T3. | Recorded. Nothing owed. |
| `cards-6:STRAT:T3` | The T3 portfolio trend layer (first definition and live paper books) | KEEP | KEEP on paper as the risk layer and judge after Q2; do not add money on this evidence. | SCHEDULED (`CHECKPOINT-30`): Kept on paper: strategy_status.json T3 UNDER_REVIEW/will_try_again, card T3 PAPER, watch T3_TREND. |
| `cards-6:R4-ROBUST` | Stress checks of T3 added after seeing the result | KEEP | KEEP the stress list as standard. | Recorded. Nothing owed. |
| `cards-6:STUDY:INTRADAY_ATLAS` | Intraday probability atlas | PARK | PARK (WATCH). | Recorded. Nothing owed. |
| `cards-6:STUDY:VARIABLE_REGISTRY` | Variable registry v1 (16 tested variables, 8 untested) | MODIFY | MODIFY: add the sample size and number of independent events to every row. | DONE (`PW-VARREG-EVENTS`): RESEARCH_RULES.md corrected and VARIABLE_REGISTRY.md rule 5 added (each row to carry its sample and independent events; known counts listed); filling the counts is… |
| `cards-6:V01` | Coin daily trend (close above its 50-day and 20-day averages) | KEEP | KEEP. | Recorded. Nothing owed. |
| `cards-6:V02` | Market gate (Bitcoin's daily close above its 50-day average) | KEEP | KEEP. | Recorded. Nothing owed. |
| `cards-6:V03` | Exit bells in slow crashes (disaster stop, trend-break exit) | KEEP | KEEP as a guard. | Recorded. Nothing owed. |
| `cards-6:V04` | Trading costs (fee plus half the bid-ask spread) | KEEP | KEEP; refresh spreads monthly. | SCHEDULED (`SPREAD-REFRESH`): KEEP: one dated table src/intelligence/ndax_costs.py (3505615; SNAPSHOT 2026-09-29, samples 1, next = worker S2 ~2026-10-25); layers.json COSTS text. |
| `cards-6:V05` | Entry order type (resting limit versus market) | KEEP | KEEP. | Recorded. Nothing owed. |
| `cards-6:V06` | Holding horizon (multi-week exposure) | KEEP | KEEP. | Recorded. Nothing owed. |
| `cards-6:V07` | Dip in a coin while Bitcoin is bullish | PARK | PARK. | Recorded. Nothing owed. |
| `cards-6:V08` | 4-hour trend filter for intraday entries | PARK | PARK. | Recorded. Nothing owed. |
| `cards-6:V09` | Other traders' entry timing (Hyperliquid) | PARK | PARK. | Recorded. Nothing owed. |
| `cards-6:V10` | Buy strength versus buy weakness (traders' context) | PARK | PARK. | Recorded. Nothing owed. |
| `cards-6:V11` | Consecutive green 5-minute candles (2 to 5) | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-6:V12` | 15-minute and 30-minute reversal crossings (S3, early versus confirmed) | RETIRE | RETIRE as a signal. | Recorded. Nothing owed. |
| `cards-6:V13` | 1-hour market bias S1 (price versus its 1-hour 50-average) | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-6:V14` | Volatility contraction and squeeze release | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-6:V15` | Volume ratio (candle volume against its 20-candle average) | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-6:V16` | Warning bells (X3) in normal times | KEEP | KEEP; revisit sizing. | Recorded. Nothing owed. |
| `cards-6:R5` | Repair-shop review #5: Madhav's three "reads" (capitulation, higher-low retest,… | KEEP | KEEP as evidence-only display; wait for live fires. | Recorded. Nothing owed. |
| `cards-6:SETUP:M1a` | Capitulation at the lows (as first written) | RE-TEST | RE-TEST: let live fires accumulate; the 120-coin result sits exactly on the bar. | SCHEDULED (`EV-Q5`): Watch live: watches.json M1a EVIDENCE_ONLY since 2026-10-03 (watch_engine at the daily close; universe_watch per tier). |
| `cards-6:SETUP:M1b` | SETUP:M1b and SETUP:M1c · Two loosened capitulation reads (2 variants) | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-6:SETUP:M2a` | Higher-low retest (as first written) | PARK | PARK. | Recorded. Nothing owed. |
| `cards-6:SETUP:M2b` | Higher-low retest with relative strength | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-6:SETUP:M3a` | Quiet base after a run, entry in the upper half (his Aug 10 buy) | PARK | PARK. | Recorded. Nothing owed. |
| `cards-6:SETUP:M3b` | Quiet base, classic breakout entry | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-6:R5-NEWS` | Would an AI news check have helped? (exploratory demo) | PARK | PARK (keep logging). | Recorded. Nothing owed. |

### Claude era: zones, reads, teachers and hypotheses (cards-7)

Rated in v1 as well; this is the final status of each. 72 rows.

| Row | What | Verdict | Standing | Now |
|---|---|---|---|---|
| `cards-7:STUDY:CASEBOOK` | Madhav's four SOL buys rebuilt from candles | KEEP | KEEP as context only. Next step: log every future owner trade in the same format from day one in any new… | RECORDED: docs/research/RESEARCH_RULES.md s7 'The casebook' (3505615): owner trades go in docs/casebook/cases.json the day they happen, with the entry-time reason; 'A case is… |
| `cards-7:STUDY:NEWS_CHECK_DEMO` | News check on six hand-picked cases | PARK | PARK the claim, keep the recorder. Next step: pre-register one test once 20-day outcomes exist (CAUTION vs… | DONE (`Q-NEWS-CREDIT`): docs/research/STUDY_NEWS_CREDIT.md pre-registers the scoring (eight comparisons, 20-day excess over the 10-coin median, /t/ >= 2.5, 10 weeks, 2 points); pushed before… |
| `cards-7:EXTRA:TEACHER_RULEBOOKS` | Notes on two YouTube teachers (Rayner Teo, Trade With Trend) | KEEP | KEEP as an idea source. Fix stale lines (`layers.json` TEACHERS still says "11 untested"). | DONE: acdd3fd removed '11 untested' (git log -S). layers.json TEACHERS evidence now: H01/H02/H14 SUPPORTED, H07 one cell, H06 PROMISING, H03-H05 NOT_SUPPORTED… |
| `cards-7:STUDY:TEACHER_FIRST_LOOK` | Five teacher systems run once on our coins (S1, S2, S3, S4, S4b) | RETIRE | RETIRE S1, S2, S4, S4b. RE-TEST S3 (H06) on the 120-coin lake with a same-exit baseline, as review #14 did… | PARKED_WINDOW (`PW-H06`): S3/H06 on the lake is a re-test of an existing idea: Rule B (RESEARCH_RULES.md s1) queues it after the window. |
| `cards-7:EXTRA:FRAMEWORK` | How Ananta reasons: the decision chain and the hypothesis register | MODIFY | MODIFY. Make status words come from one file so cards, brain and docs stop disagreeing (see DOUBTS). | DONE: tests/test_knowledge_build.py pins the brain's status words to the status-card words (20 of 20 agree). |
| `cards-7:H01` | Buy only when the whole market is in an uptrend (regime gate) | KEEP | KEEP. Re-measure the gate's edge every quarter, because the confirm period shows a thin edge. | SCHEDULED (`Q-H01`): KEEP: hypotheses.json H01 SUPPORTED (REGIME gate); card REGIME SUPPORTED/PAPER; chain.py REGIME gate. |
| `cards-7:H02` | Buy only coins that are in their own uptrend (trend gate) | KEEP | KEEP, with the "long tail fails" note kept visible. | Recorded. Nothing owed. |
| `cards-7:H03` | Weinstein stage-2 breakouts (weekly 30-week average) | RETIRE | RETIRE as an entry; PARK "stage as a regime label". | Recorded. Nothing owed. |
| `cards-7:H04` | Weekly Donchian 50/40 trend system ("+5,024%") | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-7:H05` | Bollinger 200/4 breakout | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-7:H06` | Deep Bollinger dip in an uptrend (mean reversion) | RE-TEST | RE-TEST on 120 coins with the review #14 design. | PARKED_WINDOW (`PW-H06`): Re-test of an existing idea on the lake: Rule B (RESEARCH_RULES.md s1) queues it after the window; write the pre-registration then (PIT list, s4). |
| `cards-7:H07` | Short dip trade: buy a quick fall inside a long uptrend, sell on the first boun… | KEEP | KEEP as paper-tracked, not proven. Next step: reach 10 independent live fires (queue Q6) and align the… | SCHEDULED (`EV-Q6`): Aligned: acdd3fd changed hypotheses.json H07 from PROMISING to SUPPORTED (one cell); card H07 SUPPORTED/PAPER; both name the dial-closed tier-A cell. |
| `cards-7:H08` | Relative strength: buy what beats its benchmark | RETIRE | RETIRE as a filter, keep as an observation. | Recorded. Nothing owed. |
| `cards-7:H09` | Volume: breakouts on heavy volume fail less | PARK | PARK as an observation. | Recorded. Nothing owed. |
| `cards-7:H10` | Compression: tight, quiet bases break out better (VCP, coil) | RETIRE | RETIRE as an entry. | Recorded. Nothing owed. |
| `cards-7:H11` | Buy pullbacks to the rising 50-day average | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-7:H12` | First pullback after a breakout | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-7:H13` | False break: a dip under support that closes back above it | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-7:H14` | Put the stop about 1 ATR beyond the structure, not at a fixed percent | KEEP | KEEP, but record that for dips "no stop, time exit" beat both. | DONE: status_cards.json STOPS_DIP (2914633, Oct 11): no stop + 10-day exit +6.5%/+2.4% vs +0.5%/+0.4% with a tight stop (#27); card STOPS: 'the dip trade is best with no stop… |
| `cards-7:H15` | Trail the stop (3x ATR chandelier or a close under the 20/50-day) instead of fi… | RETIRE | RETIRE as a T3 exit. | Recorded. Nothing owed. |
| `cards-7:H16` | Breadth: a real recovery needs most coins above their averages | PARK | PARK; revisit with the 120-coin breadth series. | Recorded. Nothing owed. |
| `cards-7:H17` | Position building: scale in instead of buying all at once | PARK | PARK. Test only if H07 is later proven. | Recorded. Nothing owed. |
| `cards-7:H18` | News veto: market-wide fear is the opportunity, bad news about the asset is the… | PARK | PARK the claim; keep the log. | Recorded. Nothing owed. |
| `cards-7:P01` | Risk a small fixed share per trade (policy) | KEEP | KEEP. | Recorded. Nothing owed. |
| `cards-7:P02` | Correlated coins are one bet (policy) | KEEP | KEEP; measure the actual correlation once to set the number. | PARKED_WINDOW (`PW-P02`): Measuring the correlation is a new study, so post-window (Rule B). |
| `cards-7:R5` | Madhav's three reads, pre-registered test of 7 variants | RETIRE | RETIRE M2a, M2b, M3a, M3b and M1b/M1c; keep only M1a as a cheap watch (see its card). | Recorded. Nothing owed. |
| `cards-7:M1a` | Capitulation at the lows (primary version) | RE-TEST | RE-TEST. Keep the watch; re-run when a longer history or a new market gives 30 events. | PARKED_WINDOW (`PW-M1A`): Re-run needs 30 events from new data: post-window (Rule B). |
| `cards-7:M1b` | M1b and M1c · Capitulation variants (2 variants, one card) | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-7:M2a` | Higher-low retest (primary version) | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-7:M2b` | Higher-low retest plus "BTC made a lower low, the coin did not" | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-7:M3a` | Quiet base after a run, entry in the upper half of the base | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-7:M3b` | Quiet base, first close above the base (the classic breakout) | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-7:R5-NEWS` | Would the news check have helped Madhav's reads? (exploratory) | RETIRE | RETIRE as evidence; keep the demo as a note. | Recorded. Nothing owed. |
| `cards-7:R6-RWCAL` | Random-walk calibration of the zone test (Amendments 1 and 2) | KEEP | KEEP the method; MODIFY: carry the calibration's own noise into z and re-estimate the bias from real-return… | PARKED_WINDOW (`PW-ZONE-BASELINES`): Re-calibration adds analysis: post-window (Rule B). |
| `cards-7:R6` | Do zones hold? Eight zone groups against width-matched random bands | MODIFY | MODIFY. Keep zones as a location label, not a trade trigger, until the live held rate is judged over at… | SCHEDULED (`ZONES-JUDGE`): Label, not trigger: ZONE_TOUCH EVIDENCE/wont_take_again, wakes_brain false (3fe2b48); since 16fbf74 (Oct 15) zone_entry wakes are 'monitoring only... not decided' (33… |
| `cards-7:R6:SWING-NEW` | New swing zone (a swing-low band price turned at, never yet held) | KEEP | KEEP as a location label; RE-TEST live over at least 10 market events; do not use as an entry filter. | SCHEDULED (`ZONES-JUDGE`): Label: zones.GOOD_GROUPS = {AVERAGE-200, SWING-NEW} (0f0dfcf). |
| `cards-7:R6:SWING-TESTED` | Swing zone that held once before | RETIRE | RETIRE as a separate group. | Recorded. Nothing owed. |
| `cards-7:R6:SWING-STRONG` | Swing zone that held twice or more | PARK | PARK; settle the flag contradiction (see DOUBTS). | DONE: acdd3fd: docs/research/zones_status.json strength_matters changed from true to false; updated_by cites #6/#16 (60% vs 58% held, +5.9 vs +8.6 points). |
| `cards-7:R6:EXTREME` | 52-week low or high zone | PARK | PARK. | Recorded. Nothing owed. |
| `cards-7:R6:AVERAGE-50` | The 50-day average as a zone | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-7:R6:AVERAGE-200` | The 200-day average as a zone | RE-TEST | RE-TEST with the better baseline before relying on it. | PARKED_WINDOW (`PW-ZONE-BASELINES`): The re-test adds analysis: post-window (Rule B). |
| `cards-7:R6:CONFLUENCE` | Overlapping zones (two or more kinds on top of each other) | MODIFY | MODIFY: fix the stale code lists; keep as "watched". | DONE: chain.py, PLAYBOOK.md, FRAMEWORK.md and zones_watch.py no longer list overlapping zones among the places that pass. |
| `cards-7:R6:BASE` | Base floor or top of a quiet base | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-7:R7-RWCAL` | Random-walk calibration of the lookout reactions (Amendment 1) | KEEP | KEEP the method; MODIFY by checking the invented wick model against real data. | PARKED_WINDOW (`PW-ZONE-BASELINES`): Re-calibration adds analysis: post-window (Rule B). |
| `cards-7:R7` | The lookout: which reaction inside a zone predicts "held"? (7 reactions, F1 to… | KEEP | KEEP F6 (as the regime gate); RETIRE F1 to F5 and F7 as reasons. | Recorded. Nothing owed. |
| `cards-7:R7:F1` | Rejection wick (the day closed in the upper half of its range) | RETIRE | RETIRE as a reason. | Recorded. Nothing owed. |
| `cards-7:R7:F2` | Closed back above the zone | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-7:R7:F3` | Volume at least 1.5 times the 20-day average | RETIRE | RETIRE as a reason. | Recorded. Nothing owed. |
| `cards-7:R7:F4` | Momentum divergence (lower price, higher RSI than 10 days ago) | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-7:R7:F5` | Stronger than BTC over 30 days | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-7:R7:F6` | Market allowed (Bitcoin above its 50-day average) | KEEP | KEEP as the regime gate; re-measure each quarter. | SCHEDULED (`Q-F6`): Gate kept: jarvis/service/chain.py:65-67 REGIME = BTC close above its 50-day; status_cards REGIME SUPPORTED/PAPER; lookout_status.json F6 PASS. |
| `cards-7:R7:F7` | Good zone kind (200-day average, overlapping, or new swing) | RETIRE | RETIRE (merged into R6 cards). | Recorded. Nothing owed. |
| `cards-7:EXTRA:PLAYBOOK_ATTENTION` | The playbook and the attention score | MODIFY | MODIFY: test the weights, or drop to "supported zone and market allowed". | OWNER_DECISION (`OD-PLAYBOOK-ATTENTION`): zones_watch.py:57-87 attention() unchanged since 9994b6a (Oct 3): zone 1, supported kind 2, recent 1, market allowed 2, setup FIRED 2/CLOSE 1; HIGH>=6. eye.py:200 rings… |
| `cards-7:R8` | Madhav's reads again, at a supported zone (Z), with the market allowed (G), or… | RETIRE | RETIRE all 9 variants; remove the stale phone alert for M2a-G. | DONE: 72cb592: reads_watch.py:20 ALERT_ALSO={"H07"}, pinned by tests/test_reads.py (dropped read recorded, no phone); brain.py:46 setup:M2a-G 0.5. |
| `cards-7:R8:M1a-Z` | R8:M1a-Z, M1a-G, M1a-ZG · Capitulation at a supported zone, with the market all… | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-7:R8:M2a-Z` | R8:M2a-Z and M2a-ZG · Higher-low retest at a supported zone, and with the marke… | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-7:R8:M2a-G` | Higher-low retest with the market allowed (the most promising cell, later dropp… | RETIRE | RETIRE; remove from the phone-alert list. | DONE: 72cb592 took M2a-G out of ALERT_ALSO (reads_watch.py:20 now {"H07"}) with a pinning test in tests/test_reads.py; watches.json M2a-G EVIDENCE_ONLY, alerts 'none (dropped… |
| `cards-7:R8:M3a-Z` | R8:M3a-Z, M3a-G, M3a-ZG · Quiet base at a supported zone, with the market allow… | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-7:EXTRA:NEWS_RECORDER` | A daily AI news check on every coin | KEEP | KEEP; pre-register the scoring test. | DONE (`Q-NEWS-CREDIT`): Recorder runs (news_log 130 rows). The scoring is pre-registered in docs/research/STUDY_NEWS_CREDIT.md, pushed before the first 20-day outcome (about 2026-10-22). |
| `cards-7:R9` | Explorer entries by zone and market context (4 splits) | RETIRE | RETIRE the zone-for-Explorer idea. | Recorded. Nothing owed. |
| `cards-7:R10` | Stops and exits at zones (X1 time, X2 zone stop plus next-zone target, X3 2-ATR… | KEEP | KEEP the finding; MODIFY the two status cards' wording. | DONE: acdd3fd status_cards.json: EXITS WEAK/PAPER 'A lesson kept from a failed test. |
| `cards-7:R10-NOTARGET` | Zone stop with no target, held up to 60 days (exploratory) | PARK | PARK as context. | Recorded. Nothing owed. |
| `cards-7:STUDY:CREDIT` | Credit tracking: which layer moved each decision, scored 20 days later | KEEP | KEEP; pre-register the read (8 signals, 20 days) before looking. | DONE (`Q-NEWS-CREDIT`): The read is pre-registered in docs/research/STUDY_NEWS_CREDIT.md (own outcome definition; credit.report's raw means are descriptive only). |
| `cards-7:R11:A1` | Teacher idea: buy the dip into the 50-day zone in an uptrend | RETIRE | RETIRE as a standalone; the trend gate already carries what was real. | Recorded. Nothing owed. |
| `cards-7:R11:B1` | R11:B1 and B2 · Breakouts: through a zone above, and through a swing zone that… | RETIRE | RETIRE B1; PARK B2 (note the confirm-side improvement if breakouts ever come back). | Recorded. Nothing owed. |
| `cards-7:R11:B3` | Breakout through a zone on 1.5x volume (H09 made testable) | PARK | PARK with a dated re-look (one more year of data); reconcile the two status cards. | SUPERSEDED (card R21-B3 (RETIRE as a filter); B3 and BREAKOUT_VOL both REJECTED): Reconciled in acdd3fd: status_cards B3 REJECTED/OFF and BREAKOUT_VOL REJECTED/CONTEXT ('#21 ... replaces review #11's 10-coin reading'); hypotheses.json H09… |
| `cards-7:R12` | Trend-book exits: zone trail (T3Z), 3-ATR chandelier (T3A), close under the 50-… | KEEP | KEEP T3's exit; RETIRE T3Z/T3A/T3W; re-judge T3 itself after the chop (queue). | SCHEDULED (`Q-T3`): T3 exit unchanged; T3Z/T3A/T3W exist only in src/research/t3_exits.py (no live code); hypotheses.json H15 NOT_SUPPORTED->REJECTED (acdd3fd). strategy_status T3… |
| `cards-7:R13` | The remaining teacher ideas: H07, H12, H13, H16 at a 20-day hold | KEEP | KEEP the lesson; RE-TEST H16 on the 120-coin lot; leave H12/H13 retired. | DONE: H16 re-tested on the lake by review #17 (pre-reg 7111a0b, results 0b6cc5a, Oct 5; LAB10, TOP30, ALL; review #13's breadth thresholds): FAIL. hypotheses.json H12, H13… |
| `cards-7:R13-P03` | R13-P03 / P03 · The book stop: whole-book -8% from peak, stand in cash 5 days | KEEP | KEEP as an explicit human-comfort policy only, never as claimed protection; MODIFY the register note if… | DONE: ask.py now says P03 (the 8% book stop) failed review #13: a comfort rule, never a protection. |
| `cards-7:R14` | H07 against a fair baseline: the short dip in an uptrend, with its own exit | KEEP | KEEP the paper shadow; RE-TEST live over at least 10 independent market events before any real money… | SCHEDULED (`CHECKPOINT-60`): Reconciled: hypotheses.json H07 PROMISING->SUPPORTED (acdd3fd) = status_cards H07 SUPPORTED/PAPER. |
| `cards-7:STRAT:ZONE_TOUCH` | The live zone watch and its paper trades (the eye, the OKs, 56 losses) | RE-TEST | RE-TEST: keep the watch and the paper book running, but add a no-stop or time-exit variant so "zone wrong"… | SUPERSEDED (review #27 and strategy_status ZONE_TOUCH (wont_take_again, never wakes the brain)): No live no-stop variant (watches ZONE_TOUCH exit: stop half a range under the zone, else 20 days). |
| `cards-7:Q5/Q6` | The queue: what Oct 3 left waiting | KEEP | KEEP; add the stale M2a-G phone alert to the queue as a cleanup item. | DONE: ledger.json queue keeps Q5 ('10 market days with a live signal from your setups') and Q6 ('10 market days with a live H07 signal'), both WAITING_FOR_EVIDENCE, counting… |

### Claude era: the lake, reviews #15-#30 and the queue (cards-8)

Reviews #16-#30 had no v1 rows. 43 rows.

| Row | What | Verdict | Standing | Now |
|---|---|---|---|---|
| `cards-8:LAKE-1` | The research lake: download, build, upkeep | KEEP | KEEP. Print the number of coins alive per year in every review header. | DONE: 3505615: src/lake/research.py lake_header (:193) + format_header (:216) print 'Coins alive per year: ...'; tests/test_lake_header.py pins it; RESEARCH_RULES.md:54-55… |
| `cards-8:LAKE-2` | Choosing the 120 coins (universe rule v1) | MODIFY | MODIFY. Keep v1 for history; the next rule version should rank month by month. | DONE: src/lake/universe.py (rule v1) unchanged since 3432f8d (2026-10-04). |
| `cards-8:LAKE-3` | Cleaning rules, outage days and quality grades | KEEP | KEEP. Print the dropped-day count in each review. | DONE: 3505615: research.py dropped_days() (97%-of-minutes rule) feeds lake_header; format_header prints 'Days dropped under the 97%-of-minutes rule: X of Y (Z%)'… |
| `cards-8:LAKE-4` | Token swaps, re-used tickers and delisted coins (COCOS, BNX, LUNA) | KEEP | KEEP the detector; MODIFY: check renames when joining Binance data with NDAX symbols. | DONE: Detector kept: research.py BREAKS/ENDS + unhandled_suspects(); the header prints the cuts (3505615). |
| `cards-8:LAKE-5` | The three coin tiers: LAB10, TOP30, ALL120 | MODIFY | MODIFY. Say in every pre-registration which tier decides, and judge on a month-by-month list. | DONE: 3505615 docs/research/RESEARCH_RULES.md:14-15: pre-registration heading 'The tier that decides' (LAB10, TOP30, ALL120 or a PIT list; the others never rescue a failed… |
| `cards-8:AUDIT_V1` | The research audit of 165 rows | MODIFY | MODIFY. Re-score all rows after reviews #16-#28, add rows for #16-#23, and split DUMP into "failed" and "no… | SUPERSEDED (AUDIT_V2.md and audit_register.json): docs/research/audit_v1.json: 165 rows, updated 2026-10-05, last commit 5e043d5; row R15 result still 'Not run yet'; no rows for #16-#30. |
| `cards-8:R15` | Review #15: do T3, H07 and Madhav's setups survive the full universe? | KEEP | KEEP the design; MODIFY future pre-registrations to say which tier decides. | DONE: 3505615 RESEARCH_RULES.md:14-15: every pre-registration from review #31 has the heading 'The tier that decides'; the other tiers are reported beside it and never rescue… |
| `cards-8:R15-T3` | T3 trend portfolio on 10, 30 and 120 coins | KEEP | KEEP as paper, with the stated expectation "smaller losses than holding". | Recorded. Nothing owed. |
| `cards-8:R15-H07` | H07 RSI dip buy on 10, 30 and 120 coins | KEEP | KEEP on paper; count live market events, not trades. | DONE: status_cards H07 (acdd3fd) and brain.py:81 (bf1b6d5): the 8-for-8 was one signal day (Oct 8), 'one independent event'; strategy_status H07 ACTIVE: 'the scoreboard… |
| `cards-8:R15-M1a` | Madhav's capitulation read (M1a) on 10, 30 and 120 coins | PARK | PARK. Keep as context; revisit at 10 live fires (queue Q5). | Recorded. Nothing owed. |
| `cards-8:R15-M2A-M3A-M2AG` | Madhav's retest, quiet-base and gated-retest reads | RETIRE | RETIRE as buy signals (keep as "where to look"); fix the stale watches.json text. | DONE: watches.json M2a-G now 'dropped by review #15 ... evidence only', alerts 'none' (acdd3fd; the 'most promising ... phone' text is gone). status_cards READS and M2A_G… |
| `cards-8:R16-SWING-NEW` | New swing support zones on 120 coins | KEEP | KEEP as a location gate only. | Recorded. Nothing owed. |
| `cards-8:R16-AVERAGE-200` | The 200-day average as a support zone | MODIFY | MODIFY. Keep as a location label, do not trade touches, and re-check the correction on new data. | PARKED_WINDOW (`PW-ZONE-BASELINES`): The re-check is a re-test of an existing result: post-window list (Rule B; RESEARCH_RULES.md:60, next holdout = live data after a stated date). |
| `cards-8:R16-CONFLUENCE` | Overlapping (confluence) zones | RETIRE | RETIRE as a trade gate; keep watched. | Recorded. Nothing owed. |
| `cards-8:R16-OTHER-ZONES` | AVERAGE-50, SWING-TESTED, SWING-STRONG, EXTREME, BASE zones | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-8:R16-F6` | "Market allowed" (Bitcoin above its 50-day) at a zone | KEEP | KEEP, but re-check on new data because 2024-26 shows little. | SCHEDULED (`Q-F6`): Kept: lookout_status.json F6 PASS; chain.py:65-67 REGIME gate; status_cards REGIME SUPPORTED/PAPER. |
| `cards-8:R16-LOOKOUT` | The other six lookout reactions (F1-F5, F7) | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-8:R17-H08` | Relative strength against Bitcoin (H08) as a coin filter | RETIRE | RETIRE as a filter; keep as an observation. | Recorded. Nothing owed. |
| `cards-8:R17-H16` | Market breadth (H16) as a trend filter | PARK | PARK. Re-test once on new data, counted as one variant. | PARKED_WINDOW (`PW-R17-H16`): Re-test once on data after the lake's cut, one counted variant: list it in docs/LOCK.md 'After the window'. |
| `cards-8:R18-H14` | Structural stops versus 3% stops on the dip trade (H14) | KEEP | KEEP: no stop on the dip trade; a structural stop wherever a stop is required. | Recorded. Nothing owed. |
| `cards-8:R18-CRISIS` | The 25% disaster stop (V03) and six crash windows | KEEP | KEEP the 25% stop as a guard, expecting it to do nothing in backtests. | Recorded. Nothing owed. |
| `cards-8:R19-U03` | Buying pressure (taker buy share) as a filter | PARK | PARK as context. | Recorded. Nothing owed. |
| `cards-8:R19-U01` | Funding rate (crowded longs) as an exit or filter | RETIRE | RETIRE as a filter; keep the data as context. | Recorded. Nothing owed. |
| `cards-8:R19-U02` | Open interest and leverage flushes (liquidations not tested) | PARK | PARK. | Recorded. Nothing owed. |
| `cards-8:R20` | A lower-turnover T3: T3-N, T3-B, T3-M | KEEP | KEEP T3-B on paper; MODIFY: run the buffered-exit test the review itself proposed. | PARKED_WINDOW (`PW-R20`): Rest: the buffered-exit review is a new counted T3 variant: post-window list (Rule B), judged on a point-in-time list. |
| `cards-8:STRAT:T3-B` | T3 with band re-sizing, the paper default | MODIFY | MODIFY: relabel as a loss limiter; update the audit and status card with #22; keep the paper books running. | DONE (AUDIT_V2): status_cards.json T3B tier set to LIVE10; the fuller reason (#22, #30) is in AUDIT_V2.md because audit_v1.json is frozen. |
| `cards-8:R21-E3` | E3 support bounce (Explorer setup) | RETIRE | RETIRE. | Recorded. Nothing owed. |
| `cards-8:R21-B3` | B3 volume breakout (hypothesis H09) with the A1, B1, B2 re-runs | RETIRE | RETIRE as a filter; keep as an observation. | Recorded. Nothing owed. |
| `cards-8:R22-PIT30` | The month-by-month top 30 (point-in-time list) | KEEP | KEEP; use it as the default test list for every new rule. | RECORDED: RESEARCH_RULES.md §4 'Data: the lake and the lists', bullet 'Default test list: the point-in-time lists (src/lake/pit.py: PIT10 and PIT30...)', and §1 item 2 (3505615)… |
| `cards-8:R22-T3B` | Survivorship check of T3-B on the point-in-time top 30 | MODIFY | MODIFY: describe T3-B as a loss limiter; judge the paper books against the month-by-month list. | DONE: brain.py:75 T3 line 'on altcoins it loses much less, it does not reliably make money ... on the live 10 it mostly loses less and made a little' (905cca8)… |
| `cards-8:R22-H07` | H07 dip buy on the point-in-time top 30 | KEEP | KEEP on paper; count only live market events. | DONE: status_cards H07 (acdd3fd) and brain.py:81 (bf1b6d5): the 8-for-8 was one signal day (Oct 8), 'one independent event'; strategy_status H07 ACTIVE: 'the scoreboard… |
| `cards-8:R23-U06` | Nasdaq, US dollar and VIX as trend filters | RETIRE | RETIRE as filters; keep the data as context. | Recorded. Nothing owed. |
| `cards-8:R23-U08` | Fear and Greed index as an exit and a dip filter | RETIRE | RETIRE as an exit; PARK the fear-dip idea (needs more events). | Recorded. Nothing owed. |
| `cards-8:R23-U04-U05-U07` | Untested variables: dominance and stablecoin supply, scheduled events, on-chain… | PARK | PARK. | Recorded. Nothing owed. |
| `cards-8:Q1` | Queue: Explorer live versus replay | RETIRE | RETIRE the row with a one-line result; keep the paper record as evidence. | SCHEDULED (`EV-Q1`): ledger.json Q1 WAITING_FOR_EVIDENCE (updated 2026-10-15); TK17: 'Q1 stays: it is answered at the 10th market event (the 30-trade part is met)'; daily 2026-10-15: 9 of… |
| `cards-8:Q2` | Queue: T3 live tracking | KEEP | KEEP waiting. | Recorded. Nothing owed. |
| `cards-8:Q3` | Queue: E5 probation | RETIRE | RETIRE and make the three records agree. | DONE (AUDIT_V2): status_cards.json E5 reason says the probation ended 2026-10-15 without a verdict (TK17); the audit_v1 Q3 and SETUP:E5 corrections are in AUDIT_V2.md. |
| `cards-8:Q4` | Queue: Intraday atlas alerts | RETIRE | RETIRE (merge into Q1). | Recorded. Nothing owed. |
| `cards-8:Q5` | Queue: Your setups, live record | PARK | PARK; consider closing, since review #15 rejects three of the four reads. | Recorded. Nothing owed. |
| `cards-8:Q6` | Queue: H07 short dip trade, live record | KEEP | KEEP; MODIFY the counter to count market events. | DONE: 7ef1188: jarvis/service/views.py:851-853 h07_fires = COUNT(DISTINCT day) FROM read_fires WHERE variant='H07'; ledger Q6 waiting_for '10 market days with a live H07… |
| `cards-8:STRAT:ZONE_TOUCH` | Zone touch in an allowed market (forward paper trade) | RETIRE | RETIRE as a trading idea; keep recording. | Recorded. Nothing owed. |
| `cards-8:H:H06` | Deep-dip buy in an uptrend (Bollinger form) | RE-TEST | RE-TEST once on the lake, pre-registered (low priority; H07 already covers the family). | PARKED_WINDOW (`PW-H06`): Post-window: one pre-registered lake re-test (TOP30 + PIT30, one variant beside H07). |
| `cards-8:H:H07` | H07 across all reviews and the live record | KEEP | KEEP on paper; report live results as market events. | DONE: status_cards H07 (acdd3fd) and brain.py:81 (bf1b6d5): the 8-for-8 was one signal day (Oct 8), 'one independent event'; strategy_status H07 ACTIVE: 'the scoreboard… |

### Claude era: the $500 book, the engine and the evidence record (cards-9)

Built after v1 was frozen. 32 rows.

| Row | What | Verdict | Standing | Now |
|---|---|---|---|---|
| `cards-9:BRAIN-1` | The brain's own paper book against its random twins | KEEP | KEEP as evidence only (strategy_status: EVIDENCE, "modify_rules"). | RECORDED: docs/knowledge/strategy_status.json JARVIS: status EVIDENCE, verdict modify_rules, why '...judged again after 20 closed trades under the new rules'. |
| `cards-9:TK2` | TK2 / W2 · Dip trades need 1.2% room to the target | PARK | PARK. No change until 10 market events (about Oct 16), then drop it with E6. | DONE: 905cca8: docs/repair_shop/ledger.json TK2 status DONE, next: 'Closed without a review (Madhav, Oct 15 09:10 Toronto: "room yes")... the Explorer is retired as a trading… |
| `cards-9:TK3` | Hunter's paper book pays NDAX costs, not Kraken's | PARK | PARK Hunter; KEEP the NDAX cost model. | RECORDED: strategy_status.json HOURLY: PARKED, wont_take_again ('Parked by Madhav (D6, Oct 11)'). src/intelligence/paper_exit.py COST_PROFILES 'NDAX' fee 20 bp + slippage 30 bp a… |
| `cards-9:TK4` | The brain may decide on a coin it already holds (20 open, 40 a day) | KEEP | KEEP as a safety valve. | RECORDED: jarvis/service/brain.py:62-63 MAX_OPEN = 20, MAX_PER_COIN = 2; :40-41 DAILY_MAX default 80 (a ceiling), DAILY_USD default 1.00. |
| `cards-9:GATE-27` | The Engine Acceptance Gate (27 checks) | KEEP | KEEP; MODIFY: make "sizing" wait for the 20 fills "execution" asks for, and keep "regimes" strict. | DONE: 9d65d5d: jarvis/service/evidence_live.py:889 SIZING_ENTRIES = 20, :924-929 sizing stays PENDING under 20 entries; acceptance_gate.json engine_sizing pass_mark '0… |
| `cards-9:R24` | Tuning the deep-dip buy E6 (4 variants pre-registered, 3 run) | RETIRE | RETIRE as a trading idea; keep the record only for the live-versus-replay check (Q1). | RECORDED: strategy_status.json EXPLORER: EVIDENCE, wont_take_again, wakes_brain false; its why keeps the record for '(Q1 live-vs-replay)'. |
| `cards-9:CONV-9` | Conversation checks (Oct 9), agent exam (Oct 11, 13) and voice exam (Oct 11) | KEEP | KEEP; MODIFY the judge only before running the exam. | DONE: 7ef1188: jarvis/service/exam.py:12-13 'a judge is changed only BEFORE a run. rejudge() ... is marked ("rejudged")'; evidence_live.py:1002-1003 shows the mark on the… |
| `cards-9:UR2` | Universe Rule v2: watch every coin, judged by tier | KEEP | KEEP. The one gap: "both regimes" cannot be met until Bitcoin has a falling spell (see U-LADDER). | RECORDED: docs/UNIVERSE_RULE_V2.md section 2 (tiers) and section 8 ('at least 10 independent market days ... in both market regimes'). exposure.dial_by_day (live, read-only)… |
| `cards-9:U-BOOKS` | Every daily rule on every coin, with per-tier random baselines | KEEP | KEEP; do not read 5-day numbers. | RECORDED: docs/UNIVERSE_RULE_V2.md section 8 (beat same-tier random over 10 independent market days, both regimes) and docs/research/RESEARCH_RULES.md section 2 ('Count… |
| `cards-9:U-ZONE` | The zone touch on every coin: 0 wins in 56 | RETIRE | RETIRE as a trade (already done); KEEP the recording as the zones baseline. | RECORDED: strategy_status.json ZONE_TOUCH: EVIDENCE, wont_take_again, wakes_brain false; brain.py MONITOR zone_entry -> ZONE_TOUCH (A5, 16fbf74): logged, never sent to the AI. |
| `cards-9:U-15M` | The 15-minute Explorer shadows on every coin | KEEP | KEEP as shadows; MODIFY: log compare_lab10 nightly and alert under, say, 60% agreement, because a… | DONE: 10aad54: universe_explorer.compare_nightly (:225-244; bar 60%, min 20 events, 72h) runs in universe_watch.run_daily (:681); forward() files a weekly request… |
| `cards-9:U-REBUILD` | The nightly rebuild: can yesterday be reproduced? | KEEP | KEEP; MODIFY: report the "explained" breakdown by reason each night, so a growing category is seen. | DONE: 10aad54: universe_watch.explain_unlogged (:266 EXPLAINED_BY: busy, same_episode, held_back_by_trade_guard, before_books_started, tier_changed); rebuild stores… |
| `cards-9:U-LADDER` | The promotion ladder, rule versions and the push pipe | KEEP | KEEP; PARK expectations: say out loud that the first promotion is months away unless the regime turns, and… | DONE (`OD-WORKER-HARDENING`): strategy_status.json 'pushed' text now says the first promotion may take a while; Madhav confirms a phone note arrives under OD-WORKER-HARDENING. |
| `cards-9:U-WHYNOT` | "Why didn't you take X" and the missed-move loop | KEEP | KEEP; RE-TEST via #38 before any breakout rule trades. | PARKED_WINDOW (`PW-BREAKOUT-38`): Rule B: a new crypto rule's history test waits for the window. |
| `cards-9:BRAIN-2` | Ranked wakes, the $1 budget, and what the brain never sees | KEEP | KEEP; MODIFY one thing: nearly all wakes now come from zone entries (a retired trade idea kept as a trigger… | DONE: 16fbf74 (A5, Oct 15): brain.py:43-55 MONITOR zone_entry/explorer/hunter/squeeze are logged, never sent to the AI; expectation and dial_open rank 2.0, setup:H07 3.0… |
| `cards-9:U-ACCOUNT` | The would-be $2,000 account (signals sized like real money) | MODIFY | MODIFY: filter the take list by strategy_status before simulating, because a would-be account full of… | DONE: 7ef1188: jarvis/service/universe_watch.py:630 would_be skips any watch where strategy_status.counts_watch(w) is false (only ACTIVE/UNDER_REVIEW count): zone touches… |
| `cards-9:LOT-LAKE` | The 120-coin lake as the era's history bench | RE-TEST | RE-TEST: run Q9, then re-run review #26's H07 cell on a point-in-time tier-A list. | DONE: Q9 = review #30 (db24eed pre-reg, 9950d53, 905cca8 result: T3-B passes on PIT10, +3.7% vs holding -31.9% in 2024-26; 'Q9 leaves the queue'). |
| `cards-9:R25` | The benchmark and the exposure dial | KEEP | KEEP; nothing to do but let a closed-dial spell happen. | RECORDED: docs/research/REVIEW_25_RESULTS.md (dial v1 = GATE50_200); jarvis/service/exposure.py; strategy_status.json evidence_window (Rule A: 'both market-dial states seen')… |
| `cards-9:R26` | The expected-value table: 36 cells, one edge | KEEP | KEEP; RE-TEST on point-in-time tier A before real money rides it. | DONE: Review #29 (77083dc frozen pre-reg, 6fc4245 coverage gate min 99.17%, e44328d result): H07 tier A dial CLOSED PASSES point-in-time on 530 Binance pairs, dead coins… |
| `cards-9:FIX1-5` | Engine fixes: dial wiring, EV ranking, R sizing, the hurdle, fidelity | KEEP | KEEP; MODIFY later: wire fidelity to an alert so a decaying cell is announced, not just displayed. | DONE: 7ef1188: jarvis/service/ev.py:119 fidelity_alert (a BELOW BACKTEST cell -> one request by ananta-auto + a phone note, once per cell), called in universe_watch.run_daily… |
| `cards-9:R27` | Stops on dip buys: no stop wins; a plain zone touch loses with every stop | KEEP | KEEP; RE-TEST on point-in-time data (same run as R26's). | DONE: Review #29 (e44328d) re-ran H07's live exit (RSI over 40 or 10 days, no stop) point-in-time with dead coins in (530 pairs, LUNA kept): dial CLOSED net +6.45% / +5.27%… |
| `cards-9:R28` | The brain's trigger points follow the evidence | KEEP | KEEP; MODIFY next: give attention spikes and zone entries their own measured table, as the daily rules got… | PARKED_WINDOW (`PW-ATTENTION-TABLE`): A measured table for attention spikes is a new history study: post-window under Rule B; list it in docs/LOCK.md. |
| `cards-9:BOOK500-BT` | The $500 NDAX book: rules and backtest | KEEP | KEEP as the account; RE-TEST the edge sleeve on point-in-time data. | PARKED_WINDOW (`PW-BOOK500-PIT`): Judgment call. S2 (~2026-10-25) re-runs the $500 backtest with measured spreads (RESEARCH_RULES.md section 5); that is a cost re-run, not a PIT one. |
| `cards-9:BOOK500-BRAKES` | Brakes, resting stops and the retirement rule | MODIFY | MODIFY: code the retirement rule (it is the project's only automatic "stop trusting a setup" mechanism) and… | OWNER_DECISION (`OD-BOOK500-BRAKES`): DONE: 10aad54 jarvis/service/ev.py:150 retirement_watch (last 20 closed tier-A trades averaging below 0 -> one request + phone note, nothing switched off), in run_daily… |
| `cards-9:LEARN` | The learning loop: cards, Sunday review, credit, rebuild, examples, peers | MODIFY | MODIFY: fix rebuild_brain's insert (give the brain rebuild its own table or match the 8 columns, and never… | SCHEDULED (`SUNDAY-REVIEW`): DONE: e32b668 learning.rebuild_brain writes the 8-column rebuild_log row and lets failures surface (learning.py:255-286); rebuild_log has 3 source='brain' rows, latest… |
| `cards-9:BOOK500-LIVE` | The live $500 paper book, Oct 11-14 | KEEP | KEEP; no judgment before 20 closed setup trades. | RECORDED: docs/research/BOOK500.md 'Retirement rule' table, row 'Before 20 trades: Nothing is decided'; ev.retirement_watch flags only with 20 closed (RETIRE_N = 20); gate… |
| `cards-9:H07-FWD` | The dip trade's forward record: 8 of 8, one day, wrong regime | KEEP | KEEP; resist headlining "8 of 8" to anyone; count market days, not trades. | DONE: 7ef1188: jarvis/service/views.py:852-853 h07_fires = COUNT(DISTINCT day) (market days, not fires); ledger Q6 '10 market days with a live H07 signal' (TK17); no '8 of 8'… |
| `cards-9:OFFICER` | The account officer's daily note | KEEP | KEEP; MODIFY: force the currency label into the template (write "C$"), not the model's discretion. | DONE: 7ef1188: jarvis/service/officer.py:101 cad_labels turns an account figure like '$498' into 'C$498' by code, applied at :133. |
| `cards-9:STATUS` | strategy_status.json: one list of what still trades | KEEP | KEEP; MODIFY: compute the "why" numbers from the database at read time instead of freezing them in the JSON… | DONE: d2a0dc9: strategy_status.json reasons carry {closed} {won} {net} tokens, filled at read time (render_why, per_strategy); the Explorer is counted from its whole closed… |
| `cards-9:LOSSES` | The loss classification (/v3/verdicts) | KEEP | KEEP; MODIFY: stamp each trade with the verdict in force at entry, so the history stays honest as verdicts… | DONE: d2a0dc9: strategy_verdicts table + verdict_in_force (strategy_status.py); record_verdicts every 15 min (app.py:1661); backfilled: rows from git 11+5+1+1 and 13… |
| `cards-9:LOT-FEED` | The 394-coin live feed (universe_bars) | KEEP | KEEP; extend daily backfill further back if a feed-based study is ever wanted. | RECORDED: Standing KEEP; the backfill is owed only if a feed-based study is proposed. docs/UNIVERSE_RULE_V2.md section 6: 'Rules that need history wait for it (60 days for daily… |
| `cards-9:LOT-PAPER` | What ten days of paper (Oct 4-14) can and cannot prove | KEEP | KEEP collecting; re-read every scoreboard when the first dial-closed spell ends. | SCHEDULED (`EV-DIAL-CLOSED`): Collecting: nightly universe rounds (daily/universe_2026-10-09..15.md); books still record (ZONE_TOUCH-UB last entry 2026-10-15 15:44 UTC). |

### Reconstruction fixes (the 11 fixes, P10 and bugs 4-5)

Items from the full reconstruction of the system. 14 rows.

| Row | What | Verdict | Standing | Now |
|---|---|---|---|---|
| `recon:Fix 1` | Reconstruction audit Fix 1 | - | - | PARKED_WINDOW (`PW-HL-RX`): New study (re-pull fills, pre-registered join, case 0001): post-window, e.g. with the QUARTERLY HL refresh. |
| `recon:Fix 2` | Reconstruction audit Fix 2 | - | - | DONE: e32b668: learning.py:255-287 rebuild_brain calls evidence_live._rebuild_table, inserts 8 values, no blanket except; tests/test_learning.py:74-80 on the real table… |
| `recon:Fix 3` | Reconstruction audit Fix 3 | - | - | DONE: e32b668: learning.py:424 close_counterfactuals (close_case at the case's 4h horizon on 1h bars), nightly at universe_watch.py:705; test… |
| `recon:Fix 4` | Reconstruction audit Fix 4 | - | - | DONE: evidence_live.reconstructable checks the 15-minute snapshot stream (no gap over 35 minutes in the last 2 days); gate text and tests updated. Live: PASS, 8 of 8 parts. |
| `recon:Fix 5` | Reconstruction audit Fix 5 | - | - | PARKED_WINDOW (`PW-BREAKOUT-38`): Live: #38's pattern is 10 rows on 3 market days (Oct 8-10); its text still says '10 times'. |
| `recon:Fix 6` | Reconstruction audit Fix 6 | - | - | DONE: e32b668: universe_explorer.py:209-224 like-for-like figure on setups both run; 'same engine and rules' note replaced. |
| `recon:Fix 7` | Reconstruction audit Fix 7 | - | - | DONE: brain.settle_unreviewed stores 1-day and 5-day excess over the universe median; settle_passes fills earlier PASS rows; ranking_audit adds avg_5d_ex_pct; test added. |
| `recon:Fix 8` | Reconstruction audit Fix 8 | - | - | RECORDED: RESEARCH_RULES.md §7 'The casebook' (3505615): cases.json the day they happen, entry-time reason, losers in, 30+ cases before re-testing an entry read. |
| `recon:Fix 9` | Reconstruction audit Fix 9 | - | - | DONE: Evidence page rebuild.books lists every book the nightly check covers; the Reconstruction screen has a Coverage per book card; tsc clean. |
| `recon:Fix 10` | Reconstruction audit Fix 10 | - | - | PARKED_WINDOW (`PW-LEDGER-GENERATE`): Not generated: still hand-written; the check's docstring says prose counts (65 vs 105) are not caught; Q1's stale text passes. |
| `recon:Fix 11` | Reconstruction audit Fix 11 | - | - | RECORDED: RESEARCH_RULES.md §8 'New markets' (3505615). canada/schema.py keeps close_raw, close_tr, dividend, capital_event, delisted apart (0462e4a)… |
| `recon:P10` | Reconstruction audit P10 | - | - | DONE: 10aad54: universe_watch.py:266-287 EXPLAINED_BY + explain_unlogged(); rebuild() records explained_by_reason per signal, an unexplained one goes to only_in_rebuild and… |
| `recon:Bug 4` | Reconstruction audit Bug 4 | - | - | RECORDED: Still imported only by tests/test_paper_lab.py:14. docs/knowledge/layers.json component LEGACY_LAB (status ARCHIVED, acts false) lists… |
| `recon:Bug 5` | Reconstruction audit Bug 5 | - | - | SCHEDULED (`SUNDAY-REVIEW`): A file exists: docs/repair_shop/weekly/2026-10-14.md ('Weekly situation review, 2026-10-07 to 2026-10-14', 248 decisions), committed fb8eaf7 (a Wednesday: run by hand)… |

## 5. The follow-up doubts (D128-D170)

After the cards, 43 further doubts were checked against the live files. Each was either fixed, corrected by an erratum, handed to an owner or recorded.

| Doubt | Topic | Status | Where it went | What was found and done |
|---|---|---|---|---|
| `D128` | Cost placeholders: the CFG-SPEC 0.08%, the G8 8 bp haircut, the 0/4/8/10 bp fee tables and the Blueprint's '8 bp kill' | `ERRATA` | `E-001`, `E-002` | Four frozen Grok-era scripts charged 0-10 bp for a round trip; real paper cost on the lab coins is 0.57-1.20% (errata E-001, E-002). cfg_spec.py now marks 0.08% a superseded placeholder, ndax_costs.py records when the fee was checked, and SD6 defaults to the NDAX profile (paper_exit.py). |
| `D129` | The NDAX spread table: copies, sample count and the brain's cost wording | `DONE` | `S2-SPREADS` | ndax_costs.py is the one dated table (ten modules import it). Its sample count is now 5, as CANDIDATE_V3.md recorded, not 1; RESEARCH_RULES.md, the test and the brain and stance wording (0.6-1.2% on the ten lab coins, 0.8-2.4% on other coins) agree. Measuring the other coins is S2. |
| `D130` | ETH has no 15-minute rows from April to early September 2026 | `ERRATA` | `E-003` | Merged tape, freeze copy and Binance set all lack ETH from 2026-04-01 to 09-03; the monthly files for those months are ETHFIUSDT, a different token. The lake has full ETHUSDT data, so any re-run reads the lake. |
| `D131` | Kraken USD to Binance USDT on 2026-04-01 with no conversion | `ERRATA` | `E-004` | Kraken bars pass 3x their volume average on 7.4-8.6% of bars a month and Binance bars on 2.9-4.1% in the same months, so the halving of the H1 gate rate in 'OOS' comes from the venue change. |
| `D132` | 'vz' is a volume ratio, not a z-score; PD-1 measured something else | `ERRATA` | `E-005` | Every SET and H1 script uses volume over its 20-bar average; PD-1 used a true z-score, other era cuts and 1000PEPE, so its 'stable ~7%' does not describe the H1 gate. The live repo already has the naming rule. |
| `D133` | SET4's hot bit, the retracted 14-cell pass and its continuation bar | `ERRATA` | `E-006` | SET4's hot bit is 2x volume, not the 3x its document states; the 14-cell list was retracted on 2026-09-12; its continuation bars sit below the rate at which all events continue. |
| `D134` | H1, SET14, SET16 and HOT numbers that differ between files | `ERRATA` | `E-007` | Re-derived on the freeze copy: H1's sealed lift 2.69 rests on 8 events on 4 days (history lift 2.06); SET16 OOS is 76 (the 49 is a different object); lag births 194; HOT births 353. |
| `D135` | 'OOS' means four different windows | `ERRATA` | `E-008` | Sep 1-11, from 2026-08-01, from 2025-08-01 and 'late from 2022' are all called OOS in Grok-era files; ETH's September bars were already inside the discovery files. |
| `D136` | H6, SET1, SET2 and the research catalog: stale statuses | `ERRATA` | `E-009` | H6 was tested (INSUFFICIENT, 8 events) though the registry says pending; SET1/SET2 closed with all set hunting; the catalog lacks H2-H5. |
| `D137` | Grok-era scripts step by row, not by clock | `ERRATA` | `E-010` | Where bars are missing '1 hour' is longer: 55% of pre-2016 bars and 3.7% of 2016-2021 bars are followed by a gap. |
| `D138` | Smaller script defects, including DOGE's zero-volume bars | `ERRATA` | `E-011`, `E-012` | RELEASE never coded, SEQ2 pools both signs, per-bin era rates only on screen, and the GAP state is DOGE alone (zero-volume April-August bars that are not Binance spot data). |
| `D139` | No code loads the Grok-era packs; the knowledge catalog's n of 0 for SET14 and HOT | `DONE` | `E-013` | E-013 records that load_pack was never built and nothing reads those files. knowledge_catalog_v1.json now carries n_split (early/late/OOS counts) on the SET14 and HOT cards; ranks do not change. |
| `D140` | context_cites_deployed gated nothing; the first seven agent_decisions rows; MRD cards show n 0 | `ERRATA` | `E-014`, `E-015` | The flag was only a label and 1,136 decisions cite the sync card under it (E-014); the first seven rows predate the decision writer (E-015). cite_allowlist.py comments now say so (LIVE_5 unchanged) and the MRD cards carry n_split. |
| `D141` | Citation is not influence: no log shows a card changed a decision | `OWNER_DECISION` | `OD-CARD-INFLUENCE` | No log re-runs a decision without its card. RESEARCH_RULES.md no longer says tools for this exist. Options on the due list: a post-window sample re-run with one card removed, or never claim influence. |
| `D142` | Audit v1 has no Grok-era rows and none for reviews #16-#30 | `ERRATA` | `E-016` | AUDIT_V1.md now says it is not complete and points to AUDIT_V2; relationship_registry.sqlite stops on 2026-09-12 (E-016). The missing rows are in this register. |
| `D143` | v1 row corrections: Hunter/Squeeze live results, the blanket reason, R15, H14, Q3 | `DONE` | - | Written as the 'Corrections to v1 rows' section of AUDIT_V2.md; audit_v1.json stays frozen. The E5 status card, the ledger and the register agree that Q3 ended on 2026-10-15. |
| `D144` | Stale watch, status and alert text (Squeeze, M2a-G, E3, ZONE_TOUCH, reads_status) | `ALREADY_FIXED` | - | acdd3fd, 72cb592 and e32b668 had fixed the watch, status and phone-alert text. The last stale file, reads_status.json, now carries a status_note that review #15 found M2a-G not supported. |
| `D145` | EXPLORER and E5 cards still say permission PAPER; T3B card said tier ALL | `OWNER_DECISION` | `OD-E5-PERMISSION` | The T3B card tier is now LIVE10 (reviews #22 and #30 never tested ALL). Whether the EXPLORER and E5 cards become CONTEXT is Madhav's call. |
| `D146` | Zones status record: review-6 PASS under a FAIL, CONFLUENCE in supported lists, strength_matters | `ALREADY_FIXED` | - | 0f0dfcf and acdd3fd: zones_watch reads only 'status'; CONFLUENCE is out of the supported lists (test_zones.py pins it); strength_matters is false. |
| `D147` | Hypotheses and layers text out of date (H07/H08/H09/H16, TEACHERS, FUTURES_CONTEXT) | `ALREADY_FIXED` | - | acdd3fd set H07 SUPPORTED and H08, H09, H16 REJECTED, refreshed the header date and the layers text. |
| `D148` | READS still wakes the brain; BOOK500 'while the dial is closed' | `OWNER_DECISION` | `OD-READS-WAKES` | The BOOK500 wording now says the H07 sleeve buys only while the dial is closed and sits idle while it is open (2 fills, both core). Whether READS keeps waking the brain after review #15 is Madhav's call. |
| `D149` | RANDOM_* watches and a unit test for them | `DONE` | - | e32b668 fixed the strategy matching; tests/test_strategy_status.py now asserts RANDOM_10D, _20D, _30D, their -U copies and RANDOM_BOLD all map to RANDOM. |
| `D150` | Ledger wording: E6-E8 'never traded', T3 MAIN 'you approve', sample counts | `DONE` | - | d0c45bc fixed R3 and the T3 row; the same correction is now in R4 (MAIN has been automatic since 2026-10-02) and REVIEW_2_RESULTS.md has a sample note (105 accounts drawn, 65 collected). |
| `D151` | HL-RX has no result file | `DONE` | `PW-HL-RX` | docs/research/HL_RX_RESULT.md is written from the only surviving record (the Status document of 2026-09-27). Looking again is post-window. |
| `D152` | Casebook buy C3 matches no candle | `OWNER_DECISION` | `OD-C3-PRICE` | 109.00 CAD on 2026-08-10 is 0.43% above that week's highest Binance price and 1.32% above the day's own high; two bar copies agree. Madhav reads the fill from NDAX history, or C3 stays 'not matched to a bar'. |
| `D153` | Scorecard E3 row, MTF duplicate variants, V07 order | `DONE` | - | EXPLORER_V0_SCORECARD.md shows E3 CONFIRM -$0.28 (n 9); the MTF study notes 18 of 108 variants are exact copies; VARIABLE_REGISTRY.md and variable_registry.json have V07 in the right order. |
| `D154` | Decision-quality baseline, the old app's 'proven' Tier-1 label, '+15m' means | `DONE` | `E-017` | DECISION_QUALITY_V0.md has a dated Sep 1 re-run note (the +4h 'slight protective' read did not hold); +15m means are errata E-017. The old app's Tier-1 label and the rsi-momentum note are corrected on the branch lock-labels in ~/code/Ananta; main is untouched for Madhav's review. |
| `D155` | Empty universe_knowledge and setup_memory files, five test rows, S5-H2 'done' | `DONE` | `E-018`, `E-019` | Errata E-018 and E-019 name the right copies and the test rows; ROADMAP.md now says the H2 tool only prints and no histogram was saved. |
| `D156` | The overwritten exit map and the fade ledger | `ERRATA` | `E-020`, `E-021` | lab_exit_map_1h_raw.json was overwritten by a Hunter-only rerun; every fade tick was written twice and priced 1-2 hours late, so its hit rates are not evidence. |
| `D157` | N3 and N4 sign counting and the execution wall | `ERRATA` | `E-022` | n4_score.py counts agreement in either direction (a bar that passes 37.7% of rows on coin flips) and the 'not authorized' gates were never in the campaigns' path. |
| `D158` | The S2 split files carry the Squeeze log under Hunter names | `ERRATA` | `E-023` | All three split files are the 57-trade Squeeze log; two are identical; no split was ever computed for Hunter's 16 trades. |
| `D159` | MRD rules file, two 'Watch Score' formulas, EXHAUSTING, the Foundation Map, MRR-3 | `ERRATA` | `E-024`, `E-025` | The transfer-entropy rejection was written before the test ran; 'Watch Score' names two formulas; EXHAUSTING tests volume only; quiet became more common, not stickier. |
| `D160` | What the regime column means, and why every row reads ALLOWED | `RECORDED` | `EV-DIAL-CLOSED` | Verified: ALLOWED means Bitcoin's last closed day is above its 50-day average, and it was every day from 2026-09-20 to 10-14, so all evidence rows read ALLOWED. No fix. No universe rule can be promoted until a regime with the dial closed has been seen. |
| `D161` | Pre-registration timestamps and multiple testing | `DONE` | `PW-PREREG-GUARD`, `OD-MULTITEST` | Reviews #16, #17, #18, #20 and #23 carry an 'Unanchored' note and RESEARCH_RULES.md states the look count correctly (reviews #15-#23, about 97 cells). A code guard is post-window; the family-wide correction is Madhav's call. |
| `D162` | Numbers that differ between files (closes, incomplete days, breadth, NDAX counts, grades, H07 control) | `DONE` | - | SYSTEM_MAP.md, REVIEW_15/16/17 results and BOOK500.md are corrected or carry an erratum; the H07 control differs only in its baseline; 531 vs 530 was fixed in 3432f8d. |
| `D163` | The lake holdout is not fresh | `DONE` | - | RESEARCH_RULES.md section 4 says why (Candidate v3 spent 2026-08-01 to 09-12; live paper has run since 2026-09-29); 'sealed' in reviews #29 and #30 means 'not loaded'. The next holdout is live data after a stated date. |
| `D164` | Report numbers: random baseline label, trade-count label, files outside the backups | `DONE` | - | The Evidence page says 'Explorer random entries' and splits the scored count into Explorer trades and evidence-book trades; the nightly backup also copies explorer_state.pkl and the paid-search log. |
| `D165` | The free web-search key is rejected; free-search counts are not recorded | `OWNER_DECISION` | `OD-GEMINI-KEY`, `PW-FREE-SEARCH-LOG` | Only paid checks (8 a day for the brain) can veto until the key is replaced. Logging free-search counts is a small post-window change; the paid log is now in the backups. |
| `D166` | Variable registry vs Explorer rules (V12, V13 DROP; V08) | `DONE` | `OD-RULEBOOK-S1S3` | VARIABLE_REGISTRY.md and variable_registry.json now say rulebook v0 still uses S1 and S3 and that V08 gates LONG_TERM. A v1 rulebook without them is Madhav's call after the window. |
| `D167` | Both candidate books idle; the V1 breaker still TRIPPED | `OWNER_DECISION` | `OD-CANDIDATE-BOOKS` | Last events Oct 8; the breaker has been TRIPPED since 2026-10-08 and needs a human. Retire both (recommended) or resume V1. |
| `D168` | The V4 drawdown rule measures dollars against starting capital | `DONE` | - | STUDY_V4_RESULTS.md has a reading note and RESEARCH_RULES.md section 6 defines drawdown as the percentage fall from the running peak. The study is frozen and its verdict stands. |
| `D169` | The '5y' label, 'reviews #1-#28' and the 'Fiverr' data | `ERRATA` | `E-028`, `E-029` | The 15-minute ingest's '5y' window is 4.55 years; the Fiverr vendor history was never delivered. MARKETS_PLAN.md now says reviews #1-#30. |
| `D170` | Worker recorder copies, lake outage counts, renamed tickers | `PARKED_WINDOW` | `PW-RENAMES`, `PW-QUALITY-GAPS` | The worker's files are already pulled nightly (a7f09b4). The lake quality check keeps only the 10 longest gaps and the lake does not join renamed tickers: both are code changes that wait for the window. REVIEW_30_RESULTS.md carries the erratum (62 coins, not 64). |

## 6. What was not changed

- `audit_v1.json`: frozen 2026-10-05, untouched. `AUDIT_V1.md` got a header note and corrected row counts; its ratings are as they were.
- The Grok-era files, which sit untracked in a flat folder on the Mac: never edited; corrected by `GROK_ERA_ERRATA.md` (E-001 to E-029).
- The old app (`~/code/Ananta`): main is untouched; two label fixes are on a branch for Madhav's review.
- No strategy was started, resumed or promoted, and no rule was re-tested. Re-tests wait for the end of the evidence window (Rule B).

