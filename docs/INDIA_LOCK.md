# The India lock (draft of 2026-10-23; lock day about 2026-11-01)

On 2026-10-23 Madhav chose to bring India Ananta to the same place as crypto: *"Remaining all should be done … I open the website, login and see 2 options."* Asked whether India's "done" line is a lock like crypto's (freeze the paper rules, gate them, put everything that does not change a paper rule on an after-the-window list), he answered **yes**. This page is India's `docs/LOCK.md` (the crypto lock lives in the agent repo). It says what runs, what is frozen, what decides success, who may change what, what waits for Madhav and what waits for the end of the window. It is checked by `tests/test_india_lock.py` (the frozen items, `india/registrations/india_lock.json`).

Madhav's standard for every judgement (Oct 20): *"It's not about how much money we make. It's about taking the right and best decision in the given scenario."* So: nothing on paper is tuned on early numbers; it is recorded and waits.

**Status: a draft.** The pins already declared frozen are recorded today (section 3). Lock day is when SP3's remaining parts and the SZ2 selection are in and the India gate reads daily in the app; then the items in "pinned on lock day" are added and this page loses the word draft. Until then every India job runs as it is.

## 1. The window and the rules that end it

- **Evidence window:** the stock paper book since 2026-10-16, the SP1 index line from its first recorded session (none yet: the sessions of Oct 21, 22 and 23 were lost to the dead Kite token). The gate counters D15 (30 clean nightly runs) and D16 (30 ledger snapshots) count consecutive clean sessions; a lost session restarts nothing but adds nothing.
- **Rule A (real money):** no real order before the G02 gate sentence, and then only on Madhav's written yes, with the order module reviewed and the survival rules switched from record to enforce. India's live question on his father's account is parked until then (Madhav, Oct 22).
- **Rule B (new rules):** anything that trades differently on paper is a proposal with a pre-registered test against random, run after the window, and needs Madhav's yes. A rule change inside the window restarts the 60-session clock, so none is made.
- **What ends the window:** G02 reaches 30 and 30, two families validated on development plus validation years with one holdout look each, and Madhav's sentence. About 5-8 Dec if no session is lost from Oct 26.

## 2. What runs by itself (Toronto times; IST in brackets)

