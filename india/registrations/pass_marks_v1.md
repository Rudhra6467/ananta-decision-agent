# India trials: pass marks (v1, written Mon 23 Nov 2026)

Madhav, 23 Nov 2026, in chat: "Yes please". He was answering flag 235: write a pass mark for each India trial before its finish day.

**Honesty note:** these marks were written after the trials' interim numbers had been shown on the trials page. Each mark is set from the trial's own registration and its random control, not from those interim numbers. A pass means "go to the next step". It never means "proven". Twenty sessions are too few to prove an edge. Nothing here changes a paper rule. These marks only say how each finish day is read.

## The options line (SP1): 20 scored sessions, read on Wed 25 Nov, each index on its own

**PASS (for a live start of 1 lot)** needs all four of these:
1. Its net rupees with realistic fills are above zero over the 20 sessions.
2. It is still above zero with its single best trade removed. A line that one trade carried has not shown it can repeat.
3. The mean net index move per trade, after costs, is above zero.
4. No stop or exit rule was broken in the record. Every trade's exit matches its registered exit (sp1_v2.json).

**FAIL** is any of the first three.

**Watch**, never a fail on its own:
- a premium above 25% of the Rs 50,000 options money (G-15/G-16 review);
- realistic fills more than Rs 500 a lot worse than the study fills.

## RX1, the avoid-or-exit trial: 20 sessions, about 27 Nov

- **History:** stocks falling 2%+ under their 200-day did -0.18% (2000-2017) and -0.12% (2018-2023) against the average liquid stock the next session.
- **PASS** needs the mean difference over 20 sessions to have the same sign as history and be at least half its size: -0.06% or lower.
- **FAIL** is a mean above zero.
- **INCONCLUSIVE** is anything in between.

## The shadow trader: 20 sealed sessions, about 27 Nov

- **PASS** needs both of these:
  1. At least 12 of its 20 stances (trade as planned, stand down, reduce risk) are right.
  2. Its right share is above the share it would get by always giving its most common stance.
- **FAIL** is otherwise.
- Its watch names are reported, never a pass mark: 20 sessions is far too few for them.

## The no-chase filter: 20 decision days, about 30 Nov

- **PASS** needs both of these over the same 20 days:
  1. The filtered books' expectancy after costs is at least their own record before the filter.
  2. It is at least the random control.
- **FAIL** is either one below.

## RS, the relative-strength trial: 20 sessions, about 2 Dec

- **PASS** needs both of these after costs:
  1. The RS picks beat the average liquid stock.
  2. They beat the random book of the same size.
- **FAIL** is otherwise.
- RS1 was INCONCLUSIVE in history, so a pass here only earns a second, registered study. It never earns a live rule.

## The managed book and your portfolio's twin: 60 sessions (Jan 2027)

- **PASS** needs the managed book's stocks and cash, options left out, to beat your holdings left as they were over the same sessions.
- The options lot is judged only by the options line above.
- The record is split at the decisions of 17 Nov (managed-v2) and 21 Nov (managed-v3). Each split is reported on its own.

## The practice book: 60 sessions

- **PASS** for a family needs both of these after costs:
  1. Its expectancy is above zero.
  2. It is above that family's random control.
- A family that fails stays on paper.

## Going live (Madhav, 23 Nov 2026)

Madhav, 23 Nov 2026, in chat: "let's wait for 30 clean sessions as mentioned and decide after that on going live ... if everything is running well and as per plan. And check the reconstruction, comparison analysis results. And if everything works good, looks good and feels good. Go live with options and stocks. Stocks - connect to zerodha and start working on them. Options - a 50000 is allocated for trading. Anytime after 30 sessions and good confidence."

The checklist for that day, all of it read from the system:
1. **G02:** 30 clean sessions in a row (23 on 23 Nov).
2. **The trials:** read against the marks above.
3. **The reconstruction:** its findings, and whether any changed a rule.
4. **The comparisons:** the options line against the index move; the managed book against the holdings left alone; the practice book against random.
5. **The gate's last parts** (INDIA_LOCK.md Rule A):
   - Madhav's written yes;
   - the order module reviewed;
   - the survival rules switched from record to enforce.
6. **Live options:** Rs 50,000, starting with 1 lot and a premium cap, with the paper line run beside it for 10 sessions to compare fills.
   - **The cap (Madhav, 24 Nov 2026, in chat: "yes to all your recommendations", after the stress test, flag 247):** a trade whose 1-lot premium is above Rs 25,000 is skipped, and at most one options position is held overnight. Live only: the paper line stays as frozen (SP1 v2), so its record and its clock are not split. Why: in the stress test (`stress_results_2026-11-24.md`) one bad night cost about all of a trade's premium, and both indices held overnight at their largest premiums would cost Rs 51,329, more than the whole Rs 50,000. With the cap the worst night stays near half the money; an ordinary trade can still lose about 40% of it in one bad night.
7. **Live stocks (same yes, flag 239):** broker-side stop orders at each stop (Zerodha GTT) so a stop does not wait for the next morning's open, and the survival rules (5% day, 22% pause) set to enforce. The book's 8 original holdings carry no stop; that is noted for the live day, not changed on paper.
