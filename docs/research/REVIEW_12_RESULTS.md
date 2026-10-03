# Review #12: T3's exit vs trailing stops (results)

Pre-registration `REVIEW_12.md` (9c97101); code 5a60a41; run 2026-10-03 on the laptop (review #4 simulator, NDAX costs, weekly
rebalance). Output: `~/ananta_runs/t3_exits/review12_results.json`.

| Exit | 2018-23 return | max DD | MAR | 2024-Jul 2026 return | max DD | MAR | Status |
|---|---|---|---|---|---|---|---|
| **T3** (close under the 20-day, control) | +3,558% | 49.7% | 1.57 | **+13.1%** | 41.0% | **0.12** | stays |
| T3Z zone trail | +10,258% | 52.3% | 2.11 | −25.7% | 57.2% | −0.19 | FAIL |
| T3A 3-ATR chandelier (H15) | +10,156% | 50.9% | 2.17 | −22.3% | 60.8% | −0.15 | FAIL |
| T3W close under the 50-day | +6,827% | 52.2% | 1.87 | −6.8% | 50.3% | −0.05 | FAIL |

Crisis windows (review #4): all similar except Oct 2025: T3 −4.4%, T3Z −17.9%, T3A −19.4%, T3W −10.2%.

## What it says
1. **Looser exits win big in trending years and lose in choppy ones.** 2018-23 had huge bull runs: holding through dips (zone trail,
   ATR trail) tripled T3's result. 2024-26 was choppy: the same looseness turned +13% into −22% to −26%.
2. **T3's tight 20-day exit is the one that survives both.** It gives up the giant runs but protects when trends fail. T3 stays as is.
3. This sharpens review #10: the gains come from a few big moves, **but** you only know afterwards whether the market was trending.
   An exit that bets on big trends is a bet on the regime. A regime-aware exit (loose only in strong trends) is a new, counted idea.
4. H15 (trailing stops 3x ATR, Rayner): not supported on our coins in 2024-26.