| When | What |
|---|---|
| 21:40, 21:52 Sun-Thu | `com.ananta.india.autologin`: signs Ananta in to Kite with the TOTP key; a failure rings the phone with the deadline (23:40 Toronto, 09:10 IST). The manual page stays as fallback. |
| 22:00-00:45 (07:30-10:15) | `com.ananta.india.sp1paper`: the day plan and the SP1 decisions at 09:15, 09:30, 09:45, 10:15 IST; futures shadow and the 1-lot option line. |
| 22:30 (08:00) | `com.ananta.india.paper`: the stock book's decisions and fills, then the missed-movers review, the reference-traders league and the read model. |
| 22:35 (08:05) | `com.ananta.india.spreads`: option depth snapshots (Sun-Thu). |
| 02:30 (12:00) | `com.ananta.india.nightly`: builds, integrity, leak check (9 rules), lineage, firewall, verify. |
| 07:00 (16:30) | `com.ananta.india.sp1paper.score`: the session scored three ways. |
| 07:20 (16:50) | `com.ananta.india.morning`: job health, the missed line, the league line, the SP1 replay, the next sign-in. |
| 07:25 / 07:45 | the two morning reviews (crypto, India). The crypto review's lost-runs checker reads India's session proofs (section 4) since Oct 23. Once India locks, one review writes both halves of one page. |
| 12:30 (22:00) | `com.ananta.india.recorder_noon`: option minutes, the ledger snapshot (D16), index candles. |
| 12:45 (22:15), weekdays | `com.ananta.india.nightly` again (since 24 Oct 2026): fetches the session that just closed, so the 19:00 and 22:30 jobs plan the next session on its close; the 02:30 run stays as the heal run. |
| 19:00 (04:30) | `com.ananta.india.evening`: recorder, SP1 nightly replay, US close, forecast score, day plan, option book, calibration, selection report, evidence, report, portfolio, FII/DII and deals captures. |
| Sundays | the agent exam (crypto's `com.ananta.exam`; the India exam joins it in Phase 2); the voice exam on Mondays. |

## 3. What is frozen

Pinned today (`india/registrations/india_lock.json`, each with Madhav's recorded yes of 2026-10-23 and its sha256; `tests/test_india_lock.py` fails when one changes):

| Pin | What it freezes | Where |
|---|---|---|
| `paper_rules` | The stock paper book's configuration (cfg-2026-10-19c): families BRK, PULL, REV and the CTL control, their caps, the Rs 50,000 scale unit and Rs 1,000 risk, re-entry days, the liquid 250, the Rs 60,000 main book and its shadow books, and the survival rules (5% day, 22% pause; record, do not stop, on paper, Madhav 19 Oct). | `india/paper_config.json` |
| `sp1_playbook` | The SP1 index playbook, frozen 19 Oct (sp1-v2-2026-10-19-frozen): decision points, actions, outcomes, learning. | `india/registrations/sp1_v2.json` |
| `sp3_spec` | The SP3 positional study as frozen 20 Oct after five review rounds, with its permanent-stops list. | `india/registrations/sp3_v1.json`, `sp3_permanent_stops.csv` |
| `sz2_spec` | The SZ2 sizing study's spec. | `india/registrations/sz2_v1.json` |
| `cost_model` | The costs every paper book and study pays (v1.2: STT, GST, SEBI, stamp, transaction, DP charge; lines of code). | `india/costs.py` |
| `learning_rules` | The league's horizons (1, 5, 20), top 20, 200 random draws, Rs 50,000 notional, participants, 20-session window and the four coverage classes; the missed-movers bands, base and thin-day rules, families and control. The 3-in-7 pattern rule files a DRAFT, never a rule. | `india/others.py`, `india/missed.py` |
| `no_order_rule` | The leak check: Kite GET and the margin calculator only, no order call anywhere, the sealed holdout refused without a recorded purpose (lines of code). | `india/leakcheck.py` |

**Pinned on lock day (about 1 Nov):** the G01 exit book as the stock book uses it (copied from `manifests/g01_exit_book.json` into registrations); the SP1 line's sizing after the SZ2 selection; the SP3 frozen list, or the recorded "no playbook change: the baseline hold stays" (its dev and validation runs say the situation policy does not beat `hold_60d_nostop`); the India gate's definition; the India exam's judges and pass marks; the read model's rules version.

Not frozen, by design: every reading (books, counters, league pages, the read model's numbers), the research registry's results, and the after-the-window list.

## 4. Success: the India gate

The gate is G02 (the research tracker) plus operational rows, read daily on the app's Research screen from lock day. It can turn a pass back into a fail.

| Row | Pass mark | Today (Oct 23) |
|---|---|---|
| G01 exit book | HELD cells written, READY | READY (Oct 22) |
| D15 nightly builds | 30 clean runs in a row | 5 of 30 |
| D16 ledger snapshots | 30 in a row | 3 of 30 (needs the sign-in) |
| Two families validated | development plus validation, one holdout look each | SP1 holdout run done; SP3 dev+validation: not supported |
| Lost or empty runs (India) | the 24-hour line says none, 10 sessions in a row | 5 misses on Oct 23 (the token) |
| Read model | built after every session with no missing section, 10 in a row | 2 of 10 (Oct 21, 22) |
| Sign-in | 10 sessions with no "token dead" line | 0 |
| Exam (India, Phase 2) | knows, doesn't know, why at crypto's marks; voice on India screens | not built |
| No order path | leakcheck 9 of 9 every night | 9 of 9 |
| Guardrails | recorded every session; enforce switch built and off | recorded |
| Madhav's sentence | written | - |

The lost-runs rows are read by `jarvis/service/runcheck.py` (agent repo) since Oct 23: ten dated India proofs on NSE session days, holidays from the lake's own calendar.

## 5. Checkpoints

1. **Lock day (about 1 Nov):** SP3's remaining parts run (index book, 200 nulls, ablations, 12 start months, reverse priority, filter slices) and recorded; SZ2 selection in; the gate reads in the app; the "pinned on lock day" items pinned; this page loses "draft".
2. **Day 10 of clean sessions:** the read model, the sign-in and the lost-runs rows at 10 of 10; the India exam scored.
3. **Day 30 (about 5-8 Dec):** D15 and D16 at 30; the G02 sentence is Madhav's.

Between them the morning review reads the India gate and the due list every day; an overdue item becomes a repair-board request by itself.

## 6. Who may change what

- **Madhav decides** anything that trades, sizes, costs, changes a family's status, the gate, Rule A or B, spending and accounts; every pin above; the SP3 holdout sentence; the SZ2 decisions; anything on his father's account.
- **Claude** builds platform, checking, reading and voice; runs approved research through the registry; answers the board; never changes a pin without his recorded yes; never writes an order path (leakcheck refuses it).
- **The jobs** record. Nothing in the daily loop changes a rule.

## 7. Known limits at the draft

- **The sign-in is the whole schedule.** Three sessions lost (Oct 21-23). The TOTP *key* (the long key under Console's QR code, not the 6-digit code) fixes it in minutes; until then a manual sign-in between 22:00 and 23:40 Toronto on session nights.
- **Early numbers are red and are not a verdict:** the stock book Rs -42,989 realised on hold_20d exits (Oct 22), the daily call 0 of 3, Ananta's picks at the 52nd percentile of random, SP3 flat. Recorded; nothing is tuned.
- **History is region-blocked:** NSE's deal history answers "not accessible in your region" from Toronto (451), BSE 403. Forward recording (decision D9, Oct 22) is the default; a one-off pull from an India-located machine is Madhav's call.
- **Two review tasks on two models;** one hit a usage limit on Oct 22. One review for both markets once India locks.
- **The father-mode live question** is parked; Zerodha's own words fit "Ananta guides, he confirms each order under his own login".

## 8. Waiting for Madhav

| Item | Due | Recommendation |
|---|---|---|
| The Kite TOTP key | now | Set TOTP up again on Console and copy the long key into `~/ananta_private/kite_login.env`; fallback: manual sign-in Sun 25 Oct 22:00-23:40 Toronto. |
| SZ2 decision (a): a logged sealed purpose for the completed SP1 holdout run's own policy_trades 2024-26 | before the SZ2 selection | **Yes, logged**: the spec named that window before any data was seen. |
| SZ2 decision (b): the recorder's IV-shift calibration | same | **Keep 0 and state it** until R01's four weeks give a measured number (about 15 Nov), then one pre-registered sensitivity run. |
| SP3 holdout sentence | after the remaining parts | **Not yet**: do not spend the one confirmatory run on a policy that lost to its own baseline on seen data. |
| India history from an India-located machine | optional | Only if EV6/DEALS need it; forward recording is enough for the review point. |
| UPS and SSD (D27); residency (D28); the B13 list; a weekly 10-minute read of the drafts queue | - | As on the 22 Oct ledger. |

### Decisions of 23 Oct

Madhav, 23 Oct (in chat): "Will get TOTP fixed before Sunday. Yes for all others."

| Item | Decision | What the India task does |
|---|---|---|
| The Kite TOTP key | Madhav fixes it before Sunday 25 Oct | The 24 Oct check-in verifies `kite_autologin.log` says "auto sign-in ok"; if not by Sunday, the manual sign-in 22:00-23:40 Toronto. |
| SZ2 (a): a logged sealed purpose for the completed SP1 holdout run's own policy_trades 2024-26 | **yes, logged** | Record the purpose (`sealed_access.jsonl`) before the read; the SZ2 selection may then run as the spec wrote it. |
| SZ2 (b): the recorder's IV-shift calibration | **keep 0 and state it** | 0 stays, stated in the SZ2 results; one pre-registered sensitivity run with R01's measured shift after its four weeks (about 15 Nov). |
| SP3 holdout | **not yet** | The holdout stays sealed; `sealed.holdout_open('sp3_holdout')` keeps refusing. Finish the remaining parts (index book, nulls, ablations, start months, reverse priority, filter slices); then the question returns to Madhav with the numbers. |
| Lock India like crypto | **yes** | This page; lock day about 1 Nov. |
| The worker Mac (crypto #72) | hourly pull retry | `com.ananta.workerpull` on the main Mac (agent repo LOCK.md, Decisions of 23 Oct). |

### Decisions of 25 Oct (after the process audit, `claude/audit-2026-10-25-india-process`)

Madhav, 25 Oct (in chat): "be marked when input data is stale. we will start immediately on all these items very carefully and complete fixing all of them. at the end we audit the whole process again."

| Item | Decision | Where |
|---|---|---|
| A decision made on stale inputs | **marked, never stopped or dropped** | `india/paper.py input_check` writes `inputs` into every decision from 25 Oct (outside the hashed fields); older decisions are marked from their recorded context (`readmodel.decision_inputs`); the read model brief, the app's brief, the Evidence tracker ("Picks made on stale data") and the Ask carry the mark. No paper rule changed; `paper_rules` pin untouched. |
| Every audit item | fix all now; only time-bound items stay pending | The fix list in the audit doc; the re-audit closes it. |
| The account twin when the Zerodha snapshot is stale | **marked at the last session's NSE closes** (marks only; fills keep the snapshot rule) | New sealed purpose `account_marks` (`india/sealed.py read_marks`): one live session, the held symbols only, logged; `india/account.py` is the only caller (`tests/test_india_account_marks.py`). The view says which prices it used. |
| TMCV / TMPV cost basis | **checked: correct** | The broker splits the old Tata Motors cost 68.85% / 31.15%, exactly the published demerger split (record date 14 Oct 2025). The holding detail now says so and shows the pair's combined result (`india/account.py demerger_notes`). |
| The research book on screens | **shown in % per closed trade** beside the rupees | `jarvis/india/views.py books()` (`per_trade_pct`); the ₹50,000 slots are notional, not his money. |
| The firewall's static scan | **an allowlist naming each India-app reference by file and pattern, with its reason** | `india/firewall.py ALLOWED_REFS`; any other reference, or a new pattern in a listed file, still fails; the sign-in scope check now also sees paths built on a base constant (`tests/test_india_firewall_allowlist.py`). |
| H12 and H18 (partly true by construction) | **registered money follow-ups TWT-H12F and TWT-H18F** in the same teacher bar | `india/teachers.py`; results in `teachers_results_v1.md`. |
| SZ2 decision (a) of 23 Oct, carried out | **the logged purpose `sz2_selection` added** (Madhav's 23 Oct "yes, logged"; spec run as written) | `india/sealed.py read_sz2`: the completed SP1 holdout run's own policy trades 2024-01-01..2026-10-16 and, to price them as `sz2_v1.json` prescribes, their previous-session chains, their index minutes and the 16 Oct 2026 index closes; refused before that run is completed; every read logged in `manifests/sealed_access.jsonl`; the holdout-era trade table stays inside the sealed tree (`sealed.sz2_output_dir`). No SP1 rule is scored. SZ2 decision (b): IV shift 0, stated in `sz2_results.md`. Nothing live changes: `paper_config.json` sizing waits for Madhav on lock day. |
| SP3's remaining parts | **run on dev and validation only** (the holdout stays sealed) | `india/sp3extra.py`: INDEX rows into the ledger (same frozen bar, union_k 742), 200 state-shuffle nulls, 10 ablations, 12 start months, reverse priority, filter slices; results appended to `sp3_results.md`. |

## 9. After the window

Research that does not change a paper rule: the READY studies (C04, F07, I03, I04, I06, K01, EV5, EV6, EVC and the rest of the 52), the DEALS, FUNDS and TEACHER league traders, the shadow books with no history (futures, forex, commodities, results-day options; recording forward), the SP1 2027 refit (January), one voice across both markets (after each has stood alone), and live-readiness engineering built disabled in parallel (the order module behind leakcheck, broker-side stops, reconciliation, kill switch, drift alarm, cost profiles, per-account ledger, NAV units, the enforce switch) with a monthly India risk rehearsal, switch off.

**Parked drafts.** `PW-INDIA-DRAFTS`: the 10 learning-loop DRAFTs of 19-22 Oct (8 missed-movers patterns, 2 reference-traders patterns) were read on Oct 23 and parked (status PARKED in `missed_drafts.jsonl`, with the note): read together with the league once it has 20 sessions; a new paper rule needs a pre-registered test and Madhav's yes.

## 10. The end state Madhav opens

livetrading247.com → sign in → **Which Ananta?** → Crypto (locked 15 Oct, review 07:25, other traders 04:30, exam Sundays, day-60 14 Dec) or Indian market (locked about 1 Nov, review 07:45, league 22:30, exam Sundays, G02 about 5-8 Dec). Behind each: a frozen rulebook, a checker that proves every run, a gate read daily, a review that works the board, an app, Ask and voice that answer only from the record, a due list, and an after-the-window list. The only human work anywhere is the due list.
