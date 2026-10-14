# Review #23 results: US markets, the dollar, stress and crypto sentiment (2026-10-05)

Pre-registration: `REVIEW_23.md` (8379e36). Code: `src/research/review23.py`, data `src/lake/macro.py`. Output:
`~/ananta_lake/reports/review23_results.json`. Judged on TOP30: total return % / worst fall % / MAR; share of days the filter allowed.

**Run 1 was invalid and is not counted as a result:** a date conversion bug (pandas date resolution) put every macro value in
early 1970, so each filter only ever saw the latest value (Nasdaq and VIX allowed 100% of days, the dollar 0%). Found because the
numbers were impossible; fixed in `macro.py`, data re-pulled, dates checked by hand (COVID and June 2022 show Nasdaq under its
200-day and VIX high), then run 2 below. Run 1's log is kept as `review23_run1_INVALID_dates.log`. Variants unchanged.

## Trend portfolio filters (TOP30)
| | Days allowed | 2018-23 | Jan 2024 - Jul 2026 | Verdict |
|---|---|---|---|---|
| T3-B (control) | | +7,163% / 53.2% / 1.86 | +26.1% / 44.3% / 0.21 | control |
| T3B-NQ (Nasdaq above its 200-day) | 80% | +7,860% / 54.4% / 1.87 | +8.2% / 52.3% / 0.06 | FAIL |
| T3B-USD (dollar under its 50-day) | 47% | +271% / 53.1% / 0.44 | -32.1% / 35.4% / -0.39 | FAIL (badly) |
| T3B-VIX (VIX under 25) | 84% | +4,286% / 53.2% / 1.57 | +24.0% / 45.2% / 0.19 | FAIL |
| T3B-FG (not in extreme greed) | 95% | +1,606% / 53.2% / 1.08 | -28.8% / 43.7% / -0.28 | FAIL (badly) |
The same verdicts on LAB10 and on all 120 coins.

## Dip trade in fear
| | 2018-23 | 2024-26 | Verdict |
|---|---|---|---|
| H07 (control) | 33 events / +6.2% / z 3.6 | 35 / +3.6% / 3.1 | PASS |
| H07-FG (Fear & Greed 30 or lower) | 15 / +6.2% / 1.9 | 11 / +2.9% / 1.6 | INSUFFICIENT (no better) |

## Reading
1. **Crypto's own trend beats the outside world as a gate.** Bitcoin above its 50-day (already in T3) does the job; adding the
   Nasdaq, the dollar or VIX on top only removed good days. US risk-on and crypto risk-on overlap, but crypto turns first.
2. **Selling into extreme greed is the worst idea tested today.** Extreme greed happens in the strongest part of a trend; leaving
   then cut 2018-23 profits by three quarters and turned 2024-26 negative. "Be fearful when others are greedy" does not apply to
   a trend system.
3. **Dips in fear** were about as good as all dips but too few to judge.
4. These series stay as **context** for the agent (what the wider world is doing), labelled "tested, does not improve our rules".
