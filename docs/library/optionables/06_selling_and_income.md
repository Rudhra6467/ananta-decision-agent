<!-- Trading Knowledge Library · Optionables (Optionables, India). Built 2026-10-16 from 434 public videos with captions (of 459 on the channel; members-only videos were not used): one structured note per video (Claude Sonnet 5.5) -> this chapter (Claude Opus 5.5), src/research/library.py. Paraphrased; the transcripts stay on the laptop. Evidence class: external teaching = hypotheses to test, never Ananta rules; nothing in the agent reads docs/library/. -->

# Selling and income

## 1. What he teaches here and how it fits

Option selling is the core of Optionables' trading. Most of the material is short premium on Indian index weekly options (Bank Nifty and Nifty). It comes in four forms:

1. A mechanical intraday at-the-money (ATM) short straddle, entered at fixed clock times with a stop loss on each leg.
2. Discretionary straddles and strangles whose strikes come from support/resistance and open-interest (OI) ranges, often hedged into iron-condor or iron-fly shapes.
3. Directional naked put or call selling when he holds a trend or support view.
4. Event-day straddles (Budget, RBI) and expiry-afternoon decay trades.

His stated reasoning is that markets are range-bound most of the time. He puts this at about 60–67%. Theta lets the seller win when the market is flat and also win partly when it trends, so risk control is the job. His stated aim is to keep losing trades to about 1–2% of capital [VnlxZ2uP47M, O0PDivTMZXE, uN9SRyTv_yY, NXE7KFxmH7I, 3MMjcR_ortI, IMjqrkYosgY].

Income ideas outside index selling are thin:
- He argues against covered calls [m3izeXsRdW8].
- He mentions cash-secured puts on large stocks [ilbYdeALr0M].
- He describes a layered return: pledged equity collateral plus an option-selling overlay [yDec0_hqKWk, GZlwZIH4UOI].

Everything below is his claim or method, to be treated as a hypothesis.

The emphasis shifts over time:
- **About 5 years ago:** mostly Bank Nifty afternoon timed straddles.
- **About 4 years ago:** Nifty 9:30/11:30/13:30 straddles plus hedged positional structures and iron condors.
- **About 3 years ago:** VIX-filtered backtests, OI/range-based discretion, Bitcoin.
- **About 2 years ago:** regime-dependent advice. Use condors or iron flies only in sideways markets, and do not keep running neutral trades through breakouts [F0x5faXXRTI, Vp6a7TiKiZk, Mt5qSl4j3fQ].

---

## 2. The ideas

### 2.1 Timed intraday ATM short straddle with per-leg stops (the "system")

**What it is.** At set clock times he sells the call and put at the strike nearest spot. Strikes are rounded to 100 for Bank Nifty and 50 for Nifty [O0PDivTMZXE, vmjxCxSdIn0]. Each leg has its own stop. The surviving leg is held to a fixed exit time, and there is no other management [L9f-oq8XVOo, alxZlbVHVeo].

**The variants he used:**

| Variant | Entry | Stop per leg | Exit | Source |
|---|---|---|---|---|
| Bank Nifty, three entries | 10:00, 13:00, 14:00 | not stated; partial hedges in one video | 15:15 | [vmjxCxSdIn0, c29sN7KQSIs, ocl7mwUeZA8, 3uZnthbvz3A] |
| Bank Nifty, afternoon entries | 12:30, 13:00, 14:00 | not stated | end of day | [_dQVN0WKeCE, wr82JkzZyys, WAXCM9CDx8g, yvSFv0dQQVI] |
| Nifty, three entries | 9:30, 11:30, 13:30 | not stated in these videos | end of day | [Fe766Um-ayQ, rEX0xkc5Fes, cwcwg2d8pPU, 4Zd60oo6vOM, alxZlbVHVeo, NwFNA0IjOkc] |
| Bank Nifty, single entry | 13:00 | 30% | 14:55, later 15:20 or 15:29 | [8i-eCbGznbo, lkOC0gpSmQQ, aUFKZY0o3-E] |
| Bank Nifty, single entry | 9:30 | 50% (stop at 1.5× premium) | 15:00 | [L9f-oq8XVOo] |
| Bank Nifty, single entry | 14:00 | 90% | 15:00 | [L9f-oq8XVOo] |
| Nifty, single entry | 9:30 | 70 index points | 15:20 | [X8sW2WNaKAs] |
| Bank Nifty, open | open | 75% | not stated | [nXjmslNVkyo] |
| Bank Nifty, demo | 9:20 | 25% | not stated | [F5O2b6_5npQ] |
| Bank Nifty, algo | 10:30, 11:30, 12:30 | 50% | end of day | [oQXCIfaJ1fs] |

Additional variant details:
- In the 13:00 variant of [aUFKZY0o3-E] the stop is moved to cost once a condition is met.
- The 25% demo in [F5O2b6_5npQ] is unclear on whether the stop is per leg.
- He says the system was designed for 12:45 entry on Nifty and 13:00 on Bank Nifty. Traders who enter at 9:30 or 10:00 with the same 30% stop get stopped out [HcdusL_8W5U].

**His backtest numbers.** All are unverified, and costs are mostly absent.

- **9:30 Bank Nifty, 50% stop** [L9f-oq8XVOo]
  - About 1,200 trading days.
  - About ₹5.53 lakh per lot, about ₹451 per day.
  - 72% winning days (882 wins, 342 losses); expectancy ratio 0.24.
  - No costs or slippage.
