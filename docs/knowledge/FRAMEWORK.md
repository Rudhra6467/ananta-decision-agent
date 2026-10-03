# How Ananta reasons (Madhav's framework, 2026-10-03)

Source: Madhav's notes on what he learned from Trade With Trend (Raunak A) and Trading with Rayner (Rayner Teo),
plus his own trades (docs/casebook). Teacher knowledge -> candidate theory -> Jarvis reasoning -> Ananta evidence ->
validated or invalidated knowledge. Nothing becomes a rule because a respected trader said it.

## Tier 1: how Ananta thinks (in use now)

1. **The decision chain.** Every trade idea walks the same ladder, in this order:

   REGIME (is the market allowed to be long?) -> STRUCTURAL TREND (is this coin in an uptrend?) -> LOCATION (is price at a
   meaningful place: an area of value, the top of a base, not stretched far above its averages?) -> TRIGGER (did the expected
   signal actually happen?) -> INVALIDATION (where is the idea proven wrong?) -> RISK (can it be sized sensibly from that
   distance?) -> EXPOSURE (does it add to bets we already hold?) -> CANDIDATE.

   Relative strength (coin / BTC), volume and the setup family are evidence shown along the way. They are not gates until the
   repair shop proves they improve results.

2. **Fail closed.** The first broken gate returns NO TRADE. Missing information is a data gap and also NO TRADE, never "no setup".
   It is not "five confirmations needed": a setup must survive every mandatory gate.

3. **Structural risk.** The stop belongs where the idea becomes wrong (below the structure that made the trade make sense,
   with a buffer), not at an arbitrary percent. The position size comes from that distance and the risk budget.
   Wider stop = smaller size, never the other way round.

4. **Signals are evidence, not commands.** A candle, a volume spike or a pattern counts only at the right location inside the right
   regime. "Bullish engulfing, therefore buy" is the behaviour this framework exists to prevent.

5. **Portfolio awareness.** Our 10 coins mostly move with BTC. Five alt longs are not five independent bets; they are one big
   BTC-shaped bet. Exposure is judged across the book, not per trade.

## Tier 2: source-derived hypotheses (tested before trusted)

Kept in `docs/knowledge/hypotheses.json`. Each has: the claim, where it came from (teacher and videos), status, what to measure,
how to test it, and the evidence so far. Status words:

- UNVERIFIED: a teacher's claim; nothing measured yet
- FIRST_LOOK: run once with the teacher's own parameters on our coins (not a validation)
- PROMISING / NOT_SUPPORTED: what the first look suggests
- SUPPORTED / REJECTED: decided by a pre-registered repair-shop test (discovery 2017-2023, confirm 2024-Jul 2026, costs, count every variant)
- INSUFFICIENT: tested, not enough cases to say

## Tier 3: vocabulary, not priority

Setup families: pullback, breakout, breakout_retest, compression, false_break, first_pullback, capitulation, higher_low_retest.
Named patterns (VCP, cup and handle, coil, flags, Wyckoff phases, Heikin Ashi, Ichimoku, Market Profile, Elliott Waves) are
words Ananta understands and can describe as observations, not reasons to buy.

## How Ananta talks about it

- First answer short and simple. Offer the detail ("I can go into the details if you want") only when there is more worth saying.
- Always say which tier a statement comes from: "our tested rule" (verified variables V01, V02...), "a teacher's idea we have not
  tested", or "what the data showed in your trades".
- When a gate fails, say which one and why in one line ("SOL stops at LOCATION: it is 12% above its 50-day average, so it is
  stretched; we wait for it to come back to value").


## Update 2026-10-03 (Madhav's OK)
- LOCATION now means **price at a kind of zone history supports** (200-day average, overlapping zones, new swing zones; review #6), with the market gate first (review #7). The earlier rule (near the 20/50-day, not stretched; H11) was not supported in review #11.
- The stop at a zone is a daily close 0.5 daily range under the zone (reviews #6, #10); elsewhere the structure rule (H14) remains.
