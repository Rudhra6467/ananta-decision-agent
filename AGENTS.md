# Agent Ananta — Operating Contract

Load this when working on Agent Ananta code, lab decisions, ranking, or roadmap.

## Visible to the team

Build the observable intelligence first. Build the autonomous authority later.

Aggressive on paper. Ruthless on measurement. Conservative on promotion.

Do not optimize for looking intelligent. Optimize for being **provably useful**.
Do not optimize for trading frequently. Optimize for the **right decision given available information**.
Do not optimize for autonomy quickly. Optimize for **earning autonomy through evidence**.

Full locks: `docs/NORTH_STAR_LOCK.md`, `docs/MARKET_TRUTH_LOCK.md` (2026-08-22).

## North star

Ananta provides **System Truth**. Independent **Market Truth** is the external reference. Agent Ananta understands the trader and strategy structure, decides, measures **Outcome Truth** (including SKIPs and opportunity cost), learns (evaluation + ranking + experiment proposals only), and earns autonomy through evidence — **without a self-confirming loop**.

## Laws

1. **Facts vs interpretation** — Ananta = System facts; Agent = decisions. Never invent facts Ananta did not provide. Missing information = UNKNOWN / DATA GAP, never "no setup."
2. **Ananta regime is a hypothesis, not ground truth.** Ananta output is never proof Ananta was correct.
3. **Three truths stay separate** — System | Market | Outcome. Same Observation schema for live paper and 1y Lab replay.
4. **Aggressive paper, conservative promotion.** WAIT/SKIP process marks ≠ strategy success. KEEP only with TAKE evidence (+ decision audit when available).
5. **Feature filter** — Improves intent → decision → execution → outcome → learning? Else defer.
6. **Co-design** — If the Agent needs a sense, improve Ananta exposure via the shared contract.
7. **Autonomy is earned** — Observe → Explain → Recommend → Paper → Confirm live → Constrained auto → Expanded auto.
8. **Backend is the contract host** — UI is a client. Talk through the API. Never Agent → database. Never skip auth.
9. **No production mutation** — Agent may evaluate, rank, and **propose versioned experiments**. It must not rewrite hunter/squeeze/bollinger-mr in place. Path: observation → finding → hypothesis → experiment → validation → **human** promotion.
10. **CLI is the lab** — No UI rewrite until ledgers cannot lie. Prefer `lab watch` over human-as-cron.
11. **Implementation is authoritative** — If DNA says X and router/code does Y, the Agent states Y. Thesis ≠ deployment policy ≠ implementation.
12. **Three confidences** — understanding / evidence / decision. Never one blended "82%".
13. **Evidence is sourced** — BACKTEST, PAPER, LIVE, MATRIX, USER_MARK, MARKET_TRUTH. Never silent mix. Matrix 2026-07-26 does not auto-CUT Wave A.
14. **PDFs are supporting methodology** — not trading truth.

## Wave A lab

- Strategies: hunter, squeeze, bollinger-mr (do not add unless instructed)
- All three WATCH until TAKE evidence
- Enabled ~3 (max 5); slots ≤ 5–6
- Mark TAKE / SKIP / WAIT separately; result-first (good/bad/neutral) + process quality
- Knowledge Object: `understand` / `GET /api/strategy/knowledge`
- Continuous observer: `lab watch --interval N` (Stage 1+) with independent market snapshot
- Historical replay: `lab replay` / `lab audit replay` (Stage 4; `source=historical_lab`; never mix into live jsonl)
- 1y candles must be **proven in Mongo** (`lab coverage`) before a 1y Lab claim

## Contract

See `docs/AGENT_CONTRACT_V0.md`. `agent_api_version = 0`.

Live HTTP: `/api/auth/login`, `/api/portfolio`, `/api/orders/manual`, `/api/trades`, `/api/strategy/registry`, `/api/strategy/knowledge`, `/api/strategy/{key}/profile`, `/api/cycle/run`, `/api/lab/data/coverage`, `/api/lab/runs`, `/api/lab/observation-replay`.

Cycle must expose, per enabled strategy: ran / setup / signal / reason / TAKE|SKIP|WAIT. Silence is a data-quality bug. Per-symbol per-strategy rows are mandatory.

## Current mission

**P0–P2:** Done (candles, Knowledge Object, BACKTEST lab).  
**S1–S3:** Done (`lab watch`, `lab outcomes`, `lab audit`). Overnight sample is evidence, not KEEP/CUT.  
**Stage 4 (now):** `lab replay` → `observation_replay.jsonl` (`source=historical_lab`, same `observation_v0`). `lab audit replay`. Live watcher stays first-class and continues in parallel.  
Then compare live vs historical → S5 experiment proposals.  
Do not expand the 12. Do not KEEP. Do not ML-train yet. Historical TAKE-equivalent is not promotion.

See `docs/MARKET_TRUTH_LOCK.md`, `docs/STRATEGY_INTEL_AUDIT.md`, `docs/NORTH_STAR_LOCK.md`, `docs/ROADMAP.md`.
