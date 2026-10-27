# VL1 results: Nifty valuation: does an expensive Nifty (high P/E or P/B, low dividend yield) come before weaker returns, and a cheap one before better returns?

Registered 2026-10-27T13:26:33+00:00 (spec `vl1_v1.json`, written before the run); family valuation, k = 6, z = 2.64. Development to 2017, validation 2018-2023; nothing from 2024 on.

## In plain words

**An expensive Nifty did come before weaker returns in 2003-2017, but there are too few independent periods to call it proven, and the P/E history has a method break in 2021. Every row is INCONCLUSIVE.**
- **P/E in the top tenth of its history (705 days in 2003-17, 717 in Apr 2018-Mar 2021):** the next 60 sessions were 6.7% weaker than at other times in 2003-17 (t -3.0, 21 quarters) and 9.1% weaker in 2018-21 (only 3 quarters). Over the next 250 sessions: 31.9% weaker in 2003-17 (8 years, dominated by the 2008 crash).
- **Cheap Nifty:** bottom-tenth P/E +13.6% over 60 sessions (7 quarters, all before 2018); top-tenth dividend yield +6.8% (4 quarters); neither happened in 2018-23.
- **P/B top tenth:** -2.0% (t -0.5); **dividend yield bottom tenth:** -3.1% (t -0.9).
- **Why no verdict:** valuation regimes last months to years, so 20 years hold only a handful of independent episodes; P/E and P/B switched to consolidated earnings in March 2021, so they are used only to then.
- **What Ananta does with this:** it can say where the Nifty's P/E sits against its history and that expensive markets have tended to do worse, without calling it a tested signal. No rule changes.

## The rows

Verdicts: VALIDATED and CONDITIONAL would be passes; OPPOSITE means significantly the other way round; INCONCLUSIVE means too few independent blocks (16 needed per period) or a reading below the bar.

| variant | expected | verdict | dev mean | dev t | dev blocks | val mean | val t | val blocks | events dev / val |
|---|---|---|---|---|---|---|---|---|---|
| NIFTY|pe_top10|fwd60 | - | INCONCLUSIVE | -6.74% | -3.01 | 21 | -9.12% | -1.94 | 3 | 705 / 717 |
| NIFTY|pe_bottom10|fwd60 | + | INCONCLUSIVE | +13.61% | +2.22 | 7 | n/a | n/a | 0 | 226 / 0 |
| NIFTY|pb_top10|fwd60 | - | INCONCLUSIVE | -2.01% | -0.51 | 11 | n/a | n/a | 0 | 488 / 0 |
| NIFTY|dy_top10|fwd60 | + | INCONCLUSIVE | +6.75% | +1.09 | 4 | n/a | n/a | 0 | 168 / 0 |
| NIFTY|dy_bottom10|fwd60 | - | INCONCLUSIVE | -3.05% | -0.93 | 11 | n/a | n/a | 2 | 382 / 39 |
| NIFTY|pe_top10|fwd250 | - | INCONCLUSIVE | -31.93% | -3.33 | 8 | n/a | n/a | 2 | 705 / 717 |
