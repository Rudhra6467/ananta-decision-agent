# Green-run journal v1 (GR1): pre-registration

Operator 2026-09-30:
- Track runs of 2, 3 and 4 continuous green 5m candles and find the best **entry region**.
- Use 5m for early timing, and 15m/1h/4h/daily plus volume contraction and momentum as confirmation.
- In paper, "find everything": the operator filters, then rules are written before live.

Written before any code or result. The study is descriptive **and** a test. Every cell is counted and reported.

## Data and splits
- Coins: lab-10 (`lab5_5m.sqlite`, BTC ETH SOL ADA DOGE AVAX BCH LINK LTC XRP), 5m bars, closed bars only.
- Splits by event time:
  - **DISCOVERY**: before 2024-01-01.
  - **CONFIRM**: 2024-01-01 to 2026-08-01.
  - **HOLDOUT**: Aug–Sep 2026. **Not run**, stays unused.
- Out-of-sample coins: fresh10 (`fresh10_5m.sqlite`). Reference run only for cells that pass CONFIRM. Reported, never used for selection.

## Events
- **Green candle**: close > open.
- `r[i]` is the number of consecutive green candles ending at bar i.
- **Event k** fires at the close of bar i when `r[i] == k`, for k = 2, 3, 4, 5. Run start: `s = i − k + 1`.
- **Baseline k=0**: every 6th bar, any colour. It answers: are green runs better than entering at a random time in the same context?
- An event needs contiguous 5m bars from s−288 to i. Every higher-timeframe value comes from bars closed at or before bar i's close.

## Context (all known at bar i's close)

| Feature | Values |
|---|---|
| trend_1d, trend_4h, trend_1h (close vs EMA50 and EMA20 vs EMA50) | DOWN / FLAT / UP |
| btc_4h (BTC's 4h trend, same rule) | DOWN / FLAT / UP |
| vol_prior: mean volume of the 24 bars before s ÷ mean of the 288 bars before s | LOW (<0.7) / NORMAL / HIGH (>1.3), i.e. **volume contraction** |
| squeeze: Bollinger(20, 2) width at s−1 ≤ its 20% quantile over 288 bars | NO / YES |
| run_vol: mean volume of the run ÷ mean of the 48 bars before s | NORMAL / EXPANDING (≥1.5) |
| rsi5: RSI14 on 5m at i, i.e. **momentum** | <50 / 50–70 / >70 |
| origin: low of bar s ≤ lowest low of the 48 bars before s | OTHER / FROM_4H_LOW (reversal) |
| run_size: (c[i] − o[s]) ÷ ATR14 of 5m at s−1 | SMALL (<1) / MEDIUM (1–2) / LARGE (>2) |
| session: UTC hour of i's close | 0–8 / 8–16 / 16–24 |

## Entry regions (compared for each k)
- **NOW**: market buy at the open of bar i+1.
- **PB25 / PB50**: limit buy at c[i] − 25% / 50% of the run height (c[i] − o[s]), resting 12 bars (1h).
  - If a bar opens at or below the limit, the fill is at that open.
  - The fill bar may stop out but may **not** hit the target (pessimistic).
  - No fill means no trade; the fill rate is reported.
- Baseline k=0 uses NOW only.

## Exits (a limit target, and a stop checked first when both are touched in one bar)
- B1: +1.5% / −1.0% / 4h
- B2: +3% / −1.5% / 24h
- B3: +5% / −2.5% / 72h
- B4 structure: stop at the run's lowest low, target 2× that risk, 24h. Skipped if the risk is under 0.2%. Not used for the baseline.
- A gap through the target or stop fills at the open. The time exit is at the last close.

## Costs (per side)
- **NDAX_NOW** (primary): fee 0.20%, plus the coin's measured half-spread on market orders (entry NOW, stop, time exit).
- **ZERO_FEE** (subscription scenario): half-spread only. It answers whether a free-trade plan changes the answer.
- **KRAKEN_T1**: maker 0.40%, taker 0.80%, plus 0.05% slippage.

## Journal (descriptive, no pass rule)
For every k, per split:
- the count;
- P(the run reaches k+1), i.e. P(next bar green);
- mean forward return at 1h, 4h and 24h from the NOW entry;
- median best move up and worst move down in 1h, 4h and 24h.

## Cells and pass rule
- A **cell** is a k (0, 2–5) × entry × exit × context filter. The filter is ALL, one feature value, or a pair of feature values.
- Every cell is computed and saved to `cells.csv` for filtering.
- t-statistics cluster by coin-day, because trades on the same coin and day are not independent.

A cell **passes at a cost scenario** if all of the following hold:
- **DISCOVERY**: n ≥ 300; mean net > 0; t ≥ 3.5; ≥ 6 of 10 coins positive; ≥ 60% of calendar years positive; mean net above the baseline k=0 NOW in the same context and exit.
- **CONFIRM**: n ≥ 150; mean net > 0; t ≥ 2.5; ≥ 6 of 10 coins positive; above the same baseline.

Primary: NDAX_NOW. ZERO_FEE and KRAKEN_T1 are reported under the same rule.
A passing cell becomes a **paper candidate** only. Nothing is approved for live.
