# India read model (V0) — data through 2026-11-25, built 2026-11-26T07:57:49+00:00

Rules readmodel-v0-2026-10-22. Every number below traces to the file named in its section of readmodel/latest.json; nothing here is typed by hand.

## Brief

- Through 2026-11-25: Nifty 25,819. Nifty is above both its 50- and 200-day averages: an uptrend; +9.4% from the 50-day, +7.6% from the 200-day; 63% of the liquid 250 are above their 200-day.
- Daily call for the next session: BEARISH (mechanical rule call-v0-2026-10-18); so far 9 of 24 calls right against 14 for the coin flip, one seeded draw (chance alone averages 12).
- Stock paper book: 263 open positions; realised Rs -10,970 on the hold_20d exits across campaigns.
- New for the next session: 2 BRK, 5 CTL, 3 PULL, 3 REV.
- SP1 index line: Thu 26 Nov: 5 index decisions recorded, traded BANKNIFTY at D0 (long, exit NEXTOPEN). Book over 20 scored session(s): NIFTY: 4 scored trade(s), index +60 bp, one option lot Rs 3,393 with realistic fills; BANKNIFTY: 18 scored trade(s) (1 scored late), index +905 bp, one option lot Rs 104,354 with realistic fills.
- Against the reference traders (1 session): Ananta held 9 of the top 20 trips, passed on 3, had no rule for 3; its picks sat at the 30th percentile of random.

## Decisions for the next session

| symbol | campaign | close | why |
|---|---|---|---|
| BAJAJFINSV | BRK | 1925.0 | 20-session breakout on volume: volume 4.6x its 20-day, +6.6% from the 20-day average, +4.3% from the 200-day, liquidity rank 136 |
| INDIGO | BRK | 5720.0 | 20-session breakout on volume: volume 1.7x its 20-day, +7.8% from the 20-day average, +17.9% from the 200-day, liquidity rank 49 |
| WELCORP | PULL | 2117.5 | pullback in an uptrend: volume 1.1x its 20-day, -7.3% from the 20-day average, +28.6% from the 200-day, liquidity rank 45 |
| CHENNPETRO | PULL | 1366.6 | pullback in an uptrend: volume 1.0x its 20-day, -6.8% from the 20-day average, +14.0% from the 200-day, liquidity rank 92 |
| HBLENGINE | PULL | 757.15 | pullback in an uptrend: volume 0.8x its 20-day, -5.4% from the 20-day average, +1.0% from the 200-day, liquidity rank 222 |
| RRKABEL | REV | 1801.1 | oversold reversal (RSI under 30, P01): volume 0.6x its 20-day, -8.0% from the 20-day average, -13.0% from the 200-day, liquidity rank 187 |
| INOXWIND | REV | 52.36 | oversold reversal (RSI under 30, P01): volume 0.9x its 20-day, -12.9% from the 20-day average, -36.2% from the 200-day, liquidity rank 247 |
| TATASTEEL | REV | 159.3 | oversold reversal (RSI under 30, P01): volume 4.3x its 20-day, -10.3% from the 20-day average, -17.5% from the 200-day, liquidity rank 26 |
| HAVELLS | CTL | 1196.4 | random control: no edge is claimed, it is the yardstick: volume 0.7x its 20-day, +7.0% from the 20-day average, -1.4% from the 200-day, liquidity rank 217 |
| KARURVYSYA | CTL | 378.75 | random control: no edge is claimed, it is the yardstick: volume 2.0x its 20-day, +2.7% from the 20-day average, +19.2% from the 200-day, liquidity rank 235 |
| HINDZINC | CTL | 519.7 | random control: no edge is claimed, it is the yardstick: volume 1.0x its 20-day, -3.4% from the 20-day average, -9.0% from the 200-day, liquidity rank 81 |
| PERSISTENT | CTL | 6120.0 | random control: no edge is claimed, it is the yardstick: volume 0.8x its 20-day, +1.8% from the 20-day average, +15.4% from the 200-day, liquidity rank 63 |
| PRESTIGE | CTL | 1685.1 | random control: no edge is claimed, it is the yardstick: volume 1.6x its 20-day, +5.9% from the 20-day average, +13.7% from the 200-day, liquidity rank 242 |

