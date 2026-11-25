# India stress test v1: scenarios and pass marks (written Tue 24 Nov 2026, before any run)

Madhav, 24 Nov 2026, in chat: "Some moments are too rare to wait for ... We are testing in environments where we can fail and nothing happens still. I want to perform some fail tests on Ananta India." Then: "We will do it twice. Once now, and the next one is after 30 sessions before live. We like the way everything is working now. So let's keep that as benchmark performance and start ... Even if it didn't improve, it shouldn't drop the performance."

**What this is.** A test of where Ananta India breaks, on days far worse than the 30 calm sessions of the evidence window. It never trades, never touches the live paper books (it works on copies in memory), and never changes a rule. It reads research data from 2000-2023 only (the sealed 2024+ tree is not read). A finding that points at a rule becomes a proposal for Madhav's yes, through the change door.

**Run 1 is the benchmark.** The system as it stands on 24 Nov 2026: records 87bb9af, app 2710e68, `paper_config.json` sha 8a6493dae5dd5d99 (managed-v3 of 21 Nov), the options line SP1 v2 (spec 37e918d37d0f1e3f). Run 2 comes after the 30th clean session, before the go-live decision (flag 238), on the same scenarios, the same seed and the same marks.

## What is stressed: the two things that would go live

1. **The managed stock book** (the paper copy of the account plus its replacements), as it stands after the 23 Nov session: its holdings, quantities, stops and cash, read from `paper/managed/state.json`. The options money inside it (Rs 50,000) is stressed under 2.
2. **The options line** (SP1 v2): one lot of a Nifty or Bank Nifty option, bought in the morning and held to the next session's open or its stop, with the Rs 50,000 the go-live plan sets aside.

The practice book (research families at Rs 50,000 notional each) does not go live and is not stressed in v1.

## The scenarios

Historical (each stock's own real moves on those days; Nifty 500 for comparison):

| id | window (sessions) | what happened |
|---|---|---|
| H1 | 20 Feb - 7 Apr 2020 | COVID crash and first rebound (Nifty -38% peak to low) |
| H2 | 23 Mar 2020 | the worst day: Nifty -13.0%, opened -9.1% |
| H3 | 29 Sep - 27 Oct 2008 | after Lehman; 24 Oct -12.2% |
| H4 | 14 - 25 Jan 2008 | the January 2008 crash; 21-22 Jan |
| H5 | 13 - 18 May 2004 | the election shock: -7.9%, -12.2%, then +8.3% |
| H6 | 8 - 21 Nov 2016 | demonetisation and the US election night gap |
| H7 | 7 Jan - 20 Nov 2008 | the slow bleed: months of falls (tests the 22% pause) |
| H8 | 28 Aug - 26 Oct 2018 | IL&FS: a financial-stock crash with the Nifty far less down |
| H9 | 18 May 2009 | the up shock: Nifty +17.7% in one day |
| H10 | 10 - 28 Aug 2015 | China devaluation; a moderate fall |

Combined (never happened, built from real pieces):

| id | what |
|---|---|
| C1 | the two worst days back to back: each stock's own 23 Mar 2020 move, then its own 24 Oct 2008 move |
| B1 | 2,000 made-up 20-session paths, each four blocks of 5 real consecutive sessions drawn from crisis periods (Nifty 50 more than 10% under its 60-session high), 2003-2023; every stock takes its own move on each drawn day, so they fall together as they did. Fixed seed 20261124 |

Options line nights: a long at-the-money option held overnight into each of the five worst opening gaps against it, both ways, Nifty and Bank Nifty, 2008-2023 (index opens before 2008 are not reliable in our index file). Bank Nifty's row for 27 Feb 2009 (-14.8%) is excluded: the bank stocks rose that day, so the index row is a data fault.

Machine and words (the crash day put in front of today's code):

| id | what |
|---|---|
| X | a named list of failure-path tests in both repos must pass: stale inputs marked not dropped, a lapsed Kite sign-in, a holiday on the next day, no model, a gap through a stop, a buy not chased, an order call refused, the sealed holdout refused, a holding with no price |
| W1 | the Ask after a -13% close (the H2 day, today's holdings) |
| W2 | the Ask mid-session with no live prices (the sign-in lapsed) on a falling day |
| W3 | the Ask after a +17.7% day (H9) |
| W4 | the Ask after weeks of falls, the book 25%+ under its high (H7) |

## How the money replay works (fixed before the run)

- Start: each holding at its 23 Nov close. Day by day, each holding moves by its own real close-to-close move on the scenario day.
- A holding with no bar of its own that day takes the median move of stocks with its industry label that day (5 or more stocks), else the Nifty 500's. NIFTYBEES takes the Nifty 50. A single-day move over 40% either way is treated as a data fault (unrecorded splits, data audit of 29 Oct) and replaced the same way. The count of stand-in moves is reported.
- Exits are the book's own code: `india.managed.exits` with the live config. A replacement whose close is at or under its stop is sold at the next session's real open (the stock's own open-to-previous-close ratio) less 0.1% slippage and `india.costs` delivery costs. The book's original holdings leave only through the evening cut list, which needs live features, so they are held (the stress is the harsher for it). The 200-day exit is not tested (it needs 2024+ prices).
- Survival rules (record only on paper): a day whose loss reaches 5% of the book at the start of the session, and how much of it came at the open (where the rule cannot act); the first day the book is 22% under its high.

## Pass marks

Money (the stock book's stocks and cash):
- **M1:** in each historical scenario, the book's deepest fall is no more than 1.25 times the Nifty 500's over the same sessions.
- **M2:** in B1, the book's 99th-percentile 20-session loss is no more than 1.25 times the Nifty 500's.
- **M3:** in C1, the book's two-day loss is no more than the Nifty 500's plus 5 percentage points.
- Watch, never a fail on its own: gap-through-stop losses; days where the open alone was past the 5% daily limit; the day the 22% pause would come.

Options:
- **O1:** at the largest premium the line had paid by 23 Nov (Rs 34,664), the worst single night costs no more than half of the Rs 50,000 options money.
- **O2:** at the line's median premium, the same, no more than a quarter.
- Two indices open the same night are added together.

Machine: **X:** every named test passes.

Words, each turn checked three ways (the today-block check `livesession.check`; must and must-not words; the nightly grader):
- **W-a:** no turn contradicts its moment, invents the day's move, promises a recovery or tells him to act with real money now. All turns.
- **W-b:** the grader passes at least 80% of the turns.

## Run 2: the no-drop rule

Run 2 runs everything again on the same scenarios, seed and marks, two ways:
1. **The benchmark's own holdings under the code of that day.** Every money figure must be no worse than run 1 by more than 0.5 percentage points, and every pass stays a pass. A drop names the change that caused it, and that change is undone or brought to Madhav.
2. **The holdings of that day.** Reported beside run 1, read as exposure, not as a code change.

Machine must still pass in full; words must pass at least as many turns as run 1. A change that improves a mark is kept only if no other mark drops.

## Addendum for run 2 (written 24 Nov 2026, before run 2)

Madhav, 24 Nov 2026: "Yes please, draft it and save it for the next audits and tests" (the audit question bank v2, app `docs/repair_shop/audit/2026-11-24-question-bank-v2.json`). Run 2 also asks the bank's core groups C (outages), D (crash moments) and E (pressure) at stand-in moments. Their counts are reported beside W-a and W-b, not in the no-drop comparison with run 1, which did not ask them. They become the benchmark for those groups at the next audit.
