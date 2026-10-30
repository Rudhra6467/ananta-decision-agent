# Every study in the ledger, in plain words (generated from the ledger by india.writeups, 2026-10-30)

HISTORICAL BACKTEST only: development 2000-2017, validation 2018-2023; the 2024+ years are sealed. A verdict here is the registry's rule applied to the registered numbers (one family-wide bar for every variant ever tried in that family); it is evidence, not a decision, and nothing is in the paper book because of this page. A researcher's write-up (the *_results_v1.md pages) is the better source where one exists; this page exists so that no finished study is unwritten.

## OC (3 studies)

### OC1: Opening Decision Protocol V1 (Madhav): primary tests
Claim before the run: confirmed opening-range breaks (breadth 60%, index agreement, rvol 1.5x and VWAP for stocks) by 10:15 make money net of costs, and beat the same entries and exits without the filters; standing down on scheduled event days beats trading through
Outcome: 50 did not hold, 13 came out the opposite way, 8 held up in both periods, 3 had too little data to judge across 74 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| STOCKS · k30 · E2 · X2 · vs_base | VALIDATED | +13.35 | +15.8 | +14.03 | +19.9 | 3.392 |
| STOCKS · k15 · E2 · X2 · base_net | OPPOSITE | -13.42 | -13.8 | -14.71 | -19.8 | 3.337 |
| STOCKS · k30 · E2 · X2 · base_net | OPPOSITE | -14.63 | -15.4 | -15.28 | -19.5 | 3.388 |
| STOCKS · k15 · E2 · X2 · vs_base | VALIDATED | +11.78 | +13.8 | +12.89 | +18.8 | 3.341 |
| STOCKS · k15 · E2 · X1 · base_net | OPPOSITE | -12.73 | -10.7 | -14.71 | -16.6 | 3.322 |
| STOCKS · k15 · E2 · X1 · vs_base | VALIDATED | +11.17 | +10.6 | +12.95 | +16.2 | 3.327 |
| STOCKS · k30 · E2 · X1 · vs_base | VALIDATED | +13.30 | +12.4 | +13.18 | +15.3 | 3.38 |
| STOCKS · k30 · E2 · X1 · base_net | OPPOSITE | -14.49 | -12.1 | -14.36 | -15.0 | 3.376 |
| STOCKS · k15 · E1 · X2 · vs_base | VALIDATED | +8.77 | +8.6 | +10.69 | +12.5 | 3.312 |
| STOCKS · k15 · E1 · X1 · vs_base | VALIDATED | +9.60 | +7.9 | +11.43 | +11.3 | 3.296 |
| STOCKS · k30 · E1 · X2 · vs_base | VALIDATED | +9.11 | +7.8 | +10.78 | +11.1 | 3.368 |
| STOCKS · k15 · E1 · X2 · base_net | OPPOSITE | -9.46 | -7.0 | -12.18 | -10.9 | 3.307 |

### SP1: Scenario Playbook phase 1: index intraday playbook (sp1_v2.json)
Claim before the run: a policy that reads the situation chooses intraday index actions that earn net of costs, and beats the same policy without the situation
Outcome: 5 not supported on seen years, 1 had too little data to judge, 1 supported on seen years (not confirmation) across 7 variants.

### SP1H: SP1 holdout: the one confirmatory run of the frozen index playbook (sp1_v2.json tests.holdout)
Claim before the run: the frozen SP1 policy, refitted each year on all earlier years, earns net of costs on 2024-01-01..2026-10-16
Outcome: 5 not confirmed on the sealed years across 5 variants.

## SP3 (1 studies)

### SP3: SP3 positional playbook: situation-dependent entry, exit and holding time (sp3-v1-2026-10-20-frozen): the INDEX rows
Claim before the run: the situation-aware NIFTY and BANKNIFTY near-month futures shadow books earn more per day than zero and than the same policy without situation features
Outcome: 14 not supported on seen years across 14 variants.

## SZ (1 studies)

### SZ2: Sizing v2: fraction x structure for SP1's option line (sz2-v1-2026-10-19-frozen), at Rs 60,000
Claim before the run: exploratory: each variant's daily log growth on the historical paused path (2017-2023 dev, 2024-01-01..2026-10-16 seen); the selection is counted, never confirmed
Outcome: 20 had too little data to judge across 20 variants.

## combination (1 studies)

### CL1: The combination lab: does a stock setup together with a market state earn more over 20 sessions than the better of the two alone? Five stock setups x five market states on the random (ANY) entries, 2000-2023
Claim before the run: For each pair, trades signalled while BOTH the stock setup and the market state are on earn more over the next 20 sessions (net) than trades signalled while the better of the two is on by itself (the interaction), within quarters, in both periods. A random stock flag with the same frequency paired with the same market state earns nothing in particular.
Outcome: 24 had too little data to judge, 3 did not hold, 3 held up in both periods across 30 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| deliv_high · small_lead | VALIDATED | +0.95% | +3.3 | +1.92% | +4.1 | 3.144 |
| not_extended · nifty_gt200d | VALIDATED | +1.54% | +4.6 | +1.81% | +3.4 | 3.144 |
| not_extended · small_lead | VALIDATED | +1.29% | +3.4 | +2.05% | +3.2 | 3.144 |

## context (21 studies)

### C01-ANY: Market state after shock days and in high-volatility regimes (crypto C-series port) (ANY entries)
Claim before the run: Trades signalled while the condition is on earn a different net return than trades signalled while it is off (direction as stated per condition), within quarters, in dev and validation.
Outcome: 15 had too little data to judge across 15 variants.

### C01-BRK: Market state after shock days and in high-volatility regimes (crypto C-series port) (BRK entries)
Claim before the run: Trades signalled while the condition is on earn a different net return than trades signalled while it is off (direction as stated per condition), within quarters, in dev and validation.
Outcome: 15 had too little data to judge across 15 variants.

### C01-PULL: Market state after shock days and in high-volatility regimes (crypto C-series port) (PULL entries)
Claim before the run: Trades signalled while the condition is on earn a different net return than trades signalled while it is off (direction as stated per condition), within quarters, in dev and validation.
Outcome: 15 had too little data to judge across 15 variants.

### C02-ANY: Volume heat, delivery share and own volatility at entry (crypto H1/H2 port, M-10) (ANY entries)
Claim before the run: Trades signalled while the condition is on earn a different net return than trades signalled while it is off (direction as stated per condition), within quarters, in dev and validation.
Outcome: 12 did not hold, 3 had too little data to judge across 15 variants.

### C02-BRK: Volume heat, delivery share and own volatility at entry (crypto H1/H2 port, M-10) (BRK entries)
Claim before the run: Trades signalled while the condition is on earn a different net return than trades signalled while it is off (direction as stated per condition), within quarters, in dev and validation.
Outcome: 8 did not hold, 7 had too little data to judge across 15 variants.

### C02-PULL: Volume heat, delivery share and own volatility at entry (crypto H1/H2 port, M-10) (PULL entries)
Claim before the run: Trades signalled while the condition is on earn a different net return than trades signalled while it is off (direction as stated per condition), within quarters, in dev and validation.
Outcome: 8 had too little data to judge, 7 did not hold across 15 variants.

### C03-ANY: Bank Nifty leading the broad market (TWT-H46) (ANY entries)
Claim before the run: Trades signalled while the condition is on earn a different net return than trades signalled while it is off (direction as stated per condition), within quarters, in dev and validation.
Outcome: 5 had too little data to judge, 5 did not hold across 10 variants.

### C03-BRK: Bank Nifty leading the broad market (TWT-H46) (BRK entries)
Claim before the run: Trades signalled while the condition is on earn a different net return than trades signalled while it is off (direction as stated per condition), within quarters, in dev and validation.
Outcome: 5 had too little data to judge, 5 did not hold across 10 variants.

### C03-PULL: Bank Nifty leading the broad market (TWT-H46) (PULL entries)
Claim before the run: Trades signalled while the condition is on earn a different net return than trades signalled while it is off (direction as stated per condition), within quarters, in dev and validation.
Outcome: 10 had too little data to judge across 10 variants.

### C05-ANY: India VIX regimes at entry (ANY entries)
Claim before the run: Trades signalled while the condition is on earn a different net return than trades signalled while it is off (direction as stated per condition), within quarters, in dev and validation.
Outcome: 8 had too little data to judge, 2 did not hold across 10 variants.

### C05-BRK: India VIX regimes at entry (BRK entries)
Claim before the run: Trades signalled while the condition is on earn a different net return than trades signalled while it is off (direction as stated per condition), within quarters, in dev and validation.
Outcome: 5 had too little data to judge, 5 did not hold across 10 variants.

### C05-PULL: India VIX regimes at entry (PULL entries)
Claim before the run: Trades signalled while the condition is on earn a different net return than trades signalled while it is off (direction as stated per condition), within quarters, in dev and validation.
Outcome: 9 had too little data to judge, 1 held up, weaker in one period across 10 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| vix_rising · hold_20d | CONDITIONAL | +3.82% | +4.0 | +1.53% | +1.7 | 3.656 |

### C07-ANY: Small caps leading large caps at entry (TWT-H13/14) (ANY entries)
Claim before the run: Trades signalled while the condition is on earn a different net return than trades signalled while it is off (direction as stated per condition), within quarters, in dev and validation.
Outcome: 5 came out the opposite way across 5 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| small_lead · hold_20d | OPPOSITE | -3.91% | -4.3 | -3.30% | -4.1 | 3.656 |
| small_lead · swing_low_20 | OPPOSITE | -5.74% | -4.3 | -3.88% | -3.6 | 3.656 |
| small_lead · atr_trail_4 | OPPOSITE | -4.72% | -4.8 | -3.80% | -3.5 | 3.656 |
| small_lead · sma_close_50 | OPPOSITE | -5.88% | -4.1 | -3.97% | -3.1 | 3.656 |
| small_lead · hold_60d | OPPOSITE | -6.01% | -4.2 | -4.06% | -3.0 | 3.656 |

### C07-BRK: Small caps leading large caps at entry (TWT-H13/14) (BRK entries)
Claim before the run: Trades signalled while the condition is on earn a different net return than trades signalled while it is off (direction as stated per condition), within quarters, in dev and validation.
Outcome: 5 came out the opposite way across 5 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| small_lead · swing_low_20 | OPPOSITE | -2.81% | -3.6 | -3.01% | -3.2 | 3.656 |
| small_lead · sma_close_50 | OPPOSITE | -3.14% | -3.7 | -3.15% | -3.0 | 3.656 |
| small_lead · atr_trail_4 | OPPOSITE | -2.48% | -4.2 | -2.03% | -2.9 | 3.656 |
| small_lead · hold_20d | OPPOSITE | -2.95% | -4.4 | -2.33% | -2.7 | 3.656 |
| small_lead · hold_60d | OPPOSITE | -3.26% | -3.6 | -3.11% | -2.6 | 3.656 |

### C07-PULL: Small caps leading large caps at entry (TWT-H13/14) (PULL entries)
Claim before the run: Trades signalled while the condition is on earn a different net return than trades signalled while it is off (direction as stated per condition), within quarters, in dev and validation.
Outcome: 5 had too little data to judge across 5 variants.

### C08-ANY: Breadth washouts and thrusts at entry (TWT-H01, H30-33) (ANY entries)
Claim before the run: Trades signalled while the condition is on earn a different net return than trades signalled while it is off (direction as stated per condition), within quarters, in dev and validation.
Outcome: 15 had too little data to judge across 15 variants.

