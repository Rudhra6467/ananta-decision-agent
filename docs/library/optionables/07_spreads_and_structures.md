<!-- Trading Knowledge Library · Optionables (Optionables, India). Built 2026-10-16 from 434 public videos with captions (of 459 on the channel; members-only videos were not used): one structured note per video (Claude Sonnet 5.5) -> this chapter (Claude Opus 5.5), src/research/library.py. Paraphrased; the transcripts stay on the laptop. Evidence class: external teaching = hypotheses to test, never Ananta rules; nothing in the agent reads docs/library/. -->

# Spreads and structures

## 1. What he teaches here and how it fits

Optionables is mainly a premium seller. His core book is short straddles and strangles on Bank Nifty and Nifty, and later on Bitcoin daily options. Multi-leg structures do three jobs in that method:

- **Shaping a directional tilt into a short-premium book.** Ratio spreads are the most heavily taught structure, entered for a net credit.
- **Replacing naked option buying for small-capital directional traders.** These are vertical debit spreads.
- **Capping or reshaping the risk of short straddles.** These are wings or iron flies, and calendars or diagonals with a longer-dated long leg.

The weight shifts over time:

- **About 6 years ago** he waved off a ratio-spread idea and kept to simple shorts [cA07gugsaeY].
- **About 4–5 years ago** he taught bull call spreads, straddle calendars and many live ratio spreads.
- **About 3 years ago** he published his most systematic ratio-spread rules: net credit, 1:2 preferred, month-end over weekly.
- **About 2 years ago** he recommends ratio spreads mainly for gap-prone or event regimes.

Everything below is his claim or method, to be tested. None of it is established fact.

## 2. The ideas

### 2.1 Ratio spreads: definition and construction rules

**What it is**
- Buy one option nearer the money. Sell a larger quantity of a farther option of the same type and expiry [NSeHRFG7XVA, lkOC0gpSmQQ, 3nZVT1T90R0].
- He decomposes it into a vertical spread plus one or more naked shorts. A 1:2 call ratio is a bull call spread plus one naked short call. Only the naked part needs managing when price runs toward it [urrT8zpnGus].

**Hard rule: net credit**
- Ratio × short premium must exceed the long premium [NSeHRFG7XVA, lkOC0gpSmQQ, 3nZVT1T90R0].
- Credit example: buy the 38,000 put at ~200, sell two 37,500 puts at ~160, giving 320 in against 200 out [3nZVT1T90R0].
- Debit counter-example: pushing the shorts out to two 36,500 puts at ~84 gives 168 in against 200 out. He says that version loses even when the view is right [3nZVT1T90R0].
- Another credit example: buy the 37,000 put at 552, sell two 36,500 puts at 436 [lkOC0gpSmQQ].
- Wider spacing between long and short strikes moves the far break-even out and makes the trade safer, as long as the credit survives [lkOC0gpSmQQ].

**Ratio limits (his statements are not fully consistent)**

| Source | Ratio guidance |
|---|---|
| NSeHRFG7XVA | 1:2 to 1:4 used; avoid going above about 1:4 |
| 3nZVT1T90R0 | Prefer 1:2; do not exceed 1:3 |
| lkOC0gpSmQQ | 1:2 or 1:3 typical |

- His reason for 1:2 in 3nZVT1T90R0 is adjustability, not the payoff. The platform showed 1:3 (long 38,000, short 3×36,500) as better on paper: PoP ~96%, break-even ~35,700, max profit ~24%. He still prefers 1:2 because two naked lots are much harder to adjust than one.
- His own trades break the 1:2 preference: 1:3 on Bitcoin [VmiJLxaYPUQ, MeKx6Qh50vs], 1:3 on Bank Nifty [tbHLBk84Btc], 1:2.5 [tY0noMv3lp0], and 20:50 lots on the call side [mDW8Ih4CuuY].

