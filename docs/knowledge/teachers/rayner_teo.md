<!-- Coverage update 2026-10-03: a second pass read 146 of his most-viewed and strategy videos (one method card each, kept on
the laptop in ~/ananta_runs/channels/cards). It added the 1-ATR stop buffer, build-up rules (80+ candle range, 20 MA touching the
build-up, stop 1 ATR below it), first pullback, trend strength by moving average (strong 20 / healthy 50 / weak 200), stacked
levels across timeframes (4-6x factor), chandelier trailing (3x medium, 5-6x long term), and the weekly 50/40-week Donchian system.
Madhav's summary: Rayner gives the execution structure: structure -> location -> trigger -> exit. -->
<!-- Generated 2026-10-03 by src/research/teachers.py from 30 public TradingwithRayner videos (automatic captions ->
Claude Haiku notes per video -> Claude Sonnet merge). Paraphrased; [ids] are YouTube video ids. Spot-checked against the
transcripts for the mean-reversion system (2.5 SD, 3% limit, RSI(2) > 50, 10 days). Claims are his, not verified by us.
Evidence class: external teaching (hypotheses for the repair shop, never rules Ananta trades on). -->

# Rayner Teo (TradingwithRayner): Rulebook

Source: 30 video notes (newest first). Two clearly distinct bodies of teaching exist: (A) **systematic, backtested, fully codable systems** (2024-2025 era videos) and (B) **discretionary price action** (older videos, mostly forex/stocks/crypto, partly codable). The notes do not carry dates, but ordering suggests the systematic emphasis is newer. Some of the systematic videos dated older in the list (e.g., the 88.89% RSI pullback, HnNBOReTb8g turtle upgrade) show he has used simple rule-based systems for a while. Where the two bodies conflict, I flag it.

---

## 1. How he thinks

- **Edge comes from tested rules, not eyeballing.** Discretionary chart reading is called "discretionary trading, not systematic"; backtested rules are the preferred route [DS8_-LP59pw, pGO9MwMCJKo, 7D32Zvmt-6Q].
- **Profitability = expectancy, not win rate.** A 40-45% win rate system can beat an 80% one if payoff is large enough. Mean reversion (66% wins, small wins/losses) and trend following (45% wins, big winners) are both shown as positive-expectancy [hsYw6Z1nqgw, ggnIGZiDoFY, 7D32Zvmt-6Q].
- **Run several uncorrelated systems.** Mean reversion + momentum + trend following smooth returns and reduce losing years; 50/50 mean reversion + momentum had one losing year (2022, -2.4%) over 25 years [7D32Zvmt-6Q, Ew05en-HlDs, VDvAP-QuGTY].
- **Trade many markets for trend following.** Diversification across currencies, metals, bonds, indices, commodities is "key" to catching trends [ggnIGZiDoFY, pGO9MwMCJKo, HnNBOReTb8g].
- **Trend filter first, trigger second.** 200-day MA gates mean reversion, momentum, and the S&P pullback; discretionary work starts by identifying trend/stage [NheeZ94_Ajk, XFTL5m5EbUY, W8ENIXvcGlQ, eddj9v1CfA4].
- **Stops are placed at a logical structural level plus a volatility buffer (usually 1 ATR(20))**, never at the exact swing point [wmjLoLQjXZc, Tb1CLQuJOsE, 1ohBdvp8CoU, RG4qEMp2XcU].
- **Size inversely to stop distance; dollar risk constant** [hsYw6Z1nqgw, 1ohBdvp8CoU].
- **Accept drawdowns in advance.** Prepare mentally for 30-40% (even 40-60% for trend following) [Ew05en-HlDs, ggnIGZiDoFY].
- **Automate execution** where possible; 2025 results came from a fully automated setup [Ew05en-HlDs].
- **Trade with the higher-timeframe trend; if structure is unclear, go up a timeframe, and if still unclear, skip the trade** [8hM18AHcUCs, Dnh1uya1QAg, eddj9v1CfA4].

---

## 2. Market regime

He gives no breadth, VIX or follow-day rules. Regime guidance is by system:

