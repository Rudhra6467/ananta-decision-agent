# Agent Ananta — Locked Roadmap

**Locked:** 2026-08-17  
**Operating-mode addendum:** 2026-08-20  
**North-star confirmation:** 2026-08-22 — [NORTH_STAR_LOCK.md](./NORTH_STAR_LOCK.md)  
**Strategy intelligence audit:** 2026-08-22 — [STRATEGY_INTEL_AUDIT.md](./STRATEGY_INTEL_AUDIT.md)  
**Market Truth + continuous evidence:** 2026-08-22 — [MARKET_TRUTH_LOCK.md](./MARKET_TRUTH_LOCK.md)

**Immediate (locked):** P0–P2 **done**. Next engineering = **Stage 1** (`lab watch` + independent Market Truth snapshot + co-timestamped Observation). Then S2 forward outcomes → S3 audits → S4 1y replay → S5 experiment proposals. Wave A stays hunter/squeeze/bollinger-mr **WATCH**. Do not rank the other 12. Do not ML-train yet.

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
| 4 | Decision Intelligence Infrastructure | Done enough — ledgers + wavea + audit |
| 4.5 | Market Truth + Observation schema | **Next — Stage 1** |
| 5 | Agent decision evaluation | In progress — WAIT ≠ KEEP; need TAKE + outcome audits |
| 6 | Engine + strategy validation (incl. regime audit) | Starts after S1–S3 |
| 7 | Research + PDF intelligence | Not started |
| 8 | User intelligence + personalization | Not started |
| 9 | Personalized paper closed loop | Not started |
| 10 | Trust report | Not started |
| 11 | Human-confirmed live | Not started |
| 12 | Agent cockpit | Not started |
| 13–16 | Monitoring, management, autonomy, learning | Not started |
| 17 | India adapters | Gate: after Trust + Personal Proof |

---

## Market Truth stages (2026-08-22)

| Stage | Deliverable |
|-------|-------------|
| **S1** | `lab watch --interval N` (5–15m) + market snapshot + Ananta cycle + decision → Observation |
| **S2** | Forward attach +15m / +1h / +4h |
| **S3** | Regime Audit + Decision Audit (SUPPORTED / MISCLASSIFIED / UNCERTAIN; opportunity cost) |
| **S4** | Same schema replayed on 1y Lab data |
| **S5** | Findings → experiment proposals; human approval mandatory |

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
4. **S1 — continuous Observation** (`lab watch` + Market Truth snapshot)
5. Wave A paper density + honest marks while observer runs
6. S2–S5 without expanding strategy universe or auto-mutation

Next meaningful milestone:

> Can Wave A + Contract + Market Truth Observations produce an auditable dataset showing what Ananta thought, what the market did, what the Agent decided, and what happened afterward — without Ananta grading itself?

**Do not start yet:** extra agents, fancy UI, autonomy, India, education, $50 live, leaderboard, large strategy expansion, ML training, automatic production mutation.
