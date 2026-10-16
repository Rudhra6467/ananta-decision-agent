<!-- Trading Knowledge Library · Trade With Trend (Raunak A, India). Built 2026-10-16 from 158 public videos with captions (of 287 on the channel; members-only videos were not used): one structured note per video (Claude Sonnet 5.5) -> this chapter (Claude Opus 5.5), src/research/library.py. Paraphrased; the transcripts stay on the laptop. Evidence class: external teaching = hypotheses to test, never Ananta rules; nothing in the agent reads docs/library/. -->

# Risk sizing exposure

## 1. What he teaches here and how it fits

Raunak treats risk control as the part of his method that keeps a trader in the game. Stock selection, sector rotation and base structure tell him *what* to buy. This layer decides *how much*, *when to commit more*, and *when to stand aside*.

The core ideas run through the whole period covered by the notes:
- Preserve capital first, grow it second.
- Measure every trade in R, the multiple of initial risk.
- Size from a structural stop.
- Keep losers near 1R and let a few large winners carry the account.

His later teaching (roughly the last two years of videos) adds a larger layer on top:
- Exposure is set by market regime: breadth, the 50- and 200-day averages, and volatility.
- Entries are built in tranches rather than all at once. He calls this "progressive exposure", "test portfolios", "horizontal rather than vertical" deployment, and SIP/STP-style accumulation.
- Cash levels and portfolio-level loss limits govern the account as a whole.

Earlier videos teach the mechanics: fixed-fractional sizing, ATR sizing and risk of ruin. Later videos teach regime-dependent exposure. Everything below is his claim or method, a hypothesis to test, not established fact.

## 2. The ideas

### 2.1 Capital preservation, R-multiples and the asymmetric payoff

**What it is.** He states his first goal as preserving capital and only then growing it [NYWbbvaJnPc, kkJ4m9JQ4pM].

**How R is measured.**
- Initial risk R = entry minus stop.
- R-multiple = profit or loss divided by initial risk.
- Price example: entry 100, stop 80, exit 140 gives 2R [Wk4NVr226t8].
- Money example: risk 10,000 for a 50,000 gain gives 5R [jlpd-YpqwiQ].
- At position level: risking 6,000 to make 2,055 is 0.34R [Wk4NVr226t8].

**His "golden rule".**
- Keep losses between −1R and 0, or at most about 1–1.5R [Wk4NVr226t8, jlpd-YpqwiQ].
- Let winners run, with a target of 4–6R or more [jlpd-YpqwiQ].

**His sample of 20 trades** [Wk4NVr226t8]:
- Most winners were small, about 0.34–0.52R.
- Three trades exceeded 2R, and one reached 8R.
- Losses ranged from about −0.49R to −1.17R.
- His conclusion: a few big winners drive the result, so never sell them early.

**Judging trades.** He wants each trade judged by risk taken against reward expected, not by P&L or daily mark-to-market. He says P&L focus drives greed, fear and oversized F&O positions [kkJ4m9JQ4pM]. A worked Ichimoku example frames exits as about 1.5R and about 3.5R rather than price targets [59vJPo6oiNA].

**What he tracks** [NYWbbvaJnPc]:
- R-multiple, average profit and average loss.
- Per-position open-loss drawdown and holding period.
- Recent figures compared with his own history.

**Clarity.** High and consistent, but almost all from videos 5–8 years old.

### 2.2 Risk per trade and position-size formulas

**Fixed fractional (equal risk) sizing.**
- Formula: shares = (account × risk %) ÷ (entry − stop).
- Worked examples:
  - 10 lakh capital, 1% risk = 10,000; entry 280, stop 260 → 500 shares [_AiSzhs67J4, 2Yv0E57_bs4, QWcb7yxYAxk].
  - Entry 200, stop 190, risk 5,000 → 500 shares [p03ho_Rhc_E].
  - 100,000 account at 2% = 2,000; entry 780, stop 760 → 100 shares [aUgaUeCmSOQ].
- The same formula applies to a basket, using the basket's pivot as the stop [KUlNy1_Rk9M].

**Risk-per-trade levels in the older videos (2018–2021).**
- No more than 1% per trade, up to 1.5–2% with experience [jlpd-YpqwiQ, QWcb7yxYAxk, p03ho_Rhc_E, HHkcCy5LrCM].
- Beginners 0.5%, rising to 1% only after mastering the strategy [R6QjIoYHoFE, cQpU-EnhdSw, aUgaUeCmSOQ].
- 0.5% while trialling a pattern over 20 trades on one time frame [VqoLpEvre04].
- One note says total risk should never exceed 1% of the account at any time, during a two-step entry [1jsLESmVLVU].

