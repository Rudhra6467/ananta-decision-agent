<!-- Trading Knowledge Library · Optionables (Optionables, India). Built 2026-10-16 from 434 public videos with captions (of 459 on the channel; members-only videos were not used): one structured note per video (Claude Sonnet 5.5) -> this chapter (Claude Opus 5.5), src/research/library.py. Paraphrased; the transcripts stay on the laptop. Evidence class: external teaching = hypotheses to test, never Ananta rules; nothing in the agent reads docs/library/. -->

# Hedging

## 1. What he teaches here and how it fits his method

Most of Optionables' hedging material is not about protecting a stock portfolio. It is about putting long "wings" (far out-of-the-money bought options) on his short straddles and strangles in Indian index options (Nifty, Bank Nifty) and later crypto. He gives three reasons for the wings:

- to cap loss from gaps and black-swan moves,
- to hold positions overnight safely,
- very often, mainly to cut exchange margin.

A smaller body of material covers hedging a long equity book with short Nifty futures, and hedging directional futures trades with a bought option. His position changes over time:

- **About 5–6 years ago:** wings were standard on overnight shorts and often bought for margin.
- **About 4 years ago:** he argued that buying weekly wings on a straddle loses money over time, backed by his own backtest. He said he prefers naked positions with small size.
- **About 2 years ago:** he said to hedge every short option and to prefer defined-risk structures.

Everything below is his claim or method. Treat each point as a hypothesis to test, not an established result.

## 2. The ideas

### 2.1 Wings on short straddles and strangles (iron fly / iron condor)

**What it is.** Each short option is paired with a bought option further out of the money on the same side. This caps the loss on that side at:

- strike distance minus net premium [BFZXz79936Y].

Specific conventions:

- In one early video he buys the wing first, in the same basket of orders as the short [GsrNVbSwH04].
- Once a hedged straddle passes break-even, the long legs start gaining. He therefore calls adjustments optional when time is short [JdR7-suVxCI].
- He gives a worst case of roughly Rs 3–5 lakh for one hedged Bank Nifty trade without adjustment [JdR7-suVxCI].

**Wing distance.** This varies widely across videos and has no single rule:

| Distance | Context | Videos |
|---|---|---|
| 50 points beyond the shorts | Expiry-day Nifty, about 11,550 | [GsrNVbSwH04] |
| 200 points, later tightened to 100 | Intraday strangle; aim is that the day ends positive even if wrong | [4hAvzzjA2xw] |
| 250 points | Crypto options | [3MMjcR_ortI] |
| About 300–400 points beyond the break-evens | Without a stop loss | [P21vgTId9P8] |
| At or near the break-evens | One-lot 16,550 straddle with 16,300P/16,800C (or 16,350/16,750) | [VnlxZ2uP47M] |
| 500 points beyond the shorts | Positional strangles; Bank Nifty 35,000 straddle hedged 34,500P/35,500C overnight | [8W58_AoCKrw, uN9SRyTv_yY, OSNCbyGvQm4] |
| 500–600 points | Overnight strangle | [oYfLG7jLvPQ] |
| Asymmetric: about 300 points on the feared side, about 500 on the other | Closing both sides tightly makes max loss too large relative to the credit | [ZDUmKEZXWMw] |
| 0.5%–1% from the index, depending on quantity | Recent rule | [dmZmt1T5bU0] |
| About 1,200–1,500 points (e.g. 37,000/40,000) | Mainly for margin | [UIf_6_Bg66I] |

**Short-side rules (short premium).** These are the overnight and positional rules:

- Never hold a positional strangle naked [8W58_AoCKrw].
- Overnight and positional shorts are always hedged, because there is no guarantee you can trade the next day [IMjqrkYosgY].
- He describes his book as "completely hedged" through uncertain periods [7RI6oed3Eak].
- Hedge overnight futures too; the instrument is not specified [0qmiy0rYOfE].
- In his recent rules: hedge every short and do not rely only on stop fills, because cheap options can gap past stops [dmZmt1T5bU0, W7Oa3FbF1pg].
- Prefer structures whose max loss is known even for a 10% up or down move [yofu41-yyFU].
- If unsure when to cut a loser, use iron condors, iron flies or delta hedging [WT2kYd3Sofg].

