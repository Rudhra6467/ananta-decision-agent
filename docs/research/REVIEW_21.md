# Repair-shop review #21 (pre-registration): the last two queue items - E3 support bounce and B3 volume breakout

Written 2026-10-05, before any run (audit v1, re-test queue item 6; Madhav 2026-10-05: "complete all the pending research").

## Part A: Explorer E3 (bounce from support, 15m/1h)
- The SAME engine the live Explorer runs (`explorer_engine`, rules C0, as in the v0 scorecard) replayed on the lake's 5-minute
  candles (`explorer_replay.run_coin` with a lake loader), coins TOP30 and ALL 120 (LAB10 reported as the data check against the
  v0 scorecard's E3: +$0.36 per trade, 30 discovery fires).
- Measure: E3's real trades, net $ per $100 trade (NDAX costs, its own exits), minus the RANDOM shadow trades of the same type in
  the same period (the scorecard's baseline). Market events: trades within 3 days of each other count once.
- Pass: discovery 30+ market events, mean excess > 0 with z >= 2.5; confirm mean excess > 0. Portfolio caps are not applied
  (each coin's engine has its own slots), as in the v0 scorecard.

## Part B: B3 (a daily close through a resistance zone on 1.5x volume, H09)
- Review #11's code unchanged (`zones.review11`), on lake daily candles, TOP30 and ALL (LAB10 as the data check). Review #11's
  other variants (A1, B1, B2) are re-run and reported but were already FAIL; only B3 is a re-test.
- Pass: review #11's bar (discovery 30+ market events, 20-day excess over the same-condition average > 0 with z >= 2.5;
  confirm excess > 0).

## Splits
Discovery before 2024-01-01, confirm 2024-01-01 to 2026-07-31; holdout not loaded. Two items re-tested; nothing tuned.
