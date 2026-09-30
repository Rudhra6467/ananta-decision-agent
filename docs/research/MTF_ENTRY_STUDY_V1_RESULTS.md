# Multi-timeframe entry study v1: results

Pre-registration: `MTF_ENTRY_STUDY_V1.md` (commit a7c5801, before any result).
Run 2026-09-30 on the laptop.
- Data: 10 coins, about 8.1M 5m bars.
- Variants: 108, all reported in `~/ananta_runs/mtf_entry_v1/report_setA.json`.

## Verdict

- **0 of 108 variants passed DISCOVERY** at the primary cost (Kraken Tier 1, maker entry and target).
- Therefore **nothing is CONFIRMED**.
- **The HOLDOUT (Aug–Sep 2026) was not run and stays unused**, as the rules require.

## Why nothing passed

1. **There is almost no directional edge before costs.**
   - Best variant gross: +0.073% per trade (t = 2.4). It is a SHORT: T3 squeeze release, 1h+15m confirmation, 4h-trend gate, trailing exit.
   - Average gross over all variants: LONG −0.022%, SHORT −0.027% per trade.
2. **Costs are 10–25× larger than the edge.**
   - Round trip, including 0.05% slippage per side: Kraken T1 taker 1.70%, T1 maker 0.90%, T3 0.54%, low-fee 0.19%.
   - Even at low fees, all top variants are net negative in both splits.
3. **Moves are big enough, but their direction is not predicted.**
   - The median best move within 24h after a trigger is 2.3–2.7% (p75 4.8–5.7%).
   - Price travels about as far against the entry, so 1-ATR stops are hit first.
4. **Factor effects on gross per trade (DISCOVERY):**

   | Factor | Effect |
   |---|---|
   | 4h-trend gate | Helps most: −0.039% → +0.005% |
   | 1h / 15m confirmation | Negligible (−0.025% → −0.023% / −0.027%) |
   | Exits | X3 adaptive slightly least bad (−0.017% vs −0.027% / −0.031%) |
   | Triggers | Pullback-reclaim least bad (−0.010%) |

   Trend-gated, fully confirmed **shorts** were the top 9 variants, but shorting is not currently available to the operator (Canada / Ontario).

## Trade size vs charges

- Kraken charges a **percentage**, so a bigger or smaller trade does not change the cost per trade in %.
- What lowers the rate is the **tier**:
  - Tier 2 needs $2.5k traded per 30 days.
  - Tier 3 needs $10k traded, or $20k held on Kraken.
- Maker (limit) orders cost half of taker orders.
- A trade needs an expected move of at least about 3× the round trip:
  - about 5% at Tier 1 taker
  - about 2.7% at Tier 1 maker
  - about 1.6% at Tier 3
- This points to fewer, larger-move trades held for hours to days, not 5m scalps.
- Minimum orders are not a constraint at $100 per trade (BTC 0.0001, ETH 0.01).

## Consequences

- Paper's 8bp haircut, and Hands' `taker_fee_pct` = 0.4, both **understate** real Tier 1 costs.
  Proposed: set the paper cost to the real maker/taker mix. This is an operator decision.
- v2 must be a **new pre-registration**. Suggested direction: 5m used only for entry timing, with setups and targets sized to 4h/1d moves of 3% or more. Maker entries.
