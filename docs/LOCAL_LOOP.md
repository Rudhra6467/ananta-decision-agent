# Agent Ananta — Local loop (no website)

**Updated:** 2026-08-20  
**Why this exists:** Emergent hosting expired. Agent development must not depend on the Ananta frontend.

The test that matters:

```text
You: sell ARB 1.0
Agent: Intent SELL / Asset ARB / Qty 1.0 / Mode PAPER → confirmation required
You: yes
Agent → POST /api/orders/manual
Ananta backend → DB
Order created → decision / opportunity / cycle ledgers updated
Agent receives structured result
```

That is a better test of Agent Ananta than clicking around the UI.

---

## Architecture (locked)

```text
Agent Ananta
    │  Contract v0
    ▼
Ananta Backend   (FastAPI, independently runnable)
    ├── Database (MongoDB)     — facts, positions, orders, fills
    ├── Strategies             — registry + enable/disable
    └── Execution              — paper orders, cycles
```

Clients of the same backend:

| Client | Role |
|--------|------|
| Agent Ananta CLI | Primary lab client **right now** |
| Tests / curl | Contract verification |
| Ananta UI | Optional later — not required for Wave A / ledgers |

**Never:** `Agent → PostgreSQL/Mongo` as the production path.  
**Never:** skip `/api/auth/login` to “just write the tables.”

Direct DB writes are allowed only as **test fixtures** (e.g. seed `ARB` quantity), after which the agent still goes through the API.

---

## Inspection result (2026-08-20)

Both repos are intact.

### Ananta (`Rudhra6467/Ananta`)

| Piece | Location |
|-------|----------|
| Backend entry | `backend/server.py` → FastAPI `app` |
| Start | `cd backend && uvicorn server:app --host 0.0.0.0 --port 8001 --workers 1` |
| Health | `GET /health` and `GET /api/` |
| Auth | `backend/auth.py` — owner JWT via `POST /api/auth/login` |
| Database | MongoDB (`MONGO_URL`, `DB_NAME`) |
| Paper order | `POST /api/orders/manual` |
| Portfolio | `GET /api/portfolio` |
| Trades | `GET /api/trades` |
| Strategy registry | `GET /api/strategy/registry` |
| Strategy profile | `GET/PUT /api/strategy/{key}/profile` |
| Cycle | `POST /api/cycle/run` and `POST /api/cycle/run/{symbol}` |
| Frontend | `frontend/` — **not required** for this phase |

`--workers 1` is mandatory (in-process trading loops).

### Agent Ananta (`Rudhra6467/ananta-decision-agent`)

| Piece | Location |
|-------|----------|
| Ananta client | `src/tools/ananta_api.py` |
| Login | `login()` → `POST {ANANTA_BASE_URL}/api/auth/login` |
| Paper order | `place_manual_paper_order()` → `POST /api/orders/manual` |
| CLI buy/sell/cycle | `src/cli_exec.py` |
| Contract | `docs/AGENT_CONTRACT_V0.md` |
| Decision ledger | `src/tools/decision_log.py` → `decision_log.json` |
| Cycle / opportunity ledgers | `src/tools/cycle_log.py` → `cycle_log.jsonl`, `opportunity_log.jsonl` |

Current default `ANANTA_BASE_URL` is `https://livetrading247.com` (dead hosted site). Point it at the local backend.

---

## Decision: Option A unless A fails

### A — Run existing Ananta backend locally (preferred)

Ananta backend code is intact. There is no reason to rebuild it.

1. Start Ananta backend locally (see Ananta `docs/LOCAL_BACKEND.md`).
2. Set Agent env:

```bash
ANANTA_BASE_URL=http://127.0.0.1:8001
ANANTA_EMAIL=<OWNER_EMAIL>
ANANTA_PASSWORD=<OWNER_PASSWORD>
```

3. From Agent CLI, prove the loop:

```text
status
monitor
sell ARB 1.0
yes
```

4. Verify:

```text
positions / portfolio
orders / trades
fills
decision ledger
opportunity ledger
cycle ledger
```

### B — Direct database (fixtures only)

Seed a position in Mongo (e.g. ARB = 10), then have the agent call `SELL ARB 1.0` through the API. Do not make this the architecture.

### C — Contract-faithful local harness (fallback)

Only if the real backend cannot start. Expose the same contract the agent already calls:

```text
POST /api/auth/login
GET  /api/portfolio
GET  /api/strategy/registry
GET  /api/strategy/{key}/profile
PUT  /api/strategy/{key}/profile
POST /api/orders/manual
GET  /api/trades
POST /api/cycle/run
```

A harness is a stand-in for Ananta, not a second trading engine.

---

## What this phase is testing

If the goal is:

> Does Agent Ananta correctly create/update/read decision and opportunity data?

then the website is irrelevant. Test:

```text
Agent → structured request → backend → database → structured response
```

from the command line.

---

## Explicitly out of scope until 3.6 is green

- Redeploying the React app
- Vercel / Railway / Render **for the sake of the agent**
- Agent cockpit UI
- Bypassing JWT
- Writing ledgers into Ananta Mongo from the agent without an API
- India adapters, live money, autonomy
