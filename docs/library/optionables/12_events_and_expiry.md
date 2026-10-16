<!-- Trading Knowledge Library · Optionables (Optionables, India). Built 2026-10-16 from 434 public videos with captions (of 459 on the channel; members-only videos were not used): one structured note per video (Claude Sonnet 5.5) -> this chapter (Claude Opus 5.5), src/research/library.py. Paraphrased; the transcripts stay on the laptop. Evidence class: external teaching = hypotheses to test, never Ananta rules; nothing in the agent reads docs/library/. -->

# Events and expiry

## 1. What he teaches here and how it fits his method

Optionables is mainly an intraday and short-dated index option seller on Nifty and Bank Nifty. This chapter covers the calendar he trades around.

- **Expiry day** is where time decay is strongest, so it is his main hunting ground for short premium. It also brings gamma spikes, whipsaws and occasional flash moves.
- **Scheduled events** are where implied volatility (IV) builds beforehand and collapses afterward. These include the Union Budget, RBI and Fed decisions, US inflation and jobs data, elections, and heavyweight results.

His general stance has three parts:

- Sell premium into an event only when it is intraday and staged. The Budget straddle is the main case.
- Otherwise stay flat overnight through binary events and enter after the announcement, once IV starts to fall.
- Treat open-interest and support/resistance levels as void when news dominates.

The notes also include corporate events (buybacks, delistings, IPOs, mergers) and macro shocks (Covid, war, oil). He presents these mostly as explanation, not as trading setups.

Everything below is his claim or method, to be treated as a hypothesis.

## 2. The ideas

### 2.1 Expiry day as the short-premium day

**What it is.** On weekly expiry, out-of-the-money options lose almost all time value and settle at intrinsic value, mostly zero. That creates many chances for sellers.

**How strongly he committed to it.**
- In early videos he took discretionary trades only on Thursday expiry [fQfzG_emzZw].
- He treated expiry afternoons, decaying to the 15:15 close, as the setting for theta trades [vmjxCxSdIn0].
- He argues sellers accept low premiums on expiry because OTM options go to zero whatever VIX does [d6ZOFGDVw2Y].
- He restricted a multi-time straddle system to Wednesday and Thursday, the days nearest expiry. He showed expectancy of about 0.66, win rate about 72% and reward-to-risk about 1.5 [lkOC0gpSmQQ].
- He favours the last two days before expiry because overnight decay is largest then [oYfLG7jLvPQ].

**Practical details.**
- If an OTM short will expire worthless, let it settle at zero to save exit brokerage. His example: a put sold at 133 settled at 0 [35_p7TIkaTQ].
- He uses same-week options at about Rs 0.2–0.7 as hedges on expiry for margin benefit [BFZXz79936Y].
- He applies OI reading only to weekly expiries. Monthly options are traded on a directional view [3FZRs6nCvDk].
- On some expiries he mainly reviews, adjusts or exits existing positional trades rather than opening new ones [JqEQIQyJ-FU].
- Expiry-day brokerage is notably higher and eats into profit [Bqh1AevjUzg].

**When not to use it, or the cost side.**
- Monthly expiries can be extreme. A Rs 1 OTM option can reach about Rs 30 [j-S_P5NMkDs].
- One monthly expiry turned a profit of 3–4 lakh into a loss of about 5 lakh [jEF9S2_P5Po].
- A two-minute crash around 13:00 took his mark-to-market (MTM) from about +92k to about −3.35 lakh. He treats this as an expected occasional cost [Pt5pbpK1eoI].
- Gamma explains why a Rs 2 option can jump to hundreds as delta climbs from 0.01 to 0.1 to 0.3 [3pPlHdsHBb4]. He therefore says to adjust more aggressively near expiry [d6ZOFGDVw2Y].
- He flags zero-days-to-expiry flash-crash risk, citing a Sensex expiry case [6WGhlEAouxM].
- He also mentions freak fills after NSE removed option freeze limits. His example: a 37100 put went from about 400 to about 2850 in seconds, with stops filled near 1930 [JfeLqaREQU0, vx8x_O7-01g].

**How the regime changed over time.**
- Expiries later sat on three consecutive days: FinNifty Tuesday, Bank Nifty Wednesday, Nifty Thursday. That brings more chances to lose one expiry's gains on the next [OFrd9qxUo80].
- Under daily expiry, premiums are so thin that little cushion is left, yet traders keep selling the cheapest options [W7Oa3FbF1pg].
- For crypto he chose Delta Exchange because it has daily expiry, settled on a 30-minute time-weighted average price (TWAP) at 17:30 IST [uN9SRyTv_yY].

**Clarity.** This is the most repeated theme. It is mostly anecdotal: daily P&L reports, plus one backtest summary.

### 2.2 The intraday rhythm of expiry day

His descriptions of the hourly pattern on expiry day:

