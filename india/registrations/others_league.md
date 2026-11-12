# Reference traders against Ananta India (india.others, each evening after the missed-movers review)

Rules others-v1 (22 Oct 2026) in india/others.py. Every number is on live paper sessions only, after our costs, on a Rs 50,000 delivery trip.
HINDSIGHT is the ceiling (the best trips the sessions offered), RANDOM the null, MARKET buy-and-hold of the liquid universe, ANANTA its own research
picks over the same horizon. Coverage counts, among the best 20 rises per horizon, how many Ananta held (TAKEN), only the random control held (CONTROL),
a family fired but did not hold (PASSED), or nothing fired (NOT_COVERED). INFORMED hit rates score each participant's index-futures stance and that
day's change on the next session's Nifty move; Ananta's daily call is scored the same way. Ratings are decision quality, not rupees.

## League, trailing 20 review sessions (through 2026-11-11; 17 sessions)

| H | sessions | HINDSIGHT | MARKET | RANDOM (median) | ANANTA | Ananta pct vs random | TAKEN | CONTROL | PASSED | NOT_COVERED | had a rule | took |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 16 | +4.46% | -0.11% | -0.11% | -0.02% | 49% | 136 | 17 | 44 | 118 | 57% | 43% |
| 5 | 12 | +11.20% | +1.79% | +1.85% | +0.79% | 14% | 136 | 17 | 8 | 79 | 60% | 57% |
| 20 | 0 | | | | | | | | | | | |

## Informed money and Ananta's call, next-session hit rates (last 20 scored sessions)

| who | stance hit rate (n) | flow hit rate (n) | latest |
|---|---|---|---|
| FII | 38% (16) | 60% (15) | 2026-11-11: short -70413 index futures, added longs |
| DII | 62% (16) | 53% (15) | 2026-11-11: long 27152 index futures, added shorts |
| Pro | 38% (16) | 40% (15) | 2026-11-11: short -23747 index futures, added shorts |
| Client | 62% (16) | 33% (15) | 2026-11-11: long 67008 index futures, added shorts |
| ANANTA call | 31% (13) | | 2026-11-11: BEARISH |

## 2026-11-11: best 1-session trips that closed on the day (entry 2026-11-09, 250 eligible, 0 dropped)

| symbol | net | class | why | situation at entry |
|---|---|---|---|---|
| AVALON | +9.55% | TAKEN | held by PULL (signal 2026-10-16) | rebounding from a pullback in an uptrend |
| APOLLO | +9.35% | TAKEN | held by PULL (signal 2026-10-23) | inside its range in an uptrend |
| KALYANKJIL | +8.33% | TAKEN | held by BRK, PULL, REV (signal 2026-10-23, 2026-10-27, 2026-11-06) | breaking above its 20-day range, on 2.5x its 20-day volume |
| NETWEB | +7.91% | TAKEN | held by REV (signal 2026-11-04) | bouncing from oversold (RSI 23) |
| TDPOWERSYS | +6.36% | TAKEN | held by REV (signal 2026-11-06) | bouncing from oversold (RSI 29), on 2.8x its 20-day volume |
| IIFL | +5.88% | PASSED | BRK fired on 2026-11-11 and was chosen; no executed trade covered 2026-11-09..2026-11-11 | inside its range in an uptrend |
| NAVINFLUOR | +5.59% | TAKEN | held by BRK, PULL (signal 2026-10-23, 2026-10-30) | to a 52-week high |
| BANKBARODA | +5.38% | PASSED | BRK fired on 2026-11-11; rejected: no_chase | breaking out of a tight 20-day base (10% wide), on 2.1x its 20-day volume |
| FORCEMOT | +5.11% | PASSED | BRK fired on 2026-11-11; rejected: no_chase | rising while below its 200-day average |
| M&M | +5.00% | PASSED | BRK fired on 2026-11-11; rejected: no_chase | breaking above its 20-day range |

Ananta's research picks open at 2026-11-09: 130, mean +0.89% to 2026-11-11; random band +0.09% .. +0.77% .. +1.51%; market +0.77%.

## 2026-11-11: best 5-session trips that closed on the day (entry 2026-11-03, 248 eligible, 2 dropped)

