# Pre-registered study: do the daily news check and the layer signals tell us anything? (news_log and credit_records)

Written 2026-10-15, before any 20-day outcome exists (the first settles about Oct 22). Nothing here changes a decision now: the news
check stays a veto that can only add caution, and the layer signals stay as they are. This file fixes how they will be scored, so the
scoring cannot be bent by what the outcomes show. Raised by the research audit (cards NEWS_RECORDER and STUDY:CREDIT). The commit that
holds this file is the outside timestamp (`RESEARCH_RULES.md` section 1).

## What is recorded (live, point in time)
- `news_log` (`jarvis/service/news_watch.py`, since Oct 3): after each daily close, one news check per coin of the 10: `verdict` CLEAR,
  CAUTION or BLOCK, with the headline it rests on (`why`, `json`). On Oct 15 it held 130 rows over 13 days: 64 CAUTION, 66 CLEAR, no BLOCK.
- `credit_records` (`jarvis/service/credit.py`, since Oct 2): after each daily close, one row per coin with `signals`, eight true/false flags:
  `market_allowed`, `coin_trend_up`, `chain_candidate`, `in_supported_zone`, `attention_high`, `setup_fired`, `setup_close`,
  `news_caution_or_block`; and `fwd20`, filled 20 days later by `credit.settle`: the coin's close 20 days after the signal day divided by
  that day's close, minus 1. No row has an outcome yet (130 rows on Oct 15).

## The outcome (decided now)
For each coin-day, the excess = `fwd20` minus the median `fwd20` of the 10 coins for the same day (a falling market does not make a
signal look right). The one-day delay between the close and a real entry is ignored: over 20 days it is small and it is the same on both
sides of every comparison.

## The tests (decided now)
Eight comparisons, one per flag. The news test is the eighth (`news_caution_or_block` on against off): it is the same comparison, not a ninth.
For each flag:
1. Take every UTC week that has coin-days on both sides of the flag (consecutive days share most of their 20-day window, so the week is the
   unit, not the coin-day).
2. For each such week, the mean excess of the coin-days with the flag on minus the mean excess of those with it off.
3. The flag's number is the average of those weekly differences; its standard error is the standard deviation of the weekly differences
   divided by the square root of the number of weeks; t = number / standard error.

A flag **passes** only when all three hold: at least 10 such weeks; |t| >= 2.5 (stricter than review #26's z >= 2, because eight
comparisons are made); and the difference is at least 2 points of excess return (0.02) in the useful direction. The useful direction is
"on" doing better for the seven layer signals, and "on" doing worse for the news flag (it is a veto). A flag that clears the bar in the
other direction is reported as **backwards** and does not pass. Anything short of the bar is "not shown", never "shown not to work".
`credit.report()` already prints raw with-and-without means; those are descriptive and are not this test.

## When it is read
Counts only (how many coin-days and weeks have outcomes) may be looked at any time. The comparison is computed once, when every flag has
10 weeks with both sides and an outcome (expected around January 2027 at the current pace), and the result goes to the repair shop as a
review with the numbers. It is a step of the quarterly update review (`docs/knowledge/due_list.json`). Rule B (no new crypto strategies
during the evidence window) applies: a pass becomes a proposal for after the window, never a live change.
