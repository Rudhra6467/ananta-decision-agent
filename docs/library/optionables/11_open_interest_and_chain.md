<!-- Trading Knowledge Library · Optionables (Optionables, India). Built 2026-10-16 from 434 public videos with captions (of 459 on the channel; members-only videos were not used): one structured note per video (Claude Sonnet 5.5) -> this chapter (Claude Opus 5.5), src/research/library.py. Paraphrased; the transcripts stay on the laptop. Evidence class: external teaching = hypotheses to test, never Ananta rules; nothing in the agent reads docs/library/. -->

# Open interest and chain

## 1. What he teaches here and how it fits

Optionables reads the option chain from the **seller's side**. His premise is that option writers are mostly institutions, because selling needs large margin. Open interest (OI) at a strike therefore shows where big money expects price *not* to go before expiry [kkenSM_LmbA, 81ad8bxpbrA, 3FZRs6nCvDk].

From that premise he derives the following tools:
- **OI walls.** The highest call-OI strike is treated as resistance and the highest put-OI strike as support. The two together set an expected expiry range.
- **Straddle clusters.** Heavy call and put writing at the same strike marks a pin or pivot.
- **Changes in OI.** Additions versus unwinding at each strike, read during the day, show sentiment shifting.
- **Put-call ratio (PCR).** A coarse bias gauge, with a contrarian twist at extremes.

He uses all of this mainly as an input to his short-premium trades on Nifty and Bank Nifty weeklies: choosing strikes, deciding when to adjust, and sizing. He usually cross-checks the OI levels against chart levels. He repeatedly says OI shows only what participants currently expect, not where the market will go. He also says it should be set aside when news drives the market [81ad8bxpbrA, 3FZRs6nCvDk, tn3IDCnC6dc, oAJ8k8TzB7E].

Daily FII/DII cash-flow figures appear alongside the chain reading in many of the same videos as a sentiment backdrop. They are summarized briefly below. **Max pain is never mentioned in these notes.**

## 2. The ideas

### 2.1 Foundations: what OI is and whose view it shows

**Definition.** OI is the count of contracts still open, and every open long has a matching open short. For example, 1.4 lakh lots of OI means 1.4 lakh lots long and 1.4 lakh lots short [kkenSM_LmbA].

**Why he reads it from the seller's side.**
- He cites roughly Rs 300 per lot for a buyer, against about Rs 26,000 hedged or about Rs 75,000 naked margin for a seller (lot size 50).
- From this he concludes that big money sits on the sell side [kkenSM_LmbA, 81ad8bxpbrA].
- He assumes institutions buy options only as hedges, not to bet on a price jump. He states this as an assumption, without evidence [kkenSM_LmbA].
- Either way, his logic runs as follows:
  - **High call OI is bearish.** Writers expect price to stay below the strike, and hedge-buyers of calls are short the underlying.
  - **High put OI is bullish**, by the mirror argument [kkenSM_LmbA].

**Caveats he repeats.**
- OI is a picture of today's expectations only. It must be re-read daily [81ad8bxpbrA].
- Heavily written strikes can still break, and short-covering moves can follow [3FZRs6nCvDk].
- OI should be combined with price action and charts [nvSBmk5ffzY].

**Clarity and frequency.** The framing is explicit in a dedicated basics video [kkenSM_LmbA] and a follow-up [81ad8bxpbrA]. It is implicit in nearly every other video.

### 2.2 OI walls: max call OI is resistance, max put OI is support

This is his most frequently stated rule. It appears in roughly 60 or more of the 155 videos.

**Rule.**
- The strike with the largest call OI, especially fresh call writing, is the ceiling until expiry.
- The strike with the largest put OI is the floor.
- The band between them is the expected range [EL1Baky8Uk8, h5XNvyTMSsk, cwcwg2d8pPU, xDRqGkiOnN8, tn3IDCnC6dc, FzWERdEYPmI, VV3vue5PaQo, 81ad8bxpbrA, T1cJv2Y62FU, WtIVfzJvJUg, 7RI6oed3Eak, d-_3zxoHyEg, 2jwiR_sR8W4, BGRZRDCcNSI, alxZlbVHVeo, j02d90xtn_U, NwFNA0IjOkc, MusX9A1juic, xwjZpXxwr5I, cVxwgVbHYKY, peakDi79pVs, 6qive5Kb4Jk, oAJ8k8TzB7E, xf1DJgNy3mQ, X5jF4csZwh8, OBJL069UfRQ, 3VTymF8_eww, v61SICxmkqI, iljL1viJ6I8, mW37Il_RHNg, IeeFqzGWEv0, lyQNM8KBec4, xzkqo36gp8c, jp-dpnaLs38, 9lj7Ta-vsmc, dTaB6gl7Ja4, tKlpB5RfdFA, 2SuMQE03v2w, aUFKZY0o3-E, FBNJsrqlPiQ, tbHLBk84Btc, 3FZRs6nCvDk, kkenSM_LmbA, 4bTRImkOyvY, d6ZOFGDVw2Y, DXTdywSl0D0, nvSBmk5ffzY, GR_KV8MlHZI, cA07gugsaeY, L3PBLOfzI6w, rEX0xkc5Fes, RiTtKlJDrdI, 1NAUR9k2vGs, 0xrgICpggJI, eihlpgiPJKA, IeeFqzGWEv0].

