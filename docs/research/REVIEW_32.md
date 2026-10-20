# Review #32 (pre-registration): a breakout away from support (request #38, `PW-BREAKOUT-38`)

**Status: PRE-REGISTERED, forward test.** Written 2026-10-20 (about 14:30 UTC) and pushed before any outcome dated after the
push was computed. Sources: repair-board request #38, the decision audit of 13 to 20 October (sections 1.5 and 5, fix 11) and the
gate and pipeline review of 20 October (Part 2, step 1). Forward window 2026-10-21 00:00 UTC to 2026-12-14; one look, at
`CHECKPOINT-60`. Until `REVIEW_32_RESULTS.md` exists there is no result. (Review #32 tests *request* #38; review #38 is a
different question.)

## Why
- **The casebook.** The missed-moves study (`jarvis/service/missed.py`) labels each day's biggest up-moves and the kind of move.
  On 15 Oct its pattern "breakout | no zone | ALLOWED" on the universe reached 5 distinct days in 30 and became request #38: "a
  breakout over the recent high, away from any support zone, market allowed (10 times in 30 days, about +22.7% each; STRK, PYTH,
  ATOM, ZK, S, CHIP, TIA, AERO)".
- **Parked.** Rule B parked it the same day (status WONT, `PW-BREAKOUT-38` on the after-window list). The pattern has qualified
  again since (5 days, 12 rows), but the once-ever flag (`missed:flag:breakout|no zone|ALLOWED:UNIV`) keeps it silent.
- **The caution** (decision audit, section 5). The casebook sees a move after it happened. Coins that ended the week of 13 Oct
  above their prior 20-day high averaged +13.4%, against -6.6% for the rest, but that is hindsight. The version one could trade,
  buying the first daily close above the prior 20-day high, made 7 trades that week with 1 winner and -9.2% on average after costs.
  One week, one market state: a caution, not evidence.

**The question in plain words:** if Ananta had bought every coin that closed above its recent high while far from any support
zone, with the market allowed, would those buys have made money after costs, and done better than the average coin bought the
same day?

## The tier that decides
- **Tiers A and B of the universe, point in time (decides).** Each signal day, a coin's tier comes from the registry's own rule
  (`jarvis/service/registry.py`, `TIER_A`, `TIER_B`): the median daily traded value (`universe_bars.d1.qv`) over the 30 daily
  candles before the signal day is at least $20M (tier A) or at least $1M (tier B), with 30 such candles present. The weekly
  registry file is not used, because it holds today's tiers.
- The coin also needs at least 260 daily candles to that day, because the zone test needs them.
- A coin that stops trading stays in for the days it traded. The lab 10 are included when they qualify.
- **Reported beside, never rescuing:** tier A alone.
- **Event count:** market days. Trades exiting on the same UTC day count once (review #29's count; with a fixed five-day hold this
  is the same as distinct signal days). An event's value is the mean excess of its trades.

## The test
One rule decides; a second is reported beside it. Nothing is tuned.

**The signal**, at a daily close (a candle that closes at 00:00 UTC):
- **R38-D5 (decides):** the close is above the highest high of the 5 previous daily candles. That is the casebook's own "recent
  high" (`missed.context`, `hi5`).
- **Away from support:** that day's low is not inside any live zone widened by half a daily range. This is `missed.context`'s
  test: `src.research.zones.live_zones(D)` on the coin's daily candles up to that day, and a zone counts when
  `bot - 0.5 x ATR <= low <= top + 0.5 x ATR`, with ATR as missed.py computes it.
- **Market allowed:** `watch_engine.regime_at` on Bitcoin's daily candles to that day reads ALLOWED (missed.py's regime).
- **One trade at a time per coin:** a signal while that coin's trade is open is ignored.

**The trade:** entry at the next daily open; exit at the open five daily candles later; no stop, no target.

