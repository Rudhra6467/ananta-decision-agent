<!-- Trading Knowledge Library · Trade With Trend (Raunak A, India). Built 2026-10-16 from 158 public videos with captions (of 287 on the channel; members-only videos were not used): one structured note per video (Claude Sonnet 5.5) -> this chapter (Claude Opus 5.5), src/research/library.py. Paraphrased; the transcripts stay on the laptop. Evidence class: external teaching = hypotheses to test, never Ananta rules; nothing in the agent reads docs/library/. -->

# Bases and breakouts

## 1. What he teaches and how it fits

Raunak's core long-side idea is that strong trends move in steps: an advance, a pause or base, then a fresh breakout. He likens it to trekking uphill with rests, or a "tennis ball" that drops a little and bounces higher [1jsLESmVLVU, mim7ylyaN74, eeKRfAbbvZA].

His job is to:
- find a recognisable base (volatility contraction/VCP, cup and handle, flag, Wyckoff-style accumulation range);
- check where it sits (near highs, at the 50 DMA or 30-week MA, with rising relative strength in a strong sector);
- judge the breakout by candle range, close location, volume and follow-through;
- decide whether to buy the breakout, scale in, or wait for the retest.

His tools changed over time:
- **About 13 years ago:** market-profile filters for breakouts.
- **About 5–8 years ago:** Heikin Ashi, Wyckoff, DeMark (TD) lines, Renko, Ichimoku and gap rules.
- **Last 1–3 years:** almost entirely the O'Neil / Minervini / Weinstein vocabulary (VCP, bases at the 50 DMA or 30-week MA, RS breakouts). He says he adopted VCP around 2013–14 [1jsLESmVLVU].

The base-and-breakout setup is the main entry engine. It sits downstream of his trend, relative-strength and sector work, and upstream of position building and stops. Everything below is his claim or method and should be treated as a hypothesis to test.

## 2. The ideas

### 2.1 The structural premise: trend, pause, breakout

**What it is.** He buys a stock that has already trended, then paused, then broken out again. He does not buy an arbitrary day inside a trend [1jsLESmVLVU].

**Second breakouts.** A second breakout from a consolidation inside an established uptrend, with no bearish supply candle afterwards, is treated as a strong trend to hold rather than fade [eeKRfAbbvZA].

**Repeated bases.** Multiple stages can occur on the same stock over time: contraction, then flag, then breakout [VET4JHrc2vU]. Base-on-base and stage-on-stage structures are among his accepted patterns [uw5QQOenJnQ].

**Range breakouts preferred to V-shapes.**
- Breakouts out of a range are more rewarding. If the structure is V-shaped, he reduces size [2crnCCz4Y3s].
- Later he says V-shaped recoveries usually do not give good forward returns, and he requires a VCP, cup and handle or flag instead [20BxPDdAZAE].
- In 2017–18 he preferred long horizontal accumulation ranges (his examples ran 4–6 years) over V-shaped recoveries from markdowns, which he calls hard to time [Bqp9jKQCs30].

**Patterns need not be textbook.** He says textbook patterns rarely appear. He accepts look-alikes with the same psychology, such as rounding bases and long contractions [mR0HMssJek8, Tkx2xIboYsw]. This is important for coding: his recognition is partly discretionary.

**How often.** This is a constant theme across all eras.

### 2.2 Volatility contraction (VCP) and tightness

**What it is.** A trending stock consolidates in progressively tighter contractions, then breaks out, ideally on a volume spike [1jsLESmVLVU, mim7ylyaN74, T4849hhdwTo]. He says he prefers it to cup and handle and uses it on stocks and index futures [1jsLESmVLVU].

**The most concrete numbers he gives** are successive pullback depths, each shallower than the last:

| Market | Pullback depths | What followed |
|---|---|---|
| Nifty Bank | about −12%, −9%, −8.7% | — |
| Metals | about −36%, −24%, −11% | breakout |
| Realty | contraction | breakout, then retest |

[Y4TewQHVhvc]. Other details:
- SBI is cited as a three-contraction base [BhQ_YnaRqa0].
- Multi-year contractions also count: 3–4 years [V41BUpPK3E4], about 1.5 years for pharma [0Hnffbj5pgE], about 15 months for the India manufacturing index [SuYHqw5zA8U].
- He says longer contractions take time and should not be judged over days [SuYHqw5zA8U].