### C08-BRK: Breadth washouts and thrusts at entry (TWT-H01, H30-33) (BRK entries)
Claim before the run: Trades signalled while the condition is on earn a different net return than trades signalled while it is off (direction as stated per condition), within quarters, in dev and validation.
Outcome: 15 had too little data to judge across 15 variants.

### C08-PULL: Breadth washouts and thrusts at entry (TWT-H01, H30-33) (PULL entries)
Claim before the run: Trades signalled while the condition is on earn a different net return than trades signalled while it is off (direction as stated per condition), within quarters, in dev and validation.
Outcome: 15 had too little data to judge across 15 variants.

### C09-ANY: Intermarket at entry: rupee, crude, Nasdaq, US 10-year (TWT-H42-47); Nifty valuation (D30) not yet available (ANY entries)
Claim before the run: Trades signalled while the condition is on earn a different net return than trades signalled while it is off (direction as stated per condition), within quarters, in dev and validation.
Outcome: 10 had too little data to judge, 6 did not hold, 4 came out the opposite way across 20 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| usdinr_rising · atr_trail_4 | OPPOSITE | +2.43% | +2.5 | +2.54% | +3.5 | 3.656 |
| usdinr_rising · sma_close_50 | OPPOSITE | +3.62% | +2.6 | +3.07% | +3.5 | 3.656 |
| usdinr_rising · hold_60d | OPPOSITE | +3.64% | +2.7 | +3.12% | +3.5 | 3.656 |
| usdinr_rising · swing_low_20 | OPPOSITE | +3.51% | +2.6 | +2.80% | +3.3 | 3.656 |

### C09-BRK: Intermarket at entry: rupee, crude, Nasdaq, US 10-year (TWT-H42-47); Nifty valuation (D30) not yet available (BRK entries)
Claim before the run: Trades signalled while the condition is on earn a different net return than trades signalled while it is off (direction as stated per condition), within quarters, in dev and validation.
Outcome: 10 did not hold, 10 had too little data to judge across 20 variants.

### C09-PULL: Intermarket at entry: rupee, crude, Nasdaq, US 10-year (TWT-H42-47); Nifty valuation (D30) not yet available (PULL entries)
Claim before the run: Trades signalled while the condition is on earn a different net return than trades signalled while it is off (direction as stated per condition), within quarters, in dev and validation.
Outcome: 10 did not hold, 10 had too little data to judge across 20 variants.

## context_events (3 studies)

### CEV-ANY: Rare market states as declustered events (ANY entries)
Claim before the run: Entries signalled on the first day of a market state earn a different net return than entries signalled 21-40 sessions before it.
Outcome: 30 had too little data to judge across 30 variants.

### CEV-BRK: Rare market states as declustered events (BRK entries)
Claim before the run: Entries signalled on the first day of a market state earn a different net return than entries signalled 21-40 sessions before it.
Outcome: 30 had too little data to judge across 30 variants.

### CEV-PULL: Rare market states as declustered events (PULL entries)
Claim before the run: Entries signalled on the first day of a market state earn a different net return than entries signalled 21-40 sessions before it.
Outcome: 30 had too little data to judge across 30 variants.

## events (4 studies)

### CA1: Corporate actions: do stocks do better after a bonus or split, a buyback, or a large dividend, from the ex-date on?
Claim before the run: Bonus issues and splits signal management confidence and widen ownership; buybacks signal the shares are cheap; a large dividend signals strong cash flow: each is followed by better 20-60 session returns than ordinary days.
Outcome: 2 came out the opposite way, 2 had too little data to judge, 1 did not hold across 5 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| STK · bonus_split · fwd20 | OPPOSITE | -3.76% | -3.9 | -6.00% | -6.2 | 3.134 |
| STK · bonus_split · fwd60 | OPPOSITE | -4.09% | -3.1 | -3.26% | -2.1 | 3.134 |

### V01: Quarterly results: reaction day, 20-day drift, and the cost of holding through results
Claim before the run: (a) the 20-day abnormal drift continues the day-0 reaction; (b) results days move more than normal days (holding through results adds risk)
Outcome: 2 did not hold, 1 held up in both periods, 1 had too little data to judge across 4 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| abs_reaction_excess | VALIDATED | +0.48% | +6.4 | +1.10% | +7.9 | 2.498 |

### V02: Announcement categories and price-band hits: 20-session drift after the day (top-500 stocks)
Claim before the run: After an announcement of a given category (or a price-band hit), the stock's 20-session return beyond Nifty differs from zero in the stated direction.
Outcome: 11 did not hold, 3 had too little data to judge, 1 held up, weaker in one period across 15 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| band_hit_low | CONDITIONAL | -7.54% | -6.3 | -3.12% | -2.7 | 3.078 |

### V03: IPOs: allotment gain, buying on day one, strong versus weak listings
Claim before the run: Allottees gain on listing day; buying at the day-1 close lags Nifty over 20 and 60 sessions; strong and weak listings differ afterwards.
Outcome: 5 had too little data to judge across 5 variants.

## exit (12 studies)

### E02-ANY: Exit bake-off on ANY entries
Claim before the run: An exit policy earns more than the time-matched null (same entry, same stop, held as long, no exit rule), net of Indian costs, in both the dev and validation years.
Outcome: 10 did not hold, 8 came out the opposite way across 18 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| target_1R | OPPOSITE | -0.07% | -1.9 | -0.18% | -5.4 | 3.434 |
| atr_trail_4 | OPPOSITE | -0.58% | -8.3 | -0.13% | -4.0 | 3.434 |
| scale_half_then_trail3 | OPPOSITE | -0.57% | -9.6 | -0.16% | -3.8 | 3.434 |
| atr_trail_3 | OPPOSITE | -0.59% | -9.7 | -0.16% | -3.6 | 3.434 |
| atr_trail_2 | OPPOSITE | -0.55% | -9.4 | -0.17% | -3.4 | 3.434 |
| swing_low_10 | OPPOSITE | -0.02% | -2.9 | -0.01% | -1.0 | 3.434 |
| swing_low_20 | OPPOSITE | -0.05% | -3.6 | -0.01% | -0.6 | 3.434 |
| sma_close_50 | OPPOSITE | -0.04% | -3.2 | -0.01% | -0.4 | 3.434 |

### E02-BRK: Exit bake-off on BRK entries
Claim before the run: An exit policy earns more than the time-matched null (same entry, same stop, held as long, no exit rule), net of Indian costs, in both the dev and validation years.
Outcome: 11 did not hold, 7 came out the opposite way across 18 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| scale_half_then_trail3 | OPPOSITE | -0.34% | -5.3 | -0.14% | -3.4 | 3.434 |
| sma_close_50 | OPPOSITE | -0.07% | -2.6 | -0.05% | -3.0 | 3.434 |
| atr_trail_3 | OPPOSITE | -0.43% | -6.2 | -0.13% | -2.9 | 3.434 |
| atr_trail_2 | OPPOSITE | -0.36% | -5.0 | -0.14% | -2.4 | 3.434 |
| swing_low_20 | OPPOSITE | -0.07% | -2.6 | -0.04% | -2.4 | 3.434 |
| atr_trail_4 | OPPOSITE | -0.43% | -5.8 | -0.10% | -2.4 | 3.434 |
| swing_low_10 | OPPOSITE | -0.02% | -1.7 | -0.02% | -2.4 | 3.434 |

### E02-PULL: Exit bake-off on PULL entries
Claim before the run: An exit policy earns more than the time-matched null (same entry, same stop, held as long, no exit rule), net of Indian costs, in both the dev and validation years.
Outcome: 11 did not hold, 4 came out the opposite way, 3 had too little data to judge across 18 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| atr_trail_2 | OPPOSITE | -0.68% | -7.4 | -0.27% | -4.1 | 3.434 |
| scale_half_then_trail3 | OPPOSITE | -0.72% | -8.3 | -0.18% | -3.0 | 3.434 |
| atr_trail_3 | OPPOSITE | -0.68% | -7.4 | -0.15% | -2.3 | 3.434 |
| atr_trail_4 | OPPOSITE | -0.68% | -7.0 | -0.11% | -1.5 | 3.434 |

### E03-ANY: Extra exit signals on ANY entries (E03)
Claim before the run: Adding this signal as an extra exit to a loose 4-ATR trail (or a 60-day hold) raises net return per trade, paired by trade, in both dev and validation.
Outcome: 6 did not hold across 6 variants.

### E03-BRK: Extra exit signals on BRK entries (E03)
Claim before the run: Adding this signal as an extra exit to a loose 4-ATR trail (or a 60-day hold) raises net return per trade, paired by trade, in both dev and validation.
Outcome: 6 did not hold across 6 variants.

### E03-PULL: Extra exit signals on PULL entries (E03)
Claim before the run: Adding this signal as an extra exit to a loose 4-ATR trail (or a 60-day hold) raises net return per trade, paired by trade, in both dev and validation.
Outcome: 3 did not hold, 3 came out the opposite way across 6 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| trail4+giveback50 | OPPOSITE | -0.97% | -2.3 | -1.70% | -2.5 | 3.434 |
| trail4+three_down | OPPOSITE | -1.20% | -2.3 | -2.16% | -2.1 | 3.434 |
| trail4+range_down | OPPOSITE | -0.35% | -2.1 | -0.52% | -1.5 | 3.434 |

### E07-ANY: Extra exit signals on ANY entries (E07)
Claim before the run: Adding this signal as an extra exit to a loose 4-ATR trail (or a 60-day hold) raises net return per trade, paired by trade, in both dev and validation.
Outcome: 2 came out the opposite way, 1 had too little data to judge, 1 did not hold across 4 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| hold60+prev_low | OPPOSITE | -0.95% | -1.7 | -1.34% | -1.7 | 3.434 |
| trail4+prev_low | OPPOSITE | -0.98% | -1.7 | -1.34% | -1.7 | 3.434 |

### E07-BRK: Extra exit signals on BRK entries (E07)
Claim before the run: Adding this signal as an extra exit to a loose 4-ATR trail (or a 60-day hold) raises net return per trade, paired by trade, in both dev and validation.
Outcome: 3 did not hold, 1 had too little data to judge across 4 variants.

### E07-PULL: Extra exit signals on PULL entries (E07)
Claim before the run: Adding this signal as an extra exit to a loose 4-ATR trail (or a 60-day hold) raises net return per trade, paired by trade, in both dev and validation.
Outcome: 3 came out the opposite way, 1 did not hold across 4 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| hold60+prev_low | OPPOSITE | -1.56% | -2.1 | -2.71% | -2.3 | 3.434 |
| trail4+prev_low | OPPOSITE | -1.57% | -2.1 | -2.70% | -2.3 | 3.434 |
| trail4+low20 | OPPOSITE | -0.58% | -1.8 | -0.96% | -1.8 | 3.434 |

### E11-ANY: Exit on a lower price-band hit, ANY entries
Claim before the run: Leaving at the next open after the stock hits its lower price band raises net return per trade against the same policy without it.
Outcome: 3 did not hold across 3 variants.

### E11-BRK: Exit on a lower price-band hit, BRK entries
Claim before the run: Leaving at the next open after the stock hits its lower price band raises net return per trade against the same policy without it.
Outcome: 2 came out the opposite way, 1 did not hold across 3 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| hold_60d+band_low | OPPOSITE | -0.15% | -2.3 | -0.17% | -2.3 | 3.437 |
| sma_close_50+band_low | OPPOSITE | -0.13% | -2.2 | -0.14% | -2.2 | 3.443 |