**Expiry choice**
- Month-end, roughly 20–30 days out: more premium, farther strikes, and time to adjust [NSeHRFG7XVA]. Elsewhere he says use the further expiry [o7lr4TUP3Yg], or about 50 days out [lkOC0gpSmQQ].
- His explicit weekly-versus-monthly comparison [3nZVT1T90R0]:

| Version | Example | Strike gap | Net | Return | Break-even distance |
|---|---|---|---|---|---|
| Weekly | Buy 40,000 put, sell two 39,700 puts | ~300 pts max | 95-pt debit | ~0.4% | ~3.6% |
| Month-end | (38,000 / 37,500 example) | 500 pts | credit | ~2.7% | ~9.8% |
| Two months out | Buy 37,000 put, sell two 36,500 puts | 500 pts | credit | ~5% | ~12.5% |

- He argues four weekly trades (~1.6% total) are inferior to one monthly. The monthly also makes a gap-down far less dangerous.
- Contradiction in practice: in older videos he ran ratio spreads with only 3–4 trading days to expiry [tY0noMv3lp0] and in the same expiry as weekly books [WtIVfzJvJUg, mDW8Ih4CuuY]. The monthly preference is in the ~3-year-old teaching.

**Payoff shape he claims**
- It profits if the view is right.
- It makes the most if price drifts *against* the view to the short strike.
- It loses only on a large adverse move beyond the far break-even.
- He claims no other common strategy has this shape [3nZVT1T90R0, o7lr4TUP3Yg].
- Best case is a slow drift to the short strike near expiry. A sudden or mid-term move hurts [urrT8zpnGus].

**Probability of profit claims**
- He claims PoP of 70–80% is common, sometimes 90–95% [3nZVT1T90R0, o7lr4TUP3Yg].
- These are platform model numbers (Opstra/Sensibull-type payoff charts), not tested results. He admits a "near 100%" reading is not literally true [3nZVT1T90R0].

**Teaching clarity**
- High and repeated: about 20 videos touch ratio spreads.
- The rules are clearest in 3nZVT1T90R0 and lkOC0gpSmQQ.

### 2.2 Put ratio spread (bullish to neutral side)

**Construction**
- Buy 1 put at or near a support level you expect to hold through expiry. Sell 2 farther puts. Same expiry [3nZVT1T90R0, o7lr4TUP3Yg, WtIVfzJvJUg].
- Identify the trend first so the ratio's direction matches it [o7lr4TUP3Yg].

**Worked examples (Bank Nifty)**

| Video | Long | Short | Expiry / timing | Stated results | Arithmetic check |
|---|---|---|---|---|---|
| 3nZVT1T90R0 | 1×38,000 at ~200 | 2×37,500 at ~160 | Month-end | Break-even ~36,884; PoP ~93%; ~2.7% if above 38,000; ~15% max at 37,500 | Credit 120 + width 500 gives a break-even near 36,880. Consistent. |
| o7lr4TUP3Yg | 1×~41,500 at ~600 | 2×~40,000 at ~445 | Further monthly | ~1.26 lakh capital per lot; ~5% if unchanged; ~13% max; break-even ~39,200 | Stated strikes and premiums imply ~38,200, not 39,200. Strike levels were only approximate in the captions. |
| ilbYdeALr0M | 1×31,000 at ~654 | 2×30,000 | Month-end, after a sell-off | Flat ~6,000–6,600 rupees/lot above 31,000; ~31,000/lot near 30,000; break-even ~28,734 | Implies ~250 points net credit. His own size: 28 long / 56 short lots, ~1.8 lakh flat and ~8.86 lakh at the short strike. |
| lkOC0gpSmQQ | 37,000 | 2×36,500 | ~50 days (September, entered in August) | — | — |
| tY0noMv3lp0 | 1,000 qty of 34,000 | 2,500 qty of 33,500 | 3–4 trading days | ~1 lakh above 34,000; ~6 lakh near 33,500; loss below ~33,100 | Suits bullish, sideways or mildly bearish with a floor. Ratio 1:2.5. |
| mDW8Ih4CuuY | 20 lots of 34,500 | 40 lots of 34,000 | 31 March | Flat ~25,000 above 34,500; ~2.7 lakh peak | Plans to adjust before the break-even. |

