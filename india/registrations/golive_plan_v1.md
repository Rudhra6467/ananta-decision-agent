# India readiness plan (v1, 25 Nov 2026): every check, what it answers, and the order to go live

Madhav, 25 Nov 2026, in chat: "let's take out time and plan this out, organize everything, optimize everything ... see what exactly the other tests are doing and what exactly these tests are doing ... form a plan like how we can help Ananta get better organization of this work in the workflow and the order, and then ... the scheduling ... only the things that needed to be waited that gets waited, or else we can keep doing them." Agreed the same day: "Yes , let's sort this once for all. So that everything is sorted and organised in a way that helps us."

The go-live checklist (`pass_marks_v1.md`, "Going live") says what must be true: **the map**. This page says what answers each question and in what order the work goes: **the route**. The open list says what is still open: **the state**.

## 1. Six questions, and everything that answers them

Cost: **free** means code on the Mac; **plan** means a scheduled Claude session (the Claude plan, no API credit); **paid** means API credit.

**Q1. Did everything run, on time?**

| Check | How often | Cost |
|---|---|---|
| Lost-runs table and each job's proof of work (`india.morning`) | daily 07:20 | free |
| Schedule check: every job on its India time (`jarvis.india.schedule`) | daily 03:30 | free |
| Kite sign-in result, with a phone alert on failure | each session night | free |
| G02 / D15 / D16: clean sessions, nightly runs, ledger snapshots in a row | daily | free |
| R2 backup check (by size) and disk space | nightly | free |
| Sleep log (nights the Mac slept) in the self-check | all day | free |
| New: T11 restore drill, T12 job times and memory, T14 alerts reach the phone | before go-live | free |

**Q2. Is the data right?**

| Check | How often | Cost |
|---|---|---|
| Nightly build, integrity (duplicates, mappings, stale files, calendar), data gaps | nightly / evening | free |
| Lineage (what feeds what), freshness (datacheck), data audit | evening | free |
| Stale-input mark on every decision (since 25 Oct) | every decision | free |
| Firewall: sealed data and the Kite token boundary | nightly | free |
| Fact map: every saved file reaches what Ananta reads | 3 times a day | free |
| New: T2 calendar and clock walk, T9 data cross-check | before go-live | free |

**Q3. Did Ananta follow its own rules?**

| Check | How often | Cost |
|---|---|---|
| Lock test: no frozen file changed | every commit and nightly | free |
| Leak check, 9 rules: no order path, no future data, live and lab features equal, fills after signals | evening | free |
| Hash-chained ledgers and the options line's nightly replay (`sp1nightly`, `sp1paper.verify`) | nightly | free |
| Change book: every change written with its reason | every change | free |
| New: T1 the live rules applied (done, PASS), T5 does the rule follow itself (choices, picks, fills) | before go-live | free |

**Q4. Are its decisions any good?**

| Check | How often | Cost |
|---|---|---|
| Yardstick against random, always long and a coin flip | daily | free |
| Trials with written pass marks: options line, RX1, shadow trader, no-chase, RS, managed book, practice book | daily clocks, read at 20 or 60 sessions | free |
| Missed movers, reference traders, teacher books, reconstruction, SF1 shadow | daily | free |
| Research registry (SP3, SZ2 and the rest; history 2000-2023 only) | as registered | free |
| Stress test: money and options parts (run 1 done; run 2 after the 30th session) | twice | free |
| New: Ananta and Claude side by side; T8 how much is luck; T10 simple yardsticks | daily / before go-live | plan / free |

**Q5. Does it tell the truth?**

| Check | How often | Cost |
|---|---|---|
| Answer guard on every answer (a number must be in the facts) | every answer | free |
| "Is everything running?" answered by code | every ask | free |
| Self-check: parts that disagree (wrong day on a card, counts that differ) | all day | free |
| Weekly answer replay: the week's answers, the regression bank, 39 never-again cases | Saturday night, and after any Ask code change | paid |
| Weekly India exam (gate row D32) | Saturday night | paid |
| Stress test's words part (run 1 done; run 2 after the 30th session) | twice | paid |
| Random audit with the question bank v2: India's one audit (flag 275) | 29 Dec | plan + paid (US$8 limit) |
| New: T4 same number everywhere, T6 the Ask's facts without the model, T7 guard re-test; the side-by-side's words check | before go-live / daily | free / plan |

**Q6. Is live money safe?**

| Check | How often | Cost |
|---|---|---|
| Rule A, the live rules (options first: Rs 75,000, Rs 37,500 cap, one position overnight; stocks a week later: broker stops and survival rules on enforce) | on the live days | - |
| Stress test (benchmark and run 2) | twice | free |
| New: T13 the missed exit, T15 survival rules rehearsal, T14 alerts | before go-live | free |
| **The live path itself (flag 239)** | **not built yet** | - |