### E11-PULL: Exit on a lower price-band hit, PULL entries
Claim before the run: Leaving at the next open after the stock hits its lower price band raises net return per trade against the same policy without it.
Outcome: 3 did not hold across 3 variants.

## factor_monthly (1 studies)

### FP1: Monthly factor portfolios for the long-term money: 12-month momentum, low volatility and the two combined, top decile of the 500 most traded stocks, rebalanced monthly, against the equal-weight universe and the Nifty 500, after costs (2000-2023)
Claim before the run: Among the 500 most traded NSE stocks, the top decile by 12-month momentum (skipping the latest month) earns more over the next month than the equal-weight universe and than the Nifty 500 index, after monthly rebalancing costs; the top decile by low volatility (lowest 12-month daily volatility) earns at least as much with a smaller drawdown; the two combined (average rank) earn more than either benchmark; the bottom momentum decile earns less than the universe; and a random decile earns nothing in particular.
Outcome: 6 did not hold, 2 held up, weaker in one period across 8 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| MOM_bottom · vs_EW | CONDITIONAL | -1.17% | -2.9 | -1.27% | -2.7 | 2.734 |
| RANDOM · vs_EW | CONDITIONAL | -0.41% | -3.7 | -0.47% | -2.5 | 2.734 |

## filter (4 studies)

### E04-ANY: Saturation after long runs and declines (M-03/04/13) as a no-entry filter (ANY entries)
Claim before the run: Trades signalled while the condition is on earn a different net return than trades signalled while it is off (direction as stated per condition), within quarters, in dev and validation.
Outcome: 10 had too little data to judge, 5 held up, weaker in one period, 3 held up in both periods, 2 did not hold across 20 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| ext_ret20_gt25 · hold_20d | VALIDATED | -2.05% | -5.0 | -2.84% | -4.8 | 3.437 |
| ext_ret20_gt25 · atr_trail_4 | VALIDATED | -1.86% | -3.6 | -3.29% | -4.0 | 3.437 |
| ext_sma50_gt20 · hold_20d | VALIDATED | -2.49% | -6.0 | -2.38% | -3.9 | 3.437 |
| ext_sma50_gt20 · atr_trail_4 | CONDITIONAL | -2.38% | -4.5 | -2.36% | -3.1 | 3.437 |
| ext_sma50_gt20 · swing_low_20 | CONDITIONAL | -2.44% | -4.0 | -2.37% | -2.6 | 3.437 |
| ext_sma50_gt20 · hold_60d | CONDITIONAL | -2.29% | -3.8 | -1.99% | -2.1 | 3.437 |
| ext_sma50_gt20 · sma_close_50 | CONDITIONAL | -2.40% | -3.9 | -1.95% | -2.1 | 3.437 |
| ext_ret60_gt50 · hold_20d | CONDITIONAL | -2.14% | -3.9 | -1.66% | -1.8 | 3.437 |

### E04-BRK: Saturation after long runs and declines (M-03/04/13) as a no-entry filter (BRK entries)
Claim before the run: Trades signalled while the condition is on earn a different net return than trades signalled while it is off (direction as stated per condition), within quarters, in dev and validation.
Outcome: 10 had too little data to judge, 9 did not hold, 1 held up, weaker in one period across 20 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| ext_ret20_gt25 · hold_20d | CONDITIONAL | -1.04% | -2.7 | -2.23% | -3.5 | 3.437 |

### E04-PULL: Saturation after long runs and declines (M-03/04/13) as a no-entry filter (PULL entries)
Claim before the run: Trades signalled while the condition is on earn a different net return than trades signalled while it is off (direction as stated per condition), within quarters, in dev and validation.
Outcome: 20 had too little data to judge across 20 variants.

### E05-PULL: Pullback depth and healthy pullbacks (M-05, TWT-H10/18/19), PULL entries (PULL entries)
Claim before the run: Trades signalled while the condition is on earn a different net return than trades signalled while it is off (direction as stated per condition), within quarters, in dev and validation.
Outcome: 20 did not hold, 5 had too little data to judge across 25 variants.

## flows (3 studies)

### C06: Participant positioning in Nifty futures (FII, Client) and the next 5 sessions
Claim before the run: FII net long (or rising) is followed by higher 5-session Nifty returns, FII net short by lower; a crowded Client long by lower.
Outcome: 2 had too little data to judge, 1 came out the opposite way, 1 did not hold across 4 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| fii_long_gt60 | OPPOSITE | -0.92% | -3.3 | -0.81% | -2.8 | 2.498 |

### DII1: Domestic mutual fund cash flows (the largest part of DII): do sharp outflows precede a weaker Nifty, inflows a stronger one, and does DII buying while FII sells cushion the market?
Claim before the run: Sessions after sharply negative mutual fund equity net flows (bottom decile, daily or over 5 sessions) are followed by weaker Nifty returns over 1, 5 and 20 sessions; after sharply positive flows (top decile) by stronger returns; and a day with mutual funds in their top decile while FPIs are in their bottom decile is followed by a stronger Nifty over 5 and 20 sessions (the domestic cushion).
Outcome: 10 did not hold across 10 variants.

### FII1: Foreign investor (FPI) cash flows: do sharp outflows precede a weaker Nifty, and inflows a stronger one?
Claim before the run: Sessions after sharply negative FPI equity net flows (bottom decile, daily or over 5 sessions) are followed by weaker Nifty returns over 1, 5 and 20 sessions; after sharply positive flows (top decile) by stronger returns.
Outcome: 8 did not hold across 8 variants.

## forecast_hf (1 studies)

### HF-CHRONOS: Hugging Face Chronos-Bolt: zero-shot direction forecasts of Nifty 50 and Bank Nifty
Claim before the run: Does a zero-shot Hugging Face time-series model, Chronos-Bolt, forecast the direction of NIFTY 50 and NIFTY BANK over the next session and the next 5 sessions better than (a) a coin flip and (b) Ananta's own daily-call rule (call-v0-2026-10-18, india/dailycall.py), and is its forecast spread calibrated?
Outcome: 7 did not hold, 3 had too little data to judge across 10 variants.

## futures (1 studies)

### F04: Stock futures price/open-interest quadrants and the next 5 sessions
Claim before the run: After a day with price and open interest both moving more than 2% / 5%, the next 5 sessions move the way the quadrant says (build-ups continue).
Outcome: 2 did not hold, 1 came out the opposite way, 1 had too little data to judge across 4 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| long_unwinding | OPPOSITE | +0.66% | +2.7 | +0.17% | +0.4 | 2.498 |

## fx (1 studies)

### FX1: Rupee against the dollar: does a sharply weaker rupee precede weaker Indian stocks (and stronger exporters)?
Claim before the run: After a sharp weakening of the rupee (USD/INR up) the Nifty and Bank Nifty do worse over the next 5 and 20 sessions, while the exporters (Nifty IT, Nifty Pharma) do better than the Nifty; and TWT-H42 restated on the rupee: when USD/INR is up 5%+ over 126 sessions, or breaks above its 3-year high, the Nifty's next 21 and 63 sessions are weaker.
Outcome: 6 did not hold, 4 had too little data to judge across 10 variants.

## gaps (1 studies)

### GP1: The opening gap: does buying the open after a gap-down (mean reversion) or after a gap-up (follow-through) beat ordinary days, after costs?
Claim before the run: A stock or index that opens at least 1-2% below the previous close is worth buying at that open (the gap is an over-reaction that is partly given back over the next sessions); a stock that opens 2% or more above the previous close is worth buying, at that open or at the next session's open, because the gap continues. Either beats ordinary days over the same holding period, net of costs.
Outcome: 4 had too little data to judge, 2 did not hold, 2 held up, weaker in one period, 1 held up in both periods, 1 came out the opposite way across 10 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| STK · gapdown2 · open · hold1 | VALIDATED | +2.26% | +14.7 | +0.44% | +3.0 | 2.807 |
| STK · gapdown1 · open · hold5 | CONDITIONAL | +1.22% | +10.5 | +0.41% | +2.8 | 2.807 |
| STK · gapdown2 · open · hold5 | CONDITIONAL | +2.22% | +10.9 | +0.64% | +2.4 | 2.807 |
| STK · gapup2 · open · hold5 | OPPOSITE | -1.03% | -8.2 | -0.07% | -0.4 | 2.807 |

## gate (3 studies)

### E08-ANY: Market gates on ANY entries
Claim before the run: Trades signalled while the gate is on earn more net than trades signalled while it is off, in dev and validation.
Outcome: 15 had too little data to judge, 5 came out the opposite way across 20 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| nifty_gt50d · atr_trail_4 | OPPOSITE | -5.10% | -6.0 | -4.27% | -5.3 | 3.341 |
| nifty_gt50d · swing_low_20 | OPPOSITE | -5.78% | -5.8 | -3.98% | -5.2 | 3.341 |
| nifty_gt50d · sma_close_50 | OPPOSITE | -5.62% | -5.1 | -4.12% | -5.1 | 3.341 |
| nifty_gt50d · hold_60d | OPPOSITE | -5.56% | -4.8 | -4.17% | -5.1 | 3.341 |
| nifty_gt50d · hold_20d | OPPOSITE | -4.48% | -6.7 | -2.71% | -3.7 | 3.341 |

### E08-BRK: Market gates on BRK entries
Claim before the run: Trades signalled while the gate is on earn more net than trades signalled while it is off, in dev and validation.
Outcome: 15 had too little data to judge, 5 came out the opposite way across 20 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| nifty_gt50d · sma_close_50 | OPPOSITE | -4.67% | -3.3 | -3.68% | -3.2 | 3.341 |
| nifty_gt50d · atr_trail_4 | OPPOSITE | -3.38% | -4.5 | -2.61% | -3.1 | 3.341 |
| nifty_gt50d · swing_low_20 | OPPOSITE | -4.56% | -3.5 | -3.26% | -3.0 | 3.341 |
| nifty_gt50d · hold_60d | OPPOSITE | -4.76% | -3.3 | -3.29% | -2.7 | 3.341 |
| nifty_gt50d · hold_20d | OPPOSITE | -2.33% | -3.5 | -3.35% | -2.1 | 3.341 |

### E08-PULL: Market gates on PULL entries
Claim before the run: Trades signalled while the gate is on earn more net than trades signalled while it is off, in dev and validation.
Outcome: 15 had too little data to judge, 5 came out the opposite way across 20 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| nifty_gt50d · atr_trail_4 | OPPOSITE | -3.88% | -3.1 | -3.19% | -3.1 | 3.341 |
| nifty_gt50d · swing_low_20 | OPPOSITE | -3.94% | -2.6 | -2.98% | -2.8 | 3.341 |
| nifty_gt50d · hold_60d | OPPOSITE | -3.85% | -2.3 | -3.03% | -2.6 | 3.341 |
| nifty_gt50d · hold_20d | OPPOSITE | -3.87% | -4.2 | -2.25% | -2.4 | 3.341 |
| nifty_gt50d · sma_close_50 | OPPOSITE | -4.02% | -2.5 | -2.67% | -1.9 | 3.341 |

## hedge (4 studies)

