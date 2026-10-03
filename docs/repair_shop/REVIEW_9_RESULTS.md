# Repair-shop review #9: the Explorer's setups with zones (results)

Pre-registration `REVIEW_9.md` (11a029d); code `src/research/zone_splits.py` (016b7ab); run 2026-10-03 on the laptop over the existing
rulebook v0 replay: 10,550 real trades and 45,308 random entries (2017 to July 2026; 7,558 before the first 400 days of history have
no zone context and are left out). Output: `~/ananta_runs/zones/review9_results.json`.

| Context at entry | Status | 2018-23 real, in context | Real, outside | Random, in context | t vs random | t vs outside | 2024-26 in / out |
|---|---|---|---|---|---|---|---|
| At a supported zone (Z) | FAIL | −$0.51 (3,148) | −$0.25 (2,466) | −$0.50 | −0.2 | −1.6 | −$0.60 / −$0.64 |
| At any zone (Zany) | FAIL | −$0.47 (4,828) | +$0.05 (786) | −$0.48 | 0.1 | −1.5 | −$0.63 / −$0.41 |
| Market allowed (G) | FAIL | −$0.17 (2,997) | −$0.66 (2,617) | −$0.30 | 0.9 | **3.3** | −$0.56 / −$0.70 |
| Zone and market (Z and G) | FAIL | −$0.33 (1,773) | −$0.43 (3,841) | −$0.43 | 0.7 | 0.7 | −$0.54 / −$0.66 |

(Per $100 trade, net of NDAX costs. By setup, exploratory: no setup did better at zones.)

## What it says
1. **Zones do not rescue the Explorer's trades.** Its trades last hours to a few days and lose about 50 cents per $100 to costs and
   noise, at a zone or not, the same as random entries.
2. **The market gate helps them** (−$0.17 vs −$0.66 per trade, t 3.3), but they still lose and do not beat random entries in the
   same market. V02 again.
3. **The horizons do not match.** Daily zones act over weeks (review #6 judged 20 days); the Explorer exits within hours. Your
   setups and T3 hold for weeks (V06, holding horizon, KEEP). Zones belong with the slower books, not the fast one.

## What changes
- Nothing in the Explorer. The backlog item "zone support for the Explorer" is closed as tested; zone work continues on the
  weeks-long side (your setups, T3 exits, stops).