**How he identifies a wall.**
- He looks for OI that is large *relative to neighbouring strikes* [cA07gugsaeY].
- Clusters across several strikes are treated as zones. Examples:
  - Bank Nifty 34,800 / 34,900 / 35,000 [3FZRs6nCvDk].
  - Nifty 17,200–18,000 as a resistance band [6qive5Kb4Jk].
  - Nifty 17,700–18,000 holding about 83 million calls [91-eSFLtkhg].
- He sometimes uses nested walls. On Bank Nifty: a pin at 41,000, an inner range of 40,500–41,500 and an outer range of 40,000–42,000 [lyQNM8KBec4].

**Sizes he cites.** These are the only quantitative anchors he gives:
- About 60 lakh contracts at Nifty 18,000 call [VV3vue5PaQo].
- About 90 lakh at Nifty 18,000, including about 9 million new [FBNJsrqlPiQ].
- About 7.2 million at Nifty 18,000 [3VTymF8_eww].
- About 95–98 lakh at 11,600 call, of which about 70 lakh was added the same day [GsrNVbSwH04].
- About 2 million at Bank Nifty 35,000 call [3FZRs6nCvDk].
- About 50 lakh *quantity* (he says roughly 2 lakh contracts) at Bank Nifty 36,000. He called this a record he had never seen [F6sjGAcJXXc].

**When the walls are more and less reliable.**
- More reliable in the last 1–2 days to expiry.
- On a Friday, the chain is too cluttered to rely on [BFZXz79936Y].
- A wall says the market probably will not go beyond a level. It does not say the market will reverse [BFZXz79936Y, 3VTymF8_eww].

**Relative strength of the two sides.**
- If call writing above is much larger than put writing below, resistance is stronger than support, which gives a bearish tilt [tKlpB5RfdFA, 91-eSFLtkhg].
- He compares how much put writing sits close to spot to rank indices. Bank Nifty had solid put writing at 37,000 while Nifty had little nearby, so he rated Bank Nifty stronger [FBNJsrqlPiQ].
- He reads Bank Nifty's downside from Nifty's put wall [CfriQ26BKrs].

**Failures he admits.**
- The 33,000 put wall broke on the day he sold puts just below it [iPFJBuJqM8Q].
- A bearish view built from OI the prior day failed [QED0exJOqYc].
- Nifty fell through his OI range and he exited [GsrNVbSwH04].

### 2.3 Straddle clusters and pinning

**Rule.** When heavy call *and* put OI sit at the same strike, especially near spot, he reads it as others' short straddles. He treats that strike as:
- the likely expiry or pin level,
- the pivot for the week, and
- a sensible centre for his own straddle

[EL1Baky8Uk8, dTaB6gl7Ja4, tKlpB5RfdFA, 7LlVnFIIEB4, nUnxmPBczaQ, Og7SQjotANg, m3izeXsRdW8, JPqXyHXfGfg, MusX9A1juic, VyF_xG1f6Aw, Y_0mKcvRGzo, yS4PWW8mfsE, RFvomGYSt6k, 3VTymF8_eww, it9ef0_jnVY, BGRZRDCcNSI, IeeFqzGWEv0, XA-oogDFs2s, 0xrgICpggJI, X5jF4csZwh8, lyQNM8KBec4, AyC9r0_ZiN8, 1ItbBTjFgVQ, UIf_6_Bg66I, j02d90xtn_U, XLBtvv6Jq18].

**How he reads it, step by step.**
- **Building during the day.** Rising call and put OI together at one strike shows short straddles being built, in contrast to put build with call unwinding, which shows support [7LlVnFIIEB4, IeeFqzGWEv0].
- **Equal walls, overnight.** When the max call-OI strike equals the max put-OI strike near the close (17,500 with the index at 17,496), he expects no large gap the next morning [Fe766Um-ayQ].
- **Bracketing.** Writers' profit zones around two straddle strikes (39,000 and 39,500) bracket the consolidation zone [3VTymF8_eww].

**Exceptions.**
- He still took a bearish position despite a straddle cluster [AyC9r0_ZiN8].
- A cluster ahead of an event can change quickly [1ItbBTjFgVQ].
- Short straddles get *created* at a support strike that breaks on a gap down [7De_AUtyDeI].