- **13:00 entry, 30% stop, 15:00 exit** [L9f-oq8XVOo]: about ₹4 lakh, 70% wins, expectancy 0.31.
- **14:00 entry, 90% stop, 15:00 exit** [L9f-oq8XVOo]: about ₹3 lakh, 74% wins, expectancy 0.36. He prefers this variant for its expectancy despite the lowest total.
- **13:00 Bank Nifty, 30% stop, 14:55 exit, Jan 2017–May 2021, 10 lots per leg** [8i-eCbGznbo]
  - About ₹36.8 lakh in total; 51 of 53 months positive.
  - 761 winning vs 311 losing days (about 71%).
  - Average win about ₹9k vs average loss about ₹10k.
  - Worst day −₹1.31 lakh.
  - Costs not stated.
- **13:00 Bank Nifty, 30% stop, 2017 onward** [lkOC0gpSmQQ]
  - With 0.5% slippage: about 67% wins, near 1:1 risk-reward, expectancy about 0.25.
  - Running the same rule at 9:20, 11:00, 13:00 and 14:00 combined: about 69% wins and expectancy about 0.5.
- **9:30 Nifty, 70-point stops, about 1,557 days** [X8sW2WNaKAs]: overall expectancy 0.23 (VIX breakdown in 2.4).

**Why it works and fails, in his words:**
- **Trend days:** a strong one-way move is acceptable. The losing leg stops out and the other keeps decaying. In one example the call stopped at about −90 points while the put decayed 120–130 points [c29sN7KQSIs, wdUlevVfZL4, vmjxCxSdIn0]. On trending days he keeps stops tight, about 30%, so the losing leg exits fast [L8SZ30on7po].
- **V-shaped reversal or whipsaw days:** these are the loss case. First one leg stops, then the other [vmjxCxSdIn0, k6bDh3ONgz0, hPUdSoT2c7g, m3izeXsRdW8, 0ioEL11p1kk, hLfnVGcoX_w, 3MMjcR_ortI].
- **Slightly trending days:** one video instead names slightly trending days (moves of about 0.8–2%) as the losing case [8i-eCbGznbo].
- **Why 13:00:** after 13:00 theta is highest and V-reversal risk is lower than for morning entries [8i-eCbGznbo]. A 10:00 entry that lost on a V-day was dropped the next day for an afternoon-only entry [0ioEL11p1kk].
- **Wide stops:** on days with a ±50-point swing but a flat open-to-close, sellers win only if the stops are not tight [pNloB5rjA8A].

**Clarity and frequency.** This is the most often taught idea in the notes, across roughly 40 videos, and the backtest videos are high clarity. Exact stop levels are often missing from the live-trade videos.

### 2.2 Staggering, scaling in, re-entry and re-centring

**Staggered entries.** He prefers spreading entries over time rather than one entry.
- Staggering spreads strikes across levels, for example 41,000 to 41,300 [xj-1uHZotgY].
- He reports staggering improves backtest expectancy [lkOC0gpSmQQ].
- He uses three to four entries per day as routine [Pt5pbpK1eoI, BFZXz79936Y, rEX0xkc5Fes, jztFfYokRqI].

**Sizing by time slot.**
- Budget-day example: the 9:30 and 12:00 entries were 625 quantity and the middle four were 900. A test showed 10:00–11:30 did better [xj-1uHZotgY].
- In general he starts small early and gets larger in the 13:00–15:00 window, when decay is strongest [BFZXz79936Y].

**Adding on flat days.**
- On a flat day he kept adding about 3,000 quantity of the same 15,800 straddle at 14:00, 15:00 and 15:15, reaching 18,000 quantity over six entries [u_UvOZQpRlk].
- He added 800 quantity once the position was about ₹14k in profit [A0sLu7cjjlU]. The trigger is not fully stated.

**Re-entry after a stop or a move.**
- After a stop he sells a fresh ATM straddle at the new spot [tn3IDCnC6dc, 91-eSFLtkhg, 7RI6oed3Eak, GxKIIKl4eZA, MusX9A1juic].
- He converts a strangle to a straddle at spot when price reaches the middle [tKlpB5RfdFA, u_UvOZQpRlk, 91-eSFLtkhg].
- After a 300-point gap-up on expiry he re-centred to the new strike and went from −₹3.5 lakh to +₹1.2 lakh [aDbp7e_Qvxo].

**When it failed.** On a gap-plus-trend day, repeated re-selling of the Bank Nifty ATM straddle lost on every attempt (about 30k, 70k, 50k and 1 lakh) [LPGCiis_rlg]. A community straddle placed about 150 points above spot lost about 2.4% of virtual capital through a 4% round trip [aDbp7e_Qvxo]. No rule is given for when to stop re-entering.

### 2.3 Where the decay comes from: afternoon and expiry-session timing

**Morning vs afternoon.**
- He observes little or no decay in the first hours. In one day the burst came at about 14:40–14:50 [ybZYfvQzy7E, rEX0xkc5Fes].
- A range day's profit came mostly late [jEF9S2_P5Po]. He said holding nearer to close would have paid more than ₹4 lakh against the ₹2.8–2.9 lakh made.
- From 14:00 to 15:00 a book went from about −₹1.5 lakh to about +₹30k [9pT7h-M2v64].

**Late expiry-day trades.**
- Straddle at 15:02, closed by 15:20, about ₹23k on about 5,000 quantity; strangle near 15:29, about ₹25k [N8jDRk63lK0].
- 3:15 pm straddle on about 10,500 quantity that decayed 17–18 points [nXjmslNVkyo].
- Straddle at 14:20–14:30 with 150–160 points of premium still left, which he called unusually high [NHkRRMWhx4U].
- Afternoon entries using his ITM/straddle mix with a 75-point stop, closed near 14:45–14:55 [kaPyJdhVI9c].
- He claims trades after 15:00 on expiry day help on about 8 of 10 expiries [YtLDcJgJzcQ].
- Last-hour straddles on a volatile range day recovered the day [Vn40nCE-lLI].

