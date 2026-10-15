<!-- Registration CA5, frozen from the approved C0 document (rev 24, sha256 3c3b9e939ce3cd71e6b77598af93f81ead1d78a488164fae4b814980733e1e1a). The common rules and validation checks it relies on are frozen in C0_document.md. -->

## CA#5 — The sector-breadth dial

**Question: does a dial that reads how many sectors are trending up do better than CA#1's single-index dial?** Exactly two variants are registered, CA5-A and CA5-B. If Norgate lacks continuous point-in-time sector membership, CA#5 is **NOT RUN**; today's sector labels are never substituted, because that would use knowledge from the future.

| Field | Frozen value |
| --- | --- |
| Hypothesis | Sector breadth gives a higher Calmar and no larger drawdown than CA#1's dial, with no more than 25% extra switching. |
| Null | Each variant's Calmar is no better than random timing with the same number of switches and days in the market. |
| Universe and asset | Identical to CA#1: the equal-weight basket of Composite members, monthly reset, cash at the overnight rate when OUT. |
| Sector series | For each sector index existing that day (10 before 2016-09-01, 11 after): the daily-rebalanced equal-weight mean of its members' signal-adjusted daily returns, members as of *t−1*, chained into an index. A sector with fewer than 3 members that day is left out of that day's count. |
| Sector state | A sector is UP at the close of *t* if its series is above its own 200-day simple average. |
| CA5-A | IN when more than half of the counted sectors are UP. |
| CA5-B | IN when more than half of the counted sectors are UP **and** CA#1's dial is IN. |
| Start | The first day of continuous sector membership (V8 passing) plus 200 trading days of warm-up. CA#1's dial is recomputed from the same start for every comparison below. |
| Entry, exit, costs | As CA#1. |
| Random twin | 1,000 circular shifts of each variant's IN/OUT series per period (common rules). |
| Independent event | One complete OUT-then-IN cycle. Minimum: **8** in development, **4** in validation. |
| Pass per variant, **both** periods, **1× and 2×** costs | (a) Calmar ≥ CA#1 dial's Calmar from the same start; (b) MDD ≤ CA#1 dial's MDD; (c) switches ≤ 1.25 × CA#1's; (d) Calmar above the **97.5th percentile** of its twins (0.05 split across two variants); (e) minimums met. |
| Review verdict | The better variant's grade (common rule). |
| Holdout statistic | Calmar, per variant. |
| Data needed | Continuous membership history of the sector indices (support must confirm depth), Composite membership and closes, stock prices, overnight rate. |
