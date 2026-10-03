# Zones research program (and pre-registration of review #6)

Written 2026-10-03, before any zone code or result. Madhav: "it's always a zone, and once we enter the zone we keep track and start
our lookout process to decide on next moves." Every earlier study used points (a swing low, a distance from an average); this
program measures zones and then redoes those studies with zones.

## 1. What a zone is
A zone is a **price band** where the market has reacted before or where many traders watch. Point in time: built only from daily
bars that closed before the day it is used. Five kinds:

| Kind | Band | Source |
|---|---|---|
| SWING | daily swing lows/highs (5 bars each side) from the last 3 years, grouped when within 3% of each other; band = lowest to highest member, at least 0.5 daily ATR wide | casebook, H11, H13 |
| EXTREME | the 52-week low or high, ± 0.5 daily ATR | Madhav C1, Raunak |
| AVERAGE | the 50-day and the 200-day average, ± 0.5 daily ATR (a moving zone) | H11, V01 |
| BASE | the floor and the top of a quiet base (review #5 definition), ± 0.25 daily ATR | Madhav C3, H10 |
| ROUND | (later) round numbers | not in review #6 |

Overlapping zones of different kinds merge into one **confluence** zone that keeps the list of kinds.

## 2. Zone strength (fixed before looking; not fitted)
For a SWING zone, from the history before the day:
- **touches**: days whose low (for support) entered the band;
- **held**: touches followed by a rise of at least 1.5 daily ATR above the band before a daily close more than 0.5 ATR below it;
- **flips**: times it acted as resistance before and as support later (or the reverse);
- **age** (days since first touch) and **recency** (days since last touch).
Strength tier: **NEW** (0 held touches), **TESTED** (1 held), **STRONG** (2 or more held). Confluence count = number of kinds in the zone.

## 3. Zone states (the lookout)
Per coin and zone, at each daily close: FAR (more than 2 ATR away) → APPROACHING (within 2 ATR) → INSIDE (the day traded in the band)
→ HELD (rose 1.5 ATR above the band) or BROKEN (closed 0.5 ATR beyond it) → FLIPPED (a broken support later acts as resistance).
INSIDE starts the lookout; HELD / BROKEN end it. Live, the lookout is where Ananta spends its attention (chain, your setups, news check).

## 4. Review #6: do zones hold, and does strength matter?
- **Event:** the first daily bar of an approach from above whose low enters a support zone (after at least 3 days above it).
  Events of the same coin within 5 days are one; events of different coins within 3 days form one market event.
- **Outcome:** HELD or BROKEN, whichever comes first within 20 days (neither = OPEN, reported, excluded from the rates);
  plus the 10-day return from the next open, net of NDAX costs.
- **Random baseline:** for each event, 20 pseudo-zones of the same width centred at random prices between 3% and 30% below the
  day's prior close, run through the same rules. The same coin and days, so the market is the same.
- **Groups compared:** SWING NEW / TESTED / STRONG; EXTREME; AVERAGE-50; AVERAGE-200; CONFLUENCE (2+ kinds).
- **Data:** lab-10 coins, daily bars from 5m. DISCOVERY before 2024-01-01; CONFIRM 2024-01-01 to 2026-08-01; holdout not loaded.
- **Pass rule:** a group passes if, in DISCOVERY, its held rate beats the random baseline by at least 8 percentage points with a
  z-score of at least 2 over market events, and in CONFIRM by more than 0. **STRONG must beat NEW** for strength to count.
- Every group is reported, pass or fail. Changes to thresholds are new, counted variants.

### Amendment 1 (2026-10-03, before any run on real data): the random baseline
A check on synthetic random walks (where no zone can have an edge) showed the baseline above was not neutral: random-walk
"zones" scored up to −14 points against it, because the pseudo-zones were entered later and under different conditions.
Replaced with: **RANDOM bands** of the same widths as the real zones, at random prices within ±35% of the price, refreshed with
the zone map and run through the **identical** event rule (approach from above, 3 closes above, first entry). Because band width
changes how easily a band holds, each event is compared with RANDOM bands of the **same width in ATR** (bins: under 0.75,
0.75-1.5, 1.5-3, 3+). z is over market events (each one's held share minus its width-matched random rate). Thresholds unchanged.
The random-walk check is kept as a test, and the real run happens only after it shows no edge for any group.

### Amendment 2 (2026-10-03, before any run on real data): correct for the measurement's own bias
The random-walk check (10 synthetic walks, `docs/research/zones_rw_calibration.json`) showed no group with a positive edge
(none would falsely pass), but a **negative** bias: on pure noise the zone groups scored 3 to 12 points below the random bands
(AVERAGE-200 −11.8, AVERAGE-50 −7.9, CONFLUENCE −5.7, SWING −3 to −5; BASE +5.7 on 33 events). A test that starts several
points behind would wrongly fail real zones. So each group's DISCOVERY edge is judged **after subtracting its random-walk edge**:
pass = corrected edge ≥ 8 points and corrected z ≥ 2 (corrected z = corrected edge / the real run's standard error).
CONFIRM: corrected edge > 0. Raw and corrected numbers are both reported. The calibration file is frozen.
A smaller noise check (3 walks) also showed that a small group can reach +20 points with z 2.07 by luck (EXTREME, 25 events).
With 8 groups compared, z ≥ 2 lets about one in six studies pass something by chance. So the DISCOVERY bar becomes
**at least 30 market events and corrected z ≥ 2.5** (about a 5% chance of any false pass across the 8 groups); 8 points unchanged.

## 5. Studies to redo with zones (after review #6, in this order)
| # | Earlier study | Zone question |
|---|---|---|
| 1 | Review #5 your setups (M1-M3) | Do the reads work better when they fire at a STRONG or CONFLUENCE zone? |
| 2 | Explorer setups E1-E5, hunter | Entries inside a zone vs outside (hunter found "no support zone in the tape") |
| 3 | H06 dip in an uptrend | At the 50-day zone vs anywhere |
| 4 | H11 pullback, H13 false break, H12 first pullback | Pullback into a zone; a break below a zone that closes back inside (reclaim) |
| 5 | H03-H05 breakout systems | Breakouts through a STRONG resistance zone vs weak ones; retest of the flipped zone |
| 6 | Stops (H14, SD6, exit studies) | Stop beyond the zone vs fixed % vs ATR from the price |
| 7 | Entry v2, multi-timeframe v1, green runs, candidates v3/v4 | Same rules, split by zone state at entry |
| 8 | Intraday atlas | Zone state as context for every intraday cell |
| 9 | Reconstruction (HL 62 events, review #2 traders) | Were other traders' entries at zones? |
| 10 | T3 portfolio exits | Exit at a zone break vs at the average |

## 6. Review #7: the lookout (pre-registration, written 2026-10-03 after review #6 and before any lookout code or run)
Question: once price has come down into a support zone, which **reactions**, visible at the close of the entry day, make HELD more
likely than BROKEN? Same zone engine, data, splits, outcome rule (HELD / BROKEN within 20 days) and cost as review #6.

- **Event:** the first entry from above into any support zone (3 closes above, low enters the band). One event per coin per 5 days
  (the zone with the most kinds is the one judged). Events already BROKEN at the entry day's close are kept and count as BROKEN.
- **Reactions** (all measured at the entry day's close, from earlier bars only):

| ID | Reaction | Rule |
|---|---|---|
| F1 | Rejection | the close is in the upper half of the day's range (a long lower wick) |
| F2 | Closed back above | the close is above the band's top (it only tested the zone) |
| F3 | Volume | the day's volume ≥ 1.5× its 20-day average |
| F4 | Momentum divergence | the close is lower than 10 days ago but RSI(14) is higher than 10 days ago |
| F5 | Stronger than BTC | the coin's 30-day return beats BTC's |
| F6 | Market allowed | BTC's close above its 50-day average (V02) |
| F7 | Good zone kind | the zone is a 200-day average, a confluence or a new swing zone (review #6 passes) |

- **Measure:** held rate with the reaction minus held rate without it, per market event (events of different coins within 3 days),
  z over market events. **Pass:** DISCOVERY difference ≥ 8 points, z ≥ 2.5 (7 reactions tested), at least 30 market events with the
  reaction; CONFIRM difference > 0. Also reported: the 10-day net return with and without.
- **Lookout score:** the number of reactions present among those that pass DISCOVERY; its held rate by score is reported in CONFIRM.
- Random-walk check before the real run: no reaction may pass on synthetic walks.

## 7. After that

Inside a zone, which reactions predict HELD vs BROKEN: rejection wick, volume (H09), RSI divergence, relative strength vs BTC (H08),
market regime (V02), news verdict. This is where most teacher ideas get their real test.
