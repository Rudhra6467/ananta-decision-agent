# Teacher cards v1 (pre-registration, written 25 Oct 2026 before any result was seen)

Madhav's request: extract everything useful for the Indian market from the two YouTube teachers, test every strategy that can be tested, keep every result, and track the survivors forward. Source registers: Trade With Trend TWT-H01..H60 and Optionables OPT-H01..H60 (paraphrased from public videos; members-only videos not used).

Bars: family teacher_twt k = 145, teacher_opt k = 86 (frozen in every registration); two-sided Bonferroni z at 3.58 and 3.44. VALIDATED needs |t| at z in both development (2000-2017) and validation (2018-2023) with the same sign; CONDITIONAL needs z in one and 1.65 in the other. t is across calendar-quarter means; at least 16 quarters per period. 2024 onward stays sealed.

Status counts: AMBIGUOUS 1, DEFERRED 4, DESCRIPTIVE 6, FORWARD 22, LINKED 3, NEEDS_BUILD 3, NEEDS_DATA 11, NOT_INDIA 1, TEST 65, TOO_FEW 4

## Trade With Trend (Raunak A)

### TWT-H01 · Low breadth hurts breakouts · TEST
Breakouts taken while under X% of the liquid 500 are above their 200 DMA (X = 25, 30, 35, 40) earn less over 20 and 60 sessions than breakouts taken while breadth is 50% or more; they also fail (close back under the breakout level within 5 sessions) more often.
Variants (expected sign): `lt25|net20` -; `lt25|net60` -; `lt30|net20` -; `lt30|net60` -; `lt35|net20` -; `lt35|net60` -; `lt40|net20` -; `lt40|net60` -; `lt35|fail5` +

### TWT-H02 · Index below both averages hurts breakouts · TEST
Breakouts taken while the Nifty closes below both its 50 and 200 DMA earn less over 20 and 60 sessions, and fail within 5 sessions more often, than breakouts taken while it is above both. His figure checked alongside: about 75% of longs lose over 3 months when the index is below a falling 200 DMA.
Variants (expected sign): `net20` -; `net60` -; `fail5` +

### TWT-H03 · Cut risk to 0.25-0.5% in bad regimes · DEFERRED
Sizing rule on the H02 trade list.
Note: Sizing and capital rules were deferred by Madhav on 17 Oct ('not about sizing'). Cheap to run on the H02 trade list when he wants it.

### TWT-H04 · Top-RS sectors lead · TEST
Sector version (we hold sector indices, not a stock-to-sector map): every 5th session, rank the sector indices by their 63-session change against the Nifty 500; the top 3 beat the rest over 21, 63 and 126 sessions (excess return over the Nifty 500).
Variants (expected sign): `top3|xs21` +; `top3|xs63` +; `top3|xs126` +
Note: The stock-level claim (stocks from the top sectors) needs a point-in-time stock-to-sector map: not in the lake yet.

### TWT-H05 · Strong-structure sectors outperform, weak ones lag · TEST
A sector index with higher highs and higher lows (20-session swings), above a rising 50 DMA, and a rising RS line against the Nifty 500 beats the Nifty 500 over 21/63/126 sessions; a sector below a falling 50 DMA with falling RS lags.
Variants (expected sign): `strong|xs21` +; `strong|xs63` +; `strong|xs126` +; `weak|xs21` -; `weak|xs63` -; `weak|xs126` -

### TWT-H06 · Sector breadth ranks · NEEDS_DATA
Rank sectors by the share of members above their 200/50 DMA.
Note: Needs sector membership over time (stock-to-sector map).

### TWT-H07 · Index, sector and stock all in uptrends · NEEDS_DATA
Long only when the index, the stock's sector index and the stock are above their 200 DMA.
Note: Needs the stock-to-sector map. The index-plus-stock part is TWT-H02.

### TWT-H08 · Beating both sector and index · NEEDS_DATA
Stocks beating both their sector and the broad index over 3-6 months.
Note: Needs the stock-to-sector map.

### TWT-H09 · 50 DMA pullback in leaders · TEST
Stock above a rising 50 DMA and above its 200 DMA, within 15% of its all-time high, RS line rising, low touched the 50 DMA in the last 3 sessions. Entries on a strong bullish candle (close in the top 30% of the bar, up on the day) after a pullback on volume below the 50-day average beat the same pullbacks bought without the volume and candle conditions, over 20 and 60 sessions.
Variants (expected sign): `net20` +; `net60` +
Note: His first condition (a leading sector) needs the sector map and is left out.

### TWT-H10 · Don't chase: extension above the 50 DMA · TEST
In uptrend stocks (above the 50 and 200 DMA, every 5th session), entries more than X% above the 50 DMA (X = 8, 10, 15, 25) earn less over 20 and 60 sessions than entries within 5% of it; at 15% the next-60-session drawdown is also deeper.
Variants (expected sign): `gt8|net20` -; `gt8|net60` -; `gt10|net20` -; `gt10|net60` -; `gt15|net20` -; `gt15|net60` -; `gt25|net20` -; `gt25|net60` -; `gt15|minfwd60` -

### TWT-H11 · Breakouts on volume · TEST
Breakouts on volume above X times the 50-day average (X = 1.0, 1.5, 2.0) earn more over 20 sessions than breakouts below it; at 1.5x they fail within 5 sessions less often.
Variants (expected sign): `vol1.0|net20` +; `vol1.5|net20` +; `vol2.0|net20` +; `vol1.5|fail5` -

### TWT-H12 · The breakout bar's shape · TEST
Breakout bars that are the widest of the last 20 sessions, close in the top 25% of the bar and have an upper wick under 15% of the range earn more over 5/10/20 sessions and fail less often. Wide, high-volume (1.5x) bars with an upper wick of 40% or more earn less.
Variants (expected sign): `good|net5` +; `good|net10` +; `good|net20` +; `good|fail5` -; `wicky|net20` -

