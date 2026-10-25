# Reconstruction, session 2026-10-23 (rules rx-in-v1-2026-10-23, built 2026-10-25T22:00Z)

23 Oct: Nifty in a downtrend. Ananta picked 20 stocks; of the day's 26 biggest rises it held 6 and missed 18 that no rule was watching, and it held 10 of the 27 biggest falls. 3 small fixes went to the repair shop; nothing waits for you.

## A. The market
Nifty 22,600, downtrend: below both averages (-3.4% vs 50-day, -6.3% vs 200-day); 35% of the liquid 250 above their 200-day; no India VIX close on file for the day. (The decision was made on a stale Nifty file; the Nifty numbers here come from the day's own close.)
- Up: ETERNAL +4.2% (caught); APOLLOHOSP +1.7% (missed, class b); CHENNPETRO +1.5% (missed, class b); RATNAVEER +1.4% (missed, class b); ONGC +1.1% (missed, class b); ASIANPAINT +1.0% (missed, class b)
- Down: SWIGGY -16.8% (held_into_fall); AVALON -6.4% (held_into_fall); IIFL -6.4% (held_into_fall); OLAELEC -6.3% (missed, class b); UJJIVANSFB -6.3% (missed, class b); HSCL -5.9% (missed, class b)

## B. What people did (public records, stamped at their public time; yardstick only)
FII net bought ₹888 crore; DII net bought ₹3,235 crore; 11 bulk/block deals in our universe (largest: GRAVITON RESEARCH CAPITAL LLP SELL SWIGGY ₹265.3 crore); 149 announcements on universe names, 4 on today's movers.
- League: Of the day's 20 best one-day trades, Ananta held 2, passed on 0 and had no rule for 13. Its 50 positions did -2.9% against -2.6% for the average stock (better than 20% of random picks); the best possible was +0.7%.

## C. What Ananta did
Chose 20 research signals and 5 random controls from 1008 candidates; 983 rejected (most often: REV outside_liq_top x574, PULL outside_liq_top x277); 25 fills, 17 exits at the reference exit; no call written; index line: 0 decisions, 1 error; allocation (autonomous): 2 paper move(s).

## D. What it did not do, and was that right
Of the top 26 rises the book held 6 (plus 1 by the random control), missed 1 after a family fired (class a), 18 with no family positioned (b), 0 untradeable (c); it held into 10 of the top 27 falls (₹33,354 against it so far). 

## E. Trade reviews (0 trades closed 3 sessions ago, exit day 2026-10-19)

## F. Findings
- [SAFE · JOB_FAIL · to_file] One of Ananta's India jobs ('morning') did not finish properly. It needs checking.
- [SAFE · JOB_FAIL · to_file] One of Ananta's India jobs ('paper') did not finish properly. It needs checking.
- [SAFE · WORDS · to_file] One part of the nightly review ('market') failed to build, so it shows as missing instead of guessing. It needs a code fix.

## G. The staircase
No rule has proved itself yet. The stock rules have 4 of 20 trial sessions; the options line has 0; Ananta beat chance and the average stock on 2 of the 10 days needed.
- stock:BRK: SHADOW · shadow 3/20 sessions · beats RANDOM and MARKET on 2/10 independent sessions
- stock:PULL: SHADOW · shadow 4/20 sessions · beats RANDOM and MARKET on 2/10 independent sessions
- stock:REV: SHADOW · shadow 3/20 sessions · beats RANDOM and MARKET on 2/10 independent sessions
- options:SP1: SHADOW · shadow 0/20 sessions · beats RANDOM and MARKET on 0/10 independent sessions
- queue: {'to_file': 7}
