# Repair-shop review #15 (pre-registration): do the ideas that held up survive the full crypto universe?

Written 2026-10-04, before any full-universe data was run. Madhav's plan: the 10-coin system is the proving ground, the full
100-120 coin history is the research laboratory, live paper is the exam; only what all three agree on goes near the $500 account.

## Question
On the full universe from the lake (Binance Data Vision 1-minute candles, checked, built into daily candles), do these still hold?
1. **T3, the trend portfolio** (review #4): hold coins above their 20- and 50-day averages while Bitcoin is above its 50-day.
2. **H07, the short dip trade** (reviews #13-14): RSI(10) under 30 above the 200-day; sell when RSI(10) is back over 40 or after 10 days.
3. **Madhav's setups** (reviews #5, #8): capitulation (M1a), higher-low retest (M2a), quiet base (M3a), and the retest with the
   market allowed (M2a-G).

## Data and splits (unchanged from the originals)
- Daily candles from the lake: UTC days with at least 97% of their minutes. Discovery: before 2024-01-01. Confirm: 2024-01-01 to
  2026-07-31. The holdout (from 2026-08-01) is not loaded.
- Costs: NDAX 0.20% per side plus half the spread: the measured spread for the lab 10, 0.40% for every other coin (pessimistic,
  so thin coins cannot flatter a result).
- The universe: rule v1 (src/lake/universe.py): Binance USDT pairs including delisted ones; no stablecoins, leveraged or wrapped
  tokens; 12+ months; ranked by median monthly traded value. Chosen before any result, written to reports/universe_v1.json.

## Tiers, each judged separately
- **LAB10**: the same 10 coins from the lake. A data check: the verdicts should match the original reviews. A different verdict
  here means the lake or the old database is wrong, and that is fixed before anything else is read.
- **TOP30** by the universe ranking (the size of the planned 30-50 coin paper tier).
- **ALL**: the whole chosen universe (up to 120).

## Pass rules (the originals, not loosened)
- T3: in both periods, a positive return, a smaller worst fall than buy-and-hold of the same coins, and a better return-to-worst-fall (MAR).
- H07: discovery with 30+ independent market events, mean excess over ordinary uptrend days > 0 with z >= 2.5, and confirm excess > 0.
- Setups: the review #5 verdict (8+ discovery events, 3+ confirm events, mean 30-day excess over the coin's drift > 0 with t >= 1.5
  in discovery, and > 0 in confirm).

## What follows
- A pass on ALL and TOP30 (and the LAB10 check agreeing): the idea is confirmed on full data; it keeps or gains its paper slot.
- A pass on LAB10 only: the idea was specific to our 10 coins; it stays on paper with a note, and is not promoted to live.
- Every variant run is counted here; nothing is tuned after seeing the result. Changes become review #16 with its own pre-registration.
