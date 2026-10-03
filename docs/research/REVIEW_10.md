# Review #10: stops and exits at zones (pre-registration)

Written 2026-10-03, before any code or run. Zones work over weeks (reviews #6-#9), so the exit should be judged on weeks-long holds.
Question: for a buy at a support zone with the market allowed, is a **stop beyond the zone and a target at the next zone** better than
a time exit, an ATR stop, or a tight fixed stop like the Explorer's?

- **Entries:** the review #7 events (first entry from above into a support zone, one per coin per 5 days) on days the market is
  allowed (BTC above its 50-day average, F6). Bought at the next day's open. NDAX costs both ways.
- **Exits, each applied to the same entries:**
  - **X1 TIME:** sell at the open 20 days later.
  - **X2 ZONE:** stop = a daily close below the zone's bottom minus 0.5 daily range (sell at the next open); target = the bottom of
    the next zone above the entry price (sell at that price when the day's high reaches it); otherwise sell at the open 40 days later.
  - **X3 ATR:** stop 2 daily ranges under the entry price (sold at the stop when touched); otherwise the open 20 days later.
  - **X4 TIGHT:** stop 2% under the entry price (sold at the stop when touched); otherwise the open 20 days later.
- **Measure:** net return per trade; X2 compared with each other exit on the same trades (paired), z over market events
  (entries of different coins within 3 days are one market event). Also the share stopped, average days held, worst trade.
- **Pass:** in DISCOVERY (before 2024-01-01) X2's mean net beats each of X1, X3 and X4 with z ≥ 2 over market events, and its mean
  net is above zero; in CONFIRM (2024 to July 2026) X2's mean net is above each of the others. All four exits reported either way.
- Holdout not loaded. Engine `src/research/zones.py` (`review10`).
