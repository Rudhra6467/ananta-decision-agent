<!-- Trading Knowledge Library · Optionables (Optionables, India). Built 2026-10-16 from 434 public videos with captions (of 459 on the channel; members-only videos were not used): one structured note per video (Claude Sonnet 5.5) -> this chapter (Claude Opus 5.5), src/research/library.py. Paraphrased; the transcripts stay on the laptop. Evidence class: external teaching = hypotheses to test, never Ananta rules; nothing in the agent reads docs/library/. -->

# Buying strategies

## 1. What he teaches here and how it fits

Optionables describes himself as an option seller. In his account, outright buying is something he does rarely and treats as the exception. He calls one large winning buy "luck" and says he will not adopt buying as a habit [QgqjwKIZjlM, nMlFJigaxnM, IMjqrkYosgY]. He tells his own story of starting as a buyer and losing about half his capital, much of it to revenge trading [NMxUve9X2hY].

His teaching on buying is therefore mostly about when buying fails and how to reduce the damage when you do buy. The main points are:

- **Probability.** He puts the buyer's chance of profit at roughly one in three.
- **Theta.** Decay can make a correct directional view lose money.
- **Regime.** Buy only in trends. Never buy in ranges, after a VIX spike, or through an event.
- **Strike choice.** Match the strike to the expected size of the move. ITM is the default and OTM is only for very large moves.
- **Structure.** Prefer debit spreads over naked buys, especially at confirmed breakouts.

His older videos (about 5 years ago) are the most strongly anti-buying. The later ones (about 2 years ago) present call and put debit spreads as a normal directional tool at breakouts. Everything below is his claim or method, to be treated as a hypothesis.

## 2. The ideas

### 2.1 Why naked buyers usually lose (the core claim)

**Probability claim.**
- He says a naked option buyer, OTM in particular, has about a 33% chance of profit and the seller about 67% [UdsdCODKv58, BB8KiSmE0ak, 0eEhp4WO66U].
- In [UdsdCODKv58] he derives this by treating up, flat and down as equally likely. He admits this is a simplification for beginners.
- In [0eEhp4WO66U] he ties it to an empirical-sounding claim: the market is range-bound about two-thirds of the time, so the buyer's odds are about 33–35%.
- For far OTM strikes he gives looser figures of about 10–30%, falling toward 5% the farther out the strike. He offers this as a spoken estimate, not a calculation [UdsdCODKv58].

**Right direction, still a loss.** Theta erodes an OTM option faster than a modest favourable move adds value. He gives several examples:
- A worked example where the underlying ends well above entry but the OTM call expires worthless [0eEhp4WO66U].
- Bank Nifty up about 1.1% (about 400 points) in a session, while the 36,000, 35,900 and 35,800 calls each lost roughly ₹21–27 [UdsdCODKv58].
- A day of a hard index rally on which calls barely gained [IMjqrkYosgY].
- A 35,500 CE that needs about 35,950 or higher at expiry to break even, which he puts at about 32% probability [BB8KiSmE0ak].

**Who takes which side.** Buyers chase cheap OTM options hoping for a 10x return. Sellers are glad to sell those same options and avoid selling ITM, so OTM buyers end up taking the side sellers want [0eEhp4WO66U].

**Clarity.** High, and repeated across at least four videos, all from 4–5 years ago.

### 2.2 Regime filters: when not to buy at all

**Ranges.**
- If you expect a range-bound market, do not buy any strike [l4jQUXK6UOc].
- Buy only when a trend is present; consolidation suits short straddles instead [0eEhp4WO66U].
- He leaves the choice of trend definition (price action or indicators) to the trader [0eEhp4WO66U].
- Be selective and do not buy every day [0eEhp4WO66U].

**After a VIX spike.**
- Do not buy calls or puts, especially far OTM, once VIX has spiked. Premiums already price in the recent moves and collapse if the market calms [PiY8pG6Jox4].
- His example: India VIX about 32, up about 30% in a day. A Bank Nifty 32,000 put about 10% OTM cost about ₹200, which he judged too expensive for a one-week horizon.

