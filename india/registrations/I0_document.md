# Ananta India I0: pre-registration (approved)

17 Oct 2026 · approved by Madhav in chat the same morning: "I approve India I0", "Scope Nifty 50, then 100, then 500 with the turnover rule", and "Canada is parked"; with the account statement "We will be using my account for the test phase and we will only move with NRO account once we are going to live."

Plan this registration implements: *Ananta — India First: Data Platform and Agent Plan* (16 Oct 2026), sections 4, 8 and 9.

## 1. Decisions recorded as binding

| # | Decision | Recorded as |
| --- | --- | --- |
| 1 | Order of markets | India first; Canada parked, not cancelled (C0 and the eight data decisions of 16 Oct stay approved; the Norgate trial is not started) |
| 2 | Scope | NSE only. Series EQ only (no BE, BZ, SM, ST, trade-for-trade or SME boards). Labels from the Nifty 50, 100 and 500 lists; the research universe comes from the turnover rule in section 3, never from a list |
| 3 | History | Daily 1994-11-03 to now. Development 2000-01-01 to 2017-12-31, validation 2018-01-01 to 2023-12-31, holdout 2024-01-01 onward sealed. Rows before 2000 are kept for context and calendars, never for a test |
| 4 | Data sources | Free NSE files (cash bhavcopy, F&O bhavcopy, delivery, index lists and levels, VIX, flows, corporate actions). Kite Connect for intraday candles, the instruments master and the ledger. No other vendor without Madhav's approval |
| 5 | Account | Madhav's existing Zerodha account, read-only, for every phase up to and including paper. A move to an NRO account happens before the live phase, not before |
| 6 | Budget | Kite Connect ₹500 a month; Cloudflare R2 for the off-site copy (about US$1 a month); one AI mapping pass of about US$15. Nothing else recurring without approval |
| 7 | Firewall | India shares code, schema and the knowledge library with crypto and Canada, never rows, parameters or findings. The India folder is ~/ananta_data/india, refused inside any crypto or Canada folder (india/paths.py). India never wakes the crypto agent |
| 8 | Agent | No India row reaches any agent until the database gate (plan section 8, seven persisted-data criteria) and Madhav's sentence. Every India run before that is research at L0 |
| 9 | Orders | Nothing in the India code can place, modify or cancel an order: the Kite client sends GET only, and a test fails if a write verb appears (tests/test_india.py) |

## 2. What the I-0 probe found (17 Oct 2026, 10:06 Toronto)