| System | Works best | Struggles |
|---|---|---|
| Trend following (200-day breakout) | Crises/recessions (2000 +22%, 2008 +65%, 2020 +8%, 2022 +56%); low correlation to stocks [ggnIGZiDoFY, pGO9MwMCJKo] | Choppy, range-bound, low-volatility markets; drawdown phases [7D32Zvmt-6Q, pGO9MwMCJKo] |
| Mean reversion (BB pullback) | Choppy or mildly bullish markets with pullbacks [NheeZ94_Ajk, DS8_-LP59pw] | Strong bear markets (few stocks above 200-day MA), parabolic bull markets (no pullbacks), sudden crashes [NheeZ94_Ajk, 7D32Zvmt-6Q] |
| Momentum ETF | All regimes by rotation into strongest asset; can hold bonds/gold in downturns [XFTL5m5EbUY] | Not explicitly stated; 2022 was -3% |

Other regime rules:
- **Index filter for the S&P RSI pullback:** trade only when S&P 500 is above its 200-day MA; otherwise stay in cash [W8ENIXvcGlQ].
- **Bias long in US equities;** avoid shorting uptrending markets [W8ENIXvcGlQ, wID26sF338Q].
- **Discretionary stage framework:** advancing (buy only), declining (short only), accumulation/distribution (wait for the break) [eddj9v1CfA4].
- **Sentiment/seasonality (soft):** beware extreme bullish or bearish sentiment; seasonality is optional confirmation, never a standalone trigger [VDvAP-QuGTY].
- **Deploy a new system during its drawdown, not after a hot streak** [ZmENOfdMrus] (no quantified definition of "drawdown phase").

---

## 3. What to trade

- **Mean reversion:** Russell 1000 stocks (liquidity filter); rank multiple candidates by 150-day rate of change, strongest first [NheeZ94_Ajk, ybigcO913kc, DS8_-LP59pw].
- **Momentum:** four ETFs: GLD, SPY, TLT, DBC [XFTL5m5EbUY].
- **Trend following:** 40-50+ futures markets across currencies, metals (gold, silver, copper), bonds, indices, energy, soft commodities/agriculture [ggnIGZiDoFY, HnNBOReTb8g, pGO9MwMCJKo].
- **S&P pullback:** S&P 500 index/ETF/futures; extensible to Russell 1000/3000, Nasdaq, single stocks for more trades (S&P alone gave only ~36 trades in 14 years) [W8ENIXvcGlQ].
- **Discretionary breakout stocks:** Russell 1000, above 200-day SMA, 200-day ROC greater than the S&P's; avoid illiquid/pump-and-dump names [wID26sF338Q].
- **Relative strength between similar markets:** prefer the one above (or farthest above) its 50 MA [cSWC2WwbhHE].
- **Discretionary price action:** any liquid market with a visible trend and clean support/resistance [Tb1CLQuJOsE, wmjLoLQjXZc].
- No fundamental/sector screens were taught in these notes.

---

## 4. Setups

### 4.1 Bollinger Band pullback (mean reversion, Russell 1000) [NheeZ94_Ajk, ybigcO913kc, DS8_-LP59pw, 7D32Zvmt-6Q]
- **What:** buy oversold dips in uptrending large caps.
- **Context:** close above 200-day SMA (EMA/WMA "acceptable"); close below lower Bollinger Band (20-day, **2.5 SD, not the standard 2.0**). Avoid stocks down 40-50% from highs (downtrend, not pullback) [DS8_-LP59pw].
- **Entry:** next day, buy limit at 0.97 x prior close (3% below).
- **Stop:** no price stop; time stop at 10 trading days.
- **Exit:** sell at next open after the 2-day RSI closes above 50 (~80-90% of trades), else sell at open after day 10.
- **Sizing:** 20% of capital per stock, max 5 positions, no leverage.
- **Ranking:** if more signals than slots, take highest 150-day ROC.
- **Avoid:** strong bear, parabolic bull, crash conditions.
- **Codable:** YES. Parameters: SMA 200; BB(20, 2.5); limit 3%; RSI(2) > 50; max hold 10; 20% x 5; rank = 150d ROC.
- **Note:** win rate 66%; avg win 4.1%, avg loss 4.7%; payoff below 1 [ybigcO913kc, hsYw6Z1nqgw].

### 4.2 Momentum ETF rotation (monthly) [XFTL5m5EbUY, 7D32Zvmt-6Q]
- **Context:** first trading day of each month; ETF must be above its 200-day MA.
- **Entry:** rank GLD, SPY, TLT, DBC by 12-month ROC; buy top two that qualify.
- **Exit:** sell if it drops out of the top two or falls below the 200-day MA (the notes describe the MA check as the stop but evaluated at rebalance; intramonth monitoring is unclear).
- **Sizing:** 50% each, max 2 positions. If fewer than two qualify, the notes don't say explicitly; cash is implied.
- **Codable:** YES. Parameters: 200d MA; ROC 12m; monthly rebalance; 2 x 50%.

