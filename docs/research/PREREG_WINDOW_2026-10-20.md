# Pre-registrations for the evidence window (2026-10-20)

Rule B parks every new crypto study until the window ends (LOCK section 1). These eight reviews are the parked findings of 13 to
20 October, each written as a pre-registration now, so that each gets a clean forward test on the window's own live data. That
live data is the fresh holdout RESEARCH_RULES section 4 asks for: "live data after a stated date, written in the
pre-registration". Nothing is built, nothing runs and no rule changes. Each review is scored once, at `CHECKPOINT-60`, and every
outcome is a proposal to Madhav after the window, never an automatic change.

Sources: the gate and pipeline review of 20 October (Part 2, section 2.3, step 1) and the decision audit of 13 to 20 October
(sections 1 and 3, and its ranked fixes).

## The eight reviews

All eight are **PRE-REGISTERED**, pushed on 2026-10-20 to branch `prereg-window` (not merged). Each has the forward window
**2026-10-21 00:00 UTC to 2026-12-14** and **one look, at `CHECKPOINT-60`** (2026-12-14, run after the 15 Dec 00:05 UTC close).

| Review | Finding | The one line Madhav needs |
|---|---|---|
| [#31](REVIEW_31.md) | STOP-CLOSE vs STOP-TOUCH | Our paper stops sell on any touch, but the written rule waits for a daily close; by 14 Dec we learn which loses less, and whether the stop fills were real NDAX prices. |
| [#32](REVIEW_32.md) | PW-BREAKOUT-38 (request #38) | Does buying a coin that closes above its recent high, far from support, make money after costs? It is scored on live data, and nothing trades it. |
| [#33](REVIEW_33.md) | Random beat the pick (the 14 Oct ticket) | Does Jarvis's own pick beat a random coin? Probably too few buys to tell by 14 Dec, because the brain buys only measured setups. |
| [#34](REVIEW_34.md) | PASS quality and the ranker | Are the brain's "no" answers right, and does its ranking send it the right coins? The ranking half may have too little to judge. |
| [#35](REVIEW_35.md) | The attention score | Do the coins the attention score flags do better? It measures only, and it does not touch your 31 Oct decision. |
| [#36](REVIEW_36.md) | Room to a target | Does the Explorer's "room to a target" check throw away better trades than it keeps? It concerns the Explorer only; no book that trades changes. |
| [#37](REVIEW_37.md) | The bold book against its random twin | Does the bold book beat its random twin, and when it cites a rule, did that rule actually back the coin that day? |
| [#38](REVIEW_38.md) | Caught moves that earned money | When we "catch" a big move, did a book that is allowed to trade actually make money from it? |

Review #38 is not request #38: request #38 (the breakout) is tested in review #32.

## The rules all eight share
- **The anchor.** The commit that adds these files is pushed to origin before any of the window's data exist. GitHub's push time
  is the outside timestamp, and each results file records that commit's hash (RESEARCH_RULES section 1).
- **The code version.** Every function the reviews name is used as it stands at origin/jarvis-4 commit 448cb21 (the parent
  commit), so a later change to live scoring cannot move a test. The Explorer is the one exception: it runs main's copy, and a
  merge splits review #36's window.
- **One look.** Counting events is not a look; computing any outcome is. Below a review's minimum count nothing else is computed
  and the verdict is INSUFFICIENT. Only Madhav can extend the window; the rest stays unchanged, and the one look moves to the new
  date (LOCK section 5: "extended rather than the rule bent").
- **The holdout.** Displays that already existed at the push (the Evidence page's running totals, the weekly lessons, the study's
  daily counts) are the running system. They are not looks as long as nothing in a review changes because of them. A new display of
  a review's own measure before `CHECKPOINT-60` is a look, and the results file names it. Two fixes the audit allows now would show
  a measure early, so they should log without showing totals until day 60:
  - fix 1, a close-stop score beside every touch stop (review #31);
  - fix 3, the P&L of each catch in the missed-moves study (review #38).
  The same holds for a "PASS quality" line in the morning review (review #34): it should show counts only.
- **The lake header.** Each results file opens with `format_header(lake_header(D, until=2026-12-15 00:00 UTC))` over the coins it
  read, and one live-feed coverage line per feed under it. Without both, a result is a draft (RESEARCH_RULES section 4).
- **The event counts.** Each object keeps one count rule (RESEARCH_RULES section 2):

  | Object | Count rule | Reviews |
  |---|---|---|
  | Stop exits, Explorer trades | everything closing on the same UTC day is one event (`independent_events(daily=False)`) | #31, #36 |
  | Jarvis's book pairs | Q7's rule: entries within 3 days are one event (`independent_events(daily=True)`) | #33 |
  | Rule signals, bold pairs, decisions, coin-days, moves | market days | #32, #34, #35, #37, #38 |

- **Cells.** 15 in all:

  | Review | Cells |
  |---|---|
  | #31 | 4 |
  | #32 | 2 |
  | #33 | 1 |
  | #34 | 2 |
  | #35 | 1 |
  | #36 | 1 |
  | #37 | 2 |
  | #38 | 1 |

  Each review's cells are added to its family's look count. Any pass is read against that count, not alone.

## Needs a recorder or a decision
- **Needs a recorder: Madhav's decision (`OD-SHADOW-LANE`):**
  - review #35's score-by-score calibration: the attention score's value and its WATCH and LOW levels are never stored;
  - review #35's HIGH label, if a decision in the window stops attention-HIGH being queued;
  - an intraday version of the breakout in review #32: the universe's 5-minute bars are kept for 14 days only.
  Every test that decides uses data already recorded.
- **Decisions that would split a window** (each named in its review):
  - `OD-MERGE-MAIN` (the Explorer's code, review #36);
  - the audit's fix 2 to the bold pack (review #37; it needs Madhav's OK first);
  - `OD-PLAYBOOK-ATTENTION` and `OD-READS-WAKES` (reviews #33, #34 and #35).
- **Likely INSUFFICIENT on 14 Dec, and recorded as such, not bent:**
  - review #33, unless the dial closes or more kinds wake the brain;
  - review #34's ranker cell, because since the lock the ranker turns away almost nothing.

## Not pre-registered here
- The E4-only entries of request #70 (the 10-coin side-by-side). It waits for Madhav's OK on reporting within two bars.
- The blind shadow lane itself (`OD-SHADOW-LANE`). It is a build, so it needs Madhav's yes.

## Ledger
Each review has a row in `docs/repair_shop/ledger.json`, "reviews" (R31 to R38, status PRE_REGISTERED, verdict PENDING), because
the nightly ledger check (`knowledge_build.ledger`) files a repair-board request for any review document without a row.
