# Repair-shop review #16 (pre-registration): do zones still hold on the full crypto universe?

Written 2026-10-05, before any run (audit v1, re-test queue item 2). Madhav, 2026-10-03: "it's always a zone; once we enter the
zone we track it and start the lookout process." Reviews #6 and #7 found, on the lab 10: SWING-NEW, AVERAGE-200 and CONFLUENCE
zones hold more often than random bands of the same width (PASS), and inside a zone F6, "market allowed" (Bitcoin above its
50-day), separates held from broken (PASS, 68% vs 50%).

## Question
On the lake's daily candles, with the code and rules of reviews #6 and #7 unchanged (src/research/zones.py review6 / review7):
1. Do SWING-NEW, AVERAGE-200 and CONFLUENCE still PASS? (All 8 groups are run and reported; only these three are re-tests.)
2. Does F6 still PASS? (All reactions F1-F7 are run and reported; only F6 is a re-test.)

## Data, splits and tiers
- Lake daily candles (review #15 loader: UTC days with 97%+ of their minutes; COCOS and BNX cut at their token swaps; a coin with
  an uncut swap is refused). Discovery before 2024-01-01, confirm 2024-01-01 to 2026-07-31; holdout not loaded.
- LAB10 is the data check: the verdicts should match reviews #6 and #7 (the old runs used daily candles built from 5-minute
  bars; small number differences are expected, a changed verdict is investigated before the wider tiers are read).
- TOP30 and ALL (120) are judged separately.

## Pass rules (unchanged, ZONES_PROGRAM.md section 4 and Amendments 1-2)
Zones: discovery corrected edge >= 8 points, corrected z >= 2.5, 30+ market events; confirm corrected edge > 0. The frozen
random-walk calibration files are used as they are (zones_rw_calibration.json, lookout_rw_calibration.json).
Reactions: the same bar on the held-rate difference with vs without the reaction.

## What follows
- PASS on TOP30 and ALL with LAB10 agreeing: the zone groups and F6 stay "history supports" in the live zone map and the
  decision chain's LOCATION gate, now for the 30-coin tier too.
- PASS on LAB10 only: the zone result is specific to our 10 coins; the live zone map keeps the label for LAB10 only, with a note.
- Nothing is tuned after seeing results; changes are a new, counted review.
