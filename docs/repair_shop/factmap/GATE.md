# The gate and the feature freeze (Madhav, 2 Nov 2026: "Yes, continue and keep it tight and right")

Why: every conversation kept turning up something the voice/chat agent did not know or said differently from a screen. Audits were
one-off reads; new files and features kept arriving after them. These four pieces make the mapping a standing check, not a promise.

1. Fact map — jarvis/india/factmap.py. Every file the backend wrote in the last 8 days must have a route to the Ask
   (live / nightly / feed / copied into words / internal). Daytime files read only from a nightly copy count as a gap.
   Same-number checks compare screens with the Ask (Today Nifty tile, managed buys, options open trades).
   Runs 00:05, 11:00 and 16:10 IST (com.ananta.india.factmap); a failure pushes to the phone.
2. Moment harness — jarvis/india/neveragain.py (MOMENTS). Madhav-style questions asked at 8 moments of the day
   (before open, pre-open, mid-session, after close, after IST midnight, weekend …) against what was true then.
   Runs nightly inside the replay; failures push to the phone.
3. Independent auditor — a fresh agent with only the goal and the rules, never the builder's conclusions. Report only.
4. The gate — tests/test_factmap.py plus tests/test_india_livesession.py are part of the suite:
   - no backend file without a route;
   - the screens and the Ask give the same numbers;
   - every frozen "never again" case and every moment passes.

## Feature freeze (from 2 Nov 2026)
No new India feature, screen or data file is merged until the gate is green AND the new thing has its route in the fact map
and at least one moment question in the harness. Fixes to gaps the gate or the auditor find are allowed and come first.
Crypto stays under Rule B (no new studies or rule changes before 14 Dec 2026).

## Added after the independent audit (2 Nov evening)
The first outside audit found 16 gaps the four pieces above did not catch, because they checked that data has a ROUTE, not that it is FRESH
when Madhav asks. So the gate also holds:
5. Freshness — factmap.stale_summaries(): a summary (market summary, quote book) built before its own inputs fails.
6. One clock for times — jarvis/india/schedule.py day_words()/at(): every job time Ananta or a screen says is read from the launchd jobs;
   tests/test_no_handwritten_toronto_times.py fails on a hand-written Toronto clock time.
7. Lint before commit — `~/ananta_runs/lintenv/bin/pyflakes <changed files>`: no undefined names (a missing import silently turned the
   live stock price off on 2 Nov until it was caught).
8. A fresh outside audit after every large change (brief: goal and rules only, report only; dry Ask: ~/ananta_runs/audit_ask.py).
