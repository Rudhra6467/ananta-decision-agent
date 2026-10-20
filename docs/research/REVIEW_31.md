# Review #31 (pre-registration): the written close stop against the coded touch stop

**Status: PRE-REGISTERED, forward test.** Written 2026-10-20 (about 14:30 UTC) and pushed before any outcome dated after the
push was computed. Sources: the decision audit of 13 to 20 October (sections 1 and 3, fix 1) and the gate and pipeline review of
20 October (Part 2, step 1). Forward window 2026-10-21 00:00 UTC to 2026-12-14; one look, at `CHECKPOINT-60`. Until
`REVIEW_31_RESULTS.md` exists there is no result. Index: `docs/research/PREREG_WINDOW_2026-10-20.md`.

## Why
The stop the system writes down and the stop the code trades are different.
- **Written:** the decision chain (`jarvis/service/chain.py`, step 5 INVALIDATION) and the `STOP_ZONE` card (evidence UNTESTED) say
  a zone trade's idea is wrong at "a daily close half a daily range under the zone".
- **Coded:** the trade is sold on any touch of that level: `brain.manage_live` on the eye's live price, and the daily check in
  `watch_engine._manage` on the day's low.
- **What happened (13 to 20 Oct, before the window):** all 18 stop exits of Jarvis's book (8) and its twins (10) fired during the
  day while that day's close stayed above the stop. 7 of them fired in one six-minute flush on 15 Oct (02:22 to 02:28 UTC), when
  NDAX's measured spread was 2.55% on ETH and 3.41% on AXS. Reconstructed under the written rule, Jarvis's 8 would have netted
  -$65.95 instead of -$85.74 (5 better, 3 worse). That is one market event and a reconstruction, not a test.

**The question in plain words:** when a stop level is reached, is it better to sell at once (what the code does) or to wait for a
daily close under it (what the rule says)? And were the paper stop fills prices that NDAX would really have given at that minute?

## The tier that decides
Two objects, each with one event-count rule.

**A. Stop exits (decides A): every trade whose live stop is run by `brain.manage_live`.**
- The books: Jarvis's book (`JARVIS`), its twins (`JARVIS_RANDOM`), the bold book (`JARVIS_BOLD`) and its twins (`RANDOM_BOLD`),
  on every coin and tier. One function trades all four, so any change the result proposes is a change to that function.
- A trade counts when its stop exit is in the window: `exit_why` is "stop", "stop (live price)" or "trailing stop (live price)" and
  `exit_t` is from 2026-10-21 00:00 UTC to 2026-12-14 23:59 UTC. It counts whenever it was opened: the price path after a future
  touch is unseen. At the push, 27 such trades are open with a live stop (Jarvis 10, twins 9, bold 4, bold twins 4); new ones join.
- **Reported beside, never rescuing A:** the zone-touch books (`ZONE_TOUCH`, `ZONE_TOUCH-UA`, `-UB`, `-UC`). Their stop is exactly
  the written level (`eye.py`: zone bottom minus half a daily range), checked live by the eye's evidence-stop loop. Same marks.
- **Event count:** stop exits closing on the same UTC day are one event (`scoreboard.independent_events(daily=False)` on `exit_t`,
  the rule `views._events_count` applies to exits). An event's value is the mean of its trades' values.

**B. Stop fills against NDAX (decides B):** the stop exits of A on NDAX-listed coins that carry a minute: those sold on the live
price. Exits by the daily-low check (`exit_why` "stop") have no minute and are left out of B. Same event count.

## The test
**A. Close rule against touch rule, on the same trade (paired).**
- **Touch result:** the book's own `net_usd`.
- **Close result:** the same trade replayed on daily candles from the touch onward:
  - the stop level in force at the touch is `evidence_trades.stop`. For a trade with a trailing rule, the level is then raised
    after each later day to max(level, that day's high minus `trail_atr` x `atr`), the plan's own trail rule;
  - the trade exits at the first daily close at or below the level in force at the start of that day, at that close;
  - on a day whose high reaches the trade's target, the target exit applies first, at the target (at the open if the day opened
    above it), as `watch_engine._manage` does;
  - the time exit is unchanged: the open of the first daily candle at or after `entry_t + days`;
  - candles: the universe feed's daily candles (`universe_bars.sqlite`, table `d1`) for every coin (one source per number);
  - costs: `watch_engine.net` on both results, so the comparison is cost-neutral (one exit each);
  - a close-rule trade still open after the 2026-12-14 daily close is marked at that close and flagged "marked".
- **Value per trade:** close result minus touch result, in $ per $100.
- **z** = mean of event values / (standard deviation / square root of the number of events).

**B. Stop fills against NDAX.**
- For each exit in B: the worker Mac's NDAX bid and ask for that minute (`~/ananta_worker_data/l1_<day>.sqlite`, table `ndax`,
  converted to USD with that day's `fx`), read with `realism.Quotes` (quote within 120 seconds).
- Judged by `realism.py`'s sell test as committed at 448cb21: achievable price = NDAX bid x (1 - 0.20%); the book's effective
  price = its exit x (1 - the cost it charged itself). The exit is REALISTIC when the book's price is no more than 5 basis points
  better than achievable.
