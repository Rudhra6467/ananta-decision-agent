# DII1 results: Domestic mutual fund cash flows (the largest part of DII): do sharp outflows precede a weaker Nifty, inflows a stronger one, and does DII buying while FII sells cushion the market?

Registered 2026-10-26T17:00:52+00:00 (spec `dii1_v1.json`, written before the run); family flows, k = 22, z = 3.05. Development to 2017, validation 2018-2023; nothing from 2024 on.

## In plain words

**Domestic mutual fund flows do not predict the Nifty's next 1, 5 or 20 sessions, and "funds buying while foreigners sell" is no cushion signal. All 10 versions are REJECTED (bar z 3.05; no |t| above 1.7).**
- **Sharp fund outflow days (298 in 2007-17, 209 in 2018-23) and 5-session spells (290 / 222):** the Nifty did no worse afterwards (every |t| under 1.4).
- **Sharp inflow days (409 / 219) and spells (439 / 215):** no better afterwards.
- **Funds in their top tenth on a day foreigners are in their bottom tenth (123 / 106 days):** over 5 and 20 sessions the Nifty did slightly worse in 2007-17 and better in 2018-23 (+1.0% and +1.6%, t 1.6 and 1.2): the two periods disagree and neither is significant.
- **Descriptive:** fund flows are the mirror of foreign flows (same-session correlation about -0.28 on average, -0.35 to -0.62 every year since 2016). They track the day of the trade's own Nifty move (correlation up to 0.47 before 2019, slightly negative since, as funds have taken to buying the dips) and carry nothing about the next session (about 0.01).
- **Data:** SEBI's Mutual Funds Trends, daily from January 2005, 262 months, each month equal to the page's own total; the mutual funds are the largest part of DII, insurers and banks are not in it. Rows used from the session after the trading day.
- **What Ananta does with this:** nothing changes in the paper rules. 'DIIs are buying' is context, as 'FIIs are selling' is (FII1).

## The rows

Verdicts: VALIDATED and CONDITIONAL would be passes; OPPOSITE means significantly the other way round in development and the same way in 2018-23; INCONCLUSIVE means too few independent blocks (16 needed per period) or a reading below the bar.

| variant | expected | verdict | dev mean | dev t | dev blocks | val mean | val t | val blocks | events dev / val |
|---|---|---|---|---|---|---|---|---|---|
| neg5|nfwd1 | - | REJECTED | -0.00% | -0.00 | 33 | -0.03% | -0.28 | 16 | 290 / 222 |
| neg5|nfwd5 | - | REJECTED | -0.40% | -1.19 | 33 | -0.04% | -0.13 | 16 | 290 / 222 |
| neg5|nfwd20 | - | REJECTED | -0.54% | -0.69 | 33 | +0.32% | +0.36 | 16 | 290 / 222 |
| neg1|nfwd1 | - | REJECTED | -0.04% | -0.50 | 41 | -0.09% | -0.66 | 23 | 298 / 209 |
| neg1|nfwd5 | - | REJECTED | -0.37% | -1.35 | 41 | -0.17% | -0.53 | 23 | 298 / 209 |
| pos5|nfwd5 | + | REJECTED | +0.57% | +0.96 | 37 | -0.25% | -0.44 | 20 | 439 / 215 |
| pos5|nfwd20 | + | REJECTED | -0.76% | -0.61 | 37 | +0.63% | +0.62 | 20 | 439 / 215 |
| pos1|nfwd1 | + | REJECTED | +0.01% | +0.12 | 44 | +0.09% | +0.76 | 23 | 409 / 219 |
| diibuy_fiisell|nfwd5 | + | REJECTED | -0.36% | -0.68 | 34 | +1.02% | +1.65 | 19 | 123 / 106 |
| diibuy_fiisell|nfwd20 | + | REJECTED | -0.73% | -0.55 | 34 | +1.58% | +1.24 | 19 | 123 / 106 |

## Descriptive: how mutual fund flows line up with the Nifty and with foreign flows

| year | corr same session | corr with previous session's return | corr with next session's return | corr with FPI same session | days |
|---|---|---|---|---|---|
| 2006 | -0.028 | -0.004 | 0.04 | -0.254 | 249 |
| 2007 | 0.009 | 0.286 | -0.003 | -0.09 | 245 |
| 2008 | 0.049 | 0.16 | 0.064 | -0.259 | 243 |
| 2009 | 0.039 | 0.472 | 0.037 | -0.004 | 242 |
| 2010 | -0.011 | 0.274 | 0.025 | -0.282 | 243 |
| 2011 | 0.07 | 0.231 | 0.002 | -0.191 | 239 |
| 2012 | -0.004 | 0.26 | 0.152 | 0.007 | 241 |
| 2013 | 0.141 | 0.101 | 0.037 | -0.358 | 238 |
| 2014 | -0.001 | 0.038 | 0.002 | -0.188 | 235 |
| 2015 | 0.122 | -0.01 | 0.048 | -0.094 | 241 |
| 2016 | 0.03 | 0.101 | 0.048 | -0.482 | 241 |
| 2017 | 0.025 | 0.074 | 0.039 | -0.416 | 242 |
| 2018 | -0.019 | 0.247 | -0.03 | -0.35 | 240 |
| 2019 | -0.056 | -0.011 | -0.016 | -0.356 | 242 |
| 2020 | -0.128 | -0.116 | -0.103 | -0.398 | 245 |
| 2021 | 0.184 | -0.052 | -0.011 | -0.426 | 241 |
| 2022 | -0.051 | -0.092 | -0.108 | -0.615 | 244 |
| 2023 | 0.002 | -0.031 | -0.002 | -0.291 | 240 |