**Through scheduled events.**
- Do not hold a long straddle into an event. Unless the gap exceeds about 1–1.5%, the IV crush produces a loss even if the underlying moves several hundred points [urrT8zpnGus].
- On a budget day, long straddles and strangles lost at all strikes because premiums decayed while the market barely moved [bLFCt52D89o].

**Clarity.** High on ranges and events. The VIX rule is taught once.

### 2.3 Strike selection by expected move (long and short)

This is his most detailed buying topic. It is also the one where his videos disagree.

**Default: ITM, especially deep ITM.**
- When bullish but unsure of the size of the move, buy a deep ITM call so that even a 5–10 point move pays [0eEhp4WO66U]. His example: the 16,800 call with Nifty at about 17,285, against the 17,300 ATM and 17,700 OTM.
- For a mild view (about 50–100 Nifty points), buy ITM and avoid ATM and OTM, because ITM does best on small moves and loses least on adverse moves [l4jQUXK6UOc].
- First fix how much you can lose, then buy deep ITM to reduce decay risk [d6ZOFGDVw2Y].
- ITM may cost slightly more in transaction charges but "gives more room" [QEj_68mxDHI] (low clarity).
- If you must buy and are sure of the trend, buy ATM, preferably ITM, never OTM [UdsdCODKv58].

**His equal-capital payoff table** [0eEhp4WO66U]. Capital is ₹25,000 per trade: ITM 1 lot, ATM 5 lots, OTM 50 lots.

| Nifty at expiry | ITM result | ATM result | OTM result |
|---|---|---|---|
| ~17,300–17,350 | profit | loses most or all | loses most or all |
| 17,400 | about +5,000 | about +1,700 | (not stated) |
| 17,500 | about +10,000 | about +26,000 | (not stated) |
| 17,700 | about +20,000 | about +70,000 | still a loss |

- On the Sensibull analyser at equal risk, probability of profit is about 50% for ITM, 35% for ATM and 8% for far OTM [0eEhp4WO66U].
- The implied crossover, where ATM starts to beat ITM, is around +200 points.

**OTM: only for very large expected moves.**
- Buy OTM only for a very large expected move, about 700 Nifty points, and only if you are willing to be aggressive. Gamma can turn a ₹20–30 premium into ₹200–300. Not for 100–200 point moves [l4jQUXK6UOc].
- If you are very bullish but want to play defensively, buy ITM instead, which still pays if the move comes in at, say, 200 points rather than 700 [l4jQUXK6UOc].
- For an expected move of about 2%, buy an OTM call or sell an OTM put [dPrLYK6otIo].

**Short side (puts).** For an expected sharp fall with rising IV (his example is about a 1% gap down), an OTM put can beat ATM and ITM puts. Positive vega adds to the gain, the reverse of the vega drag on up-moves [dPrLYK6otIo].

**Greek-approximation tables** [dPrLYK6otIo]. These use delta, vega and theta with IV down 1 point and one day of theta.

- **About a 1% move (175 points, Nifty 17,862):**
  - ATM calls gain most in percentage terms.
  - The ITM 17,700 call goes from about 217 to about 313, roughly +44%.
  - OTM calls keep pace with ITM and ATM calls.
  - Among puts, ITM puts lose least.
- **About a 0.5% move (90 points):**
  - ITM options far outperform OTM.
  - ITM strangle about −17%, ATM straddle about −27%, OTM strangle about −55%.
  - His conclusion: the best strike depends on how big the move turns out to be.

**Contradictions to note.**
- **ATM.** [l4jQUXK6UOc] says always avoid buying ATM because it has the highest theta, and that ATM favours sellers in every scenario. [UdsdCODKv58] accepts ATM. [dPrLYK6otIo] shows ATM gaining most on a 1% move.
- **Mild moves.** For mild movement of 0.5–0.7%, [dPrLYK6otIo] is noted as recommending ATM or OTM and avoiding ITM. That conflicts with its own 0.5% table and with [l4jQUXK6UOc] and [0eEhp4WO66U]. It may be a caption or note error, so treat it as unresolved.

**Summary heuristic** [l4jQUXK6UOc]: ITM favours buyers, ATM favours sellers, and OTM can suit either side depending on the situation. Sellers should avoid strikes that buyers favour.

