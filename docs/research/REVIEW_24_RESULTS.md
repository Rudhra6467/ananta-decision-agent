# Review #24 results: tuning the deep-dip buy (E6)

Run 2026-10-11 on lab5_5m.sqlite (the live 10 coins, 15-minute candles), with the pre-registered rules in REVIEW_24.md.
Per $100 trade after NDAX costs; the baseline is random entries on the same coins, traded with the same exits.

| Variant | Period | Trades | Win rate | Net per trade | Random | Excess |
|---|---|---|---|---|---|---|
| E6 as live | DISCOVERY (to 2023) | 15,635 | 27.6% | -$0.54 | -$0.58 | +$0.03 |
| E6 as live | CONFIRM (2024-2026) | 8,071 | 22.1% | -$0.64 | -$0.60 | -$0.05 |
| E6-NOBELL | DISCOVERY | 9,025 | 51.7% | -$0.39 | -$0.51 | +$0.12 |
| E6-NOBELL | CONFIRM | 4,530 | 48.8% | -$0.50 | -$0.47 | -$0.02 |
| E6-ROOM | DISCOVERY | 11,383 | 29.5% | -$0.52 | -$0.58 | +$0.06 |
| E6-ROOM | CONFIRM | 5,653 | 25.3% | -$0.63 | -$0.60 | -$0.03 |

**Verdict: none passes.** Every variant loses money after costs in both periods (the pass needs mean net > 0 in both), and
every variant's excess over random turns negative in CONFIRM. Dropping the warning bells doubles the win rate but the
wins are too small to pay the costs. Asking for 2% room changes almost nothing.

**Not run:** E6-ZONE and E6-ZONE-NOBELL. The replay engine has no zone history at 15-minute resolution, so the zone filter
cannot be applied fairly to the past. They are not run rather than approximated; review #27 already found that a plain
zone touch loses money on daily candles.

**What follows (as pre-registered):** E6 stays as it is on paper, and tuning did not save it. Combined with review #28, the
Explorer's setups no longer wake the brain (points 0). E6 keeps recording as evidence.
