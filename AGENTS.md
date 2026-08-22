# Agent Ananta — Operating Contract

Load this when working on Agent Ananta code, lab decisions, ranking, or roadmap.

## North star

Ananta provides the truth. Agent Ananta understands the trader, turns truth into personalized decisions, directs Ananta to execute, measures results (including SKIPs), learns, and earns autonomy through evidence.

## Laws

1. **Facts vs interpretation** — Ananta = facts; Agent = decisions. Never invent facts Ananta did not provide.
2. **Experiment aggressively. Commit conservatively.** Promote only with evidence.
3. **Feature filter** — Improves intent → decision → execution → outcome → learning? Else defer.
4. **Co-design** — If the Agent needs a sense, improve Ananta exposure via the shared contract.
5. **Autonomy is earned** — Observe → Explain → Recommend → Paper → Confirm live → Constrained auto → Expanded auto.
6. **Backend is the contract host** — The UI is a client, not a dependency. Talk to Ananta through the API. Never Agent → database as architecture. Never skip auth.

## Wave A lab

- Strategies: hunter, squeeze, bollinger-mr
- Enabled ~3–4 (max 5); slots ≤ 5–6; at 6 slots do not enable new
- Prefer ★on under load or SKIP/WAIT
- Mark by results first (good/bad/neutral)

## Contract

See `docs/AGENT_CONTRACT_V0.md`. `agent_api_version = 0`.

Live HTTP the agent uses: `/api/auth/login`, `/api/portfolio`, `/api/orders/manual`, `/api/trades`, `/api/strategy/registry`, `/api/strategy/{key}/profile`, `/api/cycle/run`.

## Ledgers

- `decision_log.json` — decision memory + marks
- `cycle_log.jsonl` — cycle provenance
- `opportunity_log.jsonl` — candidates + TAKE/SKIP choices

## Current mission

**Phase 3.6 done (2026-08-21):** local Ananta backend independently runnable; Agent pointed at `ANANTA_BASE_URL=http://127.0.0.1:8001`. Current: Wave A evidence + Contract v0 + cycle/decision/opportunity/outcome logging.

See `docs/LOCAL_LOOP.md`.

No extra agents, no India, no autonomy, no UI cockpit, no Vercel-for-the-agent until ledgers exist on a live API.