### TWT-H13 · RS line at a high confirms the breakout · TEST
Breakouts where the stock / Nifty 500 ratio is at (within 0.5% of) its 126-session high earn more over 20 and 60 sessions than breakouts where it is not.
Variants (expected sign): `net20` +; `net60` +

### TWT-H14 · RS new high before price · TEST
Stocks whose RS line is at a 126-session high while the price is still more than 5% below its 52-week high beat the market's drift over 60 and 120 sessions.
Variants (expected sign): `net60` +; `net120` +
Note: Second claim (RS breakouts lead price breakouts by a measurable time) is descriptive and not tested.

### TWT-H15 · Near highs beats far below · TEST
Stocks within 5% of their 52-week high beat stocks 40%+ below it over 20, 60 and 120 sessions (every 5th session). Stocks 40%+ down and below the 200 DMA more often fall another 40% within 120 sessions.
Variants (expected sign): `near|net20` +; `near|net60` +; `near|net120` +; `deep|fall40` +

### TWT-H16 · Group breakouts · NEEDS_DATA
Several breakouts in one industry within weeks.
Note: Needs an industry map.

### TWT-H17 · Breakout follow-through · TEST
Breakouts that close above the breakout close on each of days 1-3 and have above-average volume on at least 3 of the first 5 days earn more over the next 20 and 60 sessions, counted from day 5 (when the follow-through is known), than breakouts without it.
Variants (expected sign): `p5net20` +; `p5net60` +
Note: His 5:1 bullish-to-bearish candle filter is not added.

### TWT-H18 · Quiet pullbacks after a breakout · TEST
After a breakout, the first pullback of 3% from the post-breakout high (days 3-15): pullbacks on lower volume than the up-leg that hold the breakout level make a new high within 15 sessions more often than other pullbacks; pullbacks that retrace under 38.2% of the run do too.
Variants (expected sign): `quiet_hold|newhigh15` +; `shallow|newhigh15` +

### TWT-H19 · How often breakouts retest · DESCRIPTIVE
Share of breakouts whose close returns to the breakout level within 10 sessions, and whose low touches it within 20; also among the breakouts that went on to gain 10%+ in 60 sessions. His figures: about 40% of eventual winners, more than 65% of breakouts.
Note: The retest-entry versus breakout-entry comparison needs the exit engine (batch 3).

### TWT-H20 · 25% at the breakout, 75% after the pullback · LINKED
Staged entry versus one entry, same stop.
Note: Run on 18 Oct as E09 'stage_25_75_pullback' (his exact split) on BRK, PULL and ANY entries.

### TWT-H21 · Weekly instalments in weak markets · LINKED
Equal weekly instalments versus one breakout-day entry.
Note: Run on 18 Oct as E09 'stage_weekly4' (4 weekly instalments). His 8-16 week version was not run; it would add looks for a sizing-type rule.

### TWT-H22 · Staged stop -3/-5/-7 versus one -7% stop · TEST
On breakout entries (next open), selling a third at -3%, a third at -5% and the rest at -7% beats a single -7% stop when every position is closed at the close of day 20 or 60 at the latest; also checked when breadth is under 40%. Baseline: a single -7% stop beats no stop (60 sessions).
Variants (expected sign): `staged_vs_single|hold20` +; `staged_vs_single|hold60` +; `staged_vs_single|hold60|weak_breadth` +; `single7_vs_none|hold60` +
Note: Re-entry after recovery is not simulated.

### TWT-H23 · Structure exits · TEST
On breakout entries, an initial stop at the last confirmed swing low and an exit on the first close below the latest swing low (max 120 sessions) beats (a) a +15% target with a -7% stop and (b) a tight -3% stop held otherwise to 60 sessions.
Variants (expected sign): `vs_target15_stop7` +; `vs_tight3` +

### TWT-H24 · Three-step exit for big winners · TEST
For breakouts that reach +30% within a year: selling 30% at +40%, 35% on the first close below the 50 DMA and the rest below the latest swing low beats holding to day 250, and beats a full exit on the first close below the 50 DMA.
Variants (expected sign): `vs_hold250` +; `vs_full_50dma` +

### TWT-H25 · Portfolio drawdown rule · LINKED
Review or exit all positions at a 7-8% open drawdown.
Note: Run on 18 Oct as E10 (dd7/dd8 pause rules on 10-slot books).

### TWT-H26 · During index pullbacks, sell weak losers · TEST
While the Nifty is 3-10% below its 52-week high (every 5th session), stocks that are down over 60 sessions and lagging the Nifty 500 over 63 sessions earn less over the next 20 and 60 sessions than stocks that are up and leading, so selling the first group and keeping the second helps.
Variants (expected sign): `net20` -; `net60` -

### TWT-H27 · Stage 2 stocks · TEST
Stage 2 (above a rising 150-day average, the daily stand-in for his 30-week MA, with higher highs and lows and a rising RS line) beats every other stock over 60 and 120 sessions (every 5th session). Breakouts from a 120-session range while in stage 2 beat other 120-session breakouts.
Variants (expected sign): `stage2|net60` +; `stage2|net120` +; `range_brk_in_stage2|net60` +; `range_brk_in_stage2|net120` +

### TWT-H28 · Correction leaders · TEST
While the Nifty is 10%+ below its 52-week high (every 5th session), the top fifth of stocks by 63-session relative strength beat the bottom fifth over 60 and 120 sessions.
Variants (expected sign): `net60` +; `net120` +

### TWT-H29 · Sectors that fall least lead the rebound · TEST
While the Nifty is 10%+ below its 52-week high (every 5th session), the 3 sector indices closest to their own 52-week high beat the 3 furthest, against the Nifty 500, over 63 and 126 sessions.
Variants (expected sign): `xs63` +; `xs126` +

### TWT-H30 · Swing-structure breadth · TEST
When under 35% of the liquid 500 show higher highs and higher lows (20-session swings), the Nifty's next-21-session return is lower and its volatility higher than when over 60% do. Under 20% with the Nifty within 3% of its high flags deeper drawdowns over 63 sessions.
Variants (expected sign): `lt35|nfwd21` -; `lt35|nrv_fwd21` +; `lt20_near_high|n_mdd63` -

