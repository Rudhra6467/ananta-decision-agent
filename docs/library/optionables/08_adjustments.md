<!-- Trading Knowledge Library · Optionables (Optionables, India). Built 2026-10-16 from 434 public videos with captions (of 459 on the channel; members-only videos were not used): one structured note per video (Claude Sonnet 5.5) -> this chapter (Claude Opus 5.5), src/research/library.py. Paraphrased; the transcripts stay on the laptop. Evidence class: external teaching = hypotheses to test, never Ananta rules; nothing in the agent reads docs/library/. -->

# Adjustments

## 1. What he teaches and where it fits

Optionables is mainly a seller of index option premium. He trades short straddles, strangles, iron flies and condors, ratio spreads and calendars on Bank Nifty and Nifty weekly and monthly expiries, both intraday and positional. Adjustments sit at the centre of his method.

- **His core claim:** the money in short straddles and iron flies comes from the adjustments, not from the entry. He backs this with two backtests he cites:
  - An unadjusted positional ATM straddle lost about 1.33 lakh over roughly four years [VnlxZ2uP47M].
  - An unadjusted iron fly made about 3,000 rupees over three years [5_i637lBoPU].
- **The purpose of adjusting:** to cut the size of the average loss, not to make more profit. He accepts a slightly lower average win and win rate in exchange [8W58_AoCKrw, VnlxZ2uP47M, ZJyMZJekVBk, 09Bt6pDtUpw].
- **His toolkit:**
  - shifting (rolling) legs;
  - converting strangles to straddles, or condors to iron flies;
  - "counter" trades after a stop is hit;
  - complementary credit trades and averaging;
  - moving the surviving leg's stop to cost;
  - splitting ratio spreads into simpler parts.
- **When not to adjust:** an equally insistent strand of his teaching covers when to leave a position alone and when to book the loss and exit.
- **How the teaching evolved:**
  - The oldest videos (about 5–6 years ago) centre on intraday premium-balancing shifts and counter trades.
  - Later videos (about 3–4 years ago) lean toward pre-set price levels, candle-close triggers, open-interest (OI) confirmation, one-adjustment limits and decomposing ratio spreads.

Everything below is his claim or method, a hypothesis to test, not established fact.

## 2. The ideas

### 2.1 Why adjust: expectancy arithmetic

**What it is.** Adjusting is meant to shrink losing trades more than it shrinks winning trades. He illustrates this with hypothetical numbers, not data:

| Video | Before adjusting | After adjusting | Net result per 100 trades |
|---|---|---|---|
| [VnlxZ2uP47M] | 50% win rate, 5,000 average win, 5,000 average loss (zero edge) | 4,500 win, 3,000 loss | about +75,000 |
| [ZJyMZJekVBk] | average loss 4,900 | average loss 3,500 | about 5k becomes about 150k |
| [09Bt6pDtUpw] | 70% win rate, 5k win, 5k loss | 68% win rate, 4.5k win, 2.5k loss | 2 lakh becomes about 2.26 lakh |
| [8W58_AoCKrw] | — | capping each loss at 7.5k instead of 21,215 | turns positive, about +96k |

**Evidence he offers:**
- **Small backtest** [ZJyMZJekVBk]: 19 weekly Bank Nifty iron condors, one lot.
  - Unadjusted total about 11,903; adjusted about 18,901.
  - Wins and losses were 11 and 8 either way.
  - Average loss fell from about 2,530 to about 1,700.
  - He admits one V-shaped week where adjusting hurt.
- **Single-day comparisons:**
  - Adjusted versus unadjusted [UEOPUfhENcE, GQEbyZhG-ME, -uIGVxZWSHU, alxZlbVHVeo, QED0exJOqYc, 09Bt6pDtUpw, qyY60yFUp04, LK5yGOZMcj0, L3PBLOfzI6w, GJ-1jOUSekk].
  - These are hand-picked days. Several are hindsight estimates of what the unadjusted result would have been.

**His own caveat.** Adjustments give up profit on clean one-way trending days and protect on V-shaped days. His example pair of days [UEOPUfhENcE]:
- Trend day: about +80k adjusted versus about +3 lakh unadjusted.
- V-shaped day: about +70k adjusted versus about −3.5 lakh unadjusted.

**Without stops or adjustments**, he says any option strategy is roughly a 50/50 game [3MMjcR_ortI].

**Taxonomy.** He names four families: shifting, averaging, counter/complementary trades, and martingale [VnlxZ2uP47M]. Later he says only shifting avoids raising risk exponentially; averaging and counter trades raise risk accordingly [0tWQskBo6Pc].

### 2.2 When to adjust: triggers

He teaches the trigger far more often than the adjustment itself. The common thread: decide the level in advance, then ignore mark-to-market swings until it breaks [o7lr4TUP3Yg].

