# Opportunity Engine Lock — 2026-08-28

**Status:** Mapped. **Not implemented.** Interface only (`lab opportunity`).  
**Wave A:** frozen. **lab watch 15:** do not stop / do not change rules.

Two tracks stay separate:

```text
Wave A live evidence     (controlled baseline)
Historical research      (Universe + memory + fingerprints)
```

Coverage (`N strategies × TF × assets`) is **not** intelligence. Intelligence is:

```text
market state → historical pattern → strategy capability
  → evidence quality → expected outcome → risk → decision
```

Paper may later scan **broadly**. Live authority stays **narrow**.

---

## Capabilities (roadmap now, code later)

### 1. Continuous Opportunity Scanning — Phase I3

```text
Market APIs → Market Truth → Market State / fingerprint
  → strategy capability scanners → Opportunity Engine
  → historical/setup evidence → Decision Intelligence
  → TAKE / WAIT / SKIP / UNKNOWN → Ananta hard risk
  → execution → outcome + DQ
```

Laws:

- LLM does **not** get unrestricted scan + decide.
- Deterministic Market Truth + scanners filter first.
- DI reasons only about **candidates**.
- Scanner ≠ live enable. Research universe can be broad; live authority stays Wave A until evidence.

### 2. Fair-value / Mispricing Detection — Phase I3, under the Opportunity Engine

Not a Wave A strategy. Not an LLM-invented “fair price.”

```text
market-implied condition vs Ananta/model-estimated condition
  → measurable divergence → evidence/uncertainty → candidate
```

Needs explicit inputs, provenance, timestamps, uncertainty. Never execute from an invented number.

---

## Intelligence phases

| Id | Name | Status |
|---|---|---|
| **I1** | Current — Wave A frozen, DQ, Universe, fingerprints, memory | **Now** |
| I2 | Research expansion — more families **offline**, evidence cards | Next engineering track |
| I3 | Opportunity intelligence — scanner + fair-value **interfaces already named** | Mapped, not running |
| I4 | Decision intelligence — similar states, ranking, UNKNOWN valid | After live TAKE n + I2 |
| I5 | Forward paper — human-gated TAKEs, beat DQ-v0.0 | After I4 |
| I6 | Earned autonomy — SAFE / MODERATE / AGGRESSIVE | Last |

Do not implement I3 scan or mispricing execution while I1 is still collecting.

---

## CLI

```text
lab opportunity          # prints this lock; refuses scan
```

`refuse_scan` / `refuse_fair_value` always `executed=False` until a later human-gated phase bump.

See `src/intelligence/opportunity_engine.py`.