### F06-ANY: Nifty put protection on the 10-slot ANY book
Claim before the run: Buying monthly Nifty puts raises the book's quarterly return (it usually costs: the cost is the measured quantity) while cutting the worst drawdown.
Outcome: 4 did not hold across 4 variants.

### F06-BRK: Nifty put protection on the 10-slot BRK book
Claim before the run: Buying monthly Nifty puts raises the book's quarterly return (it usually costs: the cost is the measured quantity) while cutting the worst drawdown.
Outcome: 4 did not hold across 4 variants.

### F06-PULL: Nifty put protection on the 10-slot PULL book
Claim before the run: Buying monthly Nifty puts raises the book's quarterly return (it usually costs: the cost is the measured quantity) while cutting the worst drawdown.
Outcome: 4 did not hold across 4 variants.

### HG1: Hedging a long stock basket when the Nifty is below its 200-day average: short index futures, 20% more cash, or a monthly 5%-out-of-the-money Nifty put
Claim before the run: A long basket of liquid stocks is better protected, at an acceptable cost in return, by (i) a short Nifty futures position equal to the basket whenever the Nifty closed below its 200-day average, (ii) holding 20% of the basket in cash whenever the Nifty closed below its 200-day average, or (iii) buying a one-month Nifty put 5% out of the money every month: each shows a shallower worst 20-session drawdown, and a better return per unit of drawdown, than the unhedged basket.
Outcome: 4 did not hold, 1 held up, weaker in one period, 1 had too little data to judge across 6 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| cash20 · worst20 | CONDITIONAL | +0.66% | +3.7 | +0.66% | +1.9 | 2.991 |

## indicator (3 studies)

### P01-ANY: Indicator-pattern conditions at entry (ANY entries)
Claim before the run: Trades signalled while the indicator condition is on earn a different net return than when it is off (direction per condition), within quarters.
Outcome: 7 had too little data to judge, 5 held up, weaker in one period, 4 came out the opposite way, 3 held up in both periods, 1 did not hold across 20 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| rsi_gt70 · hold_20d | VALIDATED | -1.93% | -5.1 | -1.47% | -4.4 | 3.267 |
| rsi_gt70 · atr_trail_4 | VALIDATED | -1.66% | -3.4 | -1.82% | -3.9 | 3.279 |
| rsi_lt30 · hold_20d | VALIDATED | +2.54% | +4.2 | +1.91% | +3.4 | 3.234 |
| stoch_lt20 · atr_trail_4 | CONDITIONAL | +1.33% | +3.2 | +1.64% | +3.3 | 3.307 |
| rsi_gt70 · swing_low_20 | CONDITIONAL | -1.80% | -3.7 | -1.58% | -3.0 | 3.291 |
| rsi_lt30 · atr_trail_4 | CONDITIONAL | +2.82% | +3.3 | +3.28% | +3.0 | 3.248 |
| rsi_gt70 · sma_close_50 | CONDITIONAL | -1.75% | -3.6 | -1.43% | -2.6 | 3.285 |
| rsi_gt70 · hold_60d | CONDITIONAL | -1.71% | -3.4 | -1.26% | -2.2 | 3.273 |
| wk_outside_up · atr_trail_4 | OPPOSITE | -0.98% | -2.1 | -1.13% | -2.0 | 3.332 |
| wk_outside_up · swing_low_20 | OPPOSITE | -1.37% | -2.1 | -0.84% | -1.4 | 3.341 |
| wk_outside_up · sma_close_50 | OPPOSITE | -1.27% | -1.9 | -0.92% | -1.3 | 3.337 |
| wk_outside_up · hold_60d | OPPOSITE | -1.15% | -1.8 | -0.80% | -1.2 | 3.327 |

### P01-BRK: Indicator-pattern conditions at entry (BRK entries)
Claim before the run: Trades signalled while the indicator condition is on earn a different net return than when it is off (direction per condition), within quarters.
Outcome: 14 had too little data to judge, 5 did not hold, 1 held up, weaker in one period across 20 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| rsi_gt70 · hold_20d | CONDITIONAL | -0.93% | -3.4 | -0.55% | -1.7 | 2.638 |

### P01-PULL: Indicator-pattern conditions at entry (PULL entries)
Claim before the run: Trades signalled while the indicator condition is on earn a different net return than when it is off (direction per condition), within quarters.
Outcome: 15 had too little data to judge, 5 did not hold across 20 variants.

## intraday (5 studies)

### I01: First 30 / 60 minutes and the rest of the day (index)
Claim before the run: The direction of the first 30 (or 60) minutes carries on to the close: the rest-of-day return signed by the opening direction is positive (M-01/M-02).
Outcome: 5 had too little data to judge, 3 did not hold across 8 variants.

### I02: Intraday level-break exits on the index (spot side)
Claim before the run: Leaving an intraday index position on an opening-range break, a previous-day-level break or a 0.5% stop earns more than holding to 15:15.
Outcome: 7 did not hold, 5 had too little data to judge across 12 variants.

### I05: Expiry-day afternoon: break of the 13:00-13:29 range (spot side of O-04)
Claim before the run: On expiry days, after the first close outside the 13:00-13:29 range, the index keeps moving the break's way to 15:15 (continuation > 0).
Outcome: 4 had too little data to judge, 4 did not hold across 8 variants.

### IB1: Intraday breakouts: on Nifty, Bank Nifty and liquid stocks, does trading the break of the opening range (first 15 or 30 minutes), the break of the first hour's range after 11:00, or a stock reclaiming its VWAP earn more after costs than a random intraday entry?
Claim before the run: Breakouts within the day carry momentum: entering on the first break of the opening range (long above its high, short below its low for the indices; long only for stocks), with a stop at the other side and an exit near the close, earns more after costs than a random entry on the same days; so do a break of the first hour's range after 11:00 (indices) and a stock reclaiming its VWAP after trading below it.
Outcome: 4 held up in both periods, 3 held up, weaker in one period, 1 did not hold across 8 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| STK · orb30 · net | VALIDATED | +0.14% | +8.6 | +0.12% | +9.0 | 3.197 |
| STK · orb15 · net | VALIDATED | +0.14% | +8.5 | +0.10% | +7.4 | 3.197 |
| IDX · fh_break · net | VALIDATED | +0.08% | +3.2 | +0.11% | +5.0 | 3.197 |
| STK · vwap_reclaim · net | CONDITIONAL | +0.04% | +3.1 | +0.05% | +4.6 | 3.197 |
| NIFTY · orb30 · net | VALIDATED | +0.13% | +4.8 | +0.08% | +3.6 | 3.197 |
| BANK · orb30 · net | CONDITIONAL | +0.15% | +4.3 | +0.09% | +2.3 | 3.197 |
| BANK · orb15 · net | CONDITIONAL | +0.13% | +3.6 | +0.06% | +1.7 | 3.197 |

### MS1: Intraday patterns: does the first 15 minutes' direction carry through the rest of the day (indices and liquid stocks), does the last hour extend the day's move, does a wide opening range come before a wide rest of the day, and are expiry-day afternoons more volatile?
Claim before the run: The first 15 minutes set the day's direction (the rest of the day moves the same way), the last hour extends the move made until 14:30, a wide 09:15-09:30 range comes before a wider range for the rest of the day, and on an index's own expiry day the 13:30-15:30 move is bigger than on other days.
Outcome: 4 did not hold, 1 had too little data to judge, 1 held up, weaker in one period across 6 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| IDX · or15_top · dayrange | CONDITIONAL | +0.19% | +2.0 | +0.45% | +4.4 | 3.241 |

## news_tone (1 studies)

### HFN1: Does a financial-news model's reading of NSE company announcements predict the stock's drift over the next 5 and 20 sessions, beyond the announcement's category?
Claim before the run: Does a financial-news model's reading of NSE company announcements predict the stock's drift over the next 5 and 20 sessions, beyond the announcement's category?
Outcome: 7 did not hold, 1 had too little data to judge across 8 variants.

## options_eod (6 studies)

### DR1: Defined-risk option selling on expiry day: the short straddle, the iron fly and the iron condor on Nifty and Bank Nifty, opened at the expiry-day open and closed at the close (2014-2023 real prices), against the same structures three sessions before expiry
Claim before the run: Expiry-day time decay (GK1: option buyers lost 15-19% of the premium between the open and the close in 2018-23) is capturable from the selling side after costs and spreads: a short at-the-money straddle opened at the expiry-day open and bought back at the close earns more than zero net; the iron fly (the same straddle with bought wings 1% or 2% from the strike) keeps most of that while capping the loss at the wing width; the iron condor (short 1% out, long 2% out) earns more than zero on the capital at risk; and the same four structures opened three sessions before expiry and closed that day (the control) earn nothing in particular.
Outcome: 6 did not hold, 6 held up in both periods, 2 had too little data to judge, 2 came out the opposite way across 16 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| NIFTY · exp3 · fly_w1 | VALIDATED | -10.60% | -6.2 | -11.08% | -6.5 | 3.351 |
| NIFTY · exp3 · fly_w2 | VALIDATED | -6.92% | -3.8 | -4.28% | -5.4 | 3.351 |
| BANK · exp3 · fly_w1 | VALIDATED | -13.26% | -5.3 | -16.33% | -5.2 | 3.351 |
| BANK · exp3 · fly_w2 | VALIDATED | -7.83% | -3.9 | -6.77% | -5.0 | 3.351 |
| BANK · exp3 · condor_1_2 | VALIDATED | -11.48% | -5.9 | -13.36% | -4.9 | 3.351 |
| NIFTY · exp3 · condor_1_2 | VALIDATED | -12.46% | -4.8 | -4.91% | -4.7 | 3.351 |
| NIFTY · exp0 · condor_1_2 | OPPOSITE | -6.61% | -3.5 | -2.04% | -2.1 | 3.351 |
| NIFTY · exp0 · fly_w1 | OPPOSITE | -7.29% | -1.8 | -0.71% | -0.4 | 3.351 |

### F01: Short ATM straddle held to expiry, from k sessions before (NIFTY, BANKNIFTY)
Claim before the run: Premium decays faster than the index moves: selling the at-the-money straddle k sessions before expiry and holding to expiry earns more than zero net of costs and a half-spread (M-07/M-08).
Outcome: 7 did not hold, 1 had too little data to judge across 8 variants.

### F02: O-03 closing-price version: expiry-eve short strangle with hedges, held to expiry
Claim before the run: Selling the 1.5% strangle on the expiry eve with 3% hedges earns more than zero net of costs and spread; the tail is reported first.
Outcome: 1 did not hold, 1 had too little data to judge across 2 variants.

### F03: Option-chain shape: PCR extremes and the max-pain pin (NIFTY, BANKNIFTY)
Claim before the run: High put-call ratio (>1.3) is followed by higher 5-session index returns, low (<0.7) by lower; the expiry settlement sits nearer max pain than the eve forward.
Outcome: 3 came out the opposite way, 3 did not hold across 6 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| maxpain_pin · NIFTY | OPPOSITE | -1.55% | -7.6 | -0.18% | -3.2 | 2.935 |
| maxpain_pin · BANKNIFTY | OPPOSITE | -1.94% | -4.9 | -0.08% | -2.1 | 2.955 |
| pcr_low · NIFTY | OPPOSITE | +0.70% | +2.2 | +0.16% | +0.4 | 2.865 |

