# Market Truth + Evidence Engine Lock — 2026-08-22

**Status:** Locked. Extension of existing architecture — **not a restart**.

Two capabilities are now first-class:

1. **Strategy structure intelligence** — Agent understands Ananta strategies and may propose versioned experiments; never auto-rewrites production.
2. **Continuous objective evidence loop** — `lab watch` + independent Market Truth + forward outcomes so Ananta cannot grade itself.

Related: [NORTH_STAR_LOCK.md](./NORTH_STAR_LOCK.md), [ROADMAP.md](./ROADMAP.md), [STRATEGY_INTEL_AUDIT.md](./STRATEGY_INTEL_AUDIT.md).

---

## Hard laws

1. **Ananta regime is a hypothesis, not ground truth.**
2. **Ananta output is never proof that Ananta was correct.**
3. Keep **three truths separate**:
   - **System Truth** — cycle, regime label, strategy states, gates, Agent decision, positions/equity
   - **Market Truth** — independent observables (price, returns, vol proxy, trend/compression, breadth)
   - **Outcome Truth** — forward returns, MFE/MAE, opportunity cost, PnL path
4. **Same observation schema** for live paper cycles and 1y Lab historical replay.
5. **No automatic production mutation.** Path only:

```text
observation → finding → hypothesis → experiment → validation
  → human approval → production version (e.g. Hunter v1.1)
```

6. No expanding strategy count for this work. Wave A remains hunter / squeeze / bollinger-mr WATCH.
7. No ML "training" until the evidence base is dense and auditable.
8. Continuous observer **logs only** — never silent enable/disable/KEEP.

---

## Capability 1 — Strategy structure intelligence

Agent must understand (from Contract / Knowledge Object, not DNA alone):

- Purpose, regime requirements, gates
- Entry / exit / risk constraints
- Why ran / skipped / filtered
- Performance across market conditions (when Outcome Truth exists)

Agent may **propose** changes, e.g.:

> Hunter v1.1 — tighten REVERSAL gate; exclude strong-trend environments.

Human promotes. Lab + paper validate. Production versions stay auditable.

---

## Capability 2 — Continuous observation + evidence

### `lab watch --interval N` (default 15m; allow 5–15)

Each tick, **same timestamp**:

| Layer | Capture |
|-------|---------|
| System | Ananta cycle, regime, strategy observations, Agent WAIT/SKIP/TAKE, positions/equity |
| Market | BTC/ETH price, simple returns, vol proxy, trend/compression flags, basic breadth |
| Decision | Agent choice + reasons already on cycle contract |

### Forward outcomes (Stage 2)

Attach at least: **+15m / +1h / +4h** via Kraken OHLC (`ohlc_close_at_or_after_horizon`).

Enables:

- Regime Audit: SUPPORTED / MISCLASSIFIED / UNCERTAIN
- Decision Audit: protective vs costly WAIT; SKIP quality; TAKE path; opportunity cost
- Gate × market-condition performance

Command: `lab outcomes`

### Thin audit (Stage 3)

Command: `lab audit`

Reads the Observation ledger. Scores Ananta's BTC **market label** against independent Kraken flags, and WAIT/SKIP against subsequent BTC path. **BTC path ≠ strategy PnL.** Does not KEEP.

Overnight 2026-08-23 sample (43 obs, 0 TAKEs) is locked as **evidence, not a strategy verdict**. Hypothesis stored: BTC market label may lag rapid transitions; SKIP still avoided the drop. Do not rewrite Hunter from that window.

### Historical replay (Stage 4)

Command: `lab replay [BTC/USD] [--stride 4] [--smoke]`

Ananta `GET /api/lab/observation-replay` runs **real** `classify_regime` / `evaluate_primary` / `evaluate_squeeze` / declarative bollinger-mr on 1y Lab candles (evaluate-then-filter). Writes `observation_replay.jsonl` (`source=historical_lab`). Same `observation_v0` as live. Live file stays first-class.

`lab audit replay` scores the historical file with the same auditor. Historical TAKE = TAKE-equivalent (setup AND Wave A gate) — **not** a paper fill, **not** KEEP.

`lab understanding` prints the Strategy Understanding Report seed (thesis ≠ implementation ≠ router ≠ historical evidence ≠ paper evidence).

Live watcher continues in parallel. Do not wait for a huge live sample before using historical context. Compare live vs historical before S5 proposals.

---

## Staged build (do not parallelize all)

| Stage | Deliverable | Status |
|-------|-------------|--------|
| **1** | `lab watch` + market snapshot + cycle + decision → co-timestamped Observation | **Done** (live ticks continue) |
| **2** | Forward outcome attachment (+15m / +1h / +4h) | **Done** (`lab outcomes`, OHLC fill) |
| **3** | Thin Regime Audit + Decision Audit | **Done** (`lab audit` — 2026-08-23 overnight sample is evidence, not a verdict) |
| **4** | Replay same schema on 1y Lab dataset | **Done** (`lab replay` ran: 2474 BTC bars, usable_1y) |
| **Compare** | Live vs historical, do not mix files | **Now** (`lab compare`) |
| **5** | Agent findings → experiment proposals (human approval) | After compare review |

P0–P2 (candles, Knowledge Object, BACKTEST lab file) remain **done**. Stage 1 does not replace Wave A paper marks; it densifies evidence without human-as-cron.

---

## Explicitly not now

ML training, auto KEEP, auto strategy rewrite, expanding beyond Wave A, new UI, autonomy, India, second evidence schema for "live only."

---

## Definition of done (this lock)

Agent Ananta can **criticize Ananta with independent market evidence**, not only agree with Ananta's labels — and can propose **validated** strategy experiments without deploying them.
