# Ananta Agent — Lab Docs

Observability and operating docs for the paper-trading laboratory.

| Doc | Purpose |
|-----|---------|
| [NORTH_STAR_LOCK.md](./NORTH_STAR_LOCK.md) | Destination + sprint laws |
| [MARKET_TRUTH_LOCK.md](./MARKET_TRUTH_LOCK.md) | Independent Market Truth, lab watch, audits, experiment path |
| [STAGE4_REPLAY_LOCK.md](./STAGE4_REPLAY_LOCK.md) | 1y historical observation_v0 replay; not KEEP |
| [LIVE_VS_HISTORICAL_COMPARE.md](./LIVE_VS_HISTORICAL_COMPARE.md) | **Now** — live vs 1y, same schema, not KEEP |
| [DECISION_INTELLIGENCE_LOCK.md](./DECISION_INTELLIGENCE_LOCK.md) | **NEXT** — typed deliberation after evidence |
| [TRADINGAGENTS_REFERENCE_AUDIT.md](./TRADINGAGENTS_REFERENCE_AUDIT.md) | Tauric TradingAgents KEEP/ADAPT/REJECT; not a clone |
| [ROADMAP.md](./ROADMAP.md) | Locked product roadmap + stages S1–S5 |
| [STRATEGY_INTEL_AUDIT.md](./STRATEGY_INTEL_AUDIT.md) | What the Agent knows vs Ananta |
| [LOCAL_LOOP.md](./LOCAL_LOOP.md) | Backend-first lab loop — **no website required** |
| [AGENT_CONTRACT_V0.md](./AGENT_CONTRACT_V0.md) | Shared truth language with Ananta |
| [LABORATORY_CHARTER.md](./LABORATORY_CHARTER.md) | Hard rules: limits, ritual, kill/promotion criteria |
| [SCOREBOARD.md](./SCOREBOARD.md) | Strategy status TEST/WATCH/CORE/CUT/PARK |
| [experiments/JOURNAL.md](./experiments/JOURNAL.md) | Session-by-session log |

## Start of every lab day

1. Confirm Ananta **backend** is reachable (`ANANTA_BASE_URL`). Do not wait on the website.
2. Read charter limits (slots ≤ 6 preferred, enabled ≤ 5).
3. `git pull` + run agent.
4. Prefer `lab watch` (when available) over manual `cycle` spam; still mark and review audits. Stage 4: `lab replay` then `lab audit replay` in a third terminal — do not stop the watcher.
5. `monitor` → `status` → ledgers → `evaluate` / `wavea`.
6. Update JOURNAL + SCOREBOARD before closing the laptop.

If login fails, the backend is down or `ANANTA_BASE_URL` still points at the expired Emergent host. Fix the API, not the UI. See [LOCAL_LOOP.md](./LOCAL_LOOP.md).

## Roadmap phase map (short)

- **Phase 1–2:** Agent foundation + lab operability — done / nearly done
- **Phase 3:** Wave A discovery — current
- **Phase 3.5–3.6:** Contract v0 + local backend — done
- **Phase 4:** Decision ledgers — done enough to run
- **Phase 4.5:** Market Truth + continuous Observation — S1–S4 done; **compare now** (`lab compare`)
- **Phase 5+:** Evaluation, Trust Report, cockpit, India — gated

Do not start extra agents, fancy UI, autonomy, or India until Observations can show System + Market + Outcome without Ananta grading itself.