**Max pain.** He never names it. The straddle-pin idea is the closest thing in these notes.

### 2.4 Turning OI into an expected range with premiums

**Formula** [81ad8bxpbrA]:
- Take the max put-OI strike and the max call-OI strike.
- Add together the premiums of those two options.
- Lower bound = put strike minus that sum. Upper bound = call strike plus that sum.

**His examples.**
- Nifty: premiums 50 + 65 ≈ 110 (as he gives it), so about 17,890–18,310.
- Bank Nifty: 175 + 200 = 375, so about 38,125–39,375.

He calls this participants' current expectation, not a forecast. Which premium leg the captions refer to is unclear.

**Straddle variant.** The most-written straddle's premium gives the expected move either side of its strike:
- Nifty 17,500 straddle at about 250 points, so about 17,200–17,800.
- Bank Nifty 37,000 straddle at 600–700 points, so about 36,300–37,700 [jp-dpnaLs38].
- A 16,200 straddle at about 230 points, so break-evens about 16,000–16,450 [d-_3zxoHyEg].
- A 36,500 straddle with about 200 rupees each leg, so expiry expected in 36,000–37,000 [z0Ke0RrtVHw].

**Chart versus OI range.** When the chart range is narrower than the OI range, he treats the chart range as likely and the OI range as the conservative outer band [jp-dpnaLs38].

### 2.5 Reading OI changes at strikes: build-up versus unwinding

This is the dynamic layer, and he teaches it often. He separates the day's change in OI from total OI and checks both [eihlpgiPJKA, kkenSM_LmbA].

**Normal mechanics.** These reactions are not a signal by themselves:
- On a fall, call writing rises and in-the-money put OI unwinds.
- On a rise, in-the-money calls unwind.

The informative part is what put OI does *after* the bounce [3FZRs6nCvDk].

**Bullish or support-building patterns.**
- **Call unwinding with fresh put writing at or below spot.** He reads this as support forming, and as perceived resistance moving up [xwjZpXxwr5I, MusX9A1juic, peakDi79pVs, VyF_xG1f6Aw, Y_0mKcvRGzo, s7M-kuYOROU, lev6pAAKvYE, QED0exJOqYc, it9ef0_jnVY, o2JJ5p03cyc, 4bTRImkOyvY, 9lj7Ta-vsmc, GR_KV8MlHZI, d6ZOFGDVw2Y, tbHLBk84Btc, YBEEfvWpUG8, vRGhcoCUbBE].
- **Same strike, both sides.** Call OI unwinding while put OI builds at the *same* strike means the strike becomes support:
  - Bank Nifty 39,000: about 30 lakh calls unwound and about 30–40 lakh puts added, so he sold 38,900–39,200 puts [3Qt_5nu_0hY].
  - 37,000 on a gap-up expiry [dPuJiR0oxRs].
  - 38,000 [Og7SQjotANg].
  - Monthly series: 37,000 calls unwound with 37,500 puts added on a breakout [GWbpgCAAMkM].
- **Intraday bounce.** After a fall and recovery, if put OI at lower strikes keeps rising during the bounce, that is supportive [3FZRs6nCvDk].
- **One-sided put writing.** Strong put writing with no matching call writing led him to add higher-strike short puts (16,350 and 16,400) [cJpUydwXnIw, H_XvaXezEU0].
- **Gap up.** On a gap up, put writing should quickly appear at lower support strikes and confirm them [7De_AUtyDeI].
- **Afternoon shift.** A morning of call writing on a fall followed by afternoon put writing on a recovery means the market is stabilising [L3PBLOfzI6w].
- **Range-bound rather than bullish.** About 1.5 crore calls closed with about 2 crore puts added reads as range-bound, not outright bullish [T1cJv2Y62FU].

**Bearish or resistance-building patterns.**
- **Fresh call writing with put unwinding at higher strikes** [yS4PWW8mfsE, NwFNA0IjOkc, tKlpB5RfdFA, YYR6P430zGM, z0Ke0RrtVHw].
- **Same strike, both sides.** Put unwinding with call writing at the *same* strike means the strike caps price [FzWERdEYPmI, IeeFqzGWEv0, -wVTqlE51C8]. His argument: anyone expecting a close above 16,200 would be short those puts and would keep them [FzWERdEYPmI].
- **After a gap down.** Put OI at Bank Nifty 34,000 fell from 2.7 million to under 1 million while call OI built. He took 34,000 as resistance and sold calls [CfriQ26BKrs].
- **Round-number break.** A break below a round number with a large same-day call build there means no recovery that day, and he sells more calls at and above that strike [YhGttuO7nGQ, -IDDp5bvrVQ].
- **Shifting writing.** Calls unwinding at lower strikes while being added higher means a ceiling above [OBJL069UfRQ, 5_i637lBoPU].
- **Peak call strike moving down.** If the peak call-OI strike shifts lower day over day (16,800/16,700 to 16,500), a nearer call strike is safe to sell [km4uw-zxRZM].
- **Puts closed during a recovery.** If puts at higher strikes are closed even as the index recovers, upside is capped [3FZRs6nCvDk].

