# Repair-shop review #18 (pre-registration): stops and crash insurance

Written 2026-10-05, before any run (audit v1, re-test queue item 4; Madhav 2026-10-05 "yes lets continue").

## Part A: H14, structural vs tight stops, on H07 trades
H07 has no stop today. Same signals and exits as review #14 (RSI(10) back over 40, else 10 days), plus a stop checked on each
daily low (filled at the stop, or at the open if it opens under it):
- **H07-S1 structural (H14):** the lowest low of the 10 days up to the signal day, minus 1 daily ATR(14).
- **H07-S2 tight:** 3% under the entry price (the kind of stop that was shaken out in casebook C1/C3).
Measure: mean excess per trade over plain H07's baseline (ordinary uptrend days, review #14). Judged on TOP30.
- H14 is SUPPORTED if S1's mean excess beats S2's in both periods.
- A stop is worth adding to H07 only if it also passes H07's own bar (review #14) and beats plain H07 (no stop) in both periods.

## Part B: V03, a disaster stop on the trend portfolio
The live-rules draft uses a 25% disaster stop. Variant **T3B-D25**: T3-B, plus a coin whose daily close is 25% or more under
its entry price is sold at the next open and not bought again until T3 has turned it off and on again. The account-level 20%
shutdown is a policy (the kill switch), not tested here.
- Tiers: **ALL 120 judged** (the delisted crash coins - LUNA, FTT and the rest - are only there), TOP30 and LAB10 reported.
- Pass: in both periods a smaller worst fall than T3-B and a MAR at least 90% of T3-B's; plus the crisis windows of review #4
  (COVID 2020, May 2021, LUNA/3AC 2022, FTX 2022, Aug 2024, Oct 2025) reported for both, as the "insurance" view.

## Data and rules
Lake daily candles (review #15 loader); discovery before 2024-01-01, confirm 2024-01-01 to 2026-07-31; holdout not loaded;
NDAX costs. Three variants counted (S1, S2, D25). Nothing is tuned after the run.
