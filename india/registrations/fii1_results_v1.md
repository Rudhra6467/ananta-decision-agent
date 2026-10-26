# FII1 results: Foreign investor (FPI) cash flows: do sharp outflows precede a weaker Nifty, and inflows a stronger one?

Registered 2026-10-26T15:31:11+00:00 (spec `fii1_v1.json`, written before the run); family flows, k = 12, z = 2.87. Development to 2017, validation 2018-2023; nothing from 2024 on.

## In plain words

**Foreign investor flows, as NSDL reports them, do not predict the Nifty's next 1, 5 or 20 sessions.**
- **Sharp outflow days (442 in 2003-17, 221 in 2018-23) and weeks (464 / 209):** the Nifty did no worse afterwards (REJECTED, every |t| under 1.4).
- **Sharp inflow days (408 / 208) and weeks (407 / 202):** the Nifty did no better (REJECTED).
- **TWT-H48 (descriptive):** the day's flow barely moves with the same day's Nifty: 0.04% per standard deviation of flow before 2017, 0.05% after, with no change across the SIP era (t 0.2).
- **Flows follow the price:** most years the flow correlates 0.2-0.46 with the PREVIOUS session's Nifty return and about zero with the next one. Part of this is NSDL's reporting date sitting a day after the trade, but either way the flows trail the market rather than lead it.

## The rows

Verdicts: VALIDATED and CONDITIONAL would be passes; OPPOSITE means significantly the other way round in 2000/2003-2017 and the same way in 2018-23; INCONCLUSIVE means too few independent blocks (16 needed per period) or a reading below the bar.

| variant | expected | verdict | dev mean | dev t | dev blocks | val mean | val t | val blocks | events dev / val |
|---|---|---|---|---|---|---|---|---|---|
| neg5|nfwd1 | - | REJECTED | -0.07% | -0.68 | 38 | +0.19% | +1.37 | 20 | 464 / 209 |
| neg5|nfwd5 | - | REJECTED | -0.06% | -0.15 | 38 | +0.24% | +0.44 | 20 | 464 / 209 |
| neg5|nfwd20 | - | REJECTED | +0.09% | +0.09 | 38 | +1.31% | +1.20 | 20 | 464 / 209 |
| neg1|nfwd1 | - | REJECTED | +0.13% | +1.24 | 48 | +0.08% | +0.68 | 22 | 442 / 221 |
| neg1|nfwd5 | - | REJECTED | +0.40% | +1.17 | 48 | +0.23% | +0.61 | 22 | 442 / 221 |
| pos5|nfwd5 | + | REJECTED | +0.05% | +0.19 | 39 | -0.58% | -1.56 | 19 | 407 / 202 |
| pos5|nfwd20 | + | REJECTED | -1.22% | -1.38 | 39 | -0.68% | -0.54 | 18 | 407 / 202 |
| pos1|nfwd1 | + | REJECTED | +0.04% | +0.43 | 50 | -0.01% | -0.13 | 24 | 408 / 208 |

## TWT-H48, descriptive: how much the Nifty moves with same-day FPI flows

Mean yearly beta (Nifty % move per one trailing standard deviation of the day's FPI net flow): 2003-2016 0.04, 2017-2023 0.051 (Welch t across years 0.22).

| year | beta % per SD | corr same day | corr with previous day's return | corr with next day's return | days |
|---|---|---|---|---|---|
| 2004 | 0.15 | 0.134 | 0.177 | 0.048 | 253 |
| 2005 | 0.045 | 0.047 | 0.231 | -0.06 | 251 |
| 2006 | 0.042 | 0.029 | 0.274 | 0.024 | 249 |
| 2007 | 0.05 | 0.044 | 0.348 | -0.011 | 245 |
| 2008 | 0.241 | 0.065 | 0.421 | -0.045 | 243 |
| 2009 | -0.113 | -0.059 | 0.232 | 0.01 | 242 |
| 2010 | 0.019 | 0.022 | 0.395 | 0.096 | 243 |
| 2011 | 0.137 | 0.073 | 0.459 | -0.071 | 239 |
| 2012 | -0.158 | -0.18 | 0.218 | 0.024 | 241 |
| 2013 | -0.062 | -0.056 | 0.274 | -0.071 | 238 |
| 2014 | 0.08 | 0.108 | 0.242 | 0.015 | 235 |
| 2015 | 0.022 | 0.026 | 0.14 | -0.066 | 241 |
| 2016 | 0.072 | 0.064 | 0.301 | 0.013 | 241 |
| 2017 | 0.024 | 0.054 | 0.07 | -0.01 | 242 |
| 2018 | 0.018 | 0.021 | 0.123 | 0.078 | 240 |
| 2019 | 0.039 | 0.055 | 0.233 | -0.055 | 242 |
| 2020 | 0.222 | 0.143 | 0.257 | 0.105 | 245 |
| 2021 | -0.125 | -0.118 | 0.323 | -0.158 | 241 |
| 2022 | 0.071 | 0.073 | 0.45 | 0.06 | 244 |
| 2023 | 0.111 | 0.184 | 0.334 | 0.109 | 240 |