**Next-expiry selling late in the day.** When current-week premium is nearly gone he sells next-week options instead:
- He did this at 15:00 and caught about 13 points of decay [P21vgTId9P8].
- Next-week straddle late on expiry day, about ₹80–90k [Bqh1AevjUzg].
- When the ATM straddle is under about 0.4% of spot with about 3 hours left, he moves to next week [2m1GpJzXBt4].

**Counter-evidence.**
- A hedged 3 pm straddle after a trend day lost its full defined risk, about ₹4 lakh, within minutes [LPGCiis_rlg].
- A late bounce erased most of a straddle's gain [pxw7tkirF4Q].
- He gave back MTM to a late rally and closed when profit was eroding [H_XvaXezEU0].

**Calendar effects.**
- Fridays give little decay even for iron condors [m22yYC83nG0].
- Holidays: a weekly straddle priced through a Wednesday holiday should shrink by Thursday [oQXCIfaJ1fs]. Holiday-shortened weeks with three trading days should decay faster [9lj7Ta-vsmc]. These are LOW-to-MEDIUM clarity claims.

### 2.4 Volatility regime filters

**Low VIX helped the systematic straddle.** For the 9:30 Nifty straddle with 70-point stops [X8sW2WNaKAs]:

| Sample | Days | Expectancy | No stop hit | Both stops hit |
|---|---|---|---|---|
| All days | about 1,557 | 0.23 | 19% | 14% |
| VIX < 14 | about 425 | 0.38 | about 42% | about 3% |
| VIX > 20 | not stated | 0.17 | about 3% | about 30% |

The VIX > 20 double-stop figure is unclear: it was spoken once as 13%, likely a caption error. He concludes the system works about twice as well in low VIX. He also says a move from high VIX to low VIX favours sellers through both theta and vega [X8sW2WNaKAs].

**But low VIX also changes the structure he uses:**
- When premiums are low, book profit early and re-enter, because a 100–150 point Bank Nifty move unbalances the position [kaPyJdhVI9c].
- In low VIX (about 13), sell next-week rather than current-week, so ordinary 70–150 point moves do not trigger stops [wcTPYuhzvAU].
- Prefer strangles over straddles when premiums are low [O2h5RlRlQtQ].
- In high VIX he favours far-OTM strangles at the range edges. Examples: Bank Nifty 36,000 call at about ₹44 plus 33,000 put at about ₹55, about 1,500 points each side [v61SICxmkqI, tJEhYTG7_k4]. He also favours wide hedged credit spreads about 4,000 points out [G2Jm-SaT6M8], and strangles over straddles when volatility is elevated [h5XNvyTMSsk].

**Implied vs realized move.** He compares what the straddle prices in with what the market is actually moving:
- When realized daily moves exceed the straddle price (Nifty priced about 250 points but moving about 350; Bank Nifty priced about 750 but moving about 900), positional selling pays too little, and he shifts capital to intraday [V-R9YyFioe8].
- He favours a straddle when the expected range is wider than the implied move. Example: Bank Nifty range about 700 points vs about 500 priced [X5jF4csZwh8].
- A day priced at about 900 points that realized about ±200 points worked well [pZPCRg5w9gw].

**Selling after an IV jump.**
- Sell after a spike or a 100–150 point dip from the high, expecting IV to fall [peakDi79pVs].
- Sell after a gap-down that raised IV, followed by a narrow range [aUFKZY0o3-E].
- Sell near the intraday low at about 9:30, so IV cools on the bounce [7RI6oed3Eak].
- One counter-case: entering at 9:20 on a post-event day was "a mistake" [GJ-1jOUSekk].

### 2.5 Discretionary range straddles/strangles: strikes from support, resistance and OI

**Rules as stated:**
- Straddle at the middle of the expected range, strangle with strikes at the range edges [8W58_AoCKrw, h5XNvyTMSsk, FzWERdEYPmI, EL1Baky8Uk8, xzkqo36gp8c, iPFJBuJqM8Q, j02d90xtn_U].
- One video adds a codable filter: sell when the strikes with the highest put OI and highest call OI are within about 1.5% of spot [EL1Baky8Uk8].
- Break-evens (strike ± premium) should sit beyond the expected support and resistance.
  - Example: Bank Nifty 36,700 straddle with about 800 points of premium gives break-evens 35,912 and 37,487, against 36,000 support and 37,500 resistance [XmP7nK_TMdo].
  - Similar comparisons in [h5XNvyTMSsk, X5jF4csZwh8, XLBtvv6Jq18, 2jwiR_sR8W4].
- He uses strikes with the highest OI or heavy call/put writing [oQXCIfaJ1fs, 2SuMQE03v2w, WtIVfzJvJUg, xzkqo36gp8c, RiTtKlJDrdI, d-_3zxoHyEg].
- Strikes are chosen after the open:
  - Flat open (within about 30–40 points): Nifty 15,800/16,200 or a tighter 15,900/16,100.
  - Gap of about 130 points: shift both strikes by roughly the gap [2rTZM1IF6DE].
  - Bank Nifty gap-down of 200–300 points: use the 36,500 strike; flat or gap-up: use 36,700/36,800 [XmP7nK_TMdo].
  - Flat open → straddle; otherwise a strangle bracketed by support and resistance [SalkWOxQ2Rk, O2h5RlRlQtQ, 16t3E1t2tgk, j02d90xtn_U].
  - If the open is near one strike, sell the other side there to form a straddle [RiTtKlJDrdI].