### GK1: Option Greeks and time decay: does time decay make buying Nifty and Bank Nifty options on expiry day lose more than the index move earns, do longer-dated options do better than the nearest expiry on the same intraday trades, and do options imply bigger moves than the index then makes, by days to expiry?
Claim before the run: Buying options loses to time decay (theta), worst on expiry day: an at-the-money straddle bought at the open on expiry day loses money by the close after costs, and loses more than the same straddle bought three sessions before expiry; on the same intraday index trades an option on the next expiry earns more per rupee of premium than the nearest (highest-theta) expiry; and the move the options imply is bigger than the move the index then makes, at every distance from expiry.
Outcome: 7 did not hold, 1 came out the opposite way across 8 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| SP1 · next_vs_near · ret | OPPOSITE | -2.19% | -4.8 | -4.01% | -9.5 | 3.267 |

### OS1: Option spreads: for the same intraday index trade, does a debit spread (buy the at-the-money option, sell one 1-2 strikes further out) do better than buying the single option, overall and when the fear gauge is high?
Claim before the run: Selling the further option cuts the premium paid and the time decay, so per rupee at risk the debit spread earns more than the single option, especially when India VIX is high (options dear).
Outcome: 3 came out the opposite way, 3 had too little data to judge across 6 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| ALL · spread1 · ret | OPPOSITE | -20.47% | -29.5 | -23.87% | -35.9 | 3.213 |
| ALL · spread2 · ret | OPPOSITE | -10.86% | -27.6 | -13.73% | -31.7 | 3.213 |
| ALL · spread1 · rs | OPPOSITE | -283.18 | -15.5 | -469.67 | -12.0 | 3.213 |

## options_intraday (1 studies)

### F05-O04: O-04 expiry-day straddle reconstructed on index minutes (synthetic prices)
Claim before the run: O-04 (13:30 ATM straddle, opening-range break closes the loser, winner trailed, combined-premium stop) earns more than zero, and more than holding the same straddle to 15:15, net of costs and a half-spread, in dev (2015-2017) and validation (2018-2023).
Outcome: 8 came out the opposite way, 8 held up, weaker in one period across 16 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| vs_hold · stop0.5_trail0.35_nb14:45 | CONDITIONAL | +0.69% | +2.3 | +1.82% | +12.6 | 2.638 |
| vs_hold · stop0.6_trail0.35_nb14:45 | CONDITIONAL | +0.69% | +2.3 | +1.82% | +12.6 | 2.914 |
| vs_hold · stop0.5_trail0.35_nb15:15 | CONDITIONAL | +0.67% | +2.3 | +1.81% | +12.6 | 2.734 |
| vs_hold · stop0.6_trail0.35_nb15:15 | CONDITIONAL | +0.68% | +2.3 | +1.82% | +12.5 | 2.955 |
| stop0.5_trail0.25_nb14:45 | OPPOSITE | -0.88% | -4.5 | -1.15% | -12.0 | 1.96 |
| stop0.6_trail0.25_nb14:45 | OPPOSITE | -0.88% | -4.5 | -1.15% | -12.0 | 2.773 |
| stop0.6_trail0.25_nb15:15 | OPPOSITE | -0.89% | -4.5 | -1.16% | -11.9 | 2.838 |
| stop0.5_trail0.25_nb15:15 | OPPOSITE | -0.91% | -4.6 | -1.16% | -11.8 | 2.394 |
| vs_hold · stop0.5_trail0.25_nb14:45 | CONDITIONAL | +0.65% | +1.9 | +1.83% | +10.9 | 2.241 |
| vs_hold · stop0.6_trail0.25_nb14:45 | CONDITIONAL | +0.65% | +1.9 | +1.83% | +10.9 | 2.807 |
| vs_hold · stop0.5_trail0.25_nb15:15 | CONDITIONAL | +0.63% | +1.9 | +1.82% | +10.9 | 2.498 |
| vs_hold · stop0.6_trail0.25_nb15:15 | CONDITIONAL | +0.64% | +1.9 | +1.82% | +10.9 | 2.865 |

## portfolio (4 studies)

### BT1: Low beta and low volatility: do the calmest liquid stocks earn as much as or more than the jumpiest, after costs?
Claim before the run: The low-risk effect: a monthly-rebalanced basket of the lowest-beta (or lowest-volatility) fifth of the liquid 250 earns more per month than the highest fifth and than the whole liquid 250, after costs.
Outcome: 4 did not hold across 4 variants.

### E10-ANY: Portfolio drawdown rule on a 10-slot ANY book (hold_60d exits)
Claim before the run: Closing everything when the book is 7-8% below its peak and pausing new entries raises the book's quarterly return (TWT-H25).
Outcome: 4 did not hold across 4 variants.

### E10-BRK: Portfolio drawdown rule on a 10-slot BRK book (hold_60d exits)
Claim before the run: Closing everything when the book is 7-8% below its peak and pausing new entries raises the book's quarterly return (TWT-H25).
Outcome: 4 did not hold across 4 variants.

### E10-PULL: Portfolio drawdown rule on a 10-slot PULL book (hold_60d exits)
Claim before the run: Closing everything when the book is 7-8% below its peak and pausing new entries raises the book's quarterly return (TWT-H25).
Outcome: 4 did not hold across 4 variants.

## reposition (3 studies)

### E06-ANY: Ride and reposition vs hold, ANY entries
Claim before the run: Stepping out on a close below the moving average and back in on strength earns more over 60 sessions than holding, net of costs (M-12).
Outcome: 2 came out the opposite way, 1 did not hold across 3 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| rr_sma50_hh20 | OPPOSITE | -1.72% | -1.8 | -1.54% | -1.4 | 2.773 |
| rr_sma20_hh10 | OPPOSITE | -2.08% | -1.9 | -1.94% | -1.4 | 2.773 |

### E06-BRK: Ride and reposition vs hold, BRK entries
Claim before the run: Stepping out on a close below the moving average and back in on strength earns more over 60 sessions than holding, net of costs (M-12).
Outcome: 3 did not hold across 3 variants.

### E06-PULL: Ride and reposition vs hold, PULL entries
Claim before the run: Stepping out on a close below the moving average and back in on strength earns more over 60 sessions than holding, net of costs (M-12).
Outcome: 3 came out the opposite way across 3 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| rr_sma50_hh20 | OPPOSITE | -3.22% | -2.5 | -3.56% | -2.9 | 2.773 |
| rr_sma20_hh10 | OPPOSITE | -3.20% | -2.4 | -3.87% | -2.6 | 2.773 |
| rr_sma20_sma20 | OPPOSITE | -2.45% | -2.2 | -3.04% | -2.2 | 2.773 |

## rx_drafts (2 studies)

### RX1: The 12 reconstruction drafts of 26-27 Oct: is there a rule, known at the previous close, for the situations no family was positioned for; would a time stop have fixed the pullback trades that never worked; and would a faster exit change the random control that held into falls?
Claim before the run: Each missed situation has a version known before the move: a stock in that state at yesterday's close moves in the missed direction the next session more than the average liquid stock does (falls: breaking below its 20-day range, a 52-week low, a fall below the 200-day average, a pullback in an uptrend; rises: a rise below the 200-day average, a stock inside its range in an uptrend), and the reference traders' multi-day trips in the two gap situations beat the average stock over 5 sessions; for pullback-in-an-uptrend entries, leaving at the next open when a trade has not gained a quarter of its planned risk by the third close beats holding 20 sessions; the same time stop helps the random liquid picks, and more so while the Nifty is under its 200-day average.
Outcome: 4 did not hold, 4 came out the opposite way, 3 had too little data to judge, 1 held up, weaker in one period across 12 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| D · downtrend_fall · next_oc | CONDITIONAL | -0.18% | -4.9 | -0.12% | -2.5 | 3.59 |
| X · CTL_downtrend · unproven3_vs_hold20 | OPPOSITE | -0.48% | -2.0 | -0.64% | -2.1 | 3.59 |
| X · CTL · unproven3_vs_hold20 | OPPOSITE | -0.24% | -2.0 | -0.24% | -1.7 | 3.59 |
| X · PULL · unproven3_vs_hold20 | OPPOSITE | -0.44% | -2.4 | -0.26% | -1.5 | 3.59 |
| L · inside_range · fwd5 | OPPOSITE | -0.34% | -2.5 | -0.05% | -0.4 | 3.59 |

### RX2: Oversold reversals that never worked: does leaving at the 4th session's open, when the first 3 highs never reached a quarter of the planned risk, beat holding 20 sessions?
Claim before the run: For oversold-reversal entries (RSI under 30, liquid stocks), the day-3 time stop beats holding 20 sessions after costs.
Outcome: 1 came out the opposite way across 1 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| X · REV · unproven3_vs_hold20 | OPPOSITE | -0.41% | -2.5 | -0.63% | -2.4 | 3.591 |

## staging (3 studies)

### E09-ANY: Staged entries vs one entry, ANY entries
Claim before the run: Splitting the entry (25/75 on a pullback, or weekly quarters) earns more per rupee deployed than one entry at the signal open, same exit (TWT-H20/21).
Outcome: 2 came out the opposite way across 2 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| stage_25_75_pullback | OPPOSITE | -0.63% | -4.1 | -0.27% | -1.2 | 2.638 |
| stage_weekly4 | OPPOSITE | -0.76% | -3.1 | -0.36% | -1.0 | 2.638 |

### E09-BRK: Staged entries vs one entry, BRK entries
Claim before the run: Splitting the entry (25/75 on a pullback, or weekly quarters) earns more per rupee deployed than one entry at the signal open, same exit (TWT-H20/21).
Outcome: 2 did not hold across 2 variants.

### E09-PULL: Staged entries vs one entry, PULL entries
Claim before the run: Splitting the entry (25/75 on a pullback, or weekly quarters) earns more per rupee deployed than one entry at the signal open, same exit (TWT-H20/21).
Outcome: 2 came out the opposite way across 2 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| stage_weekly4 | OPPOSITE | -0.89% | -2.3 | -0.67% | -1.4 | 2.638 |
| stage_25_75_pullback | OPPOSITE | -0.68% | -2.7 | -0.45% | -1.3 | 2.638 |

## stop (4 studies)

### E01-ANY: Stop distance on ANY entries
Claim before the run: A different initial stop distance than 2 ATR changes net return per trade over a 20-session hold.
Outcome: 5 had too little data to judge across 5 variants.

### E01-BRK: Stop distance on BRK entries
Claim before the run: A different initial stop distance than 2 ATR changes net return per trade over a 20-session hold.
Outcome: 5 did not hold across 5 variants.

### E01-PULL: Stop distance on PULL entries
Claim before the run: A different initial stop distance than 2 ATR changes net return per trade over a 20-session hold.
Outcome: 3 had too little data to judge, 2 did not hold across 5 variants.

### TS1: Trailing stop or fixed stop: on the same entries, does a trailing stop beat a fixed one, and does either beat simply holding 20 sessions?
Claim before the run: On the campaigns' own entries, a stop that trails the price (2 ATR below the peak, or 10% below the peak) earns more per trade after costs than a fixed stop (7% below entry, or 2 ATR below entry), and a stop rule earns more than selling at the close of the 20th session.
Outcome: 5 came out the opposite way, 2 had too little data to judge, 1 did not hold across 8 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| PULL · trail2atr_vs_fixed2atr | OPPOSITE | -2.49% | -3.0 | -3.04% | -2.6 | 3.52 |
| ANY · trail2atr_vs_fixed2atr | OPPOSITE | -2.38% | -2.6 | -1.77% | -1.8 | 3.52 |
| ANY · trail10_vs_fixed7 | OPPOSITE | -1.60% | -2.7 | -0.93% | -1.7 | 3.52 |
| BRK · trail2atr_vs_fixed2atr | OPPOSITE | -1.51% | -2.0 | -1.55% | -1.6 | 3.52 |
| ANY · trail2atr_vs_hold20 | OPPOSITE | -0.73% | -3.4 | -0.28% | -1.4 | 3.52 |

