# Review 42: results (11 Nov 2026)

**The setup.**
- Pre-registered in `REVIEW_42.md`: commit 2b4d5a4, pushed at 09:24:11 Toronto, before the data was read.
- Code: `src/research/review42.py`. Figures: `~/ananta_runs/review42/review42_results.json`.
- One look. Nothing live changed.

**What was read.**
- Review 41's data: Binance one-minute candles from 2018-01-01 to 2026-07-31; 191 coins, 58 of them on NDAX today; 1,886 incomplete days dropped.
- Review 41's frozen cut-offs, unchanged.

## NDAX30 decides: ONE CELL PASSES
**The cell:** the rarest drops (a coin's worst 0.05% of 15-minute moves), with a resting buy half the coin's drop size below the price, and a sale 4 hours after the fill.

| | Discovery 2018-2023 | Confirm 2024 to Jul 2026 |
|---|---|---|
| Orders placed / filled | 3,063 / 1,570 (51%) | 869 / 394 (45%) |
| Independent days / coins | 299 / 43 | 92 / 42 |
| Average per trade before cost | +2.76% | +1.82% |
| After the deciding cost (entry fee only, exit house cost) | **+1.96%** | **+1.01%** |
| At twice that cost | +1.17% | +0.21% |
| Beside: as a market buy on the same fills | +1.57% | +0.61% |
| Beside: the harsh NDAX case (whole drop-time spread) | +0.78% | +0.18% |
| Excess over the same order placed at random times (z) | +2.83% (7.9) | +2.74% (4.6) |
| Largest month's share of the gain | 19% | 23% |

All five frozen marks hold in both periods.

The other seven NDAX30 cells fail:
- **The worst 0.2% of drops:** negative after cost in confirm, or fails the 2x-cost check.
- **Two cells with the worst 0.05%:**
  - a quarter-depth order held 4 hours passes discovery but fails at twice the cost in confirm (−0.17%);
  - a half-depth order held 1 hour passes discovery but fails at twice the cost (−0.16%) and the no-burst check in confirm.

**Beside, never deciding:**
- **PIT10:** the same cell passes in both periods: +2.22% and +1.18% after cost, z 7.4 and 2.7.
- **PIT30 (all coins):** it passes discovery but fails the 2x-cost check in confirm (+0.25% after cost).

## How to read it
1. **This is a pass by the frozen rule, and a cautious one:**
   - The review was designed after reading review 41.
   - The family's look count is large: MTF v1 108, green runs 67,167 cells, R24 3, entry v2 36, review 41 9, and review 42 8.
   - One cell of eight passed.
   - The confirm margin at double cost is thin (+0.21%).
   - Today's NDAX list is a present-day filter.
2. **The fills are Binance's.** NDAX's order book is far thinner (October: about C$600,000 of Bitcoin a day, with a 0.43% spread). Whether NDAX's own prices fall through such an order the same way is not known from history. The forward test answers that.
3. **It is rare.**
   - The confirm period had 394 fills on 92 days in 31 months, about 35 days a year across 42 coins.
   - 30 independent days of live record may take most of a year at that pace, sooner in a rough market.
4. **It holds through the drop with no stop.** A 4-hour hold after a crash can lose badly on a single trade. The averages above include those losses. No stop was tested.

## What changes (as decided before the run)
- **It is not promoted** (OD-MULTITEST (b)). Nothing reaches the $500 book, the measuring books or the account.
- **A forward test on live paper, recording only:**
  - from 12 Nov 2026;
  - each sighting on NDAX's coins logged with the order, whether NDAX's own recorded prices would have filled it, and the paper result at NDAX's bid;
  - in a shadow log and `docs/knowledge/watches.json`.
- **When it is read:** once, after 30 independent days, with these pass marks and NDAX's measured costs deciding. No early looks: until then the record is counted, not totalled.
- **Anything beyond recording** needs Madhav's separate yes, after the 14 Dec review.
- **Where the data comes from:** the lake's one-minute candles (updated every Sunday) and the worker Mac's NDAX quotes (kept by day). No sighting is lost while the recorder is built.
