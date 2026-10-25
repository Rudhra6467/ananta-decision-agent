# Reconstruction, session 2026-10-22 (rules rx-in-v1-2026-10-23, built 2026-10-25T02:30Z)

22 Oct: Nifty in a downtrend. Ananta picked 20 stocks; of the day's 25 biggest rises it held 9 and missed 14 that no rule was watching, and it held 9 of the 27 biggest falls. 2 small fixes went to the repair shop; nothing waits for you.

## A. The market
Nifty 22,688, downtrend: below both averages (-3.2% vs 50-day, -6.0% vs 200-day); 40% of the liquid 250 above their 200-day; VIX 15.73.
- Up: KAYNES +4.1% (missed, class b); INDHOTEL +3.9% (caught); POLICYBZR +3.0% (caught); BLUESTONE +2.8% (caught); UJJIVANSFB +2.5% (missed, class b); AUROPHARMA +2.0% (missed, class a)
- Down: KEI -8.5% (missed, class b); CUPID -6.1% (missed, class b); SWIGGY -5.5% (missed, class b); ZEEL -5.4% (held_into_fall); FINCABLES -5.2% (held_into_fall); KALYANKJIL -4.8% (missed, class b)

## B. What people did (public records, stamped at their public time; yardstick only)
FII net sold ₹3,459 crore; DII net bought ₹2,891 crore; 6 bulk/block deals in our universe (largest: JUMP TRADING FINANCIAL INDIA PRIVATE LIMITED SELL PCJEWELLER ₹414.8 crore); 106 announcements on universe names, 12 on today's movers.
- League: Of the day's 20 best one-day trades, Ananta held 7, passed on 1 and had no rule for 11. Its 35 positions did -1.2% against -1.2% for the average stock (better than 52% of random picks); the best possible was +1.7%.
- Notes from the web (public pages, notes only, never a reason to trade):
  - KAYNES: no public reason found; sources confirm KAYNES closed up about 4.07% at Rs 3,294 on 2026-10-22, but I found no exchange filing, company statement or news article from that day explaining the move. [C] https://finance.yahoo.com/quote/KAYNES.NS/history/, https://www.investing.com/equities/kaynes-technology-india-historical-data
  - UJJIVANSFB: No public page names a specific catalyst for the +2.5% close on 22 Oct 2026; the most likely driver is continued investor interest in the record Q2 FY27 results (PAT ₹365 crore, deposits above ₹50,000 crore, a proposed ₹409 crore preferential equity raise), and the bank filed its earnings-call transcript on 22 Oct, but no source links these to that day's move. [C] https://www.kalkine.co.in/article/announcements/ujjivan-small-finance-bank-nseujjivansfb-what-did-q2-fy27-earnings-call-reveal, https://www.screener.in/company/UJJIVANSFB/, https://www.kotakneo.com/ne
  - AUROPHARMA: no public reason found: the +2.03% close at ₹1,610.90 on 2026-10-22 is confirmed by price pages, but I found no exchange filing, company statement or news article explaining it. The stock opened lower and recovered during the session. [C] https://dhan.co/stocks/aurobindo-pharma-ltd-share-price/, https://www.valueresearchonline.com/stocks/41180/aurobindo-pharma-ltd/
  - KEI: KEI fell after its Q2 FY27 results on 21 Oct 2026, where operating (EBITDA) margins missed estimates (10.62% against about 11.5% expected), the EPC business made a loss, and weak Indian markets added to the pressure. [B] https://www.business-standard.com/markets/news/kei-industries-share-price-plunges-10-nears-52-week-low-here-s-why-126102200355_1.html, https://www.aryanage.com/article/48569/kei-industries-shares-cras
  - CUPID: no public reason found: I found no exchange filing, company statement or news item dated 22 Oct 2026 that explains the 6.1% fall (close ₹320.05 vs ₹340.75), which looks like profit-taking after a sharp rally and a record high of ₹368.95 on 12 Oct. [C] https://ticker.finology.in/company/CUPID, https://www.angelone.in/news/stocks/cupid-share-price-hit-52-week-high-in-intraday-trade-on-october-12-2026
  - SWIGGY: No company filing or news item gave a specific trigger for the drop; the best public explanation is continued pre-results selling to record lows, with Business Standard citing FPIs cutting their Swiggy stake from 13.96% to 8.55% in the September quarter. Swiggy's Q2 results came after the close, and the big post-results fall happened on Oct 23. [C] https://www.business-standard.com/markets/news/swiggy-slips-26-in-1-month-hits-record-low-stock-down-46-from-ipo-price-126102200468_1.html, https://www.marketsmojo.com/news/stocks-in-action/swiggy-ltd

## C. What Ananta did
Chose 20 research signals and 5 random controls from 754 candidates; 729 rejected (most often: REV outside_liq_top x368, PULL outside_liq_top x269); 26 fills, 7 exits at the reference exit; called the next session BULLISH; index line: 0 decisions, 1 error; allocation (autonomous): 1 paper move(s).

## D. What it did not do, and was that right
Of the top 25 rises the book held 9 (plus 1 by the random control), missed 1 after a family fired (class a), 14 with no family positioned (b), 0 untradeable (c); it held into 9 of the top 27 falls (₹18,315 against it so far). Of 694 research candidates it rejected, 606 have not run away and 29 are up 2%+ (hindsight).
- passed ANTELOPUS (PULL, outside_liq_top): +13.6% after 1 sessions (hindsight)
- passed NOVARTIND (PULL, outside_liq_top): +8.3% after 1 sessions (hindsight)
- passed IGIL (BRK, outside_liq_top): +6.8% after 1 sessions (hindsight)

## E. Trade reviews (0 trades closed 3 sessions ago, exit day 2026-10-16)

## F. Findings
- [SAFE · DATA_GAP · to_file] The session card has no announcements record for 2026-10-22: no announcement file for the session (the announce fetch runs with the evening job) (expected /Users/vamsie/ananta_data/india/bronze/announce_api/2026/20261022.json.gz).
- [SAFE · SIGNIN_LOST · to_file] The Kite sign-in was missing for the session of 2026-10-22: no Kite sign-in by 09:10 IST: the Kite token expired at 6 am IST: open http://127.0.0.1:8100/kite/login on the Mac. Jobs that ran empty because of it: autologin, evening, sp1paper, sp1paper.score, spreads. The TOTP key (Zerodha ticket) or the manual sign-in window fixes it; nothing else does.

## G. The staircase
No rule has proved itself yet. The stock rules have 4 of 20 trial sessions; the options line has 0; Ananta beat chance and the average stock on 2 of the 10 days needed.
- stock:BRK: SHADOW · shadow 3/20 sessions · beats RANDOM and MARKET on 2/10 independent sessions
- stock:PULL: SHADOW · shadow 4/20 sessions · beats RANDOM and MARKET on 2/10 independent sessions
- stock:REV: SHADOW · shadow 3/20 sessions · beats RANDOM and MARKET on 2/10 independent sessions
- options:SP1: SHADOW · shadow 0/20 sessions · beats RANDOM and MARKET on 0/10 independent sessions
- queue: {'to_file': 4}
