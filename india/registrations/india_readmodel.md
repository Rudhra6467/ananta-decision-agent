# India read model (V0) — data through 2026-11-11, built 2026-11-12T07:57:39+00:00

Rules readmodel-v0-2026-10-22. Every number below traces to the file named in its section of readmodel/latest.json; nothing here is typed by hand.

## Brief

- Through 2026-11-11: Nifty 25,255. Nifty is above both its 50- and 200-day averages: an uptrend; +8.4% from the 50-day, +5.3% from the 200-day; 65% of the liquid 250 are above their 200-day.
- Daily call for the next session: BEARISH (mechanical rule call-v0-2026-10-18); so far 5 of 16 calls right against 10 for the coin flip.
- Stock paper book: 213 open positions; realised Rs -253,346 on the hold_20d exits across campaigns.
- New for the next session: 8 BRK, 5 CTL, 1 PULL.
- SP1 index line: Thu 12 Nov: 8 index decisions recorded, traded BANKNIFTY at D3 (long, exit NEXTOPEN). Book over 12 scored session(s): NIFTY: 2 scored trade(s), index +150 bp, one option lot Rs 12,406 with realistic fills; BANKNIFTY: 10 scored trade(s), index +51 bp, one option lot Rs -5,252 with realistic fills.
- Against the reference traders (1 session): Ananta held 15 of the top 20 trips, passed on 5, had no rule for 0; its picks sat at the 62nd percentile of random.

## Decisions for the next session

| symbol | campaign | close | why |
|---|---|---|---|
| IIFL | BRK | 666.25 | 20-session breakout on volume: volume 12.3x its 20-day, +14.9% from the 20-day average, +24.1% from the 200-day, liquidity rank 165 |
| ENGINERSIN | BRK | 311.2 | 20-session breakout on volume: volume 2.6x its 20-day, +13.2% from the 20-day average, +31.0% from the 200-day, liquidity rank 211 |
| APOLLO | BRK | 454.15 | 20-session breakout on volume: volume 2.3x its 20-day, +9.7% from the 20-day average, +33.8% from the 200-day, liquidity rank 75 |
| BANKINDIA | BRK | 150.6 | 20-session breakout on volume: volume 2.3x its 20-day, +11.2% from the 20-day average, +3.4% from the 200-day, liquidity rank 244 |
| MEESHO | BRK | 248.16 | 20-session breakout on volume: volume 1.9x its 20-day, +9.4% from the 20-day average, +33.2% from the 200-day, liquidity rank 46 |
| AXISBANK | BRK | 1336.4 | 20-session breakout on volume: volume 1.8x its 20-day, +6.9% from the 20-day average, +4.2% from the 200-day, liquidity rank 12 |
| TMCV | BRK | 446.05 | 20-session breakout on volume: volume 1.5x its 20-day, +8.2% from the 20-day average, +3.7% from the 200-day, liquidity rank 50 |
| GMRAIRPORT | BRK | 100.97 | 20-session breakout on volume: volume 1.5x its 20-day, +10.4% from the 20-day average, +2.6% from the 200-day, liquidity rank 186 |
| TDPOWERSYS | PULL | 609.9 | pullback in an uptrend: volume 2.7x its 20-day, -12.3% from the 20-day average, +3.9% from the 200-day, liquidity rank 99 |
| NAUKRI | CTL | 1190.0 | random control: no edge is claimed, it is the yardstick: volume 0.7x its 20-day, -1.3% from the 20-day average, +5.3% from the 200-day, liquidity rank 114 |
| TRENT | CTL | 3222.7 | random control: no edge is claimed, it is the yardstick: volume 1.6x its 20-day, +9.1% from the 20-day average, +15.2% from the 200-day, liquidity rank 89 |
| BHEL | CTL | 432.0 | random control: no edge is claimed, it is the yardstick: volume 0.9x its 20-day, +4.1% from the 20-day average, +18.6% from the 200-day, liquidity rank 41 |
| INDUSINDBK | CTL | 900.0 | random control: no edge is claimed, it is the yardstick: volume 2.6x its 20-day, +4.0% from the 20-day average, -2.4% from the 200-day, liquidity rank 118 |
| PFOCUS | CTL | 264.55 | random control: no edge is claimed, it is the yardstick: volume 1.0x its 20-day, -6.9% from the 20-day average, -2.7% from the 200-day, liquidity rank 167 |

