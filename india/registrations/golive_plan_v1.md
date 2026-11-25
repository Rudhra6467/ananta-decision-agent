# India readiness plan (v1, written 25 Nov 2026): every check, what it answers, and the order to go live

Madhav, 25 Nov 2026, in chat: "let's take out time and plan this out, organize everything, optimize everything ... see what exactly the other tests are doing and what exactly these tests are doing ... form a plan like how we can help Ananta get better organization of this work in the workflow and the order, and then ... the scheduling ... only the things that needed to be waited that gets waited, or else we can keep doing them."

This page is the plan: how and when we get to the go-live checklist (`pass_marks_v1.md`, "Going live"). The checklist says what must be true. The open list says what is still open. This page says what answers each question, and in what order the work goes.

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
| Random audit with the question bank v2 (flag 275) | 29 Dec | plan + paid (US$8 limit) |
| Monthly outside grading of both markets (flag 90) | 10 Dec | paid |
| New: T4 same number everywhere, T6 the Ask's facts without the model, T7 guard re-test; the side-by-side's words check | before go-live / daily | free / plan |

**Q6. Is live money safe?**

| Check | How often | Cost |
|---|---|---|
| Rule A, the live rules (Rs 75,000 options money, Rs 37,500 cap, one position overnight, broker stops for stocks, survival rules on enforce) | on the live day | - |
| Stress test (benchmark and run 2) | twice | free |
| New: T13 the missed exit, T15 survival rules rehearsal, T14 alerts | before go-live | free |
| **The live path itself (flag 239)** | **not built yet** | - |

Underneath all six: 903 automated tests in records and 1,847 in the app; the lock tests run before every commit.

## 2. What taking stock found

1. **The critical path is the live path, not the tests.** There is no order module, enforce switch, broker-stop code or live reconciliation yet (flag 239). INDIA_LOCK.md section 9 lists that work as after-the-window: the order module behind the leak check, broker-side stops, reconciliation, kill switch, drift alarm, live cost profile, per-account ledger, the enforce switch. T13 and T15 test this path, so it has to be designed first.
2. **Going live needs a frozen file changed.** The leak check (pin `no_order_rule`) forbids every order call. The order code must be built where the nightly leak check does not see it (else the nightly fails and G02's clean count restarts). It joins the system on the live day, through the repair door with Madhav's written yes.
3. **Answers are checked by many things, and four of them are paid.** The free checks (guard, T4, T6, T7, self-check) should catch faults first; the paid ones (replay, exam, stress words, audits) then confirm. Fixes to the Ask should land just before the Saturday replay, so one paid run tests them all (each Ask code change also triggers a replay that night).
4. **Two audits overlap on India:** the monthly outside grading (flag 90, 10 Dec) and the random audit (flag 275, 29 Dec). India once is enough: the 29 Dec audit (Madhav's call, flag 278).
5. **Some one-off tests are worth keeping.** A fault found once comes back (the holiday words, numbers that disagree). After each pre-live test it is either closed as one-off or kept running (section 4).
6. Small things: flag 239's note still named the old Rs 25,000 cap (updated today); the four trials and the random audit had no reminder (flags 271-275, added today); the exam's real fail had no item (flag 276).

## 3. How the work is organized

- **One map, one list.** The checklist is the map, the open list is the state, this page is the route. Every check sits under one of the six questions.
- **Free first, paid to confirm.**
- **Only wait for what must wait:** a calendar date (a trial's read, the 30th session) or Madhav. Everything else runs now, in parallel.
- **Never disturb the running system:** the rules in `prelive_tests_v1.md` (daytime only, scripts outside the repos, one fix at a time, a clean next night confirmed).
- **Go-live follows readiness, not the calendar.** If the live path is not ready when G02 reaches 30, the date moves.

## 4. Four tracks, in parallel

**Track A: the live path (critical path, flag 239).** 1) A written design first: the order module, the options cap and overnight rule in code, the exits (flag 270: index-level stops), broker stops for stocks (GTT), the enforce switch, the kill switch, reconciliation of live fills against paper, and how it joins the system on the live day. 2) Built switched off, outside the leak check's view. 3) Tested by T13 and T15. 4) Reviewed (Rule A: the order module reviewed).

**Track B: the pre-live tests (free).** Faults they find feed Tracks A and C.

**Track C: fixes that bear on go-live.** Before the Saturday paid runs: the exam's decide answer (flag 276), the never-again misses (226), the holiday words (229, 252), the 30k-question answer (244). Then what the tests find.

**Track D: the daily rhythm (already automatic).** Nightly jobs, the morning summary, the India review at 07:45 with the side-by-side check.

## 5. The order

| Day | Must wait (date or Madhav) | Runs now |
|---|---|---|
| Thu 26 Nov | options line 20-session read (flag 88) | T2 calendar walk; T6 facts without the model; T7 guard re-test; Track A design |
| Fri 27 Nov | RX1 and shadow trader reads (271, 272) | T4 same number everywhere; T5 rule follows itself; Ask fixes built and tested |
| Sat 28 Nov | weekly exam and replay at night | Ask fixes land in the day (one paid run tests them); T3 fire drills; T8 luck count; T9 data cross-check |
| Sun 29 Nov | - | T11 restore drill and T12 job times (markets shut; heavy disk work is safest); Track A build |
| Mon 30 Nov | no-chase read (273) | Track A build; T13 missed exit on its design; T10 yardsticks |
| Tue 1 Dec | T14 needs Madhav's phone | T15 survival rehearsal on the built switch; T14 alerts; T1 re-run if a live rule changed |
| Wed 2 Dec | RS read (274) | fixes from the tests; Track A review |
| ~Thu 3 Dec | 30th clean session, then stress run 2 (250) | the go-live read (238) when every checklist line is read |

## 6. After each pre-live test: kept or closed

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

## 7. Decisions coming up for Madhav

- The daily test runner's schedule (next step, after this plan).
- India once in the audits: the 29 Dec random audit only (flag 278).
- Live in two steps: options first, stocks a week later (flag 277).
- Track A's design (the order path, the exits for index-level stops), then the frozen leak check's change on the live day.
- The written yes on the live day (Rule A).

## 8. Where everything lives

The map: `pass_marks_v1.md` (the go-live checklist). The route: this page. The state: the open list (app `jarvis/service/openlist.py`). The tests: `prelive_tests_v1.md`, results in `prelive/`. The side-by-side: `claude_compare_v1.md` and `claude_compare.jsonl`. Decisions: `docs/INDIA_LOCK.md`.
