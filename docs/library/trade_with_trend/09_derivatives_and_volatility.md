<!-- Trading Knowledge Library · Trade With Trend (Raunak A, Trade With Trend, India). Built 2026-10-16 from 161 public videos with captions (of 289 on the channel; members-only videos were not used): one structured note per video (Claude Sonnet 5.5) -> this chapter (Claude Opus 5.5), src/research/library.py. Paraphrased; the transcripts stay on the laptop. Evidence class: external teaching = hypotheses to test, never Ananta rules; nothing in the agent reads docs/library/. -->

# Derivatives and volatility

## 1. What he teaches here and how it fits

Raunak A's teaching on derivatives is mostly a warning. He tells beginners and small accounts to stay out of futures and options (F&O). He calls Indian retail F&O largely gambling and an opportunity cost against cash equities. He tells traders to ignore option-chain data such as open interest (OI) and put-call ratio (PCR) when judging trend [eeKRfAbbvZA, mim7ylyaN74, Lw6h6T30VvE, sbHzNd2iA8k, kkJ4m9JQ4pM, hKnYYRpd63s, kwbfXjRtEkk].

Two things sit alongside that warning:
- **An options primer.** One undated video covers premium, moneyness, theta, delta and contract mechanics [mNHXZlKSUgo].
- **Volatility as a context gauge.** This is the part he actually uses. He reads India VIX to set the market regime, to estimate where bottoms form, to decide whether intraday breakout methods are worth running, and to choose between defensive and high-beta sectors [SbtFCxbIB1w, kwbfXjRtEkk, Sb6KTt64YKE, KUlNy1_Rk9M, 4kP0_EuS_EY, hk4d8AxbQ3A, s1ZCPQI5894].

This fits his overall method, which is price-and-volume trend following in cash stocks. In that method, derivatives data is treated as noise and volatility is treated as weather. The one derivative he says he trades himself is leveraged index futures, which he also uses as a hedge [KRoie4cj5TQ, U7YrYjIS9B8].

Everything below is his claim or method, a hypothesis to test, not established fact.

## 2. The ideas

### 2.1 Stance: retail should avoid F&O

**What he claims**
- About 90% of beginners in F&O blow up their accounts and suffer psychological damage. He says retail is steered into F&O for others' benefit, meaning brokers, advisers and "the ecosystem" [eeKRfAbbvZA, mim7ylyaN74, 9dbnXEEHgsc].
- F&O with a small account is a trap that destroys capital. To grow a small account, stay out of F&O entirely [arFNgAPisHU, sbHzNd2iA8k].
- **Opportunity cost.** In Oct–Dec 2023, Nifty rose from under 19,000 to about 21,400 while retail sold options and straddles. He says taxes and losses compound in F&O, whereas money and experience compound in equities [Lw6h6T30VvE].
- **Short horizons lose.** Option buyers and writers working over days have time and volatility against them. Longer-horizon investors make both work for them [-qQntPmfe-s, uw5QQOenJnQ].
- **News-driven and thin markets are worst for short-term F&O.** His example is a 250-point Nifty fall in 15 minutes, with expiry-day puts rising several-fold. Position traders can sit through such swings [N5bb0Cu8RAs, KDSbZ0oW2U0].
- He says he has given the same advice for over a decade, and his community carries no short-term or F&O content [kwbfXjRtEkk].

**How strongly and how often**
This is his most repeated theme here: at least 14 videos spread across about 8 years. It is mostly argument, not data.

**Where the videos disagree**
- One 8-year-old video rates options the "most rewarding" instrument, with loss limited when buying, though it needs a lot of experience [9dbnXEEHgsc].
- A video from 5 months ago expects responsible F&O traders working within risk limits to do well over the next 24 months [-qQntPmfe-s].
- One video says he teaches equities and index futures [KRoie4cj5TQ]. A later one says his community has no F&O content [kwbfXjRtEkk].

### 2.2 Options mechanics (primer)

All of this comes from one video with no publish date [mNHXZlKSUgo]. It is taught clearly and is textbook material, not his own edge.

- **Definition.** An option gives the right, but not the obligation, to buy (call) or sell (put) at a strike by an expiry date. The underlying can be a stock, index, commodity or currency.
- **Premium.** Premium = intrinsic value + time value.
  - Call intrinsic value = max(spot − strike, 0).
  - Example: Nifty spot 11,570, 11,400 call priced at 200 → intrinsic 170, time value 30.