**Three sizing models** [aUgaUeCmSOQ]:
1. **Equal value.** Account ÷ planned number of holdings. Example: 100,000 / 20 = 5,000 each. He recommends it for beginner long-term or part-time investors.
2. **Equal risk.** The formula above. He recommends it for beginner short-term traders.
3. **Volatility-based.** Shares = risk amount ÷ (2 × 14-day ATR). Example: 1,000 / 36 ≈ 28 shares. He suggests moving here as the trader advances, because high volatility deserves smaller size.

He defines the "right" size as the one that fits both the trader's temperament and the account's risk capacity [aUgaUeCmSOQ].

**Stop distance governs size.**
- Set the stop at the structure pivot before buying, and size so normal swings inside the structure do not shake you out [mim7ylyaN74].
- Wide stop means small position, and deploy only what you can tolerate losing [sIo5XQqZ0b0].

**Instrument choice.** He prefers stocks to futures for these signals, because futures lot sizes make a failed signal costly while stock quantities can be sized finely [R6QjIoYHoFE].

**Short side.** The same 1% rule applies. He accepts wide stops on shorts (the opposite end of the range a gap broke out of) because short-side volatility is high, and sizes down accordingly [HHkcCy5LrCM, LahSe1vu1kY].

**Clarity.** Very high; this is taught in about ten videos.

### 2.3 Regime-scaled exposure: breadth, moving averages, volatility

**What it is.** Risk per trade and total exposure rise and fall with market conditions.

**Risk-per-trade numbers by regime.**

| Regime | Risk per trade | Source |
|---|---|---|
| Strong bull market | about 2% | N5bb0Cu8RAs |
| Thin, volatile market | about 1–1.25% | N5bb0Cu8RAs |
| "Normal" | about 2% | M4Z-Gi4gGag, 8QeR8FmYYg4 |
| Index below 50 and 200 DMA, or index below the 50 DMA pivot or breadth poor | about 0.25–0.5% (roughly 8–15% of normal position size) | M4Z-Gi4gGag, 8QeR8FmYYg4 |

He keeps buying in weak conditions at this tiny size. His argument is that you cannot enter 100% at the bottom and must accept small losses to catch the real trend [8QeR8FmYYg4]. Being bullish, he says, is separate from committing capital [M4Z-Gi4gGag, L-PGsMh2vHw].

**Breadth.**
- Poor breadth means bare-minimum size [-qQntPmfe-s].
- Breadth should dictate sizing [Jpu536_AmGc].
- He counts breadth as poor when fewer than 50% of stocks are above their 200 DMA. Even then he allows larger size in strong-sector pockets, but warns of random pullbacks, especially when volatility is very low (India VIX about 9.3) [SbtFCxbIB1w].

**Moving averages.**
- Short- and medium-term players should stay small and inactive until the index retakes its 50- and 200-day averages [Sb6KTt64YKE].
- Traders lighten or rebalance when the index sustains below its 50 DMA. Investors brace for trouble below a falling 200 DMA. He credits these O'Neil/Weinstein-style rules with getting his community out before the 2025 fall, saving 20–25% of account size; this is an unverified claim [hpbDmEK-FvM].
- Do not buy stocks trading below their own 200 DMA. He calls this the main cause of big losses [sbHzNd2iA8k].

**Other size cuts.**
- Down-trending market: cut size even on a good setup [Ux_uuOj-gKs].
- Counter-trend trades: small size [G2gjQUJRfJM].
- Rough markets: book profits, cut size, and buy only starter positions until the index repairs [mR0HMssJek8].

**Volatility.** Size inversely to volatility: smaller as it expands, larger as it subsides. He is in no hurry to be fully invested while volatility is high [KUlNy1_Rk9M].

**Own equity curve.** When his recent book is struggling, he cuts size drastically. His example: a new large-cap book down about 2.9% in 20 days [U7YrYjIS9B8].

**Market Profile context (2013).** In an unsupportive profile (wide initial balance with price mid-range, overlapping value areas, heavy selling tails), take about one-tenth of normal size. Scale up if range extension confirms [z-ae7tLVdoo].

**Horizon matching.** The same drawdown means different things by horizon [Sb6KTt64YKE]:
- 4+ year investors: a buying zone.
- 24–30 month holders: nibble with care in stocks below the 200 DMA.
- 6–18 month traders: do nothing.

**Clarity and frequency.** High and frequent in the last two years: more than ten videos.

### 2.4 Stop placement used for sizing

The stop is structural and comes before the size. A separate chapter likely covers stops in depth; these are the anchors used for sizing.

**Swing and pivot stops.**
- Major swing low on retracement entries, because a tight stop gets hit during sideways consolidation [FtxgOtPYqVA].
- Most recent swing low [R6QjIoYHoFE, cQpU-EnhdSw, p03ho_Rhc_E].
- Pivot just below the 50 DMA, with the next major pivot as the wide option [jkga2zdA9dY].
- Nearest pivot for swing trades, next major pivot for positional trades. Example: entry 394–396, stops 384 and 368 [mRAndF9wyaA].
- Per-horizon support levels for one stock [jBYC0t30fz8].

