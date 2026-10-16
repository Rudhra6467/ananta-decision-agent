<!-- Trading Knowledge Library · Optionables (Optionables, India). Built 2026-10-16 from 434 public videos with captions (of 459 on the channel; members-only videos were not used): one structured note per video (Claude Sonnet 5.5) -> this chapter (Claude Opus 5.5), src/research/library.py. Paraphrased; the transcripts stay on the laptop. Evidence class: external teaching = hypotheses to test, never Ananta rules; nothing in the agent reads docs/library/. -->

# Option basics

## 1. What he teaches here and how it fits

Optionables does not teach option basics as one structured course. The basics come up as he goes, inside videos on cost breakdowns, payoff spreadsheets, order entry and new venues. The core he returns to is short:

- An option is like an insurance contract.
- Premium is priced by the probability of finishing in the money.
- Premium splits into intrinsic value and time value.
- Strikes of the same expiry must be priced in order.
- Contract size is lot size times price.
- Costs on Indian options are charged on premium turnover.

These basics serve his main activity. Across this set of notes, that activity looks like selling index options. Examples include a 5,000-quantity Bank Nifty short straddle [TcH5IWySLJw], selling far out-of-the-money crypto options [JPqXyHXfGfg], and daily intraday option selling on Delta Exchange [3MMjcR_ortI]. That focus explains why he spends so much time on liquidity, freeze quantities, lot sizes and the exact fee stack, and very little on the long-call side. Everything below is his claim or method, to be treated as a hypothesis.

## 2. The ideas

### 2.1 What an option is: the insurance model

- **What it is.** He frames an option as insurance with three parts [3pPlHdsHBb4]:
  - The buyer pays an upfront premium.
  - The seller pays out if the insured event happens before expiry. For a call, the event is the index rising above the strike.
  - If the event does not happen, the seller keeps the whole premium with no refund.
- **Same mechanics on any underlying.** He says the contract works the same on any underlying: Nifty and Bank Nifty indices, USD-INR, gold, silver, crude, Bitcoin or Ethereum. He uses this to argue that index-option skills carry over to crypto options [uN9SRyTv_yY].
- **Why options matter.** He points to leverage and the flexibility to manage positions. He says institutions use options mainly to hedge large portfolios, not to collect small premiums. He adds that hedging flows can influence the index indirectly, though stocks generally drive it. This is low clarity in the captions [d6ZOFGDVw2Y].
- **Clarity and frequency.** The insurance framing is clear, but the notes show it in only one video. It is not codable as a rule.

### 2.2 Calls, puts and break-even

**Long call.** If held to expiry, a long call profits only above strike plus premium [UdsdCODKv58]. His example:

| Item | Value |
|---|---|
| Bank Nifty spot | 35,000 |
| Call bought | 36,000 strike for 200 |
| Break-even | 36,200 |

His point is that even a 1,199-point rally still ends as a loss. He uses this to show how hard it is for out-of-the-money call buyers to win.

**Short call.** This is the mirror image. Under the insurance model, the seller keeps the full premium if the index stays below the strike [3pPlHdsHBb4]. No separate worked short-call example appears in the notes.

**Puts.** Puts appear only as legs in his payoff spreadsheet [myBFImpycfo]:
- The sheet has 6 call slots and 6 put slots.
- Each leg takes strike, buy or sell, premium and lots.
- The sheet rejects put data typed into a call slot, and the reverse.

There is no worked put break-even or put payoff example in these notes.

**Clarity and frequency.** The call break-even is clear and codable but comes from a single video.

### 2.3 Premium: intrinsic value and time value

**Decomposition.** Premium equals intrinsic value plus time value [0eEhp4WO66U]. His example, with Nifty near 17,285:

| Call | Premium | Intrinsic | Time value |
|---|---|---|---|
| 16,800 (in the money) | 495 | about 485 | about 10 |
| 17,700 (out of the money) | 10 | 0 | 10 |

He concludes that both options lose the same rupee amount to theta. This is clear and codable.

His conclusion assumes the two time values decay along the same path. Equal time value today does not by itself guarantee equal decay per day. Treat it as a hypothesis.

**Premium follows probability.** A strike nearer the money costs more than a far out-of-the-money strike because it is more likely to finish in the money. He compares this to health insurance costing more for older people [3pPlHdsHBb4].

**No-arbitrage ordering.** For calls of the same expiry, the lower strike must trade at or above the higher strike. His example of an impossible state is the 16,450 call priced above the 16,400 call. He says arbitrage firms remove such states instantly [vx8x_O7-01g]. This is clear and codable.