**Price-level triggers, confirmed by a close:**
- Hourly close below a prior support, about 40,250 on Bank Nifty, for a bullish put ratio. Any timeframe works if chosen in advance [o7lr4TUP3Yg].
- 5-minute close below marked support; he wants a close, not a wick [oQXCIfaJ1fs].
- Daily close below 41,700 to convert a naked short put into a straddle [XA-oogDFs2s].
- Close below 36,400 or above 37,000 for a strangle [RtecFQegmSI].
- Decisive close above 42,000 for a call ratio [urrT8zpnGus].
- "Close well below" 34,700 for short puts [1ItbBTjFgVQ].
- For the next session: no change until Bank Nifty breaks 35,700 or Nifty 16,400 [EL1Baky8Uk8].
- Upside line near 36,300 on a carried position [kaPyJdhVI9c].
- Bitcoin straddle at 19,500: act only beyond the break-evens or about 21,000 [VmiJLxaYPUQ, MeKx6Qh50vs].

**Break-even triggers:**
- Do nothing while the index stays inside the break-even zone. One example: about 38,500–40,500 with roughly two weeks left [VV3vue5PaQo].
- A large intraday move inside the break-evens is ignored [eihlpgiPJKA].
- Act when the index reaches a break-even [8W58_AoCKrw, 2jwiR_sR8W4, FBNJsrqlPiQ].

**Distance triggers:**
- About 300 points from the strike, when the premium implied a roughly 900-point range, i.e. about one third of the implied move [pZPCRg5w9gw].
- About 100 points from the start on Bank Nifty intraday; a 50-point move is too small to act on [WAXCM9CDx8g].
- About 50 points on Nifty or the "400 level" on Bank Nifty, held for some time [IMjqrkYosgY].

**Hedge-strike trigger (a deliberate contrast to the break-even trigger)** [ZJyMZJekVBk]:
- On a weekly 500/800 iron condor, he waits until the index has moved 800 points and touched a hedge strike.
- He explicitly does not act at the break-even, to give the trade room to revert.

**Premium-imbalance triggers** (no stop hit, but the legs have drifted apart). Each case below shows the leg premiums and, where it can be computed, the ratio of the cheaper leg to the more expensive one.

| Video | Adjust | Do not adjust |
|---|---|---|
| [BFZXz79936Y] | 260 vs 440 (≈0.59) | 300 vs 340 |
| [LK5yGOZMcj0] | 273 vs 139, a ~140-point gap (≈0.51) | 224 vs 153, an ~80-point gap (≈0.68); also 50 vs 39 and 38 vs 55 |
| [09Bt6pDtUpw] | 300 vs 520 (≈0.58) | 350 vs 480 (≈0.73); 320 vs 490 |
| [wcTPYuhzvAU] (both legs sold at 100) | 135 vs 68 | 120 vs 82 |
| [uoFMqwhG5-4] | 48 vs 78 | 55 vs 75 |
| [yvSFv0dQQVI] | imbalance of about 20% of premium is significant | about 10% is fine; 20–30% tolerable in larger books |
| [d6ZOFGDVw2Y] | one leg at about 450 of about 650 combined, i.e. ~70% | — |
| [V-R9YyFioe8] (test note) | cheap leg at roughly 60% of the expensive leg or less | — |

- **His stated test:** would a small bounce bring the two premiums back together? If yes, do nothing [BFZXz79936Y, wcTPYuhzvAU, yvSFv0dQQVI, LK5yGOZMcj0].
- **Rough cross-video pattern:** adjust when the ratio is about 0.6 or lower; leave it at about 0.7 or higher. This is an inference from his examples, not a rule he states.

**OI and chart confirmation:**
- Do not adjust just because spot is past the break-even if strong OI and a chart support or resistance sit nearby [5_i637lBoPU, VnlxZ2uP47M].
- Adjust only after OI or charts confirm the trend has changed [4bTRImkOyvY, eihlpgiPJKA].
- He skipped one day's adjustment because OI did not support it [it9ef0_jnVY].
- Adjust when OI at protecting strikes weakens; the details are unrecoverable from the captions [nvSBmk5ffzY].
- After a gap, adjustments are decided after the open together with the OI build-up [2rTZM1IF6DE].

**Contradiction.** Some videos trigger at the break-even [8W58_AoCKrw, ~5 years ago]. Another refuses to act at the break-even and waits for the hedge strike [ZJyMZJekVBk, ~4 years ago]. Others prefer a discretionary OI and chart read over any mechanical trigger [VnlxZ2uP47M, 09Bt6pDtUpw]. He also says plainly that discretionary adjusting has no fixed rulebook [kyQf5lGc_6s, 09Bt6pDtUpw].

### 2.3 Shifting (rolling legs)

**What it is.** Buy back the cheap, decayed (untested) leg and re-sell the same option type nearer to spot. This moves the profit range toward the market [VnlxZ2uP47M, BFZXz79936Y, 09Bt6pDtUpw, GJ-1jOUSekk].
- **Execution:** use a basket order that closes the old strike and opens the new one together [BFZXz79936Y].

