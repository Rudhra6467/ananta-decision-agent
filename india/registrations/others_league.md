# Reference traders against Ananta India (india.others, each evening after the missed-movers review)

Rules others-v1 (22 Oct 2026) in india/others.py. Every number is on live paper sessions only, after our costs, on a Rs 50,000 delivery trip.
HINDSIGHT is the ceiling (the best trips the sessions offered), RANDOM the null, MARKET buy-and-hold of the liquid universe, ANANTA its own research
picks over the same horizon. Coverage counts, among the best 20 rises per horizon, how many Ananta held (TAKEN), only the random control held (CONTROL),
a family fired but did not hold (PASSED), or nothing fired (NOT_COVERED). INFORMED hit rates score each participant's index-futures stance and that
day's change on the next session's Nifty move; Ananta's daily call is scored the same way. Ratings are decision quality, not rupees.

## League, trailing 20 review sessions (through 2026-11-16; 20 sessions)

| H | sessions | HINDSIGHT | MARKET | RANDOM (median) | ANANTA | Ananta pct vs random | TAKEN | CONTROL | PASSED | NOT_COVERED | had a rule | took |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 19 | +4.36% | -0.17% | -0.16% | -0.07% | 51% | 174 | 21 | 51 | 129 | 60% | 46% |
| 5 | 15 | +11.40% | +1.87% | +1.92% | +0.98% | 19% | 187 | 17 | 9 | 87 | 65% | 62% |
| 20 | 0 | | | | | | | | | | | |

## Informed money and Ananta's call, next-session hit rates (last 20 scored sessions)

| who | stance hit rate (n) | flow hit rate (n) | latest |
|---|---|---|---|
| FII | 37% (19) | 56% (18) | 2026-11-16: short -56687 index futures, added shorts |
| DII | 63% (19) | 50% (18) | 2026-11-16: long 22464 index futures, added shorts |
| Pro | 37% (19) | 44% (18) | 2026-11-16: short -24161 index futures, added longs |
| Client | 63% (19) | 39% (18) | 2026-11-16: long 58384 index futures, added shorts |
| ANANTA call | 31% (16) | | 2026-11-16: BEARISH |

## 2026-11-16: best 1-session trips that closed on the day (entry 2026-11-13, 250 eligible, 0 dropped)

| symbol | net | class | why | situation at entry |
|---|---|---|---|---|
| MAXHEALTH | +6.30% | TAKEN | held by REV (signal 2026-10-19) | breaking above its 20-day range |
| FORTIS | +4.75% | TAKEN | held by REV (signal 2026-10-21) | rising while below its 200-day average |
| ASTERDM | +3.43% | TAKEN | held by BRK (signal 2026-11-04) | inside its range in an uptrend |
| ITC | +3.25% | PASSED | BRK fired on 2026-11-16; rejected: no_chase | rising while below its 200-day average |
| TATACONSUM | +3.19% | NOT_COVERED | no family fired in the window | rising while below its 200-day average |
| LICHSGFIN | +3.11% | PASSED | BRK fired on 2026-11-16; rejected: no_chase | breaking above its 20-day range |
| YESBANK | +3.07% | TAKEN | held by REV (signal 2026-11-02) | rising while below its 200-day average |
| RAYMOND | +2.82% | TAKEN | held by PULL (signal 2026-10-21) | inside its range in an uptrend |
| APOLLOHOSP | +2.58% | CONTROL | held only by CTL, the random control draw: luck by construction | inside its range in an uptrend |
| GMRAIRPORT | +2.45% | TAKEN | held by BRK (signal 2026-11-11) | inside its range in an uptrend |

Ananta's research picks open at 2026-11-13: 141, mean -1.18% to 2026-11-16; random band -1.82% .. -0.90% .. -0.25%; market -1.02%.

## 2026-11-16: best 5-session trips that closed on the day (entry 2026-11-06, 248 eligible, 2 dropped)

| symbol | net | class | why | situation at entry |
|---|---|---|---|---|
| KALYANKJIL | +19.56% | TAKEN | held by BRK, PULL, REV (signal 2026-10-23, 2026-10-27, 2026-11-06) | breaking out of a tight 20-day base (15% wide), on 5.5x its 20-day volume |
| PNB | +13.86% | TAKEN | held by BRK (signal 2026-10-19) | inside its range in an uptrend |
| APOLLO | +13.43% | TAKEN | held by BRK, PULL (signal 2026-10-23, 2026-11-11) | inside its range in an uptrend |
| LICHSGFIN | +12.57% | NOT_COVERED | no family fired in the window | rising while below its 200-day average |
| ZEEL | +11.63% | TAKEN | held by REV (signal 2026-10-26) | rising while below its 200-day average |
| POLICYBZR | +11.47% | TAKEN | held by REV (signal 2026-10-21) | rising while below its 200-day average |
| DATAPATTNS | +10.82% | TAKEN | held by PULL, REV (signal 2026-10-21, 2026-10-26) | inside its range in an uptrend, on 2.5x its 20-day volume |
| POWERINDIA | +10.76% | TAKEN | held by BRK, REV (signal 2026-10-22, 2026-11-13) | rising while below its 200-day average |
| MFSL | +10.74% | TAKEN | held by REV (signal 2026-10-22) | rising while below its 200-day average |
| MOTILALOFS | +10.05% | TAKEN | held by BRK, PULL (signal 2026-10-23, 2026-11-05) | to a 52-week high |

Ananta's research picks open at 2026-11-06: 125, mean +2.06% to 2026-11-16; random band -0.43% .. +1.35% .. +2.96%; market +1.22%.

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
| 2026-11-12 | ok | +5.18% / +0.40% / +0.74% | +14.46% / +3.62% / +1.96% |  | 4 | 2 |
| 2026-11-13 | ok | +3.60% / -0.75% / -0.53% | +11.10% / +1.74% / +0.98% |  | 3 | 0 |
| 2026-11-14 | no session (weekend) | | | | | |
| 2026-11-15 | no session (weekend) | | | | | |
| 2026-11-16 | ok | +2.72% / -1.02% / -1.18% | +10.95% / +1.22% / +2.06% |  | 4 | 0 |
