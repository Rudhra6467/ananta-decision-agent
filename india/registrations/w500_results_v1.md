# W500 v1 results: do the narrow-universe results carry to the next band of stocks?

Frozen spec registrations/w500_v1.json (Madhav, 3 Nov 2026 (chat: 'yes to all your recommendations and next steps', after the draft registrations/w500_v1_draft.md)). Bands: OC1 ranks 101-250, IB1 ranks 51-150, GP1 ranks 251-500. HISTORICAL BACKTEST, research years only. 'Carries' = same sign and t >= 2.0 in both periods on the new band; the ledger verdict uses k = 11.

| variant | original dev t | original val t | new band dev mean | t | new band val mean | t | carries | ledger verdict |
|---|---|---|---|---|---|---|---|---|
| OC1 · STOCKS · k15 · E1 · X1 · vs_base | +7.9 | +11.3 | +20.49 | +15.3 | +21.77 | +22.0 | yes | VALIDATED |
| OC1 · STOCKS · k15 · E1 · X2 · vs_base | +8.6 | +12.5 | +20.68 | +19.3 | +21.54 | +25.0 | yes | VALIDATED |
| OC1 · STOCKS · k15 · E2 · X1 · vs_base | +10.6 | +16.2 | +24.39 | +23.5 | +23.10 | +30.1 | yes | VALIDATED |
| OC1 · STOCKS · k15 · E2 · X2 · vs_base | +13.8 | +18.8 | +23.38 | +28.3 | +22.19 | +34.8 | yes | VALIDATED |
| OC1 · STOCKS · k30 · E1 · X1 · vs_base | +6.6 | +9.4 | +20.43 | +12.6 | +22.82 | +19.7 | yes | VALIDATED |
| OC1 · STOCKS · k30 · E1 · X2 · vs_base | +7.8 | +11.1 | +21.87 | +17.9 | +22.11 | +24.0 | yes | VALIDATED |
| OC1 · STOCKS · k30 · E2 · X1 · vs_base | +12.4 | +15.3 | +24.34 | +17.8 | +23.48 | +26.5 | yes | VALIDATED |
| OC1 · STOCKS · k30 · E2 · X2 · vs_base | +15.8 | +19.9 | +23.00 | +23.6 | +22.66 | +31.7 | yes | VALIDATED |
| IB1 · STK · orb15 · net | +8.5 | +7.4 | +0.0016 | +10.9 | +0.0010 | +8.8 | yes | VALIDATED |
| IB1 · STK · orb30 · net | +8.6 | +9.0 | +0.0017 | +10.4 | +0.0011 | +10.4 | yes | VALIDATED |
| GP1 · STK · gapdown2 · open · hold1 | +14.7 | +3.0 | +0.0224 | +19.6 | +0.0089 | +9.3 | yes | VALIDATED |

11 of 11 variants carry to the next band.

## What 'carries' does and does not mean (written after the run, from the ledger extras)

- Every one of these is a RELATIVE result, and each one carries: the effect is not confined to the most traded names. None of them is a way to make money by itself.
- OC1: on ranks 101-250 the filtered trades still lose about 25-33 bps per trade after costs in both periods (the baseline loses about 24-29). 'vs_base' is positive because the filters skip many losing trades. The protocol tells you when NOT to trade a stock at the open; it does not find trades that pay.
- IB1: on ranks 51-150 the breakout trades lose about 0.10-0.14% per trade after costs, against about 0.25% for random intraday entries. Better than random, but still a loss.
- GP1: buying the open after a 2% gap-down earns on paper on ranks 251-500 too (about +2.0% dev, +0.3% val per trade after costs). The GP1 results page already says it cannot be traded as defined (the gap is known only once the open prints) and that the edge has faded; a wider universe does not change that.
- So: no rule, book or paper position changes. The finding goes into each study's write-up as 'holds beyond the most traded names'.
