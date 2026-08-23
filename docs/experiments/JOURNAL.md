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

## 2026-08-23 — S3 audit locked as evidence; S4 replay shipped

Wave: A (hunter / squeeze / bollinger-mr) — all **WATCH**

Actions:
- `lab audit` on 43 live observations (0 TAKEs)
- Did **not** KEEP/CUT/rewrite Hunter
- Started Stage 4 historical replay (`lab replay` / `GET /api/lab/observation-replay`)
- Live `lab watch 15` continues in parallel

S3 result (evidence, not a verdict):
- 43 obs, 39 with +1h, SKIP 19 / WAIT 24 / TAKE 0
- regime: SUPPORTED 6 / MISCLASSIFIED 9 / UNCERTAIN 28
- decision: PROTECTIVE 17 / COSTLY 4 / UNCERTAIN 22
- mean BTC +1h after sit-out: −0.2415%

FINDING (not a modification):
> Ananta's BTC market label may lag rapid overnight transitions. SKIP still avoided the drop. Do not blame Hunter until 1y replay exists.

Scoreboard: no change. No HYPOTHESIS experiment opened (S5).

Charter OK? yes

---

## 2026-08-20 — ops (Emergent expired → backend-first)

Regime: n/a (no live API)
Slots (start → end): n/a — hosted backend unavailable
Enabled (start): n/a
Enabled (end): n/a
Wave: A (paused on API)

Actions:
- Confirmed failure chain: Agent → Ananta auth/API → backend unavailable → login failed
- Inspected `Rudhra6467/Ananta` and `Rudhra6467/ananta-decision-agent`
- Backend is intact (`backend/server.py`, FastAPI, Mongo, owner JWT, `/api/orders/manual`)
- Locked operating mode: UI is a client; Agent talks to independently runnable backend
- Preferred path: Option A — run existing Ananta backend locally; point `ANANTA_BASE_URL` at it
- Explicitly rejected: Vercel-for-the-agent, Agent→DB architecture, auth bypass

Cycle summary:
- None (no backend)

Marks:
- None

Charter OK? n/a — lab paused until local API is up

Scoreboard updates:
- None (book cannot be read)

Notes:
- **Next session priority:** start Ananta backend locally, then `status` / `monitor` / paper `sell ARB 1.0` through the contract
- Default Agent URL `https://livetrading247.com` is dead; local default is `http://127.0.0.1:8001`
- Product roadmap still locked (Wave A + Contract + Phase 4 ledgers). This is an operating-mode change, not a thesis change.

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
