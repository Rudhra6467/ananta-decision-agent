# Review #16 results: zones on the full crypto universe (2026-10-05)

Pre-registration: `REVIEW_16.md` (f6e556d). Code: reviews #6/#7 unchanged (`src/research/zones.py`), run through
`src/lake/research.review16`. Output: `~/ananta_lake/reports/review16_results.json`. Zone entries: 6,451 (LAB10), 12,337
(TOP30), 33,358 (ALL 120). Numbers: market events / held % vs random % / corrected edge (points) / corrected z.

## LAB10 data check: two verdicts changed, the data did not
SWING-NEW and F6 reproduce review #6/#7. AVERAGE-200 and CONFLUENCE fell from just above the bar to just below it
(AVERAGE-200 z 3.49 -> 2.38, CONFLUENCE edge 8.9 -> 7.3) on the same events (102 vs 101; 190 vs 189). Investigated before
reading the wider tiers: the lake's daily candles match the old ones (closes identical on 8 of 10 coins, under 0.6% apart on
BTC/ETH); the one difference is that the lake leaves out incomplete days (exchange outages, 11-54 per coin) that the old
5-minute build kept. So no data error: those two passes were fragile, close enough to the bar that 1% fewer days moved them.

## Zones (re-tests: SWING-NEW, AVERAGE-200, CONFLUENCE)
| Group | LAB10 | TOP30 | ALL 120 |
|---|---|---|---|
| **New swing zone (SWING-NEW)** | PASS 172 / 59 vs 59 / +9.7 / 2.8 | PASS 215 / +10.0 / 3.4 | **PASS** 273 / +10.3 / **4.4**; confirm +9.2 |
| **200-day average** | FAIL (z 2.38) | PASS 140 / +10.1 / 2.7 | **PASS** 195 / +12.3 / **4.4**; confirm +12.6 |
| Confluence | FAIL (edge 7.3) | FAIL (edge 7.9, z 3.2) | FAIL (edge 7.8, z 3.6) |
| 50-day average (not a re-test) | FAIL | PASS (+9.5, z 2.9) | FAIL (edge 8.0, z 2.4) |
| Swing tested / strong, 52-week low, base | FAIL on every tier | | |

## The lookout (re-test: F6, market allowed = Bitcoin above its 50-day)
| | LAB10 | TOP30 | ALL 120 |
|---|---|---|---|
| F6 held with vs without (discovery) | 68% vs 50%, +23 pts, z 4.6 | 68% vs 50%, +24, z 5.2 | **69% vs 53%, +21, z 4.4** |
| F6 confirm (2024-Jul 2026) | +7.9 pts | +6.7 | +7.4 |
| F1-F5, F7 | FAIL on every tier | | |

## Reading
1. **New swing zones and the 200-day average are confirmed on full data**, and get stronger with more coins (z 4.4 on 120).
2. **Confluence no longer passes.** It is consistently 7-9 points better than random with a high z, but misses the
   pre-registered 8-point size bar on every tier. Under the rules it loses "history supports".
3. **F6 (market allowed) holds everywhere.** It is the one reaction inside a zone that separates held from broken; its edge is
   much smaller since 2024 (+7 points vs +21-24 before).
4. The 50-day average passing on TOP30 is a new observation, not a re-test; it is not promoted (a counted review would have to
   test it on its own).
5. Same caution as review #6: entering a zone is not a trade; these are hold rates, not profits.

## Open (Madhav)
- Update the live zone map and the decision chain's LOCATION gate: keep SWING-NEW and AVERAGE-200 as "history supports",
  drop CONFLUENCE to "watched, not supported" (yes / no). Nothing is changed in the running system until then.
