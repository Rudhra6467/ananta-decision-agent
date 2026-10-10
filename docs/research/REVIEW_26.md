# Review #26: the expected-value table (pre-registration)

Written 2026-10-10, before any code or run (engine fix 3). Today the brain's ranking uses points picked by hand. This review
replaces them with what history measured: for each daily rule, in each market state and liquidity tier, the average result per
trade after costs, against random entries in the same state and tier.

- **Rules (6, the universe's daily rules, the same code as live via watch_engine._fires):** H07, M1a, M2a, M2a-G, M3a, M3b.
- **Coins:** the lake's 120 (rule v1, delisted coins included, so dead coins count). Liquidity tier at each signal from the
  coin's median daily traded value over the previous 30 days: A >= $20M, B >= $1M, C below (Universe Rule v2).
- **Market state at each signal:** the exposure dial v1 (review #25): OPEN when Bitcoin closed above its 50-day and 200-day
  averages, else CLOSED.
- **Trades:** entry at the next day's open; exits exactly as live (H07: the next open after RSI(10) over 40, or 10 days; the
  setups: their stop, or 30 days); one trade at a time per rule and coin; the setups one episode per 20 days.
  Costs each side: NDAX 0.20% plus the tier's half-spread floor (A 0.20%, B 0.40%, C 0.80%).
- **Baseline:** random days of the same coins in the same tier and market state, held for the rule's time limit, same costs.
  Excess = trade net minus the baseline mean of its cell. Market days: trades exiting on the same day count once.
- **Splits:** DISCOVERY 2018-01-01 to 2023-12-31; CONFIRM 2024-01-01 to the latest close.
- **The table (what the engine uses):** per rule x state x tier: trades, market days, mean net %, mean excess %, z, in both
  periods. A cell's expected value is used only when DISCOVERY has >= 30 market days, mean excess > 0 with z >= 2, mean net > 0,
  and CONFIRM agrees in sign on both mean excess and mean net; its value is then the pooled mean excess shrunk toward zero by
  n / (n + 50) (n = market days). Every other cell is 0: no measured edge.
- **What changes:** the brain's ranking uses this value in place of the hand-picked points; the pack shows it; promotion still
  needs forward evidence. With 6 rules x 2 states x 3 tiers = 36 cells, a single cell passing is treated as a candidate, not proof.
