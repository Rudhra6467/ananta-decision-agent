<!-- Registration CA3, frozen from the approved C0 document (rev 24, sha256 3c3b9e939ce3cd71e6b77598af93f81ead1d78a488164fae4b814980733e1e1a). The common rules and validation checks it relies on are frozen in C0_document.md. -->

## CA#3 — The sharp dip

**Question: after a TSX 60 stock falls unusually hard over three days, does buying it at the next open and holding 10 trading days beat buying a random TSX 60 stock on the same day, after costs?** The dip is measured against each stock's own volatility, so no crypto threshold is carried over. Four cells are registered; crypto's finding sat in one cell, and Canada does not presume which.

| Field | Frozen value |
| --- | --- |
| Hypothesis | Volatility-adjusted sharp dips in liquid Canadian large caps are followed by 10-day returns above same-day random entries, in at least one of the four cells. |
| Null | Dip entries earn no more than random TSX 60 entries on the same dates. |
| Universe | S&P/TSX 60 members, point-in-time as of *t−1*. |
| Dip measure | On signal-adjusted closes: R3 = close on *t* ÷ close on *t−3* − 1. σ = standard deviation of the 20 daily returns ending on *t−3* (the last 20 available). z = R3 ÷ (σ × √3). |
| Signal | z ≤ **−2.5** at the close of day *t*. Ignored if *t−3* to *t* contains a capital event, a distribution day or a data gap, or if the stock is already held. |
| Entry and exit | Buy at the open of *t+1*; sell at the open of the 11th trading day after entry (10 trading days held). **No stop-loss.** |
| Sector index for the split | For the stock's sector on day *t* (the 10 or 11 sector indices of that era): the daily-rebalanced equal-weight mean of the signal-adjusted daily returns of that sector's members as of *t−1*, **excluding the signal stock**, chained into an index. Its own z uses the same R3 and σ formula. Fewer than 3 remaining members: the stock-day is excluded from the split and counted. |
| Cells (four, all graded) | Dial state at the signal close (IN or OUT, CA#1's definition) × dip type: **sector-wide** if the sector index's z ≤ **−1.5** on day *t*, else **stock-only**. |
| Costs | Common rules, per trade. |
| Random twin | For each trade, a random TSX 60 member eligible on the same entry date (excluding that day's signal stocks), same open-to-open 10-day hold. 1,000 draws per cell; the statistic is mean net return per trade. |
| Independent event | Clusters, by the common definition, counted per cell. Minimum per cell: **30** in development, **15** in validation. |
| Metrics | Mean and median net return per trade, mean excess over twins, hit rate, worst trade, clusters per cell. |
| Pass per cell, **both** periods, **1× and 2×** costs | (a) mean net return per trade above the **98.75th percentile** of its twins (0.05 split across four cells); (b) mean net return per trade above zero at 2× costs; (c) minimums met. |
| Review verdict | The best cell grade (common rule). A cell graded ENOUGH is named and is the only cell that may ever be discussed for integration. |
| Holdout statistic | Each graded cell's mean net return per trade versus its twins' median. |
| Data needed | TSX 60 membership, sector-index memberships, stock prices (signal-adjusted, total return; capital-adjusted highs and lows for costs), capital-event and distribution days, Composite closes. Without sector membership, the split is NOT RUN and only the two dial cells are graded, at the 97.5th percentile. |
