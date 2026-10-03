# Repair-shop review #5 (Q5): Madhav's reads (pre-registration)

Written 2026-10-03 **before** any run. Source: his SOL buys C1-C4 (`docs/casebook/`), rebuilt from candles the same day.
The question: when the market shows what he saw at those buys, does buying work better than buying a random day?
Four buys inspired these definitions, so on their own they prove nothing. History decides.

- **Data:** UTC daily bars built from our 5m Binance history, lab-10 coins (BTC ETH SOL ADA DOGE AVAX BCH LINK LTC XRP).
  **DISCOVERY** = signals before 2024-01-01. **CONFIRM** = 2024-01-01 to 2026-08-01. The Aug-Sep 2026 holdout is not loaded.
  A forward window that would reach past 2026-08-01 is dropped (no peeking).
- **Point in time:** each read uses only daily bars that closed at or before the signal day. Entry = the next day's open.
- **Costs:** NDAX fee 0.20% + the coin's half-spread, each side (as in every study).
- **Code:** `src/research/reads.py` (the same reader feeds the live app).

## The three reads (all conditions must hold at the day's close)

**M1 Capitulation at the lows** (C1, Jun 5)
1. Location: the day's low is at most 3% above the lowest low of the previous 365 days, and the close is at least 60% under the highest high of the previous 365 days.
2. Long fall: the close was below its 200-day average on at least 90 of the last 100 days.
3. Panic: the coin's daily RSI(14) ≤ 25 and BTC's daily RSI(14) ≤ 30 on the same day.
4. Capitulation volume: the biggest daily volume of the last 3 days ≥ 2.5× the median daily volume of the 90 days before.
- Invalidation (stop): the lowest low of the last 3 days minus 1 daily ATR(14).

**M2 Higher-low retest** (C2 Jun 25, C4 Jun 26)
1. First low: the lowest low of the previous 365 days (L0) was made 8 to 60 days ago.
2. Rally: some daily high since L0 reached at least 10% above L0.
3. Retest: today's low is above L0 (a higher low) and at most 12% above it.
4. Momentum improving: today's daily RSI(14) is at least 10 points above the RSI on L0's day.
- Invalidation (stop): L0 minus 1 daily ATR(14).

**M3 Quiet base after a run** (C3, Aug 10)
1. Base: the last N ≥ 20 daily closes all sit inside a 10% band (highest close / lowest close − 1 ≤ 0.10); N = the longest such run (≤ 120).
2. Prior run: in the 90 days before the base, a low-to-later-high rise of at least 25%.
3. Quiet: mean volume in the base ≤ 0.8× and mean daily range ≤ 0.8× those of the 20 days before the base.
4. Market: BTC's close above its 50-day average (V02).
- Entry a (his C3): the close is in the upper half of the base (between the lowest low and highest high of the base).
- Entry b (classic): the first close above the base's highest high (base measured up to yesterday).
- Invalidation (stop): the base's lowest low minus 0.5 daily ATR(14).

## Variants (7, all reported)

| ID | Read |
|---|---|
| M1a | M1 as written (primary) |
| M1b | M1 without BTC's RSI condition (coin-only panic) |
| M1c | M1 with location relaxed to ≥ 50% under the 52-week high |
| M2a | M2 as written (primary) |
| M2b | M2 plus relative strength: BTC's lowest low of the last 30 days is below BTC's low on L0's day (BTC made a lower low, the coin did not) |
| M3a | M3, entry a (primary) |
| M3b | M3, entry b |

## Counting
- **Episode:** after a read fires on a coin, its further fires on that coin within 20 days belong to the same episode (first fire counts).
- **Independent market event:** episodes of one variant whose signal days are within 10 days of each other (any coins) form one event;
  the event's return is the mean of its episodes. Crypto falls together, so ten coins capitulating on one day are one event, not ten.
- **Excess** = the episode's net return minus the same coin's mean return over all days of the same split for the same holding (drift removed).

## Outcomes
- Primary: 30-day hold, net of costs, excess over the same coin's drift.
- Also reported: 7- and 90-day holds, win rate, the deepest drop within 30 days, and a **managed** version: exit at the read's stop
  if a daily low touches it (at the stop, or at the open if it gaps below), otherwise at the day-30 open (his flexible stop under structure).

## Pass rule (per variant)
- **DISCOVERY:** at least 8 independent events, mean 30-day excess > 0, and t ≥ 1.5 over events.
- **CONFIRM:** at least 3 independent events and mean 30-day excess > 0.
- Status: both pass = **SUPPORTED**; DISCOVERY passes, CONFIRM fails = **NOT_CONFIRMED**; DISCOVERY fails = **NOT_SUPPORTED**;
  too few events in either split = **INSUFFICIENT**.

## What a result changes
- Every read is shown live in the app (Markets and each coin page) with its conditions and its history status, as **evidence**, not a trade rule.
- A SUPPORTED read may raise an alert when it fires, with the AI news check as the last look for blunders.
- No read changes the Explorer's paper trading without Madhav's sentence.
- The thresholds above are frozen for this review; any change is a new variant, counted.