**Variants:**

- **Midpoint shift** [8W58_AoCKrw]:
  1. Trigger: price touches a break-even.
  2. Re-sell the untested leg at the average of the two short strikes. Example: shorts at 15,000P/16,500C with the market at 16,500, so the put moves to 15,750. No extra margin is needed.
  3. Next, a 500-point reference from that point. A 500-point reversal means exit everything at a profit.
  4. A further 500-point continuation means moving the other leg too, making a straddle at the tested strike while keeping the hedges.
- **Step shifts with the trend:**
  - One strike at a time: 100 points on Bank Nifty, 50 on Nifty [nXjmslNVkyo, -uIGVxZWSHU, GQEbyZhG-ME, IMjqrkYosgY, LK5yGOZMcj0, pdGXhkLJPj0, HcdusL_8W5U, UEOPUfhENcE, JdR7-suVxCI, P21vgTId9P8, T1cJv2Y62FU, Ga6QSMLRT4o, u_UvOZQpRlk, jztFfYokRqI, ujTuECvyPzc].
  - On one expiry day he shifted about 11 times [-uIGVxZWSHU]. That example keeps only two open legs and books the loss on each shift.
- **Shift both legs** with an upside breakout: put closer and call farther, e.g. 39,200→39,300 and 39,600→39,800 [pZPCRg5w9gw, T1cJv2Y62FU, 5vAHDwZkoHc, 9a3TdAs7xUw].
- **Shift to keep premium constant** [M18fQBnjMLA]. A related idea: shift the higher-premium leg farther out to rebalance, e.g. 36,700→36,800 calls at about 290 vs 200 [peakDi79pVs].
- **OI-guided rolls:**
  - Roll a call down to the strike with heavy call writing [4hAvzzjA2xw, km4uw-zxRZM, IeeFqzGWEv0, tJEhYTG7_k4].
  - Roll a far OTM put up when it has decayed to almost nothing (about 15 rupees, the market up about 1,200 points). The new strike is where fresh put writing builds, at about 98 rupees, and only after the rise is confirmed [Og7SQjotANg].
  - Roll puts up after a resistance break or a gap-up [ufH0zRUyuIw, JqEQIQyJ-FU, it9ef0_jnVY].
- **Re-centre the whole straddle** at the new ATM strike, or at the strike where OI shows others building straddles [HcdusL_8W5U, -wVTqlE51C8, MusX9A1juic, d6ZOFGDVw2Y, nUnxmPBczaQ, MeKx6Qh50vs, tTR4X1FsFgE].
  - Shifting can also mean rolling to the next expiry [MeKx6Qh50vs].
  - Long-dated positions are easier to shift because the break-even range is wider [tTR4X1FsFgE].

**Sizing the new leg: do not rebalance exactly.** Leave the side that moved against you somewhat heavier. Examples:
- cut a 200-point imbalance to about 100–150 [yvSFv0dQQVI];
- move a sold leg toward about 90 when it stands at 120 against 60 [BFZXz79936Y];
- re-sell at about 85 against 135, not at 135 [wcTPYuhzvAU];
- leave the new leg a bit cheaper than the expensive one [09Bt6pDtUpw].

His reasoning: exact balance leaves you exposed if the market snaps back.

**Limits on shifting:**
- About two shifts, then stop [wdUlevVfZL4].
- After seven or eight adjustments it stops making sense, and a small reversal re-creates the imbalance [nXjmslNVkyo].
- One or two adjustments, then book the loss and come back the next day [IMjqrkYosgY].
- Once a leg is near its stop (339 against a 360 stop), stop shifting it and wait for the stop [LK5yGOZMcj0].

**Where he says shifting did not help:**
- The strangle would have done better untouched [5vAHDwZkoHc].
- Shifting a straddle during a headline spike locked in the loss before a bounce [hPUdSoT2c7g].
- Repeatedly closing and re-creating straddles turned a potential +10 lakh flat day into −1.45 lakh [aDbp7e_Qvxo].
- An unnecessary shift into a bounce, plus an execution glitch, cost about 12k [WAXCM9CDx8g].
- A Nifty shift made only for convenience while tracking two indices [LK5yGOZMcj0].
- A Nifty adjustment driven by a Bank Nifty stop [jztFfYokRqI].

**Labelling caution.** Some notes call the leg being moved "threatened", but the leg moved is in fact the untested one (e.g. calls moved down in a falling market) [qyY60yFUp04, NTavZ18KPh8]. The consistent mechanic is moving the cheap leg toward spot.

### 2.4 Converting structures

**Strangle to straddle at the tested strike.** When price nears or reaches a short strike, sell the opposite type at that strike.

