# Repair-shop review #19 (pre-registration): cheap new variables - buying pressure, funding, open interest

Written 2026-10-05, before any of the futures data was looked at (audit v1, re-test queue item 5; Madhav 2026-10-05: "complete
all the pending research tasks"). Data: taker buy volume is in the lake's spot candles; funding rates and open interest are
Binance USD-M futures files from Data Vision (src/lake/futures.py; funding from 2019-20, open interest from Sep 2020).

## Definitions (fixed now; earlier bars only; a day without the data = undefined = the filter does not block)
- **Buying pressure (U03):** taker buy share = taker buy volume / volume, per day. "High" = its 7-day average is above the
  median of the coin's previous 180 days.
- **Funding (U01):** the mean funding rate per UTC day. "Crowded long" = its 7-day average is above the 80th percentile of the
  coin's previous 365 days (at least 90 days of history, else undefined).
- **Leverage flushed (U02):** open interest (USD value at the day's last reading) fell over the last 5 days.

## Variants (5, all counted; nothing added after the run)
- **T3B-TB:** T3-B, a coin is held only while its buying pressure is high.
- **T3B-F:** T3-B, a coin is not held while it is crowded long.
- **H07-TB:** H07 signals only when buying pressure is high.
- **H07-F:** H07 signals only when the coin is not crowded long.
- **H07-OI:** H07 signals only when leverage was flushed (open interest fell over 5 days).
Controls: T3-B and plain H07 in the same code (review #17's code path).

## Tiers, splits, pass rules
Judged on TOP30 (open interest is pulled for TOP30 only); LAB10 and ALL reported where the data exist. Discovery before
2024-01-01, confirm 2024-01-01 to 2026-07-31, holdout not loaded. NDAX costs. Pass rules as review #17: a T3 filter must pass
T3's own rules and beat T3-B's MAR in both periods; an H07 filter must pass H07's bar (30+ discovery market events, excess > 0,
z >= 2.5; confirm > 0) and beat plain H07's excess in both periods, against plain H07's baseline. Because futures data start in
2019-20, the discovery period is shorter for U01/U02 (stated in the results, not a reason to loosen anything).

## What follows
A pass becomes a candidate rule change (Madhav's sentence). A fail keeps the variable as context for the agent (shown, not used
to decide). The futures data stay in the lake either way, for the agent and for later reviews.
