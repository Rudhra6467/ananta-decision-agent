# Review #20 results: a lower-turnover T3 (2026-10-05)

Pre-registration: `REVIEW_20.md` (dc6dfa4). Code: `src/research/t3_turnover.py` (the control reproduces review #4's simulator
exactly on LAB10: same final equity 42.0952x, same costs). Output: `~/ananta_lake/reports/review20_results.json`.
Columns: total return % / worst fall % / MAR / costs paid (sum of each day's cost as % of that day's equity), per period.

## LAB10 (the coins live would trade)
| | 2018-23 | Jan 2024 - Jul 2026 | Verdict |
|---|---|---|---|
| T3 (control) | +3,555% / 49.7% / 1.57 / 91.3 | +13.1% / 41.0% / 0.12 / 41.0 | control |
| T3-N no reset | +8,129% / 46.9% / 2.19 / 79.4 | +3.9% / 42.0% / 0.04 / 38.7 | FAIL (2024-26 MAR 0.04 < 90% of T3) |
| **T3-B band 0.5x-1.5x** | +6,162% / 47.2% / 2.00 / 82.5 | **+15.1% / 40.7% / 0.14 / 39.1** | **PASS** |
| T3-M monthly reset | +6,014% / 48.5% / 1.93 / 83.7 | +13.3% / 41.9% / 0.12 / 39.3 | PASS |
| Buy-and-hold | +2,575% / 87.8% / 0.79 | -21.6% / 71.2% / -0.13 | |

## TOP30
| | 2018-23 | Jan 2024 - Jul 2026 | Verdict |
|---|---|---|---|
| T3 (control) | +3,684% / 54.8% / 1.45 / 104.4 | +19.0% / 43.9% / 0.16 / 46.6 | control |
| T3-N | +8,072% / 53.2% / 1.93 / 90.0 | +22.6% / 45.6% / 0.18 / 43.0 | PASS |
| **T3-B** | +7,163% / 53.2% / 1.86 / 93.5 | **+26.1% / 44.3% / 0.21 / 43.8** | **PASS** |
| T3-M | +7,864% / 54.5% / 1.87 / 94.3 | +23.3% / 45.2% / 0.19 / 43.8 | PASS |
| Buy-and-hold | +5,454% / 85.4% / 1.06 | -23.7% / 76.0% / -0.13 | |

## Double-cost stress: nothing is ROBUST
At double costs every version, T3 included, loses money in 2024-26 on both tiers (LAB10: T3 -25.0%, T3-B -22.3%;
TOP30: T3 -25.4%, T3-B -20.6%; buy-and-hold -23.7% / -27.4%).

## Reading
1. **T3-B is the candidate** by the pre-registered tie rule (no variant is robust, so lowest costs among passers on LAB10):
   it passes on both tiers and has the best 2024-26 MAR on both. It trades about a third as often as T3 (2,340 vs 6,783 coin
   re-sizings on LAB10).
2. **The savings are small.** Costs fell only ~5-15% although trades fell by two thirds: the re-sizing trades are small, and
   most of the cost is the in-and-out of the 20-day exit itself. Review #4's guess (costs come mostly from weekly re-sizing) was
   wrong; this review corrects it.
3. **The cost warning stands.** No version survives double costs in 2024-26. T3 needs NDAX's 0.20% or cheaper; at roughly twice
   that (e.g. a 0.40%+ venue, or wide spreads) it loses money in a choppy market.
4. Nothing was tuned; three variants counted. Replacing the paper/live T3 rule with T3-B needs Madhav's sentence.

## Open
- Madhav: switch the paper and live T3 to T3-B (yes / no).
- The real cost driver is the 20-day exit's churn; a test of a buffered exit (e.g. close under the 20-day by a margin) would be
  a new counted review, after #16-#19.
