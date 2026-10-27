# GP1 registration v1: The opening gap: does buying the open after a gap-down (mean reversion) or after a gap-up (follow-through) beat ordinary days, after costs?

Written 2026-10-26, before any outcome was read. Asked by: Madhav, 26 Oct 2026 20:26 Toronto: "your recommendations sounds good, yes to all." (the recommendation: test the opening-gap rule, because Ananta had no tested gap rule)

**Family:** gaps. **Frozen bar:** k = 10, z = 2.807 (a new family 'gaps'; k frozen at the 10 variants below).

## Hypothesis

A stock or index that opens at least 1-2% below the previous close is worth buying at that open (the gap is an over-reaction that is partly given back over the next sessions); a stock that opens 2% or more above the previous close is worth buying, at that open or at the next session's open, because the gap continues. Either beats ordinary days over the same holding period, net of costs.

## Data

- **stocks:** gold/teachers/stock_panel.parquet (adjusted daily bars of the liquid universe, 2000-01-03 to 2023-12-29); events and base = liquidity rank 1-250 that day
- **index:** silver/kite_index/day (NIFTY 50, NIFTY BANK) 2003-2023: open and close of each session; silver/kite_index/5minute (2015-2023) for the wait-30-minutes version only
- **nothing_sealed:** no 2024+ row and no sealed folder is read; nothing was looked at for outcomes before this spec was written

## Definitions

- **gap:** today's open divided by yesterday's close, minus 1, where yesterday is the stock's previous session in the panel (a continuous run: n increments by 1) and the move is under 50% (an unadjusted corporate action is not a gap)
- **gapdown2 / gapdown1 (stocks):** gap <= -2% (or <= -1%); one event per stock per 10 sessions
- **gapup2 (stocks):** gap >= +2%; one event per stock per 10 sessions
- **open entries:** buy at today's open (the gap is known at the open, nothing later is used)
- **next entry (STK|gapup2|next|hold5):** the same gap-up days, but bought at the open of the following session
- **hold1 / hold5:** sold at the close of the entry session (hold1) or of the fifth session counting the entry session (hold5)
- **index events:** gap <= -1% or >= +1% (the 2% gap is too rare on the indices to test); one event per 5 sessions
- **wait30 (NIFTY|gapdown1|wait30|hold5):** the same gap-down days, but bought at the open of the 09:45 five-minute bar (30 minutes after the open) and sold at the close of the fifth session; the base is every session with the same entry and exit. 2015-2017 holds only 12 quarters, so a verdict is impossible in development (INCONCLUSIVE by the 16-block rule); the row is recorded for the numbers
- **windows with a one-day move over 50% inside the holding window:** skipped (an artefact, not a trade)
- **REV entries:** not used here; the gap rule is its own entry

## Outcomes

- **stocks:** (sale price / entry price - 1) minus the panel's cost column (delivery round trip plus the spread estimate by liquidity rank, india/costs.py). The one-session versions are charged the same delivery cost, which is conservative for an intraday trade
- **index:** (sale / entry - 1) minus 0.10% round trip (futures or ETF: charges plus slippage), fixed before the run

## Statistics

- **stocks vs ordinary days:** india.teachers_stock.level: event mean minus the mean of all base rows (every 5th session of every liquid-250 stock, plus the events) in the same quarter, outcome defined from the open exactly as the event's, t across quarters
- **stocks, the trade itself after costs:** india.teachers_stock.absolute: the event's own mean outcome, quarter means (reported in the extra fields)
- **index (market timing):** india.teachers_stock.msplit against all other sessions, quarter blocks, Welch t
- **periods:** development 2000-2017 (index from 2003, the 30-minute version from 2015), validation 2018-2023
- **verdict:** india/registry.record standard rule; MIN_DATES 16 blocks per period

## Variants (expected sign)

- `STK|gapdown2|open|hold1` (+)
- `STK|gapdown2|open|hold5` (+)
- `STK|gapdown1|open|hold5` (+)
- `STK|gapup2|open|hold5` (+)
- `STK|gapup2|next|hold5` (+)
- `NIFTY|gapdown1|open|hold5` (+)
- `NIFTY|gapup1|open|hold5` (+)
- `BANK|gapdown1|open|hold5` (+)
- `BANK|gapup1|open|hold5` (+)
- `NIFTY|gapdown1|wait30|hold5` (+)

## Not claimed

No paper rule changes from this study; a pass would be a proposal for Madhav, then a forward paper check. The gap rule is not tested on the sealed 2024+ data.
