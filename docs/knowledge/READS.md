# Your setups: Madhav's three buy reads

Built 2026-10-03 from his own SOL buys (`docs/casebook/`). Code: `src/research/reads.py` (one reader for history and live),
live watcher `jarvis/service/reads_watch.py`. Tested in repair-shop review #5 (`docs/repair_shop/REVIEW_5_RESULTS.md`).
Evidence class: **casebook (his own trades)**, tested on history: not supported as stand-alone buy signals.

## The three reads (checked on every coin at each daily close, 8 pm Toronto)

**M1 Capitulation at the lows** (like his Jun 5 buy at 87.67 CAD)
- At or within 3% of the 52-week low, and at least 60% under the 52-week high.
- A long fall: under the 200-day average on at least 90 of the last 100 days.
- Panic: the coin's daily RSI 25 or lower, and BTC's 30 or lower.
- Capitulation volume: one of the last 3 days at 2.5x the 90-day median or more.
- If wrong: stop under the last 3 days' low minus one day's average range.

**M2 Higher-low retest** (like his Jun 25 and Jun 26 buys)
- A 52-week low made 8 to 60 days ago, then a rally of at least 10%.
- Price comes back down but holds above that low (at most 12% above it).
- Momentum better than at the low: daily RSI at least 10 points higher.
- If wrong: stop under the first low.

**M3 Quiet base after a run** (like his Aug 10 buy)
- At least 20 days of closes inside a 10% band, after a run of 25% or more.
- Quieter than before: volume and daily ranges at most 0.8x the 20 days before the base.
- The market allows it: BTC above its 50-day average (V02).
- a: price in the upper half of the base (his entry). b: the first close above the base (the classic breakout).
- If wrong: stop under the base floor.

## What history said (review #5, 2018-2023 tested, 2024-July 2026 confirm)
- The reader fired on the right days for all four of his buys.
- None of the reads beat buying a random day on its own in 2018-2023. Capitulations in 2022 (LUNA, FTX) kept falling.
- Since 2024 all of them did better than average, on few events (quiet base: +12% over average after 30 days, 8 events).
- So: they show **where to look**. Market regime, the news check, buying in steps, a stop under the structure and holding for
  weeks are what turned his reads into +56% to +94%.

## How Ananta uses them
- Markets tab and each coin page: "Your setups" with each condition (found vs needed), SHOWING / 1 SIGN MISSING / NOT NOW.
- The decision chain lists them as evidence, never as a gate.
- The Home feed records each new fire (once per coin and read every 20 days).
- The phone rings only for a read history SUPPORTS (none yet). Madhav can ask to be told about every fire instead.
- The news check (blunder guard) runs when he taps "Check the news" on a coin page: Claude Haiku, about a cent.

## Update: review #8 (with zones and the market gate)
- The **higher-low retest with the market allowed** (BTC above its 50-day) is the most promising read so far: 12 episodes in 2018-23,
  11 up after 30 days, +20% on average (+10.6% over the coin's drift), 2 more since 2024 (one up strongly, one down; +25% on average). One market event short of the
  pre-registered bar, so INSUFFICIENT; it shows live as its own read and every fire is recorded.
- Capitulation never happens with the market allowed; zones did not improve any of the three reads.
