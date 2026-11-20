# India read model (V0) — data through 2026-11-19, built 2026-11-20T07:57:18+00:00

Rules readmodel-v0-2026-10-22. Every number below traces to the file named in its section of readmodel/latest.json; nothing here is typed by hand.

## Brief

- Through 2026-11-19: no Nifty close for the day (the index download did not run). Nifty's trend could not be read; n/a from the 50-day, n/a from the 200-day; 64% of the liquid 250 are above their 200-day.
- Daily call for the next session: BEARISH (mechanical rule call-v0-2026-10-18); so far 7 of 21 calls right against 12 for the coin flip, one seeded draw (chance alone averages 10.5).
- Stock paper book: 249 open positions; realised Rs -211,406 on the hold_20d exits across campaigns.
- New for the next session: 6 BRK, 5 CTL, 1 PULL.
- Marked: these picks were made on stale inputs (Nifty 50: stale: last row 2026-11-18; India VIX: stale: last row 2026-11-18; small-cap ratio: missing or stale).
- SP1 index line: Fri 20 Nov: 5 index decisions recorded, traded BANKNIFTY at D0 (long, exit NEXTOPEN). Book over 17 scored session(s): NIFTY: 4 scored trade(s), index +60 bp, one option lot Rs 3,393 with realistic fills; BANKNIFTY: 17 scored trade(s) (1 scored late), index +535 bp, one option lot Rs 43,431 with realistic fills.
- Against the reference traders (1 session): Ananta held 9 of the top 20 trips, passed on 4, had no rule for 4; its picks sat at the 41st percentile of random.

## Decisions for the next session

| symbol | campaign | close | why |
|---|---|---|---|
| WOCKPHARMA | BRK | 2187.0 | 20-session breakout on volume: volume 3.8x its 20-day, +12.0% from the 20-day average, +25.4% from the 200-day, liquidity rank 125 |
| HEROMOTOCO | BRK | 5556.0 | 20-session breakout on volume: volume 2.4x its 20-day, +4.7% from the 20-day average, +5.6% from the 200-day, liquidity rank 59 |
| IDFCFIRSTB | BRK | 86.05 | 20-session breakout on volume: volume 2.3x its 20-day, +11.9% from the 20-day average, +12.2% from the 200-day, liquidity rank 149 |
| HYUNDAI | BRK | 2219.2 | 20-session breakout on volume: volume 2.3x its 20-day, +9.7% from the 20-day average, +10.1% from the 200-day, liquidity rank 152 |
| SHADOWFAX | BRK | 313.6 | 20-session breakout on volume: volume 1.9x its 20-day, +9.2% from the 20-day average, +53.2% from the 200-day, liquidity rank 189 |
| UNITDSPR | BRK | 1460.0 | 20-session breakout on volume: volume 1.6x its 20-day, +6.8% from the 20-day average, +6.5% from the 200-day, liquidity rank 217 |
| MPHASIS | PULL | 2356.0 | pullback in an uptrend: volume 0.7x its 20-day, -5.2% from the 20-day average, +0.4% from the 200-day, liquidity rank 164 |
| ENGINERSIN | CTL | 307.5 | random control: no edge is claimed, it is the yardstick: volume 0.3x its 20-day, +8.0% from the 20-day average, +27.2% from the 200-day, liquidity rank 204 |
| KEI | CTL | 3826.2 | random control: no edge is claimed, it is the yardstick: volume 0.6x its 20-day, -2.2% from the 20-day average, -20.4% from the 200-day, liquidity rank 124 |
| GODREJPROP | CTL | 1881.0 | random control: no edge is claimed, it is the yardstick: volume 0.7x its 20-day, +9.3% from the 20-day average, +4.9% from the 200-day, liquidity rank 181 |
| TORNTPHARM | CTL | 4611.0 | random control: no edge is claimed, it is the yardstick: volume 0.7x its 20-day, -0.9% from the 20-day average, +1.2% from the 200-day, liquidity rank 133 |
| GLAND | CTL | 3292.9 | random control: no edge is claimed, it is the yardstick: volume 0.2x its 20-day, +4.9% from the 20-day average, +38.7% from the 200-day, liquidity rank 183 |

## Stock paper book (exec, policy shown: hold_20d)