**Probability from adjacent strikes.** He uses a 100-point strike gap so that the price difference between adjacent in-the-money and at-the-money options reads directly as a percentage probability. Probability runs from 0 to 100, and the gap is 100 points. He says this is why he does not use 20- or 50-point gaps [P-hGtRW78rw].

The logic underneath is that the largest possible difference between adjacent strikes equals the gap. With any gap g, you would divide the price difference by g. Clarity is medium and the method is only partly codable.

### 2.4 Moneyness and strike spacing

- **Strike intervals he cites** [myBFImpycfo]:

  | Underlying | Interval |
  |---|---|
  | Nifty | 50 points |
  | Bank Nifty | 100 points |
  | ITC | 2.5 rupees |

- **How the sheet uses them.** His payoff sheet takes spot and interval, then generates a ladder of strikes [myBFImpycfo].
- **A tension in the notes.** He uses Nifty's 50-point listing in one video but argues for a 100-point gap in the probability method [P-hGtRW78rw]. These are probably compatible: one is the exchange listing, the other a choice of strikes for the calculation. The notes do not reconcile them.
- **What is missing.** In-the-money, at-the-money and out-of-the-money are used throughout but never formally defined in these notes.

### 2.5 Expiry and settlement

**Nifty expiry ladder** [tTR4X1FsFgE]:
- 7 weekly expiries, then 3 monthly, then quarterly and half-yearly contracts, out to June 2026.
- Liquidity is thin beyond about 5 months.
- Far-dated volume sits in quarter-end months (September and December), at strikes around 15,500–16,500, with Nifty then near 15,700–16,000.
- An example spread: 4–5 rupees on a December 16,000 call.
- Few brokers enable long-dated contracts, so you may have to ask for access.

**BSE.** Weekly futures and options on the S&P BSE Sensex 50 were launched. The captions suggest Thursday expiry, but this is unclear [pTS4LS3Czos].

**Delta Exchange (crypto).**
- One video says daily expiry at 5 pm, with 10–20x leverage that makes far out-of-the-money selling possible. His team had only just started trying it [JPqXyHXfGfg].
- Another says daily expiry at 5:30 pm, about 365 expiries a year, settled on the weighted average price of the last 30 minutes [3MMjcR_ortI].
- These two times conflict. See section 5.

**Settlement of Indian index and stock options.** This is not described anywhere in these notes.

### 2.6 Lot sizes, contract value, open interest and order limits

**Contract value** is index level times lot size [0qmiy0rYOfE]. His example: lot of 75 × index at 12,000 ≈ 9 lakh.

**Lot size change.** The Nifty lot was moving from 75 to 50 from July 1, which lowers margin per lot [BFZXz79936Y]. Lot sizes are dated and change over time.

**Open interest.** Open interest is shown in quantity units. Divide by lot size to get lots [BFZXz79936Y]:
- 36 lakh ÷ 75 = 48,000 lots.
- That means 48,000 lots bought and the same number sold.

**Freeze quantities.** The exchange caps the quantity allowed in a single order:

| Index | Freeze quantity | How he handles it |
|---|---|---|
| Bank Nifty | 1,250 | Basket orders repeat the same leg; example is a 5,000-quantity short straddle built from 1,000-quantity legs [TcH5IWySLJw] |
| Nifty | about 1,800 | His broker auto-slices 5,000 into 1,800 + 1,800 + 1,400 [cVxwgVbHYKY] |

**Delta Exchange contract specs** [uN9SRyTv_yY]:
- 1 BTC option lot = 0.001 BTC, so a quantity of 500 = 0.5 BTC.
- Fees are about 0.02% for futures-style orders and 0.05% for options.
- Margin was about 784 USD per short leg in his example.
- Funds are deposited in USDT.

### 2.7 Trading costs (India)

All of the following is from [LsyNOm0vDec] and is dated. Clarity is high except where noted.

**The cost stack.** Brokerage, STT, exchange transaction charge plus clearing charge, GST, SEBI fee and stamp duty. Some are fixed by government or exchange; others can be reduced.

**Turnover basis.** Turnover is premium × quantity, on both the buy and sell side, not notional value. Every extra trade in the same contract adds charges again.

**Each charge:**

