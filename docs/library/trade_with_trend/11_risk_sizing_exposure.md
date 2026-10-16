<!-- Trading Knowledge Library · Trade With Trend (Raunak A, Trade With Trend, India). Built 2026-10-16 from 161 public videos with captions (of 289 on the channel; members-only videos were not used): one structured note per video (Claude Sonnet 5.5) -> this chapter (Claude Opus 5.5), src/research/library.py. Paraphrased; the transcripts stay on the laptop. Evidence class: external teaching = hypotheses to test, never Ananta rules; nothing in the agent reads docs/library/. -->

# Risk sizing exposure

## 1. What he teaches here and how it fits

Raunak A treats risk control as the base layer of his trend-following method. Preserving capital comes first and growth second [NYWbbvaJnPc, kkJ4m9JQ4pM]. He works at four levels:

- **Per trade:** a fixed fraction of the account is risked per trade, and the share count follows from the stop distance. Results are tracked in R-multiples.
- **Entry construction:** he scales into a position through pyramids or time-staggered purchases rather than buying full size at once.
- **Portfolio exposure:** total exposure is set by market regime, using index moving averages (50/200 DMA), breadth and volatility, plus a portfolio-level drawdown limit.
- **Capital allocation:** money is split across swing, positional and long-term buckets, with an emergency fund held outside the market.

His late-period teaching centres on "progressive exposure". You start with small test positions, let the profits from them form a cushion, and concentrate only into names that are already working. When conditions are weak, he stays bullish in view but keeps size small.

Everything below is his claim or method. Each item is a hypothesis to test, not established fact.

## 2. The ideas

### 2.1 Capital preservation and "protect the downside"

**What he says**
- Protect the downside with predefined rules and the upside takes care of itself [N2dUTcb9CzQ, S--7ta4FmbY].
- Decide your square-off threshold in advance so that you do not need to fear news [SuYHqw5zA8U].
- Nibble on dips with stops rather than predicting the next 20–30 days [0nbQs92kYuY].
- Judge each trade by reward against the risk taken up front, not by P&L or daily mark-to-market. He says P&L focus drives greed, fear and oversized F&O bets [kkJ4m9JQ4pM].

**Why he thinks long-only cash equity is safer**
- A long-only cash-equity trader with exit rules is unlikely to blow up an account, unlike an F&O trader [jcWYGNInYg8].
- Accounts are ruined by leverage and refusal to take losses, not by cutting quickly [Y4TewQHVhvc].

**Coverage:** a recurring theme, high clarity, but conceptual and not codable on its own.

### 2.2 Per-trade risk and position-sizing formulas

**Fixed-fractional risk (his most consistently stated rule)**
- Formula: shares = (account × risk%) ÷ (entry − stop).
- Risk levels: 1% of capital per trade; 0.5% for beginners until the strategy is mastered; 1.5–2% or more once experienced [jlpd-YpqwiQ, _AiSzhs67J4, 2Yv0E57_bs4, QWcb7yxYAxk, p03ho_Rhc_E, R6QjIoYHoFE, cQpU-EnhdSw, VqoLpEvre04, HHkcCy5LrCM, 1jsLESmVLVU].
- Worked examples:
  - 10 lakh capital, 1% risk (10,000), entry 280, stop 260 → 500 shares [_AiSzhs67J4, 2Yv0E57_bs4, QWcb7yxYAxk].
  - Entry 200, stop 190, risk 5,000 → 500 shares [p03ho_Rhc_E].
- Total risk should never exceed 1% of the account at any time, including across a two-step entry [1jsLESmVLVU].
- To practise, stay on one time frame for 20 trades at 0.5% risk and journal every trade [VqoLpEvre04].

**Three sizing models [aUgaUeCmSOQ]**

| Model | Formula | Example | Suits |
|---|---|---|---|
| Equal value | account ÷ planned number of holdings | 100,000 ÷ 20 = 5,000 per position | Long-term, part-time traders |
| Equal risk | (account × risk%) ÷ (entry − stop) | 2% of 100,000 = 2,000; entry 780, stop 760 → 100 shares | Short-term traders; beginners at 0.5–1% |
| Volatility | risk amount ÷ (2 × ATR14, daily) | 1,000 ÷ (2 × 18) ≈ 28 shares | Advanced traders |

- He suggests moving from equal value to volatility-based sizing as a trader advances.
- The stated purpose of sizing is that no single trade causes a drawdown too deep to recover from.
- He warns that oversized, leveraged positions can lose 10–30% of an account in one gap session.
- He defines the right size as one that fits both the trader's temperament and what the account can bear.

**Stop first, then size**
- Set the stop at the structure pivot before buying, and size so that normal swings inside the structure do not shake you out [mim7ylyaN74].
- Wide stops require small positions. Deploy only what you can tolerate losing [sIo5XQqZ0b0].
- The same formula works for a basket of stocks, using the basket's pivot or low as the stop [KUlNy1_Rk9M].

