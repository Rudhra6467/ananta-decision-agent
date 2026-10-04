# Research audit v1: every analysis of the prototype, rated and ranked

Written 2026-10-04, before any new test was run on the 120-coin lake. The rubric below was fixed first; the ratings were then
applied to the inventory (`audit_v1.json`, 164 rows: reviews, studies, variables, hypotheses, setups, strategies, policies, queue).
Rows are rated on what their own records say, quoting their own numbers. No new numbers were produced for this audit.

## 1. Evidence score (0-10, one point table for every row)

| Point | Rule |
|---|---|
| +2 | Pass rule written before the run (pre-registered) |
| +2 | Costs included (NDAX fee + half-spread) |
| +2 | Looked at two separate periods (2017/18-2023 discovery, 2024-26 confirm) |
| +1 | A sealed holdout or fresh coins were used |
| +2 / +1 | At least 30 / 10-29 independent events (episodes, not overlapping trades) |
| +1 | Low risk of hindsight or future data leaking in |

The score says how far the result can be trusted, not whether it was good.

## 2. Ratings

| Rating | Meaning | What happens to it |
|---|---|---|
| **KEEP** | Passed its own written test after costs in both periods, or is a lesson confirmed three or more times by different analyses | Stays in use; re-confirmed on the lake as part of a normal review |
| **RE-TEST** | Promising, passed on thin data (10 coins, few events), or never properly tested and testable on the lake | Gets a pre-registered review on the 120-coin lake (#15, #16, ...) |
| **CONTEXT** | Not a trading edge, but explains something (a baseline, a method check, a risk rule, a live queue) | Kept as reference; never sold as an edge |
| **DUMP** | Failed its own pre-written test, only "worked" in hindsight, was superseded, or left no numbers | Not carried forward; the reason is kept so it is not rediscovered |
| **UNTESTED** | An idea that was never measured | Queued (data is free) or parked (needs outside data) |

Rules that decide close calls:
- A variant of a family that failed is not re-tested separately (fewer forks = fewer lucky passes). Only the family's
  pre-registered representative goes to the lake.
- "Worked in 2018-23, failed 2024-26" is DUMP unless the reason is understood and testable.
- A result that depends on its 10 best trades for most of its profit is DUMP as a strategy and CONTEXT as a lesson.
- Anything rated RE-TEST keeps its original pass rule; the lake can only confirm or reject, never re-tune.

## 3. Re-test queue on the lake (order fixed now)

1. **Review #15** (already pre-registered): T3, H07 (+H06 family), Madhav's reads M1a/M2a/M3a/M2a-G.
2. **Review #16, zones:** do SWING-NEW, AVERAGE-200 and CONFLUENCE zones still hold more often than the random-walk
   corrected baseline on 120 coins, and does F6 (market allowed) still separate held from broken?
3. **Review #17, coin choice:** H08 relative strength vs BTC and H16 market breadth (daily), as filters on T3 / H07.
4. **Review #18, exits:** H14 structural stops vs tight stops on H07 and T3 trades; V03 crash bells on 120 coins
   (the delisted coins - LUNA, FTT and others - matter most here).
5. **Review #19, cheap new variables:** U03 taker buy share (already in our candles), then U01/U02 funding and open
   interest (free Binance futures files).
6. **Last:** E3 support bounce (1h) and the B3 volume breakout (daily), both thin and low priority.

The ledger (`audit_v1.json`) holds every row with its rating, score and one-line reason.
