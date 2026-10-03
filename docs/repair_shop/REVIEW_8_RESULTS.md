# Repair-shop review #8: your setups with zones and the market gate (results)

Pre-registration `REVIEW_8.md` (e363b5b); code ae8bdfa; run 2026-10-03 on the laptop. Same data, rules and pass bar as review #5.
Output: `~/ananta_runs/reads/review8_results.json`.

| Variant | Status | 2018-23 events (episodes) | Excess 30 d | t | Net 30 d, win rate | 2024-Jul 2026 events | Excess 30 d |
|---|---|---|---|---|---|---|---|
| M1a capitulation at a supported zone (Z) | INSUFFICIENT | 6 (16) | −7.2% | −1.2 | −2.9%, 44% | 2 | +3.7% |
| M1a with the market allowed (G, ZG) | INSUFFICIENT | 0 | — | — | — | 0 | — |
| M2a higher-low retest at a supported zone (Z) | INSUFFICIENT | 13 (14) | −3.8% | −0.9 | +2.1% | 2 | +6.4% |
| **M2a retest with the market allowed (G)** | INSUFFICIENT | **7 (12)** | **+10.6%** | **1.7** | **+20.3%, 92%** | 2 | +24.7% |
| M2a with both (ZG) | INSUFFICIENT | 4 (4) | +7.1% | 0.9 | +15.3%, 100% | 0 | — |
| M3a quiet base at a supported zone (Z, ZG) | NOT_SUPPORTED | 12 (16) | −5.5% | −1.5 | −1.8% | 7 | +14.3% |
| M3a with the market allowed (G) | NOT_SUPPORTED | 16 (25) | −4.2% | −0.9 | −0.1% | 8 | +12.1% |

## What it says
1. **Capitulation never happens with the market allowed**, as written down beforehand: when a coin capitulates, BTC is under its
   50-day average. The gate cannot help M1; its own record stays "too few cases" (review #5).
2. **The higher-low retest with the market allowed is the most promising thing found so far**: 12 episodes in 2018-23, 11 of them
   up after 30 days, +20% average, +10.6% over the coin's own drift; 2 more since 2024, both up. It misses the pre-registered bar by
   one market event (7 of 8) and confirm has only 2. So: INSUFFICIENT, but worth recording live.
   Note: your own June 25 buy (C2) is not in this group: BTC was under its 50-day then (it had just made a new 52-week low).
3. **Zones did not improve your setups.** Requiring a supported zone kept or lowered the results; the base (M3a) already includes the
   market condition, so the gate changed nothing there.

## What changes
- "Higher-low retest with the market allowed" (M2a-G) is shown live as its own read with this record, and every live fire is kept
  (repair-shop queue Q5). It is still evidence, not an order; a phone alert needs your sentence (the rule is: only SUPPORTED reads ring).
