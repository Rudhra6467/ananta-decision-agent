# The 11 late passes, explained (audit item, 25 Oct 2026)

The 25 Oct audit found 11 study versions whose first run was not a pass and whose later run passed, some on the same git hash. This page says
what changed between the runs. Script: `~/ananta_runs/late_pass.py` (reads `manifests/test_ledger.jsonl` only).

## What happened

All 11 first runs were on 18 Oct 2026, during the second build day, on code that was not yet committed:

| study / version | first run (UTC) | first verdict | later run | later verdict | what changed |
|---|---|---|---|---|---|
| E04-BRK ext_ret20_gt25 · hold_20d | 22:34 | INCONCLUSIVE (val 15 quarters) | 22:39 | CONDITIONAL | uncommitted conditions code; validation quarters 15 → 22 |
| E04-ANY ext_ret60_gt50 · hold_20d | 22:34 | INCONCLUSIVE (val 6 quarters) | 22:39 | CONDITIONAL | same |
| E04-ANY ext_sma50_gt20 · hold_20d | 22:34 | INCONCLUSIVE (val 7 quarters) | 22:39 | VALIDATED | same |
| E04-ANY ext_sma50_gt20 · hold_60d | 22:34 | INCONCLUSIVE | 22:39 | CONDITIONAL | same |
| E04-ANY ext_sma50_gt20 · atr_trail_4 | 22:34 | INCONCLUSIVE | 22:39 | CONDITIONAL | same |
| E04-ANY ext_sma50_gt20 · sma_close_50 | 22:34 | INCONCLUSIVE | 22:39 | CONDITIONAL | same |
| E04-ANY ext_sma50_gt20 · swing_low_20 | 22:34 | INCONCLUSIVE | 22:39 | CONDITIONAL | same |
| E04-ANY ext_ret20_gt25 · hold_20d | 22:34 | INCONCLUSIVE (val 4 quarters) | 22:39 | VALIDATED | same |
| E04-ANY ext_ret20_gt25 · atr_trail_4 | 22:34 | INCONCLUSIVE (val 4 quarters) | 22:39 | VALIDATED | same |
| C05-PULL vix_rising · hold_20d | 22:34 | INCONCLUSIVE (dev t 2.4, bar 3.35) | 22:39 | CONDITIONAL (dev t 4.0, bar 3.66) | same |
| V02 band_hit_low | 23:22 | INCONCLUSIVE (val t 1.5) | 23:26 | CONDITIONAL (val t 2.7) | uncommitted vstudies/conditions code (the dirty list grew) |

- **None of the first runs failed the test.** Every one was INCONCLUSIVE: too few quarters (4-15 validation quarters against the minimum 16),
  or below the bar without the opposite sign. The first runs were development runs of a conditions module that dropped most dates; the fixed
  module was committed two minutes later (34dc41d, 18 Oct 18:41 Toronto, "conditions and studies E04-E06/E09/C02-C09").
- **The passes were made under a higher bar, not a lower one.** The family count grew between the runs (E04: k 11-53 → 85; C05: 61 → 195), so
  the later passes cleared a stricter threshold.
- **Every pass reproduces on committed code.** The 10 E04 and C05 passes were re-run twice on the committed code 34dc41d (22:59 and 23:07 UTC)
  with the same numbers. V02 band_hit_low was re-run today (25 Oct) on committed code with a recorded re-run reason: CONDITIONAL again,
  dev -7.54% (t -6.3), validation -3.12% (t -2.7), against -7.58% (t -6.3) and -3.14% (t -2.7) on 18 Oct.

## What was wrong, and the fix

The ledger stamped only the git hash, so two runs on different uncommitted code looked identical, and a re-run carried no reason. From 25 Oct
(`india/lineage.py`, `india/registry.py`): every changed or new Python file under india/ is hashed into a dirty fingerprint, each result's
code id reads `<git>+dirty:<fingerprint>`, and a study registered again carries a version number and a re-run reason (or "no reason given").
Tests: `tests/test_india_audit_fixes.py`.

Verdict: the 11 late passes are real results of fixed code, not results picked from repeated tries. They stay as recorded.
