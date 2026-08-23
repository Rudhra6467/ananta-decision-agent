# Feature-complete foundation (Wave A still WATCH)

**Locked:** 2026-08-23  
What "build everything we can now" produced. None of this enables a strategy.

| User ask | Where | Status |
|----------|-------|--------|
| Agent ↔ Ananta API/data contract | `src/intelligence/contract.py` · `lab contract` | Checker + v0 table + `decision_v0`. Probe optional. |
| Decision / Opportunity / SKIP ledger | `src/intelligence/ledgers.py` + existing jsonl | SKIP is first-class. `typed_decision.jsonl` additive. |
| Decision Intelligence foundation | `src/intelligence/` | In tree. |
| Evidence-backed reasoning | `adjudicate.py` | Thesis / counter-thesis / citations. No extra agents. |
| Typed TAKE / WAIT / SKIP | `schema.py` `decision_v0` | HOLD / EXIT / REDUCE included. |
| Decision/outcome attribution | `attribution.py` · `lab attribution` | Engine ready. **S5-H3 not running.** |
| User context and intent | `user_context.py` · `lab intent` | OBSERVE/RESEARCH forbid TAKE. |
| Research / strategy-analysis | `research.py` · `lab research` | Thesis ≠ implementation ≠ evidence. Verdict WATCH. |
| Experiment proposal → approval → eval | `experiments.py` · `lab experiments` | Ledger exists. `try_run` refused. H1 live enable rejected. |
| Monitoring, auditability, recovery | `system_status.py` · `lab system` | Completeness + recovery notes. |
| Orchestration + safety gates | `orchestrate.py` · `gates.py` · `lab gates` | observe → adjudicate → gate → record → no self-fill. |
| E2E paper/simulation | `paper.py` · `lab paper-sim` | No `place_manual_paper_order`. No enable. |
| UI/API integration | CLI + JSON (`--json`) + contract spec | CLI is the lab. No cockpit. |
| Tests / failure paths | `tests/test_intelligence.py` | Offline unittest. |

Still gated on tape / human / Trust Report:

```text
Data collection (running)
      +
Historical replay (done)
      +
Live vs historical comparison (done)
      ↓
Fine-tune decision behaviour     ← after more live tape
      ↓
End-to-end validation
      ↓
Controlled autonomous testing    ← three profiles, limited capital, later
```

Do not confuse this table with Wave A promotion.
