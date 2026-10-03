# Review #13: the remaining teacher ideas (pre-registration)

Written 2026-10-03, before any code or run. The last untested ideas from Rayner and Trade With Trend that can be tested on daily
data. Same framework as review #11 (zones from earlier bars only, lab-10 coins, NDAX costs, next-open entries, DISCOVERY before
2024-01-01, CONFIRM to 2026-08-01, holdout not loaded, one event per coin per 5 days, market events = coins within 3 days).

**Entry ideas** (measure: 20-day net return minus the same coin's average 20-day return on days with the same conditions):
- **H07 RSI dip in an uptrend:** the coin's close above its 200-day average and its RSI(10) under 30. Same condition for the baseline:
  above the 200-day. Also reported (not judged): its own exit (RSI(10) back above 40 or 10 days).
- **H12 first pullback after a breakout:** market allowed; a close above the previous 20-day high; then, within 15 days, the first day
  whose low touches the 20-day average while the close stays above it; buy when a later day (within 5) trades above that day's high,
  at that high (or the open if it opens above). Baseline: market allowed.
- **H13 false break of a support zone:** market allowed; the day's low goes under a support zone (below the previous close) and the
  day closes back above the zone's bottom. 52-week-low zones excluded (the teacher says those are only short bounces). Baseline:
  market allowed.
- Pass (each): DISCOVERY ≥ 30 market events, mean excess > 0, z ≥ 2.5; CONFIRM mean excess > 0.

**Market idea:**
- **H16 breadth:** on days the market is allowed (BTC above its 50-day), is the next 20 days better for our coins when breadth is
  strong (at least 7 of the 10 coins above their 50-day and at least 5 above their 200-day) than when it is weak? One sample every 20
  days (no overlap); measure = average 20-day net return of all available coins from that day. Pass: DISCOVERY difference > 0 with
  z ≥ 2.5 and at least 30 samples on each side... if fewer, INSUFFICIENT; CONFIRM difference > 0.

**Book idea:**
- **P03 book stop on T3:** T3 as in review #4, plus: when the book's equity falls 8% under its highest point since it last left cash,
  sell everything and stay in cash for 5 days, then follow T3 again. Pass: MAR above T3's in both periods.

**Not tested here, with reasons:** H10 (tight bases) was tested as your quiet-base read (reviews #5, #8) and as base floors (review #6):
not supported. H17 (staged entries) needs entries worth staging; breakouts were not reliable (review #11), so it waits.
