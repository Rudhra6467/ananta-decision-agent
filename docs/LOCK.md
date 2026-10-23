# The crypto lock (2026-10-15)

On 2026-10-15 Madhav asked to lock the crypto system: "so now lets complete this crypto system and lock it", and that morning, "we will park it for daily reconstruction process and updates reviews, everything else should be completed." From that day the crypto system runs as it is, on paper, and has to prove itself. This page says what runs, what is frozen, what decides success, who may change what, what waits for Madhav and what waits for the end of the window.

The page was checked a second time on Oct 15 evening by an independent review (18 findings, each fixed or stated in section 7). It is checked by `tests/test_crypto_lock.py` (the frozen items), `tests/test_due_list.py` (the dates) and `tests/test_audit_register.py` (the audit). Every audit card has a final status in `docs/research/AUDIT_V2.md` and `docs/knowledge/audit_register.json`.

**Updated 2026-10-20** with Madhav's decisions of that day (section 8, "Decisions of 20 Oct"). From that update this page is edited by hand: `~/ananta_runs/build_lock_md.py` (Oct 15) wrote it from the live files and fixed prose, and it knows none of the Oct 20 changes, so running it again would overwrite them. Do not re-run it; if it is ever wanted again, its prose and tables must first be brought up to this page.

**Updated 2026-10-21** with Madhav's answers of 09:41 Toronto ("Complete all pending tasks and all that are waiting for me. I approve all." … "for all the recommeneded items , its yes."): every open decision takes Claude's recommended option, the gate bundle and the live-code reliability fixes are in (section 8, "Decisions of 21 Oct").

## 1. The window and the rules that end it

- **Evidence window:** day 1 was Oct 15 and it needs 60 market days, so it ends about Dec 14 (`evidence_window` in `docs/knowledge/strategy_status.json`).
- **Rule A (real money):** none until 60 market days have passed, BOTH dial states (open and closed) have been seen, and the $500 book's execution fidelity is within 3 points of its backtest. Then the Acceptance Gate, then a tiny live step, and only with Madhav's written yes.
- **Rule B:** no new crypto strategies during the window. A re-test of an old idea, a new study or a build that adds analysis waits for the end of it, unless it is a tiny document, config or test fix. Ideas go to the after-the-window list (section 9).
- **Paper only.** Passwords are never handled by Claude. No account, licence or spending without Madhav's OK.
- **Other traders** are reference and event generators, never teachers or copy signals (D8).
- **Canada (C0)** is deferred until crypto is done. It never shares data, findings, parameters or files with crypto, and nothing Canadian wakes the agent.

## 2. What runs by itself

| When | What |
|---|---|
| always on | `com.ananta.jarvis`: the eye reads live prices every 10 seconds (stops and alerts, Bitcoin shocks, zone entries), the universe feed keeps every watched coin's prices, runs the 5-minute shadow step and the daily close, the brain decides on the moments they flag, and the health watchdog checks every part every 2 minutes and sends a phone note when one goes quiet. `com.ananta.explorer` runs the Explorer (from main), `com.ananta.website` the public site, `com.ananta.voice` and `com.ananta.telugu` the speech servers, `com.ananta.tunnel` the link to the app, `com.ananta.awake` keeps the Mac awake. launchd restarts them after a crash and at log-in; the job files are checked with `plutil -lint` by the checkpoints (the Jarvis file was found corrupt and repaired on Oct 15 evening; `scripts/install_jarvis_job.sh` rewrites it). |
| always on (from Oct 20) | `com.ananta.hands`: Hands, the paper order service the trend books and the Explorer send their paper orders through (`127.0.0.1:8001`), is a launchd job, so launchd restarts it after a crash and at log-in (#71, bc0a6c1, Madhav's yes of Oct 20 09:39; killed on purpose and back in 8 s). Before it, a 426-minute Hands outage on Oct 17 cost two trend-book buys (TRX, WLD). |
| every 5 minutes | the outside watchdog (`com.ananta.watchdog`, `scripts/jarvis_watchdog.py`): two failed looks at Jarvis in a row, or its health checks silent for 10 minutes, send a phone note. It never restarts anything. |
| every minute | the worker Mac records NDAX and Binance bid and ask, USD/CAD and whether the public page answers. Its phone alert for a main-Mac outage is not counted as armed until Madhav confirms the test note (`OD-WORKER-HARDENING`). |
| every hour (worker Mac) | `com.ananta.worker.hlcapture` (`worker/hl_capture.py`): other traders' fills, data only: every finished UTC day of 59 public Hyperliquid accounts (review #2's fixed sample, less its 6 market makers), one file per day, catching up after a sleep (`OD-HL-FILLS` (a), Madhav, Oct 20). It installs itself when the worker Mac is back online (#72); until then nothing is captured. Reference only, never a copy signal (D8). |
| every 15 minutes | the Explorer scans one minute after each 15-minute close (evidence only); Jarvis's 15-minute jobs run (value history, alerts, the reads watch, following the stance's expectations, phone notes). |
| daily close (about 00:05 UTC, 8 pm Toronto in summer time) | the daily rules on every tier and their rebuild; the brain's moments; every book re-checked against its candles (the Explorer replay, every evidence trade, Jarvis's trades, both trend books, the $500 book's fills and sizes, the 15-minute snapshot stream); the $500 book's step at NDAX's live quotes; the fidelity check (a cell 3 or more points under its backtest is forwarded by itself); the stance and the bold book; the officer's note; the due list (an overdue item becomes one repair-board request); the evening review. |
| 03:20 | the old app's database archive (`com.ananta.mongoarchive`). |
| 03:40 | database backups, 14 days kept, Sundays also to R2 (`com.ananta.backup`, `scripts/backup_db.py`); from the night of Oct 16: the Explorer's live state and the paid-search log are copied beside them, the worker's finished days are pulled in, and a copy of the newest backups (no logins, conversations or guests' books) goes to the worker. From Oct 23 `com.ananta.workerpull` retries the worker pull at 04:20, 05:20, 06:20, 07:05, 08:20 and 09:20 until the day lands (Madhav's yes, #72). |
| 04:30 Toronto (from Oct 20) | `com.ananta.othersdaily` (`src.research.others_daily`): rebuilds yesterday's other-traders trades on our coins and sorts each one: we had a rule and took it / we had a rule and passed (and why) / no rule of ours covers it / they lost after costs. A situation that repeats on 3 days in 7 files a draft request, never a rule or a copy signal (D8). It reads the worker's daily fill files, so it has little to read until the worker capture runs. |
| every 15 minutes (from Oct 21) | each 15-minute run writes one line to `~/ananta_runs/jobs_steps.jsonl` with every step's error (empty when all went well); the run checker reads it (`jobs_steps`). The outside watchdog's `watchdog.log` lines and the health watchdog's last check (`health_state` row `_last_check`) carry a time, so the checker can date them. |
| daily close (from Oct 21) | `learning.count_lessons`: each brain decision is labelled once, under its own week, as soon as its result can no longer change; a lesson kind reaching 3 cases in a week files one repair-board request (never twice while one is open). Decisions from Oct 21 on are counted but not labelled until Dec 15, so the forward tests stay blind. |
| 07:25 Toronto | the morning review, a scheduled task: health, evidence, the gate, the repair board and the due list; one page in `docs/repair_shop/daily/`. It works the board and never changes a trading rule. |
| Sundays | the weekly situation review (`docs/repair_shop/weekly/`), written by the daily close of Sunday 00:05 UTC (Saturday 8 pm Toronto); the research lake is extended at 02:15 Toronto (`com.ananta.lake`, `scripts/lake_weekly.sh`; launchd reads the Mac's own clock; this page said 02:15 UTC until Oct 20); the agent exam runs at 07:10 Toronto (`com.ananta.exam`, `scripts/run_agent_exam.py`, about $1.30 a run, `OD-EXAM-CADENCE` (a), f6d70cd; first run Oct 20 09:51: 20 of 20 'knows', 10 of 10 'doesn't know', 5 of 5 'why'). |

## 3. What is frozen

A frozen item changes only with Madhav's recorded yes. `tests/test_crypto_lock.py` hashes each one and fails the build when a hash differs from the one in `docs/knowledge/crypto_lock.json`, or when a re-pin has no recorded approval. To change one: undo the change, or (Madhav's decision only) add an entry to that item's `history` in `crypto_lock.json` with his approval, a note quoting what he decided, and the new hash.

