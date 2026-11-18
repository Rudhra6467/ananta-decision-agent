# India read model (V0) — data through 2026-11-17, built 2026-11-18T07:57:42+00:00

Rules readmodel-v0-2026-10-22. Every number below traces to the file named in its section of readmodel/latest.json; nothing here is typed by hand.

## Brief

- Through 2026-11-17: Nifty 25,387. Nifty is above both its 50- and 200-day averages: an uptrend; +8.5% from the 50-day, +5.8% from the 200-day; 66% of the liquid 250 are above their 200-day.
- Daily call for the next session: BEARISH (mechanical rule call-v0-2026-10-18); so far 6 of 20 calls right against 12 for the coin flip, one seeded draw (chance alone averages 10).
- Stock paper book: 243 open positions; realised Rs -263,060 on the hold_20d exits across campaigns.
- New for the next session: 2 BRK, 5 CTL, 1 PULL.
- SP1 index line: Wed 18 Nov: 5 index decisions recorded, traded BANKNIFTY at D0 (long, exit NEXTOPEN). Book over 16 scored session(s): NIFTY: 3 scored trade(s), index +71 bp, one option lot Rs 5,637 with realistic fills; BANKNIFTY: 15 scored trade(s) (1 scored late), index +482 bp, one option lot Rs 38,737 with realistic fills.
- Against the reference traders (1 session): Ananta held 10 of the top 20 trips, passed on 2, had no rule for 5; its picks sat at the 42nd percentile of random.

## Decisions for the next session

| symbol | campaign | close | why |
|---|---|---|---|
| DELHIVERY | BRK | 457.95 | 20-session breakout on volume: volume 2.3x its 20-day, +11.5% from the 20-day average, +2.9% from the 200-day, liquidity rank 222 |
| CANBK | BRK | 134.0 | 20-session breakout on volume: volume 2.1x its 20-day, +8.9% from the 20-day average, +1.6% from the 200-day, liquidity rank 103 |
| APARINDS | PULL | 14171.0 | pullback in an uptrend: volume 0.8x its 20-day, -5.6% from the 20-day average, +3.3% from the 200-day, liquidity rank 85 |
| BANKINDIA | CTL | 159.28 | random control: no edge is claimed, it is the yardstick: volume 2.1x its 20-day, +14.0% from the 20-day average, +9.4% from the 200-day, liquidity rank 220 |
| MTARTECH | CTL | 5709.5 | random control: no edge is claimed, it is the yardstick: volume 0.6x its 20-day, -9.9% from the 20-day average, +33.9% from the 200-day, liquidity rank 7 |
| SUZLON | CTL | 37.19 | random control: no edge is claimed, it is the yardstick: volume 0.5x its 20-day, -1.2% from the 20-day average, -21.3% from the 200-day, liquidity rank 77 |
| SHREEJISPG | CTL | 910.35 | random control: no edge is claimed, it is the yardstick: volume 0.8x its 20-day, +6.8% from the 20-day average, +66.1% from the 200-day, liquidity rank 245 |
| INDHOTEL | CTL | 901.55 | random control: no edge is claimed, it is the yardstick: volume 0.8x its 20-day, +7.9% from the 20-day average, +28.4% from the 200-day, liquidity rank 89 |

## Stock paper book (exec, policy shown: hold_20d)

| campaign | what | open | closed | realised Rs | unrealised Rs | win rate | expectancy R |
|---|---|---|---|---|---|---|---|
| BRK | 20-session breakout on volume | 59 | 7 | -25,073 | +142,468 | 0.0 | -1.0500324295476473 |
| CTL | random control: no edge is claimed, it is the yardstick | 86 | 14 | -45,685 | +223,348 | 0.0 | -1.0534292107308936 |
| PULL | pullback in an uptrend | 43 | 30 | -140,425 | +154,467 | 0.0 | -1.048744369515629 |
| REV | oversold reversal (RSI under 30, P01) | 55 | 14 | -51,877 | +276,284 | 0.0 | -1.050785415684926 |

## SP1 index line

Wed 18 Nov: 5 index decisions recorded, traded BANKNIFTY at D0 (long, exit NEXTOPEN). Book over 16 scored session(s): NIFTY: 3 scored trade(s), index +71 bp, one option lot Rs 5,637 with realistic fills; BANKNIFTY: 15 scored trade(s) (1 scored late), index +482 bp, one option lot Rs 38,737 with realistic fills

## Jobs

- autologin: ok
- evening: ok
- evening_zerodha: ok
- factmap: ok
- kitefill: ok
- morning: ok
- morningview: PROBLEM exit 1: no error line in the log tail (that run ended Tue 17 Nov 22:00)
- nightly: ok
- openingview: ok
- paper: ok
- postclose: ok
- preopen: ok
- recorder_noon: ok
- replay: PROBLEM stuck: running (pid 53400) with no output for 51 h, since Sun 15 Nov 23:20
- schedulecheck: ok
- shadowtrader: ok
- sp1paper: ok
- sp1paper.score: ok
- spreads: PROBLEM stuck: running (pid 96192) with no output for 21 h, since Tue 17 Nov 05:01
- studies: ok
- web: ok

Next sign-in: automatic at 20:10 Toronto, 06:40 IST (last automatic sign-in ok Tue 17 Nov 20:10 Toronto); by hand only if it fails, Wed 18 Nov 21:00-22:40 Toronto (07:30-09:10 IST, for the Thu 19 Nov session)

## Research

- studies: {'ready': 53, 'blocked': 11, 'with_results': 40}
- gate G02: {'state': 'BLOCKED', 'waiting_on': 'D15 (wait_time, 30 runs); D16 (wait_time, 30 snapshots); D32 (wait_time, weekly runs)'} counters {'D15': '31 of 30 nightly runs; 19 clean sessions in a row (the gate needs 30 in a row)', 'D16': '26 of 30 snapshots', 'D32': '2026-11-12: knows 18 of 18, unknowns 5 of 7, why 4 of 5, answers and decides 8 of 9, safety 39 of 39, plain words 37 of 39: FAIL; 4 of 7 runs passed'}
- registry verdicts: {'REJECTED': 511, 'OPPOSITE': 158, 'INCONCLUSIVE': 661, 'CONDITIONAL': 38, 'VALIDATED': 44, 'NOT_SUPPORTED_SEEN': 22, 'SUPPORTED_SEEN': 1, 'NOT_CONFIRMED': 5}
- exit book (G01): {'BRK/all': 'sma_close_50', 'BRK/above_both': 'hold_60d', 'BRK/mixed': 'sma_close_50', 'BRK/below_both': None, 'PULL/all': None, 'PULL/above_both': None, 'PULL/mixed': 'hold60+low20', 'PULL/below_both': None, 'ANY/all': None, 'ANY/above_both': None, 'ANY/mixed': None, 'ANY/below_both': 'hold60+low20'}

## Guardrails

Stop for the day at a 5.0% loss; pause new entries when 22.0% below the high-water mark until Madhav resumes — recorded, not enforced (paper); enforcement is W7 live-readiness work
