# Review #28: the brain's trigger points follow the evidence

Written 2026-10-11 (plan D-batch 3). This is a change review, not a new study: it lines up what wakes the brain with what
earlier reviews measured.

**Before:** every trigger counted the same, so the Explorer (the busiest source) woke the brain most often.

**Evidence used:**
- Review #1: no Explorer setup has an edge after costs.
- Intraday atlas: 0 of 55 setup and market contexts are stable-positive in both periods.
- Review #24 (results above): tuning E6 did not save it.
- Review #27: the H07 dip trade with no stop is the one daily edge (+6.48% to 2023, +2.38% 2024-2026).

**After (brain.TRIGGER_POINTS):**

| Trigger | Points |
|---|---|
| attention_high | 1.0 |
| zone_entry | 0.5 |
| hunter | 0.5 |
| squeeze | 0.5 |
| explorer | 0.0 |

A moment's score is its biggest trigger plus half a point for each extra trigger. A zone entry that history supports gets
+1, and a daily rule ranks by its measured edge (review #26). So the brain spends its attention on attention spikes, supported
zones and measured daily rules first, and an Explorer setup on its own ranks last.

**How it is checked:** the change log in docs/repair_shop/ledger.json ("changes") records the before numbers. The weekly
situation review (jarvis/service/learning.py) prints the after numbers every Sunday. If decisions fall so low that nothing
gets measured for 4 weeks, that becomes a ticket.