- **Band rule** [h5XNvyTMSsk]:
  - A close between 33,800 and 34,100 means a straddle at 34,000.
  - A close between 34,600 and 34,900 means a straddle at 34,700.
  - Checked at the next day's close, with expiry two days later.
  - Otherwise leave it alone.
- **Strike triggers:**
  - Breaks of 35,000 or 35,800 [d-_3zxoHyEg].
  - Breaks of 38,000 or 39,500 [XLBtvv6Jq18].
  - Break of 33,700 [OBJL069UfRQ].
  - Generic statements of the same idea [91-eSFLtkhg, tKlpB5RfdFA, FzWERdEYPmI, GsrNVbSwH04, u_UvOZQpRlk, Ga6QSMLRT4o].
- **Pre-set exit after converting** [aUFKZY0o3-E]:
  - Triggers about 39,800 or 41,500.
  - Convert once.
  - If price then breaks the straddle's break-even, exit with a small loss.
  - No second adjustment.
- **Conditional conversion** [EL1Baky8Uk8]: convert to straddles only if the market opens weak, gaps up and fades, or fails to hold higher levels. Leave the strangle alone on strength.
- **Inconsistency:** in one video the target straddle strike is stated as both 41,000 and 41,500 [DLJ0AmH6hS0].
- **Sequencing on a gap-down expiry:** short calls first, then add puts once support forms [16t3E1t2tgk].

**Other conversions:**
- **Naked put to straddle:** on a daily close below 41,700 [XA-oogDFs2s].
- **Iron condor to iron fly** [ZJyMZJekVBk]:
  1. When the hedge strike is hit, close the profitable side's short and its hedge, both near zero.
  2. Re-sell an ATM option at the opposite short's strike, with a hedge 300 points away.
  3. Then make no further adjustments until expiry.
  4. In the example week, maximum loss fell from about 2,060 to about 600.
- **Hedged short call spread on a bull put spread** [Y_0mKcvRGzo]: if the market fails to hold 36,000, add 36,500/37,000 calls with equal lots. Claimed risk-reward goes from about 1:10 to about 1:3.

### 2.5 After a stop-loss hits one leg

**Stop to cost.** Move the surviving leg's stop to its entry price, so the day costs at most one stop.
- Example: both legs sold at 400 with 560 stops. After one stops out, the other's stop goes to 400 [8No43FVgZfU].
- Taught repeatedly and clearly [xj-1uHZotgY, bLFCt52D89o, QVeSJBPD_i4, Hma2mI-kOjY, 3MMjcR_ortI, m3izeXsRdW8].

**Variants and contradictions:**
- **Trail to a small locked gain** [oIU_xUVFnwk]: the put sold at 400 had its stop moved from 500 to 280, locking about +20 points net of the stopped call.
- **Contradiction, keep the original stop** [NXE7KFxmH7I]:
  - Keep the other leg with its own original stop until 2:55 pm.
  - His argument: most stopped days still finish green.
  - This conflicts with the stop-to-cost rule.
- **Fixed P&L exits on the survivor** [UIf_6_Bg66I]: exit at about +15–20k or −50k.
- **Hold the survivor naked when the trend favours it:**
  - Call decayed from about 120 to about 45 [JPqXyHXfGfg].
  - Hold the puts naked until Nifty returns below 16,000 [jztFfYokRqI].
  - Keep a naked call because OI suggested a cap [4Zd60oo6vOM].
- **His warning:** a survivor is only safe if price stays flat or moves away. A reversal builds the loss in minutes [RiTtKlJDrdI, 3uZnthbvz3A].

**Counter trade.** A fresh short placed after a stop. The definitions conflict between videos.

- **Same side as the stopped leg, farther OTM:**
  - Price it at about 50–60% of the surviving leg's premium: about 120–150 against 370 [09Bt6pDtUpw].
  - Or about 300 points beyond the stopped strike at about 20–22 rupees [GQEbyZhG-ME].
  - Or at the level where the two premiums are expected to meet; with 100 vs 200, about 140, which also sets the counter's stop [BFZXz79936Y].
  - Or a cheaper strike chosen after waiting [peakDi79pVs, M18fQBnjMLA, nXjmslNVkyo, IMjqrkYosgY, pdGXhkLJPj0, UEOPUfhENcE].
  - [UEOPUfhENcE] uses about half of the surviving leg's premium.
  - Worked numbers in [09Bt6pDtUpw], which he says are illustrative and not backtested:

    | Path after the counter trade | Net result |
    |---|---|
    | Trend continues | +50 |
    | Market consolidates | +20 |
    | Market bounces back | −30 (vs −110 without the counter) |

- **Opposite side, far OTM:** after a call stop, sell a 15,300 put at about 17–20 [qyY60yFUp04]. [GJ-1jOUSekk] says "about half the stopped leg's premium" on the opposite side.
- **Timing:**
  - Wait a couple of minutes to see whether the move continues [LK5yGOZMcj0].
  - Wait for a bounce before re-selling [M18fQBnjMLA].
  - Do it only if you expect consolidation or a reversal [09Bt6pDtUpw].
  - Counter legs are then shifted with the market [qyY60yFUp04, -uIGVxZWSHU, pdGXhkLJPj0].