**Adjustments shown**
- As the market rose, he rolled the short put strike up from 34,000 to 34,500 to 35,000. That lifted the upside break-even to ~39,000 [JqEQIQyJ-FU]. (The notes call this an upside break-even, which a plain put ratio should not have. The full position probably had other legs; unclear.)
- He then bought 40 lots of a 38,500 call (end-September) to stretch it to ~40,000, expecting ~6.5–7 lakh if the market consolidated [JqEQIQyJ-FU].
- Adjustment rules for a ratio "going wrong" were promised but are not in these notes [WtIVfzJvJUg].

### 2.3 Call ratio spread (bearish to neutral side)

**Construction**
- The mirror of the put ratio: buy 1 nearer call, sell 2–3 farther calls [o7lr4TUP3Yg, T2p11C5qPxk].

**Bank Nifty example**
- Long 20 lots of the 42,500 call, short 40 lots of the 43,000 call, October expiry [urrT8zpnGus].
- Profits on a fall, flat market or slow rise.
- Upper break-even ~43,835, about 6% above spot. That implies ~335 points of credit.

**Bitcoin example (one trade, three videos) [NSeHRFG7XVA, VmiJLxaYPUQ, MeKx6Qh50vs]**
- Spot ~19,200, about 33 days to the 25 Nov expiry.
- Long 0.5 BTC of the 23,000 call (~113). Short 1.5 BTC of the 25,000 call (~89 each, ~267 total). Ratio 1:3, net credit.
- He describes this size as 500 long / 1,500 short contracts.
- Small profit below 23,000. Maximum near 25,000, ~$2,000 at that size. Loss above ~25,800–26,000.
- Rationale: consolidation with a mild bullish bias [MeKx6Qh50vs].
- Management:
  - No adjustment while price is far away [VmiJLxaYPUQ].
  - If wrong, split it into a bull call spread plus a short call and manage the short call [MeKx6Qh50vs].

**Other call ratios**
- Long 1 of 37,500, short 3 of 38,000, September month-end. Best between 37,500 and 38,000. Initial upper break-even ~38,200–38,400 [tbHLBk84Btc].
- A long call against shorts at 37,500 and 38,000 (40 lots each), 30 Sept expiry [it9ef0_jnVY]:
  - Maximum profit at 37,500; support expected near 36,500.
  - Notes say ~4 lakh loss at expiry on a large drop, which is odd for a call ratio unless it was entered for a debit. Not resolved in the notes.
  - Adjustments: short more calls, and short puts if 37,500 breaks.

### 2.4 When to use ratio spreads (regime conditions, partly conflicting)

**Conditions he gives**
- **Consolidation.** He calls it a complementary strategy that leaves time to adjust or exit [NSeHRFG7XVA, MeKx6Qh50vs].
- **High VIX with rich premiums** [N8jDRk63lK0].
- **Gap- or event-driven volatility.** Prefer put ratios or OTM call ratios over naked shorts or an equidistant strangle, because a single 1.5–2% gap can destroy a naked short [yofu41-yyFU].
- **A trend expected out of consolidation, with direction known.** Use call or put ratios or credit spreads, not non-directional structures [xpMrVzXpW34].
- **After an index closes the week above broken resistance** (~41,700), enter at the Friday close [XA-oogDFs2s].

**Tension in these conditions**
- "Works best in consolidation" sits against "use when a trend is expected" [NSeHRFG7XVA vs xpMrVzXpW34].

**When not to use**
- Not suited to a strongly bullish view. He calls ratio spreads mostly relaxed trades [XA-oogDFs2s].
- He implies avoiding them when credit cannot be obtained [3nZVT1T90R0].

