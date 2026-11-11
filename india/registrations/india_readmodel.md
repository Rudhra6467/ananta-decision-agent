# India read model (V0) — data through 2026-11-09, built 2026-11-11T07:57:47+00:00

Rules readmodel-v0-2026-10-22. Every number below traces to the file named in its section of readmodel/latest.json; nothing here is typed by hand.

## Brief

- Through 2026-11-09: Nifty 25,045. Nifty is above both its 50- and 200-day averages: an uptrend; +7.6% from the 50-day, +4.4% from the 200-day; 62% of the liquid 250 are above their 200-day.
- Daily call for the next session: BEARISH (mechanical rule call-v0-2026-10-18); so far 5 of 15 calls right against 9 for the coin flip.
- Stock paper book: 204 open positions; realised Rs -253,346 on the hold_20d exits across campaigns.
- New for the next session: 3 BRK, 5 CTL, 1 REV.
- SP1 index line: Wed 11 Nov: 4 index decisions recorded, traded BANKNIFTY at D0 (long, exit NEXTOPEN), NIFTY at D2 (long, exit NEXTOPEN). Book over 11 scored session(s): NIFTY: 2 scored trade(s), index +150 bp, one option lot Rs 12,406 with realistic fills; BANKNIFTY: 10 scored trade(s), index +51 bp, one option lot Rs -5,252 with realistic fills.
- Against the reference traders (1 session): Ananta held 10 of the top 20 trips, passed on 3, had no rule for 6; its picks sat at the 64th percentile of random.

## Decisions for the next session

| symbol | campaign | close | why |
|---|---|---|---|
| SANSERA | BRK | 4653.4 | 20-session breakout on volume: volume 3.0x its 20-day, +10.5% from the 20-day average, +52.3% from the 200-day, liquidity rank 225 |
| SBIN | BRK | 1042.0 | 20-session breakout on volume: volume 2.1x its 20-day, +7.2% from the 20-day average, +0.3% from the 200-day, liquidity rank 8 |
| MANKIND | BRK | 2668.3 | 20-session breakout on volume: volume 2.1x its 20-day, +10.6% from the 20-day average, +14.9% from the 200-day, liquidity rank 184 |
| RAIN | REV | 162.03 | oversold reversal (RSI under 30, P01): volume 2.8x its 20-day, -20.5% from the 20-day average, -8.4% from the 200-day, liquidity rank 248 |
| GVT&D | CTL | 4106.0 | random control: no edge is claimed, it is the yardstick: volume 0.5x its 20-day, +2.1% from the 20-day average, -2.0% from the 200-day, liquidity rank 48 |
| HINDUNILVR | CTL | 1990.3 | random control: no edge is claimed, it is the yardstick: volume 0.9x its 20-day, +5.5% from the 20-day average, -6.6% from the 200-day, liquidity rank 75 |
| ADANIENT | CTL | 2706.3 | random control: no edge is claimed, it is the yardstick: volume 0.6x its 20-day, +3.1% from the 20-day average, +3.3% from the 200-day, liquidity rank 36 |
| ICICIBANK | CTL | 1589.0 | random control: no edge is claimed, it is the yardstick: volume 1.8x its 20-day, +12.6% from the 20-day average, +17.2% from the 200-day, liquidity rank 3 |
| SONACOMS | CTL | 924.0 | random control: no edge is claimed, it is the yardstick: volume 0.4x its 20-day, +10.0% from the 20-day average, +40.7% from the 200-day, liquidity rank 120 |

## Stock paper book (exec, policy shown: hold_20d)

| campaign | what | open | closed | realised Rs | unrealised Rs | win rate | expectancy R |
|---|---|---|---|---|---|---|---|
| BRK | 20-session breakout on volume | 44 | 7 | -25,073 | +108,180 | 0.0 | -1.0500324295476473 |
| CTL | random control: no edge is claimed, it is the yardstick | 64 | 11 | -35,971 | +192,086 | 0.0 | -1.0541843554633534 |
| PULL | pullback in an uptrend | 42 | 30 | -140,425 | +115,406 | 0.0 | -1.048744369515629 |
| REV | oversold reversal (RSI under 30, P01) | 54 | 14 | -51,877 | +251,538 | 0.0 | -1.050785415684926 |

## SP1 index line

Wed 11 Nov: 4 index decisions recorded, traded BANKNIFTY at D0 (long, exit NEXTOPEN), NIFTY at D2 (long, exit NEXTOPEN). Book over 11 scored session(s): NIFTY: 2 scored trade(s), index +150 bp, one option lot Rs 12,406 with realistic fills; BANKNIFTY: 10 scored trade(s), index +51 bp, one option lot Rs -5,252 with realistic fills

## Jobs

- autologin: ok
- evening: ok
- evening_zerodha: ok
- factmap: PROBLEM exit 1: no error line in the log tail (that run ended Wed 11 Nov 00:30)
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
- spreads: PROBLEM stuck: running (pid 58975) with no output for 21 h, since Tue 10 Nov 05:01
- studies: ok
- web: ok

Next sign-in: automatic at 19:35 Toronto, 06:05 IST (last automatic sign-in ok Tue 10 Nov 19:47 Toronto); by hand only if it fails, Wed 11 Nov 21:00-22:40 Toronto (07:30-09:10 IST, for the Thu 12 Nov session)

## Research

- studies: {'ready': 53, 'blocked': 11, 'with_results': 40}
- gate G02: {'state': 'BLOCKED', 'waiting_on': 'D15 (wait_time, 30 runs); D16 (wait_time, 30 snapshots); D32 (wait_time, weekly runs)'} counters {'D15': '24 of 30 nightly runs; 15 clean sessions in a row (the gate needs 30 in a row)', 'D16': '21 of 30 snapshots', 'D32': '2026-11-05: knows 16 of 18, unknowns 2 of 7, why 5 of 5, answers and decides 8 of 9, safety 38 of 39, plain words 38 of 39: FAIL; 4 of 6 runs passed'}
- registry verdicts: {'REJECTED': 511, 'OPPOSITE': 158, 'INCONCLUSIVE': 661, 'CONDITIONAL': 38, 'VALIDATED': 44, 'NOT_SUPPORTED_SEEN': 22, 'SUPPORTED_SEEN': 1, 'NOT_CONFIRMED': 5}
- exit book (G01): {'BRK/all': 'sma_close_50', 'BRK/above_both': 'hold_60d', 'BRK/mixed': 'sma_close_50', 'BRK/below_both': None, 'PULL/all': None, 'PULL/above_both': None, 'PULL/mixed': 'hold60+low20', 'PULL/below_both': None, 'ANY/all': None, 'ANY/above_both': None, 'ANY/mixed': None, 'ANY/below_both': 'hold60+low20'}

## Guardrails

Stop for the day at a 5.0% loss; pause new entries when 22.0% below the high-water mark until Madhav resumes — recorded, not enforced (paper); enforcement is W7 live-readiness work