- **Rebalance net exposure:** after a stop, add shorts on the other side to rebalance net delta against a carried bias [lkOC0gpSmQQ]. Use unequal lots and strikes to roughly balance premium while keeping a tilt with the trend [wdUlevVfZL4].

**Re-entry with fresh straddles after stops:**
- Re-sell a fresh ATM straddle at the new spot [_dQVN0WKeCE, 4Zd60oo6vOM, m3izeXsRdW8].
- Shifted-strike re-entry, 17,150 instead of the ATM 17,050 [L3PBLOfzI6w].
- Deliberately at the old strike to stack calls in a slide [alxZlbVHVeo].
- He tags [m3izeXsRdW8] with the opposite hypothesis: repeated re-entry may lose more on whipsaw days.

### 2.6 Credit-collection repair and averaging (higher-risk families)

**Loss converted into points.** Divide the rupee loss by the total quantity to get the premium points that must be collected. Examples:

| Video | Loss | Quantity | Points needed |
|---|---|---|---|
| [3Qt_5nu_0hY] | 2.4 lakh | 3,000 | ≈80 |
| [dPuJiR0oxRs] | 4.5 lakh | 3,000 | ≈150 |
| [9lj7Ta-vsmc] | 1.75 lakh | ≈3,000 | ≈60 |
| [4bTRImkOyvY] | 37k | 500 | ≈74 |
| [-IDDp5bvrVQ] | — | — | ≈130 needed, ≈170 collected |

Each added credit trade is judged by whether it closes that gap.

**Staged selling on the trend-favoured side:**
- About 170 points collected against 80 needed, including a double-size 39,000 put [3Qt_5nu_0hY].
- Staged puts in 3,000 quantity until 165 points were in, waiting for put writing at 37,500 [dPuJiR0oxRs].
- Puts at 36,000, then 36,500, then 37,000 [GWbpgCAAMkM]; loss from about 2.8 to 1.7 lakh.
- Extra puts after a gap-up [KqKOdPHFG-I].
- A put on the non-threatened side cut the upside loss from 1.75 lakh to about 42k [9lj7Ta-vsmc].
- Roll calls down in steps, not one big move [-IDDp5bvrVQ].
- [GWbpgCAAMkM] adds an order: buy the upside hedge first, then decide on extra sales.

**Averaging:**
- Add a second straddle at the new level [VV3vue5PaQo, uoFMqwhG5-4, MeKx6Qh50vs, oO-T8_3l_5g].
- Double the straddle on a close above the range high [cJpUydwXnIw].
- Roll a breached strangle lower at double size (10 to 20 lots) so the new credit covers the old loss [4bTRImkOyvY].
- Scale up late-day straddles in consolidation:
  - to about 12,000 quantity [NTavZ18KPh8];
  - from about 1,750 to 5,500–6,000 [peakDi79pVs];
  - from 4,050 to 8,100 [HcdusL_8W5U];
  - from 2,000 to about 4,000 [3uZnthbvz3A].

**Counter on a profitable naked short** (protecting gains rather than repairing):
- Sell a call at about half of the put's premium (17,400 call at about 46 against a put at about 76) after about 70k of mark-to-market profit [N8jDRk63lK0].
- Add far OTM calls when only puts remain after a rally [7RI6oed3Eak].

**Contradictions:**
- He says not to raise size sharply when adjusting [MeKx6Qh50vs].
- He says averaging and counters raise risk [0tWQskBo6Pc].
- Yet several repairs double the size.
- Selling more options on the adverse side before a reversal is his most common self-identified error:
  - extra puts after a gap-up, then extra calls, then a loss of about 3.5 lakh [pxw7tkirF4Q];
  - shorts added after a gap held for only about 10 minutes [oAJ8k8TzB7E];
  - calls sold at the day's low [3VTymF8_eww];
  - a put added late, then the sell-off continued [XLBtvv6Jq18].
- Discretionary overrides of the system:
  - credited with recoveries [Fe766Um-ayQ, GxKIIKl4eZA, vmjxCxSdIn0, RiTtKlJDrdI];
  - and blamed for losses [G2Jm-SaT6M8].

### 2.7 Dropping or tilting a leg directionally

- **Exit the threatened leg on a swing break:**
  - On a break above swing resistance (35,050 on Bank Nifty), exit the call leg and keep the put naked. He accepts a possible 20–30-point loss and will re-add the calls if the level is reclaimed [EL1Baky8Uk8].
  - Exit the put leg on a 5-minute close below support [oQXCIfaJ1fs].
