# Independent audit of Ananta India: what it says against what it holds (3 Nov 2026)

For Madhav. Run on your Mac, Monday 2 Nov 9:20 to 9:40 pm Toronto (Tuesday 3 Nov 07:50 to 08:10 in India, about an hour before the open,
on a Nifty weekly expiry day). I only read and asked; nothing was fixed, changed or traded.

## What I did, in plain words

1. **Your conversations, last 7 days** (125 thread files, 323 questions). How you ask: almost always by voice, from Toronto, in long spoken
   sentences that carry two to four questions at once ("what happened, what did we do, what did you see and what did you find?"). You use
   Toronto words for India's day ("yesterday", "Monday already happened in India, right?"), you name stocks the way they sound ("Jio Finance",
   "Geofin"), you ask what waits for your yes, and you push back when the answer is about the wrong day. Your busy times are 6 to 8:30 am
   Toronto (India's evening, after the close) and 9:30 pm to midnight Toronto (India's morning, before and at the open). Some threads (27 Oct,
   31 Oct) are another assistant reading questions to Ananta and grading them out loud; I left those out of the "how Madhav asks" picture.
2. **73 new questions in your style**, asked to the India Ask in dry runs (nothing saved, nothing flagged, nothing traded), voice on:
   45 at the real moment (9:25 pm Toronto, before the 9:30 pm job), 7 more at the same moment just after the 9:30 pm job, and 21 at five
   other moments: mid-session Monday 10:20 IST; Monday 8:30 am Toronto after the close; Tuesday 10 Nov (an NSE holiday); Sunday 8 Nov
   (Diwali, Muhurat Sunday); and Sunday 14 March 2027 (the first night of summer time). Other moments use the builders' own stand-in prices.
3. **Every number checked** against /v3/live, /v3/surface/today, /v3/surface/money, /v3/surface/proof, /v3/options, /v3/morning (snapshots
   at 9:21 pm and again at 9:33 pm, after the 9:30 pm job), the files under ~/ananta_data/india, the NSE F&O day file, the launchd jobs and
   the job logs in ~/ananta_runs.

**Totals: 34 findings: 10 high, 12 medium, 12 low** (plus two things I could not verify, listed at the end).

One thing I could not reach: "what's waiting for my yes" and your flags come from the Jarvis service (port 8100), which needs your token; I
did not open it, so those answers are not checked here.

## Findings

Times are Toronto unless marked IST. "Real" means asked at the real moment (Mon 2 Nov ~9:25 pm Toronto / Tue 3 Nov ~07:55 IST).

