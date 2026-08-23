# North Star Lock — 2026-08-22

**Status:** Locked. Destination is refined. Current sprint extended by Market Truth lock (same day).

Build the observable intelligence first. Build the autonomous authority later.

**Operating philosophy:** Aggressive on paper. Ruthless on measurement. Conservative on promotion. Aggressive on **development**. Conservative on **promotion**.

**Evidence philosophy (locked):** Ananta regime is a **hypothesis**. Market measurements + forward price are the external reference. Agent must never learn "Ananta was correct because Ananta said so."

Full Market Truth detail: [MARKET_TRUTH_LOCK.md](./MARKET_TRUTH_LOCK.md).

---

## Destination (not full autonomy this sprint)

One platform, three jobs, one trust ladder:

```text
LEARN → UNDERSTAND → PRACTICE → DECIDE → EXECUTE
  → PAPER → LIVE WITH CONFIRMATION
  → CONSTRAINED AUTONOMY → AUTONOMOUS CAPITAL
```

**A. Trading intelligence** — personalized TAKE/SKIP/WAIT, not generic signals.
**B. Trading OS** — natural-language control of Ananta (and later honest API adapters).
**C. Autonomous operator** — allocated capital only after evidence.

Closed loop (non-circular):

```text
USER INTENT → Agent (understand) → Ananta System Truth (Contract)
  + Independent Market Truth
  → DECISION (TAKE/SKIP/WAIT/HOLD/EXIT) → EXECUTION
  → OUTCOME Truth (forward path, opportunity cost)
  → LEDGERS → REGIME AUDIT + DECISION AUDIT
  → LEARNING (eval + ranking + experiment proposals only)
  → TRUST → PERMISSION
```

Moat is the loop, not the LLM. Missing data = UNKNOWN, never "no setup."

Strategy feedback into Ananta design is first-class, **human-gated**:

```text
finding → hypothesis → experiment → lab/paper → human approval → versioned production
```

---

## Confirmed 1–6 (hard)

1. Vision is destination. Sprint stays Wave A + Contract truth + evidence engine (Market Truth Stages 1–5).
2. First user is still this lab (personal proof). Education product is later. Agent is the student; market + marks are the teachers.
3. **No automatic production-strategy mutation.** Eval and ranking may update. Hunter/squeeze/bollinger-mr code does not mutate from a losing week. Mutation only via: observation → hypothesis → experiment → paper/backtest → eval → validation → **human** promotion.
4. Two surfaces later. **CLI is the lab until ledgers cannot lie.** No UI rewrite now.
5. Portfolio veto is later — after real TAKE evidence, not empty WAITs.
6. $50 live test only after shadow → virtual treasury → written criteria → evidence → human approval.

---

## Architecture law

```text
Agent → Shared Contract / API → Ananta → DB / market / execution
```

Ananta owns **System** facts. Market Truth is computed from **independent observables** (and historical candles), not from Ananta's regime field as proof. Agent owns intelligence. No Agent→Mongo. No UI scrape.

Three truths stay distinct: **System | Market | Outcome**.

Policy/risk sits **outside** the LLM. Implemented: `src/intelligence/gates.py`. Profiles cannot override Ananta.

---

## Current sprint

**Wave A:** hunter, squeeze, bollinger-mr. Do not add a strategy unless instructed.
All three stay **WATCH** until TAKE evidence exists. WAIT-only marks ≠ KEEP.

**Knowledge law:** Implementation + router are authoritative. DNA is thesis, not live policy. Contradictions are first-class. Three confidences stay separate: understanding / evidence / decision. Historical Lab = `source=BACKTEST`. Paper = `source=PAPER`. Matrix 2026-07-26 = `source=MATRIX`. Never mix into KEEP.

| P / Stage | Job | Status |
|-----------|-----|--------|
| **P0** | Prove ~1y 1h candles in Mongo Lab/API reads | **Done** |
| **P1** | Wave A Strategy Knowledge Object | **Done** |
| **P2** | Lab 1y evidence `source=BACKTEST` | **Done** |
| **S1** | `lab watch` + independent market snapshot + Observation | **Done** |
| **S2** | Forward outcomes +15m / +1h / +4h | **Done** |
| **S3** | Regime Audit + Decision Audit (thin) | **Done** (overnight sample = evidence, not KEEP/CUT) |
| **S4** | Same schema on 1y historical replay | **Done** (`lab replay` / `lab audit replay` — TAKE-eq ≠ KEEP) |
| **Compare** | Live vs historical, same schema, do not mix | **Done** (`lab compare` 2026-08-23) |
| **S5** | Findings → experiment proposals (human-gated) | **Parked** — tape accumulating; ledger exists; not executing |
| **DI** | Typed decisions, profiles, gates, orchestration | **Foundation now** — Wave A still WATCH; extra agents still not |
| P3–P7 | Per-symbol marks, paper density, KEEP only with TAKE evidence | Ongoing ops |

Lab ops: `cycle` / `lab watch` → ledgers → `mark` → `evaluate` → `wavea` → audits.
Knowledge: `understand` / `lab understanding`. History: `lab coverage` / `lab replay` / `lab audit replay` / `lab compare`.

Definition of done: the Agent can repeatedly observe System + Market truth, decide, record why, observe Outcome truth, evaluate honestly (including opportunity cost), rank without inventing evidence, and **propose** experiments without deploying them.

Not done because: commands work, text looks smart, one green trade, `evaluate` says SUPPORTED, paper equity ticks up, or Ananta regime matched itself.

---

## Explicitly not now

Extra agents, cloning, autonomous wallets, live autonomy, $50 live, public leaderboard, education product, Vercel/UI rewrite, Agent→Mongo, multi-broker, India/US/CA adapters, unrestricted self-modification, automatic production mutation, Agent cockpit, ML training on thin data, TradingAgents integration / Bull-Bear nodes / provider zoo.

Decision Intelligence foundation is **in tree** (typed deliberation, profiles, hard gates). Extra agents (Bull/Bear, TradingAgents integration, provider zoo) remain **not now**. Destination lock: [DECISION_INTELLIGENCE_LOCK.md](./DECISION_INTELLIGENCE_LOCK.md).

Learning allowed now: evaluation + ranking + structured experiment proposals. Production mutation: never automatic.