**Over-hedging.** He sometimes buys more wings than he sells:

- About 22,000 wings against 14,000 shorts on an expiry-day straddle [F6sjGAcJXXc].
- In Bitcoin, a 1.1× wing ratio (sell 600, buy 660). His reasoning is that a 5–10% daily move turns the trade profitable, at a small extra premium [LrBXT5C_YYY].

**Managing the wings.** The videos disagree:

- Never touch the hedge legs during adjustments [8W58_AoCKrw].
- Shift the hedge legs when they sit in an expiring weekly series [kaPyJdhVI9c].
- Keep stop-losses on the hedges [GQEbyZhG-ME] (low clarity).
- Move a wing closer as size is added, e.g. 36,100 → 36,000 [F6sjGAcJXXc].

**Evidence he cites.** These are anecdotes, not systematic evidence:

- Wings kept a mishap survivable on a crash day [PiY8pG6Jox4].
- A far 16,000 put held against short 16,700 puts gained when VIX jumped, even though the market rose [o2JJ5p03cyc].

**When he says not to use wings:**

- **Intraday, with stops in place.** He prefers stops to wings. In consolidation both legs decay, so the wing is pure cost. In a big move the stop already limits the loss. He buys intraday wings mainly for margin [IMjqrkYosgY].
- **When the wing premium would nearly cancel the credit.** He skips the hedge [cA07gugsaeY].
- **Weekly straddles held for the whole week.** See 2.2.

**How often taught.** Wings are the most repeated idea in this chapter. They appear in roughly 25 videos, mostly from the 4–6-year-old period, with high clarity in about half.

### 2.2 The counter-argument: weekly wings cost more than they save (about 4 years ago)

**His cost arithmetic [1fDefykVmnk]:**

- Bank Nifty 39,000 straddle, with wings at the break-evens (38,300P / 39,700C).
- Wing cost: about 230 points per week.
- Annualised: about 11,960 points, roughly 30% of the index, or about Rs 3 lakh per lot at lot size 25.

**His break-even method.** He converts the annual wing cost into the number of gaps needed to lose the same amount on a naked straddle:

| Gap size | Gaps per year needed to equal the wing cost |
|---|---|
| 2% | about 120 |
| 3% | about 26 |
| 5% | about 10 |
| 10% | about 4 |

He then compares these counts with how often such gaps actually occur.

**His backtest [1fDefykVmnk].** Stockmock, 1 lot, Jan 2017–Aug 2022, Friday 9:16 entry to Thursday 3:29 pm exit, wings about 800 points out (about the priced-in move):

| Version | Profit | Win rate | Max loss |
|---|---|---|---|
| Naked straddle | about Rs 4.49 lakh | 63% | about Rs 85,000 |
| Hedged (800-point wings) | about Rs 0.88 lakh | 50% | about Rs 14,200 |

- He says the naked version won in every calendar year and had better expectancy and return-to-max-drawdown.
- The worst naked loss came in a budget week.

**A related stream [lkOC0gpSmQQ]:**

- A wing 1,500 points away costing about 100–150 points per week adds up to about 5,200–7,800 points a year.
- He says Bank Nifty has not delivered a gap that large.
- He therefore prefers going naked with small size over iron flies.

**Conflict.** This directly contradicts the "hedge every short" rules in 2.1, both the older ones and the newer ones [dmZmt1T5bU0, W7Oa3FbF1pg, yofu41-yyFU]. The argument applies to buying wings every week for a weekly straddle. It does not address margin savings, which is the main reason he gives for wings elsewhere.

### 2.3 Hedges bought for margin, not risk

He repeatedly says the main purpose of wings is to reduce Indian exchange margin:

- After the new margin regime, large unhedged selling was no longer possible [k6bDh3ONgz0]. Captions say "h positions"; this is read as hedge positions.
- Example margin cut: about Rs 1.6–1.7 lakh unhedged to about Rs 60,000 hedged per set [IMjqrkYosgY].
- Examples of cheap far wings:
  - 11,000 quantity at Rs 9 and Rs 5 [nXjmslNVkyo]
  - 44,000–45,000 strikes at about Rs 11 [xj-1uHZotgY]
  - Far weekly puts at Rs 10–20 on a put ratio spread [o7lr4TUP3Yg]
- Further cases where he names margin as the main purpose: [cA07gugsaeY, UIf_6_Bg66I, YtLDcJgJzcQ, o2JJ5p03cyc].
- **Calendar hedge.** Short next-week options and buy cheap current-week options as the hedge. He says this costs little and gives a large margin benefit compared with same-expiry wings [wcTPYuhzvAU].
- **Cheaper alternative.** In one video he calls the wings "fairly expensive" and suggests running fewer entries (three of six) instead [xj-1uHZotgY].

### 2.4 Rolling cheap weekly hedges on a long-dated short straddle

- Protect a long-dated short straddle by buying weekly options near its break-evens. Example: 14,950P at about Rs 3 and 17,000C at about Rs 1, so about Rs 4–5 per week.
- Over about 20 weeks this totals roughly Rs 80 at most, assuming the hedge stays cheap.
- He notes the cost rises if Nifty moves toward the hedge strike [tTR4X1FsFgE].
- Same video, low clarity: long-dated puts or calls suit portfolio hedging because of low theta and high IV sensitivity [tTR4X1FsFgE]. He gives no detail.

### 2.5 Hedging a long equity portfolio with short index futures

This is the long-book side. Single detailed source [w5oNCUY0Yyg], plus one corroborating anecdote [ow6NsXYp9G0].

**Instrument and size:**

- Most holdings are Nifty 50 names, so he shorts Nifty futures.
- Long exposure: about Rs 4 crore (about Rs 3.15 crore equities plus about Rs 90 lakh stock futures).
- Short: 1,150 Nifty quantity, worth about Rs 1.8 crore. This is a hedge ratio of about 45%, roughly a half-hedge.

**Trigger.** Start the hedge after a large run-up, when he sees limited upside:

- He stayed fully long from about 10,800 to 15,000.
- He shorted at about 15,700–15,800.
- His reasoning: there is less upside to give up when the market is already high.
- He gives no objective trigger.

**Arithmetic he gives:**

- A half-hedge halves both P&L directions: ±20% gives ±Rs 40 lakh instead of ±Rs 80 lakh.
- Upside cost: in a 25% rally, he makes about Rs 50 lakh instead of Rs 1 crore.
- His justification for accepting that cost: the market cannot rise without a normal correction of about 20%.

**Exit, and the round-trip argument:**

- If the market falls 20% and he covers at the low, the hedge profit (about Rs 40 lakh, about 10%) is kept when the market recovers. The unhedged book is only back to flat.
- This works only if the hedge is lifted before the recovery.
- In the corroborating anecdote, he covered the shorts gradually as the market fell, believing upside had become larger [ow6NsXYp9G0].

**Roll income.** Here the short-futures overlay is the instrument, and he treats the basis as a return:

- He assumes about 50 points of basis per month.
- 12 flat months: about 600 points, about Rs 7 lakh on 1,150 quantity. He says the hedge then costs nothing.
- About 35 months: about 1,750 points, about Rs 20 lakh, about 5%.

**His market scenario at the time (not a rule):**

- Expected path: 17,000–17,500, then a 15–20% correction, then a run toward 20,000.
- Short 15,800, cover 14,800: about Rs 18.4 lakh (futures plus premium) against about Rs 24 lakh lost on the book. Net loss about Rs 6 lakh.

**Related practice:**

- He closed long Nifty futures because they doubled the downside of his existing short puts [1ItbBTjFgVQ].
- He describes a pledged index ETF (Nifty Bees) used as margin under a futures pair. The ETF supplies the market return and the pair adds return. His example: about 15% + 15% [E5rCsOzaXyY]. This is capital efficiency rather than a hedge.

### 2.6 Directional futures hedged with a bought option

**Long futures + put:**