| Frozen item | What it freezes | Where |
|---|---|---|
| `book500_rules` | The $500 book's rules as coded: coins, filters, sizing, stops, exits, brakes and fills (code of src/research/book500.py; comments and docstrings are not counted). | `src/research/book500.py` |
| `exposure_dial` | The exposure dial and its four measuring books: review #25's rules (code of src/research/review25.py) and the start date, book list and roles in jarvis/service/exposure.py. | `src/research/review25.py`, `jarvis/service/exposure.py` |
| `measured_edges` | The measured results the live rules rest on: the result files of review #26 and review #29, whole. | `docs/research/review26.json`, `docs/research/review29.json` |
| `paper_costs` | What the paper books charge: NDAX fee and half-spread table with its defaults (ndax_costs.py), the tier floors, fee literals and cost formula (registry.py), and SD6's cost profiles (paper_exit.py). | `src/intelligence/ndax_costs.py`, `jarvis/service/registry.py`, `src/intelligence/paper_exit.py` |
| `t3_rule` | The T3 portfolio rule (code of src/intelligence/portfolio_layer.py). | `src/intelligence/portfolio_layer.py` |
| `strategy_verdicts` | Each strategy's status, verdict and whether it wakes the brain, plus the evidence window and the account (docs/knowledge/strategy_status.json). Evidence counts are not pinned. Re-pinned Oct 21: READS wakes the brain no more (OD-READS-WAKES (a)); CANDIDATE retired (OD-CANDIDATE-BOOKS (a)). | `docs/knowledge/strategy_status.json` |
| `gate_definition` | The Acceptance Gate's 27 checks: id, area, check, measure and pass mark (docs/knowledge/acceptance_gate.json). The daily readings are not pinned. Re-pinned Oct 20 for `engine_execution`'s new measure and pass mark (Madhav: "2. yes"). Re-pinned Oct 21 for the gate bundle (section 4). | `docs/knowledge/acceptance_gate.json` |
| `exam_judges` | How the agent exam marks the agent: the 'knows' and 'why' question lists and the 'why' pass mark, the 'don't know', certainty, forecast and hedge patterns, the voice rules and the five judging functions (jarvis/service/exam.py). The pass marks of the three exams are in `live_logic`. | `jarvis/service/exam.py` |
| `research_rules` | The research rules by their headings (docs/research/RESEARCH_RULES.md): pre-registration, counting looks, real costs, lake header, status from one file. | `docs/research/RESEARCH_RULES.md` |
| `live_logic` | The logic that decides money or the success verdict and sat outside the first nine pins (found by the independent check of Oct 15): how the dial is read (exposure.state, dial_by_day); what may enter the $500 book's edge sleeve (ndax_book.passed_rules, edge_signals); the trade guard's staleness limits and its list of paths; the exams' pass marks and run/rejudge/voice (exam.py); the gate's constants (EXAM_FRESH_DAYS, _exam_age, SIZING_ENTRIES, CITES_N, CITES_PASS, OUTAGE_MIN, ALERT_WITHIN_S, GOAL_EVENTS); Rule A's fidelity bar (ev.fidelity); the default cost profile (paper_exit.settings_for); the hand-written status of every gate check; and, from Oct 20, engine_execution's rule (EXEC_SINCE, EXEC_FILLS, EXEC_ACHIEVABLE, EXEC_MEDIAN_BPS, execution_reading) with the realism test it rests on (realism.NDAX_FEE, TOLERANCE_BPS, MAX_QUOTE_GAP_S, optimism_bps, score). Re-pinned Oct 20 (Madhav: "2. yes"). Re-pinned Oct 21 for the gate bundle's rules and constants (OUTAGE_DAYS, PART_OUTAGE_MAX_MIN, WORKER_BLIND_MAX_MIN, each check's expires_days). | `jarvis/service/exposure.py`, `jarvis/service/ndax_book.py`, `jarvis/service/trade_guard.py`, `jarvis/service/exam.py`, `jarvis/service/evidence_live.py`, `jarvis/service/ev.py`, `src/intelligence/paper_exit.py`, `docs/knowledge/acceptance_gate.json`, `jarvis/service/realism.py` |

**Not pinned:** the bold book (`jarvis/service/bold.py`, `docs/knowledge/bold_mandate.json`) and the brain's knowledge list (`brain.KNOWLEDGE`) sit under no pin. Their Oct 20 change (Madhav: "4. yes") is recorded as an amendment in `bold_mandate.json` and an erratum in `docs/research/PREREG_WINDOW_2026-10-20.md`, not as a re-pin.

The cost table changes the same way: the monthly spread check (`SPREAD-REFRESH`) and stage S2 only report the gaps; the table changes with Madhav's yes and a dated line in `ndax_costs.py`, and then the `paper_costs` pin is re-recorded.

Not frozen, but guarded: the Acceptance Gate's *results* move every day by design, and strategy *evidence* (trades, counts) accumulates; only the definitions above are pinned. Code pins count the lines of code only, so a corrected comment or docstring does not trip them; a changed number, name or line of logic does.

## 4. Success: the Acceptance Gate

The gate has 27 checks that must all pass at the same time. It is read daily on the Evidence page, and a pass can turn back into a fail. Its definition (`gate_definition`) is frozen; its readings are not. Twelve of the sixteen passes at the lock are statuses written by hand (section 7 names them); the other four and every non-pass are computed daily.

**From Oct 21 (the gate bundle, Madhav: "I approve all").** Six checks changed their measure: `strategy_baselines` reads the account's books (the $500 book and the books allowed to trade, `missed.book_allowed`) against their random twins, buy-and-hold and Bitcoin's 50-day rule, and needs 10 independent events (entries within 3 days are one event); `ops_outages` also counts part outages (a 10+ minute outage needs its phone note within 5 minutes and must end within 60) and the worker Mac's blind minutes (at most 420 in 7 days); `agent_cites` counts conversation answers only, never scheduled briefs or the stance; `agent_no_failed_rules` also checks the bold book; `strategy_regimes` counts independent events, not trades; every hand-written check carries an evidence date and an expiry (30 days, `engine_risk` 35) and an expired hand-written PASS reads PARTLY. The honest reading the day it went in: **18 of 27** (from 20): `strategy_baselines` PASS → PENDING (the retired Explorer no longer counts), `ops_outages` PASS → FAIL (the Oct 16 Hands and Explorer outages, which drop out of the 7 days on Oct 24), `agent_no_failed_rules` PENDING → FAIL (a bold buy listed FILTERS, a context-only idea), `agent_cites` FAIL → PENDING (3 of 8 conversation answers so far). The table below is the reading at the lock.

