# Review #14: the short dip trade (H07) against a fair baseline (pre-registration)

Written 2026-10-03, before any code or run. Review #13 found H07 (above the 200-day, RSI(10) under 30; sell when RSI(10) is back
over 40 or after 10 days) made about +4% per trade with about 70% wins in both periods, but it was never compared with ordinary days
traded the same way. In an uptrend almost any entry with a quick exit can look good.

- **Signal (H07):** the close above the 200-day average and RSI(10) under 30; buy at the next open. **H07-G:** the same with the
  market allowed (BTC above its 50-day).
- **Exit (both and the baseline):** sell at the next open after a close with RSI(10) over 40, or at the open 10 days after entry.
- **Baseline:** every day of the same coin and split with the same condition (above the 200-day; for H07-G also the market allowed),
  traded with the same exit. Excess = trade net minus the coin's baseline mean. NDAX costs both ways.
- **Data, splits, events:** lab-10 coins, DISCOVERY before 2024-01-01, CONFIRM to 2026-08-01, holdout not loaded; one signal per coin
  per 5 days; market events = coins within 3 days.
- **Pass (2 variants):** DISCOVERY ≥ 30 market events, mean excess > 0, z ≥ 2.5; CONFIRM mean excess > 0.
- If one passes, it becomes a **paper shadow** first (recorded live, no money), never a trade without Madhav's sentence.
