# Review #35 (pre-registration): does the attention score point at better coins? (measures only)

**Status: PRE-REGISTERED, forward test; it measures and decides nothing.** Written 2026-10-20 (about 14:30 UTC) and pushed before
any outcome dated after the push was computed. Sources: LOCK section 7 ("Zone entries still ring the phone"), `OD-PLAYBOOK-ATTENTION`
(due 31 Oct), the decision audit of 13 to 20 October (section 1.7, fix 10) and the gate and pipeline review of 20 October (Part 2,
step 1). Forward window 2026-10-21 00:00 UTC to 2026-12-14; one look, at `CHECKPOINT-60`. Until `REVIEW_35_RESULTS.md` exists
there is no result.

## Why
- **The score.** `zones_watch.attention` scores each of the lab 10 every 15 minutes:
  - in a zone: 1 point;
  - a zone kind that history supports: 2;
  - came down into the zone within 5 days: 1;
  - market allowed: 2;
  - Madhav's setup showing: 2 (one sign away: 1).
  At 6 or more the level is HIGH, which wakes the brain once per coin per day (`brain.scan`); at 4 or more it is WATCH; anything
  less is LOW.
- **A design rule, never a test.** The score was built from reviews #5 to #7 and has never been tested as a signal (LOCK section 7).
- **What it does now.** Since the lock, 9 of 11 brain decisions were attention-HIGH wakes on the same four lab coins (ADA, LTC, XRP
  and BCH), all PASS, edge 0.
- **The decision.** `OD-PLAYBOOK-ATTENTION` (due 31 Oct) asks whether the score stays. Claude's recommendation (a) is to keep the
  weights and let the credit study judge them.

**The question in plain words:** in the window, do the lab coins the score marks HIGH do any better over the next five days than
the lab coins it does not mark? This review measures. It decides nothing, and its one look comes after `OD-PLAYBOOK-ATTENTION` is
decided, so it cannot inform that decision and is not evidence for it.

## The tier that decides
- **The lab 10 (`src.research.reads.COINS`), the only coins the attention board scores (decides).**
- **The object** is a lab coin on a UTC day on which the wake machinery ran: `brain_queue` holds at least one row of any kind that
  day. A day without one (the service down) is left out and counted.
- **HIGH:** the coin has a `brain_queue` row that day whose trigger includes `attention_high`.
- **Not HIGH:** the other lab coins that day. WATCH and LOW cannot be told apart from the record (see Data).
- **Event count:** market days, the UTC day. A day's value is defined in the test.

## The test
- **Per coin-day:**
  - p0 = the coin's daily close at 00:00 UTC that day (universe `d1`; the candle that opened the day before);
  - p5 = its daily close at 00:00 UTC five days later;
  - excess = (p5 / p0 - 1) minus the universe median move between the same two closes: `brain.market_median_move(t0, 5)` with
    t0 = 00:00 UTC of the day before, because that function starts from the close of the candle that opens at t0. It needs at
    least 20 coins; otherwise the excess is left empty.
- **Day value:** the mean excess of HIGH coins minus the mean excess of not-HIGH coins, on days with both.
- **z:** five-day horizons on consecutive days overlap, so z comes from a moving-block bootstrap over days: blocks of 5 days,
  10,000 draws, seed 35. z = mean / the standard deviation of the bootstrap means.
- **Reported beside, not judged:**
  - each coin's own HIGH-minus-not-HIGH difference. HIGH falls on the same few coins most days, so the coin and the label are
    hard to separate;
  - the HIGH coin-days the brain decided against those it did not reach.

**Data, and the recorder gap.**
- HIGH is recorded in `brain_queue` (82 attention-HIGH wakes since 4 Oct; 3 to 5 a day since the lock). Candles are recorded.
- The score's value and its WATCH and LOW levels are **never stored**: the board is computed on the fly every 15 minutes and held
  in memory. A calibration score by score (does a 7 do better than a 5?) **needs a recorder: Madhav's decision (`OD-SHADOW-LANE`)**.
  It is not in this review.
- If a decision in the window stops attention-HIGH being queued (`OD-PLAYBOOK-ATTENTION` or `OD-READS-WAKES`), the HIGH label stops
  being recorded that day. The population ends there, and the rest of the window **needs a recorder: Madhav's decision
  (`OD-SHADOW-LANE`)**.
- If the weights change in the window, the days before and after the change are reported separately. The verdict uses the days
  before, because the score as it stood at the push is the rule under test.

**Code version:** every function named here is used as it stands at origin/jarvis-4 commit 448cb21 (this file's parent commit).

**Forward window and looks.**
- Window: coin-days from 2026-10-21 to 2026-12-09, so that the five-day close exists by the 2026-12-14 close.
- Looks: **one**, at `CHECKPOINT-60`, run after the 2026-12-15 00:05 UTC daily close.
- Counting days first is not a look; computing any excess is. If the count is under the minimum, nothing else is computed; only
  Madhav can extend the window, and the one look moves with it.
- Cells: 1, in the family "attention and zone entries" (reviews #5 to #7, R28).

**Holdout.**
- The zones board shows today's levels; nothing shows their later results. That display is not a look.
- Any computation of this review's difference before `CHECKPOINT-60`, including for the 31 Oct decision, is a look, and the results
  file names it.

**Lake header.**
- The results file opens with `format_header(lake_header(D, until=2026-12-15 00:00 UTC))` over the lab 10, with D their universe
  daily candles in the window. If the weekly lake job has not reached the window's end, `until` is the lake's last complete day,
  and the header says so.
- Directly under it comes the live-feed line: the daily candles expected and present per coin, the days left out because the wake
  machinery did not run, and the days with fewer than 20 coins in the market median.
- A result without both is a draft (RESEARCH_RULES section 4).

## Pass marks (frozen)
- **INSUFFICIENT:** fewer than 10 days with both HIGH and not-HIGH coins.
- **HIGH_AHEAD:** the mean day value is above 0 with z of 2.0 or more.
- **HIGH_BEHIND:** the mean day value is below 0 with z of -2.0 or less.
- **NO_INFORMATION:** everything else.

## What each outcome changes (decided now)
Nothing changes by itself, and nothing here is for the 31 Oct decision. Each line is a proposal to Madhav after the window, in the
order he sets (LOCK section 9).
- **HIGH_AHEAD:** propose pre-registering the attention trigger table (`PW-ATTENTION-TABLE`, R28) on the lake, with this as its
  forward evidence.
- **HIGH_BEHIND:** propose that attention-HIGH stops waking the brain, if it still does. Madhav decides.
- **NO_INFORMATION or INSUFFICIENT:** reported as evidence for the credit study (`OD-PLAYBOOK-ATTENTION`, option (a)); nothing else.

## Not in this review
- The phone note on zone entries.
- Zone entries as trades (review #21; `ZONE_TOUCH` is "won't take again").
- Madhav's setups (the reads) as signals of their own.
- Coins outside the lab 10.
- The score's separate parts.
