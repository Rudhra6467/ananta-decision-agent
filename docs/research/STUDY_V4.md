# Study v4: market filter and honest drawdown. Pre-registration

Committed **before any fresh-set #2 bar is analysed**. The download only stores bars.

## Why v4

v3's V1_RIDE passed on fresh coins, but post-hoc checks showed:
- Profit depends on rare mega-trends.
- Choppy markets bleed capital: −61% from a 2025-01-01 fresh start.
- The pre-registered drawdown rule was flawed: it was measured against inflated peak equity.

v4 tests a **market-level filter**: only take new trades when Bitcoin's daily trend is up.
It also fixes the drawdown measurement.

## Test data: fresh set #2, never used

- Selection: `FRESH2_SELECTION.json`. A rule-based random draw from Binance USDT pairs listed by mid-2020, **including later-delisted coins**, excluding every coin used before.
- Coins: EOS, HOT, MATIC, NEO, OMG, TCT, TFUEL, THETA, VITE, WTC, XMR, XTZ.
- 5m bars, 2019-01 → 2026-08-31, or until the coin's data ends.
  - At delisting, open positions and buy-and-hold close at the last bar. This is honest about dead coins.
- Market filter input: BTC from `lab5_5m.sqlite`. BTC is not traded here, only read.
- **One run.** A marker file prevents a second run.
- v3's fresh-10 set and the lab-10 set are run as **references only**. They are not evidence.

## Variants (all share v2/v3 definitions: S3 setup, E_DIP limit entry, closed bars only, no lookahead)

- `V1_CONTROL`: V1_RIDE unchanged. This is the replication test of v3 on new coins.
- `V4A_BTC_GATE`: V1_RIDE, but a setup counts only if BTC's **last closed daily bar** has trend UP.
  - Trend UP = close > EMA50 and EMA20 > EMA50.
- `V4B_BTC_GATE_EXIT`: V4A, plus an open position exits at the first daily close (after entry) where BTC's daily trend is not UP. It fills at the next 5m open, whichever of the V1 exits comes first.
- `V4C_HOLD_BTC_GATE`: v3's V3_TREND_HOLD with BTC's daily trend UP required for entry. It exits at the first daily close where the coin's **or** BTC's daily trend is not UP.

## Benchmark

`BH`: $100 buy-and-hold per coin, from its first bar to its last. One round trip of costs.

## Costs

NDAX primary.
- Limit entry: 0.20%.
- Market: 0.20% + 0.40% half-spread (fresh coins).
- Kraken Tier 1 also reported.

## Book and metrics (the fix)

- $100 fixed per coin slot. **Starting capital = $100 × the number of coins** ($1,200 for 12).
- Daily mark-to-market.
- **Max drawdown is measured in dollars against starting capital**: the largest peak-to-trough fall of the $ P&L curve, divided by starting capital. It is no longer a % of inflated peak equity.
- **Fresh-start test:** from every calendar-quarter start with at least 12 months of data after it, compute the 12-month P&L as a % of starting capital. Report the worst and the median.
- Era P&L (% of starting capital):
  - E1: → 2021-12-31
  - E2: 2022–2023
  - E3: 2024 →
- **Score** = total return % ÷ $-max-drawdown %.

## Pass rules (fixed now, NDAX, fresh set #2)

A variant PASSES if all of these hold:
1. n ≥ 50 trades
2. total return > 0
3. $-max-drawdown ≤ 35% of starting capital
4. worst 12-month fresh start ≥ −20% of starting capital
5. score > BH score
6. P&L > 0 in at least 2 of the 3 eras

- If several pass, the highest score becomes the paper proposal. Paper still needs the operator (a PR merge).
- If none passes, that is the v4 result.

## Laws

- Research only. Long only, spot.
- A pass is a proposal, not authority.

---

## Amendment 1 (2026-09-30, engineering only, before any result was seen)

The first `run` on fresh2 (09:35 UTC) crashed while saving the report: numpy booleans are not
JSON-serializable. The crash happened before anything was printed or written (empty output folder,
no `run_done.json` marker), so no fresh2 result was seen. Fix: checks are cast to plain `bool`, and
numpy scalars are converted when saving. No rule, variant, threshold or data changed. The fresh2 set
is then run once, as registered.