### 4.3 200-day breakout trend following (long and short) [ggnIGZiDoFY, pGO9MwMCJKo, 7D32Zvmt-6Q]
- **Context:** daily close = highest close of last 200 days (long) or lowest (short). No other filter.
- **Entry:** next day open.
- **Stop/exit:** Chandelier trailing stop at 6 x ATR (20); exit at next open after a daily close beyond the stop line. No profit target.
- **Sizing:** risk 2% of account per trade; shares = 2% x equity / stop distance. Actual loss may reach 2.2-2.5% on gaps.
- **Avoid:** choppy/range markets, low volatility, intraday signals.
- **Codable:** YES. Parameters: lookback 200 (closes); ATR period 20; multiple 6; risk 2%.

### 4.4 Enhanced Turtle breakout [HnNBOReTb8g]
- **Entry:** next open after breaking 200-day high (Donchian) / low.
- **Stop:** initial 2 x ATR; **exit** trailing on 10-day low (long) / high (short), executed next open.
- **Sizing:** 1% risk; size = (equity x 0.01) / (2 x ATR in dollars).
- **Universe:** 40-50+ futures markets.
- **Codable:** YES. ATR period not stated in this video.
- **Disagreement:** this and 4.3 are both 200-day breakout systems but differ in stop (2 ATR + 10-day-low trail vs 6 ATR chandelier) and risk (1% vs 2%). Both are presented as profitable (32%/yr with 41% DD vs 14%/yr with 37% DD); different backtest periods and universes, so not directly comparable. Original turtle (20-day, 2%) is shown as unprofitable.

### 4.5 S&P 500 RSI pullback [W8ENIXvcGlQ]
- **Context:** index above 200-day MA.
- **Entry:** next open after 10-period RSI closes below 30.
- **Exit:** next open after RSI(10) crosses above 40, or after 10 trading days.
- **Sizing/stop:** not specified; time stop is the risk control.
- **Codable:** YES. Claimed 88.89% win rate, 36 trades, avg +1.43% / -0.87%.

### 4.6 Breakout after tight consolidation (stocks) [wID26sF338Q, eJOvSqcp_Jw, xTd6nlbcIZc]
- **Context:** Russell 1000; above 200 SMA; 200-day ROC > S&P's; tight consolidation near highs with higher lows into resistance. Consolidation should be long (120+ daily bars for reversal setups; ~88 acceptable in continuation) [eJOvSqcp_Jw]; avoid breakouts after parabolic, large-candle moves; confirm contraction via ATR/MACD histogram [xTd6nlbcIZc].
- **Entry:** bullish close above resistance (or gap up); enter next open.
- **Stop:** below consolidation lows / swing low; ~1 ATR below breakout candle or prior low.
- **Exits:** Fib 2.0 extension (swing); close below 20 MA (short-term), 50 MA (medium), or prior swing low; percentage trail 20-30% mentioned [eJOvSqcp_Jw].
- **Sizing:** not specified.
- **Codable:** PARTLY (consolidation tightness, "higher lows" need definitions).

### 4.7 Pullback to area of value in trend (discretionary core) [RG4qEMp2XcU, Tb1CLQuJOsE, jIqtzTnfNHY, 4MPR-7bickE, 8hM18AHcUCs]
- **Context:** clear trend (HH/HL or LH/LL); price at support (prior resistance turned support is best) or a trend-strength-matched MA: 20 MA for strong, 50 for healthy, 200 for weak trends [4MPR-7bickE]. Uptrend is invalid if price closes below the swing low that preceded the breakout [jIqtzTnfNHY]. Use only the two most recent swing points [Tb1CLQuJOsE].
- **Entry:** next open after reversal pattern (hammer, bullish engulfing, shooting star, false break), or lower-timeframe break of structure.
- **Stop:** 1 ATR(20) beyond the swing extreme.
- **Exits:** first target just before the prior swing high/resistance (take ~50%); second target Fib 1.27/1.618, or trail the rest with 50 MA or 100 MA (varies by video: 100 MA in RG4qEMp2XcU, 50 MA in Tb1CLQuJOsE, 20 MA in GvMdTMSvoDo) or structure.
- **Sizing:** split 50/50; overall risk % not specified.
- **Avoid:** no clear trend, chasing, entry without a trigger, targets right at resistance, ignoring higher timeframe.
- **Codable:** PARTLY (pattern recognition and "clear trend" are judgment; stop, trail and targets are precise).