## teacher_opt (24 studies)

### T-OPT-H16: Optionables · OPT-H16 Weekly straddle: naked versus winged
Claim before the run: Sell the ATM weekly straddle at the first session's open of the expiry week (Friday, or the session after the previous expiry), hold to expiry settlement. Naked earns more than zero; naked minus the version with wings bought at the breakevens (strikes nearest K +/- the credit) is positive.
Outcome: 4 had too little data to judge across 4 variants.

### T-OPT-H17: Optionables · OPT-H17 Overnight expiry-eve strangle
Claim before the run: Sell the call and put about 200 points out (Bank Nifty), or 0.7% of spot, at the close the session before expiry; buy back at the expiry-day open. A winged version buys the strikes 550 points out. Earns more than zero; his figures: 75%+ wins, 20-25% a year, max drawdown ~11%.
Outcome: 2 did not hold, 2 had too little data to judge across 4 variants.

### T-OPT-H20: Optionables · OPT-H20 VIX level and premium selling
Claim before the run: The short ATM straddle sold 5 sessions before each expiry and held to expiry earns more when VIX is under 14 than at 14+ (claim a), and more when VIX is over 20 than at 20 or less (claim d). His videos conflict, so both are registered; claim (b) 'worse in low VIX' shows as OPPOSITE on the first.
Outcome: 4 had too little data to judge across 4 variants.

### T-OPT-H21: Optionables · OPT-H21 Rising VIX hurts premium sellers
Claim before the run: The same straddle earns less when VIX rose over the prior 5 sessions, and when it rose 10%+ from under 14.
Outcome: 2 did not hold, 2 had too little data to judge across 4 variants.

### T-OPT-H24: Optionables · OPT-H24 Flat through binary events
Claim before the run: A short ATM straddle sold at the close and bought back at the next open earns less on nights before scheduled binary events (elections, RBI, Budget, Fed, from the event table) than on other nights.
Outcome: 2 did not hold across 2 variants.

### T-OPT-H25: Optionables · OPT-H25 OI band contains the expiry
Claim before the run: k sessions before expiry (k = 5, 1), the settlement lands between the biggest put-OI strike below spot and the biggest call-OI strike above spot more often than inside a band of the same width centred on spot.
Outcome: 3 came out the opposite way, 1 did not hold across 4 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| NIFTY · k1 | OPPOSITE | -20.83% | -5.7 | -10.52% | -4.3 | 3.44 |
| BANKNIFTY · k1 | OPPOSITE | -15.39% | -4.1 | -6.49% | -2.8 | 3.44 |
| NIFTY · k5 | OPPOSITE | -13.89% | -3.7 | -2.87% | -1.0 | 3.44 |

### T-OPT-H26: Optionables · OPT-H26 OI band contains tomorrow
Claim before the run: The next session's high and low stay inside the prior close's biggest call-OI and put-OI strikes (nearest expiry) more often than inside an equal-width band centred on the close.
Outcome: 2 came out the opposite way across 2 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| BANKNIFTY | OPPOSITE | -17.72% | -6.7 | -12.74% | -8.6 | 3.44 |
| NIFTY | OPPOSITE | -19.88% | -13.8 | -10.98% | -7.8 | 3.44 |

### T-OPT-H27: Optionables · OPT-H27 OI levels fail when VIX is high
Claim before the run: The H26 band holds less often when VIX is 20 or more.
Outcome: 2 had too little data to judge across 2 variants.

### T-OPT-H28: Optionables · OPT-H28 PCR and direction
Claim before the run: Nearest-expiry put/call OI ratio at the close against the index from the next open to the close 1 or 5 sessions later: (a) PCR over 1.2 bullish; (b) PCR under 0.5 contrarian bullish; (c) PCR under 0.7 bearish. All three registered (his videos contradict each other).
Outcome: 5 did not hold, 4 had too little data to judge across 9 variants.

### T-OPT-H29: Optionables · OPT-H29 PCR near 1 means a quiet day
Claim before the run: With PCR 0.85-1.15 and the biggest single strike holding more than the median share of OI, the next session's range (and the next 5 sessions') is narrower.
Outcome: 3 did not hold across 3 variants.

### T-OPT-H30: Optionables · OPT-H30 OI change near the money
Claim before the run: Within 2% of spot (nearest expiry): call OI falling while put OI rises predicts a higher index over 1 and 5 sessions; call OI added at 2x the put OI added while put OI falls predicts a lower one.
Outcome: 6 did not hold across 6 variants.

### T-OPT-H31: Optionables · OPT-H31 Max-OI pinning
Claim before the run: Expiry settles closer to the strike with the biggest call+put OI (k = 1, 3 sessions before) than to the at-the-money strike at the same time.
Outcome: 4 came out the opposite way across 4 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| BANKNIFTY · k1 | OPPOSITE | +3.34% | +8.0 | +0.78% | +6.5 | 3.44 |
| NIFTY · k1 | OPPOSITE | +1.95% | +6.7 | +0.76% | +4.7 | 3.44 |
| BANKNIFTY · k3 | OPPOSITE | +2.69% | +7.4 | +0.56% | +4.5 | 3.44 |
| NIFTY · k3 | OPPOSITE | +1.57% | +7.2 | +0.80% | +4.2 | 3.44 |

### T-OPT-H32: Optionables · OPT-H32 OI the day after expiry
Claim before the run: The OI band (H25) taken from the next contract on the first session after an expiry contains that contract's settlement more often than the band taken on the expiry day itself.
Outcome: 2 had too little data to judge across 2 variants.

### T-OPT-H41: Optionables · OPT-H41 Early profit-taking
Claim before the run: Short weekly ATM straddle (H16 entries, naked): closing at the first daily close where it has kept 65%, 75% or 90% of the credit beats holding to expiry.
Outcome: 6 had too little data to judge across 6 variants.

### T-OPT-H42: Optionables · OPT-H42 Monthly put ratio spread 1:2
Claim before the run: About 20 sessions before monthly expiry: buy the ATM put, sell 2 puts ~1.3% lower, hold to expiry. Earns more than zero (Nifty, Bank Nifty); net-credit entries beat net-debit ones; entries with VIX over 20 beat the rest. His figure: profitable 60-70% of months.
Outcome: 2 did not hold, 2 had too little data to judge across 4 variants.

### T-OPT-H45: Optionables · OPT-H45 Implied probabilities are well calibrated
Claim before the run: 5 sessions before expiry, the probability of settling above each near strike from adjacent call prices scores better (lower Brier score) than a lognormal built from the last 20 sessions' realised volatility.
Outcome: 2 came out the opposite way across 2 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| BANKNIFTY | OPPOSITE | -1.67% | -3.5 | -2.49% | -10.7 | 3.44 |
| NIFTY | OPPOSITE | -4.29% | -5.4 | -1.47% | -5.0 | 3.44 |

### T-OPT-H47: Optionables · OPT-H47 Buying after an IV spike loses
Claim before the run: After a 25%+ weekly VIX jump (and with VIX over 30), an ATM Nifty call bought at the close and sold 3 sessions later loses on average.
Outcome: 2 had too little data to judge across 2 variants.

### T-OPT-H48: Optionables · OPT-H48 Range breakouts
Claim before the run: Stocks closing above a 20-session range no wider than 10% beat the market drift over 5 and 10 sessions; 60-session ranges (15% or tighter) beat the 20-session ones over 10. Nifty: a close above a 20-session range no wider than 4% is followed by higher 5 and 10 session returns than other sessions.
Outcome: 2 had too little data to judge, 2 did not hold, 1 came out the opposite way across 5 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| stk20 · net10 | OPPOSITE | -0.63% | -2.5 | -0.31% | -1.0 | 3.44 |

### T-OPT-H49: Optionables · OPT-H49 Big red day without follow-through
Claim before the run: After a 1.5%+ down day in an uptrend stock (above its 200 DMA, rising 50 DMA), if the next 3 closes stay above that day's low, the next 5 and 20 sessions (counted from day 3) beat red days that did get follow-through.
Outcome: 2 did not hold across 2 variants.

### T-OPT-H50: Optionables · OPT-H50 Swing-low invalidation
Claim before the run: Stocks closing below their last confirmed swing low earn less over 5, 10 and 20 sessions than stocks still above it (every 5th session).
Outcome: 3 did not hold across 3 variants.

### T-OPT-H51: Optionables · OPT-H51 New all-time highs
Claim before the run: A stock's first close above every earlier high (one per 10 sessions) beats the market drift over 5, 10 and 20 sessions; Nifty all-time-high closes are followed by higher 5 and 21 session returns than other sessions.
Outcome: 3 came out the opposite way, 2 had too little data to judge across 5 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| stk · net20 | OPPOSITE | -1.91% | -3.0 | -0.83% | -1.7 | 3.44 |
| stk · net10 | OPPOSITE | -0.90% | -2.4 | -0.48% | -1.5 | 3.44 |
| stk · net5 | OPPOSITE | -0.53% | -2.7 | -0.35% | -1.5 | 3.44 |

### T-OPT-H52: Optionables · OPT-H52 Broken resistance holds on the first retest
Claim before the run: The first retest of a broken 60-session high (low within 1% of the level, close no more than 2% under it, 5-20 sessions after the breakout) beats the market drift over 10 sessions.
Outcome: 1 came out the opposite way across 1 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| first_retest · net10 | OPPOSITE | -0.62% | -3.0 | -0.17% | -0.9 | 3.44 |

### T-OPT-H58: Optionables · OPT-H58 Holiday weeks decay faster
Claim before the run: The ATM straddle's decay per session from the start of the expiry week to the expiry eve is faster in weeks shortened by a holiday.
Outcome: 2 had too little data to judge across 2 variants.

### T-OPT-H59: Optionables · OPT-H59 Next week's straddle sold on expiry day
Claim before the run: On each weekly expiry day, sell the next expiry's ATM straddle at the close; buy back at the next open, or at the next close. Earns more than zero.
Outcome: 4 had too little data to judge across 4 variants.

## teacher_twt (43 studies)

### T-TWT-H01: Trade With Trend (Raunak A) · TWT-H01 Low breadth hurts breakouts
Claim before the run: Breakouts taken while under X% of the liquid 500 are above their 200 DMA (X = 25, 30, 35, 40) earn less over 20 and 60 sessions than breakouts taken while breadth is 50% or more; they also fail (close back under the breakout level within 5 sessions) more often.
Outcome: 9 had too little data to judge across 9 variants.

### T-TWT-H02: Trade With Trend (Raunak A) · TWT-H02 Index below both averages hurts breakouts
Claim before the run: Breakouts taken while the Nifty closes below both its 50 and 200 DMA earn less over 20 and 60 sessions, and fail within 5 sessions more often, than breakouts taken while it is above both. His figure checked alongside: about 75% of longs lose over 3 months when the index is below a falling 200 DMA.
Outcome: 3 had too little data to judge across 3 variants.