**Exit**
- Close when the market has stalled and little remaining profit is left. He then rotated into a short straddle [rEX0xkc5Fes].
- One far-expiry hypothesis note mentions a profit target of ~3–4% of capital [lkOC0gpSmQQ]. This comes from the note writer, not a stated rule.

### 2.5 Double ratio spreads

**Construction**
- A put-side and a call-side ratio together [mDW8Ih4CuuY].
- Put side: buy 34,500 ×20 lots, sell 34,000 ×40 lots.
- Call side: buy 36,500 ×20 lots, sell 37,000 ×50 lots.

**Stated payoff and management**
- Profitable roughly 33,350–37,400, about −6% to +5%.
- Peak ~70,000 to 2 lakh inside that zone.
- Adjust near 34,000 or on a break of 37,000.

**His other description**
- Elsewhere he describes a double ratio as a short strangle plus an iron condor [lkOC0gpSmQQ]. This is low clarity.

**Mixed books**
- A put ratio was used as the bullish tilt inside a book of an ATM short straddle (35,000) and a short strangle (34,000 put / 36,000 call). Quoted break-evens were ~34,100 and ~36,000 [ufH0zRUyuIw].
- Positional bullish ratios run beside a strangle got the credit for a day's profit [T1cJv2Y62FU].

### 2.6 Vertical debit spreads (long side: bull call; short side: bear put)

**Who it is for**
- Small capital plus a directional view, ideally from technicals. Not for non-directional traders; he himself prefers straddles and strangles [BB8KiSmE0ak, lkOC0gpSmQQ].

**Construction**
- Buy an ITM call, sell an ATM or OTM call, same expiry.
- Example: Bank Nifty ~35,300, buy the 35,000 CE, sell the 35,300 or 35,400 CE [BB8KiSmE0ak].
- Bearish mirror: the bear put spread [UdsdCODKv58]. He only names it; there are no worked examples.

**Strike-placement rule**
- Place the spread so its break-even sits at the level you are confident the market will hold at expiry.
- Example: shift from the 35,000/35,500 spread (break-even ~35,315) to 35,200/35,700, giving break-even ~35,500 and about 1:1 reward to risk [UdsdCODKv58].
- The spread needs the market only to *end* above a level, not to make a big move [BB8KiSmE0ak, UdsdCODKv58].

**Comparison numbers (platform estimates)**

| Comparison | Spread | Alternative | Source |
|---|---|---|---|
| Break-even vs naked 35,500 call | ~35,315 | ~35,842 | UdsdCODKv58 |
| PoP vs naked call | ~52% (break-even ~35,283) | ~32% | BB8KiSmE0ak |
| PoP vs naked 36,000 call | — | ~25% | UdsdCODKv58 |
| Example: buy 34,200 / sell 34,500 | Break-even ~34,452 | — | BB8KiSmE0ak |
| Deep ITM, month-end: 32,500 / 33,000 | Break-even ~32,922, PoP ~88% | — | BB8KiSmE0ak |
| What-if, spot +1.5% midway | 34,700/35,100 spread +Rs 2,300–2,400 | Naked 36,500 CE about −Rs 8,000 | BB8KiSmE0ak |
| What-if, flat market | Spread about +Rs 800 | Naked call about −Rs 10,000 | BB8KiSmE0ak |
| vs naked put, same break-even (~34,729) and PoP (~70%) | Max loss ~Rs 5,000, far less margin | ~Rs 50,000 loss on a 7.5% fall | BB8KiSmE0ak |

**Entry triggers he uses (long side)**
- **Daily close above a resistance that rejected price for 10–12 days** (39,800). Next day, buy the 39,700/39,800 bull call spread or a few futures lots. Stop on a close below 39,700. Roughly 1:1, ~1,200 rupees/lot reward [xzkqo36gp8c].
- **Expiry day: open above resistance and hold 30–45 minutes** [j02d90xtn_U].
  - Nifty 16,000 spread.
  - Bank Nifty 34,300 spread if the open is above 34,400 and holds to ~10:00.
  - Exit on a close below 34,300.
