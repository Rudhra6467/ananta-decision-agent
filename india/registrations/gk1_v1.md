# GK1 v1 (spec, written 2026-10-27 before any outcome was read)

**Asked by:** Madhav, 27 Oct 2026 18:26 Toronto: "yes please also run the three studies on the gaps the grader named" (the grader named option Greeks among the topics Ananta has no test for)

**Question:** Option Greeks and time decay: does time decay make buying Nifty and Bank Nifty options on expiry day lose more than the index move earns, do longer-dated options do better than the nearest expiry on the same intraday trades, and do options imply bigger moves than the index then makes, by days to expiry?

**Hypothesis:** Buying options loses to time decay (theta), worst on expiry day: an at-the-money straddle bought at the open on expiry day loses money by the close after costs, and loses more than the same straddle bought three sessions before expiry; on the same intraday index trades an option on the next expiry earns more per rupee of premium than the nearest (highest-theta) expiry; and the move the options imply is bigger than the move the index then makes, at every distance from expiry.

## Data

- **options_daily:** silver/fo_bhavcopy 2014-2023: NIFTY and BANKNIFTY OPTIDX daily open and close per strike and expiry (real traded prices), lot size
- **greeks:** silver/fo_greeks 2014-2023: settle, forward, years to expiry T and implied volatility per strike (IV solved from the settle)
- **index:** silver/kite_index day: the index open and close per session (2003-2023)
- **expiries:** the actual expiry of each option row in the bhavcopy and greeks (weekly Bank Nifty from 27 May 2016, weekly Nifty from 11 Feb 2019; earlier monthly), sessions counted on the trading calendar silver/calendar
- **sp1_trades:** gold/studies/SP1_outcomes.parquet (the completed SP1 research 2015-2023, not the holdout): candidate trades at D1 and D2 with the ATRSTOP and T1515 exits, the single nearest-expiry option leg as stored
- **nothing_sealed:** no 2024+ row, no sealed folder, no holdout row

## Definitions

- **exp0 straddle_oc:** on an expiry day of that index, buy the at-the-money call and put of the expiring series (strike nearest the index open) at their daily open prices and sell both at their daily close; net return on the premium paid, after india.costs option charges and sp1's half-spread model (max(tick floor, 0.25% of premium) per leg per side); both legs need a traded open and close
- **exp3:** the same straddle on the session three trading days before that expiry, same expiry series
- **exp0_vs_exp3:** expiry-day straddle return minus the three-sessions-before straddle return, compared by calendar quarter
- **realised_vs_implied:** for each index and session d with an at-the-money implied volatility (average of call and put nearest the forward, flag ok) on the nearest expiry: the realised absolute log move of the index from d's close to the expiry close divided by the expected absolute move the IV implies (IV * sqrt(T) * sqrt(2/pi)), minus 1; buckets by trading sessions from d to expiry: 1, 2-3, 4-7
- **next_vs_near:** for each SP1 candidate trade: the same at-the-money option bought at entry and sold at the index exit, priced with sp1.option_leg on the NEXT expiry of the previous-session chain (its own IVs and carry) instead of the nearest; per trade next-expiry return on premium minus nearest-expiry return on premium

## Statistics

- **absolute:** straddle returns: calendar-quarter means, t across quarters (india.teachers_stock.absolute)
- **paired:** exp0_vs_exp3 and next_vs_near: per calendar quarter (straddle) or month (SP1 trades) the mean difference, t across blocks
- **realised_vs_implied:** calendar-quarter means of the ratio minus 1, t across quarters
- **periods:** development to 2017 (options from 2014), validation 2018-2023; nothing from 2024 on
- **verdict:** india/registry.record standard rule; 16 blocks per period

## Bar

Family options_eod; union k = 46, z = 3.267 (families 'options_intraday' (16) and 'options_eod' (22, OS1 included) = 38, plus these 8; k frozen at 46).

## Versions (expected sign)

- NIFTY|exp0|straddle_oc: -
- BANK|exp0|straddle_oc: -
- NIFTY|exp0_vs_exp3|straddle_oc: -
- BANK|exp0_vs_exp3|straddle_oc: -
- SP1|next_vs_near|ret: +
- ALL|dte1|realised_vs_implied: -
- ALL|dte2_3|realised_vs_implied: -
- ALL|dte4_7|realised_vs_implied: -

**Not claimed:** The options line stays shadow and keeps its one plain lot; a pass is a description of option pricing, a proposal at most.

Results: `gk1_results_v1.md`; code: `india/lab4.py`.
