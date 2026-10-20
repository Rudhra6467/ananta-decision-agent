# Review #37 (pre-registration): the bold book against its random twin, and whether its cited rule backed the coin

**Status: PRE-REGISTERED, forward test.** Written 2026-10-20 (about 14:30 UTC) and pushed before any outcome dated after the
push was computed. Sources: the decision audit of 13 to 20 October (sections 1.3, 3 and 4.4, fix 2) and the gate and pipeline
review of 20 October (sections 1.3, item 6, and Part 2, step 1). Forward window 2026-10-21 00:00 UTC to 2026-12-14; one look,
at `CHECKPOINT-60`. Until `REVIEW_37_RESULTS.md` exists there is no result.

## Why
- **The book.** The bold book (agent fix A8, `jarvis/service/bold.py`; mandate in `docs/knowledge/bold_mandate.json`) must take its
  single best tier-A idea on every dial-open day: $100 of paper, against a random tier-A twin (`RANDOM_BOLD`) opened at the same
  moment with the same plan.
- **Unaudited.** It is the only stream of brain decisions that can buy while the dial is open, and no gate check audits it
  (`agent_no_failed_rules`, `strategy_regimes` and Q7 all leave it out).
- **Its record so far (15 to 20 Oct):** 4 TAKEs (BTC on 15 and 16 Oct, AAVE on 17 Oct, SUI on 20 Oct) and 2 WOULD_ADD. The four
  trades are marked at -$0.70 together, their twins at -$5.20: too early to read.