- **Moneyness.**
  - Calls: strike below spot is in the money (ITM); strike above spot is out of the money (OTM).
  - Puts: the reverse.
  - OTM options hold only time value.
- **Theta (time decay).**
  - Theta hurts buyers and helps sellers.
  - Practical rule: subtract theta from the premium for each day passed. Example: 11,600 call at 52, 6 days to expiry, theta about −7.2 → about 45 the next day.
  - Decay is gentle at 90 days and falls off a cliff in the last 10–15 days. Writers sell OTM options in that window.
- **Delta and gamma.**
  - Delta runs 0 to 1 for calls and −1 to 0 for puts.
  - Option change ≈ delta × move in the underlying. Example: delta 0.886, premium 193, Nifty +100 points → about 281.
  - Gamma is the rate of change of delta. Its practical use was deferred.
- **IV, vega and rho.** IV appears in the option chain and drives hedge strike selection. Vega and rho were deferred. Clarity on this point is low.
- **Contract specs at the time (India).**
  - Lot sizes: Nifty 50, Bank Nifty 40.
  - Monthly expiry: last Thursday, moved to the prior trading day if that is a holiday.
  - Weekly options: only Bank Nifty, expiring Thursdays.
  - Liquidity sits in a few near-the-money strikes. LEAPS exist but are illiquid.
  - These specs are now outdated.
- **How options differ from stocks and futures.** Options expire and pay no dividends. Futures roll monthly.
- **Three uses he lists:**
  - Income via writing: viable but risky.
  - Portfolio insurance: for example, against a 10–15% drop around a general election, on a ₹50 lakh portfolio.
  - Leverage: far OTM calls potentially returning 200–400%.

### 2.3 Option writing (selling)

**Conditions he sets before anyone writes options**
- At least 5 years of profitable trading with good capital protection.
- A large account.
- Tested sizing and entry methods.
- Strong support/resistance reading.
- Anyone thriving at it early is, in his view, lucky [6ZKLrl0z8jY, arFNgAPisHU].

**Arguments for writing**
- Most options expire worthless.
- Capital needs are lower.
- Writers can sell OTM options in the last 10–15 days [6ZKLrl0z8jY, mNHXZlKSUgo].

**Arguments against naked writing**
- Poor asymmetry: his example is risking 50,000 to make 20,000.
- Backtests show single days wiping out months of profit. The notes contain no backtest detail.
- Newer Indian margin rules made selling harder [KRoie4cj5TQ, 6ZKLrl0z8jY].

**What is missing**
No strike rules, sizing, stops or defined-risk structures are given. Spreads and straddles are not taught. Straddle selling appears only as an example of retail gambling [Lw6h6T30VvE].

### 2.4 Open interest, option chain and PCR: ignore for direction

**Rule.** Do not mix price-action trend analysis with OI data, because price decides and OI does not. For 4–6 month trend views, option data always shows overhead resistance on dips and prompts early exits [kkJ4m9JQ4pM]. This is taught clearly and has the most detail of any point in this section.

**Supporting example.** In Oct–Nov 2020, option-chain resistance was widely quoted at Nifty 11,300, 12,000, 12,500 and 13,000. The index went to about 14,500 [kkJ4m9JQ4pM].

**Other mentions**
- He dismisses OI expansion and aggressive put writing, as cited by breakout chasers, as hot-stock noise [mim7ylyaN74].
- Small accounts should ignore OI and the option chain [sbHzNd2iA8k].
- PCR, like RSI or stochastic oversold readings, is not a bottom signal. Markets can stay oversold a long time; he cites O'Neil's 2000 example and rejects claims such as "RSI 18" [hKnYYRpd63s].
- OI is defined, with its use deferred to a later part that is not in the notes [mNHXZlKSUgo].

**Consistency.** He takes this line across 5 videos, from about 5 years ago to 1 year ago.

### 2.5 India VIX as a regime gauge

**Levels he uses**
- **Benign:** about 9 to 13–14.
- **Concern:** above about 16–18 [SbtFCxbIB1w].

**How to read a low reading**
- A low reading is not itself a warning. Example: 10.45 inside a recent 10.4–11.9 range.
- VIX needs a catalyst to rise; he names tariff news and an Iran–US conflict.
- Worry only when the whole range shifts up, for example from 10–12 to about 14–18 [kwbfXjRtEkk].
- Even at a very low 9.2–9.4, random pullbacks can still happen, so keep position sizes measured [SbtFCxbIB1w].
- He treats VIX fear-mongering as noise [SbtFCxbIB1w].
- He attributes low VIX partly to low derivative positioning and SIP/STP flows holding up the market [kwbfXjRtEkk].

