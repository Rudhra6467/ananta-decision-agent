# Multi-timeframe entry study v1: pre-registration

Written and committed **before any result is looked at**. The commit time is the
pre-registration stamp. Anything changed after results are seen is a new version
(v2) and must say so.

Operator request 2026-09-29: rebuild the entry on history up to July 2026.
- 5m trigger
- 15m + 1h confirmation
- 4h decides the market type
- long and short measured separately
- Kraken fees and low fees
- then one final check on Aug–Sep 2026
- use real charges

## Data

- Source: `lab5_5m.sqlite` (Binance 5m klines, 10 coins, 2017→2026-09-12), read-only.
- Higher timeframes are built from 5m, UTC-aligned, complete buckets only.
- Splits (research law discovery end = 2026-08-01T00:00Z):
  - **DISCOVERY**: first bar → 2023-12-31 23:55Z. Used to choose.
  - **CONFIRM**: 2024-01-01 → 2026-07-31 23:55Z. Used once per survivor, no retuning.
  - **HOLDOUT (Set B)**: 2026-08-01 → 2026-09-12. Used once, at the end, only for CONFIRMED variants.
- A trade belongs to the split of its **entry** bar. A trade entered in a split may
  not exit in the next split: it is force-closed at the split's last bar.

## No-lookahead rules

- A signal on the 5m bar that **closed** at time t may use only 15m/1h/4h bars whose
  close is ≤ t.
- Entry is at the **next** 5m bar's open.
- Exits are simulated on 5m bars after entry. If stop and target are both touched
  in one bar, the **stop** is assumed. A gap through the stop fills at the bar open.

## 4h market type (last closed 4h bar)

- Trend
  - UP = close > EMA50 and EMA20 > EMA50
  - DOWN = close < EMA50 and EMA20 < EMA50
  - else RANGE
- Volatility: ATR14/close percentile over the last 180 4h bars
  - HIGH ≥ 70th
  - LOW ≤ 30th
  - else NORMAL

## Confirmation (last closed bar of each timeframe)

- LONG confirm on a timeframe = close > EMA20 and EMA20 rising over 3 bars. SHORT is the mirror.
- Modes:
  - `C0` = none (control)
  - `C1` = 1h confirms
  - `C2` = 1h and 15m confirm

## 5m triggers (LONG shown; SHORT is the exact mirror)

- `T1 BREAKOUT`: close > highest high of the prior 24 bars (2h), and volume ≥ 2× mean volume of the prior 48 bars.
- `T2 PULLBACK_RECLAIM`: within the prior 6 bars a low touched the 15m EMA20; the previous bar closed ≤ 5m EMA20; this bar closes > 5m EMA20 and is a green candle.
- `T3 SQUEEZE_RELEASE`: the previous bar's 5m Bollinger(20, 2) width is in the lowest 20% of the last 288 bars (1 day), and this bar closes above the upper band.

## Regime gate

- `G0` = no gate (control)
- `G1` = direction must match the 4h trend: LONG only in UP, SHORT only in DOWN

## Exits

Sized on the 1h ATR14 at entry (A).

- `X1 FIXED`: stop 1.0A, target 2.0A, time stop 24h.
- `X2 TREND`: stop 1.0A; once +1.0A in profit, trail 1.5A from the best price; time stop 72h.
- `X3 ADAPTIVE`: if the 4h trend matches the direction, use X2. Otherwise (range or counter-trend) use stop 1.0A, target 1.5A, time stop 12h.

## One position per coin per variant

A new signal is ignored while that variant already holds that coin.

## Variants

3 triggers × 3 confirmations × 2 gates × 3 exits × 2 directions = **108 variants**,
pooled over the 10 coins. All 108 are reported, whatever the result.

## Real charges (checked 2026-09-29, Kraken Pro Canada, since 2026-07-09)

| Scenario | Entry | Target exit | Stop / time exit | Slippage (per side) |
|---|---|---|---|---|
| `KRAKEN_T1_TAKER` | 0.80% | 0.80% | 0.80% | 0.05% |
| `KRAKEN_T1_MAKER` (limit entry and target, market stop) | 0.40% | 0.40% | 0.80% | 0.05% |
| `KRAKEN_T3` ($10k/30d volume or $20k held) | 0.22% | 0.22% | 0.38% | 0.05% |
| `LOW_FEE` (Hyperliquid-level taker, reference only; not available in Ontario) | 0.045% | 0.045% | 0.045% | 0.05% |

`KRAKEN_T1_MAKER` is **primary**. It assumes limit orders fill at the next bar's open,
which is optimistic, and this is stated in the results.

## Pass rules (fixed now)

- **DISCOVERY pass**, at the primary cost, pooled over coins:
  - n ≥ 200 trades
  - mean net return per trade > 0
  - profit factor ≥ 1.15
  - t-stat of per-trade net ≥ 3.0 (strict because of 108 tries)
  - net positive on ≥ 6 of 10 coins
- **CONFIRMED**: a discovery survivor that, on CONFIRM with no changes, has n ≥ 100, mean net > 0 and profit factor ≥ 1.05.
- **HOLDOUT**: CONFIRMED variants run once on Aug–Sep 2026. Reported as is. Not retuned.
- If nothing passes, that is the result. Nothing is relaxed after the fact in v1.

## Also reported (diagnostics, never used to choose)

- Every variant at every cost scenario, by split and by coin.
- Per market-type cell (4h trend × vol) mean net per trade, for LONG and SHORT.
- Break-even: for every raw trigger, the best favourable move (MFE) within 24h,
  compared with each cost scenario's round-trip cost. This answers
  "how big must a move be to beat the charges".

## Laws kept

- Research-time only. Nothing here can issue a TAKE.
- A CONFIRMED variant becomes a proposal. Paper trading needs its own operator sentence.
- Shorting is measured but not tradeable at present: Kraken futures are unavailable
  in Canada, and Hyperliquid restricts Ontario.
