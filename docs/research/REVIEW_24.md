# Review #24: tuning the deep-dip buy (E6) (pre-registration)

Written 2026-10-08, before any code or run (Madhav's request #15). Live paper: E6 (15-minute RSI under 30) is the Explorer's busiest
setup: 115 of 138 real trades, 10 won, -$0.89 per $100 after costs. Most closed early for small losses when the hourly warning bell
(price under the 50-hour average) rang. Review #3 found buying 15m RSI under 30 beats random entries before costs but not after.
The question: does any simple change to the entry or the exit turn it positive after costs, against a fair baseline?

- **Variants (4, fixed now; nothing added after the first run):**
  - **E6-NOBELL:** the same entry; exits only by stop, target or time (no warning bells).
  - **E6-ZONE:** the same entry, only inside a zone our reviews support (new swing zone or the 200-day average) with the market
    allowed (BTC above its 50-day); the same exits as live.
  - **E6-ROOM:** the same entry, only when there is at least 2% room to the target (live W2 uses 1.2%); the same exits.
  - **E6-ZONE-NOBELL:** E6-ZONE with E6-NOBELL's exits.
- **Baseline:** random entries on the same coin, the same hours and the same market condition, traded with the variant's exit.
  Excess = trade net minus the baseline mean. NDAX costs (0.20% fee + half-spread) both ways.
- **Data, splits, events:** the live 10 coins, 15-minute candles; DISCOVERY before 2024-01-01, CONFIRM 2024-01-01 to 2026-08-01;
  one entry per coin per 4 hours; market events = trades closing on the same day count once.
- **Pass (each variant):** DISCOVERY >= 30 market events, mean excess > 0, z >= 2.5, and mean net per trade > 0 after costs;
  CONFIRM mean excess > 0 and mean net > 0. With 4 variants, the best one must also clear z >= 2.8 (multiple tries).
- **Live check alongside:** the live E6 record keeps running unchanged; its numbers are reported, not used to pick a variant.
- **If one passes:** it runs on paper next to E6 (both recorded) for 10 market events before Madhav decides. If none passes: E6 stays
  as is, and the report says plainly that tuning did not save it.
