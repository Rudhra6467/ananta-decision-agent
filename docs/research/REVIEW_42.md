# Review 42: after an extreme drop, does a resting buy order below the price beat costs?

Written 11 Nov 2026, before the data is touched, under a lift of Rule B for this review only. Madhav, 11 Nov 2026 09:20 Toronto: "Yes",
to review 42 as proposed at 09:19: a buy order resting below the price, judged on the coins NDAX lists, on history only. Even a pass has to
prove itself on live paper before it becomes even a watch. No live rule changes on this result without his separate yes.

## 1. Why
Review 41 (`REVIEW_41_RESULTS.md`, commits 7277749 and 5d6635c) found three things:
- **The bounce is real.** After a coin's worst 15-minute drops the price bounces more than a random entry, in all 9 cells and both periods (z 3.2 to 17.3).
- **It loses on PIT30.** A market buy and a market sell cost about 1.4% to 1.6% a round trip, more than the bounce.
- **The lead.** Beside, on the ten most traded coins, the rarest drops came close.

A market buy pays the spread on the way in; a resting limit order does not. The house cost model already says so: a LIMIT entry pays the
NDAX fee only (`src/intelligence/explorer_engine.py`). So the question: with the entry made by a resting limit order instead of a market
buy, does the bounce beat costs? Asked once.

## 2. The tier that decides
**NDAX30** decides: the PIT30 months (`~/ananta_lake/reports/pit_top30.json`), restricted to the coins NDAX lists today (`universe_live.json`, `ndax: true`, read 11 Nov 2026).
- There is no point-in-time history of NDAX's listings, so today's list is a present-day filter; it is noted as a limit of this review.
- Reported beside, never deciding: PIT30 (all coins) and PIT10.

## 3. The test
- **Data, periods, the drop and the cut-offs** are as in review 41:
  - one-minute Binance candles, 2018-01-01 to 2026-07-31, the 97% rule, BREAKS and ENDS;
  - discovery 2018-2023, confirm 2024 to 2026-07-31;
  - the frozen `~/ananta_runs/review41/review41_cutoffs.json`, unchanged.
- **The cut-offs used:** the worst 0.2% and 0.05%. The worst 1% is left out, because its bounce before costs in review 41 (+0.09% to +0.49%) is below even this review's cheapest round trip.
- **The order:**
  - At the first minute d where r15 is at or below the cut-off, a resting limit buy is placed at L = close(d) x (1 - k x |the coin's cut-off|).
  - k is 0.25 or 0.5: a quarter or a half of the coin's own drop size at that cut-off (data-derived, PDLAW).
  - It rests for 60 minutes (d+1 to d+60, by clock time).
  - It fills at L in the first of those minutes whose low is at or below L x 0.999. The price must trade through the order by 0.1%; a touch is not a fill.
  - An order that does not fill is cancelled: no trade.
  - At most one order per coin per 60 minutes.
- **The exit:** a market sell at the open 60 or 240 minutes after the fill minute.
- **Cells:** 2 cut-offs x 2 depths x 2 holds = 8.
- **The baseline:**
  - The same order placed at random minutes: for each event, 10 random minutes in the same coin, the same calendar month and the same UTC hour, with a fixed seed per coin.
  - Each gets the same depth relative to that minute's close, and the same window, fill rule and exit.
  - Excess = the event's return minus the mean return of its random orders that filled. An event whose random orders all went unfilled has no excess and is counted apart.
- **Costs:**
  - **Deciding:** the entry pays the NDAX fee only (0.20%: a resting order pays no spread). The exit pays the house cost per side, `jarvis/service/registry.cost()`.
  - **Reported beside, never deciding:**
    - no cost;
    - the market round trip on the same fills (twice the house cost);
    - the harsh NDAX case: 0.20% in and out plus the coin's whole median NDAX spread at a fast drop (`REVIEW_41_ndax_drop_costs.json`; 2.5% where a coin had fewer than five drops).
- **Counting:**
  - An independent event is a UTC day with at least one fill in the cell. The mean is the mean of the day means; the z-score is on the day means of the excess.
  - Orders placed and orders filled are reported for every cell.

## 4. Pass marks (frozen)
The same as review 41. A cell passes only if, in BOTH discovery and confirm:
1. it has at least 30 independent events (days);
2. the mean return after the deciding cost is above zero;
3. the excess over the random orders has a z of 2.5 or more;
4. it is still above zero at twice the deciding cost;
5. no single month gives more than half of its after-cost gain.

One look. Anything else is a fail.

**The family's look count:** these 8 cells join it (MTF v1 108, green runs 67,167 cells, R24 3, entry v2 36, review 41 9). This review was designed after reading review 41, so a pass is read against that count.

## 5. What each outcome changes (decided now)
- **A pass:**
  - It is not promoted (OD-MULTITEST (b)).
  - It becomes a forward test on live paper, recording only. Each live sighting is logged with the order, whether NDAX's own recorded prices would have filled it, and the paper result. That goes in `docs/knowledge/watches.json` and a shadow log; it never touches the $500 book, the measuring books or the account.
  - The record is read once, after 30 independent events, with these pass marks and NDAX's measured costs deciding.
  - Anything beyond recording needs Madhav's separate yes, after the 14 Dec review.
- **A fail:**
  - It is written up as a lesson with its numbers, including the fill rates.
  - Nothing is recorded live.
- **Either way:**
  - The result file `docs/research/REVIEW_42_RESULTS.md` records this pre-registration's commit.
  - The change book gets its line, and the look count is updated.

## 6. Not in this review
- limit or target exits;
- other depths, windows or holds;
- the worst-1% cut-off;
- shorting;
- coins NDAX does not list (they are reported beside only);
- anything from 2026-08-01 on, the live window included.
