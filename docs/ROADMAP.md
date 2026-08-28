# Agent Ananta — Locked Roadmap

**Locked:** 2026-08-17  
**Operating-mode addendum:** 2026-08-20  
**North-star confirmation:** 2026-08-22 — [NORTH_STAR_LOCK.md](./NORTH_STAR_LOCK.md)  
**Strategy intelligence audit:** 2026-08-22 — [STRATEGY_INTEL_AUDIT.md](./STRATEGY_INTEL_AUDIT.md)  
**Opportunity Engine addendum:** 2026-08-28 — [OPPORTUNITY_ENGINE_LOCK.md](./OPPORTUNITY_ENGINE_LOCK.md) (mapped, not running)

**Immediate (locked):** P0–P2 **done**. S1–S4 **done**. Compare **done**. H3 **measurement done**. DQ-v0 **locked**. Universe v1.3.1 + fingerprints + memory **done**. Opportunity Engine **interface only**. H1 live enable rejected. Wave A stays **WATCH**. Live watch continues. Extra agents still not.

**North star:** Ananta provides System Truth. Independent Market Truth is the external reference. Agent Ananta understands the trader and the strategies, decides, measures Outcome Truth (including SKIPs and opportunity cost), learns (evaluation + ranking + proposals only), and earns autonomy through evidence — without a self-confirming loop.

**Philosophy:** Aggressive on paper. Ruthless on measurement. Conservative on promotion.  
**Evidence law:** Ananta regime = hypothesis. Ananta output is never proof Ananta was correct.

**Feature filter:** Does this improve user intent → informed decision → execution → outcome → learning? If no, defer.

This file does **not** reopen education, adapters, $50 live, cockpit, or leaderboard.

---

## Status board

| Phase | Objective | Status |
|-------|-----------|--------|
| 0 | Architecture + product lock | Locked (2026-08-22 + Market Truth) |
| 1 | Agent foundation | Done |
| 2 | Lab operability | Nearly done |
| 3 | Wave A discovery | Current — paper + continuous observer |
| 3.5 | Shared contract v0 | Proven locally |
| 3.6 | Backend independence (local Ananta API) | **Done 2026-08-21** |
| 4 | Decision Intelligence Infrastructure | **Foundation now** — typed decisions, profiles, gates |
| 4.5 | Market Truth + Observation schema | **S1–S4 + compare done**; live watch continues |
| 5 | Agent decision evaluation | **DQ-v0.0 locked 2026-08-25** — `lab quality`; WAIT ≠ KEEP |
| 6 | Engine + strategy validation (incl. regime audit) | S1–S3 done; KEEP still gated |
| 7 | Research + PDF intelligence | Research workflow scaffold (`lab research`); PDF later |
| 8 | User intelligence + personalization | Intent + profiles scaffold; personalization later |
| 9 | Personalized paper closed loop | Not started (paper-sim exists, no fills) |
| 10 | Trust report | Not started |
| 11 | Human-confirmed live | Not started |
| 12 | Agent cockpit | Not started — CLI is the lab |
| 13 | Monitoring | Scaffold — `lab system` |
| 14 | Management | Scaffold — profiles + intent |
| 15 | Autonomy | Scaffold — orchestrate + gates; not live |
| 16 | Learning | Proposals only |
| 17 | India adapters | Gate: after Trust + Personal Proof |

---

## Market Truth stages (2026-08-22)

| Stage | Deliverable | Status |
|-------|-------------|--------|
| **S1** | `lab watch --interval N` (5–15m) + market snapshot + Ananta cycle + decision → Observation | **Done** |
| **S2** | Forward attach +15m / +1h / +4h | **Done** |
| **S3** | Regime Audit + Decision Audit (SUPPORTED / MISCLASSIFIED / UNCERTAIN; opportunity cost) | **Done** (not a KEEP/CUT verdict) |
| **S4** | Same schema replayed on 1y Lab data | **Done** — `lab replay` / `lab audit replay` |
| **Compare** | Live vs historical (`lab compare`) | **Done** — reviewed 2026-08-23, not KEEP |
| **S5** | Findings → experiment proposals; human approval mandatory | **H3 measurement done**; H2 pending instrumentation; H1 live enable rejected — [S5_HYPOTHESES.md](./S5_HYPOTHESES.md) |
| **DQ** | Decision Quality meter (TAKE/WAIT/SKIP, per strategy, live vs hist) | **v0.0 locked 2026-08-25** — [DECISION_QUALITY_V0.md](./DECISION_QUALITY_V0.md) `lab quality` |
| **DI** | Typed decisions, profiles, hard gates, paper-sim | **Foundation now** — [DECISION_INTELLIGENCE_LOCK.md](./DECISION_INTELLIGENCE_LOCK.md) |

Same schema for live paper and historical replay. No second parallel evidence system.

---

## Operating mode (2026-08-20)

Emergent hosting expired. Lab runs on local Ananta backend + Mongo Atlas.

```text
Agent Ananta → Contract/API → Ananta Backend → DB / market / execution
```

UI is just another client. Never Agent→Mongo as architecture.

See [LOCAL_LOOP.md](./LOCAL_LOOP.md).

---

## Wave A constraints

- Set: `hunter`, `squeeze`, `bollinger-mr`
- All three WATCH until TAKE evidence exists
- Enabled prefer 3 (max 5)
- Slots prefer ≤ 5–6; at 6 → no new enables
- Result-first marks: good / bad / neutral; WAIT/SKIP ≠ KEEP
- Production strategy code is immutable to the Agent; proposals only

---

## Current mission

1. ~~P0 1y candles~~ **Done**
2. ~~P1 Knowledge Object~~ **Done**
3. ~~P2 Lab BACKTEST file~~ **Done** (mixed symbol results; not KEEP)
4. ~~S4 1y historical Observation replay~~ **Done** (`lab replay` + `lab audit replay`; TAKE-eq ≠ KEEP)
5. Live watcher continues (`lab watch 15`) as a parallel evidence stream
6. ~~live vs historical compare~~ **Done** (`lab compare` 2026-08-23)
7. **H3 done** (`lab attribution`). **DQ-v0.0 locked** (`lab quality`). **H2 done** (`lab h2`). H1 live enable rejected. Wave A WATCH **frozen**.
8. **Universe v1.2** — continuation hist shadow. **Setup Memory v0** — `lab memory`. Wave A frozen.

Next meaningful milestone:

> Setup-memory query (`lab memory replay`). Fingerprints next. Similarity only after TAKE n is real.

**Do not start yet:** extra agents, Bull/Bear, TradingAgents integration, fancy UI, live autonomy, India, education, $50 live, leaderboard, putting the other 12 on live watch, ML training, automatic production mutation, H1 TREND_UP enable, chart-similarity search, blended 81/100 scores.
