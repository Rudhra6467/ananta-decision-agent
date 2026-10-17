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
| Kite intraday depth | Not yet measured: needs Madhav's first sign-in; `python -m india.probe kite` writes manifests/probe_kite_<date>.json |

The three bronze backfills (cash 1994 to now, delivery 2003 to now, F&O 2000 to now) started the same morning at one request a second each.

## 3. The universe rule (U_LIQ-IN)

On each trading day the research universe is the top N names by 60-trading-day median rupee turnover among series-EQ stocks that have traded for at least 126 trading days and whose unadjusted close is above ₹10, with N = 50, 100 or 500 by phase. Membership is a half-open interval table in the catalog, recomputed only from bronze, so no point-in-time index list is needed and no survivorship enters: delisted names are in every day's bhavcopy until their last day.

## 4. Adjustments: two records

Record A is derived from the files themselves: on an ex-date NSE sets the day's previous-close column to the adjusted value, so the factor is prior close divided by the day's previous close, kept when it differs from 1 by more than 0.5%. Record B is NSE's corporate-action file. Adjusted prices are a view over unadjusted rows and factors; a disagreement between the records is a row in the quality table, never a silent choice.

## 5. The I-1 quality gate (daily spine)

- 300 random (symbol, day) pairs from 2000 onward compared with Kite daily candles: at least 297 closes within 0.5%.
- Every weekday from 1994-11-03 to now has a manifest line: a file or a recorded no-file (holiday); the holiday calendar is derived from those gaps and cross-checked with NSE's published list for 2015 onward.
- Record A and Record B agree on at least 95% of ex-dates where both exist for 2010 onward; every disagreement listed.
- 30 consecutive nightly runs with zero quality failures before the database gate.
- Holdout rows (2024-01-01 onward) live under sealed/ and the research loader refuses them without a logged unseal token; a test greps for direct reads.

## 6. What this approval unlocks and what it does not

Unlocks: the bronze backfills; Kite 5-minute and daily backfills for the Nifty 50, then 100, then 500 lists as labels; the read-only ledger sync; the catalog; the hypothesis map; the nightly job and the R2 copy.

Does not unlock: any research run before the I-1 gate; any look at 2024 onward outside the sealed loader; any order of any kind; any purchase; any India row in any agent.
