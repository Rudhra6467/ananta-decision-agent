# Review #14: the short dip trade (H07) against a fair baseline (results)

Pre-registration `REVIEW_14.md` (1408733); code ecea2b1 / b282f5c; run 2026-10-03 17:00 UTC. Output: `~/ananta_runs/teachers2/review14_results.json`.

| Variant | Status | 2018-23: trades (events), net, won, baseline, **excess**, z | 2024-Jul 2026: trades (events), net, won, baseline, **excess**, z |
|---|---|---|---|
| **H07** above the 200-day, RSI(10) under 30 | INSUFFICIENT | 44 (25), +4.1%, 70%, −0.3%, **+3.9%**, 2.3 | 38 (16), +4.2%, 68%, −0.5%, **+5.6%**, 2.8 |
| H07-G the same with the market allowed | INSUFFICIENT | 6 (4), 0.0%, 50% | 10 (5), +0.9%, 40% |

Each trade: buy at the next open, sell when RSI(10) is back over 40 or after 10 days, NDAX costs. Baseline: every uptrend day of the
same coin traded with the same exit.

## What it says
1. **This is the most consistent result found so far:** in both periods the short dip trade beat ordinary uptrend days traded the
   same way by about 4-6% per trade, winning about 70% of the time. It misses the pre-registered bar only on numbers: 25 independent
   market events in 2018-23 against 30 required (and z 2.3 against 2.5).
2. **It works when the market is not "allowed".** These dips mostly happen when BTC is under its 50-day; with the market gate on
   there were only 9 cases. So it is a different kind of trade from everything else: a quick bounce in a coin's long uptrend while
   the market is shaken, held for days, not weeks.
3. Under the rules it stays a hypothesis (H07 PROMISING). It is now shown live as a teacher read next to your setups and every fire
   is recorded; with about 5 cases a year across the 10 coins, live evidence will be slow.

## What changes
- H07 is recorded live (reads lookup, Markets, coin pages). A paper shadow needs Madhav's sentence.
