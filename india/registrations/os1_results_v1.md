# OS1 results: Option spreads: for the same intraday index trade, does a debit spread (buy the at-the-money option, sell one 1-2 strikes further out) do better than buying the single option, overall and when the fear gauge is high?

Registered 2026-10-27T13:26:40+00:00 (spec `os1_v1.json`, written before the run); family options_eod, k = 38, z = 3.21. Development to 2017, validation 2018-2023; nothing from 2024 on.

## In plain words

**For Ananta's kind of trade (an intraday index move), a debit spread was much worse than buying the single option: OPPOSITE in development and validation.**
- **Candidate SP1 trades, entry 15 or 30 minutes after the open, ATR-stop or 15:15 exit (11,552 in 2015-17, about 23,450 in 2018-23):** the single at-the-money option made +4.1% a trade on its premium; selling the next strike out made it -18.5% a trade on the net debit (spread1), selling two strikes out -8.6% (spread2). In rupees per lot: -232 against +172 (2015-17 difference -283, t -15.5; 2018-23 -470, t -12.0). Win rate 25% against 44%.
- **When India VIX was above 18:** the same, -19.5% against +4.5% a trade; INCONCLUSIVE only because 2015-17 holds just 15 high-VIX months.
- **Why:** on a same-day index trade the option moves only a little, so the sold option takes away much of the gain while adding a second set of bid-ask spreads and charges on a smaller debit. The cheaper premium does not make up for it. SP1's own policy trades 2017-23 (descriptive): single +4.7%, spread1 -19.0%, spread2 -7.9% a trade.
- **What Ananta does with this:** the options line keeps one plain lot. A spread is a tool for multi-day views with a target, which this study did not test.

## The rows

Verdicts: VALIDATED and CONDITIONAL would be passes; OPPOSITE means significantly the other way round; INCONCLUSIVE means too few independent blocks (16 needed per period) or a reading below the bar.

| variant | expected | verdict | dev mean | dev t | dev blocks | val mean | val t | val blocks | events dev / val |
|---|---|---|---|---|---|---|---|---|---|
| ALL|spread1|ret | + | OPPOSITE | -20.47% | -29.54 | 36 | -23.87% | -35.88 | 72 | 11552 / 23444 |
| ALL|spread2|ret | + | OPPOSITE | -10.86% | -27.64 | 36 | -13.73% | -31.75 | 72 | 11550 / 23446 |
| HIVIX|spread1|ret | + | INCONCLUSIVE | -21.49% | -14.26 | 15 | -23.56% | -20.42 | 41 | 2032 / 9022 |
| HIVIX|spread2|ret | + | INCONCLUSIVE | -10.92% | -11.19 | 15 | -13.23% | -17.55 | 41 | 2032 / 9014 |
| ALL|spread1|rs | + | OPPOSITE | -283.18 | -15.54 | 36 | -469.67 | -12.05 | 72 | 11552 / 23474 |
| HIVIX|spread1|rs | + | INCONCLUSIVE | -189.37 | -3.78 | 15 | -492.80 | -6.08 | 41 | 2032 / 9042 |

## Means per trade and SP1's policy trades (descriptive)

| variant | spread mean | single mean | spread win rate | single win rate | policy trades n | policy spread mean | policy single mean |
|---|---|---|---|---|---|---|---|
| ALL|spread1|ret | -18.52% | +4.11% | +25.25% | +44.23% | 2541 | -18.95% | +4.72% |
| ALL|spread2|ret | -8.64% | +4.05% | +35.37% | +44.21% | 2541 | -7.91% | +4.72% |
| HIVIX|spread1|ret | -19.54% | +4.49% | +24.71% | +44.56% | 2541 | -18.95% | +4.72% |
| HIVIX|spread2|ret | -8.93% | +4.44% | +35.67% | +44.54% | 2541 | -7.91% | +4.72% |
| ALL|spread1|rs | -232.39 | +171.54 | +25.26% | +44.22% | 2542 | -221.29 | +230.48 |
| HIVIX|spread1|rs | -240.38 | +262.82 | +24.76% | +44.56% | 2542 | -221.29 | +230.48 |
