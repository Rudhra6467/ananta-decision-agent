# Review 41: results (11 Nov 2026)

**The setup.**
- Pre-registered in `REVIEW_41.md`: commit 7277749, pushed at 09:14:57 Toronto, before the data was read.
- Code: `src/research/review41.py`. The cut-offs were frozen at 09:15 to `~/ananta_runs/review41/review41_cutoffs.json` and the replay ran right after. Figures: `~/ananta_runs/review41/review41_results.json`.
- One look. Nothing live changed.

**What was read.**
- Binance one-minute candles from 2018-01-01 to 2026-07-31; nothing after that.
- 191 coins: 19 alive in 2018, 167 in 2025. 312,325 complete days kept; 1,886 incomplete days dropped (97% rule). BREAKS and ENDS applied.
- 38 coins absent from today's registry were charged the tier C assumption.

**The cut-offs: each coin's own worst moves over 15 minutes, in discovery.**

| | Worst 1% | Worst 0.2% | Worst 0.05% |
|---|---|---|---|
| Bitcoin | −1.17% | −2.16% | −3.37% |
| Ethereum | −1.44% | −2.60% | −4.10% |
| Pooled (coins with too little history) | −2.07% | −3.63% | −5.57% |

## PIT30 decides: FAIL
No cell passed. Every one of the 9 cells failed "above zero after the deciding cost" in both periods.

Average return per trade, PIT30. The excess is over a random entry in the same coin, month and hour.

| Cut-off, hold | Period | Trades | Days | Before cost | After house cost | Excess (z) |
|---|---|---|---|---|---|---|
| worst 1%, 15 min | discovery / confirm | 97,695 / 29,955 | 2,124 / 927 | +0.15% / +0.09% | −1.49% / −1.30% | +0.15% (15.2) / +0.10% (6.1) |
| worst 1%, 4 h | | 97,500 / 29,955 | 2,124 / 927 | +0.49% / +0.29% | −1.15% / −1.10% | +0.46% (16.7) / +0.29% (6.2) |
| worst 0.2%, 1 h | | 22,189 / 5,347 | 1,573 / 623 | +0.58% / +0.38% | −1.08% / −1.07% | +0.59% (16.1) / +0.39% (5.7) |
| worst 0.2%, 4 h | | 22,168 / 5,347 | 1,573 / 623 | +0.87% / +0.42% | −0.78% / −1.03% | +0.83% (14.6) / +0.42% (3.8) |
| worst 0.05%, 15 min | | 5,860 / 1,393 | 723 / 253 | +0.86% / +0.54% | −0.79% / −0.99% | +0.87% (12.6) / +0.56% (3.2) |
| worst 0.05%, 1 h | | 5,859 / 1,393 | 723 / 253 | +1.13% / +0.75% | −0.52% / −0.79% | +1.14% (11.9) / +0.78% (3.7) |
| worst 0.05%, 4 h | | 5,854 / 1,393 | 723 / 253 | +1.55% / +1.04% | −0.09% / −0.49% | +1.49% (10.6) / +1.05% (3.5) |

The other two cells (worst 1%, 1 h and worst 0.2%, 15 min) sit between these; all 9 are in the result file. At the NDAX drop-time cost
(beside) every PIT30 cell is worse still: −0.97% to −2.30% a trade.

## Beside, never deciding: PIT10 (the ten most traded coins)
- **The most extreme drops, held 1 to 4 hours, stay above zero after the house cost in both periods:**
  - worst 0.05%, held 4 hours: +2.00% before cost and +0.70% after it in discovery (2,130 trades on 443 days); +1.71% and +0.50% in confirm (368 trades on 110 days); excess z 12.3 and 4.6;
  - the same drops held 1 hour: +0.10% and +0.35% after cost.
- **Where they fail:** they fail the 2x-cost check (−0.60% and −0.70% at double cost). At NDAX's drop-time cost they are about break-even (−0.01% and −0.05%).
- **The rules:** PIT10 was named "beside, never deciding" before the run, and a tier reported beside never rescues a failed one (LAKE-5). This is a lead, not a result.

## What it means
1. **The bounce is real.** After a coin's worst 15-minute moves, the price rises more than a random entry at the same coin, month and hour.
   - That held in all 9 cells, in both periods, on both lists, with z from 3.2 to 17.3.
   - The deeper the drop and the longer the hold, the bigger the bounce: about +1% to +2% for the rarest drops held four hours.
   - This answers Madhav's question ("How are these bounce backs working?"): they work before costs.
2. **On the top-30 list it does not pay.** A round trip at the house cost (about 1.4% to 1.6% on average on these coins, more on thin ones) is bigger than the bounce, in every cell. The thin coins, where most extreme drops happen, are the most expensive to trade. NDAX's own quotes in October showed a median spread of 2.5% at such drops.
3. **On the ten most-traded coins the rarest drops come close.** They pay at today's house cost in both periods, but not at double it, and only break even at NDAX's drop-time cost. A cheaper way in is the one thing that could turn it: a resting limit order below the price pays no spread.
4. **The look count.** It now includes these 9 cells. Any later pass in this family is read against it.

## What changes (as decided before the run)
- A fail: no watch is added and nothing live changes.
- The lesson, with these numbers, goes into the research cards and into the facts Ask reads.
- **The next question** (section 6 of the pre-registration) is resting limit orders below the price, now that a bounce exists before costs. It would be review 42:
  - written before the data is read;
  - deciding on the coins NDAX lists;
  - with this review's 9 looks counted;
  - any pass would still need a forward test on live paper before it could even become a watch (OD-MULTITEST (b)).
- It needs Madhav's yes, because his 11 Nov lift of Rule B covered review 41 only.