- **Remove the hedge** of a bull put spread after a break of the opening high, and add size (5,000 to 7,000) [35_p7TIkaTQ].
- **Roll a call down to ATM at double size** after a failed high breaks the day's open [OSNCbyGvQm4].
- **Whipsaw costs he reports:**
  - Flipping short puts to short calls after a 400-point fall cost him when price reversed within 5–10 minutes [iPFJBuJqM8Q].
  - A flip-flop cost about 60–70k [X5jF4csZwh8].
  - Exiting on a support break without confirmation [XmP7nK_TMdo].
  - A spike exit and re-entry cost about 1 lakh, which he still judged reasonable [RtecFQegmSI].

### 2.8 Spreads, ratios and calendars

**Decompose first** [NSeHRFG7XVA, o7lr4TUP3Yg, lkOC0gpSmQQ]:
- A put ratio is a bear put spread plus one naked short put.
- A call ratio is a bull call spread plus naked short calls.
- Only the naked part is managed. The spread is never touched.
- Re-decompose after every change and touch only the leg that hurts [o7lr4TUP3Yg].

**Long side (bullish put ratio)** [o7lr4TUP3Yg]:
1. Trigger: an hourly close below support (about 40,250).
2. Sell a call at the next resistance (about 41,700), turning the naked put into a strangle.
3. Manage that strangle normally.
4. If the market reverses, manage only the new call.

Related:
- Short a 31,000 call below 30,000 [ilbYdeALr0M].
- Sell 34,000 calls near 33,500 to bank profit [tY0noMv3lp0].
- Sell higher calls, or convert to a ratio, if 34,700 closes well below [1ItbBTjFgVQ].
- **Alternative: do nothing** [lkOC0gpSmQQ]. He accepts the one loss and relies on a claimed ~85% win rate (example: loss about 8,000 vs gain about 6,000).

**Short side (bearish call ratio):**
- On an upside break, turn the naked calls into an iron condor or iron fly [NSeHRFG7XVA].
- Or, after a decisive close above 42,000, into a 43,000 straddle or a 42,000/43,000 strangle [urrT8zpnGus].
- A call ratio's break-evens were reshaped with a short put plus about 40 lots of a deep ITM 36,500 call [GWbpgCAAMkM].

**Calendars and multi-leg books.** He reshapes them by:
- exiting long puts and doubling short puts to move break-evens [tbHLBk84Btc];
- rolling puts nearer and removing a decaying long put [JqEQIQyJ-FU];
- removing decay-heavy long legs to lock in about 1.76 lakh above 38,000 [9lj7Ta-vsmc];
- closing a hedge and selling about 200 lots of the 38,000 puts at OI support [s7M-kuYOROU].

He judges each change on a payoff graph with combined break-evens, plotted only to the nearest expiry [tbHLBk84Btc, GWbpgCAAMkM, jp2M9NfVAig].

**Other spread cases:**
- A long option cannot really be adjusted once it moves against you [QgqjwKIZjlM].
- Bull call spread adjustment rules are unrecoverable from the captions [RN0TY5FeGHE].

### 2.9 When not to adjust, and when to exit instead

**Regime filters:**
- **Uncertain markets:** do not adjust when the market swings, e.g. −900 points one day and +700 the next. Book a small loss instead [0tWQskBo6Pc].
- **Clear conditions only:** adjust only when the trend, sentiment and news are clear [0tWQskBo6Pc].
- **High volatility:** in choppy high-volatility markets, move to intraday trading [xf1DJgNy3mQ].
- **VIX level:**
  - Low VIX, expected weekly range about 2%: rarely needs adjusting.
  - High VIX, about 4.5%: forces adjustments that often prove unnecessary [X8sW2WNaKAs].
- **Speed of the move:** gradual trends are repairable; sudden moves leave no time [LK5yGOZMcj0]. If the move had been gradual he would have adjusted [Pt5pbpK1eoI].

**Comfort and worst case:**
- Adjust only if the adjusted worst case is a minor injury, not a wipe-out [0tWQskBo6Pc].
- If uncomfortable, exit [0tWQskBo6Pc].
- Take naked positions only if you can adjust them [s2KhVugNPfI].
- There is no need to force a trade back to profit; exit and start fresh [vRGhcoCUbBE, JqEQIQyJ-FU].
- Simplify a messy position by closing it all and rebuilding about four legs [ZDUmKEZXWMw, _dQVN0WKeCE, peakDi79pVs].

**Hard stops on adjusting:**
- Stop adjusting and close everything once the move is strong; no number given [it9ef0_jnVY].
- No adjustment near the risk limit [Pt5pbpK1eoI].
- Cut everything at about 4.5 lakh of mark-to-market loss [BGRZRDCcNSI].
- Close if the market opens near 16,150 with no support [km4uw-zxRZM].
- Exit everything at about 1.4 lakh after a failed hold [YtLDcJgJzcQ].
- Full resets: square off and restart fresh, e.g. from 1 February [xwWE0ZPmP3s, vmjxCxSdIn0].

