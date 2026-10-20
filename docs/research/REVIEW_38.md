# Review #38 (pre-registration): when Ananta "catches" a big move, does a book allowed to trade make money from it?

**Status: PRE-REGISTERED, forward test.** Written 2026-10-20 (about 14:30 UTC) and pushed before any outcome dated after the
push was computed. Sources: the decision audit of 13 to 20 October (sections 1.4 and 4.2, fix 3) and the gate and pipeline review
of 20 October (Part 2, step 1). Forward window 2026-10-21 00:00 UTC to 2026-12-14; one look, at `CHECKPOINT-60`. Until
`REVIEW_38_RESULTS.md` exists there is no result. (This is review #38. Request #38, the breakout, is tested in review #32.)

## Why
- **How the study counts a catch.** The missed-moves study (`jarvis/service/missed.py`) labels each of the day's biggest up-moves
  CAUGHT when any paper trade of ours was in it (`missed.what_we_saw`). That means an evidence trade entered by 2 hours after the
  move's low and not closed before it, or an Explorer trade or order around the low. The kind of book does not matter.
- **What a catch earned (13 to 20 Oct):**
  - the study counted 15 catches, and the account (the $500 book) caught none of them;
  - 22 of the 28 catching trades belonged to books classed "won't take again" (zone touch 13, Explorer 9);
  - the 28 trades made +$7.85 together. One AVA tier-C zone-touch trade (+$54.23, counted on three separate days) carries that
    total; the other 27 lost $46.38.

**The question in plain words:** when Ananta "catches" one of the day's big moves, does a book that is allowed to trade actually
make money from it?

## The tier that decides
- **The moves:** every row the study writes (`missed_moves`) for days from 2026-10-21 to 2026-12-14, on all three of its tiers
  (UNIV, LIVE10 and T30), pooled. Each tier is also reported on its own.
- **Event count:** market days, the move's day (`missed.py` counts days). An event is a day with at least one move caught by an
  allowed book.
- **The money object:** each distinct catching trade, counted once however many moves it is in.

**Allowed books, frozen now from `docs/knowledge/strategy_status.json` at 448cb21:** strategies whose verdict is not
`wont_take_again` and whose status is not PARKED or RETIRED, without the random baselines.
- `BOOK500`: the $500 book (holdings from the `book500` state and `book500_fills`);
- `T3`: the 10-coin trend book (MAIN, fills in `portfolio_book.sqlite`), and `T3_T30`, the 30-coin trend book (MAIN, fills in
  `portfolio_book_t30.sqlite`);
- `H07`: the watches `H07`, `H07-UA`, `H07-UB`, `H07-UC` and `H07-T30`;
- `JARVIS` and `BOLD`: the watches `JARVIS` and `JARVIS_BOLD`;
- `READS`: `M1a`, `M2a`, `M2a-G`, `M3a`, `M3b` and their `-UA`, `-UB` and `-UC` copies;
- `MANUAL`: Madhav's own paper fills (`manual_fills`).

A watch's tier copy belongs to its base strategy: strip a trailing `-UA`, `-UB`, `-UC` or `-T30`.

**Not allowed:** `ZONE_TOUCH` and its tiers, the Explorer (every setup), HOURLY, CANDIDATE, and every random baseline (`RANDOM*`,
`JARVIS_RANDOM`, `RANDOM_BOLD`).

## The test
**CAUGHT_ALLOWED.** A move is CAUGHT_ALLOWED when an allowed book was in it by missed.py's own rule for evidence trades: entered by
2 hours after the move's low (`low_t`) and not closed before the low.
- For the T3 books and the $500 book, "in it" means the book held units of the coin at `low_t`, or bought it by `low_t` plus 2
  hours, from its fills.

**Each catching trade's result, per $100:**
- evidence trades: `net_usd` (they are $100 trades);
- the T3 books and the $500 book: the holding's round trip from its buy fill to its sell fill, after the book's own fill costs, per
  $100 bought;
- `MANUAL`: the same from its fills;
- a trade or holding still open after the 2026-12-14 daily close is marked at that close.

**z** = mean of day values / (standard deviation / square root of the number of days). A day's value is the mean result of the
distinct trades first counted on that day.

**Measures, all reported:**
1. Moves CAUGHT by the study's own label, moves CAUGHT_ALLOWED, and moves caught by the account (`BOOK500`).
2. The mean result per $100 of the distinct catching trades of allowed books.
3. The same mean without the single largest trade.
4. Beside, not judged: the same money figures for the catches of books that are not allowed.

**Data, all recorded today:** `missed_moves` (day, coin, low_t, high_t, tier), `evidence_trades`, the two T3 books' `fills`,
`book500` and `book500_fills`, `manual_fills`, and `universe_bars.d1` for the marks. Nothing is built. No recorder is needed.

**Code version:** every function named here is used as it stands at origin/jarvis-4 commit 448cb21 (this file's parent commit).

**If missed.py changes in the window.**
- The audit's fix 3 relabels CAUGHT. This review labels from the raw rows (moves and trades), so the relabelling does not affect
  it.
- If the move detection itself changes (`MIN_PCT`, `MIN_ATR`, `MAX_MOVES` or the move window), rows written after the change are
  reported separately and not counted.

**Forward window and looks.**
- Window: moves on days from 2026-10-21 to 2026-12-14, with results marked at the 2026-12-14 close.
- Looks: **one**, at `CHECKPOINT-60`, run after the 2026-12-15 00:05 UTC daily close.
- Counting days first is not a look; computing any trade result for the caught moves is. If the count is under the minimum,
  nothing else is computed; only Madhav can extend the window, and the one look moves with it.
- Cells: 1, in the family "the missed-moves study".

**Holdout.**
- The morning review and the Evidence page show the study's CAUGHT, SEEN and MISSED counts every day. Those displays existed at the
  push and are the running system. They are not a look.
- Nothing today shows the allowed books' catches with their money.
- If the audit's fix 3 is built in the window, it may relabel and count, but it must not show the money column for the window
  before `CHECKPOINT-60`. If it does, this review reads "seen in the window".
- Any computation of measures 2 or 3 before `CHECKPOINT-60` is a look, and the results file names it.

**Lake header.**
- The results file opens with `format_header(lake_header(D, until=2026-12-15 00:00 UTC))` over the coins of the window's move rows,
  with D their universe daily candles in the window. If the weekly lake job has not reached the window's end, `until` is the
  lake's last complete day, and the header says so.
- Directly under it comes the live-feed line: the study's nightly runs expected and present (the `missed:<day>` and
  `missed_t30:<day>` traces in `engine_state`), the days a tier failed, and the coins with gaps in their daily candles.
- A result without both is a draft (RESEARCH_RULES section 4).

## Pass marks (frozen)
- **INSUFFICIENT:** fewer than 10 market days with a CAUGHT_ALLOWED move.
- **CATCHES_EARN:** both hold:
  - the mean of day values is above 0 with z of 2.0 or more;
  - the mean result of the distinct catching trades is still above 0 with the single largest trade removed.
- **CATCHES_DO_NOT_EARN:** the mean is 0 or below, or it is 0 or below once the largest trade is removed.
- **UNCLEAR:** everything else.

## What each outcome changes (decided now)
Nothing changes by itself. Each line is a proposal to Madhav after the window, in the order he sets (LOCK section 9).
- **CATCHES_DO_NOT_EARN:** propose that "caught" is never shown as a success. The study, the morning review and the brain's pattern
  knowledge say "in it", with the allowed books' result beside it and the account's catches shown on their own.
- **CATCHES_EARN:** propose "caught with a profit (allowed books)" as a line of the learning-loop section and as a candidate gate
  measure (a `gate_definition` change, so Madhav decides).
- **UNCLEAR or INSUFFICIENT:** reported. The audit's label fix stands on its own reasoning.

## Not in this review
- The missed and seen moves (review #32 tests the breakout pattern).
- Whether a move could have been caught at all: the "low to high" figure is hindsight.
- Judging the books that are not allowed: their catches are reported beside, not judged.
