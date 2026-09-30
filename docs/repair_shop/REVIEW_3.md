# Repair-shop review #3: buy weakness (pre-registration)

Written 2026-09-30 **before** any run.
- **Hypothesis**, from review #2's D2 (traders' long entries, 2024–26): buying weakness beats buying strength over the next day.
- **Test data:** our own 5m history, **2017–2023 (DISCOVERY)**, which the trader data never touched. 2024–July 2026 is reported as **in-sample** (it produced the idea). The Aug–Sep 2026 holdout is not loaded.

## New setups (engine; off in v0, so the live Explorer is unchanged)

| ID | Fires at a 15-minute scan when |
|---|---|
| E6 | 15m RSI < 30 |
| E7 | 1h RSI < 40 **and** 4h trend DOWN |
| E8 | daily close below its EMA50 **and** momentum percentile ≤ 0.30 |

- Entry: a limit at the scan close, resting 2 hours.
- Type: always SHORT_TERM (5-day cap). The review #2 effect was measured at 24h to 5 days.
- Exits: disaster stop (2 × ATR 1h), target (nearest resistance or +2R), time cap. The warning bells are off (x3 = False), because the SHORT_TERM warning "1h close below EMA50" would exit every dip trade at once.
- The random-entry baseline in each run uses the same rules.

## Variants (4, all reported)

| ID | Setups |
|---|---|
| R3a | E6 |
| R3b | E7 |
| R3c | E8 |
| R3all | E6 + E7 + E8 |

## Pass rule (DISCOVERY only)

A variant passes if:
1. its mean net per trade is **> $0**;
2. it beats the random SHORT_TERM entries of the same run by Welch t ≥ 2;
3. it beats C0 (v0) DISCOVERY mean net (−$0.38) by Welch t ≥ 2.

A passing variant becomes a **paper shadow** in the live Explorer. It is promoted only with the operator's approval (R4).
