# Repair-shop review #4: portfolio trend exposure with crash protection (pre-registration)

Written 2026-09-30 **before** any run.
- **Question** (from reviews #1–#3): can Jarvis manage a basket like a portfolio manager? Stay invested while trends are up, go to cash when they turn down, and trade rarely so costs stay small. Does that beat simply buying and holding?
- **Data:** lab-10 coins, daily candles built from the 5m history (UTC days).
  - Test on **DISCOVERY 2017–2023** and **CONFIRM 2024 to July 2026**; the holdout (Aug–Sep 2026) is not loaded.
  - A coin joins the basket once it has 50 days of history.

## Strategies (5, all reported)

| ID | Rule, decided on each daily close, traded at the next day's open |
|---|---|
| BH | Buy and hold: equal weight across available coins, rebalanced weekly |
| T1 | Hold a coin while its daily close > its daily EMA50; its share sits in cash otherwise |
| T2 | T1, and only while **BTC**'s daily close > BTC's EMA50 (market gate) |
| T3 | T2, but exit a coin as soon as its daily close < its **EMA20** (faster crash exit); re-enter on the T2 rule |
| T4 | Hold the whole basket while BTC's daily close > BTC's EMA50; all cash otherwise |

- Each available coin has an equal target share (1/N). Weights are reset to target weekly and whenever a signal changes.
- Every trade pays NDAX market costs: 0.20% fee plus the coin's half-spread.

## Measures (each split, and the whole period)

- Total return and CAGR.
- **Max drawdown**, measured from the running peak.
- MAR (CAGR ÷ max drawdown).
- Worst and median 12-month result from quarterly fresh starts.
- Time in market, number of trades, costs paid.
- Return in each of the six crisis windows (R6).

## Pass rule (vs BH)

A strategy passes if, in **both** DISCOVERY and CONFIRM:
1. its total return is **> 0**;
2. its **max drawdown is lower** than BH's;
3. its **MAR is higher** than BH's.

A passing strategy is proposed as the Explorer's **portfolio layer**:
- paper first;
- its drawdown and worst 12-month start are checked against the $500 plan before any live use;
- the operator decides.