- **Gap-down into a level with heavy put OI support** (Nifty 17,200, ~80-point gap). Enter around 10–11 am [VyF_xG1f6Aw].
- **Bounce from 38,000 support after a gap-down**, taken instead of selling premium [91-eSFLtkhg].
- **A data-verified tendency to open higher.** He calls the bull call spread the cheapest way to express it [oO-T8_3l_5g].

**Pre-event use**
- Before the budget, in a range-bound market with rising volatility, use defined-risk spreads rather than theta alone.
- Long-vega debit spreads pay if VIX rises and the direction is right [20cgOw1G6FE].

**Long strangle with short wings**
- Long 34,500 PE and 36,500 CE (20 lots), short 34,000 PE and 37,000 CE. This is two debit verticals that profit on a breakout.
- Upside break-even ~37,400. Most of the ~1.5 lakh expected gain was already made [L3PBLOfzI6w].

### 2.7 Vertical credit spreads (long side: bull put; short side: bear call)

**Construction**
- Sell a put, buy a lower put.
- At the money, risk to reward is roughly 1:1. Example: short 36,300 / long 36,200, 100 wide [35_p7TIkaTQ].

**Triggers and examples**
- **Close above a 15-minute resistance zone that failed several times** (33,700–33,800) [0xrgICpggJI]:
  - Sell the slightly ITM 33,700 put at ~280, buy the 33,600 at ~240.
  - ~40 credit, break-even ~33,660, which sits below the level.
- **Gap-up close above a drawn resistance line** [OBJL069UfRQ].
- **Live trade at support (38,000)** [oQXCIfaJ1fs]:
  - Sell the 38,000 put at ~292, buy the 37,500 at ~148, 500 qty each.
  - A bear spread was planned for 1 pm. No details.
- **Community trade around 35,500** [Y_0mKcvRGzo]:
  - PoP ~85%, max profit ~30k against max loss ~2 lakh, about 1:10.
  - He accepts that ratio only with active management.

**Hold rule** [lyQNM8KBec4]
- Hold to expiry unadjusted when all of these hold:
  - About 4,000 of ~17,500 max profit is still left (13,500 already made).
  - The index is unlikely to reach the short-strike zone (~39,972).
  - Margin use is small: ~5 lakh of 25 lakh.
  - PoP is high.

**Bear call side**
- Named only [lkOC0gpSmQQ, oQXCIfaJ1fs].

### 2.8 Hedged straddles, iron flies and condors (short-premium with wings)

**Arithmetic for symmetric wings [jp2M9NfVAig]**
- Max profit = net credit.
- Max loss = wing distance − net credit.
- Break-evens = straddle strike ± net credit.
- Max profit + max loss = wing distance.

| Example | Credit | Hedge cost | Net | Wing | Max loss | Break-evens |
|---|---|---|---|---|---|---|
| Bank Nifty | 825 | 200 | 625 | 1,000 | 375 | 37,775–39,025 |
| HDFC | 60 | 10 | 50 | 100 | 50 | 1,490–1,590 |

- He says the logic extends to strangles and other spreads [jp2M9NfVAig].
- He treats the computed break-evens as the support/resistance zone to watch, e.g. ~38,700 and ~40,300 [VV3vue5PaQo].

**Iron fly example** [myBFImpycfo]
- Sell the 35,400 call (~400) and put (~360). Buy wings 1,000 points out: 36,400 C (~89) and 34,400 P (~75).
- Stated profit range ~34,700–36,100, max loss ~404.
- The identity gives a net credit of 596 and max loss of 404. That matches.
- The identity gives break-evens of ~34,804/35,996, slightly narrower than his stated range.