| Charge | Basis and rate as quoted | His example or note |
|---|---|---|
| Brokerage | Flat fee per order or per lot | 20 rupees per order (6 orders = 120); or 1 rupee per lot (12 lots = 12) |
| STT | 0.05% of sell-side premium only; fixed, so no markup possible | Sell premium ≈ 1.75 lakh gave ≈ 87 rupees |
| Exchange transaction charge | 0.053% of premium turnover, about 5,300 rupees per crore, for a self-clearing member | Medium clarity |
| Clearing add-on | Non-clearing brokers may add about 700–3,000 rupees per crore | One broker charged 0.0545%, about 100 rupees extra on his example |
| GST | 18% on brokerage plus exchange and clearing charges only | Not charged on turnover |
| SEBI fee | About 10 rupees per crore | Caption figure garbled |
| Stamp duty | About 300 rupees per crore, buy side | — |

**His claim about hidden charges.** The exchange and clearing line is where non-clearing brokers quietly earn extra. He says this markup is negotiable, and that "free brokerage" offers often recover money this way.

**Expiry days.** Expiry days carry more transactions, so he assumes higher brokerage: about 12,500 versus 7,000 on a normal day. The notes do not say what time period or position size these figures cover [NTavZ18KPh8].

### 2.8 P&L versus M2M

He distinguishes two profit views [-mr_hT8olBE]:
- **P&L** is measured from your entry price.
- **M2M** (mark-to-market) is measured from the previous day's close.

His demo used Nifty futures entered at about 17,656 with a prior close of about 17,623. It showed about 1.6 lakh M2M against about 1.93 lakh P&L.

These figures are consistent with a short position of roughly 1,000 units held from an earlier day. That is my inference; the notes do not say it.

### 2.9 Liquidity and execution

- **Index over stock options.** He prefers liquid index options because thin stock options can leave you stuck. This is low clarity, from a viewer Q&A [QEj_68mxDHI].
- **Market protection.** The broker's "market protection" setting limits how far from the quote an order can fill. Only the feature's existence is clear, not his explanation [Q_BhDmUE22M].
- **Far-dated contracts.** See the liquidity points in section 2.5 [tTR4X1FsFgE].

### 2.10 Related non-option basics appearing in the same notes

- **Index ETFs.** You cannot buy Nifty directly; you buy ETFs that track it [NJbO4bl6sLQ]:
  - Nippon Nifty BeES (most liquid), Kotak, ICICI, HDFC, at about 165–170 rupees per unit.
  - Also mid-cap, sector, Nifty 100 and India-listed Nasdaq 100 ETFs. Names are partly garbled in the captions.
- **Market-cap bands** (his rough figures) [TGlIz26DNMQ]:
  - Large cap above about 50,000 crore.
  - Mid cap about 10,000–50,000 crore.
  - Small cap below about 10,000 crore.
- **Short selling through SLB** [QhERbElbSOM]. Borrow the share for a fixed period (7 days in his example), sell, buy back and return. Selling at 1,400 and covering at 1,200 gains 200 per share.

## 3. How a program would test it

1. **Strike monotonicity (no-arbitrage)** [vx8x_O7-01g].
   - Statement: for every same-expiry call pair with K1 < K2, the K1 call is priced at or above the K2 call. For puts, the higher strike is priced at or above the lower.
   - Measure: count violations using bid/ask, not last trade, and how long each lasts.
   - Data: NSE option tick or 1-minute quote data for Nifty and Bank Nifty.

2. **Premium ordered by distance from the money** [3pPlHdsHBb4].
   - Statement: at a fixed timestamp and expiry, out-of-the-money premium falls monotonically as distance from spot grows, for calls and puts separately.
   - Data: the same quote data plus spot or futures prices.

3. **Adjacent-strike price difference as a probability** [P-hGtRW78rw].
   - Statement: (C(K−g) − C(K)) / g at a given time predicts the frequency of expiry above K.
   - Measure: bin the predictions and compare to realized expiry outcomes (a calibration plot and Brier score), for g = 50 and g = 100.
   - Data: end-of-day option chains plus expiry settlement prices over several years.

4. **Equal time value decays equally** [0eEhp4WO66U].
   - Statement: two strikes of the same expiry with equal time value at time t lose the same rupee time value by any later time t+k.
   - Measure: compare deep in-the-money and far out-of-the-money pairs. Measure the gap in time-value decay and its dependence on spot moves and implied volatility changes.
   - Data: intraday option and spot prices.

5. **Long out-of-the-money calls rarely clear break-even** [UdsdCODKv58].
   - Statement: for calls bought at fixed out-of-the-money distances (for example, 1%, 2% or 3% from spot) and held to expiry, compute the share where settlement exceeds strike plus premium, and the mean P&L.
   - Data: historical chains and settlement prices.