| Check | Result |
| --- | --- |
| NSE archive reachability | 23 requests at one a second, zero refusals, about 2,500 files an hour at this rate |
| First cash bhavcopy | 1994-11-03 (NSE's first trading day), 135 rows |
| Format change | Old `cm*bhav.csv.zip` through 2024-07-05; UDiFF `BhavCopy_NSE_CM_*` from 2024-07-08, both parse; the previous-close column exists in both (PREVCLOSE, PrvsClsgPric) |
| First F&O bhavcopy | 2001-07-02 reachable (index futures began June 2000; the backfill starts 2000-06-12); 37,866 rows on 2026-10-15 |
| Delivery files | MTO format at least from 2016-01-04; sec_bhavdata_full (with OHLC and delivery %) from 2020 or earlier; the backfill from 2003 finds the first day |
| Index lists | Nifty 50 (50), Nifty 100 (100), Nifty 500 (501 rows) downloaded to bronze/indices |
| Kite intraday depth (11:52 Toronto, after Madhav's first sign-in) | 5-minute candles from 2015-02-02 for 45 of the Nifty 50; the other five start at listing (INDIGO 2016, BSE 2017, MAXHEALTH 2021, ETERNAL 2022, JIOFIN 2024). Daily candles from 2003-01-01 for most names, so Kite is the second record for spot checks from 2003 on; 2000 to 2002 rests on the bhavcopy alone. One oddity to watch: HDFCLIFE answers 5-minute bars from 2015 but daily only from its 2017 listing (a token quirk the quality gate will catch). 599 requests, no refusals |

The three bronze backfills (cash 1994 to now, delivery 2003 to now, F&O 2000 to now) started the same morning at one request a second each.

## 3. The universe rule (U_LIQ-IN)

On each trading day the research universe is the top N names by 60-trading-day median rupee turnover among series-EQ stocks that have traded for at least 126 trading days and whose unadjusted close is above ₹10, with N = 50, 100 or 500 by phase. Membership is a half-open interval table in the catalog, recomputed only from bronze, so no point-in-time index list is needed and no survivorship enters: delisted names are in every day's bhavcopy until their last day.

## 4. Adjustments: two records

Record A is derived from the prices themselves (the ex-date gap and the five-day gap, both snapped to a clean ratio). Record B is NSE's corporate-actions feed. Adjusted prices are a table over unadjusted rows and the agreed factors; a disagreement between the records is a row in the quality table, never a silent choice. (As written on 17 Oct morning this section assumed NSE adjusts its previous-close column on ex-dates; section 4a records that it does not.)

## 4a. What the first silver build found (17 Oct 2026, afternoon)

- NSE does not adjust the previous-close column on an ex-date (INFY 2015-06-15: previous close 1975.05, open 976.95), so Record A is the price gap, not that column. Record B is NSE's corporate-actions API, one call per year for every symbol, 42,819 rows 2000 to 2026 (659 bonuses, 699 splits, 30 combined on one date, 1 consolidation). Where both records exist for 2010 to 2023 they agree on 685 of 691 ex-dates (99.1%); the 6 disagreements and the 237 gaps with no announcement are the review list. Before 2010 Record B is thin (2005 lists one bonus), so pre-2010 factors rest on Record A until a third source is added.
- Kite's historical candles, daily and 5-minute alike, come back adjusted for splits, bonuses, dividends and demergers (COALINDIA 2022-12-20: NSE close 226.10, Kite 210.65; RELIANCE 2009 carries the 2023 Jio Financial demerger). They are therefore not a raw second record. They become Record C, a total-return adjustment series, and the intraday bars are rescaled to raw prices day by day with the NSE close over Kite's own daily close before any research reads them.
- The raw second record for the spot checks is therefore NSE's security-wise delivery report (same exchange, separate report, carries OHLC from 2020) as the parse check, and the BSE bhavcopy (a different exchange) as the independent check at 1% for cross-listed names; both are I-2 items.

## 5. The I-1 quality gate (daily spine)

- 300 random (symbol, day) pairs from 2020 onward compared with the NSE delivery report's close: at least 297 within 0.5%; and 300 pairs from 2003 onward compared with the BSE close for cross-listed names: at least 285 within 1%.
- Every weekday from 1994-11-03 to now has a manifest line: a file or a recorded no-file (holiday); the holiday calendar is derived from those gaps and cross-checked with NSE's published list for 2015 onward.
- Record A and Record B agree on at least 95% of ex-dates where both exist for 2010 onward; every disagreement listed.
- 30 consecutive nightly runs with zero quality failures before the database gate.
- Holdout rows (2024-01-01 onward) live under sealed/ and the research loader refuses them without a logged unseal token; a test greps for direct reads.

## 6. What this approval unlocks and what it does not

Unlocks: the bronze backfills; Kite 5-minute and daily backfills for the Nifty 50, then 100, then 500 lists as labels; the read-only ledger sync; the catalog; the hypothesis map; the nightly job and the R2 copy.

Does not unlock: any research run before the I-1 gate; any look at 2024 onward outside the sealed loader; any order of any kind; any purchase; any India row in any agent.

## 7. Results recorded 18 Oct 2026 (I-1, Sunday run)
- BSE independent check (section 5): 300 stock-day pairs, 63 sampled dates 2011-2023, up to eight liquid names per date (top 100 NSE turnover), NSE close against BSE close for the same ISIN: 299 of 300 within 1% (gate 285); the one miss is ELGIEQUIP 15 Feb 2018 at 1.06%. Coverage starts in 2011, not 2003: NSE's bhavcopy has no ISIN column before mid-2011 (0% of rows 1994-2010, 54% in 2011, 100% from 2012), so earlier years cannot be paired by ISIN and rest on the delivery report and Kite checks. BSE files: EQ_ISINCODE_ddmmyy.zip (2017 on) and EQddmmyy_CSV.ZIP (2008 on) reachable with browser headers at 1 req/s. Report: manifests/probe_bse_check_20261018.json.
- Security master: 4,144 ISINs, 3,613 company entities (496 entities span more than one ISIN, linked when the same symbol continues within 10 days), 430 ISINs renamed, 547 symbols reused by a different ISIN. Kite carries no ISIN, so Kite symbols link through the symbol in the latest cash rows: 494 of the 495 intraday symbols link.
- Intraday rescale joined on company entity instead of symbol: unscaled 5-minute rows 7,478,345 of 84,011,923 (8.90%) before; 1,297,579 (1.54%) after. An ISIN-only join was tried first and was worse (12.1%) because ISINs change at face-value changes; the entity link fixed it. What remains is mostly names with no matching NSE EQ close (MTARTECH, CUPID, SHRIPISTON).
- Nightly job india.nightly (launchd com.ananta.india.nightly, 02:30 Toronto) ran once by hand and wrote its heartbeat; R2 bucket ananta-india-lake holds silver, sealed silver and manifests (85 objects, 2.6 GB on the first sync), uploads only.

## 8. Added 18 Oct 2026 (afternoon): ledger snapshots and the option recorder
- `india.ledger snapshot`: holdings, positions, funds, orders, trades to bronze/ledger/<IST date>.json, mode 600, never synced to R2; heartbeat carries counts only. First snapshot 18 Oct: 14 holdings, 0 open positions.
- `india.recorder run`: 1-minute candles for live NIFTY (±20 strikes) and BANKNIFTY (±15 strikes) options on the two nearest expiries, the two nearest futures, and the NIFTY 50, NIFTY BANK, FIN SERVICE, MIDCAP SELECT and INDIA VIX indices; 30 days back on every run, so each contract's whole life is captured. First run 18 Oct: 296 contracts, 1,852,526 candles, 300 calls, 191 s. Bronze: bronze/kite_1m_fo/<expiry>/<symbol>.jsonl.gz.
- Both run from launchd `com.ananta.india.evening` at 19:00 Toronto (04:30 or 05:30 IST next day, before the 06:00 IST token expiry), so a Kite sign-in at any time during the Toronto day serves that evening's run. Kite reported the account holder on sign-in as the pinned user (Zerodha ID kept in ~/ananta_private).
- Decided with Madhav for O-04: "clearly moves" = a level break (levels to be defined from the backtest, which is itself the study: where are the best exits); stop = exit both legs when the combined premium falls to 50-60% of what was paid (a 40-50% loss on premium); the trail on the winner is a fixed, pre-declared plan, not discretion. Exit research is the priority across all families: Ananta should get smarter at exits (ride, expect the turn, leave) before entries.

## 9. Fundamentals probe, 18 Oct 2026 (answers gate G-U in principle)
NSE's corporate financial-results endpoint (nseindia.com/api/corporates-financial-results) returns, per filing: symbol, ISIN, period, consolidated or standalone, audited flag, broadcast timestamp to the second (the point-in-time date), and a link to the XBRL file. Queried over a date window without a symbol it lists every company's filings in that window, which makes both a bulk history pull and a daily incremental possible. XBRL (standard tags: revenue from operations, profit or loss for the period, EPS, assets, equity) is attached to every result from about Aug 2020 and to about 58% in Aug 2018; filings before 2018 are 'Old' format with an HTML result page and no XBRL. A per-symbol query returned only up to Dec 2024 for RELIANCE (stale cache), so the window query is the one to use. Not yet done: licence terms read, coverage report, parser. BSE's equivalent not yet probed.