Underneath all six: 903 automated tests in records and 1,847 in the app; the lock tests run before every commit.

## 2. What taking stock found

1. **The critical path is the live path, not the tests.** There is no order module, enforce switch, broker-stop code or live reconciliation yet (flag 239). INDIA_LOCK.md section 9 lists that work as after-the-window: the order module behind the leak check, broker-side stops, reconciliation, kill switch, drift alarm, live cost profile, per-account ledger, the enforce switch. T13 and T15 test this path, so it is designed first.
2. **Going live needs a frozen file changed.** The leak check (pin `no_order_rule`) forbids every order call. The order code is built in its own folder and branch (a git worktree, `~/code/ananta-records-live`, branch `live-path`), which no running job reads and the nightly checks do not see, so G02's clean count is safe. It joins on the live day through the repair door, with Madhav's written yes.
3. **Answers are checked by many things, and four of them are paid.** The free checks (guard, T4, T6, T7, self-check) catch faults first; the paid ones (replay, exam, stress words, the audit) confirm. Changes to the Ask's code files land on Saturday daytime only, so the Saturday-night replay and exam test them in one paid run (any Ask code change also triggers a replay that night).
4. **Fixes reach the running services only when they restart, and no restart was planned.** The India service has run since Tue 24 Nov 07:40, so flag 237's fix of that morning is not live yet. A planned Saturday restart is Madhav's call (flag 279).
5. **India was audited twice:** decided 25 Nov, the 29 Dec random audit only (flag 278).
6. **Some one-off tests are worth keeping** (section 7).
7. Small things fixed today: flag 239's note named the old cap; the four trials and the random audit had no reminder (flags 271-275); the exam's real fail had no item (flag 276); flags 89 and 236 were one item; flag 83 was out of date.

## 3. How the work is organized

- **One map, one route, one list.** Every check sits under one of the six questions.
- **Free first, paid to confirm.**
- **Only wait for what must wait:** a calendar date (a trial's read, the 30th session) or Madhav. Everything else runs now, in parallel.
- **Never disturb the running system:** the rules in `prelive_tests_v1.md` (daytime only, scripts outside the repos, one fix at a time, a clean next night confirmed).
- **Most important first:** what blocks a checklist line, then the live path, then the tests, then the other fixes.
- **Go-live follows readiness, not the calendar.** If the live path is not ready when G02 reaches 30, the date moves.

## 4. Four tracks, in parallel

- **Track A, the live path (critical, flag 239).** 1) A written design first, for Madhav's yes: the order module; the options cap and overnight rule in code; the exits, including index-level stops (flag 270); broker stops for stocks (GTT); the enforce and kill switches; reconciliation of live fills against paper and random (flag 241); and how it joins on the live day. 2) Built switched off, in its worktree. 3) Tested by T13 and T15. 4) Reviewed by a separate agent that did not build it (Rule A: the order module reviewed).
- **Track B, the pre-live tests (free).** What they find feeds Tracks A and C.
- **Track C, the fixes that bear on go-live** (section 6).
- **Track D, the daily rhythm (automatic).** Nightly jobs, the morning summary, the India review at 07:45 with the side-by-side check.

## 5. The order

| Day | Must wait (a date or Madhav) | Runs now |
|---|---|---|
| Thu 26 Nov | the options line's 20-session read (flag 88, in the 07:45 review) | T2, T6, T7; Track A design written for Madhav's yes |
| Fri 27 Nov | RX1 and shadow trader reads (271, 272) | T4, T5; the Ask fixes built and tested, not landed; display fixes 230, 231, 236 |
| Sat 28 Nov | the exam and replay at night | the Ask fixes land in the day; T3, T8, T9; flag 124 checked; 14:00 restart if flag 279 is yes |
| Sun 29 Nov | - | T11, T12 (markets shut: heavy disk work is safest); the sign-in fixes 165, 210, 150, 152; Track A build if the design has his yes |
| Mon 30 Nov | no-chase read (273) | Track A build; T13 with flag 270; T10; flag 151 |
| Tue 1 Dec | T14 needs Madhav's phone | T15 on the built switch; T14; T1 again if a live rule changed; flags 153, 157, 168 |
| Wed 2 Dec | RS read (274) | fixes from the tests; flag 241 with Track A; Track A review |
| ~Thu 3 Dec | the 30th clean session, then stress run 2 (250) | the go-live read (238), when every checklist line is read |
| one week later | options live for a week | live stocks, the second step (flag 277) |

## 6. The open list, sorted (25 Nov)

