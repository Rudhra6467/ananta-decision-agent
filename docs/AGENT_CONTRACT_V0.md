# Ananta ↔ Agent Ananta Contract v0

**Version:** `agent_api_version = 0`  
**Status:** Minimum shared truth (both repos)  
**Rule:** If Agent Ananta reasons on a fact, Ananta must expose it explicitly. No hidden assumptions. No duplicate truth.

---

## Ownership

| System | Owns |
|--------|------|
| **Ananta** | Market data, portfolio, strategy state, orders, fills, exits, risk controls, telemetry, actual outcomes |
| **Agent Ananta** | User understanding, interpretation, ranking, recommendations, decisions, explanation, evaluation, learning |

Agent must never become a second hidden trading engine.

---

## Decision vocabulary (stable)

`TAKE` · `SKIP` · `HOLD` · `EXIT` · `REDUCE`

## Strategy lifecycle (stable)

`CANDIDATE` · `WATCH` · `PAPER` · `LIVE` · `PARK` · `CUT`

## Evidence lifecycle (stable)

`UNKNOWN` · `WEAK` · `PROMISING` · `SUPPORTED` · `VALIDATED`

---

## Contract domains (v0 minimum)

### portfolio_state
| Field | Meaning |
|-------|--------|
| `equity` | Total portfolio equity |
| `cash` | Available cash |
| `invested` | Capital in positions |
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
| `strategy` / `strategy_key` | Target strategy |
| `confidence` | 0–1 or score used by Agent |
| `reason` | Short explanation |
| `top_recommendation` | What Agent ranked #1 |
| `user_confirmed` | bool |
| `user_override` | bool — user picked non-top |
| `ranked_options` | optional list of candidates |

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

## Implementation note

Agent repo implements consumers + local cycle/decision/opportunity ledgers.  
Ananta repo should expose matching facts via existing or new API fields over time.