**Daily-range compression.**
- Tightening daily candle ranges precede an explosive move, more often in the direction of the prevailing trend, though "sometimes it backfires" [g3mcqf6rqoc].
- Higher lows inside a contracting range are a favoured variant. He reports flagged names rising about 8–12% in 7–8 days, a self-reported result [g3mcqf6rqoc].
- Two or more consecutive inside days are a context clue that a range break with momentum is coming, not an entry rule [LahSe1vu1kY].

**Mother-candle variant.** A wide-range "mother" candle followed by smaller candles inside its range, then a break [CXJZMbE_d5o, Y4TewQHVhvc]. Details:
- **Weekly example:** Amara Raja valid on a weekly close above about 850 [CXJZMbE_d5o].
- **Monthly version:** a master candle with 2–4 inside months, then a breakout targeting a 2–4 month trend [mRAndF9wyaA].
- The monthly breakout candle must be long-range, close near its high, have little upper wick and carry substantial volume. He rejected Adani Ports in 2016–17 for a weak breakout candle [mRAndF9wyaA].
- On Nifty Bank's monthly chart he wanted price to hold above the high of a doji-like inside candle (about 47,255–47,374 per the captions) [Y4TewQHVhvc].

**Coil spring (older, more precise geometry)** [VqoLpEvre04]:
- Three down-swings (A–B, C–D, E–F), each smaller than the last.
- Lows B, D and F roughly equal; a resistance line joins highs A, C and E.
- Buy the break of the A–C–E line, or wait for wide-range Heikin Ashi candles after the break.
- Minimum duration 1 month; ideal 1–3 months, which he says gave his best reward-to-risk.
- Preferred variant: F above B and D (rising triangle), which he rates highest-odds.
- If A is much higher than C and E, he uses the C–E line as the trigger.

**Clarity and frequency.** VCP is taught very often in recent videos, but the notes never give a full coded definition: no maximum final contraction width, no required number of contractions, no minimum base length. The coil spring is the most rule-like version but appears in one older video.

### 2.3 Where the base sits: moving averages, highs, first base

**Moving-average anchors.**
- Positional traders look for a base or contraction near the 50 DMA; investors near the 200 DMA. He credits Livermore, O'Neil and Weinstein [Oq4FjWEDbd0].
- Many recent examples are contractions at the 50 DMA [S--7ta4FmbY, VCNsjVuGoWQ, rbSj4pOg3_I, sIo5XQqZ0b0, T4849hhdwTo, SuYHqw5zA8U, r63sarc_qV8].
- On weekly charts he prefers bases centred on the 30-week MA [NUDjIohACWs, lRUDp336l7Q, CFJNeCPMQ1o]:
  - Mastek, a base whipsawing around the 30-week MA, is the good case.
  - A base below it (Tech Mahindra) draws a mild caveat.
  - No base at all (Mphasis) means avoid [NUDjIohACWs].
- Citing O'Neil, he says many weeks of tight index consolidation above the 30-week (about 200-day) average is rare and often precedes a large move [kwbfXjRtEkk].
- Sector-index version: two consecutive weekly closes above the 30-week MA, with RS turning up and a DeMark trendline break [lRUDp336l7Q].
- In one recent video the chart showed a 30-period average while he said he meant the 50 [YFsvQXZZt1g].

**Distance limits.**

| Limit | Source |
|---|---|
| For a breakout after a pullback near the 50 DMA, buy within about 3–5% of the 50 DMA; not once the stock is 10% above it | [S--7ta4FmbY] |
| A fresh breakout about 7% above the pivot beats one already about 30% up | [6fowSBDs3eY] |
| Buy the first base; a later base after a 120–130% advance has poor reward-to-risk | [mR0HMssJek8] |

**Near highs, not far below.**
- Stocks near all-time highs break out sooner because there is no overhead supply. Stocks 40–60% below their highs face trapped sellers on every rally [Jpu536_AmGc, V41BUpPK3E4].
- His watchlist is only stocks near 52-week or all-time highs, breaking out of sound bases of at least 7–8 weeks [KRoie4cj5TQ].
- Fundamentally screened stocks still need a clean breakout or a 52-week/all-time high after the index bottoms [hpbDmEK-FvM].
- A multi-year resistance zone that has not been crossed is a negative. HDFC Bank at about 1,620–1,760 is his example [BhQ_YnaRqa0].

**Partial contradiction on extension.** One video says buy the first base only [mR0HMssJek8]. Another approves scaling into KPIT after it was already about 100–120% above its 52-week low, arguing high-looking stocks keep rising while the broad trend is strong [KRoie4cj5TQ]. A third treats continuation structures as tradeable even when extended from the 50 DMA [T4849hhdwTo].

### 2.4 Cup and handle

