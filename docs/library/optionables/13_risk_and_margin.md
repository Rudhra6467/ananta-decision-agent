<!-- Trading Knowledge Library · Optionables (Optionables, India). Built 2026-10-16 from 434 public videos with captions (of 459 on the channel; members-only videos were not used): one structured note per video (Claude Sonnet 5.5) -> this chapter (Claude Opus 5.5), src/research/library.py. Paraphrased; the transcripts stay on the laptop. Evidence class: external teaching = hypotheses to test, never Ananta rules; nothing in the agent reads docs/library/. -->

# Risk and margin

## 1. What he teaches here and how it fits

Optionables' method is mostly short premium on Indian index options: intraday system straddles at fixed times, discretionary positional straddles, strangles, iron flies and ratio spreads, plus some futures, equities and crypto. He treats risk control as what makes that style survivable.

His core message is consistent across five to six years of videos. Losing trades are normal; what matters is the size of the loss. He fixes the loss before entry in three ways:

- a per-trade cap as a percent of capital;
- a daily cap that flattens everything;
- longer drawdown circuit breakers.

He sizes from the worst case rather than from available margin. For naked overnight shorts, the worst case is an overnight gap of a stated size.

His later videos (about 2–3 years ago) lean harder toward three things:

- hedged, defined-risk structures;
- distrust of stop orders in flash spikes;
- warnings against selling cheap far-OTM options.

The earlier videos lean on stop losses, leg stops, and naked positions kept small.

Margin is treated mostly as an Indian regulatory and operational topic: SEBI peak margin, pledging, the cash/collateral split, and hedges bought for margin benefit. Throughout, these are his claims and practices, not tested results.

## 2. The ideas

### 2.1 Per-trade risk cap as a percent of capital

**What it is.** Decide the worst-case loss before entry and size quantity so it fits a fixed share of capital. The order of operations is: set the loss cap, then set the stop distance, then derive quantity [RiTtKlJDrdI]. For example, a 1.5 lakh cap on 3,000 quantity gives a 50-point stop.

**Numbers given, by band:**

| Band | Videos |
|---|---|
| 1–2% of capital (most common) | NSeHRFG7XVA, xj-1uHZotgY, oYfLG7jLvPQ, nXjmslNVkyo, Hma2mI-kOjY, VDvCfzInayY, 3MMjcR_ortI, GsrNVbSwH04 |
| About 2% | wdUlevVfZL4 |
| 1–1.5%, never above 2% | LrBXT5C_YYY, QgqjwKIZjlM |
| About 1% per trade/day | uN9SRyTv_yY |
| About 1% per directional view | mW37Il_RHNg |
| 2–3% | VmiJLxaYPUQ, ujTuECvyPzc |
| 2–3% preferred, 5% hard ceiling | VnlxZ2uP47M |
| About 3% | wr82JkzZyys, 8No43FVgZfU, MeKx6Qh50vs |

Smaller caps appear in specific trades:

- 0.3% on a ~100-lot defined-risk spread [0xrgICpggJI];
- 0.5% on hedged bearish or hedged structures [AyC9r0_ZiN8, P21vgTId9P8];
- 1–2% worst case per trade, either on a 1,400-point gap or if all futures stops hit [urrT8zpnGus].

**Special cases.**
- **Event days.** Any overnight non-directional trade through a major event is capped at about 0.5% of capital, however confident he is [KBx0tqQMkNw, 9xAzvNa4s5U].
- **Option buying.** A different rule applies: risk 7–10% of capital per trade (15–20k on 2 lakh) so the account survives 10–15 straight losers, because win rate is low [0eEhp4WO66U]. Buyer risk should be read as the percent of premium that can be lost, not rupees per lot [l4jQUXK6UOc].

**Why.** He cites past years in which he lost 25–30% of capital [VmiJLxaYPUQ]. A 2% loss can be won back the same day; a 10–20% loss cannot [GsrNVbSwH04].

**Adjustment limit.** After two or three adjustments, exit rather than keep firefighting [o7lr4TUP3Yg]. Cut at about 2% instead of making a mess of repeated adjustments [wdUlevVfZL4].

**Clarity and frequency.** High, and very frequent: 20+ videos. The level drifts: early videos allow up to 3–5%; later event-day guidance is 0.5%.

### 2.2 Daily loss limit (kill switch)

**What it is.** A pre-set MTM loss for the whole book at which he squares off everything and stops for the day. Fixing it before the session matters because during a trade the mind keeps moving the exit [oQXCIfaJ1fs]. After being wrong on one side, ego drives overtrading [ZbtIFwwTWhQ, 3MMjcR_ortI].

**Percent versions:**

