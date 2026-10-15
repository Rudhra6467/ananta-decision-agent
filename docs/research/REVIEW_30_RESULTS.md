# Repair-shop review #30 results: the survivorship check for the live 10 (T3-B on the point-in-time top 10)

Run 2026-10-15 09:13 Toronto on the pre-registration in `REVIEW_30.md`, unchanged. Madhav's decision was written into it before
the run (09:10: "30 yes b": run it; the gate's survivorship check counts only the tiers that could trade real money).
Results file: `~/ananta_lake/reports/review30_results.json`; the tier: `~/ananta_lake/reports/pit_top10.json`.

## Data
- PIT10 = for each month, the 10 most-traded Binance spot coins over the 3 months before (earlier data only). 64 coins were
  ever in it (Nov 2017 to Sep 2026, 107 months); all 64 loaded; 9.3 members per day on average (a coin needs 3 months of
  history). 54 of the 64 are not in today's 10 (LUNA, EOS, BNB, DOT, SHIB, MATIC, FTM, APE, PEPE, TRX and more).
- One loader fix, made before any result (the first run stopped while loading): 15 of the 64 (APE, AXS, CHZ, CYBER, GMT, ID,
  IOTA, LUNA, MANA, NEO, NOT, ONT, QTUM, XTZ, YFI) are held as Binance's own daily candles since the lake extension of
  Oct 9-11 (`lake_extend`, 303 coins outside the 120), which re-wrote their daily files without the minute-coverage column
  `share`. `src/lake/research.daily` failed on them ("share" not found). Such files now load as complete days, the same rule
  as review #29's loader (kept by Madhav on Oct 15); files built from minute data still drop days under 97% coverage. Test:
  `tests/test_lake.py::test_daily_loads_binance_daily_candles_that_have_no_share_column`. Ticket TK16.
- LUNA's re-used ticker is cut at 2022-05-31 (`ENDS`), as in review #22. No coin was fetched.

## T3-B on PIT10
| | Discovery (to 2023) | Confirm (2024 - Jul 2026) |
| --- | --- | --- |
| Buy and hold, same PIT10 coins | +29.6%, worst fall 91.2%, MAR 0.05 | -31.9%, worst fall 68.5%, MAR -0.20 |
| T3-B | +589.3%, worst fall 63.9%, MAR 0.57 | **+3.7%**, worst fall 39.0%, MAR 0.04 |

T3's rule (a positive return, a smaller worst fall and a better MAR than holding, in both periods): **PASS** (2,679 trades).

Beside it, not tested: on today's lab 10 (review #20) T3-B made +6,162% / +15.1% (worst fall 47% / 41%) and holding made
+2,575% / -21.6%. So the live 10's history was strongly flattered too: on the coins that really were the 10 most traded,
T3-B's 2024-26 result shrinks from +15.1% to +3.7%, and its discovery result from +6,162% to +589%. It still passes: it made a
little money while holding the same coins lost 31.9%, and it fell about half as far.

Costs matter: T3-B's costs added up to 42% of the starting equity over 2024-26 (95% over 2018-23). Review #20 found every T3
version loses at double costs; NDAX's 0.20% fee stays a must.

## What follows (as pre-registered, scope b)
- Gate: `data_survivorship` PASS (the 30-coin tier in #22, the live 10 here). `strategy_survivorship` PASS: it counts the live
  10 only (Madhav's scope b); the 30-coin tier failed (#22) and is labelled evidence only.
- The agent pack: T3's knowledge line, status card and strategy status add "passes point-in-time on the 10 (#30), much weaker
  than on today's 10". The 30-coin books' cards say evidence only, never a candidate for real money.
- Q9 leaves the queue. Rule A is unchanged: no real money until 60 market days, both dial states and execution within 3 points.
- Reading for the agent: on the live 10, T3-B is "lose much less in slides, make a little"; do not quote +15.1% as its edge.
