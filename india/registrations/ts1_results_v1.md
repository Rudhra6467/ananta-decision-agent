# TS1 results: Trailing stop or fixed stop: on the same entries, does a trailing stop beat a fixed one, and does either beat simply holding 20 sessions?

Registered 2026-10-27T00:38:15+00:00 (spec `ts1_v1.json`, written before the run); family stop, k = 116, z = 3.52. Development to 2017, validation 2018-2023; nothing from 2024 on.

## In plain words

**A trailing stop did not beat a fixed stop. It lost to it in every comparison, and nothing passed the strict bar (z 3.52).**
- **2 ATR trailing against 2 ATR fixed, same entries (114,128 entries in 2000-17, 37,513 in 2018-23):** the trailing stop earned 2.38% less per trade in 2000-17 (t -2.6) and 1.77% less in 2018-23 (t -1.8): OPPOSITE. On breakout entries: -1.51% and -1.55%; on pullback entries: -2.49% and -3.04% (t -3.0 and -2.6). A 10% trailing stop against a fixed 7% stop: -1.60% and -0.93%. (The campaigns have breakout, pullback and any-day entries; there is no reversal set.)
- **Why:** a trailing stop is hit almost every time (99% of trades) and the trade ends after 11 days on average, selling strength after the first pullback; the fixed 2 ATR stop is hit on 64% and holds about 32 days. Net per trade: trailing about zero (-0.05% and +0.06%), fixed 2 ATR +2.21% and +1.83%, fixed 7% +1.91% and +1.54%. Part of the fixed stops' lead is simply more time invested in a market that rose; the earlier exit test (E02) found no exit rule beats a time-matched hold, and this does not change that.
- **Against simply selling after 20 sessions:** fixed 7% was +1.24% and +1.20% a trade better (t 2.4 and 1.6) and fixed 2 ATR +1.65% and +1.49% (t 2.2 and 1.8): INCONCLUSIVE, positive but under the strict bar, and they hold twice as long (28-33 days against 15). Trailing 2 ATR against the 20-session sale: -0.73% and -0.28%, OPPOSITE; 10% trailing: -0.36% and +0.27%, REJECTED.
- **The tail:** the 7% fixed stop kept the 5th-percentile trade at -8.3% and -7.4%, against -17.0% and -11.8% for the 2 ATR fixed stop, for a similar average. That is a risk-control argument for a hard stop, not a return edge.
- **What Ananta does with this:** nothing changes in the paper rules (a fixed stop). 'Trail the stop to lock in profit' has no support in 24 years of data here: on these entries it gave back more than it saved. The stored E02 trade files predate the current data and cost settings, so TS1 recomputed all five rules on the same entries with current code; the walk was checked to match the exitlab rules.

## The rows

Verdicts: VALIDATED and CONDITIONAL would be passes; OPPOSITE means significantly the other way round in development and the same way in 2018-23; INCONCLUSIVE means too few independent blocks (16 needed per period) or a reading below the bar.

| variant | expected | verdict | dev mean | dev t | dev blocks | val mean | val t | val blocks | events dev / val |
|---|---|---|---|---|---|---|---|---|---|
| ANY|fixed7_vs_hold20 | + | INCONCLUSIVE | +1.24% | +2.39 | 71 | +1.20% | +1.60 | 23 | 114128 / 37513 |
| ANY|fixed2atr_vs_hold20 | + | INCONCLUSIVE | +1.65% | +2.17 | 71 | +1.49% | +1.75 | 23 | 114128 / 37513 |
| ANY|trail2atr_vs_hold20 | + | OPPOSITE | -0.73% | -3.38 | 71 | -0.28% | -1.36 | 23 | 114128 / 37513 |
| ANY|trail10_vs_hold20 | + | REJECTED | -0.36% | -1.37 | 71 | +0.27% | +0.68 | 23 | 114128 / 37513 |
| ANY|trail2atr_vs_fixed2atr | + | OPPOSITE | -2.38% | -2.64 | 71 | -1.77% | -1.83 | 23 | 114128 / 37513 |
| ANY|trail10_vs_fixed7 | + | OPPOSITE | -1.60% | -2.73 | 71 | -0.93% | -1.72 | 23 | 114128 / 37513 |
| BRK|trail2atr_vs_fixed2atr | + | OPPOSITE | -1.51% | -2.04 | 71 | -1.55% | -1.58 | 23 | 16581 / 5456 |
| PULL|trail2atr_vs_fixed2atr | + | OPPOSITE | -2.49% | -2.97 | 71 | -3.04% | -2.58 | 23 | 14477 / 3767 |

