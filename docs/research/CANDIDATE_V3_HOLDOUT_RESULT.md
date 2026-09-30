# Candidate v3: one-time holdout result

Run: 2026-09-30T01:52:59Z. The marker file prevents a rerun.
Window: 2026-08-01 → 2026-09-12. Pre-registration: `CANDIDATE_V3.md` (11996ab).

**Parity check before the run:** the runner reproduced v2's recorded trades exactly
(BTC and SOL, both earlier splits, identical gross values).

## Result: FAIL

| | n | Mean net per trade | 90% bootstrap interval | Win rate | PF |
|---|---|---|---|---|---|
| Candidate @ NDAX (primary) | 62 | **−0.48%** | −1.66% … +0.81% | 32% | 0.81 |
| Candidate @ Kraken T1 | 62 | −1.10% | −2.27% … +0.17% | 32% | 0.62 |
| B1: just be long in the same windows @ NDAX | 62 | −1.83% | −2.98% … −0.62% | 27% | 0.46 |

- Candidate $1,000 book: **−2.94%**.
- **B2 equal-weight buy-and-hold: +24.69%.**
- Gross per trade: +0.20%, against +1.97% (2017–2023) and +1.13% (2024–Jul 2026).
- Exits: 59 of 62 were stops or trail. Median hold: 47h.
- Per coin ($100 per trade, NDAX): LINK +25.0, ETH +4.3, SOL +3.8; DOGE −20.7, BCH −15.8, XRP −14.6, LTC −10.8.

## Reading

- The dip-limit entry and trailing exit did beat naive timing (B1).
- In a strong up-market, a 1.5 × ATR4h stop with a 2.5 × ATR trail exits far too early. Holding beat all of it.
- The historical gross edge shrank sharply from 2017–2023, to 2024–26, to the holdout.
- Per the pre-registration, paper-forward still proceeds (operator approved it). This FAIL is recorded for the live gate as a strong warning.
- All historical data (Set A and Set B) has now been used for this family. **Any redesign, such as regime-wide exits in strong trends, can only be validated forward, on paper.**
