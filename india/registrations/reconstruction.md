# Reconstruction, session 2026-10-29 (rules rx-in-v1-2026-10-23, built 2026-10-30T02:30Z)

29 Oct: Nifty in a downtrend. Ananta picked 4 stocks; of the day's 23 biggest rises it held 9 and missed 8 that no rule was watching, and it held 14 of the 25 biggest falls. 6 closed trades reviewed (5 never worked, 1 gave back). Nothing went to the repair shop; 1 idea waits for your yes.

## A. The market
Nifty 22,937, downtrend: below both averages (-1.5% vs 50-day, -4.6% vs 200-day); 44% of the liquid 250 above their 200-day; VIX 15.12.
- Up: ACUTAAS +7.2% (caught); SYRMA +6.8% (missed, class a); ADANIPORTS +6.3% (missed, class b); JSWENERGY +5.6% (missed, class b); ADANIENSOL +5.5% (missed, class b); IIFL +5.4% (missed, class a)
- Down: CARTRADE -5.7% (held_into_fall); HEROMOTOCO -4.1% (missed, class b); OLAELEC -4.1% (held_into_fall); RRKABEL -3.8% (missed, class b); NEULANDLAB -3.5% (held_into_fall); NAVINFLUOR -2.8% (held_into_fall)

## B. What people did (public records, stamped at their public time; yardstick only)
FII net sold ₹944 crore; DII net bought ₹1,924 crore; 4 bulk/block deals in our universe (largest: JUMP TRADING FINANCIAL INDIA PRIVATE LIMITED BUY PCJEWELLER ₹90.9 crore).
- League: Of the day's 20 best one-day trades, Ananta held 6, passed on 3 and had no rule for 10. Its 89 positions did +0.6% against +0.7% for the average stock (better than 40% of random picks); the best possible was +4.5%.
- announcements: missing (no announcement file for the session (the announce fetch runs with the evening job))

## C. What Ananta did
Chose 4 research signals and 5 random controls from 374 candidates; 365 rejected (most often: REV outside_liq_top x144, PULL outside_liq_top x139); 14 fills, 1 exits at the reference exit; called the next session BULLISH; index line: 9 decisions, 0 error; allocation: no row.

## D. What it did not do, and was that right
Of the top 23 rises the book held 9 (plus 1 by the random control), missed 5 after a family fired (class a), 8 with no family positioned (b), 0 untradeable (c); it held into 14 of the top 25 falls (₹11,985 against it so far). 

## E. Trade reviews (6 trades closed 3 sessions ago, exit day 2026-10-26)
- NEVER_WORKED: JSWINFRA (pullback in an uptrend): exit stop, -7.4% net; never got a quarter of a risk unit above the entry (the entry timing was poor)
- NEVER_WORKED: BELRISE (pullback in an uptrend): exit stop, -9.0% net; never got a quarter of a risk unit above the entry (the entry timing was poor)
- NEVER_WORKED: LTF (oversold reversal): exit stop, -6.9% net; never got a quarter of a risk unit above the entry (the entry timing was poor)
- NEVER_WORKED: IIFL (pullback in an uptrend): exit stop, -8.7% net; never got a quarter of a risk unit above the entry (the entry timing was poor)
- NEVER_WORKED: HAL (random control): exit stop, -5.1% net; never got a quarter of a risk unit above the entry (the entry timing was poor)
- GAVE_BACK: PAISALO (pullback in an uptrend): exit stop, -9.2% net; was up one and a half risk units at some point and still closed at or under the entry (no plan to protect a winner)

## F. Findings
- [DECISION · MISS_PATTERN · DRAFT] No family was positioned for 'breakout base, intraday run' on 3 of the last 6 sessions (e.g. JSWENERGY, BLUESTARCO, DLF, BANKBARODA). Question for a registered study: is there an entry rule, known before the move, for this situation? Development and validation years only.

## G. The staircase
No rule has proved itself yet. The stock rules have 8 of 20 trial sessions; the options line has 4; Ananta beat chance and the average stock on 5 of the 10 days needed.
- stock:BRK: SHADOW · shadow 6/20 sessions · beats RANDOM and MARKET on 5/10 independent sessions
- stock:PULL: SHADOW · shadow 6/20 sessions · beats RANDOM and MARKET on 5/10 independent sessions
- stock:REV: SHADOW · shadow 7/20 sessions · beats RANDOM and MARKET on 5/10 independent sessions
- options:SP1: SHADOW · shadow 4/20 sessions · beats RANDOM and MARKET on 0/10 independent sessions
- queue: {'to_file': 8, 'APPROVED': 15, 'DRAFT': 1}
