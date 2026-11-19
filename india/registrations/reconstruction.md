# Reconstruction, session 2026-11-18 (rules rx-in-v2-2026-11-06, built 2026-11-19T02:30Z)

18 Nov: Nifty in an uptrend. Ananta picked 1 stocks; of the day's 24 biggest rises it held 16 and missed 2 that no rule was watching, and it held 13 of the 25 biggest falls. 1 small fix went to the repair shop; 2 new ideas tonight; 4 drafts wait for your yes or skip. Value since 22 Oct: 0 findings changed a rule; 21 approved and 2 skipped drafts started 4 studies (RX1, RX2, RX3, K02-R1); in a paper trial: falls under the 200-day (RX1) 14/20; relative strength (RS) 11/20.

## A. The market
Nifty 25,228, uptrend: above its 50- and 200-day averages (+7.7% vs 50-day, +5.2% vs 200-day); 63% of the liquid 250 above their 200-day; VIX 15.53.
- Up: URBANCO +6.9% (caught); NAVINFLUOR +4.7% (caught); E2E +4.1% (caught); IIFL +4.0% (caught); RATNAVEER +3.1% (caught); MTARTECH +3.1% (caught)
- Down: TITAN -5.3% (held_into_fall); FCL -5.3% (held_into_fall); POLYCAB -5.1% (held_into_fall); KALYANKJIL -4.8% (held_into_fall); SKYGOLD -4.8% (held_into_fall); MANAPPURAM -4.6% (missed, class b)

## B. What people did (public records, stamped at their public time; yardstick only)
FII net bought ₹5,867 crore; DII net sold ₹3,160 crore; 9 bulk/block deals in our universe (largest: RAKESH CHOPDAR SELL AZAD ₹800.2 crore); 80 announcements on universe names, 8 on today's movers (the news read (FinBERT): 5 positive, 3 negative, 72 neutral announcements; a note, never a reason to trade).
- League: Of the day's 20 best one-day trades, Ananta held 15, passed on 0 and had no rule for 3. Its 141 positions did -1.4% against -1.3% for the average stock (better than 50% of random picks); the best possible was +2.3%.

## C. What Ananta did
Chose 1 research signals and 5 random controls from 141 candidates; 135 rejected (most often: PULL outside_liq_top x41, REV outside_liq_top x31); 8 fills, 11 exits at the reference exit; called the next session BEARISH; index line: 6 decisions, 0 error; allocation: no row.

## D. What it did not do, and was that right
Of the top 24 rises the book held 16 (plus 2 by the random control), missed 4 after a family fired (class a), 2 with no family positioned (b), 0 untradeable (c); it held into 13 of the top 25 falls (₹38,363 against it so far). 

## E. Trade reviews (0 trades closed 3 sessions ago, exit day 2026-11-13)

## F. Findings
- [SAFE · JOB_FAIL · to_file] One of Ananta's India jobs ('morningview') did not finish properly. It needs checking.
- [DECISION · OPTIONS_LINE · DRAFT] The index line traded the wrong way on 5 of its last 10 recorded sessions. Question for the SP1 playbook (pinned): which decision point misfires, and does the frozen model still beat its own no-trade baseline?
- [DECISION · MISS_PATTERN · DRAFT] No family was positioned for 'breakout range, intraday run' on 5 of the last 10 sessions (e.g. TATACONSUM). Question for a registered study: is there an entry rule, known before the move, for this situation? Development and validation years only.

## G. The staircase
No rule has proved itself yet. The stock rules have 21 of 20 trial sessions; the options line has 17; Ananta beat chance and the average stock on 10 of the 10 days needed.
- stock:BRK: SHADOW · shadow 18/20 sessions · beats RANDOM and MARKET on 10/10 independent sessions
- stock:PULL: SHADOW · shadow 14/20 sessions · beats RANDOM and MARKET on 10/10 independent sessions
- stock:REV: SHADOW · shadow 13/20 sessions · beats RANDOM and MARKET on 10/10 independent sessions
- options:SP1: SHADOW · shadow 17/20 sessions · beats RANDOM and MARKET on 0/10 independent sessions
- queue: {'to_file': 11, 'APPROVED': 21, 'SKIPPED': 2, 'DRAFT': 4}
