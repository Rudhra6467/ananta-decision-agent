# The data-set audit, first version (3 Nov 2026)

Madhav asked for this before any new research (flag 63): how wide and how good each data set is. Research years only (to 2023); the sealed years are counted by their own manifest and not opened. Nothing trades from it.

## What we have

| data | rows | research years | live to |
|---|---|---|---|
| gold/bars | 6,647,204 | 1994-2023 | - |
| gold/features | 3,456,514 | 1995-2023 | - |
| gold/hypothesis_map | 137 | - | - |
| gold/universe | 6,812,969 | 1995-2023 | - |
| silver/calendar | 8,378 | 1994-2026 | - |
| silver/cm_bhavcopy | 9,883,851 | 1994-2023 | 2026-11-02 |
| silver/corporate_actions | 325,752 | 1994-2026 | - |
| silver/delivery | 7,664,008 | 2003-2023 | 2026-11-02 |
| silver/flows | 39,404 | 2000-2023 | 2026-11-02 |
| silver/fo_bhavcopy | 157,536,583 | 2000-2023 | 2026-11-02 |
| silver/fo_calendar | 4,489 | - | - |
| silver/fo_greeks | 3,402,929 | 2001-2023 | 2026-11-02 |
| silver/ipo | 681 | - | - |
| silver/kite_5m | 83,656,639 | 2015-2023 | 2026-11-03 |
| silver/kite_day | 1,533,700 | 2003-2023 | 2026-10-16 |
| silver/kite_index/5minute | 1,029,458 | 2015-2023 | 2026-11-03 |
| silver/kite_index/day | 230,382 | 2003-2023 | 2026-11-03 |
| silver/kite_index/minute | 5,146,641 | 2015-2023 | 2026-11-03 |
| silver/macro | 85,028 | 1990-2026 | - |
| silver/pr | 8,746,016 | 2010-2023 | 2026-11-02 |
| silver/reference | 756 | - | - |
| silver/security_master | 14,878 | - | - |
| silver/valuation | 17,486 | 1999-2023 | 2026-11-02 |

## What the audit found

- **company results** (high): results with revenue and EPS are parsed for 2018, 2019, 2020, 2021, 2022, 2023; the results index lists filings from 2007, but before 2018 they are HTML pages with no XBRL, which are not parsed (D20b). So: a per-stock P/E or results study can use 2018-2023 today; the 2010-2017 years still need the HTML pages.
- **company announcements (old PR files)** (medium): the old PR-zip files thin out: 2022: 22,367 lines, while the timestamped source is complete (2022: 120,937); V02 and HFN1 read the PR files. So: new announcement studies use the timestamped source; V02's and HFN1's 2021-2022 years carry the hole, and re-running them on the timestamped source would be a new registration (Madhav's decision), not a change to the frozen ones.
- **intraday stock bars (5-minute)** (medium): coverage of the day's 250 most traded rises from 56% in 2015 to 89% in 2023; lowest 2015. So: intraday stock studies before about 2019 see only part of the liquid market; say so or start them in 2019.
- **the research universe** (medium): in 2023, 1,765 stocks had a liquidity rank, 362 were in the day's 250 most traded and 722 in the 500 most traded at some point (chosen each day, so delisted names are included). The studies that held up use: OC1 the 100 most traded (india/ocstudy.py); IB1 Nifty, Bank Nifty and the 50 most traded (india/lab4.py); GP1 the 250 most traded (india/gaplab.py); V01 the 500 most traded (india/vstudies.py); E04, P01, CL1 the lab features table, the 500 most traded (india/lab.py); T-TWT H10/H12/H18 the teachers' stock panel, the 500 most traded (india/teachers_stock.py); DR1 index options only. So: a finding says nothing about stocks outside its own universe; the narrow ones (OC1, IB1, GP1) are the ones to re-test on the next band of stocks, registered before the run (registrations/w500_v1_draft.md).
- **survivorship and adjustments** (low): top-250 members that later stopped trading: 7021 stock-years; share by year 0.0%-100.0%; 568 ex-dates in the features table; 3 (0.53%) still jump more than 30% after adjustment; 367 liquid-stock falls over 45% with no action within 3 days; 423 frozen runs (5+ unchanged closes with volume) in liquid stocks across 217 stocks, 4876 runs flagged and skipped by the lab; recent sessions unchanged-close share max 1.5%. So: delisted names are in; a few unexplained jumps remain, and the lab skips frozen prices.
- **not on file** (medium): analyst estimates (no 'beat or miss'); GIFT Nifty and live Asian markets; bulk and block deals before 23 Oct 2026; competitor financials beyond the sector map. So: estimates are paid; GIFT Nifty has no free source.

## Company results, by period year (parsed = revenue and EPS read from the filing)

| year | filings | companies | with EPS |
|---|---|---|---|
| 2017 | 12 | 8 | 12 |
| 2018 | 7,638 | 1,606 | 7,537 |
| 2019 | 9,362 | 1,665 | 9,164 |
| 2020 | 11,268 | 1,703 | 11,060 |
| 2021 | 11,525 | 1,811 | 11,367 |
| 2022 | 11,882 | 1,904 | 11,706 |
| 2023 | 9,890 | 1,959 | 9,736 |

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

1. Done 3 Nov 2026 for 2018-2023 (the XBRL files). Left: the old HTML result pages for 2010-2017 (D20b).
2. Done 3 Nov 2026: the timestamped announcements are complete for 2010-2023 (the 2022 hole is in the old PR files only, and the 2010-2012 rows lost to a de-duplication bug are back). Left: V02 and HFN1 on the timestamped source, as new registrations, if Madhav wants.
3. Done 3 Nov 2026: NSE's board-meetings calendar is fetched every night (60 days ahead) with history from 2010 (115,461 meetings to 2023).
4. Mapped 3 Nov 2026: most studies that held up already use the 500 most traded; the narrow ones are OC1 (100), IB1 (50) and GP1 (250). Left: re-test those three on the next band of stocks, registered before the run (registrations/w500_v1_draft.md), on Madhav's yes.
5. Done 3 Nov 2026: each intraday stock study's write-up now carries the 5-minute coverage of its own universe by year (registrations/intraday_coverage.md). Left: whether new intraday stock studies start in 2019 is Madhav's choice.
6. Checked 3 Nov 2026 (registrations/big_falls_v1.md): of 369 unexplained falls, 126 look like a split, bonus or demerger left out of the adjustment (49 since 2010); 243 show no action nearby and need a look. Left: add the confirmed ones to the corporate-actions table (it changes past prices, so Madhav's decision).
