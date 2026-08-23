# Live vs Historical compare (first pass)

**Date:** 2026-08-23  
**Command:** `lab compare` (recomputes from local jsonl)  
**Status:** Evidence. **Not KEEP. Not S5 yet.**

Two files, same `observation_v0`, **do not mix**:

| | Live | Historical |
|---|---|---|
| File | `observation_log.jsonl` | `observation_replay.jsonl` |
| Source | `live_paper` | `historical_lab` |
| Clock | ~15m ticks, multi-symbol | BTC 1h, stride=4, 420.6d |
| TAKE | paper / agent take | TAKE-equivalent (setup AND Wave A gate) |
| n (first run) | 43–52 ticks | 2474 bars, +1h complete |

## First-pass numbers (from `lab audit` + `lab replay` / `lab audit replay`)

| | Live overnight | Historical 1y BTC |
|---|---|---|
| Decisions | SKIP 19 / WAIT 24 / **TAKE 0** | WAIT 2206 / SKIP 213 / TAKE-eq **55** |
| Regime MISCLASSIFIED | 9/43 (~21%) | 633/2474 (~26%) |
| Regime SUPPORTED | 6/43 | 931/2474 |
| Sit-out COSTLY vs PROTECTIVE | 4 vs 17 | 315 vs 319 |
| Mean BTC +1h after SKIP/WAIT | −0.24% | −0.007% |
| Mean BTC +1h after TAKE | n/a (0 TAKEs) | −0.056% (mostly bollinger-mr) |
| Hunter | ~no_setup dominant; 2 REGIME_FILTERED | 108 setups, **104 REGIME_FILTERED**, **4 TAKE-eq** |
| Squeeze | scarce | 10 setups, 4 TAKE-eq, COMPRESSION-aligned |
| Bollinger-mr | shadow | 158 setups, **47 TAKE-eq** (dominates hist TAKEs) |

These tables are **not commensurate**. Live hunter skip totals are per-symbol flattened. Historical TAKE is not a fill.

## What survives as findings (not experiments)

1. Hunter generates setups in **TREND_UP**; Wave A/router allow **REVERSAL only**. 85 of 108 hist setups were TREND_UP filtered. Measured, not DNA folklore.
2. Hunter is almost **silent in allowed REVERSAL** (4 TAKE-eq on stride=4). Gates look tight where permitted, noisy where forbidden.
3. Squeeze is rare and **aligned**. Scarcity is the fact.
4. Bollinger-MR is a **Wave A re-test / shadow**. Do not read 47 TAKE-eq as Wave A working. Router still has RANGE=[].
5. Sit-out +1h is a **wash at 1y**; overnight live window was slightly protective. Neither promotes.
6. ~20–26% MISCLASSIFIED is **slow EMA market label vs fast 1h flags** on both clocks. Do not convict `classify_regime` from that alone.

## What is forbidden from this compare

- Hunter v1.1 / auto-rewrite
- KEEP / CUT / enable the other 12
- Extra agents, TradingAgents clone
- Treating hist TAKE-eq as paper PnL
- Opening S5 experiments without human review of this compare

## Next

```text
lab compare          (on the laptop, both files present)
  → review findings
  → S5 proposed experiments only
  → human approval
  → Wave A WATCH
```

Decision Intelligence (typed deliberation, counter-thesis) is **NEXT after** this evidence layer, not this sprint. See [DECISION_INTELLIGENCE_LOCK.md](./DECISION_INTELLIGENCE_LOCK.md).