| Pattern | What he says | Source |
|---|---|---|
| Gradual decay, then spikes | Decay until about 12:30–13:00. Spikes and delta moves between about 13:00 and 14:30. Use the morning's gains to press harder in that window. If a downside spike comes, build gradually and scale up with profit already made. | [qPTgHSIq_f0] |
| Little decay until after 13:00 | On a very volatile Bank Nifty expiry there was almost no decay until after about 13:00. The straddle then dropped about 150–160 points in the last ~40 minutes. | [NHkRRMWhx4U] |
| No decay until 14:30 | In strong-trend weeks premiums did not decay until about 14:30. One side surged while the other failed to decay. | [UaR5uzHcLos] |
| Tight range, then late breakout | A morning range of about 100 points, broken around 14:00 for a 500–600-point move. | [3Zu5thbvz3A is not cited; source is 3uZnthbvz3A? No — see note] |
| Tight range, then late breakout | A morning range of about 100 points, broken around 14:00 for a 500–600-point move. | [3Qt_5nu_0hY] |
| Tight range, then late breakout | A range of about 200 points until 14:15–14:30, then 400–500 points. | [ujTuECvyPzc] |
| Morning range, then breakdown | Morning range followed by a sharp breakdown. | [GR_KV8MlHZI] |
| Fast decay after 15:00 | MTM rose from 4.3 lakh to 6.2 lakh between 15:00 and 15:30. | [F6sjGAcJXXc] |
| Last hour in a quiet session | With Nifty inside a ~25-point range after 14:00, profit went from 60k to 1.3 lakh. | [NTavZ18KPh8] |
| Decay until 15:00 | Strong decay until about 15:00 on a flat expiry. | [wcTPYuhzvAU] |

**How his advice splits on entry and exit timing.**
- If the morning is volatile, avoid aggression. Wait for roughly 14:15–15:00 and enter small. No trade is acceptable [cA07gugsaeY].
- On expiry, keep entries running into the last 30 minutes and do not book early. Book 20–25% of quantity at intervals. On other days he takes about 1 lakh and stops [IMjqrkYosgY].
- When news flow is unusual, skip the first minutes after the open [QEj_68mxDHI].

**What helps or hurts sellers.**
- He calls a one-way expiry favourable for his straddle approach [ocl7mwUeZA8]. On one day Bank Nifty rose about 1,000 points one way and he made about 5.2 lakh [hqdIcWNjFgE].
- A morning IV spike can make decay large even through swings [CfriQ26BKrs].
- V-shaped whipsaws hurt:
  - a 300–400 gap up, a 600 fall, then a 600–700 rebound [3uZnthbvz3A];
  - a 700 gap down, an 850 bounce, a 700 fall, then a 250–300 bounce, with very low premiums after 13:00. He swung from −3 lakh to +1.2–1.4 lakh [xzkqo36gp8c];
  - a weekly profit given back on expiry [NSFWr0h2n_c];
  - both-side stops hit [BGRZRDCcNSI].

**Volatility clustering.**
- A very volatile day before expiry signals a volatile expiry [pMVDiDH8v08].
- After a one-way down day, expect late recovery and a slight gap up that stalls in the first 15 minutes [2B5kf_5QkpM].

**Clarity.** The timing differs across videos (12:30, 13:00, 14:00, 14:15, 14:30, 15:00). He never states one fixed schedule.

### 2.3 Setting the expiry-day range and trading inside it

**Four ways to set the range.**
- **OI band.** The heaviest call-writing strike is the cap and the heaviest put-writing strike is the floor. Narrow it as the session develops; it is a probability, not a guarantee [dTaB6gl7Ja4].
  - He made specific calls on this basis. Examples: Nifty 15,000–15,700 and Bank Nifty 32,500–33,500, conditioned on a flat open within ±100 points [uM7_U5MZToA]. Nifty: a close below 15,700 means no 16,000 before expiry [OBJL069UfRQ].
- **Straddle-implied range.** A straddle of about 130–150 means Nifty roughly 17,300–17,700 [Fe766Um-ayQ].
  - With VIX low, the expiry-morning straddle is under about 100 points [O2h5RlRlQtQ].
- **Widen when volatility is high.** A 200-point OI band is too narrow in high volatility, so widen to about 400 (16,900–17,300) [cVxwgVbHYKY].
- **Condition on the open.** The open is set by global cues, and the gap shifts which strikes get written [7De_AUtyDeI].
  - Expiry-day OI tells you little about next week; read it the following day [4Zd60oo6vOM].
  - A day that is both monthly and weekly expiry, with futures rollover, is expected to be volatile [cVxwgVbHYKY].

**Trades inside the range.**

