# Option strategies Madhav wants tracked — 18 Oct 2026

Given by Madhav as "important options trading strategies that we gonna keep tap on, in research, paper and live". Three come from YouTube teachers (summaries Madhav supplied, not transcripts we fetched), one is his own from his India trading. Every one is a **hypothesis**, never a rule: it enters research, earns paper, and only then live, through the same gates as everything else. Madhav's instruction for the futures/options area: he is not fully knowledgeable here, so this section is designed and judged mainly on **reconstructions, comparisons and repair-shop evidence**, not on his eye.

## How each is judged (same for all four)
1. **Reconstruction:** write the teacher's rule exactly as stated, no improvements, and run it on the lake.
2. **Comparison:** against (a) no trade, (b) the same entries at random times in the same session window, (c) the simplest version of the same idea, so we know which part carries the result.
3. **Evidence:** after costs (brokerage, STT on option sells, exchange charges, GST, stamp duty, a labelled slippage estimate), per year, per volatility regime (India VIX tercile), with event days (Budget, RBI policy, US CPI, elections) shown separately. A claimed hit rate ("70–80%") is checked as stated and then replaced by what matters: average R, worst day, worst month.
4. **Verdict** in the repair shop: works / works only in a regime / does not survive costs / cannot be tested yet (and what data would fix that).

## The data problem, stated once
Our lake has Nifty and stocks as 5-minute bars from 2015 (Kite) and every option's **end-of-day** price, settlement and open interest from 2000 (NSE F&O bhavcopy). It does **not** have historical intraday option prices: Kite serves candles only for contracts that are still live, and free sources keep no expired-option intraday history. So:
- Rules on the **spot chart** can be tested now on index bars.
- Rules that need the **option price inside the day** are tested two ways: (a) a synthetic option price from the spot path, days to expiry and India VIX (Black-Scholes, labelled "synthetic"), and (b) a **forward recorder** from now on: every trading day after the close, pull 1-minute candles for the live Nifty and Bank Nifty contracts near the money, before they expire and vanish. Each month of recording turns synthetic evidence into real evidence.

## O-01 Triangle breakout, spot first then option (Nifty Gurukulam)
- Rule as given: 1-minute chart; a triangle forms; enter only when **spot** breaks out first and the **option chart** confirms; book in steps (1:1, 1:2) with multiple lots; exit when momentum slows or the pattern fails. "PMP (Pure Momentum Power)" is the creator's momentum filter.
- Testable now: triangle detection and breakout on Nifty spot (1-minute needs a Kite 1-minute pull for the index; 5-minute exists). Staggered exits vs single exit.
- Needs the recorder: the option-chart confirmation step.
- Open question for the reconstruction: PMP's exact definition is not in the summary; it is replaced by a declared stand-in (rate of change over N bars) and labelled as such until the definition is known.

## O-02 SuperTrend (10,2) + VWAP + VWMA(20), 3-minute (Telugu Trader Aryan)
- Rule as given: no trades before 9:25; buy calls when a candle closes above all three, puts when below all three; stop at the signal candle's low/high; target 1:2 or 1:3; one or two trades a day; skip when the three lines are bunched (sideways). Claimed accuracy 70–80%.
- Testable now on spot almost entirely (3-minute bars are built from 1-minute; option P&L synthetic until recorded).
- The "lines bunched = sideways" filter is made exact (spread of the three lines below X% of price) and X is chosen on the development years only.

## O-03 Expiry-eve short strangle with hedges (YouTube)
- Rule as given: at 3:00 pm the day before expiry, sell Nifty call and put about 1.5% away, buy cheap far hedges (about ₹1); exit at 50% premium decay or at 11:00 am next day; stop at 1% of capital used; skip Budget, RBI policy, US inflation, election and war days, and skip before weekends and long holidays.
- Testable now as an end-of-day version from the bhavcopy (enter at the previous close, exit at expiry-day close, strikes 1.5% away, hedges at the cheapest listed strikes). The 3:00 pm entry and 11:00 am exit need the recorder or synthetic prices.
- This is a short-option strategy: the test reports the tail first (worst single expiry, worst run of expiries, margin needed) before any average.

## O-04 Madhav's expiry late-session long straddle, "buy both, cut loser, ride winner"
- Rule (his words): on weekly expiry day after about 1:00–1:30 pm, buy ATM call and ATM put of the same strike; when the market clearly moves one way, close the losing leg and book or trail the winner; with no clear direction, take a small profit or exit on the stop; always out by 3:15–3:20 pm. A late-session gamma play with active leg management.
- Needs intraday option prices for the real test; synthetic version now from Nifty 5-minute (later 1-minute) bars and VIX, real version from the recorder.
- What has to be defined before the test (to settle with Madhav, not guessed): what "clearly moves" means (points or % from entry, or a level break), the stop on the combined premium, and the trail on the winner.
- It is the mirror of O-03 (long gamma at the end of expiry vs short premium the night before), so the two are tested on the same expiries and compared side by side.

## Expiry calendar note
Weekly expiry weekdays and lot sizes have changed several times (SEBI's 2024 rules left one weekly index expiry per exchange; Bank Nifty weeklies ended in Nov 2024). The tests use the actual expiry dates found in the F&O bhavcopy for each year, never an assumed weekday.
