# Research rules: how a review is asked, run and read

Written 2026-10-15 from the research audit (cards LAW, PDLAW, BESTPF, COST-TEST, LAKE-1 to LAKE-5, R22-PIT30, 5M-FREEZE, STUDY:CASEBOOK, REGISTRY,
APP-LABMACH, FRAMEWORK and the reconstruction audit). These rules were scattered over old Grok-era files and review texts; this is the one
place. They apply to every crypto review from #31 on. Ananta Canada keeps its own frozen C0 rules and shares nothing with this file.

A review that breaks a rule here is not a result; it is a draft.

## 1. Asking the question: the pre-registration

Every review starts as `docs/research/REVIEW_N.md`, written before the data is touched, with these headings (the shape reviews #29 and #30 used):

1. **Why**: the question, and what prompted it.
2. **The tier that decides**: one of LAB10, TOP30, ALL120 or a point-in-time list (PIT10, PIT30, tier A). Say which one decides; the others are
   reported beside it and never rescue a failed one (LAKE-5). Judge on a month-by-month list wherever the list can change over time.
3. **The test**: one rule, parameters from the data's own distribution (section 3), nothing tuned afterwards, the periods (discovery, confirm; the
   old holdout is spent, section 4), the baseline (random entries with the same exit and the same coins), and the costs (section 5).
4. **Pass marks (frozen)**: numbers. A minimum count of independent events (section 2), the same sign in both periods, a z-score bar, the
   after-cost figure, and the 2x-cost and no-burst checks where they apply.
5. **What each outcome changes (decided now)**: the files, cards, gate checks and books a pass or a fail touches. Decided before the result so the
   result cannot bend it.
6. **Not in this review**: what is deliberately left out.

**The outside timestamp.** The pre-registration commit is pushed to `origin` before the run; GitHub's push time is the timestamp that does not
depend on the session that wrote it. The result file records that commit's hash. A pre-registration written and run in the same minute with no
push in between is marked "unanchored" in the result.

**One question at a time.** Reviews run one after another in the numbered queue (`docs/repair_shop/ledger.json`, `queue`), never as a sweep.
Every review adds its cell count to the family's running look count (REVIEW_15 judged about 97 cells in one day; the 660 looks of the first
relationship hunt are carried by anything born from it). A pass found after many looks is read against that count, not on its own.

**Rule B.** Inside the evidence window no review creates a new crypto strategy. A re-test of an existing idea is queued for the period
after the window (the list is in `docs/LOCK.md`, section "After the window") and runs under these same rules.

## 2. Counting

- Count **independent market events**, not rows, bars or trades. Coins that fire together on one day are one event (`missed.py` counts market
  days; `evidence_live.py` shows one event count everywhere).
- One definition and one count per object. When two files disagree, the later review wins and the older text gets an erratum
  (`docs/research/GROK_ERA_ERRATA.md`), never a silent edit of a frozen result.
- Every script logs the date range it read and the number of days it dropped (section 4).
- Say "sample size" and "independent events" side by side in every table that quotes a result (`docs/VARIABLE_REGISTRY.md` does).

## 3. Parameters: the parameter-discovery law (PDLAW, BESTPF)

1. Never seed a study with a textbook default (ATR 2.5, a 14-bar indicator, a $3 move).
2. Measure the quantity's distribution on the data first, freeze two or three data-derived candidates, then replay, then apply the economic gate.
3. After the pass marks are frozen, no parameter moves because of what a profit factor looked like.
4. "Least bad of five losers" is not a KEEP. A row that only looks best among pre-chosen losers is written down as exactly that.
5. A volume ratio is called a volume ratio. "z-score" is reserved for a real standard score.

## 4. Data: the lake and the lists

- **Header of every review** (`src.lake.research.lake_header(D)`, printed by `format_header`): coins alive per year, the number of days dropped under the 97%-of-minutes rule, the
  coins cut by `BREAKS` and `ENDS` (token swaps and re-used tickers), and the quality grades. A review without its header is a draft.