*Range-fade and long side*
- Mark upper and lower levels, play cheap OTM option "shots" inside the range, and play reversal trades at the edges [QIcP9ScvavE]. The captions are unclear on the exact structure.
- Buy near the lower reversal level, about 17,700–17,720, in a range-to-bullish plan [walrtSCYQew].
- On Bank Nifty, fade rejections at 43,000 and 42,450 with very small stops, accepting low accuracy for high payoff [walrtSCYQew].
- A flat open between the levels that then breaks upward beats a big gap-up as a bullish signal. After a big gap, let a range form first [walrtSCYQew].
- If Nifty opens inside 18,645–18,880, treat it as range-bound and go long on a break of the top. Short only after 15–30 minutes of consolidation and then a breakdown, and even then cautiously [r3E7X4Se0vk].
- After a gap up, consolidation then an upside breakout should give a trend day [VWpU_gijON8].
- Bank Nifty on a slight gap up tends to sell early and close higher in the second half [VWpU_gijON8]. He says this pattern recurs, but clarity is low.
- He marked 44,600 and 44,150 as Bank Nifty decision zones [4Zd60oo6vOM is not the source; 4hAvzzjA2xw is not the source — the source is 4Xh-l7vMVcM].

*Short side*
- Small gap up: sell Nifty puts at 18,400–18,450, covering above 18,500 (prior-day support) [16t3E1t2tgk].
- Bank Nifty gap up: sell 44,100–44,200 puts. Add a 44,500 call if there is no follow-through, turning it into a short strangle [16t3E1t2tgk].
- After a multi-week resistance breakout that holds as support, sell puts at progressively higher strikes (39,800, 39,900, toward 40,000) [aUFKZY0o3-E].
- Do not adjust a short straddle while Bank Nifty stays within about ±150 points of strike (35,700–36,000). The expected OI range was 35,500–36,200 [JdR7-suVxCI].
- Late discretionary call shorts at 36,600, 36,700 and 36,800 rescued a red system day to about +4.3 lakh [ocl7mwUeZA8].

**Clarity.** The levels are one-off. The repeatable parts are the methods for building a band (OI, straddle) and the "open inside or outside the band" conditioning.

### 2.4 Union Budget: selling the IV crush

**What it is.** Uncertainty inflates premiums before the speech. Once the outcome is known, IV collapses [QVeSJBPD_i4, 8No43FVgZfU].
- He cites a Bank Nifty ATM straddle of about 950 before the Budget versus 450–500 on a normal Tuesday. He expects up to a ~50% fall to about 400–450 by 15:30 [QVeSJBPD_i4].
- His two phases:
  - Phase 1, 09:15–12:00: speech under way, IV highest, the time to sell.
  - Phase 2, 12:00–15:30: IV and theta drag premiums down [QVeSJBPD_i4].
- On 1 Feb 2022 most of the collapse came after about 12:30, within roughly an hour. A no-surprise budget is neutral to positive for sellers [dzFMyd0FiXA].
- He argues the market has already priced a big move in, so a surprise is unlikely to raise IV further [xj-1uHZotgY].
- Habitually buying options on Budget day is a poor idea. The 2021 rally (his figures: about 4% Nifty, 8% Bank Nifty) was a one-off [8No43FVgZfU, bLFCt52D89o].

**Setup variants (short side only).**

| Version | Entries | Stops | Source |
|---|---|---|---|
| Two entries | Separate ATM straddles at 10:00 and 11:00 IST (the speech starts around 11:00), each with its own stops, so no single price decides the day | Per straddle | [bLFCt52D89o] |
| Six entries | Bank Nifty ATM straddles at 09:30, 10:00, 10:30, 11:00, 11:30, 12:00 | 50% stop on each leg's sold premium; exit intraday | [xj-1uHZotgY] |

**His Budget backtest.** He showed a Stockmock backtest over about five budgets, one lot [8No43FVgZfU]:
- Bank Nifty 10:00 entry: about Rs 19,000 total, one losing day of about Rs 2,483.
- Bank Nifty 11:00 entry: about Rs 22,000 total, one losing day of about Rs 2,300, best day about Rs 7,000.
- Nifty: 3 of 3 budgets profitable at both entry times.
- Combining the two entries softened the losing years.
- The stop structure attached to this test (40% per leg, stop moved to cost) differs from the 50% stop in the later six-entry version.

**Budget-day statistics he cites.**
- 7 of the last 10 budgets (interim excluded) closed down. He stresses this does not mean the next must fall [8No43FVgZfU].
- The prevailing trend reversed after 14 of 22 budgets: a pre-budget rally, then profit booking [8No43FVgZfU].
- The index moved more than 4% one month later in 14 of 22 cases. He extrapolates about a 70% chance Nifty (then ~17,300) ends outside 16,500–18,000 [8No43FVgZfU].
- The average move versus the prior close is about 1.2% for Nifty and 2.2% for Bank Nifty [dzFMyd0FiXA].
- Before a budget the market typically rallies or falls in the run-up [20cgOw1G6FE].