- Ethereum: long 5 futures at about 1,625 on a break of the prior day's high.
  - Hedged with a next-day 1,580 put.
  - Stop about 1,595.
  - Max loss about $140–150, under 1% of capital [MeKx6Qh50vs].
- Nifty futures with a 17,900 put, and Bank Nifty futures with a put whose strike is unclear in the captions (about 42,100) [xV7EMUdSL4w].

**Short futures + call:**

- Short 1,000 Nifty (about 20 lots) with a long 17,300 call.
- Max risk about Rs 3 lakh, about 0.5% of capital [AyC9r0_ZiN8].

### 2.7 Short futures plus a short straddle above spot

**The structure:**

- Short 1,000 Nifty futures (entered around 17,000) plus a 1,000-quantity 17,500 short straddle.
- His stated logic: a fall pays on the futures, and a rise is "offset" by the straddle [cwcwg2d8pPU, ApP_IR63Ff8].
- A calendar version: on one day the futures made about +Rs 3.67 lakh, the straddle about −Rs 3.5 lakh and the calendar about +Rs 2.1 lakh. Net is reported as −Rs 1.4 lakh, which does not reconcile with the three legs as stated [NwFNA0IjOkc].
- Futures are marked to market daily. On one day the futures lost about Rs 1.8 lakh while the options gained about Rs 2.5 lakh over two days [QED0exJOqYc].

**Caution (an analytic point, not his claim).** The straddle offsets only up to around the strike plus the credit. Above 17,500 the short call adds to the short-future loss, so this is not protection against a strong rally.

### 2.8 Discretion and overrides

- He closed hedged positions early twice around financial year-end for about Rs 60,000–70,000.
- He called this a mistake costing about Rs 14 lakh in opportunity [Vn40nCE-lLI].

## 3. How a program would test it

1. **Naked vs winged weekly ATM straddle (replicating [1fDefykVmnk, lkOC0gpSmQQ]).**
   - Setup: Bank Nifty weekly ATM short straddle, Friday 9:16 to Thursday 15:29, 2017 onward.
   - Variants: naked, and wings at the break-evens, 500, 800 and 1,500 points, 0.5% and 1% of spot.
   - Metrics: total P&L, win rate, expectancy, max drawdown, worst week, per-year P&L, and return on actual margin.
   - Data: minute or EOD option chains with bid/ask, historical SPAN margins.
   - Repeat on SPX/XSP weeklies.

2. **Gap break-even count.**
   - For each year, compute the actual weekly wing cost at the break-evens.
   - Compute the naked-straddle loss for gaps of 2/3/5/10%.
   - Compare the implied break-even gap counts with observed overnight and intraweek move counts.
   - Data: index OHLC and option prices.

3. **Overnight strangle with 500–600-point wings vs naked [oYfLG7jLvPQ, 8W58_AoCKrw, IMjqrkYosgY].**
   - Hypothesis: the winged version has materially lower max drawdown, positive net return, and higher return on margin.
   - Separate days with moves of 3% or more [PiY8pG6Jox4].

4. **Wing ratio of 1.1× on a high-IV underlying [LrBXT5C_YYY].**
   - Compare 1.0× and 1.1× iron condors on BTC daily options.
   - Data: Deribit option history.

5. **Half-hedge with index futures after a run-up [w5oNCUY0Yyg].**
   - Define the trigger objectively, e.g. index more than X% above its 52-week low or Y% above its 200-day average.
   - Hedge ratio: 45–50%.
   - Exit after a 10–20% decline.
   - Compare against unhedged and constant-hedge versions on CAGR, volatility and max drawdown.
   - Data: Nifty, S&P 500, TSX 60 futures and index total-return series.

6. **Roll-yield claim.**
   - In flat 12-month windows, a rolled short future earns roughly the accumulated basis.
   - Measure realised roll P&L against the "50 points/month" figure, and against rate minus dividend yield.

7. **Short future + short straddle above spot vs short future alone [cwcwg2d8pPU, ApP_IR63Ff8].**
   - Measure the payoff distribution over weekly and monthly horizons, especially for rallies past the strike.

