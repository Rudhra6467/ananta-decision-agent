# MS1 results: Intraday patterns: does the first 15 minutes' direction carry through the rest of the day (indices and liquid stocks), does the last hour extend the day's move, does a wide opening range come before a wide rest of the day, and are expiry-day afternoons more volatile?

Registered 2026-10-27T22:37:32+00:00 (spec `ms1_v1.json`, written before the run); family intraday, k = 42, z = 3.24. Development to 2017, validation 2018-2023; nothing from 2024 on.

## In plain words

**The opening and the close are the busy parts of the Indian day, a wide first 15 minutes comes before a wide rest of the day (CONDITIONAL), but the first 15 minutes do not tell you the day's direction, and expiry afternoons are not wilder than other afternoons.**
- **First 15 minutes' direction carrying to the close:** Nifty +0.07% in 2015-17 (t 2.8) and -0.01% in 2018-23; Bank Nifty and liquid stocks the same story. REJECTED: the opening direction is no guide to the close.
- **Last hour extending the move made by 14:30 (both indices, 4,411 days):** +0.03% (t 2.9 and 3.2), a slight lean, below the strict bar: INCONCLUSIVE.
- **A wide 09:15-09:30 range (top third of the last year):** the rest of the day's range averaged 1.64% against 0.96% after a narrow open; held strongly in 2018-23 (t 4.4), weaker in 2015-17 (t 2.0): CONDITIONAL. It predicts how much the day will move, not which way.
- **Expiry-day afternoons (13:30-15:30):** an average 0.40% move, the same as other afternoons: REJECTED.
- **The shape of the day (Nifty 2015-2023, descriptive):** the first 15 minutes move most (22 bp on average) and lean slightly down (-4.7 bp); midday is quietest (7-8 bp per 15 minutes); activity picks up after 14:00 and peaks at 15:00-15:15 (16 bp).
- **What Ananta does with this:** it can say a wide open usually means a wide day, and that the first quarter-hour's direction is not a forecast. No rule changes.

## The rows

Verdicts: VALIDATED and CONDITIONAL would be passes; OPPOSITE means significantly the other way round; INCONCLUSIVE means too few independent blocks (16 needed per period) or a reading below the bar.

| variant | expected | verdict | dev mean | dev t | dev blocks | val mean | val t | val blocks | events dev / val |
|---|---|---|---|---|---|---|---|---|---|
| NIFTY|first15|rest_signed | + | REJECTED | +0.07% | +2.83 | 36 | -0.01% | -0.27 | 72 | 727 / 1477 |
| BANK|first15|rest_signed | + | REJECTED | +0.05% | +1.60 | 36 | -0.02% | -0.68 | 72 | 728 / 1477 |
| STK|first15|rest_signed | + | REJECTED | +0.02% | +0.89 | 35 | +0.04% | +2.74 | 72 | 29184 / 64159 |
| IDX|lasthour|extends | + | INCONCLUSIVE | +0.02% | +2.89 | 36 | +0.04% | +3.22 | 72 | 1456 / 2955 |
| IDX|or15_top|dayrange | + | CONDITIONAL | +0.19% | +1.95 | 30 | +0.45% | +4.45 | 66 | 308 / 991 |
| IDX|expiry_pm|absmove | + | REJECTED | +0.01% | +0.35 | 36 | -0.02% | -0.52 | 72 | 136 / 585 |

## Nifty through the day, 2015-2023 (descriptive, no verdict)

| 15 minutes from | mean move (bp) | mean absolute move (bp) |
|---|---|---|
| 09:15 | -4.73 | 22.1 |
| 09:30 | -1.06 | 13.5 |
| 09:45 | +0.09 | 10.9 |
| 10:00 | -0.34 | 9.4 |
| 10:15 | +0.42 | 9.2 |
| 10:30 | -0.40 | 8.9 |
| 10:45 | -0.60 | 8.0 |
| 11:00 | -0.25 | 8.3 |
| 11:15 | -0.44 | 8.0 |
| 11:30 | -0.27 | 7.9 |
| 11:45 | +0.10 | 7.4 |
| 12:00 | -0.13 | 7.7 |
| 12:15 | +0.19 | 7.4 |
| 12:30 | +0.21 | 8.7 |
| 12:45 | +0.22 | 8.4 |
| 13:00 | -0.09 | 9.0 |
| 13:15 | -0.02 | 8.9 |
| 13:30 | +0.58 | 9.9 |
| 13:45 | -0.25 | 9.8 |
| 14:00 | -0.26 | 10.8 |
| 14:15 | +0.15 | 10.7 |
| 14:30 | -0.76 | 11.5 |
| 14:45 | -0.38 | 10.3 |
| 15:00 | +0.12 | 15.8 |
| 15:15 | +0.08 | 8.5 |
