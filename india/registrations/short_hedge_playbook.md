# The short and hedge playbook (Phase 3.2 of the 29 Oct 2026 plan)

What Ananta knows about the down side, in one place, from its own registered tests (2000-2023, nothing from 2024 on), and what it does with it. HISTORICAL BACKTEST evidence; paper only; never advice. Nothing here changes a pinned rule (change control until Phase 7); where a rule already exists it is named.

## 1. What the tests found

| question | study | verdict | the number |
|---|---|---|---|
| Short Nifty futures equal to the basket when the Nifty is below its 200-day | HG1 | return REJECTED, worst-20 INCONCLUSIVE | protects most (worst 20 sessions -44% -> -32% in 2003-17, -41% -> -16% in 2018-23) but costs 1.1-1.7% a quarter; growth 11.0% -> 5.6% a year in 2018-23 |
| 20% more cash when the Nifty is below its 200-day | HG1 | worst-20 CONDITIONAL, return REJECTED | the worst stretch 0.66% shallower a quarter at a cost of 0.2-0.4% a quarter; the only hedge that earned its place, and it is small |
| A monthly 5%-out-of-the-money Nifty put | HG1, F06 | REJECTED | helped only in 2018-23 (drawdown -55% -> -39%); always-on puts cost more than they saved over 2003-17 |
| Buying puts to protect the 10-slot paper books | F06 | REJECTED (12 variants) | the premium is the measured cost; no book was better off |
| A stock falling 2%+ while already below its 200-day, next session | RX1 | CONDITIONAL | 0.18% (2000-17) and 0.12% (2018-23) worse than the average stock, open to close; 20-session paper trial running since 28 Oct (avoid / exit, never a short book) |
| Shorting that stock at the open, intraday | RX1 | descriptive | about +0.36% after a 0.10% cost, of which about 0.22% is the ordinary open-to-close drift; fills at the open assumed |
| Buying a stock more than 20% above its 50-day or up 25% in 20 sessions | E04 | VALIDATED (no-entry filter) | 2-3% less over 20 sessions: "don't chase" |
| Buying at RSI over 70 | P01 | VALIDATED the other way | 1.5-1.9% less over 20 sessions |
| Bottom momentum decile, monthly | FP1 | CONDITIONAL (expected way) | the losers keep losing 5-7% a year: falling knives are not bargains |
| The low-volatility decile, monthly | FP1 | REJECTED as a return claim | the same return as the universe with a third of the drawdown: the cheapest "hedge" is owning calmer names |
| Selling expiry-day premium with bought wings | DR1 | REJECTED / OPPOSITE | the decay is real (naked +11-13% of premium in 2018-23) but the wings and four legs of friction eat it |
| Short option structures three sessions before expiry | DR1 control | lost in both periods | short premium without expiry-day decay is a steady loss after costs |

## 2. What Ananta does on the down side today (rules in force)
- **Cash by regime** (allocation rule v1, pinned, 23 Oct): cash floor 5% above both averages, 10% mixed, 20% below both; options cap 35% / 30% / 20%, 20% while unproven. This is HG1's cash20 in rule form; the regime today is below both.
- **Survival limits** (paper config, pinned, 19 Oct): 5% a day, a pause at 22% drawdown (on paper everything keeps running and is logged both ways).
- **Fixed first stops** on every stock trade (the exit book: 2 ATR; E01/E02), the only exit family that held up.
- **No chasing**: the E04 saturation filter and the RSI>70 result are proven and not yet in the paper rules (map class C, on the one-yes list for Phase 7).
- **RX1 avoid/exit** on stocks falling 2%+ under their 200-day: in a 20-session paper trial, scored nightly; a yes only after the trial.

## 3. What Ananta does not do, and why
- **No short stock book.** Shorting is intraday-only in Indian cash; the measured edge (+0.36% with open fills, mostly drift) is below realistic slippage on a market-open short.
- **No always-on puts.** Rejected twice (F06, HG1). A put is a cost, bought for a reason, not a policy.
- **No futures hedge by default.** It protects the most and costs the most (half the growth in 2018-23); one Nifty lot is about Rs 15 lakh of notional, far beyond the book. If a hedge is ever added it is the cash rule, already in force.
- **No premium selling at the sleeve's size.** DR1: the affordable version does not pay.

## 4. Open items (the staircase)
1. RX1 20-session trial (started 28 Oct) -> a yes or a no on the avoid/exit rule.
2. The no-chase filters (E04, RSI>70) into the paper rules: Madhav's one yes at Phase 7.
3. A hedge tested on the real paper slots, not the 250-name proxy basket, once the books have 60+ sessions.
4. For the long-term money (Phase 5): the low-volatility or combined tilt as the paper twin's candidate, judged on drawdown as much as return.

Sources: hg1_results_v1.md, f06 rows in ledger_results.md, rx1_results_v1.md, exit_policy_book.md, conditions results (E04, P01) in ledger_results.md, fp1_results_v1.md, dr1_results_v1.md, allocation_rule_v1.json, paper_config.json.
