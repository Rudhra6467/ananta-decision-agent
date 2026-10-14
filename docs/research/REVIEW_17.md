# Repair-shop review #17 (pre-registration): coin choice filters on T3 and H07

Written 2026-10-05, before any run (audit v1, re-test queue item 3; Madhav 2026-10-05 "yes, lets continue").
Question: do H08 (relative strength vs Bitcoin) or H16 (market breadth) improve the two ideas that passed review #15 on the
top 30 coins: T3 (now with T3-B sizing, review #20) and H07 (the short dip trade)?

## Definitions (fixed now; earlier bars only)
- **RS on (H08):** the coin's close divided by Bitcoin's close that day is above its own 50-day average (EMA of that ratio).
  Bitcoin always counts as RS on.
- **Breadth strong (H16):** among the tier's coins with 200 days of history, at least 70% close above their 50-day EMA and at
  least 50% above their 200-day average (review #13's thresholds). With fewer than 8 such coins, breadth is undefined and the
  filter does not block (the variant behaves like its control).

## Variants (4, all counted; nothing added after the run)
- **T3B-RS:** T3-B, but a coin is held only when T3 holds it AND it is RS on.
- **T3B-BR:** T3-B, but coins are held only while breadth is strong (on top of the Bitcoin gate).
- **H07-RS:** H07 signals only on days the coin is RS on.
- **H07-BR:** H07 signals only on days breadth is strong.
Controls: T3-B and plain H07, run in the same code.

## Data, splits, tiers
Lake daily candles (review #15 loader). Discovery before 2024-01-01; confirm 2024-01-01 to 2026-07-31; holdout not loaded.
NDAX costs (0.20% + half spread; 0.40% outside the lab 10). **Judged on TOP30** (where both controls pass). LAB10 and ALL
are reported, not judged.

## Pass rules
- T3 filters: pass T3's own rules in both periods (positive return, smaller worst fall than buy-and-hold, better MAR than
  buy-and-hold) AND a higher MAR than T3-B in both periods.
- H07 filters: H07's own bar (discovery 30+ market events, mean excess over ordinary uptrend days > 0 with z >= 2.5; confirm
  excess > 0) AND a higher mean excess than plain H07 in both periods. The baseline is plain H07's (ordinary uptrend days,
  unfiltered), so a filter cannot win by changing the yardstick. Fewer than 30 discovery events: INSUFFICIENT.

## What follows
A passing filter becomes a candidate rule change for the paper books (Madhav's sentence needed). A failing filter stays an
observation in the decision chain, as now.
