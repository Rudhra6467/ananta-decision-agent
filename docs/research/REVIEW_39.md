# Review 39: is the buy-in-thirds core at least as good as the all-in core it replaced?

Written 10 Nov 2026, before the data is touched. Rule B is lifted for this review and review 40 only, by Madhav (10 Nov 2026 08:41 Toronto,
"yes", to: "fix the faults, run the two studies on history, and bring you the short-dip decision and the study results before any live rule
changes"). No live rule changes on this result without his separate yes.

## 1. Why
The $500 book's core has bought in thirds since 24 Oct 2026 (core-v2: discipline_v1.json, `jarvis/service/ndax_book.py` step,
`jarvis/service/discipline.py` core_targets). It was never backtested: the pinned backtest (`src/research/book500.py`) holds the old all-in
core. Rule A compares live with a backtest of a different rule (the outsider's review, 10 Nov 2026).

## 2. The tier that decides
Not a coin list: the core is Bitcoin and Ethereum only, by weight (BTC 0.40, ETH 0.20). One row decides: THIRDS against ALLIN.

## 3. The test
Daily candles of BTC and ETH from the lake (`review25.daily`, Binance, US dollars). A decision is made on a day's close and filled at the
next day's open. Cost on every fill: the NDAX fee plus the coin's half-spread from the dated table (`src/intelligence/ndax_costs.py`).
The book starts at 500; the part outside the core sits in cash and earns nothing. No edge trades, no brakes (the core only).
Periods: DISCOVERY 2018-01-01 to 2023-12-31; CONFIRM 2024-01-01 to the last candle on file.

- **ALLIN** (the old core): when Bitcoin closes above both its 50-day (EMA) and 200-day (SMA) averages and no core is held, buy BTC 40% and
  ETH 20% of the book. When Bitcoin closes below either, sell the whole core.
- **THIRDS** (the live core, as coded): the dial's three states (CLOSED; FRAGILE = open and under 3% above the 50-day; CONFIRMED = open and
  3% or more above), `discipline.core_targets` called as the live step calls it (first fill at most 20% of the book, then thirds; the next
  third needs CONFIRMED, a Bitcoin close above its 20-day average, a later session and fewer than three thirds done), the trim back to the
  cap beyond the trim band, each coin sold on a daily close under its own 50-day average, the whole core sold when the dial closes, and no buy
  under max(5, 1% of the book). Parameters are the live file's own; none is tuned here.

Reported beside, never deciding: Bitcoin just held at 60% of the book; "60% Bitcoin by the plain 50-day rule" (the hurdle at the core's
weight); entries per year; time in the market; cost paid.

## 4. Pass marks (frozen)
THIRDS passes when, in BOTH periods:
1. its yearly return divided by its worst fall (CAGR / |max drawdown|, on daily closes) is at least ALLIN's, and
2. it ends each period above its starting money after costs.
One look. Anything else is a fail.

## 5. What each outcome changes (decided now)
- Pass: the thirds core has its backtest; `docs/research/BOOK500.md` gets a dated note with the figures. Nothing live changes.
- Fail: the result goes to Madhav with both rows. The choice (keep thirds, return to all-in, or something else) is his; nothing live changes
  on the result itself.
Either way review 40 then runs on the version that had the better CAGR / |max drawdown| in DISCOVERY (written here so the result cannot bend it).

## 6. Not in this review
The edge trades, the brakes, Ethereum's place in the core, other thresholds, other coins, intraday data.
