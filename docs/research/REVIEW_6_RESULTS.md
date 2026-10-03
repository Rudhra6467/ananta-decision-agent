# Review #6: do zones hold? (results)

Pre-registration: `ZONES_PROGRAM.md` sections 1-4 plus Amendments 1-2, all committed before the run (6744e09).
Engine: `src/research/zones.py` (lookahead test, random-walk calibration). Run 2026-10-03 15:30 UTC on the laptop:
10 coins, daily bars from 5m, 6,567 zone entries. Holdout (Aug-Sep 2026) not loaded. Numbers: `zones_status.json`.

**Event:** price comes down from above (3 closes over the band) and enters a support band. **Held** = it then rises 1.5 daily
ranges above the band before a close 0.5 range below it (20 days). **Random bands:** same widths, random prices, same rule.

| Group | Status | 2018-2023: held vs random (market events) | Edge raw → corrected | z | 2024-Jul 2026 edge raw → corrected |
|---|---|---|---|---|---|
| Swing zone, never held before (NEW) | **PASS** | 58% vs 59% (177) | +4.0 → +8.6 | 2.5 | +10.0 → +14.6 |
| Swing zone, held once (TESTED) | FAIL | 63% vs 61% (144) | +4.3 → +7.5 | 2.1 | +5.8 → +9.0 |
| Swing zone, held twice+ (STRONG) | FAIL | 60% vs 65% (240) | +2.8 → +5.9 | 2.3 | +13.7 → +16.8 |
| 52-week low (EXTREME) | FAIL | 69% vs 73% (65) | +1.5 → +5.5 | 1.0 | +13.5 → +17.5 |
| 50-day average | FAIL | 68% vs 73% (125) | −0.1 → +7.8 | 1.6 | −3.3 → +4.6 |
| **200-day average** | **PASS** | 75% vs 76% (101) | +2.5 → +14.3 | 3.5 | +4.7 → +16.5 |
| **Confluence (2+ kinds overlap)** | **PASS** | 67% vs 71% (189) | +3.2 → +8.9 | 3.1 | +3.3 → +9.0 |
| Base floor | FAIL | 60% vs 66% (45) | −7.4 → −13.1 | −1.9 | −1.8 → −7.5 |

(The "held vs random" columns pool all entries; the edge compares each market event with random bands of the same width, so
the two can point different ways. Wider bands hold more easily: random bands held 57% under 0.75 ATR wide and 88% over 3 ATR.)

## What it says, plainly
1. **Zones are real but modest.** Price coming into a zone holds a few points more often than at a random band of the same width
   (raw +2 to +4 points before 2024, +3 to +14 since). Three groups pass the pre-registered bar: the **200-day average**,
   **confluence** (two or more kinds overlapping) and new swing zones.
2. **The passes lean on the bias correction.** On pure noise the method scores zones 3-12 points *below* random; the passes are
   measured against that. Real markets are not random walks, so treat the corrected size as approximate; the direction
   (positive in both periods for six of eight groups) is the steadier finding.
3. **"Strong" (held twice before) did not beat "new"** by a meaningful amount (60% vs 58% held in 2018-23). How many times a level
   held is not, by itself, what makes a zone work. Confluence and the 200-day mattered more.
4. **Entering a zone is not a trade.** The 10-day return after entering a zone was about zero after costs, no better than random
   bands (+1.2% in 2018-23). Holding more often does not pay by itself: what happens *inside* the zone decides it.
   That is exactly Madhav's point: the zone starts the lookout; the lookout decides the move (review #7).
5. **Base floors failed** (held less often than random), the same way your quiet-base read did in review #5 before 2024.

## What changes
- The live zone map shows every zone, marks the three passing groups as "zones history supports", and records each entry
  and how it ended (live evidence for review #7). No zone places a trade.
- Next: review #7, the lookout: inside a zone, which reactions (rejection wick, volume, divergence, relative strength,
  regime, news) separate HELD from BROKEN; then the studies in section 5 of the program, redone with zones.
