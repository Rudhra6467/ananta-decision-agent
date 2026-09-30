# Repair-shop review #1: results

Pre-registration: `REVIEW_1.md` (commit 26a6e89, before any run). Engine v0.2 (b5b7375); all 6 variants were replayed 2026-09-30 on the laptop. The holdout was not loaded.

## Verdict: no variant passes. Rulebook v0 stays.

| Variant | DISCOVERY mean / trade (vs C0 −$0.38) | Welch t | CONFIRM mean / trade (vs C0 −$0.62) | Welch t | Crisis total (C0 −$515) | Result |
|---|---|---|---|---|---|---|
| P1a market entry | −$0.69 (n 11,054) | **−3.56** | −$0.90 (n 4,916) | **−2.97** | −$843 | fail: **significantly worse** |
| P1b limit at the scan close | −$0.42 | −0.38 | −$0.61 | +0.08 | −$605 | fail: no difference |
| P2 no warning bells | −$0.39 | −0.05 | −$0.66 | −0.40 | −$598 | fail: no difference; crises worse |
| P3 drop E5 | −$0.37 | +0.15 | −$0.60 | +0.16 | **−$468** | fail: slightly better, not significant; crises better |
| V1c P1a + P2 + P3 | −$0.66 | −3.16 | −$0.92 | −3.12 | −$837 | fail: worse (market entry dominates) |

## What we learned

1. **The "missed orders did better" evidence was biased, and it was our error.**
   - An order only counts as missed when the price never came back down to the limit, which mostly happens when the price ran up.
   - So the MISSED_CHASE shadow looks at the future. It measured hindsight, not a better entry method.
   - Taking every trade at market (P1a) raised trades from 7,329 to 11,054 and costs per trade, and it was **significantly worse** in both periods.
   - The chase shadow stays in the logs, but it is **not evidence about entry methods**. The scorecard's wording is corrected.
2. **The warning bells (X3) neither help nor hurt on average.** Removing them changed nothing in normal times and made crisis losses worse (−$598 vs −$515). They stay as crash insurance.
3. **E5 (squeeze release) is the weakest setup.** Removing it helped slightly in both periods and in the crises, but not by enough to count (t = 0.15). Candidate for PROBATION rather than removal.
4. **The "hold" edge is market drift, not our setups.** Holding to the time cap, per $100 trade:

| | DISCOVERY: our setups | DISCOVERY: random entries | CONFIRM: our setups | CONFIRM: random entries |
|---|---|---|---|---|
| LONG_TERM hold (60 days) | +$32.80 | +$31.99 | +$7.40 | +$5.30 |
| SHORT_TERM hold (5 days) | +$1.02 | −$0.15 | −$1.38 | −$0.72 |
| INTRADAY hold (8 hours) | −$0.55 | −$0.60 | −$0.75 | −$0.71 |

   Random 60-day holds earn about the same as our setups' 60-day holds. The money comes from being in the market during up-trends, and v0's entry setups add little to that.

## What this means for review #2

- v0's **entries have no measurable edge over random entries** at NDAX costs. Tuning their details (entry price, bells) will not change that.
- The real source of return in this data is **trend exposure over weeks**, which is what the earlier V1_RIDE study also found.
- Review #2 should therefore test **where** to be in the market (trend and market-regime filters for long holds), not how to fine-tune 15-minute entries. It should also learn from **other traders' actual trades** (the reconstruction step) to find entry context we don't yet have.
