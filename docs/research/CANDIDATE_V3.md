# Candidate v3: frozen trend-dip, NDAX costs, one-time holdout. Pre-registration

Committed **before** the holdout is looked at.

Operator 2026-09-29:
- primary venue = **NDAX**
- "paper-trade it" = yes

## Frozen candidate: exactly v2 `S3_TREND_CONTROL | E_DIP | X_TRAIL | LONG`

Code is `src/research/entry_v2.py` at commit 613ac43, unchanged.

- **Setup:** at a 4h close, with daily trend UP and 4h trend UP.
  - UP means close > EMA50 and EMA20 > EMA50.
- **Entry:** limit buy at 4h close − 0.5 × ATR4h, resting for 24h; no fill means no trade.
  - Skip the setup if 3 × ATR4h / entry < 3%.
- **Exit:** stop 1.5A. After the price has risen 1.5A, a trailing stop 2.5A below the best price; time stop 14 days.
- **Positions:** one at a time per coin.

## Why this must be a new test

The candidate was chosen **after** seeing v2's DISCOVERY and CONFIRM results. So only:
- the holdout (2026-08-01 → 2026-09-12), and
- forward paper trading

count as clean evidence.

## Costs

**Primary: `NDAX`**, measured 2026-09-29.
- Entry fee 0.20%, no spread, since the entry is a limit order.
- Exit fee 0.20% (market), plus the coin's measured half-spread (median of 5 snapshots):

| Coin | Half-spread |
|---|---|
| BTC | 0.178% |
| ETH | 0.084% |
| SOL | 0.289% |
| ADA | 0.273% |
| DOGE | 0.307% |
| AVAX | 0.370% |
| BCH | 0.400% (book empty on one side; conservative) |
| LINK | 0.341% |
| LTC | 0.334% |
| XRP | 0.251% |

**Also reported:** Kraken Tier 1 (maker entry 0.40%, taker exit 0.80%, 0.05% slippage per side).

## Benchmarks (same holdout, same costs)

- `B1 SAME_WINDOW_LONG`: for each candidate trade, a market buy at the setup's 4h close and a sale at the same exit time. Taker fee plus half-spread on both sides.
  - This tests whether the dip-limit entry and trailing exit add anything over "just be long then".
- `B2 BUY_AND_HOLD`: equal-weight buy of all 10 coins at the first holdout bar, sold at the last. One round trip of costs.
  - Reported as % of capital, next to the candidate's capital-weighted result: $100 per trade, 10 coins, $1,000 book.

## Holdout rules (fixed now)

- It is run **once**. A marker file prevents a second run.
- Report n, mean net per trade at NDAX with a bootstrap 90% interval, win rate, profit factor, per-coin totals, and B1/B2.
- **Holdout PASS** = n ≥ 20, mean net > 0 at NDAX, and mean net ≥ B1 mean net.
- The holdout is ~6 weeks of a strong up-market. A PASS is weak, favourable-regime evidence. A FAIL is a strong warning.
- Whatever the result, paper-forward proceeds (operator approved it). The holdout result goes in the evidence file for the live gate.

## Paper-forward (operator approved)

- Separate agent-side paper book: $1,000 total, $100 per position, at most one position per coin.
- NDAX cost profile.
- Evidence class `CANDIDATE_PAPER`: never counts for M2, never executes, never touches Hands.
- Candles are Hands' closed 1d / 4h / 1h Kraken USD candles.
  - Limit fills and trail exits are checked on 1h bars, which is coarser than the 5m replay.
  - Kraken USD prices stand in for NDAX CAD prices; NDAX costs are applied.
