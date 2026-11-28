# India read model (V0) — data through 2026-11-27, built 2026-11-28T07:44:27+00:00

Rules readmodel-v0-2026-10-22. Every number below traces to the file named in its section of readmodel/latest.json; nothing here is typed by hand.

## Brief

- Through 2026-11-27: Nifty 25,607. Nifty is above both its 50- and 200-day averages: an uptrend; +8.1% from the 50-day, +6.7% from the 200-day; 63% of the liquid 250 are above their 200-day.
- Stock paper book: 279 open positions; realised Rs +156,161 on the hold_20d exits across campaigns.
- New for the next session: 2 BRK, 5 CTL, 1 REV.
- SP1 index line: Fri 27 Nov: 5 index decisions recorded, traded BANKNIFTY at D0 (long, exit NEXTOPEN) (marked: planned on stale inputs: the US close (QQQ)). Book over 22 scored session(s): NIFTY: 4 scored trade(s), index +60 bp, one option lot Rs 3,393 with realistic fills; BANKNIFTY: 19 scored trade(s) (1 scored late), index +894 bp, one option lot Rs 103,219 with realistic fills.
- Against the reference traders (1 session): Ananta held 15 of the top 20 trips, passed on 0, had no rule for 1; its picks sat at the 74th percentile of random.

## Decisions for the next session

| symbol | campaign | close | why |
|---|---|---|---|
| DATAPATTNS | BRK | 4336.9 | 20-session breakout on volume: volume 2.6x its 20-day, +6.2% from the 20-day average, +8.2% from the 200-day, liquidity rank 126 |
| RAYMOND | BRK | 1278.6 | 20-session breakout on volume: volume 2.3x its 20-day, +10.3% from the 20-day average, +89.0% from the 200-day, liquidity rank 175 |
| TATAPOWER | REV | 320.05 | oversold reversal (RSI under 30, P01): volume 1.0x its 20-day, -7.3% from the 20-day average, -16.1% from the 200-day, liquidity rank 129 |
| TCS | CTL | 2572.5 | random control: no edge is claimed, it is the yardstick: volume 0.9x its 20-day, +4.3% from the 20-day average, +8.7% from the 200-day, liquidity rank 10 |
| FCL | CTL | 42.7 | random control: no edge is claimed, it is the yardstick: volume 0.4x its 20-day, -11.7% from the 20-day average, +11.1% from the 200-day, liquidity rank 210 |
| WELSPUNLIV | CTL | 285.52 | random control: no edge is claimed, it is the yardstick: volume 0.4x its 20-day, +12.1% from the 20-day average, +68.1% from the 200-day, liquidity rank 215 |
| VBL | CTL | 424.9 | random control: no edge is claimed, it is the yardstick: volume 0.6x its 20-day, +0.0% from the 20-day average, -6.5% from the 200-day, liquidity rank 101 |
| TMCV | CTL | 424.95 | random control: no edge is claimed, it is the yardstick: volume 0.8x its 20-day, -1.2% from the 20-day average, -1.1% from the 200-day, liquidity rank 61 |

## Stock paper book (exec, policy shown: hold_20d)

| campaign | what | open | closed | realised Rs | unrealised Rs | win rate | expectancy R |
|---|---|---|---|---|---|---|---|
| BRK | 20-session breakout on volume | 56 | 26 | +9,908 | +99,623 | 0.4230769230769231 | 0.28204339473105117 |
| CTL | random control: no edge is claimed, it is the yardstick | 84 | 51 | +48,541 | +119,924 | 0.4117647058823529 | 0.26395081547562527 |
| PULL | pullback in an uptrend | 26 | 54 | -51,743 | +52,447 | 0.2777777777777778 | -0.1182613669822863 |
| REV | oversold reversal (RSI under 30, P01) | 16 | 58 | +149,455 | +36,319 | 0.6206896551724138 | 0.7470767605538629 |

## SP1 index line

Fri 27 Nov: 5 index decisions recorded, traded BANKNIFTY at D0 (long, exit NEXTOPEN) (marked: planned on stale inputs: the US close (QQQ)). Book over 22 scored session(s): NIFTY: 4 scored trade(s), index +60 bp, one option lot Rs 3,393 with realistic fills; BANKNIFTY: 19 scored trade(s) (1 scored late), index +894 bp, one option lot Rs 103,219 with realistic fills

## Jobs

- autologin: ok
- evening: ok
- evening_zerodha: ok
- factmap: PROBLEM exit 1: no error line in the log tail (that run ended Sat 28 Nov 00:30)
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
- spreads: ok
- studies: ok
- web: ok

Next sign-in: automatic at 20:10 Toronto, 06:40 IST (last automatic sign-in ok Fri 27 Nov 19:58 Toronto); by hand only if it fails, Sun 29 Nov 21:00-22:40 Toronto (07:30-09:10 IST, for the Mon 30 Nov session)

## Research

- studies: {'ready': 53, 'blocked': 11, 'with_results': 40}
- gate G02: {'state': 'BLOCKED', 'waiting_on': 'D15 (wait_time, 30 runs); D16 (wait_time, 30 snapshots); D32 (wait_time, weekly runs)'} counters {'D15': '41 of 30 nightly runs; 26 clean sessions in a row (the gate needs 30 in a row)', 'D16': '35 of 30 snapshots', 'D32': '2026-11-21: knows 17 of 18, unknowns 6 of 7, why 4 of 5, answers and decides 8 of 9, safety 39 of 39, plain words 39 of 39: FAIL; 4 of 8 runs passed'}
- registry verdicts: {'REJECTED': 523, 'OPPOSITE': 169, 'INCONCLUSIVE': 705, 'CONDITIONAL': 40, 'VALIDATED': 47, 'NOT_SUPPORTED_SEEN': 22, 'SUPPORTED_SEEN': 1, 'NOT_CONFIRMED': 5}
- exit book (G01): {'BRK/all': 'sma_close_50', 'BRK/above_both': 'hold_60d', 'BRK/mixed': 'sma_close_50', 'BRK/below_both': None, 'PULL/all': None, 'PULL/above_both': None, 'PULL/mixed': 'hold60+low20', 'PULL/below_both': None, 'ANY/all': None, 'ANY/above_both': None, 'ANY/mixed': None, 'ANY/below_both': 'hold60+low20'}

## Guardrails

Stop for the day at a 5.0% loss; pause new entries when 22.0% below the high-water mark until Madhav resumes — recorded, not enforced (paper); enforcement is W7 live-readiness work