### TWT-H31 · New highs on thin breadth · TEST
With the Nifty within 2% of its 52-week high, a 4%+ drawdown within 21 and 63 sessions is more likely when 50% or fewer stocks are above their 200 DMA than when 70% or more are.
Variants (expected sign): `dd4|21` +; `dd4|63` +

### TWT-H32 · Short-term breadth damage, long-term intact · TEST
Three versions, each against all other sessions, Nifty over 21 and 63 sessions: (v1) 50-DMA breadth down 20+ points in 10 sessions while 200-DMA breadth is down 10 or less; (v2) 50-DMA breadth 45% or less with 200-DMA breadth 65%+; (v3) the Nifty 4-6% off its high with 50-DMA breadth 55%+.
Variants (expected sign): `v1|nfwd21` +; `v1|nfwd63` +; `v2|nfwd21` +; `v2|nfwd63` +; `v3|nfwd21` +; `v3|nfwd63` +
Note: One of his videos (8QeR8FmYYg4) says a fast drop is bearish: the test is two-sided, so that reading would show as OPPOSITE.

### TWT-H33 · Breadth washouts · TEST
When 20% or fewer stocks are above their 200 DMA, or 11% or fewer above their 50 DMA, the Nifty's next 63/126/252 sessions beat all other sessions.
Variants (expected sign): `b200le20|nfwd63` +; `b200le20|nfwd126` +; `b200le20|nfwd252` +; `b50le11|nfwd63` +; `b50le11|nfwd126` +; `b50le11|nfwd252` +
Note: Washouts cluster in a few quarters (2008, 2011, 2020): expect INCONCLUSIVE on the 16-quarter minimum.

### TWT-H34 · Bottoming signals · TOO_FEW
Strong up days after lows, holding the first rally day's low, ranges above the 50/200 DMA.
Note: About 8-10 corrections in 2003-2023: below the 16-quarter minimum for a test. A descriptive table can be added.

### TWT-H35 · Bear-market rallies fail near the 50 DMA · TEST
With the Nifty below a falling 50 DMA and below its 200 DMA, the session it rallies to within 3% of the 50 DMA (from further below) is followed by lower 10 and 21 session returns than the market's drift.
Variants (expected sign): `nfwd10` -; `nfwd21` -

### TWT-H36 · Deep below the 200 DMA · TEST
Nifty closes 8-14% below its 200 DMA are followed by higher 21 and 63 session returns than other sessions; the 9-10% band by higher 63 and 126 session returns.
Variants (expected sign): `b8_14|nfwd21` +; `b8_14|nfwd63` +; `b9_10|nfwd63` +; `b9_10|nfwd126` +
Note: Few episodes: likely INCONCLUSIVE.

### TWT-H37 · India VIX spikes above 28 · TEST
Sessions with India VIX at 28 or more, and sessions within 10% of a VIX peak of 28+ in the last 5 sessions after it turned down 10%, are followed by higher Nifty returns than other sessions (21, 63, 252 and 21, 63 sessions).
Variants (expected sign): `ge28|nfwd21` +; `ge28|nfwd63` +; `ge28|nfwd252` +; `peak_turn|nfwd21` +; `peak_turn|nfwd63` +
Note: India VIX from 2009 (dev 2009-2017). High-VIX sessions cluster: likely INCONCLUSIVE.

### TWT-H38 · VIX waking up from low levels · TEST
The Nifty's drawdown over the next 21 sessions is deeper (a) when VIX reaches 14+ after 15 sessions at 13 or less, (b) after a 30%+ weekly VIX jump, and (c) when VIX is above 17 rather than below 14.
Variants (expected sign): `wake14|n_mdd21` -; `jump30|n_mdd21` -; `gt17_vs_lt14|n_mdd21` -

### TWT-H39 · Small caps' turn · TEST
When the Nifty Smallcap 100 / Nifty 100 ratio has risen over 40 sessions, or closes above its 50 DMA, the ratio keeps rising over the next 63 and 126 sessions.
Variants (expected sign): `ret40|slfwd63` +; `ret40|slfwd126` +; `above50|slfwd63` +; `above50|slfwd126` +

### TWT-H40 · Index contraction on a rising 50 DMA · TEST
In an uptrend (Nifty above a rising 50 DMA), sessions with the 10-day average range under 70% of the 50-day average and the Nifty within 3% above its 50 DMA are followed by higher 10 and 21 session returns than other uptrend sessions.
Variants (expected sign): `nfwd10` +; `nfwd21` +

### TWT-H41 · Leadership turns over after a bear phase · TOO_FEW
Prior-cycle leaders lag for 1-3 years.
Note: About 4 bear phases since 2000: too few for a test. The correction-leaders cross-section is TWT-H28.