**Bitcoin daily-expiry condors**
- Version 1 [3MMjcR_ortI]:
  - Shorts ~750 points from spot, hedges 250 points beyond.
  - Enter 2:00 pm, exit at the 5:30 pm expiry or on stops.
  - He uses "iron fly" and "iron condor" interchangeably.
- Version 2 [LrBXT5C_YYY]:
  - Shorts 250 points from spot, hedges 500 points from spot.
  - Entry 2:00–2:15 pm, exit 5:30 pm.
  - Described as moving the shorts "much closer than before". This is the later version, though both videos are ~4 years old.

**Variants**
- **Asymmetric hedges.** A tighter put hedge reflects a negative view, for example a next-week 35,700 straddle with 35,500 and 35,300 puts and a farther call hedge, sold around 14:15–14:30 on expiry day. About 70k profit [KqKOdPHFG-I].
- **Straddle cluster.** Shorts at 35,800, 35,900 and 36,000 with wings at 35,200 and 36,500, treated as one straddle at 35,900. He accepts less profit for simplicity: ~5 lakh potential against ~10.8–13 lakh max loss [JdR7-suVxCI].
- **ITM short strangle.** A short 41,000 call plus a 40,500 put; risk is above the call strike [-IDDp5bvrVQ].

**Related claim**
- Straddle beats strangle. Moving both strikes 300 points out widened break-evens by only ~32 points a side. Max profit fell from 23,475 to 16,775 and PoP rose only from 58% to 60% [O0PDivTMZXE].

### 2.9 Calendars and diagonals

**ATM straddle calendar**
- Sell the near-expiry ATM straddle, buy the same-strike straddle in a later expiry [oO-T8_3l_5g, cJpUydwXnIw, JdR7-suVxCI, tbHLBk84Btc].
- Monthly example, Bank Nifty 36,000: short the September straddle (~1,850 points), long the October straddle (~2,330) [oO-T8_3l_5g]. His scenarios:

| Scenario | Path | Stated result |
|---|---|---|
| 1 | Pinned at the strike | Near leg fully kept; far leg loses ~1,000 and retains ~1,200–1,400; net ~+850–900 |
| 2 | Spike then crash (36,000 → 37,000 → 35,000) | IV rises, far leg holds; net ~+650 |
| 3 | Staged trend to the break-even | ~−150 |

- Weekly variant: sell 18 Aug, buy 26 Aug; ~800 collected, ~1,100 paid; ~+550 if pinned [oO-T8_3l_5g].
- Nifty examples: 16,300 at 2,500 qty per leg [cJpUydwXnIw]; 16,600 at 2,000 qty [JdR7-suVxCI].
- Bank Nifty calendar around a 36,000 straddle, break-evens ~35,100/37,100, normally run neutral [tbHLBk84Btc].
- Bullish-biased calendar [JqEQIQyJ-FU]: max ~11 lakh near 36,000, ~4 lakh at 37,000–38,000. Act only if the index falls back toward ~36,200.

**Regime rule: prefer calendars when VIX is low** [oO-T8_3l_5g]
- A small expected move lets the near leg decay to zero while the far leg keeps value.
- A volatility rise lifts the far leg more.
- This complements "ratio spreads in high VIX" [N8jDRk63lK0]. That pairing is my inference, not his stated framework.

**Double diagonal (Nifty)** [it9ef0_jnVY]
- Short next-week 17,100 P and 17,700 C, long 30 Sept ~16,800 P and 18,000 C, 80 lots each.
- Target ~2 lakh in a week if Nifty ranges; support expected near 17,300.
- Might bring the puts in to 17,200. Replicated for the 30 Sept and 7 Oct expiries.

**Calendar-style hedge**
- Weekly short straddles hedged with long month-end options near the break-evens [2jwiR_sR8W4].
- Nifty: 30 Sept 17,100 P and 17,500 C. Bank Nifty: a 36,700 month-end option against the 36,700 straddle.

