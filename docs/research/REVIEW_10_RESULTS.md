# Review #10: stops and exits at zones (results)

Pre-registration `REVIEW_10.md` (ea32eaf); code fce9e0d; run 2026-10-03 on the laptop. Entries: 466 (2018-23, 145 market events)
and 341 (2024-Jul 2026, 77) support-zone entries with the market allowed. Net of NDAX costs, per trade.
Output: `~/ananta_runs/zones/review10_results.json`.

| Exit | 2018-23 mean (median) | win | stopped | days | 2024-26 mean (median) |
|---|---|---|---|---|---|
| X1 time, 20 days | **+5.8%** (+0.3%) | 51% | — | 20 | +0.3% (−3.3%) |
| X2 zone stop + target at the next zone | 0.0% (+1.2%) | **64%** | 21% | 5.6 | −1.3% (+0.5%) |
| X3 2-ATR stop | +5.3% (−1.7%) | 46% | 40% | 15 | −0.7% (−8.6%) |
| X4 2% stop | +1.2% (−2.9%) | 12% | 88% | 4.5 | −1.2% (−3.0%) |

X2 vs X1: −6.2 points (z −3.4); vs X3: −6.1 (z −3.6); vs X4: −1.0 (z −0.8). **Status: FAIL.**

## What it says
1. **Selling at the next zone cuts the winners.** Zones are close together, so the next one is near: the target was hit 77% of the
   time after about 5 days. It wins often (64%) but small, and the few big moves that make the average are sold early.
2. **The gains live in a few big moves.** Every exit has a median near or below zero and a positive mean: most trades go nowhere,
   a few run far. Exits that let those run (time, wide stops) keep the average; tight stops (2%) are stopped out 88% of the time.
3. Exploratory, decided after seeing this (not a test): the zone stop **without** a target, held up to 60 days, gave +18.1% in 2018-23
   and +3.2% since 2024, close to simply holding 60 days (+20.8% / +4.5%). The zone stop rarely saved much; holding through the
   noise did the work. This matches T3 and your own trades (+56% to +94% by holding with a stop under the structure).

## What changes
- No zone target goes into any book. The playbook's plan says: the stop goes beyond the zone (where the idea is wrong); the next
  zone above is where to **review**, not where to sell.
- Next test (new, counted): exits that let winners run, e.g. a trailing stop under each newly held zone, against holding with T3's rule.
