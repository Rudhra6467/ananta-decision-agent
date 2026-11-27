# India read model (V0) — data through 2026-11-26, built 2026-11-27T07:57:49+00:00

Rules readmodel-v0-2026-10-22. Every number below traces to the file named in its section of readmodel/latest.json; nothing here is typed by hand.

## Brief

- Through 2026-11-26: Nifty 25,884. Nifty is above both its 50- and 200-day averages: an uptrend; +9.5% from the 50-day, +7.9% from the 200-day; 66% of the liquid 250 are above their 200-day.
- Daily call for the next session: BEARISH (mechanical rule call-v0-2026-10-18); so far 9 of 25 calls right against 15 for the coin flip, one seeded draw (chance alone averages 12.5).
- Stock paper book: 274 open positions; realised Rs +79,014 on the hold_20d exits across campaigns.
- New for the next session: 1 BRK, 5 CTL.
- SP1 index line: Fri 27 Nov: 5 index decisions recorded, traded BANKNIFTY at D0 (long, exit NEXTOPEN) (marked: planned on stale inputs: the US close (QQQ)). Book over 21 scored session(s): NIFTY: 4 scored trade(s), index +60 bp, one option lot Rs 3,393 with realistic fills; BANKNIFTY: 19 scored trade(s) (1 scored late), index +894 bp, one option lot Rs 103,219 with realistic fills.
- Against the reference traders (1 session): Ananta held 12 of the top 20 trips, passed on 1, had no rule for 5; its picks sat at the 61st percentile of random.

## Decisions for the next session

| symbol | campaign | close | why |
|---|---|---|---|
| LODHA | BRK | 1261.2 | 20-session breakout on volume: volume 2.0x its 20-day, +9.0% from the 20-day average, +21.9% from the 200-day, liquidity rank 127 |
| WOCKPHARMA | CTL | 2233.7 | random control: no edge is claimed, it is the yardstick: volume 2.4x its 20-day, +10.7% from the 20-day average, +26.9% from the 200-day, liquidity rank 122 |
| IFCI | CTL | 57.35 | random control: no edge is claimed, it is the yardstick: volume 0.6x its 20-day, -4.3% from the 20-day average, -15.7% from the 200-day, liquidity rank 114 |
| AXISBANK | CTL | 1408.0 | random control: no edge is claimed, it is the yardstick: volume 1.2x its 20-day, +6.8% from the 20-day average, +9.5% from the 200-day, liquidity rank 9 |
| HBLENGINE | CTL | 764.25 | random control: no edge is claimed, it is the yardstick: volume 0.4x its 20-day, -4.3% from the 20-day average, +2.0% from the 200-day, liquidity rank 220 |
| TMPV | CTL | 262.0 | random control: no edge is claimed, it is the yardstick: volume 0.5x its 20-day, -4.3% from the 20-day average, -20.8% from the 200-day, liquidity rank 75 |

## Stock paper book (exec, policy shown: hold_20d)

| campaign | what | open | closed | realised Rs | unrealised Rs | win rate | expectancy R |
|---|---|---|---|---|---|---|---|
| BRK | 20-session breakout on volume | 58 | 23 | -3,208 | +116,185 | 0.34782608695652173 | 0.13463222346549447 |
| CTL | random control: no edge is claimed, it is the yardstick | 85 | 45 | +20,871 | +141,770 | 0.35555555555555557 | 0.10902898285943731 |
| PULL | pullback in an uptrend | 26 | 54 | -51,743 | +36,245 | 0.2777777777777778 | -0.1182613669822863 |
| REV | oversold reversal (RSI under 30, P01) | 22 | 52 | +113,094 | +64,797 | 0.5961538461538461 | 0.625864718507149 |

## SP1 index line

Fri 27 Nov: 5 index decisions recorded, traded BANKNIFTY at D0 (long, exit NEXTOPEN) (marked: planned on stale inputs: the US close (QQQ)). Book over 21 scored session(s): NIFTY: 4 scored trade(s), index +60 bp, one option lot Rs 3,393 with realistic fills; BANKNIFTY: 19 scored trade(s) (1 scored late), index +894 bp, one option lot Rs 103,219 with realistic fills

## Jobs

- autologin: ok
- evening: ok
- evening_zerodha: ok
- factmap: PROBLEM exit 1: no error line in the log tail (that run ended Fri 27 Nov 00:30)
- kitefill: ok
- morning: ok
- morningview: ok
- nightly: ok
- openingview: ok
- paper: ok
- postclose: ok
- preopen: ok
- recorder_noon: ok
- replay: ok
- schedulecheck: ok
- shadowtrader: ok
- sp1paper: ok
- sp1paper.score: ok
- spreads: PROBLEM stuck: running (pid 90039) with no output for 21 h, since Thu 26 Nov 05:01
- studies: ok
- web: ok

Next sign-in: automatic at 20:10 Toronto, 06:40 IST (last automatic sign-in ok Thu 26 Nov 20:10 Toronto); by hand only if it fails, Sun 29 Nov 21:00-22:40 Toronto (07:30-09:10 IST, for the Mon 30 Nov session)

## Research

- studies: {'ready': 53, 'blocked': 11, 'with_results': 40}
- gate G02: {'state': 'BLOCKED', 'waiting_on': 'D15 (wait_time, 30 runs); D16 (wait_time, 30 snapshots); D32 (wait_time, weekly runs)'} counters {'D15': '40 of 30 nightly runs; 25 clean sessions in a row (the gate needs 30 in a row)', 'D16': '34 of 30 snapshots', 'D32': '2026-11-21: knows 17 of 18, unknowns 6 of 7, why 4 of 5, answers and decides 8 of 9, safety 39 of 39, plain words 39 of 39: FAIL; 4 of 8 runs passed'}
- registry verdicts: {'REJECTED': 523, 'OPPOSITE': 169, 'INCONCLUSIVE': 705, 'CONDITIONAL': 40, 'VALIDATED': 47, 'NOT_SUPPORTED_SEEN': 22, 'SUPPORTED_SEEN': 1, 'NOT_CONFIRMED': 5}
- exit book (G01): {'BRK/all': 'sma_close_50', 'BRK/above_both': 'hold_60d', 'BRK/mixed': 'sma_close_50', 'BRK/below_both': None, 'PULL/all': None, 'PULL/above_both': None, 'PULL/mixed': 'hold60+low20', 'PULL/below_both': None, 'ANY/all': None, 'ANY/above_both': None, 'ANY/mixed': None, 'ANY/below_both': 'hold60+low20'}

## Guardrails

Stop for the day at a 5.0% loss; pause new entries when 22.0% below the high-water mark until Madhav resumes — recorded, not enforced (paper); enforcement is W7 live-readiness work
