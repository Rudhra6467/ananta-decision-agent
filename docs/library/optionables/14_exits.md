<!-- Trading Knowledge Library · Optionables (Optionables, India). Built 2026-10-16 from 434 public videos with captions (of 459 on the channel; members-only videos were not used): one structured note per video (Claude Sonnet 5.5) -> this chapter (Claude Opus 5.5), src/research/library.py. Paraphrased; the transcripts stay on the laptop. Evidence class: external teaching = hypotheses to test, never Ananta rules; nothing in the agent reads docs/library/. -->

# Exits

## 1. What he teaches here and how it fits his method

Optionables is mainly a seller of index option premium. His core trades are intraday and expiry-day short straddles and strangles on Bank Nifty and Nifty, plus positional ratio spreads, calendars and condors. For him, exits matter more than entries. He insists the exit plan exists before the trade is placed [uN9SRyTv_yY, iZcd9gImTFU].

His exit toolkit has six layers:

- **Per-leg stop on the sold premium.** Placed right after entry. This is by far his most repeated rule.
- **What to do with the surviving leg** once its partner is stopped.
- **Level-based exits on the underlying.** Used mostly for positional books, often set inside the break-evens.
- **Loss caps.** Either a percentage of capital or a rupee mark-to-market cap, combined with a refusal to keep adjusting a messy position.
- **Profit-taking.** Either a share of the maximum achievable profit or a rupee/daily target, often with partial scale-outs and a fresh re-entry.
- **Fixed clock exits** shortly before the Indian close.

Much of the material is live-trade narration and post-mortems, not formal rules. Many "lessons" are hindsight about a single day. Everything below is his claim or practice and should be treated as a hypothesis.

---

## 2. The ideas

### 2.1 Per-leg stop on short option premium (short side)

**What it is**
- Each sold leg of a straddle or strangle gets its own stop. The stop is placed immediately after entry, as an order at the exchange [ybZYfvQzy7E, A0sLu7cjjlU, lkOC0gpSmQQ, BFZXz79936Y].
- He says a combined stop cannot be set manually, and that a pre-placed stop removes panic and hesitation [BFZXz79936Y].
- He claims he never holds a short leg without a stop since a crash in which an unstopped short put went from about 40–60 to about 360 [IMjqrkYosgY].
- The purpose: in a trend one leg exits quickly and the other keeps decaying. This means he does not have to keep adjusting [lkOC0gpSmQQ, G2Jm-SaT6M8, O0PDivTMZXE].
- He also says per-leg stops make "unlimited loss" a misconception, because the surviving leg tends to profit if the move continues [O0PDivTMZXE].

**Widths he has used (they vary a lot)**

| Stop basis | Width | Videos |
|---|---|---|
| % above entry premium | 30% (e.g. 300 → 390; 500 → 650) | 8i-eCbGznbo, NXE7KFxmH7I, 09Bt6pDtUpw, IMjqrkYosgY, HcdusL_8W5U, lkOC0gpSmQQ (system tests) |
| | ~35% (75 → 101) | GQEbyZhG-ME |
| | ~25–35% (stop ~430 on ~320–350 entry) | WAXCM9CDx8g |
| | 40% morning, narrowing to ~30% later in the day | BFZXz79936Y |
| | 40% | bLFCt52D89o |
| | ~40–50% (85 → 130; 75–80 → 108) | UEOPUfhENcE |
| | ~1.5× entry (stop ~350 on entries of ~200–290) | peakDi79pVs |
| | 50% (e.g. 500 → 750) | QVeSJBPD_i4, JPqXyHXfGfg |
| | 75% | xXDwxid9Fjc, V-R9YyFioe8, LK5yGOZMcj0, uoFMqwhG5-4, Pt5pbpK1eoI; QEj_68mxDHI (unclear) |
| | 100% (exit when the option doubles), crypto | Hma2mI-kOjY, 3MMjcR_ortI |
| | ~2–3× sold price, far-OTM expiry shorts | cA07gugsaeY |
| Fixed premium points above entry | 100 (400 → 500, "no deeper logic") | oIU_xUVFnwk |
| | ~60–80 | lkOC0gpSmQQ |
| | ~70–85 on ~100 premiums | YtLDcJgJzcQ |
| | 50 (220 → 270) | UIf_6_Bg66I |
| | 40 (Nifty put) | RiTtKlJDrdI |
| | fixed level of 120 on legs sold ~32–65 | F6sjGAcJXXc |
| Underlying points per leg | ~50 (40–50, "arbitrary") | G2Jm-SaT6M8 |
| | ~100–120 | fQfzG_emzZw |
| Combined straddle premium level | 101 | pdGXhkLJPj0 |

