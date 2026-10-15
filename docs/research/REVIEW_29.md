# Review #29 (pre-registration): H07 on a point-in-time tier A, both dial states

**Status: APPROVED and frozen.** Written 2026-10-15 before any code or data for it was touched; approved by Madhav in chat on
2026-10-15 at 06:33 Toronto ("1. approved"). Nothing below changes from here; any later change is a new review. Not yet run
when frozen: until REVIEW_29_RESULTS.md exists there is no result.

## Why
Review #26 found one cell of 36 with an edge: H07 (the short dip) on tier A while the exposure dial is CLOSED (discovery 92
trades, 48 market days, +9.3% over random, z 5.0; confirm 83 trades, 46 days, +6.3%, z 4.9; expected value +5.1% a trade).
Two gaps remain (research audit, Oct 14): the 120 lake coins were chosen by their last 24 months, so coins that were big and
later died are missing, and dip buying is exactly where dead coins hurt most; and the costs were tier floors, not the measured
spreads the live books pay. Madhav's directive (Oct 14): register H07 tests for both dial states before running them.

## The test (one rule, two cells, nothing tuned)
- **Rule, exactly as live** (`watch_engine._fires`, review #27): signal when RSI(10) closes under 30 while the close is above
  the 200-day average; entry at the next day's open; exit at the next open after RSI(10) closes over 40, or after 10 days; no
  stop; one trade at a time per coin. RSI 10/30/40, the 200-day and 10 days are fixed.
- **Point-in-time tier A:** on each signal day, coins whose median daily traded value over the previous 30 days is at least
  $20M (Universe Rule v2), taken from EVERY eligible Binance spot USDT pair of rule v1 (no stablecoins, leveraged or wrapped
  tokens), not just the lake's 120. Coins that died or were delisted stay in for the days they traded.
- **Coverage check first (stop rule):** before any result is computed, the coins with clean daily candles must cover at least
  99% of tier A's traded value in every month (`reports/monthly_values.json`). A missing coin is downloaded and quality-checked
  as in review #22 (token-swap check included). If coverage is short after that, the run stops and only the coverage is reported.
- **Market state:** the exposure dial v1 at the signal day (review #25: Bitcoin closed above its 50-day and 200-day averages =
  OPEN, else CLOSED).
- **Costs:** each side, the coin's live Universe Rule v2 cost (`registry.cost`: the fee where it can be bought plus three times
  its measured Binance half-spread, never under the tier floor). A coin that no longer trades pays twice its tier floor. A
  stress run doubles every cost.
- **Baseline (random twins):** random days of the same point-in-time tier-A coins in the same dial state, held 10 days, same
  costs (as review #26). Excess = trade net minus the baseline mean of its cell. Market days: trades exiting on the same day
  count once. Secondary, reported only: each trade paired with a random tier-A coin entered the same day under the same exit.
- **Periods:** DISCOVERY 2018-01-01 to 2023-12-31; CONFIRM 2024-01-01 to 2026-07-31. **HOLDOUT 2026-08-01 to 2026-12-14
  stays sealed:** not loaded by this run; opened once, after the 60-day evidence window and only with Madhav's OK, with the
  criteria below unchanged.

## Pass marks (frozen)
**Primary cell: H07, tier A, dial CLOSED.**
- PASS when all hold: DISCOVERY has at least 30 market days; mean excess > 0 with z >= 2.5 (the stricter bar of review #22,
  because this cell was picked from 36); mean net > 0. CONFIRM: mean excess > 0 with z >= 2.0 and mean net > 0. The 2x-cost
  stress keeps mean net > 0 in both periods. Dropping the two largest bursts (trades within 10 days of each other) keeps the
  excess > 0 in both periods.
- WEAKENED: both periods keep mean excess > 0 and mean net > 0, but a z, stress or burst mark fails.
- FAIL: mean excess or mean net is 0 or below in either period.
- INSUFFICIENT: under 30 market days in DISCOVERY.

**Secondary cell: H07, tier A, dial OPEN** (where every live H07 trade so far was taken). Judged by the same marks; reported
beside the primary. A pass here makes it a CANDIDATE only: it needs 10 independent live market days before the brain may
treat it as an edge.

## What each outcome changes (decided now)
- PASS: the closed-dial value in `ev.py` becomes the new pooled excess shrunk by n/(n+50); the H07 knowledge line and status
  card cite #29; the $500 book's edge sleeve stays as built.
- WEAKENED: the same, with the smaller value, and the knowledge line says "weaker on a point-in-time list".
- FAIL: the cell's value goes to 0 (no measured edge anywhere); with the dial closed the brain admits nothing new; the $500
  book's edge sleeve stays empty. Madhav decides whether H07's paper books keep running as evidence.
- INSUFFICIENT: nothing changes; reported as such.
- The holdout, when opened, can confirm or weaken the verdict; it is never used to tune.

## Not in this review
No other rule, no other tier, no parameter search, no stop variants (review #27 settled the stop).