## Mean net return per trade, by rule (same entries)

| variant | rule | dev mean | dev stopped | dev days | dev p5 | val mean | val stopped | val days | val p5 |
|---|---|---|---|---|---|---|---|---|---|
| ANY|fixed7_vs_hold20 | fixed7 | +1.91% | +70.00% | 28.1 | -8.29% | +1.54% | +63.99% | 32.6 | -7.36% |
| ANY|fixed7_vs_hold20 | hold20 | +0.70% | +43.93% | 15.5 | -15.06% | +0.33% | +45.80% | 15.2 | -10.86% |
| ANY|fixed2atr_vs_hold20 | fixed2atr | +2.21% | +64.02% | 32.6 | -17.03% | +1.83% | +64.40% | 32.2 | -11.84% |
| ANY|fixed2atr_vs_hold20 | hold20 | +0.70% | +43.93% | 15.5 | -15.06% | +0.33% | +45.80% | 15.2 | -10.86% |
| ANY|trail2atr_vs_hold20 | trail2atr | -0.05% | +99.13% | 11.2 | -12.57% | +0.06% | +98.97% | 11.4 | -9.08% |
| ANY|trail2atr_vs_hold20 | hold20 | +0.70% | +43.93% | 15.5 | -15.06% | +0.33% | +45.80% | 15.2 | -10.86% |
| ANY|trail10_vs_hold20 | trail10 | +0.32% | +94.77% | 17.2 | -10.31% | +0.59% | +88.40% | 24.3 | -10.09% |
| ANY|trail10_vs_hold20 | hold20 | +0.70% | +43.93% | 15.5 | -15.06% | +0.33% | +45.80% | 15.2 | -10.86% |
| ANY|trail2atr_vs_fixed2atr | trail2atr | -0.05% | +99.13% | 11.2 | -12.57% | +0.06% | +98.97% | 11.4 | -9.08% |
| ANY|trail2atr_vs_fixed2atr | fixed2atr | +2.21% | +64.02% | 32.6 | -17.03% | +1.83% | +64.40% | 32.2 | -11.84% |
| ANY|trail10_vs_fixed7 | trail10 | +0.32% | +94.77% | 17.2 | -10.31% | +0.59% | +88.40% | 24.3 | -10.09% |
| ANY|trail10_vs_fixed7 | fixed7 | +1.91% | +70.00% | 28.1 | -8.29% | +1.54% | +63.99% | 32.6 | -7.36% |
| BRK|trail2atr_vs_fixed2atr | trail2atr | -0.70% | +99.71% | 7.5 | -10.21% | -0.29% | +99.71% | 8.3 | -7.66% |
| BRK|trail2atr_vs_fixed2atr | fixed2atr | +2.04% | +70.01% | 28.1 | -13.74% | +2.27% | +67.71% | 29.5 | -9.94% |
| PULL|trail2atr_vs_fixed2atr | trail2atr | -0.85% | +98.65% | 12.5 | -15.92% | +0.18% | +98.99% | 12.8 | -10.60% |
| PULL|trail2atr_vs_fixed2atr | fixed2atr | +1.08% | +62.60% | 32.9 | -20.76% | +2.27% | +59.78% | 34.2 | -13.64% |
