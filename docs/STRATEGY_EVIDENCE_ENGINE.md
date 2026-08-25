# Strategy Evidence Engine — destination lock (2026-08-25)

**Status:** Destination architecture. **Not built as a ranker.** v0 is the Evidence Card on Universe cells.  
**Now:** Universe-v1.1 depth metadata. Wave A frozen.

## The question this layer exists to answer

> Have I seen this kind of situation before, what happened when I did, which capabilities handled it, how reliable is that evidence, and is today’s evidence strong enough to act?

Not: “which strategy is #1?”  
Not: “this setup won 95% of the time — trade it.”

## Four related stores (do not collapse)

| Layer | Job | Today |
|---|---|---|
| Strategy Library | What capabilities exist? | Universe specs (15) |
| Strategy Knowledge | What have we measured? | `universe_knowledge.json` cells |
| Setup Memory | What happened on similar states? | `observation_v0` rows (live + hist). **Not a new DB.** |
| Decision Quality | Were decisions any good? | DQ-v0 cells |

Loop: Market → setup → (later) similar memory → ranking boards → DI → TAKE/WAIT/SKIP → Ananta gates → Outcome → DQ → update knowledge.

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
4. **Universe v1.1 evidence depth ← now**  
5. One extra spec on real `observation_v0` (`continuation` × BTC × 1h, **not** live watch)  
6. Setup records = joins of existing jsonl  
7. Fingerprints from Market Truth  
8. Similarity search (only after TAKE n is real)  
9. Contextual ranking — **separate boards**, never one leaderboard  
10. Forward paper vs hist  
11. Constrained autonomy  

## Explicitly not now

Similarity engine, 2y multi-TF crawl, Donchian×5m/15m/4h explosion, 81/100 scores, putting the catalog on `lab watch`, Hunter TREND_UP, KEEP.
