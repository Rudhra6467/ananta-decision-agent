# TS1 registration v1: Trailing stop or fixed stop: on the same entries, does a trailing stop beat a fixed one, and does either beat simply holding 20 sessions?

Written 2026-10-26, before any outcome was read. Asked by: Madhav, 26 Oct 2026 20:26 Toronto: "your recommendations sounds good, yes to all." (the recommendation: test trailing stops against fixed stops directly; E02 compared exits against a time-matched null, never one stop rule against another)

**Family:** stop. **Frozen bar:** k = 116, z = 3.52 (families 'exit' (93 rows) and 'stop' (15 rows) already in the ledger plus these 8 variants; k frozen at 116 (the strictest bar of the three studies, because exit rules have been tried more often than anything else)).

## Hypothesis

On the campaigns' own entries, a stop that trails the price (2 ATR below the peak, or 10% below the peak) earns more per trade after costs than a fixed stop (7% below entry, or 2 ATR below entry), and a stop rule earns more than selling at the close of the 20th session.

## Data

- **entries:** the same entries as the E02 exit campaign: the unique (stock, signal date) pairs in gold/studies/E02-ANY, E02-BRK and E02-PULL trades (ANY = liquid-250 stock days, BRK = 20-session breakout on 1.5x volume above the 200-day, PULL = 5% under the 20-day while above the 200-day, as india/studies.py entry_sets defines them) signals 2000-2023 (about 150,000 entries in ANY, 22,000 in BRK, 18,000 in PULL: every signal the campaign generated; the numbers were counted, no outcome was read). There is no REV set in the campaigns, so none is used
- **bars:** gold/bars/adj_daily via india.exitlab.load_bars (adjusted bars to 2023-12-29); features gold/features/daily.parquet for ATR14 and liquidity rank
- **nothing_sealed:** no 2024+ row and no sealed folder is read; nothing was looked at for outcomes before this spec was written

## Definitions

- **entry:** signal on the close of day t, buy at the open of day t+1 (the exitlab convention); the same window, data-hygiene skips and corporate-action skips as india.exitlab.simulate
- **fixed2atr:** initial stop 2 ATR14 below the entry, never moved; sold at the stop (or at the open if it gapped through), else at the close of the 60th session (exitlab hold_60d)
- **fixed7:** stop 7% below the entry, never moved; the same 60-session cap
- **trail2atr:** initial stop 2 ATR below the entry, then 2 ATR below the highest high since entry, only ever raised (exitlab atr_trail_2); the same 60-session cap
- **trail10:** initial stop 10% below the entry, then 10% below the highest high since entry, only ever raised; the same 60-session cap
- **hold20:** the exitlab hold_20d benchmark: the 2 ATR initial stop, otherwise sold at the open after the 20th session's close
- **fills:** a stop fills at the stop price, or at the open if the open is already through it; stop and target in the same bar counts as the stop (exitlab rules, reused: india.exitlab._exit)
- **costs:** the delivery round trip plus the spread estimate by liquidity rank, on a Rs 50,000 notional, exactly as india.exitlab._row; the same costs for every rule (a stop out costs the same as a time exit)

## Outcomes

net return per trade (sale value minus notional minus costs, over notional) for each rule on each entry; a comparison is rule A minus rule B on the SAME entry

## Statistics

- **comparison:** per entry, net_A minus net_B; mean by calendar quarter of the signal date, t across quarters (the registry's standard: quarters are the independent blocks)
- **periods:** development signals 2000-2017, validation 2018-2023
- **extras reported:** mean net per trade for each rule and period, share stopped out, mean days held, 5th percentile and worst trade
- **verdict:** india/registry.record standard rule; MIN_DATES 16 blocks per period

## Variants (expected sign)

- `ANY|fixed7_vs_hold20` (+)
- `ANY|fixed2atr_vs_hold20` (+)
- `ANY|trail2atr_vs_hold20` (+)
- `ANY|trail10_vs_hold20` (+)
- `ANY|trail2atr_vs_fixed2atr` (+)
- `ANY|trail10_vs_fixed7` (+)
- `BRK|trail2atr_vs_fixed2atr` (+)
- `PULL|trail2atr_vs_fixed2atr` (+)

## Not claimed

No paper rule changes from this study; the paper engine's exits stay as they are. A pass would be a proposal for Madhav, then a forward paper check.
