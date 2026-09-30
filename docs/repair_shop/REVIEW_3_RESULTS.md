# Repair-shop review #3: results (buy weakness)

Pre-registration: `REVIEW_3.md` (commit 09d0901). Evaluation: `review_compare.review3` (commit 83fb70a). Run 2026-09-30.
- Test period: DISCOVERY, 2017–2023, which the trader data never touched.
- CONFIRM (2024–July 2026) is in-sample and shown for reference. The holdout was not loaded.

## Verdict: no variant passes. Every one loses after costs.

| Variant | DISCOVERY trades | Mean net / $100 | Win rate | Random SHORT_TERM entries | t vs random | t vs v0 (−$0.38) | 2024–26 (in-sample) mean | vs random |
|---|---|---|---|---|---|---|---|---|
| R3a: 15m RSI < 30 | 19,557 | −$0.40 | 42% | −$0.50 | **+3.88** | −0.20 | −$0.49 | −$0.46 |
| R3b: 1h RSI < 40 in a 4h downtrend | 16,022 | −$0.48 | 37% | −$0.50 | +0.71 | −1.33 | −$0.49 | −$0.46 |
| R3c: below daily EMA50, low momentum | 28,172 | −$0.45 | 30% | −$0.50 | +2.63 | −0.89 | −$0.49 | −$0.46 |
| R3all: any of the three | 41,177 | −$0.42 | 34% | −$0.50 | **+4.21** | −0.50 | −$0.48 | −$0.46 |

## What we learned

1. **Buying weakness is a real but small effect.** In 2017–2023, buying when the 15m RSI was under 30 beat random short-term entries by about $0.10 per $100 trade (t = 3.9). That is the first entry rule in our tests to beat chance on data it was not built from.
2. **It is far too small to pay the costs.** Every variant still loses about $0.40–0.48 per trade after NDAX fees and spread, no better than v0.
3. **The traders' pattern does not survive being traded.** In 2024–26, the very period it came from, dip entries with our exits did slightly *worse* than random entries. The 24h "excess" that traders' dip buys showed does not survive real exits and costs.

## Where the evidence now points (reviews #1–#3 and the earlier studies)

- On these 10 coins at NDAX costs, **no short-horizon entry rule has cleared costs**: 5m candle runs, v0's five setups, market vs limit entries, trader contexts, dip buying.
- The one consistent source of return is **being in the market during multi-week up-trends** (random 60-day holds ≈ our setups' 60-day holds).
- The one consistent protection is the **exit bells in slow crashes** (+$2,365 saved across four crashes).
- The next review should therefore test **portfolio-level trend exposure with crash protection**. It trades rarely, so costs are small.
