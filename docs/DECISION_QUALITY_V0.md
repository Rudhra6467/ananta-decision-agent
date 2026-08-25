# Decision Quality — v0.0 baseline + v0.1 population integrity

**Commands:** `lab quality`  
**Baseline (locked):** `DQ-v0.0` 2026-08-25  
**Meter code:** `DQ-v0.1` — integrity patch (SKIP_SETUP vs FILTERED_IDLE). **Not a quality win. Not KEEP.**

v0.1 does not beat v0.0. It makes the denominator honest so future Δ is real.

---

```text
Ananta DI v0.x
      ↓
Decision Quality baseline  (this file + lab quality)
      ↓
Behavior modification (human-gated, never silent)
      ↓
Retest  (lab quality)
      ↓
Δ vs DQ-v0.0
      ↓
Did this make decisions better?
```

If a change cannot show Δ on this meter, it did not improve Agent Ananta.

---

## Populations (law — measurement integrity)

The squeeze/bollinger live print `setup=12 SKIP=2360` was a **denominator leak**: most of those SKIPs were idle bars behind a closed regime gate, not refused opportunities.

| Token | Population | Used for |
|---|---|---|
| **UNIVERSE** | observation × symbol rows for that strategy (`n_rows`) | Coverage only |
| **SETUP** | `setup_detected=True` | Opportunity existed |
| **TAKE** | SETUP in an allowed regime (paper TAKE or hist TAKE-eq) | **A. Opportunity quality** |
| **SKIP_SETUP** | SETUP that was refused (`SKIP` or `REGIME_FILTERED`) | **B. Refusal quality** |
| **FILTERED_IDLE** | No setup; regime gate closed | **Not refusal.** Do not score as SKIP quality |
| **WAIT** | No setup, not filtered | Idle / nothing to say |
| **SKIP_LEGACY** | H3 all-row SKIP (includes FILTERED_IDLE) | Δ vs DQ-v0.0 only |
| **FILTERED** | `skip_reason` starts with `REGIME_FILTERED` | Gate accounting |
| **SIT-OUT** | Agent-level WAIT/SKIP vs BTC path | **C. Opportunity cost of the book** |

Hunter live 64/64 TREND_UP setups are **SKIP_SETUP**. That is the 64 we may ask “was refusing correct?”

Squeeze live ~12 setups vs ~2360 legacy SKIP: refusal n ≈ 12 (`SKIP_SETUP`); the rest is `FILTERED_IDLE`.

---

## Five questions (v0 answers A–B–C only; D–E later)

| | Question | v0.1 |
|---|---|---|
| **A** | When we TAKE, was taking good? | Live: `NO_LIVE_TAKE`. Hist: hunter/squeeze `INSUFFICIENT`; bollinger `WASH` |
| **B** | When we SKIP a **setup**, was refusing good? | Hunter live SKIP_SETUP n=64 WASH/+4h slight protective. Squeeze/bollinger SKIP_SETUP still small n |
| **C** | Did we miss something meaningful? | Sit-out WASH. Not demonstrated. |
| **D** | Calibration: does stated confidence match reality? | **Not yet.** No blended score as a fake substitute |
| **E** | Consistency across asset × TF × regime × vol | **Universe v1+.** Do not pretend we have it |

Readiness: **NOT EARNED**. Keep it that way until A or B is actually earned.

Do **not** add Decision Quality = 73.4.

---

## What “finest” means here

Not the most trades. Not the most confident LLM. Not blended “82%.”

Finest decision quality in a market is:

1. **Separate questions.** (A) Does the strategy have edge? (B) Do TAKE / WAIT / SKIP improve on acting the raw setup? Never mix.
2. **Evidence depth gates claims.** n=4 is not a track record. Low n → `INSUFFICIENT_EVIDENCE`, never “excellent.”
3. **Opportunity cost is first-class.** SKIP/WAIT are scored. Silence is a decision.
4. **Unusable clocks are marked unusable.** Hist `+15m` on a 1h-stride replay is garbage. Do not trade on it.
5. **BTC path ≠ strategy PnL.** Forward % is opportunity-cost context, not Hunter P&L.
6. **Refusal is a feature.** `NO_LIVE_TAKE` under WATCH is the safety architecture working, not a missing grade.
7. **Promotion is conservative.** KEEP needs live TAKE with adequate n and TAKE_HELPED on +1h and +4h **and** a human. This baseline does not have that.

