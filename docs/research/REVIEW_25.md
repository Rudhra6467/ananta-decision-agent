# Review #25: the benchmark and the exposure dial (pre-registration)

Written 2026-10-10, before any code or run (Madhav, 2026-10-10: "Let's start and fix this engine"). The engine review found that
every idea that held up is about how much to be in the market and how long to hold, and none about precise entries. Before any
setup is judged again, two questions:

1. **The benchmark.** What does the simplest strategy earn: Bitcoin held only while its daily close is above its 50-day average
   (the gate review #7 supports), bought and sold at the next open, NDAX costs? Every Ananta strategy must beat this after costs to
   deserve live money; if none does, this is the live strategy.
2. **The exposure dial.** Does deciding how much to hold (not only in or out) improve the benchmark's return per unit of risk?

- **Variants (fixed now; nothing added after the first run):**
  - **HOLD:** Bitcoin bought and held (the reference, not a candidate).
  - **GATE50:** in when the close is above the 50-day average, else cash. **The benchmark.**
  - **GATE50_200:** in only when the close is above both the 50-day and the 200-day averages.
  - **GATE50_VOL:** GATE50, with the position sized to 40% annual volatility (the last 30 days' realized volatility), at most 100%,
    changed only when the target moves by a quarter or more (to limit costs).
  - **PAIR_GATE50:** half Bitcoin, half Ethereum, each with its own 50-day gate.
- **Data, splits:** the lake's daily candles (Binance spot). DISCOVERY 2018-01-01 to 2023-12-31; CONFIRM 2024-01-01 to the latest
  close. Costs: NDAX 0.20% fee plus the measured half spread, each side, on every change of position.
- **Measures:** total return, yearly return, worst fall from a peak (max drawdown), return / drawdown, daily Sharpe, time in the
  market, number of trades.
- **Pass for a dial variant:** better return / drawdown than GATE50 in BOTH periods, and not more than 20% lower total return in either.
  With 3 challengers, a win in one period only is reported as "mixed", never adopted.
- **What happens next:** GATE50 becomes the hurdle in the promotion rule (Universe Rule v2, section 8). A dial variant that passes
  becomes the exposure dial's first version on paper; if none passes, the dial starts as GATE50 itself.
