# Repair-shop review #8: your setups again, with zones and the market gate (pre-registration)

Written 2026-10-03, before any run. Review #5 found your three setups (M1 capitulation, M2 higher-low retest, M3a quiet base) catch
your buys but do not beat random days on their own. Reviews #6 and #7 then found what matters at a support: the market being allowed
(BTC above its 50-day average) and, less, the kind of zone (200-day average, overlapping zones, new swing zones).
Question: do your setups work when they fire **at a zone history supports** and/or **with the market allowed**?

- **Same as review #5:** reader (`src/research/reads.py`), daily bars, lab-10 coins, NDAX costs, entry at the next open, 30-day hold,
  excess over the coin's own drift, episodes (20 days), independent market events (10 days), DISCOVERY < 2024-01-01 <= CONFIRM < 2026-08-01,
  holdout not loaded. Pass rule unchanged: DISCOVERY >= 8 events, mean excess > 0, t >= 1.5; CONFIRM >= 3 events, mean excess > 0.
- **Filters** (applied to each day's fire before episodes are formed):
  - **Z (zone):** on the fire day, the day's range touches a support zone of a kind review #6 passed (AVERAGE-200, CONFLUENCE, SWING-NEW),
    built only from bars before that day (`src/research/zones.py`).
  - **G (gate):** BTC's close is above its 50-day average (V02) on the fire day.
- **Variants (9, all reported):** M1a-Z, M1a-G, M1a-ZG, M2a-Z, M2a-G, M2a-ZG, M3a-Z, M3a-G, M3a-ZG.
- Expectation written down now: M1 (capitulation) rarely happens with BTC above its 50-day, so M1a-G and M1a-ZG may be INSUFFICIENT.
- Nine variants at t >= 1.5 means about one lucky pass is possible; a pass is a candidate for live recording, not a trade rule.