**What it is.** A rounded cup, a small handle, then a breakout. He wants volume watched while the cup's sides form and a clear volume spike at the breakout, where he enters [1jsLESmVLVU].
- He says it works on daily as well as weekly charts [mim7ylyaN74].
- He uses a 30-minute version: a deeper retracement then a shallower one, read as strengthening demand. TCS resistance was about 2,750–2,760 [Tkx2xIboYsw].

**Index and sector use.**
- Weekly-or-longer cups on Nifty Midcap 100 and Nifty 500 are bullish once validated. He stresses that validation does not mean immediate momentum; price can consolidate for months [yEKNcJ4EH0U].
- Sector cups: defense, tourism, finance, rare earth [Yxo-rYOCuAo, L-PGsMh2vHw, rbSj4pOg3_I].
- He admits the defense index's short history made its base look V-shaped [L-PGsMh2vHw].
- A cup and handle inside a Nifty flag triggered on 14 Feb 2024 [Pm_1kb8Fku0].
- Lw6h6T30VvE builds a watchlist from cup and handle plus contraction plus volume plus RS. Its reported returns were selected after the fact, and the captions are garbled.

**Clarity.** It is named often, but the notes contain no rules on cup depth, handle depth, handle position or duration. One video uses the pattern only as a process-focus illustration and gives no rules [NYWbbvaJnPc].

### 2.5 Flags and flat bases

**Flat or flag pattern.** An uptrend, then a sideways pause in which weak holders exit, then a breakout. He says professionals buy near the breakout, not inside the pause. IndusInd consolidated about 12–13 days, then moved about 4% [1jsLESmVLVU].