**Thin claims**
- Long-dated spreads or calendars on a pledged portfolio for ~10–15% extra per year [GZlwZIH4UOI].
- December-against-current-month calendars, with strategies promised later [tTR4X1FsFgE].
- Nifty plus Sensex options across different expiry dates, exploiting their correlation. Low clarity [pTS4LS3Czos].

### 2.10 Butterflies

The only butterfly-type structure in these notes is the short iron fly (§2.8). There is no long butterfly, broken-wing butterfly or call/put fly.

## 3. How a program would test it

1. **Credit versus debit ratio spreads.**
   - Statement: on Bank Nifty or Nifty (or SPX), 1:2 put ratios with the long strike ~ATM to 3% OTM, held to expiry, show a higher win rate and better mean P&L per unit margin when opened for a net credit than for a net debit, at equal days to expiry.
   - Data: daily EOD option chains with bid/ask, settlement prices, margin model.
   - Source: [3nZVT1T90R0, lkOC0gpSmQQ, NSeHRFG7XVA]

2. **Monthly versus stacked weekly ratios.**
   - Statement: one month-end 1:2 put ratio (net credit, ~20–30 DTE, 500-pt or ~1.3% spacing) against four consecutive weekly 1:2 ratios over the same window. Compare total return, worst loss, and loss on gap-down days (≥1.5%).
   - Data: weekly and monthly chains, open/close gaps.
   - Source: [3nZVT1T90R0]

3. **1:2 versus 1:3 under stress.**
   - Statement: same long strike, shorts set for net credit. Compare the outcome distribution, max adverse excursion before expiry, and results in months with a >8% fall.
   - Data: daily marks for MAE, not just expiry values.
   - Source: [3nZVT1T90R0, NSeHRFG7XVA]

4. **Platform PoP versus realised frequency.**
   - Statement: for ratio spreads and bull call spreads, compare model PoP at entry (lognormal from IV) with realised expiry win rate. He claims 70–95% for ratios and ~52% vs ~32% for spread vs naked call.
   - Data: IV at entry, expiry settlement.
   - Source: [3nZVT1T90R0, BB8KiSmE0ak, UdsdCODKv58]

5. **Regime filter for ratios.**
   - Statement: ratio spreads opened when VIX is in its upper tercile, or in high-gap regimes (frequent ≥1.5% gaps), have a better return-to-max-loss ratio than in low VIX. They also have a smaller worst case than equal-credit naked short strangles held overnight.
   - Data: India VIX / VIX history, gap statistics, chains.
   - Source: [N8jDRk63lK0, yofu41-yyFU]

6. **ATM straddle calendar by VIX regime.**
   - Statement: sell the near-month ATM straddle, buy the next-month same strike, close at near expiry. Mean net P&L after costs is positive when opened in low-VIX percentiles and worse in high VIX. Include the weekly-pair version.
   - Data: chains for both expiries, VIX percentile at entry.
   - Source: [oO-T8_3l_5g, cJpUydwXnIw, JdR7-suVxCI]

7. **Breakout-triggered verticals.**
   - Statement: after a daily close above a level rejected ≥3 times in the prior 10–12 sessions, a next-day ~1:1 bull call spread (strikes straddling the level) or bull put spread (break-even below the level) has a higher expiry win rate than the same spread on random days.
   - Data: daily OHLC, a codified "rejected level" definition, chains.
   - Source: [xzkqo36gp8c, 0xrgICpggJI, OBJL069UfRQ, j02d90xtn_U]

8. **Bitcoin daily condor.**
   - Statement: compare the 250/500-point and 750/1,000-point versions, entered at 2:00 pm and held to the 5:30 pm expiry. Report P&L after fees, and the same scaled to IV-based distances.
   - Data: intraday Bitcoin daily option quotes (Delta Exchange or Deribit).
   - Source: [LrBXT5C_YYY, 3MMjcR_ortI]

