# Ananta Lab Experiment Journal

One block per lab session. Newest at the **top**.

Copy the template for each day.

---

## Template

```text
### YYYY-MM-DD — session N

Regime: 
Slots (start → end): 
Enabled (start): 
Enabled (end): 
Wave: none | A | B | C | D

Actions:
- 

Cycle summary:
- 

Marks:
- 

Charter OK? yes/no (if no, what breached)

Scoreboard updates:
- 

Notes:
- 
```

---

## 2026-08-14 — session 1 (baseline)

Regime: NEUTRAL (from agent runs earlier today)
Slots (start → end): ~8–9 → still elevated (cleanup not fully applied)
Enabled (start): hunter, ema-cross, time-series-momentum, stochastic-momentum, aggressive-movement / later mixes including squeeze, continuation, bollinger-mr
Enabled (end): _update after next status_
Wave: none (charter + scoreboard created today)

Actions:
- Created Laboratory Charter (docs/LABORATORY_CHARTER.md)
- Created Scoreboard (docs/SCOREBOARD.md)
- Agent features already live: real strategy ranking, cleanup, WAIT path, mark learning
- Paper buy ARB 100 tested (small cover; slots did not improve materially)
- WAIT confirmed successfully via agent

Cycle summary:
- Multiple cycles: often NEUTRAL, Hunter no qualifying setup (credit-preserving skip)

Marks:
- Prior marks exist in decision_log (Breakout +0.08 family bias historically; WAIT bias negative) — review with `history`

Charter OK? **no** — slots above preferred max (6) and near absolute max (8)

Scoreboard updates:
- All strategies initialized as PARK pending first clean wave

Notes:
- **Next session priority:** reduce slots ≤ 6 before new discovery wave
- Prefer `sell` on large longs / cockpit close on large shorts over tiny buys into shorts
- First discovery wave when book is clean: **Wave A** (squeeze, bollinger-mr, vwap-mr) + optional hunter

---
