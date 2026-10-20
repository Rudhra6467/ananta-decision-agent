# Ananta crypto: the decision map, the seven areas, and the learning loop (20 Oct 2026)

Madhav, 20 Oct 09:39: "It's not about how much money we make. It's about taking the right and best decision in the given scenario."

Everything here is judged by that standard. It comes from four independent read-only reviews done today:
- a decision audit of 556 decision points, 13 to 20 Oct;
- a silent-failure audit of every job since 1 Oct;
- a review of the 27 readiness checks and the repair-shop pipeline;
- a new execution-realism check.

The working files are on the Mac under `~/ananta_runs/decision_audit/`, `silent_audit/` and `gate_review/`.

---

## 1. The headline: decisions are mostly right; the system around them is weak

**Decision quality, 13 to 20 Oct:** 537 of the 550 judged decisions were the right call; 6 are too recent to judge.

| | Good outcome | Bad outcome |
|---|---|---|
| **Right decision** | 236 | 301 (noise: mostly measuring books losing as their verdicts predicted) |
| **Wrong decision** | 5 (luck) | 8 |

- **The brain passed on all 103 decisions it saved.** The coins it passed on fell 8.1% on average over the next 5 days; only 8 of 92 would have beaten their costs.
- **Holding cash and the core by the dial was right.** The median liquid coin fell 6.1% (only 19% rose); the $500 book fell 1.0%.
- **The 3 misses (NIL, TIA, GTC) and INJ were right to skip.** No measured rule covers a breakout away from support, and chasing the first close above the 20-day high lost on 6 of 7 coins this week (−9.2%).

**The 13 wrong decisions have three causes:**
1. **8 stop exits: the written rule and the code disagree.**
   - The written zone stop (`chain.py`, the STOP_ZONE card) is a daily close half a range under the zone. The code sells on any touch during the day.
   - All 18 stops in the window (8 for Jarvis, 10 for its twins) fired intraday while the day's close stayed above the stop. 7 of them fell in one 6-minute flush on 15 Oct, when NDAX's spread was 2.5–3.4%.
   - Under the written rule, Jarvis's 8 would have made −$65.95 instead of −$85.74. That is one market event, so it is a pointer, not proof.
2. **3 bold-book picks misread the trend rule.**
   - AAVE and SUI were bought "as T3" on days when T3's own rule rated them OUT; the brain read "20-day exit" as "hold 20 days".
   - A second BTC buy doubled the first. You closed that gap on 16 Oct.
3. **2 trend-book buys never happened** (TRX, WLD, 17 Oct) because Hands was down for 426 minutes. Fixed today: Hands now restarts by itself.

**The C− on engine decisions graded trade outcomes, not decisions.** The real weak areas are execution realism, the learning loop, and seeing failures.

---

## 2. The decision map: situation → right decision → evidence → what Ananta does → gap

