# India read model (V0) — data through 2026-11-16, built 2026-11-17T07:59:44+00:00

Rules readmodel-v0-2026-10-22. Every number below traces to the file named in its section of readmodel/latest.json; nothing here is typed by hand.

## Brief

- Through 2026-11-16: Nifty 25,291. Nifty is above both its 50- and 200-day averages: an uptrend; +8.2% from the 50-day, +5.4% from the 200-day; 64% of the liquid 250 are above their 200-day.
- Daily call for the next session: BEARISH (mechanical rule call-v0-2026-10-18); so far 6 of 19 calls right against 11 for the coin flip, one seeded draw (chance alone averages 9.5).
- Stock paper book: 239 open positions; realised Rs -260,175 on the hold_20d exits across campaigns.
- New for the next session: 5 CTL.
- SP1 index line: Tue 17 Nov: 5 index decisions recorded, traded BANKNIFTY at D0 (long, exit NEXTOPEN), NIFTY at D3 (long, exit NEXTOPEN). Book over 15 scored session(s): NIFTY: 3 scored trade(s), index +71 bp, one option lot Rs 5,637 with realistic fills; BANKNIFTY: 14 scored trade(s) (1 scored late), index +437 bp, one option lot Rs 33,318 with realistic fills.
- Against the reference traders (1 session): Ananta held 11 of the top 20 trips, passed on 3, had no rule for 5; its picks sat at the 30th percentile of random.

## Decisions for the next session

| symbol | campaign | close | why |
|---|---|---|---|
| PNBHOUSING | CTL | 1135.9 | random control: no edge is claimed, it is the yardstick: volume 0.5x its 20-day, +2.5% from the 20-day average, +11.9% from the 200-day, liquidity rank 243 |
| LICI | CTL | 400.0 | random control: no edge is claimed, it is the yardstick: volume 1.0x its 20-day, +1.4% from the 20-day average, -2.2% from the 200-day, liquidity rank 55 |
| ZEEL | CTL | 71.66 | random control: no edge is claimed, it is the yardstick: volume 0.8x its 20-day, +4.9% from the 20-day average, -19.1% from the 200-day, liquidity rank 163 |
| BANKBARODA | CTL | 270.2 | random control: no edge is claimed, it is the yardstick: volume 0.9x its 20-day, +9.4% from the 20-day average, +3.1% from the 200-day, liquidity rank 104 |
| JSWINFRA | CTL | 335.7 | random control: no edge is claimed, it is the yardstick: volume 0.7x its 20-day, +1.9% from the 20-day average, +11.5% from the 200-day, liquidity rank 239 |

## Stock paper book (exec, policy shown: hold_20d)

| campaign | what | open | closed | realised Rs | unrealised Rs | win rate | expectancy R |
|---|---|---|---|---|---|---|---|
| BRK | 20-session breakout on volume | 59 | 7 | -25,073 | +127,792 | 0.0 | -1.0500324295476473 |
| CTL | random control: no edge is claimed, it is the yardstick | 82 | 13 | -42,800 | +212,017 | 0.0 | -1.053522181232265 |
| PULL | pullback in an uptrend | 43 | 30 | -140,425 | +170,289 | 0.0 | -1.048744369515629 |
| REV | oversold reversal (RSI under 30, P01) | 55 | 14 | -51,877 | +289,903 | 0.0 | -1.050785415684926 |

## SP1 index line

Tue 17 Nov: 5 index decisions recorded, traded BANKNIFTY at D0 (long, exit NEXTOPEN), NIFTY at D3 (long, exit NEXTOPEN). Book over 15 scored session(s): NIFTY: 3 scored trade(s), index +71 bp, one option lot Rs 5,637 with realistic fills; BANKNIFTY: 14 scored trade(s) (1 scored late), index +437 bp, one option lot Rs 33,318 with realistic fills

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
- replay: PROBLEM stuck: running (pid 53400) with no output for 27 h, since Sun 15 Nov 23:20
- schedulecheck: ok
- shadowtrader: ok
- sp1paper: ok
- sp1paper.score: ok
- spreads: PROBLEM stuck: running (pid 85358) with no output for 21 h, since Mon 16 Nov 05:01
- studies: ok
- web: ok

Next sign-in: automatic at 20:10 Toronto, 06:40 IST (last automatic sign-in ok Mon 16 Nov 20:10 Toronto); by hand only if it fails, Tue 17 Nov 21:00-22:40 Toronto (07:30-09:10 IST, for the Wed 18 Nov session)

## Research

- studies: {'ready': 53, 'blocked': 11, 'with_results': 40}
- gate G02: {'state': 'BLOCKED', 'waiting_on': 'D15 (wait_time, 30 runs); D16 (wait_time, 30 snapshots); D32 (wait_time, weekly runs)'} counters {'D15': '30 of 30 nightly runs; 18 clean sessions in a row (the gate needs 30 in a row)', 'D16': '25 of 30 snapshots', 'D32': '2026-11-12: knows 18 of 18, unknowns 5 of 7, why 4 of 5, answers and decides 8 of 9, safety 39 of 39, plain words 37 of 39: FAIL; 4 of 7 runs passed'}
- registry verdicts: {'REJECTED': 511, 'OPPOSITE': 158, 'INCONCLUSIVE': 661, 'CONDITIONAL': 38, 'VALIDATED': 44, 'NOT_SUPPORTED_SEEN': 22, 'SUPPORTED_SEEN': 1, 'NOT_CONFIRMED': 5}
- exit book (G01): {'BRK/all': 'sma_close_50', 'BRK/above_both': 'hold_60d', 'BRK/mixed': 'sma_close_50', 'BRK/below_both': None, 'PULL/all': None, 'PULL/above_both': None, 'PULL/mixed': 'hold60+low20', 'PULL/below_both': None, 'ANY/all': None, 'ANY/above_both': None, 'ANY/mixed': None, 'ANY/below_both': 'hold60+low20'}

## Guardrails

Stop for the day at a 5.0% loss; pause new entries when 22.0% below the high-water mark until Madhav resumes — recorded, not enforced (paper); enforcement is W7 live-readiness work
