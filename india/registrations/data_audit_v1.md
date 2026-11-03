# The data-set audit, first version (3 Nov 2026)

Madhav asked for this before any new research (flag 63): how wide and how good each data set is. Research years only (to 2023); the sealed years are counted by their own manifest and not opened. Nothing trades from it.

## What we have

| data | rows | research years | live to |
|---|---|---|---|
| gold/bars | 6,647,204 | 1994-2023 | - |
| gold/features | 3,456,514 | 1995-2023 | - |
| gold/hypothesis_map | 137 | - | - |
| gold/universe | 6,812,969 | 1995-2023 | - |
| silver/calendar | 8,377 | 1994-2026 | - |
| silver/cm_bhavcopy | 9,883,851 | 1994-2023 | 2026-10-30 |
| silver/corporate_actions | 325,732 | 1994-2026 | - |
| silver/delivery | 7,664,008 | 2003-2023 | 2026-10-30 |
| silver/flows | 39,404 | 2000-2023 | 2026-10-30 |
| silver/fo_bhavcopy | 157,536,583 | 2000-2023 | 2026-10-30 |
| silver/fo_calendar | 4,489 | - | - |
| silver/fo_greeks | 3,402,929 | 2001-2023 | 2026-10-30 |
| silver/ipo | 681 | - | - |
| silver/kite_5m | 83,610,866 | 2015-2023 | 2026-10-23 |
| silver/kite_day | 1,533,700 | 2003-2023 | 2026-10-16 |
| silver/kite_index/5minute | 1,029,458 | 2015-2023 | 2026-10-30 |
| silver/kite_index/day | 230,382 | 2003-2023 | 2026-10-30 |
| silver/kite_index/minute | 5,146,641 | 2015-2023 | 2026-10-30 |
| silver/macro | 85,013 | 1990-2026 | - |
| silver/pr | 8,746,016 | 2010-2023 | 2026-10-30 |
| silver/reference | 756 | - | - |
| silver/security_master | 14,878 | - | - |
| silver/valuation | 17,486 | 1999-2023 | 2026-10-30 |

## What the audit found

- **company results** (high): results with revenue and EPS are parsed for 2022, 2023 only; earlier years hold the filing but not its numbers (2017: 2 of 12, 2018: 2 of 7638, 2019: 12 of 9362, 2020: 18 of 11268, 2021: 23 of 11525); the results index lists filings from 2007, but the parsed table starts in 2018, and the old HTML result pages before 2018 are not parsed at all (D20b). So: a per-stock P/E or results study can use 2022-2023 only today; that is too short for the registry's strict bar.
- **company announcements** (medium): years with under half the count of the years either side: 2022: 22,367 (2021: 113,496, 2023: 131,213). So: any study of announcements must leave out or flag those years; refetch them first.
- **intraday stock bars (5-minute)** (medium): coverage of the day's 250 most traded rises from 56% in 2015 to 89% in 2023; lowest 2015. So: intraday stock studies before about 2019 see only part of the liquid market; say so or start them in 2019.
- **the research universe** (medium): in 2023, 1,765 stocks had a liquidity rank and 362 were in the day's 250 most traded at some point; most studies use only those 250 of each day (chosen on that day, so delisted names are included). So: a finding on the 250 most traded says nothing about the other 1,000+ stocks; widen to the top 500 for the ideas that pass.
- **survivorship and adjustments** (low): top-250 members that later stopped trading: 7021 stock-years; share by year 0.0%-100.0%; 568 ex-dates in the features table; 3 (0.53%) still jump more than 30% after adjustment; 367 liquid-stock falls over 45% with no action within 3 days; 423 frozen runs (5+ unchanged closes with volume) in liquid stocks across 217 stocks, 4876 runs flagged and skipped by the lab; recent sessions unchanged-close share max 1.5%. So: delisted names are in; a few unexplained jumps remain, and the lab skips frozen prices.
- **not on file** (medium): NSE's board-meetings calendar (results dates ahead come only from filings that name them); analyst estimates (no 'beat or miss'); GIFT Nifty and live Asian markets; bulk and block deals before 23 Oct 2026; competitor financials beyond the sector map. So: the board-meetings calendar is free and the cheapest to add; estimates are paid; GIFT Nifty has no free source.

## Company results, by period year (parsed = revenue and EPS read from the filing)

| year | filings | companies | with EPS |
|---|---|---|---|
| 2017 | 12 | 8 | 2 |
| 2018 | 7,638 | 1,606 | 2 |
| 2019 | 9,362 | 1,665 | 12 |
| 2020 | 11,268 | 1,703 | 18 |
| 2021 | 11,525 | 1,811 | 23 |
| 2022 | 11,882 | 1,904 | 7,451 |
| 2023 | 9,890 | 1,959 | 9,734 |

## The research universe, by year

| year | stocks ranked | ever in the top 250 | ever in the top 500 |
|---|---|---|---|
| 2010 | 1,336 | 372 | 716 |
| 2011 | 1,382 | 326 | 668 |
| 2012 | 1,401 | 360 | 698 |
| 2013 | 1,367 | 350 | 679 |
| 2014 | 1,372 | 364 | 682 |
| 2015 | 1,371 | 372 | 708 |
| 2016 | 1,402 | 366 | 732 |
| 2017 | 1,455 | 347 | 745 |
| 2018 | 1,471 | 327 | 701 |
| 2019 | 1,394 | 317 | 662 |
| 2020 | 1,405 | 358 | 673 |
| 2021 | 1,568 | 372 | 705 |
| 2022 | 1,731 | 367 | 728 |
| 2023 | 1,765 | 362 | 722 |

## What to widen first (in order)

1. Parse the downloaded results (XBRL) for 2018-2021 so revenue and EPS cover six years, then the old HTML pages for 2010-2017 (D20b): the base for any results or P/E study.
2. Refetch the announcement years that are under half the usual count, so studies of announcements do not have holes.
3. Fetch NSE's board-meetings calendar each evening, so results days ahead are complete.
4. Re-run the ideas that held up on the 250 most traded on the top 500, to see whether they carry to a wider market.
5. Start intraday stock studies in 2019, when coverage of the liquid names is high, or report coverage beside each result.
6. Check the liquid-stock falls of over 45% with no corporate action within 3 days: each is either a real crash or a missed split, bonus or demerger, and a missed one fakes a loss in every study that holds the stock.