- Also: the NDAX full spread at that minute divided by the coin's median NDAX full spread over that UTC day.
- Exits with no worker quote (worker outages, coins NDAX does not list) are counted and left out.

**Data, all recorded today:** `evidence_trades` (stop, exit_t, exit, net_usd, detail: `stop_moves`, `target`, `days`,
`trail_atr`, `atr`), `universe_bars.d1`, and the worker's `l1_*.sqlite`, pulled nightly. Nothing is built. No recorder is needed.

**Code version:** every function named here is used as it stands at origin/jarvis-4 commit 448cb21 (this file's parent commit).

**Forward window and looks.**
- Window: stop exits from 2026-10-21 00:00 UTC to 2026-12-14 23:59 UTC.
- Looks: **one**, at `CHECKPOINT-60`, run after the 2026-12-15 00:05 UTC daily close.
- Counting events first is not a look. Computing any value of A or B is.
- If the count is under a minimum below, nothing else is computed. Only Madhav can extend the window (LOCK section 5: "extended
  rather than the rule bent"); everything else stays unchanged, and the one look moves to the new date.
- Cells: A (decides) and the zone-touch cell beside it; B's realism mark and its spread mark. Four cells, in the stops family
  (reviews #10, #12, #18 and #27).

**Holdout.**
- Nothing in the app shows close-rule results today. The Evidence page shows each book's running net; that is the running system.
  It is not a look as long as nothing in this file changes because of it.
- Any computation of A or B before `CHECKPOINT-60` is a look, and the results file names it.
- The decision audit's fix 1 ("score a close-based stop next to every live-touch stop") is allowed now as scoring. If it is built
  in the window, it must log without showing totals until `CHECKPOINT-60`. If its totals are shown, this review reads "seen in the
  window" (a log kept but not shown is what `OD-SHADOW-LANE` describes).

**Lake header.**
- The results file opens with `format_header(lake_header(D, until=2026-12-15 00:00 UTC))` over the coins of the counted trades,
  with D their universe daily candles in the window. If the weekly lake job has not reached the window's end, `until` is the
  lake's last complete day, and the header says so.
- Directly under it comes one live-feed line per feed read: the daily candles expected and present per coin in the window, the
  worker's NDAX minutes expected and present per UTC day, and the coins or days with gaps (the worker's outages, #72).
- A result without both is a draft (RESEARCH_RULES section 4).

## Pass marks (frozen)
**A (decides; the books run by `brain.manage_live`):**
- **INSUFFICIENT:** fewer than 10 events (exit days). Nothing beyond the count is computed.
- **CLOSE_BETTER:** all three hold:
  - the mean event value is above 0 with z of 2.0 or more;
  - the close rule is ahead in more than half of the events;
  - the mean is still above 0 with the single largest event removed (no one flush carries it).
- **TOUCH_BETTER:** the mirror: mean below 0 with z of -2.0 or less, touch ahead in more than half of the events, and still below 0
  with the largest event removed.
- **NO_DIFFERENCE:** everything else.

The zone-touch cell is judged by the same marks and reported beside A. It never changes A's verdict.

**B:**
- **INSUFFICIENT:** fewer than 10 stop exits with a worker quote.
- **FILLS_REALISTIC:** at least 80% of them are REALISTIC.
- **FILLS_OPTIMISTIC:** under 80%.
- **WIDE_AT_STOPS** (a separate flag): the median spread ratio is 1.5 or more.

## What each outcome changes (decided now)
Nothing changes by itself. Each line is a proposal to Madhav after the window, in the order he sets (LOCK section 9). A stop is a
trading rule, so Madhav decides.
- **CLOSE_BETTER:** propose trading the written rule. The brain's books exit on a daily close under the stop, so
  `brain.manage_live` and the daily-low check in `watch_engine._manage` stop selling on a touch for them. The zone-touch books
  follow only if their own cell agrees. `STOP_ZONE` cites #31 for the trigger; its evidence word for "stop or no stop" is not
  decided here.
- **TOUCH_BETTER:** propose that the words follow the code: chain.py's INVALIDATION text and the `STOP_ZONE` card say "sold when the
  price touches the level".
- **NO_DIFFERENCE or INSUFFICIENT:** propose the cheaper fix (the words follow the code, as for TOUCH_BETTER), noting that the
  trigger made no measured difference.
- **FILLS_OPTIMISTIC or WIDE_AT_STOPS:** propose that paper stop exits on NDAX coins pay the worker's measured spread at that minute.
  That is a `paper_costs` change: it needs Madhav's yes and a re-pin. Also propose that `data_costs` names stop exits.
  **FILLS_REALISTIC:** nothing changes, and the report says so.
- **In every case:** correcting the `STOP_ZONE` card to say what the code does today is a docs fix the audit already allows. It
  does not wait for this review and does not change it.

## Not in this review
- Stop against no stop (review #27 settled it for dips; for zone trades `STOP_ZONE` stays UNTESTED).
- Where the stop level is placed.
- The daily watches' own stops (H07, M2a and others are checked on the daily low by design).
- The $500 book (its stops are its own pinned rules).
- Intraday paths after the touch: the universe's 5-minute bars are kept for 14 days only (`feed.KEEP_5M_DAYS`), so the replay uses
  daily candles.
