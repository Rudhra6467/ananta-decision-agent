# Reconstruction, session 2026-11-23 (rules rx-in-v2-2026-11-06, built 2026-11-24T02:30Z)

23 Nov: Nifty in an uptrend. Ananta picked 4 stocks; of the day's 25 biggest rises it held 14 and missed 7 that no rule was watching, and it held 19 of the 25 biggest falls. 11 closed trades reviewed (3 lost small, 5 clean, 2 gave back, 1 never worked). 1 small fix went to the repair shop; 1 new idea tonight; 1 draft waits for your yes or skip. Value since 22 Oct: 0 findings changed a rule; 25 approved and 2 skipped drafts started 4 studies (RX1, RX2, RX3, K02-R1); in a paper trial: falls under the 200-day (RX1) 17/20; relative strength (RS) 14/20.

## A. The market
Nifty 25,366, uptrend: above its 50- and 200-day averages (+7.7% vs 50-day, +5.7% vs 200-day); 63% of the liquid 250 above their 200-day; VIX 17.6.
- Up: RATNAVEER +8.9% (caught); POLICYBZR +6.5% (caught); JSWINFRA +3.6% (caught_by_control); TCS +3.5% (missed, class b); LAURUSLABS +3.3% (caught); PVRINOX +2.9% (missed, class b)
- Down: APLAPOLLO -21.3% (held_into_fall); TATASTEEL -8.4% (missed, class b); PFOCUS -6.3% (held_into_fall); SKYGOLD -6.3% (held_into_fall); E2E -5.0% (held_into_fall); FCL -4.9% (held_into_fall)

## B. What people did (public records, stamped at their public time; yardstick only)
FII net bought ₹5,673 crore; DII net sold ₹2,760 crore; 11 bulk/block deals in our universe (largest: STEADVIEW CAPITAL MAURITIUS LIMITED-FDI SELL LENSKART ₹835.2 crore); 76 announcements on universe names, 12 on today's movers (the news read (FinBERT): 2 positive, 4 negative, 70 neutral announcements; a note, never a reason to trade).
- League: Of the day's 20 best one-day trades, Ananta held 13, passed on 1 and had no rule for 4. Its 143 positions did -1.2% against -1.4% for the average stock (better than 64% of random picks); the best possible was +2.6%.

## C. What Ananta did
Chose 4 research signals and 5 random controls from 198 candidates; 189 rejected (most often: PULL outside_liq_top x70, REV outside_liq_top x55); 9 fills, 20 exits at the reference exit; called the next session BULLISH; index line: 9 decisions, 0 error; allocation: no row.

## D. What it did not do, and was that right
Of the top 25 rises the book held 14 (plus 1 by the random control), missed 3 after a family fired (class a), 7 with no family positioned (b), 0 untradeable (c); it held into 19 of the top 25 falls (₹17,684 against it so far). 

## E. Trade reviews (11 trades closed 3 sessions ago, exit day 2026-11-18)
- LOST_SMALL: TECHM (20-session breakout on volume): exit time, -1.0% net; a loss smaller than a risk unit with no better path on record
- CLEAN: BHARTIARTL (20-session breakout on volume): exit time, +11.5% net; a win that kept at least half of its best move
- CLEAN: INDHOTEL (20-session breakout on volume): exit time, +16.2% net; a win that kept at least half of its best move
- LOST_SMALL: HCLTECH (20-session breakout on volume): exit time, -2.7% net; a loss smaller than a risk unit with no better path on record
- CLEAN: ICICIBANK (20-session breakout on volume): exit time, +13.6% net; a win that kept at least half of its best move
- LOST_SMALL: AVALON (pullback in an uptrend): exit time, -8.9% net; a loss smaller than a risk unit with no better path on record
- CLEAN: ACUTAAS (random control): exit time, +19.7% net; a win that kept at least half of its best move
- CLEAN: PNB (random control): exit time, +23.9% net; a win that kept at least half of its best move
- GAVE_BACK: FCL (pullback in an uptrend): exit stop, -12.7% net; was up one and a half risk units at some point and still closed at or under the entry (no plan to protect a winner)
- GAVE_BACK: FCL (random control): exit stop, -11.4% net; was up one and a half risk units at some point and still closed at or under the entry (no plan to protect a winner)
- NEVER_WORKED: SAIL (20-session breakout on volume): exit stop, -7.3% net; never got a quarter of a risk unit above the entry (the entry timing was poor)

## F. Findings
- [SAFE · JOB_FAIL · to_file] One of Ananta's India jobs ('openingview') did not finish properly. It needs checking.
- [DECISION · EXIT_LESSON · DRAFT] 5 closed random control trades in the last 20 sessions were tagged GAVE_BACK: was up one and a half risk units at some point and still closed at or under the entry (no plan to protect a winner). Question for the G01 exit book cell CTL: does the registered exit that fixes this hold up on the development and validation years?

## G. The staircase
No rule has proved itself yet. The stock rules have 24 of 20 trial sessions; the options line has 19; Ananta beat chance and the average stock on 11 of the 10 days needed.
- stock:BRK: SHADOW · shadow 20/20 sessions · beats RANDOM and MARKET on 11/10 independent sessions
- stock:PULL: SHADOW · shadow 17/20 sessions · beats RANDOM and MARKET on 11/10 independent sessions
- stock:REV: SHADOW · shadow 13/20 sessions · beats RANDOM and MARKET on 11/10 independent sessions
- options:SP1: SHADOW · shadow 19/20 sessions · beats RANDOM and MARKET on 0/10 independent sessions
- queue: {'to_file': 14, 'APPROVED': 25, 'SKIPPED': 2, 'NOTE': 1, 'DRAFT': 1}
