# Ananta and Claude, side by side (v1, written 25 Nov 2026)

Madhav, 25 Nov 2026, in chat: "for the next few days until we go live, so that we know how ... Ananta is behaving in the market ... comparative to with your actions, what your actions might have been" and "we have to add this very carefully and precisely ... make sure we are giving the feedback to ananta, from which we will know what to do to ananta."

## What it is, and what it is not

- A measuring stick for how Ananta behaves in the market, read beside its own yardsticks ("always long" and the coin flip). It is not a trading rule and Claude is not a proven trader: the Claude call is a sensible-human baseline.
- It runs from the session of Thu 26 Nov 2026 to the go-live read (flag 238, about 3-4 Dec). Paper only.
- It never changes a paper trade, a rule, a pin or the gate, and it does not count toward G02. A rule change still needs a pre-registered test against random after the window and Madhav's yes (Rule B, INDIA_LOCK.md section 1).
- About 6 sessions: who "scores more" is mostly luck. The verdict is on decisions, not rupees.
- The comparison Claude gave in chat on 25 Nov was written after the close and does not count.

## The call (before the session)

- Written by the India morning review, about 18:15 IST the evening before, from facts on file at that moment only (the last close, the trend, the fear gauge, Ananta's own recorded reads). Overnight US prices and GIFT Nifty are not known yet, so the call depends on the open.
- For Nifty and Bank Nifty: (1) the close-to-close direction, up, flat or down by more than 0.3% (the morning view's base-rate bands); (2) an action for each of three opens: up more than 0.5%, within 0.5%, down more than 0.5%. Each action is long, short or pass, at one of the options line's decision points (09:15, 09:30, 09:45, 10:15 IST), with an exit at the close or at the next open, and any condition written so it can be checked from the record (for example Ananta's own breadth read: the share of its 49 heavy names above their own 09:15 open). One plain reason each.
- No stock picks.
- One row in `claude_compare.jsonl` (kind "call"), committed and pushed with the morning page. The commit time is the seal: a call committed after 09:15 IST of its session is void and is never graded.

## The grade (the next morning review)

- From the record only: the SP1 decision rows (`paper/sp1/decisions.jsonl`: each point's index level `entry_estimate`, the breadth reads, the costs `pcost`), the morning view and the 10:20 update (`paper/morningview/<session>.json`), the scored outcomes after 07:00 Toronto, and at most one dry Ask question for the closes. Never the sealed folders.
- Per index: the open that happened, Claude's action for it, Ananta's actions, and each in basis points from its decision point's index level to its exit, less the options line's own cost (`pcost`, about 6 bp). A pass scores 0. An exit at the next open is graded in the following run from the next session's 09:15 read.
- Decision quality first, in Madhav's words, "the right and best decision in the given scenario": was each choice sensible for what was known at its time? Then the outcome, named as one day.
- Ananta's words: the morning view and the 10:20 update checked against the record.
- One row in `claude_compare.jsonl` (kind "grade").

## The feedback to Ananta (where each finding goes)

1. A wrong word or wrong fact in what Ananta said: an open-list WORK item (market india, topic `compare-words`) with a first answer, fixed as reporting code with a test. Ananta's Ask reads the open list.
2. A behaviour seen once (for example a pass on a gap that held): written in the grade row only.
3. The same behaviour in 3 graded sessions: an open-list PARKED item (topic `compare-pattern-<name>`): a draft for after the window, to be tested against random with a written pass mark, then Madhav's yes.
4. At the go-live read (flag 238): one summary for Madhav: sessions graded, where Claude and Ananta agreed and differed, whose decisions were sounder, the word faults found and fixed, and the drafts waiting.

## Cost

No extra scheduled run: the call and the grade are steps of the India morning review. At most one dry Ask question a run.
