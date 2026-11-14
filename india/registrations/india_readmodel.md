# India read model (V0) — data through 2026-11-13, built 2026-11-14T07:57:35+00:00

Rules readmodel-v0-2026-10-22. Every number below traces to the file named in its section of readmodel/latest.json; nothing here is typed by hand.

## Brief

- Through 2026-11-13: Nifty 25,144. Nifty is above both its 50- and 200-day averages: an uptrend; +7.7% from the 50-day, +4.8% from the 200-day; 64% of the liquid 250 are above their 200-day.
- Daily call for the next session: BEARISH (mechanical rule call-v0-2026-10-18); so far 6 of 18 calls right against 10 for the coin flip.
- Stock paper book: 234 open positions; realised Rs -253,346 on the hold_20d exits across campaigns.
- New for the next session: 2 BRK, 5 CTL.
- SP1 index line: Fri 13 Nov: 8 index decisions recorded, traded BANKNIFTY at D3 (long, exit NEXTOPEN). Book over 14 scored session(s): NIFTY: 3 scored trade(s), index +71 bp, one option lot Rs 5,637 with realistic fills; BANKNIFTY: 12 scored trade(s), index +85 bp, one option lot Rs -1,746 with realistic fills.
- Against the reference traders (1 session): Ananta held 15 of the top 20 trips, passed on 0, had no rule for 4; its picks sat at the 76th percentile of random.

## Decisions for the next session

| symbol | campaign | close | why |
|---|---|---|---|
| POWERINDIA | BRK | 31595.0 | 20-session breakout on volume: volume 5.8x its 20-day, +11.9% from the 20-day average, +5.7% from the 200-day, liquidity rank 53 |
| GVT&D | BRK | 4420.0 | 20-session breakout on volume: volume 2.0x its 20-day, +9.6% from the 20-day average, +4.9% from the 200-day, liquidity rank 47 |
| KALYANKJIL | CTL | 697.0 | random control: no edge is claimed, it is the yardstick: volume 1.8x its 20-day, +24.8% from the 20-day average, +47.9% from the 200-day, liquidity rank 46 |
| BHARTIARTL | CTL | 2106.0 | random control: no edge is claimed, it is the yardstick: volume 0.6x its 20-day, +5.9% from the 20-day average, +11.4% from the 200-day, liquidity rank 5 |
| PREMIERENE | CTL | 895.9 | random control: no edge is claimed, it is the yardstick: volume 0.6x its 20-day, +1.7% from the 20-day average, -4.8% from the 200-day, liquidity rank 214 |
| JSWSTEEL | CTL | 1348.0 | random control: no edge is claimed, it is the yardstick: volume 0.7x its 20-day, +5.2% from the 20-day average, +7.6% from the 200-day, liquidity rank 94 |
| SBICARD | CTL | 578.3 | random control: no edge is claimed, it is the yardstick: volume 0.9x its 20-day, +3.5% from the 20-day average, -10.8% from the 200-day, liquidity rank 236 |

## Stock paper book (exec, policy shown: hold_20d)

| campaign | what | open | closed | realised Rs | unrealised Rs | win rate | expectancy R |
|---|---|---|---|---|---|---|---|
| BRK | 20-session breakout on volume | 57 | 7 | -25,073 | +140,407 | 0.0 | -1.0500324295476473 |
| CTL | random control: no edge is claimed, it is the yardstick | 79 | 11 | -35,971 | +241,005 | 0.0 | -1.0541843554633534 |
| PULL | pullback in an uptrend | 43 | 30 | -140,425 | +206,083 | 0.0 | -1.048744369515629 |
| REV | oversold reversal (RSI under 30, P01) | 55 | 14 | -51,877 | +313,197 | 0.0 | -1.050785415684926 |

## SP1 index line

Fri 13 Nov: 8 index decisions recorded, traded BANKNIFTY at D3 (long, exit NEXTOPEN). Book over 14 scored session(s): NIFTY: 3 scored trade(s), index +71 bp, one option lot Rs 5,637 with realistic fills; BANKNIFTY: 12 scored trade(s), index +85 bp, one option lot Rs -1,746 with realistic fills

## Jobs

- autologin: ok
- evening: ok
- evening_zerodha: PROBLEM empty run: recorder: 0 contracts saved since 20:00; steps failed inside the job (india.ledger, india.recorder, step): token dead; next sign-in automatic at 19:35 Toronto, 06:05 IST (last automatic sign-in ok Fri 13 Nov 20:35 Toronto); by hand only if it fails, Sun 15 Nov 21:00-22:40 Toronto (07:30-09:10 IST, for the Mon 16 Nov session)
- factmap: PROBLEM exit 1: no error line in the log tail (that run ended Sat 14 Nov 00:30)
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

Next sign-in: automatic at 19:35 Toronto, 06:05 IST (last automatic sign-in ok Fri 13 Nov 20:35 Toronto); by hand only if it fails, Sun 15 Nov 21:00-22:40 Toronto (07:30-09:10 IST, for the Mon 16 Nov session)

## Research

- studies: {'ready': 53, 'blocked': 11, 'with_results': 40}
- gate G02: {'state': 'BLOCKED', 'waiting_on': 'D15 (wait_time, 30 runs); D16 (wait_time, 30 snapshots); D32 (wait_time, weekly runs)'} counters {'D15': '27 of 30 nightly runs; 17 clean sessions in a row (the gate needs 30 in a row)', 'D16': '23 of 30 snapshots', 'D32': '2026-11-12: knows 18 of 18, unknowns 5 of 7, why 4 of 5, answers and decides 8 of 9, safety 39 of 39, plain words 37 of 39: FAIL; 4 of 7 runs passed'}
- registry verdicts: {'REJECTED': 511, 'OPPOSITE': 158, 'INCONCLUSIVE': 661, 'CONDITIONAL': 38, 'VALIDATED': 44, 'NOT_SUPPORTED_SEEN': 22, 'SUPPORTED_SEEN': 1, 'NOT_CONFIRMED': 5}
- exit book (G01): {'BRK/all': 'sma_close_50', 'BRK/above_both': 'hold_60d', 'BRK/mixed': 'sma_close_50', 'BRK/below_both': None, 'PULL/all': None, 'PULL/above_both': None, 'PULL/mixed': 'hold60+low20', 'PULL/below_both': None, 'ANY/all': None, 'ANY/above_both': None, 'ANY/mixed': None, 'ANY/below_both': 'hold60+low20'}

## Guardrails

Stop for the day at a 5.0% loss; pause new entries when 22.0% below the high-water mark until Madhav resumes — recorded, not enforced (paper); enforcement is W7 live-readiness work