- Skew toward the trend:
  - Strangle skewed up in a rising market [vmjxCxSdIn0].
  - Put closer and call farther when bullish [lkOC0gpSmQQ, hPUdSoT2c7g, aUFKZY0o3-E, DLJ0AmH6hS0, RFvomGYSt6k].
  - Straddle struck above spot as a bullish drift trade [vRGhcoCUbBE].
  - Bearish tilt when bearish [xf1DJgNy3mQ, 5vAHDwZkoHc].
  - Uneven quantity across two strikes, weighted toward the expected expiry zone [2jwiR_sR8W4, nUnxmPBczaQ].

**When he says not to use it:**
- No clear range: a broad band of about 400 points with no nearby levels pays too little for the risk [pMVDiDH8v08].
- Expiry gaps over about 0.5% leave a symmetric strangle with no gain. If he has a view, he prefers a biased structure [wcnl7rEBE7U].
- Skip next-week strangles on a large opening gap [2m1GpJzXBt4].
- Exit or turn directional when the range breaks [oQXCIfaJ1fs, RxxeW4MyxJg, bxx4CGJ39Ks, Mt5qSl4j3fQ].
- Do not keep repeating a neutral trade through a breakout. One breakout leg can lose more than the whole range period earned [F0x5faXXRTI].

**The one quantified sample.** Monthly Nifty strangles over Jan–May 2021, one lot, about ₹50k margin, discretionary ranges [8W58_AoCKrw]:
- Monthly P&L: +883, −16,537, +11,085, +13,196, −6,341.
- Adjusted total about +₹10k (about 21%) vs unadjusted about +₹1.9k (about 3.9%).
- The platform showed about 77% probability of profit.
- Only five months, all in a bull trend.

### 2.6 Straddle vs strangle (and ITM vs OTM)

**Balance the premiums.** Sell the strike pair whose call and put premiums are closest.
- A strangle at 360/360 was chosen over a straddle at 350/390 [BFZXz79936Y].
- He switched from a straddle to a strangle when the ATM call was about ₹290 vs the put about ₹190 [M18fQBnjMLA].
- Equal-premium afternoon strangles at about ₹205 each [wdUlevVfZL4].
- He went the other way, strangle to straddle, when the strangle premium was too small [NTavZ18KPh8].

**His preference is inconsistent:**

| Prefers | Reason given | Source |
|---|---|---|
| Straddle over strangle | details deferred to a separate video | [8i-eCbGznbo] |
| Straddle | "host" in a guest video | [d6ZOFGDVw2Y] |
| Strangle (favourite) | can start small and add or shift | [uN9SRyTv_yY] |
| Strangle for beginners | smaller MTM swings, delta below 0.5 | [NXE7KFxmH7I] |
| Strangle | easier to adjust | [V-R9YyFioe8] |
| Far-OTM strangle | when the view is unclear | [pMVDiDH8v08] |
| Strangle | when premiums are low | [O2h5RlRlQtQ] |

**Inverted (ITM) strangles:**
- He says plain strangles are better than inverted ones, with the explanation promised but not given [oQXCIfaJ1fs].
- A guest says inverted strangles suffer less from expiry gamma [d6ZOFGDVw2Y].
- He nonetheless sells ITM strangles: 36,600 call / 36,700 put with spot near 36,650 [IeeFqzGWEv0]; 38,700/38,500 [9lj7Ta-vsmc]; [kaPyJdhVI9c].
- Elsewhere he teaches never to sell ITM. ITM and OTM carry similar time value (about ₹44 vs ₹46 in one example), but ITM has far more delta risk. A 25-point adverse move cost the ITM option about 29 points vs about 25 for ATM [l4jQUXK6UOc].

### 2.7 Systematic strangle rules

- **12:30 Nifty strangle** [NXE7KFxmH7I]
  - At 12:30 daily, round Nifty spot to the nearest 100.
  - Sell the call 100 points above and the put 100 points below. Example: 15,175 rounds to 15,200, giving a 15,300 call and a 15,100 put.
  - Exit at 14:55.
  - He prefers 100-point spacing even where 50-point strikes exist.
- **9:30 strangle at fixed distance** [V-R9YyFioe8]: about 300 points from spot on Bank Nifty and about 150 on Nifty, exit about 15:20. Chosen over a straddle because it is easier to adjust.
- **Overnight pre-expiry Bank Nifty strangle** [oYfLG7jLvPQ]
  - Rules:
    - Sell the 200-point OTM call and put at 15:15 the day before expiry.
    - Exit at 9:20 on expiry day.
    - If expiry moves to Wednesday because of a holiday, enter Tuesday.
  - Unhedged backtest, about 4.5 years, 10 lots, ₹10 lakh capital:
    - About ₹13.16 lakh profit, 83% wins (about 17 losses in about 206 expiries).
    - Average win about ₹10k, average loss about ₹12k.
    - Maximum drawdown about ₹1.16 lakh (11%).
    - He expects 20–25% a year.
  - Hedged version with a 75% stop:
    - About ₹8.5 lakh (about 20% a year).
    - Drawdown about ₹96k; worst trade about ₹7–7.45k (0.74% of capital).
    - Worst month October 2018, about −₹85k.
- **Wide expiry-morning strangle** [-uIGVxZWSHU]: at 9:30, sell about 400 points above and 500 below spot (about 1.2% each side) with fixed per-leg stops.
- **±100 strangles in the morning** [IMjqrkYosgY, pdGXhkLJPj0].

### 2.8 Hedged positional structures: iron condor, iron fly, winged straddles