**Rallying into a call wall.**
- Without fresh put writing, he expects profit booking [xf1DJgNy3mQ].
- A close above 18,000 needs put writing at or near it, call unwinding, and buying in HDFC Bank, Reliance and Infosys [VV3vue5PaQo].
- A rally where call writing keeps building at higher strikes is less reliable [it9ef0_jnVY, tJEhYTG7_k4].
- If put OI does not keep adding as price nears resistance, a breach becomes more likely [d6ZOFGDVw2Y].

**Exit trigger.** If short a straddle as price approaches a heavy call strike, and calls there start to unwind, he exits immediately (Nifty 16,300) [Bqh1AevjUzg].

**Other inferences.**
- Cheap far-OTM puts (about 8–9 rupees) being closed while OI is added at closer strikes is writers moving to richer premium. The strike they shift toward marks where they expect the index to end above [cJpUydwXnIw].
- In a short-covering reversal, call writers who had shifted strikes lower roll up or square off [j-S_P5NMkDs].
- Expiry location: ITM call writing that keeps rising during a rally, or put OI that does not unwind on a modest break, both mean expiry stays near that strike (17,500) [xwWE0ZPmP3s].

**Ambiguous readings.**
- In the basics video, falling put OI at 18,100/18,200 is read as sellers not expecting a rise above those strikes. The notes flag the direction as unclear [kkenSM_LmbA].
- In [cJpUydwXnIw], call writers closing at strikes up to 16,500 is read as them "no longer expecting a fall below" those levels. That is an odd inference for call writers, and the notes record it as given.

### 2.6 Breaks of walls

**Upside break.**
- A decisive close above heavy call writing just above spot forces covering and a run to the next level, for example Bank Nifty 34,000 to about 34,500 [OBJL069UfRQ, SalkWOxQ2Rk, aUFKZY0o3-E, 2SuMQE03v2w, o2JJ5p03cyc].
- Bank Nifty 36,500 break with a target of 37,000 [o2JJ5p03cyc].
- Nifty 17,400/17,500 break with a target of 17,600, which he wants on strong volume and frames only as possible [SalkWOxQ2Rk].

**A broken call wall can flip to support.** This happens when the open is above it and he sees call covering plus new put writing (18,000) [4bTRImkOyvY, 3Qt_5nu_0hY].

**What it takes to break the upper limit.** Only a huge gap up combined with aggressive put writing breaks the OI-implied upper limit [dTaB6gl7Ja4].

**Downside break.** A break of a put-dominant strike triggers put writers covering, which pushes price further down (Nifty 15,700) [OBJL069UfRQ].

**His view on the mechanism changed.** In [81ad8bxpbrA] he rejects the popular claim that call short-covering itself lifts the index, saying options derive from the underlying. His account is that crossing the wall changes expectations, traders buy heavyweights (HDFC Bank, Kotak, ICICI, SBI), and writers then panic. Several other videos describe covering as fuel without this nuance [OBJL069UfRQ, aUFKZY0o3-E, SalkWOxQ2Rk, o2JJ5p03cyc].

### 2.7 Aggregate OI and the put-call ratio

**Definition.** Total put OI ÷ total call OI, for the near expiry [kkenSM_LmbA, 81ad8bxpbrA].

**Long side.** PCR above about 1 is mildly bullish, and above about 1.2 is bullish:
- Bank Nifty 1.2 [EL1Baky8Uk8, vRGhcoCUbBE, xwjZpXxwr5I].
- Nifty 1.3 [VyF_xG1f6Aw].
- 1.3–1.4 on expiry morning [35_p7TIkaTQ].
- Put OI greater than call OI [4bTRImkOyvY, j02d90xtn_U, Y_0mKcvRGzo].
- About 65M puts vs 38M calls, with daily put writing about 3× call writing [o2JJ5p03cyc].

**Neutral.** A PCR of about 0.85–1.1, or roughly equal totals (about 80M each, about 38M each), means consolidation [rEX0xkc5Fes, FzWERdEYPmI, T1cJv2Y62FU, RxxeW4MyxJg, MusX9A1juic, jp-dpnaLs38, 2jwiR_sR8W4, 0xrgICpggJI, Fe766Um-ayQ, xzkqo36gp8c, XA-oogDFs2s, oQXCIfaJ1fs, SalkWOxQ2Rk, tn3IDCnC6dc, 7RI6oed3Eak, hLfnVGcoX_w, nUnxmPBczaQ, RiTtKlJDrdI].

