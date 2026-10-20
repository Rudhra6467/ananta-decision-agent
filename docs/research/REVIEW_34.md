# Review #34 (pre-registration): are the brain's PASSes right, and does the ranker send it the right coins?

**Status: PRE-REGISTERED, forward test.** Written 2026-10-20 (about 14:30 UTC) and pushed before any outcome dated after the
push was computed. Sources: the gate and pipeline review of 20 October (section 1.3, item 1; Part 2, step 1) and the decision
audit of 13 to 20 October (section 4.1). Forward window 2026-10-21 00:00 UTC to 2026-12-14; one look, at `CHECKPOINT-60`.
Until `REVIEW_34_RESULTS.md` exists there is no result.

## Why
- **The passes look right.** From 5 to 14 Oct the brain logged 264 PASSes with a five-day result. The coins it declined moved
  -7.79% on average in five days, and -1.41 points against the universe median (`after_5d_ex`); only 42% beat the median.
- **The ranker may be backwards.** The 2,189 wakes it never reviewed (`brain_unreviewed`) ended +0.37 points over the median, so
  the ranker may have sent the brain worse candidates than the ones it turned away (gate review, section 1.3).
- **The audit's week.** The decision audit of 13 to 20 Oct agrees on the first part: 92 PASSes with a result, -8.1% raw and -0.8
  points against the median, 49 of 92 ahead. It also found that the 1,183 zone entries ranked too low fell 5.2%.
- **Not measured by the gate.** No gate check measures decision quality on a PASS.

**The questions in plain words:**
- **(A)** Do the coins the brain passes on do any better than the median coin over the next five days?
- **(B)** Does the ranker send the brain worse candidates than the ones it turns away?

## The tier that decides
Every tier. Two cells, each with its own population.
- **A (decides A):** every brain PASS (`brain_decisions`, action PASS) decided from 2026-10-21 00:00 UTC to 2026-12-09 00:00 UTC,
  so that its five-day result exists by the 2026-12-14 close.
- **B (decides B):** on each UTC day, two groups, the two the ranker separates (`brain.process`):
  - the decided wakes: every `brain_decisions` row that day, PASS or TAKE;
  - the ranked-out wakes: `brain_unreviewed` rows whose reason starts "ranked too low" or "waited 45 minutes".
  Same dates as A.
- **Reported beside B, never deciding:** monitoring-only wakes (kept from the brain by the registry, not by the ranker) and wakes
  dropped because the dial was closed.
- **Event count, both cells:** market days, the decision's UTC day (RESEARCH_RULES section 2's rule for moments; missed.py counts
  days the same way). A day's value is the mean of its rows.