| # | Sev | What was asked (moment) | What Ananta said / showed | What is true | Evidence |
|---|---|---|---|---|---|
| 1 | High | The Today screen and the live block, before the open (real) | Today: "Nifty · Mon 2 Nov close 23,441, +0.0% on the day". /v3/live: "Nifty 23,440.80 (+0.00% on the previous close 23,440.80; opened 0.00)"; same for Bank Nifty and the VIX. Still so at 9:33 pm | Monday closed +1.68% (23,053.10 to 23,440.80), Bank Nifty +0.58%, VIX +1.31%. Before the open Zerodha's quote reports the last close as both "last" and "close" and the open as 0, and the code reads that as today's change | /v3/surface/today `numbers`; /v3/live `index_now.rows`; manifests/market_context.json words ("+1.7% on the day") |
| 2 | High | "How did my stocks do today?" (real); the live block | /v3/live: "Your holdings ... are up about Rs 0 (+0.00%) on Monday 2 Nov", every row 0.0; practice book "its 101 open trades moved Rs +0 (+0.00%)". The Ask itself said "The rupee total shows Rs 0" | Your holdings rose about +2.24% (+Rs 2,172) on Monday (JIOFIN +4.3%, TATAPOWER +3.1%, KARURVYSYA -3.3%). Same root cause as #1 | /v3/live `holdings_today`, `practice_today`; jarvis/india/neveragain.py CASES[0] holdings line |
| 3 | High | "Is everything running fine? Did any job fail tonight?" (real, asked before and after 9:30 pm) | "No job shows a problem right now" / "no job reports a problem tonight". Today screen: "Everything is running" | Tonight's 7 pm evening run got "403 Forbidden" from Zerodha on the holdings call and on the index history calls (day and minute bars) | ~/ananta_runs/india_evening.err, lines 294-359, all after the "2026-11-02_19:00:05 evening" header |
| 4 | High | "Did the Zerodha snapshot work tonight?" (real) | "Yes, sir. The account snapshot ... was taken at 23:06 IST on 2 Nov ... so tonight's ratings use fresh holdings" | 23:06 IST is 12:36 pm Toronto, the midday snapshot. Tonight's snapshot in the 7 pm run failed (403 on /portfolio/holdings) | india_evening.err line 294; account snapshot taken_at 2026-11-02T17:36Z |
| 5 | High | "What time is your morning sign-in to Zerodha in my time?" and "Is everything running?" (real, 9:28 pm) | "9:40 pm Toronto, 08:10 IST ... about 12 minutes from now ... the last automatic sign-in worked on Sunday 1 Nov at 9:40 pm" | Since your yes on 2 Nov the sign-in runs at 7:35 pm (06:05 IST), with retries at 7:50 and 8:40 pm; tonight it signed in at about 7:31-7:46 pm. The live block's own timetable says 7:35 pm. After the 9:30 pm job the answer became right (7:46 pm) | launchd com.ananta.india.autologin (Hour 19 Min 35 / 19:50 / 20:40, read with plutil -p); india_autologin.log login_time 00:31 and 00:46 UTC; /v3/live `data_timing` |
| 6 | High | "But the Money screen says no open option positions. Which one is right?" (real) | "I can't see the Money screen's figure from here. It may be reading your real account ... but that is a guess" | The Money screen (/v3/surface/money options_book) says "No open option positions" and counts 0 Nifty trades, while the options ledger holds two open longs (Bank Nifty 55000 CE, Nifty 23300 CE) closing at Tuesday's open. The screen is wrong and the Ask cannot see it although it is the same service | /v3/surface/money `options_book.open_words`, `by_index.NIFTY.trades = 0`; /v3/live `options_today.taken` |
| 7 | High | "How much is my account worth right now?" (real) and the screens | Ask: "about Rs 163,141: Rs 99,541 in stocks, Rs 34,000 options, Rs 29,600 cash". Today and Money at the same minute: "₹1,62,645: ₹99,153 stocks, ₹34,000 options, ₹29,492 cash, 13 stocks". Twelve minutes later: "₹1,62,616 ... ₹50,000 options", stocks ₹85,731 | Three different totals in 12 minutes. The Money screen's own holdings list has 14 rows adding to ₹1,11,641 under a header of ₹99,153 (later ₹85,731) "in 13 stocks"; the Ask said 14 | /v3/surface/money at 9:21 and 9:33 pm (`value_inr`, `stocks_inr`, `holdings`); /v3/options `allocation.sleeves.now` (pool 163,141) |
| 8 | High | "The Today screen says cut list UNITDSPR, Tata Power, IDEA, TMCV but the plan says nothing on the cut list" (real) | Ask: "the evening list is TATAPOWER, LICI, TMCV, KARURVYSYA, JIOFIN and IEX". Today (still at 9:33 pm): "Cut list: UNITDSPR, TATAPOWER, IDEA, TMCV" | At 9:33 pm Money grades TATAPOWER B "hold", TMCV B "hold", UNITDSPR and IDEA B "tidy". Four different "what to sell" lists live at once (Today card, Money grades, the managed book's 10 sales, the allocator's IEX/JIOFIN). Grades jumped 20-30 points in one night: JIOFIN 21 to 51, TATAPOWER 46 to 66, TMCV 36 to 56, the same stocks the managed book sold that morning as cuts | /v3/surface/today `cards[holdings]`; /v3/surface/money `holdings` at 9:21 vs 9:33 pm; paper/allocation_ledger.jsonl last row `grades` |
| 9 | High | "Good morning Ananta, what happened in the Indian market today and what did we do?" (Mon 8:30 am, after the close) and "When does the morning view come, in my time?" (March moment) | Both answered by reading out "The view for 2 Nov: US: the S&P 500 closed -1.8% (30 Oct) ... Nifty closed at 23,053 on 30 Oct": Friday's numbers, nothing about Monday's close or what Ananta did | Monday closed 23,441 (+1.7%); the options line took two trades, the managed book made 13 fills. The words "good morning" / "morning view" route the question to the stored morning view, whatever was asked. This is your usual opener | out_m2 Q1, out_m4 Q3 (audit run); /v3/morning |
| 10 | High | "Is tomorrow an expiry day?" (Mon 8:30 am) | "the monthly one is on 24 Nov" | 24 Nov is an NSE holiday (Guru Nanak); the November monthly expiry is Mon 23 Nov, as the options ledger (BANKNIFTY26NOV, expiry 2026-11-23) and the NSE F&O day file show. At the real moment the Ask gave 23 Nov correctly, so the answer depends on the moment | ~/ananta_data/india/manifests/nse_holidays.json; sealed/silver/fo_bhavcopy 2026 (NIFTY expiries 2026-11-09, 2026-11-23); /v3/live `options_today.taken[0].expiry` |
| 11 | Medium | The allocator's plan, and "the allocator wants to sell IEX and Jio Fin into cash. Is that happening? When?" (real, 9:2x pm) | /v3/options at 9:21 pm: plan "for_session 2026-11-02", built 9:18 pm Monday from 30 Oct data, guard "Next decisions at the open on 2 Nov", moves "at the session's close (not filled yet)". Ask: "queued ... the earliest it happens is this evening's close" | The plan was for a session that had already closed. By 9:33 pm the moves (₹16,000 cash to options, IEX and JIOFIN to cash) had been applied silently and the next plan said "Nothing to move today". The allocator runs every 5 minutes on whatever read model exists, so from the close until the 9:30 pm job it plans for the finished day | launchd com.ananta.india.allocator (StartInterval 300); paper/allocation_ledger.jsonl; /v3/surface/money at 9:21 vs 9:33 pm |
| 12 | Low | "Why did you sell ten stocks but buy only three? Where is the rest of the money?" (real) | "the facts don't give the exact cash left after the three buys" | The managed book's own view holds it: cash ₹43,614, stocks ₹83,699, value ₹161,313. (The answer's other parts were right: at most 3 new names a week, and on the ₹34,000 question the Ask correctly said ₹16,000 had gone options to cash on 22 Oct, which the allocation ledger confirms.) | paper/managed/view.json `cash_inr`; ananta-records india/managed.py `max_new_per_week`; paper/allocation_ledger.jsonl (22 Oct row) |
| 13 | Medium | "Overall how much has the options line made or lost since it started?" (real) | "the only total I have is for Bank Nifty ... -13,146. I don't have a matching combined figure for the Nifty trades" | -13,146 is the whole book (Nifty has 0 scored trades). A second options book, the expiry-day recorder, has 27 trades for -₹31,440 and is never mentioned. The options line's own count also disagrees across screens: 6 sessions (Money, Proof) vs "5 sessions on record" (Today chances card); graded "after 20" (Money words, Proof) vs "a grade needs about 10", and a grade "A, score 72" shown next to "too early to grade" | /v3/options `by_index`, `recorder`; /v3/surface/today chances card; /v3/surface/money `options` |
| 14 | Medium | "How many open trades does the practice book have?" (real, before 9:30 pm) | "141 open trades in the last official record ... The live view today shows 101 held, a different count, so use 141" | Three counts in one hour: 141 (official, 30 Oct), 101 (live block), 151 (the 9:30 pm job). Nobody says which trades the 101 leaves out | /v3/live `practice_today.held`; ~/ananta_runs/india_paper.log tail ("151 open positions") |
| 15 | Medium | "And Bank Nifty and the VIX, how much did they move?" (real) | Answered only the VIX, "15.43 (+0.9%)", from the market summary; nothing on Bank Nifty | Bank Nifty +0.58% to 55,002. The VIX is 15.50 (+1.31%) in Zerodha's close and 15.43 (+0.85%) in the market summary: two VIX numbers in the same service | /v3/live `index_now`; manifests/market_context.json `india_vix` |
| 16 | Medium | "So what do you expect when it opens?" (real) | "The latest US close I hold is Friday's, when the S&P 500 fell 1.8%" | Monday's US close is on disk since 7 pm (SPY 752.10, -0.5%); the market summary only reads FRED, 3 days behind. Its "rupee, same day" line is from Wed 28 Oct | bronze/us_close/SPY/SPY_20261018_20261102_20261103T020011.json (last row 2026-11-02); manifests/us_close.jsonl; market_context.json words |
| 17 | Medium | The options line's paper loss (live block, Money, Ask) | "Nifty 23300 CE ... Rs 91.15 now, about Rs -1,261 a lot on paper (in loss)" | Rs 91.15 is the official NSE close, but with the Nifty at 23,440.8 that call is 141 points in the money and expires today; it cannot be worth less than about Rs 141 at the open. The screen states a loss as fact; the Ask (to its credit) said not to trust it | NSE F&O day file 2026-11-02, NIFTY 2026-11-03 23300 CE close 91.15, underlying 23440.8 |
| 18 | Medium | After the 9:30 pm job (real, 9:33 pm) | /v3/live `practice_today` and `managed_today` both become empty ({"words": null}) | Between 08:00 and 09:15 IST the live block has nothing to say about the practice book or the managed book, so "what did we do" in that window falls back to older facts | /v3/live at 9:33 pm |
| 19 | Medium | Today's "What to watch" card on Tuesday morning (real) | "Next options expiry: 3 Nov (NIFTY). The lines that decide the day's label: above 23,122 is an up day, below 22,984 a down day" | Those lines are Friday's close ±0.3%. Monday closed at 23,441, already above both, so any Tuesday would be called an "up day". The card has no date; it is the 2 Nov morning view's, shown until 10 pm | /v3/surface/today `cards[watch]` |
| 20 | Medium | "When does the practice book pick for tomorrow, in my time?" (real) | "for tomorrow's session (Tuesday 4 Nov in India) that is tomorrow night at 9:30 pm" | Tuesday is 3 Nov; the next session after today's is Wednesday 4 Nov | calendar |
| 21 | Medium | "When does the clock change again and will your jobs move?" (real) | "I can't see whether my jobs are pinned to the Toronto clock or the India clock, so I can't promise whether they move in March" | The jobs are on Toronto clock times, and a daily job (schedulecheck, 6 pm) checks each one against its India time and moves it ("India schedule: every job is on its Indian time", 2 Nov 6 pm). Ananta has this and says "I can't" | jarvis/india/schedule.py; ~/ananta_runs/india_schedulecheck.log |
| 22 | Medium | "Is today an expiry day?" on the holiday Tuesday 10 Nov (holiday moment) | "when an expiry falls on a holiday the exchange normally moves it ... which would make it Monday 9 Nov. I haven't confirmed that for this week" | The NSE F&O day file already lists a NIFTY expiry of 2026-11-09. At the real moment the Ask did give Monday 9 Nov, so this fact reaches it only sometimes | sealed/silver/fo_bhavcopy 2026 (expiry 2026-11-09 rows) |
| 23 | Medium | How the "as if" tests work (all non-real moments) | At Mon 8:30 am the Ask quoted "sold 59 JIOFIN at Rs 207 ... bought 3 AJANTPHARM at Rs 3,481" | Those fills were only booked at 7 pm that evening. LIVE_OVERRIDE freezes only the today block; the managed book, lookups and grades are read as they are now. The nightly "never again" cases can therefore pass on data that did not exist at the moment they replay | jarvis/india/neveragain.py `live_at`; out_m2 (audit run) |
| 24 | Low | "Are there any new picks for the open today?" (real, after 9:30 pm) | Read out RATNAVEER (a breakout pick) | RATNAVEER is not in the spoken-name list, so the voice spells the ticker. Every other ticker in tonight's 73 answers was mapped | jarvis/india/voice.py `say_names` (checked all tickers in the audit answers) |
| 25 | Low | "How did my stocks do today?" (Mon 8:30 am) | "The Nifty gained a little less than 2.24%? No, it gained less in the other direction: ..." | A muddled self-correction is spoken aloud | out_m2 (audit run) |
| 26 | Low | "Are the options trades closed?" (Mon 8:30 am); "What did the options line do this morning?" (mid-session) | The first starts by pasting the raw clock sentence ("It is Monday 2 Nov, 19:00 in India ... 3 h 30 min ago."); the second ends mid-sentence ("... and is.") | Voice quality: raw block text and a cut sentence | out_m2, out_m1 (audit run) |
| 27 | Low | "When will you book the practice picks?" (mid-session) | "I don't have a stated time for when today's open-price entries are booked, so I won't guess" | The timetable in the same block says the engine books them at 9:30 pm Toronto (08:00 IST) | /v3/live `data_timing`, `practice_today.words` |
| 28 | Low | The options line's decision window (Muhurat moment; Money screen) | "decides only between 09:15 and 10:15" / Money: "decided between 09:15 and 10:15" | The timetable and the ledger say 09:15, 09:30 and 09:45 IST | /v3/surface/money `options_book.words`; /v3/live `data_timing` |
| 29 | Low | "Is the market open tomorrow?" (Sun 8 Nov) | "a normal NSE session ... a regular weekday" | Monday 9 Nov is the moved Nifty weekly expiry and the eve of the Diwali holiday; worth saying | fo_bhavcopy expiry 2026-11-09; nse_holidays.json |
| 30 | Low | The timetable at a future moment (March moment) | The timetable words are built from today's date (schedule.ist_of uses "now"), not from the moment asked | In March the India times printed next to Toronto times would be an hour off until the schedule check moves the jobs. Fine today, wrong for any "as if" test across the clock change | jarvis/india/schedule.py `ist_of`, `day_words`; livesession.data_timing ignores the clock it is given |
| 31 | Low | Proof and Today health lines (real) | Proof: "Nightly check 1 Nov: 7 of 7 ..." at 9:33 pm on 2 Nov; Today at 9:21 pm: "Everything was running at the last check · checked 508 min ago" | The health line was 8.5 hours old when shown; the exam line is a day old | /v3/surface/proof `exam`; /v3/surface/today `running` |
| 32 | Low | Flag comments by number | Code adds a fixed 81 to the number you say ("Flag 5" becomes request 86) | Works only while the board keeps that exact offset; a reset or a crypto flag in between breaks it silently | jarvis/india/ask.py, flag-comment block (`int(m.group("n")) + 81`) |
| 33 | Low | "What did you find last night?" (mid-session) | "three of its stock kinds of buy rule (pullbacks, reversals and the random comparison picks)" | Garbled phrase; also calls the random comparison picks a "buy rule" | out_m1 (audit run) |
| 34 | Low | "Why is the managed book +0.51% since 30 Oct if it only started trading on Monday?" (real) | "I don't have the split between the two" | The book's start value (₹160,499 on 30 Oct) and its Monday fills are both on disk, so the split is a subtraction; Proof also says the trial "started 2 Nov" while Money says "since 30 Oct" | paper/managed/view.json `start_inr`, `filled_today`; /v3/surface/proof clocks |

