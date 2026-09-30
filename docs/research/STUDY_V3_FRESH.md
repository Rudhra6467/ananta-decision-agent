# Study v3: regime-adaptive exits on fresh coins. Pre-registration

Committed **before any fresh-coin bar is analysed**. The download only stores bars.

## Why v3

The v2 candidate's gross edge was real historically, but it failed the Aug–Sep 2026 holdout:
- 59 of 62 exits were stops.
- Buy-and-hold made +24.7%.
- Tight ATR exits leave strong trends far too early.

v3 keeps the entry idea (trend-up regime, limit-dip entry, 5m timing) and tests exits
that follow the market type, as the operator asked. It is judged at book level against
equal-weight buy-and-hold of the same coins.

## Test data: fresh coins, never used

- Coins: DOT, ATOM, ETC, XLM, TRX, UNI, FIL, NEAR, ALGO, AAVE.
- Source: Binance 5m, via `src/research/fresh_data.py`.
- Window: each coin's first month → 2026-08-31.
- None of these coins was used in v1, v2, the candidate or the holdout.
- **The whole window is one test.** No discovery on these coins.
- **One run only.** A marker file prevents a second run.
- The lab-10 coins are run too, but only as an **in-sample reference**. They were used for everything before and are not evidence.

## Shared definitions

- Daily/4h trend UP = close > EMA50 and EMA20 > EMA50. Same as v2.
- A4 = ATR14 on 4h at the setup.
- Every signal uses closed bars only.
- Market entries and exits fill at the next 5m open.
- Stops are checked on 5m bars and fill at the stop, or at the open if price gapped through it.
- One position per coin. $100 per trade (fixed, no compounding).
- Book = 10 coin slots, $1,000. An unused slot holds cash.

## Variants (4, all reported)

- **`V0_CANDIDATE`**: the frozen v2 candidate, unchanged: S3 trend setup, E_DIP limit entry, X_TRAIL exit. Control.
- **`V1_RIDE`**: same setup and E_DIP entry, but the exit rides the trend:
  - initial stop 2.5 × A4
  - exit at the first daily close below the daily EMA20
  - time stop 60 days
- **`V2_ADAPTIVE`**: same setup and E_DIP entry. The market type at fill time picks the exit:
  - STRONG = daily close > daily EMA20, and daily EMA50 above its value 10 days earlier → V1_RIDE exit.
  - otherwise → V0 X_TRAIL exit.
- **`V3_TREND_HOLD`**: a simple trend filter with no dip, as a reference strategy.
  - Market buy at the first 5m open after a 4h close where daily and 4h trends are UP.
  - Exit at the first daily close where the daily trend is no longer UP.
  - No stop.

## Benchmark

`BH`: $100 buy-and-hold per coin, bought at its first bar and held to the end. One round trip of costs.

## Costs

**Primary: NDAX.**
- Limit entries: 0.20%.
- Market entries and exits: 0.20% + half-spread.
- Fresh-coin half-spread is fixed at **0.40%**. That is conservative: NDAX CAD books are thin, and some of these coins may not be listed there.
- Lab-10 coins use their measured half-spreads.

**Also reported:** Kraken Tier 1 (0.40% limit, 0.80% market, 0.05% slippage per side).

## Book metrics

- Daily mark-to-market equity.
- Total return, max drawdown, MAR (= total return ÷ max drawdown).
- Time in market.
- Trades n, win rate, mean net per trade.
- Per era:
  - E1: start → 2021-12-31
  - E2: 2022–2023 (the bear market)
  - E3: 2024 → 2026-08-31

## Pass rules (fixed now, NDAX costs, fresh coins)

A variant **PASSES** if all of these hold:
1. n ≥ 50 trades
2. book total return > 0
3. MAR > BH MAR
4. max drawdown ≤ 0.6 × BH max drawdown
5. book return > 0 in at least 2 of the 3 eras

Rationale: a trend strategy rarely beats buy-and-hold on raw return in a bull market.
Its job is to keep most of the upside while avoiding much of the crash. Rules 3 and 4 test exactly that.

If more than one variant passes, all are reported. The one with the highest MAR becomes
the paper proposal, and paper still needs an operator sentence.

If none passes, that is the v3 result.

## Laws

- Research only.
- Nothing here can issue a TAKE.
- Shorts are out of scope: long only, spot.
