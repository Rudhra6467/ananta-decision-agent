# BT1 results: Low beta and low volatility: do the calmest liquid stocks earn as much as or more than the jumpiest, after costs?

Registered 2026-10-27T13:26:36+00:00 (spec `bt1_v1.json`, written before the run); family portfolio, k = 16, z = 2.96. Development to 2017, validation 2018-2023; nothing from 2024 on.

## In plain words

**Low-beta and low-volatility stocks did not earn more per month on average (all four rows REJECTED), but they compounded better with about half the swings and much smaller falls (reported, not tested).**
- **Monthly net difference (153 months in 2004-17, 72 in 2018-23):** low beta minus high beta -0.05% and +0.62% a month; low beta minus the whole liquid 250 +0.00% and +0.25%; low volatility minus high volatility +0.11% and +0.84%; low volatility minus all -0.28% and +0.12%. None significant.
- **Whole-period picture, net of costs:** the low-beta fifth (average beta 0.55) grew 19.0% a year in 2004-17 and 15.7% in 2018-23, against 12.3% and 2.3% for the high-beta fifth (beta 1.6) and 16.5% and 10.6% for the whole liquid 250; volatility 23% and 16% against 44% and 35%; worst fall -64% and -21% against -76% and -73%. The low-volatility fifth: 15.7% and 14.0% a year, worst fall -56% and -24%.
- **Why the two pictures differ:** the high-risk baskets' big swings drag their compounded growth down even when their average month is similar.
- **What Ananta does with this:** beta is a risk measure, not a return signal. It can say a holding is high-beta (swings harder than the Nifty) and that the calm fifth compounded better here; no rule changes.

## The rows

Verdicts: VALIDATED and CONDITIONAL would be passes; OPPOSITE means significantly the other way round; INCONCLUSIVE means too few independent blocks (16 needed per period) or a reading below the bar.

| variant | expected | verdict | dev mean | dev t | dev blocks | val mean | val t | val blocks | events dev / val |
|---|---|---|---|---|---|---|---|---|---|
| LOWBETA-HIGHBETA|monthly | + | REJECTED | -0.05% | -0.08 | 153 | +0.62% | +0.78 | 72 | 153 / 72 |
| LOWBETA-ALL|monthly | + | REJECTED | +0.00% | +0.01 | 153 | +0.25% | +0.67 | 72 | 153 / 72 |
| LOWVOL-HIGHVOL|monthly | + | REJECTED | +0.11% | +0.19 | 153 | +0.84% | +1.12 | 72 | 153 / 72 |
| LOWVOL-ALL|monthly | + | REJECTED | -0.28% | -0.86 | 153 | +0.12% | +0.35 | 72 | 153 / 72 |

## The baskets, whole period (net of costs)

| comparison | period | basket | CAGR | volatility | CAGR / volatility | max drawdown | avg beta |
|---|---|---|---|---|---|---|---|
| LOWBETA-HIGHBETA|monthly | dev | LOWBETA | +19.01% | +23.30% | +0.82 | -63.62% | +0.55 |
| LOWBETA-HIGHBETA|monthly | dev | HIGHBETA | +12.31% | +44.04% | +0.28 | -75.59% | +1.60 |
| LOWBETA-HIGHBETA|monthly | val | LOWBETA | +15.73% | +16.44% | +0.96 | -20.78% | +0.55 |
| LOWBETA-HIGHBETA|monthly | val | HIGHBETA | +2.30% | +34.80% | +0.07 | -73.36% | +1.59 |
| LOWBETA-ALL|monthly | dev | LOWBETA | +19.01% | +23.30% | +0.82 | -63.62% | +0.55 |
| LOWBETA-ALL|monthly | dev | ALL | +16.45% | +31.69% | +0.52 | -70.48% | +1.04 |
| LOWBETA-ALL|monthly | val | LOWBETA | +15.73% | +16.44% | +0.96 | -20.78% | +0.55 |
| LOWBETA-ALL|monthly | val | ALL | +10.64% | +23.80% | +0.45 | -48.76% | +1.04 |
| LOWVOL-HIGHVOL|monthly | dev | LOWVOL | +15.68% | +20.94% | +0.75 | -56.14% | +0.76 |
| LOWVOL-HIGHVOL|monthly | dev | HIGHVOL | +6.99% | +42.14% | +0.17 | -81.75% | +1.27 |
| LOWVOL-HIGHVOL|monthly | val | LOWVOL | +13.98% | +16.78% | +0.83 | -23.92% | +0.76 |
| LOWVOL-HIGHVOL|monthly | val | HIGHVOL | -1.30% | +33.20% | -0.04 | -76.79% | +1.27 |
| LOWVOL-ALL|monthly | dev | LOWVOL | +15.68% | +20.94% | +0.75 | -56.14% | +0.76 |
| LOWVOL-ALL|monthly | dev | ALL | +16.45% | +31.69% | +0.52 | -70.48% | +1.04 |
| LOWVOL-ALL|monthly | val | LOWVOL | +13.98% | +16.78% | +0.83 | -23.92% | +0.76 |
| LOWVOL-ALL|monthly | val | ALL | +10.64% | +23.80% | +0.45 | -48.76% | +1.04 |