Per-leg stops are also mentioned with no width given in: vmjxCxSdIn0, _dQVN0WKeCE, 7RI6oed3Eak, c29sN7KQSIs, M18fQBnjMLA, jztFfYokRqI, GxKIIKl4eZA, wr82JkzZyys, 6knNR520aK8, yvSFv0dQQVI, ocl7mwUeZA8, wdUlevVfZL4. In wdUlevVfZL4 the put stop was raised from 320 to 340 to 360 across re-entries.

**Conditions and changes in his view**

- **Time of day.** He says 30% is too tight in the morning, when the market is volatile after the open, and suits entries after about 13:00 [HcdusL_8W5U]. BFZXz79936Y has the same idea: wider in the morning, tighter later.
- **30% vs 75%.** In one video he moved from 30% to 75% and ran both side by side:
  - the normal system: 30% stop, overnight-product orders;
  - a larger intraday version: 75% stop [uoFMqwhG5-4].
  
  In another, he calls his main account's 75% stop a disadvantage on a crash day. Accounts with 30% stops finished profitable because their surviving call legs kept decaying [Pt5pbpK1eoI]. He gives a rationale for 75% too: it leaves room for big two-way institutional swings [V-R9YyFioe8].
- **Low premiums: the videos contradict each other.**
  - On a very low-premium day he widened the stop to 75% [BFZXz79936Y].
  - Elsewhere he dropped premium stops entirely when premiums were low. A 40–50% stop would trip on a 50–60 point Bank Nifty move, so he relied on small size and hedges instead [P21vgTId9P8].
- **Moving to defined risk instead of stops.**
  - If a stop is so tight that an IV spike alone can hit it, use a defined-risk structure instead [6WGhlEAouxM].
  - A modified iron condor system uses no stop and sizes so the worst case is small [LrBXT5C_YYY].
  - A base iron condor system has no stop or target, only the expiry-time exit [ZJyMZJekVBk].
  
  These are the 2–4-year-old videos. The per-leg percentage stops are mostly 4–5 years old. That suggests, but does not prove, a shift over time.
- **Crypto.** He chose 100% because 30–50% stops get hit by normal swings and the option then decays to zero anyway [3MMjcR_ortI].

**Evidence he cites**

His only quantified evidence is one in-sample backtest of a Nifty strangle with ±100-point strikes, entered 12:30 and exited 14:55, 10 lots, about Feb 2019–mid 2021 [NXE7KFxmH7I]. The note flags the with-stop figures as uncertain because of captions.

| Version | Profit | Win rate | Worst day / drawdown | Return on capital (as heard) |
|---|---|---|---|---|
| No stop | ~6.1 lakh | ~73% | worst day ~1.8 lakh | ~18% |
| 30% per-leg stop | ~12 lakh | not given | max drawdown ~34k | ~35% |

With the stop, stops fired on about 121 days, and both legs were stopped on about 55 of them.

**Failure modes he admits**

- **Whipsaw / double stop-outs.** Examples:
  - six stops hit on a day Nifty closed nearly unchanged [AyC9r0_ZiN8];
  - +2.5 lakh at the peak to −50k at the close [hLfnVGcoX_w];
  - all four sides stopped, about −6.5 lakh [ocl7mwUeZA8];
  - a loss after a stop then a bounce [9pT7h-M2v64];
  - a 14:00 straddle stopped on both sides [fQfzG_emzZw];
  - a 350-point crash in about 15 minutes cut MTM from ~1.1 lakh to ~10k [GxKIIKl4eZA].
- **Stop placed at the worst price.**
  - A put sold ~180 was stopped ~310 at the day's high, then went to zero [3uZnthbvz3A].
  - A stop tightened late in the day cost about 2.5 lakh versus a stop 10 points wider [vmjxCxSdIn0].