**Pattern-specific stops.**
- Wyckoff: spring low, or selling-climax low if there is no spring. If both exist, exit 50% at the climax low and 50% at the spring low [K06GqbJwEv4].
- Ichimoku: Senkou A, Senkou B or the Kumo-twist level [2crnCCz4Y3s], or the lowest low before the twist [xzR6bwNgb18].
- Market Profile: the zone of heavy prior trading, not a single low [uFFAAZNSozg]. Low around the HVN (aggressive, triggered often) versus swing low (conservative) [p03ho_Rhc_E].
- Reversal candle low or high [_AiSzhs67J4].
- True low of the supply region [Vz5lqc_RO7M].
- First-bottom low [IHqkSPVCxko].

**Percentage and intraday stops.**
- About 2% below entry in a daily demand zone. His loose example: entry ~1530, stop ~1500, target 1800, roughly 9:1 [dV4MiNaAenI].
- ORB day trades: stop at the session low or high. A working professional uses a deeper but undefined stop and holds 3–4 sessions [hk4d8AxbQ3A].

**Long-term holdings use review levels, not hard stops** [Q-uCkMMTh5Q, 6GqBBVt6fUs].

**Location matters.**
- Enter near a defined pivot so the stop is close.
- Momentum entries after big moves have pivots 20–25%+ below, which makes stops very wide; pick one style or the other [Y4TewQHVhvc, -SC5vcQ1NuE, 4CzLWJxP4UM].

### 2.5 Percentage loss cuts and staged exits (long side)

**Staged 3-5-7 cut (credited to Jim Roppel).**
- Sell ⅓ at −3% from average cost, ⅓ at −5%, and the rest at −7%.
- He gives the blended loss as about 5%.
- He prefers it to O'Neil's flat −7%.
- He rebuys the cut shares if price recovers above the buy point.
- Sources: [mR0HMssJek8] (2 years ago), repeated for volatile markets [Y4TewQHVhvc] and as recently as 7 days ago, especially for weak breadth [rhiXs5Kh_0g].

**Flat stops.**
- O'Neil's 7% below average cost, with the recovery arithmetic: −30% needs about +42%, −50% needs +100% [hKnYYRpd63s].
- A ballpark 7–10% maximum loss [KRoie4cj5TQ].

**Partial cuts on structure breaks.**
- Buy-candle-low rule: if price trades below the low of the wide-range breakout candle, cut about 50%. He claims about 9 in 10 of his winners never break that low [KRoie4cj5TQ].
- Close back below the TD supply line within about 2 sessions: sell half and hold the rest to the true low [Vz5lqc_RO7M].
- Staged reduction as structure deteriorates: first to 50%, then to 25%, so a failure costs a quarter position [eeKRfAbbvZA].
- He trimmed 75% of Emami near his buy level and planned to re-add above about 510–515 rupees [eeKRfAbbvZA].
- He sometimes trims about half and re-enters later [uw5QQOenJnQ].

**Behavioural rules.**
- Small corrections in choppy markets tend to extend: −5% can become −10% to −30%. Cut early even if a next-day bounce makes it look foolish [Y4TewQHVhvc].
- Gaps of 4–6% can repeat after a short pause [KRoie4cj5TQ].
- On a breadth-damaging day, cut losers and tighten risk, but do not dump winners or buy the falling knife [S--7ta4FmbY, N2dUTcb9CzQ].
- Exit a laggard while the rest of the portfolio rises, and reallocate to new structures [mR0HMssJek8].

**Short side.** No staged percentage-cut rule appears for shorts in these notes.

### 2.6 Scaling into trades (pyramiding)

**What it is.** A partial first entry, then additions only as price confirms. A failed trade loses on the starter only, while the stop logic is unchanged [C8IZozIkPJY].

**Splits he has given:**

| Split | Context | Source |
|---|---|---|
| 25% at breakout, 75% after confirmation | "reverse pyramid" | C8IZozIkPJY |
| about 30% at the first bullish bias in a range, add as trend confirms, more if the profile VAH is taken out | Market Profile | uFFAAZNSozg |
| 30–50% at breakout / about 30% on pullback-and-resume / about 20% on confirmation | trading example | JJEB-UZgK4E |
| about 30% / 30% / 30% at breakout, then on each pullback-and-rebreak | — | U7YrYjIS9B8 |
| 34% / 33% / 33% | for aggressive profiles | Lw6h6T30VvE |
| 50% at the cheat pivot, 50% at the confirmed pivot | 1% total risk | 1jsLESmVLVU |
| about 20% first, add on each fresh breakout | large caps | mR0HMssJek8 |
| about 30% initially | sector unconfirmed and earnings near | NUDjIohACWs |
| about 20% (caption unclear) | before results, because of 3–8% gap risk | mim7ylyaN74 |

