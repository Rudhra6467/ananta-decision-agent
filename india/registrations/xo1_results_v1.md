# XO1 results: Moving-average and MACD crossovers, and averages converging: do they give a buy (or sell) call?

Registered 2026-10-26T15:31:07+00:00 (spec `xo1_v1.json`, written before the run); family technical, k = 27, z = 3.11. Development to 2017, validation 2018-2023; nothing from 2024 on.

## In plain words

**Crossovers are not a buy call here. Nothing reached the bar (z 3.11), and on stocks the classic buy crosses did slightly WORSE than ordinary days.**
- **Stocks, 50/200 golden cross (2,557 events in 2000-17, 936 in 2018-23):** the next 60 sessions were about 2.7% worse than an ordinary day in the same quarter, in both periods (t -2.6 and -2.2): OPPOSITE. The cross comes after the move.
- **Stocks, 20/50 upward cross (10,551 / 3,892 events):** about 0.5-0.7% worse over 20 sessions: OPPOSITE. Taken as a trade after costs, golden and 20/50 crosses earned about zero (REJECTED).
- **Stocks, death cross and 20/50 downward cross:** no difference from ordinary days (REJECTED).
- **MACD signal-line crosses:** upward crosses are no help on stocks, Nifty or Bank Nifty (REJECTED). Downward crosses on stocks were weaker in 2000-17 (t -2.8) but not in 2018-23 (INCONCLUSIVE).
- **Index 50/200 crosses:** there were only 8 golden and 8 death crosses on the Nifty in 2003-17, and 5 each in 2018-23 (Bank Nifty about the same), far too few to judge: INCONCLUSIVE. The 20/50 crosses (about 34 and 14) are also INCONCLUSIVE.
- **Holding the Nifty only while the 50-day is above the 200-day:** not better. In 2018-23 the next 20 sessions were weaker in that state (t -2.4, only 10 blocks): INCONCLUSIVE.
- **Averages converging (20, 50 and 200-day within 2%):** on stocks it was followed by SMALLER moves, not bigger ones (t -2.8 and -2.9): OPPOSITE. It marks a quiet stock that stays quiet.
- **What Ananta does with this:** nothing changes in the paper rules. Crossovers stay a description of the trend, never a reason to buy.

## The rows

Verdicts: VALIDATED and CONDITIONAL would be passes; OPPOSITE means significantly the other way round in 2000/2003-2017 and the same way in 2018-23; INCONCLUSIVE means too few independent blocks (16 needed per period) or a reading below the bar.

| variant | expected | verdict | dev mean | dev t | dev blocks | val mean | val t | val blocks | events dev / val |
|---|---|---|---|---|---|---|---|---|---|
| NIFTY|gc|fwd60 | + | INCONCLUSIVE | +0.24% | +0.09 | 8 | +1.38% | +0.55 | 5 | 8 / 5 |
| NIFTY|dc|fwd60 | - | INCONCLUSIVE | +1.64% | +0.42 | 8 | +2.71% | +0.63 | 5 | 8 / 5 |
| NIFTY|x2050up|fwd20 | + | INCONCLUSIVE | -0.86% | -0.77 | 33 | +0.70% | +0.44 | 13 | 34 / 14 |
| NIFTY|x2050dn|fwd20 | - | INCONCLUSIVE | -0.88% | -0.70 | 33 | -1.80% | -1.22 | 14 | 34 / 15 |
| NIFTY|macdup|fwd20 | + | REJECTED | +0.40% | +0.53 | 55 | -0.16% | -0.19 | 24 | 122 / 52 |
| NIFTY|macddn|fwd20 | - | INCONCLUSIVE | -1.39% | -1.69 | 55 | -0.64% | -0.57 | 24 | 121 / 51 |
| NIFTY|state50gt200|fwd20 | + | INCONCLUSIVE | -0.70% | -0.62 | 24 | -3.33% | -2.37 | 10 | 2542 / 1124 |
| NIFTY|converge|abs20 | + | INCONCLUSIVE | -1.67% | -2.41 | 11 | -0.50% | -0.75 | 9 | 165 / 164 |
| BANK|gc|fwd60 | + | INCONCLUSIVE | +2.63% | +0.61 | 9 | +8.73% | +1.60 | 5 | 9 / 5 |
| BANK|dc|fwd60 | - | INCONCLUSIVE | +0.29% | +0.04 | 8 | +1.24% | +0.24 | 5 | 8 / 5 |
| BANK|x2050up|fwd20 | + | INCONCLUSIVE | +1.31% | +0.60 | 34 | +1.93% | +1.13 | 15 | 36 / 16 |
| BANK|x2050dn|fwd20 | - | INCONCLUSIVE | -3.51% | -1.87 | 32 | +1.91% | +1.10 | 15 | 35 / 16 |
| BANK|macdup|fwd20 | + | REJECTED | -0.17% | -0.15 | 56 | -0.30% | -0.22 | 24 | 122 / 49 |
| BANK|macddn|fwd20 | - | REJECTED | -0.54% | -0.45 | 57 | -0.91% | -0.42 | 23 | 120 / 48 |
| BANK|state50gt200|fwd20 | + | INCONCLUSIVE | -1.77% | -0.97 | 21 | -4.55% | -2.42 | 10 | 2480 / 1119 |
| BANK|converge|abs20 | + | INCONCLUSIVE | -0.73% | -0.32 | 6 | +1.63% | +1.13 | 8 | 86 / 87 |
| STK|gc|net60 | + | OPPOSITE | -2.74% | -2.64 | 64 | -2.75% | -2.23 | 23 | 2557 / 936 |
| STK|dc|net60 | - | REJECTED | -0.18% | -0.19 | 65 | +0.67% | +0.52 | 23 | 2739 / 984 |
| STK|x2050up|net20 | + | OPPOSITE | -0.74% | -2.10 | 70 | -0.54% | -1.23 | 24 | 10551 / 3892 |
| STK|x2050dn|net20 | - | REJECTED | -0.66% | -1.34 | 70 | +0.07% | +0.21 | 24 | 11439 / 4069 |
| STK|macdup|net20 | + | REJECTED | +0.23% | +0.99 | 70 | +0.43% | +1.54 | 24 | 34114 / 12234 |
| STK|macddn|net20 | - | INCONCLUSIVE | -0.75% | -2.82 | 70 | -0.21% | -0.84 | 24 | 34263 / 12390 |
| STK|converge|abs20 | + | OPPOSITE | -1.29% | -2.77 | 66 | -0.95% | -2.89 | 24 | 1886 / 966 |
| STK|x2050up_uptrend|net20 | + | REJECTED | +0.29% | +0.82 | 50 | -0.08% | -0.17 | 23 | 6238 / 3115 |
| STK|x2050up_downtrend|net20 | + | INCONCLUSIVE | -0.29% | -0.34 | 20 | -2.40% | -1.29 | 12 | 669 / 476 |
| STK|gc|net60|absolute | + | REJECTED | +0.74% | +0.38 | 66 | -0.17% | -0.07 | 24 | 2557 / 936 |
| STK|x2050up|net20|absolute | + | REJECTED | +0.12% | +0.16 | 70 | +0.08% | +0.09 | 24 | 10551 / 3892 |
