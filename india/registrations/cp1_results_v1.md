# CP1 results: Candlestick patterns: do a hammer or a bullish engulfing after a fall, or a bearish engulfing or a doji after a rise, predict the next 5-20 sessions on liquid stocks?

Registered 2026-10-27T13:26:30+00:00 (spec `cp1_v1.json`, written before the run); family technical, k = 46, z = 3.27. Development to 2017, validation 2018-2023; nothing from 2024 on.

## In plain words

**No candlestick pattern is a usable signal on liquid Indian stocks. Nothing passed the bar (z 3.27); the directions mostly match the textbook, but the effects are small and do not hold in both periods.**
- **Hammer after a fall (14,079 events in 2000-17, 4,381 in 2018-23):** next 5 sessions +0.11% and +0.20% against ordinary days (REJECTED); next 20 sessions +0.62% (t 2.4) and +0.31% (t 0.8): INCONCLUSIVE, under the bar and fading.
- **Bullish engulfing after a fall (9,052 / 3,046):** -0.13% and +0.16% over 5 sessions, +0.28% and +0.63% over 20: REJECTED.
- **Bearish engulfing after a rise (19,498 / 6,478):** -0.42% (t -2.4) and -0.17% over 20 sessions: INCONCLUSIVE. **Doji after a rise (24,125 / 7,676):** -0.28% and -0.30%: INCONCLUSIVE. Both lean the textbook way, too weakly to use.
- **As trades after costs (buy the next open, sell 20 sessions later):** hammer +1.56% and +0.93% a trade, bullish engulfing +1.21% and +1.28%, both INCONCLUSIVE; most of that is the market's own rise over 20 sessions, as the rows against ordinary days show.
- **What Ananta does with this:** nothing changes. A hammer or an engulfing candle can be described on a chart; it is not a reason to buy or sell.

## The rows

Verdicts: VALIDATED and CONDITIONAL would be passes; OPPOSITE means significantly the other way round; INCONCLUSIVE means too few independent blocks (16 needed per period) or a reading below the bar.

| variant | expected | verdict | dev mean | dev t | dev blocks | val mean | val t | val blocks | events dev / val |
|---|---|---|---|---|---|---|---|---|---|
| STK|hammer|fwd5 | + | REJECTED | +0.11% | +0.98 | 70 | +0.20% | +1.00 | 24 | 14079 / 4381 |
| STK|hammer|fwd20 | + | INCONCLUSIVE | +0.62% | +2.37 | 70 | +0.31% | +0.76 | 24 | 14079 / 4381 |
| STK|bullengulf|fwd5 | + | REJECTED | -0.13% | -0.87 | 70 | +0.16% | +0.75 | 24 | 9052 / 3046 |
| STK|bullengulf|fwd20 | + | REJECTED | +0.28% | +1.11 | 70 | +0.63% | +2.02 | 24 | 9052 / 3046 |
| STK|bearengulf|fwd20 | - | INCONCLUSIVE | -0.42% | -2.41 | 70 | -0.17% | -0.80 | 24 | 19498 / 6478 |
| STK|doji_rise|fwd20 | - | INCONCLUSIVE | -0.28% | -1.93 | 70 | -0.30% | -1.58 | 24 | 24125 / 7676 |
| STK|hammer|trade20 | + | INCONCLUSIVE | +1.56% | +2.17 | 70 | +0.93% | +0.88 | 24 | 14079 / 4381 |
| STK|bullengulf|trade20 | + | INCONCLUSIVE | +1.21% | +1.94 | 70 | +1.28% | +1.61 | 24 | 9052 / 3046 |