**Patience:**
- With a known, acceptable worst case, do not rush. Be extra careful on expiry day [dPuJiR0oxRs].
- Wait one or two sessions for a bounce before adjusting aggressively [xDRqGkiOnN8].
- A notional loss above the break-even is not a reason to panic [-wVTqlE51C8].
- An adjustment can still be overwhelmed: a 1,300-point bounce beat it, where one of 500–600 points would not have [tn3IDCnC6dc].

**Self-diagnosed errors:**
- Adjusting too early; the market often reverses right after [oQXCIfaJ1fs].
- Oversized quantity made him adjust trades that did not need it [qhHfMHyouqs].
- Deciding not to adjust also lost on one day [hLfnVGcoX_w].
- Leaving a position alone when support held earned about 2 lakh [2SuMQE03v2w].
- Exiting a very lopsided straddle (legs about 17 and 1) was in hindsight too early [Bqh1AevjUzg].
- Rapid 300-point V-swings make the adjust-or-not decision hard; he exited and re-entered [mDW8Ih4CuuY].

## 3. How a program would test it

**Data needed:**
- Intraday (1-minute) option prices for Bank Nifty and Nifty weekly and monthly options: bid/ask or at least last price, by strike.
- Index candles.
- India VIX.
- NSE strike-wise OI snapshots.
- Realistic costs: brokerage, STT, slippage at the bid/ask.
- Results should report the full distribution (mean, tail, maximum drawdown), not only averages, since his claim is about loss size.

1. **One-adjustment iron condor** [ZJyMZJekVBk].
   - Setup: weekly Bank Nifty iron condor, short strikes ±500 from entry, wings ±800.
   - Rule: when spot first touches a wing strike, close the untested short and its wing, then sell ATM at the opposite short strike with a wing 300 points away. Hold to expiry.
   - Compare against unadjusted, over several years (not 19 weeks).
   - Measure: total P&L, average loss, win rate, worst week.
   - Run a variant that triggers at the break-even [8W58_AoCKrw] to settle that contradiction.
2. **Surviving-leg stop after the first stop** (intraday ATM straddle, one leg stopped at +30–40% of premium).
   - Compare: (a) other leg's stop moved to cost; (b) original stop held to 14:55 [NXE7KFxmH7I]; (c) trailed to lock net ≈0 [oIU_xUVFnwk].
3. **Premium-imbalance shift.** With no stop hit, shift the cheap leg one strike toward spot when the cheap/expensive premium ratio is at or below a threshold.
   - Thresholds: grid of 0.5, 0.6, 0.7, plus "any imbalance" and "never".
   - Re-entry: either an exactly balanced new leg or a partial one (closing half the gap).
   - Caps: shifts per day of 1, 2 or unlimited.
4. **Strangle to straddle on close** [h5XNvyTMSsk, aUFKZY0o3-E].
   - Rule: if the daily close lands within 100–200 points of a short strike, convert to a straddle at that strike. Optional exit at the new straddle break-even. Maximum one conversion.
   - Compare against a static strangle held to expiry.
5. **Counter trade after a stop.**
   - Arms: (a) sell same-side OTM at 50–60% of the survivor's premium [09Bt6pDtUpw]; (b) sell opposite-side far OTM [qyY60yFUp04]; (c) none.
   - Each with and without a 2–5 minute wait [LK5yGOZMcj0].
   - Split results into trend days and V days, classified ex post by the close relative to the extreme.
6. **Credit-collection repair** [3Qt_5nu_0hY, dPuJiR0oxRs, GWbpgCAAMkM].
   - Rule: after a break-even breach, sell OTM options on the trend side in staged steps until cumulative credit is at least the open loss divided by quantity.
   - Measure especially the conditional loss when the index reverses afterward. This is his reported failure mode [pxw7tkirF4Q].
7. **Regime filter** [0tWQskBo6Pc, X8sW2WNaKAs, xf1DJgNy3mQ].
   - Apply rules 3–6 only when VIX is below about 14, and with no consecutive opposite daily moves above about 2%.
   - Otherwise exit at the trigger.
   - Compare against applying them in all regimes.
8. **Put-ratio support-break adjustment** [o7lr4TUP3Yg, lkOC0gpSmQQ].
   - Rule: on an hourly close below the nearest prior swing low, sell a call at the nearest swing high.
   - Compare against no adjustment, which he suggests may be fine given an ~85% win rate.

## 4. Transfer to TSX and US markets

**Usable as is (mechanics are market-neutral):**
- Splitting ratio spreads into a spread plus a naked part.
- Stop to cost on the survivor.
- The premium-ratio imbalance test and partial rebalancing.
- Strangle-to-straddle conversion.
- Iron condor to iron fly.
- Converting loss into points of credit needed (loss divided by contract multiplier and quantity).
- Pre-set, close-confirmed triggers.
- The "exit instead of adjust" principles.