**High tight flag (O'Neil).** A flag breakout within 3–5 weekly candles [dERi8MUU5es].

**Other uses.**
- Flags breaking out to new 52-week highs after volume dries up [VET4JHrc2vU].
- When an index breaks out of a flag, check its constituents for the same pattern [q26J58h5Qt8].
- A long monthly flag in the midcap 150 index [rbSj4pOg3_I].
- Members' examples include horizontal flags and ascending VCPs [T4849hhdwTo].

**Clarity.** Thin. Only the high-tight-flag duration is numeric.

### 2.6 Wyckoff accumulation (bottoming bases)

**What it is.** A taught sequence from one detailed older video [K06GqbJwEv4], with a follow-up on post-breakout trend quality [tTdy5srpW9Q]. It applies after a strong momentum downtrend (lower highs and lower lows, no consolidation). His reading tools are candle spread and volume only.

**Phase A**
- **Preliminary support (PS):** a wide bullish candle on high volume, often tailed.
- **Selling climax (SC):** a bearish candle on a volume spike. A more intense climax makes the lows more likely to hold.
- **Automatic rally (AR):** rebounds to about the PS area.
- **Range:** the top is a line from the PS candle's close; the bottom is the SC low area.

**Phase B**
- The secondary test of the SC low should come on average or lower volume and an average range.
- Volume and range shrink through the phase.

**Phase C**
- **Spring:** a brief undercut of the SC low that reverses quickly, on low volume. It is optional.
- If the undercut comes with expanding volume and wide candles, expect further decline.

**Phase D**
- **Jump:** a move above range resistance, ideally on wider spread and higher volume. He accepts it sometimes comes without volume.
- **Sign of strength (SOS):** wide-range up candles on rising volume.

**Phase E**
- Check candle range, closes near the high, and short tails.
- Many SOS candles plus last-point-of-support (LPS) pullbacks mean the up-move has begun.

**Entry**
- Buy the first LPS.
- If price goes vertical with no LPS, buy 50% on the volume-expanded breakout and 50% on the LPS test [K06GqbJwEv4].

**Case: Bank Nifty, 2018–19.**
- Range about 24,200–25,500.
- The breakout came without volume, so he advised waiting for the LPS.
- Price reached about 27,000, roughly 1:1, which he attributes to the missing volume [K06GqbJwEv4].

**Post-breakout trend quality** [tTdy5srpW9Q]:
- Bullish candles closing near highs should dominate and bearish candles should be few and narrow. His example: 31 strong bullish versus 5 relevant bearish candles over the first 15% of a move.
- A rise steeper than about 45–50° tends to continue; falling below the 45° line suggests taking profits. This is scale-dependent and would need converting to a rate of change.
- Volatility should fall and the first retracement should be negligible.
- Bharti Airtel is his counter-example: flat volatility and a retrace to the breakout point.

### 2.7 What a healthy base looks like inside

- **Indecision, not supply.** Mostly indecision candles (wicks, small bodies), few bearish candles, and volume drying up on the drift lower. He reads this as strong holders not exiting [jBYC0t30fz8].
- **Bearish candles without follow-through,** then a wide-range bullish candle on volume above the last 20–25 sessions [4CzLWJxP4UM].
- **Count initiation candles before trading a long range break.** In gold's roughly 6-month triangle, bullish wide-range Heikin Ashi candles dominated before the June 2019 break [FtxgOtPYqVA].
- **Selling exhaustion.** Narrow candles and rare bearish candles near support after a decline. He still wants a range-high break to confirm (TCS above about 2,700) [CXJZMbE_d5o].
- **Repeated long lower tails** above an unfilled weekly gap read as persistent demand [Tkx2xIboYsw].
- **A suspect up-move.** Price up about 8% with no initiation candles, narrow bullish candles and wider bearish candles. He reads this as sellers in control [L99LgSdCDD8].
- **Profile version (older).** Before trusting a range breakout, check prior profiles for net upside range extensions, buying tails and value areas trying to rise [cDcvc9esnwo].

### 2.8 Range length and zones

**Minimum duration.**

| Minimum | Context | Source |
|---|---|---|
| 7–8 weeks | Base before breakout | [KRoie4cj5TQ] |
| 1–3 months | Coil spring | [VqoLpEvre04] |
| At least 1 month, ideally 1.5–2.5 months | Renko ranges; about 20 days is "weak" | [Mf7ZD9MY7vI] |
| About 10 days | Accepted as a breakout range | [p6pwKWQgxUw] |

These thresholds differ by video and are not reconciled.

**Renko method** [Mf7ZD9MY7vI]:
- Brick size at least 0.5% of price; preferred 0.5–1%.
- Smaller bricks (0.3%) or 5–15 minute charts produce many false double-top and support signals.
- Exit from a month-plus range is the signal, up or down.
- Examples (selected after the fact): Bank Nifty, the S&P 500 on 60-minute, Tata Steel 2019.
- He claims this beats three-touch trendlines.

**Zones, not lines.**
- Support forms where price spent the most time, not at the single extreme low. His example zones are about 5–7% wide.
- Wait for a decisive move clear of the whole zone before calling a breakout [d7cwBnW78XI].
- Profile version: read resistance at the prior value area rather than the swing high. Enter when price leaves the overlapping value area [uFFAAZNSozg].

### 2.9 The breakout itself: trigger and quality checks

**Trigger.**
- Price moves above the top of the contraction or range [Oq4FjWEDbd0, p6pwKWQgxUw].
- A decisive close above a falling TD supply line [Vz5lqc_RO7M].
- A close beyond a weekly or monthly level for higher-timeframe patterns [CXJZMbE_d5o, mRAndF9wyaA].
- "Decisive" is never quantified.

**Volume.** He repeatedly says a breakout needs substantially higher-than-normal volume [1jsLESmVLVU, N5bb0Cu8RAs, Tkx2xIboYsw, mim7ylyaN74, uw5QQOenJnQ]. The benchmark varies by video:

| Volume benchmark | Source |
|---|---|
| Above the prior 5 sessions | [1jsLESmVLVU] |
| Above the 20–25 session average | [4CzLWJxP4UM] |
| A clear spike above the 50-day volume average; then about average during the next consolidation, contracting before the next breakout | [N5bb0Cu8RAs] |

His ORB study claim: failed opening-range breakouts shared low breakout-bar volume [hk4d8AxbQ3A].

He is not absolute about volume. The Wyckoff jump may lack volume, but he then waits for the LPS and expects a smaller move [K06GqbJwEv4].

**Candle.**
- Wide range with a close near the high. A long upper wick means supply, so skip; a small wick is fine on a very wide candle [p6pwKWQgxUw].
- Widest high-low range of the last 20 sessions plus clear volume expansion [jBYC0t30fz8].
- A failed example had a wide candle with a long upper wick on huge volume, closing well below its high [mR0HMssJek8].
- Wide-range bullish candles above resistance, with breaks of long-term resistance described as especially positive [Ux_uuOj-gKs].
- No numeric wick or close-location thresholds are given.

**Relative strength.**
- His three-part checklist: strong candle, expanded volume, rising RS versus the benchmark. He applied it on daily and 60-minute charts [p6pwKWQgxUw].
- Price and RS line breaking out together is "very reliable." Berger Paints: price out of a 16-month base, RS above a 24-month high [Ux_uuOj-gKs].
- Reliance broke about 3 years of resistance in April 2017 with RS doing likewise, above the 50-week MA [Ux_uuOj-gKs].
- RS strong over the prior 4–5 months [Oq4FjWEDbd0].
- Recent template: clean base, above the 50 DMA, rising RS, sector heading higher [sIo5XQqZ0b0, kwbfXjRtEkk, rbSj4pOg3_I].

**Sector participation.** He checks whether other stocks in the sector are also moving [mim7ylyaN74, 4CzLWJxP4UM].

**Follow-through.**
- Several consecutive up days after leaving the base, more being better, on rising volume, which he reads as institutional buying [NUDjIohACWs, VET4JHrc2vU].
- Quoting O'Neil, the best trades are profitable right away [VET4JHrc2vU].
- A tight sideways hold at the breakout level for 3–4 weeks reads as supply absorption (SBI) [BhQ_YnaRqa0].

**Overhead supply.**
- Older profile rule: skip a breakout above a high-volume node (HVN) if another HVN sits 2–3% above.
- The HVN must come from at least 30 days of trading with a prominent volume skew.
- The breakout candles must be wide and strong [p03ho_Rhc_E].
- Prior breakdown zones and gaps act as hurdles [KUlNy1_Rk9M].

### 2.10 Entry timing: breakout, scale-in, cheat entry, or retest

This is his most internally tense topic.

**Buy the breakout.**
- He enters cup-and-handle breakouts at the breakout [1jsLESmVLVU].
- Contraction-high breaks near the 50 DMA, accepting that they can fail [Oq4FjWEDbd0].
- The coil spring at the line break [VqoLpEvre04].

**Do not chase; wait for the retest.**
- He says over 65% of breakouts initially fail. This is an unsourced claim. Breakout-candle buyers get poor trade location and are shaken out on the pullback [-SC5vcQ1NuE].
- Odds of failure are highest right at the breakout, so build slowly [C8IZozIkPJY].
- Buying breakouts more often than not gets you in trouble, while buying pullbacks rarely does, if done well [mim7ylyaN74].
- After a wide-range, higher-volume break of a multi-month range, wait for the pullback to old resistance (now support) and buy only if strength reappears [4CzLWJxP4UM].
- Two or more long-lower-wick candles holding just above the broken resistance are a positive watch-list sign [4CzLWJxP4UM].

**Scale in.**
- Retail traders should take a starter position at the breakout and add on a pullback in the established trend [sbHzNd2iA8k].
- Wyckoff 50/50 split [K06GqbJwEv4].
- Members' probe-then-add examples (EMS, 19 July probe, 23 July add) [T4849hhdwTo].
- Slow accumulation in a market where rallies are being sold [iWa7MbGawvU].

**Cheat pivot (Minervini).** Enter inside the base before the formal pivot. It is aggressive and better in strong markets. The Bank Nifty example levels are unclear in the captions [1jsLESmVLVU].

**Retest logic.**
- Old resistance becomes support [jBYC0t30fz8, -SC5vcQ1NuE, Tkx2xIboYsw].
- A multi-week consolidation broken with a wide, high-volume candle becomes a demand zone [dV4MiNaAenI].
- Acceptable states for a stock: broken out, threatening to break out, or broken out and retesting [V41BUpPK3E4].
- Profile version: buy the bounce back above the prior HVN [su1cu2Y3AXA].

**Lower-timeframe triggers.**
- 30-minute break above a daily demand zone once 30-minute structure turns to higher highs and higher lows. Example: entry about 1,350–1,360, stop about 1,300 at the zone low [1klATqC7oks].
- 60-minute pivot break after a daily divergence; skip if price has already run [cQpU-EnhdSw].

**Stops.**
- At the nearest pivot. About 10% was acceptable positionally (MCX) [T4849hhdwTo].
- At the zone low [1klATqC7oks].
- Thin overall in this chapter.

**Change over time.** The "don't chase, buy the retest" videos cluster around 3–5 years ago. Recent videos also add regime caveats (2.11) rather than a blanket preference.

### 2.11 False breakouts and the regime filter

**Definition.** Price moves beyond resistance, fully reverses and traps buyers. He calls this the main reason traders abandon breakout methods [p6pwKWQgxUw].

**Undercut principle (O'Neil).** A pivot can be undercut and then rally (a shakeout), or exceeded and then reversed. A single break or reclaim is not conclusive [8QeR8FmYYg4].

**Market regime.** Recent videos add this repeatedly:
- In a weak market even a small index breakout tends to fail. Nifty IT is his example [M4Z-Gi4gGag].
- In a "broken" low-breadth market, a clean defense contraction breakout fully retraced [Sb6KTt64YKE].
- Chasing breakouts is not working in a non-momentum market; holding good structures paid. He cites his portfolio up about 3–4% in 15–30 days [CFJNeCPMQ1o].
- The broad index was in a long contraction where the end is hard to predict, hence breadth matters [6GqBBVt6fUs].
- An older profile video warns that high-volatility breakouts, especially in bear markets, can turn into open-rejection reversals. He suggests protective options [dUeQOEU6FlQ].

**His own failed calls.** He read Bank Nifty as a classic contraction at the 50 DMA, expected an upside resolution, and saw it break below its pivot. He says the structure read was right but timing was wrong, and that such setups fail sometimes [r63sarc_qV8, rhiXs5Kh_0g]. In another recent video he still calls Bank Nifty's tightness bullish, with a breakout area of about 58,000–58,800 [YFsvQXZZt1g].

**Other filters.**
- A higher-timeframe trend filter for 15-minute cloud breakouts [59vJPo6oiNA].
- Index-level confirmation [T4849hhdwTo].
- Read weak signals against the overall market [_AiSzhs67J4].

### 2.12 Short side (thin)

- Stage 3 tops form a defined range or triangle; short the break below it together with the 150-day average [G2gjQUJRfJM].
- Mirror candle rule: avoid shorting a breakdown candle with a long lower tail [p6pwKWQgxUw].
- Renko range breakdowns, such as one of the Tata Steel ranges [Mf7ZD9MY7vI].
- TD supply and demand lines are symmetric [1FA93wpDNq4].
- Gaps, ORB and outside bars are symmetric (2.13).
- He says bullish outside bars work better than bearish ones because of markets' upward bias [_AiSzhs67J4].
- There is no short-side base taxonomy comparable to the long side.

### 2.13 Older trigger toolkits that bear on breakouts

These are mostly from single older videos, are more mechanical, and were not repeated recently.

**DeMark TD lines** [1FA93wpDNq4, Vz5lqc_RO7M]
- A TD point's level is the minimum of the left and right counts of consecutive lower highs (or higher lows).
- Join only two points, of the same level, drawn right to left from the most recent point.
- He claims this cuts whipsaws.
- Entry is a decisive close above a falling TD supply line.
- Gap-over case: project from the line contact point. Example: 5,730 + 300 points = 6,030 target.

**Ichimoku Kumo breakout**
- Long valid only when price is clearly above the cloud and both Senkou A and B are rising, with Chikou above price and Tenkan and Kijun rising [2crnCCz4Y3s].
- His short-term version requires all four of volume, RS, Tenkan/Kijun trend and Chikou position, and says Senkou A/B may be flat or falling [xzR6bwNgb18]. This is an explicit difference between positional and short-term rules.
- 15-minute version: stop at Senkou B. Skip weak breakouts (falling cloud, fading volume, red breakout candle, resistance just above) and prefer a green cloud with a wide candle clearing the prior pivot [59vJPo6oiNA].
- Skip when the cloud, Kijun and Chikou are flat [153pJZk-ixo].

**Opening-range breakout and initial balance (IB)**
- ORB uses the first 15- or 30-minute candle; failures shared low volume [hk4d8AxbQ3A].
- IB extension suggests the other-timeframe trader is present [z-ae7tLVdoo].
- A narrow IB favours breakout signals; a wide IB suggests a non-trend day [4kP0_EuS_EY, z-ae7tLVdoo].
- An open above the prior value area and range favours taking the breakout. An open inside it with low volatility means wait, or watch whether the first 2–3 half-hour periods leave the range [dUeQOEU6FlQ].

**Gaps** [HHkcCy5LrCM]
- Trade only runaway/breakout and continuation gaps, on 30- or 60-minute charts. The gap must exit a defined range.
- Gap candle range above about 0.8–1%, closing near the extreme.
- Gap window up to about 1–1.5%; wider gaps fill more often.
- Stop looking after a run of about 10–15% (index) or 20–25% (stock).
- Weak gap candles call for small starter positions.
- He also notes holding runaway gaps on the Nasdaq above the 50 DMA [sIo5XQqZ0b0].

**Heikin Ashi**
- Initiation candles need continuation candles [L99LgSdCDD8].
- Three expanding same-colour candles form a trending pattern [L99LgSdCDD8].
- Green candles with no lower shadow mean hold or add [uqEFppHC4Jw].
- Heikin Ashi makes patterns cleaner [uqEFppHC4Jw].
- Never use it without prior breakout and support/resistance levels [e34G88-BKI4].
- Double bottom on falling momentum: wide candles at the first low, narrow at the second; skip if candles expand on the approach [IHqkSPVCxko].

**Reversal bars**
- **Weekly outside bar:** needs a prior trend of at least 6–10%. Enter on the weekly close, invalidated below the bar's low [_AiSzhs67J4].
- **Kicker:** two strong opposite candles after a trend [QWcb7yxYAxk].
- These are reversal tools rather than base breakouts.

**Elliott wave rules and corrective forms** [JMZFlzfNOCQ, KvhIh2rU0R0] appear only as structural background. The notes do not link them to breakout entries.

## 3. How a program would test it

1. **Breakout-quality filter.**
   - **Event:** daily close above the prior N-day high, or the top of a base of at least 35 trading days (7 weeks).
   - **Filter, all required:**
     - breakout-bar range is the widest of the last 20 sessions;
     - volume is at least 1.5× the 50-day average;
     - close is in the top 25% of the bar;
     - upper wick is no more than 25% of the range.
   - **Compare to:** unfiltered breakouts.
   - **Outcomes:** failure rate (close back below the pivot within 5 and 10 sessions); 20- and 60-day forward return.
   - **Data:** daily OHLCV, survivorship-free.
   - **Sources:** [jBYC0t30fz8, N5bb0Cu8RAs, p6pwKWQgxUw, mR0HMssJek8, hk4d8AxbQ3A].

2. **The 65% initial-failure claim, and breakout versus retest entry.**
   - **Measure:** the share of breakouts that return to the pivot within 5, 10 and 20 sessions.
   - **Compare three entries:**
     - (a) breakout-day close;
     - (b) first retest within 1–2% of the pivot, followed by a bullish close;
     - (c) 50% at (a) plus 50% at (b).
   - **Outcomes:** expectancy in R, maximum adverse excursion, and the miss rate of strategy (b).
   - **Sources:** [-SC5vcQ1NuE, C8IZozIkPJY, 4CzLWJxP4UM, sbHzNd2iA8k, K06GqbJwEv4].

3. **Base location and extension.**
   - **Condition:** contraction with low within 5% of a rising 50 DMA, versus bases far from it.
   - **Entry buckets:** within 5% of the 50 DMA versus 10% or more above it; within 7% of the pivot versus 30% or more.
   - **Second split:** first base after a 52-week low versus bases after a 100%+ advance.
   - **Sources:** [Oq4FjWEDbd0, S--7ta4FmbY, 6fowSBDs3eY, mR0HMssJek8, KRoie4cj5TQ].

4. **VCP definition test.**
   - **Condition:** at least 3 successive swing pullbacks, each shallower than the last, with the final one under about 10%, then a close above the base high.
   - **Compare to:** non-contracting bases of the same length.
   - **Data:** daily OHLC plus a zig-zag swing detector with a fixed percentage threshold.
   - **Sources:** [Y4TewQHVhvc, 1jsLESmVLVU, VqoLpEvre04].

5. **Proximity to highs.**
   - **Compare:** base breakouts within 5–10% of the 52-week or all-time high, versus breakouts or bounces in stocks 40% or more below their high.
   - **Horizon:** 1–6 months.
   - **Sources:** [Jpu536_AmGc, KRoie4cj5TQ, V41BUpPK3E4].

6. **Regime dependence.**
   - **Measure:** failure rate and 20-day return of breakouts, split by:
     - the benchmark above or below its 50 and 200 DMA;
     - the share of stocks above their 200 DMA (below 25%, 25–60%, above 60%).
   - **Data:** constituent-level breadth history.
   - **Sources:** [M4Z-Gi4gGag, Sb6KTt64YKE, CFJNeCPMQ1o].

7. **RS co-breakout.**
   - **Compare:** price breakout to a 52-week or multi-month high with the RS line (stock divided by benchmark) also at a new high of the same lookback, versus price-only breakouts.
   - **Sources:** [Ux_uuOj-gKs, p6pwKWQgxUw, Oq4FjWEDbd0].

8. **Follow-through and range-duration rules.**
   - **(a) Follow-through:** breakouts with above-average volume and net gains on 3 of the first 5 days, versus others; measure 20–60 day returns [NUDjIohACWs, VET4JHrc2vU].
   - **(b) Renko ranges:** ranges of at least 1 month on 0.5% bricks versus ranges under 20 days; sweep brick sizes of 0.3%, 0.5%, 0.75% and 1% [Mf7ZD9MY7vI].

## 4. Transfer

**Applies to TSX and US as is.** These are pure price and volume logic:
- trend–base–breakout;
- contraction and pullback-depth logic;
- coil spring;
- the candle-quality rules (range, close location, wicks);
- the volume-versus-average rules;
- the retest and old-resistance-as-support idea;
- the 50 DMA / 30-week MA base location and extension limits;
- the near-highs preference;
- TD lines;
- Renko percentage bricks, which are scale-free;
- Wyckoff phase reading;
- Heikin Ashi rules.

He himself cites US sources (O'Neil, Minervini, Weinstein, Bulkowski) and applies the ideas to the S&P 500 and Nasdaq [Mf7ZD9MY7vI, sIo5XQqZ0b0].

**Needs adapting.**
- **RS benchmark:** Nifty 50/500 becomes the S&P/TSX Composite, the S&P 500 or the Russell 3000.
- **Sector confirmation:** use GICS sector and industry ETFs or indices. TSX sub-indices are concentrated in a few names, so sector "participation" is a weaker signal there.
- **Volume thresholds on the TSX:** many names are thinly traded, so volume multiples need a liquidity floor and possibly consolidated (multi-venue) volume.
- **Gap rules:** the 0.8–1% range and 1–1.5% window thresholds should be volatility-scaled. Hourly-bar gap definitions differ with US pre- and post-market sessions [HHkcCy5LrCM].
- **Intraday tools (ORB, IB, profiles):** need session-specific timing, 9:30 ET opens and intraday data.
- **IPO-base ideas:** need a recent-listings universe; there is no direct Nifty IPO index equivalent [r63sarc_qV8, SbtFCxbIB1w, T4849hhdwTo].
- **Costs:** retest and scale-in strategies trade more often and should be costed.

**India-only.**
- Specific levels: Bank Nifty 31,600, 24,200–25,500, 58,000–58,800; Nifty 500 21,900.
- Stock-specific examples.
- The remark that India offers few hedging instruments besides options [dUeQOEU6FlQ].
- His current-regime market calls.

## 5. Gaps and doubts

**Undefined patterns.** VCP, cup and handle and flags are his most-cited bases, yet the notes give no complete coded definition:
- no handle depth;
- no maximum final contraction;
- no required contraction count;
- no base duration, except 7–8 weeks [KRoie4cj5TQ] and the high tight flag's 3–5 weekly candles [dERi8MUU5es].

He openly accepts non-textbook look-alikes [mR0HMssJek8], so his live recognition is discretionary.

**Unquantified words.** "Decisive," "wide range," "long wick" and "substantial volume" are never given numbers. The volume baselines differ by video: 5 sessions, 20–25 sessions, 50-day average.

**Inconsistent thresholds.** Minimum range lengths vary from about 10 days to 7–8 weeks to 1–3 months.

**Contradictions.**
- **Breakout versus pullback entry:** he enters at the breakout [1jsLESmVLVU, Oq4FjWEDbd0] but also says breakouts mostly fail and pullbacks are safer [-SC5vcQ1NuE, mim7ylyaN74, 4CzLWJxP4UM].
- **Extension:** first base only [mR0HMssJek8] versus buying stocks already doubled [KRoie4cj5TQ, T4849hhdwTo].
- **Ichimoku Senkou slope:** required [2crnCCz4Y3s] versus not required short-term [xzR6bwNgb18].
- **Volume:** described as mandatory, yet accepted as absent in the Wyckoff jump [K06GqbJwEv4].

**Unsupported statistics.**
- The 65% breakout-failure figure is unsourced [-SC5vcQ1NuE].
- Reported gains (8–12% in 7–8 days; 37–40% in a month; 50% to over 1,000% watchlist returns) are self-selected, often after the fact. Some come from garbled captions [g3mcqf6rqoc, rbSj4pOg3_I, Lw6h6T30VvE].

**Unclear captions.** Cheat-pivot levels [1jsLESmVLVU], Nifty Bank monthly levels [Y4TewQHVhvc], regular-flat wording [KvhIh2rU0R0], and a 30- versus 50-period average mix-up [YFsvQXZZt1g].

**Regime caveat versus repeated calls.** His recent Bank Nifty contraction call failed by his own admission [r63sarc_qV8, rhiXs5Kh_0g], while another recent video repeats a similar bullish tightness read [YFsvQXZZt1g]. He gives no rule for when a regime is good enough to trade breakouts beyond qualitative "weak or broken market" language.

**Not covered here.** Little on:
- stop placement (beyond pivot or zone low, about 10%);
- position sizing (beyond 50/50 and starter-then-add);
- exits and targets after a breakout (only the TD projection and the 45° line);
- time stops;
- what to do when a retest fails.

The short-side base taxonomy is essentially absent. The Elliott wave, kicker and outside-bar material is marginal to bases and breakouts.