**When not to use it, and the contradiction.**
- In a 2023 video he says to keep positions light before the Budget and wait for direction [drr-Gaxlp28].
  - In that video he instead sold a small FinNifty call, about 1,000 quantity, from about 40 to about 20. The FinNifty contract expired Tuesday, the day before the Wednesday Budget, so the position avoided the event [drr-Gaxlp28].
- In the run-up to the 2024 Budget and election he warns sellers to be cautious as VIX rises [m3vTimQ3HiE].
- On the day before or after a Budget, and in the months before elections, he expects irrational moves and call gamma risk on short calls, so stops are needed [ZbtIFwwTWhQ].
- The intraday staged straddle and "go light" are not strictly contradictory, since the former is closed intraday. The emphasis does shift between his 2022 and 2023–24 videos.

### 2.5 Central-bank and macro releases (RBI, Fed, ECB, CPI, jobs)

**Premium behaviour before the event.**
- Premiums do not decay, and may rise, before a known announcement even in a tight range:
  - flat 10:30–14:30 ahead of a 15:00 finance-minister speech [Ga6QSMLRT4o];
  - a 17:00 PM speech [pdGXhkLJPj0, Ga6QSMLRT4o].
- They tend to rise late in the session before the Fed, RBI or US CPI (after about 15:00) [urrT8zpnGus].
- A short put rose from about 85 to about 95 in the last 30 minutes even as the market closed near its high [IjQOUXNIJgk].
- Premiums did not decay on the session before a US jobs report [xzkqo36gp8c].
- The session before big IT results and inflation data should be quieter [RFvomGYSt6k].

**His rules around the event.**
- Exit shorts about an hour before the event. Re-enter with a fresh basket just after it starts (about 15:10) as IV drops [Ga6QSMLRT4o].
- Close intraday positions by about 14:00 before a Fed event. Possibly buy a small long strangle near 15:00 instead [oQXCIfaJ1fs].
- Sell only after the RBI announcement [MusX9A1juic].
- Enter 15–30 minutes after a 10:00 RBI announcement [GxKIIKl4eZA].
- Do not carry positions overnight through US CPI at 18:00 IST [5PSE_0Yw9sc], FOMC [D84ygO71gvA, O2h5RlRlQtQ] or the Fed in general [tKlpB5RfdFA].
- Wait for the next morning's reaction. On a flat open, wait for the market to develop before trading [5PSE_0Yw9sc].
- Keep pre-event analysis brief and do not forecast [JPqXyHXfGfg].
- On news days, OI and technical readings help little. The close and late institutional buying matter more [IjQOUXNIJgk].

**After the event.**
- He expects strong decay the next morning when the event is ordinary. After a no-decay speech day he planned to enter earlier, around 09:20–09:30 [pdGXhkLJPj0].
- He expects strong decay on a post-Fed expiry [IjQOUXNIJgk].
- An RBI straddle was priced for about 600 Bank Nifty points the evening before. With an unchanged policy and an expiry the next day, he expected a sharp drop in premium [7LlVnFIIEB4].
  - Read literally, that implies holding short premium through an RBI event. This conflicts with his "sell after" rule [MusX9A1juic].

**Surprise versus consensus.** He says the surprise relative to expectations matters more than the decision itself.
- With about 40 bp priced (estimates ranged 25–50), a smaller hike reads as positive [1ItbBTjFgVQ].
- An in-line hike with a hawkish tone could still push the market below 16,400 [1ItbBTjFgVQ].
- Fed 50 bp versus 75 bp feared: US up 3–4% [QgqjwKIZjlM].
- Fed 25 bp versus some 50 bp expected: Nasdaq about +3%, Hang Seng about +6%, then an Indian gap up [35_p7TIkaTQ].
- A Fed 75 bp hike was already priced, while 100 bp would get a different reaction [urrT8zpnGus].
- RBI 50 bp in line plus an upbeat governor: Bank Nifty rose about 1,500 points over the week [pZPCRg5w9gw].
- RBI 50 bp versus about 40 bp expected: banks still rallied about 500 points after 15–20 minutes, because they had underperformed beforehand [OSNCbyGvQm4].
- An unscheduled RBI 40 bp hike: Bank Nifty fell about 1,000 points. Selling seemed to start once the 14:00 announcement time became known [NwFNA0IjOkc].
- In a tightening cycle, a strong US jobs beat (265k versus 250k) reads as bad news for markets [pZPCRg5w9gw].
- Cooling US CPI (6.5%) and Indian CPI below estimate (5.72% versus 5.9%) are positive [RxxeW4MyxJg].
- US CPI above 9% was absorbed by the close, and India opened positive [2m1GpJzXBt4].
- A hawkish Fed: India opened about −1.5% and sold until noon [LPGCiis_rlg]. Another time Nasdaq fell about 4% and GIFT Nifty pointed to about −220 [91-eSFLtkhg].