**Watching for spikes**
- Volatility is likely to expand. If it spikes again, expect more trouble.
- Catalysts he listed: the US Fed cut expected in September, the US elections and the debates.
- Don't believe "back to normal" talk [B8HZvUkY5sA].

**Perspective on extremes.** At about 21, VIX was far below the 2008 peak (about 68–72) and the Covid peak (about 80–85). So extreme volatility hadn't been seen yet, and short-term traders should be careful because the eventual peak is unknown [yYwiSDVwgyA].

**How often.** Taught in 4 recent videos (1 month to 2 years old). The thresholds are consistent across them.

### 2.6 VIX spikes and market bottoms (long side)

**Levels he cites**
- **Recent peak zone:** India VIX has tended to peak at 28–32 over the last 2–3 years. A peak there followed by a decline is a positive sign [KUlNy1_Rk9M].
- **Likely final bottom:** with VIX at about 23, he expected a final bottom near 32–33, the Russia–Ukraine level. Prior peaks he cited were 32–33 and 28–30. The bottom might come only after a V-shaped bounce to the 50- and 200-day averages first [Sb6KTt64YKE].
- **Historical case:** in 2011–13, VIX cycled between spikes and crashes. The market bottomed in August 2013 with VIX at about 35–36 [s1ZCPQI5894].

**Action and attribution**
- He favours deploying into ETFs when volatility spikes [yYwiSDVwgyA].
- He attributes to Druckenmiller the practice of watching VIX spikes as extreme fear near turning points [ywccnKeWXNo].

**Tension.** He gives a recent "normal peak" zone of 28–32, and in another video warns the peak is unknowable with historic peaks of 68–85 [KUlNy1_Rk9M vs yYwiSDVwgyA].

**What is missing.** No exact entry trigger, such as "first close back below X," is given.

**Short side.** None is stated for VIX.

### 2.7 VIX as a filter for intraday methods

**Initial balance (IB), from a 13-year-old video [4kP0_EuS_EY]**
- **Low VIX:** wide IB with VIX about 12–14 → stay out.
- **High VIX:** wide IB with VIX above about 17–18 → expect the IB to be breached later in the day.
- **Stock choice:** prefer high-beta stocks (examples: JP Associates, SBI, ICICI Bank) over low-beta ones (example: ITC).

**Historical case.** Sept–Dec 2012: Nifty stuck at 5900–6100 with VIX falling, many non-trend days, a poor time to trade. Trader-friendly day structures returned when VIX rose [4kP0_EuS_EY].

**Opening range breakout (ORB), from a 6-year-old video [hk4d8AxbQ3A]**
- ORB works only in high VIX: above about 18, and he cites above 20 as the condition for months of good performance. VIX was about 25 at the time.
- Avoid ORB in low volatility.
- In other markets, check the local volatility index.

**Status.** Both are older material, from his intraday era. His current teaching rejects short-term trading.

### 2.8 VIX and sector choice

- **Rising or spiking VIX:** defensive pockets tend to do well over time.
- **Tight, low VIX range without frequent spikes:** high-beta sectors do well [s1ZCPQI5894].

This comes from one video, with no thresholds or holding periods.

### 2.9 Volatility within a stock's trend

**Long-side guidelines [tTdy5srpW9Q]**
- Volatility should fall as a new uptrend starts.
- His "non-negotiable" guideline 3: if price is up 5–6% and volatility has not dipped, or has stayed flat, be cautious.
- **Trend change:** after a prolonged volatility upswing plus a shift in the economy or market, look for a change of trend.
- **Exit:** as the trend matures and volatility rises with deeper retracements, book profits.

**Weakness.** The volatility measure is not named in the captions, and clarity is low to medium. It comes from one video.

### 2.10 Futures and hedging

**Futures**
- He trades index futures with leverage himself [KRoie4cj5TQ].
- For beginners, small margin builds large positions and risk is hard to manage [9dbnXEEHgsc].
- Fixed lot sizes stop graduated scaling in and out. His strategies should be traded in cash stocks for that reason [2Yv0E57_bs4, zWYCYySQVNc].
- Options rank last in his preference: decay and volatility must work for you, and gaps are hard to manage [zWYCYySQVNc].