| Daily cap | Videos |
|---|---|
| 0.5–1% | ZbtIFwwTWhQ |
| Under 1% | IMjqrkYosgY, hPUdSoT2c7g |
| 1–1.5% | d6ZOFGDVw2Y, LrBXT5C_YYY |
| 1–2% | Pt5pbpK1eoI, YtLDcJgJzcQ |
| About 2% | jztFfYokRqI, 3MMjcR_ortI, F6sjGAcJXXc |
| Normally ~2%, applied at 1.5% that day | 6qive5Kb4Jk |
| 2–3% for beginners | lkOC0gpSmQQ |
| 3% (~7.5 lakh) | 3uZnthbvz3A |
| 2% (guest's example) | dAx2mchFMSs |

**Rupee versions** (they scale with his capital):

| Daily cap | Videos |
|---|---|
| 2 lakh | tn3IDCnC6dc, 2dJOkeen6RM, V-R9YyFioe8, IMjqrkYosgY, 5vAHDwZkoHc, 4Zd60oo6vOM, JPqXyHXfGfg |
| 1.5–2 lakh | pdGXhkLJPj0 |
| 2.5 lakh | oQXCIfaJ1fs |
| 3 lakh | ZDUmKEZXWMw |
| 4 lakh (about 10k per lot × 40 lots) | dzFMyd0FiXA, bLFCt52D89o |
| 4–5 lakh | NHkRRMWhx4U |
| 5–7 lakh | xj-1uHZotgY |
| 60–80k on a smaller intraday book | RFvomGYSt6k |
| 10k total for a small multi-trade budget-day system | 8No43FVgZfU |

**Staged budgets.** Several videos split the daily cap into a first stop and a reserved second attempt:

- 2 lakh day: first trade capped at 1–1.2 lakh, about 80k kept for a re-entry around 12–1 pm [tn3IDCnC6dc].
- 1.4 lakh first exit, then 1 lakh on a final trade, totalling 2.5 lakh [YtLDcJgJzcQ].
- Cut and re-enter at 1.5 lakh; stop for the day at 3 lakh [LK5yGOZMcj0].
- Reset at 5.5 lakh, soft cut at 6.5, hard stop at 7.5 [3uZnthbvz3A].
- A similar two-stage plan whose numbers are internally inconsistent [nXjmslNVkyo].

**Limitation he admits.** A fast spike can blow through a manual daily cap. He planned to cut at 4.5 lakh but ended about 7.5 lakh down, with 4 lakh of that in the last 15 minutes. He uses this as an argument for buying hedges in advance [LPGCiis_rlg].

**Clarity and frequency.** High; this is the most repeated rule in the set.

### 2.3 Drawdown circuit breakers beyond the day

- **Quarterly:** F&O drawdown limit of about 10% of the portfolio (about 50 lakh on 5 crore). If hit, become much more cautious. A bad month should be recoverable within about one month, not three or four [ow6NsXYp9G0].
- **Monthly:** after about a 3% drawdown (by around 21 December) he took only small trades until month-end [Au2cYvYojNM].
- **Recovery speed:** holding the options drawdown near 3% of capital (15 lakh) rather than 8% (30–40 lakh) means one good month recovers it rather than two or three [7yL3qGyijeM].
- **Strategy level:** keep maximum drawdown within 15–20% of capital, beyond which traders stop executing properly, and have an exit plan for the strategy [oYfLG7jLvPQ, NXE7KFxmH7I].
- **Losing streaks:** he expects streaks of 5–6 days in his system and pre-budgets them (under ~2 lakh total) [A0sLu7cjjlU]. He uses backtest worst cases to set tolerance: on 10 lots, max drawdown 2.79 lakh, return/drawdown about 3, worst losing streak 7 days [8i-eCbGznbo]. Capital should come from the worst backtest loss over recent years, not the average [sk4_m8Yfzu0, captions unclear].
- **After oversizing:** he cut size sharply and rebuilt only as confidence returned [qhHfMHyouqs].

Clarity is medium to high, but each version appears in only a few videos.

### 2.4 Gap-budget sizing for naked and overnight short options (short side)

**What it is.** Size the naked short so that a specified overnight gap costs a small share of capital. This is his main defence against black swans in the earlier and middle videos.

**Worked figures:**

| Position | Gap or move | Loss | Video |
|---|---|---|---|
| 750 qty (30 lots) | ~1,000 pts / ~4% gap | ~1.8 lakh / ~2.7 lakh; he notes an accidental 5,000 qty would have been dangerous | h5XNvyTMSsk |
| 36,000 naked straddle | 3% / 4% / 5% | ~2 / ~3 / ~5 lakh; 5 lakh is under 1% of capital; exit rather than hold in a bad gap | rEX0xkc5Fes |
| Naked straddle | ~3% fall in both indices | ~1% of capital | tn3IDCnC6dc |
| Naked overnight rule | 2–3% gap | ≤ 1–1.5% of capital | s2KhVugNPfI |
| Short straddle, ~50 lots on ~6 crore | 2–3% gap, loss doubled for safety | must stay under 3%; ~1.5% at that size | XLBtvv6Jq18 |
| 18 lots | 10% gap | ~3% of capital; under 40% even if the index went to zero; "unlimited risk" is a sizing problem | lkOC0gpSmQQ |
| Naked positional cap ~1,000 qty Bank Nifty | 8–9% gap | ≤ ~10% of capital | CfriQ26BKrs |
| Positional book | 1,000-pt move | ~1% of capital | Fe766Um-ayQ |
| Naked book | 1,000 / 2,000 pts | ~1% / ~3% of capital | XA-oogDFs2s |
| Expiry book | 2% gap | ~0.5% of capital | RiTtKlJDrdI |
| Bank Nifty book | 800-pt gap | should not worry him | 2rTZM1IF6DE |

**Capital-equals-notional variant.** Overnight capital per lot should be close to the contract value: about 9 lakh per Bank Nifty lot against roughly 10 lakh notional, with the premium as a ~1,000-point cushion. The test is that the account's percent loss on any gap should not exceed the gap percent itself. Intraday, with stops, 1.5–2.5 lakh per lot is allowed [1fDefykVmnk].

**Related checks.**
- Small size let him ride out a ~3% fall without hedging up front [-kE6iIjC1Ys].
- A 500–600-point fall cost the whole book ~71k, under 15% of the prior week's profit [5_i637lBoPU].
- He pre-computes tolerable and painful gaps (100 vs 200 Nifty points) [dTaB6gl7Ja4].
- Avoid large overnight size when the market is trending strongly rather than consolidating [WtIVfzJvJUg].

**Contradiction (important).** Other videos say:

- never carry a naked short straddle overnight; always add current-week or later-expiry hedges [VnlxZ2uP47M];
- positional trades should always be hedged, at 15–20% of capital, with an overnight loss target of 3–5% [d6ZOFGDVw2Y];
- always keep hedged positions in news-driven markets [G2Jm-SaT6M8, E04yFLaCuas, -IDDp5bvrVQ];
- always trade with a hedge [6WGhlEAouxM].

Against this, he argues one naked lot beats five hedged lots on win rate and expectancy for a similar gap loss [1fDefykVmnk]. The no-stop rule is narrow: trade without a stop only when quantity is low **and** the hedge is near [P21vgTId9P8]. The later videos lean to hedged structures. He also claims a naked straddle's gap loss is comparable to or smaller than an equal-capital index holding [vRGhcoCUbBE, low clarity].

### 2.5 Size from max loss, not from margin; capital per lot; notional leverage

**Rule.** Required capital equals max loss divided by the risk percent. For example, a 5,000 max loss at 2% needs 2.5 lakh per lot; at 5%, 1 lakh [VnlxZ2uP47M]. A four-stop worst case of about 10k at 3% needs about 3.5 lakh, with 5 lakh safer and ~8 lakh margin for all four trades [8No43FVgZfU].

**Capital-per-lot figures (mostly Bank Nifty, Indian lot sizes of the time):**

| Capital per lot | Context | Video |
|---|---|---|
| 2 lakh | Typical stop-out 3–4% of capital, with a 30% premium stop | wcTPYuhzvAU |
| 2.5 lakh | One-lot drawdown ~27k ≈ 11%; sizing on ~90k margin would push drawdown toward 50% | 8i-eCbGznbo |
| 2.5 lakh intraday / 7.5 lakh positional | Margin would allow far more (~60k) | Pt5pbpK1eoI |
| 7.5 lakh of margin | Positional guideline | P21vgTId9P8 |
| 3 lakh minimum, 8 lakh fine | Naked selling | BFZXz79936Y |
| 5 / 7.5 / 10 lakh | Starting / safer / very conservative, naked | lkOC0gpSmQQ |
| At least 5 lakh | Ratio spread | mDW8Ih4CuuY |
| 1–1.25 lakh per hedged set | Keeps ~2× required margin as a buffer | oYfLG7jLvPQ |
| 3 hedged sets on 3 lakh | Rolling straddle | VDvCfzInayY |

**Notional leverage.** Keep notional at no more than 1.5–2× capital: one ~10 lakh Nifty lot on 5 lakh is 2×, and a 5% fall then costs ~10%. Running a lot on ~30k via hedge margin benefit risks a 30–40% loss in one spike; such traders win 99 times and then blow up [yofu41-yyFU].

**Futures.** Size to the full notional you would hold in shares, not to the low margin [PBQXg7M_NVg]. At about 8×, a ~12.5% move doubles or wipes the account [0qmiy0rYOfE]. When hedging a stock portfolio with index futures, compute contract value first: hedge ratio equals hedge notional divided by portfolio value [w5oNCUY0Yyg].

**Minimum account.**
- 5–10 lakh for his strategies; 50k–3 lakh is too small [4HFSshCojaI, mzj47qCugkc, kyQf5lGc_6s].
- About 10 lakh to run several strategies at once [Gv3AMZVWrrI, qiAfmhcuxJE].
- 5–7.5 lakh to start selling [IMjqrkYosgY].
- About 5 lakh [d6ZOFGDVw2Y, NXE7KFxmH7I].

Clarity is high; this is frequent.

### 2.6 Keep spare capital; partial deployment; scaling in

- **Do not deploy everything.** Keep margin free for adjustments [VnlxZ2uP47M, KqKOdPHFG-I, QED0exJOqYc, _sEwi7lQuNA, d3ohL4Aorac].
- **Examples of utilisation:**
  - an iron fly using ~20% of capital as margin, max loss ~1.7%, leaving 80% free; at 5× size the same move would have cost 35 lakh [dPuJiR0oxRs];
  - 5 lakh of 25 lakh used on a positional straddle [ujTuECvyPzc];
  - live-session deployment of 30–40 lakh on a 2.5 crore base [BFZXz79936Y];
  - margin used of 1.38 crore out of ~5.8 crore [xj-1uHZotgY].
- **Start at a fraction.** Begin at about 30% of the intended quantity to leave room to adjust [DnJHEujUHb4].
- **Build during the day.** Scale in through the day with small early entries and size added late. With 10,000 instead of 2,000 quantity, a 3 lakh loss would have been 15 lakh [Pt5pbpK1eoI]. Build in 750-quantity tranches up to 2,000–2,250 [UIf_6_Bg66I].
- **House money.** Size up only with banked profit: go aggressive on expiry only with the day's M2M in hand [qPTgHSIq_f0]. Banked profit offsets the worst case on an add-on, and he caps the net worst case at 2% of capital [F6sjGAcJXXc, oIU_xUVFnwk, QgqjwKIZjlM].
- **Tension.** Elsewhere he says keep position size constant and never double after good days [oYfLG7jLvPQ]. Profit-scaled risk and constant size are not reconciled.
- **Protecting open profit.** Once ~1 lakh is unrealised, the goal becomes not losing it [7RI6oed3Eak]. He cut 4,000 to 1,000 quantity on a sharp afternoon candle [MusX9A1juic]. He calls failing to book at 50–60k profit before it turned into a 91k loss a mistake [4Zd60oo6vOM].

### 2.7 Regime- and event-conditioned size reduction

**Cut size when:**

- **Volatility or premiums are high:** 1,750 to 1,250 quantity [k6bDh3ONgz0]; defensive in high-volatility markets [BGRZRDCcNSI].
- **Swings are choppy:** for example Nifty +300 then −230 points on consecutive days [uM7_U5MZToA].
- **Markets are headline- or news-driven** [tn3IDCnC6dc, E04yFLaCuas].
- **There is an event or election plus expiry** [2dJOkeen6RM].
- **The open is outside the plan,** in which case use small quantity or skip [2rTZM1IF6DE].
- **Conditions are uncertain:** pause, or trade at 10–20% of normal size [xI4klDv-W9U].
- **Trading live on stream:** about half size [BFZXz79936Y].
- **Event risk is expected over the next quarter,** especially for traders with under 1–2 years' experience [m3vTimQ3HiE].

**Other changes:**

- On volatile days, delay the 10 am entry to about 12 pm [NHkRRMWhx4U].
- In trends, use wider strikes; go back to aggressive straddles only in consolidation [4bTRImkOyvY].
- Near Indian financial year-end (March), reduce lots and skip the 10:00 system [OGPVzN-tt3k, jEF9S2_P5Po]. He also cut 70 to 50 to 40 lots to protect a strong run, describing a 3 lakh day loss as ~1% [Vn40nCE-lLI].

No numeric trigger (VIX level, range threshold) is ever given.

### 2.8 Stops, order types, and tail risk of cheap options (short side)

**Always use stops.**
- Keep stops in the system on non-directional shorts rather than watching levels [ZbtIFwwTWhQ, HcdusL_8W5U].
- Put a stop on every leg, even while adjusting: a fixed Rs 100 premium stop, or Rs 150–160 for options sold near Rs 30–40 [-uIGVxZWSHU].
- On expiry, use a stop or a hedge [j-S_P5NMkDs].

**Stop width.**
- Normally 30% of premium. In low VIX he widened to 75% with active adjustments, warning that a both-sides whipsaw then costs much more [wcTPYuhzvAU].
- On a point basis, 75 points versus an earlier 30 on the system straddle [kaPyJdhVI9c].
- He calls a double-sided stop hit the worst outcome of a straddle [L3PBLOfzI6w].

**Order type.**
- Use stop-limit, not stop-market, with the limit 5–10 rupees beyond the trigger (for example trigger 100, limit 103–105) [vx8x_O7-01g].
- Leave an adequate trigger-to-limit gap [rc4ZbNpzND8].
- Stop-market orders cascade through stacked triggers until the book is empty; example: a trigger at 700 filled at 1,800 [JfeLqaREQU0].
- He claims stop-limit works about 99.99% of the time, with no data [JfeLqaREQU0].
- Personal cases: a Tata Steel put sold at ~2 with a stop-market at 1.5 averaged ~5, worst fill 13.7, for a ~3.6 lakh loss; the option expired worthless [vx8x_O7-01g].
- Use the broker's market-protection setting [lev6pAAKvYE].

**Later shift.** Do not rely on stops at all in flash moves. Example: a far-OTM put went 7 → 38 → 100 → ~210 with no trades in between [yofu41-yyFU]. A far hedge (~1,000 points) bought only for margin does not protect you; a real hedge sits 200–300 points away [6WGhlEAouxM]. Keep hedges close and know the max loss before holding overnight [yofu41-yyFU, ujTuECvyPzc].

**Cheap far-OTM shorts are the main black-swan warning:**

- 5-rupee calls went to ~40 in 5 minutes; a 1-rupee hedge went to ~92. Selling 2–5-rupee options with full capital can lose 20%+ on one jump to ~100 [W7Oa3FbF1pg].
- 20 → 350 in 3 minutes on a midcap index option [dmZmt1T5bU0].
- After 3:10 pm on expiry, a ~300-point Bank Nifty drop and recovery within ~4 minutes sent 2–8-rupee options to 100–150; sellers lost 1–8% of capital [WT2kYd3Sofg].
- A Sensex put at 40–52 spiked to ~700 and expired near 250 in the money [6WGhlEAouxM].
- Similar warnings: rc4ZbNpzND8, O2h5RlRlQtQ, c1hz4zsTuvc, CfriQ26BKrs.
- Do not sell full-capital unhedged puts near the money just because the premium looks safe [BT__dPid_rk]. Index concentration (HDFC Bank ~31% of Bank Nifty) is a hidden gap source [BT__dPid_rk].

### 2.9 Expectancy, win rate and reward-to-risk

- **Formula:** expectancy = p_win·avg_win − p_loss·avg_loss. His expectancy ratio divides this by avg_loss. Example: 50% win, 1,500 average win, 1,000 average loss gives 0.25. A higher-expectancy variant can be scaled up in lots [L9f-oq8XVOo].
- **Unadjusted condor:** 75% win rate, 3,785 max profit, 21,215 max loss gives about −2.46 lakh over 100 trades, using the conservative assumption that every loss is a full max loss [8W58_AoCKrw].
- **His logs:**
  - 28 days, 75% win rate, average loss ~60k, average win ~82k. With 2.5 lakh losses instead, the same win rate turns ~+13 lakh into −85k [YMB-ruN6sp8].
  - July: 61% win rate, average loss ~70k, average win ~1.75 lakh; still profitable after removing the two best days [3rLNeQZk0mk].
  - About 60% winning days [IMjqrkYosgY, 6knNR520aK8].
- **Targets and judgment:**
  - Risk 1% to make 0.75–1% at about a 60% hit rate [uN9SRyTv_yY].
  - 50% at 1:1 is worthless; 50% at 1:1.5 is attractive [BFZXz79936Y].
  - He accepts unfavourable payoffs when probability is high: 13k max profit against 37k max loss at 62% PoP [4bTRImkOyvY]; ~1:1.5 against [0xrgICpggJI].
- **Screening thresholds (illustrative only):** max drawdown under 10%, win rate over 70%, expectancy about 0.4. Read risk metrics before returns [NMxUve9X2hY].
- **Loss asymmetry:** a 10/20/50/90% loss needs an 11/25/100/900% gain to recover [dAx2mchFMSs, mW37Il_RHNg, NXE7KFxmH7I].
- **Diversification:** combine strategies so that losing days offset [R22ZKq9rs_M]. This is a concept only, with no numbers.

### 2.10 Margin mechanics (mostly India)

**SEBI peak margin.**
- Upfront margin phased in at 25% → 50% → 75% → 100% (about 4× → 2× → 1.5× → none). Brokers report margin four times a day and can no longer fund clients [AGATtid-fhU].
- Example under the VaR rule: minimum 20% upfront, maximum 5× intraday leverage [A8cB9woq5eQ].
- Consequences for him: size cut from 70 to 50 lots and margin-shortfall rejections on afternoon entries [c29sN7KQSIs, k6bDh3ONgz0].

**Views on leverage (they diverge).**
- Less leverage helps retail survive [AGATtid-fhU].
- But he credits up to 20× leverage for his own early growth and backed the protest against the rules [QED0exJOqYc, qiAfmhcuxJE].
- Indian SPAN margin on hedged spreads can be many times the max loss (4k max loss needing 24k margin; ~3k needing ~43k) [d6ZOFGDVw2Y].

**Pledge and collateral.**
- Shares stay in the client's demat under a lien [I12Dp96UaYM, GZlwZIH4UOI].
- Haircut on equity is max(VaR, 20%); bonds 2–10%; corporate bonds up to 15% [GZlwZIH4UOI]. About 80–90% of share value counts [IMjqrkYosgY].
- ~2.9 crore pledged gave ~2.48 crore of margin [YMB-ruN6sp8]. He prefers brokers that take 100% collateral with no interest [fiueDBlIWgw].
- A 50/50 cash/collateral rule applies. Gilt or G-sec funds count toward the cash half; he cites ~7.3–9% historical returns versus ~3–4% for liquid ETFs [oQXCIfaJ1fs, urrT8zpnGus].
- Drawbacks: falling pledged stocks shrink margin, and pledge margin cannot buy options. Keep a 5–10% cash buffer for daily MTM [GZlwZIH4UOI].

**Hedges for margin benefit.**
- Buy the far hedge first, then sell, in one basket [BFZXz79936Y, BB8KiSmE0ak].
- Examples:
  - ~98k → ~15k [BFZXz79936Y];
  - 1.7 lakh → ~23k [BB8KiSmE0ak];
  - 1.07 lakh → 36k, with PoP falling 57% → 46% [VnlxZ2uP47M];
  - 1.64 lakh → 17k [UdsdCODKv58].
- He states the cheap long leg is for margin, not protection [cJpUydwXnIw].
- Expiries over nine months away need double margin [tTR4X1FsFgE].
- Check basket margin before ordering; the platform display included existing margin [TcH5IWySLJw, -mr_hT8olBE].
- Freeing margin by closing one book to adjust another [GWbpgCAAMkM, lyQNM8KBec4, JdR7-suVxCI].
- Skipping trades when futures had used the margin [cJpUydwXnIw, xV7EMUdSL4w, c29sN7KQSIs].

**Crypto.**
- Use only 25× when up to 100× is available; leverage should fall as capital grows [uN9SRyTv_yY, 3MMjcR_ortI].
- Portfolio margin on Delta Exchange [LrBXT5C_YYY].
- The exchange's claims about insurance fund and auto-liquidation, as he relays them [uN9SRyTv_yY].

### 2.11 Costs as a risk drag

| Period | Total charges | Brokerage | Other components / note | Video |
|---|---|---|---|---|
| Year | ~27 lakh | ~2.2 lakh | ~14 lakh turnover charges | xwWE0ZPmP3s |
| Quarter | ~6.47 lakh | ~67k | about 0.53% of contract value; under 100 orders/day | YMB-ruN6sp8 |
| Quarter | ~6.74 lakh | ~12% | ~88% statutory | TotwNo2N6Jg |
| Month | ~4.29 lakh | ~29k | — | 3rLNeQZk0mk |
| Quarter | ~4.7 lakh on ~27 lakh gross | — | about 17% of gross | U_YWXcxYBXc |
| Crypto, small account | 20–30% of gross | — | — | Hma2mI-kOjY |

Other cost points:

- Pick brokers charging the exchange base rate (no clearing markup) [LsyNOm0vDec].
- At 1 lot a calendar strategy doesn't cover costs; at 10 lots it does [oO-T8_3l_5g].
- A market-order square-off of the whole book realised ~1.33 lakh against ~1.54 lakh displayed [WAXCM9CDx8g].

### 2.12 Operational and execution risk

- **Copy trading and freeze limits.** A copy-trading multiplier pushed an exit order over the Bank Nifty freeze limit (~1,200). About 9,000 quantity per leg stayed open and cost ~20 lakh [91-eSFLtkhg].
- **Hidden duplicate.** A duplicate order hidden by an intraday-only filter cost 6–8 lakh; extra hedges limited it [PiY8pG6Jox4].
- **Typo into a deep-ITM strike** cost 60–70k in slippage [0ioEL11p1kk].
- **Industry fat-finger:** a 14,500 call sold at market for an estimated 200–250 crore loss [hm1ZKfkO9Oo].
- **Leg risk:** closing one leg leaves a naked leg exposed [6knNR520aK8].
- **Order routing** failure took profit from 5 lakh to 1.7 lakh [Vn40nCE-lLI].
- **Glitches** of 20–25 lakh in a quarter [TotwNo2N6Jg, NSFWr0h2n_c, aUFKZY0o3-E]. His response was to close all futures and trade only options for the rest of the quarter [xzkqo36gp8c].
- **Phone management:** verify quantity and stops before walking away; don't manage from a phone [xXDwxid9Fjc].
- **Two terminals** during a broker migration made execution hard to manage [hqdIcWNjFgE].

### 2.13 Capital allocation across books

- **F&O versus equities.** Risk limits apply to F&O. Quality large-cap equities are held through drawdowns [ow6NsXYp9G0, U_YWXcxYBXc]. Equity concentration (top 7 holdings over 50%) caused ~1% versus Nifty's 5.9% in one quarter [Au2cYvYojNM]. He trims equities into SGBs or Liquid BeES under a "50-50 rule" [WtIVfzJvJUg, low clarity].
- **Discretionary versus systems.** Find the capital level where discretionary returns peak and put the excess into systems [lkOC0gpSmQQ].
- **New markets get a sliver:**
  - ~0.5% of the portfolio for crypto [3MMjcR_ortI];
  - ~4% of capital on a BTC option trade, aiming at a 2% loss of crypto capital [NSeHRFG7XVA];
  - ~6k margin out of $15k [MeKx6Qh50vs];
  - $500 → $5k, with $50k only later [uN9SRyTv_yY].
- **Return targets:** 2–3% per month; more means extra risk [lkOC0gpSmQQ, pNloB5rjA8A, qyY60yFUp04, jztFfYokRqI, M18fQBnjMLA, 3FZRs6nCvDk]. A quarterly target is turned into a weekly one without raising size [U_YWXcxYBXc]. 2.5% a month is hard to sustain at hundreds of crores [yDec0_hqKWk].
- **Money discipline:** trade only money you can afford to lose; never borrowed or earmarked money [uN9SRyTv_yY, iZcd9gImTFU].
- **Pairs as partial protection:** a pair offsets part of a market fall only if the long beats the short [E5rCsOzaXyY].

### 2.14 Psychology of size

Oversizing is his stated main cause of failure:

- 3–5× normal size to recover a loss wrecked his emotional control [qhHfMHyouqs].
- Positional Bank Nifty size raised from 500–1,000 to 2,000–2,500 was a "disaster" [7yL3qGyijeM].
- Adding to a carried straddle magnified a bad day [XLBtvv6Jq18].
- About 120 days without profit plus fixed expenses led to irrational decisions [xwWE0ZPmP3s].

The principle: size so normal swings don't hurt emotionally [iZcd9gImTFU, IMjqrkYosgY, xj-1uHZotgY, dAx2mchFMSs (guest)].

Self-reported worst events:
- 15–18 lakh in the COVID crash, with stops not properly placed [BFZXz79936Y];
- 16–17 lakh in a budget rally, with accounts blown 10–12 times early on [IMjqrkYosgY].

## 3. How a program would test it

**1. Daily kill switch.** On an intraday ATM short-straddle book with leg stops (entries at 10:00/13:00/14:00, Nifty and Bank Nifty weekly), compare five cases: flatten all at daily MTM loss of 0.5%, 1%, 2% and 3% of capital, and no cap. Metrics: worst day, max drawdown, CAGR, return/MDD. Variant: staged cap (first cut at ~50–60% of the budget, one re-entry with the remainder) versus a single cap [ZbtIFwwTWhQ, tn3IDCnC6dc, 3uZnthbvz3A, LK5yGOZMcj0].
- *Data:* 1-minute option prices for all strikes, and a cost model including STT, exchange charges, GST and stamp duty.

**2. Gap-budget sizing versus margin sizing.** For carried naked ATM straddles, size so a 5% gap costs ≤1% of capital (or capital per lot ≈ 90% of notional) versus sizing to available SPAN margin. Measure:
- distribution of overnight-gap losses as % of capital;
- the share of gap days where account loss % exceeds index gap % [rEX0xkc5Fes, 1fDefykVmnk, lkOC0gpSmQQ].
- *Data:* daily close and next-open option chains, and historical SPAN margins.

**3. Capital-per-lot claim.** Re-run his 10-lot backtest: does 2.5 lakh per lot keep MDD near 11% while margin-based sizing pushes it toward ~50% [8i-eCbGznbo]? Does 1 lot per 2 lakh with a 30% stop rarely exceed 4% per trade [wcTPYuhzvAU]?

**4. Cheap-option spike frequency.** On expiry days, how often does an option trading under Rs 5 reach ≥8× (and ≥20×) intraday? How often does it end in the money? Split by VIX regime and by the last 20 minutes versus earlier [W7Oa3FbF1pg, WT2kYd3Sofg, 6WGhlEAouxM, O2h5RlRlQtQ].
- *Data:* tick or 1-minute option data.

**5. Stop-market versus stop-limit with a 5–10 rupee buffer.** On short OTM options, simulate both against order-book snapshots. Measure fill minus trigger for stop-market, and the miss rate and eventual exit slippage for stop-limit, during spike events [vx8x_O7-01g, JfeLqaREQU0, yofu41-yyFU].
- *Data:* level-2 or tick data around known freak trades.

**6. Hedge distance.** Compare short strikes with wings 200–300 points away, ~1,000 points away, and naked, on worst-day loss and net return across flash-spike and large-range days [6WGhlEAouxM, P21vgTId9P8].

**7. Volatility-conditioned sizing.** Scale size to 50% (or 10–20%) when VIX, or the prior day's range or reversal, exceeds a threshold, versus constant size. Compare drawdown versus forgone return [k6bDh3ONgz0, uM7_U5MZToA, xI4klDv-W9U, BGRZRDCcNSI]. He gives no threshold, so the threshold itself must be fit out-of-sample.

**8. Drawdown circuit breaker.** Cut size to ~25% after a 3% month-to-date drawdown, or after 10% quarter-to-date F&O drawdown, versus no rule. Compare subsequent MDD and recovery time [Au2cYvYojNM, ow6NsXYp9G0, 7yL3qGyijeM].

## 4. Transfer

**Applies as is (percent-based logic):**
- per-trade caps of 1–2%, with 0.5% around events;
- daily flatten-all caps;
- drawdown circuit breakers;
- sizing from max loss rather than margin;
- keeping spare capital for adjustments;
- expectancy arithmetic and stress-testing by removing best days;
- gap-budget sizing for anything held overnight or over weekends;
- verifying order quantity and leg completion;
- warnings about stop-market orders in thin books;
- the minimal-allocation rule for unfamiliar markets.

**Needs adapting:**
- **Instruments and expiries.** The weekly or daily Indian expiry behaviour maps most closely to SPX/SPY/QQQ 0DTE and short-dated options. TSX index options (e.g. on XIU) are far less liquid, so stop-slippage and spike behaviour would differ.
- **Rupee caps and per-lot capital.** Convert via notional; for example, his "capital ≈ notional for naked overnight" becomes capital per SPX contract near its notional.
- **Margin.** US Reg-T or portfolio margin and Canadian CIRO rules replace SPAN, peak margin and the 50/50 cash rule. Hedge-for-margin effects and order sequencing must be checked per broker.
- **Order types.** US and Canadian stops on options are typically held at the broker, so test stop-limit behaviour there.
- **Costs.** Statutory charges dominate in India. In the US and Canada, commissions and spreads dominate, so the cost drag must be recomputed. Index concentration checks (his HDFC Bank point) apply to sector ETFs and narrow indices.
- **Calendar.** Event-day reduction maps to FOMC, CPI and earnings.

**India-only:**
- SEBI peak-margin phases;
- the pledge and CDSL mechanics, haircut tables and gilt-fund collateral;
- the freeze-quantity rule;
- STT and GST;
- the March financial-year-end size cut;
- the specific lot sizes and margins quoted;
- the far-expiry double margin.

## 5. Gaps and doubts

**Unrecoverable captions.** Several videos are too garbled to state a rule: cmhJCosywwM, f35t-KwNtWk, 2_GaRiEktDk, JyvPu-OYgE4, KQ8kf6Nbt0U, adkYwcQWv1c, c4yDnTlhYSM, D9ctkD_pCxQ, Q_BhDmUE22M, YTyEWqqMNpY, jNqYVp_RXgg. Figures in d3ohL4Aorac and sk4_m8Yfzu0 are flagged as unclear.

**Internally inconsistent figures:**
- nXjmslNVkyo: 3 lakh is both "capital" and the day's risk.
- 303gQALZWuw: capital growth numbers conflict.
- XA-oogDFs2s: "capital ~15 lakh" sits oddly with 1,500 quantity costing only 1% on 1,000 points.
- vRGhcoCUbBE: a 9 lakh loss described as less than an equivalent index position.

**Contradictions or unreconciled shifts:**
- Naked overnight shorts sized small and preferred over hedged lots [1fDefykVmnk, lkOC0gpSmQQ, CfriQ26BKrs] versus never naked overnight and always hedged [VnlxZ2uP47M, d6ZOFGDVw2Y, 6WGhlEAouxM].
- Stop-limit "works 99.99%" [JfeLqaREQU0] versus don't rely on stops in flash moves [yofu41-yyFU].
- Constant size [oYfLG7jLvPQ] versus scaling with banked profit [qPTgHSIq_f0, F6sjGAcJXXc].
- 30% versus 75% premium stops [wcTPYuhzvAU, kaPyJdhVI9c].
- Per-trade caps ranging from 0.3% to 5%, and daily caps from 0.5% to 3%. No single rule ties the level to strategy or regime.
- Pro-leverage [QED0exJOqYc] versus pro-limits [AGATtid-fhU].

The direction over time is toward tighter, hedged, defined risk. The capital base also changes across videos (~70 lakh, 2.5 crore, 3 crore, 5 crore, 6 crore), so rupee caps are not comparable across them.

**Not covered or thin:**
- No quantitative volatility trigger for sizing.
- No Kelly or optimal-f reasoning.
- No portfolio Greek limits (vega or gamma caps).
- No correlation measurement behind the diversification claim [R22ZKq9rs_M].
- No standing tail hedge program (for example long far-OTM puts as permanent black-swan insurance). Protection is via sizing, near hedges, and stops only.
- No rule for overnight-to-weekend or holiday gap scaling, beyond one anecdote [alxZlbVHVeo].

**Evidence quality.** All performance numbers (win rates, monthly returns, worst losses, recovery times) are self-reported and unverified. Some statements come from guests rather than him [dAx2mchFMSs, d6ZOFGDVw2Y].
