# Repair-shop review #2: results (learning from other traders' trades)

Pre-registration: `REVIEW_2.md` (commit 0712842). Code c68273f. Run 2026-09-30.
- Data: 7,441 round trips on the 10 coins (5,815 long, 1,626 short) from 37 accounts, September 2024 to July 2026.
- 6 market-maker / HFT accounts were excluded; entries after 2026-08-01 were dropped.
- **Excess** = the signed price move after the entry minus the same coin's average move over that calendar month (drift removed). t-statistics cluster by account-day.

## D1: is there information in their entry timing? Hardly.

| Their long entries | n | Win rate (their exits) | Excess 1h | Excess 4h | Excess 24h | Excess 5d |
|---|---|---|---|---|---|---|
| All accounts | 5,815 | 60% | +0.06% (t 2.9) | +0.06% (t 1.5) | +0.10% (t 0.8) | −0.16% (t −0.8) |
| Leaderboard winners | 188 | 53% | −0.05% | +0.06% | +0.35% (t 1.2) | +0.66% (t 1.2) |
| Random live-tape wallets | 1,211 | 44% | +0.03% | −0.05% | **−0.47% (t −2.7)** | −0.80% (t −1.9) |
| Vaults (automated) | 3,227 | 76% | +0.08% (t 2.6) | +0.08% | +0.15% | −0.07% |

- The only measurable effect is **+0.06% in the first hour**: real but tiny, about a tenth of NDAX costs.
- Random traders buy at bad times.

## D1b: does skill persist (no survivorship)? No.

- Ranked on the **first half** of their trades, the top 8 of 24 eligible accounts showed **no edge in the second half** (longs: 24h excess +0.05%, t 0.2).
- Together they **lost $1.45M** in that second half. Their short entries showed +1.07% excess at 5 days (t 2.0), but we cannot short.

## D3: coverage

- Our v0 setups fired within 2 hours before only **25%** of their long entries, and the same 25% of their *winning* ones.
- When they bought and we did nothing, our state was mostly **BEAR (53%)** with a falling 1h direction (**DOWN 50%**).

## D2: the one clear pattern, they did better buying weakness

Their long entries, mean 24h excess by our context at the moment they bought (all accounts, in-sample):

| Context | Bought weakness | Bought strength |
|---|---|---|
| Our S1 bias | BEAR: **+0.67%** | BULL: −0.41% |
| 4h trend | DOWN: **+0.63%** | UP: −0.35% |
| Daily close vs EMA50 | below: **+0.35%** | above: −0.44% |
| 1h RSI | < 40: **+0.84%** | > 60: −0.29% |
| 15m RSI | < 30: **+1.25%** | > 70: −0.06% |
| Momentum percentile | low: **+0.62%** | high: −0.16% |

This is the **opposite** of v0, whose setups buy strength (trend, momentum, breakout).

## D4 verdict

- 0 of 823 context cells qualified (skilled group, second half, t ≥ 3, n ≥ 150). **S5 is not run**, as pre-registered.
- The D2 pattern comes from **all** accounts in 2024–26 and was not a pre-registered test. It becomes the hypothesis of **review #3**, tested on 2017–2023, which these trades never touched.
