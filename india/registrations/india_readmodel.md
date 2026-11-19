# India read model (V0) — data through 2026-11-18, built 2026-11-19T07:58:10+00:00

Rules readmodel-v0-2026-10-22. Every number below traces to the file named in its section of readmodel/latest.json; nothing here is typed by hand.

## Brief

- Through 2026-11-18: Nifty 25,228. Nifty is above both its 50- and 200-day averages: an uptrend; +7.7% from the 50-day, +5.2% from the 200-day; 63% of the liquid 250 are above their 200-day.
- Daily call for the next session: BEARISH (mechanical rule call-v0-2026-10-18); so far 7 of 21 calls right against 12 for the coin flip, one seeded draw (chance alone averages 10.5).
- Stock paper book: 248 open positions; realised Rs -242,685 on the hold_20d exits across campaigns.
- New for the next session: 5 CTL, 1 PULL.
- SP1 index line: Thu 19 Nov: session lost: no Kite sign-in by 09:10 IST: the Kite token expired at 6 am IST: open http://127.0.0.1:8100/kite/login on the Mac. Book over 17 scored session(s): NIFTY: 4 scored trade(s), index +60 bp, one option lot Rs 3,393 with realistic fills; BANKNIFTY: 16 scored trade(s) (1 scored late), index +568 bp, one option lot Rs 48,172 with realistic fills.
- Against the reference traders (1 session): Ananta held 15 of the top 20 trips, passed on 0, had no rule for 3; its picks sat at the 50th percentile of random.

## Decisions for the next session

| symbol | campaign | close | why |
|---|---|---|---|
| FCL | PULL | 44.63 | pullback in an uptrend: volume 1.7x its 20-day, -11.3% from the 20-day average, +18.0% from the 200-day, liquidity rank 197 |
| RVNL | CTL | 189.0 | random control: no edge is claimed, it is the yardstick: volume 0.9x its 20-day, -0.9% from the 20-day average, -23.5% from the 200-day, liquidity rank 231 |
| NAM-INDIA | CTL | 1052.6 | random control: no edge is claimed, it is the yardstick: volume 1.5x its 20-day, +4.3% from the 20-day average, -0.2% from the 200-day, liquidity rank 168 |
| SIEMENS | CTL | 3520.0 | random control: no edge is claimed, it is the yardstick: volume 0.6x its 20-day, +1.5% from the 20-day average, -1.7% from the 200-day, liquidity rank 213 |
| ADANIENSOL | CTL | 1490.0 | random control: no edge is claimed, it is the yardstick: volume 2.2x its 20-day, +7.8% from the 20-day average, +10.9% from the 200-day, liquidity rank 88 |
| PAYTM | CTL | 1890.0 | random control: no edge is claimed, it is the yardstick: volume 0.7x its 20-day, +8.1% from the 20-day average, +40.8% from the 200-day, liquidity rank 20 |

## Stock paper book (exec, policy shown: hold_20d)

| campaign | what | open | closed | realised Rs | unrealised Rs | win rate | expectancy R |
|---|---|---|---|---|---|---|---|
| BRK | 20-session breakout on volume | 55 | 13 | -9,989 | +107,992 | 0.23076923076923078 | 0.04112966084165474 |
| CTL | random control: no edge is claimed, it is the yardstick | 88 | 17 | -29,593 | +165,301 | 0.11764705882352941 | -0.5008453279532549 |
| PULL | pullback in an uptrend | 42 | 32 | -151,226 | +142,281 | 0.0 | -1.0373457153223753 |
| REV | oversold reversal (RSI under 30, P01) | 55 | 14 | -51,877 | +231,389 | 0.0 | -1.050785415684926 |

## SP1 index line

Thu 19 Nov: session lost: no Kite sign-in by 09:10 IST: the Kite token expired at 6 am IST: open http://127.0.0.1:8100/kite/login on the Mac. Book over 17 scored session(s): NIFTY: 4 scored trade(s), index +60 bp, one option lot Rs 3,393 with realistic fills; BANKNIFTY: 16 scored trade(s) (1 scored late), index +568 bp, one option lot Rs 48,172 with realistic fills

## Jobs

- autologin: PROBLEM exit 1: no error line in the log tail (that run ended Wed 18 Nov 20:40)
- evening: ok
- evening_zerodha: PROBLEM empty run: recorder: 0 contracts saved since 20:25; steps failed inside the job (india.ledger, india.recorder, step): token dead; next sign-in Thu 19 Nov 21:00-22:40 Toronto (07:30-09:10 IST, for the Fri 20 Nov session); the automatic sign-in is failing (no request_token in the Kite redirect chain (last status 400); the Kite Connect app's redirect URL or the session may ha)
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
- replay: PROBLEM stuck: running (pid 53400) with no output for 75 h, since Sun 15 Nov 23:20
- schedulecheck: ok
- shadowtrader: ok
- sp1paper: PROBLEM empty run: IST 2026-11-19: plan NO, 0 decision rows, errors ['no Kite sign-in by 09:10 IST: the Kite token expired at 6 am IST: open http://127.0.0.1:8100/kite/login on the Mac']
- sp1paper.score: ok
- spreads: PROBLEM empty run: IST 2026-11-19: 0 depth snapshots
- studies: ok
- web: ok

Next sign-in: Thu 19 Nov 21:00-22:40 Toronto (07:30-09:10 IST, for the Fri 20 Nov session); the automatic sign-in is failing (no request_token in the Kite redirect chain (last status 400); the Kite Connect app's redirect URL or the session may ha)

## Research

- studies: {'ready': 53, 'blocked': 11, 'with_results': 40}
- gate G02: {'state': 'BLOCKED', 'waiting_on': 'D15 (wait_time, 30 runs); D16 (wait_time, 30 snapshots); D32 (wait_time, weekly runs)'} counters {'D15': '32 of 30 nightly runs; 20 clean sessions in a row (the gate needs 30 in a row)', 'D16': '26 of 30 snapshots', 'D32': '2026-11-12: knows 18 of 18, unknowns 5 of 7, why 4 of 5, answers and decides 8 of 9, safety 39 of 39, plain words 37 of 39: FAIL; 4 of 7 runs passed'}
- registry verdicts: {'REJECTED': 511, 'OPPOSITE': 158, 'INCONCLUSIVE': 661, 'CONDITIONAL': 38, 'VALIDATED': 44, 'NOT_SUPPORTED_SEEN': 22, 'SUPPORTED_SEEN': 1, 'NOT_CONFIRMED': 5}
- exit book (G01): {'BRK/all': 'sma_close_50', 'BRK/above_both': 'hold_60d', 'BRK/mixed': 'sma_close_50', 'BRK/below_both': None, 'PULL/all': None, 'PULL/above_both': None, 'PULL/mixed': 'hold60+low20', 'PULL/below_both': None, 'ANY/all': None, 'ANY/above_both': None, 'ANY/mixed': None, 'ANY/below_both': 'hold60+low20'}

## Guardrails

Stop for the day at a 5.0% loss; pause new entries when 22.0% below the high-water mark until Madhav resumes — recorded, not enforced (paper); enforcement is W7 live-readiness work
