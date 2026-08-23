# Stage 4 Lock — Historical Observation Replay — 2026-08-23

**Status:** Locked and implemented. Extension of [MARKET_TRUTH_LOCK.md](./MARKET_TRUTH_LOCK.md). Not a restart.

Live paper observations stay **first-class**. 1y historical replay is a **second evidence layer on the same schema**, not a replacement.

---

## S3 overnight sample (locked interpretation)

43 observations, 39 with +1h, **0 TAKEs**, 19 SKIP, 24 WAIT.  
Regime: 6 SUPPORTED / 9 MISCLASSIFIED / 28 UNCERTAIN.  
Decision: 17 PROTECTIVE / 4 COSTLY / 22 UNCERTAIN.  
Mean BTC +1h after sit-out: −0.2415%.

This is **evidence, not a strategy verdict**.

```text
Hunter       → WATCH
Squeeze      → WATCH
Bollinger-MR → WATCH
```

No KEEP, no CUT, no Hunter v1.1 from one night. Stored hypothesis: BTC market label may lag rapid overnight transitions; SKIP still avoided the drop. Need 1y replay before blaming Hunter.

---

## Parallel tracks (do not serialize)

```text
Live laboratory                         Development
lab watch 15                            S4 1y replay (same observation_v0)
  → collect observations                  → lab replay / lab audit replay
  → periodic lab outcomes                 → compare live vs historical
  → periodic lab audit                    → S5 versioned experiment proposals
                                          → human approval
```

Do not wait for days of live data before developing. Do not stop the watcher to develop.

---

## Schema (same as live)

`observation_v0` in `observation_replay.jsonl` (`source=historical_lab`).

Never write historical rows into `observation_log.jsonl`.

Fields: timestamp, symbol, strategy, Ananta regime (hypothesis), decision, setup, skip/wait/take reason, strategy state, +15m/+1h/+4h, independent market truth, laws.

---

## Implementations (must be Ananta, not a second evaluator)

| Piece | Function |
|-------|----------|
| Regime | `regime.classify_regime` |
| Hunter | `primary_layer.evaluate_primary` |
| Squeeze | `squeeze.evaluate_squeeze` |
| Bollinger-MR | `declarative_engine.evaluate(DECLARATIVE['bollinger-mr'])` |
| Gates | Wave A allow-list; router recorded separately |

Evaluate **then** filter (live cycle observation contract). Backtest-only TAKE logs are not this.

---

## TAKE / SKIP / WAIT

| Decision | Meaning in historical replay |
|----------|------------------------------|
| TAKE | TAKE-**equivalent**: setup detected AND Wave A regime gate passes. Not a paper fill. |
| SKIP | Setup detected, filtered (usually `REGIME_FILTERED`) |
| WAIT | Model ran, no qualifying setup |
| UNKNOWN | Data gap — never treat as no-setup |

Historical TAKE ≠ live paper TAKE ≠ KEEP.

---

## Evidence layers (must stay separate)

```text
Market Truth          → Regime Classification Quality
Strategy Signal       → Strategy Quality
Agent Decision        → Decision Quality
Execution             → Execution Quality
Outcome               → Economic Result
```

Invalid:

```text
Ananta said BULL, Kraken said BEAR, BTC dropped, therefore Hunter is bad
SKIP, BTC dropped, therefore Hunter is good
```

A bad regime label can coexist with a good decision. Overnight data showed that. Keep it explicit.

Knowledge Object layers also stay separate:

```text
thesis ≠ implementation ≠ router/gates ≠ historical evidence ≠ paper evidence
```

Three confidences: understanding / evidence / decision. Never blended.

---

## Promotion law

```text
enough information to evaluate  ≠  enough evidence to promote
```

1y dataset may be enough to **evaluate** Hunter. It does not automatically KEEP Hunter. A few good paper trades do not KEEP either.

Mutation path only:

```text
finding → HYPOTHESIS (PROPOSED) → EXPERIMENT → RESULT → EVALUATION
  → HUMAN APPROVAL → PROMOTE / REJECT
```

Never rewrite production strategy logic from S4 output.

---

## Acceptance (S4 is not done merely because the job ran)

1. Same `observation_v0` schema.
2. Historical candles cover the intended period (`usable_1y` on coverage).
3. Strategy implementations are the real Ananta functions.
4. Regime classification recorded (asset + BTC market label).
5. Strategy decisions recorded per Wave A model.
6. SKIP / WAIT / TAKE remain distinct.
7. +15m / +1h / +4h reproducible from subsequent candles (15m omitted if series absent).
8. Independent market truth comparable to live flags.
9. Results stored (`observation_replay.jsonl`, `audit_report_replay.json`).
10. Historical evidence cannot silently become KEEP / WATCH / CUT.
11. Strategy evidence and decision evidence remain separate.

---

## Commands

```text
lab replay                 # BTC/USD, stride=4, writes observation_replay.jsonl
lab replay BTC/USD ETH/USD
lab replay --smoke         # short sanity, not a 1y claim
lab audit replay           # same auditor, historical file
lab understanding          # Strategy Understanding Report seed
```

Ananta: `GET /api/lab/observation-replay` (owner JWT, spawn process pool).

---

## Explicitly not now

ML training, extra agents, UI/cockpit, $50 live, India adapters, Agent→Mongo, auto KEEP, enabling the other 12, auto-rewrite of Hunter/Squeeze/Bollinger-MR.