## Stock paper book (exec, policy shown: hold_20d)

| campaign | what | open | closed | realised Rs | unrealised Rs | win rate | expectancy R |
|---|---|---|---|---|---|---|---|
| BRK | 20-session breakout on volume | 60 | 19 | -11,957 | +122,574 | 0.2631578947368421 | 0.027237762362302763 |
| CTL | random control: no edge is claimed, it is the yardstick | 85 | 40 | +3,956 | +147,261 | 0.325 | -0.008425764225929245 |
| PULL | pullback in an uptrend | 23 | 54 | -51,743 | +17,505 | 0.2777777777777778 | -0.1182613669822863 |
| REV | oversold reversal (RSI under 30, P01) | 28 | 43 | +48,775 | +118,946 | 0.5116279069767442 | 0.3245754484134371 |

## SP1 index line

Thu 26 Nov: 5 index decisions recorded, traded BANKNIFTY at D0 (long, exit NEXTOPEN). Book over 20 scored session(s): NIFTY: 4 scored trade(s), index +60 bp, one option lot Rs 3,393 with realistic fills; BANKNIFTY: 18 scored trade(s) (1 scored late), index +905 bp, one option lot Rs 104,354 with realistic fills

## Jobs

- autologin: ok
- evening: ok
- evening_zerodha: PROBLEM steps failed inside the job (step): step: sp1 nightly replay failed
- factmap: PROBLEM exit 1: no error line in the log tail (that run ended Thu 26 Nov 00:30)
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
- spreads: PROBLEM stuck: running (pid 44455) with no output for 21 h, since Wed 25 Nov 05:01
- studies: ok
- web: ok

Next sign-in: automatic at 20:10 Toronto, 06:40 IST (last automatic sign-in ok Wed 25 Nov 20:10 Toronto); by hand only if it fails, Thu 26 Nov 21:00-22:40 Toronto (07:30-09:10 IST, for the Fri 27 Nov session)

## Research

- studies: {'ready': 53, 'blocked': 11, 'with_results': 40}
- gate G02: {'state': 'BLOCKED', 'waiting_on': 'D15 (wait_time, 30 runs); D16 (wait_time, 30 snapshots); D32 (wait_time, weekly runs)'} counters {'D15': '39 of 30 nightly runs; 24 clean sessions in a row (the gate needs 30 in a row)', 'D16': '33 of 30 snapshots', 'D32': '2026-11-21: knows 17 of 18, unknowns 6 of 7, why 4 of 5, answers and decides 8 of 9, safety 39 of 39, plain words 39 of 39: FAIL; 4 of 8 runs passed'}
- registry verdicts: {'REJECTED': 523, 'OPPOSITE': 169, 'INCONCLUSIVE': 705, 'CONDITIONAL': 40, 'VALIDATED': 47, 'NOT_SUPPORTED_SEEN': 22, 'SUPPORTED_SEEN': 1, 'NOT_CONFIRMED': 5}
- exit book (G01): {'BRK/all': 'sma_close_50', 'BRK/above_both': 'hold_60d', 'BRK/mixed': 'sma_close_50', 'BRK/below_both': None, 'PULL/all': None, 'PULL/above_both': None, 'PULL/mixed': 'hold60+low20', 'PULL/below_both': None, 'ANY/all': None, 'ANY/above_both': None, 'ANY/mixed': None, 'ANY/below_both': 'hold60+low20'}

## Guardrails

Stop for the day at a 5.0% loss; pause new entries when 22.0% below the high-water mark until Madhav resumes — recorded, not enforced (paper); enforcement is W7 live-readiness work