- **Beginner iron condor** [ZJyMZJekVBk]
  - Every Friday at 9:20, for the next weekly expiry.
  - Sell Bank Nifty 500 points OTM each side, buy 800 points OTM. Example at 38,500 spot: short 38,000 put and 39,000 call, long 37,700 put and 39,300 call.
  - He prefers it for beginners: smaller swings than a straddle.
- **Other condors:**
  - Short 37,200 put / 38,500 call, wings at 36,700 / 39,000, about 40 lots, max loss about ₹3.5 lakh [FBNJsrqlPiQ].
  - Nifty 17,800 / 18,300 with 100-point wings, entered Monday afternoon [4bTRImkOyvY].
  - Far-OTM hedged credit spreads both sides: short 31,500 put / long 31,200 put (about 20 points credit); short 39,000 call with a 500-point wing [G2Jm-SaT6M8].
  - Iron condors or iron flies are only for sideways regimes [Vp6a7TiKiZk].
- **Iron fly / winged straddle wing widths:**

| Wings | Details | Source |
|---|---|---|
| 200 points | Bank Nifty 38,800 straddle; max profit about ₹3.6 lakh, max loss about ₹2.4 lakh | [3Qt_5nu_0hY] |
| 500 points | Iron fly at 37,000, break-evens about 265 points each side | [dPuJiR0oxRs] |
| 500 points | Hedged 41,000 straddle | [-IDDp5bvrVQ] |
| Nifty 200 / Bank Nifty 500 points | Hedged straddles into expiry | [7De_AUtyDeI] |
| 1,000 points | Straddle plus strangle, break-evens 35,415 / 36,585 | [oAJ8k8TzB7E] |
| 1,000 points | Demo with 30% leg stops and ±₹1,000 MTM exit | [6lVvi-ULRVE] |
| 1,500 points | Bank Nifty 39,500 straddle | [VV3vue5PaQo] |
| Very close, about 100–200 points | Three adjacent straddles on expiry; capped worst case about ₹2.5 lakh net, under 0.7% of capital | [ujTuECvyPzc] |

- **Asymmetric wings:**
  - Close put hedge 300 points away, call hedge 500 points away: downside max loss about ₹60k, upside about ₹8 lakh [ZDUmKEZXWMw].
  - Closer puts and farther calls [3VTymF8_eww].
  - Nifty put hedge 200 points below and call hedge 300 above, max loss about ₹3 lakh down / ₹2 lakh up, no adjustment until near break-even [s7M-kuYOROU].
- **Calendar hedge.** A same-strike month-end long option against the weekly short straddle [nUnxmPBczaQ, 2jwiR_sR8W4, QED0exJOqYc].
- **Sizing hedged risk.** Max risk = wing width − credit. Example: 300 − 180 = about 120 points. He sized to about ₹2.4 lakh worst case, within a 1–2% limit [P21vgTId9P8].
- **Why hedge.** He says to always hedge range trades [m22yYC83nG0]. A naked straddle is hard to adjust on a sharp move [GWbpgCAAMkM].
- **Naked weekly straddle backtest.** He set one up (Friday 9:16 → Thursday 15:29, no stop, no hedge) but the notes contain no result [1fDefykVmnk].

### 2.9 Long-dated and monthly selling

- **Year-out straddle** [9a3TdAs7xUw]
  - About 2,000 points collected, implying a range of roughly 10,000–14,000.
  - Keeping only 500 points on a 75 lot is about ₹37k on about ₹1.5 lakh margin, his "25%".
- **5-month straddle and strangle in low VIX** [tTR4X1FsFgE]
  - 16,000 straddle collecting about 1,050 points, break-evens about 15,000–17,000.
  - 14,000 put / 17,000 call strangle for about ₹180–200, with VIX at 12–13.
  - A 13,000 put about 20% below spot still paid about ₹40. He suggests hedging with weeklies.
- **Monthly straddles:**
  - Nifty about 500 points and Bank Nifty about 2,000 points collected [c29sN7KQSIs].
  - Monthly preferred over weekly because it prices more movement: Nifty about 320 vs about 200. Exit only the threatened leg when a range edge breaks [RxxeW4MyxJg].

### 2.10 Far-OTM "penny" selling on expiry day

**The method.**
- Sell far-OTM options at ₹0.25–5, expecting them to decay to zero [cA07gugsaeY, 9a3TdAs7xUw, KqKOdPHFG-I].
- Sell early in the day, because waiting leaves too little premium. Example: an 11,900 call at about ₹4 [9a3TdAs7xUw].
- No hedge: the hedge would eat most of the credit. Example: a 37,000 call at ₹5 vs a further call at about ₹4.2 [KqKOdPHFG-I].
- A highest-OI far call at about ₹3 can be shorted with a stop at ₹6–7 [GsrNVbSwH04].

**When not to sell a straddle instead.** He passed on a straddle in a choppy market because its premium, about 20 points, was too small [cA07gugsaeY].

**Crypto version.** Sell far-OTM Bitcoin options only in the last 3–4 hours before expiry, in high volatility [3MMjcR_ortI].

### 2.11 Directional selling: puts with the trend or at support, calls into spikes

**Long side (selling puts):**
- In uptrends he sells puts or put credit spreads [rc4ZbNpzND8, c1hz4zsTuvc]. He credits about ₹45 lakh in July to put selling in an uptrend [WtIVfzJvJUg].
- Puts at support:
  - Bank Nifty 35,500 [s2KhVugNPfI].
  - A strike just defended as support: 34,700, 1,500 quantity, next week. He would add the call side if price returns there [H_XvaXezEU0].
  - Hold while 34,700 holds [hm1ZKfkO9Oo].
  - Large put-OI strike [OBJL069UfRQ].
  - 18,000 Nifty put at about ₹55 [4hAvzzjA2xw].
