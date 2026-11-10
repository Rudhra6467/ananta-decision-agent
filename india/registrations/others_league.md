# Reference traders against Ananta India (india.others, each evening after the missed-movers review)

Rules others-v1 (22 Oct 2026) in india/others.py. Every number is on live paper sessions only, after our costs, on a Rs 50,000 delivery trip.
HINDSIGHT is the ceiling (the best trips the sessions offered), RANDOM the null, MARKET buy-and-hold of the liquid universe, ANANTA its own research
picks over the same horizon. Coverage counts, among the best 20 rises per horizon, how many Ananta held (TAKEN), only the random control held (CONTROL),
a family fired but did not hold (PASSED), or nothing fired (NOT_COVERED). INFORMED hit rates score each participant's index-futures stance and that
day's change on the next session's Nifty move; Ananta's daily call is scored the same way. Ratings are decision quality, not rupees.

## League, trailing 20 review sessions (through 2026-11-09; 16 sessions)

| H | sessions | HINDSIGHT | MARKET | RANDOM (median) | ANANTA | Ananta pct vs random | TAKEN | CONTROL | PASSED | NOT_COVERED | had a rule | took |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 15 | +4.38% | -0.17% | -0.17% | -0.09% | 49% | 121 | 17 | 39 | 118 | 54% | 41% |
| 5 | 11 | +10.86% | +1.51% | +1.58% | +0.56% | 15% | 126 | 17 | 7 | 70 | 60% | 57% |
| 20 | 0 | | | | | | | | | | | |

## Informed money and Ananta's call, next-session hit rates (last 20 scored sessions)

| who | stance hit rate (n) | flow hit rate (n) | latest |
|---|---|---|---|
| FII | 40% (15) | 57% (14) | 2026-11-09: short -90741 index futures, added longs |
| DII | 60% (15) | 57% (14) | 2026-11-09: long 30457 index futures, added shorts |
| Pro | 40% (15) | 43% (14) | 2026-11-09: short -20475 index futures, added shorts |
| Client | 60% (15) | 36% (14) | 2026-11-09: long 80759 index futures, added shorts |
| ANANTA call | 33% (12) | | 2026-11-09: BEARISH |

## 2026-11-09: best 1-session trips that closed on the day (entry 2026-11-06, 248 eligible, 2 dropped)

| symbol | net | class | why | situation at entry |
|---|---|---|---|---|
| DIVISLAB | +11.76% | TAKEN | held by BRK (signal 2026-10-30) | to a 52-week high |
| ZEEL | +8.68% | TAKEN | held by REV (signal 2026-10-26) | rising while below its 200-day average |
| EXIDEIND | +7.37% | TAKEN | held by REV (signal 2026-11-02) | rising while below its 200-day average |
| SANSERA | +7.26% | TAKEN | held by PULL (signal 2026-10-21) | inside its range in an uptrend, on 2.6x its 20-day volume |
| AEGISLOG | +7.12% | TAKEN | held by PULL (signal 2026-11-05) | rebounding from a pullback in an uptrend |
| DATAPATTNS | +6.44% | TAKEN | held by PULL, REV (signal 2026-10-21, 2026-10-26) | inside its range in an uptrend, on 2.5x its 20-day volume |
| COCHINSHIP | +5.36% | TAKEN | held by REV (signal 2026-10-21) | rising while below its 200-day average |
| UNIONBANK | +4.97% | NOT_COVERED | no family fired in the window | inside its range in an uptrend |
| MANKIND | +4.67% | PASSED | BRK fired on 2026-11-09 and was chosen; no executed trade covered 2026-11-06..2026-11-09 | inside its range in an uptrend |
| LAURUSLABS | +4.57% | TAKEN | held by BRK (signal 2026-10-27) | inside its range in an uptrend |

Ananta's research picks open at 2026-11-06: 125, mean +0.63% to 2026-11-09; random band -0.28% .. +0.50% .. +1.16%; market +0.46%.

## 2026-11-09: best 5-session trips that closed on the day (entry 2026-11-02, 248 eligible, 2 dropped)

| symbol | net | class | why | situation at entry |
|---|---|---|---|---|
| KALYANKJIL | +20.56% | TAKEN | held by BRK, PULL, REV (signal 2026-10-23, 2026-10-27, 2026-11-06) | rebounding from a pullback in an uptrend |
| CARTRADE | +18.86% | TAKEN | held by PULL, REV (signal 2026-10-28) | bouncing from oversold (RSI 23) |
| LODHA | +18.76% | TAKEN | held by REV (signal 2026-10-23) | inside its range in an uptrend, on 2.2x its 20-day volume |
| MOTILALOFS | +18.56% | TAKEN | held by BRK, PULL (signal 2026-10-23, 2026-11-05) | rebounding from a pullback in an uptrend |
| ASHOKLEY | +16.85% | NOT_COVERED | no family fired in the window | rising while below its 200-day average |
| ANGELONE | +16.15% | CONTROL | held only by CTL, the random control draw: luck by construction | rising while below its 200-day average |
| PATANJALI | +15.98% | NOT_COVERED | no family fired in the window | rising while below its 200-day average |
| DIVISLAB | +15.98% | TAKEN | held by BRK (signal 2026-10-30) | to a 52-week high |
| MUTHOOTFIN | +15.62% | TAKEN | held by REV (signal 2026-10-21) | rising while below its 200-day average, on 3.9x its 20-day volume |
| M&M | +14.39% | NOT_COVERED | no family fired in the window | rising while below its 200-day average |

Ananta's research picks open at 2026-11-02: 99, mean +2.85% to 2026-11-09; random band +2.49% .. +4.92% .. +6.74%; market +4.62%.

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