## The test
**Scoring.** Each row is scored exactly as `brain.settle_passes` and `brain.settle_unreviewed` score it at origin/jarvis-4 commit
448cb21 (this file's parent commit):
- price = the row's price;
- the five-day close = the coin's first daily close at least five full days later (`_coin_daily`);
- excess = the coin's move minus `brain.market_median_move` for the same day and horizon.

TAKE rows in B are scored the same way from their decision price: the coin's move, not the trade's result. The excess columns are
recomputed with that code. The recorded `after_5d_ex` values are shown beside as a check, because a later change of the live
scoring (for example the audit's fix 8) must not change this test.

**Cell A.** The statistic is the mean of the day values. Five-day horizons on consecutive days overlap, so z comes from a
moving-block bootstrap over days: blocks of 5 market days, 10,000 draws, seed 34. z = mean / the standard deviation of the
bootstrap means.

**Cell B.** On days where both groups have scored rows, the day value is the mean excess of the ranked-out wakes minus the mean
excess of the decided wakes. The bootstrap is the same as A's.

**The cost for A's second mark:** the median of `2 x registry.cost(coin)` over the passed rows.

**Data, all recorded today:** `brain_decisions`, `brain_unreviewed`, `brain_queue`, the universe feed's and the Explorer's daily
candles. Nothing is built. No recorder is needed.

**The likely counts.**
- **A:** since 18 Oct the brain decides 3 or 4 times a day, all PASS (attention-HIGH on ADA, LTC, XRP and BCH, plus one H07 tier A
  and one M2a tier B). That gives about 40 or more market days.
- **B:** since the lock, zone entries and Explorer setups are monitoring only (`wakes_brain` false in the registry), and from
  17 to 20 Oct the ranker turned away one wake. B is likely INSUFFICIENT unless the registry lets more kinds wake the brain.
  It is recorded as such, not bent.

**Forward window and looks.**
- Window: decisions and wakes from 2026-10-21 00:00 UTC to 2026-12-09 00:00 UTC, scored with data to the 2026-12-14 close.
- Looks: **one**, at `CHECKPOINT-60`, run after the 2026-12-15 00:05 UTC daily close.
- Counting days first is not a look; computing any excess is. If a count is under its minimum, that cell computes nothing; only
  Madhav can extend the window, and the one look moves with it.
- Cells: 2 (A and B), in the family "decision quality".

**Holdout.**
- `brain.ranking_audit` and the weekly review's credit table compute these averages when someone calls them. The gate review
  proposes a "PASS quality" line in the morning review.
- To keep this test clean, any such line added before `CHECKPOINT-60` shows counts only (decisions made, rows scored), not the
  excess figures.
- Any display of the excess figures for the window before `CHECKPOINT-60` is a look, counted and named in the results file.

**Lake header.**
- The results file opens with `format_header(lake_header(D, until=2026-12-15 00:00 UTC))` over the coins of the scored rows, with
  D their universe daily candles in the window. If the weekly lake job has not reached the window's end, `until` is the lake's
  last complete day, and the header says so.
- Directly under it comes the live-feed line: the daily candles expected and present per coin, the days with fewer than 20 coins
  in the market median (excess left empty), and the brain's lost runs (failed or budget-dropped wakes).
- A result without both is a draft (RESEARCH_RULES section 4).

## Pass marks (frozen)
**A:**
- **INSUFFICIENT:** fewer than 10 market days.
- **PASSES_RIGHT:** the mean day excess is 0 or below, or it is above 0 with z under 2.0.
- **PASSES_COSTLY:** the mean day excess is above the median round-trip cost, with z of 2.0 or more. The declined coins beat the
  median coin by more than buying them would have cost.
- **PASSES_MIXED:** the mean is above 0 with z of 2.0 or more, but under the cost.

**B:**
- **INSUFFICIENT:** fewer than 10 days with both groups present.
- **RANKER_SENDS_WORSE:** the mean day value is above 0 with z of 2.0 or more.
- **RANKER_SENDS_BETTER:** the mean day value is below 0 with z of -2.0 or less.
- **NO_DIFFERENCE:** everything else.

## What each outcome changes (decided now)
Nothing changes by itself. Each line is a proposal to Madhav after the window, in the order he sets (LOCK section 9).
- **PASSES_RIGHT:** propose a gate check for PASS quality using this measure (the gate review's "four new checks"). That is a
  `gate_definition` change, so Madhav decides. The brain's default PASS stands.
- **PASSES_COSTLY:** propose a pre-registered review of what the passes declined (by trigger and tier) before any change to the
  brain's stance.
- **PASSES_MIXED:** reported; nothing is proposed beyond it.
- **RANKER_SENDS_WORSE:** propose a review of `brain.score` and `TRIGGER_POINTS` (review #28). This is a question for a review,
  not a change.
- **RANKER_SENDS_BETTER, NO_DIFFERENCE or INSUFFICIENT:** reported; nothing changes.

## Not in this review
- Why a pass was made (its thesis), and the brain's stated confidence against outcomes (calibration).
- One-day results, including the audit's fix 8 to score from the nearest daily close.
- The 226 decisions lost on 14 and 15 Oct.
- The attention score as a signal (review #35).