- **Stop left too loose.** A put stop sat at 245 when the option traded ~40, as the market crashed toward support. He says he should have trailed it [fQfzG_emzZw].
- **Fills not visible on the chart.**
  - A stop was hit by about 5 points on a wick the chart never showed [dzFMyd0FiXA].
  - A fill at 977 when the candle high showed 952 [bLFCt52D89o].

---

### 2.2 The surviving leg after one leg is stopped (short side)

He uses several incompatible rules, sometimes in the same video.

1. **Leave it to decay until the time exit.** Watch only that the index does not cross back over the strike [vmjxCxSdIn0, A0sLu7cjjlU, 7RI6oed3Eak, -wVTqlE51C8]. In HcdusL_8W5U he did no counter-trade, let the put decay to about 70k profit, then closed because he was uncomfortable with the size.
2. **Move its stop to cost (entry price).** He presents this as a system rule [oQXCIfaJ1fs, Fe766Um-ayQ] and as an app feature [_sEwi7lQuNA]. Once it backfired: the cost stop was hit on the bounce [dzFMyd0FiXA].
3. **Close it immediately.**
   - In a very volatile, high-VIX market: he cannot judge a reversal, so he took only ~5k [N8jDRk63lK0].
   - After a sharp one-way move with good profit, he would consider exiting rather than holding to about 15:20 [xj-1uHZotgY].
   - Close everything and re-sell a new at-the-money straddle [NTavZ18KPh8].
4. **Hold until the underlying crosses a level.** Same video as rule 3: the put was held until Nifty fell below 17,000, giving ~70k combined [N8jDRk63lK0].
5. **Counter-trade instead of adjusting** once a stop has fired. Shifts are only done before the stop triggers [LK5yGOZMcj0, wcTPYuhzvAU].
6. **Asymmetric stops on a directional view.** A very tight call stop (250 on a ~224 entry) while the put rides [XA-oogDFs2s].

---

### 2.3 Exits on the underlying's level (mostly positional books)

**What it is.** He fixes, in advance, an index level, band, or trend line. He exits the whole book on a break, rather than waiting for premium stops or hoping for a return.

**Bands and levels on short straddles/strangles**

| Video | Exit rule |
|---|---|
| h5XNvyTMSsk | below 33,000 or above 35,500 (support/resistance); est. loss ~4 lakh unadjusted |
| 7LlVnFIIEB4 | band 36,200–36,900, inside break-evens of ~35,835 / 37,201 |
| F6sjGAcJXXc | narrow band 35,800 / ~35,960 around the strike |
| XLBtvv6Jq18 | Nifty close above 18,000 or break of 17,400, with no adjustment (little premium left later in the week to adjust with) |
| 9a3TdAs7xUw | a trend-line level on Nifty (~12,080) for short puts, plus breaks of the expected range |

**Exit before the break-even, not at it**
- Exit at 37,200 vs a break-even of ~36,719 [GWbpgCAAMkM].
- Exit at 37,800 vs a break-even of ~37,427. He accepts ~1.5 lakh because losses accelerate beyond (1 → 4 → 6 lakh) and adjustment gets harder near break-even [Og7SQjotANg].

**Support levels for bullish positional structures**
- Exit if Nifty breaks 16,800 on a near expiry: no time left to adjust [tbHLBk84Btc].
- Bank Nifty 36,000: exit added puts in stages, or cut 80 lots to 40 below 36,200, then exit fully below 36,000, accepting ~1.0–1.2 lakh [tbHLBk84Btc].
- Bank Nifty 36,200 [z0Ke0RrtVHw].
- 37,500 [dPuJiR0oxRs].
- Adjust below 33,500, exit on a daily close below 33,000 (~1.2% of capital) [tY0noMv3lp0].
- A break of 34,700 as the review point [hm1ZKfkO9Oo].
- A reclaim of the hedge-purchase level [ZDUmKEZXWMw].
- 40,500 toward 40,700 for an added short call [-IDDp5bvrVQ].
- Settle below 38,000 [vRGhcoCUbBE].

