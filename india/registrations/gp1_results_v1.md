# GP1 results: The opening gap: does buying the open after a gap-down (mean reversion) or after a gap-up (follow-through) beat ordinary days, after costs?

Registered 2026-10-30T02:04:52+00:00 (spec `gp1_v1.json`, written before the run); family gaps, k = 10, z = 2.81. Development to 2017, validation 2018-2023; nothing from 2024 on.

## In plain words

**The gap rule is not a usable buy call. The stock "buy the open after a gap-down" rows pass the bar on paper (bar z 2.81), but they cannot be traded as defined, and the edge has faded to nothing in the last three years.**
- **Stocks, gap-down of 2% or more at the open (31,064 events in 2000-17, 5,901 in 2018-23):** buying that open and selling the same close beat an ordinary day by 2.26% in 2000-17 (t 14.7) and by 0.44% in 2018-23 (t 3.0): VALIDATED. Held five sessions: +2.22% and +0.64%; gap-down of 1% or more: +1.22% and +0.41% (both CONDITIONAL).
- **Why this is not trusted:** the gap is only known once the market has opened, and an order placed then does not fill at the opening price; the open is often the low of a panic. By year the edge was about +2.6% to +3.2% a trade after costs in 2002-07, about +0.1% to +1.2% in 2015-20, and zero or negative in 2021-23 (-0.5%, -0.2%, -0.1%). Checked after the run (not registered, no verdict) with an order at the open of the second five-minute bar (09:20), 2015-23: the gap-down days beat ordinary days by +0.63% in 2015-17 (t 1.6) and +0.17% in 2018-23 (t 1.4), and the trade itself lost 0.08% after costs; entering at 09:45 the difference is +0.15% and +0.04%. Nothing is left once the price is one a person could get.
- **Gap-ups:** buying the open of a stock that gapped up 2% or more did worse than ordinary days (-1.03%, t -8.2, in 2000-17; -0.07% in 2018-23): OPPOSITE; the opening print is the high. Buying the next session's open instead did nothing (+0.03% and +0.15%): REJECTED.
- **Nifty and Bank Nifty:** gap-downs of 1% or more were followed by slightly better five-session returns, but not significantly (Bank Nifty +0.11% and +0.75%, 198 and 62 events: REJECTED); the Nifty has only 38 and 37 such days (INCONCLUSIVE). Gap-ups of 1% or more: no difference. A 2% gap is too rare on the indices to test. Waiting 30 minutes after the open on the Nifty: 12 events in 2015-17 and 37 in 2018-23, +0.22% and +0.44%, INCONCLUSIVE (the 5-minute history only starts in 2015).
- **What Ananta does with this:** nothing changes in the paper rules. There is still no gap rule it can use: a gap-down used to bounce at the open, that was an opening-price effect, it has faded, and it is not available to a person placing an order.

## The rows

Verdicts: VALIDATED and CONDITIONAL would be passes; OPPOSITE means significantly the other way round in development and the same way in 2018-23; INCONCLUSIVE means too few independent blocks (16 needed per period) or a reading below the bar.

| variant | expected | verdict | dev mean | dev t | dev blocks | val mean | val t | val blocks | events dev / val |
|---|---|---|---|---|---|---|---|---|---|
| STK|gapdown2|open|hold1 | + | VALIDATED | +2.26% | +14.74 | 71 | +0.44% | +2.98 | 24 | 31064 / 5901 |
| STK|gapdown2|open|hold5 | + | CONDITIONAL | +2.22% | +10.87 | 71 | +0.64% | +2.45 | 24 | 31064 / 5901 |
| STK|gapdown1|open|hold5 | + | CONDITIONAL | +1.22% | +10.47 | 71 | +0.41% | +2.77 | 24 | 53279 / 12997 |
| STK|gapup2|open|hold5 | + | OPPOSITE | -1.03% | -8.20 | 71 | -0.07% | -0.39 | 24 | 41862 / 6346 |
| STK|gapup2|next|hold5 | + | REJECTED | +0.03% | +0.31 | 71 | +0.15% | +0.83 | 24 | 41502 / 6314 |
| NIFTY|gapdown1|open|hold5 | + | INCONCLUSIVE | +0.07% | +0.22 | 17 | +0.69% | +1.58 | 13 | 38 / 37 |
| NIFTY|gapup1|open|hold5 | + | INCONCLUSIVE | -0.60% | -0.77 | 26 | -0.08% | -0.16 | 15 | 57 / 42 |
| BANK|gapdown1|open|hold5 | + | REJECTED | +0.11% | +0.25 | 52 | +0.75% | +1.38 | 22 | 198 / 62 |
| BANK|gapup1|open|hold5 | + | INCONCLUSIVE | +0.61% | +1.78 | 56 | +0.22% | +0.39 | 21 | 232 / 70 |
| NIFTY|gapdown1|wait30|hold5 | + | INCONCLUSIVE | +0.22% | +0.32 | 8 | +0.44% | +1.04 | 13 | 12 / 37 |