### 4.8 False break (failed breakout) [wmjLoLQjXZc, Tb1CLQuJOsE, eddj9v1CfA4]
- **Context:** established trend, pullback to defined support (long) / resistance (short).
- **Entry:** price pierces the level, then closes back inside; enter next open (buy limit at original level if missed, which risks no fill).
- **Stop:** 1 ATR(20, SMA) beyond the extreme.
- **Exit:** just short of nearest swing; remainder at Fib 1.27/1.618/2.0 chosen by how far the market has extended historically.
- **Codable:** YES for the mechanics once support/resistance is defined; the level itself is judgment.

### 4.9 Power move vs crawling move at support/resistance [GvMdTMSvoDo]
- **Power move** (large candles, rapid, no obstacle) into support: expect reversal; enter on reversal pattern, stop 1 ATR beyond reversal candle high/low, targets swing and Fib 1.27.
- **Crawling move** (lower highs into support, higher lows into resistance): expect break; enter on close beyond the level; 20 MA close as trail.
- **Conflict:** this video says do not move stop to break-even mid-trade [GvMdTMSvoDo], while another version of the idea mentions trailing to break-even after target 1 in the same video's setup text. Treat as unresolved.
- **Codable:** PARTLY.

### 4.10 Multi-timeframe stacked level / break of structure [Dnh1uya1QAg, Tb1CLQuJOsE, RG4qEMp2XcU]
- Higher timeframe = 4-6x the trading timeframe. Take reversals at levels present on both; or enter lower-timeframe break of structure aligned with the higher-timeframe trend. Weekly trend with 8-hour entry; daily consolidation with 4-hour entry.
- **Codable:** PARTLY (swing/structure definition needed).

### 4.11 ATR-based setups [LBQIkLkU8WY]
- Breakout after weekly ATR(20) at multi-year low (needs a lookback definition for "multi-year low"; not given).
- Reversal after a 1.5 x ATR extension into structure with a reversal candle; stop beyond the swing plus 0.5-1 ATR; target prior swing or 1:2.
- Chandelier trailing at 2x (short term), 4x (medium), 6x+ (long term).
- **Codable:** YES for the 1.5 ATR reversal and trailing; PARTLY for the squeeze.

### 4.12 Swing patterns [QUFAaWw3kU0]
"Stuck in a box" (buy rejection at range support, exit before resistance), "Catch the wave" (50 MA bounce in a healthy uptrend), "Fit the move" (short a false break after a big rally, tight management). **Codable:** PARTLY; no numbers.

### 4.13 Forex MACD pattern setups [9vvAsxNmyT8]
Inside/engulfing/outside/pin bar breakouts at swings with MACD at an extreme and turning or diverging; "first red candle" scalps; head-and-shoulders; flags. Stops, risk % and exits are largely unstated; claimed 87% wins, 1,377 trades. **Codable:** PARTLY at best; quality rated medium. Lowest-confidence material.

### 4.14 Seasonality-confirmed pullback [VDvAP-QuGTY]
Uptrend + seasonally strong month (e.g., Bitcoin Oct-Nov) + valid technical setup. Never trade seasonality alone. **Codable:** PARTLY.

---

## 5. Risk, position sizing, exposure

- **Formula:** shares = dollar risk / (entry - stop); constant dollar risk, variable share count [hsYw6Z1nqgw, 1ohBdvp8CoU].
- **Risk per trade:** 1-2% generally [hsYw6Z1nqgw]; trend following 2% [ggnIGZiDoFY], turtle upgrade 1% [HnNBOReTb8g]. In the turtle video, 4% risk turned the system into 75%/yr with a -96% max drawdown ("ruins the system"), so more risk is not better.
- **Position-percentage systems:** 20% x 5 stocks (fully invested, no leverage); 50% x 2 ETFs [NheeZ94_Ajk, XFTL5m5EbUY]. No leverage in any system [7D32Zvmt-6Q].
- **Allocation across systems:** example 50% trend following / 50% mean reversion [Ew05en-HlDs]; his own accounts split systems by account [VDvAP-QuGTY].
- **Stops:** always use one (exceptions: options, mental stops, hedging) [1ohBdvp8CoU]; place beyond swing point plus ATR buffer, not at obvious levels; stop width scales with market and timeframe volatility.
- **Pyramiding/adding:** not taught in these notes.
- **Drawdown expectation:** claims of 22% (momentum), 24-27% (mean reversion), 37% (trend following); trend followers can see 40-60%.

