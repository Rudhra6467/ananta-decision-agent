# CL1 results: The combination lab: does a stock setup together with a market state earn more over 20 sessions than the better of the two alone? Five stock setups x five market states on the random (ANY) entries, 2000-2023

Registered 2026-10-30T02:41:51+00:00 (spec `cl1_v1.json`, written before the run); family combination, k = 30, z = 3.14. Development 2000-2017, validation 2018-2023; nothing from 2024 on. HISTORICAL BACKTEST, paper only.

The verdict stat (v2) = mean net 20-session return with both on, minus the mean with the market state on and the setup off, per quarter; t across quarters (the setup's added value given the state). The state's added value given the setup is in the manifest; the shortlist needs both positive in validation. Plateau = the same at the loose and tight thresholds of the stock setup (validation period). Consistency = share of years in which both-on beat the state alone.

## In plain words

**No pair beats its parts. The lab, run honestly (one bar over all 30 tries, a plateau, year-by-year consistency, a random control), shortlists nothing: the found single filters do the work, and adding a market state to them adds nothing or subtracts.**
- **The control held:** a random stock flag inside each market state earned +0.03% / +0.01% (t 0.2 / 0.1) and -0.05% / +0.28% (t -0.2 / +1.0): the pipeline finds nothing in noise. (The first version of the metric was biased and the control caught it; v2 is an ordinary on/off comparison inside the state, quarter by quarter.)
- **'Not extended' (no more than 20% above the 50-day, up no more than 25% in 20 sessions) is VALIDATED inside two market states** (+1.5% / +1.8% a trade given Nifty above its 200-day, t 4.6 / 3.4; +1.3% / +2.1% given small-cap leadership, t 3.4 / 3.2; plateau holds, 76% and 55% of years): that is E04's no-chase filter again, working in any market. The market state itself subtracts given the setup (-4.1% and -3.2% in 2018-23: inside a quarter, the sessions with the Nifty above its 200-day were worse to buy than those below, the weak-market entry effect of E08/C01). So: keep the filter, ignore the state.
- **Delivery share over 60% inside small-cap leadership:** +0.9% / +1.9% a trade (t 3.3 / 4.1), 65% of years, plateau holds; the state adds nothing given the setup (-1.1%, t -1.3). The single delivery effect (C02) stands; the pair is not more than it.
- **Oversold (RSI under 30) in a washed-out or fearful market** (under 30% of stocks above their 200-day; India VIX above 20): the only pairs where each side added to the other (+1.8% / +1.9% a trade given the state in 2018-23, +10% / +7% given the setup), but fear states are rare: 8-10 validation quarters against 16 needed, INCONCLUSIVE, and not on the shortlist. Worth a look again when the sealed years can be opened, not before.
- **Healthy pullbacks and 60-session washouts** added nothing in any state; the breadth-thrust state is too rare to test (0-4 quarters).
- **Note on the table:** pooled means over all years are not comparable between groups (extended stocks cluster in roaring quarters); the quarter-paired numbers are the statistic.
- **What Ananta does with this:** no paper trial from this lab; the two single filters it re-confirmed (not extended; delivery over 60%) are already on the one-yes list for the paper rules (map class C). The combination question is closed for this version; it is not re-opened with more pairs.

## Shortlist (the spec's rating: a pass, a plateau, consistency 60%+)

- none

## The rows

| pair | expected | verdict | dev mean | dev t | dev q | val mean | val t | val q | both-on trades | plateau holds | consistency |
|---|---|---|---|---|---|---|---|---|---|---|---|
| rsi_lt30|nifty_gt200d | + | INCONCLUSIVE | +0.89% | +1.72 | 46 | +1.10% | +1.54 | 21 | 2910 | yes | +70.00% |
| rsi_lt30|breadth_lt30 | + | INCONCLUSIVE | +3.83% | +2.65 | 24 | +1.84% | +1.71 | 8 | 3304 | yes | +73.33% |
| rsi_lt30|vix_gt20 | + | INCONCLUSIVE | +1.24% | +0.88 | 20 | +1.85% | +1.86 | 10 | 1630 | yes | +61.54% |
| rsi_lt30|small_lead | + | INCONCLUSIVE | +0.68% | +1.22 | 42 | -0.77% | -1.08 | 14 | 1531 | no | +31.58% |
| rsi_lt30|breadth_thrust | + | INCONCLUSIVE | n/a | n/a | 0 | n/a | n/a | 0 | 2 | no | n/a |
| not_extended|nifty_gt200d | + | VALIDATED | +1.54% | +4.61 | 50 | +1.81% | +3.44 | 22 | 89098 | yes | +76.19% |
| not_extended|breadth_lt30 | + | INCONCLUSIVE | +2.52% | +1.59 | 17 | +1.21% | +0.38 | 3 | 25162 | yes | +64.29% |
| not_extended|vix_gt20 | + | INCONCLUSIVE | +2.33% | +2.22 | 17 | +2.20% | +1.18 | 8 | 26854 | yes | +83.33% |
| not_extended|small_lead | + | VALIDATED | +1.29% | +3.40 | 46 | +2.05% | +3.16 | 19 | 59407 | yes | +55.00% |
| not_extended|breadth_thrust | + | INCONCLUSIVE | +2.88% | +1.53 | 3 | n/a | n/a | 0 | 302 | no | +60.00% |
| pull_healthy|nifty_gt200d | + | INCONCLUSIVE | -0.77% | -0.81 | 40 | -1.41% | -1.28 | 15 | 992 | no | +40.00% |
| pull_healthy|breadth_lt30 | + | INCONCLUSIVE | -2.56% | -1.47 | 11 | n/a | n/a | 1 | 187 | yes | +20.00% |
| pull_healthy|vix_gt20 | + | INCONCLUSIVE | -0.90% | -0.35 | 12 | -2.66% | -1.80 | 7 | 390 | no | +45.45% |
| pull_healthy|small_lead | + | INCONCLUSIVE | -0.03% | -0.03 | 33 | -0.81% | -0.59 | 11 | 716 | no | +52.63% |
| pull_healthy|breadth_thrust | + | INCONCLUSIVE | n/a | n/a | 0 | n/a | n/a | 0 | 0 | no | n/a |
| deliv_high|nifty_gt200d | + | INCONCLUSIVE | +0.73% | +3.12 | 50 | +0.91% | +2.84 | 22 | 18699 | yes | +71.43% |
| deliv_high|breadth_lt30 | + | INCONCLUSIVE | -1.12% | -1.17 | 20 | -1.45% | -1.68 | 8 | 3698 | no | +46.15% |
| deliv_high|vix_gt20 | + | INCONCLUSIVE | -0.80% | -0.86 | 22 | -0.19% | -0.22 | 12 | 4399 | no | +30.77% |
| deliv_high|small_lead | + | VALIDATED | +0.95% | +3.29 | 50 | +1.92% | +4.10 | 20 | 12017 | yes | +65.00% |
| deliv_high|breadth_thrust | + | INCONCLUSIVE | +0.74% | +0.91 | 4 | n/a | n/a | 2 | 153 | yes | +75.00% |
| washout60|nifty_gt200d | + | REJECTED | +1.07% | +1.13 | 46 | +0.47% | +0.33 | 18 | 2303 | no | +47.62% |
| washout60|breadth_lt30 | + | INCONCLUSIVE | +3.97% | +2.93 | 27 | +0.79% | +0.71 | 8 | 6457 | yes | +86.67% |
| washout60|vix_gt20 | + | INCONCLUSIVE | +5.42% | +2.92 | 18 | +2.19% | +1.18 | 9 | 1826 | yes | +90.91% |
| washout60|small_lead | + | INCONCLUSIVE | +0.93% | +0.85 | 38 | -0.43% | -0.23 | 14 | 1189 | no | +50.00% |
| washout60|breadth_thrust | + | INCONCLUSIVE | n/a | n/a | 0 | n/a | n/a | 0 | 3 | no | n/a |
| RANDOM|nifty_gt200d | 0 | REJECTED | +0.03% | +0.19 | 50 | +0.01% | +0.05 | 22 | 89260 | - | +42.86% |
| RANDOM|breadth_lt30 | 0 | INCONCLUSIVE | -0.91% | -1.73 | 25 | -0.31% | -0.38 | 8 | 24422 | - | +26.67% |
| RANDOM|vix_gt20 | 0 | INCONCLUSIVE | -0.18% | -0.54 | 19 | +0.54% | +0.47 | 13 | 27409 | - | +38.46% |
| RANDOM|small_lead | 0 | REJECTED | -0.05% | -0.23 | 47 | +0.28% | +0.99 | 20 | 60660 | - | +45.00% |
| RANDOM|breadth_thrust | 0 | INCONCLUSIVE | +1.22% | +2.93 | 3 | n/a | n/a | 0 | 620 | - | +80.00% |
