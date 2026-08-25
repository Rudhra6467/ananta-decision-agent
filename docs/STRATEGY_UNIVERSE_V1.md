# Strategy Research Universe v1 — 2026-08-25

**Status:** Offline research track. **v1.1** adds evidence depth. Wave A **frozen**.  
**CLI:** `lab universe`  
**Knowledge file:** `universe_knowledge.json` (local; not a live enable list)  
**Destination:** [STRATEGY_EVIDENCE_ENGINE.md](./STRATEGY_EVIDENCE_ENGINE.md)

## What this is

A generated **strategy × asset × timeframe × regime** matrix from specifications.

Not a farm of bots. Not live watch. Not KEEP.

```text
specs → cells → historical_lab replay → DQ-v0 cells
     → SUITABLE / UNSUITABLE / UNKNOWN
     → Strategy Knowledge Base (research)
```

## What this is not

- No new strategy on `lab watch`
- No Hunter rewrite
- No TREND_UP enable
- No KEEP
- No automatic promotion
- DNA `confidence=87` is **not** evidence

## Coverage v1

Replay we actually have: Wave A (`hunter`, `squeeze`, `bollinger-mr`) × `BTC/USD` × `1h` × Ananta regimes.

Everything else is **catalogued** and scored `UNKNOWN / NO_OBSERVATION_REPLAY` until an `observation_v0` stream exists for that cell.

## Fit rules (evidence only)

| TAKE +1h (DQ-v0) | Fit | status_class |
|---|---|---|
| No observation_v0 | UNKNOWN | UNTESTED |
| n < 30 / no sample | UNKNOWN | TESTED_UNKNOWN |
| WASH (\|mean\| < 0.25%) | UNKNOWN | WASH |
| TAKE_HURT | UNSUITABLE | UNSUITABLE |
| TAKE_HELPED | SUITABLE | SUITABLE |

UNTESTED ≠ TESTED_UNKNOWN ≠ WASH. WASH is not UNSUITABLE.  
**SUITABLE is not KEEP. SUITABLE is not live.**

Policy is stored separately: `ALLOWED` (Wave A) / `ROUTER_ONLY` / `THESIS_ONLY` / `UNMAPPED`. A cell can be evidence-UNSUITABLE in an ALLOWED regime, or UNKNOWN in TREND_UP. That is the Hunter contradiction, documented — not a rewrite ticket.

## Parallel tracks

```text
lab watch 15          Wave A live baseline (do not contaminate)
lab universe          Offline cells vs observation_replay.jsonl
```

Additional live days of Wave A are valuable evidence. They are **not** a blocker for this track.

## Destination

Market Truth → Market State → **this knowledge base** → ranking → DI → TAKE/WAIT/SKIP → Ananta hard gates → Outcome Truth → DQ → update knowledge.

Universe v1 only starts the knowledge base. It does not give the agent authority to pick strategies live.
