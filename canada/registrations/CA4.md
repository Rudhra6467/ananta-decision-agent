<!-- Registration CA4, frozen from the approved C0 document (rev 24, sha256 3c3b9e939ce3cd71e6b77598af93f81ead1d78a488164fae4b814980733e1e1a). The common rules and validation checks it relies on are frozen in C0_document.md. -->

## CA#4 — The cost law

**Question: as stocks get less liquid, does any edge disappear once costs are paid, and where is the last decile still worth trading?** This review sets the boundary below which the agent may never trade Canadian stocks. The cost side is estimated from daily highs and lows, so the cost curve is **reported, not tested**, and the verdict is **capped at WEAK until spreads are measured**, whatever the numbers say.

| Field | Frozen value |
| --- | --- |
| Hypothesis | The dip rule's edge after costs is larger in the more liquid half of the Composite than in the less liquid half. |
| Null | Edge after costs shows no difference between the liquid and illiquid halves beyond what random shuffling of liquidity labels produces. |
| Universe | S&P/TSX Composite members, point-in-time as of *t−1*. |
| Liquidity deciles | Median daily traded value (Norgate's Turnover, C$) over the last 63 available trading days ending *t−1*. Deciles formed among eligible members on the first trading day of each calendar quarter; decile 1 = most liquid. |
| Trades | CA#3's dip rule exactly (signal, exclusions, next-open entry, 10-day hold, no stop), on every Composite member; all dial states and dip types pooled. |
| Edge | Per trade: net return at the stated cost level **minus the mean gross, uncosted return** of 1,000 random members of the same decile entered on the same date with the same hold. Costs therefore count against the edge instead of cancelling. |
| Cost curve (reported only) | Median estimated one-way cost per decile per period, and its rank correlation with decile number. Not a pass criterion until spreads are measured. |
| Independent event | Clusters, by the common definition, counted per decile. Minimum: **30** per decile in development, **15** in validation. At least **3** deciles on each side (1–5 and 6–10) must meet it, or the verdict is INSUFFICIENT EVIDENCE. |
| Pass, **both** periods, **1× and 2×** costs | Mean edge of deciles 1–5 minus mean edge of deciles 6–10 (qualifying deciles only) is above zero **and** above the **95th percentile** of 1,000 permutations that shuffle decile labels among trades entered on the same date. |
| Tradable boundary (output, whatever the verdict) | The largest *k* such that **every** decile from 1 to *k* has mean edge ≥ 0 at 2× costs in both periods with minimums met; "none" if decile 1 fails. Labelled ESTIMATE. |
| Verdict cap | WEAK at most until measured spreads replace the estimates. |
| Holdout statistic | Edge still falls with liquidity (rank correlation between decile number and edge below zero), and the boundary decile's edge ≥ 0. |
| Data needed | Composite membership, Turnover, prices (signal-adjusted, total return; capital-adjusted highs and lows), capital-event and distribution days. |
