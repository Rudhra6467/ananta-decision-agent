# Green-run journal v1: results

Pre-registration: `GREEN_RUNS_STUDY_V1.md` (commit 2a2c37c, before code and results). Engine commit 2a4687d, with 7 tests including lookahead.
Run 2026-09-30 on the laptop.
- 10 coins, 2.69M events (1.63M green runs plus a 1.06M every-6th-bar baseline).
- 67,167 cells counted, all saved in `~/ananta_runs/green_runs_v1/cells.csv`.
- **HOLDOUT (Aug–Sep 2026) not touched.** The fresh10 reference was not run, because nothing passed.

## Verdict: 0 cells pass, at any cost, including zero fees

| Cost | Pass DISCOVERY | Pass CONFIRM |
|---|---|---|
| NDAX_NOW (primary) | 0 | 0 |
| ZERO_FEE (subscription scenario) | 0 | 0 |
| KRAKEN_T1 | 0 | 0 |

- At NDAX costs, not one of about 21,000 cells with enough trades has a positive mean, even in DISCOVERY.
- At zero fees, 62 cells are positive in DISCOVERY. The best t is 3.2, below the 3.5 rule, and every one of them is negative in CONFIRM.

## The journal: what happens after 2, 3, 4, 5 green 5m candles

| Split | Run length | Count | P(next candle green) | Mean return, next 24h | Median best / worst move, next 4h |
|---|---|---|---|---|---|
| DISCOVERY | any bar (baseline) | 666,038 | 47.9% | +0.25% | +0.90% / −0.94% |
| | 2 greens | 608,133 | 46.5% | +0.27% | +0.90% / −0.96% |
| | 3 greens | 282,449 | 46.0% | +0.30% | +0.92% / −0.98% |
| | 4 greens | 129,817 | 45.2% | +0.35% | +0.93% / −0.99% |
| | 5 greens | 58,642 | 44.8% | +0.39% | +0.95% / −1.01% |
| CONFIRM | any bar (baseline) | 353,458 | 48.0% | +0.04% | +0.76% / −0.80% |
| | 2 greens | 328,535 | 47.0% | +0.04% | +0.76% / −0.81% |
| | 3 greens | 154,305 | 46.8% | +0.05% | +0.76% / −0.82% |
| | 4 greens | 72,154 | 45.8% | +0.04% | +0.77% / −0.82% |
| | 5 greens | 33,043 | 45.6% | +0.05% | +0.78% / −0.82% |

- **A run of green 5m candles is slightly more likely to end than to continue.** The longer the run, the lower the chance of another green candle.
- **What follows is the same as at a random moment.** The moves after a run are the same size in both directions, and the 24h return matches the baseline. In DISCOVERY the drift is market drift (2019–2023); in CONFIRM it is almost zero.

## Entry region: which run length and which entry

Mean net per trade over all contexts. Zero-fee case, exit B2 (+3% / −1.5% / 24h):

| Run length | Buy now (next open) | Limit at 25% pullback | Limit at 50% pullback |
|---|---|---|---|
| 2 | −0.48% / −0.53% | −0.22% / −0.26% | −0.22% / −0.26% |
| 3 | −0.48% / −0.52% | −0.22% / −0.26% | −0.22% / −0.26% |
| 4 | −0.47% / −0.51% | −0.20% / −0.24% | −0.20% / −0.26% |
| 5 | −0.46% / −0.50% | −0.19% / −0.23% | −0.18% / −0.24% |

The first figure in each cell is DISCOVERY, the second is CONFIRM.

1. **Run length hardly matters.** 2 vs 5 greens differ by about 0.02–0.03% per trade.
2. **The entry method matters, but only through cost.** A resting limit on a pullback saves the spread on entry, about 0.26%. Losses after that equal the exit spread, so the direction edge is still about zero.
3. **With zero fees, a subscription alone does not rescue a signal with no edge.** On NDAX the spread (0.08–0.40% per side) is a large part of the cost. Fees matter once a real edge exists: at NDAX today they cost about 0.4% per round trip.

## Contexts checked (every one-feature and two-feature combination)

The 11 context features:
- Trends: daily, 4h, 1h, BTC 4h.
- Volume contraction before the run.
- Squeeze.
- Expanding volume during the run.
- RSI momentum.
- Reversal from a 4h low.
- Run size.
- Time of day.

**No combination of these turns a green run into an edge that survives into 2024–2026.**
- The best zero-fee DISCOVERY cells (high prior volume + RSI > 70, pullback entry, wide exit) all reversed sign in CONFIRM.

## What this means for the operator's question

- **Counting consecutive green 5m candles, confirmed by volume contraction, momentum and trend, does not find an early entry region on these 10 coins.** The early information in 5m colour runs is noise at the level that matters for costs.
- **What the study did find is useful:**
  - Enter with resting limits, never at market. That saves about a quarter of a percent per trade.
  - The fee decision should wait until a real edge exists; the spread dominates on NDAX.
- **What is left untested:**
  - Order-flow-type data (order book, trade imbalance), which 5m OHLCV candles cannot show.
  - Events defined by *price structure* rather than candle colour, e.g. a break of the prior day's high or a failed breakdown.
  - Other markets.