## 4. Transfer

**Applies as is (pure payoff logic)**
- Wing arithmetic (§2.8).
- The ratio-spread net-credit rule and its decomposition.
- Vertical spread construction and break-even placement.
- Calendar mechanics.
- US SPX/XSP options suit this well: cash-settled, European, like Indian index options. Daily, weekly and monthly expiries let the weekly-versus-monthly ratio test be run directly.

**Needs adapting**
- **Strike distances.** All his distances are in Bank Nifty or Bitcoin points (500, 1,000, 250, 750). Scale by IV or ATR. For example, his 500-pt Bank Nifty spacing was ~1.3% [3nZVT1T90R0], and the Bitcoin long call sat ~20% above spot.
- **Margin.** Naked short legs in ratios face Reg T or portfolio margin in the US and IIROC/CIRO rules in Canada. Capital-percentage returns (2.7%, 15%) will differ.
- **Skew.** US index put skew makes put ratios richer and call ratios poorer than in India. The net-credit condition will behave differently.
- **Canada.** XIU and SXO options exist but are thin, so wide spreads may kill net-credit ratios and calendars. US-listed SPY, QQQ and IWM, or single names, are more practical.
- **Nifty/Sensex cross-index idea.** It would map to highly correlated pairs (SPX/ES/SPY variants). SPX/NDX is less correlated.

**India-specific**
- Lot sizes and quantities.
- The specific weekly-expiry setups.
- Opstra/Sensibull PoP numbers.
- Expiry-day timing rules.
- Indian weekly expiry rules have changed since many of these videos. Bank Nifty weekly-based setups may not be reproducible in current Indian data.

**Bitcoin**
- The examples are exchange-specific: Delta daily contracts settled on a 30-minute average.

## 5. Gaps and doubts

**Contradictions**
- Maximum ratio: ~1:4 [NSeHRFG7XVA] vs 1:3 with 1:2 preferred [3nZVT1T90R0]. His own 1:3 and 1:2.5 trades break his 1:2 preference.
- Ratio regime: consolidation [NSeHRFG7XVA] vs expected trend [xpMrVzXpW34] vs high VIX [N8jDRk63lK0] vs gap regimes [yofu41-yyFU].
- Expiry: he teaches far or monthly expiry, yet older live ratios had 3–4 days to expiry [tY0noMv3lp0].

**Inconsistent numbers**
- Break-even of 39,200 vs arithmetic near 38,200 [o7lr4TUP3Yg].
- ilbYdeALr0M: his 28,734 break-even fits the implied credit arithmetic. The conflict is between calling it roughly 13% below the then level and his "about 1,300 points below 30,000" remark, and the caption figures do not settle which is right.
- A loss on a large drop in a call ratio [it9ef0_jnVY].
- An "upside break-even" on a put ratio [JqEQIQyJ-FU].
- Iron-fly range slightly wider than the identity gives [myBFImpycfo].

**Model numbers only**
- Nearly all PoP and return figures are payoff-chart estimates, not results. He acknowledges this once [3nZVT1T90R0].

**Missing**
- Ratio adjustment rules (promised in WtIVfzJvJUg).
- Stop-losses for ratios and calendars.
- Profit-taking rules beyond "little left".
- Transaction costs and slippage.
- Margin per structure.
- Bear-side worked examples (bear put, bear call).
- Long butterflies.
- More than one diagonal example.
- Calendar exit rules.

**Undefined terms**
- "Triangle" position [wcnl7rEBE7U, pxw7tkirF4Q].
- "Double spread" [KBx0tqQMkNw].
- An older put-short / call-long "ratio" [pNloB5rjA8A].

**Thin or unverifiable claims**
- The 10–15% yearly extra from pledged-portfolio spreads [GZlwZIH4UOI].
- The Nifty/Sensex combination [pTS4LS3Czos].
- Several community trades whose outcomes are not reported.
