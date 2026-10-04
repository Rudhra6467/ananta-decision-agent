# Review #15 results: the held-up ideas on the full crypto universe (2026-10-04)

Pre-registration: `REVIEW_15.md`. Data: the lake, 120 coins by universe rule v1 (90 still listed, 30 delisted), 257M one-minute
candles, 0 download errors, quality 92 A / 27 B / 1 C. Output: `~/ananta_lake/reports/review15_results.json`.

## Runs counted
1. Run 1: found two token redenominations Binance did not back-adjust: COCOS (x1220 on 2021-01-24) and BNX (/100 on 2023-02-23).
   COCOS alone pushed the ALL-tier baselines to nonsense (H07 baseline +17%, M3a excess -140%). Kept as
   `review15_results_run1_unfixed.json`.
2. Run 2 (the result): only the post-swap history of those two coins (`BREAKS` in `src/lake/research.py`). Verdicts did not change.
   Other big daily moves were checked and are real (DOGE Jan 2021, LUNA/ANC, OM, PNUT listing, UNFI, BTCST, BAKE).

## LAB10 data check: passes
H07 reproduces review #14 (discovery 25 events, +4.2% excess, z 2.27 vs 25 / +3.9% / 2.3; confirm 16 / +5.6% / 2.8, identical).
T3 passes as in review #4 (confirm +13.1% vs buy-and-hold -21.6%, matching review #12).

| Idea | LAB10 | TOP30 | ALL (120) |
|---|---|---|---|
| T3 trend portfolio | PASS | **PASS** (confirm +19.0%, worst fall 43.9% vs B&H -23.7% / 76.0%) | FAIL: confirm -13.8% (B&H -65.8%); passes the fall and MAR checks |
| H07 short dip | INSUFFICIENT (25 events) | **PASS** (33 events, +6.0%, z 3.5; confirm +3.6%, z 3.2) | FAIL: discovery z 1.77 (48 events); confirm +4.8%, z 4.6 |
| H07-G (market allowed) | INSUFFICIENT | INSUFFICIENT | INSUFFICIENT |
| M1a capitulation | INSUFFICIENT | INSUFFICIENT | SUPPORTED, thin: 10 events, t 1.51 (bar 1.5); confirm 3 events |
| M2a higher-low retest | NOT SUPPORTED | NOT SUPPORTED | NOT SUPPORTED |
| M3a quiet base | NOT SUPPORTED | NOT SUPPORTED | NOT SUPPORTED |
| M2a-G retest, market allowed | INSUFFICIENT | NOT SUPPORTED | NOT SUPPORTED |

## Reading
- T3 and H07 hold on the 30 most-traded coins, not on the long tail. The pre-registration did not write down the
  "TOP30 yes, ALL no" case, so no promotion follows automatically; Madhav decides. Nothing was tuned.
- In 2024-26 the long tail lost two thirds holding; T3 cut that to -14% but did not make money there.
- M2a and M3a fail on every tier; M2a-G fails on the wider tiers. M1a's ALL pass sits right on the bar with 3 confirm events.
- Holdout (from 2026-08-01) not loaded.

## Open
- Decide what a TOP30-only pass earns (paper slot for the 30-coin tier, not live).
- Quality check should flag x10+ day moves as possible redenominations (it graded COCOS and BNX B).
- R2 copy waits for the bucket.