---

## 6. Selling and exits (beyond the stop)

- **No profit targets in trend following;** exit only on trailing stop [ggnIGZiDoFY, pGO9MwMCJKo].
- **Mean reversion:** indicator exit (RSI(2) > 50) with a 10-day time stop; all exits at next open [NheeZ94_Ajk, DS8_-LP59pw].
- **Momentum:** rank-based exit (falls out of top 2) or MA breach [XFTL5m5EbUY].
- **Discretionary hybrid:** take 50% at first swing target (just before the opposing zone, not at the extreme), trail the rest with MA/structure [RG4qEMp2XcU, Tb1CLQuJOsE].
- **Trailing choices:** 20 MA (short term, smaller profit, lower drawdown), 50-200 MA (longer trends) [cSWC2WwbhHE]; 10-day low [HnNBOReTb8g]; Chandelier ATR multiples [LBQIkLkU8WY]; previous swing low.
- **Counter-trend:** exit on close beyond the entry candle's extreme [QUFAaWw3kU0].
- **Forex discretionary:** close profitable trades Friday afternoon, avoid exotics overnight [9vvAsxNmyT8].
- **Cross-video inconsistency:** the preferred trailing MA varies (20/50/100/200) with no single rule; the logic is to match it to the trend length wanted.

---

## 7. Mindset and process

- Systems will have losing months and years; the edge is long-term [pGO9MwMCJKo, Ew05en-HlDs].
- Prepare for 30-40% drawdowns before they happen [Ew05en-HlDs].
- Confidence comes from historical data; 90% of traders fail within 2-3 years from lacking a working system or losing confidence [VDvAP-QuGTY].
- Don't chase parabolic moves; the urge to buy strong momentum is a red flag [xTd6nlbcIZc].
- If uncertain after checking the higher timeframe, stay out; other opportunities exist [8hM18AHcUCs].
- Separate systems by account for clarity [VDvAP-QuGTY].

---

## 8. Claims made (his numbers, unverified)

| System | Claims |
|---|---|
| Trend following (200d, 6 ATR) [ggnIGZiDoFY, pGO9MwMCJKo] | +2,864% over 25 yrs (~14%/yr); 45% win; payoff 1.74; max DD 37%; 2000 +22%, 2008 +65%, 2020 +8%, 2022 +56% |
| BB mean reversion [NheeZ94_Ajk, ybigcO913kc, DS8_-LP59pw] | +2,834% over 25 yrs; ~14%/yr; 66% win (one note says 33-34% losers); avg win 4.1% / loss 4.7%; max DD 27% (24% in one video) |
| Momentum ETF [XFTL5m5EbUY] | +535% (since 2006 or 2016, inconsistent within the same notes); ~10%/yr; ~60% win; payoff 1.13; max DD 22%; 2008 +15%, 2020 +18%, 2022 -3% |
| 50/50 mean reversion + momentum [7D32Zvmt-6Q] | Only one losing year in 25 (2022, -2.4%) |
| Turtle upgrade [HnNBOReTb8g] | Original: 36% win, -0.38%/yr, -95% DD; enhanced: 40.95% win, 32%/yr, -41% DD; (headline "26,210% over 20 years") |
| S&P RSI pullback [W8ENIXvcGlQ] | 88.89% win, 36 trades 1996-2019 (the "14 years" in the notes does not match the stated range), avg +1.43% / -0.87% |
| Forex MACD patterns [9vvAsxNmyT8] | 87% win on 1,377 trades; 15 straight profitable months |
| His accounts | 2024: mean reversion +29%, trend following +50%; 2025: momentum account +45-46%, mean reversion +20% [VDvAP-QuGTY, Ew05en-HlDs] |
| Overnight effect (SPY 1993-2023) [wID26sF338Q] | Open-to-close $1M to $831K; close-to-open $1M to ~$9M |
| Stock system [wID26sF338Q] | "3,225% over 22 years" (promo mention) |

Data caveats: the momentum and 2022 results conflict between summary lines; backtest costs, slippage, survivorship (current Russell 1000 constituents?), and period selection are not stated. All figures are his claims.

---

## 9. For a testing program: rules to test first