**Clarity and frequency.** High and frequent (about six videos) for the ITM preference. Medium for the move-size thresholds, which are given in Nifty points tied to the index level at the time.

### 2.4 Checking implied probability before buying OTM

He uses a "neighbor-price" method: compare adjacent strikes to read the market-implied chance of finishing ITM [P-hGtRW78rw].
- **Example:** Nifty 18,000 call at about ₹3 and 17,900 call at about ₹4.5.
- **His reading:** about 1% probability of finishing ITM by the 9 December expiry.
- The premium difference divided by the strike gap gives about 1.5%, so his "about 1%" is a rough reading. He does not explain the formula further.
- He gives no threshold below which to refuse a trade.

Taught once.

### 2.5 Holding period and structure: naked vs spread vs long-dated

His choice depends on how long the trade will be held [BB8KiSmE0ak]:

| Trader type | Holding period | His preferred structure | His reason |
|---|---|---|---|
| Scalper | about 3 minutes | naked option | on violent moves IV rises, so premium builds faster than it decays |
| Intraday | about 4–5 hours | bull call spread | less theta impact; can profit if flat or slightly up |
| Positional | overnight to 3–4 days | bull call spread | theta hurts naked ATM/OTM most over longer holds |

**Long-dated options** [tTR4X1FsFgE]:
- For longer-term views, buy long-dated options: little daily decay and the most benefit from rising IV.
- His example: a 16,000 Nifty call at about ₹500 with about 5 months to expiry, which could reach ₹600–700 if Nifty moves above 16,000.
- Taught once; medium clarity.

**Trade management** [d6ZOFGDVw2Y]: buyers should let winners run, while sellers cut losses quickly.

### 2.6 Debit spreads at breakouts (the later, preferred buying structure)

**Long side.**
- On an upside breakout he prefers a call debit spread [F0x5faXXRTI]. His reasons:
  - target reward-to-risk of about 1:2 to 1:3;
  - small capital and small risk;
  - the trade can be adjusted and managed if the breakout fails.
- He does not specify what that adjustment is.
- Bank Nifty example: on a break above 43,900, go bullish with a call debit spread or short puts rather than fight the move [xFZsJsVyU8s].

**Either side.** Once a directional breakout is confirmed, use credit or debit spreads [DnJHEujUHb4]. For those who dislike spreads, use broken-wing butterflies, described as one side fully kept and the other carrying a loss. The note does not make the construction clear.

**Short side.** Put debit spreads are implied by symmetry. The only concrete bearish spread is a bear put spread combined with an outright Nifty ITM put, which he calls a rare outright purchase [nMlFJigaxnM].

**Credit spreads.** These are always offered as an equal alternative [F0x5faXXRTI, DnJHEujUHb4, xFZsJsVyU8s].

**Earlier stance.** [BB8KiSmE0ak] already says spreads are sometimes better than naked buying because of the 33% problem.

**Clarity.** Medium. The structure is clear, but strikes, width, DTE and exits are not given.

### 2.7 Entry locations he pairs with buying (long side)

**Tested support** [pMVDiDH8v08]:
- Buy near well-tested Nifty support at about 18,100–18,120, with a stop at 18,050.
- Risk is 60–70 points against a reward of 180–240 points, so reward-to-risk is about 1:3 to 1:4.
- He says he bought "OTM" 17,800 calls in his own account. With spot at about 18,100, a 17,800 call would be ITM, so either the strike or the label is a caption error.

**Pullbacks to prior breakout or retest zones** [K6Fnb-G4Fl0]: if you missed the breakout, buy dips at prior breakout or retest zones rather than every dip. No instrument is specified.

**Stock breakout** [xzkqo36gp8c]: ICICI Bank ranged 850–890. A close above 890, with Bank Nifty positive, is a long breakout; he preferred it over HDFC and Kotak as relatively stronger. This is a directional idea, and no option structure is stated.

### 2.8 Short-side outright buys (the exceptions)

**Loss-recovery far OTM put** [QgqjwKIZjlM]:

| Element | Detail |
|---|---|
| Position | 8,000 qty of the Nifty 16,750 put at ₹15–16 |
| View | Nifty would revisit the prior day's low near 16,700 |
| Maximum risk | about ₹1.2 lakh (the premium paid) |
| Exit | ₹65–70 (the high was about ₹95–99), roughly +50 points, about ₹4 lakh |

- **Why he bought instead of sold:** recovering ₹4 lakh by selling needed about 10,000 qty of ATM at about ₹40, which was too much risk. Alternatively, 5,000 qty ITM at ₹80 has delta near 1. Buying capped the loss at the premium, accepting a low chance of being right.
- **He disowns it as a method:** it was luck, there is no way to adjust a bought option, and a full loss would have left him about ₹5.2 lakh down for the day.

**Bear put spread plus ITM put** [nMlFJigaxnM]: see 2.6.

### 2.9 Event IV run-up trade (long straddle, either direction)

This is his one buy-volatility setup, taught clearly in [urrT8zpnGus]:
- **Instrument:** buy the ATM call and ATM put (straddle or strangle) on the day before a major event.
- **Entry:** shortly before the close, at 2:40 pm. The earlier plan was 2:55 pm.
- **Size:** 30 lots, about 1,000 qty.
- **Combined target and stop:** ₹15,000 each.
- **Exit:** by 3:15 pm at the latest.
- **Result:** it hit target in under 20 minutes.
- **Limit:** do not hold through the event itself (see 2.2).

He gives a single instance only.

## 3. How a program would test it

**1. Moneyness vs realized move.**
- **Test:** for daily or weekly Nifty and Bank Nifty options, compute the percentage return of ITM (about 1–2 strikes in), ATM and OTM calls and puts over 1 day and to expiry. Bucket the results by realized underlying move (e.g. <0.5%, 0.5–1%, 1–2%, >2%) and by IV change.
- **Claims tested:** ITM wins for moves below about +200 Nifty points or 1%. OTM wins only above about 1.5–2%, or for puts on gap-downs with rising IV.
- **Data:** historical EOD and intraday option chains (NSE bhavcopy plus intraday vendor), underlying OHLC, India VIX.

**2. Buyer win rate by strike distance.**
- **Test:** across all weekly expiries, measure the share of calls and puts at each delta or distance bucket that finish above break-even (strike plus premium).
- **Claims tested:** about 33% overall, 5–30% far OTM, and ITM about 50% vs ATM about 35% vs far OTM about 8%.
- **Data:** expiry settlement prices plus entry premiums at fixed times (e.g. T−5, T−1).

**3. Range-bound share and trend filter.**
- **Range share:** check that about two-thirds of daily Nifty moves fall within ±1%.
- **Trend filter:** compare expectancy of naked buys taken when a defined trend filter is on (e.g. 20/50-day MA alignment or ADX>25) against buys taken in consolidation (e.g. a narrow 10-day range).
- **Data:** index daily bars plus the option chain.

**4. VIX-spike rule.**
- **Test:** when India VIX rises more than about 25% in a day to above about 30, measure the return of buying far OTM (about 10%) weekly Bank Nifty options held 4–5 sessions, against unconditional buys.
- **Data:** VIX daily plus the option chain.
- **Caveat:** the sample of such events is small.

**5. Event straddle.**
- **Test A (run-up):** buy the ATM straddle at 14:40 on the day before scheduled events (budget, RBI policy, election results) and exit at 15:15 or at ±₹15,000 combined, net of costs. The claim is positive expectancy.
- **Test B (hold-through):** hold the same straddle through to the next open. The claim is a loss unless the gap exceeds 1–1.5%.
- **Data:** minute-level option prices plus an event calendar.

**6. Debit spread at breakouts.**
- **Test:** on a close above an N-day range high, buy an ATM/OTM call debit spread (fixed width, fixed DTE). Measure average reward-to-risk and expectancy over a fixed hold. Run the mirror test for puts on range lows.
- **Benchmarks:** the naked ATM call and the short put on the same signal.
- **Claim tested:** realized reward-to-risk of 2 or more.
- **Data:** daily bars plus the option chain.

**7. Holding period vs structure.**
- **Test:** on identical intraday bullish signals, compare naked ATM calls against bull call spreads at 3-minute, 4–5 hour and 1–4 day holds.
- **Claim tested:** naked wins only at the scalp horizon.
- **Data:** tick or minute option data.