**Hedging**
- He is not a believer in option hedges.
- When he hedges, he keeps large-cap longs and shorts Nifty futures [U7YrYjIS9B8]. No hedge ratio or trigger is given.
- In weak phases, a trader may short sell or buy puts to satisfy the urge to act. No rules are given [M4Z-Gi4gGag].
- This conflicts with the primer, which lists portfolio insurance with options as a main use [mNHXZlKSUgo].

**India market-structure remarks**
- **Volume ratio:** India's derivatives-to-cash volume ratio far exceeds other markets, roughly India about 420, Germany in the 30s, US about 9, Japan about 2. The figures come from captions and are uncertain [Lw6h6T30VvE, Y4TewQHVhvc].
- **Whipsaws help cash traders:** option-driven gap-downs and gap-ups shake out weak hands. For cash traders this brings pullbacks in which to add to winners [Y4TewQHVhvc].
- **Closing auction (live since 3 August):** he believes it is distorting expiry days and being gamed. Examples: far-OTM puts going from a few rupees to hundreds in minutes, and Sensex falling about 1,500 points in minutes. He says this may drive out option writers [kwbfXjRtEkk].
- **CAS distortion:** the new CAS system distorts index candles on lower timeframes. Use the Nifty and Bank Nifty futures charts on daily and weekly timeframes, preferring weekly. He expects 2–3 months to stabilise [SuYHqw5zA8U].

## 3. How a program would test it

1. **VIX regime buckets.** Compare Nifty 50 forward 20-, 60- and 120-day returns and maximum drawdown when India VIX is ≤14, 14–16 and >16–18. Also test regime *shifts*: a 20-day VIX average moving from 10–12 to ≥14 versus staying low.
   - Data: daily India VIX and Nifty, 2008 onward.
   - Sources: [SbtFCxbIB1w, kwbfXjRtEkk].

2. **VIX peak-and-fade entry.** Define the event as India VIX making a local peak between 28 and 36, then closing at least 20% below that peak. Compare forward 1-, 3-, 6- and 12-month Nifty returns against unconditional returns. Run variants:
   - first close above 30;
   - first close above 30 with Nifty below its 200-DMA.
   - Data: as in test 1.
   - Sources: [KUlNy1_Rk9M, Sb6KTt64YKE, s1ZCPQI5894, yYwiSDVwgyA, ywccnKeWXNo].

3. **IB breach versus VIX and beta.** On days whose first-hour range is in the top tercile of the trailing 20 days, measure the probability that the rest of the day extends beyond the IB. Split by India VIX (12–14 vs >17) and by stock beta (top vs bottom quintile versus Nifty).
   - Data: 1-minute or 5-minute bars for liquid NSE stocks and Nifty, plus VIX.
   - Source: [4kP0_EuS_EY].

4. **ORB conditional on VIX.** Run a fixed ORB rule (for example, the 15-minute range, stop at the opposite side, exit at the close) on Nifty futures. Compare net-of-cost expectancy on days when prior-close VIX is above 18 (and above 20) versus below.
   - Data: intraday futures bars, VIX, costs.
   - Source: [hk4d8AxbQ3A].

5. **Option-chain resistance.** For each monthly expiry from 2019 to 2024, mark the max-call-OI strike above spot at the start of the series. Measure how often Nifty closes above it before expiry. Separately, test whether adding OI-derived levels improves a 4–6 month trend model built only on price and volume.
   - Data: historical NSE option-chain OI snapshots.
   - Source: [kkJ4m9JQ4pM].

6. **Volatility contraction after breakout.** For 52-week-high or base breakouts, measure the change in ATR(14), or 20-day realized volatility, over the first 5–6% of the advance. Compare forward 3- and 6-month returns between the bucket where volatility declined and the bucket where it was flat or rising.
   - Data: daily OHLC for the stock universe.
   - Source: [tTdy5srpW9Q].

7. **Defensive versus high-beta by VIX trend.** When VIX is above its 50-day average and rising, compare the next 1–3 month relative return of defensive indices (FMCG, pharma) against high-beta ones (metal, realty, PSU bank). Reverse the comparison for low, range-bound VIX.
   - Data: NSE sector indices and VIX.
   - Source: [s1ZCPQI5894].

8. **Index-futures hedge.** Take a long large-cap book. Short Nifty futures at a 0.5–1.0 beta-adjusted ratio when Nifty is below its 50-DMA, or when VIX is above 18. Compare drawdown, CAGR and Sharpe against the unhedged book, net of roll costs.
   - Data: stock and futures prices, roll data.
   - Source: [U7YrYjIS9B8].