**Short side.** PCR below 1 is bearish, or at least means resistance overhead [cVxwgVbHYKY, kkenSM_LmbA, 3FZRs6nCvDk, YYR6P430zGM, RiTtKlJDrdI, nUnxmPBczaQ]. His graded thresholds:
- **About 0.8:** only resistance on the upside, not significant [81ad8bxpbrA, tn3IDCnC6dc].
- **About 0.6–0.7:** bearish [xf1DJgNy3mQ, FBNJsrqlPiQ].
- **About 0.6–0.65:** his example of clearly bearish [81ad8bxpbrA].
- **About 0.5:** called bearish [V-R9YyFioe8, 6qive5Kb4Jk], but only "slightly bearish" for Bank Nifty in [81ad8bxpbrA].
- **Flip after a rally.** A move from above 1 to below 1 made him slightly bearish [XLBtvv6Jq18].

**Contrarian extreme.** At about 0.4 and especially 0.3–0.2, call writing is over-extended:
- Any bounce forces covering, put writing begins, and downside becomes limited [xDRqGkiOnN8, 7LlVnFIIEB4, 6qive5Kb4Jk, yS4PWW8mfsE, -wVTqlE51C8, 7De_AUtyDeI].
- He adds "with the index oversold" in [6qive5Kb4Jk].
- If put writing recovers the ratio, he expects consolidation with a bearish tilt [xDRqGkiOnN8].
- **Disagreement:** he read Bank Nifty PCR of about 0.4 as plainly bearish in one video [NwFNA0IjOkc] and as over-extended in another [yS4PWW8mfsE].

**PCR moves fast.** A shift from 0.7 to about 2 within a day meant growing support [QED0exJOqYc]. A gap up with put writing lifts PCR, which he reads as bullish confirmation [0xrgICpggJI].

**Day-change imbalance.** He compares the day's call OI added against put OI added:
- Calls 28M vs puts 11M: bearish [kkenSM_LmbA].
- About 22M calls added in a day [dTaB6gl7Ja4].
- 45 lakh calls written with 12 lakh puts unwound: limited upside, range about 300–400 points [z0Ke0RrtVHw].
- Puts about 21M vs calls about 5M (about 4×): bullish [tbHLBk84Btc].
- Bank Nifty 9.5M calls vs 5.3M puts: mildly bearish [nUnxmPBczaQ].

**Up day, call-heavy additions.** When the index rises but call additions are at least about equal to put additions (for example 9.2M vs 1.7M, about 5×, or about 2:1 on a green day), he reads limited upside [eihlpgiPJKA, OBJL069UfRQ].

### 2.8 When and how to read the chain

**Wait for the new series.**
- Do not read next-week OI on expiry day or right after it. A Thursday, or the first day of a new series, has too little activity [ApP_IR63Ff8, QgqjwKIZjlM, ufH0zRUyuIw, JqEQIQyJ-FU, 2jwiR_sR8W4].
- Wait one or two sessions, or at least the next morning [JqEQIQyJ-FU, 2jwiR_sR8W4].
- End-of-day OI is less trusted than next-day changes, because fresh positions come the next day [XmP7nK_TMdo].

**Track OI through the day.**
- He checks every few minutes [nvSBmk5ffzY], notes the feed updates about every 3 minutes [NwFNA0IjOkc], and uses 5-minute steps [YYR6P430zGM].
- Multi-strike OI charts on Sensibull show *when* OI changed, not just end-of-day totals [3FZRs6nCvDk, xwWE0ZPmP3s, 3Qt_5nu_0hY].
- Intraday change in OI is used for adjustments [cA07gugsaeY, 7LlVnFIIEB4, IeeFqzGWEv0].

**Data hygiene.**
- **Discount late OI.** OI falls naturally into the close, and especially after about 14:30, as intraday (MIS) positions are squared off. He says not to read this as a signal [3FZRs6nCvDk, IeeFqzGWEv0].
- **Check freshness.** Verify the feed is current. He once dismissed a put-writing "signal" as stale data [lkOC0gpSmQQ].

**Expiry-day protocol** [F6sjGAcJXXc]:
- Trade from OI rather than charts [also NHkRRMWhx4U].
- Re-check at about 13:45 and 14:40.
- Add to the short straddle only while the walls keep growing (48 to 53 lakh).
- More confirming evidence means larger size.

### 2.9 When not to use OI

