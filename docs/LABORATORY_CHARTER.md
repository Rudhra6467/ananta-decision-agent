# Ananta Laboratory Charter

**Version:** 1.0  
**Effective:** 2026-08-14  
**Scope:** Crypto paper trading + Agent Ananta  
**Owner:** Project operator (single-user lab)

This charter is the rulebook for the paper laboratory.  
If a session conflicts with this document, **the charter wins** until it is explicitly revised.

---

## 1. Mission of the lab

Find what works by **aggressive discovery in paper**, then **filter by evidence**.

We are not trying to look profitable for one day.  
We are trying to learn which strategies, regimes, and behaviors deserve to survive.

---

## 2. Universe

**Primary symbols (crypto):**
- BTC/USD
- ETH/USD
- SOL/USD
- Plus any symbol already enabled in Ananta (ARB, AAVE, LINK, XRP, etc.)

**Market mode:** PAPER only for all lab experiments unless a later Trust Report opens tiny live.

**Timeframes:** Follow Ananta engine defaults (strategy-native). Do not change TF mid-wave without logging it.

---

## 3. Risk and capacity limits (hard)

| Limit | Value | Action if breached |
|--------|--------|--------------------|
| Max **enabled** strategies | **5** | Disable until ≤ 5 before new enables |
| Max **slots / open positions** (Ananta portfolio) | **6** preferred, **8** absolute max | Cleanup / WAIT; no new enables |
| New enables when slots ≥ 7 | **Forbidden** | WAIT + cleanup only |
| New enables when load CRITICAL | **Forbidden** | Disable + reduce positions |
| Real-money live size | **0** until Trust Report | — |

**Profile default for lab days:** Medium risk is allowed for exploration, but **limits above still apply**.

---

## 4. Daily ritual (required)

Run in order when doing a lab session:

```text
1. monitor
2. cleanup list   (if slots ≥ 6)
3. status
4. run           (agent full analysis)
5. enable/disable only if within limits
6. cycle         (if something enabled or book changed)
7. history
8. mark <n> good|bad|neutral   (at least review pending)
9. Update SCOREBOARD + experiment journal
```

Minimum viable day if short on time:

```text
monitor → status → run → mark (if pending) → journal one line
```

---

## 5. Strategy status labels

Every strategy in the scoreboard must have exactly one status:

| Status | Meaning |
|--------|---------|
| **TEST** | In an active discovery wave |
| **WATCH** | Survived initial tests; collecting more evidence |
| **CORE** | Multi-week / multi-regime evidence; allowed as default on |
| **CUT** | Failed kill criteria; do not re-enable without new hypothesis |
| **PARK** | Not under test; available later |

Only **WATCH** and **CORE** may stay enabled outside an active wave (still respecting max 5).

---

## 6. Kill criteria (strategy)

Move to **CUT** if any of the following hold **and** sample is meaningful:

1. **Paper process failure:** Repeated enable → no sensible behavior / constant noise with no journal justification for 5+ lab days.
2. **Marked outcomes:** Among last 10 related decisions, **bad ≥ 7** with notes pointing at the strategy (not just market luck).
3. **Book damage:** Strategy repeatedly pushes slots over limit or stacks correlated risk with another enabled strategy.
4. **Operator judgment (logged):** You write why it dies; no silent deletes.

Soft rule: prefer **PARK** over CUT if evidence is thin (less than 1 week).

---

## 7. Promotion criteria

### TEST → WATCH
- At least **5 lab days** enabled in relevant regimes
- No charter breaches caused by this strategy alone
- At least some marked decisions not all `bad`
- One written note: "Why it stays"

### WATCH → CORE
- At least **3 calendar weeks** of intermittent or continuous paper use
- Seen in **more than one regime** (e.g. NEUTRAL + TREND or COMPRESSION)
- Scoreboard updated; no unresolved critical issues
- Optional: backtest / walk-forward note attached (Phase 4)

### CORE → demotion
- Breaks kill criteria, or
- Trust Report removes it

---

## 8. Discovery waves (template)

Run one wave at a time when exploring:

| Wave | Focus | Example keys |
|------|--------|----------------|
| A | Mean reversion / range | `squeeze`, `bollinger-mr`, `vwap-mr` |
| B | Trend / momentum | `ema-cross`, `continuation`, `supertrend` |
| C | Breakout | `donchian-breakout`, `atr-breakout`, `keltner-breakout` |
| D | Selective core | `hunter` + best survivors |

**Wave rules:**
- Max 3–4 wave strategies + optional 1 CORE
- Wave length: 5–10 lab days
- End of wave: update scoreboard; CUT/PARK/WATCH

---

## 9. Agent decision policy

- Prefer **WAIT** when slots ≥ 7 or enabled ≥ 5 with weak setups
- Prefer **real Ananta keys** (hunter, squeeze, …) over abstract labels
- Every enable/disable should be logged (agent memory or journal)
- Marks feed ranking — mark honestly, not to "make the agent look right"

---

## 10. What success means in the lab

Not: maximum paper PnL this week.  
Yes:

- Stable book under limits
- Clear winners and losers with written reasons
- Growing decision memory with marks
- Agent actions that match charter
- Progress toward a Trust Report (Phase 6)

---

## 11. Revision process

Change this charter only by:

1. Writing the new rule
2. Dating the change in a short "Charter changelog" at the bottom
3. Not rewriting history of past experiments

### Charter changelog

| Date | Change |
|------|--------|
| 2026-08-14 | v1.0 initial charter |