## 4. Transfer to TSX and US markets

**Applies largely as is (concepts)**
- The options primer [mNHXZlKSUgo].
- The argument that short-horizon option trading fights decay and volatility.
- Distrust of OI/PCR for multi-month trend calls.
- Volatility contraction inside a new trend.
- Using spikes in the volatility index as bottom context.
- Defensive versus high-beta rotation by volatility regime.
- A short index-futures overlay as a hedge.

**Needs recalibrating**
- **VIX thresholds.** All levels (14, 16–18, 20, 28–32, 35) are India VIX levels.
  - For the US, use VIX. Its typical calm and spike levels differ, so derive thresholds as percentiles of each index's own history rather than copying numbers.
  - For Canada, the notes name VIXC (S&P/TSX 60 VIX). Check its data history and liquidity before relying on it.
- **Futures instruments.**
  - US: ES and micro MES. Micro contracts largely remove his fixed-lot objection [2Yv0E57_bs4].
  - Canada: SXF (S&P/TSX 60 futures). These have larger contract sizes and thinner liquidity, so the lot-size problem is more relevant there.
- **Sector mapping.** Use TSX/US sector indices or ETFs, for example staples, utilities and health care versus energy, materials and tech.
- **Costs and margin.** US/Canadian option and futures costs, margin and tax differ from India's. The writing gate and the small-account warnings should be re-argued on local costs.
- **IB and ORB tests.** These need local session times. US equities also have pre-market activity that affects the opening range.

**India-only**
- Weekly-expiry dynamics, the NSE closing auction, CAS candle distortion and SEBI margin changes.
- Lot sizes and expiry days in the primer.
- The derivatives-to-cash volume ratio argument.
- SIP/STP flow remarks.
- The specific Nifty episodes from 2012, 2020 and 2023.

## 5. Gaps and doubts

**Not taught in these notes**
- **Spreads, straddles and strangles:** no strategy content at all. Straddle selling appears only as an example of gambling [Lw6h6T30VvE].
- **PCR:** mentioned only to dismiss it as a bottom signal [hKnYYRpd63s].
- **OI usage:** promised in a later part of the primer that is not in the notes.
- **Gamma, vega, rho and IV:** practical use deferred and absent [mNHXZlKSUgo].
- **Rules for any options trade:** no strikes, sizing, stops or exits for writing, put buying or hedging [6ZKLrl0z8jY, M4Z-Gi4gGag].
- **Hedge parameters:** none given for his index-futures hedge [U7YrYjIS9B8].

**Unverified or unclear**
- **Claimed numbers:** the "about 90%" beginner-failure figure and the writing "backtests" are asserted without data [eeKRfAbbvZA, KRoie4cj5TQ].
- **Caption uncertainty:**
  - the derivatives-to-cash ratios (about 420 for India; "several hundred times") [Lw6h6T30VvE, Y4TewQHVhvc];
  - the unnamed volatility measure [tTdy5srpW9Q];
  - "75–90" presumed to be a crude oil range [kwbfXjRtEkk].

**Dating and staleness**
- The primer [mNHXZlKSUgo] has no date. Its contract specs (Nifty lot 50, Bank Nifty-only weeklies, last-Thursday expiry) are outdated.
- The IB and ORB VIX filters come from 6- and 13-year-old intraday-era videos. They may not reflect his current view, which rejects short-term trading.

**Contradictions or shifts**
- Options as "most rewarding" [9dbnXEEHgsc], versus last in preference [zWYCYySQVNc], versus near-blanket avoidance [eeKRfAbbvZA, kwbfXjRtEkk].
- Option hedging as a key use [mNHXZlKSUgo], versus not believing in option hedges [U7YrYjIS9B8].
- A 28–32 VIX "normal peak" zone [KUlNy1_Rk9M], versus the warning that the peak is unknowable with historic peaks of 68–85 [yYwiSDVwgyA]. His 32–33 bottom estimate [Sb6KTt64YKE] sits between the two.
- Teaching index futures [KRoie4cj5TQ], versus no F&O content in his community [kwbfXjRtEkk].
- A broadly negative stance, versus an optimistic 24-month outlook for responsible F&O traders [-qQntPmfe-s].

**Untested assertions about market structure**
- The closing-auction "gaming" claim is opinion [kwbfXjRtEkk].
- The CAS stabilisation estimate of 2–3 months is a guess [SuYHqw5zA8U].
