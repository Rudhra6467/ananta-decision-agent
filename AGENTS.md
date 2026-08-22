# Agent Ananta — Operating Contract

Load this when working on Agent Ananta code, lab decisions, ranking, or roadmap.

## Visible to the team

Build the observable intelligence first. Build the autonomous authority later.

Aggressive on paper. Ruthless on measurement. Conservative on promotion.

Do not optimize for looking intelligent. Optimize for being **provably useful**.
Do not optimize for trading frequently. Optimize for the **right decision given available information**.
Do not optimize for autonomy quickly. Optimize for **earning autonomy through evidence**.

Full lock: `docs/NORTH_STAR_LOCK.md` (2026-08-22). Destination ≠ current sprint.

## North star

Ananta provides the truth. Agent Ananta understands the trader, turns truth into personalized decisions, directs Ananta to execute, measures results (including SKIPs), learns (evaluation + ranking only), and earns autonomy through evidence.

## Laws

1. **Facts vs interpretation** — Ananta = facts; Agent = decisions. Never invent facts Ananta did not provide. Missing information = UNKNOWN / DATA GAP, never "no setup."
2. **Aggressive paper, conservative promotion.** WAIT/SKIP process marks ≠ strategy success. KEEP only with TAKE evidence.
3. **Feature filter** — Improves intent → decision → execution → outcome → learning? Else defer.
4. **Co-design** — If the Agent needs a sense, improve Ananta exposure via the shared contract.
5. **Autonomy is earned** — Observe → Explain → Recommend → Paper → Confirm live → Constrained auto → Expanded auto.
6. **Backend is the contract host** — UI is a client. Talk through the API. Never Agent → database. Never skip auth.
7. **No production mutation** — Agent may evaluate, rank, and **propose versioned experiments**. It must not rewrite hunter/squeeze/bollinger-mr in place. Human promotes versions.
8. **CLI is the lab** — No UI rewrite until ledgers cannot lie.
9. **Implementation is authoritative** — If DNA says X and router/code does Y, the Agent states Y. Thesis ≠ deployment policy ≠ implementation.
10. **Three confidences** — understanding / evidence / decision. Never one blended "82%".
11. **Evidence is sourced** — BACKTEST, PAPER, LIVE, MATRIX, USER_MARK. Never silent mix. Matrix 2026-07-26 does not auto-CUT Wave A.
12. **PDFs are supporting methodology** — not trading truth.

## Wave A lab

- Strategies: hunter, squeeze, bollinger-mr (do not add unless instructed)
- All three WATCH until TAKE evidence
- Enabled ~3 (max 5); slots ≤ 5–6
- Mark TAKE / SKIP / WAIT separately; result-first (good/bad/neutral) + process quality
- Knowledge Object: `understand` / `GET /api/strategy/knowledge`
- 1y candles must be **proven in Mongo** (`lab coverage`) before a 1y Lab claim

## Contract

See `docs/AGENT_CONTRACT_V0.md`. `agent_api_version = 0`.

Live HTTP: `/api/auth/login`, `/api/portfolio`, `/api/orders/manual`, `/api/trades`, `/api/strategy/registry`, `/api/strategy/knowledge`, `/api/strategy/{key}/profile`, `/api/cycle/run`, `/api/lab/data/coverage`, `/api/lab/runs`.

Cycle must expose, per enabled strategy: ran / setup / signal / reason / TAKE|SKIP|WAIT. Silence is a data-quality bug. Per-symbol per-strategy rows are mandatory.

## Current mission

**P0:** Prove ~1y 1h candles in the Mongo collection Lab/API read.  
**P1:** Wave A Strategy Knowledge Object (implementation truth).  
**P2:** Structured Lab backtest evidence (`source=BACKTEST`).  
Then paper loop. Do not expand the 12. Do not KEEP.

See `docs/STRATEGY_INTEL_AUDIT.md`, `docs/NORTH_STAR_LOCK.md`, `docs/ROADMAP.md`.
