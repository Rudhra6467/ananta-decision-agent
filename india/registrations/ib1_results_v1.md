# IB1 results: Intraday breakouts: on Nifty, Bank Nifty and liquid stocks, does trading the break of the opening range (first 15 or 30 minutes), the break of the first hour's range after 11:00, or a stock reclaiming its VWAP earn more after costs than a random intraday entry?

Registered 2026-10-27T22:37:25+00:00 (spec `ib1_v1.json`, written before the run); family intraday, k = 36, z = 3.20. Development to 2017, validation 2018-2023; nothing from 2024 on.

## In plain words

**Intraday breakouts beat a random entry on the same days, often strongly, but almost none of them make money after costs on their own: they lose less than random entries do. VALIDATED here means 'better than random', not 'profitable'.**
- **Liquid stocks, buy the break above the first 15 or 30 minutes' high (stop at the range low, out at 15:25), 17,590 and 15,377 trades in 2015-17, 38,153 and 33,420 in 2018-23:** about 0.10-0.14% a trade better than a random entry (t 7-9, VALIDATED), but the trades themselves averaged -0.07% and -0.06% after costs, against -0.18% for random entries. Stopped out on 38% and 29% of trades; win rate about 40%.
- **Stocks reclaiming VWAP:** 0.04-0.05% better than random (CONDITIONAL), but -0.14% a trade after costs.
- **Nifty opening-range breakout, both directions:** 15 minutes REJECTED; 30 minutes VALIDATED against random (+0.13% and +0.08% a trade better) yet about -0.005% a trade after costs. **Bank Nifty:** 15 and 30 minutes CONDITIONAL; the 30-minute version earned +0.02% a trade after costs.
- **Breaking the first hour's range after 11:00 (both indices, 3,910 trades):** VALIDATED against random (+0.08% and +0.11%); +0.03% a trade after costs: the only version clearly above zero, and small next to realistic slippage on a stop order.
- **Caveats:** fills at the breakout level and at the stop are assumed with only the half-spread cost model; a fast breakout usually slips a few basis points more, which is about the whole edge. The stock universe was re-run on the previous session's liquidity rank (a same-day rank leaked slightly); the results barely changed.
- **What Ananta does with this:** a breakout is better timing than a random entry, but not a money-maker by itself after costs. It could be tested as a shadow paper book, never traded on this alone.

## The rows

Verdicts: VALIDATED and CONDITIONAL would be passes; OPPOSITE means significantly the other way round; INCONCLUSIVE means too few independent blocks (16 needed per period) or a reading below the bar.

| variant | expected | verdict | dev mean | dev t | dev blocks | val mean | val t | val blocks | events dev / val |
|---|---|---|---|---|---|---|---|---|---|
| NIFTY|orb15|net | + | REJECTED | +0.03% | +1.31 | 36 | +0.05% | +2.46 | 72 | 718 / 1472 |
| NIFTY|orb30|net | + | VALIDATED | +0.13% | +4.80 | 36 | +0.08% | +3.60 | 72 | 701 / 1456 |
| BANK|orb15|net | + | CONDITIONAL | +0.13% | +3.60 | 36 | +0.06% | +1.70 | 72 | 723 / 1456 |
| BANK|orb30|net | + | CONDITIONAL | +0.15% | +4.31 | 36 | +0.09% | +2.35 | 72 | 689 / 1433 |
| IDX|fh_break|net | + | VALIDATED | +0.08% | +3.25 | 36 | +0.11% | +4.99 | 72 | 1263 / 2647 |
| STK|orb15|net | + | VALIDATED | +0.14% | +8.47 | 35 | +0.10% | +7.39 | 72 | 17590 / 38153 |
| STK|orb30|net | + | VALIDATED | +0.14% | +8.64 | 35 | +0.12% | +8.96 | 72 | 15377 / 33420 |
| STK|vwap_reclaim|net | + | CONDITIONAL | +0.04% | +3.12 | 35 | +0.05% | +4.56 | 72 | 21057 / 44948 |
