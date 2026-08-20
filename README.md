# Agent Ananta

AI decision / co-pilot layer for the [Ananta](https://github.com/Rudhra6467/Ananta) trading system.

Ananta owns **truth** (market, portfolio, strategies, orders, fills).  
Agent Ananta owns **interpretation, ranking, decisions, explanation, and learning**.

Built with LangGraph. Paper mode only until a Trust Report exists.

## Current phase (2026-08-20)

Wave A + Contract v0 + Phase 4 ledgers.

Emergent hosting is expired. **Do not depend on the Ananta website.** Run the Ananta **backend** locally and point this agent at it.

```text
Agent Ananta  →  Contract/API  →  Ananta backend  →  DB / strategies / execution
```

The UI is just another client of the same backend. See [docs/LOCAL_LOOP.md](docs/LOCAL_LOOP.md) and [docs/ROADMAP.md](docs/ROADMAP.md).

## Local lab loop

1. Start Ananta backend (Ananta repo: `docs/LOCAL_BACKEND.md`).
2. Copy `.env.example` → `.env` and set:

```text
ANANTA_BASE_URL=http://127.0.0.1:8001
ANANTA_EMAIL=...
ANANTA_PASSWORD=...
```

3. Run the agent CLI (see `main.py`). Prove:

```text
status → monitor → sell ARB 1.0 → yes
```

4. Check portfolio/trades **and** local ledgers (`decision_log.json`, `cycle_log.jsonl`, `opportunity_log.jsonl`).

Do not bypass login. Do not write Mongo from the agent.

## Docs

| Doc | Purpose |
|-----|---------|
| [docs/ROADMAP.md](docs/ROADMAP.md) | Locked roadmap |
| [docs/LOCAL_LOOP.md](docs/LOCAL_LOOP.md) | Backend-first operating mode |
| [docs/AGENT_CONTRACT_V0.md](docs/AGENT_CONTRACT_V0.md) | Shared contract with Ananta |
| [docs/LABORATORY_CHARTER.md](docs/LABORATORY_CHARTER.md) | Lab rules |
| [AGENTS.md](AGENTS.md) | Operating contract for coding agents |