## The trade itself after costs (stocks)

| variant | mean net per trade, all years | dev: quarter-mean t | val: quarter-mean t |
|---|---|---|---|
| STK|gapdown2|open|hold1 | +1.72% | +1.96% (t +12.07) | -0.02% (t -0.17) |
| STK|gapdown2|open|hold5 | +1.56% | +2.12% (t +6.62) | +0.38% (t +0.96) |
| STK|gapdown1|open|hold5 | +0.78% | +1.13% (t +4.59) | +0.16% (t +0.56) |
| STK|gapup2|open|hold5 | -1.53% | -1.54% (t -6.51) | -0.40% (t -1.25) |
| STK|gapup2|next|hold5 | -0.31% | -0.30% (t -1.44) | -0.15% (t -0.54) |

## Diagnostic after the run (not registered, no verdict): is the open-price edge tradable?

Stock gap-down of 2% or more, liquid 250, bought at the open and sold at the close of the same day, after costs, by year:

| year | events | event mean (hold 1) | ordinary day mean | event mean (hold 5) | ordinary mean (hold 5) |
|---|---|---|---|---|---|
| 2000 | 3676 | +1.15% | -0.76% | -0.30% | -1.35% |
| 2001 | 3227 | +1.73% | -0.55% | +0.78% | -0.93% |
| 2002 | 2287 | +2.59% | -0.78% | +3.36% | -0.42% |
| 2003 | 1913 | +3.22% | -0.54% | +4.31% | +0.80% |
| 2004 | 1905 | +2.59% | -0.64% | +1.77% | -0.21% |
| 2005 | 1369 | +3.23% | -0.72% | +3.89% | -0.10% |
| 2006 | 1862 | +2.84% | -0.74% | +2.38% | -0.27% |
| 2007 | 2458 | +2.94% | -0.53% | +3.61% | +0.58% |
| 2008 | 3545 | +1.52% | -0.92% | -1.04% | -2.31% |
| 2009 | 2277 | +2.38% | -0.41% | +5.04% | +1.00% |
| 2010 | 1279 | +2.09% | -0.59% | +2.20% | -0.44% |
| 2011 | 549 | +2.14% | -0.67% | +2.58% | -1.23% |
| 2012 | 983 | +2.56% | -0.46% | +2.98% | +0.06% |
| 2013 | 879 | +0.93% | -0.45% | -0.27% | -0.80% |
| 2014 | 430 | +0.23% | -0.20% | +0.77% | +0.39% |
| 2015 | 964 | +0.10% | -0.45% | +0.76% | -0.48% |
| 2016 | 1038 | +1.24% | -0.56% | -0.23% | -0.45% |
| 2017 | 423 | +0.58% | -0.46% | +1.51% | +0.23% |
| 2018 | 1091 | +0.53% | -0.56% | +2.10% | -0.75% |
| 2019 | 629 | +0.16% | -0.59% | -0.26% | -0.63% |
| 2020 | 1620 | +0.12% | -0.27% | -0.14% | -0.23% |
| 2021 | 806 | -0.48% | -0.45% | +1.03% | +0.13% |
| 2022 | 1272 | -0.24% | -0.60% | -0.64% | -0.60% |
| 2023 | 483 | -0.09% | -0.46% | +0.42% | +0.14% |

The same days entered at the open of the second five-minute bar (09:20) or of the 09:45 bar and sold at the close, stocks in the 5-minute history only, against every 5th session of the same stocks (quarters; development 2015-17 holds 12 quarters):

| entry | events | mean net per trade | ordinary day mean | vs ordinary 2015-17 (t) | vs ordinary 2018-23 (t) |
|---|---|---|---|---|---|
| 09:20 bar open | 5385 | -0.08% | -0.43% | +0.63% (+1.64) | +0.17% (+1.36) |
| 09:45 bar open | 5394 | -0.36% | -0.44% | +0.15% (+0.57) | +0.04% (+0.40) |