### T-TWT-H04: Trade With Trend (Raunak A) · TWT-H04 Top-RS sectors lead
Claim before the run: Sector version (we hold sector indices, not a stock-to-sector map): every 5th session, rank the sector indices by their 63-session change against the Nifty 500; the top 3 beat the rest over 21, 63 and 126 sessions (excess return over the Nifty 500).
Outcome: 3 did not hold across 3 variants.

### T-TWT-H05: Trade With Trend (Raunak A) · TWT-H05 Strong-structure sectors outperform, weak ones lag
Claim before the run: A sector index with higher highs and higher lows (20-session swings), above a rising 50 DMA, and a rising RS line against the Nifty 500 beats the Nifty 500 over 21/63/126 sessions; a sector below a falling 50 DMA with falling RS lags.
Outcome: 6 did not hold across 6 variants.

### T-TWT-H09: Trade With Trend (Raunak A) · TWT-H09 50 DMA pullback in leaders
Claim before the run: Stock above a rising 50 DMA and above its 200 DMA, within 15% of its all-time high, RS line rising, low touched the 50 DMA in the last 3 sessions. Entries on a strong bullish candle (close in the top 30% of the bar, up on the day) after a pullback on volume below the 50-day average beat the same pullbacks bought without the volume and candle conditions, over 20 and 60 sessions.
Outcome: 1 had too little data to judge, 1 did not hold across 2 variants.

### T-TWT-H10: Trade With Trend (Raunak A) · TWT-H10 Don't chase: extension above the 50 DMA
Claim before the run: In uptrend stocks (above the 50 and 200 DMA, every 5th session), entries more than X% above the 50 DMA (X = 8, 10, 15, 25) earn less over 20 and 60 sessions than entries within 5% of it; at 15% the next-60-session drawdown is also deeper.
Outcome: 3 held up, weaker in one period, 3 had too little data to judge, 2 did not hold, 1 held up in both periods across 9 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| gt15 · minfwd60 | VALIDATED | -5.49% | -14.3 | -4.89% | -8.4 | 3.579 |
| gt8 · net20 | CONDITIONAL | -1.32% | -4.4 | -0.88% | -2.4 | 3.579 |
| gt10 · net20 | CONDITIONAL | -1.42% | -4.2 | -0.97% | -2.3 | 3.579 |
| gt15 · net20 | CONDITIONAL | -1.65% | -3.9 | -1.23% | -2.1 | 3.579 |

### T-TWT-H11: Trade With Trend (Raunak A) · TWT-H11 Breakouts on volume
Claim before the run: Breakouts on volume above X times the 50-day average (X = 1.0, 1.5, 2.0) earn more over 20 sessions than breakouts below it; at 1.5x they fail within 5 sessions less often.
Outcome: 3 came out the opposite way, 1 held up, weaker in one period across 4 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| vol1.5 · fail5 | CONDITIONAL | -3.24% | -3.0 | -9.99% | -7.9 | 3.579 |
| vol1.0 · net20 | OPPOSITE | -2.11% | -4.2 | -0.84% | -2.1 | 3.579 |
| vol2.0 · net20 | OPPOSITE | -1.93% | -5.7 | -0.60% | -1.8 | 3.579 |
| vol1.5 · net20 | OPPOSITE | -2.17% | -5.4 | -0.48% | -1.3 | 3.579 |

### T-TWT-H12: Trade With Trend (Raunak A) · TWT-H12 The breakout bar's shape
Claim before the run: Breakout bars that are the widest of the last 20 sessions, close in the top 25% of the bar and have an upper wick under 15% of the range earn more over 5/10/20 sessions and fail less often. Wide, high-volume (1.5x) bars with an upper wick of 40% or more earn less.
Outcome: 3 did not hold, 1 held up in both periods, 1 came out the opposite way across 5 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| good · fail5 | VALIDATED | -12.39% | -11.1 | -17.76% | -8.8 | 3.579 |
| good · net5 | OPPOSITE | -0.40% | -1.8 | -0.06% | -0.2 | 3.579 |

### T-TWT-H12F: Trade With Trend (Raunak A) · TWT-H12F Follow-up: do the good breakout bars pay later?
Claim before the run: H12's good breakout bars (widest of 20, close in the top 25%, upper wick under 15%) failed less in 5 days but did not earn more from the next open. Follow-up: counted from day 5 (once the 5-day failure is known), do they earn more over the next 20 and 60 sessions than other breakouts?
Outcome: 1 did not hold, 1 came out the opposite way across 2 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| good · p5net60 | OPPOSITE | -2.34% | -4.0 | -0.34% | -0.4 | 3.59 |

### T-TWT-H13: Trade With Trend (Raunak A) · TWT-H13 RS line at a high confirms the breakout
Claim before the run: Breakouts where the stock / Nifty 500 ratio is at (within 0.5% of) its 126-session high earn more over 20 and 60 sessions than breakouts where it is not.
Outcome: 2 did not hold across 2 variants.

### T-TWT-H14: Trade With Trend (Raunak A) · TWT-H14 RS new high before price
Claim before the run: Stocks whose RS line is at a 126-session high while the price is still more than 5% below its 52-week high beat the market's drift over 60 and 120 sessions.
Outcome: 2 did not hold across 2 variants.

### T-TWT-H15: Trade With Trend (Raunak A) · TWT-H15 Near highs beats far below
Claim before the run: Stocks within 5% of their 52-week high beat stocks 40%+ below it over 20, 60 and 120 sessions (every 5th session). Stocks 40%+ down and below the 200 DMA more often fall another 40% within 120 sessions.
Outcome: 2 came out the opposite way, 1 held up, weaker in one period, 1 did not hold across 4 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| deep · fall40 | CONDITIONAL | +4.15% | +3.3 | +8.95% | +3.9 | 3.579 |
| near · net20 | OPPOSITE | -1.87% | -2.7 | -1.52% | -2.1 | 3.579 |
| near · net60 | OPPOSITE | -2.67% | -1.7 | -0.63% | -0.3 | 3.579 |

### T-TWT-H17: Trade With Trend (Raunak A) · TWT-H17 Breakout follow-through
Claim before the run: Breakouts that close above the breakout close on each of days 1-3 and have above-average volume on at least 3 of the first 5 days earn more over the next 20 and 60 sessions, counted from day 5 (when the follow-through is known), than breakouts without it.
Outcome: 2 did not hold across 2 variants.

### T-TWT-H18: Trade With Trend (Raunak A) · TWT-H18 Quiet pullbacks after a breakout
Claim before the run: After a breakout, the first pullback of 3% from the post-breakout high (days 3-15): pullbacks on lower volume than the up-leg that hold the breakout level make a new high within 15 sessions more often than other pullbacks; pullbacks that retrace under 38.2% of the run do too.
Outcome: 2 held up in both periods across 2 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| shallow · newhigh15 | VALIDATED | +15.17% | +16.1 | +15.23% | +11.8 | 3.579 |
| quiet_hold · newhigh15 | VALIDATED | +9.96% | +14.5 | +10.87% | +9.5 | 3.579 |

### T-TWT-H18F: Trade With Trend (Raunak A) · TWT-H18F Follow-up: do quiet pullbacks pay?
Claim before the run: H18's quiet (lower volume, holding the breakout level) and shallow (under 38.2% of the run) pullbacks made new highs more often, partly because they start closer to the high. Follow-up: buying the next open after the pullback day, do they earn more over 5 and 20 sessions, net of costs, than other first pullbacks?
Outcome: 3 did not hold, 1 came out the opposite way across 4 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| shallow · net20 | OPPOSITE | -0.61% | -1.7 | -0.20% | -0.7 | 3.59 |

### T-TWT-H22: Trade With Trend (Raunak A) · TWT-H22 Staged stop -3/-5/-7 versus one -7% stop
Claim before the run: On breakout entries (next open), selling a third at -3%, a third at -5% and the rest at -7% beats a single -7% stop when every position is closed at the close of day 20 or 60 at the latest; also checked when breadth is under 40%. Baseline: a single -7% stop beats no stop (60 sessions).
Outcome: 2 did not hold, 1 came out the opposite way, 1 had too little data to judge across 4 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| single7_vs_none · hold60 | OPPOSITE | -2.04% | -1.7 | -2.25% | -1.6 | 3.579 |

### T-TWT-H23: Trade With Trend (Raunak A) · TWT-H23 Structure exits
Claim before the run: On breakout entries, an initial stop at the last confirmed swing low and an exit on the first close below the latest swing low (max 120 sessions) beats (a) a +15% target with a -7% stop and (b) a tight -3% stop held otherwise to 60 sessions.
Outcome: 2 did not hold across 2 variants.

### T-TWT-H24: Trade With Trend (Raunak A) · TWT-H24 Three-step exit for big winners
Claim before the run: For breakouts that reach +30% within a year: selling 30% at +40%, 35% on the first close below the 50 DMA and the rest below the latest swing low beats holding to day 250, and beats a full exit on the first close below the 50 DMA.
Outcome: 2 came out the opposite way across 2 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| vs_hold250 | OPPOSITE | -14.75% | -4.0 | -17.62% | -3.1 | 3.579 |
| vs_full_50dma | OPPOSITE | -2.40% | -3.6 | -1.35% | -1.4 | 3.579 |

### T-TWT-H26: Trade With Trend (Raunak A) · TWT-H26 During index pullbacks, sell weak losers
Claim before the run: While the Nifty is 3-10% below its 52-week high (every 5th session), stocks that are down over 60 sessions and lagging the Nifty 500 over 63 sessions earn less over the next 20 and 60 sessions than stocks that are up and leading, so selling the first group and keeping the second helps.
Outcome: 2 did not hold across 2 variants.

### T-TWT-H27: Trade With Trend (Raunak A) · TWT-H27 Stage 2 stocks
Claim before the run: Stage 2 (above a rising 150-day average, the daily stand-in for his 30-week MA, with higher highs and lows and a rising RS line) beats every other stock over 60 and 120 sessions (every 5th session). Breakouts from a 120-session range while in stage 2 beat other 120-session breakouts.
Outcome: 4 did not hold across 4 variants.

### T-TWT-H28: Trade With Trend (Raunak A) · TWT-H28 Correction leaders
Claim before the run: While the Nifty is 10%+ below its 52-week high (every 5th session), the top fifth of stocks by 63-session relative strength beat the bottom fifth over 60 and 120 sessions.
Outcome: 2 had too little data to judge across 2 variants.

### T-TWT-H29: Trade With Trend (Raunak A) · TWT-H29 Sectors that fall least lead the rebound
Claim before the run: While the Nifty is 10%+ below its 52-week high (every 5th session), the 3 sector indices closest to their own 52-week high beat the 3 furthest, against the Nifty 500, over 63 and 126 sessions.
Outcome: 2 had too little data to judge across 2 variants.

### T-TWT-H30: Trade With Trend (Raunak A) · TWT-H30 Swing-structure breadth
Claim before the run: When under 35% of the liquid 500 show higher highs and higher lows (20-session swings), the Nifty's next-21-session return is lower and its volatility higher than when over 60% do. Under 20% with the Nifty within 3% of its high flags deeper drawdowns over 63 sessions.
Outcome: 1 had too little data to judge, 1 came out the opposite way, 1 did not hold across 3 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| lt35 · nfwd21 | OPPOSITE | +2.41% | +2.3 | +2.33% | +2.0 | 3.579 |

