# Safety gates — outside the LLM

**Locked:** 2026-08-23  
**Status:** Deterministic. Not a debate. Not a persona.

Hard codes (always on):

| Code | Meaning |
|------|---------|
| `WAVE_A_WATCH` | hunter / squeeze / bollinger-mr cannot fill from this package |
| `NON_WAVE_A_LOCKED` | the other 12 stay locked |
| `ANANTA_KILL` | kill switch asserted → no TAKE |
| `ANANTA_UNREACHABLE` | no TAKE into a hole |
| `REGIME_FILTER` | Agent cannot override Ananta `REGIME_FILTERED` |
| `SLOT_CAP` / `ENABLED_CAP` | charter 8 / 5 |
| `NO_STRATEGY_MUTATION` | no in-place rewrite of Wave A |
| `NO_KEEP_WITHOUT_TAKE` | WAIT/SKIP marks ≠ KEEP |
| `NO_S5_RUN` | H1/H2/H3 will not start from this package |
| `NO_EXTRA_AGENTS` | profiles ≠ agents |
| `PAPER_ONLY` | no live capital until Trust Report |
| `EXECUTION_AUTHORITY_ANANTA` | Ananta owns fills |
| `UNKNOWN_IS_DATA_GAP` | missing observations ≠ "no setup" |
| `NO_SETUP_IS_WAIT` | no setup cannot become TAKE |

Profile gates (SAFE/MODERATE/AGGRESSIVE) may only **tighten** the above.

CLI proof: `lab gates` runs a confirmed high-confidence hunter TAKE and prints BLOCK on `WAVE_A_WATCH`.

Code: `src/intelligence/gates.py`.
