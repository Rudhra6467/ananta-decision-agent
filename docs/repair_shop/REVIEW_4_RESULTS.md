# Repair-shop review #4: results (portfolio trend exposure vs buy-and-hold)

Pre-registration: `REVIEW_4.md` (commit 7dd77e4). Simulator: `portfolio_trend.py` (commit 863ec7d, 3 tests incl. lookahead). Run 2026-09-30.
- Daily decisions from UTC daily closes of the lab-10 coins, traded at the next day's open, NDAX market costs on every change.
- The holdout (Aug–Sep 2026) was not loaded.

## Verdict: T3 passes. T1, T2 and T4 fail.

| Strategy | 2017–2023 return | max drawdown | MAR | 2024–Jul 2026 return | max drawdown | MAR | Time in market | Pass |
|---|---|---|---|---|---|---|---|---|
| BH buy & hold (weekly equal-weight) | +2,576% | 88% | 0.79 | **−22%** | 71% | −0.13 | 100% | — |
| T1 coin > EMA50 | +4,579% | 62% | 1.37 | −25% | 57% | −0.19 | 41–47% | fail |
| T2 T1 + BTC gate | +5,822% | 57% | 1.62 | −8% | 51% | −0.06 | 36–41% | fail |
| **T3 T2 + fast EMA20 exit** | **+3,558%** | **50%** | **1.57** | **+13%** | **41%** | **0.12** | 31–36% | **PASS** |
| T4 whole basket on BTC gate | +6,143% | 72% | 1.31 | −15% | 56% | −0.11 | 52% | fail |

- **Worst 12-month start:** T3 −31% (Apr 2022) and −13% (Apr 2025); BH −76% and −50%.
- **Median 12-month start in 2024–26:** T3 +15%, BH −6%.

### Crisis windows (return during the window)

| Crisis | BH | T3 |
|---|---|---|
| COVID 2020 | −37% | −2% |
| May 2021 | −38% | −16% |
| LUNA / 3AC 2022 | −56% | **0%** (already in cash) |
| FTX 2022 | −26% | −15% |
| August 2024 | −10% | −3% |
| October 2025 | −14% | −4% |

## Robustness (post-hoc, added after seeing the result; T3 against the same pass rule)

| Check | 2017–2023 T3 return / max DD | 2024–26 T3 return / max DD | Pass |
|---|---|---|---|
| EMA 40 / 15 | +3,340% / 47% | +25% / 38% | PASS |
| EMA 60 / 25 | +3,090% / 54% | +20% / 38% | PASS |
| EMA 100 / 20 | +3,546% / 50% | +33% / 34% | PASS |
| EMA 50 / 30 | +3,494% / 55% | +1% / 46% | PASS |
| BTC gate on EMA100 | +3,803% / 57% | +10% / 41% | PASS |
| **Fees doubled (0.40%)** | +2,357% / 56% | **−4.5%** / 46% | fail (return < 0; still far better than BH's −22%) |
| Without DOGE | +2,678% / 53% | +0.1% / 42% | PASS (barely) |
| Without SOL | +2,316% / 52% | +11% / 43% | PASS |

## What this means

1. **A portfolio layer works where trade entries did not.** Holding coins only in their up-trends, with a market gate and a fast exit:
   - **halved the drawdown** in both periods;
   - avoided most of every crash;
   - stayed profitable in 2024–26 while buy and hold lost 22%.

   It is stable across parameter choices.
2. **Its 2024–26 profit is thin.** It depends on costs (it fails with double fees) and partly on DOGE. Costs come mostly from the **weekly rebalancing**, so a lower-turnover version is the obvious next test.
3. **Drawdown is still too big for the $500 plan as it stands.** 41–50% is far above the 20% circuit breaker. With half the capital in this layer and half in cash, the drawdown would be about 20–25%. Sizing is a decision for the live rulebook.

## Proposed next step (operator decides)

Add T3 to the Explorer as a **paper portfolio layer**:
- a daily book that holds or sells each coin by the T3 rule;
- a daily "hold / move to cash" suggestion per coin with the reason (trend, BTC gate, EMA20 exit);
- phone alerts when a coin moves in or out.

It runs next to v0's trade setups, so both collect evidence.
