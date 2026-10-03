# Review #7: the lookout (results)

Pre-registration: `ZONES_PROGRAM.md` section 6 (4fb0a84) and Amendment 1 (4ab4617), both before the run. Engine `src/research/zones.py`
(`review7`). Run 2026-10-03 15:44 UTC: 1,775 entries into support zones (one per coin per 5 days), lab-10 coins, 2018 to July 2026.
Holdout not loaded. Numbers: `lookout_status.json`. Baseline: 59% of entries held in 2018-23, 56% in 2024-26.

| Reaction at the entry day's close | Status | 2018-23 held with vs without | raw → corrected | z | 2024-26 raw → corrected |
|---|---|---|---|---|---|
| F6 **Market allowed** (BTC above its 50-day) | **PASS** | **68% vs 50%** | +18.1 → +23.5 | 4.6 | +2.1 → +7.5 |
| F2 Closed back above the zone | FAIL | 68% vs 44% | +24.4 → +1.9 | 0.5 | +29.8 → +7.3 |
| F1 Long lower wick (rejection) | FAIL | 72% vs 54% | +18.3 → −11.7 | −3.1 | +15.0 → −15.0 |
| F7 Good zone kind (200-day, confluence, new swing) | FAIL | 62% vs 55% | +7.2 → +1.2 | 0.3 | +10.1 → +4.1 |
| F4 Momentum divergence | FAIL | 54% vs 59% | −4.6 → −0.3 | 0.0 | +4.1 → +8.4 |
| F3 Volume 1.5x | FAIL | 55% vs 60% | −4.9 → −3.5 | −0.7 | −7.7 → −6.3 |
| F5 Stronger than BTC | FAIL | 59% vs 59% | −0.1 → −9.5 | −1.9 | +0.2 → −9.2 |

"Corrected" subtracts what each reaction scores on random walks, where it cannot mean anything (Amendment 1).

## What it says, plainly
1. **The reaction that matters most is the market itself.** When BTC is above its 50-day average, a support zone held 68% of the
   time vs 50% when it is not (2018-23), and the next 10 days returned +3.7% vs −1.2% after costs. Weaker since 2024 (57% vs 55%).
   This is V02 again, now confirmed at zones: **regime first, then zone, then reaction**, the same order as Madhav's chain.
2. **Wicks and "closed back above" look powerful but are mostly arithmetic.** A higher close starts nearer the "held" line.
   On random walks the same rules score +30 and +22 points; real markets did no better (the wick did worse). They describe the
   day; they do not predict the zone.
3. **Volume, momentum divergence and relative strength vs BTC added nothing** at support zones.
4. So the lookout, in order: is the market allowed (F6)? Is it a zone history supports? Then the plan: where the zone is wrong,
   and the size from that distance. Reactions are shown as description, not as reasons.

## What changes
- The live lookout shows each reaction with its history verdict; only F6 is labelled as one history supports.
- Teacher ideas updated with this evidence: H01 (market regime) supported again; H08 (relative strength) and H09 (volume) added nothing at support zones (they stay untested for breakouts, where H09's claim applies).
- Next (backlog): attention ranking from these results; then the old studies redone with zones, starting with your setups.