- **Default test list**: the point-in-time lists (`src/lake/pit.py`: PIT10 and PIT30, by month, using only earlier data), because a list chosen with
  today's knowledge flatters a rule (review #22: T3-B +26.1% on today's 30, -22.5% on the coins that really were the 30).
- **Renames** (MATIC to POL, FTM to S, RNDR to RENDER): join Binance and NDAX symbols by the rename table (`RENAMED` in `jarvis/service/tier30.py`) before
  counting coins, so one coin is never two.
- **The holdout is spent.** The lake's holdout (from 2026-08-01) has been looked at (reviews #22 to #30); it is no longer fresh. The next holdout is
  live data after a stated date, written in the pre-registration. An untouched holdout is never inspected early.
- **One source per number.** The old 15-minute tape (`lab10_15m_merged`, outside git) joins two sources with no conversion and no venue column:
  Kraken USD to 2026-03-31, Binance USDT from 2026-04-01, and ETH has no bars from 2026-04-01 to 2026-09-03. The lake (`src/lake`) is Binance
  USDT only. A study that joins sources adds a source and quote column to every bar and reports before and after the join separately; a result
  that crosses the old tape's seam is marked "source change" until it is re-run on one source.
- **Time**: look prices up by clock time, never by row offset; a trailing feature is trailing and a forward one is forward.

## 5. Costs

- The venue's own all-in cost: NDAX's 0.20% fee a side plus the coin's half-spread. For the ten lab coins the half-spreads are one NDAX snapshot
  (2026-09-29, one sample each) in `src/intelligence/ndax_costs.py`, the only copy; the dated sample count sits beside the numbers. Every other
  coin is an assumption, labelled as one: `jarvis/service/registry.cost()` charges the larger of three times its Binance half-spread and its
  tier's floor. The worker Mac's minute-by-minute NDAX bid and ask (`jarvis/service/ndax_spreads.py`) is evidence, not yet a setting: stage S2
  (about 2026-10-25) reruns the $500 backtest with each coin's 75th-percentile half-spread, and Madhav decides what changes.
- Never a 0 to 10 basis-point table for a decision. A fee screen run at placeholder costs is marked "indicative" and is not cited.
- Before testing any new exchange, replace the cost default with that venue's schedule and state the date it was read ("check current rule").
- Placeholder results (old library numbers, the 8 bp haircut) are never quoted.

## 6. Reading a result

- Evidence is what the pre-registered rule says it is. A card that was cited is not a card that mattered: before claiming a card changed a
  decision, log the decision with and without it (the exam and the counterfactual log are the tools); citation is not influence.
- A strategy's status comes from one file, `docs/knowledge/strategy_status.json`; the nightly build step (`jarvis/service/knowledge_build.py`,
  `align`) makes `watches.json` and the cards' permissions in `status_cards.json` agree with it and reports any drift it will not decide. A card's
  evidence word (SUPPORTED, WEAK, CONFLICTING, INSUFFICIENT, REJECTED, UNTESTED; defined in `status_cards.json`) changes only when a
  pre-registered review decides it. Brain text and docs quote these words, they do not coin their own.
- A failed review is kept as a lesson with its numbers (EXITS, STOP_ZONE), never quietly deleted.
- Other traders are reference and event generators, never teachers or signals (D8).

## 7. The casebook

Madhav's own trades go in `docs/casebook/cases.json` the day they happen, in one format, **with the reason he gave at entry time** (not a reason
reconstructed later) and with the losers. A case is context, never evidence. Re-testing an entry read against the casebook waits for at least 30
cases.

## 8. New markets

Build the data layer first: raw and adjusted prices and corporate actions stored separately, every outside event stamped at its public release
time, overnight and weekend gaps handled inside every "move" and "stop" definition. The process carries over; the findings do not. Ananta
Canada's frozen C0 rules govern its own work.
