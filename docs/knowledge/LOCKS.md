# The lock book: every lock Ananta works under (from 13 Nov 2026)

One page for every lock. A lock that is not on this page does not exist. Madhav's yes of 13 Nov 2026 ("Yes to all") set it up; the list
it came from and the reasons are in the project document `claude/review-2026-11-13-the-locks-and-a-plan.md`.

## The three kinds

- **A strict lock** protects something that cannot be undone. Only Madhav opens it, and no repair door opens it.
- **A test lock** protects a rule while it is being tested on paper. It freezes the decisions, not the file they sit in. It has a repair
  door and an end date; on that date it lapses unless Madhav renews it.
- **A habit** is how the work is done. A habit never blocks a fix.

## The repair door

A fault in a locked thing is fixed the same day. One question decides how: does the fix change any decision Ananta would have made?

- **No** (a crash, a wrong record, wrong words): it is fixed at once, the pin's history gets an entry that starts "Repair, no rule
  change", and Madhav is told after, in the change book and the next message.
- **Yes** (it changes what Ananta buys, sells or sizes): it is fixed now too, on Madhav's one-word yes for that repair. The record is
  split at that day: one record up to the fix, a clean one after.

Both doors are opened with one tool, `scripts/lock_door.py` (`repair` and `change`; `status` shows every pin), so a pin's history is
written the same way every time and nobody edits a lock file by hand. A rule Madhav changes after seeing how it did goes through
the `change` door too: his own yes, and the record split at that day. A door opens only on committed work, and the entry names the
commit. A lock past its end day is said by `status` and stops nothing: Madhav renews it or it is dropped.

The tool cannot tell whether a change alters a decision. Calling a change a repair is the builder's word, and the guard on that
word is the one outside check every repair gets: it reads each door entry against the commit it names and says whether any
decision changes. (A check that replays the stored history through the old and the new code was planned on 13 Nov and dropped
the same day: Madhav asked for the simplest method that still gives the proof, and two doors with one outside read are that.)

## Strict locks

| Lock | What it protects | What it does not stop | Who opens it |
|---|---|---|---|
| No real money before 60 paper sessions have passed their test | Real money | Any work on paper | Madhav |
| The Zerodha account is read only; no order is ever placed | The account | Reading it for the paper books | Madhav, at go-live |
| The sealed India years (2024 on) are not looked at; India's data and crypto's stay apart | A look cannot be taken back | Research on 2000 to 2023; the paper books | Madhav |
| No early looks at the crypto measuring books' results | The crypto forward test | Counting their trades | Ends by itself on 15 Dec 2026 |
| Keys, passwords and tokens are never opened or printed | Safety | Nothing | Nobody |

## Test locks

| Lock | Where it is kept | What it protects | What it does not stop | Ends |
|---|---|---|---|---|
| The crypto lock (10 pins) | `docs/knowledge/crypto_lock.json`, `docs/LOCK.md` | The crypto rules through the evidence window | Repairs through the door; words on screens; studies on history | 14 Dec 2026 |
| The India lock (13 pins) | the records checkout's `india/registrations/india_lock.json` | India's paper rules through their tests | Repairs through the door; words on screens | The options line: 25 Nov 2026. The rest: the managed book's 60-session judgement, about the end of January 2027 |
| No new crypto strategy goes live in the window | `docs/LOCK.md` | The window | Studies on history, always | 14 Dec 2026 |
| The crypto scorecard's marks are frozen | the open list | The 14 Dec review | Fixing a counting error in the scorecard itself, with a dated line | 14 Dec 2026 |
| The options line's rule | the open list | The options test | Repairs through the door | 25 Nov 2026 |
| The managed book's rules for 60 sessions | the India lock | The portfolio test | Repairs through the door | About the end of January 2027 |
| The brain's own prompt and stance in the forward test | `docs/LOCK.md` | The forward test | Words shown on screens | 14 Dec 2026 |

## No longer locks (dropped on 13 Nov 2026)

- India's feature freeze to 23 Nov. In its place, one test for new work: does it help Ananta make or explain a portfolio call, or keep
  what it says true? If not, it waits.
- "Repairs only" until version 1's finish line. The finish line stays as a measure of health, not as a gate.
- Wording that waited for 14 Dec because its file is pinned. Words are fixed now, at the source, through the repair door.
- India decisions that waited for the 23 Nov review. They are Madhav's to make on any day.
- "Never edit the due list". Nobody knew where it came from.

## Habits (they never block a fix)

- One outside check for each repair. A fault that touches money, a decision or a locked rule gets a second check; a fault in words or
  labels is fixed, read on the live screen, and does not hold the go-live.
- Every code change has a line in the change book the same day.
- The tests run behind their wall; privacy checks run before every commit; the main branch is never merged into.
- The Mac is kept light in its quiet hours, and nothing of India's goes live during India's session night.
- Zerodha-calling code and the allocator are never run by hand.
- The open list is the only place that says what is open.

## Adding a lock

A new lock goes on this page with the thing it protects, what it does not stop, who opens it and the day it ends. A caution after an
incident is a habit, kept in the working notes, and blocks nothing.
