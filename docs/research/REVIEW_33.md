# Review #33 (pre-registration): does Jarvis's pick beat a random coin? (the 14 Oct weekly ticket)

**Status: PRE-REGISTERED, forward test.** Written 2026-10-20 (about 14:30 UTC) and pushed before any outcome dated after the
push was computed. Sources: the weekly situation review of 14 Oct (`docs/repair_shop/weekly/2026-10-14.md`) and the gate and
pipeline review of 20 October (sections 2.2 and 2.3). Forward window 2026-10-21 00:00 UTC to 2026-12-14; one look, at
`CHECKPOINT-60`. Until `REVIEW_33_RESULTS.md` exists there is no result.

## Why
- **The ticket.** The weekly review of 7 to 14 Oct counted the lesson "random beat the pick" 3 times among Jarvis's closed buys
  (for example LINK and DOGE, both bought 8 Oct). It wrote one ticket: "random beat the pick: 3 times this week. Proposed: a
  pre-registered review of this pattern before any change."
- **Orphaned.** The ticket lives only in that markdown file. It was never filed as a request or in the ledger (gate review, section
  2.2: no owner).
- **The lesson's definition** (`learning.card`): a closed Jarvis trade whose net is not above its closed random twin's net. The
  twin is a random coin, opened at the same moment with the same plan in its own daily ranges.
- **The record so far:** Jarvis's book, 25 closed at -$7.77 per $100 against its twins' -$7.97 (to 20 Oct). Ledger question Q7
  counts 1 independent event.

**The question in plain words:** does Jarvis's own pick do better than a random coin traded with the same plan at the same moment?
This is ledger question Q7's question. This file fixes its pass mark and its window before the data exist.

## The tier that decides
- **Jarvis's book (`JARVIS`) and its twins (`JARVIS_RANDOM`), all coins and tiers (decides)**, paired by `brain_decisions.trade_id`
  and `random_id`.
- A pair counts when its TAKE decision is at or after 2026-10-21 00:00 UTC.
- **Reported beside, never counted:** the 10 pairs open at the push (entered 8 to 10 Oct; their marks are already partly seen) and
  every earlier pair.
- **Event count:** Q7's, so that the object keeps one count (RESEARCH_RULES section 2). Entries within 3 days of each other, on
  any coin, are one event (`scoreboard.independent_events(daily=True)` on `entry_t`). An event's value is the mean of its pairs'
  values.

## The test
- **Value per pair:** the trade's net minus the twin's net, in $ per $100 after each book's own cost.
- A leg still open after the 2026-12-14 daily close is marked at that close with `watch_engine.net`. Both legs are treated the same
  way.
- **z** = mean of event values / (standard deviation / square root of the number of events).
- **Reported beside:** the lesson count itself. For pairs with both legs closed, "pick beat random" against "random beat the pick",
  labelled exactly as `learning.card` labels them.

**Data, all recorded today:** `brain_decisions` (TAKE rows with `trade_id` and `random_id`), `evidence_trades`, and
`universe_bars.d1` for the marks. Nothing is built. No recorder is needed.

**Code version:** every function named here is used as it stands at origin/jarvis-4 commit 448cb21 (this file's parent commit).

**The likely count.**
- The brain has not bought since 10 Oct 02:10 UTC. Since the lock it decides 3 or 4 times a day, all PASS, mostly on attention-HIGH
  wakes on the same lab coins.
- It buys only where an edge is measured, and with the dial open there is none (reviews #26 and #29). So new pairs are likely only
  after the dial closes (H07 on tier A; `EV-DIAL-CLOSED`), or after a decision of Madhav's changes what wakes the brain
  (`OD-READS-WAKES`, `OD-PLAYBOOK-ATTENTION`).
- INSUFFICIENT is the likely reading on 14 Dec. It is recorded as such, not bent.

**Forward window and looks.**
- Window: TAKE decisions from 2026-10-21 00:00 UTC to 2026-12-14 23:59 UTC, marked at the 2026-12-14 close.
- Looks: **one**, at `CHECKPOINT-60`, run after the 2026-12-15 00:05 UTC daily close.
- Counting events first is not a look; computing any pair value is. If the count is under the minimum, nothing else is computed;
  only Madhav can extend the window, and the one look moves with it.
- Cells: 1, in the family "Jarvis's book against random" (Q7).

**Holdout.**
- The Evidence page shows Jarvis's book against its twins every day (`brain.report`, `vs_random_usd`), and the weekly review prints
  the lessons. Those displays existed at the push and are the running system. They are not a look as long as nothing in this file,
  or in how the brain buys, changes because of them.
- A change to the brain's buying made in the window because of that display makes this review "seen", and the results file says
  so.
- Any computation of this review's mean before `CHECKPOINT-60` is a look, and the results file names it.

**Lake header.**
- The results file opens with `format_header(lake_header(D, until=2026-12-15 00:00 UTC))` over the coins of the counted pairs
  (both legs), with D their universe daily candles in the window. If the weekly lake job has not reached the window's end, `until`
  is the lake's last complete day, and the header says so.
- Directly under it comes the live-feed line: the daily candles expected and present per coin, and the brain's lost runs in the
  window (failed or budget-dropped wakes from `brain_queue`), because a lost run is a pair that never formed.
- A result without both is a draft (RESEARCH_RULES section 4).

## Pass marks (frozen)
- **INSUFFICIENT:** fewer than 10 Q7 events.
- **PICK_BEATS_RANDOM:** all three hold:
  - the mean event value is above 0 with z of 2.0 or more;
  - the pick is ahead in more than half of the events;
  - the mean is still above 0 with the single largest event removed.
- **RANDOM_BEATS_PICK:** the mirror: mean below 0 with z of -2.0 or less, random ahead in more than half of the events, and still
  below 0 with the largest event removed.
- **NO_DIFFERENCE:** everything else.

## What each outcome changes (decided now)
Nothing changes by itself. Each line is a proposal to Madhav after the window, in the order he sets (LOCK section 9).
- **PICK_BEATS_RANDOM:** Q7 is answered "yes, in this window" in the ledger. Propose that Jarvis's book counts as evidence for the
  brain's picking inside its measured cells. `JARVIS` stays EVIDENCE in `strategy_status.json` until Madhav decides.
- **RANDOM_BEATS_PICK:** Q7 is answered "no". Propose that the brain's buys stay limited to measured cells (its default PASS), and
  that `JARVIS`'s verdict `modify_rules` gets this dated reason.
- **NO_DIFFERENCE or INSUFFICIENT:** Q7 stays open.
- **In every case,** the weekly ticket of 14 Oct is closed with "pre-registered in #33" and this review's verdict.

## Not in this review
- The bold book against its twin (review #37).
- The other two lessons: "stopped at the low" belongs to the stop question (review #31), and "missed winner" is a PASS lesson
  (review #34).
- When a lesson matures inside the weekly review: that is a plumbing fix (gate review, step 2), and this review scores everything
  once, at day 60.
