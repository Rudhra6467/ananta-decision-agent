# Review #11: two teacher ideas redone with zones (pre-registration)

Written 2026-10-03, before any code or run. Both ideas are judged on weeks (20-day hold), where zones act (reviews #6-#10).

- **A1, H06 / H11 (dip in an uptrend, as a zone):** the market is allowed (BTC above its 50-day average), the coin's previous close is
  above its 200-day average, and the day's low comes down from above (3 closes above) into the coin's 50-day-average zone
  (the average ± 0.5 daily range). Buy at the next open.
- **B1, breakouts through a zone (H03-H05 idea, as a zone):** the market is allowed, and the coin closes above a zone that sat above
  the previous close (first close above it: the 3 closes before were under its top). Buy at the next open.
- **B2:** B1 where the zone is a swing zone that turned price down at least twice before (as resistance: 2+ swing highs in it).
- **B3, H09 (volume on breakouts, the place the claim applies):** B1 on a day with volume ≥ 1.5× its 20-day average.
- **Data and rules:** zones from `src/research/zones.py` (built from earlier bars only), lab-10 coins, NDAX costs, DISCOVERY before
  2024-01-01, CONFIRM to 2026-08-01, holdout not loaded. One event per coin per 5 days; events of different coins within 3 days are one
  market event.
- **Measure:** 20-day net return from the next open, minus the same coin's average 20-day return over all days **with the same
  conditions** in the same split (A: market allowed and above the 200-day; B: market allowed) = excess.
- **Pass (4 variants):** DISCOVERY ≥ 30 market events, mean excess > 0, z ≥ 2.5 over market events; CONFIRM mean excess > 0.