**Sector effects.**
- Banks and NBFCs are hurt by rate hikes [QgqjwKIZjlM].
- Bank Nifty reacts more sharply than Nifty to rate decisions [1ItbBTjFgVQ].
- Higher rates pull money from risk assets into deposits [QgqjwKIZjlM].

**How quiet RBI days are: conflicting observations.**
- An in-line RBI day (25 bp, hawkish) stayed in a narrow range [DLJ0AmH6hS0].
- Another RBI week priced only about 250 points, which he called underpriced [xf1DJgNy3mQ].

### 2.6 Elections

**Rules.**
- No overnight positions into result days [2dJOkeen6RM, -jtW7ba1bsg].
  - His example: the market priced the ruling party to win 2 of 4 states, it won 3 of 4, and Bank Nifty rallied nearly 2,500 points [-jtW7ba1bsg].
- When results land on a Sunday, Monday gaps on the reaction and Tuesday sets the week's direction [z3WtRYijB8U]. Clarity is low.
- Major results, like strong GDP data, can change market structure. This is an exception to his "don't trade news" rule [dmZmt1T5bU0].
  - He cites a December election gap of about 2% on Nifty and about 3% on Bank Nifty [dmZmt1T5bU0].
  - Event-day gaps can also fade: a Bank Nifty gap up (stated as ~4.5%, probably overstated) lost about 1,000 points from the high [pxw7tkirF4Q].

**Claims.**
- A decisive result lowers VIX and is good for the market; a close contest raises VIX [ilbYdeALr0M].
- Before general elections he expects higher IV and VIX and erratic, rangeless intraday action [ZbtIFwwTWhQ, rc4ZbNpzND8, m3vTimQ3HiE].
- Bank Nifty will stay range-bound until results [Vp6a7TiKiZk].
- In 2024 he saw volatility stay low, which he read as the market expecting a clear majority. After elections the market often consolidates [DnJHEujUHb4].
  - This partly contradicts his own expectation of rising VIX before elections.

### 2.7 Company results and heavyweights

**Rules.**
- Do not hold overnight through a heavyweight's results; the reaction is unpredictable [BT__dPid_rk].
  - In that results season, good results gave about +10% and bad ones gave lower circuits or more than 5–6% falls [BT__dPid_rk].
- A heavyweight gap can wreck overnight straddles. HDFC Bank rose about 3% on a card-ban lift, moving Bank Nifty about +300 and costing him 80–90k at the open [KqKOdPHFG-I].

**IV crush on results.**
- After results IV crashes, so Wipro put sellers profited despite a ~6% fall in the stock [4hAvzzjA2xw].

**Reactions he describes.**
- Big misses can get muted reactions: Reliance about 14k crore profit versus 25k expected, stock about −3% [RtecFQegmSI].
- High-P/E stocks (60–70) are punished for small misses: Asian Paints −4 to −5% [xV7EMUdSL4w].
- A cost item can outweigh a beat: Hindustan Unilever fell about 5% on a royalty increase [xV7EMUdSL4w].
- Base effects can inflate growth: Titan sales +200%, stock +6% [ufH0zRUyuIw].
- After a ~10% news jump, the next day pulled back 2.5–3% (HDFC/HDFC Bank) [m3izeXsRdW8].

**Index effects.**
- Heavyweight banks' results swung the index [20cgOw1G6FE, xV7EMUdSL4w, 0ioEL11p1kk].
- A Kotak block deal (about −3%) dragged Bank Nifty about 1.5% while Nifty barely moved [mDW8Ih4CuuY].
- TCS sets the tone for other IT stocks [hLfnVGcoX_w].
- Rupee weakness helps IT exporters [2SuMQE03v2w].
- The IT and HDFC Bank beats he saw as positive [RxxeW4MyxJg].

### 2.8 Geopolitical and shock events

**Claims.**
- Markets fear uncertainty more than the event itself.
  - As the Russia–Ukraine attack actually began, European indices recovered from about −2% to positive [N8jDRk63lK0].
  - De-escalation signals produced a Nifty gap up of 100–150 points [cVxwgVbHYKY].
  - News of a troop pullback produced a ~500-point rally off 16,800 [tn3IDCnC6dc].
  - Peace-talk headlines pointed to a 150–200 point gap up, or 50–100 if the US faded [rEX0xkc5Fes].
  - Gap-downs may reverse, while sanction damage shows up over the longer run [hNhLolw563A].
  - Sanction costs make a quick war less likely [0tWQskBo6Pc].
  - Headline scares often fade, as with North Korea [SalkWOxQ2Rk].
- Shocks are priced in fast:
  - Covid: about −35%, bottoming in April 2020 while GDP fell later [EI9hs2l7RBo].
  - The war: about 10% within a week, then recovery while it continued [EI9hs2l7RBo].
  - Omicron's effect lasted one to two days [aDbp7e_Qvxo].