He gives several conditions under which OI should be set aside:
- **News regimes.** In news- and sentiment-driven markets such as war headlines, elections or the Budget, OI and technical levels are unreliable [tn3IDCnC6dc, 2dJOkeen6RM, E04yFLaCuas, drr-Gaxlp28, 1ItbBTjFgVQ].
- **Large expected gaps.** Before an expected large gap, the pre-gap OI will be rewritten at the open, so he uses chart levels instead [pZPCRg5w9gw].
- **VIX filter.** OI sentiment can be carried to the next day only once news calms and VIX is below about 20 [oAJ8k8TzB7E, mDW8Ih4CuuY].
- **Holidays.** Before a long holiday weekend with news risk, OI and charts are less useful [35_p7TIkaTQ].
- **Later shift in stance.** One video says he *normally* advises not relying on OI because it is news-driven, but uses it on expiry day, when little overnight news can arrive [35_p7TIkaTQ]. This sits uneasily with the many videos where he reads OI for the next day or week.
- **Breakouts shift the levels.** A large up-move shifts put writing higher, so earlier levels stop applying [tn3IDCnC6dc].

### 2.10 Using OI in his trades

**Strike selection for selling.**
- He sells at or beyond the walls, expecting those options to expire worthless [cA07gugsaeY, GsrNVbSwH04, KqKOdPHFG-I, fQfzG_emzZw, M18fQBnjMLA, 4hAvzzjA2xw, z0Ke0RrtVHw].
- For example, he shorted about 8,000 quantity of Bank Nifty 37,200 calls above walls at 36,500/37,000 [z0Ke0RrtVHw].
- He places short puts just below the put wall [iPFJBuJqM8Q].
- A call-heavy chain led to a bearish-tilted strangle instead of a neutral straddle [91-eSFLtkhg].
- He centres the straddle on the cluster strike [XA-oogDFs2s, j02d90xtn_U, F6sjGAcJXXc].
- The OI range acts as an exit trigger: if the range breaks, he exits [9a3TdAs7xUw].

**Adjustments.** He adjusts or flips bias when OI confirms the move: call unwinding plus put addition, put writing on a rise, or covering shorts on put build-up [QED0exJOqYc, GWbpgCAAMkM, eihlpgiPJKA, DXTdywSl0D0, -IDDp5bvrVQ, CfriQ26BKrs].

**Chart agreement.** When the chart range and the OI range agree, he treats the view as confirmed [h5XNvyTMSsk, 2rTZM1IF6DE, 5_i637lBoPU, IeeFqzGWEv0, 7De_AUtyDeI, RiTtKlJDrdI, cVxwgVbHYKY, peakDi79pVs].

### 2.11 Futures OI build-up quadrants

Covered in a single video [0qmiy0rYOfE], clearly stated:

| Price | OI | His label | Reading |
|---|---|---|---|
| Up | Up | Long build-up | Bullish participation |
| Down | Up | Short build-up | Bearish participation |
| Up | Down | Short covering | Rise from shorts exiting |
| Down | Down | Long unwinding | Fall from longs exiting |

He says OI should be read with the published FII/DII positioning in index futures, but gives no rule for using that data.

### 2.12 Context series: FII/DII cash flows (India-only)

These are given as sentiment, not as rules.

**Net-flow readings.**
- Heavy FII selling beyond DII buying caps rallies [FzWERdEYPmI, 2dJOkeen6RM, yS4PWW8mfsE, xDRqGkiOnN8, GEdPl2wK2mY, FBNJsrqlPiQ, RiTtKlJDrdI, alxZlbVHVeo].
- FII selling that slows or flips to buying is supportive [rEX0xkc5Fes, aDbp7e_Qvxo, IjQOUXNIJgk, xV7EMUdSL4w, VyF_xG1f6Aw, vRGhcoCUbBE, EL1Baky8Uk8, peakDi79pVs].
- DII buying offsetting FII selling helps closes [N8jDRk63lK0, hNhLolw563A, XmP7nK_TMdo].

**Record selling episodes.** He cites:
- About 46,000 crore in a month [h5XNvyTMSsk].
- More than 1 lakh crore in Q1 2022 [ilbYdeALr0M].
- About 2 lakh crore in 2022 [tnuVuazeRw8].
- About 2.5 lakh crore in the prior year, which he expects to return when rate cuts begin [EI9hs2l7RBo].

**Flow size and volatility.**
- Flows of 4,000–5,000 crore on each side go with 120–150-point moves.
- Flows of 1,000–2,000 crore go with 50–60-point moves [tJEhYTG7_k4, DXTdywSl0D0].
- Gradual selling does not spike VIX [hm1ZKfkO9Oo].

**Time-of-day patterns.**
- FIIs sold around 13:30–14:00 most days in one week [iljL1viJ6I8].
- A morning-up, 2 pm sell-off pattern held for 3–4 weeks in Mar–May 2022 [tY0noMv3lp0].
- FII last-hour buying over two weeks [XLBtvv6Jq18].

**Heavyweights as the FII channel.** HDFC Bank and Kotak are the names through which FII flows move Bank Nifty [4hAvzzjA2xw, v61SICxmkqI, -kE6iIjC1Ys, JPqXyHXfGfg].

