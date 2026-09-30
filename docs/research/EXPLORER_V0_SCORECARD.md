# Explorer v0: first scorecard (history replay of Rulebook v0)

The same engine the live Explorer runs (`explorer_engine.py`, commit 767eb56) was fed 2017–July 2026 of closed 5m bars for the lab-10 coins.
- Splits: **DISCOVERY** before 2024-01-01; **CONFIRM** 2024-01-01 to 2026-08-01. The **HOLDOUT** (Aug–Sep 2026) was not loaded.
- $100 per trade, NDAX costs: limit entries 0.20%, market exits 0.20% plus half-spread.
- Shadows as well as real trades: random entries, NO_TYPE and rejected candidates, "chase" versions of missed limit orders, and every real trade under the other exit sets.

> **Correction (same day).** The first run (commit 8a6daed) kept a trade's slot busy until its shadow exit variants finished, up to 60 days. This wrongly rejected about half the real trades. Fixed in 767eb56, with a regression test. The numbers below are from the corrected run; the first run's conclusions held.

This is **v0 as written**: loose on purpose. The scorecard's job is to show what to fix first.

## Headline

| | DISCOVERY (2017–2023) | CONFIRM (2024–Jul 2026) |
|---|---|---|
| Real trades | 7,329 | 3,221 |
| Win rate | 33.4% | 29.3% |
| Mean net per $100 trade | −$0.38 | −$0.62 |
| Mean R | +0.04 | −0.02 |
| Paper account ($2,000) | −$2,815 (wiped out) | −$1,982 (−99%) |
| Random entries (short-term / intraday), same exits and costs | −$0.58 / −$0.60 | −$0.60 / −$0.68 |

- **Before costs, v0 is about break-even. The costs are the loss.**
- In DISCOVERY, v0 beats random entries slightly, carried by the 2019–2021 bull market in long-term trades.
- In CONFIRM, it doesn't beat random entries.

## Rule by rule (mean net per trade, DISCOVERY / CONFIRM)

| Rule | DISCOVERY | CONFIRM | Read |
|---|---|---|---|
| E1 trend pullback | −$0.27 (n 785) | −$0.94 (n 337) | falls apart in CONFIRM |
| E2 breakout | −$0.57 (n 2,120) | −$0.65 (n 998) | consistently negative |
| E3 bounce from support | +$0.36 (n 30) | none | fires too rarely to judge |
| E4 momentum continuation | −$0.24 (n 3,498) | −$0.47 (n 1,448) | least bad large setup |
| E5 squeeze release | −$0.64 (n 896) | −$0.80 (n 429) | worst in both |
| G1 LONG_TERM | **+$0.35** (n 1,678) | −$0.45 (n 762) | positive only in the bull years; random LONG_TERM was +$0.32 there too |
| G2 SHORT_TERM | −$0.65 | −$0.78 | |
| G3 INTRADAY | −$0.58 | −$0.62 | costs dominate, as the 5m studies predicted |
| S3 reversal EARLY vs CONFIRMED | +$0.58 vs −$0.72 | −$1.35 vs −$0.48 | flips between periods: noise |
| S1 BEAR vs BULL | −$0.52 vs −$0.37 | −$0.42 vs −$0.63 | no stable difference |
| Expensive coins (half-spread > 0.30%) | −$0.49 vs −$0.28 | −$0.74 vs −$0.45 | costs show up as expected |

## Exits (the same trades, different exits)

| Exit set | DISCOVERY | CONFIRM |
|---|---|---|
| The assigned type (actual) | −$0.38 | −$0.62 |
| As LONG_TERM | −$0.34 | −$0.81 |
| As SHORT_TERM | −$0.52 | −$0.64 |
| As INTRADAY | −$0.59 | −$0.63 |
| **HOLD** (no stop, no bells, time cap only) | **+$7.43** | **+$1.04** |

- **Holding to the time cap made money in both periods; every bell-based exit set lost.**
  - Most of it likely comes from 60-day holds of LONG_TERM trades riding the market's drift.
  - A **random-entry HOLD baseline** is needed before this means anything. It is the first addition for v0.2.
- The **warning bells (X3)** exit at a loss almost every time: 0–14% winners, −$0.91 to −$3.12 per trade.
- Winning exits come from **targets** (+$1.61 to +$1.98) and above all **LONG_TERM trailing stops** (+$8.65 to +$11.68 per trade).

## Limit orders pick the worse trades

| | DISCOVERY | CONFIRM |
|---|---|---|
| Filled limit orders (real trades) | −$0.38, 33% winners | −$0.62, 29% winners |
| **Missed** limit orders, bought at market instead ("chase") | **+$0.07, 57% winners** | **−$0.32, 51% winners** |

A limit order below the price fills most often when the price keeps falling, and misses when it runs up. N1 saves the spread but **selects the losers**.

## Crisis replays (R6): bells vs holding to the time cap

| Crisis | Trades | With bells | Held to cap | Bells saved |
|---|---|---|---|---|
| COVID 2020 | 75 | −$74 | −$54 | −$21 (a V-shaped rebound) |
| May 2021 | 121 | −$157 | −$1,548 | **+$1,391** |
| LUNA / 3AC 2022 | 214 | −$182 | −$388 | +$206 |
| FTX 2022 | 67 | −$85 | −$606 | +$520 |
| August 2024 | 36 | −$8 | +$35 | −$43 (a V-shaped rebound) |
| October 2025 | 15 | −$8 | −$256 | +$248 |

- The bells are a **crash insurance**: they cost money in normal times and in V-shaped rebounds, and they saved $2,365 in the four slow crashes.
- The disaster exits (X2) fired 111 times in DISCOVERY; no stop filled through a gap.

## Proposals for the first repair-shop review (max 3, written down before testing)

1. **Entry method:** test market entry, or a limit much closer to the price, because the missed chases beat the fills in both periods.
2. **Exits:** replace the X3 warning bells with "disaster stop + trailing stop + time cap". Keep crash insurance through X1/X2, and measure it with the crisis replays. Add the random-entry HOLD baseline first.
3. **Setups:** drop E5 (worst in both periods) and put E2 on probation. Test whether E4 LONG_TERM, the least-bad combination, beats a random LONG_TERM entry.

Each proposal is tested on DISCOVERY first, then CONFIRM, and runs as a paper shadow before the operator decides.
