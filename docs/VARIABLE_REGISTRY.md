# Variable registry (the prototype's knowledge, for the large datasets)

Every variable we have tested, what the evidence says, and whether it carries forward. Machine-readable copy: `docs/variable_registry.json`.
Status: **KEEP** (survived our tests, carry forward) · **WATCH** (some information, not enough alone) · **DROP** (no usable information) · **UNTESTED** (needs data).

## KEEP

| ID | Variable | Horizon | Evidence | Carry forward |
|---|---|---|---|---|
| V01 | Coin daily trend: close vs 50-day and 20-day averages | weeks | Portfolio layer T3: halves drawdown vs buy-and-hold in 2017-23 and 2024-26; stable for 40/15 to 100/20 averages (`repair_shop/REVIEW_4_RESULTS.md`) | Core variable for every market: per-instrument trend state |
| V02 | Market gate: BTC daily close vs its 50-day average | weeks | T2/T3 beat T1 on drawdown and MAR; LUNA crash 0% vs -56%; study v4 also found the BTC gate reduced losses (`repair_shop/REVIEW_4_RESULTS.md; research/STUDY_V4_RESULTS.md`) | Generalise to 'market-wide gate' per market (index trend for stocks: Nifty, TSX, S&P 500) |
| V03 | Exit bells in slow crashes (disaster stop, trend-break exit) | days | Saved $2,365 across May 2021, LUNA, FTX, Oct 2025; cost money in V-shaped rebounds (COVID, Aug 2024) (`research/EXPLORER_V0_SCORECARD.md; repair_shop/REVIEW_1_RESULTS.md`) | Crash insurance: keep, and measure per market with crisis replays |
| V04 | Trading costs: fee + half-spread per instrument | all | Every short-horizon rule failed on costs, not direction (round trip about 0.6-1.2% at NDAX); expensive coins lose more (`research/GREEN_RUNS_STUDY_V1_RESULTS.md; research/EXPLORER_V0_SCORECARD.md`) | First-class variable: measured spreads per instrument and venue, refreshed monthly |
| V05 | Entry order type: resting limit vs market | minutes | Market entry significantly worse than limits (t -3.6 / -3.0); limit saves about 0.26% per trade (`repair_shop/REVIEW_1_RESULTS.md; research/GREEN_RUNS_STUDY_V1_RESULTS.md`) | Default to limits; never trust 'missed order' shadows as evidence (hindsight bias) |
| V06 | Holding horizon (multi-week exposure) | weeks | Random 60-day holds earned like our setups' holds (+$32 vs +$33 per $100 in 2017-23): return comes from being in up-trends (`repair_shop/REVIEW_1_RESULTS.md`) | Horizon is a decision variable; compare every rule against random entries at the same horizon |

## WATCH

| ID | Variable | Horizon | Evidence | Carry forward |
|---|---|---|---|---|
| V07 | Dip in a coin while BTC is bullish (15m RSI < 30, coin BEAR, BTC BULL) | hours-days | RSI15<30 beat random short-term entries by about $0.10 per trade in 2017-23 (t 3.9) but loses after costs; E6|BEAR|BTC BULL slightly positive gross in both periods (+0.17% / +0.07%) (`repair_shop/REVIEW_3_RESULTS.md; intraday atlas v1`) | Retest on low-cost venues and on stocks (relative dips vs index) |
| V08 | 4h trend filter for intraday entries | hours | Largest gross improvement in MTF entry study v1 (-0.039% to +0.005% per trade) but far below costs (`research/MTF_ENTRY_STUDY_V1_RESULTS.md`) | Useful as a context tag, not as an edge by itself |
| V09 | Other traders' entry timing (Hyperliquid) | hours | +0.06% excess in the first hour (t 2.9), nothing later; skill did not persist from first to second half (`repair_shop/REVIEW_2_RESULTS.md`) | Reference only; revisit with order-flow data (who is aggressive, size) |
| V10 | Buy strength vs buy weakness (traders' context) | days | Traders' longs did better buying weakness (BEAR +0.67% vs BULL -0.41% 24h excess) but this did not survive being traded (`repair_shop/REVIEW_2_RESULTS.md; REVIEW_3_RESULTS.md`) | Candidate for stocks, where mean reversion is better documented |
| V16 | Warning bells (X3) in normal times | hours-days | Neither help nor hurt on average; removing them worsened crisis losses (`repair_shop/REVIEW_1_RESULTS.md`) | Keep as insurance; revisit sizing instead |

## DROP

| ID | Variable | Horizon | Evidence | Carry forward |
|---|---|---|---|---|
| V11 | Consecutive green 5m candles (2-5) | minutes-hours | After green runs the next candle is slightly less likely green (46.5% to 44.8% vs 47.9%); 0 of 67,167 cells pass; 15-60 min moves smaller than costs (`research/GREEN_RUNS_STUDY_V1_RESULTS.md`) | Do not carry forward |
| V12 | 15m/30m reversal crossings (S3) | minutes-hours | Confirmed vs early reversals flip sign between periods; confirmation does not help (`research/EXPLORER_V0_SCORECARD.md`) | Do not carry forward as a signal; keep as a descriptive tag |
| V13 | 1h market bias S1 (EMA50) for intraday entries | hours | No stable difference between BULL and BEAR entries in either period (`research/EXPLORER_V0_SCORECARD.md`) | Use daily trend (V01) instead |
| V14 | Volatility contraction (Bollinger width / ATR) and squeeze release | hours | Squeeze setup E5 worst in both periods; contraction tags carry no stable information (`research/EXPLORER_V0_SCORECARD.md; repair_shop/REVIEW_1_RESULTS.md`) | Retest only with volume/order-flow context |
| V15 | Volume ratio (candle volume vs 20-candle average) | minutes-hours | No stable effect as a confirmation (green-run study, breakout setup) (`research/GREEN_RUNS_STUDY_V1_RESULTS.md`) | Replace with better volume data (taker buy/sell split) |

## UNTESTED (candidates, in the order we would test them)

| ID | Variable | Family | Data source |
|---|---|---|---|
| U01 | Perpetual futures funding rates | crowding / leverage | Hyperliquid, Binance public APIs (free) |
| U02 | Open interest and liquidations | leverage | exchange APIs (free / low cost) |
| U03 | Order-book imbalance and taker buy/sell volume | order flow | exchange websockets (must be recorded live; history is expensive) |
| U04 | Bitcoin dominance and stablecoin supply | market-wide flows | public APIs |
| U05 | Scheduled events: US Fed, CPI, token unlocks | calendar | public calendars (Rulebook R7) |
| U06 | Cross-asset: US dollar index, US 10-year yield, Nasdaq | macro | daily data (free for delayed) |
| U07 | On-chain flows (exchange inflows/outflows) | on-chain | paid providers |
| U08 | News and social sentiment | sentiment | paid / scraping; test last |

## How a variable changes status

1. A study or repair-shop review is written down before it runs; the variable's test is part of it.
2. The result is recorded here with the document that holds the evidence.
3. KEEP needs evidence in two separate periods; DROP needs a clean test with enough data; everything else is WATCH.
4. When the large datasets arrive, KEEP variables are built first, WATCH variables are retested there, DROP variables are not rebuilt.