- Price leads data. Examples: November 2020 highs with a weak economy; an 8.1% GDP print near a top [EI9hs2l7RBo].

**How shocks unfold intraday.**
- A geopolitical sell-off deepened when Europe opened weak. Nifty fell about 3%, Bank Nifty about 1,400 points [-kE6iIjC1Ys].
- An India-only Taiwan-drill drop (Bank Nifty −1,000, Nifty −300) recovered quickly once global markets were seen to be green [hPUdSoT2c7g].
- The UK strain news drove a fall that continued despite a US rebound [snLUyn-bzeM].
- Lockdown rumours drove falls of 300 and then 500 points, then recovery. Expiry that day was wild [aKHjPFQ75dk].

**Rules.**
- OI and support/resistance stop working in a news-driven war market [7RI6oed3Eak, tKlpB5RfdFA].
- Bound loss by position structure, not by trusting a directional view [KBx0tqQMkNw].

**Overnight cues and gaps.**
- Global cues and GIFT/SGX Nifty set the expected gap [FzWERdEYPmI, j02d90xtn_U, 91-eSFLtkhg].
- A major US data day brings an unpredictable gap and first hour [9xAzvNa4s5U].
- With no domestic event, a gap is expected to extend; a flat global open means no big move [OSNCbyGvQm4].
- A gap up that holds and closes near the high is positive; one that fades is not. This matters before month, quarter and year-end expiry [rEX0xkc5Fes].
- Other events he flagged as uncertainty drivers: the US debt-ceiling vote [16t3E1t2tgk], GDP releases [iljL1viJ6I8], and the Fed plus Budget as triggers for a bottom [6qive5Kb4Jk, FBNJsrqlPiQ, 0tWQskBo6Pc].
- An LIC-IPO motive for holding 16,800 was his speculation [N8jDRk63lK0].

### 2.9 Holidays and calendar effects

- Holidays compress decay:
  - Theta is higher in weeks with two holidays [3VTymF8_eww].
  - With only three trading days left before expiry, decay is concentrated [9lj7Ta-vsmc]. A three-day holiday week also makes a big move to far strikes less likely [91-eSFLtkhg].
- A holiday-shifted expiry (Wednesday) makes Tuesday behave like the day before expiry [hLfnVGcoX_w].
  - All three of his systems worked on one such Wednesday expiry [Vn40nCE-lLI].
  - He warns that shifted dates add error to day-of-week studies [oYfLG7jLvPQ].
- Sell next-week options before a roughly four-day holiday weekend [RiTtKlJDrdI].
- He closed expiry-week straddles at a small loss rather than leave them needing adjustment on a day he would not trade [tbHLBk84Btc].
- A holiday the following week needs planning; the captions are too garbled for detail [YTyEWqqMNpY].
- Seasonal claims:
  - Low volatility on the last trading day of the financial year (a range of about 50–60 points) [xwWE0ZPmP3s].
  - A quiet Christmas–New Year week [xDRqGkiOnN8].
  - An erratic June expiry, repeated from the year before [wcnl7rEBE7U].
- A US-session expiry ignored on the Fed's day is not in the notes; the only holiday/expiry content is above.

### 2.10 Corporate and regulatory events (mostly explanatory)

**Buyback.** He gives three channels by which a buyback lifts price:
- Cancelled shares raise each holder's stake and the maximum dividend per share.
- Value per share rises mechanically. His arithmetic ignores the cash leaving the company.
- A premium price signals management's view of value.

His TCS example: a buyback at Rs 3,000 against a market price of about Rs 2,300. The stock went to about Rs 2,800 in 2–3 days [6lOMwtB_oyU].

**Delisting.**
- Price is discovered by reverse book-building at a stated 90% threshold, with a counter-offer allowed within 2 days [EKBihK0IM6E].
- Vedanta: the parent offered 87.5. LIC held out at 320, which became the discovered price. The delisting failed and the stock fell about 21% to about 100 [EKBihK0IM6E].

**IPOs.**
- A grey-market premium of 15–20% suggests a listing gain of about 10–15% [V0yxJqF2Ccs].
- A premium of about 60% plus strong demand means apply for listing gains [g2EoRGqSNUg].
- Other IPO notes are informational: Happiest Minds, Burger King, CAMS, Star Health pre-IPO [dRVf5R71OP8, CL3j4gTVCOA, PftU0l74WDQ, 7PqDLtG2KYM].

**Regulatory and court liabilities.**
- The adjusted gross revenue (AGR) ruling hurt telecom stocks [CwJXRe52BSo, 5s7hi1G2PNI].
- IndusInd fell about 10–11% on whistleblower news [f0-yTPpO71M].
- Excise and duty changes: autos up, metals about −8.5% [tY0noMv3lp0].
- Margin rules: he forecast F&O volume falling at least 30–40% under full upfront margin [AGATtid-fhU]. The 50/50 rule was deferred [PiY8pG6Jox4].
- The SEBI multi-cap rule requires at least 25% in each cap segment [TGlIz26DNMQ].
- Budget wish-lists covered STT, speculative income tax treatment, crypto and sector asks [YnjJZPHEsF0].