- **The cited rule.** Every bold TAKE in that week (4 of 4) cited T3, the trend book, yet T3's own rule rated the coin OUT that
  day: BTC, AAVE and SUI had closed under their 20-day average. The brain read T3's 20-day exit as a 20-day hold. The audit judged
  3 of the 6 bold decisions wrong (section 3, rows 9 to 11): AAVE and SUI for this cause (i), and the second BTC buy as the same
  bet twice. BTC on 15 Oct was right, but on the dial rule (review #25), not on T3.

**The questions in plain words:**
- **(A)** Does the bold pick beat a random tier-A coin traded the same way?
- **(B)** When the bold book cites a rule as its reason, did that rule actually rate the coin IN on that day?

## The tier that decides
- **The population (decides):** bold TAKE decisions (`bold_decisions`, action TAKE) from 2026-10-21 00:00 UTC to 2026-12-14
  23:59 UTC.
  - A uses each TAKE paired with its twin by `trade_id` and `random_id`. A TAKE without a twin (the twin's price was stale) counts
    in B and is left out of A.
  - B uses every TAKE.
- **Reported beside, never counted:** the 4 pairs opened from 15 to 20 Oct.
- **Event count, A:** market days. Pairs whose bold leg closes on the same UTC day count once (review #29's count). The bold book
  has no ledger question of its own, and Q7's three-day chaining would make a once-a-day book a single event for the whole window.
  Legs marked at the window's end share that day.
- **Event count, B:** one per TAKE. It is a check of the process behind each decision, not a market result.

## The test
**A.**
- **Value per pair:** the bold net minus the twin net, in $ per $100 after each leg's own cost.
- A leg still open after the 2026-12-14 daily close is marked at that close with `watch_engine.net`. Both legs are treated the same
  way.
- **z** = mean of event values / (standard deviation / square root of the number of events).

**B.**
- **"Cites T3":** the TAKE's `thesis` or `why` text contains the T3 card's id or one of its aliases in `status_cards.json` ("T3",
  "trend portfolio", "portfolio layer"), ignoring case. The model's `knowledge_used` list is not saved in `bold_decisions`, so the
  text is what is recorded.
- **T3's rating that day:** the coin's entry in the `ratings` of the T3 book's decision for that daily close:
  - `portfolio_book.sqlite` for the lab 10;
  - `portfolio_book_t30.sqlite` for the 28 coins of the 30-coin tier;
  - for a coin in neither book, `portfolio_layer.rate` computed from the universe daily candles to that close: EMA20 and EMA50 of
    the closes, and Bitcoin's close against its own EMA50, as `daily_view` builds them.
- **IN** means the rating is STRONG, OK or WEAK (`hold` true). **OUT** is anything else.

**Reported beside, not judged:**
- A split by "cited rule rated IN" and "cited rule rated OUT" (counts only when a side has fewer than 10);
- the mandate misses (`MISS` rows) and the WOULD_ADD days;
- the mandate's other two benchmarks, doing nothing and the market median over the same days.

**Data, all recorded today:** `bold_decisions`, `evidence_trades` (`JARVIS_BOLD`, `RANDOM_BOLD`), the two T3 books' daily
`decisions`, and `universe_bars.d1`. Nothing is built. No recorder is needed.

**Code version:** every function named here is used as it stands at origin/jarvis-4 commit 448cb21 (this file's parent commit).

**Changes in the window.**
- The audit's fix 2 (give the bold pack each candidate's T3 rating and the dial rule as facts) changes the inputs of this
  registered experiment. It needs Madhav's OK first.
- If it happens, the window is split at the date written in `bold_mandate.json`. A is judged on the whole window, with each part
  reported. B is judged on each part separately, because fix 2 is aimed at B.
- Any other change to the mandate or the bold pack splits the window the same way.

**Forward window and looks.**
- Window: TAKEs from 2026-10-21 00:00 UTC to 2026-12-14 23:59 UTC, marked at the 2026-12-14 close.
- Looks: **one**, at `CHECKPOINT-60`, run after the 2026-12-15 00:05 UTC daily close.
- Counting first is not a look: events for A, T3-citing TAKEs for B. Computing any pair value or any IN/OUT share is.
- If a count is under its minimum, that part computes nothing; only Madhav can extend the window, and the one look moves with it.
- Cells: 2 (A and B), in the family "the brain's picks against random" (with Q7 and review #33).

**Holdout.**
- `bold.record` (the bold book against its twins) is shown in the app. That display existed at the push and is the running system.
  It is not a look as long as nothing in this file, or in the mandate, changes because of it.
- Any computation of A or B before `CHECKPOINT-60` is a look, and the results file names it.

**Lake header.**
- The results file opens with `format_header(lake_header(D, until=2026-12-15 00:00 UTC))` over the coins of the counted pairs
  (both legs), with D their universe daily candles in the window. If the weekly lake job has not reached the window's end, `until`
  is the lake's last complete day, and the header says so.
- Directly under it comes the live-feed line: the daily candles expected and present per coin, the days the bold book did not run
  (budget, guard or switch), and the days a T3 book wrote no decision.
- A result without both is a draft (RESEARCH_RULES section 4).

## Pass marks (frozen)
**A:**
- **INSUFFICIENT:** fewer than 10 events.
- **BOLD_BEATS_TWIN:** all three hold:
  - the mean event value is above 0 with z of 2.0 or more;
  - the bold pick is ahead in more than half of the events;
  - the mean is still above 0 with the single largest event removed.
- **TWIN_BEATS_BOLD:** the mirror: mean below 0 with z of -2.0 or less, the twin ahead in more than half of the events, and still
  below 0 with the largest event removed.
- **NO_DIFFERENCE:** everything else.

**B:**
- **INSUFFICIENT:** fewer than 10 TAKEs that cite T3.
- **CITES_SOUND:** at most 10% of the T3-citing TAKEs had the coin rated OUT that day.
- **CITES_UNSOUND:** more than 10%.

## What each outcome changes (decided now)
Nothing changes by itself. Each line is a proposal to Madhav after the window, in the order he sets (LOCK section 9).
- **BOLD_BEATS_TWIN:** propose that the bold book's record counts as evidence that the brain picks well with the dial open. `BOLD`
  stays EVIDENCE in `strategy_status.json` until Madhav decides. No money.
- **TWIN_BEATS_BOLD:** propose stopping the bold book or rewriting its mandate. Madhav decides.
- **NO_DIFFERENCE or INSUFFICIENT:** reported; the book keeps running if Madhav wants it to.
- **CITES_UNSOUND:** propose two code changes, each needing Madhav's yes:
  - the bold pack carries each candidate's T3 rating and the dial rule as facts, and `bold.check` rejects a pick that cites a rule
    rating the coin OUT;
  - `agent_no_failed_rules` includes the bold book (gate review, section 1.5).
- **CITES_SOUND:** reported. If fix 2 was applied, this is its forward check.

## Not in this review
- The bold book's stop trigger (review #31 covers it).
- The no-stacking rule (added 16 Oct).
- Which knowledge cards moved a pick: citation is not influence (RESEARCH_RULES section 6, `OD-CARD-INFLUENCE`).
- Dial-closed days, unless they happen; they are reported beside if they do.
