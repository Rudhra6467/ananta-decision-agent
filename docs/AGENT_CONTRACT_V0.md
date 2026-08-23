# Ananta ↔ Agent Ananta Contract v0

**Version:** `agent_api_version = 0`  
**Status:** Minimum shared truth (both repos)  
**Updated:** 2026-08-20 (HTTP surface + backend-first note)  
**Rule:** If Agent Ananta reasons on a fact, Ananta must expose it explicitly. No hidden assumptions. No duplicate truth.

Canonical copy also lives in `Rudhra6467/Ananta` → `docs/AGENT_CONTRACT_V0.md`.

---

## Ownership

| System | Owns |
|--------|------|
| **Ananta** | Market data, portfolio, strategy state, orders, fills, exits, risk controls, telemetry, actual outcomes |
| **Agent Ananta** | User understanding, interpretation, ranking, recommendations, decisions, explanation, evaluation, learning |

Agent must never become a second hidden trading engine.

The **backend** is the contract host. The Ananta UI is one client. Agent Ananta is another. Tests/CLI are a third. Hosting provider (Emergent, localhost, Railway, Vercel) is not part of the contract.

---

## Decision vocabulary (stable)

`TAKE` · `SKIP` · `HOLD` · `EXIT` · `REDUCE`

CLI/enable actions also use: `ENABLE` · `DISABLE` · `WAIT`

## Strategy lifecycle (stable)

`CANDIDATE` · `WATCH` · `PAPER` · `LIVE` · `PARK` · `CUT`

## Evidence lifecycle (stable)

`UNKNOWN` · `WEAK` · `PROMISING` · `SUPPORTED` · `VALIDATED`

---

## HTTP surface the agent actually calls (v0)

All routes are under Ananta `APIRouter(prefix="/api")`. Auth is owner JWT unless noted.

| Agent need | Method | Path | Notes |
|------------|--------|------|-------|
| Login | `POST` | `/api/auth/login` | `{email, password}` → `{token, email, role}` |
| Portfolio | `GET` | `/api/portfolio` | equity, cash, positions, `slots_used` |
| Paper / manual order | `POST` | `/api/orders/manual` | BUY: `notional_usd` and/or `quantity`; SELL: `fraction` or `quantity` |
| Trades | `GET` | `/api/trades` | paper fills / history |
| Strategy registry | `GET` | `/api/strategy/registry` | keys, names, DNA (thesis only) |
| Strategy knowledge | `GET` | `/api/strategy/knowledge` | Wave A SKO — implementation + router authoritative |
| Strategy profile | `GET`/`PUT` | `/api/strategy/{key}/profile` | enable/disable + regimes |
| Evaluation cycle | `POST` | `/api/cycle/run` | optional `/{symbol_base}` |
| Lab coverage | `GET` | `/api/lab/data/coverage` | 1h count, ISO span, gaps, `usable_1y` |
| Lab run | `POST`/`GET` | `/api/lab/runs` | backtest JSON; tag `source=BACKTEST` |
| Health | `GET` | `/health` | no `/api` prefix; no DB |

There is **no** `/api/orders/paper`. Paper mode is Ananta's default execution environment; the agent places paper orders through `/api/orders/manual`.

`GET /api/summary` is referenced in the agent client but is **not** a current Ananta route. Do not reason on it until Ananta exposes it.

### Auth rule

Agent Ananta always authenticates. Do not bypass JWT to write Mongo collections from the agent. Direct DB access is fixture-only.

---

## Contract domains (v0 minimum)

### portfolio_state
| Field | Meaning |
|-------|--------|
| `equity` | Total portfolio equity |
| `cash` | Available cash |
| `invested` | Capital in positions (`positions_value` on Ananta today) |
| `open_positions` / `slots_used` | Count of open positions |
| `unrealized_pnl` | Open PnL |
| `realized_pnl` | Closed PnL (if available) |
| `load_level` | OK / CAUTION / OVERLOADED (Agent may derive) |

### strategy_state
| Field | Meaning |
|-------|--------|
| `key` | Stable strategy id (e.g. `hunter`) |
| `name` | Display name |
| `enabled` | bool |
| `status_label` | Human status string |

### market_state
| Field | Meaning |
|-------|--------|
| `symbol` | e.g. BTC |
| `price` | Last price |
| `change_24h` | Percent |
| `regime` | e.g. COMPRESSION, TREND_UP |
| `regime_confidence` | optional 0–1 |

### cycle_state
| Field | Meaning |
|-------|--------|
| `cycle_id` | Immutable id for one Agent reasoning cycle |
| `timestamp` | ISO UTC |
| `agent_api_version` | `0` |

### decision_state
| Field | Meaning |
|-------|--------|
| `action` | TAKE / SKIP / HOLD / EXIT / REDUCE / ENABLE / DISABLE / WAIT |
| `recommended_action` | What evidence argues (`decision_v0`) |
| `issued_action` | What hard gates allow (`decision_v0`) |
| `strategy` / `strategy_key` | Target strategy |
| `confidence` | **deprecated as a single number** — use the triplet |
| `confidences.understanding` / `.evidence` / `.decision` | Three separate 0–1 scores; never blended |
| `reason` | Short explanation |
| `thesis` / `counter_thesis` / `adjudication` | DI deliberation (`decision_v0`) |
| `citations` | System / Market / Outcome row refs |
| `skip_reason` | First-class SKIP (not "no setup") |
| `profile` | SAFE / MODERATE / AGGRESSIVE |
| `execution_allowed` | Always false for Wave A WATCH from the agent package |
| `top_recommendation` | What Agent ranked #1 |
| `user_confirmed` | bool |
| `user_override` | bool — user picked non-top |
| `ranked_options` | optional list of candidates |

Additive: Agent package schema `decision_v0` (`src/intelligence/schema.py`). Does not bump `agent_api_version`. Ananta still owns fills.

### trade_state / exit_state (best-effort in v0)
| Field | Meaning |
|-------|--------|
| `symbol`, `side`, `quantity`, `price` | Open paper trade facts from Ananta |
| `exit_reason` | When Ananta provides it |

### risk_state
| Field | Meaning |
|-------|--------|
| `open_positions` | Count |
| `enabled_strategy_count` | Count |
| `notes` | Free-text risk notes |

### telemetry
Enough to reconstruct: what was known, what was decided, what happened next.

---

## Evolution

- v0 is intentionally small.
- New fields require a version bump or additive optional keys.
- Breaking renames are discouraged; prefer additive fields.
- New HTTP routes that the agent must call belong in this table in the same change.

## Implementation note

Agent repo implements consumers + local cycle/decision/opportunity ledgers (`decision_log.json`, `cycle_log.jsonl`, `opportunity_log.jsonl`).  
Ananta repo exposes matching facts via the HTTP surface above.  
Do not move ledger writes onto raw Mongo from the agent. If ledgers need to live in Ananta later, add an API.
