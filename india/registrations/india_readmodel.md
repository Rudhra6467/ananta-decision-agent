# India read model (V0) — data through 2026-10-29, built 2026-10-30T11:20:05+00:00

Rules readmodel-v0-2026-10-22. Every number below traces to the file named in its section of readmodel/latest.json; nothing here is typed by hand.

## Brief

- Through 2026-10-29: Nifty 22,937. Nifty is below both its 50- and 200-day averages: a downtrend; -1.5% from the 50-day, -4.6% from the 200-day; 44% of the liquid 250 are above their 200-day.
- Daily call for the next session: BULLISH (mechanical rule call-v0-2026-10-18); so far 2 of 8 calls right against 4 for the coin flip.
- Stock paper book: 134 open positions; realised Rs -149,903 on the hold_20d exits across campaigns.
- New for the next session: 3 BRK, 5 CTL, 1 REV.
- SP1 index line: Fri 30 Oct: 5 index decisions recorded, traded BANKNIFTY at D0 (long, exit NEXTOPEN). Book over 5 scored session(s): BANKNIFTY: 4 scored trade(s), index -116 bp, one option lot Rs -13,575 with realistic fills.
- Against the reference traders (1 session): Ananta held 6 of the top 20 trips, passed on 3, had no rule for 10; its picks sat at the 40th percentile of random.

## Decisions for the next session

| symbol | campaign | close | why |
|---|---|---|---|
| ADANIPORTS | BRK | 1872.0 | 20-session breakout on volume: volume 2.5x its 20-day, +6.4% from the 20-day average, +13.3% from the 200-day, liquidity rank 41 |
| GESHIP | BRK | 1618.8 | 20-session breakout on volume: volume 1.7x its 20-day, +5.3% from the 20-day average, +15.5% from the 200-day, liquidity rank 168 |
| KOTAKBANK | BRK | 459.0 | 20-session breakout on volume: volume 1.7x its 20-day, +5.0% from the 20-day average, +14.6% from the 200-day, liquidity rank 17 |
| IFCI | REV | 58.26 | oversold reversal (RSI under 30, P01): volume 0.3x its 20-day, -9.8% from the 20-day average, -13.9% from the 200-day, liquidity rank 55 |
| TFCILTD | CTL | 159.66 | random control: no edge is claimed, it is the yardstick: volume 1.0x its 20-day, +5.7% from the 20-day average, +71.6% from the 200-day, liquidity rank 114 |
| TVSMOTOR | CTL | 4280.0 | random control: no edge is claimed, it is the yardstick: volume 2.7x its 20-day, +6.4% from the 20-day average, +12.9% from the 200-day, liquidity rank 58 |
| CIPLA | CTL | 1358.0 | random control: no edge is claimed, it is the yardstick: volume 1.0x its 20-day, +1.9% from the 20-day average, -0.5% from the 200-day, liquidity rank 164 |
| CUMMINSIND | CTL | 4515.2 | random control: no edge is claimed, it is the yardstick: volume 1.1x its 20-day, -3.3% from the 20-day average, -10.0% from the 200-day, liquidity rank 90 |
| DMART | CTL | 3175.0 | random control: no edge is claimed, it is the yardstick: volume 1.3x its 20-day, -6.5% from the 20-day average, -19.8% from the 200-day, liquidity rank 118 |

## Stock paper book (exec, policy shown: hold_20d)

| campaign | what | open | closed | realised Rs | unrealised Rs | win rate | expectancy R |
|---|---|---|---|---|---|---|---|
| BRK | 20-session breakout on volume | 16 | 2 | -7,339 | +9,525 | 0.0 | -1.0424985873380148 |
| CTL | random control: no edge is claimed, it is the yardstick | 35 | 5 | -15,204 | +60,380 | 0.0 | -1.0580752528049178 |
| PULL | pullback in an uptrend | 34 | 21 | -89,624 | +51,423 | 0.0 | -1.0439123071553598 |
| REV | oversold reversal (RSI under 30, P01) | 49 | 10 | -37,736 | +78,090 | 0.0 | -1.0513513669999683 |

## SP1 index line

Fri 30 Oct: 5 index decisions recorded, traded BANKNIFTY at D0 (long, exit NEXTOPEN). Book over 5 scored session(s): BANKNIFTY: 4 scored trade(s), index -116 bp, one option lot Rs -13,575 with realistic fills

## Jobs

- allocator: ok
- autologin: ok
- evening: ok
- findings: ok
- kitefill: ok
- morning: ok
- morningview: ok
- netnotes: ok
- nightly: ok
- openingview: ok
- paper: ok
- postclose: ok
- recorder_noon: ok
- replay: ok
- shadowtrader: ok
- sp1paper: ok
- sp1paper.score: ok
- spreads: ok
- web: ok

Next sign-in: automatic at 21:40 Toronto (last automatic sign-in ok Thu 29 Oct 21:40 Toronto); by hand only if it fails, Sun 01 Nov 21:00-22:40 Toronto (07:30-09:10 IST, for the Mon 02 Nov session)

## Research

- studies: {'ready': 53, 'blocked': 11, 'with_results': 40}
- gate G02: {'state': 'BLOCKED', 'waiting_on': 'D15 (wait_time, 30 runs); D16 (wait_time, 30 snapshots); D32 (wait_time, weekly runs)'} counters {'D15': '12 of 30 nightly runs; 7 clean sessions in a row (the gate needs 30 in a row)', 'D16': '9 of 30 snapshots', 'D32': '2026-10-30: knows 16 of 18, unknowns 7 of 7, why 4 of 5, answers and decides 8 of 9, safety 39 of 39, plain words 38 of 39: FAIL; 4 of 5 runs passed'}
- registry verdicts: {'REJECTED': 487, 'OPPOSITE': 155, 'INCONCLUSIVE': 650, 'CONDITIONAL': 37, 'VALIDATED': 33, 'NOT_SUPPORTED_SEEN': 19, 'SUPPORTED_SEEN': 1, 'NOT_CONFIRMED': 5}
- exit book (G01): {'BRK/all': 'sma_close_50', 'BRK/above_both': 'hold_60d', 'BRK/mixed': 'sma_close_50', 'BRK/below_both': None, 'PULL/all': None, 'PULL/above_both': None, 'PULL/mixed': 'hold60+low20', 'PULL/below_both': None, 'ANY/all': None, 'ANY/above_both': None, 'ANY/mixed': None, 'ANY/below_both': 'hold60+low20'}

## Guardrails

Stop for the day at a 5.0% loss; pause new entries when 22.0% below the high-water mark until Madhav resumes — recorded, not enforced (paper); enforcement is W7 live-readiness work