| # | Situation | The right decision | Evidence | What Ananta does today | Gap and fix |
|---|---|---|---|---|---|
| 1 | Dial open; a zone entry, attention spike or Explorer setup on any coin | **Pass** | Zone touch lost with every exit on 8 years (wont_take_again); no intraday setup beats costs (#1, #3, #24); 5-day result of the passes −8.1% | Passes (103 of 103) | None in the decision. The ranker sent the brain worse candidates than the ones it never saw (−1.41 pts vs +0.37): pre-registered for the window. |
| 2 | Dial open; the account's core | **Hold BTC 40%, ETH 20%** by the dial | Review #25; the $500 book −1.0% while the median coin fell 6.1% | Holds by its frozen rules | ETH really costs 2.7× the table (0.427% a side measured vs 0.284%). S2 on 26 Oct reprices it; the decision is yours. |
| 3 | Dial open; trend books | **Follow T3** (in above the 20-day average, out under it) | #12, #20, #30; T3 −7.6% vs equal-weight hold −11.6% | Follows (8 of 10 right); 2 buys blocked by Hands | Hands is now a launchd job. Only 46% of T30's fills could really have been had at NDAX's price that minute (the new realism check), so its paper results flatter it. |
| 4 | **Dial closed**; tier A dip (H07) | **Buy the dip:** the one measured edge | Reviews #26 and #29: +5.1% a trade over random, tier A, dial closed | Can't happen yet: the dial has been open since August | Rule A needs this state. The window will probably have to be extended (section 5). |
| 5 | Breakout away from support (NIL, TIA, GTC, INJ) | **Stay out** (no measured rule) | Breakouts through zones failed on every tier (#21); the chase lost 6 of 7 this week | Stays out | Request #38 is pre-registered as a forward test on the window's own data. |
| 6 | A stop level is touched intraday in a flush | **Today:** the code sells on the touch. **As written:** sell only on a daily close under the zone | Both untested (STOP_ZONE is UNTESTED); this window favours the close rule, from one event | Sells on the touch, at 2.5–3.4% spreads | **Your decision:** which one is the rule? Recommendation: change nothing in the window (Rule B), score both side by side from today (pre-registered), and decide at day 60. Meanwhile the card is corrected to say what the code does. |
| 7 | The bold book's one idea a day, dial open | **The pick a measured rule backs that day:** BTC by the dial, or a coin T3 rates IN | The decision audit: 3 of 6 picks cited T3 when T3 rated the coin OUT | Picks "as T3" without T3's rating | **Your decision:** give the bold book each coin's T3 rating and correct the T3 wording it reads. This changes a registered experiment. |
| 8 | The system is unhealthy (kill switch unreadable, stale price) | **No trade** | The guard failed safe on 16–17 Oct | No trade; but signals and their random twins were refused unevenly | Hands auto-restart; the lost-runs checker reports refusals. |
| 9 | A paper fill at a price NDAX didn't offer | **Price it at NDAX's real quote** | The new realism check: 86 of 142 measurable fills since 12 Oct were achievable (61%) | Books price from candles plus a cost table | Realism report daily (built); S2 on 26 Oct; the readiness-check change below. |

---

## 3. The seven areas: what's wrong, what's done today, what's next

| Area (grade) | What is actually wrong (evidence) | Done today | Next (allowed now) | Needs you |
|---|---|---|---|---|
| **Engine decisions** (C−) | Decisions right 537 of 550. Wrong: stop rule vs code (8), bold T3 misread (3), Hands (2) | Decision audit; STOP-CLOSE vs STOP-TOUCH pre-registration (in progress) | Daily process line in the morning review (did each decision follow the dial and the measured edges); outcomes of the pre-registered findings stay hidden until 14 Dec so the forward tests stay clean | The stop rule (#6 above); the bold book's T3 rating (#7) |
| **Risk and survival** (B) | Cash was right; the guard failed safe; the stops sold into 2.5–3.4% spreads | Hands is a launchd job, tested: killed on purpose and back in 8 s | Monthly risk rehearsal before 30 Oct (ENGINE-RISK-REHEARSAL) | none |
| **Execution realism** (D) | The `engine_execution` check cannot fail (the $500 book copies its fill from the very quote it is checked against). Only 61% of paper fills were achievable at NDAX; T30 46%; ETH 2.7× the cost table | `realism.py`: every paper fill of every book checked against the worker's independent NDAX quote for that minute | In the morning review daily; S2 on 26 Oct | The readiness-check wording (section 4) |
| **Learning loop** (D+) | Stopped for 4 reasons: Rule B; triggers that can't fire; nobody owns weekly tickets; a hand-written ledger. The missed-moves review was **skipped 9 of 11 nights** (a bug, still happening). Other traders rebuilt only once (30 Sep) | Daily other-traders rebuild installed (04:30); the worker capture installs itself when the worker is back; 8 parked findings being pre-registered | Fix the skipped reviews and add profit scoring (branch in progress); weekly tickets filed automatically | A shadow lane (OD-SHADOW-LANE, section 6) |
| **Data and running health** (B−) | 226 brain decisions paid for but never saved; the error was swallowed. 304 wakes dropped. 0 brain decisions on 15–17 Oct. 15-minute job errors are thrown away. A failed save after a buy could orphan a trade | Run checker, 49 parts, wired into the morning review as a section that is never omitted | Correct the "15-hour hole" note (the worker recorded every minute); LOCK errata | Live-code fixes: log every failed save, one transaction per decision, a retry for the stance |
| **Voice and app** (B) | Screen didn't match speech (7 of 38); first words clipped | Both fixes built and tested (80 service tests, 56 app checks) | none | "deploy voice" |
| **Cost** (A−) | The brain spent $4.26 against its $1 cap on 15 Oct, because failed saves didn't count | Already fixed (15 Oct) | The checker reconciles paid calls against saved decisions daily | none |

---

## 4. The readiness checks: honest review

**Reading:** 20 of 27 at 10:30 today, after the exam (20/20, 10/10, 5/5 on the "why" questions, 2/2 consistency).

**It is not "all good":**
- **12 of the 20 passes are hand-written** verdicts no code re-checks.
- **Four checks can't move** while the dial is open and the brain doesn't buy: `strategy_regimes`, `agent_no_failed_rules`, `engine_sizing`, `engine_execution`.
- **Three pass or would pass wrongly:**
  - `engine_execution` can't fail by construction;
  - `strategy_baselines` passes on the retired Explorer (−$0.90 vs random −$1.05, both losing);
  - `ops_outages` stayed green through the Hands outage and 7 hours with no Explorer scans.
- **Not measured at all:** the quality of PASSes (they were mostly right), lost runs, the idle brain, the bold book, cost realism per coin, how fast the learning loop moves.

**Forecast:**
- With today's changes and the Sunday exam: 18 to 24 over the next three weeks.
- It can't reach 27 before a dial-closed spell, so the honest answer on 14 Dec will probably be "not yet: extend the window" (Rule A says extend, never bend).

**My correction on the execution-check yes you gave:** only the $500 book is truly priced at NDAX. Counting "every NDAX-priced book" would change nothing, and counting the fixed-$100 books for sizing would let the check pass without the $500 book's sizing ever running live. So I recommend instead:
- **`engine_execution`** counts every paper fill of every book, judged against the worker's independent NDAX quote for that minute. Pass: at least 20 fills, at least 90% achievable, and the median gap within 5 bp.
- **`engine_sizing`** stays on the $500 book only.

This is a gate change, so I'll record it only after you say yes to this exact wording.

**Other gate changes to put to you as one bundle** (each needs your recorded yes):
- `strategy_baselines` points at the account's books, adding buy-and-hold and the BTC 50-day benchmark;
- `ops_outages` counts part outages and the time the worker can't see anything;
- `agent_cites` counts conversations only (scheduled briefs inflate it);
- the bold book is added to `agent_no_failed_rules`;
- `strategy_regimes` uses the stricter event count;
- each hand-written check gets an evidence date and an expiry.

---

## 5. Your specific questions

**Missed moves: what I would have done, what it did.**
- Same calls: all four misses were right to skip.
- The fix is in the scoring. "Caught" meant some watch held the coin, usually a monitor-only one. The $500 book caught none of the 15. The 28 "in it" trades made +$7.85, and −$46.38 without one AVA trade. 22 of the 28 are from books marked won't-take-again.
- New rule: a catch counts only if a book allowed to trade held it, with its profit or loss attached (being built).
- Bigger: the review of the live 10 and the 30-coin tier was **skipped 9 of 11 nights** because a newer review writes its rows first. Being fixed; the skipped days will be re-run.

**Other traders, daily: why not?** You're right; daily is how we learn.
- It was quarterly because the 30 Sep study found their timing edge was about a tenth of trading costs, and continuous capture was marked optional.
- Now:
  - the worker saves 59 accounts' fills every day (installs itself when the worker Mac is back online);
  - a 04:30 job rebuilds yesterday's trades on our coins and sorts each one: we had a rule and took it / we had a rule but passed (and why) / no rule of ours covers it / they lost after costs;
  - a situation that repeats on 3 days in 7 files a draft request. Never a rule or a copy signal: other traders stay reference only (D8).

**Repair shop to engine: what's the problem and the way forward.**
- **The problem.** Rule B is the intended reason nothing reaches the engine. Behind it the inputs dried up:
  - the brain gets almost nothing to decide;
  - weekly lessons mature after the weekly review has run;
  - missed-move repeats need 5 separate days;
  - the 14 Oct "random beat the pick" ticket was never filed;
  - the ledger is hand-written.
- **The way forward, in three steps:**
  1. **Now (allowed):** pre-register every parked finding with the window's own live data as its fresh test, to be scored once at day 60: done, reviews #31-#38 (docs/research/PREREG_WINDOW_2026-10-20.md); their results stay hidden until 14 Dec.
  2. **Now:** a learning-loop section in the morning review, plus small fixes (file weekly tickets, count lessons when they mature).
  3. **Needs your yes (OD-SHADOW-LANE):** a blind, append-only shadow log that records what each pre-registered rule would have done each day, unseen until day 60, never touching a book.

**The 227 lost brain wake-ups: why, why nobody saw it, what else.**
- **Why.** A 14 Oct change added 2 columns to the decisions table, but the save still wrote 18 values. From 14 Oct 22:02 to 15 Oct 08:26 UTC every decision was paid for and then failed to save. The error was caught and written only into the queue row: no log line, no alert.
- **The knock-on.** With nothing saved, the spending cap and the 6-hour cooldown stopped working: $4.65 spent, 304 more wakes dropped, 0 brain decisions on 15–17 Oct.
- **Why nobody saw it:**
  - the watchdog checks that parts are alive, not that they did work;
  - the morning review only greps for tracebacks, and this never reached the log;
  - "no brain buy since 10 Oct" reads the same whether the brain passes or saves nothing;
  - the sprint's rebuild checks can't see rows that were never written.
- **More of the same kind, now listed:**
  - the skipped missed-move reviews (still happening);
  - 15-minute job errors thrown away;
  - a failed save after a buy could orphan a trade;
  - the stance paid for unreadable replies on 18–19 Oct;
  - outage minutes under-counted when the Mac sleeps;
  - India's evening chain reports success when steps failed.
- **How we keep finding them:** the run checker counts work, not heartbeats. It covers 49 parts, each with a minimum amount of work, reconciles counts that must agree (paid against saved), and is a section of the morning review that can never be left out. On today's data it caught all of the above.

**Readiness checks.** Section 4.

---

## 6. Waiting for you (in order of importance)

1. **"deploy voice":** both voice fixes, plus the missed-moves fix once it passes, in one restart.
2. **The execution-check wording** in section 4 (independent NDAX quote; sizing stays on the $500 book).
3. **The stop rule:** keep the touch stop running, score the close stop beside it, and decide at day 60 (recommended).
4. **The bold book:** give it each coin's T3 rating (recommended yes).
5. **OD-SHADOW-LANE:** a blind forward log for the pre-registered findings (recommended yes).
6. **The live-code reliability fixes** from section 3, as one reviewed branch:
   - log and alert every failed save;
   - one transaction per decision;
   - a stance retry;
   - 15-minute job errors recorded.
7. **SP3 (India) bar:** A (recommended) or B.
8. Physical: the worker Mac keeps dropping off the network (#72).
