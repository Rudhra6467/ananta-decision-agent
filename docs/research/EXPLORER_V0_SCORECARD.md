# Explorer v0: first scorecard (history replay of Rulebook v0)

The same engine the live Explorer runs (`explorer_engine.py`, commit 8a6daed) was fed 2017–July 2026 of closed 5m bars for the lab-10 coins.
- Splits: **DISCOVERY** before 2024-01-01; **CONFIRM** 2024-01-01 to 2026-08-01. The **HOLDOUT** (Aug–Sep 2026) was not loaded.
- $100 per trade, NDAX costs: limit entries 0.20%, market exits 0.20% plus half-spread.
- 5,513 real trades and 137,547 shadow trades: random entries, NO_TYPE and rejected candidates, and "chase" versions of missed limit orders.

This is **v0 as written**: loose on purpose. The scorecard's job is to show which rules to fix first.

## Headline

| | DISCOVERY (2017–2023) | CONFIRM (2024–Jul 2026) |
|---|---|---|
| Real trades | 3,698 | 1,815 |
| Win rate | 32.1% | 29.7% |
| Mean net per $100 trade | −$0.63 | −$0.61 |
| Mean R | −0.02 | −0.00 |
| Paper account ($2,000) | −$2,342 (wiped out) | −$1,114 (−56%) |
| Random entries, same exits and costs | −$0.38 | −$0.60 |

**Before costs, v0 is roughly break-even** (mean R ≈ 0). The loss equals the costs.
- In CONFIRM, the setups do no better than random entries.
- In DISCOVERY they do worse. The random LONG_TERM entries even made money there: +$0.32 per trade from the 2019–2021 bull drift.

## Rule by rule (mean net per trade, DISCOVERY / CONFIRM)

| Rule | DISCOVERY | CONFIRM | Read |
|---|---|---|---|
| E1 trend pullback | −$0.96 (n 206) | −$0.51 (n 96) | worst in DISCOVERY |
| E2 breakout | −$0.51 (n 1,427) | −$0.58 (n 718) | least bad large setup |
| E3 bounce from support | −$0.03 (n 26) | none | fires too rarely to judge |
| E4 momentum continuation | −$0.72 (n 1,471) | −$0.65 (n 686) | worst large setup; E4 INTRADAY −$0.67 / −$0.71 |
| E5 squeeze release | −$0.63 (n 568) | −$0.67 (n 308) | |
| G1 LONG_TERM | −$1.22 | −$0.52 | **worse than random LONG_TERM** in DISCOVERY |
| G2 SHORT_TERM | −$0.58 | −$0.61 | |
| G3 INTRADAY | −$0.60 | −$0.62 | |
| S3 reversal CONFIRMED | −$1.08 | −$0.59 | the 30m confirmation does **not** help |
| Market state S1 BEAR vs BULL | −$0.54 vs −$0.65 | −$0.43 vs −$0.64 | buying in BULL is not better |
| 5m green run ≥ 3 at entry | no difference | no difference | agrees with the green-run study |
| Expensive coins (half-spread > 0.30%) | −$0.73 vs −$0.54 | −$0.66 vs −$0.56 | costs show up as expected |

## Exits (the same trades, different exits)

| Exit set | DISCOVERY | CONFIRM |
|---|---|---|
| The assigned type (actual) | −$0.63 | −$0.61 |
| As LONG_TERM | −$0.59 | −$0.89 |
| As SHORT_TERM | −$0.56 | −$0.62 |
| As INTRADAY | −$0.61 | −$0.61 |
| **HOLD** (no bells, time cap only) | **+$1.59** | −$0.56 |

- The **warning bells (X3)** exit at a loss almost every time: −$0.90 to −$2.25 per trade, 0–12% winners.
  - In the bull years, holding beat the bells by a wide margin.
  - In 2024–2026 the bells and holding are about equal.
- The bells are not yet adding value.

## The biggest lesson: limit orders pick the worse trades

| | DISCOVERY | CONFIRM |
|---|---|---|
| Filled limit orders (real trades) | −$0.63, 32% winners | −$0.61, 30% winners |
| **Missed** limit orders, bought at market instead ("chase") | **−$0.17, 55% winners** | **−$0.29, 52% winners** |

- A limit order below the price fills most often when the price keeps falling. When the price runs away, it never fills.
- So N1 ("limit orders only") saves the spread but **selects the losing trades**. This is the first thing v1 should test.

## Crisis replays (R6): bells vs holding to the time cap

| Crisis | Trades | With bells | Held to cap | Bells saved |
|---|---|---|---|---|
| COVID 2020 | 42 | −$63.78 | −$19.49 | −$44.29 (a fast rebound: the bells sold the bottom) |
| May 2021 | 44 | +$13.38 | −$243.02 | **+$256.40** |
| LUNA / 3AC 2022 | 134 | −$100.00 | −$158.28 | +$58.29 |
| FTX 2022 | 36 | −$20.08 | −$109.14 | +$89.06 |
| August 2024 | 22 | −$5.96 | +$30.49 | −$36.45 (a fast rebound) |
| October 2025 | 8 | +$2.67 | −$54.21 | +$56.88 |

- No stop filled through a gap in any crisis window: with 5m execution, stops fill at their level.
- The BTC-crash disaster exit (X2) fired once. Crashes were spread over several hours rather than one 1h candle.
- Bells help most in slow crashes (May 2021, LUNA, FTX, October 2025) and hurt in V-shaped rebounds (COVID, August 2024).

## Proposals for the first repair-shop review (max 3, to be written down before testing)

1. **Entry method:** test market entry (or a limit much closer to the price) for E2 and E4, because the missed chases beat the fills in both splits.
2. **Warning bells:** test the X3 bells against a looser version (only the disaster stop and the time cap), since the bells lose to holding or tie.
3. **Retire or rebuild E4 INTRADAY and the LONG_TERM gate:** E4 INTRADAY is the worst large cell in both splits, and G1 LONG_TERM underperforms random long-term entries.

Each proposal is tested on DISCOVERY first, then CONFIRM, and runs as a paper shadow before the operator decides.