### TWT-H42 · A strong dollar hurts the Nifty · TEST
When the broad dollar index (the Fed's, from 2006; stand-in for DXY) is up 5%+ over 126 sessions, or breaks above its 3-year high, the Nifty's next 21 and 63 sessions are weaker than other sessions.
Variants (expected sign): `up5|nfwd21` -; `up5|nfwd63` -; `break3y|nfwd21` -; `break3y|nfwd63` -
Note: His threshold is +10% on DXY; the broad index moves less than DXY, so +5% is used and labelled. A US close counts from the next Indian session.

### TWT-H43 · Strong crude hurts the Nifty · TEST
Brent above its 50 DMA, or at $100+, is followed by weaker Nifty returns over 21 and 63 sessions.
Variants (expected sign): `above50|nfwd21` -; `above50|nfwd63` -; `ge100|nfwd21` -; `ge100|nfwd63` -
Note: Another of his videos says Brent at 80-100 is not meaningfully worse: two-sided test.

### TWT-H44 · US weakness leads the Nifty lower · TEST
With the Nasdaq (stand-in: the lake's S&P 500 starts 2016) below its 50 DMA, or 10%+ below its 60-session high, the Nifty's next 21 and 63 sessions are weaker; in the 5 sessions after the Nasdaq reclaims its 50 DMA the Nifty's next 21 and 42 sessions are stronger.
Variants (expected sign): `below50|nfwd21` -; `below50|nfwd63` -; `dd10|nfwd21` -; `dd10|nfwd63` -; `reclaim|nfwd21` +; `reclaim|nfwd42` +

### TWT-H45 · India vs US relative legs · TOO_FEW
Nifty 500 / S&P 500 legs of 4-12 months.
Note: The lake's S&P 500 starts 2016, and legs of 4-12 months give only a handful of observations.

### TWT-H46 · Bank Nifty leads · TEST
After a 3.5%+ weekly Bank Nifty gain the Nifty's next 21 sessions and the 200-DMA breadth over 21 sessions rise more than otherwise; with Bank Nifty above its 200 DMA the Nifty's next 21 and 63 sessions beat sessions when it is below.
Variants (expected sign): `wk35|nfwd21` +; `wk35|breadth_fwd21` +; `above200|nfwd21` +; `above200|nfwd63` +

### TWT-H47 · Rate-cut lags · TOO_FEW
First cut of a cycle to the index's major low: 4-8 months.
Note: About 5 RBI cutting cycles since 2000.

### TWT-H48 · FII flow beta · NEEDS_DATA
FII flow sensitivity before and after the SIP era.
Note: The FII/DII cash-flow table in the lake is empty.

### TWT-H49 · Stochastic pullback with filters · TEST
Among Stochastic(15,3,3) dips with %K and %D both under 30, those with the close above the 100-day average and at most one wide-range down candle (range over 1.5 ATR, red) in the last 5 sessions earn more over 10 and 20 sessions.
Variants (expected sign): `net10` +; `net20` +
Note: His narrow Heikin Ashi condition has no numeric definition and is left out.

### TWT-H50 · Confirmed Heikin Ashi entries · TEST
Entries on the second green Heikin Ashi candle after 3+ red ones (initiation plus confirmation) earn more over 10 and 20 sessions than entries on every red-to-green change.
Variants (expected sign): `net10` +; `net20` +

### TWT-H51 · Hidden bullish divergence · TEST
In stocks above their 200 DMA, a confirmed higher swing low in price with a lower RSI(14) low at 35 or under beats the market drift of uptrend pullbacks (below the 20 DMA, every 5th session) over 5, 10 and 20 sessions.
Variants (expected sign): `net5` +; `net10` +; `net20` +

### TWT-H52 · Ichimoku: all elements aligned · TEST
Among closes above the cloud (first close above), those with Senkou A and B rising, Chikou above price and Tenkan and Kijun rising earn more over 10 and 20 sessions.
Variants (expected sign): `net10` +; `net20` +
Note: The bearish mirror (shorts) is not tested: the India paper book is long only.

### TWT-H53 · Weekly outside reversal bars · TEST
A bullish weekly outside bar (high above and low below the prior week, close above the prior week's high) after a 10%+ fall over 8 weeks beats the market drift over 10 and 20 sessions; with the week's volume the highest in 52 weeks over 20 sessions; a bearish one after a 10%+ rise lags over 20.
Variants (expected sign): `bull|net10` +; `bull|net20` +; `bull_vol52|net20` +; `bear|net20` -

### TWT-H54 · ADX trend pullback to the 20 EMA · TEST
Buying the break of the high of a candle that touched the 20 EMA (entry next open) earns more over 10 and 20 sessions when ADX(14) was above 30 and rising with +DI above -DI than for any 20-EMA touch.
Variants (expected sign): `net10` +; `net20` +
Note: He buys the break intraday; this enters at the next open (one session later).

### TWT-H55 · Daily beats intraday · NEEDS_DATA
Same rules on daily versus 5-30 minute bars.
Note: Needs stock minute history before 2024.

### TWT-H56 · Intraday entries aligned with the daily trend · NEEDS_DATA
30/60-minute entries only with the daily trend up.
Note: Needs stock minute history before 2024.

### TWT-H57 · Index ETF tranches · DEFERRED
Buying an index ETF in drawdown tranches.
Note: Sizing rule: deferred by Madhav.

### TWT-H58 · Quality screen · NEEDS_BUILD
Sales growth, margins, ROE, D/E screen.
Note: Fundamentals exist but a point-in-time screen (as reported, with filing dates) must be built first.

### TWT-H59 · Opening outside yesterday's range · TEST
Days the Nifty (and Bank Nifty) opens outside the prior day's high-low range have a bigger range (vs the 20-day average) and more often close further in the direction of the gap than days opening inside.
Variants (expected sign): `NIFTY|range` +; `NIFTY|continuation` +; `BANKNIFTY|range` +; `BANKNIFTY|continuation` +
Note: His value-area version needs minute profiles (index minutes exist from 2015; a later build).

### TWT-H60 · Value-area sequences · NEEDS_BUILD
Higher non-overlapping value areas predict continuation.
Note: Needs TPO profiles built from minute bars.

## Optionables

### OPT-H01 · Intraday ATM straddle at fixed times · FORWARD
Sell the ATM Bank Nifty/Nifty straddle at 9:20, 9:30, 9:45, 10:00, 12:30, 13:00 or 14:00 with a premium stop on each leg; same-day exit.
Note: Needs intraday option prices. The recorder saved nothing from 21 Oct until the Kite sign-in was fixed on 25 Oct; it records from Mon 26 Oct.
Forward: Shadow book on the live option recorder (kite_1m_fo, from the first recorded session): one lot on paper at the recorder's prices with full charges, scored at 12 weeks, tail check at 26 weeks, no verdict before.

### OPT-H02 · The 1 pm Bank Nifty straddle · FORWARD
ATM Bank Nifty straddle at 13:00, 30% stop per leg, exit 14:55. His figures: ~70% winning days, win/loss ~1:1, max drawdown ~11% at 2.5 lakh per lot.
Note: Needs intraday option prices. The recorder saved nothing from 21 Oct until the Kite sign-in was fixed on 25 Oct; it records from Mon 26 Oct.
Forward: Shadow book on the live option recorder (kite_1m_fo, from the first recorded session): one lot on paper at the recorder's prices with full charges, scored at 12 weeks, tail check at 26 weeks, no verdict before.

### OPT-H03 · The 9:30 Bank Nifty straddle · FORWARD
ATM Bank Nifty straddle at 9:30, 50% stop per leg, exit 15:00. His figure: ~70% winning days.
Note: Needs intraday option prices. The recorder saved nothing from 21 Oct until the Kite sign-in was fixed on 25 Oct; it records from Mon 26 Oct.
Forward: Shadow book on the live option recorder (kite_1m_fo, from the first recorded session): one lot on paper at the recorder's prices with full charges, scored at 12 weeks, tail check at 26 weeks, no verdict before.

### OPT-H04 · The 9:30 Nifty straddle, split by VIX · FORWARD
ATM Nifty straddle at 9:30, 70-point stop per leg, exit 15:20; better below VIX 14, more double stops above 20.
Note: Needs intraday option prices. The recorder saved nothing from 21 Oct until the Kite sign-in was fixed on 25 Oct; it records from Mon 26 Oct.
Forward: Shadow book on the live option recorder (kite_1m_fo, from the first recorded session): one lot on paper at the recorder's prices with full charges, scored at 12 weeks, tail check at 26 weeks, no verdict before.

### OPT-H05 · Entry time · FORWARD
Afternoon entries (12:30-14:00) beat 9:30-10:00 entries (conflicting videos: all slots registered together).
Note: Needs intraday option prices. The recorder saved nothing from 21 Oct until the Kite sign-in was fixed on 25 Oct; it records from Mon 26 Oct.
Forward: Shadow book on the live option recorder (kite_1m_fo, from the first recorded session): one lot on paper at the recorder's prices with full charges, scored at 12 weeks, tail check at 26 weeks, no verdict before.

### OPT-H06 · Per-leg stop width · FORWARD
Stops of 25/30/35/40/50/75/100% of premium on identical entries.
Note: Needs intraday option prices. The recorder saved nothing from 21 Oct until the Kite sign-in was fixed on 25 Oct; it records from Mon 26 Oct.
Forward: Shadow book on the live option recorder (kite_1m_fo, from the first recorded session): one lot on paper at the recorder's prices with full charges, scored at 12 weeks, tail check at 26 weeks, no verdict before.

### OPT-H07 · Stop to cost · FORWARD
After the first leg stops, move the other leg's stop to its entry price.
Note: Needs intraday option prices. The recorder saved nothing from 21 Oct until the Kite sign-in was fixed on 25 Oct; it records from Mon 26 Oct.
Forward: Shadow book on the live option recorder (kite_1m_fo, from the first recorded session): one lot on paper at the recorder's prices with full charges, scored at 12 weeks, tail check at 26 weeks, no verdict before.

### OPT-H08 · Staggered entries · FORWARD
Split the same size over 2-3 entry times: lower drawdown, daily P&L correlation below 1.
Note: Needs intraday option prices. The recorder saved nothing from 21 Oct until the Kite sign-in was fixed on 25 Oct; it records from Mon 26 Oct.
Forward: Shadow book on the live option recorder (kite_1m_fo, from the first recorded session): one lot on paper at the recorder's prices with full charges, scored at 12 weeks, tail check at 26 weeks, no verdict before.

### OPT-H09 · Where straddle losses come from · FORWARD
Losses concentrate on V-shaped or whipsaw days; trend and range days pay.
Note: Needs intraday option prices. The recorder saved nothing from 21 Oct until the Kite sign-in was fixed on 25 Oct; it records from Mon 26 Oct.
Forward: Shadow book on the live option recorder (kite_1m_fo, from the first recorded session): one lot on paper at the recorder's prices with full charges, scored at 12 weeks, tail check at 26 weeks, no verdict before.

### OPT-H10 · Late-session exit · FORWARD
Close intraday short premium at 14:55-15:20 rather than the final minutes.
Note: Needs intraday option prices. The recorder saved nothing from 21 Oct until the Kite sign-in was fixed on 25 Oct; it records from Mon 26 Oct.
Forward: Shadow book on the live option recorder (kite_1m_fo, from the first recorded session): one lot on paper at the recorder's prices with full charges, scored at 12 weeks, tail check at 26 weeks, no verdict before.

### OPT-H11 · Expiry last-hour decay · FORWARD
ATM straddle sold after 15:00 on expiry day profitable on ~80% of days.
Note: Needs intraday option prices. The recorder saved nothing from 21 Oct until the Kite sign-in was fixed on 25 Oct; it records from Mon 26 Oct.
Forward: Shadow book on the live option recorder (kite_1m_fo, from the first recorded session): one lot on paper at the recorder's prices with full charges, scored at 12 weeks, tail check at 26 weeks, no verdict before.

### OPT-H12 · Expiry afternoon straddle · FORWARD
ATM straddle sold 12:30-14:00 on expiry day, held to close; better after a contracted morning range.
Note: Needs intraday option prices. The recorder saved nothing from 21 Oct until the Kite sign-in was fixed on 25 Oct; it records from Mon 26 Oct.
Forward: Shadow book on the live option recorder (kite_1m_fo, from the first recorded session): one lot on paper at the recorder's prices with full charges, scored at 12 weeks, tail check at 26 weeks, no verdict before.

### OPT-H13 · Daily loss cap · FORWARD
Flatten the book at a 0.5-3% daily loss: smaller worst day without losing expectancy.
Note: Needs intraday option prices. The recorder saved nothing from 21 Oct until the Kite sign-in was fixed on 25 Oct; it records from Mon 26 Oct.
Forward: Shadow book on the live option recorder (kite_1m_fo, from the first recorded session): one lot on paper at the recorder's prices with full charges, scored at 12 weeks, tail check at 26 weeks, no verdict before.

### OPT-H14 · Capital per lot · DEFERRED
One lot per 2-2.5 lakh.
Note: Sizing rule: deferred by Madhav.

### OPT-H15 · Gap-stress sizing · DEFERRED
Size so a stress gap costs a fixed small share.
Note: Sizing rule: deferred by Madhav.

### OPT-H16 · Weekly straddle: naked versus winged · TEST
Sell the ATM weekly straddle at the first session's open of the expiry week (Friday, or the session after the previous expiry), hold to expiry settlement. Naked earns more than zero; naked minus the version with wings bought at the breakevens (strikes nearest K +/- the credit) is positive.
Variants (expected sign): `BANKNIFTY|naked` +; `BANKNIFTY|naked_minus_winged` +; `NIFTY|naked` +; `NIFTY|naked_minus_winged` +
Note: Weekly expiries only: Bank Nifty from 2016 and Nifty from 2019 leave too few development quarters, so INCONCLUSIVE is likely by design.

### OPT-H17 · Overnight expiry-eve strangle · TEST
Sell the call and put about 200 points out (Bank Nifty), or 0.7% of spot, at the close the session before expiry; buy back at the expiry-day open. A winged version buys the strikes 550 points out. Earns more than zero; his figures: 75%+ wins, 20-25% a year, max drawdown ~11%.
Variants (expected sign): `BANKNIFTY|200pt` +; `BANKNIFTY|0.7pct` +; `BANKNIFTY|200pt_wings550` +; `NIFTY|0.7pct` +
Note: His 9:20 exit is approximated by the expiry-day open price in the bhavcopy; his 75% stop at 9:16 is then the same moment.

### OPT-H18 · Two thirds of days are range days · DESCRIPTIVE
Share of Nifty and Bank Nifty days with open-to-close within 1%, close-to-close within 1%, and moves over 2%, by period. His figures: Bank Nifty o-c within 1% ~66% (2012-20); Nifty within 1% 62%+ and over 2% 10% or less (2006-21); Nifty c-c within 1% ~68% (since 2000).

### OPT-H19 · VIX buckets and realised range · DESCRIPTIVE
Nifty mean (high-low)/open, mean |open-to-close| and mean |overnight gap| for VIX under 14, 14-20 and over 20. His figures: 0.78/1.0/1.78% range, 0.4/0.56/1.0% open-to-close, gaps ~3x larger above 20 than below 14.

### OPT-H20 · VIX level and premium selling · TEST
The short ATM straddle sold 5 sessions before each expiry and held to expiry earns more when VIX is under 14 than at 14+ (claim a), and more when VIX is over 20 than at 20 or less (claim d). His videos conflict, so both are registered; claim (b) 'worse in low VIX' shows as OPPOSITE on the first.
Variants (expected sign): `BANKNIFTY|vix_lt14` +; `NIFTY|vix_lt14` +; `BANKNIFTY|vix_gt20` +; `NIFTY|vix_gt20` +

### OPT-H21 · Rising VIX hurts premium sellers · TEST
The same straddle earns less when VIX rose over the prior 5 sessions, and when it rose 10%+ from under 14.
Variants (expected sign): `BANKNIFTY|vix_rising` -; `NIFTY|vix_rising` -; `BANKNIFTY|vix_rising_from_low` -; `NIFTY|vix_rising_from_low` -

### OPT-H22 · Budget day straddles · FORWARD
ATM straddles every 30 minutes 9:30-12:00 on Budget day, 40-50% stops, stop to cost, exit 15:23-15:29.
Note: Needs intraday option prices. The recorder saved nothing from 21 Oct until the Kite sign-in was fixed on 25 Oct; it records from Mon 26 Oct.
Forward: Shadow book on the live option recorder (kite_1m_fo, from the first recorded session): one lot on paper at the recorder's prices with full charges, scored at 12 weeks, tail check at 26 weeks, no verdict before.

### OPT-H23 · After RBI announcements · FORWARD
Straddles sold ~30 minutes after a policy announcement beat those held into it.
Note: Needs intraday option prices. The recorder saved nothing from 21 Oct until the Kite sign-in was fixed on 25 Oct; it records from Mon 26 Oct.
Forward: Shadow book on the live option recorder (kite_1m_fo, from the first recorded session): one lot on paper at the recorder's prices with full charges, scored at 12 weeks, tail check at 26 weeks, no verdict before.

### OPT-H24 · Flat through binary events · TEST
A short ATM straddle sold at the close and bought back at the next open earns less on nights before scheduled binary events (elections, RBI, Budget, Fed, from the event table) than on other nights.
Variants (expected sign): `BANKNIFTY|event_nights` -; `NIFTY|event_nights` -

### OPT-H25 · OI band contains the expiry · TEST
k sessions before expiry (k = 5, 1), the settlement lands between the biggest put-OI strike below spot and the biggest call-OI strike above spot more often than inside a band of the same width centred on spot.
Variants (expected sign): `NIFTY|k5` +; `NIFTY|k1` +; `BANKNIFTY|k5` +; `BANKNIFTY|k1` +

### OPT-H26 · OI band contains tomorrow · TEST
The next session's high and low stay inside the prior close's biggest call-OI and put-OI strikes (nearest expiry) more often than inside an equal-width band centred on the close.
Variants (expected sign): `NIFTY` +; `BANKNIFTY` +

### OPT-H27 · OI levels fail when VIX is high · TEST
The H26 band holds less often when VIX is 20 or more.
Variants (expected sign): `NIFTY|vix_ge20` -; `BANKNIFTY|vix_ge20` -

### OPT-H28 · PCR and direction · TEST
Nearest-expiry put/call OI ratio at the close against the index from the next open to the close 1 or 5 sessions later: (a) PCR over 1.2 bullish; (b) PCR under 0.5 contrarian bullish; (c) PCR under 0.7 bearish. All three registered (his videos contradict each other).
Variants (expected sign): `NIFTY|a_gt1.2|d1` +; `NIFTY|a_gt1.2|d5` +; `NIFTY|b_lt0.5|d1` +; `NIFTY|b_lt0.5|d5` +; `NIFTY|c_lt0.7|d1` -; `NIFTY|c_lt0.7|d5` -; `BANKNIFTY|a_gt1.2|d5` +; `BANKNIFTY|b_lt0.5|d5` +; `BANKNIFTY|c_lt0.7|d5` -

### OPT-H29 · PCR near 1 means a quiet day · TEST
With PCR 0.85-1.15 and the biggest single strike holding more than the median share of OI, the next session's range (and the next 5 sessions') is narrower.
Variants (expected sign): `NIFTY|d1` -; `BANKNIFTY|d1` -; `NIFTY|d5` -

### OPT-H30 · OI change near the money · TEST
Within 2% of spot (nearest expiry): call OI falling while put OI rises predicts a higher index over 1 and 5 sessions; call OI added at 2x the put OI added while put OI falls predicts a lower one.
Variants (expected sign): `NIFTY|bull|d1` +; `NIFTY|bull|d5` +; `NIFTY|bear|d1` -; `NIFTY|bear|d5` -; `BANKNIFTY|bull|d5` +; `BANKNIFTY|bear|d5` -

### OPT-H31 · Max-OI pinning · TEST
Expiry settles closer to the strike with the biggest call+put OI (k = 1, 3 sessions before) than to the at-the-money strike at the same time.
Variants (expected sign): `NIFTY|k1` -; `NIFTY|k3` -; `BANKNIFTY|k1` -; `BANKNIFTY|k3` -

### OPT-H32 · OI the day after expiry · TEST
The OI band (H25) taken from the next contract on the first session after an expiry contains that contract's settlement more often than the band taken on the expiry day itself.
Variants (expected sign): `NIFTY` +; `BANKNIFTY` +

### OPT-H33 · FII/DII flows · NEEDS_DATA
FII selling versus DII buying predicts returns.
Note: The FII/DII cash-flow table in the lake is empty.

### OPT-H34 · Premium-imbalance shift · FORWARD
Shift the cheap leg toward the money only beyond an imbalance threshold (~20% of premium).
Note: Needs intraday option prices. The recorder saved nothing from 21 Oct until the Kite sign-in was fixed on 25 Oct; it records from Mon 26 Oct.
Forward: Shadow book on the live option recorder (kite_1m_fo, from the first recorded session): one lot on paper at the recorder's prices with full charges, scored at 12 weeks, tail check at 26 weeks, no verdict before.

### OPT-H35 · Counter trade after a stop · FORWARD
After one leg stops, sell a fresh option at 40-60% of the surviving leg's premium.
Note: Needs intraday option prices. The recorder saved nothing from 21 Oct until the Kite sign-in was fixed on 25 Oct; it records from Mon 26 Oct.
Forward: Shadow book on the live option recorder (kite_1m_fo, from the first recorded session): one lot on paper at the recorder's prices with full charges, scored at 12 weeks, tail check at 26 weeks, no verdict before.

### OPT-H36 · Adjust versus don't · FORWARD
The shift-plus-counter adjusted straddle beats the unadjusted one over a large sample.
Note: Needs intraday option prices. The recorder saved nothing from 21 Oct until the Kite sign-in was fixed on 25 Oct; it records from Mon 26 Oct.
Forward: Shadow book on the live option recorder (kite_1m_fo, from the first recorded session): one lot on paper at the recorder's prices with full charges, scored at 12 weeks, tail check at 26 weeks, no verdict before.

### OPT-H37 · Strangle to straddle · FORWARD
Convert a short strangle into a straddle when spot nears the threatened strike.
Note: Needs intraday option prices. The recorder saved nothing from 21 Oct until the Kite sign-in was fixed on 25 Oct; it records from Mon 26 Oct.
Forward: Shadow book on the live option recorder (kite_1m_fo, from the first recorded session): one lot on paper at the recorder's prices with full charges, scored at 12 weeks, tail check at 26 weeks, no verdict before.

### OPT-H38 · Weekly Bank Nifty condor · FORWARD
Iron condor Friday 9:20, shorts 500 points out, longs 800; convert to an iron fly once at an 800-point move.
Note: Needs intraday option prices. The recorder saved nothing from 21 Oct until the Kite sign-in was fixed on 25 Oct; it records from Mon 26 Oct.
Forward: Shadow book on the live option recorder (kite_1m_fo, from the first recorded session): one lot on paper at the recorder's prices with full charges, scored at 12 weeks, tail check at 26 weeks, no verdict before.

### OPT-H39 · Cap on adjustments · FORWARD
Cap adjustments at 1-4, then exit.
Note: Needs intraday option prices. The recorder saved nothing from 21 Oct until the Kite sign-in was fixed on 25 Oct; it records from Mon 26 Oct.
Forward: Shadow book on the live option recorder (kite_1m_fo, from the first recorded session): one lot on paper at the recorder's prices with full charges, scored at 12 weeks, tail check at 26 weeks, no verdict before.

### OPT-H40 · Adjust only on breach · FORWARD
No action inside the breakevens; adjust only on a breach.
Note: Needs intraday option prices. The recorder saved nothing from 21 Oct until the Kite sign-in was fixed on 25 Oct; it records from Mon 26 Oct.
Forward: Shadow book on the live option recorder (kite_1m_fo, from the first recorded session): one lot on paper at the recorder's prices with full charges, scored at 12 weeks, tail check at 26 weeks, no verdict before.

### OPT-H41 · Early profit-taking · TEST
Short weekly ATM straddle (H16 entries, naked): closing at the first daily close where it has kept 65%, 75% or 90% of the credit beats holding to expiry.
Variants (expected sign): `BANKNIFTY|take65` +; `BANKNIFTY|take75` +; `BANKNIFTY|take90` +; `NIFTY|take65` +; `NIFTY|take75` +; `NIFTY|take90` +
Note: Re-entry after the early close is not simulated.

### OPT-H42 · Monthly put ratio spread 1:2 · TEST
About 20 sessions before monthly expiry: buy the ATM put, sell 2 puts ~1.3% lower, hold to expiry. Earns more than zero (Nifty, Bank Nifty); net-credit entries beat net-debit ones; entries with VIX over 20 beat the rest. His figure: profitable 60-70% of months.
Variants (expected sign): `NIFTY|all` +; `BANKNIFTY|all` +; `NIFTY|credit_vs_debit` +; `NIFTY|vix_gt20` +
Note: His 3-4% capital stop and margins are not modelled.

### OPT-H43 · Call ratio spread 1:3 · AMBIGUOUS
Long a call ~20% OTM, short 3 calls ~30% OTM, 30 days, net credit.
Note: Index calls 20-30% out of the money do not trade on monthly Nifty/Bank Nifty; the numbers fit stocks or crypto. Needs his exact strikes before a test.

### OPT-H44 · Bitcoin daily condor · NOT_INDIA
BTC daily-expiry condor.
Note: Crypto, not India. Crypto has its own locked research.

### OPT-H45 · Implied probabilities are well calibrated · TEST
5 sessions before expiry, the probability of settling above each near strike from adjacent call prices scores better (lower Brier score) than a lognormal built from the last 20 sessions' realised volatility.
Variants (expected sign): `NIFTY` +; `BANKNIFTY` +

### OPT-H46 · Most OTM call buyers lose · DESCRIPTIVE
Share of 1-3% out-of-the-money calls bought 5 sessions before expiry and held to expiry that end above their cost; same for debit call spreads. His figure: one third or fewer.

### OPT-H47 · Buying after an IV spike loses · TEST
After a 25%+ weekly VIX jump (and with VIX over 30), an ATM Nifty call bought at the close and sold 3 sessions later loses on average.
Variants (expected sign): `NIFTY|vix_jump25_gt30` -; `NIFTY|vix_jump25` -

### OPT-H48 · Range breakouts · TEST
Stocks closing above a 20-session range no wider than 10% beat the market drift over 5 and 10 sessions; 60-session ranges (15% or tighter) beat the 20-session ones over 10. Nifty: a close above a 20-session range no wider than 4% is followed by higher 5 and 10 session returns than other sessions.
Variants (expected sign): `stk20|net5` +; `stk20|net10` +; `stk60_vs_20|net10` +; `nifty20|nfwd5` +; `nifty20|nfwd10` +

### OPT-H49 · Big red day without follow-through · TEST
After a 1.5%+ down day in an uptrend stock (above its 200 DMA, rising 50 DMA), if the next 3 closes stay above that day's low, the next 5 and 20 sessions (counted from day 3) beat red days that did get follow-through.
Variants (expected sign): `p3net5` +; `p3net20` +

### OPT-H50 · Swing-low invalidation · TEST
Stocks closing below their last confirmed swing low earn less over 5, 10 and 20 sessions than stocks still above it (every 5th session).
Variants (expected sign): `net5` -; `net10` -; `net20` -
Note: The short-side half is not tested: the India paper book is long only.

### OPT-H51 · New all-time highs · TEST
A stock's first close above every earlier high (one per 10 sessions) beats the market drift over 5, 10 and 20 sessions; Nifty all-time-high closes are followed by higher 5 and 21 session returns than other sessions.
Variants (expected sign): `stk|net5` +; `stk|net10` +; `stk|net20` +; `nifty|nfwd5` +; `nifty|nfwd21` +

### OPT-H52 · Broken resistance holds on the first retest · TEST
The first retest of a broken 60-session high (low within 1% of the level, close no more than 2% under it, 5-20 sessions after the breakout) beats the market drift over 10 sessions.
Variants (expected sign): `first_retest|net10` +
Note: His conflicting claims about later retests are not tested (no objective count of 'tests' before the break).

### OPT-H53 · Pair ratio at 2 SD · NEEDS_DATA
Same-sub-sector pairs revert from 2 SD.
Note: Needs a sub-sector map to pick the pairs.

### OPT-H54 · Expectancy screen · NEEDS_BUILD
High in-sample expectancy keeps working out of sample.
Note: Testable on our own ledger once enough systems have both dev and validation trade logs; a later check.

### OPT-H55 · Charges eat option sellers' profits · DESCRIPTIVE
For a typical index-option round trip, the share of total cost that is statutory (STT, exchange, GST, stamp, SEBI) versus brokerage, from the cost model; and the cost as a share of the gross on the F01 short straddles. His figures: statutory ~88% of cost; costs 10-20% of gross profit.

### OPT-H56 · Stop-limit versus stop-market · NEEDS_DATA
Stop-limit buffers in fast spikes.
Note: Needs tick and order-book data.

### OPT-H57 · Cheap OTM options spike on expiry day · DESCRIPTIVE
On expiry days, share of options opening at Rs 5 or less whose day high reaches 8x the open, and how many close back under 2x.

### OPT-H58 · Holiday weeks decay faster · TEST
The ATM straddle's decay per session from the start of the expiry week to the expiry eve is faster in weeks shortened by a holiday.
Variants (expected sign): `NIFTY` +; `BANKNIFTY` +

### OPT-H59 · Next week's straddle sold on expiry day · TEST
On each weekly expiry day, sell the next expiry's ATM straddle at the close; buy back at the next open, or at the next close. Earns more than zero.
Variants (expected sign): `NIFTY|next_open` +; `NIFTY|next_close` +; `BANKNIFTY|next_open` +; `BANKNIFTY|next_close` +
Note: He sells around 15:00; the close is the nearest end-of-day price.

### OPT-H60 · Nifty P/E zones · NEEDS_DATA
Buy at P/E 18-19 or lower.
Note: No Nifty P/E history in the lake (NSE publishes it; a fetch is needed).
