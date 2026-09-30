# Entry study v2: results

Pre-registration: `ENTRY_STUDY_V2.md` (commit b31a344, before any v2 result).
Run 2026-09-29 on the laptop. Full table: `~/ananta_runs/entry_v2/report_setA.json`.

## Verdict (by the pre-registered rules)

- **0 of 36 passed DISCOVERY at the primary cost (Kraken Tier 1).** Nothing is CONFIRMED.
- **The HOLDOUT (Aug–Sep 2026) stays unused.**

## What changed from v1: a real gross edge exists at this horizon

Leading variant: `S3_TREND_CONTROL | E_DIP | X_TRAIL | LONG`.
- Setup: daily and 4h trend both UP.
- Entry: limit buy at the 4h close − 0.5 × ATR4h.
- Exit: trailing exit.
- Median hold about 40h. Exits are all stops or trail, except for a few time exits.

| Split | Trades | Gross per trade | Kraken T1 net | Kraken T3 net | Low-fee net |
|---|---|---|---|---|---|
| DISCOVERY (→2023) | 1,795 | **+1.97%** (t 7.3; +1.1% to +4.4% on every coin) | +0.67% (t 2.46, PF 1.20, 8/10 coins) | +1.27% (t 4.7, 10/10) | +1.78% |
| CONFIRM (2024–Jul 2026) | 768 | **+1.13%** (t 3.8; +0.2% to +2.5% on every coin) | **−0.17%** (3/10) | +0.43% (PF 1.18, 8/10) | +0.94% |

- It fails DISCOVERY at Tier 1 by t = 2.46 against the 2.5 required.
- It would fail CONFIRM at Tier 1 anyway.
- At Tier 3-like costs (round trip ~0.6–0.7%) it would pass both splits.

Other patterns (gross per trade):
- **Limit dip entries beat market entries** in every setup (about +0.7 to +1.0 percentage points).
- **Longs beat shorts.**
- **The simple trend control (S3) beat the pullback (S1) and breakout (S2) setups.**

Honest reading: much of the edge is "be long in confirmed uptrends, buy the dip".
That is partly crypto's rise over 2017–2026 (beta), not skill. A buy-and-hold benchmark
must sit beside it in any next test.

## Venue costs measured 2026-09-29

This strategy uses a limit entry and a market stop exit.

| Venue | Fee | Spread | Round trip for this strategy |
|---|---|---|---|
| Kraken Tier 1 | 0.40% maker / 0.80% taker | ≈ 0 (0.00–0.05%) | ≈ 1.25% |
| Kraken Tier 3 | 0.22% / 0.38% | ≈ 0 | ≈ 0.65% |
| NDAX (CIRO, API available) | flat 0.20% | CAD books 0.17–0.74% (half-spread ~0.3%) | ≈ 0.7% |

## What a valid next step looks like (not done; needs the operator)

1. Choose the venue. That fixes the primary cost.
2. Pre-register v3: freeze this single variant exactly, at the chosen venue's cost, with buy-and-hold as the benchmark.
3. Use the holdout once. It is only about 6 weeks, and it was a strong up-market, so it flatters a long trend strategy.
4. Paper-forward the frozen variant on new data. This needs an operator sentence.

The variant was picked after seeing v2's DISCOVERY and CONFIRM, so only the holdout and forward paper are clean evidence for it.