**Adding to winners.**
- Add on new breakouts or new base stages [488FDla8kuc (low clarity), uw5QQOenJnQ].
- Raise the trailing stop and size as the stock moves in his favour [mR0HMssJek8].

**Clarity.** The principle is consistent across about ten videos. The split percentages vary video to video, and no canonical split exists.

### 2.7 Time-staggered accumulation (SIP / STP / "systematic trading plan")

**What it is.** Buy in equal chunks on a calendar schedule rather than at price triggers. He uses it especially in volatile markets, near short-term cycle highs, and after sharp rallies off lows.

**Parameters he has given:**
- Monthly SIP or weekly STP on Fridays near a cycle peak [BhQ_YnaRqa0, Lw6h6T30VvE].
- 16, 32 or 48 weeks rather than all at the breakout. His Tata Motors example: breakout about 1,050, pullback to about 1,000. He says use ETFs if you want one-shot or pyramided bets [B8HZvUkY5sA].
- Small, mid and micro caps over 8, 12 or 16 weeks. Large caps one-shot or pyramided [mR0HMssJek8].
- Strong sectors that are pulling back: 8–12 weekly instalments [fFUPLUEhzVo]. Basket rule from the same video:
  - Pause instalments if the basket is 5–7% below average cost.
  - Resume only on recovery, for example back to −3%.
  - 7% is the basket stop.
- Poor breadth: spread a sector allocation over 12 months, reviewed monthly or quarterly [s1ZCPQI5894].
- Single stocks staggered over 6–12 months when reward to risk is only about 1:1–1:1.5. Sector ETFs at 1–5% of the portfolio each [q26J58h5Qt8].
- When "everything can fall further": about 10 parts over 10–30 weeks, or a starter of about 2% of intended size [V41BUpPK3E4].
- After a sharp rise from a bottom: spread over about 6 months, for example 10 lakh [KUlNy1_Rk9M].
- After a 3–5 day bounce: do not commit heavily. Test with 10–15% of intended capital [20BxPDdAZAE].
- General statements of the same idea [Pm_1kb8Fku0, L-PGsMh2vHw, YVGWKmpHStM, g3mcqf6rqoc, U7YrYjIS9B8, yYwiSDVwgyA].

**Long-term SIP book with price-triggered extras** [Q-uCkMMTh5Q]:
- Budget about 10% of monthly income across 5–8 stocks, kept separate from his trading books.
- Add more at each 10% decline. His HDFC Bank example: buys at about 1183, 1083, 1050 and 1000, totalling about 50,000.
- At the review level, if the company and trend are intact, double the amount invested so far.
- Invest less as price rises.
- He separates this explicitly from averaging down in trading, which he forbids.

### 2.8 Drawdown-scaled buying in index and sector ETFs

**Template** [hpbDmEK-FvM]: deploy more of the available cash the deeper the fall, then add after a new base. He says to modify it to risk appetite, and some captions are unclear.

| Index fall | Cash deployed |
|---|---|
| −5% | 5% |
| −10% | 10% |
| −15% | 20% |
| −25% | 35% |
| −35% | 45% |

**Other parameters:**
- Below the 200 DMA: index ETFs only, only after 10–20% waterfall drops, in tranches of 1%, 2% or 5% of capital, as a multi-year bet. No bottom-fishing in single stocks [yYwiSDVwgyA].
- About 2% of capital after a 5–6% fall, and 3–5% into a Nifty ETF on sharp corrections. "Never 80% at once" [rxqOUxO_vP4].
- Example tranches of 10%, then 5%, 5%, 5% rather than a single 20–75% bet [NtpyZH5cfaE].
- Long-term (4+ year) investors: 5–10% of the intended position now, about 30% if the index reaches about 15% below its 200 DMA. Nibble at long-held stocks that are down about 20% [Sb6KTt64YKE].
- Cash reserve of about 30–35%, deployed on a 4–5% correction, a 50 DMA retest or breach, or a 200 DMA retest, into the strongest sectors [Qu49zHwEGwo].

**When not to use it.** Rupee-cost averaging is for broad index ETFs, not individual stocks. He cites O'Neil: winners of the last cycle rarely lead the next, so averaging into 2020–24 winners is dangerous [hpbDmEK-FvM].

### 2.9 Progressive exposure and the test portfolio

**Definition.** Start small, build slowly, and use existing gains as a cushion to raise exposure. It ends in large bets on 3–5 stocks [YLAIkbRSnsA].