### T-TWT-H31: Trade With Trend (Raunak A) · TWT-H31 New highs on thin breadth
Claim before the run: With the Nifty within 2% of its 52-week high, a 4%+ drawdown within 21 and 63 sessions is more likely when 50% or fewer stocks are above their 200 DMA than when 70% or more are.
Outcome: 2 had too little data to judge across 2 variants.

### T-TWT-H32: Trade With Trend (Raunak A) · TWT-H32 Short-term breadth damage, long-term intact
Claim before the run: Three versions, each against all other sessions, Nifty over 21 and 63 sessions: (v1) 50-DMA breadth down 20+ points in 10 sessions while 200-DMA breadth is down 10 or less; (v2) 50-DMA breadth 45% or less with 200-DMA breadth 65%+; (v3) the Nifty 4-6% off its high with 50-DMA breadth 55%+.
Outcome: 5 had too little data to judge, 1 did not hold across 6 variants.

### T-TWT-H33: Trade With Trend (Raunak A) · TWT-H33 Breadth washouts
Claim before the run: When 20% or fewer stocks are above their 200 DMA, or 11% or fewer above their 50 DMA, the Nifty's next 63/126/252 sessions beat all other sessions.
Outcome: 6 had too little data to judge across 6 variants.

### T-TWT-H35: Trade With Trend (Raunak A) · TWT-H35 Bear-market rallies fail near the 50 DMA
Claim before the run: With the Nifty below a falling 50 DMA and below its 200 DMA, the session it rallies to within 3% of the 50 DMA (from further below) is followed by lower 10 and 21 session returns than the market's drift.
Outcome: 2 had too little data to judge across 2 variants.

### T-TWT-H36: Trade With Trend (Raunak A) · TWT-H36 Deep below the 200 DMA
Claim before the run: Nifty closes 8-14% below its 200 DMA are followed by higher 21 and 63 session returns than other sessions; the 9-10% band by higher 63 and 126 session returns.
Outcome: 4 had too little data to judge across 4 variants.

### T-TWT-H37: Trade With Trend (Raunak A) · TWT-H37 India VIX spikes above 28
Claim before the run: Sessions with India VIX at 28 or more, and sessions within 10% of a VIX peak of 28+ in the last 5 sessions after it turned down 10%, are followed by higher Nifty returns than other sessions (21, 63, 252 and 21, 63 sessions).
Outcome: 5 had too little data to judge across 5 variants.

### T-TWT-H38: Trade With Trend (Raunak A) · TWT-H38 VIX waking up from low levels
Claim before the run: The Nifty's drawdown over the next 21 sessions is deeper (a) when VIX reaches 14+ after 15 sessions at 13 or less, (b) after a 30%+ weekly VIX jump, and (c) when VIX is above 17 rather than below 14.
Outcome: 3 had too little data to judge across 3 variants.

### T-TWT-H39: Trade With Trend (Raunak A) · TWT-H39 Small caps' turn
Claim before the run: When the Nifty Smallcap 100 / Nifty 100 ratio has risen over 40 sessions, or closes above its 50 DMA, the ratio keeps rising over the next 63 and 126 sessions.
Outcome: 2 had too little data to judge, 1 came out the opposite way, 1 did not hold across 4 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| above50 · slfwd63 | OPPOSITE | -3.13% | -2.2 | -0.21% | -0.1 | 3.579 |

### T-TWT-H40: Trade With Trend (Raunak A) · TWT-H40 Index contraction on a rising 50 DMA
Claim before the run: In an uptrend (Nifty above a rising 50 DMA), sessions with the 10-day average range under 70% of the 50-day average and the Nifty within 3% above its 50 DMA are followed by higher 10 and 21 session returns than other uptrend sessions.
Outcome: 2 had too little data to judge across 2 variants.

### T-TWT-H42: Trade With Trend (Raunak A) · TWT-H42 A strong dollar hurts the Nifty
Claim before the run: When the broad dollar index (the Fed's, from 2006; stand-in for DXY) is up 5%+ over 126 sessions, or breaks above its 3-year high, the Nifty's next 21 and 63 sessions are weaker than other sessions.
Outcome: 4 had too little data to judge across 4 variants.

### T-TWT-H43: Trade With Trend (Raunak A) · TWT-H43 Strong crude hurts the Nifty
Claim before the run: Brent above its 50 DMA, or at $100+, is followed by weaker Nifty returns over 21 and 63 sessions.
Outcome: 2 did not hold, 2 had too little data to judge across 4 variants.

### T-TWT-H44: Trade With Trend (Raunak A) · TWT-H44 US weakness leads the Nifty lower
Claim before the run: With the Nasdaq (stand-in: the lake's S&P 500 starts 2016) below its 50 DMA, or 10%+ below its 60-session high, the Nifty's next 21 and 63 sessions are weaker; in the 5 sessions after the Nasdaq reclaims its 50 DMA the Nifty's next 21 and 42 sessions are stronger.
Outcome: 3 did not hold, 2 had too little data to judge, 1 came out the opposite way across 6 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| below50 · nfwd21 | OPPOSITE | +2.08% | +2.3 | +1.63% | +1.5 | 3.579 |

### T-TWT-H46: Trade With Trend (Raunak A) · TWT-H46 Bank Nifty leads
Claim before the run: After a 3.5%+ weekly Bank Nifty gain the Nifty's next 21 sessions and the 200-DMA breadth over 21 sessions rise more than otherwise; with Bank Nifty above its 200 DMA the Nifty's next 21 and 63 sessions beat sessions when it is below.
Outcome: 3 did not hold, 1 had too little data to judge across 4 variants.

### T-TWT-H49: Trade With Trend (Raunak A) · TWT-H49 Stochastic pullback with filters
Claim before the run: Among Stochastic(15,3,3) dips with %K and %D both under 30, those with the close above the 100-day average and at most one wide-range down candle (range over 1.5 ATR, red) in the last 5 sessions earn more over 10 and 20 sessions.
Outcome: 2 came out the opposite way across 2 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| net10 | OPPOSITE | -0.55% | -1.7 | -0.53% | -2.9 | 3.579 |
| net20 | OPPOSITE | -1.15% | -2.2 | -1.10% | -2.3 | 3.579 |

### T-TWT-H50: Trade With Trend (Raunak A) · TWT-H50 Confirmed Heikin Ashi entries
Claim before the run: Entries on the second green Heikin Ashi candle after 3+ red ones (initiation plus confirmation) earn more over 10 and 20 sessions than entries on every red-to-green change.
Outcome: 2 did not hold across 2 variants.

### T-TWT-H51: Trade With Trend (Raunak A) · TWT-H51 Hidden bullish divergence
Claim before the run: In stocks above their 200 DMA, a confirmed higher swing low in price with a lower RSI(14) low at 35 or under beats the market drift of uptrend pullbacks (below the 20 DMA, every 5th session) over 5, 10 and 20 sessions.
Outcome: 3 had too little data to judge across 3 variants.

### T-TWT-H52: Trade With Trend (Raunak A) · TWT-H52 Ichimoku: all elements aligned
Claim before the run: Among closes above the cloud (first close above), those with Senkou A and B rising, Chikou above price and Tenkan and Kijun rising earn more over 10 and 20 sessions.
Outcome: 2 did not hold across 2 variants.

### T-TWT-H53: Trade With Trend (Raunak A) · TWT-H53 Weekly outside reversal bars
Claim before the run: A bullish weekly outside bar (high above and low below the prior week, close above the prior week's high) after a 10%+ fall over 8 weeks beats the market drift over 10 and 20 sessions; with the week's volume the highest in 52 weeks over 20 sessions; a bearish one after a 10%+ rise lags over 20.
Outcome: 2 had too little data to judge, 2 did not hold across 4 variants.

### T-TWT-H54: Trade With Trend (Raunak A) · TWT-H54 ADX trend pullback to the 20 EMA
Claim before the run: Buying the break of the high of a candle that touched the 20 EMA (entry next open) earns more over 10 and 20 sessions when ADX(14) was above 30 and rising with +DI above -DI than for any 20-EMA touch.
Outcome: 2 came out the opposite way across 2 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| net10 | OPPOSITE | -0.58% | -2.2 | -0.59% | -1.8 | 3.579 |
| net20 | OPPOSITE | -1.35% | -3.2 | -0.73% | -1.1 | 3.579 |

### T-TWT-H59: Trade With Trend (Raunak A) · TWT-H59 Opening outside yesterday's range
Claim before the run: Days the Nifty (and Bank Nifty) opens outside the prior day's high-low range have a bigger range (vs the 20-day average) and more often close further in the direction of the gap than days opening inside.
Outcome: 3 did not hold, 1 had too little data to judge across 4 variants.

## technical (3 studies)

### CP1: Candlestick patterns: do a hammer or a bullish engulfing after a fall, or a bearish engulfing or a doji after a rise, predict the next 5-20 sessions on liquid stocks?
Claim before the run: The classic reading: a hammer or a bullish engulfing candle after a decline marks a turn up (better returns ahead, worth buying at the next open); a bearish engulfing candle or a doji after a rise marks a turn down (worse returns ahead).
Outcome: 5 had too little data to judge, 3 did not hold across 8 variants.

### SR1: Support and resistance as an entry: does a bounce off support or a close through resistance give a buy call (and a close below support a sell call)?
Claim before the run: Buying a stock that touches its swing-low support and closes up within 1.5% above it, or that closes above its swing-high resistance, beats ordinary days over the next 20 sessions (and pays after costs); a close below support is followed by weaker returns; the same bounce and breakout on the Nifty and Bank Nifty are followed by better index returns.
Outcome: 9 did not hold, 2 came out the opposite way across 11 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| STK · break60 · net20 | OPPOSITE | -0.95% | -4.6 | -0.54% | -2.9 | 3.213 |
| STK · break20 · net20 | OPPOSITE | -1.08% | -4.3 | -0.49% | -2.0 | 3.213 |

### XO1: Moving-average and MACD crossovers, and averages converging: do they give a buy (or sell) call?
Claim before the run: After a 50/200 golden cross, a 20/50 upward cross or a MACD(12,26,9) upward signal-line cross, forward returns beat ordinary days (and the opposite crosses are followed by weaker returns); the 50-over-200 state is a better time to hold the index; when the 20, 50 and 200-day averages converge, a bigger move (either way) follows.
Outcome: 15 had too little data to judge, 9 did not hold, 3 came out the opposite way across 27 variants.

| variant | verdict | 2000-17 mean | t | 2018-23 mean | t | bar |
|---|---|---|---|---|---|---|
| STK · converge · abs20 | OPPOSITE | -1.29% | -2.8 | -0.95% | -2.9 | 3.113 |
| STK · gc · net60 | OPPOSITE | -2.74% | -2.6 | -2.75% | -2.2 | 3.113 |
| STK · x2050up · net20 | OPPOSITE | -0.74% | -2.1 | -0.54% | -1.2 | 3.113 |

## valuation (1 studies)

### VL1: Nifty valuation: does an expensive Nifty (high P/E or P/B, low dividend yield) come before weaker returns, and a cheap one before better returns?
Claim before the run: When the Nifty 50's P/E or P/B is in the top tenth of its own history (or its dividend yield in the bottom tenth), the next 60 and 250 sessions are weaker than other times; when it is cheap (bottom-tenth P/E, top-tenth yield) they are better.
Outcome: 6 had too little data to judge across 6 variants.
