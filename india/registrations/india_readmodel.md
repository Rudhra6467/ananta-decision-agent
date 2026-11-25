# India read model (V0) — data through 2026-11-23, built 2026-11-25T07:57:15+00:00

Rules readmodel-v0-2026-10-22. Every number below traces to the file named in its section of readmodel/latest.json; nothing here is typed by hand.

## Brief

- Through 2026-11-23: Nifty 25,366. Nifty is above both its 50- and 200-day averages: an uptrend; +7.7% from the 50-day, +5.7% from the 200-day; 63% of the liquid 250 are above their 200-day.
- Daily call for the next session: BULLISH (mechanical rule call-v0-2026-10-18); so far 8 of 23 calls right against 14 for the coin flip, one seeded draw (chance alone averages 11.5).
- Stock paper book: 264 open positions; realised Rs -133,433 on the hold_20d exits across campaigns.
- New for the next session: 2 BRK, 5 CTL, 2 REV.
- SP1 index line: Wed 25 Nov: 5 index decisions recorded, traded BANKNIFTY at D0 (long, exit NEXTOPEN). Book over 19 scored session(s): NIFTY: 4 scored trade(s), index +60 bp, one option lot Rs 3,393 with realistic fills; BANKNIFTY: 18 scored trade(s) (1 scored late), index +905 bp, one option lot Rs 104,354 with realistic fills.
- Against the reference traders (1 session): Ananta held 13 of the top 20 trips, passed on 1, had no rule for 4; its picks sat at the 64th percentile of random.

## Decisions for the next session

| symbol | campaign | close | why |
|---|---|---|---|
| JSWINFRA | BRK | 353.55 | 20-session breakout on volume: volume 2.6x its 20-day, +5.9% from the 20-day average, +16.6% from the 200-day, liquidity rank 232 |
| PERSISTENT | BRK | 6282.5 | 20-session breakout on volume: volume 2.1x its 20-day, +4.8% from the 20-day average, +18.4% from the 200-day, liquidity rank 63 |
| APLAPOLLO | REV | 1670.0 | oversold reversal (RSI under 30, P01): volume 27.9x its 20-day, -22.5% from the 20-day average, -17.6% from the 200-day, liquidity rank 154 |
| MANAPPURAM | REV | 271.0 | oversold reversal (RSI under 30, P01): volume 2.1x its 20-day, -9.8% from the 20-day average, -12.8% from the 200-day, liquidity rank 146 |
| HAL | CTL | 4780.0 | random control: no edge is claimed, it is the yardstick: volume 0.5x its 20-day, -1.7% from the 20-day average, +6.6% from the 200-day, liquidity rank 45 |
| PVRINOX | CTL | 1699.7 | random control: no edge is claimed, it is the yardstick: volume 1.2x its 20-day, +7.5% from the 20-day average, +50.2% from the 200-day, liquidity rank 209 |
| GROWW | CTL | 216.46 | random control: no edge is claimed, it is the yardstick: volume 1.6x its 20-day, +2.6% from the 20-day average, +13.5% from the 200-day, liquidity rank 23 |
| IDFCFIRSTB | CTL | 85.4 | random control: no edge is claimed, it is the yardstick: volume 1.8x its 20-day, +9.3% from the 20-day average, +11.3% from the 200-day, liquidity rank 139 |
| GODREJCP | CTL | 912.3 | random control: no edge is claimed, it is the yardstick: volume 0.3x its 20-day, +5.6% from the 20-day average, -9.4% from the 200-day, liquidity rank 219 |

## Stock paper book (exec, policy shown: hold_20d)

| campaign | what | open | closed | realised Rs | unrealised Rs | win rate | expectancy R |
|---|---|---|---|---|---|---|---|
| BRK | 20-session breakout on volume | 60 | 17 | -4,398 | +102,952 | 0.29411764705882354 | 0.15373335854567413 |
| CTL | random control: no edge is claimed, it is the yardstick | 87 | 33 | -19,023 | +146,374 | 0.2727272727272727 | -0.20217249569490808 |
| PULL | pullback in an uptrend | 31 | 46 | -114,566 | +82,899 | 0.1956521739130435 | -0.5154584955648679 |
| REV | oversold reversal (RSI under 30, P01) | 38 | 31 | +4,555 | +176,098 | 0.41935483870967744 | 0.03760698050215153 |

## SP1 index line

Wed 25 Nov: 5 index decisions recorded, traded BANKNIFTY at D0 (long, exit NEXTOPEN). Book over 19 scored session(s): NIFTY: 4 scored trade(s), index +60 bp, one option lot Rs 3,393 with realistic fills; BANKNIFTY: 18 scored trade(s) (1 scored late), index +905 bp, one option lot Rs 104,354 with realistic fills

## Jobs

- autologin: ok
- evening: ok
- evening_zerodha: ok
- factmap: PROBLEM exit 1: no error line in the log tail (that run ended Wed 25 Nov 00:30)
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
- spreads: PROBLEM stuck: running (pid 90551) with no output for 21 h, since Tue 24 Nov 05:01
- studies: ok
- web: ok

Next sign-in: automatic at 20:10 Toronto, 06:40 IST (last automatic sign-in ok Tue 24 Nov 20:10 Toronto); by hand only if it fails, Wed 25 Nov 21:00-22:40 Toronto (07:30-09:10 IST, for the Thu 26 Nov session)

## Research

- studies: {'ready': 53, 'blocked': 11, 'with_results': 40}
- gate G02: {'state': 'BLOCKED', 'waiting_on': 'D15 (wait_time, 30 runs); D16 (wait_time, 30 snapshots); D32 (wait_time, weekly runs)'} counters {'D15': '38 of 30 nightly runs; 24 clean sessions in a row (the gate needs 30 in a row)', 'D16': '32 of 30 snapshots', 'D32': '2026-11-21: knows 17 of 18, unknowns 6 of 7, why 4 of 5, answers and decides 8 of 9, safety 39 of 39, plain words 39 of 39: FAIL; 4 of 8 runs passed'}
- registry verdicts: {'REJECTED': 511, 'OPPOSITE': 158, 'INCONCLUSIVE': 661, 'CONDITIONAL': 38, 'VALIDATED': 44, 'NOT_SUPPORTED_SEEN': 22, 'SUPPORTED_SEEN': 1, 'NOT_CONFIRMED': 5}
- exit book (G01): {'BRK/all': 'sma_close_50', 'BRK/above_both': 'hold_60d', 'BRK/mixed': 'sma_close_50', 'BRK/below_both': None, 'PULL/all': None, 'PULL/above_both': None, 'PULL/mixed': 'hold60+low20', 'PULL/below_both': None, 'ANY/all': None, 'ANY/above_both': None, 'ANY/mixed': None, 'ANY/below_both': 'hold60+low20'}

## Guardrails

Stop for the day at a 5.0% loss; pause new entries when 22.0% below the high-water mark until Madhav resumes — recorded, not enforced (paper); enforcement is W7 live-readiness work