8. **Directional futures with an option hedge [MeKx6Qh50vs, AyC9r0_ZiN8].**
   - Break of the prior day's high or low, futures entry, with an OTM option hedge plus stop.
   - Compare against stop-only on expectancy and worst loss.

## 4. Transfer

**Applies roughly as-is:**

- The wing/iron-condor logic and the cost-vs-gap-frequency method. These are generic.
- Half-hedging a large-cap book with a short index future: ES/MES against US large caps, SXF (TSX 60 futures) against Canadian large caps.
- The half-hedge arithmetic.
- The directional futures + option hedge. Crypto examples transfer directly.

**Needs adapting:**

- **Wing distances in points.** Rescale to SPX, XSP or TSX 60 levels and implied volatility. The percent-of-spot version [dmZmt1T5bU0] is the more portable form.
- **US instruments.** Weekly and daily SPX/XSP and SPY expiries replace Indian weeklies. Cash settlement and European exercise on SPX make it the closer analogue.
- **Canadian instruments.** TSX 60 options (SXO) and XIU options are thinner, so wing costs and spreads will be worse.
- **Roll income.** In North America the roll on a short future reflects interest rate minus dividend yield. Check the size; do not assume 50 Nifty points per month.
- **Margin.** "Wings for margin" depends on Reg T vs portfolio margin in the US and on CIRO rules in Canada. Defined-risk spreads usually do cut margin, but the size of the saving differs.
- **Beta and sector match.** Index-futures hedges need a beta check for portfolios that are not index-like.

**India-only:**

- SPAN margin-benefit specifics [k6bDh3ONgz0, cA07gugsaeY, o7lr4TUP3Yg].
- The current-week vs next-week calendar margin trick [wcTPYuhzvAU].
- Pledging Nifty Bees.
- Bank Nifty weekly lot sizes and his Stockmock results.
- Note: Indian weekly-expiry availability has changed since many of these videos. Check current contract specs before reusing his setups.

## 5. Gaps and doubts

**Core contradiction.**
- "Always hedge shorts" (about 5–6 years ago, and again about 2 years ago) conflicts with "weekly wings don't pay; go naked, small" (about 4 years ago).
- Intraday he also prefers stops to wings [IMjqrkYosgY].
- The videos never reconcile these positions. A possible reading is that he hedges for margin and overnight gaps, and goes naked only for weekly straddles with small size. This reading is unconfirmed.

**Backtest inconsistency [1fDefykVmnk].**
- From the reported figures, profit divided by max loss is about 5.3 for naked (4.49/0.85) and about 6.2 for hedged (0.88/0.142).
- That conflicts with his claim that the naked version had the better return-to-max-drawdown, unless max drawdown differs from max single loss.
- This needs replication.

**No consistent wing distance.** The range runs from 50 points to 1,500 points and from 0.5% to 1% of spot. There is no volatility-based rule except "about the priced-in move" [1fDefykVmnk].

**Conflicting wing management.** Never touch [8W58_AoCKrw], shift at weekly expiry [kaPyJdhVI9c], stop-losses on wings [GQEbyZhG-ME].

**Futures + short straddle (2.7).** He calls it a hedge, but it is not one against a strong rally. The one P&L breakdown also does not add up [NwFNA0IjOkc].

**Caption problems:**
- "h positions" [k6bDh3ONgz0].
- Unclear Bank Nifty put strike [xV7EMUdSL4w].
- "600 points from ATM at 700-strike straddle" [YtLDcJgJzcQ].
- "Dollars" for a put on Bank Nifty-like strikes [uN9SRyTv_yY].

**Not covered at all:**
- Collars.
- Protective puts on individual stocks.
- Beta-weighted hedge ratios.
- VIX-based hedge timing.
- Tail-hedge programs for portfolios beyond one low-clarity remark on long-dated options [tTR4X1FsFgE].

**Thin sources.**
- The portfolio futures hedge rests essentially on one video [w5oNCUY0Yyg] plus one anecdote [ow6NsXYp9G0].
- Its run-up trigger and cover rule are discretionary.
- Its market scenario was a call made at that time, not a method.