**Concentration choices** [YLAIkbRSnsA]:
- 30–60 stocks: roughly index-like returns, so an ETF would serve.
- 10–12 stocks: higher returns.
- 3–5 stocks: highest risk, with a claimed 1x–3x outperformance of Nifty if done right.

**Middle path.** Less experienced traders should put only 25–50% of capital into progressive exposure and the rest into ETFs [YLAIkbRSnsA].

**Prerequisites he lists** [YLAIkbRSnsA]:
- Cutting losses fast.
- Knowing when to bet big and when to sit in cash.
- Following the trend regardless of valuation.
- Intuition from screen time and losses.

**Risks he names** [YLAIkbRSnsA]: early leaders fading, and news shocks. Example: a 20% position falling 20–40% in a week.

**Test portfolio mechanics.**
- About 1–2% of equity (up to 3–5%) in high-RS stocks from strong sectors during corrections, because live exposure gives better feedback than screens [hKnYYRpd63s].
- Add only if the test holds up while the market is weak, funding adds from its profits [dERi8MUU5es].
- Lump-sum or pyramid traders wait until the test portfolio and sectors improve [dERi8MUU5es].
- Expect 2–3 stop-outs while sentiment is poor [ywccnKeWXNo].
- Early partial buying (e.g. 20–30% of the account) builds a cushion of about 10% that lets you hold through, and add on, the later pullback [NtpyZH5cfaE].
- With a cushion, sit tight. Without one, wait for a pullback [bhTEw6wD_CU].
- Move money toward "stars" and sell "dogs" (growth/share matrix) [Jpu536_AmGc].

### 2.10 Cash levels and total exposure

**Stated cash levels** (how his own exposure changed over time):
- About 30–35% [Qu49zHwEGwo].
- 38–40%, raised by cutting losers during pullbacks [KDSbZ0oW2U0].
- 35–36% [VCNsjVuGoWQ].
- Three weeks ago: fully invested. He sold nothing in the fall and only rotated into strength. For him, not being in the market is the bigger risk. The alternative for others is to wait for a further 4–5% fall, and he warns crude at 120–130 could hit even strong pockets [r63sarc_qV8].

**Other exposure rules:**
- Nibble on dips with stops [0nbQs92kYuY].
- Stay nimble through position management rather than avoid the market [LWoEC9OjajE].
- Partial profit-taking in extended markets, sized by tenure: about 50–70% for those invested since 2020, about 10% for recent entrants with about 20% gains [r11n7ztY2YY].
- Do not churn core winners on noise; confine frequent trading to swing positions [Y4TewQHVhvc].
- Excess churning loses money through costs more than through bad strategy [6K1LOJqZYEg].

### 2.11 Concentration and diversification limits

**Positions by trading-capital size** [C8IZozIkPJY]:

| Trading capital | Positions | Allowed caps |
|---|---|---|
| 5–15 lakh | at most 5 | large caps only |
| 15–30 lakh | 8–10 | large and mid caps |
| over 50 lakh | at most 12 | small caps allowed |

**Single-position limits.**
- Beginners: at most about 7–8% in one stock. 20 stocks at 5% survive a 20% gap; 5 at 20% do not. Roppel: price can hurt, size can kill [T4849hhdwTo].
- Experienced members ran 9% caps, 15%, and one at 75%, which he calls dangerous [T4849hhdwTo].

**Sector and style limits.**
- At most one trade per sector: best trade from the top sector, the next from the second sector [jlpd-YpqwiQ].
- Blend high-beta with defensive names (IT, pharma, consumption) [CXJZMbE_d5o].
- Overseas AI exposure: a modest 15–20%, via an advisor [dpsU7JvHiMA].

**Cap-size and theme risk.**
- Avoid micro caps, SME stocks and new listings in weak markets. These corrected 25–45% on average [iWa7MbGawvU].
- Small/micro index drawdowns understate stock pain: index about −9%, typical stocks −25–30% [JcxWhCO0hqI].
- Rotate toward mid and large caps in uncertainty (citing Druckenmiller) [ywccnKeWXNo].
- Reduced size in extended IPO/new-age names [rhiXs5Kh_0g].
- Crowded themes fall hard even in rising markets, e.g. defence about −20% [q26J58h5Qt8].

### 2.12 Portfolio-level drawdown limits

- If total open loss reaches about 7–8%, exit all positions. The caption reads "78%"; 7–8% is the likely reading [C8IZozIkPJY].
- Personal −7% portfolio drawdown triggers serious adjustment. He sees −7% to +7% as the normal range, and each trader must set their own number. Sitting at −50–60% with no action is not what he means [DCG1GO9TGFU].
- ETF or long-term portfolio: review at about −5% rather than ride a 15–20% fall [KDSbZ0oW2U0].
- Sector basket: pause instalments at −5 to −7% [fFUPLUEhzVo].
- Decide square-off thresholds in advance; that removes fear of event risk [SuYHqw5zA8U].
- Drawdown means open loss on a position. Beginners mishandle it by doubling down or panic-exiting valid trends [JJEB-UZgK4E].
- Newcomers who have never seen a 20–25% monthly fall lack drawdown experience [6fowSBDs3eY].
- If many picks from a prior cycle are losing, he blames sizing and scaling. He points to Van Tharp for the remedy [KDSbZ0oW2U0, _--GkDAomPk].

