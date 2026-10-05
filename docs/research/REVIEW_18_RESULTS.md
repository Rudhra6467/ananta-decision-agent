# Review #18 results: stops and crash insurance (2026-10-05)

Pre-registration: `REVIEW_18.md` (35a364a). Code: `src/research/review18.py`; the disaster stop is an option of
`t3_turnover.simulate` (T3-B parity with the paper book unchanged). Output: `~/ananta_lake/reports/review18_results.json`.

## Part A: stops on the short dip trade (TOP30 judged; H07 rows: market events / mean excess % / z / % stopped)
| | 2018-23 | 2024-26 | Verdict |
|---|---|---|---|
| H07, no stop (control) | 33 / +6.2% / 3.6 / 0% | 35 / +3.6% / 3.1 / 0% | PASS |
| H07-S1 structural (10-day low - 1 ATR, median 11-13% away) | 33 / +3.1% / 1.5 / 32% | 35 / +1.3% / 0.9 / 35% | FAIL |
| H07-S2 tight (3%) | 33 / +0.9% / 0.6 / 80% | 35 / -0.6% / -1.0 / 70% | FAIL |
- **H14 is SUPPORTED** on every tier: the structural stop beats the tight stop in both periods (TOP30 +3.1 vs +0.9; +1.3 vs
  -0.6). A 3% stop is hit in 70-85% of dip trades: dips are exactly where tight stops get shaken out (casebook C1, C3).
- **But neither stop is worth adding to H07.** Both cut its edge; the dip trade works by riding out the dip, and its worst
  trades without a stop (-17% to -19% on TOP30) are about the same as with the structural stop (-20%).

## Part B: 25% disaster stop on the trend portfolio (ALL 120 judged)
| | 2018-23 | 2024-26 | Verdict |
|---|---|---|---|
| T3-B (control) | +4,045% / 49.8% / 1.64 | -7.0% / 54.0% / -0.05 | control |
| T3B-D25 | +4,271% / 49.8% / 1.68 | -7.0% / 54.0% / -0.05 | FAIL: no smaller worst fall |
Same on TOP30 and LAB10: identical 2024-26, slightly better 2018-23, identical worst falls.

Crisis windows (ALL 120; buy-and-hold / T3-B / T3B-D25): COVID 2020 -40.9 / -9.0 / -9.0; May 2021 -36.5 / -6.1 / -5.9;
LUNA-3AC 2022 -51.3 / 0.0 / 0.0; FTX 2022 -27.5 / -14.2 / -14.2; Aug 2024 -10.5 / -1.1 / -1.1; Oct 2025 -17.2 / -3.3 / -3.3.

## Reading
1. **The trend portfolio already has its crash insurance: the Bitcoin gate and the 20-day exit.** In the LUNA crash T3-B was
   fully in cash; in every window it lost a fraction of buy-and-hold. A coin 25% under its entry has almost always closed under
   its 20-day average already, so the disaster stop sells on the same day T3 would; it adds nothing to T3.
2. **The 25% disaster stop is still right for live, as a guard, not as a strategy rule.** It costs nothing here, and it protects
   against what a backtest cannot show (a missed daily run, a frozen data feed, an exchange problem). Keep it in the live rules.
3. **Stops and the dip trade:** if a stop is ever required for H07 (live risk rules), use the structural one (H14), sized from
   its distance, never a tight percent stop.
4. FTX 2022 is the worst window for T3-B (-14% to -16% on every tier): a sudden crash inside an allowed market, which no daily
   rule here avoids. That is what the account-level 20% shutdown and the disaster stop are for.

## Changes
None to the running system. The decision chain's INVALIDATION gate already uses H14; its status moves from UNVERIFIED to
SUPPORTED (structural beats tight), with the note that H07 itself works best without a stop.