**8. Implied-probability filter.**
- **Test:** using the butterfly/digital approximation (ΔC/ΔK), check whether OTM buys with implied probability below about 5% have negative EV net of costs, and whether realized ITM frequency matches the implied probability.

## 4. Transfer

**Applies to US and TSX as is:**
- The logic of theta vs move size.
- Payoff and break-even reasoning.
- ITM/ATM/OTM trade-offs framed in percentage or delta terms.
- Avoiding long premium after IV spikes.
- IV crush through events.
- Debit spreads as defined-risk directional tools.
- Matching structure to holding period.

**US markets:**
- **Direct analogues.** SPX, SPY and QQQ have daily expiries and deep liquidity, so the intraday, scalp and event-run-up tests port directly.
- **Events.** FOMC, CPI and earnings replace the budget and RBI.
- **Volatility gauge.** VIX replaces India VIX. Re-derive the spike thresholds; VIX 30 means something different in US history.

**TSX / Canada:**
- Index options (SXO on the TSX 60) and XIU options are thin and wide. Weekly expiries exist mainly on large single names and ETFs.
- Intraday scalping, the event straddle and the 30-lot sizing are unlikely to be practical.
- Debit spreads on liquid single stocks or ETFs with monthly expiries are the feasible adaptation.
- Use the VIX or VIXC (S&P/TSX 60 VIX) cautiously.

**Needs adapting everywhere:**
- All point thresholds (50–100, 200 and 700 Nifty points; 60–70 point stops) should become % or ATR or delta terms.
- Lot sizes, ₹ targets and stops should become risk as a % of account.
- Costs differ: Indian STT and exchange charges vs US per-contract commissions and wider spreads.
- Time-of-day rules (14:40–15:15) need mapping to each market's close.
- Indian weekly-expiry rules have changed since these videos, so even the Indian tests must use the contract specs current at each date.

**India-only:**
- The Union Budget-day observations.
- Specific Nifty and Bank Nifty levels.
- Sensibull analyser outputs.
- Lakh-denominated recovery trade sizing.

## 5. Gaps and doubts

**Numbers that are not derived.**
- The 33% buyer probability is an admitted beginner's simplification (three equally likely outcomes) [UdsdCODKv58].
- The 5–30% far OTM figures are loose spoken estimates.
- The two-thirds range-bound claim is not supported with data in the notes.

**Internal contradictions on ATM.**
- "Always avoid ATM" [l4jQUXK6UOc] vs "ATM, preferably ITM" [UdsdCODKv58] vs ATM best on a 1% move [dPrLYK6otIo].
- The [dPrLYK6otIo] advice to avoid ITM on mild moves contradicts its own table and two other videos. This may be a captioning or notes error.

**Practice vs rules.** He says he rarely buys naked, yet he bought "OTM" 17,800 calls at support [pMVDiDH8v08]. That strike looks ITM, so it is probably a caption error. He also made a large far OTM put recovery trade, which he calls luck.

**Debit spreads underspecified.** The notes give no strike placement, width, DTE, profit-taking or stop rules, and no description of how a failed breakout is "adjusted." The broken-wing butterfly description is unclear.

**Little on the short side.** Puts are mostly by symmetry. The only specific bearish content is the recovery trade, the bear put spread with an ITM put, and the OTM-put-with-rising-IV argument.

**Exits for naked buys.** Apart from "let winners run" and premium-as-max-loss, there are no stop or target rules for naked buys.

**Single-instance evidence.** The event straddle run-up, the VIX-spike rule, long-dated calls and the implied-probability method are each taught once. Several examples are one-day anecdotes.

**Change over time.** The 5-year-old videos are broadly anti-buying with an ITM default. The 2-year-old videos treat debit spreads as routine at breakouts. Whether his view on naked ITM buying itself changed is not visible in these notes.

**Not covered:**
- Position sizing for buyers beyond defining the loss first.
- IV percentile or rank thresholds for when buying is cheap.
- Calendar or diagonal debit structures.
- Rolling.
- Any backtest or track record of his buying trades.
