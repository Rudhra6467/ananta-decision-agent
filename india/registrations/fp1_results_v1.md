# FP1 results: Monthly factor portfolios for the long-term money: 12-month momentum, low volatility and the two combined, top decile of the 500 most traded stocks, rebalanced monthly, against the equal-weight universe and the Nifty 500, after costs (2000-2023)

Registered 2026-10-30T02:33:47+00:00 (spec `fp1_v1.json`, written before the run); family factor_monthly, k = 8, z = 2.73. Development 2000-2017, validation 2018-2023; nothing from 2024 on. HISTORICAL BACKTEST, paper only.

Monthly excess return of the portfolio over the benchmark, quarter means, t across quarters. Costs: delivery charges of the day and the half-spread by turnover rank on the weight that changes hands each month. The Nifty 500 is the price index (dividends of about 1.2-1.5% a year are not in it, which flatters the portfolio by that much against N500 but not against EW).

## In plain words

**The two best-known factor tilts show their known shape in Indian data, but neither passes the strict bar on monthly excess return: momentum earned more (clearly in 2018-23, barely in 2000-17) with the deepest crashes; low volatility earned the same as the universe with half the swings and a third of the drawdown. Nothing is a rule from this; the low-swing shape is the useful fact for the long-term money.**
- **Momentum (top 50 of 500 by 12-month return, monthly):** 16.1% a year in 2000-17 and 25.1% in 2018-23 after costs (turnover 31% a month, costs 1.7% a year), against 14.4% and 12.8% for the equal-weight universe and 20.4% (2003-17) and 12.5% for the Nifty 500. Monthly excess over the universe +0.23% (t +0.7) and +0.93% (t +2.3, bar 2.73): REJECTED. Worst months -36% (Sep 2008), -31% (Mar 2000), -28% (Feb 2020); maximum drawdown -76%.
- **Low volatility (the 50 calmest):** 13.8% and 14.9% a year, the same as the universe (excess -0.3% and -0.0% a month, REJECTED as a return claim) with annual swings of 19% and 15% against 32% and 25%, and a maximum drawdown of -49% and -18% against -72% and -51%. Turnover 13% a month, costs 0.8% a year.
- **Combined (average rank):** 16.6% and 18.7% a year, drawdown -61% and -21%; excess over the Nifty 500 +0.45% a month in 2018-23 (t +1.9), under the bar.
- **The bottom momentum decile** lost 5-7% a year (CONDITIONAL the expected way): the losers keep losing, which is the same fact as 'don't catch falling knives' in the exit book.
- **The control:** a random decile matched the universe before costs (-0.00% and -0.05% a month, t 0.0 and -0.3: the pipeline finds nothing in noise) and lost 4.9% a year after costs because a random decile turns over 90% a month. The registered row shows that cost, not a flaw: the benchmarks carry no trading cost, so every net row above is a little harsh on the portfolio (the universe's own turnover is a few percent a month).
- **Not covered:** quality and value need the point-in-time fundamentals, which start in 2017 (too short for this test); the Nifty 500 is the price index (dividends of about 1.2-1.5% a year would narrow the gap to it).
- **What Ananta does with this:** no rule change. For Phase 5 (the long-term money on paper) the honest candidate is the low-volatility or combined tilt judged on drawdown as much as return, run as a paper twin for at least 12 months before any yes; momentum alone is a crash-prone bet.

## The rows

| variant | expected | verdict | dev mean/mo | dev t | dev q | val mean/mo | val t | val q | months ahead | turnover/mo | cost drag/yr |
|---|---|---|---|---|---|---|---|---|---|---|---|
| MOM|vs_EW | + | REJECTED | +0.23% | +0.71 | 69 | +0.93% | +2.34 | 24 | +58.84% | +30.53% | +1.74% |
| MOM|vs_N500 | + | REJECTED | +0.62% | +1.53 | 57 | +1.09% | +1.68 | 24 | +57.08% | +30.53% | +1.74% |
| LOWVOL|vs_EW | + | REJECTED | -0.31% | -1.02 | 69 | -0.02% | -0.05 | 24 | +49.46% | +13.18% | +0.76% |
| LOWVOL|vs_N500 | + | REJECTED | -0.08% | -0.43 | 57 | +0.12% | +0.54 | 24 | +49.17% | +13.18% | +0.76% |
| COMBO|vs_EW | + | REJECTED | -0.06% | -0.18 | 69 | +0.28% | +0.64 | 24 | +54.51% | +25.93% | +1.40% |
| COMBO|vs_N500 | + | REJECTED | +0.15% | +0.66 | 57 | +0.45% | +1.91 | 24 | +57.50% | +25.93% | +1.40% |
| MOM_bottom|vs_EW | - | CONDITIONAL | -1.17% | -2.88 | 69 | -1.27% | -2.69 | 24 | +30.69% | +31.80% | +1.85% |
| RANDOM|vs_EW | 0 | CONDITIONAL | -0.41% | -3.66 | 69 | -0.47% | -2.47 | 24 | +39.35% | +90.49% | +4.88% |

## Portfolios and benchmarks by period (annualised return, volatility, max drawdown)

| portfolio | period | ann return | ann vol | max drawdown | months |
|---|---|---|---|---|---|
| MOM | dev | +16.13% | +34.50% | -76.06% | 205 |
| MOM | val | +25.12% | +27.44% | -42.81% | 72 |
| EW | dev | +14.39% | +32.11% | -72.01% | 205 |
| EW | val | +12.75% | +25.12% | -50.82% | 72 |
| N500 | dev | +20.44% | +24.77% | -60.91% | 169 |
| N500 | val | +12.46% | +18.98% | -29.98% | 71 |
| LOWVOL | dev | +13.77% | +18.67% | -49.23% | 205 |
| LOWVOL | val | +14.92% | +14.55% | -17.98% | 72 |
| COMBO | dev | +16.61% | +21.13% | -61.05% | 205 |
| COMBO | val | +18.69% | +17.05% | -21.38% | 72 |
| MOM_bottom | dev | -5.60% | +47.15% | -81.79% | 205 |
| MOM_bottom | val | -6.72% | +37.22% | -79.89% | 72 |
| RANDOM | dev | +8.88% | +32.44% | -73.55% | 205 |
| RANDOM | val | +6.62% | +25.43% | -58.80% | 72 |