1. **BB mean reversion (Russell 1000):** universe = point-in-time Russell 1000 members. Signal at close t: Close > SMA(200) AND Close < BB(20, 2.5 SD) lower. Order: buy limit = 0.97 x Close(t), valid day t+1 only. Exit at next open after RSI(2) closes > 50 or after 10 trading days. 20% equity per name, max 5; rank excess signals by 150-day ROC. Human judgment: none.
2. **Same system, parameter sensitivity:** BB SD 2.0 vs 2.5; limit 0-5%; RSI exit 50 vs 60; hold 5-15 days; SMA 100/200; tests whether 2.5/3% is robust.
3. **200-day breakout trend following (2% risk):** signal at close = 200-day highest/lowest close; enter next open; Chandelier exit = highest high (20) minus 6 x ATR(20) for longs (specify the chandelier's period vs the 20-ATR clearly); exit at next open on close beyond; size = 2% x equity / (6 x ATR). Basket: 40+ futures across five classes. Human judgment: contract rolls/data adjustment.
4. **Turtle-upgrade variant:** 200-day entry, 2 ATR initial stop, 10-day-low/high trail, 1% risk. Compare with #3 on the same data and costs; test risk 1/2/4%.
5. **Momentum ETF rotation:** monthly, first trading day: filter Close > SMA(200); rank by 12-month ROC; hold top 2 at 50% each; unspecified case (fewer than 2 qualify) tested as cash. Verify the period discrepancy (2006 vs 2016 start).
6. **Combination test:** 50/50 of #1 and #5; also #1/#3/#5 equal-weight; check the "one losing year" claim and correlation.
7. **S&P RSI pullback:** S&P > SMA(200); buy next open after RSI(10) < 30; exit next open after RSI(10) > 40 or day 10. Extend to Russell 1000 single stocks to get adequate trade count.
8. **Overnight effect:** SPY close-to-open vs open-to-close, 1993 onward; then conditioned on SMA(200).
9. **Breakout from tight consolidation + RS filter (Russell 1000):** Close > SMA(200), 200d ROC > SPX 200d ROC; define consolidation (e.g., 20-bar range / ATR below threshold; higher-lows count); trigger = close above range high; exits compared: 20 MA, 50 MA, prior swing low, Fib 2.0. Needs a precise operational definition of "tight" (human judgment to calibrate).
10. **False break in trend with ATR stop:** trend = 50 MA slope plus HH/HL; level = prior swing; trigger = pierce then close back inside; stop 1 ATR(20); targets swing and Fib 1.27/1.618. Needs a swing-point algorithm.
11. **1.5 ATR extension reversal at structure:** entry = close extends 1.5 x ATR(20) beyond a swing level then reversal candle; stop beyond swing + 0.5-1 ATR; target 1:2.
12. **Entry timing vs relative strength (cSWC2WwbhHE):** between similar markets pick the one above 50 MA; test pullback-to-MA entries vs breakout entries on risk-adjusted return.

Judgment-heavy parts to defer: support/resistance placement, "clear trend" classification, candlestick pattern recognition, consolidation quality, 4-stage market classification, the forex MACD patterns.

**Approximate codable share:** ~45-50% of the content is directly codable (the five systematic setups account for most of the high-quality material); ~35-40% is partly codable discretionary price action once swings/patterns are defined; ~15% (forex MACD, mindset, meta-videos) is not usefully codable.


## 10. What was tested on our coins (first look, 2026-10-03)

`src/research/teacher_systems.py`, stated parameters only, our 10 coins, NDAX costs, 2017-2023 vs 2024-Jul 2026:

| System (his numbers on US stocks) | 2017-2023 on our coins | 2024-Jul 2026 on our coins | Status |
|---|---|---|---|
| Weekly 50/40-week breakout (+5,024%) | 16 trades, 62% won, avg +152% (random same-hold +435%) | 6 trades, 0 won, avg -43% | NOT_SUPPORTED (H04) |
| Bollinger 200/4 breakout (13.9%/yr) | 19 trades, avg +267% (one +4,021% outlier) | 9 trades, 1 won, avg -7.9% | NOT_SUPPORTED (H05) |
| Bollinger 20/2.5 mean reversion (+2,834%) | 30 trades, 77% won, avg +4.5% (random +0.35%) | 20 trades, 60% won, avg +0.6% (random -0.9%) | PROMISING (H06) |

The long-hold trend systems rode crypto's bull runs but gave too much back and lost in 2024-2026; the short 'buy a deep dip inside
an uptrend' system was positive and beat random in both periods (only 50 trades). See docs/knowledge/hypotheses.json.