6. **Cost model reproduces actual charges** [LsyNOm0vDec, NTavZ18KPh8].
   - Statement: his fee stack applied to trade logs reproduces broker contract-note totals within a small tolerance.
   - Second check: expiry days have more orders per position than other days.
   - Data: contract notes and the order log, with rates aligned to the date of each trade.

7. **Liquidity: stock versus index options, and far expiries** [QEj_68mxDHI, tTR4X1FsFgE].
   - Statement: the relative bid-ask spread (spread ÷ mid) is materially wider for single-stock options than for index options at comparable moneyness.
   - Statement: Nifty spreads widen sharply beyond about 5 months to expiry.
   - Data: quote snapshots across underlyings and expiries.

## 4. Transfer to TSX and US markets

**Applies as it is.** These hold anywhere options trade:
- The insurance framing, intrinsic and time value, and break-even arithmetic.
- No-arbitrage strike ordering and premium ordering by moneyness.
- The adjacent-strike probability idea, scaled by the local strike gap.
- P&L versus M2M.
- The payoff-ladder design.
- The preference for liquid index products over thin single names.

[uN9SRyTv_yY, 0eEhp4WO66U, UdsdCODKv58, vx8x_O7-01g, 3pPlHdsHBb4, -mr_hT8olBE, myBFImpycfo]

**Needs adapting.** The following are my notes, not his:
- **Underlyings.** The Nifty and Bank Nifty equivalents would be SPX, SPY or QQQ in the US, and the S&P/TSX 60 or XIU in Canada.
- **Contract size.** North American equity options typically use a 100-share multiplier rather than Indian lot sizes, and strike gaps differ by product.
- **Expiry structure.** Weeklies, monthlies and LEAPS replace the Nifty ladder.
- **Exercise and settlement style.** These differ by product, which he does not cover.
- **Costs.** US and Canadian costs are per-contract commissions plus exchange and regulatory fees. There is no STT, GST-on-brokerage or Indian stamp duty. His point that hidden fees sit in non-transparent lines is worth re-checking against local fee schedules.
- **Other items.** The ETF and market-cap material and SLB-based shorting also need local equivalents.

**India-only.**
- The Indian charge stack and its rates [LsyNOm0vDec].
- NSE freeze quantities and auto-slicing [TcH5IWySLJw, cVxwgVbHYKY].
- BSE Sensex 50 weeklies [pTS4LS3Czos].
- Specific Nifty lot sizes [0qmiy0rYOfE, BFZXz79936Y].
- Broker availability of far-dated contracts and market protection [tTR4X1FsFgE, Q_BhDmUE22M].

Delta Exchange specifics are venue-specific, not India-specific, and regulatory access differs by country [uN9SRyTv_yY, JPqXyHXfGfg, 3MMjcR_ortI].

## 5. Gaps and doubts

**Thin coverage.**
- **Puts** are barely covered: no put payoff or break-even example, and no put-call relationship.
- **Missing topics:**
  - formal definitions of in-the-money, at-the-money and out-of-the-money;
  - American versus European exercise;
  - cash versus physical settlement of Indian index and stock options;
  - exercise and assignment;
  - implied volatility;
  - option margin in India (only a Delta example exists).
- **Single-video support.** Most basics are taught clearly but each rests on one video.

**Contradictions.**
- **Delta expiry time:** 5 pm [JPqXyHXfGfg] versus 5:30 pm [3MMjcR_ortI].
- **Strike gap:** a 100-point gap is argued for in the probability method [P-hGtRW78rw], while 50-point Nifty strikes are used elsewhere [myBFImpycfo]. Probably not a real conflict, but not explained.

**Unclear captions.**
- The BSE Thursday expiry [pTS4LS3Czos].
- The SEBI fee figure [LsyNOm0vDec].
- The market protection explanation [Q_BhDmUE22M].
- The ETF names [NJbO4bl6sLQ].
- The stock-versus-index option remark [QEj_68mxDHI].

**Unverified claims.**
- **Equal theta decay** for equal time value is asserted, not demonstrated [0eEhp4WO66U].
- **Instant removal of arbitrage** is asserted [vx8x_O7-01g].
- **Hidden-charge broker markups** are his claim [LsyNOm0vDec].

**Dated figures.** Lot sizes, freeze quantities, fee rates and the expiry ladder are all from 4–6 years ago and must be refreshed before any use [0qmiy0rYOfE, BFZXz79936Y, TcH5IWySLJw, cVxwgVbHYKY, LsyNOm0vDec, tTR4X1FsFgE].

**Missing context.** The expiry-day brokerage figures (12,500 versus 7,000) come with no stated position size or period [NTavZ18KPh8].