**Not verified (could not reach, no finding counted):** (a) "What's waiting for my yes?" said "nothing" in every dry run because the dry
run cannot read Jarvis without your token; the Today screen showed 0 drafts at 9:21 pm and 1 at 9:33 pm, and the reconstruction answer said
"1 draft waits". (b) "Any flags I raised still open?" got "I don't have your flag list in front of me this turn"; whether the real (token)
path fetches the list I could not test.

**What was right** (so you know the checks were not one-sided): the clock and Toronto/India time words at all six moments; "the market
opens in 45 minutes" correctly refused on the 10 Nov holiday; the 9.5-hour gap after March's change; Monday's close (23,441, +1.7%) when
asked directly; the expiry of the Nifty option on Tuesday; the managed book's 10 sales and 3 replacements with prices; the replacement for
Jio Financial and Tata Power; FII/DII for Monday; the holiday list; the next Nifty expiry moving to Mon 9 Nov (at the real moment); company
names for voice (all but one).

## The patterns behind them

1. **One fact, several sources, no single owner.** The account's value has three (the allocator's pool, the account book, the holdings
   snapshot); "what to sell" has four (Today's cut list, Money's grades, the managed plan, the allocator); the options line has three (the
   live ledger, the Money book, the expiry-day recorder); the practice book's open trades have three (141, 101, 151); the VIX has two. Each
   screen and each answer picks one, so they disagree in the same minute (#6, #7, #8, #13, #14, #15).
2. **Zerodha's quote is read the same way at every hour.** Outside the session its "close" is the last price, so today's change becomes
   0.00% and "opened 0.00" on the Today screen, in the live block and in your holdings (#1, #2). The never-again cases use stand-in prices
   with a proper previous close, so they never see this.
3. **The 7 pm to 9:30 pm gap.** Several facts (sign-in, job health, the read model, the allocator's day) are only refreshed by the 9:30 pm
   job. Between your new 7:35 pm sign-in and 9:30 pm, Ananta speaks from the night before (#5, #11, #19), and the allocator, which runs
   every 5 minutes, plans for a session that has already closed.
4. **Health means "the job exited", not "the job worked".** The 403 errors sit in the evening job's error file, but nothing reads that
   file, so the screen and the voice both say all is well (#3, #4).
5. **Fixed routes beat the question.** "Good morning" or "morning view" returns the stored morning view, whatever you asked (#9).
6. **"I can't" when the fact is one screen away.** The Money screen, the job schedule, the managed book's cash, Monday's US close, the
   moved expiry dates and the booking time are all on disk or on the same service, yet the Ask says it cannot see them (#6, #12, #16, #21,
   #22, #27, #34). The same question gets the right answer at one moment and "I haven't confirmed" at another (#10, #22).
7. **Grades swing overnight and the screens lag the swing.** A stock can be a "cut" in the morning, sold by the managed book, and a "hold"
   that night, while the Today card still lists it as a cut (#8).
8. **The "as if" tests only freeze part of the world.** The today block is frozen, everything else is read as of now, so a replayed
   morning question can see fills booked that evening (#23, #30).

## What I would change (for the builders; I changed nothing)

1. Previous close from the last finished session's own closing bar (the read model or the NSE day file), never from Zerodha's quote when
   the session is not open; add a never-again case at 07:50 IST with real Zerodha-style quotes (open 0, close = last).
2. One owner per number: one function for the account value, one for "what to sell", one for the options book (including open
   positions and the recorder), one for the practice book count; every screen and the Ask read those, and a nightly check compares the
   screens with each other and fails loudly when they differ.
3. Job health reads each job's error file and log for the run that just happened (403, Traceback, "Forbidden"), not only whether it ran;
   tell the Ask and the Today screen "the 7 pm Zerodha snapshot failed" in plain words.
4. Refresh the sign-in and job facts when each job runs, not only at 9:30 pm; stop the allocator from planning for a session that has
   already closed (it should wait for the day's data or plan for the next session).
5. Let a direct question win over a stored route: "what happened today" after "good morning" is a question about today.
6. Give the Ask the Money screen's own output, the schedule check, the managed book's cash, Monday's US close and the F&O expiry list,
   and add a rule to the grader: an "I can't" answer when the fact is in the facts counts as a failure.
7. Show a grade change with its reason ("TATAPOWER moved from trim to hold tonight because the Nifty left its downtrend"), and date the
   Today cards ("written before the 2 Nov open").
8. Freeze the whole world in the "as if" tests (or at least drop facts written after the moment), and let the timetable take the moment's
   date.
9. Small ones: add RATNAVEER (and any new pick) to the spoken names automatically from the NSE company list; keep the options window in
   one place; drop the fixed +81 flag offset in favour of the board's own numbers.

## Files from this run

The 73 dry-run answers and the endpoint snapshots are in /tmp/audit1103 on your Mac (out_m0 to out_m6, ep_*, ep2_*, ep3_*). They are
working files and will go when the Mac clears /tmp.