**Closing basis vs intraday touch.** He repeatedly prefers closes:
- daily close [tY0noMv3lp0, drr-Gaxlp28];
- "decisive close" [tnuVuazeRw8];
- 5-minute close rather than a wick [XA-oogDFs2s];
- two 3-minute closes [xXDwxid9Fjc].

**Directional short (on the underlying)**
- Hold the short until a decisive close above 16,000 and cover in steps near 15,500 [tnuVuazeRw8].
- Pre-announced invalidation closes: Nifty 16,000, Bank Nifty 34,500 [nMlFJigaxnM]. Executed when Nifty crossed 16,000 with heavy put writing there [DXTdywSl0D0].
- Cover short futures above 16,800 [NwFNA0IjOkc].
- A stop on short futures near 16,600, unclear in the captions [5vAHDwZkoHc].
- Close an index hedge after a 20–25% fall, because a rebound is likely (his hypothetical) [w5oNCUY0Yyg].

**Directional long**
- Stop on a close just below the breakout (39,700 vs 39,800). Risk 100–120 points vs a 700–800 point target [xzkqo36gp8c].
- M&M: close below a 1,300 box floor, target 100–120 points above 1,340, about 1:6 reward-to-risk [drr-Gaxlp28].
- Long futures: 5–10% target, 10% stop tied to support [hPUdSoT2c7g].
- Trailing a long put to each new lower high on a 3-minute chart (34,700 → 34,650 → 34,500), exit on two closes below 34,500, half booked earlier [xXDwxid9Fjc].
- Bitcoin trailing stop, ~$80 loss [VmiJLxaYPUQ].

**Caution he gives himself.** On expiry day, a band exit (17,200–17,300) fired. The index then settled at 17,248, where both legs would have expired near worthless. He called the exit hasty [XmP7nK_TMdo].

---

### 2.4 Loss caps and "stop adjusting"

**Percentage of capital**

