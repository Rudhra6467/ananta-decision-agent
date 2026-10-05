# Repair-shop review #22 results: the survivorship check (T3-B and H07 on the point-in-time top 30)

Run 2026-10-05 on the pre-registration in `REVIEW_22.md`, unchanged. Results file: `~/ananta_lake/reports/review22_results.json`.

## Data
- PIT30 = for each month, the 30 most-traded Binance spot coins over the 3 months before (earlier data only). 191 coins were
  ever in it; all 191 loaded (98 downloaded for this review, built and quality-checked like the rest).
- One flag: **LUNAUSDT** was re-used by Binance on 2022-05-31 for the new "LUNA 2.0" chain (price jump x180,184). Only the
  history BEFORE the re-use is the coin we mean (Terra, through its collapse and trading halt). Added as `ENDS` in
  `src/lake/research.py` (the loader drops LUNA bars from 2022-05-31 on). No other uncut token swap.
- 155 of the 191 are not in today's top 30 (FTT, LUNA, EOS, XLM, DOT, SHIB and many more).
- Average PIT30 members per day: 26.1 (a coin needs 3 months of history to qualify).

## T3-B on PIT30
| | Discovery (to 2023) | Confirm (2024 - Jul 2026) |
| --- | --- | --- |
| Buy and hold, same PIT30 coins | +21.2%, worst fall 91.7%, MAR 0.03 | -76.0%, worst fall 84.2%, MAR -0.50 |
| T3-B | +1,221.4%, worst fall 61.1%, MAR 0.84 | **-22.5%**, worst fall 44.8%, MAR -0.21 |

T3's rule needs a positive return in both periods: **FAIL** (confirm -22.5%). T3-B lost far less than holding (-22.5% vs -76%)
and fell about half as far, but it did not make money in 2024-26 on the coins that really were the most traded then.
For comparison, on today's top 30 (review #15/#20) T3-B made +26% in the same period: the TOP30 result was survivorship-flattered.

## H07 on PIT30
| | Trades | Market events | Mean net | Mean excess over ordinary uptrend days | z |
| --- | --- | --- | --- | --- | --- |
| Discovery | 134 | 44 | +6.08% | +4.21% | 2.45 |
| Confirm | 102 | 42 | +3.53% | +5.08% | 4.80 |

H07's bar is 30+ discovery events, excess > 0 and z >= 2.5: **FAIL** by a hair (z 2.45). The confirm period is strong
(+5.1% excess, z 4.8). On today's top 30 the discovery figures were +6.0% and z 3.5, so part of that was flattering too.

## What follows (as pre-registered)
- Both 30-coin results are reported as survivorship-flattered. The 30-coin paper books keep running as evidence; neither idea
  is promoted on history. Madhav decides whether to stop a book (recommendation: keep both; they are paper and cost nothing).
- Reading for the agent: on altcoins T3-B means "lose much less in slides", not "make money"; H07 stays PROMISING.
- New question for the queue: the same check for the live 10 (the top 10 as it was each month), because the lab 10 were also
  chosen with today's knowledge.