### 2.13 Risk of ruin [_Gy6ZltWxPw]

**Definitions.**
- Ruin is a trader-chosen loss level, e.g. 50–60% of capital, not 100%.
- N, the number of risk units, is either account ÷ risk per trade (100,000/5,000 = 20) or capital ÷ max drawdown to date.

**Formula.** It is shown only on screen. His figures match the standard gambler's-ruin form ((1 − e)/(1 + e))^N, where e = win rate − loss rate. A check:

| Win rate | N | Formula gives | He states |
|---|---|---|---|
| 56% | 20 | about 0.8% | about 1% |
| 53% | 10 | about 30% | about 30% |
| 51% | 10 | about 67% | about 67% |
| 60% | 10 | 1.7% | 1.7% |
| 65% | 10 | 0.2% | 0.2% |

**Limits.** Keep risk of ruin under 2%; above 4% "does not work long term".

**Three levers:**
1. Lower risk per trade, which raises N.
2. Use a higher win-rate strategy. Below 50% is a red flag.
3. Use a smaller max drawdown.

**Supporting data.** Estimate inputs from at least 3 years of your own backtest.

**Caveat (from the notes).** The model treats wins and losses as equal size. It ignores payoff ratio, so his preferred low-hit-rate, big-winner style is mis-described by it.

### 2.14 Leverage, gaps and event risk

- **Leverage arithmetic** [zWYCYySQVNc]:
  - No leverage until about 5–7 years of experience; he himself took about 15 years.
  - A 100-point loss on a 10,000 account costs 1% unleveraged, 5% at 5x and 50% at 50x.
- Oversized or levered positions can lose 10–30% of an account in one gap session [aUgaUeCmSOQ].
- No leverage in late-cycle or correction phases [hKnYYRpd63s].
- Leverage and refusing to take losses ruin accounts; quick cuts rarely do [Y4TewQHVhvc].
- Reduced pre-earnings size [mim7ylyaN74, NUDjIohACWs].

### 2.15 Capital allocation across strategies and life

**His splits at different times:**

| Source | Split |
|---|---|
| 8 years ago [9dbnXEEHgsc] | 10% swing / 30% positional / 60% long-term. Beginners should split because all three rarely win in the same year. |
| 5 years ago [sbHzNd2iA8k] | 50% long-term sector bets / 40% longer-form mid and small caps / 10% swing. Retail often does the reverse, about 90% short-term. |
| 5 years ago [6ZKLrl0z8jY] | Full-time traders keep about 70–80% in long-term investments; trading is for income. He started at about 50/50. Within trading capital, about 60% positional / 40% swing once a trader has 3–4 profitable years across cycles; his own start was 80/20. |
| [Y4TewQHVhvc] | Value/momentum by risk profile: conservative 80/20, moderate 60/40, aggressive 20/80. |

**Capital needed to trade for a living** [6ZKLrl0z8jY]:
- Method: yearly expenses + 10% buffer, grossed up for tax, ÷ assumed return.
- Example: 1 lakh/month → 13.2 lakh → about 18.86 lakh pre-tax at 30% tax → about 75.4 lakh at 25%, or about 1.25 crore at 15%.
- 2 lakh/month → about 2.5 crore at 15%, about 1.5 crore at 25%.
- 75,000/month → about 94 lakh. The notes say "at the same return", but the arithmetic fits 15%.
- He calls 20–25% compounded a year over 5 years realistic for a good trader with 3–5 years' experience. Monthly 15–20% runs are an illusion.

**Personal-finance rules:**
- Emergency fund of 12–36 months of expenses, held in liquid ETFs or deposits [6ZKLrl0z8jY].
- Income splits: 70/10/20 [6ZKLrl0z8jY], or 20% save / 20% invest / 50% expenses / 9% leisure / 1% donations / 0% debt [wtWoGmPsvTY].
- No borrowing to trade [arFNgAPisHU].
- Small capital cannot produce a monthly income [arFNgAPisHU].
- Let profits compound if other income covers expenses [UVuqS0p3eLk].

## 3. How a program would test it