All of these can be run on SPX/XSP/SPY/QQQ weeklies and 0DTE.

**Needs adapting:**
- **Point thresholds must become percentages or sigma.** Bank Nifty 100 points was roughly 0.25–0.3% at his levels. The 500/800-point condor maps to about 1.3%/2% of the index. The 300-of-900 trigger maps to one third of the implied move.
- **Strike spacing and liquidity:**
  - SPX has 5-point strikes and deep 0DTE liquidity, so his intraday shifting is feasible there.
  - TSX options (e.g. XIU, the S&P/TSX 60 index options SXO) have wide spreads, thin weeklies and poor intraday liquidity. Frequent shifting would likely be eaten by costs.
- **Costs:** his examples show up to about 11 shifts a day. US per-contract fees and spreads need explicit modelling.
- **Assignment:** SPY and equity options are American style. His deep ITM shifted legs and ITM strangles [IeeFqzGWEv0, JdR7-suVxCI] carry early-assignment risk; SPX/XSP (European, cash-settled) avoid it.
- **Margin:** his sizing of naked repairs relies on Indian margin. US Reg-T versus portfolio margin changes what doubling size costs.
- **OI-based rules:**
  - US OI is published once daily (OCC), so his intraday "fresh put writing at strike X" reads are not reproducible.
  - Volume or the end-of-day OI change is only a proxy.

**India-only or largely so:**
- Bank Nifty/Nifty weekly expiry dynamics as he traded them. Indian expiry rules have since changed; check current NSE schedules before replicating.
- India VIX thresholds.
- SGX Nifty gap cues.
- Budget-day timing.
- Lot and quantity conventions in lakh.
- NSE intraday OI snapshots.

## 5. Gaps and doubts

**Weak evidence:**
- Almost all of it is single-day anecdotes with hindsight "unadjusted" estimates [UEOPUfhENcE, GQEbyZhG-ME, -uIGVxZWSHU, QED0exJOqYc, alxZlbVHVeo, 09Bt6pDtUpw].
- The one adjusted-versus-unadjusted backtest is 19 trades in one regime, with no costs [ZJyMZJekVBk].
- The negative unadjusted backtests [VnlxZ2uP47M, 5_i637lBoPU] are stated, not shown in detail.

**Unresolved contradictions:**
- Trigger at the break-even [8W58_AoCKrw] versus wait for the hedge strike [ZJyMZJekVBk] versus a discretionary read [09Bt6pDtUpw, kyQf5lGc_6s].
- Stop to cost [8No43FVgZfU and others] versus hold the original stop to 2:55 [NXE7KFxmH7I].
- Counter trade on the same side as the stopped leg [09Bt6pDtUpw, GQEbyZhG-ME] versus the opposite side [qyY60yFUp04]. The definition is also deferred to another video [qyY60yFUp04, pdGXhkLJPj0].
- Avoid size increases [MeKx6Qh50vs, 0tWQskBo6Pc] versus repairs at double size [4bTRImkOyvY, 3Qt_5nu_0hY, OSNCbyGvQm4, HcdusL_8W5U].
- The cap on adjustments varies: 1 [aUFKZY0o3-E, ZJyMZJekVBk], about 2 [wdUlevVfZL4, IMjqrkYosgY], 7–8 [nXjmslNVkyo], about 11 shifts in one day [-uIGVxZWSHU].
- Inconsistent target strike in [DLJ0AmH6hS0].

**Undefined thresholds:**
- "Large" imbalance has no single number. The inferred ~0.6 ratio is the editor's synthesis.
- "Strong move", "decisive close" and "comfortable" are not quantified [it9ef0_jnVY, urrT8zpnGus, 0tWQskBo6Pc].

**Captions unrecoverable or adjustment not described:**
- f35t-KwNtWk, CfHEwRn-BZg, tvOPgvNOQ_A, XzUS02tUivU, K2Z3ZsEXXTg, Q_BhDmUE22M, d3ohL4Aorac, RN0TY5FeGHE, lev6pAAKvYE, jNqYVp_RXgg, U5mFJXhLKK4, AyC9r0_ZiN8, OGPVzN-tt3k, _sEwi7lQuNA, esyG-xHXwZ0, ke5FNmK9VXs.

**Not covered in these notes:**
- Greeks-based adjusting (delta or vega targets).
- Rolling out in time, beyond one passing mention [MeKx6Qh50vs].
- Assignment handling.
- Explicit cost accounting.
- Adjusting long-premium or debit positions; he says long options cannot really be adjusted [QgqjwKIZjlM].
- A systematic rule for when discretionary overrides are allowed. He reports them both helping [Fe766Um-ayQ, vmjxCxSdIn0] and hurting [G2Jm-SaT6M8, pxw7tkirF4Q].