- After Bank Nifty closes above the heavy call-writing strike (35,500), sell naked puts at 35,000 for the week [2SuMQE03v2w].
- After an upside breakout:
  - About 5,000 quantity of OTM puts each in Bank Nifty and Nifty, around 13:00 [oIU_xUVFnwk].
  - After a breakout above 16,325, he added 2,500 short puts. He cited Europe gapping up and positive US futures, and it was allowed only because his loss cap still held [2dJOkeen6RM].
- Put selling is conditional on support holding (15,500 or 15,800) [YhGttuO7nGQ].
- **Drawdown puts:**
  - After about a 17% fall, sell 13,000 June puts at about ₹150, about 12–13% OTM. Framed as an idea, not executed [GEdPl2wK2mY].
  - Month-end Bank Nifty puts 4–9% below spot: 32,000, 32,500 and 30,000 strikes, 6,000–9,000 quantity [_sEwi7lQuNA].
- **Pre-event ITM put** [urrT8zpnGus]
  - 20 lots of the 41,500 put before the Fed decision, expecting 75 bp to be priced in.
  - Loss about ₹2.4–2.5 lakh on a 700-point gap down; worst case about ₹5 lakh (1% of capital).
  - Gain about ₹2.2 lakh if flat or higher.
- **Cash-secured puts** on Nifty, Bank Nifty and large stocks [ilbYdeALr0M]:
  - Stocks named: Reliance, HDFC Bank, Asian Paints.
  - He treats the MTM loss as notional because he is happy to take delivery, for example HDFC Bank below 1,200.
- **Cost-offset put.** A far-OTM put (36,000 strike, about ₹50, 1,000 quantity) sold only to cover about a week's brokerage [RFvomGYSt6k].

**Short side (selling calls):**
- On a bearish expiry day, do not sell calls at the open. Wait for a spike toward resistance and sell into it. In his example the premium held until about 14:00 [T2p11C5qPxk].
- On a down-trending day: a ladder of OTM calls at and above broken resistance, plus short futures [YhGttuO7nGQ].
- Trend-following call writing: he stays bearish short-term through call writing [YhGttuO7nGQ].
- Adding 35,500 calls when an intraday rally stalled [OSNCbyGvQm4].

**Risk warnings he gives:**
- A naked put held overnight met a roughly 1,300-point fall on war news [-kE6iIjC1Ys].
- Full-capital naked puts the day before a heavyweight result [BT__dPid_rk]:
  - ₹10 lakh capital, about 8 lots of 1% OTM puts at ₹28–30.
  - Premium earned was about 0.5–1% of capital.
  - A 4% fall would cost about 21–22% of capital.
- Trending, volatile markets punish sellers, and rising IV hurts even sellers who are right on direction [UaR5uzHcLos, bxx4CGJ39Ks].

### 2.12 Event-day straddles

**Budget-day system** [8No43FVgZfU, dzFMyd0FiXA, bLFCt52D89o]:
- Sell one ATM straddle each in Nifty and Bank Nifty at 10:00, and again at 11:00.
- 40% stop on each leg's premium; no further trades after 11:00; exit at 15:29.

**Budget-day results he reports:**
- The 11:00 Bank Nifty straddle was stopped for about −₹1.3 lakh.
- The IV crash after the speech then swung it about ₹1.4 lakh.
- Combined profit about ₹4 lakh by 13:30 and about ₹7 lakh for the day.
- The Bank Nifty straddle premium fell from about 1,300 to about 1,000 points in roughly an hour.

**Later Budget version** [QVeSJBPD_i4, xj-1uHZotgY]:
- An ATM straddle every 30 minutes from 9:30 to 12:00 (six entries), exit 15:23.
- Sized by time slot as in 2.2.

**RBI policy** [s7M-kuYOROU]:
- Bank Nifty straddle collecting about 800 points (80 lots).
- Wings about 700 points away in larger size (100 lots), so that a very large move helps rather than hurts.

**Results days.** See the warning in 2.11 [BT__dPid_rk].

### 2.13 Carrying short premium overnight into expiry

**Gap tolerance he states:**
- A neutral structure carried overnight profits on a 0.2–0.3% gap and loses little on 0.5–0.6% [j-S_P5NMkDs].
- Avoid a biased overnight structure, for example rich puts with cheap calls, when unsure [j-S_P5NMkDs].
- A call-side credit structure tolerates a 0.25–0.30% gap-up and gets painful beyond that [QIcP9ScvavE]. The captions are garbled.
- A 1,500-point Bank Nifty gap is no big problem for a wide-break-even position [it9ef0_jnVY].

**Losses he accepted in advance:**
- About ₹3–4 lakh on an 800-point gap-down for a 34,300 Bank Nifty straddle [2rTZM1IF6DE].
- About ₹2.3 lakh, about 0.5% of capital, on a +2% gap [RiTtKlJDrdI].

**Recovery after a gap.** After a gap-up, consolidation took a hedged book from about −₹90k to about +₹1 lakh in about an hour [KqKOdPHFG-I].

### 2.14 Covered calls and collateral overlays

- **Against covered calls** [m3izeXsRdW8]. The popular claim is about 10–12% extra a year. He argues covered calls cap returns: one big month wipes out a year or more of premium. His examples: ITC about +30% and Infosys about +25% in a month.
- **Positive view of a related combination** [sk4_m8Yfzu0]. A short ATM call with futures works acceptably in quiet or mildly rising markets because the call's time premium stays roughly constant. This is low clarity.
- **Layered return** [yDec0_hqKWk]:
  - Equity earns about 12–15%.
  - Pledged equity serves as margin for an option or futures overlay adding about 5–18%.
  - Combined target about 20–30% a year.
