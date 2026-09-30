# Study v4 results: BTC market filter on fresh set #2

Pre-registration: `docs/research/STUDY_V4.md` (commit ae0faf3, plus Amendment 1, an engineering-only fix).
Run once on fresh set #2 at 2026-09-30 ~09:36 UTC (`run_done.json` marker written). The fresh10 run is a reference, not evidence.
Sizing: $100 per coin, fixed $100 per trade (no compounding). Drawdown is measured against starting capital.

## Verdict: no variant passes. Nothing goes to paper as a new candidate.

Fresh set #2: 12 coins, 2019 to 2026, including delisted coins. Results at NDAX costs:

| Variant | Trades | Total return | Max drawdown vs start | Worst 12-month start | Eras (to 2021 / 2022–23 / 2024 on) | Fails |
|---|---|---|---|---|---|---|
| V1_CONTROL | 734 | +535% | 88% | −42% (2021Q4) | +550 / −18 / +3 | drawdown, worst 12m |
| V4A_BTC_GATE | 637 | +544% | 75% | −26% (2021Q4) | +544 / −6 / +6 | drawdown, worst 12m |
| V4B_BTC_GATE_EXIT | 664 | +541% | 87% | −27% (2021Q4) | +529 / −1 / +12 | drawdown, worst 12m |
| V4C_HOLD_BTC_GATE | 415 | +843% | 335% | −165% (2021Q2) | +869 / −3 / −23 | drawdown, worst 12m, eras |

At Kraken T1 costs every row is worse, and V1_CONTROL also fails the eras check.
The fresh10 reference tells the same story: all variants fail on drawdown (94–112%) and worst 12-month start (−40% to −52%, 2025Q1).

## Post-hoc checks (not part of the pass rule)

These checks explain **why** the variants fail.

- **Concentration.** On fresh2, the 10 best trades out of about 650 make 85% of the profit. Without them, the whole run earns about $950 on $1,200 over 7 years. On fresh10, the 10 best trades are 91–106% of the profit.
- **Per year.** 2021 alone is about $5,700 of the $6,500 total on fresh2. 2022, 2023, 2025 and 2026 are all negative.
- **Starting on 2025-01-01.** On fresh2, the losses since then are −19% (V4B) to −25% (control) of starting capital. On fresh10 they are −39% to −61%.
- **The BTC gate helps, consistently.** On both sets it lowers drawdown and the worst 12-month loss, and it cuts about 12% of trades. It is a real improvement, but far from enough.

## What this means

After four studies (MTF v1, entry v2, candidate v3, study v4), this family of strategies shows the same pattern. The family is trend entries on alt coins with daily-trend exits at real costs. Its profit comes from a few huge wins in a bull market (2020–21). In the years between, it loses slowly and steadily.

A live start today would most likely begin in a losing stretch. This study does not support live trading of any V-family variant.

The V1_RIDE paper book keeps running. It is cheap evidence about the current market, and it shows whether live behaviour matches the backtest.

Every variant is counted. With v4, 4 variants were tested on fresh set #2, and fresh set #2 is now used up.
