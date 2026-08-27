# Strategy Evidence Engine — destination lock (2026-08-25)

**Status:** Destination architecture. **Not built as a ranker.** v0 is the Evidence Card on Universe cells.  
**Now:** Market Truth fingerprints (`lab fingerprints`). Wave A frozen.

## The question this layer exists to answer

> Have I seen this kind of situation before, what happened when I did, which capabilities handled it, how reliable is that evidence, and is today’s evidence strong enough to act?

Not: “which strategy is #1?”  
Not: “this setup won 95% of the time — trade it.”

## Four related stores (do not collapse)

| Layer | Job | Today |
|---|---|---|
| Strategy Library | What capabilities exist? | Universe specs (15) |
| Strategy Knowledge | What have we measured? | `universe_knowledge.json` cells |
| Setup Memory | What happened on similar states? | **v0** `lab memory` — jsonl join of `setup_detected` rows |
| Decision Quality | Were decisions any good? | DQ-v0 cells |

Loop (locked — this is Decision Intelligence, not a strategy bot):

```text
What is the market doing?          Market Truth
        ↓
What state are we in?              Market State (Ananta regime = hypothesis)
        ↓
Which strategies are compatible?   Universe specs + policy
        ↓
What happened historically here?   Setup memory / cells
        ↓
How deep/reliable is that?         DQ-v0 + depth + provenance
        ↓
What is forward paper doing now?   live_paper (separate file)
        ↓
How did prior decisions perform?   DQ-v0
        ↓
TAKE / WAIT / SKIP / UNKNOWN       DI
        ↓
Ananta hard risk constraints
        ↓
Execution
```

Not: Market → Strategy #1 → BUY.

## Provenance (v1.1)

Every cell/card carries `evidence_provenance_v0`:

| Field | Why |
|---|---|
| source | `historical_lab` vs `live_paper` vs `NONE` — never mixed |
| strategy + strategy_version | Which implementation; missing = DATA_GAP |
| evaluator | Function identity (e.g. `evaluate_primary`) |
| asset / timeframe | Cell identity |
| regime + classifier | `classify_regime`; **regime_version is DATA_GAP until Ananta stamps it** |
| decision_policy | WAVE_A WATCH + DQ-v0.1 + UNIVERSE-v1.1 + KEEP=false |
| outcome_horizons | +15m / +1h / +4h (hist +15m UNUSABLE on 1h stride) |
| period | min_ts / max_ts / n_rows |

Law: **evidence without provenance is a speech.**

## Setup Memory v0 (`lab memory`)

Join, not a database.

Each `setup_detected=True` row → `setup_record_v0` (strategy × asset × TF × regime × role × outcomes × market flags × provenance).

**Refused setups are first-class.** SKIP_SETUP rows stamp what the tape did after the refusal:

| +1h after SKIP | stamp |
|---|---|
| ≥ +0.25% | COSTLY — we missed upside |
| ≤ −0.25% | PROTECTIVE — skip was right |
| inside band | WASH |
| missing | NO_SAMPLE |

COSTLY ≠ TREND_UP enable. COSTLY ≠ Hunter rewrite. It is a finding for later judgment.

## Fingerprints v0 (`lab fingerprints`)

Coarse Market Truth bins on each setup: `trend | compression | ret_1h | independent_label`.

v0.1: **strategy-conditioned slices**. Mixed rollup confounds Bollinger TAKE-eq with Hunter refusals.

```text
lab fingerprints
lab fingerprints replay hunter
```

Cross-tab TAKE vs COSTLY / PROTECTIVE / WASH. Not chart-similarity. Not KEEP.

Idle bars (WAIT / FILTERED_IDLE) are **not** memory of a setup.

```text
lab memory                  # hist default
lab memory replay continuation TREND_UP
lab memory live
```

Not a ranker. n=7 TAKE-eq is still ANECDOTE. KEEP forbidden.

A claim like “this setup has historically performed well” must answer: which data, which strategy version, which period, which regime definition, which policy, which outcomes.

## Laws

- UNKNOWN is valid. UNKNOWN ≠ UNSUITABLE.
- SUITABLE ≠ KEEP. Memory does not authorize KEEP.
- Win rate ≠ confidence. n=20 at 95% is ANECDOTE.
- **No blended 81/100.** Cards show TAKE / SKIP_SETUP / depth / completeness / confidence **band**.
- Confidence is **computed**, never LLM “I’m 95% sure.”
- Historical replay ≠ forward paper. Disagreement lowers confidence.
- Similarity = structured Market Truth features, not “charts look alike.”
- Funding / news = DATA_GAP until Ananta exposes them.
- A fat sample of a bad rule is still a bad rule.
- **Evidence without provenance is a speech.**

## Evidence Card v0 (built)

Every Universe cell now carries:

`status_class` · `samples` · `n_take` · `outcome_completeness_1h` · `evidence_depth` · `coverage_band` · `confidence_band`

| status_class | Meaning |
|---|---|
| UNTESTED | No observation_v0 for this spec/asset/TF |
| TESTED_UNKNOWN | Evaluator ran; TAKE n too small or no sample |
| WASH | Adequate n, path inside noise — not an edge, not a condemnation |
| UNSUITABLE | Adequate n, TAKE_HURT |
| SUITABLE | Adequate n, TAKE_HELPED — still not KEEP |

## Sequence (do not skip)

1. Wave A frozen  
2. DQ-v0 locked  
3. Universe v1 scaffold  
4. Universe v1.1 evidence depth  
5. Universe v1.2 continuation hist shadow  
6. **Setup Memory v0 ← now** (`lab memory` — jsonl join, not a DB)  
7. Market-state fingerprints from Market Truth (`lab fingerprints`)  
8. Similarity search (only after TAKE n is real)  
9. Contextual ranking — **separate boards**, never one leaderboard  
10. Forward paper vs hist  
11. Constrained autonomy  

## Explicitly not now

Similarity engine, 2y multi-TF crawl, Donchian×5m/15m/4h explosion, 81/100 scores, putting the catalog on `lab watch`, Hunter TREND_UP, KEEP.
