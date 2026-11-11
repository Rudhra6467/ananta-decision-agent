# Review 41: after an extreme 15-minute drop, does the price bounce enough to beat costs?

Written 11 Nov 2026, before the data is touched, under a lift of Rule B for this review only. Madhav, 11 Nov 2026 09:06 Toronto: "Yes to all
recommendations to get it started", answering the plan of 09:03: a third study, on history only, written down first, with nothing live
before the 14 Dec review. No live rule changes on this result without his separate yes.

## 1. Why
Madhav, 11 Nov 09:03: "Why did we just test it on 1 hour charts when we have 5 minutes time frames and 1 minute time frames ... Is there any
cutoff edge that we can find in these moments? ... We might find some magic at the end." And at 09:04: "something that's worthy to add to
watch at least".

The earlier intraday studies all looked at ordinary setups:
- **5-minute entries:** MTF v1, 108 variants. None beat costs.
- **5-minute green runs:** 2.69M events. There is a slight snap-back.
- **15-minute dips:** R24. They beat random entries by a few cents and lost to costs.
- **Hourly reversals at support:** Hunter. It lost in every test.

None looked only at the most extreme drops, on one-minute candles, where a bounce could be larger than a round trip's cost. That is the
question here, asked once.

**Context, not evidence.** On 11 Nov the worker's NDAX quotes for 11 Oct to 10 Nov 2026 were counted for costs only; nothing after a drop was
looked at.
- **Median NDAX spread:** 0.43% for Bitcoin, 0.44% for Ethereum, 0.50% for XRP, 0.56% for Solana, and 1.1% across 67 coins.
- **At falls of 2% or more in 15 minutes:** 2,677 events on 67 coins, nearly all on thin coins (Bitcoin had one). Their median spread was 2.5%. On the liquid coins it was about the normal spread.
- **Per-coin table:** `docs/research/REVIEW_41_ndax_drop_costs.json`.

## 2. The tier that decides
**PIT30** decides: the top 30 coins by traded value over the three months before each month (`src/lake/pit.py`, `~/ananta_lake/reports/pit_top30.json`).
- A coin counts in a month only if it was on that month's list.
- Stable, wrapped and leveraged tokens are left out (`src/lake/universe.py`).
- **PIT10** is reported beside it and never decides.

## 3. The test
- **Data:**
  - The lake's Binance spot one-minute candles (`~/ananta_lake/clean/binance/spot/1m`), one source, Binance USDT.
  - A day with fewer than 97% of its minutes (1,397 of 1,440) is dropped and counted in the header.
  - BREAKS and ENDS apply (`src/lake/research.py`).
- **Periods:**
  - Discovery: 2018-01-01 to 2023-12-31.
  - Confirm: 2024-01-01 to 2026-07-31 (the loader's CONF_END).
  - Nothing from 2026-08-01 on is loaded:
    - Aug-Sep 2026 was spent by Candidate v3.
    - The live window from 11 Oct 2026 is the fresh test of reviews #31-#38 and of the forward test, read on 14 Dec.
- **The drop:** the 15-minute return at minute t, r15 = close(t) / close(t - 15 min) - 1, looked up by clock time, never by row offset.
- **The cut-offs** (data-derived, PDLAW):
  - For each coin: the 1st, 0.2nd and 0.05th percentiles of its own r15 in discovery, its worst 1%, 0.2% and 0.05% of 15-minute moves.
  - They are frozen to `~/ananta_runs/review41/review41_cutoffs.json` by a first step that reads no outcome.
  - A coin with fewer than 100,000 discovery minutes uses the pooled cut-offs: the median of the coins' own.
- **The entry:** the first minute where r15 is at or below the cut-off; buy at the open of the next minute. At most one entry per coin per 60 minutes.
- **The exits** (one each, nothing else): sell at the open 15, 60 or 240 minutes after the entry, the drop window x1, x4 and x16.
- **Cells:** 3 cut-offs x 3 holds = 9.
- **The baseline:**
  - A random entry in the same coin, the same calendar month and the same UTC hour, with the same hold and the same next-minute entry.
  - Its expected return is the mean over every such minute, not a sample.
  - Excess = the event's return minus that mean. The cost is the same on both sides, so the excess is the same before and after cost.
- **Costs:**
  - **Deciding:** the house cost per side, `jarvis/service/registry.cost()`: the measured NDAX half-spreads for the lab coins, and the labelled assumption for every other coin (coins missing from today's registry are tier C). It is charged on the way in and on the way out.
  - **Reported beside, never deciding:**
    - no cost, to show the bounce itself;
    - the NDAX drop-time cost: 0.20% a side plus the coin's median spread at a fast drop in the table above, or 2.5% where the coin had fewer than five drops.
- **Counting:**
  - An independent event is a UTC day with at least one entry in the cell; coins that fire together on one day are one event.
  - The mean is the mean of the day means. The z-score is on the day means.

## 4. Pass marks (frozen)
A cell passes only if, in BOTH discovery and confirm:
1. it has at least 30 independent events (days);
2. the mean return after the deciding cost is above zero;
3. the excess over the random baseline has a z of 2.5 or more;
4. it is still above zero at twice the deciding cost (the 2x-cost check);
5. no single month gives more than half of its after-cost gain (the no-burst check).

One look. Anything else is a fail.

**The family's look count:** these 9 cells join the intraday family's running count (MTF v1 108, green runs 67,167 cells, R24 3, entry v2 36). A pass is read against that count.

## 5. What each outcome changes (decided now)
- **A pass:**
  - The passing cell is not promoted on that pass alone (OD-MULTITEST (b)).
  - It becomes a recording-only watch. Each live sighting on the worker's NDAX quotes is logged with what a paper buy at NDAX's ask and a sale at its bid would have made, in `docs/knowledge/watches.json` and a shadow log.
  - It never enters the $500 book, the measuring books or the account.
  - That forward record is read once, after 30 independent events, with these pass marks and with the NDAX drop-time cost deciding.
  - Anything beyond recording needs Madhav's separate yes, after the 14 Dec review.
- **A fail:**
  - It is written up as a lesson with its numbers: the bounce before costs, and the cost it lost to.
  - That goes in the research cards and the facts Ask reads.
  - No watch is added.
- **Either way:**
  - The result file `docs/research/REVIEW_41_RESULTS.md` records this pre-registration's commit.
  - The change book gets its line, and the look count is updated.

## 6. Not in this review
- resting limit orders below the price (the next question, if a bounce exists before costs);
- shorting;
- other windows or holds;
- coins outside PIT30;
- anything from 2026-08-01 on, the live window included;
- what happened after the drops in the NDAX month: that month is the fresh test of the pre-registered reviews and is read on 14 Dec.
