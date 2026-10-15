<!-- Registration CA1, frozen from the approved C0 document (rev 24, sha256 3c3b9e939ce3cd71e6b77598af93f81ead1d78a488164fae4b814980733e1e1a). The common rules and validation checks it relies on are frozen in C0_document.md. -->

## CA#1 — The market dial

**Question: does holding Canadian stocks only while the S&P/TSX Composite closes above its 200-day average cut losses enough to beat buy-and-hold on risk-adjusted terms, after costs?** A pass earns the label *loss limiter*; it is a profit claim only if its yearly return also matches buy-and-hold, which is reported but not required.

| Field | Frozen value |
| --- | --- |
| Hypothesis | The dial reduces the worst peak-to-trough loss of a broad Canadian stock basket by at least a quarter, and its return per unit of loss beats both buy-and-hold and random timing. |
| Null | The dial's Calmar is no better than random timing with the same number of switches and days in the market. |
| Universe | S&P/TSX Composite members (TSE 300 before May 2002), point-in-time as of *t−1*. |
| Asset | An equal-weight basket of all eligible members, total return, reset to equal weight on the first trading day of each month. Deleted members are sold at the next open after deletion; added members join at the next monthly reset. |
| Signal | At the close of day *t*: **IN** if the Composite's close is above its 200-trading-day simple average of closes; **OUT** otherwise. No buffer, no confirmation days. |
| Entry and exit | IN after OUT: buy the whole basket at the next open. OUT after IN: sell the whole basket at the next open; cash earns the overnight rate. |
| Benchmark | The same basket held always (buy-and-hold), same resets, same costs. Costs do not cancel here: the dial trades more, so its extra switching is charged. |
| Costs | Common rules; every switch costs the one-way cost of every stock in the basket; monthly resets costed in both arms. |
| Random twin | 1,000 circular shifts of the IN/OUT series per period (common rules). |
| Start | 2000-01-04 if 200 prior trading days of Composite closes exist, else the first day that has them. |
| Independent event | One complete OUT-then-IN cycle. Minimum: **8** in development, **4** in validation. |
| Metrics | Maximum drawdown (MDD), compound yearly return (CAGR), Calmar = CAGR / MDD (losing arms ranked last), days in market, switches. |
| Pass, **both** periods, **1× and 2×** costs | (a) dial MDD ≤ 0.75 × buy-and-hold MDD; (b) dial Calmar ≥ buy-and-hold Calmar; (c) dial Calmar above the **95th percentile** of the 1,000 twins; (d) minimums met. |
| Holdout statistic | Calmar. |
| Data needed | Composite closes, Composite membership, stock prices (total return; capital-adjusted highs and lows for costs), Bank of Canada overnight rate. |
