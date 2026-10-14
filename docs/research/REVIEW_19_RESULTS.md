# Repair-shop review #19 results: buying pressure, funding, open interest

Run 2026-10-05 on the pre-registration in `REVIEW_19.md`, unchanged. Results file: `~/ananta_lake/reports/review19_results.json`.
Judged on TOP30 (today's top 30, as pre-registered; note review #22 found this tier flatters both ideas). Futures data from
Binance Data Vision: funding for every coin with a futures market, open interest for the top 30 (from Sep 2020).

## T3 filters (must pass T3's rules AND beat T3-B's MAR in both periods)
| Variant | Discovery return, worst fall, MAR | Confirm return, worst fall, MAR | Verdict |
| --- | --- | --- | --- |
| T3-B (control) | +7,163%, 53.2%, 1.86 | +26.1%, 44.3%, 0.21 | control |
| T3B-TB (held only while buying pressure is high) | +2,474%, 51.8%, 1.32 | +49.3%, 38.4%, 0.44 | FAIL (worse MAR before 2024) |
| T3B-F (not held while crowded long) | +1,709%, 53.2%, 1.11 | -25.3%, 39.1%, -0.27 | FAIL |

## H07 filters (must pass H07's bar AND beat plain H07's excess in both periods)
| Variant | Discovery events, excess, z | Confirm events, excess, z | Verdict |
| --- | --- | --- | --- |
| H07 (control) | 33, +6.16%, 3.57 | 35, +3.56%, 3.07 | control |
| H07-TB (buying pressure high) | 14, +5.76%, 2.25 | 15, +3.22%, 2.04 | FAIL (too few events) |
| H07-F (not crowded long) | 31, +6.15%, 3.39 | 34, +3.97%, 3.26 | FAIL (discovery excess 0.01 short) |
| H07-OI (leverage flushed) | 33, +6.36%, 3.70 | 32, +3.48%, 3.69 | FAIL (confirm excess 0.08 short) |

## Reading
- Nothing passes. The same pattern as breadth in review #17: buying pressure helps T3-B in 2024-26 (+49% vs +26%, smaller
  fall) but costs two thirds of the gain before 2024. A filter that only helps in one period is not a rule.
- Crowded funding as an exit hurts T3-B in both periods: crowded markets kept rising more often than not.
- The H07 filters change almost nothing: H07's edge comes from the dip itself, not from futures positioning.
- LAB10 and ALL tiers (reported, not judged) agree: no filter is better in both periods.

## What follows
Funding, open interest and taker buy share stay in the lake and in the agent's context (shown as information, never used to
decide). Audit rows U01-U03: tested, FAIL.