- **Pledging rule (India).** Pledged margin can be used to sell options and to trade futures, but not to buy options or shares [GZlwZIH4UOI].

### 2.15 Win-rate and risk claims

**Win-rate claims:**
- Sellers win about 66–67% by default, because they win in two of three market outcomes [uN9SRyTv_yY, NXE7KFxmH7I, 3MMjcR_ortI].
- Markets are range-bound about 60% of the time [VnlxZ2uP47M] or about 66% [O0PDivTMZXE].
- Neutral selling wins 58–60% vs about 40% for directional trades [IMjqrkYosgY].
- About 70% winning days [8i-eCbGznbo].

**Loss caps:**
- 1–2% of capital per loser [uN9SRyTv_yY, P21vgTId9P8].
- About 2% loss vs 1–2% gain per trade [GsrNVbSwH04].

**Instruments.** Sell index options, not stock options, especially with small capital, because of liquidity [BFZXz79936Y].

**Gross vs net.** A single day showed ₹99.5k gross, about ₹82k after about ₹17.5k of charges [3rLNeQZk0mk]. Charges are material.

### 2.16 Bitcoin variants (Delta Exchange)

- **Weekly ATM straddles:**
  - 19,500 strike, about 1,300 points collected, break-evens about 18,200 / 20,800 [MeKx6Qh50vs].
  - 21,500, slightly bullish tilt, about $857, with complementary put sales [VmiJLxaYPUQ].
- **Same-day strangle** [uN9SRyTv_yY]: 38,500 put / 39,750 call, about 4 hours to expiry, 0.5 BTC per leg.
- **Daily iron condor** [LrBXT5C_YYY, Hma2mI-kOjY]
  - Enter about 14:00–14:15, exit at the 17:30 expiry.
  - Shorts 750 points out, wings 1,000 points out, 100% stop on each short leg.
  - He found that a roughly 1% Bitcoin move hit the stop while the wing gained little.

---

## 3. How a program would test it

1. **Timed ATM straddle grid (Bank Nifty and Nifty weeklies, 2017→present)**
   - Grid:
     - Entry times: 9:20, 9:30, 10:00, 11:00, 11:30, 12:30, 12:45, 13:00, 13:30, 14:00.
     - Per-leg stops: 25%, 30%, 40%, 50%, 75%, 90%, and 70-point index-based.
     - Exits: 14:55, 15:00, 15:20.
   - Measure win rate, average win and loss, expectancy ratio, and maximum drawdown, net of brokerage, STT, exchange fees and slippage of at least 0.5%.
   - Check his specific numbers:
     - 9:30 with 50% stop: about 72% wins, expectancy 0.24 [L9f-oq8XVOo].
     - 13:00 with 30% stop: about 67–71% wins, roughly 1:1 win/loss [8i-eCbGznbo, lkOC0gpSmQQ].
     - 14:00 with 90% stop: highest expectancy, 0.36 [L9f-oq8XVOo].
   - Data: 1-minute option prices by strike and expiry, 1-minute index data, VIX, historical lot sizes, and the expiry calendar.
2. **VIX conditioning.** For the 9:30 Nifty straddle with 70-point stops, compare buckets VIX < 14, 14–20 and > 20 on expectancy, no-stop-hit rate and double-stop rate. His claim is 0.38 vs 0.23 vs 0.17, and double stops about 3% vs about 14% vs about 30% [X8sW2WNaKAs]. Repeat for the 13:00 Bank Nifty variant.
3. **Day-type attribution.**
   - Classify days as:
     - Range: small high-low.
     - Trend: close near an extreme.
     - V-reversal: large excursion with close near open.
     - Mild trend: 0.8–2% net move.
   - Test whether the losses of timed straddles concentrate on V-days [vmjxCxSdIn0, hPUdSoT2c7g] or on mild-trend days [8i-eCbGznbo].
   - Test whether the stopped leg is outweighed by the surviving leg on strong-trend days [c29sN7KQSIs].
4. **Staggered vs single entry.**
   - Same total quantity, split across 3–6 time slots vs one slot.
   - Compare expectancy and drawdown. He claims expectancy about 0.5 vs about 0.25 [lkOC0gpSmQQ, xj-1uHZotgY].
   - Separately test unlimited re-entry after stops on gap-plus-trend days, where he expects losses [LPGCiis_rlg].
5. **Overnight pre-expiry strangle.**
   - Bank Nifty, sell 200 points OTM each side at 15:15 the day before expiry, exit 9:20 on expiry day, with holiday shifts.
   - Run unhedged and hedged with a 75% stop.
   - Target figures: about 83% wins, unhedged drawdown about 11%, hedged drawdown about 20–25% lower [oYfLG7jLvPQ].
   - Include the full period after his sample, when expiry weekdays changed.
6. **Implied vs realized filter.**
   - Next-day or next-week P&L of ATM straddles, conditioned on the ratio of recent realized moves to the straddle price.
   - He expects losses when realized moves exceed the straddle price for several days [V-R9YyFioe8, X5jF4csZwh8, pZPCRg5w9gw].
   - Add the 0.4%-of-spot premium floor rule [2m1GpJzXBt4].
