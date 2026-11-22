# India read model (V0) — data through 2026-11-20, built 2026-11-22T07:58:04+00:00

Rules readmodel-v0-2026-10-22. Every number below traces to the file named in its section of readmodel/latest.json; nothing here is typed by hand.

## Brief

- Through 2026-11-20: Nifty 25,801. Nifty is above both its 50- and 200-day averages: an uptrend; +9.7% from the 50-day, +7.5% from the 200-day; 64% of the liquid 250 are above their 200-day.
- Daily call for the next session: BEARISH (mechanical rule call-v0-2026-10-18); so far 7 of 22 calls right against 13 for the coin flip, one seeded draw (chance alone averages 11).
- Stock paper book: 258 open positions; realised Rs -169,105 on the hold_20d exits across campaigns.
- New for the next session: 3 BRK, 5 CTL, 1 PULL.
- SP1 index line: Fri 20 Nov: 5 index decisions recorded, traded BANKNIFTY at D0 (long, exit NEXTOPEN). Book over 18 scored session(s): NIFTY: 4 scored trade(s), index +60 bp, one option lot Rs 3,393 with realistic fills; BANKNIFTY: 17 scored trade(s) (1 scored late), index +535 bp, one option lot Rs 43,431 with realistic fills.
- Against the reference traders (1 session): Ananta held 8 of the top 20 trips, passed on 6, had no rule for 1; its picks sat at the 20th percentile of random.

## Decisions for the next session

| symbol | campaign | close | why |
|---|---|---|---|
| INDUSINDBK | BRK | 1003.0 | 20-session breakout on volume: volume 6.0x its 20-day, +12.8% from the 20-day average, +8.7% from the 200-day, liquidity rank 111 |
| ADANIPOWER | BRK | 211.95 | 20-session breakout on volume: volume 1.7x its 20-day, +6.2% from the 20-day average, +8.0% from the 200-day, liquidity rank 33 |
| ICICIGI | BRK | 1736.0 | 20-session breakout on volume: volume 1.6x its 20-day, +6.2% from the 20-day average, +0.7% from the 200-day, liquidity rank 182 |
| AVALON | PULL | 1728.3 | pullback in an uptrend: volume 0.7x its 20-day, -12.1% from the 20-day average, +7.0% from the 200-day, liquidity rank 246 |
| NATIONALUM | CTL | 303.2 | random control: no edge is claimed, it is the yardstick: volume 1.9x its 20-day, -5.1% from the 20-day average, -17.9% from the 200-day, liquidity rank 114 |
| LUPIN | CTL | 2014.0 | random control: no edge is claimed, it is the yardstick: volume 0.9x its 20-day, +1.3% from the 20-day average, -9.7% from the 200-day, liquidity rank 150 |
| FEDERALBNK | CTL | 373.5 | random control: no edge is claimed, it is the yardstick: volume 1.3x its 20-day, +6.7% from the 20-day average, +17.9% from the 200-day, liquidity rank 99 |
| ULTRACEMCO | CTL | 12939.0 | random control: no edge is claimed, it is the yardstick: volume 2.0x its 20-day, +8.8% from the 20-day average, +11.4% from the 200-day, liquidity rank 55 |
| NAVINFLUOR | CTL | 10077.0 | random control: no edge is claimed, it is the yardstick: volume 1.2x its 20-day, +11.0% from the 20-day average, +34.8% from the 200-day, liquidity rank 183 |

## Stock paper book (exec, policy shown: hold_20d)

| campaign | what | open | closed | realised Rs | unrealised Rs | win rate | expectancy R |
|---|---|---|---|---|---|---|---|
| BRK | 20-session breakout on volume | 57 | 17 | -4,398 | +128,276 | 0.29411764705882354 | 0.15373335854567413 |
| CTL | random control: no edge is claimed, it is the yardstick | 86 | 29 | -23,123 | +198,906 | 0.2413793103448276 | -0.27056378719184676 |
| PULL | pullback in an uptrend | 38 | 38 | -116,973 | +98,948 | 0.13157894736842105 | -0.7021373933840868 |
| REV | oversold reversal (RSI under 30, P01) | 46 | 23 | -24,610 | +223,372 | 0.30434782608695654 | -0.3190049590606971 |

## SP1 index line

Fri 20 Nov: 5 index decisions recorded, traded BANKNIFTY at D0 (long, exit NEXTOPEN). Book over 18 scored session(s): NIFTY: 4 scored trade(s), index +60 bp, one option lot Rs 3,393 with realistic fills; BANKNIFTY: 17 scored trade(s) (1 scored late), index +535 bp, one option lot Rs 43,431 with realistic fills

## Jobs

- autologin: ok
- evening: ok
- evening_zerodha: ok
- factmap: ok
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

Next sign-in: automatic at 20:10 Toronto, 06:40 IST (last automatic sign-in ok Sat 21 Nov 20:10 Toronto); by hand only if it fails, Sun 22 Nov 21:00-22:40 Toronto (07:30-09:10 IST, for the Mon 23 Nov session)

## Research

- studies: {'ready': 53, 'blocked': 11, 'with_results': 40}
- gate G02: {'state': 'BLOCKED', 'waiting_on': 'D15 (wait_time, 30 runs); D16 (wait_time, 30 snapshots); D32 (wait_time, weekly runs)'} counters {'D15': '35 of 30 nightly runs; 23 clean sessions in a row (the gate needs 30 in a row)', 'D16': '29 of 30 snapshots', 'D32': '2026-11-21: knows 17 of 18, unknowns 6 of 7, why 4 of 5, answers and decides 8 of 9, safety 39 of 39, plain words 39 of 39: FAIL; 4 of 8 runs passed'}
- registry verdicts: {'REJECTED': 511, 'OPPOSITE': 158, 'INCONCLUSIVE': 661, 'CONDITIONAL': 38, 'VALIDATED': 44, 'NOT_SUPPORTED_SEEN': 22, 'SUPPORTED_SEEN': 1, 'NOT_CONFIRMED': 5}
- exit book (G01): {'BRK/all': 'sma_close_50', 'BRK/above_both': 'hold_60d', 'BRK/mixed': 'sma_close_50', 'BRK/below_both': None, 'PULL/all': None, 'PULL/above_both': None, 'PULL/mixed': 'hold60+low20', 'PULL/below_both': None, 'ANY/all': None, 'ANY/above_both': None, 'ANY/mixed': None, 'ANY/below_both': 'hold60+low20'}

## Guardrails

Stop for the day at a 5.0% loss; pause new entries when 22.0% below the high-water mark until Madhav resumes — recorded, not enforced (paper); enforcement is W7 live-readiness work