**Other context (no trading rule attached).** Hindenburg/Adani allegations [drr-Gaxlp28], HDFC merger [oIU_xUVFnwk], Adani–NDTV [91-eSFLtkhg], Jio–Facebook [rPDPt4A8tuI], negative WTI [p1Rt5u412Ec], the March 2020 oil crash [A1wXLf8v3ps], and further Covid/sector notes.

## 3. How a program would test it

1. **Budget-day IV crush.**
   - *Hypothesis:* On Union Budget days, the Bank Nifty ATM straddle at 15:15 is at least 40% below its 09:30 value, and below its value on matched non-event Tuesdays in percentage terms.
   - *Strategy test:* A six-entry version (09:30–12:00 half-hourly, 50% per-leg premium stop, intraday exit) against single 10:00 and 11:00 entries. Report the per-budget P&L distribution, not just totals.
   - *Data:* 1-minute option chain, strikes and premiums, for all budgets since about 2016, excluding interim budgets. Include costs, STT and slippage.
   - *Sample size:* Expect fewer than 10 events, so treat results as descriptive.

2. **Intraday decay profile on expiry days.**
   - *Measure:* The share of the 09:20 ATM straddle value lost in each window: 09:20–12:30, 12:30–14:30, 14:30–15:00, 15:00–15:30.
   - *Second measure:* Whether absolute index moves in 13:00–14:30 exceed those in the morning.
   - *Conditioning:* Split by expiry-day range terciles and by prior-day range. This tests the volatility-clustering claim [pMVDiDH8v08].
   - *Data:* Weekly expiries for Nifty and Bank Nifty, with 1-minute data.

3. **Pre-event premium behaviour.**
   - *Event days:* Sessions before RBI, FOMC, US CPI and NFP releases.
   - *Comparison:* Change in ATM straddle (or ATM IV) from 14:40 to 15:20 versus ordinary sessions, matched on days-to-expiry and VIX.
   - *Second comparison:* The same measure for intraday-announced events, such as PM or FM speeches, during the hours before the event.

4. **Overnight hold versus flat-then-enter.**
   - *Strategy A:* An ATM short straddle carried from the prior close through an RBI, FOMC, CPI, election-result or heavyweight-results night.
   - *Strategy B:* Flat overnight, then enter 15–30 minutes after the announcement or open.
   - *Metrics:* Mean, the 5th percentile, and the worst outcome.
   - *Data:* An event calendar plus close and open option prices.

5. **Expiry-range containment.**
   - *Measure:* The hit rate of the expiry-day high and low staying inside the band. Define the band as either the highest call-OI strike above spot and highest put-OI strike below spot at the prior close, or the prior-close ATM straddle price added to and subtracted from spot.
   - *Conditioning:* Compare widening the band in high-VIX regimes [cVxwgVbHYKY, dTaB6gl7Ja4, Fe766Um-ayQ].
   - *Data:* End-of-day OI by strike.

6. **Budget statistics replication.** Check his three figures: the fraction of budgets closing down (about 70% claimed); trend reversal from 20 sessions before to 20 after (about 66%); and an absolute 1-month move above 4% (14 of 22 claimed). Also check the mean absolute day move (about 1.2% Nifty, 2.2% Bank Nifty).

7. **Consensus surprise.**
   - *Measure:* Regress the index or Bank Nifty return from the decision to the close (and over 5 days) on actual minus consensus basis points, controlling for hike size.
   - *Data:* Bloomberg or Reuters consensus for RBI and Fed.
   - *Secondary test:* Bank Nifty's absolute move versus Nifty's.

8. **Post-earnings IV crush for short puts.**
   - *Test:* For single-stock options sold at the pre-result close and bought back at the next close, measure the P&L conditional on stock moves of 0–3%, 3–7% and above 7%.
   - *Data:* Results dates and stock option IV.

## 4. Transfer to US and Canadian markets

**Applies largely as is (to SPX/SPY/QQQ and US single names).**
- IV crush after scheduled events: FOMC, CPI, NFP, earnings.
- Pre-event premium firmness in the last hour.
- Staying flat overnight through binary events.
- Surprise-versus-consensus reading of rate decisions.
- The "good news is bad news" jobs logic in a hiking cycle.
- Fast decay and gamma risk near expiry. US 0DTE SPX options are the nearest analogue to his daily-expiry regime [W7Oa3FbF1pg], and the thin-premium warning carries over.
- Heavyweight earnings moving the index: mega-cap tech moves SPX/NDX.

