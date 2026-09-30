# Entry study v2: pre-registration

Written and committed **before any v2 result is looked at**. v2 is a new study, not a
retune of v1. v1 found no edge at 5m horizons with 1h-ATR exits (0/108), and a real
round trip of 0.9–1.7%. v2 tests the direction v1 pointed to:

- fewer trades
- larger moves (≥ 3% targets)
- setups on 4h with daily context
- 5m used only to time the entry
- limit (maker) entries where possible

## Data and splits

Identical to v1:
- `lab5_5m.sqlite`, 10 coins, higher timeframes built from 5m (complete UTC buckets).
- DISCOVERY: → 2023-12-31
- CONFIRM: 2024-01-01 → 2026-07-31
- HOLDOUT: 2026-08-01 → 2026-09-12

The holdout is still unused: v1 never ran it.

## No-lookahead

- A 4h setup is known only at its 4h close.
- Daily context uses the last closed daily bar.
- 5m timing uses only 5m bars after the setup close.
- Limit fills need price to trade **through** the limit (low < limit for a buy).
- On a limit-fill bar, a stop in that same bar is assumed hit (pessimistic), and a target is not allowed until the next bar.
- Market entries fill at the next 5m bar's open.
- If a stop and a target are hit in the same bar, the stop is assumed.

## Market type

- Daily trend: UP = close > EMA50 and EMA20 > EMA50; DOWN = mirror; else RANGE.
- 4h trend: same rule on 4h.

## 4h setups (LONG shown; SHORT is the exact mirror)

- `S1 TREND_PULLBACK`: daily UP and 4h UP, and one of the last 2 closed 4h bars had low ≤ 4h EMA20, and the latest 4h close > 4h EMA20.
- `S2 BREAKOUT`: 4h close > highest high of the prior 30 4h bars (5 days), 4h volume ≥ 1.5× mean of the prior 30, and daily trend not DOWN.
- `S3 TREND_CONTROL` (baseline): daily UP and 4h UP, a new setup each time a 4h bar closes in that state and no position is open. It shows what "just be long in an uptrend" earns.

A setup stays armed for 24h after its 4h close. One entry per setup at most.

## 5m entry timing

- `E_NOW`: market entry at the first 5m open after the setup close. Taker.
- `E_DIP`: limit buy at setup close − 0.5 × ATR4h, resting for up to 24h. Maker. No fill means no trade.
- `E_RECLAIM`: first 5m pullback-reclaim (v1 T2 rule) inside the 24h window. Market entry. Taker.

## Exits

A = 4h ATR14 at the setup.

- `X_TARGET`: stop 1.5A, target 3.0A (maker), time stop 7 days.
- `X_TRAIL`: stop 1.5A; after +1.5A, trail 2.5A from the best price; time stop 14 days.

**Minimum-move rule (fixed):** skip the setup unless 3.0A / entry price ≥ 3.0%.

## One position per coin per variant

## Variants

3 setups × 3 timings × 2 exits × 2 directions = **36 variants**, all reported.

## Costs

Same four scenarios as v1. Maker entry applies only to E_DIP. Target exits are maker; stop and time exits are taker. 0.05% slippage per side.

| Scenario | Maker | Taker |
|---|---|---|
| KRAKEN_T1 | 0.40% | 0.80% |
| KRAKEN_T3 | 0.22% | 0.38% |
| LOW_FEE (reference) | 0.045% | 0.045% |

- **Primary:** `KRAKEN_T1` real mix (maker where it applies, taker otherwise).
- **Also reported:** all-taker T1, T3, and LOW_FEE.

## Pass rules (fixed now)

- **DISCOVERY**, primary cost, pooled over the 10 coins:
  - n ≥ 100
  - mean net > 0
  - profit factor ≥ 1.15
  - t ≥ 2.5 (36 tries)
  - net positive on ≥ 6 coins
- **CONFIRMED**: n ≥ 50, mean net > 0 and profit factor ≥ 1.05 on CONFIRM, with nothing changed.
- **HOLDOUT**: CONFIRMED variants only, run once, reported as is.
- If nothing passes, that is the v2 result. Nothing is relaxed after the fact.

## Laws

- Research only.
- A CONFIRMED variant becomes a proposal; paper use needs an operator sentence.
- Shorts are measured, but are not tradeable for the operator today (Canada / Ontario).
