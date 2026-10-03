# Review #12: T3's exit vs trailing stops (zones, ATR, the 50-day) (pre-registration)

Written 2026-10-03, before any code or run. T3 (review #4) is the one book that passed: hold a coin while its close is above its
50- and 20-day averages and BTC is above its 50-day. Its exit is "close under the 20-day average". Reviews #10-#11 say the gains come
from a few big moves; does a looser, structure-based exit keep more of them?

- **Same entry for every variant** (T3's rule), same simulator as review #4 (`src/research/portfolio_trend.py`: equal share per
  available coin, daily decisions at the close, trades at the next open, NDAX costs, weekly rebalance), same data and splits
  (DISCOVERY before 2024-01-01, CONFIRM to 2026-08-01, holdout not loaded).
- **Exits (once in, stay in until):**
  - **T3** (control): the entry rule stops holding (close under the 20- or 50-day, or the BTC gate closes).
  - **T3Z** (zone trail): the BTC gate closes, or a close under the trailing zone stop. The stop = the bottom of the highest zone
    below the close minus 0.5 daily range (zones from `src/research/zones.py`, built from earlier bars only); it only moves up.
  - **T3A** (H15, chandelier): the BTC gate closes, or a close under the highest close since entry minus 3 daily ranges.
  - **T3W** (wide): the BTC gate closes, or a close under the 50-day average.
- **Pass:** a variant passes if its MAR (yearly return / max drawdown) beats T3's in both DISCOVERY and CONFIRM. Also reported:
  return, drawdown, trades, costs, the crisis windows of review #4.
