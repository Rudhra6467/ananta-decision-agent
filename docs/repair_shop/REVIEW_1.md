# Repair-shop review #1: pre-registration

Written 2026-09-30 **before** any variant below was run. Source: the three proposals in `docs/research/EXPLORER_V0_SCORECARD.md`.
Engine: `explorer_engine` with a `Rules` setting per variant. The v0 default is unchanged, so the live Explorer keeps running v0.

## Variants (6, all reported)

| ID | Change vs v0 | Tests proposal |
|---|---|---|
| C0 | none (control, v0) | — |
| P1a | **market entry**: buy at the next 5m open after the scan (fee + half-spread) | 1: limits pick the losers |
| P1b | **limit at the scan close** (instead of 0.25 × ATR below it) | 1: a limit much closer to the price |
| P2 | **no warning bells**: X3 off; X1 stop, X2 disaster, X4 target/trail and X5 time cap stay | 2: simpler exits |
| P3 | **setups E1–E4 only**: E5 removed | 3: drop the worst setup |
| V1c | P1a + P2 + P3 together | the combined v1 candidate |

## Baseline added before the run

RANDOM shadow entries now also carry the HOLD and AS_&lt;type&gt; exit sets. This lets "hold to the time cap" be compared with holding **random** entries: does the edge come from the setups or from market drift?

## Measures

For each variant, in DISCOVERY (before 2024-01-01) and CONFIRM (2024-01-01 to 2026-08-01):
- the number of real trades, win rate, mean net per $100 trade, mean R;
- the paper account ($2,000, N4 caps);
- the crisis replays (R6).

The HOLD exit set is compared with random-entry HOLD. The holdout (Aug–Sep 2026) is not loaded.

## Rule for a change to enter Rulebook v1 (proposed to the operator; the operator decides)

A variant **passes** if, in **both** DISCOVERY and CONFIRM:
1. its mean net per trade is higher than C0's, by a Welch t ≥ 2.0 on per-trade net;
2. its total loss in the six crisis windows is not more than 20% worse than C0's.

- If V1c passes, it is the Rulebook v1 candidate.
- If not, v1 takes the single changes that pass.
- If nothing passes, v0 stays and review #2 starts from what was learned.
- Whatever passes still runs as a paper **shadow** next to v0 before promotion, per R4.
