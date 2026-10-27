# HG1 results: Hedging a long stock basket when the Nifty is below its 200-day average: short index futures, 20% more cash, or a monthly 5%-out-of-the-money Nifty put

Registered 2026-10-27T00:37:41+00:00 (spec `hg1_v1.json`, written before the run); family hedge, k = 18, z = 2.99. Development to 2017, validation 2018-2023; nothing from 2024 on.

## In plain words

**None of the three hedges is free. Only holding 20% more cash in a downtrend passes the bar, and it is small; the futures hedge protects most but costs the most, and the put protected only in 2018-23.**
- **The basket:** an equal-weight daily average of the 250 most liquid stocks, a proxy for a long book (not the paper slots). The Nifty was below its 200-day average on 22.6% of sessions in 2003-17 and 21.1% in 2018-23. The unhedged basket's worst 20 sessions were -43.8% and -40.7%, its maximum drawdown -74.2% and -55.1%.
- **20% more cash below the 200-day (CONDITIONAL):** the worst 20-session stretch in a quarter was 0.66% shallower (t 3.7 in 2003-17, t 1.9 in 2018-23); the return given up was 0.21% and 0.40% a quarter (not significant): growth 22.5% to 22.4% a year and 11.0% to 10.0%. The maximum drawdown only moved from -74.2% to -68.1% and from -55.1% to -52.8%: a little protection for a little cost.
- **Short Nifty futures equal to the basket below the 200-day (INCONCLUSIVE):** the worst 20 sessions fell from -43.8% to -31.7% (2003-17) and from -40.7% to -16.1% (2018-23), the maximum drawdown from -74.2% to -55.1% and from -55.1% to -45.0%. It cost 1.09% and 1.70% a quarter (growth 22.5% to 19.1% and 11.0% to 5.6% a year): return per unit of drawdown improved in 2003-17 (0.30 to 0.35) and worsened in 2018-23 (0.20 to 0.12). The development quarter test passed (t 3.0) but 2018-23 did not (t 1.5).
- **Monthly 5%-out-of-the-money Nifty put (REJECTED):** in 2018-23 it cut the worst 20 sessions to -15.2% and the maximum drawdown to -39.0% and raised return per drawdown (0.20 to 0.25), but in 2003-17 it did not help the average quarter (-0.42%, t -1.2) and the maximum drawdown stayed -74.0%; it cost 0.10% and 0.68% a quarter. That is F06's result again (always-on puts rejected).
- **What Ananta does with this:** nothing changes in the paper rules. If a hedge is ever added, the cash version is the only one that earned its place on this evidence, and it should be tested on the real slots on the forward paper book first. The futures proxy used the actual nearest-month settlement prices.

## The rows

Verdicts: VALIDATED and CONDITIONAL would be passes; OPPOSITE means significantly the other way round in development and the same way in 2018-23; INCONCLUSIVE means too few independent blocks (16 needed per period) or a reading below the bar.

| variant | expected | verdict | dev mean | dev t | dev blocks | val mean | val t | val blocks | events dev / val |
|---|---|---|---|---|---|---|---|---|---|
| short_futures|return | + | REJECTED | -1.09% | -1.20 | 59 | -1.70% | -1.12 | 24 | 59 / 24 |
| short_futures|worst20 | + | INCONCLUSIVE | +1.99% | +3.01 | 59 | +2.28% | +1.45 | 24 | 59 / 24 |
| cash20|return | + | REJECTED | -0.21% | -0.81 | 59 | -0.40% | -0.98 | 24 | 59 / 24 |
| cash20|worst20 | + | CONDITIONAL | +0.66% | +3.72 | 59 | +0.66% | +1.93 | 24 | 59 / 24 |
| put5otm|return | + | REJECTED | -0.10% | -0.23 | 59 | -0.68% | -0.65 | 24 | 59 / 24 |
| put5otm|worst20 | + | REJECTED | -0.42% | -1.20 | 59 | +2.20% | +1.66 | 24 | 59 / 24 |

## The whole-period picture (unhedged basket against each arm)

| arm | period | signal on | CAGR unhedged | CAGR hedged | max drawdown unhedged | max drawdown hedged | worst 20 sessions unhedged | worst 20 sessions hedged | CAGR / max drawdown unhedged | hedged |
|---|---|---|---|---|---|---|---|---|---|---|
| short_futures | dev | +22.62% | +22.48% | +19.05% | -74.16% | -55.14% | -43.75% | -31.67% | +0.30 | +0.35 |
| short_futures | val | +21.08% | +10.99% | +5.56% | -55.09% | -45.01% | -40.72% | -16.11% | +0.20 | +0.12 |
| cash20 | dev | +22.62% | +22.48% | +22.35% | -74.16% | -68.09% | -43.75% | -36.61% | +0.30 | +0.33 |
| cash20 | val | +21.08% | +10.99% | +10.02% | -55.09% | -52.77% | -40.72% | -34.45% | +0.20 | +0.19 |
| put5otm | dev | +22.62% | +22.48% | +21.12% | -74.16% | -73.99% | -43.75% | -37.04% | +0.30 | +0.29 |
| put5otm | val | +21.08% | +10.99% | +9.68% | -55.09% | -39.04% | -40.72% | -15.16% | +0.20 | +0.25 |
