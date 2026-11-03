# W500 v1 (DRAFT, not frozen, nothing run): do the narrow-universe results carry to the next band of stocks?

Data audit step 4 (3 Nov 2026). The audit first said most studies use only the 250 most traded stocks. The code says otherwise. Most studies that held up already use the 500 most traded (V01, E04, P01, CL1, the T-TWT tests). Three are narrow:

| study | its universe | the next band to test | why this band |
|---|---|---|---|
| OC1 (opening decision protocol, stocks) | the 100 most traded | ranks 101-250 | 5-minute bars cover these names well enough from 2015 |
| IB1 (intraday breakouts, stock rows) | the 50 most traded | ranks 51-150 | as above; ranks past 150 have thin 5-minute coverage before 2019 |
| GP1 (opening gap, stock rows) | the 250 most traded | ranks 251-500 | daily data, no coverage limit |

## What would be tested (fixed now, before any number is seen)

Only the variants that are VALIDATED today, with their frozen rules, costs and periods (development 2000-2017 or the study's own start, validation 2018-2023). There is no new search and no new variant.

- **OC1, 8 variants.** STOCKS · k15/k30 · E1/E2 · X1/X2 · vs_base: the filtered entries against the same entries without the filters. The base trades themselves lose money net of costs (base_net came out OPPOSITE). So OC1 says the filters help, not that the trades pay.
- **IB1, 2 variants.** STK · orb15 · net and STK · orb30 · net. The index rows are not stock rows, so they are left out.
- **GP1, 1 variant.** STK · gapdown2 · open · hold1.

The universe is chosen the same way as in each study: the previous session's liquidity rank, chosen each day, delisted names included. The only change is the band.

**Pass rule ("carries").** The same sign as the original, with t at least 2.0 in both periods, on the new band alone. Each variant is reported on its own; 11 tests are set before the run. If a variant fails, that is a finding about how wide the edge is, not a rejection of the original.

**What it changes.** Nothing trades from it. A variant that carries is wider evidence. A variant that does not carry has its write-up say it holds only in the most traded names.

## Needs Madhav's yes

The freeze needs Madhav's yes; after it, the run goes into the ledger as W500. Reading the research years only (to 2023) is within the firewall. The sealed years are not touched.