**1. Regime-scaled risk per trade** [M4Z-Gi4gGag, 8QeR8FmYYg4, N5bb0Cu8RAs, SbtFCxbIB1w, -qQntPmfe-s]
- Setup: one breakout entry rule, fixed-fractional sizing.
- Variant A: constant 2% risk.
- Variant B: 2% when the index is above both its 50 and 200 DMA *and* at least 50% of constituents are above their 200 DMA; otherwise 0.375% (midpoint of 0.25–0.5%).
- Optional Variant C: an intermediate 1–1.25% band for "thin" markets.
- Compare CAGR, max drawdown, MAR and Ulcer index.
- Data: daily OHLCV for the index constituents with survivorship-free membership, index closes, and a computed breadth series.

**2. Staged entry vs full entry** [C8IZozIkPJY, JJEB-UZgK4E, U7YrYjIS9B8, Lw6h6T30VvE]
- Same breakout signals and the same initial structural stop.
- Variants:
  - (a) 100% at breakout.
  - (b) 25% at breakout, 75% on the first pullback that holds above the stop and then makes a new closing high.
  - (c) 30/30/30 at the breakout and each subsequent pullback-and-rebreak.
- Metrics: average loss on failed trades in R of full size, capture of winners, return/drawdown.
- Data: daily OHLCV.

**3. Staged 3-5-7 stop vs flat 7% stop** [mR0HMssJek8, Y4TewQHVhvc, rhiXs5Kh_0g, hKnYYRpd63s]
- Positions: breakout longs.
- Variant (a): sell ⅓ at −3%, ⅓ at −5% and the rest at −7% from average cost, with and without re-buying cut shares on a close above the buy point.
- Variant (b): single −7% stop.
- Split results by breadth regime, since he claims the staged rule matters most in weak breadth.
- Data: daily OHLC. Intraday data would improve fill realism.

**4. Portfolio-level drawdown circuit breaker** [C8IZozIkPJY, DCG1GO9TGFU, KDSbZ0oW2U0]
- Run a 5–12 position swing portfolio.
- Variants: (a) exit everything when open loss reaches 7%; (b) halve exposure at −7% from equity peak; (c) review at −5%; (d) no breaker.
- The re-entry rule must be specified. For example, resume when the index reclaims its 50 DMA, because he gives no re-entry condition.
- Metrics: max drawdown, return, time out of market.

**5. Drawdown-scaled ETF deployment** [hpbDmEK-FvM, yYwiSDVwgyA, rxqOUxO_vP4]
- Hold a cash pool.
- Deploy 5/10/20/35/45% of remaining cash at −5/−10/−15/−25/−35% from the index high.
- Compare with lump sum at −5%, and with equal monthly SIP from the high.
- Measure average cost and 3- and 5-year forward returns.
- Data: long index or ETF price history including several bear markets.

**6. Time-staggered accumulation in small caps** [B8HZvUkY5sA, mR0HMssJek8, fFUPLUEhzVo]
- Universe: small and mid-cap breakouts.
- Variants: equal weekly tranches over 8, 12 and 16 weeks, with the 5–7% basket pause rule; versus a single entry at the breakout.
- Metrics: max adverse excursion, return, drawdown.

**7. Risk-of-ruin formula vs simulation** [_Gy6ZltWxPw]
- Monte Carlo on his payoff profile: win rate about 35–45%, small winners plus a fat right tail, as in [Wk4NVr226t8].
- Compare simulated probability of hitting a 50% drawdown with the gambler's-ruin estimate.
- Repeat across risk per trade from 0.25% to 5%.

**8. Concentration caps** [T4849hhdwTo, jlpd-YpqwiQ, YLAIkbRSnsA]
- Same signals under three portfolio rules:
  - Max 5–8% per name with one position per sector.
  - Max 15–20% per name.
  - Progressive concentration into the top 3–5 winners.
- Compare drawdown, worst single-day loss from gaps, and excess return over the index.

## 4. Transfer to TSX and US markets

**Applies as is:**
- R-multiples and fixed-fractional, equal-value and ATR sizing.
- Risk-of-ruin arithmetic.
- Staged entries and exits, including 3-5-7 and partial cuts at structure breaks.
- Regime filters using the 50/200 DMA and percent-of-stocks-above-200-DMA. These are O'Neil/Weinstein ideas of US origin.
- Portfolio drawdown breakers.
- Leverage arithmetic and earnings gap-risk sizing.
- Staggered dollar-cost averaging into broad index ETFs (XIU/XIC, SPY/VTI).

