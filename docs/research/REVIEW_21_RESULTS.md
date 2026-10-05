# Review #21 results: the last queue items, E3 support bounce and B3 volume breakout (2026-10-05)

Pre-registration: `REVIEW_21.md`. Code: `src/research/review21.py` (the live Explorer engine, rules C0, replayed on the lake's
5-minute candles for all 120 coins; review #11's code for B3). Output: `~/ananta_lake/reports/review21_results.json`,
trades in `~/ananta_runs/review21/`.

## Data check (LAB10)
E3 reproduces the v0 scorecard exactly: 30 discovery trades, +$0.36 per $100 trade. The engine on lake candles = the engine on the
old database.

## E3, bounce from support (per $100 trade, after costs; excess = minus the random entries of the same trade type)
| | 2018-23: trades / events / net / excess / z | 2024-26: trades / events / net / excess / z | Verdict |
|---|---|---|---|
| LAB10 | 30 / 26 / +$0.36 / +$0.97 / 2.4 | 9 / 9 / -$0.28 / +$0.41 / 0.9 | INSUFFICIENT |
| TOP30 | 45 / 38 / +$0.33 / +$0.84 / 2.7 | 24 / 20 / **-$0.56** / +$0.05 / 0.2 | PASS by the rule, **not tradable** |
| ALL 120 | 165 / 124 / -$0.47 / +$0.23 / 1.0 | 103 / 66 / -$0.76 / -$0.20 / -0.9 | FAIL |

**Reading:** on the 30 coins E3 clears the pre-registered bar (it beats random entries in both periods), but since 2024 it loses
money per trade; it only "passes" because random entries lost more. A setup that loses money after costs is not a candidate,
whatever it beats. E3 stays where it is (an Explorer setup on the 10 live coins, paper evidence) and is not promoted.

## B3, a daily close through a resistance zone on 1.5x volume (and review #11's other variants)
| | LAB10 | TOP30 | ALL 120 |
|---|---|---|---|
| B3 (2018-23 events / excess % / z) | FAIL 84 / +4.8 / 0.9 | FAIL 111 / +10.1 / 1.8 | FAIL 156 / +5.3 / 1.4 |
| A1, B1, B2 | FAIL on every tier | | |
Breakouts on volume are positive on average in both periods on every tier, but never reliably (z under 2.5): the same as review
#11. H09 stays "positive but not reliable".

## The re-test queue of audit v1 is complete
Items 1-6 are done (reviews #15-#18, #19 pending its open-interest download, #21), plus #20 (sizing), #22 (point-in-time
universe, running) and #23 (outside world).