| symbol | net | class | why | situation at entry |
|---|---|---|---|---|
| KALYANKJIL | +30.28% | TAKEN | held by BRK, PULL, REV (signal 2026-10-23, 2026-10-27, 2026-11-06) | rebounding from a pullback in an uptrend |
| IIFL | +22.62% | PASSED | PULL fired on 2026-11-03; rejected: inside the 14-day re-entry gap | inside its range in an uptrend |
| M&M | +18.84% | NOT_COVERED | no family fired in the window | rising while below its 200-day average |
| WABAG | +15.63% | TAKEN | held by REV (signal 2026-10-23) | inside its range in an uptrend |
| ZEEL | +14.50% | TAKEN | held by REV (signal 2026-10-26) | rising while below its 200-day average |
| MUTHOOTFIN | +14.31% | NOT_COVERED | no family fired in the window | rising while below its 200-day average |
| PATANJALI | +14.30% | NOT_COVERED | no family fired in the window | rising while below its 200-day average |
| MOTILALOFS | +14.11% | TAKEN | held by BRK, PULL (signal 2026-10-23, 2026-11-05) | inside its range in an uptrend, on 2.6x its 20-day volume |
| PNB | +14.08% | TAKEN | held by BRK (signal 2026-10-19) | inside its range in an uptrend |
| ASHOKLEY | +13.51% | NOT_COVERED | no family fired in the window | rising while below its 200-day average |

Ananta's research picks open at 2026-11-03: 109, mean +3.09% to 2026-11-11; random band +3.30% .. +4.85% .. +6.82%; market +4.76%.

## History

| date | status | H1 hindsight / market / Ananta | H5 | H20 | NOT_COVERED keys | drafts |
|---|---|---|---|---|---|---|
| 2026-10-16 | ok |  |  |  | 0 | 0 |
| 2026-10-19 | ok | +2.41% / -1.43% /  |  |  | 3 | 0 |
| 2026-10-21 | ok | +1.69% / -2.17% / -2.10% |  |  | 3 | 0 |
| 2026-10-22 | ok | +1.66% / -1.23% / -1.18% |  |  | 2 | 2 |
| 2026-10-23 | ok | +0.73% / -2.63% / -2.86% |  |  | 2 | 0 |
| 2026-10-24 | no session (weekend) | | | | | |
| 2026-10-25 | no session (weekend) | | | | | |
| 2026-10-26 | ok | +6.41% / +0.91% / +1.21% | +3.44% / -5.02% /  |  | 6 | 0 |
| 2026-10-27 | ok | +6.92% / +0.98% / +1.55% | +6.41% / -2.73% / -3.24% |  | 4 | 0 |
| 2026-10-28 | ok | +4.19% / -0.17% / +0.01% | +8.66% / -0.74% / -1.81% |  | 4 | 2 |
| 2026-10-29 | ok | +4.54% / +0.74% / +0.57% | +10.25% / +1.07% / -0.36% |  | 4 | 0 |
| 2026-10-30 | ok | +3.51% / -1.60% / -1.94% | +13.35% / +2.18% / +2.69% |  | 4 | 0 |
| 2026-10-31 | no session (weekend) | | | | | |
| 2026-11-01 | no session (weekend) | | | | | |
| 2026-11-02 | ok | +6.14% / +1.03% / +0.97% | +11.94% / +2.34% / +1.67% |  | 4 | 2 |
| 2026-11-03 | ok | +5.45% / +0.57% / +0.42% | +9.64% / +2.00% / +0.39% |  | 3 | 0 |
| 2026-11-04 | ok | +6.72% / +1.57% / +1.85% | +11.32% / +3.68% / +0.64% |  | 3 | 0 |
| 2026-11-05 | ok | +6.15% / +1.00% / +0.78% | +13.18% / +4.04% / +0.32% |  | 4 | 0 |
| 2026-11-06 | ok | +3.76% / -0.61% / -1.13% | +16.22% / +5.22% / +2.47% |  | 4 | 2 |
| 2026-11-07 | no session (weekend) | | | | | |
| 2026-11-08 | no session (weekend) | | | | | |
| 2026-11-09 | ok | +5.45% / +0.46% / +0.63% | +15.05% / +4.62% / +2.85% |  | 3 | 0 |
| 2026-11-10 | no session (NSE holiday) | | | | | |
| 2026-11-11 | ok | +5.61% / +0.77% / +0.89% | +14.97% / +4.76% / +3.09% |  | 2 | 0 |