**Needs adapting:**
- **Thresholds in lakh.** Position counts by account size [C8IZozIkPJY] and capital-needed examples must be rebased to CAD or USD and to local living costs.
- **Volatility gauge.** India VIX readings, e.g. about 9.3 as "very low", do not map directly to VIX or VIXC levels.
- **Cap tiers.** TSX small and micro caps are thinner and more resource-heavy. His "avoid micro/SME and new listings" and cap-based stagger windows need local liquidity cut-offs.
- **Sector rules.** The TSX is concentrated in financials, energy and materials, so "one trade per sector" bites harder there than on Nifty 500. The US has the breadth of sectors his rule assumes.
- **Sector ETFs.** Plentiful in the US. In Canada, coverage is limited and some sleeves would need US-listed ETFs, with currency exposure.
- **Costs.** He says Indian churn is cost-driven [6K1LOJqZYEg]. US commissions are near zero, but spreads and short-term capital gains tax matter. Canadian trading in TFSAs and RRSPs changes after-tax math, and frequent trading can be treated as business income.
- **Tax rate.** The 30% in the capital-needed formula must change.
- **Short side.** Uptick, borrow and margin rules differ.

**India-only:**
- SIP and STP as product labels (the concept is ordinary DCA).
- Liquid BeES and Indian deposit instruments.
- SME-segment stocks.
- F&O lot-size reasoning [R6QjIoYHoFE].
- The specific Indian ETF list and gaps such as no defence ETF [q26J58h5Qt8].
- Stock-specific levels: Emami, ACC, HDFC Bank, Tata Motors, Reliance.
- Indian sector lists in the value/momentum split [Y4TewQHVhvc].

## 5. Gaps and doubts

**Risk-per-trade drift.** Older videos cap risk at 1% (0.5% for beginners, 2% "or more" once experienced). Recent videos call 2% normal and cut to 0.25–0.5% in weak markets. It is not clear whether 2% is for him personally or a general recommendation, or whether it applies per trade or per full pyramided position.

**Total open risk ("heat") is not defined.** Only [1jsLESmVLVU] says total risk should never exceed 1%. It is unclear whether that means the whole account or one position's two tranches. Nothing explains how adds in a pyramid relate to the 1–2% per-trade budget.

**Caption problems:**
- "78%" portfolio stop, almost certainly 7–8% [C8IZozIkPJY].
- Pre-results size "about 20%", wording unclear [mim7ylyaN74].
- ETF deployment percentages partly unclear [hpbDmEK-FvM].
- The risk-of-ruin table labelled "45% win rate" cannot come from his own formula, which gives certain ruin for a negative edge. The figures (67/36/14/5/2/1%) match a **55%** win rate exactly, so 45% is probably the loss rate or a mis-transcription [_Gy6ZltWxPw].

**Compounding examples need recomputing** [wtWoGmPsvTY]. Monthly compounding of 1 lakh plus 20,000 a month at 6% for 10 years gives roughly 34–35 lakh, not 36–37. The 15% case (about 67–68 lakh) is closer to annual compounding. These are his illustrations, not rules.

**Contradictions:**
- **Allocation splits.** 10/30/60 [9dbnXEEHgsc], 50/40/10 [sbHzNd2iA8k] and 70–80% investing with a 60/40 trading split [6ZKLrl0z8jY] are not consistent with each other.
- **Averaging into stocks.**
  - He doubles a long-term stock position at the review level and buys more on each 10% fall [Q-uCkMMTh5Q].
  - He rupee-cost-averages into themes including IPO stocks [KDSbZ0oW2U0].
  - Yet he warns that averaging individual stocks is dangerous [hpbDmEK-FvM] and says to avoid new listings [iWa7MbGawvU].
  - The stated reconciliation (sector leaders, 5–10 year horizon, pivots intact) is only partly spelled out.
- **Concentration.** At most 12 stocks and 7–8% per name for beginners [C8IZozIkPJY, T4849hhdwTo] versus a progressive-exposure end state of 3–5 stocks [YLAIkbRSnsA]. He frames it as experience-dependent, with no transition criteria.
- **Cash stance.** 30–40% cash a year ago versus fully invested three weeks ago [r63sarc_qV8]. He presents this as personal choice, not a rule change.
- **Beginner sizing model.** Equal value for long-term beginners [aUgaUeCmSOQ] versus equal risk everywhere else.

**Vague triggers:**
- "Bare minimum" size, "small" size, "test portfolio holds up", "market stability", and "drastically reduce" after an equity-curve dip have no numbers.
- Only [SbtFCxbIB1w] gives a breadth cutoff: below 50% of stocks above their 200 DMA.

**Thin on the short side.** Only the 1% rule and wide-stop advice apply. There is no short pyramiding, short staged stop, or short exposure limit.

**Unverified claims:**
- 9 in 10 winners never break the buy-candle low.
- 20–25% of account saved in 2025 by the DMA rules.
- 1x–3x outperformance from concentration.
- 20–25% CAGR as realistic.
- "Worked for 25 years" for rupee-cost averaging.
- The ruin model ignores payoff ratio, which is central to his own big-winner style.

**Not covered in these notes:**
- Correlation between positions beyond the one-per-sector rule.
- Kelly or optimal-f sizing.
- Currency risk.
- How to size options.
- Explicit re-entry rules after a portfolio-level stop.