**R38-H20 (reported beside, the audit's chase):** the first daily close above the highest high of the 20 previous daily candles
(the day before closed at or under its own 20-day high), with the same filters, entry and exit.

**Costs:** each side, `registry.cost(coin)` (Universe Rule v2: the NDAX fee plus three times the coin's measured Binance
half-spread, never under its tier's floor; the lab 10 at their NDAX table). The stress run doubles every cost.

**Baseline:** for the same entry open and exit open, every other coin in the same point-in-time tiers, each after its own cost.
The baseline is their mean, so it carries no sampling noise (it plays the role of review #26's random entries in the same tier and
market state). **Excess** = the trade's net minus the baseline.

**z** = mean of event values / (standard deviation / square root of the number of events).

**Data, all recorded today:** `universe_bars.d1` (open, high, low, close and traded value, from 2024-01-07, 488 coins), Bitcoin's
daily candles, `src/research/zones.py` and `registry.cost`. Nothing is built: the run script is the review.
- A version that buys the minute the price crosses its recent high would need intraday prices, and the universe's 5-minute bars
  are kept for 14 days only. That version is not tested here: it **needs a recorder: Madhav's decision (`OD-SHADOW-LANE`)**.

**Code version:** every function named here is used as it stands at origin/jarvis-4 commit 448cb21 (this file's parent commit).

**Forward window and looks.**
- Window: signal closes from 2026-10-21 00:00 UTC to 2026-12-09 00:00 UTC. The last of those signals exits at the open of
  2026-12-14, inside the window.
- Looks: **one**, at `CHECKPOINT-60`, run after the 2026-12-15 00:05 UTC daily close.
- Counting market days first is not a look; computing any trade result is. If the count is under the minimum, nothing else is
  computed; only Madhav can extend the window, and the one look moves with it.
- Cells: 2 (R38-D5 decides; R38-H20 beside). **Family:** breakouts, which carries the looks of reviews #11 (teacher breakouts
  with zones) and #21 (volume breakout), both FAIL. The pattern was also picked after the fact from the casebook's kinds
  (breakout, rebound and swing, each at a zone or not). So D5's z bar is 2.5, the stricter bar review #29 used for a cell picked
  from many.

**Holdout.**
- missed.py keeps writing casebook rows every night, and the morning review shows them. Those are lists of moves, not this rule's
  trades.
- Nothing displays this rule's result. The audit's figures for the week of 13 Oct are before the window and are no part of the
  test.
- Any computation of R38-D5 or R38-H20 trades in the window before `CHECKPOINT-60` is a look, and the results file names it.

**Lake header.**
- The results file opens with `format_header(lake_header(D, until=2026-12-15 00:00 UTC))` over every coin that was eligible on
  any signal day, with D their universe daily candles in the window. If the weekly lake job has not reached the window's end,
  `until` is the lake's last complete day, and the header says so.
- Directly under it comes the live-feed line: the daily candles expected and present per coin in the window, and the coins with
  gaps.
- A result without both is a draft (RESEARCH_RULES section 4).

## Pass marks (frozen)
**R38-D5 (decides):**
- **INSUFFICIENT:** fewer than 10 market days.
- **PASS:** all four hold:
  - the mean excess is above 0 with z of 2.5 or more;
  - the mean net is above 0;
  - at twice the cost, the mean net is still above 0;
  - dropping the two market days with the most trades keeps the mean excess above 0.
- **WEAKENED:** the mean excess and the mean net are both above 0, but the z, double-cost or burst mark fails.
- **FAIL:** the mean excess or the mean net is 0 or below.

**R38-H20** is judged by the same marks and reported beside D5. It never rescues D5. If D5 passes and H20 fails, the result says
the pass belongs to the five-day definition only.

## What each outcome changes (decided now)
Nothing changes by itself. Each line is a proposal to Madhav after the window, in the order he sets (LOCK section 9).
- **PASS:** propose request #38's rule as a candidate for a paper evidence book. That needs Madhav's yes and a new entry in
  `strategy_status.json`, and Rule A applies. Before it, propose a lake re-test of the same rule on point-in-time tiers in the
  discovery and confirm periods, because one forward window in one market state is not enough to trade on.
- **WEAKENED:** propose the lake re-test only; no book.
- **FAIL:** request #38 is closed as tested, and the verdict is kept as a lesson with its numbers (RESEARCH_RULES section 6). The
  brain's knowledge line for the pattern "breakout, no zone, market allowed" says "tested forward, no edge (#32)". The casebook
  keeps recording it.
- **INSUFFICIENT:** nothing changes; `PW-BREAKOUT-38` stays on the after-window list.

## Not in this review
- Breakouts on volume (review #21) and breakouts read with zones (review #11): both failed and are not re-tested here.
- Intraday entries, stops and targets.
- Volume.
- The 30-coin tier's own casebook rows (they are in the casebook, not here).
- Rebounds and swings.