| Cap | Context | Video |
|---|---|---|
| ~2–2.5% (later 2–3%), max 3 adjustments | general trade exit | NSeHRFG7XVA |
| 3–4% of deployed capital; above 5% "psychology turns irrational" | put ratio spreads | o7lr4TUP3Yg |
| ~3% (a loss near break-even is ~1%, still adjustable) | short straddle | VmiJLxaYPUQ |
| 1.5–2% per trade (says his group's norm) | general | iZcd9gImTFU |
| ~1% of index move (~25k) | community trade | UIf_6_Bg66I |

**Daily rupee kill switches**
- 1% daily limit extended to ~1.3% because IV might cool, then tightened to 2.5 lakh, then closed at −1.79 lakh [Pt5pbpK1eoI].
- A trailing daily limit, 10 lakh moved to 8 lakh as the loss shrank [CfriQ26BKrs].
- Book-level stop of ~4.5 lakh MTM [BGRZRDCcNSI].
- −3 lakh on a naked put [35_p7TIkaTQ].
- Booked at ~−1.2 lakh after repeated adjustments [nXjmslNVkyo].
- Book at ±30k on ~5 crore scale [jp-dpnaLs38].
- App-level total-M2M exit, ±1,000 rupees in a demo [6lVvi-ULRVE].

**Exit when the position is messy or uncomfortable**

| Rule as he states it | Videos |
|---|---|
| Close, rethink, re-enter later | P21vgTId9P8 (~−25k), wdUlevVfZL4, HcdusL_8W5U, QED0exJOqYc |
| Close after many shifts | qyY60yFUp04 (~4 shifts) |
| Reset by judgment | -uIGVxZWSHU |
| No further repair after the straddle stage; rely on hedges | 8W58_AoCKrw |
| Close the next day rather than hold to expiry | 3VTymF8_eww |
| Square off at the open after a gap loss | CfriQ26BKrs |
| Cut losses while small (host/guest stream; the host attributes it to him) | dAx2mchFMSs |

He also admits the opposite error: holding a recovered loss of ~−1.2 lakh, which relapsed to ~−2.1 lakh [Pt5pbpK1eoI]. In CfriQ26BKrs he exited after recovering half a loss, and the market then came back to his strangle's center.

---

### 2.5 Profit-taking rules

**Share of maximum achievable profit (most codable)**

| Threshold | Context | Video |
|---|---|---|
| 70–75% of premium collected | his main stated rule; otherwise rely on the loss rule | VmiJLxaYPUQ, km4uw-zxRZM, JdR7-suVxCI (also 70%) |
| ~60–70% | discretionary trades only; system trades held to their rule exit without interference | d6ZOFGDVw2Y |
| ~60–65% (11–12k of ~18k) | community trade | 3VTymF8_eww |
| ~80% (15k of 18k), then roll | short straddle | VV3vue5PaQo |
| ~90% (19k of 21k) | bear call spread | ujTuECvyPzc |
| "most captured" | calendar | z0Ke0RrtVHw |

- **Exceeding the modelled maximum.** When MTM exceeds the payoff's expiry maximum (10.2k vs 8.6k), exit [lyQNM8KBec4].
- **Positional ratio spreads.** Take 3–4% of margin, often within ~20 days [lkOC0gpSmQQ].
- **Residual premium too small to be worth it.**
  - Buy back shorts near Rs 0.2–0.4 [cA07gugsaeY, GsrNVbSwH04].
  - Close when sold options are under ~10–15 [dPuJiR0oxRs].
- **Other target types.**
  - A bull call spread at its target [NSeHRFG7XVA].
  - A pair ratio held until it returns to its mean, with no stop or time limit [gFcyYYtgnOE].

**Rupee / daily targets (scale to his size, typically crores)**
- ~1 lakh daily lock [N8jDRk63lK0, jEF9S2_P5Po].
- 40–45k then 1 lakh [kaPyJdhVI9c].
- 30–40k in the morning, then re-enter in the afternoon [BFZXz79936Y].
- 50–60k on a straddle [ufH0zRUyuIw].
- A small target, then stop for the day, to recover losses [xwjZpXxwr5I].
- An expiry-day intraday target of 1.5–2 lakh [OSNCbyGvQm4].
- Points per trade:
  - 10–15 points per straddle [UIf_6_Bg66I];
  - 3 points per leg in an app demo [6lVvi-ULRVE];
  - repeated ~15k bookings [7RI6oed3Eak].

**Trailing profit floor**
- Book half near 3 lakh, then exit if profit falls below 3.5 lakh, then below 4 lakh, in 50k steps [bLFCt52D89o].
- Exit when a late trend move erodes open profit [H_XvaXezEU0].

**Book on retracement**
- After shifts, exit when price returns to the center in profit [VnlxZ2uP47M].
- Exit all on a 500-point reversal [8W58_AoCKrw].
- Stop re-adjusting once recovered to +1 lakh [KqKOdPHFG-I].
- Book when an in-profit short sees the market turn back toward it [cA07gugsaeY].

**Volatile or trending days: book quickly.** Videos: Bqh1AevjUzg, L8SZ30on7po (IV can spike at any time), ApP_IR63Ff8, aKHjPFQ75dk, 3rLNeQZk0mk, uoFMqwhG5-4, mDW8Ih4CuuY (news).

**Counter-evidence in his own narration**
- He regrets booking early: ~60–70k vs ~2–2.5 lakh if held [0ioEL11p1kk].
- Holding paid in tn3IDCnC6dc and wdUlevVfZL4.
- Not booking cost him in:
  - pZPCRg5w9gw;
  - tKlpB5RfdFA (+40–50k to −40k);
  - oIU_xUVFnwk (10.5 → 9 lakh);
  - 6knNR520aK8 (waited 10 minutes past a ~20k plan, went to −30–40k);
  - jEF9S2_P5Po.
- d6ZOFGDVw2Y says that for non-directional selling, more time means more decay, so stay in until exit criteria.

---

### 2.6 Partial exits and scaling out

**Halves**
- Half at a profit [7LlVnFIIEB4, GsrNVbSwH04, c29sN7KQSIs, cA07gugsaeY].
- Half near the close on expiry [9a3TdAs7xUw].
- Half when the index hits a pre-identified support while in profit (2,000 of 4,000) [JPqXyHXfGfg].
- Half, then half again, as the favourable move extends [-wVTqlE51C8, dAx2mchFMSs guest].
- Unclear captions [GR_KV8MlHZI].

**20–25% slices with basket and market-protection orders**
- IMjqrkYosgY, wdUlevVfZL4, wcTPYuhzvAU.
- In wdUlevVfZL4 and wcTPYuhzvAU this is partly framed as a slippage control.

**Staged size cuts**
- 700 quantity booked near 3 pm [ybZYfvQzy7E].
- 80 lots, then the rest [tbHLBk84Btc].
- Gradual square-off in the first hour of expiry if the open is near the strike [oAJ8k8TzB7E].

---

### 2.7 Time exits

**The 14:55 rule**
- 14:55 for the 1 pm and 12:30 systems [8i-eCbGznbo, NXE7KFxmH7I].
- Reasons he gives: afternoon theta, fewer V-reversals, and rising risk after 3 pm.
- In hqdIcWNjFgE, 14:55 is an announced experiment after seeing profits drop after 3 pm.
- Close naked legs at 2:50–3:00 and the rest by 3:20, because markets often reverse after 3 pm [V-R9YyFioe8].

**Later exits he has used**

| Exit time | Videos |
|---|---|
| 2:58 | 4hAvzzjA2xw |
| 3:05–3:15 | wdUlevVfZL4 |
| 3:08 | 4Zd60oo6vOM |
| 3:12–3:13 | aKHjPFQ75dk, OGPVzN-tt3k |
| ~3:15 (broker intraday cutoff) | GsrNVbSwH04 |
| 3:15–3:30 | d6ZOFGDVw2Y |
| ~3:20 | uoFMqwhG5-4, pdGXhkLJPj0 |
| ~3:22 | GQEbyZhG-ME, HcdusL_8W5U, M18fQBnjMLA |
| ~3:25 | ybZYfvQzy7E |
| ~15:20 | xj-1uHZotgY |
| 2:50 onward, stops cancelled first | A0sLu7cjjlU |
| 15:29 (backtested systems) | 8No43FVgZfU, ZJyMZJekVBk |

**Evidence about the final minutes points both ways**
- Holding later hurt:
  - two extra minutes and a ~150-point rally cut ~2 lakh to 1.26 lakh [aKHjPFQ75dk];
  - holding past the usual time shrank the profit [ybZYfvQzy7E].
- Holding later helped:
  - 3:29 would have given 2.54 lakh vs 76k at 3:22 [GQEbyZhG-ME];
  - premiums only cooled after ~3:10–3:15 [pdGXhkLJPj0].

**Other clocks**
- Overnight strangle: at ~9:16, if any sold leg is ≥75% above entry, close all four legs; otherwise exit at 9:20. He notes stops cannot be held overnight [oYfLG7jLvPQ].
- Next day after the open, unclear [sk4_m8Yfzu0].
- Crypto exits at 5:30 pm [LrBXT5C_YYY].

**Intraday-only vs carrying positions**
- Algo and intraday trades are never converted to positional [d6ZOFGDVw2Y, oQXCIfaJ1fs].
- Yet leftovers are converted to the overnight product (NRML) in GsrNVbSwH04.

---

### 2.8 Exit-and-re-enter

He often flattens and starts fresh rather than holding:

| How he re-enters | Videos |
|---|---|
| New at-the-money strike after a stop or near-stop | NTavZ18KPh8, 6knNR520aK8 |
| Flatten at breakeven, re-sell, gained ~1.8 lakh | JPqXyHXfGfg |
| Afternoon re-entry after a morning booking | kaPyJdhVI9c, BFZXz79936Y, mDW8Ih4CuuY, -uIGVxZWSHU |
| Roll to the next expiry | VV3vue5PaQo, JdR7-suVxCI |
| Risk only the profit already booked | RFvomGYSt6k |

Re-entries that lost or added nothing:
- N8jDRk63lK0 (−10k);
- 6qive5Kb4Jk (another −1 lakh after −1.5 lakh);
- GJ-1jOUSekk (−54k);
- 0ioEL11p1kk (nothing earned).

---

### 2.9 Order mechanics for exits

**Stop-limit vs stop-market: his advice conflicts**
- Use stop-limit: trigger 500, limit 510–520 [JfeLqaREQU0].
- Leave at least 3–4 rupees between trigger and limit on a ~20 stop, and even 5–6 can fail in a spike [dmZmt1T5bU0].
- For large size, use stop-market, since a limit may miss [8i-eCbGznbo].

**Limiting slippage on bulk exits**
- Market orders with 0.5 "market protection" [A0sLu7cjjlU, IMjqrkYosgY, uoFMqwhG5-4, wcTPYuhzvAU].
- Exit in ~20% slices [wdUlevVfZL4].

**How his app handles targets.** Targets are watched in the app and fired as market orders, because a resting target plus a resting stop would need extra margin in India. Fills can be worse than the trigger: a 150 trigger filled at 135 [6lVvi-ULRVE].

**Slippage examples**
- Aimed at 1.2 lakh, got 1.05 [HcdusL_8W5U].
- 60–80k shrank to 20–25k [GJ-1jOUSekk].
- A target filled at 90 while the low reached 70–80 [RiTtKlJDrdI].

---

## 3. How a program would test it

**Data needed throughout**
- 1-minute (ideally tick) option quotes and trades for Nifty/Bank Nifty weeklies.
- Underlying index and futures bars.
- India VIX.
- Realistic slippage and cost models.

Tick or quote data is needed because he reports stop fills at prices the candles did not show [dzFMyd0FiXA, bLFCt52D89o].

1. **Per-leg stop width × entry time.**
   - Trade: sell an at-the-money straddle on the weekly at 09:30, 12:30 and 13:00; exit at 14:55.
   - Compare per-leg stops of none, 30%, 40%, 50%, 75% and 100% of entry premium, plus fixed point stops (premium +40/+50/+100).
   - Report expectancy, max drawdown, double-stop frequency and the tail of daily losses.
   - Sub-hypotheses:
     - 30% beats 75% for afternoon entries but not morning entries [HcdusL_8W5U, BFZXz79936Y, Pt5pbpK1eoI, uoFMqwhG5-4];
     - the result replicates the NXE7KFxmH7I claim of roughly doubled profit with lower drawdown, out of sample.
   - Split results by premium regime (lowest premium tercile) to settle the low-premium contradiction [P21vgTId9P8 vs BFZXz79936Y].
2. **Surviving-leg policy.**
   - Same entries, 30% stops. After the first leg stops, compare: hold to 14:55; move stop to cost; close immediately; close immediately only when India VIX is above a threshold such as the 80th percentile.
   - Sources: oQXCIfaJ1fs, Fe766Um-ayQ, N8jDRk63lK0, xj-1uHZotgY.
3. **Time-of-exit curve.** For afternoon straddles, mark P&L at each minute from 14:50 to 15:29. Test whether average P&L declines or rises after 15:00, and whether variance rises [8i-eCbGznbo, hqdIcWNjFgE, aKHjPFQ75dk vs GQEbyZhG-ME, pdGXhkLJPj0].
4. **Profit capture at a share of the maximum.**
   - Trade: weekly short straddle/strangle held from week start with a 3%-of-capital stop.
   - Exit when 60%, 70–75% or 90% of collected premium is captured, versus holding to expiry.
   - Compare win rate, mean, and return per day of margin used [VmiJLxaYPUQ, km4uw-zxRZM, JdR7-suVxCI, ujTuECvyPzc].
5. **Underlying band exits.**
   - Trade: positional short strangles.
   - Exit when spot crosses: (a) the break-even; (b) a level set X% inside the break-even; (c) never. Optionally test closing-basis vs intraday-touch triggers.
   - Measure worst-case loss and the profit forgone on reversions [Og7SQjotANg, GWbpgCAAMkM, 7LlVnFIIEB4, XmP7nK_TMdo].
6. **Daily MTM kill switch and profit lock.**
   - On an intraday short-premium book, apply a fixed loss cap (1%, 1.3% or 2% of capital) and a profit lock (e.g. 0.25–0.3% of capital).
   - Compare with holding to the clock exit [Pt5pbpK1eoI, jEF9S2_P5Po, BGRZRDCcNSI, jp-dpnaLs38].
7. **Stop order type.** Replay spike events using quote data. Compare unfilled-stop rate and realized slippage for stop-market vs stop-limit with gaps of 5%, 15% and 25% of the stop price [JfeLqaREQU0, dmZmt1T5bU0, 8i-eCbGznbo].

---

## 4. Transfer to US and Canadian markets

**Usable as-is in concept (US)**
- Per-leg premium stops, surviving-leg rules, percentage-of-max-profit exits, capital-percentage loss caps, underlying band/closing-basis exits and partial scale-outs are all market-neutral logic.
- Daily-expiry SPX/XSP, SPY and QQQ options are the closest analogues to his intraday weekly-expiry straddles.

**Needs adapting**
- **Clock exits.** "14:55" and "15:12–15:29" map to minutes before the US 16:00 ET close, but the late-session behaviour must be re-measured. His post-3 pm reversal claim is about the Indian session and his own anecdotes.
- **Fixed thresholds.** Point stops (40/50/100 premium points, 50 index points) and rupee targets must be rescaled to the instrument's premium level and the trader's capital.
- **US order handling.** Stops on multi-leg or spread orders are often not supported or are handled synthetically by brokers. Per-leg stops can widen risk on defined-risk spreads.
- **Settlement.** The settlement style of the product (cash-settled index vs physically settled ETF options) changes how "hold to expiry" behaves.

**Canada (TSX)**
- Options on S&P/TSX 60 and on XIU and similar ETFs exist, but liquidity and weekly expiries are far thinner.
- Wide bid–ask spreads would trigger percentage premium stops on noise and make stop-limit fills unreliable.
- His intraday expiry-day machinery is unlikely to transfer. His positional exits (percentage-of-max profit, capital loss caps, closing-basis level exits) transfer better.

**India-only**
- MIS/NRML products and the ~3:15 broker auto square-off [GsrNVbSwH04, GQEbyZhG-ME].
- 0.5 "market protection" orders.
- The margin reason for app-side targets [6lVvi-ULRVE].
- Thursday weekly-expiry timing [ZJyMZJekVBk]. The notes themselves flag that the Nifty weekly structure has since changed [NXE7KFxmH7I].
- Interplay specific to Nifty/Bank Nifty [ujTuECvyPzc].

---

## 5. Gaps and doubts

- **Stop size is often unstated.** He refers viewers to other videos for it [ybZYfvQzy7E, M18fQBnjMLA, _dQVN0WKeCE]. Where stated, widths range from 30% to 100% and from 40 to 100 points, with no single rule.
- **The only systematic evidence is one in-sample, ~28-month backtest** with uncertain caption figures [NXE7KFxmH7I]. Everything else is single-day P&L narration, often hindsight that cuts both ways (booking early vs holding).
- **Direct contradictions**
  - Low premium: widen the stop vs use no stop.
  - 30% vs 75% stops.
  - Stop-limit vs stop-market.
  - Never carry intraday positions vs converting leftovers to NRML.
  - Surviving leg: close vs hold vs stop-to-cost.
  - Band exits praised [7LlVnFIIEB4] vs regretted [XmP7nK_TMdo].
- **No formal definition** of a "decisive close," of "uncomfortable," or of when a position is "too messy." The judgment-based exits cannot be coded.
- **Rupee thresholds are not normalised** to capital in most videos. Only a few give percentages (1–4% of capital).
- **Barely covered**
  - Long-option exits: only a trailing example and a Bitcoin anecdote.
  - Exits driven by IV or Greeks: none, beyond remarks about IV spikes.
  - Time stops for positional trades: the pair trade explicitly has none [gFcyYYtgnOE].
- **Captions unclear or unrecoverable** in: cmhJCosywwM, QdIk7kAkHHc, U5mFJXhLKK4, 3PZu-YM162o, Q_BhDmUE22M, YBEEfvWpUG8, c4yDnTlhYSM, K2Z3ZsEXXTg, sk4_m8Yfzu0, 5vAHDwZkoHc, QEj_68mxDHI, GR_KV8MlHZI. The weekly return figure in jNqYVp_RXgg is also uncertain.
- **Some notes are off-topic or not his own rule**: a staged equity sale in 1989 [7PqDLtG2KYM], a track-record claim [VDvCfzInayY], and a host/guest stream [dAx2mchFMSs].
- **Evolution over time is only suggestive.** Older videos (5–6 years) centre on per-leg intraday stops and clock exits. Videos from 2–4 years ago lean toward capital-percentage loss caps, percentage-of-max profit taking, and defined-risk structures without stops. Publication ages are approximate, so the order of changes cannot be pinned down.
