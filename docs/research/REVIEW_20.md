# Repair-shop review #20 (pre-registration): a lower-turnover T3

Written 2026-10-05, before any run. Why: review #4 found T3's 2024-26 profit is thin, fails with double fees, and that its
costs come mostly from re-sizing every coin back to equal shares (each Monday and on every single entry or exit). The live
rules draft (backlog J5) asks for this test before live. Madhav, 2026-10-05: "lets start".

## What stays the same
T3's signal, unchanged: hold a coin while its daily close is above its 20- and 50-day averages and Bitcoin is above its
50-day; decided at the UTC close, traded at the next open; target size = equity / number of available coins. Data: the lake
(review #15 loader, COCOS/BNX cuts). Costs: NDAX 0.20% a side plus half the spread (measured for the lab 10, 0.40% otherwise).
Splits: discovery before 2024-01-01, confirm 2024-01-01 to 2026-07-31; the holdout (from 2026-08-01) is not loaded.

## Variants (all counted; nothing added after the run)
- **T3** (control): today's rule. Weekly reset to equal shares, and every change re-sizes all held coins.
- **T3-N** no reset: an entry buys the new coin at its target size, an exit sells that coin; the others are not touched.
- **T3-B** band: T3-N, plus on Mondays a held coin is re-sized only if it has drifted outside 0.5x to 1.5x of its target.
- **T3-M** monthly: T3-N, plus a full reset to equal shares on the first Monday of each month only.

## Tiers
LAB10 (the coins live would trade on NDAX) and TOP30 (the 30-coin paper tier). Each judged separately.

## Pass rules (fixed now)
A variant passes on a tier when, in BOTH periods:
1. it passes T3's own rules (positive return; smaller worst fall than buy-and-hold; better MAR than buy-and-hold), and
2. it pays less in costs than T3, and
3. its MAR is at least 90% of T3's MAR in the same period (cheaper must not mean meaningfully worse).
Stress (reported, decides ties): every variant and T3 re-run at double costs; a variant that still passes rule 1 at double
costs in both periods is marked ROBUST.

## What follows
- A variant that passes on LAB10 (and ideally TOP30) becomes the candidate for the live T3, and replaces the paper rule only
  with Madhav's sentence. Several pass: the most ROBUST one, then the lowest costs.
- None pass: T3 stays as is; the live rules keep the cost warning.