| campaign | what | open | closed | realised Rs | unrealised Rs | win rate | expectancy R |
|---|---|---|---|---|---|---|---|
| BRK | 20-session breakout on volume | 51 | 17 | -4,398 | +121,265 | 0.29411764705882354 | 0.15373335854567413 |
| CTL | random control: no edge is claimed, it is the yardstick | 86 | 24 | -38,556 | +216,965 | 0.16666666666666666 | -0.4991304229355555 |
| PULL | pullback in an uptrend | 41 | 34 | -136,404 | +150,745 | 0.058823529411764705 | -0.9003308381102872 |
| REV | oversold reversal (RSI under 30, P01) | 52 | 17 | -32,048 | +243,217 | 0.17647058823529413 | -0.5423625368882694 |

## SP1 index line

Fri 20 Nov: 5 index decisions recorded, traded BANKNIFTY at D0 (long, exit NEXTOPEN). Book over 17 scored session(s): NIFTY: 4 scored trade(s), index +60 bp, one option lot Rs 3,393 with realistic fills; BANKNIFTY: 17 scored trade(s) (1 scored late), index +535 bp, one option lot Rs 43,431 with realistic fills

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
- postclose: PROBLEM steps failed inside the job (india.kite_index): token dead; next sign-in automatic at 20:10 Toronto, 06:40 IST (last automatic sign-in ok Thu 19 Nov 21:02 Toronto); by hand only if it fails, Sun 22 Nov 21:00-22:40 Toronto (07:30-09:10 IST, for the Mon 23 Nov session)
- preopen: ok
- recorder_noon: PROBLEM exit 1: token dead; next sign-in automatic at 20:10 Toronto, 06:40 IST (last automatic sign-in ok Thu 19 Nov 21:02 Toronto); by hand only if it fails, Sun 22 Nov 21:00-22:40 Toronto (07:30-09:10 IST, for the Mon 23 Nov session)
- replay: PROBLEM stuck: running (pid 53400) with no output for 99 h, since Sun 15 Nov 23:20
- schedulecheck: ok
- shadowtrader: ok
- sp1paper: ok
- sp1paper.score: PROBLEM steps failed inside the job (india.sp1paper): token dead; next sign-in automatic at 20:10 Toronto, 06:40 IST (last automatic sign-in ok Thu 19 Nov 21:02 Toronto); by hand only if it fails, Sun 22 Nov 21:00-22:40 Toronto (07:30-09:10 IST, for the Mon 23 Nov session)
- spreads: PROBLEM stuck: running (pid 17813) with no output for 29 h, since Wed 18 Nov 21:35
- studies: ok
- web: ok

Next sign-in: automatic at 20:10 Toronto, 06:40 IST (last automatic sign-in ok Thu 19 Nov 21:02 Toronto); by hand only if it fails, Sun 22 Nov 21:00-22:40 Toronto (07:30-09:10 IST, for the Mon 23 Nov session)

## Research

- studies: {'ready': 53, 'blocked': 11, 'with_results': 40}
- gate G02: {'state': 'BLOCKED', 'waiting_on': 'D15 (wait_time, 30 runs); D16 (wait_time, 30 snapshots); D32 (wait_time, weekly runs)'} counters {'D15': '33 of 30 nightly runs; 21 clean sessions in a row (the gate needs 30 in a row)', 'D16': '27 of 30 snapshots', 'D32': '2026-11-12: knows 18 of 18, unknowns 5 of 7, why 4 of 5, answers and decides 8 of 9, safety 39 of 39, plain words 37 of 39: FAIL; 4 of 7 runs passed'}
- registry verdicts: {'REJECTED': 511, 'OPPOSITE': 158, 'INCONCLUSIVE': 661, 'CONDITIONAL': 38, 'VALIDATED': 44, 'NOT_SUPPORTED_SEEN': 22, 'SUPPORTED_SEEN': 1, 'NOT_CONFIRMED': 5}
- exit book (G01): {'BRK/all': 'sma_close_50', 'BRK/above_both': 'hold_60d', 'BRK/mixed': 'sma_close_50', 'BRK/below_both': None, 'PULL/all': None, 'PULL/above_both': None, 'PULL/mixed': 'hold60+low20', 'PULL/below_both': None, 'ANY/all': None, 'ANY/above_both': None, 'ANY/mixed': None, 'ANY/below_both': 'hold60+low20'}

## Guardrails

Stop for the day at a 5.0% loss; pause new entries when 22.0% below the high-water mark until Madhav resumes — recorded, not enforced (paper); enforcement is W7 live-readiness work
