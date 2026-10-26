# SR1 results: Support and resistance as an entry: does a bounce off support or a close through resistance give a buy call (and a close below support a sell call)?

Registered 2026-10-26T16:24:45+00:00 (spec `sr1_v1.json`, written before the run); family technical, k = 38, z = 3.21. Development to 2017, validation 2018-2023; nothing from 2024 on.

## In plain words

**Support and resistance are not an entry signal here. Nothing reached the bar (z 3.21), and on stocks a close through resistance did WORSE than ordinary days.** The levels are the technicals panel's own (swing points with 5 bars each side; checked to match it exactly).
- **Stocks, breakout above 60-session resistance (35,883 events in 2000-17, 13,411 in 2018-23):** the next 20 sessions were about 0.95% worse than an ordinary day in the same quarter in 2000-17 and 0.54% worse in 2018-23 (t -4.6 and -2.9): OPPOSITE. Over 20-session resistance (23,226 / 8,521): about 1.1% and 0.5% worse (t -4.3 and -2.0): OPPOSITE. As a trade after costs the breakout earned about zero (REJECTED).
- **Stocks, bounce off support (touched it and closed up within 1.5% above):** no edge over ordinary days, from 60-session support (10,946 / 5,102: +0.1% and +0.2%, t 0.6 and 0.8) or 20-session support (5,001 / 2,355). As a trade the 60-session bounce made about +0.9% after costs in both periods, which is the market's own drift, not significant (t 1.5 and 1.0): REJECTED.
- **Stocks, close below 60-session support (31,331 / 11,514):** not followed by weaker returns (REJECTED).
- **Nifty and Bank Nifty, bounce off and break through 60-session levels:** no difference from other sessions (REJECTED, every |t| under 1.2).
- **What Ananta does with this:** nothing changes in the paper rules. Support and resistance stay a description of where the price has turned before, never a reason to buy; a close through resistance is, if anything, a reason not to chase (as TWT-H10 'don't chase' found).

## The rows

Verdicts: VALIDATED and CONDITIONAL would be passes; OPPOSITE means significantly the other way round in 2000/2003-2017 and the same way in 2018-23; INCONCLUSIVE means too few independent blocks (16 needed per period) or a reading below the bar.

| variant | expected | verdict | dev mean | dev t | dev blocks | val mean | val t | val blocks | events dev / val |
|---|---|---|---|---|---|---|---|---|---|
| STK|bounce20|net20 | + | REJECTED | -0.05% | -0.18 | 70 | +0.13% | +0.35 | 24 | 5001 / 2355 |
| STK|bounce60|net20 | + | REJECTED | +0.11% | +0.60 | 70 | +0.24% | +0.80 | 24 | 10946 / 5102 |
| STK|bounce60|net20|absolute | + | REJECTED | +0.93% | +1.46 | 70 | +0.86% | +0.98 | 24 | 10946 / 5102 |
| STK|break20|net20 | + | OPPOSITE | -1.08% | -4.29 | 70 | -0.49% | -1.97 | 24 | 23226 / 8521 |
| STK|break60|net20 | + | OPPOSITE | -0.95% | -4.57 | 70 | -0.54% | -2.88 | 24 | 35883 / 13411 |
| STK|break60|net20|absolute | + | REJECTED | -0.12% | -0.18 | 70 | +0.08% | +0.10 | 24 | 35883 / 13411 |
| STK|breakdown60|net20 | - | REJECTED | +0.08% | +0.22 | 70 | +0.49% | +1.51 | 24 | 31331 / 11514 |
| NIFTY|bounce60|fwd20 | + | REJECTED | +0.36% | +0.39 | 39 | -0.12% | -0.13 | 21 | 80 / 44 |
| NIFTY|break60|fwd20 | + | REJECTED | -0.42% | -0.44 | 57 | -0.06% | -0.06 | 24 | 152 / 66 |
| BANK|bounce60|fwd20 | + | REJECTED | +1.68% | +1.11 | 37 | +0.66% | +0.41 | 21 | 60 / 43 |
| BANK|break60|fwd20 | + | REJECTED | -0.86% | -0.83 | 56 | -0.06% | -0.05 | 24 | 160 / 66 |