Every India and shared work item now has its place. On the list, "before go-live" items carry their day as a due date; "after go-live" items wait for 14 Dec.

**Before go-live, by day:**
- Thu 26 Nov: 239 (the live path, design first); the tests 255 (T2), 260 (T6), 261 (T7).
- Fri 27 Nov: the Ask fixes, landed Sat: 276 (the exam's decide answer, gate D32), 226 (never-again), 229 and 252 (a holiday read as a session), 244 (the 30k question), 233 (counts named by book); display: 230 (trials list a session behind), 231 (managed book's clock and headline), 236 (the daily call off the screen); the tests 258 (T4), 259 (T5).
- Sat 28 Nov: 124 (check the keen audit's nine decisions in code); the tests 256 (T3), 262 (T8), 263 (T9).
- Sun 29 Nov: the sign-in and its night jobs: 165, 210, 150, 152; the tests 264 (T11), 265 (T12).
- Mon 30 Nov: 270 (index-level stops) and 151 (the morning note); the tests 257 (T13), 268 (T10).
- Tue 1 Dec: 153 (one price per option trade), 157 (one total), 168 (honest marks): what the paper-beside-live comparison reads; the tests 266 (T14), 267 (T15).
- Wed 2 Dec: 241 (live fills in the yardstick, built with Track A).

**After go-live (14 Dec):** 96, 131, 140, 146, 147, 154, 155, 169, 172, 194, 195, 198, 199, 204, 232, 234, 240, 242. They are kept and dated, so the 14 Dec morning review brings them up.

**Joined to the test that covers them (closed into it):** 105 into T3, 170 into T7, 214 into T5, 248 into T9.

**Dated reads (unchanged):** 88, 197 and 243 (the options line, 26 Nov); 132 (26 Nov); 271-274 (the trials); 238 and 250 (go-live and stress run 2); 253 (the side-by-side summary); 90 (10 Dec, crypto only); 128 (29 Dec, with the random audit); 275 (29 Dec); 166 (SF1, months).

## 7. After each pre-live test: kept or closed

| Test | After go-live |
|---|---|
| T1 live rules | re-run on the live day and whenever a live rule changes |
| T2 calendar walk | kept as an automated test (before each new year's holiday list) |
| T3 fire drills | monthly |
| T4 same number | kept nightly in the self-check |
| T5 rule follows itself | kept nightly with the options line's replay |
| T6 facts without the model | kept nightly (free), ahead of the Saturday paid replay |
| T7 guard re-test | kept in the automated tests |
| T8 luck, T9 data cross-check | quarterly |
| T10 yardsticks | kept in the daily yardstick |
| T11 restore, T14 alerts, T15 rehearsal | monthly (T15 is the monthly India risk rehearsal) |
| T12 job times | kept in the morning summary |
| T13 missed exit | a written runbook, read monthly |

## 8. Who does what, and when

- **The nightly and session jobs** (launchd, Toronto evenings and nights): unchanged.
- **The India morning review**, 07:45 daily (scheduled): lost runs, never-again, the self-check, evidence, the side-by-side grade and call, the board. It reports the readiness items and leaves their work to the readiness run.
- **The India readiness run**, 08:37 daily (scheduled, from Thu 26 Nov): works this page's order, most important first, until the go-live read is with Madhav; then it turns itself off. It stops starting new work at 18:30 and never works during the sign-in, session or nightly windows.
- **Saturday:** the Ask's code files (`jarvis/india/ask.py`, `askprompt.py`, `askwords.py`, `answerguide.py`, `livesession.py`, `numcheck.py`, `neveragain.py`, `lookup.py`) change only on Saturday daytime, before 19:00, so one paid replay and exam test them. At 14:00, a planned restart of the services, only if flag 279 has Madhav's yes.
- **Madhav:** the Track A design (his yes); flag 279; the phone checks of T14 (Tue 1 Dec); the written yes on each live day.

## 9. Decisions

- **Decided 25 Nov:** this plan; live in two steps (flag 277); India once in the audits (flag 278); the daily readiness run; the options money and cap (flag 269). All are recorded in INDIA_LOCK.md, "Decisions of 25 Nov".
- **Waiting:** the planned Saturday restart (flag 279); the Track A design (filed on Thu 26 Nov); the leak check's change and the written yes on each live day.

## 10. Where everything lives

The map: `pass_marks_v1.md`. The route: this page. The state: the open list (app `jarvis/service/openlist.py`). The tests: `prelive_tests_v1.md`, with results in `prelive/`. The side-by-side: `claude_compare_v1.md` and `claude_compare.jsonl`. Decisions: `docs/INDIA_LOCK.md`. The live path's code, until the live day: the worktree `~/code/ananta-records-live` (branch `live-path`).