---

## Bands (locked)

| | Rule |
|---|---|
| Noise / wash | `|+1h| < 0.25%` |
| Slight | `0.25–0.40%` |
| Material | `≥ 0.40%` |
| TAKE claim | n ≥ 30 |
| Sit-out claim | n ≥ 30 |
| Hist +15m | **UNUSABLE_CLOCK** |
| Live TAKE n=0 | **NO_LIVE_TAKE** |

Depth: `NONE` 0 · `ANECDOTE` 1–9 · `THIN` 10–29 · `ADEQUATE` 30–99 · `SOLID` 100+.

---

## Frozen baseline (do not “improve” by rewriting this table)

### Live paper (15m ticks, multi-symbol flattened)

| Cell | n +1h | +1h | +4h | Verdict |
|---|---|---|---|---|
| Hunter TAKE | 0 | — | — | **NO_LIVE_TAKE** |
| Hunter SKIP (64 TREND_UP setups) | 64 | +0.00% | −0.26% | +1h **WASH**; +4h **SLIGHT / SITOUT_PROTECTIVE** — **not** a TREND_UP enable |
| Hunter WAIT | 2306 | +0.02% | +0.20% | **WASH** (drift) |
| Squeeze TAKE | 0 | — | — | **NO_LIVE_TAKE** |
| Squeeze SKIP | 2320 | +0.02% | +0.19% | **WASH** — same BTC path as bollinger SKIP (shared sit-out, not two edges) |
| Bollinger TAKE | 0 | — | — | **NO_LIVE_TAKE** |
| Bollinger SKIP | 2320 | +0.02% | +0.19% | **WASH** (same rows as squeeze SKIP) |

### Historical lab (1h stride=4) — use +1h / +4h only

| Cell | n +1h | +1h | +4h | Verdict |
|---|---|---|---|---|
| Hunter TAKE-eq | **4** | −0.00% | −0.40% | **INSUFFICIENT_EVIDENCE** |
| Squeeze TAKE-eq | **4** | +0.11% | +0.10% | **INSUFFICIENT_EVIDENCE** |
| Bollinger TAKE-eq | **47** | **−0.07%** | **−0.08%** | **WASH** (slightly negative point estimate) |
| Bollinger SKIP | 111 | +0.05% | +0.07% | **WASH** — sitting out was not worse than taking |

Hist TAKE-eq is **almost entirely bollinger**. Wave A “TAKE quality” without a split was a Bollinger number wearing a Wave A badge.

---

## Rollup (DQ-v0.0)

```text
KEEP allowed      : False
wave_a            : WATCH
live TAKE quality : NO_LIVE_TAKE
live sit-out      : WASH
hist TAKE usable  : bollinger-mr n=47 WASH (slightly negative)
hunter live SKIP  : n=64 WASH at +1h; slight protective at +4h
promotion         : FORBIDDEN
readiness         : NOT EARNED
```

Hunter TREND_UP contradiction remains a **map cell**, not a rewrite sprint.

---

## How a later version earns a better grade

A DI / gate / ranking change is an improvement only if `lab quality` shows, with adequate n:

- fewer `SITOUT_COSTLY` or more `SITOUT_PROTECTIVE` **without** creating live TAKE harm, **or**
- live TAKE appears and is `TAKE_HELPED` on +1h and +4h with n ≥ 30,

and Wave A is still not silently KEEP’d.

Empty `delta_vs_baseline.moved_cells` means we are still on this baseline.

v0.1 population split is **not** a quality win.

---

## Explicitly not a quality improvement

- Enabling TREND_UP
- Hunter v1.1 / loosened RSI / disabled VCP
- KEEP because SKIP was slightly protective one week
- Blending understanding/evidence/decision into one %
- Using hist +15m
- Opening 20 strategies to “get more n”
- Extra agents

---

## Sequence this meter sits in

```text
H3 report (done) → DQ-v0.0 (locked) → v0.1 populations (integrity)
  → H2 instrumentation (queued)
  → Decision Quality retest
  → Strategy Research Universe v1 (specs → cells → this meter)
```

Universe v1 does not replace this meter. Every new cell must be scored here.

CLI: `lab quality`  (alias `lab dq`)  
Code: `src/intelligence/decision_quality.py`  
H3: `lab attribution live` / `lab attribution replay`
