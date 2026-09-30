# Repair-shop review #2: learning from other traders' trades (pre-registration)

Written 2026-09-30 **before** any of the analysis below was run.

- **Question:** where did real traders enter that our rules miss, and does their entry context carry information we can use?
- **Data:** the Hyperliquid benchmark (`hl_bench.sqlite`): public fills of 65 accounts, sampled at random by stratum with a fixed seed. Strata: leaderboard winners / middle / losers, random live-tape wallets, and public vaults. Fills run from September 2024 to September 2026.
- **Law kept:** external trades are **reference, never teacher**. Nothing here copies a trader or creates a signal directly. Anything learned becomes a *candidate rule* that must pass our own tests.

## Clean split (why this design is honest)

| Period | Use |
|---|---|
| Sept 2024 – July 2026 (our CONFIRM era) | **learn**: their entries + our context at those moments |
| 2017 – 2023 (our DISCOVERY era, no Hyperliquid trades exist) | **test**: candidate rules replayed through our engine |
| Aug – Sept 2026 | holdout: **not used** (their entries after 2026-08-01 are dropped) |

## Steps

**S1. Context table.**
- Replay our engine (rules C0) over the 5m history. At every 15-minute scan, save the full state (S1, S2, S3, 4h trend, daily vs EMA50, BTC S1/S2, RSI 15m/1h, momentum percentile, contraction, 1h volume ratio, green-run count, in-support, hour) and which setups fired.

**S2. Their entries.**
- Round trips (flat → flat) on the 10 coins, entered before 2026-08-01.
- An account whose median hold is under 10 minutes, or that trades more than 200 round trips a week, is a market maker / HFT: excluded and counted.
- Each entry is joined to the **last scan at or before** its entry time (no lookahead).

**S3. Forward outcome, independent of their exit.**
- Price move after each entry at 1h, 4h, 24h and 5 days, from our 5m data. It is signed by direction (a long gains when the price rises).
- **Excess** = that move minus the average move of the same coin over all 5m bars of the same calendar month. That removes market drift, the review #1 lesson.
- t-statistics cluster by account-day.

**S4. Analyses (all reported).**

| ID | Analysis |
|---|---|
| D1 | Is there information in their timing? Mean excess of their entries (longs, shorts), all accounts and by stratum. |
| D1b | Skill without survivorship: rank accounts by the net of their **first half** of trades and take the top third. Their **second-half** entries show whether skill persists. |
| D2 | Winners vs losers: for their long trades, the win rate and excess by each context value. |
| D3 | Coverage: share of their long entries (all, and winning) where any of our setups fired in the 2 hours before, and the context where they bought while we did nothing. |
| D4 | Candidate contexts: single context values or pairs where **long** entries of the D1b skilled group (second half) have 24h **or** 5-day excess > 0 with t ≥ 3 and n ≥ 150. At most the **top 5 by t** become candidate rules. |

**S5. Test of the candidate rules (a follow-up run, pre-registered here).**
- Each candidate becomes a setup `E6..E10`: "in context K at a scan, buy with a limit at the scan close; trade types and exits as v0".
- Each is replayed alone on DISCOVERY (2017–2023).
- **Pass:** its mean net per trade beats the random-entry baseline of the same trade type with Welch t ≥ 2, and it beats C0's mean net.
- CONFIRM is reported but labelled in-sample, because the context came from that era.

If D1 and D1b show **no** information in their timing, S5 is not run. The review then reports that these traders' entries carry nothing our context doesn't already have.
