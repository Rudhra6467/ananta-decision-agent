# Review #36 (pre-registration): does the "room to a target" check stop better trades?

**Status: PRE-REGISTERED, forward test.** Written 2026-10-20 (about 14:30 UTC) and pushed before any outcome dated after the
push was computed. Sources: the gate and pipeline review of 20 October (Part 2, step 1, and its appendix) and the Evidence page's
limits table (`evidence_live`, "Room to a target"). Forward window 2026-10-21 00:00 UTC to 2026-12-14; one look, at
`CHECKPOINT-60`. Until `REVIEW_36_RESULTS.md` exists there is no result.

## Why
- **The check.** The Explorer places a real paper trade only when one trade kind has room to its target
  (`explorer_engine.trade_type`):
  - a dip setup (E6 to E8) needs at least 1.2% to the next resistance (TK2, Madhav's yes on 5 Oct);
  - other setups need 3% (G2) or 1.2% to 3% (G3), unless G1 applies.
  Without room, the signal becomes a `NO_TYPE` shadow: tracked with the SHORT_TERM exits, never traded.
- **The record to 20 Oct:** real trades, 293 closed, -$0.90 per $100; random entries -$1.05; `NO_TYPE` shadows -$0.65 (gate
  review appendix). The trades the check stopped did better than the trades it let through, and all three lost.

**The question in plain words:** does the "room to a target" check throw away trades that would have done at least as well as the
ones it lets through?

## The tier that decides
- **The live Explorer on the lab 10 (decides):** `explorer_book.sqlite`, table `trades`. The Explorer runs main's copy of
  `src/intelligence/explorer_engine.py` (LOCK section 7).
- **The object:** one closed Explorer trade, in one of three groups by its `shadow` field: real (empty), `NO_TYPE`, or `RANDOM`.
  A trade counts when `entry_t` (in its `json`) is at or after 2026-10-21 00:00 UTC and `exit_t` is by 2026-12-14 23:59 UTC.
- **Reported beside, never rescuing:** the universe Explorer (`universe_explorer.sqlite`, by tier).
- **Event count:** the Explorer's own count. Everything closing on the same UTC day is one event (`views._events_count`, i.e.
  `scoreboard.independent_events(daily=False)` on `exit_t`).

## The test
- **Per exit day:** the day value is the mean `net` (per $100 trade, after the Explorer's own costs) of the `NO_TYPE` shadows minus
  the mean net of the real trades, on days with both.
- **z** = mean of day values / (standard deviation / square root of the number of days).
- **Reported beside, not judged:**
  - each group against `RANDOM`, the same way;
  - `NO_TYPE` split into dip setups (TK2's room check) and the others;
  - each group's mix of setups;
  - the share of each group still open at the window's end. Open trades are left out of every group alike.

**Data, all recorded today:** the Explorer's `trades` table (shadow, entry_t, exit_t, net, setup, `tag_room`). Since the lock, 218
`NO_TYPE`, 73 real and 31 random trades closed in five days, so the count is not the problem. Nothing is built. No recorder is
needed.

**Code changes in the window.**
- The Explorer's rules change only through main (`OD-MERGE-MAIN` and a restart of `com.ananta.explorer`).
- If that happens, the window is split at the restart and both parts are judged. The verdict stands only when both parts give the
  same verdict; otherwise it reads MIXED.
- Code named here outside the Explorer is used as it stands at origin/jarvis-4 commit 448cb21 (this file's parent commit).

**Forward window and looks.**
- Window: trades entered from 2026-10-21 00:00 UTC and closed by 2026-12-14 23:59 UTC.
- Looks: **one**, at `CHECKPOINT-60`, run after the 2026-12-15 00:05 UTC daily close.
- Counting days first is not a look; computing any group mean is. If the count is under the minimum, nothing else is computed;
  only Madhav can extend the window, and the one look moves with it.
- Cells: 1, in the Explorer family (reviews #1, #3, #9 and #24).

**Holdout.**
- The Evidence page shows "Explorer: no room to a target (tracked)" with its running average every day
  (`evidence_live._results`), and its limits table compares that group with real trades. That display existed at the push and is
  the running system.
- It is not a look as long as nothing in this file, or in the Explorer's rules, changes because of it.
- Any computation of this review's day values before `CHECKPOINT-60` is a look, and the results file names it.

**Lake header.**
- The results file opens with `format_header(lake_header(D, until=2026-12-15 00:00 UTC))` over the lab 10, with D their universe
  daily candles in the window. If the weekly lake job has not reached the window's end, `until` is the lake's last complete day,
  and the header says so.
- Directly under it comes the live-feed line: the Explorer's 15-minute scans expected and run per day (a day with no scans is named,
  as on 16 Oct), and the coins with gaps.
- A result without both is a draft (RESEARCH_RULES section 4).

## Pass marks (frozen)
- **INSUFFICIENT:** fewer than 10 days with both groups.
- **FILTER_STOPS_BETTER:** all three hold:
  - the mean day value is above 0 with z of 2.0 or more;
  - `NO_TYPE` is ahead on more than half of the days;
  - the mean is still above 0 with the single largest day removed.
- **FILTER_HELPS:** the mirror: mean below 0 with z of -2.0 or less, real trades ahead on more than half of the days, and still
  below 0 with the largest day removed.
- **NO_DIFFERENCE:** everything else.

## What each outcome changes (decided now)
Nothing changes by itself. Each line is a proposal to Madhav after the window, in the order he sets (LOCK section 9). The Explorer
stays "won't take again" whatever the result, so no book that trades changes.
- **FILTER_STOPS_BETTER:** propose a lake review of the room check (TK2's 1.2% and the G-rule room bands) on point-in-time tiers
  before any change. The Evidence page's verdict on this limit cites #36.
- **FILTER_HELPS:** TK2's record cites #36 as forward support; nothing else changes.
- **NO_DIFFERENCE, INSUFFICIENT or MIXED:** reported; nothing changes.

## Not in this review
- The Explorer's other limits (one trade per coin per kind, the account cap, missed chases).
- The Explorer's entry setups (E1 to E8; reviews #1, #3 and #24).
- The brain's own "room to beat costs" ranking point.