**Flow guesses that missed.**
- FIIs were net buyers when he assumed selling [oAJ8k8TzB7E].
- A sell-off came on a day both FIIs and DIIs bought [m3izeXsRdW8].
- Flows too small to explain a fall led him to guess at margin calls [snLUyn-bzeM].
- Near-zero net flows on strong-momentum days [7LlVnFIIEB4, cVxwgVbHYKY, pZPCRg5w9gw].

## 3. How a program would test it

**Data needed.**
- NSE end-of-day strike-wise OI and settlement prices (F&O bhavcopy) for Nifty and Bank Nifty weeklies, 2019 onward.
- Index OHLC and India VIX.
- Futures OI.
- FII/DII provisional data.
- Where available, intraday OI snapshots at 3–5 minute frequency (vendor data such as Sensibull-type feeds). This is needed for tests 5 and 8.

**Recommended cross-cutting conditions** for every test:
- Split by VIX below vs at or above 20, and by prior-day absolute move above vs below 2.5%. This is his news filter [oAJ8k8TzB7E, tn3IDCnC6dc].
- Split by days to expiry: 1–2 days vs earlier [BFZXz79936Y].
- Skip the first session of each new series [2jwiR_sR8W4].

**Tests.**

1. **Wall band containment.** At the close of T−k (k = 1, 2, 3 sessions before weekly expiry), define the band from the max put-OI strike below spot to the max call-OI strike above spot.
   - Measure how often the expiry settlement, and separately the expiry-week high and low, falls inside the band.
   - Compare with a band of equal width centred on the T−k close, and with an ATM-straddle-implied band.
   - Sub-test: PCR between 0.9 and 1.1 vs other days [T1cJv2Y62FU, rEX0xkc5Fes].

2. **Single-wall ceiling and floor.** Measure the frequency with which the index closes above the max call-OI strike by expiry, against randomly chosen strikes at the same distance from spot. Do the same for the put side.
   - Add a variant where wall OI is in the top decile of its own history [F6sjGAcJXXc].

3. **Pin.** Compare the absolute distance from the expiry settlement to the strike with max combined call+put OI at T−1 or T−2, against the distance to the ATM strike at the same time [dTaB6gl7Ja4, nUnxmPBczaQ, Og7SQjotANg].

4. **PCR buckets.** Compute the near-expiry OI PCR at close and bucket it: below 0.4, 0.4–0.6, 0.6–0.8, 0.8–1.2, above 1.2.
   - Measure forward 1-, 3- and 5-session returns and the return to expiry.
   - Check whether the relation is monotonic, as his linear reading implies, or U-shaped, as the contrarian extreme implies [81ad8bxpbrA, xDRqGkiOnN8, 6qive5Kb4Jk, yS4PWW8mfsE vs NwFNA0IjOkc].

5. **Same-strike flip.** Find days where, at one strike, call OI falls by X% and put OI rises by Y%. For example, use top-quintile changes, with the reference example of 30 lakh unwound and 30–40 lakh added [3Qt_5nu_0hY].
   - Measure the probability the index closes above that strike through expiry, against strikes without the pattern.
   - Mirror test: put down and call up gives a cap [FzWERdEYPmI, CfriQ26BKrs].

6. **Wall breaks.** After a daily close above the T−1 max call-OI strike, measure the forward return to expiry and the probability of reaching the next 500-point Bank Nifty or 100-point Nifty strike.
   - Compare with closes of similar size that do not cross a wall [OBJL069UfRQ, 81ad8bxpbrA].

7. **Premium range formula.** Check the coverage of [max put strike − (P + C), max call strike + (P + C)], using both possible premium-leg definitions given the caption ambiguity, against ATM straddle break-evens. Compare both hit rate and width [81ad8bxpbrA, jp-dpnaLs38].

8. **Intraday and futures add-ons.**
   - (a) Test whether intraday OI changes before 14:30 at the nearest strikes predict the close-minus-14:30 move, and whether changes after 14:30 have lower predictive power [IeeFqzGWEv0, YYR6P430zGM].
   - (b) Compute the four futures quadrants from daily Nifty futures price and OI changes, then measure 1–5 day forward returns per quadrant [0qmiy0rYOfE].

## 4. Transfer to Canadian (TSX) and US markets

**Usable largely as is.**
- The futures OI quadrant logic, for ES and NQ, and for SXF on the TSX 60.
- PCR as a computed statistic.
- Straddle-implied expected move.
- End-of-day max-OI walls on SPX, SPY and QQQ, as a test subject.
- The news and VIX filter (VIX for the US, VIXC for Canada).

