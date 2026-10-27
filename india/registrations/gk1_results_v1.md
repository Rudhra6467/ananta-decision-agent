# GK1 results: Option Greeks and time decay: does time decay make buying Nifty and Bank Nifty options on expiry day lose more than the index move earns, do longer-dated options do better than the nearest expiry on the same intraday trades, and do options imply bigger moves than the index then makes, by days to expiry?

Registered 2026-10-27T22:35:50+00:00 (spec `gk1_v1.json`, written before the run); family options_eod, k = 46, z = 3.27. Development to 2017, validation 2018-2023; nothing from 2024 on.

## In plain words

**Time decay is real and brutal on expiry day, but it did not pass the strict bar in both periods; and for Ananta's same-day trades the nearest expiry still beat a longer-dated option (OPPOSITE). Options did not systematically imply bigger moves than the index then made.**
- **Buying an at-the-money straddle (call + put) at the open on expiry day, sold at the close, after costs:** Nifty lost 14.7% of the premium on average (315 expiry days), Bank Nifty 16.5% (424). In 2018-23 the loss was 16% and 19% (t -4.7 and -6.2, strong); in 2014-17 about 8% (t -0.7 and -0.6, monthly expiries only for Nifty, too noisy). REJECTED only because the early period is weak. Only about a third of these days were winners.
- **The same straddle three sessions before expiry:** about +0% to +1% a day on average, so expiry day was 12-14% worse in 2014-17 and 20% worse in 2018-23 (t -3.8 and -5.3); REJECTED for the same reason.
- **Nearest against next expiry on the options line's research trades (11,552 in 2015-17, about 23,124 in 2018-23):** the nearest-expiry option made +4.1% of its premium a trade (Rs 164 a lot), the next expiry only +0.8% (Rs 43). OPPOSITE: for a move inside one day, the nearest option's bigger response to the index outweighs its faster decay.
- **Implied against realised moves:** one session before expiry the index moved 3.5% less than the options implied on average, 2-3 sessions out 4.5% less, 4-7 sessions out 4.9% more: no consistent overpricing (all REJECTED). The typical day moved less than implied (median 0.78-0.87 of it), but the occasional big move makes up the average.
- **What Ananta does with this:** never buy options on expiry day to hold for the day; that is the clearest loss in the data. For a same-day trade the options line's nearest-expiry lot stays. No rule changes.

## The rows

Verdicts: VALIDATED and CONDITIONAL would be passes; OPPOSITE means significantly the other way round; INCONCLUSIVE means too few independent blocks (16 needed per period) or a reading below the bar.

| variant | expected | verdict | dev mean | dev t | dev blocks | val mean | val t | val blocks | events dev / val |
|---|---|---|---|---|---|---|---|---|---|
| NIFTY|exp0|straddle_oc | - | REJECTED | -8.24% | -0.73 | 16 | -19.43% | -4.74 | 24 | 47 / 268 |
| BANK|exp0|straddle_oc | - | REJECTED | -8.65% | -0.65 | 16 | -19.36% | -6.17 | 24 | 111 / 313 |
| NIFTY|exp0_vs_exp3|straddle_oc | - | REJECTED | -12.44% | -0.91 | 16 | -20.02% | -3.82 | 24 | 47 / 268 |
| BANK|exp0_vs_exp3|straddle_oc | - | REJECTED | -13.98% | -0.85 | 16 | -20.32% | -5.28 | 24 | 111 / 313 |
| SP1|next_vs_near|ret | + | OPPOSITE | -2.19% | -4.81 | 36 | -4.01% | -9.47 | 72 | 10628 / 23124 |
| ALL|dte1|realised_vs_implied | - | REJECTED | +7.78% | +0.91 | 16 | -6.47% | -1.80 | 24 | 158 / 579 |
| ALL|dte2_3|realised_vs_implied | - | REJECTED | +8.42% | +1.00 | 16 | -8.13% | -2.62 | 24 | 315 / 1149 |
| ALL|dte4_7|realised_vs_implied | - | REJECTED | +12.55% | +1.35 | 16 | +1.83% | +0.47 | 24 | 446 / 1036 |
