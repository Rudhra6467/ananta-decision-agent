# Review #17 results: coin choice filters on T3-B and H07 (2026-10-05)

Pre-registration: `REVIEW_17.md` (7111a0b). Code: `src/research/review17.py`. Output: `~/ananta_lake/reports/review17_results.json`.
Judged on TOP30. Columns: total return % / worst fall % / MAR per period; H07 rows: market events / mean excess % / z.

## T3-B with filters (TOP30, judged)
| | 2018-23 | Jan 2024 - Jul 2026 | Verdict |
|---|---|---|---|
| T3-B (control) | +7,163% / 53.2% / 1.86 | +26.1% / 44.3% / 0.21 | control |
| T3B-RS (relative strength vs BTC) | +2,261% / 43.4% / 1.52 | -1.8% / 40.7% / -0.02 | FAIL: worse in both periods |
| T3B-BR (breadth strong) | +3,356% / 53.2% / 1.44 | **+74.8% / 29.0% / 0.84** | FAIL: worse 2018-23, much better 2024-26 |
Breadth was strong on about a third of days (31% LAB10, 23% ALL).

Reported, not judged: LAB10 (T3-B 2024-26 +15.1%; RS -3.1%; breadth +29.9%, worst fall 32% vs 41%) and ALL 120 (T3-B -7.0%;
RS -28.9%; breadth +35.0%, worst fall 38% vs 54%). The same shape on every tier.

## H07 with filters (TOP30)
| | 2018-23 | 2024-26 | Verdict |
|---|---|---|---|
| H07 (control) | 33 / +6.2% / 3.6 | 35 / +3.6% / 3.1 | PASS (as in review #15) |
| H07-RS | 10 / +0.3% / 0.1 | 9 / +1.3% / 1.0 | INSUFFICIENT (and no better) |
| H07-BR | 2 / -7.7% | 2 / -2.6% | INSUFFICIENT |

## Reading
1. **Relative strength vs Bitcoin hurts.** As a filter on T3 it cut returns in both periods on every tier. Requiring a coin to
   beat Bitcoin removes the alts' catch-up runs, which is where much of T3's profit came from.
2. **Breadth is a trade-off, not an improvement.** Waiting for most of the market to be above its averages cut the worst fall
   sharply in 2024-26 and tripled the return there, but it gave up most of the 2019-21 trend profits by entering late. It fails
   the pre-registered "better in both periods" rule. It is the most interesting failure so far: it looks like a choppy-market
   defence. It is not promoted; testing it again would need a new counted review (and the holdout, untouched since Aug 2026,
   is the only clean third look).
3. **The dip trade cannot be filtered this way.** Dips under RSI 30 rarely happen while a coin is beating Bitcoin or while the
   whole market is strong, so the filtered versions have too few events to judge.
4. H08 and H16 stay observations in the decision chain, as now. Nothing changes in the running system.
