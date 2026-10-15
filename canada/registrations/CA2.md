<!-- Registration CA2, frozen from the approved C0 document (rev 24, sha256 3c3b9e939ce3cd71e6b77598af93f81ead1d78a488164fae4b814980733e1e1a). The common rules and validation checks it relies on are frozen in C0_document.md. -->

## CA#2 — The trend book

**Question: does holding TSX 60 stocks only while they trend up, and only while the dial is IN, beat holding randomly chosen TSX 60 stocks for the same days, and does it still earn more than cash after twice the estimated costs?** Two outcomes are registered in advance so no result can be relabelled afterwards: a *return engine* (beats the twins on return) and a *loss limiter* (beats them only on risk-adjusted return).

| Field | Frozen value |
| --- | --- |
| Hypothesis | Trend selection within the TSX 60 adds return over random selection of the same number of stocks held for the same days, and the book earns more than cash after 2× costs. |
| Null | Its return is no better than random picks with identical timing, count and holding lengths. |
| Universe | S&P/TSX 60 members, point-in-time as of *t−1*. |
| Book | 60 equal slots, one per possible member. Slot size = 1/60 of book value on the first trading day of each month; unused slots hold cash at the overnight rate. |
| Entry signal | At the close of day *t*: the stock was a member at *t−1*, its signal close is above **both** its 20-day and 50-day simple averages, and CA#1's dial is IN. Buy at the next open if not already held. |
| Exit signal | At the close of day *t*: the close is below either average, **or** CA#1's dial is OUT, **or** the stock has left the TSX 60. Sell at the next open. No stop-loss. |
| Dial | CA#1's definition exactly, whatever CA#1's verdict. |
| Costs | Common rules, per stock, per trade; monthly slot resizing costed. |
| Random twin | For every strategy trade, the twin buys a randomly chosen TSX 60 member eligible on the same entry date and not already held by that twin, for the same number of days at the same slot size. If no eligible name remains, that twin slot holds cash. 1,000 twins; the average overlap between twin and book holdings is reported. |
| Independent event | One dial IN-spell containing at least one trade. Minimum: **8** spells and **100** completed trades in development; **4** spells and **40** trades in validation. |
| Metrics | Book CAGR, MDD, Calmar, trades, average holding days, yearly turnover; equal-weight buy-and-hold TSX 60 reported alongside. |
| Pass as return engine, **both** periods, **1× and 2×** costs | (a) book CAGR above the **95th percentile** of the 1,000 twins; (b) book CAGR at 2× costs above the overnight-rate cash return of the same period; (c) minimums met. |
| Pass as loss limiter (graded only if the return engine is not ENOUGH or WEAK) | Book Calmar above the 95th percentile of twins **and** book MDD ≤ 0.75 × the twins' median MDD, both periods, both cost levels, minimums met. Graded by the common ordered rule and written as "return engine: \[grade\]; loss limiter: \[grade\]". |
| Holdout statistic | CAGR if graded as return engine; Calmar if graded as loss limiter. |
| Data needed | TSX 60 membership, stock prices (signal-adjusted, total return; capital-adjusted highs and lows for costs), Composite closes for the dial, overnight rate. |
