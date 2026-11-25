# India pre-live tests (v1, written Wed 25 Nov 2026, before any is run)

Madhav, 25 Nov 2026, in chat: "sounds like we have to do all of them before going live ... organize everything properly, and we will do every test on our project, and we will see if we find anything, and that we can sort that out ... make sure we are not missing on anything".

## Rules for every test

- Code only, on the Mac: no Claude API call, no money, no order. Building them uses Claude plan time, not API credit.
- Read-only on live data. A test that plants faults works in a copy folder, never in `~/ananta_data/india`.
- No pin, paper rule or trade changes. A test that finds a fault files it; the fix is reporting code with a test, or Madhav's decision.
- The sealed firewall holds: research data 2000-2023 only. The one test that needs live-day prices for a new use (T10) waits for Madhav's yes.
- Each pass mark is written here before the test runs and is not moved after.
- Each result goes to `india/registrations/prelive/T<n>_<date>.md`. Its open-list item closes only by the commit that adds that result. Every fault found is its own open-list item (topic `prelive-T<n>`).
- Done means all 15 read, and each fail either fixed or accepted by Madhav in writing. That is item 8 of the go-live checklist (`pass_marks_v1.md`).

## Not disturbing the running system (Madhav, 25 Nov 2026: "we have to make sure we are not disturbing the workflow, and everything is properly integrated")

- Tests run in Toronto daytime, 08:30-19:30, never during the sign-in (20:10), the session jobs (21:00-05:00) or the nightly build (02:30).
- Test scripts live outside both repos, in `~/ananta_runs/prelive/`, so the nightly leak check, firewall and fact map never see them. Each result names its script and the script's sha256. Results go to records `india/registrations/prelive/`, never into `~/ananta_data/india`.
- No test restarts a service, edits a launchd job, or writes to live data. Kite is used only through `india/kite.py` (GET and the margin calculator), and no token or account figure is printed.
- A fix found by a test goes in one at a time: its own test, both full test suites and the lock tests, its change-book line naming the item it closes, and never during the session window. The next morning review confirms the following night ran clean, so G02's count is not put at risk. A fix to a frozen file waits for Madhav's yes through the repair door.

Open-list names: T1 flag 254, T2 flag 255, T3 flag 256, T13 flag 257, T4 flag 258, T5 flag 259, T6 flag 260, T7 flag 261, T8 flag 262, T9 flag 263, T11 flag 264, T12 flag 265, T14 flag 266, T15 flag 267; T10's yes is flag 268. The live options cap question that T1 feeds is flag 269.

## Order

The order is kept in one place: `golive_plan_v1.md`, section 5 (from 25 Nov, replacing the first day-by-day table here). T1 ran on 25 Nov. T13 and T15 wait for the live path's design and build (Track A there). The pass marks below do not change.

## A. Before going live

**T1. Would it have gone live?** How would the options line have traded under the go-live rules of 24 Nov? Take every options decision since 26 Oct. Apply the premium cap, the one-overnight-position rule and the order's shape: the contract exists that day, the lot size, the price step and the broker's quantity limit. Ask Zerodha's margin calculator (read-only, allowed by the leak check) whether the money would have covered it. Write a "would-have-been-live" table beside the paper record. Already known: 6 of 23 decisions had a 1-lot premium above Rs 25,000, including 25 Nov (Rs 44,806). *Pass:* every decision gets a verdict (traded, or skipped and why), and the broker would refuse nothing for a reason the live path does not already name.

**T2. Calendar and clock walk.** Take every day from 26 Nov 2026 to 31 Mar 2027 at six Toronto times (07:45, 20:10, 21:00, 22:45, 00:45, 05:00) on a frozen clock. Ask Ananta's own code: what is today, the next session, "tomorrow", the expiry day, and what India time each job runs at. Check the answers against the NSE calendar and a list written first: the 24 Nov holiday, November's expiry moved by it, the weekends, and Toronto's clock change on 14 Mar 2027. *Pass:* no disagreement. A missing 2027 NSE holiday list is itself a fail.

