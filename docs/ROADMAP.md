# Agent Ananta — Locked Roadmap

**Locked:** 2026-08-17  
**Operating-mode addendum:** 2026-08-20  
**North star:** Ananta provides the truth. Agent Ananta understands the trader, turns truth into personalized decisions, directs Ananta to execute, measures results (including SKIPs), learns, and earns autonomy through evidence.

**Philosophy:** Experiment aggressively. Commit conservatively. Promote only with evidence.

**Feature filter:** Does this improve user intent → informed decision → execution → outcome → learning? If no, defer.

This addendum does **not** reopen the product roadmap. It records how we run the current phases after Emergent hosting expired.

---

## Status board

| Phase | Objective | Status |
|-------|-----------|--------|
| 0 | Architecture + product lock | Locked by principles |
| 1 | Agent foundation | Done |
| 2 | Lab operability | Nearly done |
| 3 | Wave A discovery | Current — local API live; gather marks |
| 3.5 | Shared contract v0 | Proven locally (auth, portfolio, paper order, enable, cycle) |
| 3.6 | Backend independence (local Ananta API) | **Done 2026-08-21** — localhost:8001 + Mongo Atlas |
| 4 | Decision Intelligence Infrastructure | Done enough to run — ledgers + wavea + audit |
| 5 | Agent decision evaluation | Started — `evaluate` (process vs outcome, evidence label) |
| 6 | Engine + strategy validation | Not started |
| 7 | Research + PDF intelligence | Not started |
| 8 | User intelligence + personalization | Not started |
| 9 | Personalized paper closed loop | Not started |
| 10 | Trust report | Not started |
| 11 | Human-confirmed live | Not started |
| 12 | Agent cockpit | Not started |
| 13–16 | Monitoring, management, autonomy, learning | Not started |
| 17 | India adapters | Gate: after Trust + Personal Proof |

---

## Operating mode (2026-08-20)

Emergent was hosting Ananta. That account is expired. The agent login failure is the expected chain:

```text
Agent Ananta → Ananta auth/API → Ananta backend → [backend unavailable] → Login failed
```

The website is **not** a dependency for Wave A, Contract v0, or Phase 4 ledgers.

Keep this architecture:

```text
                Agent Ananta
                     │
                     │ Contract
                     ▼
              Ananta Backend
                     │
          ┌──────────┼──────────┐
          ▼          ▼          ▼
       Database   Strategies   Execution
```

Treat the UI as just another client:

```text
                   Ananta Backend
                  /       |       \
                 /        |        \
                ▼         ▼         ▼
             Ananta    Agent     Tests/CLI
               UI      Ananta
```

The agent does not care whether the backend is Emergent, localhost, Vercel, Railway, or AWS. It cares about the **contract**.

### Options for the current phase

| Option | When | Use? |
|--------|------|------|
| **A. Run the existing Ananta backend locally** | Backend code is intact (it is) | **Preferred** |
| **B. Talk directly to the database** | Test fixtures only (seed a position, then hit the API) | Fixtures only — never production architecture |
| **C. Local contract-faithful test backend** | Only if A cannot start | Fallback |

**Do not:**

- Launch the Ananta website / Vercel frontend just so the agent has a host
- Bypass authentication and write from Agent Ananta into production-style tables
- Make `Agent → MongoDB` the architecture
- Start Automaton, live autonomy, India adapters, or an agent cockpit

Production boundary stays:

```text
Agent → Contract/API → Ananta backend → DB
```

See [LOCAL_LOOP.md](./LOCAL_LOOP.md).

---

## Wave A constraints

- Set: `hunter`, `squeeze`, `bollinger-mr`
- Enabled prefer 3–4 (max 5)
- Slots prefer ≤ 5–6; at 6 → no new enables
- Result-first marks: good / bad / neutral
- Exit: KEEP / WATCH / CUT with documented evidence

---

## Current mission

1. ~~Make Ananta backend independently runnable locally (Phase 3.6)~~ **Done 2026-08-21**
2. ~~Point Agent Ananta at that backend via `ANANTA_BASE_URL`~~ **Done**
3. Keep proving Contract v0 over the live API (auth → portfolio → paper order → ledgers)
4. Resume Wave A evidence (`hunter`, `squeeze`, `bollinger-mr`)
5. Cycle logger → decision ledger → opportunity ledger → outcome linkage

The next meaningful milestone is still:

> Can Wave A + Contract + ledgers produce a durable, auditable dataset showing exactly what Agent Ananta decided, what it skipped, why, and what happened afterward?

Phase 3.6 is complete. Do not reopen hosting/UI work.

**Do not start yet:** extra agents, fancy UI, autonomy, India, large strategy expansion, Vercel-for-the-agent.
