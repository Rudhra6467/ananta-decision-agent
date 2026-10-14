# Review #27 results (Oct 11, 2026): stops for dip-style buys

Rules as pre-registered in REVIEW_27.md. 120 lake coins, daily candles from 2018, tiers A and B, NDAX costs, 10-day time exit.
Average net % per trade (win rate) for 2018-2023 | 2024-Oct 2026.

| Entry | Exit | Trades | 2018-2023 | 2024-2026 |
| --- | --- | --- | --- | --- |
| Dip trade (H07) | Tight stop (1 ATR) | 147 / 178 | +0.54% (38%) | +0.35% (40%) |
| Dip trade (H07) | Structural stop | 147 / 178 | +0.35% (35%) | -0.88% (37%) |
| Dip trade (H07) | Disaster stop (-15%) | 147 / 178 | +1.19% (46%) | -0.22% (47%) |
| Dip trade (H07) | **No stop** | 147 / 178 | **+6.48% (55%)** | **+2.38% (58%)** |
| 200-day touch | Tight stop | 748 / 778 | -1.51% (31%) | -2.86% (25%) |
| 200-day touch | Structural stop | 748 / 778 | -0.96% (37%) | -3.43% (29%) |
| 200-day touch | Disaster stop | 748 / 778 | -0.69% (40%) | -3.35% (33%) |
| 200-day touch | No stop | 748 / 778 | -0.07% (43%) | -2.86% (37%) |

**Verdict.** Dip trade: NO STOP passes (better than the tight stop in both periods, 76 and 83 market days). The brain's DIP exit plan
now exits by time only; the stop it writes is kept as the invalidation point. 200-day touch: nothing passes, and every variant loses
money in 2024-2026: touching the zone is not by itself a reason to buy (consistent with review #7). Zone-touch stops stay as they are;
the zone-touch watch's own scoreboard decides its future.

**Why it matters live.** All 26 closed brain and zone-touch paper trades ended at their stop in one dip (Oct 7-8). For dips, a tight
stop sells at the low. For live money the account-level brakes (D12) replace the per-trade stop on dip buys.

Files: src/research/review27.py, docs/research/review27.json.