**T3. Fire drills for the checkers.** Plant 10 faults in a copy folder: a file two sessions old, an empty file, a duplicated row, a row dated tomorrow, a job that exits 0 but writes nothing, a log that says "ok" with no proof, a token refused mid-job, the read model older than the book, a session missing in the middle, and a holiday written as a session. Run the morning summary, the self-check, the fact map and the integrity checks against it. *Pass:* every fault is named by at least one check. A check that cannot be pointed at a copy is itself a finding.

**T4. Same number everywhere.** Take 15 facts: options sessions scored and the lot's rupees per index; open positions per book; realised rupees; G02, D15, D16; the exam result; the daily call's record; the managed book's and the holdings' value; the last Nifty close; the next session; missed movers caught; the yardstick percentile. Read each from the app screens (local, read-only), the read model, the morning view, the trials list and the Ask's facts built without the model. *Pass:* every fact is equal everywhere, or differs only by an as-of time that is shown.

**T5. Does the rule follow itself?** For every options decision, recompute "qualifies" and the choice from the row's own logged numbers and the frozen SP1 v2 rule. For every stock pick, check it meets its family's definition from its logged features. Compare each paper fill with the recorder's bid and ask at that minute. *Pass:* every choice matches, and every fill is inside the realistic-fill rule; each difference is listed (flag 214 joins).

**T13. The missed exit.** On a live night, what happens if the Mac sleeps, the Kite sign-in fails or the 09:15 job crashes while a position is held overnight? Walk each case through the live path's design: who closes the position, by when, and how Madhav is told. *Pass:* each case has a written fallback that works without the Mac (a broker-side order, or a phone alert with the exact step for Madhav).

**T14. Alerts reach the phone.** Send one test alert through each path: a HIGH self-check line, a sign-in failure and the morning note. Madhav confirms each arrival time. *Pass:* each arrives within 5 minutes.

**T15. Survival rules rehearsal.** Run the 5% day, 22% pause and kill-switch checks in record mode over the paper record. *Pass:* they fire on exactly the days the record says, the enforce switch exists, and it is off. This is the first monthly India risk rehearsal (INDIA_LOCK.md section 9).

## B. Answers, without the model

**T6. Fact-page check.** Build the Ask's facts for each question in the question bank (v2) without calling the model. Compare every number with the truth sheet (`~/ananta_runs/audit_23nov/truth.py`). *Pass:* no wrong number; every missing fact listed.

**T7. Guard re-test.** Run today's answer guard over the saved answers: the 23 Nov audit's 72, the replay bank and the stress words. *Pass:* it catches every answer marked wrong for a number, including flag 170's case (a figure found in no file).

## C. Research honesty

**T8. How much is luck?** From the registry: versions tested (1,440), VALIDATED (44), how many would pass by chance at each study's bar, and whether each validated one held on a later look. *Pass:* the table is written, and a VALIDATED resting on one look is marked "not yet trusted".

**T9. Data cross-check.** Search 2000-2023 for index days that moved more than 2% one way while their weighted constituents moved the other way; also compare Kite and NSE closes where both exist. *Pass:* every such day is explained, or marked as a known fault so studies skip it (flag 248 joins).

**T10. More simple yardsticks.** Add "follow the opening gap", "fade it" and "buy at the open, sell at the close" for Nifty and Bank Nifty on live paper days since 26 Oct, beside "always long" and the coin flip. Needs a new sealed purpose (live paper days' index opens and closes, for the yardstick only, no rule scored) and Madhav's yes. *Pass:* a written comparison only.

## D. The Mac

**T11. Restore drill.** Restore the R2 backup into `~/ananta_restore_test` and run both test suites and a read-model build there. Compare file hashes with the live copy. The backup job's own code holds the keys; nothing is printed. *Pass:* all 583 files are hash-equal and the tests pass.

**T12. Job times and memory.** Over 30 days of logs: each job's run time per night, its finish against the job that needs it next, the options decisions' lateness (`late_s`), memory and swap, and nights the Mac slept. *Pass:* the slowest of 30 nights still leaves 10 minutes before the next job that needs it, and every decision is under 60 s late.
