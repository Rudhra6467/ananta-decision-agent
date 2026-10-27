# CA1 results: Corporate actions: do stocks do better after a bonus or split, a buyback, or a large dividend, from the ex-date on?

Registered 2026-10-27T13:26:34+00:00 (spec `ca1_v1.json`, written before the run); family events, k = 29, z = 3.13. Development to 2017, validation 2018-2023; nothing from 2024 on.

## In plain words

**Corporate actions did not come before better returns. After a bonus or split ex-date, stocks did WORSE than ordinary days (OPPOSITE); large dividends and buybacks showed nothing.**
- **Bonus or split (321 ex-dates in 2000-17, 119 in 2018-23, panel stocks):** the next 20 sessions from the day after the ex-date were 3.8% (t -3.9) and 6.0% (t -6.2) weaker than ordinary days; the next 60 sessions 4.1% and 3.3% weaker: OPPOSITE. The stock had typically run up into the event (median +1.4% at the ex-date open). The price adjustment was checked: no artificial jumps.
- **Buyback (32 / 95 ex-dates):** -1.3% and -0.4% over 20 sessions, -4.4% and -1.1% over 60: INCONCLUSIVE (too few in 2000-17).
- **Dividend of 2% or more of the price (715 / 429):** +1.1% and +0.2% over 20 sessions: REJECTED.
- **The limit:** the free history has ex-dates, not announcement dates, so the reaction to the news itself is untested.
- **What Ananta does with this:** a bonus or split is no reason to buy; the record says the run-up tends to reverse after the ex-date. No rule changes.

## The rows

Verdicts: VALIDATED and CONDITIONAL would be passes; OPPOSITE means significantly the other way round; INCONCLUSIVE means too few independent blocks (16 needed per period) or a reading below the bar.

| variant | expected | verdict | dev mean | dev t | dev blocks | val mean | val t | val blocks | events dev / val |
|---|---|---|---|---|---|---|---|---|---|
| STK|bonus_split|fwd20 | + | OPPOSITE | -3.76% | -3.91 | 36 | -6.00% | -6.16 | 18 | 321 / 119 |
| STK|bonus_split|fwd60 | + | OPPOSITE | -4.09% | -3.12 | 36 | -3.26% | -2.09 | 18 | 321 / 119 |
| STK|buyback|fwd20 | + | INCONCLUSIVE | -1.25% | -0.40 | 5 | -0.38% | -0.33 | 16 | 32 / 95 |
| STK|buyback|fwd60 | + | INCONCLUSIVE | -4.43% | -1.10 | 5 | -1.15% | -0.41 | 15 | 32 / 95 |
| STK|dividend_y2|fwd20 | + | REJECTED | +1.06% | +0.91 | 37 | +0.16% | +0.19 | 22 | 715 / 429 |
