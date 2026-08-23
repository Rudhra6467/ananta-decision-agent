# Live vs Historical compare

**Date:** 2026-08-23  
**Command:** `lab compare` — **ran**. n_live=54 (+1h=50), n_hist=2474 (+1h=2474)  
**Status:** Reviewed as evidence. **Not KEEP. S5 = proposed only (see [S5_HYPOTHESES.md](./S5_HYPOTHESES.md)).**

Two files, same `observation_v0`, **do not mix**:

| | Live | Historical |
|---|---|---|
| File | `observation_log.jsonl` | `observation_replay.jsonl` |
| Source | `live_paper` | `historical_lab` |
| Clock | 15m ticks, ~10 symbols | BTC 1h, stride=4, 420.6d |
| TAKE | paper / agent take | TAKE-equivalent (setup AND Wave A gate) |
| n | **54** (50 with +1h) | **2474** (all with +1h) |

## `lab compare` (authoritative snapshot)

| | Live | Historical 1y BTC |
|---|---|---|
| Decisions | SKIP 19 / WAIT 35 / **TAKE 0** | WAIT 2206 / SKIP 213 / TAKE-eq **55** |
| Regime MIS / SUP | 9 (16.7%) / 9 (16.7%) | 633 (25.6%) / 931 (37.6%) |
| Sit-out COSTLY vs PROTECTIVE | 7 vs 17 | 315 vs 319 |
| Mean BTC +1h after SKIP/WAIT | **−0.116%** | **−0.007%** |
| Mean BTC +1h after TAKE | none | −0.056% (mostly bollinger-mr) |
| Hunter | 538 no-setup + **2 TREND_UP REGIME_FILTERED** (those are the only live setups) | 2366 WAIT, 108 setups, **104 filtered**, **4 TAKE-eq** |
| Squeeze | 490 REGIME_FILTERED / 50 no-setup / **0 setups** | 10 setups, 4 TAKE-eq, COMPRESSION |
| Bollinger-mr | **47 setups, all SKIP**; 490 REGIME_FILTERED | 158 setups, 111 filtered, **47 TAKE-eq** |

Live hunter's 2 setups used skip reason `REGIME_FILTERED regime=TREND_UP allowed=['REVERSAL']`. Same contradiction as 1y, now on the live tape.

Live squeeze/bollinger REGIME_FILTERED ≈ 490 of ~540 symbol-ticks: overnight book was not COMPRESSION/RANGE. Expected on a BULL/NEUTRAL tape.

## Findings (locked — still not experiments)

1. Hunter fires in **TREND_UP**; Wave A allows **REVERSAL only**. Live 2/2 setups and hist 85/108 setups were TREND_UP filtered.
2. Hunter is almost **silent in REVERSAL** (4 TAKE-eq, stride=4). Tight where allowed, noisy where forbidden.
3. Squeeze is rare and **aligned**. Live window: no squeeze setups.
4. Bollinger-MR **dominates hist TAKE-eq (47/55)** and produced 47 live SKIPs. Still shadow. Router RANGE=[].
5. Sit-out +1h is a **1y wash**; live window still slightly protective as ticks accrued (−0.24% → −0.116%). Neither promotes.
6. MISCLASSIFIED 17% live vs 26% hist = slow EMA market label vs fast 1h flags. Do not convict `classify_regime` from that.

## Forbidden

Hunter v1.1, KEEP/CUT, extra agents, TradingAgents clone, treating TAKE-eq as paper PnL, enabling TREND_UP without a versioned experiment + human approval.
