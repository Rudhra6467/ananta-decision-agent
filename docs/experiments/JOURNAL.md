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