At the lock (Oct 15, read from the live service): **16 of 27 pass**; 3 FAIL, 2 PARTLY, 5 PENDING, 1 NOT_MEASURED.

| Check | What | At the lock | Reading | What it waits for |
|---|---|---|---|---|
| `data_correct` | Data: Correct | PASS | COCOS, BNX and LUNA cut | - |
| `data_complete` | Data: Complete | PASS | - | - |
| `data_pit` | Data: Point-in-time | PASS | - | - |
| `data_survivorship` | Data: Survivorship controlled | PASS | 30-coin tier (#22) and live 10 (#30, Oct 15) re-tested on their point-in-time tiers | - |
| `data_costs` | Data: Cost-aware | **PARTLY** | the 10 books' own coins costlier than assumed: ETH 0.45% a side measured against 0.284% in our table; NDAX measured on 3 full days and 1 part day,… | Stage S2 (about Oct 26) re-runs the $500 backtest with the half-spreads the worker Mac measured; Madhav decides about any coin whose real cost erases its edge. |
| `engine_reproducible` | Engine: Reproducible | **PENDING** | 15 of 30 nights in a row match | 30 nights in a row with no mismatch; it counts the nights that match in a row, so it can start over. |
| `engine_lookahead` | Engine: No lookahead | PASS | - | - |
| `engine_sizing` | Engine: Sizing correct | **PENDING** | 0 violations in 2 entries of the $500 book (needs 20); the 2018-2026 backtest: every size followed the rule | 20 live entries of the $500 book with no sizing violation (the book has had very few entries). |
| `engine_execution` | Engine: Execution assumptions | **PENDING** | 2 of 2 paper fills inside NDAX's bid and ask (needs 20); spreads measured by the worker on 3 full days and 1 part day | From Oct 20 (Madhav: "2. yes"): every paper fill of every book since Oct 12, judged against the worker Mac's independent NDAX quote for that minute (`realism.py`). PASS: at least 20 measured fills, at least 90% achievable, median optimism within 5 bp; FAIL below either bar; PENDING under 20. The old count could not fail (the $500 book copies its fill from the quote it was checked against); it stays in the note. `engine_sizing` stays on the $500 book only. |
| `engine_risk` | Engine: Risk controls | PASS | rehearsed Sep 30; next due Oct 30 | - |
| `strategy_oos` | Strategy: Out-of-sample | PASS | T3-B on 10 coins; the dip trade is weak | - |
| `strategy_universe` | Strategy: Broader universe | PASS | #15 | - |
| `strategy_survivorship` | Strategy: Survivorship | PASS | Live 10 passes (#30): +3.7% in 2024-26 vs holding -31.9%, much weaker than on today's 10 (+15.1%); the 30-coin tier failed (#22) and is evidence only | - |
| `strategy_baselines` | Strategy: Beats baselines | **PENDING** | 9 of 10 market events; real -$0.98 vs random -$1.14 per $100 | 10 independent market events with the book ahead of its random twin after costs. |
| `strategy_regimes` | Strategy: Failure regimes known | **PENDING** | H07 tier A: 1 events dial open, 0 dial closed; Jarvis's book: 6 events dial open, 0 dial closed (needs 10 each; the backtest's split is in… | 10 market events with the dial open and 10 with it closed. The dial has been open since August, so this waits for Bitcoin to fall below its averages (`EV-DIAL-CLOSED`). |
| `agent_knows` | Agent: Knows what it knows | PASS | 20 of 20 on 2026-10-15 (re-judged on 2026-10-15 06:51, same score) | - |
| `agent_unknowns` | Agent: Knows what it doesn't | PASS | 9 of 10 on 2026-10-15 as run; 10 of 10 when re-judged on 2026-10-15 06:51 with a judge changed after the run (not counted; only a new run confirms it) | - |
| `agent_no_failed_rules` | Agent: No failed research as rules | **FAIL** | 3 of 16 buys leaned partly on a context-only idea; 0 buys that rested only on one were stopped (last 7 days, checked since Oct 6) | 0 flagged buys among the brain's buys of the last 7 days. The brain's newest buy was Oct 10 02:10 UTC, so from Oct 17 the reading turns PENDING (no buys in the window), not PASS; it passes only after at least one clean buy, and fails again whenever a buy leans on a context-only idea. |
| `agent_explains` | Agent: Explains decisions | PASS | Jarvis's book | - |
| `agent_cites` | Agent: Cites evidence | **FAIL** | 14 of the last 20 answers with numbers carry evidence that opens on screen (needs 18 of 20); 14 of 20 name a source for every item (last 7 days,… | At least 18 of the newest 20 answers with numbers must carry evidence that opens on screen (checked by code). The newest 20 change as answers arrive, so the reading moves daily. |
| `ops_outages` | Operations: Outages detected | **FAIL** | outside view (worker, 7 days): 2 outages of 10+ minutes; unalerted before the worker's alert was armed: Oct 12 02:18 Toronto, 312 min; Oct 13 11:51… | The worker Mac's phone alert counts as armed only after Madhav confirms the test note reached his phone (`OD-WORKER-HARDENING`); then every outage of 10 minutes or more must be alerted by minute 15. |
| `ops_stale` | Operations: Stale data detected | PASS | the Explorer stands still | - |
| `ops_no_trade_unhealthy` | Operations: No trade when unhealthy | **PARTLY** | 9 of 11 paths that open a paper position ask the guard first (kill switch on or unreadable, price older than 5 minutes live or 20 for the Explorer's… | All books must ask the guard first. Two paths, the trend books (T3) and the Explorer's own setups, run inside the Explorer and ask it only after branch jarvis-4 is merged to main and the Explorer restarted (`OD-MERGE-MAIN`). |
| `ops_reconstructable` | Operations: Every decision reconstructable | PASS | 8 of 8 parts re-checked and matching | - |
| `ux_voice` | Experience: Voice commands work | PASS | 10 of 10 heard on 2026-10-11 | - |
| `ux_confirm` | Experience: Actions visible, confirmed | PASS | orders and switches | - |
| `ux_why` | Experience: User understands why | **NOT_MEASURED** | the exam has not asked its 'why' questions yet (added at the Oct 15 lock; the next exam run measures them) | One exam run with the five new 'why' questions (about $1.30 for the whole exam, `OD-EXAM-CADENCE`); it passes at 4 of 5 answers that give the real reason. |

**The exam checks.** The gate counts each exam run as it was first saved and shows any later re-judge beside it without counting it.  `agent_knows`, `agent_unknowns`, `ux_why` and `ux_voice` read the newest run of the agent exam and the voice exam (`jarvis/service/exam.py`). Since Oct 20 the agent exam runs every Sunday at 07:10 Toronto (`com.ananta.exam`, `OD-EXAM-CADENCE` (a)); the voice exam is still run by hand. The agent exam costs about $1.30 in paid AI answers; the voice exam uses the Mac's own speech tools and Gemini's free tier, so the morning review runs it on Mondays. Since the lock, a pass from a run older than 8 days reads PARTLY, so an exam that is never run again cannot hold a green check (`OD-EXAM-CADENCE`, answered (a) on Oct 20: weekly). The five 'why' questions were added at the lock, before any run; they pass at 4 of 5.

## 5. Checkpoints

**Day 30 (about Nov 14, `CHECKPOINT-30`):**
1. Open the Evidence page and read every count: the ledger questions Q1 (Explorer live against its replay), Q2, Q5, Q6, Q7 and Q8 (what each counts is in section 9), with how many independent market events, market days or rebalances each has so far.
2. Say whether both dial states have been seen and what the $500 book's execution fidelity is so far (fills inside NDAX's bid and ask; backtest against live).
3. Read the Acceptance Gate (27 checks) and the graduation scorecard, and list what moved since Oct 15.
4. Check that every nightly step ran: the 'steps that failed tonight' line in the newest `daily/universe_*.md`, the backups (including the worker's pull), the ledger check and the weekly reviews.
5. Write a short day-30 note in `docs/repair_shop/` and tell Madhav. Nothing changes by itself; a rule change goes through him.

**Day 60 (about Dec 14, `CHECKPOINT-60`):**
1. Run the Acceptance Gate and the graduation scorecard and write the result in `docs/repair_shop/`: what passed, what did not, and why.
2. Judge Rule A for Madhav: 60 market days of paper operation, both dial states seen, execution fidelity within 3 points of the backtest. If any part is missing the answer is 'not yet', and the window is extended rather than the rule bent.
3. Read the live zone visits (`ZONES-JUDGE`) and the other questions the due list attaches to day 60.
4. Put the real-money decision to Madhav. Real money is his decision alone and never starts by itself; the first step would be the tiny-live plan, with his written yes.
5. Then open the after-the-window list below.

Between the checkpoints the morning review reads the Evidence page, the gate and the due list every day; an overdue item becomes one repair-board request by itself.

## 6. Who may change what

- **Madhav decides** anything that trades, sizes, costs, changes a strategy's status, the gate, Rule A or B, spending and accounts.
- **Research, docs and tests** merge freely, through pre-registered reviews (the pass rule written and pushed before the run; every look counted).
- **App, Hands, safety and live changes** are built on branch jarvis-4, shown on the live site, and merged to main on his word. The Explorer runs from main, so its side of a change goes live only after the merge and a restart of `com.ananta.explorer`.
- **The repair shop** (requests, tickets, reviews) is the only door for a change. The morning review works the board but never changes a trading rule.

## 7. Known limits at the lock

- **Costs are a one-evening snapshot.** `src/intelligence/ndax_costs.py` holds the median of 5 NDAX order-book readings per lab coin from 2026-09-29; coins outside the lab ten are charged the fee plus a tier floor or three times their Binance half-spread (`registry.cost`). The worker Mac has recorded NDAX bid and ask every minute since Oct 12 (77 NDAX coins on Oct 14), as evidence only: it sets no cost yet. Stage S2 (about Oct 26) re-runs the $500 backtest with each coin's 75th-percentile measured half-spread; the gate check `data_costs` stays PARTLY until then, and any change to the table needs Madhav's yes.
- **Cost figures live in many files, and the pin covers the table.** `paper_costs` freezes the table in `ndax_costs.py`, the tier floors and fee literals in `registry.py`, and SD6's own flat NDAX profile (20 bp fee and 30 bp slippage a side, `COST_PROFILES` in `paper_exit.py`); `live_logic` freezes which profile a book gets by default. `reads.py` reads the table through `explorer_engine.HALF_SPREAD`, but ten research and manual files (`reads.py`, `manual.py`, `teachers2.py`, `intraday_atlas.py`, `t3_turnover.py`, `portfolio_trend.py`, `teacher_systems.py`, `learning.py` and two more) carry the same 0.004 fallback literal, none pinned.
- **ETH costs about three times what the table says.** The worker's first days (Oct 12 to 14) measured ETH's median half-spread at 0.25% against 0.084% in the table (0.45% a side measured against 0.28% assumed); BTC 0.21% against 0.18%. ETH is a fifth of the $500 book's core. Stage S2 (Oct 26, `S2-SPREADS`) re-runs the backtest with measured costs and Madhav decides; `data_costs` stays PARTLY until S2 is recorded done.
- **The pins hash branch jarvis-4; the Explorer and the T3 trend books run main's copy.** `~/code/ananta-decision-agent` (main) is the Explorer's working directory, and its `portfolio_layer.py`, `explorer_engine.py` and `explorer_live.py` differ from jarvis-4's (main has no `ndax_costs.py`; its own half-spread literals equal the pinned ones today). So `t3_rule` protects the copy that will run after `OD-MERGE-MAIN`, and the Explorer's own entry rules are pinned in neither tree. The merge changes the running Explorer in the window; it is dated in the Q1 evidence.
- **12 of the 16 gate passes are recorded by hand** (`data_correct`, `data_complete`, `data_pit`, `data_survivorship`, `engine_lookahead`, `engine_risk`, `strategy_oos`, `strategy_universe`, `strategy_survivorship`, `agent_explains`, `ops_stale`, `ux_confirm`): their status in `acceptance_gate.json` is a written verdict that no code re-checks daily. Since Oct 15 evening those statuses are pinned (`live_logic`), `engine_risk` degrades after its monthly date, and `data_costs` cannot fall back to its hand-written pass.
- **The brain has not bought since Oct 10 02:10 UTC** (Oct 11 to 14: 40, 47, 46 and 46 decisions, all PASS). While it does not buy, `agent_no_failed_rules` reads PENDING from Oct 17, Jarvis's book adds no events to `strategy_regimes` or Q7, and the day-30 checkpoint reports the days since its last buy. The likely reason (zone entries quiet with the dial open; Hunter and Squeeze parked) is not established.
- **The exam checks go stale on known dates.** With no new run, `ux_voice` (Oct 11) reads PARTLY from Oct 20 and `agent_knows` and `agent_unknowns` (Oct 15) from Oct 24, two days after `OD-EXAM-CADENCE` is due: the gate would read 15 of 27 on Oct 20 and 13 of 27 on Oct 24. The gate counts each exam run as it was first saved; a later re-judge is shown beside it and never counted (the Oct 11, 13 and 15 runs were re-judged after their results, which the stricter judge of Oct 15 evening replaces from the next run).
- **One market state has been seen.** The exposure dial has been open since August 2026. Rule A needs both states and no dial-closed spell has happened since, and the wording on H07's read alerts ('History: ...' from `reads_status.json`) was written while only the open state had live data. Until a closed spell has produced events, `strategy_regimes` cannot pass. `EV-DIAL-CLOSED` re-reads every scoreboard when the first closed spell ends.
- **Citation is not influence.** The logs record which cards a decision cited, not that a card changed it. Nothing re-runs a decision without its card, so no result may claim a card influenced a decision (`OD-CARD-INFLUENCE`).
- **The decision writer has been idle since 2026-10-11 07:02 UTC** because the hourly watch (Hunter, Squeeze) is parked. The knowledge-catalog and cite-list fixes tidy the records and change nothing live; resuming the watch needs `PW-HOURLY-RESUME` first.
- **Zone entries still ring the phone.** A zone entry still sends a phone note, although zone touches are 'won't take again' and the M2a-G alert was silenced for the same reason. The attention score is a design rule, never a tested signal, yet HIGH reaches the brain (10 TAKE and 13 PASS decisions from Oct 4 to 14). `OD-PLAYBOOK-ATTENTION` asks whether it should stay.
- **Some words are rules, not checks.** `lake_header` (coins alive per year, dropped days) is printed by no review runner, and a pre-registration pushed before a run is a rule in `RESEARCH_RULES.md` section 1, not code (`PW-PREREG-GUARD`). A review without the header is a draft by rule only.
- **24 of the 39 watches in `watches.json` belong to no strategy**, so the nightly align does not repair their words (`PW-ALIGN-WATCHES`).
- **Graduation gate 7 cannot read READY.** The $500 book labels no market sideways, so the scorecard (`jarvis/service/graduation.py`) can never say READY until a label is defined (`OD-GRAD-GATE7`). It is a second view; Rule A and the Acceptance Gate decide.
- **The 10-coin shadow replay and the live Explorer agree on 56.5% of 23 events** in the first like-for-like reading (bar: 60% on 20 events). The nightly check files a repair-board request when the reading stays under the bar.
- **The free web-search key is unproven.** Of the 24 paid-search rows since Oct 13, eight were quota (HTTP 429) on Oct 13 and eight on Oct 15 came from test and script runs; the live brain has not searched since. Madhav has since replaced the key ('key done'). A working free search now writes a line to `~/ananta_runs/web_free_log.jsonl` (nothing recorded free successes before); until one appears, only paid checks (at most 8 a day for the brain) can veto a buy, and the Monday voice exam, which uses the same key for speech-to-text, can fail the same way (`OD-GEMINI-KEY`).
- **The lake holdout is not fresh.** No lake review loaded anything from 2026-08-01 on, but Candidate v3 spent the window 2026-08-01 to 2026-09-12 once and live paper has run on these coins since 2026-09-29. Review #29 calls the window 'sealed': read that as 'not loaded', never as 'fresh' (`RESEARCH_RULES.md`, 'The holdout is not fresh'). The next holdout is live data after a date written in a pre-registration.
- **'D6' names two decisions** (the form-of-address rule in `account.py` and `ask.py`, and parking the hourly watch: the marker file `hourly_watch.PARKED`, read at `health.py`; the code is `paper_watch`). Read the context.
- **The audit register's RECORDED rows carry no new evidence.** 267 of its 398 rows are standing verdicts restated ('Standing verdict (X): X. Nothing further is owed.'); the evidence of the other 131 names a commit, file, erratum or due item. Row `cards-7:STRAT:ZONE_TOUCH` is SUPERSEDED with verdict RE-TEST: the re-test is dropped, not replaced, and belongs on the after-window list.
- **Correction (Oct 20): the worker Mac had no 15-hour hole on Oct 18-19.** The morning review of Oct 20 and repair request #72 said the outage 'left about a 15-hour hole in the NDAX spread record'. The worker's own files show 1,435 of 1,440 minutes recorded on Oct 18 and 1,440 of 1,440 on Oct 19: only the SSH link from the main Mac (the nightly pull) was down. S2 (Oct 26) counts those two days as clean. The worker still drops off the network (#72, physical).
- **Correction (Oct 20): the lake job runs at 02:15 Toronto, not UTC.** launchd reads the Mac's clock (`com.ananta.lake`, Sundays 02:15); section 2 said 02:15 UTC until Oct 20.
- **Erratum (Oct 20): the Oct 14-15 lost brain decisions.** A 14 Oct change added 2 columns to the decisions table while the save still wrote 18 values, so from 14 Oct 22:02 to 15 Oct 08:26 UTC every brain decision was paid for and then failed to save: **226 decisions paid and not saved, $4.65 spent**; with nothing saved, the spending cap and the 6-hour cooldown stopped working, **304 more wakes were dropped**, and there were **0 brain decisions from Oct 15 to 17**. The error was written only into the queue row (no log line, no alert). The count of decisions for Oct 14 above and 'the brain has not bought since Oct 10' must be read with this; the decision map's heading '227 lost wake-ups' is the same incident (226 is the count). The run checker (49 parts, in the morning review) now reconciles paid calls against saved decisions; the live-code fixes wait for Madhav (decision map, section 6, item 6).
- **Dead code on the layer map.** `cycle_contract_v01.py` and `ingest_contract.py` are imported by nothing; the cycle contract never shipped a v0.2.

## 8. Waiting for Madhav

Sixteen decisions were waiting at the lock, each with the date it matters and what Claude would recommend; the ones answered since are marked in the table and quoted in "Decisions of 20 Oct" below. Claude changes nothing on his accounts or machines, and spends nothing, without his explicit OK. The options for each are in `docs/knowledge/due_list.json`.

| Decision | By | What | Claude's recommendation |
|---|---|---|---|
| `OD-A6-EXAM` (**answered parked, Oct 21**) | 2026-10-22 | A6 (shorter prompts per kind of question): the first try cut the prompt to 45% but failed the keep rule (one flip, $1.37 against $1.31), so it was not deployed (branch a6-prompt). | Park A6 for now: a prompt change during the window muddies the evidence. |
| `OD-EXAM-CADENCE` (**answered (a), Oct 20**) | 2026-10-22 | The agent exam (jarvis/service/exam.py: 20 'knows' questions, 10 'doesn't know', 5 'why', 2 consistency pairs) is run by hand; nothing schedules it. Done: `com.ananta.exam`, Sundays 07:10 Toronto (f6d70cd); first run Oct 20 09:51, 20/20, 10/10, 5/5. | (a) yes: one run now, then every Sunday. The three exam checks (`agent_knows`, `agent_unknowns`, `ux_why`) cannot stay green any other way; about $1.30 a run, about $13 over the window (one run now and nine Sundays). The stricter judge of Oct 15 evening applies from the first run. |
| `OD-PLAYBOOK-ATTENTION` (**answered (a), Oct 21**) | 2026-10-31 | The attention score (zones_watch.attention) gives points for zone position, a supported zone kind, a recent visit, market allowed and Madhav's setups showing. | (a) keep the weights and let the credit study judge them (about Jan 2027); and stop the phone note on zone entries. |
| `OD-BOOK500-BRAKES` (**answered (1), Oct 21**) | 2026-10-31 | The D12 brakes (2% day, 4% week, 4 losses in a row, 15% fall from the peak) apply to the whole $500 book. | (1) keep the brakes on the whole book, as decided; changing a rule in the window is what the lock is for. |
| `OD-CANDIDATE-BOOKS` (**answered (a), Oct 21**) | 2026-10-31 | The two candidate books have not traded since 2026-10-08. | (a) retire both and leave the breaker as history. |
| `OD-READS-WAKES` (**answered (a), Oct 21**) | 2026-10-31 | The READS entry (M1a, M2a, M2a-G, M3a, M3b) still has wakes_brain true, although its own line says no measured edge yet (reviews #5 and #26). | (a) set wakes_brain false for READS: none of the five has a measured edge (M1a's review #15 pass was by 0.01 of t on 3 confirm events and review #26 was mixed). (b) is the fallback if Madhav wants M1a's live record to keep growing through the brain. |
| `OD-E5-PERMISSION` (**answered (a), Oct 21**) | 2026-10-31 | The status cards EXPLORER and E5 still say permission PAPER (tier LIVE10), which the brain counts as support, while the Explorer's losing trades are classed 'won't take again'. | (a) set both cards to CONTEXT, which matches 'won't take again'. |
| `OD-C3-PRICE` (**answered (b), Oct 21**) | 2026-11-14 | Casebook buy C3 (SOL, 2026-08-10, 109 CAD) matches no candle: it is about 0.4% above the week's high (108.5 CAD on Aug 9), so it was left 'not matched'. | (b) leave C3 'not matched' unless the NDAX fill is easy to find; nothing uses its price. |
| `OD-MULTITEST` (**answered (b), Oct 21**) | 2026-11-30 | Multiple-testing rule: reviews #15 to #23 judged about 97 cells on Oct 4-5 and no family-wide correction exists (RESEARCH_RULES.md section 1). | (b) keep the per-test bar and require a point-in-time or forward re-test before any promotion. |
| `OD-GRAD-GATE7` (**answered (b), Oct 21**) | 2026-11-14 | Graduation gate 7 (no overtrading in sideways markets) cannot be measured for the $500 book because it labels no market sideways, so the scorecard can never read READY. | (b) leave gate 7 strict and rely on Rule A and the Acceptance Gate. |
| `OD-GEMINI-KEY` (**answered ticked done, Oct 21**) | 2026-10-22 | The free web-search key was rejected ('API key not valid') on 2026-10-15, so the news veto relied on the paid search path. | From Oct 15 evening a working free search writes one line to `~/ananta_runs/web_free_log.jsonl`: a line there proves 'key done' worked, so tick it. If it still fails (new rows only in the paid log), type a fresh free key into `.env` yourself (a); never in chat. The voice exam's speech-to-text uses the same key, so check the Monday voice run too. |
| `OD-HL-FILLS` (**answered (a), Oct 20**) | 2026-11-14 | Optional (worker stage S3): capture Hyperliquid fills continuously, data only, so the HL-RX question (docs/research/HL_RX_RESULT.md) can be asked again and the quarterly other-traders study has the fills. Done: the worker's hourly capture (installs itself when the worker is back online) and the daily rebuild `com.ananta.othersdaily` at 04:30. | (b) rely on the quarterly pull for now. Madhav chose (a). |
| `OD-WORKER-HARDENING` (**answered his own steps, Oct 21**) | 2026-10-22 | Worker Mac, two small items: confirm the worker's test phone note from the morning of Oct 15 reached his phone, and decide the optional step of turning off password SSH login on the worker (worker plan, stage S2). | Confirm the phone note. Say yes to the SSH step only after you have checked that key login from the main Mac works. |
| `OD-RULEBOOK-S1S3` (**answered (a), after the window, Oct 21**) | 2026-11-30 | The variable registry says not to use S3 and S1 as signals (V12, V13), yet E1, E3, E4 and the LONG_TERM type still require them (audit doubt 19). | (a) a rulebook v1 without S1 and S3, after the window. |
| `OD-CARD-INFLUENCE` (**answered (b), Oct 21**) | 2026-11-30 | No log can show that a knowledge card changed a brain decision. | (b) build nothing and never claim a card influenced a decision; revisit after the window. |
| `#71` (**answered yes, Oct 20**) | 2026-10-20 | Repair request #71: Hands was not a launchd job, so a crash stayed down (426 minutes on Oct 17). Done: `com.ananta.hands` (bc0a6c1). | yes. |
| `OD-SHADOW-LANE` (**answered yes, Oct 20**) | 2026-10-20 | A blind, append-only shadow log that records what each pre-registered rule (reviews #31-#38) would have done each day, unseen until day 60, never touching a book. A build, so it needed Madhav's yes (Rule B). Another agent builds it. | yes. |
| `OD-STOP-RULE` (**answered, Oct 20**) | 2026-10-20 | The written zone stop (STOP_ZONE: a daily close half a range under the zone) and the code (sells on any touch during the day) disagree; all 18 stops of Oct 13-20 fired intraday while the close stayed above the stop. | Keep the touch stop running unchanged in the window, score the close stop beside it (review #31), decide at day 60. Madhav: yes. |
| `OD-MERGE-MAIN` (**answered Oct 16**: "lets merge"; main fast-forwarded to 9520668 and the Explorer restarted at 10:34 Toronto; recorded done on the due list) | 2026-10-20 | Merge branch jarvis-4 into main after Madhav has looked at the live site. | Look at the live site, then say 'merge'. It also turns the two Explorer-side guard paths on. Note: the Explorer and the T3 books run main's copy of the code, so the merge changes their entry behaviour on that day (the guard can pause new entries); the Q1 live-versus-replay evidence gets a dated note. |

### Decisions of 20 Oct

Madhav's answers, quoted. Numbered items answer the numbered list of the decision map (`docs/repair_shop/plan-2026-10-20-decision-map.md`, section 6), at 12:08 Toronto; the others were given at 09:39.

| # | Asked | Madhav | What it changed |
|---|---|---|---|
| 09:39 | `#71`: make Hands a launchd job | yes | `com.ananta.hands` (bc0a6c1), section 2. |
| 09:39 | `OD-EXAM-CADENCE`: (a) one run now, then every Sunday | yes (a) | `com.ananta.exam`, Sundays 07:10 (f6d70cd); first run Oct 20 09:51: 20/20, 10/10, 5/5. |
| 09:39 | `OD-HL-FILLS`: (a) the worker saves other traders' fills, plus a daily rebuild | "let the worker Mac save other traders' fills every day, data only ... Yes. We have to do it." | The worker's hourly capture (waits for the worker to be back online) and `com.ananta.othersdaily` at 04:30. |
| 09:39 | The India items | yes | Recorded in the India plans; not part of the crypto lock (India shares nothing with crypto). |
| 2 | "`engine_execution` counts every paper fill of every book, judged against the worker's independent NDAX quote for that minute. Pass: at least 20 fills, at least 90% achievable, and the median gap within 5 bp. `engine_sizing` stays on the $500 book only." | "2. yes" | `acceptance_gate.json` (measure, pass mark), `evidence_live.execution_reading`; `gate_definition` and `live_logic` re-pinned with that quote. `engine_sizing` unchanged. |
| 3 | "The stop rule: keep the touch stop running, score the close stop beside it, and decide at day 60." | "3. yes" | Nothing in the code changes. The touch stop keeps running; review #31 (pre-registered) scores the written close stop beside it; the rule is decided at `CHECKPOINT-60`. |
| 4 | "The bold book: give it each coin's T3 rating." | "4. yes" | `bold.py`: each candidate's T3 rating (IN or OUT that day) is in the pick input; T3's wording corrected in `brain.KNOWLEDGE` (T3 and TRAIL: '20-day exit' is a close under the 20-day average, not a 20-day hold); a pick citing T3 on a coin rated OUT is flagged (`cites_t3_on_out`), never blocked. The mandate is unchanged. Splits review #37's window at the first row with pack `t3-v1` (`bold_mandate.json`, amendment of Oct 20; erratum in `PREREG_WINDOW_2026-10-20.md`). |
| 5 | "`OD-SHADOW-LANE`: a blind forward log for the pre-registered findings." | "5. yes" | Approved; another agent builds it. |

### Decisions of 21 Oct

Madhav, 09:41 Toronto: "Complete all pending tasks and all that are waiting for me. I approve all." … "for all the recommeneded items , its yes." Every decision took Claude's recommended option. Built on four branches, merged as `integrate-1021`, reviewed independently, deployed in one restart.

| Decision | Answer | What it changed |
|---|---|---|
| `OD-READS-WAKES` | (a) | `strategy_status.json`: READS `wakes_brain` false. M1a, M2a, M2a-G, M3a and M3b still log their signals and paper trades (EV-Q5 still counts them); their moments no longer cost a brain call. `strategy_verdicts` re-pinned. |
| `OD-E5-PERMISSION` | (a) | `status_cards.json`: EXPLORER and E5 permission CONTEXT, so the brain no longer counts them as support. |
| `OD-CANDIDATE-BOOKS` | (a) | `candidate_paper.RETIRED`: V0 and V1 never open a new entry; history and the tripped breaker kept. `strategy_verdicts` re-pinned. |
| `OD-PLAYBOOK-ATTENTION` | (a) | Weights unchanged; `eye.ZONE_ENTRY_PHONE = False`: zone entries are recorded and still go to the brain's queue (monitoring only through ZONE_TOUCH) but no longer ring the phone. |
| `OD-MULTITEST` | (b) | `RESEARCH_RULES.md` section 1: no promotion without a point-in-time or forward re-test, pre-registered as one look (headings unchanged). |
| `OD-CARD-INFLUENCE` | (b) | `RESEARCH_RULES.md` section 6: a card is never claimed to have influenced a decision; nothing built. |
| `OD-RULEBOOK-S1S3` | (a) | On the after-the-window list as `PW-RULEBOOK-V1`; the rulebook is unchanged in the window. |
| `OD-A6-EXAM` | park | Branch `a6-prompt` stays unmerged. |
| `OD-GEMINI-KEY` | tick | Done (the voice exam passed on the same key). |
| `OD-BOOK500-BRAKES`, `OD-C3-PRICE`, `OD-GRAD-GATE7` | (1), (b), (b) | Recorded; no change. |
| `OD-WORKER-HARDENING` | — | The test phone note and turning off password SSH on the worker are security steps on his own machine, so they stay his. |
| The gate bundle (decision map section 4) | yes | Section 4 above; `gate_definition` and `live_logic` re-pinned. |
| The live-code reliability fixes (decision map section 6, item 6) | yes | `reliability.py`: every failed paid save (brain decision, stance, bold pick) is logged and sends one phone note an hour at most; the brain's and bold book's decision row, paper trade and random twin save in one transaction; the stance asks once more for a shorter reply when its reply is cut off (the Oct 18-19 cause) within the daily AI dollar; 15-minute step errors, watchdog lines and the health watchdog's checks are dated and read by the run checker. No trading rule changed. |
| The learning loop (decision map section 5) | yes | `learning.count_lessons` (section 2); the 14 Oct "random beat the pick" ticket filed as TK19 (`ledger.json`, linked to review #33, closes at day 60); a read-only ledger consistency warning in the morning review. |

### Decisions of 23 Oct

Madhav, 23 Oct (in chat): "Will get TOTP fixed before Sunday. Yes for all others."

| Item | Decision | Done |
|---|---|---|
| Hunter's book (#80) | (a) a written rule: after 10 independent market events, retire it unless it is ahead of its random twin after costs; until then unchanged | Recorded on #80; nothing changes in the window; judged at the 10th event, never before. |
| Worker pull retry (#72) | yes: retry the worker pull each hour until the day lands | `com.ananta.workerpull` at 04:20, 05:20, 06:20, 07:05, 08:20, 09:20 Toronto (`worker.pull()` never overwrites a day already pulled); log `~/ananta_runs/workerpull.log`. The worker already has wake-for-network on and never sleeps (pmset: womp 1, sleep 0), so the 03:40 failures are the main Mac's link, not the worker. |
| India: lock India like crypto | yes | `INDIA_LOCK.md` (records repo), section 10 here. |
| India: SZ2 (a) and (b), SP3 holdout | yes-logged, keep 0, not yet | Recorded in INDIA_LOCK.md "Decisions of 23 Oct". |

## 9. After the window

**Dated and recurring steps that run before and after day 60** (each is on the due list; an overdue item becomes a repair-board request):

| Id | Due | Cadence | Who | What |
|---|---|---|---|---|
| `SUNDAY-REVIEW` | 2026-10-18 | weekly | automatic | The weekly situation review (docs/repair_shop/weekly/) is written by the Sunday night run, which ticks this item itself. |
| `STANCE-CHECK` | 2026-10-17 | once | Claude | Check the first brain-written stance after the Oct 16 close (about 20:10 Toronto); a scheduled check also runs at 2026-10-17 00:45 UTC. |
| `S2-SPREADS` | 2026-10-26 | once | Claude | Worker stage S2: rerun the $500 backtest with the half-spreads the worker Mac measured on NDAX (each coin's 75th percentile, after 14 days of clean data). |
| `SPREAD-REFRESH` | 2026-11-01 | monthly | Claude | Cost table check (V04): once a month compare the worker Mac's measured NDAX spreads with the table in src/intelligence/ndax_costs.py. |
| `CHECKPOINT-30` | 2026-11-14 | once | Claude | Day-30 checkpoint of the 60-market-day evidence window: read every evidence count and confirm nothing is silently stuck. |
| `CHECKPOINT-60` | 2026-12-14 | once | Claude | Day-60 checkpoint: the evidence window ends and Rule A (60 market days, both dial states seen, fidelity within 3 points) is judged for Madhav. |
| `ZONES-JUDGE` | 2026-12-14 | once | Claude | Judge the live zone visits (audit cards R6 and SWING-NEW): zones stay a location label, never a trade. |
| `Q-R2-HL` | 2027-01-01 | quarterly | Claude | Quarterly refresh of the other-traders study (R2, Hyperliquid). |
| `Q-ME1` | 2027-01-01 | quarterly | Claude | Quarterly refresh of ME1, the base-rate sheet of how often coins move 0.5%, 1% or 2% within 5 minutes to 4 hours, used to size stops and targets. |
| `Q-F6` | 2027-01-01 | quarterly | Claude | Quarterly re-measure of 'market allowed' (Bitcoin above its 50-day average; audit cards R7:F6 and R16-F6): 2024-26 shows little. |
| `Q-H01` | 2027-01-01 | quarterly | Claude | Quarterly re-measure of H01, the regime gate 'buy only when the whole market is in an uptrend'; the confirm period shows a thin edge. |
| `Q-T3` | 2027-01-01 | quarterly | Claude | Quarterly re-judge of the 10-coin trend portfolio (T3): its exit stays (audit card R12); the book itself is judged on its live record. |
| `Q-NEWS-CREDIT` | 2027-01-01 | quarterly | Claude | Quarterly update review: score the daily news check and the seven layer signals once, exactly as docs/research/STUDY_NEWS_CREDIT.md fixed. |
| `ENGINE-RISK-REHEARSAL` | 2026-10-30 | monthly | Claude | Gate check engine_risk ('Kill switch, stops, caps rehearsed', pass mark 'Rehearsal passes monthly') is a hand-written PASS from the Sep 30 rehearsal. |

**Evidence counts the ledger keeps** (not calendar dates; the Evidence page shows each count):

| Id | Count | What |
|---|---|---|
| `EV-Q1` | 10 independent market events of Explorer trades (one count) | Ledger Q1: does the live Explorer behave like its 7-year replay (same win rate and cost drag)? |
| `EV-Q2` | 6 weekly rebalances of the 10-coin trend book | Ledger Q2: does the live 10-coin trend book follow its backtest (in when trends are up, in cash in slides, few trades)? |
| `EV-Q5` | 10 market days with a live signal from the setups | Ledger Q5: the live record of Madhav's setups (M1a, M2a, M2a-G, M3a, M3b). |
| `EV-Q6` | 10 market days with a live H07 signal | Ledger Q6: the live record of H07, the short dip trade in an uptrend (review #14: strong in both periods but a few events short). |
| `EV-Q7` | 10 independent market events of Jarvis's book | Ledger Q7: is Jarvis's own book (one decision-maker with all the knowledge) better than random coins traded with the same plan? |
| `EV-Q8` | 6 weekly checks of the 30-coin trend book and 10 dip-trade events | Ledger Q8: the 30-coin tier, trend book and dip trade. |
| `EV-DIAL-CLOSED` | the dial has closed once and reopened (both states seen) | The first dial-closed spell: Rule A needs both dial states seen, and the dial has been open since August 2026. |

**The after-the-window list.** New research, re-tests and builds that Rule B holds back. They are opened after `CHECKPOINT-60`, each as a pre-registered review with its pass rule written first, and in an order Madhav sets:

| Id | What |
|---|---|
| `PW-LIBRARY` | Old-app re-test queue: APP-LIBRARY (13 outside ideas, each needs a written pass rule), APP-REGVAL (re-run the regime validation on the daily horizon with NDAX-type costs, the baseline for any new cost model) and… |
| `PW-H1` | H1 volume shock, used only as a risk flag (skip or shrink the entry on the bar after a burst), never an entry. |
| `PW-FEE-SCREEN` | SET8 (volume spike by time of day), SET12 (breadth: isolated against crowd shock) and SET16 (move-lag fee) were screened with the Grok-era fee tables. |
| `PW-HL-RX` | HL-RX camera: ask again whether any trader's entries were visible in our snapshot stream before they happened (first try: 62 eligible episodes, none matched, no snapshot at that moment). |
| `PW-MSM` | msm_v1_stamp_v1: restamp the market states on the lake and cap how long COOLING can run on, before any use. |
| `PW-H06` | H06 deep Bollinger dip in an uptrend (still PROMISING, never pre-registered on the lake), and the TEACHER_FIRST_LOOK S3 re-test. |
| `PW-P02` | P02 correlated coins are one bet: the cap of 5 open longs (chain.py) was never set from a measured correlation, and the $500 book uses a different rule (2 open coins with 90-day correlation over 0.8). |
| `PW-M1A` | M1a capitulation at the lows has never fired live and was not re-run after reviews #15 and #26. |
| `PW-ZONE-BASELINES` | Zone baselines: carry the calibration's own noise into z and re-estimate the bias from real-return shuffles (R6-RWCAL); check the invented wick model against real data (R7-RWCAL); run a better baseline for AVERAGE-200, still a… |
| `PW-R17-H16` | H16 market breadth as a trend filter: re-test once on new data, counted as one variant (parked). |
| `PW-R20` | T3 buffered exit (T3-B on paper): run the buffered-exit test review #20 proposed. |
| `PW-BREAKOUT-38` | Repair-board request #38: does a breakout away from support work? |
| `PW-ATTENTION-TABLE` | R28: give attention spikes and zone entries their own measured trigger table, as the daily rules got in review #26. |
| `PW-BOOK500-PIT` | BOOK500-BT: re-test the $500 book's edge sleeve on point-in-time data. |
| `PW-LEDGER-GENERATE` | Audit Fix 10: the repair-shop ledger is still written by hand; generate it from the databases. |
| `PW-VARREG-EVENTS` | Variable registry: fill each row's sample size and independent market events (most rows counted overlapping trades). |
| `PW-PREREG-GUARD` | A possible code check that refuses a review script whose pre-registration is not pushed (today RESEARCH_RULES.md section 1 is a rule, not a check). |
| `PW-RENAMES` | Join renamed tickers in the lake (the BCC and BCHABC chain to BCH) so point-in-time lists stop dropping Bitcoin Cash at its ticker changes. |
| `PW-QUALITY-GAPS` | The lake quality check lists only the first 10 gaps per coin (quality.py LIMIT 10). |
| `PW-FREE-SEARCH-LOG` | Free web-search counts and answers are not recorded anywhere (audit live-outcomes), so a rejected key shows only in web_paid_log.jsonl. |
| `PW-ALIGN-WATCHES` | 24 of 39 watches belong to no strategy (UNIVERSE_DAILY, HUNTER, SQUEEZE, E1-E6, T3_TREND and others), so the nightly align does not repair their words. |
| `PW-HOURLY-RESUME` | Before the hourly watch (Hunter, Squeeze; parked Oct 11, D6) is ever resumed: re-decide cite_allowlist LIVE_5 and the statuses in knowledge_catalog_v1.json. |

## 10. The Indian market beside this lock (from 2026-10-23)

Madhav, 23 Oct: bring India to the same place as crypto ("Remaining all should be done … I open the website, login and see 2 options"), and yes to locking India like crypto. The plan is the project doc `claude/plan-2026-10-23-ananta-to-the-review-point.md`; India's own lock page is `~/code/ananta-records/docs/INDIA_LOCK.md` (pins in `india/registrations/india_lock.json`, guarded by `tests/test_india_lock.py` in that repo; lock day about 1 Nov). What the morning review does about India from Oct 23:

- The lost-runs checker proves every India session (ten dated proofs on NSE session days: the SP1 line's decisions, the ledger snapshot, the decision journal, the read model, the daily call, the league, the missed-movers review, the recorder, the evening report, the auto sign-in) and prints India's own 24-hour and 7-day lines. They are part of the review page; a **high** India miss (a lost SP1 session, a missing ledger snapshot, a failed auto sign-in) becomes a repair-board request with a first answer, like a crypto one.
- The review never changes an India paper rule or pin. India decisions go under "Waiting for Madhav" with the recommendation from INDIA_LOCK.md section 8. India's builds (SP3, SZ2, Ask, the exam, Telugu) belong to the India task at 07:45, not to this review.
- When the worker Mac's nightly pull failed and the worker answers over SSH, the review runs the pull by hand (`jarvis.service.worker.pull()`) and re-runs the checker, as on Oct 22 and 23.
- The one app is live since Oct 23: sign in → "Which Ananta?" → Crypto or Indian market; India reads the app's own `/v3` contract from `api.livetrading247.com/india` (read-only, no order path). Once India locks, one morning review writes both halves of one page.
