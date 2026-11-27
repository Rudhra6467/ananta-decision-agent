# HS1: what actually tells us a holding will lag or lead? (design, frozen 27 Nov 2026, before any run or outcome)

Madhav, 26 Nov 2026, 22:19 Toronto: "the stock adjustments and grading is not going great according to numbers and results. Why is it not up to the mark? What exactly should we do here in order to better this area ... help Ananta improve its decision process in this case of stock replacement." Then, 22:22: "Yes, let's set it up."

**A study, never a trading rule by itself.** It reads history only (2000-2023; the sealed years are never touched). Nothing in the managed book, the allocator or any pinned file changes because of it. A change to the cut or replacement rules afterwards needs its own written yes from Madhav, through the repair door, with the result in hand.

## Why this study

- The managed book's stocks and cash made +2.1% from 30 Oct to 26 Nov while the Nifty 500 made +10.0% (session 17 of 60; one market state, a strong rally).
- Ananta's own decisions cost about Rs 1,100 net (sold shares now worth Rs 2,095 more than sold for; replacements +Rs 778; the index-fund park about +Rs 455; costs Rs 259). Most of the gap is the holdings it kept.
- The cut study of 17 Nov (india/cutstudy.py) found today's grade alone right 53% / 52% against a random stock's 54% / 53%: no edge. Only the weakest fifth against the market, under its own 200-day average, was slightly better (56% / 55%).
- The grade gives 15 of 100 points to the holding's result on what was paid, and up to 10 to its size in the account. Neither says anything about where the stock goes next.
- All three replacements (chosen as calm and strong) trail the market (Ajanta -0.8%, Cipla +4.5%, Eternal +6.9% against NIFTYBEES +11.1% since 2 Nov).

## Part A: which measures say a holding will lag the market?

- **Universe, each month-end, point in time:** the 250 most-traded Nifty 500 names by median 60-session turnover (the grade's own universe), with survivors and delisted names as the lake holds them.
- **Target:** the stock's return over the next 20 and the next 60 sessions minus the Nifty 500's (equal-weight Nifty 500 as a second read). A "right cut" is a stock that then lags.
- **Measures, fixed now (no others added after the first look):**
  1. the grade's outlook part alone (trend, regime, volatility, liquidity: the grade without its result and size parts);
  2. strength against the Nifty 500 over 60 and 120 sessions;
  3. strength against the stock's own industry over 60 and 120 sessions;
  4. distance from the one-year high;
  5. close against the 50- and 200-day averages;
  6. 60-session volatility;
  7. the last results day's reaction (from NC1's announcement data: the stock's move on its latest results day beyond the Nifty), for 2010-2023 where announcements exist;
  8. controls: a random stock with the same count, and today's full grade.
- **Market states:** the allocator's own three (Nifty above both averages, between, below both), read on the month-end day.
- **Splits:** 2005-2014 to look, 2015-2023 to check (2000-2004 only builds the averages). One look at the check years.
- **What passes:** a measure's weakest fifth lags its strongest fifth by more than costs (0.5% a round trip) over 60 sessions, in both periods and in at least two of the three market states, at the ledger's bar for its family, and better than the random control and the full grade. Otherwise it reads REJECTED or INCONCLUSIVE, and that is the honest answer.

## Part B: what should replace a cut?

- **On the same months and universe,** the replacement rankers, each buying its top pick in the cut stock's place, held 60 sessions with the book's 7% stop:
  1. today's ranker (calm plus strength against the market, managed-v3 filters);
  2. strength only;
  3. calm only;
  4. the best Part A measure, if one passes;
  5. the Nifty index fund (NIFTYBEES, or the Nifty 50 index before NIFTYBEES has bars), the default to beat.
- **What passes:** a ranker beats the index fund after costs over 60 sessions in both periods and in at least two of the three market states. If none does, the honest result is that the index fund is the better replacement, and the proposal to Madhav says so.

## What it never does

- No trade, rule, pin, gate, book or score changes. No API credit. Runs only 08:30-19:30 Toronto, outside the sign-in, session and nightly windows, with a capped temp folder outside the repos (the NC1 lesson of 25 Nov).
- Results go to records india/registrations/hs1_results_v1.md, with the ledger rows, before anyone reads them as a rule.

## Beside it (reporting only; built 27 Nov: twins a4b7fd9, grade split 95c7f08)

- **Two twins for the managed book**, marked every evening from 30 Oct: the 30 Oct book held unchanged (no cuts, no buys, no park) and the 30 Oct stocks put whole into NIFTYBEES. The book's page then says what Ananta's own decisions added or cost in rupees.
- **The grade shown in two parts**: the outlook (the stock) and the fit (its size in the account). The fit's result-on-cost part is shown as a fact, not counted. Shown only; the cut rule keeps reading today's grade until HS1 is read and Madhav says yes.

## Frozen

Madhav said yes in the app on Thu 26 Nov 2026, 22:31 Toronto (open-list flag 292). Frozen unchanged from the draft of 26 Nov except this title and the two section notes; nothing has been run. Any change after this line is a new version (hs1_v2.md), never an edit.