7. **Trend-filtered put selling.**
   - Sell OTM index puts at a fixed delta or distance only when the index is above a trend filter, vs unconditionally.
   - Compare expectancy, tail loss and overnight-gap loss [WtIVfzJvJUg, c1hz4zsTuvc, rc4ZbNpzND8]. Include event days separately [BT__dPid_rk].
8. **Covered call vs buy-and-hold.**
   - Monthly ATM or OTM call overlay on the index and on large stocks vs holding the underlying.
   - Test whether a few large up-months drive the underperformance he claims [m3izeXsRdW8].
   - Data: monthly option chains or an existing benchmark such as BXM for the US.

---

## 4. Transfer to Canadian (TSX) and US markets

**Applies as it is, as an idea:**
- Short-premium logic: range days favour sellers, V-reversals hurt per-leg-stop straddles, trend days are survivable with fast stops.
- The decay timing idea of selling into the last hours.
- Premium balancing between call and put legs.
- Break-evens checked against support and resistance.
- The implied-vs-realized check.
- His warning about naked selling before events.
- His covered-call critique (and the opposing evidence) can be tested directly on US data.
- Cash-secured puts on stocks you would own.

**Needs adapting:**
- **Instruments.** The Indian weekly/expiry-day structure maps best to US SPX/XSP/SPY/QQQ 0DTE and daily expiries. The timed intraday straddle and late-session trades can be retested there, but:
  - Clock times must be re-chosen for the 9:30–16:00 ET session.
  - Point-based stops and strike distances (70 points; 100/200/300/500/750/1,000-point wings) must become percent-of-spot or delta-based.
- **Canada.** Index options (SXO on the TSX 60) are thin. Use US-listed options or liquid single-stock options on large TSX names, mainly for cash-secured puts and covered calls.
- **Costs and taxes.** US commissions and fees are lower than Indian STT-heavy costs, but bid/ask spreads on SPX are wider in absolute terms.
- **Margin.** Portfolio margin and PDT rules differ from Indian SPAN plus pledging.
- **OI-based strike selection.** US OI data is available, but its behaviour (dealer positioning) differs, so it needs revalidation.
- **Events.** Budget and RBI days map to FOMC, CPI and NFP days, and results-day naked puts to earnings. The IV-crush logic should be retested per event type.
- **VIX thresholds.** India VIX < 14 and > 20 do not equal the same US VIX levels; use percentile ranks.

**India-only:**
- Budget-day timing.
- The 15:22 intraday auto-square-off workaround (use a regular rather than intraday order).
- MIS product type.
- Pledged-collateral rules.
- Physical settlement of stock options.
- Bank Nifty/Nifty lot sizes and the weekday expiry calendar, which changed after his videos.
- His rupee results.

**Exchange-specific:** the Bitcoin variants use Delta Exchange timings and daily crypto expiries.

---

## 5. Gaps and doubts

**Backtest quality**
- Costs are excluded in [L9f-oq8XVOo], unstated in [8i-eCbGznbo], and modelled only as 0.5% slippage in [lkOC0gpSmQQ].
- The naked weekly straddle backtest has no reported result [1fDefykVmnk].
- The VIX > 20 double-stop rate is ambiguous: 30% or 13% [X8sW2WNaKAs].
- Most rupee figures are single-day, self-reported, live-session outcomes.

**Inconsistencies in the system rules**
- The entry times differ across videos.
- He says morning entries with a 30% stop fail [HcdusL_8W5U], yet the 9:30 variant with a 50% stop is positive in his own backtest [L9f-oq8XVOo].
- Stop basis (per leg vs combined; premium vs index points) is often unstated [F5O2b6_5npQ, Fe766Um-ayQ, L3PBLOfzI6w].

**Contradictions**
- Straddle vs strangle preference flips across videos (2.6).
- "Never sell ITM" [l4jQUXK6UOc] conflicts with his repeated ITM strangles [IeeFqzGWEv0, 9lj7Ta-vsmc, kaPyJdhVI9c].
- Plain vs inverted strangle: the promised explanation was never given [oQXCIfaJ1fs].
- Low VIX is "best for the system" [X8sW2WNaKAs] but also "premiums too small, book early or go to next week" [kaPyJdhVI9c, wcTPYuhzvAU].
- The losing day type is V-reversal in most videos but mild-trend in [8i-eCbGznbo].
- Late-session decay trades are praised [YtLDcJgJzcQ, N8jDRk63lK0] but also blew up [LPGCiis_rlg].

**Thin areas**
- Credit spreads are barely covered, and the captions are garbled ("pull put sprint", "racial trades") [hPUdSoT2c7g, QIcP9ScvavE].
- Covered calls appear only as a critique.
- The collateral overlay has targets but no method [yDec0_hqKWk].
- Adjustment rules are referred to but mostly not specified here [8W58_AoCKrw, kyQf5lGc_6s, GWbpgCAAMkM, 91-eSFLtkhg]. No rule says when to stop re-entering after repeated stops.

**Unclear structures.** Several videos give no recoverable structure or rules [QdIk7kAkHHc, her05sgUyOQ, c4yDnTlhYSM, 5_i637lBoPU, Gv3AMZVWrrI, 3PZu-YM162o, CfriQ26BKrs]. "Triangle" in the captions usually means strangle.

**Shift in his teaching.** His later framing — non-directional only inside a defined range, directional spreads after a breakout [F0x5faXXRTI, Mt5qSl4j3fQ, Vp6a7TiKiZk] — qualifies the earlier unconditional daily timed-straddle approach. No video reconciles the two.

**Not covered here**
- Assignment and early-exercise handling.
- How sizing scales with account size, beyond the 1–2% loss cap.
- Out-of-sample performance after 2021–2022.
- Behaviour under the later changes to Indian expiry days.