**Needs adapting.**
- **Writer mix.** The core premise that OI equals institutional writers' view is untested in the US. There, dealer and market-maker positioning, retail call buying and hedging flows dominate, and OI does not reveal which side opened.
- **OI timing.** US OI is published once a day by OCC, the next morning. Every intraday and "every 3 minutes" rule (sections 2.5 and 2.8) cannot be replicated from public data. Volume or trade-direction proxies would be needed.
- **Expiry structure.** SPX and SPY now have daily expiries, so define which expiry's chain counts. This differs from India's single dominant weekly.
- **Thresholds.** His PCR thresholds and contract counts are calibrated to Indian weekly chains and mix lots with quantity. Recalibrate them per instrument, using percentiles of the instrument's own history.
- **Canada.** TSX 60 index options (SXO) and XIU options are thin and mostly monthly. OI walls are likely too sparse to read, so test on US index products first.
- **Instrument economics.** Costs, lot sizes and margin (his Rs 300 versus Rs 26,000–75,000 argument) differ. The margin-based "sellers have the edge" reasoning does not carry over.
- **Square-off cutoff.** The 14:30 MIS square-off effect is an Indian broker convention. The US analogue would be 0DTE closing flows into the close.

**India-only.**
- The FII/DII daily cash and futures-positioning series and every rule built on them (section 2.12). The US and Canada have no daily equivalent; only slower foreign-flow and COT-type data exist.
- SGX/Gift Nifty pre-open gaps [FBNJsrqlPiQ].
- Bank Nifty-specific weekly behaviour.

**Caution for India testing.** Indian exchanges have reduced weekly index expiries in recent years. Check the expiry calendar per period so weeklies are not pooled across regimes.

## 5. Gaps and doubts

**Coverage gaps.**
- **Max pain is absent** from all notes, despite the chapter title.
- **"Heavy" is never defined.** There is no threshold for heavy writing, unwinding or wall size relative to neighbours. Every rule needs a researcher-chosen cutoff.
- **Units are inconsistent:** contracts, lakh, "quantity" and million. One note explicitly converts about 50 lakh quantity into about 2 lakh contracts [F6sjGAcJXXc]. Cited sizes cannot be compared across videos.
- **No statistics.** He offers no hit rates or backtests. Evidence is per-day anecdote, with a few admitted failures [iPFJBuJqM8Q, QED0exJOqYc, GsrNVbSwH04]. Selection bias in which days get discussed is likely.

**Internal contradictions.**
- PCR 0.4 is read as bearish [NwFNA0IjOkc] and as contrarian or bullish-leaning [yS4PWW8mfsE, -wVTqlE51C8].
- PCR 0.5 is "slightly bearish" [81ad8bxpbrA] and "clearly bearish" [6qive5Kb4Jk].
- Short covering is described as fuelling rallies [OBJL069UfRQ, SalkWOxQ2Rk, aUFKZY0o3-E], but he denies that options drive the index [81ad8bxpbrA].
- He says he usually doesn't rely on OI [35_p7TIkaTQ], yet reads OI daily in most other videos.

**Unclear interpretations.**
- The put-unwinding direction in the basics video [kkenSM_LmbA].
- The "call writers closing implies no fall" inference [cJpUydwXnIw].
- Which premium leg the range formula uses [81ad8bxpbrA].

**Caption problems.**
- "4500" for 40,500 [aUFKZY0o3-E].
- An 11,036 low that is likely mis-captioned [GsrNVbSwH04].
- Contradictory DII buy/sell figures [OBJL069UfRQ].
- Unrecoverable content [DimfDZRACgQ, 0pvrPKfpU4U, F13SplxY6po, d3ohL4Aorac, Q_BhDmUE22M, YBEEfvWpUG8, lev6pAAKvYE].

**Change over time.**
- The oldest videos (about 6 years) already use OI walls to pick selling strikes [cA07gugsaeY, GsrNVbSwH04].
- The more nuanced material sits mostly in the 4–5-year range: intraday OI dynamics, the 14:30 caveat, the news and VIX filter, and the options-don't-drive-price argument.
- Very few notes are newer than 3 years, so his current stance is unknown.

**Single-source items.**
- The futures quadrants [0qmiy0rYOfE].
- The premium range formula [81ad8bxpbrA].
- Scaling into expiry straddles [F6sjGAcJXXc].

**Peripheral items** in these notes, not developed into rules:
- Freak-trade and spike mechanics, including 1-second chart resolution and a put's OI halving in 5 minutes after a spike [xj-1uHZotgY, vx8x_O7-01g, JfeLqaREQU0].
- Call premiums surging on small up-moves [m3vTimQ3HiE].
- GameStop short interest versus float [QhERbElbSOM].
- Multi-cap fund rebalancing [TGlIz26DNMQ].
- Sensex option liquidity [pTS4LS3Czos].
- Platform option-chain tooling [TcH5IWySLJw].
- India's retail options volume [D9ctkD_pCxQ].
