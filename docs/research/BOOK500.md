# The $500 NDAX book (paper)

Written 2026-10-11 from Madhav's decisions D9 (the book), D12 (brakes) and D13 (NDAX only, CAD). The rules live in one
place, `src/research/book500.py`. The backtest below and the live paper book (`jarvis/service/ndax_book.py`) both call it,
so what was tested is what runs.

## Rules

| Sleeve | Share | What fills it |
|---|---|---|
| Core | up to 60% | BTC 40% + ETH 20% while the exposure dial is open (Bitcoin above its 50-day and 200-day averages, review #25); cash when it is closed |
| Measured edges | up to 30% | Only edges a review measured. Today that is one: H07 dips on tier-A NDAX coins while the dial is closed (review #26). Next-open entry, exit when RSI(10) closes over 40 or after 10 days, no stop (review #27) |
| Judgment | up to 10% | The brain's buys on NDAX coins (live paper only; cannot be replayed) |

- **Sizing:** 0.5% of the book at risk per setup trade, measured to an invalidation level 2 × ATR(14) under the entry.
- **Limits:** at most 10% of the book in one trade, at most 6% at risk across open setup trades, and at most 2 open in coins
  whose 90-day correlation is over 0.8.
- **NDAX:** CAD pairs only (68 coins, 19 of them tier A). Each instrument's minimum quantity and quantity step apply. Costs
  are the 0.20% fee a side plus the spread.
- **Brakes (D12, enforced in code, outside the AI; they stop new buys, exits always run):**
  - a day's loss of 2% (about $10): no buys the next day
  - a week's loss of 4% (about $20): no buys until Monday
  - 4 losing setup trades in a row: no buys for 7 days
  - a 15% fall from the peak (about $75): paused until Madhav resumes it (the backtest stands in 30 days)

## Backtest: 2018-2026, CAD, NDAX costs

Prices come from our lake's daily candles, converted to CAD with the Bank of Canada's daily USD/CAD rate. Each period starts
fresh with $500.

| Period | Book | Worst fall | Hold Bitcoin | Its worst fall | GATE50 (the hurdle) | Its worst fall |
|---|---|---|---|---|---|---|
| 2018-2023 | $2,229 (+346%) | -34% | $1,619 (+224%) | -80% | $2,565 (+413%) | -64% |
| 2024-Oct 2026 | $872 (+74%) | -22% | $1,055 (+111%) | -52% | $888 (+78%) | -35% |

- The book is in the core 35% of days (2018-2023) and 46% of days (2024-2026).
- Setup trades:
  - 39 trades in 2018-2023, 80% won, +5.7% a trade.
  - 28 trades in 2024-2026, 82% won, +4.5% a trade.
- Every size followed the rule: the largest risk seen on one trade was 0.50% of the book.

**Plainly:** the book does not beat the hurdle on return (-67 and -4 percentage points). It does fall about half as far as
the hurdle in both periods. Per unit of fall, it is the best of the three in both periods.

## What the brakes cost (for Madhav's decision)

| Period | With brakes | Without brakes |
|---|---|---|
| 2018-2023 | +346%, worst fall -34% | +473%, worst fall -38% |
| 2024-2026 | +74%, worst fall -22% | +70%, worst fall -22% |

The day brake fired 97 times in 2018-2023 and 34 times in 2024-2026. With 60% of the book in Bitcoin and Ethereum, a
3-4% crypto day is enough to trip it. Each time it skips buys the next day, and some of those were the best entries.

The brakes are a safety rule (D12), not a performance rule, so they stay exactly as decided. One option for Madhav: apply the
day and week brakes only to the setup sleeves and let the dial alone run the core.

## Stops resting on NDAX (D12)

| Stop | Setup trades 2024-2026 | Book 2024-2026 |
|---|---|---|
| none | +4.5% a trade | +74% |
| 2 × ATR | +1.9% | +67% |
| 4 × ATR | +4.2% | +73% |
| 6 × ATR | +4.5% (never touched) | +74% |

In 2018-2023 the book returned +346% with no stop or a 6 × ATR stop, and +339% with 2 × ATR. Recommended: 6 × ATR, as outage
insurance only (docs/LIVE_MONEY_SAFETY.md).

## Caveats

- **Survivorship:** the coins are today's tier-A NDAX list. Coins that died since 2018 are not in it.
- **Judgment sleeve:** not tested here.
- **NDAX spreads:** the backtest uses our cost model. The live book fills at NDAX's own bid and ask, so the live numbers will
  show the real spread.
- **Files:** the backtest's full output is in `~/ananta_runs/book500/book500_backtest.json`.
