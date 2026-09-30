# Study v3 on fresh coins: results

- Run once: 2026-09-30T02:38:41Z. The marker prevents a rerun.
- Pre-registration: `STUDY_V3_FRESH.md` (9dfd5a4).
- Data: 10 fresh coins, 2019-01 → 2026-08-31, about 7M 5m bars.
  - Data check: on-grid, no duplicates; gaps are Binance maintenance only.

## By the pre-registered rules (NDAX costs)

| Variant | Book return | Max DD (vs peak equity) | MAR | E1 ≤2021 | E2 2022–23 | E3 2024– | Trades | Verdict |
|---|---|---|---|---|---|---|---|---|
| Buy & hold | +327% | 88% | 3.7 | +1022% | −58% | −11% | – | benchmark |
| V0 candidate (v2) | +62% | 37% | 1.7 | +118% | −14% | −13% | 2,117 | FAIL |
| **V1 ride** | +285% | 25% | **11.5** | +270% | −0.8% | +4.9% | 707 | **PASS** |
| V2 adaptive | +282% | 25% | 11.2 | +272% | −1.8% | +4.4% | 787 | PASS |
| V3 trend hold | +316% | 29% | 11.0 | +324% | +4.4% | −6.1% | 393 | PASS |

- The same three pass at Kraken Tier 1 costs.
- The lab-10 in-sample reference (not evidence) shows the same pattern. All four meet the rules there.
- **By the rules, V1_RIDE (highest MAR) becomes the paper proposal.**
- The v2 candidate has now failed twice: the holdout and the fresh coins.

## What the rules did not show (found in post-hoc checks, disclosed here)

1. **Fat-tailed and concentrated.**
   - Win rate 23%; average win $37 vs average loss $6.
   - The top 10 of 707 trades produced 106% of all profit. Without them the result is −$178.
   - All 10 coins were net positive.
2. **Profits come from mega-trend years.**

   | Year | V1 net (entry-year basis) |
   |---|---|
   | 2020 | +$1,737 |
   | 2021 | +$958 |
   | 2022 | −$210 |
   | 2023 | +$87 |
   | 2024 | +$893 |
   | 2025 | **−$521** |
   | 2026 YTD | **−$88** |

3. **Flaw in the pre-registered drawdown rule.**
   - The book trades a fixed $100 per coin, with no compounding.
   - Measuring drawdown as a % of peak equity understates the pain after early profits inflate that peak.
   - Against the $1,000 base, V1's worst drawdown was **$1,123 (112% of starting capital)**, Dec 2024 → Aug 2026.
   - **Starting fresh on 2025-01-01 with $1,000, V1 ended at −$609 (−61%)**, with a worst drawdown of $680.
   - V2 and V3 look the same (−$579, −$580).
   - Future pre-registrations must measure drawdown against starting capital, and include fresh-start windows.
4. **Survivorship.** The fresh coins were chosen as today's well-known survivors. Coins that died are missing, which flatters any long strategy.

## Reading

- Trend-following on these rules is real on unseen coins. It avoided most of the 2022 crash (−1% vs −58% for holding) and captured the 2020–21 and 2024 rallies.
- **Its recent 20 months were a heavy losing streak.** In choppy markets, about 110 trades a year at a 23% win rate bleed capital.
- **Not fit for live money now.** Forward paper is the right next evidence.
- Sizing must change before any live use: smaller slots, or fewer coins, relative to capital.
- A market-level on/off filter (trade only when the broad market trend is up) is the obvious v4 idea. It needs unseen data: another fresh coin set, or forward paper.