## Stock paper book (exec, policy shown: hold_20d)

| campaign | what | open | closed | realised Rs | unrealised Rs | win rate | expectancy R |
|---|---|---|---|---|---|---|---|
| BRK | 20-session breakout on volume | 47 | 7 | -25,073 | +127,281 | 0.0 | -1.0500324295476473 |
| CTL | random control: no edge is claimed, it is the yardstick | 69 | 11 | -35,971 | +218,661 | 0.0 | -1.0541843554633534 |
| PULL | pullback in an uptrend | 42 | 30 | -140,425 | +158,746 | 0.0 | -1.048744369515629 |
| REV | oversold reversal (RSI under 30, P01) | 55 | 14 | -51,877 | +286,120 | 0.0 | -1.050785415684926 |

## SP1 index line

Thu 12 Nov: 8 index decisions recorded, traded BANKNIFTY at D3 (long, exit NEXTOPEN). Book over 12 scored session(s): NIFTY: 2 scored trade(s), index +150 bp, one option lot Rs 12,406 with realistic fills; BANKNIFTY: 10 scored trade(s), index +51 bp, one option lot Rs -5,252 with realistic fills

## Jobs

- autologin: ok
- evening: ok
- evening_zerodha: ok
- factmap: PROBLEM exit 1: no error line in the log tail (that run ended Thu 12 Nov 00:30)
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
- spreads: PROBLEM stuck: running (pid 97751) with no output for 21 h, since Wed 11 Nov 05:01
- studies: ok
- web: ok

Next sign-in: automatic at 19:35 Toronto, 06:05 IST (last automatic sign-in ok Wed 11 Nov 19:59 Toronto); by hand only if it fails, Thu 12 Nov 21:00-22:40 Toronto (07:30-09:10 IST, for the Fri 13 Nov session)

## Research

- studies: {'ready': 53, 'blocked': 11, 'with_results': 40}
- gate G02: {'state': 'BLOCKED', 'waiting_on': 'D15 (wait_time, 30 runs); D16 (wait_time, 30 snapshots); D32 (wait_time, weekly runs)'} counters {'D15': '25 of 30 nightly runs; 15 clean sessions in a row (the gate needs 30 in a row)', 'D16': '22 of 30 snapshots', 'D32': '2026-11-05: knows 16 of 18, unknowns 2 of 7, why 5 of 5, answers and decides 8 of 9, safety 38 of 39, plain words 38 of 39: FAIL; 4 of 6 runs passed'}
- registry verdicts: {'REJECTED': 511, 'OPPOSITE': 158, 'INCONCLUSIVE': 661, 'CONDITIONAL': 38, 'VALIDATED': 44, 'NOT_SUPPORTED_SEEN': 22, 'SUPPORTED_SEEN': 1, 'NOT_CONFIRMED': 5}
- exit book (G01): {'BRK/all': 'sma_close_50', 'BRK/above_both': 'hold_60d', 'BRK/mixed': 'sma_close_50', 'BRK/below_both': None, 'PULL/all': None, 'PULL/above_both': None, 'PULL/mixed': 'hold60+low20', 'PULL/below_both': None, 'ANY/all': None, 'ANY/above_both': None, 'ANY/mixed': None, 'ANY/below_both': 'hold60+low20'}

## Guardrails

Stop for the day at a 5.0% loss; pause new entries when 22.0% below the high-water mark until Madhav resumes — recorded, not enforced (paper); enforcement is W7 live-readiness work