**Needs adapting.**
- *Expiry rhythm.* Session times and settlement differ. SPX is PM-settled (cash-settled at the close) on most expiries, and some contracts are AM-settled. His 13:00–14:30 and after-15:00 windows must be remapped to the 9:30–16:00 ET session and retested from scratch.
- *Budget play.* US and Canadian federal budgets are rarely IV events. The template (staged short straddles into a scheduled event, closed intraday) could be tried on FOMC or CPI days instead. FOMC is at 14:00 ET, so the intraday-entry version fits; CPI is pre-market, which forces an overnight hold or a post-open entry.
- *Canada.*
  - The relevant events are Bank of Canada decisions and Canadian CPI/LFS releases.
  - TSX 60 index options (SXO) and most Canadian single-stock options are far less liquid, so straddle-crush tactics may not survive spreads. US-listed options on Canadian names or on SPX are more practical.
  - TSX is dominated by banks and energy, so his "banks react more to rate decisions" idea should be tested on the S&P/TSX banks against the TSX Composite.
- *Gap cues.* Map GIFT/SGX Nifty to overnight ES/NQ futures. Map "Europe opening weak" to Asia/Europe overnight sessions for US cash opens.
- *Costs.* Indian expiry-day brokerage and STT logic, such as letting worthless shorts settle, differ from US per-contract fees. Exchange rules on far-OTM settlement and assignment also differ.

**India only.**
- Union Budget statistics, STT, the speculative-income tax discussion.
- Grey-market premium for IPOs.
- Reverse book-building delisting.
- NSE freeze-limit history.
- SEBI margin and multi-cap rules.
- The Tue/Wed/Thu expiry calendar and holiday shifts.
- State-election and general-election timing.
- The FinNifty expiry falling the day before the Budget.
- Financial-year-end (March) seasonality.

## 5. Gaps and doubts

**Small samples and self-reported results.**
- The Budget backtest covers about 5 Bank Nifty and 3 Nifty events. His Budget statistics (7/10, 14/22) come without a stated method; "trend reversal" is undefined.
- The 0.66 expectancy for the Wednesday/Thursday filter [lkOC0gpSmQQ] is shown without out-of-sample detail.
- Daily P&L figures are self-reported: 3.3 lakh [GR_KV8MlHZI], 5.2 lakh [hqdIcWNjFgE], 4.3 lakh [ocl7mwUeZA8].

**Contradictions.**
- Sell into the Budget [xj-1uHZotgY, bLFCt52D89o, QVeSJBPD_i4] versus go light and wait [drr-Gaxlp28, m3vTimQ3HiE].
- Sell before an RBI event and expect a crush [7LlVnFIIEB4] versus sell only after it [MusX9A1juic, GxKIIKl4eZA].
- A 50% per-leg stop [xj-1uHZotgY] versus 40% with stop-to-cost [8No43FVgZfU].
- Two entries versus six entries on Budget day.
- Expiry timing: decay until 12:30 then spikes [qPTgHSIq_f0] versus no decay until 13:00 or 14:30 [NHkRRMWhx4U, UaR5uzHcLos].
- Wait until about 15:00 on volatile expiries [cA07gugsaeY] versus stay in through the last 30 minutes [IMjqrkYosgY].
- Pre-election VIX rises [ZbtIFwwTWhQ] versus stayed low [DnJHEujUHb4].
- RBI days are quiet [DLJ0AmH6hS0] versus underpriced [xf1DJgNy3mQ].
- One-way expiries favour his straddles [ocl7mwUeZA8, hqdIcWNjFgE], while large swings wreck them [jEF9S2_P5Po, 3uZnthbvz3A].

**Change over time.**
- About 5–6 years ago: Thursday-only discretionary selling.
- About 3 years ago: three consecutive expiry days.
- About 2 years ago: a daily-expiry regime he says left little premium cushion.
- He does not say how his expiry rules were revised for this, and the notes show no updated method.

**Unclear captions.**
- The "triangle" OTM-shot structure [QIcP9ScvavE].
- The "APE data" release [9xAzvNa4s5U].
- A ~4.5% Bank Nifty gap, likely overstated [pxw7tkirF4Q].
- The Bank Nifty 45100 level [2B5kf_5QkpM].
- A monthly-expiry fall of 800–2000 points [jEF9S2_P5Po].
- Delisting type labels [EKBihK0IM6E].
- IPO subscription figures.
- A strike near "31,xxx" [B8U5XuXjo5o].
- Holiday advice [YTyEWqqMNpY].

**Not covered here.**
- No concrete earnings-straddle setup for stocks beyond the Wipro put example.
- No position sizing for event trades beyond "small" or "light".
- No exact adjustment rules for expiry gamma spikes, beyond the ±150-point no-adjust band.
- No hedging recipe for overnight event risk.
- No VIX thresholds for when to skip an event.
- No treatment of US-style earnings calendars, or of event trades in commodities and currencies.
- No systematic test of the geopolitical "priced in fast" claims, which rest on hand-picked cases.
