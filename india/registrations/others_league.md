# Reference traders against Ananta India (india.others, each evening after the missed-movers review)

Rules others-v1 (22 Oct 2026) in india/others.py. Every number is on live paper sessions only, after our costs, on a Rs 50,000 delivery trip.
HINDSIGHT is the ceiling (the best trips the sessions offered), RANDOM the null, MARKET buy-and-hold of the liquid universe, ANANTA its own research
picks over the same horizon. Coverage counts, among the best 20 rises per horizon, how many Ananta held (TAKEN), only the random control held (CONTROL),
a family fired but did not hold (PASSED), or nothing fired (NOT_COVERED). INFORMED hit rates score each participant's index-futures stance and that
day's change on the next session's Nifty move; Ananta's daily call is scored the same way. Ratings are decision quality, not rupees.

## League, trailing 20 review sessions (through 2026-11-12; 18 sessions)

| H | sessions | HINDSIGHT | MARKET | RANDOM (median) | ANANTA | Ananta pct vs random | TAKEN | CONTROL | PASSED | NOT_COVERED | had a rule | took |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 17 | +4.50% | -0.08% | -0.08% | +0.03% | 51% | 148 | 19 | 48 | 120 | 58% | 44% |
| 5 | 13 | +11.45% | +1.93% | +1.98% | +0.89% | 14% | 151 | 17 | 9 | 83 | 62% | 58% |
| 20 | 0 | | | | | | | | | | | |

## Informed money and Ananta's call, next-session hit rates (last 20 scored sessions)

| who | stance hit rate (n) | flow hit rate (n) | latest |
|---|---|---|---|
| FII | 35% (17) | 62% (16) | 2026-11-12: short -49719 index futures, added longs |
| DII | 65% (17) | 50% (16) | 2026-11-12: long 27148 index futures, added shorts |
| Pro | 35% (17) | 38% (16) | 2026-11-12: short -35374 index futures, added shorts |
| Client | 65% (17) | 31% (16) | 2026-11-12: long 57945 index futures, added shorts |
| ANANTA call | 29% (14) | | 2026-11-12: BEARISH |

## 2026-11-12: best 1-session trips that closed on the day (entry 2026-11-11, 250 eligible, 0 dropped)

| symbol | net | class | why | situation at entry |
|---|---|---|---|---|
| CUPID | +8.40% | TAKEN | held by PULL (signal 2026-10-28) | inside its range in an uptrend |
| POLICYBZR | +7.26% | TAKEN | held by REV (signal 2026-10-21) | rising while below its 200-day average |
| PAYTM | +7.01% | PASSED | BRK fired on 2026-11-12; rejected: no_chase | inside its range in an uptrend |
| KALYANKJIL | +6.80% | TAKEN | held by BRK, PULL, REV (signal 2026-10-23, 2026-10-27, 2026-11-06) | to a 52-week high, on 10.8x its 20-day volume |
| SKYGOLD | +6.39% | TAKEN | held by PULL (signal 2026-10-28) | inside its range in an uptrend |
| ABCAPITAL | +5.55% | PASSED | BRK fired on 2026-11-12; rejected: no_chase | inside its range in an uptrend |
| PINELABS | +5.49% | CONTROL | held only by CTL, the random control draw: luck by construction | rising while below its 200-day average |
| ANANTRAJ | +5.30% | TAKEN | held by REV (signal 2026-11-02) | rising while below its 200-day average |
| PHOENIXLTD | +5.19% | CONTROL | held only by CTL, the random control draw: luck by construction | to a 52-week high |
| MFSL | +5.14% | TAKEN | held by REV (signal 2026-10-22) | rising while below its 200-day average, on 2.1x its 20-day volume |

Ananta's research picks open at 2026-11-11: 133, mean +0.74% to 2026-11-12; random band -0.33% .. +0.41% .. +1.14%; market +0.40%.

## 2026-11-12: best 5-session trips that closed on the day (entry 2026-11-04, 248 eligible, 2 dropped)

| symbol | net | class | why | situation at entry |
|---|---|---|---|---|
| KALYANKJIL | +34.04% | TAKEN | held by BRK, PULL, REV (signal 2026-10-23, 2026-10-27, 2026-11-06) | rebounding from a pullback in an uptrend |
| MOTILALOFS | +19.71% | TAKEN | held by BRK, PULL (signal 2026-10-23, 2026-11-05) | inside its range in an uptrend |
| PNB | +15.42% | TAKEN | held by BRK (signal 2026-10-19) | inside its range in an uptrend |
| MAHABANK | +14.90% | TAKEN | held by BRK (signal 2026-11-05) | inside its range in an uptrend |
| M&M | +14.45% | NOT_COVERED | no family fired in the window | breaking out of a tight 20-day base (7% wide) |
| IIFL | +14.29% | TAKEN | held by BRK (signal 2026-11-11) | rebounding from a pullback in an uptrend |
| DIVISLAB | +14.11% | TAKEN | held by BRK (signal 2026-10-30) | inside its range in an uptrend |
| CUPID | +14.04% | TAKEN | held by PULL (signal 2026-10-28) | inside its range in an uptrend |
| NAVINFLUOR | +13.08% | TAKEN | held by BRK, PULL (signal 2026-10-23, 2026-10-30) | breaking out of a tight 20-day base (14% wide) |
| SKYGOLD | +12.85% | TAKEN | held by PULL (signal 2026-10-28) | rebounding from a pullback in an uptrend |

Ananta's research picks open at 2026-11-04: 114, mean +1.96% to 2026-11-12; random band +1.51% .. +3.45% .. +5.56%; market +3.62%.

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