**Instrument choice:** he prefers stocks to futures because futures lot sizes make failed signals costly and do not allow fine sizing [R6QjIoYHoFE].

**Short side:** the same 1% rule applies. For gap-down shorts the stop goes at the opposite end of the range, and he accepts that this stop is wide because shorts are volatile [HHkcCy5LrCM]. Nothing else on short sizing is distinct.

**Coverage:** taught often and clearly, mostly in 5–8-year-old videos.

### 2.3 Regime-scaled sizing: index averages, breadth, volatility, counter-trend

Size and risk shrink as conditions worsen. This is one of his most frequent late-period themes.

**Per-trade risk by regime**
- About 2% risk per trade in a strongly bullish market; 1–1.25% in a thin, volatile market [N5bb0Cu8RAs].
- Normal 2%, cut to 0.25–0.5% when broad indices are below the 50 and 200 DMA or breadth is poor. That is roughly 8–15% of normal size [M4Z-Gi4gGag, 8QeR8FmYYg4].
- He keeps buying small even in weak markets. His reason: you cannot enter 100% only at the bottom, so you must accept small losses to catch the real trend [8QeR8FmYYg4].

**Index moving-average rules**
- Small size and "do nothing" until the index retakes its 50- and 200-day averages, for 6–18-month traders [Sb6KTt64YKE].
- Traders lighten up once the index sustains below the 50 DMA. Investors treat the index sustaining below the 200 DMA, especially with the 200 DMA turning down, as a warning [hpbDmEK-FvM].
- He claims these rules (credited to O'Neil and Weinstein) saved his community 20–25% of account size in the 2025 fall [hpbDmEK-FvM].
- Buying stocks below their own 200 DMA is "the main cause of big losses" [sbHzNd2iA8k].

**Breadth**
- Size should follow breadth [-qQntPmfe-s, Jpu536_AmGc, SbtFCxbIB1w, jcWYGNInYg8].
- Poor breadth means "bare minimum" size [-qQntPmfe-s].
- The one numeric threshold: fewer than 50% of stocks above the 200 DMA counts as poor, with India VIX near 9.3 as context [SbtFCxbIB1w].
- In poor breadth, expect frequent stop-outs and possible 10–15% index falls, and stay nimble [jcWYGNInYg8].
- **Nuance:** in [SbtFCxbIB1w] he allows larger size in strong-sector pockets even when broad breadth is poor. That softens the "bare minimum" rule in [-qQntPmfe-s].

**Volatility:** size smaller when volatility expands and larger when it subsides. He is in no hurry to be fully invested while volatility is high [KUlNy1_Rk9M]. No volatility threshold is given.

**Counter-trend or weak-market setups:** keep size small [G2gjQUJRfJM]. Limit size even on a good setup when the broad trend is down (Berger Paints example) [Ux_uuOj-gKs].

**Equity-curve feedback:** when his own recent book is doing badly, he sharply reduces size. His example was a large-cap book down 2.89% in 20 days, and he treats his own results as the best gauge of being in sync with the market [U7YrYjIS9B8]. No numeric rule is given.

**Event and context cuts**
- Before earnings, enter with about 20% of intended size, because stocks can gap 3–8% on results. Clarity is LOW; the caption wording is unclear [mim7ylyaN74].
- When the sector is unconfirmed and earnings are near, start at about 30% [NUDjIohACWs].
- When market-profile context is unsupportive (wide initial balance with price mid-range, overlapping value areas, or big selling tails), trade about one-tenth of intended size and wait for range extension [z-ae7tLVdoo]. This comes from a 13-year-old video.

**Corrections:** in rough or correcting markets he books profits, reduces size, and only buys small starters until the index recovers its structure [mR0HMssJek8]. After a 3–5-day bounce off a low, test with 10–15% of intended capital at most [20BxPDdAZAE].

### 2.4 R-multiples and the asymmetric-payoff rule

**Definitions [Wk4NVr226t8, jlpd-YpqwiQ]**
- R = entry − stop. R-multiple = P&L ÷ R.
- Price example: entry 100, stop 80, exit 140 → 2R.
- Money examples: risk 6,000 to make 2,055 → 0.34R; risk 3,800 to make 7,800 → 2.07R; risk 10,000 to make 50,000 → 5R.

**The "golden rule"**
- Losers should land between −1R and 0 [Wk4NVr226t8]; elsewhere he allows up to 1–1.5R [jlpd-YpqwiQ].
- Winners should run as far as possible; he states a target of at least 4–6R [jlpd-YpqwiQ].

**Evidence he offers:** his 20-trade example.
- Most winners were 0.34–0.52R; three exceeded 2R and one reached 8R.
- Losses ranged from −0.49R to −1.17R.
- His conclusion: a few big winners drive the result, so do not sell them early.

**What he tracks:** R-multiple, average profit, average loss, open-loss drawdown per position and holding period. He compares recent figures against his history [NYWbbvaJnPc].

**Further reading:** he recommends Van Tharp's *Trade Your Way to Financial Freedom* for sizing and scaling [_--GkDAomPk, KDSbZ0oW2U0].

**Trade location:** take risk-reward entries near a pivot or retest with a close stop. Avoid extended entries where the trending pivot is 20–25% or more away [-SC5vcQ1NuE, 4CzLWJxP4UM, Y4TewQHVhvc]. He would only day-trade an extended stock [4CzLWJxP4UM].

### 2.5 Risk of ruin [_Gy6ZltWxPw]

**Definition:** the probability of losing enough to stop trading. "Ruin" is a trader-chosen loss level, for example 50–60% of capital.

**Inputs**
- Win rate W and loss rate L.
- N, the number of risk units, defined either as account ÷ risk per trade (100,000 ÷ 5,000 = 20) or as capital ÷ maximum drawdown to date (50,000 ÷ 5,000 = 10).

**The formula**
- It is only shown on screen, not spoken.
- His numbers fit (L/W)^N:
  - 56% win rate, N = 20 → about 1%.
  - 53% win rate, N = 10 → about 30%.
  - At N = 10: 51% → 67%, 60% → 1.7%, 65% → 0.2%.
  - Drawdown version at 51%: max drawdown 5,000 → 67%; 4,000 → 61%; 500 → about 2%.

**Targets:** keep risk of ruin near zero. He says above 4% does not work long term, and later sets the target below 2%.

**Three levers**
1. Lower risk per trade. His table: 2 units → 67%, 5 → 36%, 10 → 14%, 15 → 5%, 20 → 2%, 25 → 1%.
2. Use a higher-win-rate strategy. If the win rate is below 50%, switch strategy or cut risk.
3. Use a strategy with a smaller maximum drawdown.

**Data requirement:** estimate the inputs from at least 3 years of backtest on your own strategy.

**Caveat (noted in the source):** the model treats wins and losses as equal-sized and ignores payoff ratio.

### 2.6 Stop placement as the input to sizing

Stop placement is mostly covered by the pattern chapters. The sizing-relevant parts follow.

**Structure stops, set wide enough for normal volatility**
- Major swing low for retracements [FtxgOtPYqVA].
- Pivot below the 50 DMA, or the next major pivot as a wider choice [jkga2zdA9dY].
- Most recent swing low [R6QjIoYHoFE, cQpU-EnhdSw, p03ho_Rhc_E].
- Reversal-candle extreme [_AiSzhs67J4].
- Spring or selling-climax low [K06GqbJwEv4].
- First-bottom low [IHqkSPVCxko].
- TD "true low" [Vz5lqc_RO7M].
- Ichimoku options: Senkou A, Senkou B, Kumo twist, or the low before the twist [2crnCCz4Y3s, xzR6bwNgb18].
- Market-profile value zone rather than the lowest low [uFFAAZNSozg].
- About 2% below entry at a demand zone [dV4MiNaAenI].

He repeatedly offers an aggressive (tight) and a conservative (wide) version [VqoLpEvre04, p03ho_Rhc_E, jkga2zdA9dY].

**Horizon-matched stops**
- Swing trades use the nearest pivot (example 384 on an entry of 394–396). Positional trades use the next major pivot (368) [mRAndF9wyaA].
- Day, swing and positional support zones differ (395–400 / 370–380 / 345) [jBYC0t30fz8].
- ORB day trades: stop at the session low (session high for shorts). Working professionals use a deeper, unspecified stop and hold 3–4 sessions [hk4d8AxbQ3A].

**Fixed-percentage stops**
- Cut at roughly 7–10% loss [KRoie4cj5TQ].
- O'Neil's 7% below average cost [hKnYYRpd63s]. His recovery arithmetic: a 30% loss needs about a 42% gain to recover; a 50% loss needs 100%.
- **Staged 3-5-7 stop (Roppel):** sell ⅓ at −3%, ⅓ at −5%, and the rest at −7%, for a blended loss of about 5%. He prefers it to O'Neil's flat 7% and rebuys the cut shares if price recovers above the buy point [mR0HMssJek8, rhiXs5Kh_0g, Y4TewQHVhvc].
  - His reasoning: in choppy markets a −5% loss often becomes −10%, −15% or −30% [Y4TewQHVhvc].
  - Three videos over 2 years, high clarity.

**Partial cuts at structure**
- 50% off when the selling-climax low breaks, the rest when the spring low breaks [K06GqbJwEv4].
- 50% off if price trades below the low of the wide-range buy candle; he claims about 9 in 10 winners never break that low [KRoie4cj5TQ].
- 50% off on a close back below the TD line within about 2 sessions [Vz5lqc_RO7M].
- Cut to 50%, then to 25%, as structure deteriorates [eeKRfAbbvZA]. He re-adds trimmed size above the prior high (Emami: re-add 75% above about 510–515).

**Investments:** use a review level rather than a hard stop [Q-uCkMMTh5Q, 6GqBBVt6fUs].

### 2.7 Pyramiding into a trade (price-confirmed scaling)

**Shared principle:** the stop is unchanged. A failed trade costs only the starter, and full size is committed only to trades that are confirming [C8IZozIkPJY].

**The splits vary by video**

| Video | Starter | Adds |
|---|---|---|
| [C8IZozIkPJY] | 25% at breakout | 75% after confirmation |
| [1jsLESmVLVU] | 50% at early "cheat" pivot | 50% at confirmed pivot (total risk ≤1%) |
| [U7YrYjIS9B8] | ~30% at base breakout | ~30% after pullback and re-break; ~30% on the next one |
| [JJEB-UZgK4E] | 30–50% at breakout | ~30% on pullback-resume; ~20% on confirmation (trading, not positional) |
| [Lw6h6T30VvE] | 34% | 33% / 33%, for aggressive profiles |
| [mR0HMssJek8] | ~20% (large caps) | adds on each fresh breakout; trail stop and increase size as it works |
| [uFFAAZNSozg] | ~30% when bias turns bullish without a decisive breakout | adds as the trend continues, and above the profile value-area high |

**Other statements**
- Add as price rises or on breakouts [488FDla8kuc]. Clarity is LOW.
- Add at each new base stage, cut losers fast, and sometimes trim about 50% and re-enter later [uw5QQOenJnQ].
- Leaders of a rally retrace less and form a new base, which gives a second chance to add [ywccnKeWXNo].

**Short side:** no pyramiding examples.

### 2.8 Time-staggered accumulation (SIP/STP-style)

**Method:** split capital into equal chunks and buy on a fixed schedule rather than on price confirmation. Each chunk goes in weekly (often on Fridays) or monthly [BhQ_YnaRqa0, Lw6h6T30VvE].

**Accumulation windows**

| Window | Context | Video |
|---|---|---|
| 8–12 weeks | Pulling-back high-momentum sectors | [fFUPLUEhzVo] |
| 8 / 12 / 16 weeks | Small, mid and micro caps (large caps: single entry or pyramid) | [mR0HMssJek8] |
| 16 / 32 / 48 weeks | Volatile markets; use ETFs for one-shot or pyramided bets | [B8HZvUkY5sA] |
| About 10 parts over 10–30 weeks | When "everything can fall further" | [V41BUpPK3E4] |
| 12 months, monthly/quarterly review | Weak breadth | [s1ZCPQI5894] |
| 6–12 months | After 35–40% sector run-ups with poor risk-reward | [q26J58h5Qt8] |
| About 6 months | After a sharp rally off the bottom | [KUlNy1_Rk9M] |

- In [V41BUpPK3E4] the starter can be as small as 2 shares out of an intended 100.
- In [q26J58h5Qt8] he describes risk-reward as only 1:1 to 1:1.5 and caps ETFs at 1–5% of the portfolio each.
- In [KUlNy1_Rk9M] he describes this as "horizontal, not vertical" deployment, the price of not having been systematic during the fall.

**Basket pause rule:** if the basket is down 5–7% from average cost partway through, pause installments and review. Resume only after recovery, for example from −5% back to −3% [fFUPLUEhzVo].

**Case study:** Tata Motors broke out near 1,050 and fell back toward 1,000. A staggered buyer between about 1,000 and 1,175 fared better than a lump-sum buyer [B8HZvUkY5sA]. Clarity is LOW.

**Matching method to risk profile [Lw6h6T30VvE, dERi8MUU5es]**
- Conservative: SIP or STP.
- Moderate: STP plus one scale-in.
- Aggressive: lump sum or pyramid. Aggressive traders should wait for the test portfolio and sectors to improve.

**Long-term SIP book [Q-uCkMMTh5Q]** (5-year-old video)
- Budget: 10% of monthly income, kept as a separate book, split equally across 5–8 stocks.
- Allocate more at each further 10% drop. His example buys near 1183, 1083, 1050 and 1000 total about 50,000.
- At the review level (HDFC Bank about 1000, below the 1150 breakout), if the company and trend are still sound, double the invested amount.
- Invest less when price is rising, to avoid averaging up.
- He explicitly separates this from trading, where you never average a loser. It is allowed only for 5–10-year plans in sector leaders.

### 2.9 Index-ETF deployment scaled to drawdown

**Drawdown ladders**
- Deploy more cash the deeper the fall: −5% → 5% of cash; −10% → 10%; −15% → 20%; −25% → 35%; −35% → 45%. Add again after a new base. Some captions are unclear, and he says to modify the ladder to taste [hpbDmEK-FvM].
- Below the 200 DMA, buy only index ETFs, and only after 10–20% "waterfall" drops, in tranches of 1%, 2% and 5% of capital, as a multi-year bet [yYwiSDVwgyA].
- About 2% of capital (2 lakh of 1 crore) after a 5–6% fall, with 3–5% top-ups into a Nifty ETF on sharp corrections, "never 80% at once" [rxqOUxO_vP4].
- For 4+-year investors: 5–10% of the intended position now, about 30% if the index reaches about 15% below its 200-day average. Also nibble at long-held stocks down about 20% [Sb6KTt64YKE].
- Tranches of 10%, 5%, 5%, 5% rather than 20–75% at once. Early partial buys create a cushion (example: 20–30% deployed early building about a 10% cushion) [NtpyZH5cfaE].

**Cash reserve:** about 30–35% held, deployed only on a 4–5% correction, a retest or breach of the 50 DMA, or a 200 DMA retest. More is allocated when fear is high, always into the strongest sectors [Qu49zHwEGwo].

**Horizon decides the action:** the same drawdown is a buying zone for 4+-year investors, a careful-nibble zone for 24–30-month holders, and a do-nothing zone for 6–18-month traders [Sb6KTt64YKE].

**Averaging single stocks: a contradiction**
- He warns that rupee-cost averaging into single stocks is risky, especially into the prior cycle's winners. Broad indices have historically recovered; single stocks may not [hpbDmEK-FvM].
- Yet he also advises small gradual buys in themes (defence, capital markets, IPOs, banks) as the market makes new lows, while major pivots hold [KDSbZ0oW2U0].

### 2.10 Progressive exposure and the test portfolio

**Definition [YLAIkbRSnsA]**
- Start small, build slowly, and use existing gains as the cushion to raise exposure.
- It ends with large bets in 3–5 stocks.
- Prerequisites: cut losses fast, know when to bet big and when to sit in cash, follow the trend regardless of valuation, and have screen-time intuition.
- Risks: early leaders fade, or sudden news hits. A 20% position falling 20–40% in a week is a substantial loss.
- For the less experienced: only 25–50% of capital in progressive exposure, with 50–75% in ETFs.

**Test portfolio**
- About 1–2% of equity, up to 3–5%, in high-relative-strength stocks from strong sectors during corrections. Live feedback beats screens [hKnYYRpd63s].
- Add only if it holds up despite market weakness, funding the adds from its profits and adding to names already working [dERi8MUU5es].
- Expect 2–3 stop-outs while sentiment is poor; scale up only if the test holds [ywccnKeWXNo].
- Those with a cushion sit tight; those without one wait for another pullback [bhTEw6wD_CU].
- Put more money into "stars" to concentrate and sell "dogs" [Jpu536_AmGc].

### 2.11 Concentration and diversification limits

**Position count by trading-portfolio size [C8IZozIkPJY]**

| Portfolio size | Rule |
|---|---|
| 5–15 lakh INR | Max 5 positions, large caps only |
| 15–30 lakh | 8–10 positions, large and mid caps |
| Above 50 lakh | Max 12 positions, small caps allowed |

The 30–50 lakh band is missing from the notes.

**Single-stock caps for beginners [T4849hhdwTo]**
- At most about 7–8% of the portfolio in one stock.
- 20 stocks at 5% survive a 20% gap; 5 stocks at 20% do not.
- He quotes Roppel: price can hurt you, but position size can kill you.
- Experienced members ran 9% maximums, a 15% flag trade, and one trader at 75% in one stock, which he called dangerous for beginners.

**Concentration styles [YLAIkbRSnsA]**
- 30–60 stocks: barely beats Nifty, so an ETF would do as well.
- 10–12 stocks: higher return, moderately diversified.
- 3–5 stocks: highest risk, with claimed 1–3× outperformance of Nifty if done right.

**Selectivity in poor seasons:** take only 3–5 positions from a 30–50-stock watch list [mim7ylyaN74].

**Sector limits**
- At most one trade per sector: best stock of the top sector, then best of the second sector [jlpd-YpqwiQ].
- Mix high-beta and defensive names [CXJZMbE_d5o].

**Cap-size and theme risk**
- Avoid micro caps, SME stocks and new listings in weak markets. These segments had fallen 25–45% on average [iWa7MbGawvU].
- A micro-cap index down about 9% meant typical stocks down 25–30% [JcxWhCO0hqI].
- Mid and large caps held up better [ywccnKeWXNo].
- Use reduced size in extended IPO and new-age names [rhiXs5Kh_0g].
- Over-owned themes fall hard even in rising markets, for example defence down about 20% [q26J58h5Qt8].

### 2.12 Portfolio drawdown limits, cash and profit-taking

**Drawdown limits (they vary by video)**
- Exit all positions if total open loss exceeds about 7–8%. Clarity is LOW: the caption reads "78%" [C8IZozIkPJY].
- A personal hard limit of −7%, beyond which he makes serious adjustments. He treats −7% to +7% as normal fluctuation and says each person sets their own number [DCG1GO9TGFU].
- For ETF or long-term portfolios: a −5% hard stop, then review, rather than riding a 15–20% fall [KDSbZ0oW2U0].

**Cash levels over time**
- About 38–40% cash, raised by cutting losers [KDSbZ0oW2U0].
- About 35–36% [VCNsjVuGoWQ].
- About 30–35% [Qu49zHwEGwo].
- Fully invested, with no selling during the fall, only reallocation to strength. He calls not being in the market the bigger risk for him, while noting others may wait for a further 4–5% fall. He warns that crude at 120–130 could break even strong pockets [r63sarc_qV8].

**Other rules**
- No leverage in late-cycle or correction phases [hKnYYRpd63s].
- On breadth-damaging days, cut losers but do not dump winners or buy the falling knife [S--7ta4FmbY].
- When one losing stock lags a rising portfolio, exit it and trim the weakest first [mR0HMssJek8].
- Do not dump the existing book in hard markets; be careful with new money [U7YrYjIS9B8].
- In extended markets, trim by tenure: 50–70% for holders since 2020, about 10% for recent entrants with about 20% gains. He calls this a judgement call [r11n7ztY2YY].

### 2.13 Leverage, derivatives and costs

**Leverage [zWYCYySQVNc]**
- Avoid it until you have 5–7 years of experience; he himself took about 15 years.
- His example: the same 100-point loss on a 10,000 account is 1% of equity unleveraged, 5% at 5×, and 50% at 50×.

**Options [mNHXZlKSUgo]** (undated video)
- Option buying is "safest" because maximum loss is the premium.
- Writing has capped gain and unlimited loss. He has seen expiry premiums jump from about 1 rupee to 400–500.

**Transaction costs**
- Churning costs, not strategy flaws, are a main source of losses, so he advises doing nothing short term [6K1LOJqZYEg, DU5Y5AsCMZM].
- Do not overtrade core winners that could grow 1–4× [Y4TewQHVhvc].

**Borrowing:** borrowing to trade is a serious mistake [arFNgAPisHU].

### 2.14 Capital allocation across strategies and personal finance

**Strategy splits (they differ by video)**

| Video | Split |
|---|---|
| [9dbnXEEHgsc] (8 years ago) | 10% swing / 30% positional / 60% long-term. All three seldom win in the same year. |
| [sbHzNd2iA8k] (5 years ago) | 50% long-term sector bets / 40% longer-form mid- and small-cap trading / 10% short-term. Beginners often do the reverse (about 90% short-term). |
| [6ZKLrl0z8jY] (5 years ago) | Full-timers keep 70–80% in long-term investments; he began at 50/50. Trading capital: 60% positional / 40% swing for traders with 3–4 years of consistent profit; his own start was 80/20. |
| [Y4TewQHVhvc] | Value/momentum by risk profile: conservative 80/20, moderate 60/40, aggressive 20/80. |

Overseas AI exposure: a modest 15–20% through an advisor [dpsU7JvHiMA].

**Capital needed to trade for a living [6ZKLrl0z8jY]**
- Steps: yearly expenses, plus 10%, grossed up for tax (30% in his example), divided by the assumed return.
- Worked example: 1 lakh a month → 13.2 lakh needed after tax → about 18.86 lakh pre-tax.
  - At 25% return: about 75.4 lakh.
  - At 15% return: about 1.25 crore.
  - At 2 lakh a month: about 2.5 crore at 15%, about 1.5 crore at 25%.
- **Error check:** at 75,000 a month the stated "about 94 lakh at the same return" only matches the 15% case. At 25% the arithmetic gives about 57 lakh.
- Realistic return: 20–25% a year compounded over about 5 years, needing 3–5 years of experience. Monthly bull-run returns of 15–20% are an illusion.
- Small capital cannot produce a monthly income [arFNgAPisHU].

**Emergency fund:** 12–36 months of expenses (also stated as 24–36), held outside the market in liquid ETFs or deposits [6ZKLrl0z8jY].

**Income budgets (two versions conflict)**
- 70% expenses / 10% emergency / 20% long-term investing [6ZKLrl0z8jY].
- 20% savings / 20% investment / 50% basics / 9% leisure / 1% donations / 0% debt, with savings taken first [wtWoGmPsvTY].

**Compounding illustrations [wtWoGmPsvTY]**
- Savings only: 1 lakh plus 20,000 a month at 6% for 10 years → he says 36–37 lakh. A rough recompute gives about 34–35 lakh.
- 5 lakh plus 20,000 a month for 10 years: 67–68 lakh at 15% and 87 lakh at 20%. With annual compounding these recompute to about 69 lakh and about 93 lakh.
- 50,000 a month at 15% → about 1.3 crore.
- Treat all of these as approximate.

**Other income ideas**
- With other income covering expenses, leave trading profits to compound [UVuqS0p3eLk].
- Seed a proven trader in exchange for a profit share [UVuqS0p3eLk]. Clarity is LOW.

## 3. How a program would test it

1. **Regime-scaled risk per trade.**
   - Run one breakout system three ways: (a) fixed 2% risk; (b) 0.25–0.5% when Nifty 500 is below both its 50 and 200 DMA, or fewer than 50% of constituents are above their 200 DMA, otherwise 2%; (c) a three-tier version (2% / 1–1.25% / 0.25–0.5%).
   - Compare CAGR, maximum drawdown, MAR and time-to-recover.
   - Data: daily OHLC for an index and its constituents, survivorship-free; a daily percent-above-200DMA series; signal list. [M4Z-Gi4gGag, 8QeR8FmYYg4, N5bb0Cu8RAs, SbtFCxbIB1w, -qQntPmfe-s]

2. **Staged entry versus full size at breakout, with the same stop.**
   - Compare 25% at breakout plus 75% on confirmation (a pullback that holds above the stop, then a new high) against 100% at breakout.
   - Also test 50/50 and 30/30/30 variants.
   - Measure average loss on failed trades (claimed to be about ¼ of full size), capture on winners, and return-to-drawdown.
   - Data: daily bars and a base-breakout detector. [C8IZozIkPJY, 1jsLESmVLVU, U7YrYjIS9B8, JJEB-UZgK4E]

3. **3-5-7 staged stop.**
   - On breakout entries, compare ⅓ out at −3%, ⅓ at −5% and the rest at −7%, with rebuy above entry, against a flat −7% stop, a 7–10% stop, and a structure (pivot-low) stop.
   - Split results by breadth regime.
   - Metrics: expectancy in R, maximum drawdown, whipsaw count and cost drag. [mR0HMssJek8, rhiXs5Kh_0g, Y4TewQHVhvc, KRoie4cj5TQ, hKnYYRpd63s]

4. **Portfolio circuit breaker.**
   - Compare liquidating (or halving) all positions when open-position drawdown reaches −7%, then re-entering on index reclaim of the 50 DMA, against no breaker.
   - Also test −5% and −8% thresholds.
   - Data: portfolio-level daily equity from the system in test 1. [C8IZozIkPJY, DCG1GO9TGFU, KDSbZ0oW2U0]

5. **Drawdown-ladder ETF deployment.**
   - Compare the ladder (−5% → 5% of cash, −10% → 10%, −15% → 20%, −25% → 35%, −35% → 45%) against lump sum at the first −5% and against equal monthly DCA.
   - Measure average cost and 3- and 5-year forward return across all Nifty 50/500 drawdowns since about 2000.
   - Run variant [yYwiSDVwgyA]: buy only after −10% or −20% while below the 200 DMA.
   - Data: daily index total-return series. [hpbDmEK-FvM, yYwiSDVwgyA, rxqOUxO_vP4, Sb6KTt64YKE]

6. **Time-staggered entry for small caps.**
   - Compare equal weekly tranches over 8, 12 or 16 weeks against a single buy on the breakout day.
   - Add the pause rule: stop installments at −5% to −7% from average cost and resume above −3%.
   - Measure maximum adverse excursion, final return and drawdown.
   - Data: small- and mid-cap daily bars with a breakout or relative-strength screen. [mR0HMssJek8, fFUPLUEhzVo, B8HZvUkY5sA]

7. **Risk-of-ruin formula against simulation.**
   - Compute (L/W)^N for his cases, then Monte-Carlo fixed-fractional paths with equal and with unequal payoffs.
   - Measure how often each hits a 50% ruin drawdown.
   - Purpose: check whether the formula misstates ruin for low-win-rate, high-R strategies. [_Gy6ZltWxPw]

8. **Concentration and sector caps.**
   - On identical signals, compare portfolios with: a 5% versus 20% maximum weight; one position per sector versus unlimited; 3–5, 10–12 and 30–60 holdings.
   - Metrics: return, maximum drawdown and worst single-day gap loss.
   - Data: constituents with sector tags. [T4849hhdwTo, jlpd-YpqwiQ, YLAIkbRSnsA, C8IZozIkPJY]

## 4. Transfer to TSX and US markets

**Applies as is**
- Fixed-fractional, equal-value and ATR sizing.
- R-multiples and risk-of-ruin arithmetic.
- Pyramid and staged-stop mechanics.
- Regime filters on index 50/200 DMA. Use the S&P 500 or TSX Composite.
- Breadth filters: percent of S&P 500, Nasdaq or TSX constituents above the 200 DMA.
- Portfolio drawdown breakers, position caps, one-per-sector limits, leverage cautions, and the loss/recovery arithmetic.

**Needs adapting**
- **Position-count tiers:** his tiers are set in INR lakh and Indian cap classes [C8IZozIkPJY]. Rescale to CAD/USD account sizes and local large/mid/small definitions. The TSX is narrow and sector-heavy (financials, energy, materials), so the one-per-sector rule bites hard there.
- **Volatility gauge:** replace India VIX (about 9.3 context) with VIX or VIXC, and recalibrate thresholds.
- **Turnover and costs:** his warnings reflect Indian STT and charges. US and Canadian commissions are near zero, but spreads and taxes (for example, superficial-loss and wash-sale rules) change the cost of the 3-5-7 rebuy and of churn. Re-estimate [6K1LOJqZYEg, DU5Y5AsCMZM].
- **SIP/STP:** maps to dollar-cost averaging.
- **ETFs:** US and Canadian ETFs cover more sectors than the Indian list he gives [q26J58h5Qt8].
- **Futures lot-size point:** less relevant where fractional shares exist.
- **Capital-needed formula:** works with a local tax rate in place of 30%. Liquid BeES and fixed deposits become HISA/money-market ETFs or GICs. Tax-advantaged accounts (TFSA, RRSP, IRA) change the after-tax maths.
- **Small-cap and SME warnings:** loosely analogous to the TSX Venture Exchange and US micro caps. Test separately.

**India-only**
- The specific Indian sector and theme lists: PSU, defence, railways, and the value/momentum sector picks in [Y4TewQHVhvc].
- The Indian ETF universe.
- The SME listing segment.
- Specific stock levels (Emami, HDFC Bank, ACC, Tata Motors).
- The 2025 Indian fall claims.

## 5. Gaps and doubts

**Changes in his teaching over time**
- **"Normal" risk:** 1% per trade is the norm in 5–8-year-old videos, with 2% only for experienced traders. In 1–2-year-old videos 2% is called "normal" [M4Z-Gi4gGag, 8QeR8FmYYg4, N5bb0Cu8RAs]. The baseline appears to have drifted.
- **Cash:** about 30–40% about a year ago [Qu49zHwEGwo, KDSbZ0oW2U0, VCNsjVuGoWQ] versus fully invested one month ago [r63sarc_qV8]. He frames this as personal choice.
- **Concentration:** the beginner cap of 7–8% per stock and 20-stock example [T4849hhdwTo] coexist with progressive exposure ending in 3–5 stocks [YLAIkbRSnsA]. He reconciles them only through experience level and the 25–50% capital limit.

**Contradictions in thresholds**
- **Portfolio limits:** "exit all at 7–8%" [C8IZozIkPJY], "serious adjustments at −7%" [DCG1GO9TGFU], and "−5% then review" [KDSbZ0oW2U0] are different rules. The first rests on an unclear "78%" caption.
- **Allocation splits:** 10/30/60 [9dbnXEEHgsc], 50/40/10 [sbHzNd2iA8k], 60/40 or 80/20 positional/swing [6ZKLrl0z8jY]. The budgets also differ: 70/10/20 [6ZKLrl0z8jY] against 20/20/50/9/1 [wtWoGmPsvTY].
- **Averaging down:** "never in trading" [Q-uCkMMTh5Q], and single-stock averaging is called dangerous [hpbDmEK-FvM]. Yet he advises gradual buys in themes at new market lows [KDSbZ0oW2U0] and doubling at the review level in the SIP book [Q-uCkMMTh5Q].
- **Breadth sizing:** "bare minimum" [-qQntPmfe-s] versus allowing larger size in strong pockets despite poor breadth [SbtFCxbIB1w].
- **Pre-earnings starter:** 20% [mim7ylyaN74] versus 30% [NUDjIohACWs]. The pyramid splits also vary widely (20/25/30/34/50% starters) with no rule for choosing between them.

**Undefined or thin**
- **Missing definitions:**
  - "Confirmation" for pyramid adds is rarely defined precisely.
  - "Sustains below the 50 DMA" has no day count or percent band.
  - Breadth is quantified only once (<50% above 200 DMA).
  - Volatility scaling has no threshold.
- **Equity-curve rule:** no trigger is stated [U7YrYjIS9B8].
- **Combined exposure:** he never gives a maximum total open risk (portfolio heat). The only exception is the 1% total in [1jsLESmVLVU].
- **Correlation:** not addressed beyond one-per-sector.

**Numerical problems**
- **Risk-of-ruin model:**
  - It ignores payoff size (noted in the source).
  - The "45% win-rate" table cannot come from (L/W)^N, which gives certain ruin when L > W. The figures match a 55% win rate (45% loss rate) exactly, so this is probably a labelling slip in the video or the notes.
  - The formula was shown on screen only.
- **Arithmetic slips:**
  - The 75,000-a-month capital figure (see 2.14).
  - The loose 2% stop in [dV4MiNaAenI].
  - The compounding outputs in [wtWoGmPsvTY] are only approximately reproducible.

**Thin areas**
- **Short-side sizing:** only the 1% rule and wide shorting stops. No short pyramiding, short exposure limits, or hedging guidance.
- **Unbacked performance claims:** "9 of 10 winners never break the buy-candle low" [KRoie4cj5TQ], "saved 20–25%" [hpbDmEK-FvM], "worked for 25 years" [KDSbZ0oW2U0], and 1–3× outperformance from concentration [YLAIkbRSnsA]. None comes with data.
- **Options:** risk is covered only conceptually [mNHXZlKSUgo]. Futures sizing and margin are not covered.
- **Dates:** some notes carry vague dates, and [mNHXZlKSUgo] has none, so the order of evolution is approximate.
