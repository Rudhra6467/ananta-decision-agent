<!-- Trading Knowledge Library · Optionables (Optionables, India). Built 2026-10-16 from 434 public videos with captions (of 459 on the channel; members-only videos were not used): one structured note per video (Claude Sonnet 5.5) -> this chapter (Claude Opus 5.5), src/research/library.py. Paraphrased; the transcripts stay on the laptop. Evidence class: external teaching = hypotheses to test, never Ananta rules; nothing in the agent reads docs/library/. -->

# Volatility and VIX

## 1. What he teaches here and how it fits his method

Optionables is mainly an index option seller. He trades short straddles and strangles on Nifty and Bank Nifty, often intraday and around weekly expiries. In his teaching, volatility is the variable that decides whether the seller's day goes well or badly. Seven threads recur:

- **VIX as an uncertainty gauge.** He reads India VIX as the market's uncertainty level. Its level tells you how large a range to expect.
- **The ATM straddle as the market's priced-in move.** He compares that priced move against the move that actually happens.
- **VIX direction over level.** He treats the direction of VIX (falling vs rising) as more important for sellers than the level.
- **Asymmetric option reaction to moves.** IV jumps on fast falls, so puts explode and calls fail to decay. Gradual rallies tend to bleed IV.
- **Event crush.** IV builds into scheduled events and collapses once they start.
- **Intraday IV swings.** Much of his live-trading commentary explains P&L swings with no index move as vega, not price.
- **Hold through spikes.** He often advises holding short positions through a temporary IV spike if the index stays in range.

These are his claims and observations, mostly from his own trades and one simple data study. They are hypotheses to test.

## 2. The ideas

### 2.1 VIX level sets the expected range

**What.** High VIX means more uncertainty, richer premiums and bigger moves. Low VIX means cheaper premiums and smaller ranges [N8jDRk63lK0, O2h5RlRlQtQ, kaPyJdhVI9c, 4Zd60oo6vOM]. He states this as a concept and backs it with one quantitative study [X8sW2WNaKAs].

**Numbers from that study** (Nifty daily data from 2017, VIX buckets <14 / 14–20 / >20) [X8sW2WNaKAs]:

| Measure | VIX <14 | VIX 14–20 | VIX >20 |
|---|---|---|---|
| Mean absolute overnight gap | ~0.2–0.25% | ~0.4% | ~0.75% |
| Mean absolute open-to-close move | ~0.4% | ~0.56% | ~1% |
| Mean daily high-low range | ~0.78% | ~1% | ~1.78% |
| Weekly mean absolute open-to-close move | ~1.03% | ~1.48% | ~2.48% |
| Weekly high-low range | ~2.04% (~360 pts) | not given | ~4.63% (~840 pts) |

**Premium examples.**
- Friday-morning Bank Nifty ATM straddle: ~800–850 points at VIX 18–20, versus ~500–550 at VIX ~13 [X8sW2WNaKAs].
- At VIX near 20, premiums price roughly double the move of a low-VIX day [kaPyJdhVI9c].

**Related claims.**
- A falling VIX (19 toward 18) means smaller expected gaps, though anything can still happen [H_XvaXezEU0].
- Falling VIX near 20 made him comfortable holding straddles overnight into expiry [Fe766Um-ayQ].

**Clarity.** High, and taught often. The data study is the strongest single source.

### 2.2 VIX direction matters more than level for sellers

**What.** Selling is easy when VIX is falling, because both legs decay. When VIX is rising, a move inflates one leg while the other does not decay, so straddles and strangles lose quickly [RxxeW4MyxJg, Au2cYvYojNM].

**Conditions and numbers.**

*Favourable for sellers:*
- Oct–Nov 2022: VIX fell from ~18 to ~12–13, with flat opens and narrow ranges. Sitting through the day in straddles was easy money [Au2cYvYojNM].
- VIX cooling from 16–17 (Adani spike) to ~13 with a narrow range [DLJ0AmH6hS0].
- VIX easing from ~15 to ~13 over a week gave a calm expiry [xV7EMUdSL4w].
- Falling below 20 brought sharp decay [oAJ8k8TzB7E].
- Falling toward 14–15 makes selling easier [j02d90xtn_U].
- Calmer VIX helps intraday systematic traders generally [2SuMQE03v2w].

*Unfavourable for sellers:*
- December 2022: VIX rose from ~13 to ~15–16, swings grew and the same selling lost money [Au2cYvYojNM, RxxeW4MyxJg].
- After three straight days of rising VIX, both ATM legs rose in the first 5–10 minutes after the 9:15 open [UaR5uzHcLos].

*As a rule:* he teaches entering short straddles on a day VIX falls sharply. His example was about −8% to below 17 [XmP7nK_TMdo].

*A variant:* a market going nowhere while VIX stays at ~18–19 is ideal. Premiums stay rich but realized movement is small, a pattern he says normally belongs to much lower VIX [d-_3zxoHyEg].

**Persistence claim.** Rising VIX tends to keep rising and falling tends to keep falling over a few days. After 3–4 choppy days he does not expect an immediate trend [F0x5faXXRTI].

**When not to use.** Low VIX does not guarantee easy selling. In one case VIX was ~13 but 2–3 weeks of directionless whipsaw hurt sellers [Vp6a7TiKiZk]. In another, repeated 50–80 point Nifty reversals hit all six algo stops, losing about ₹4 lakh [QgqjwKIZjlM].

**Clarity.** High and repeated, mostly from the 3–4-year-old videos.

### 2.3 Does the VIX level itself change seller profitability? (He is inconsistent)

**"Level doesn't matter / low VIX is fine":**
- Below India VIX 12, sellers historically did well. He tells viewers to verify this themselves [F0x5faXXRTI, ~2 yrs].
- Low VIX (~12) needs only small system tweaks. Tighter stops get hit more often, but the tighter range pays [uoFMqwhG5-4, ~5 yrs].
- He avoids no IV range [IMjqrkYosgY].
- No free lunch: high premium only reflects bigger expected moves [F0x5faXXRTI].
- In a streamed discussion, the host does not filter by VIX. The guest (Praful) says a VIX rise matters on Mon/Fri but little on Wed/Thu weekly options unless an event is due [d6ZOFGDVw2Y].

**"Level does matter":**
- At VIX 20–23 he consistently earned over ₹1.5 lakh on certain days, and profits fell as VIX dropped [BFZXz79936Y, ~5 yrs].
- At very low VIX, a 150–200 point Bank Nifty move puts a straddle into loss [P21vgTId9P8].
- Weak afternoon decay once VIX first fell below 20 after a margin cut. He felt unsure how the market behaves in that regime [A0sLu7cjjlU].
- High premiums favour the seller, so he chose a further expiry [lyQNM8KBec4].
- The March 2020 crash was not his worst straddle loss, because IV was already huge. The worst came in a lower-volatility budget-week rally [1fDefykVmnk].

**Reading.** The "low VIX is fine, even good" view appears in both old and recent videos. The "higher VIX paid more" comments are older, situational, and tied to single trades. Treat this as unresolved.

### 2.4 Implied move (ATM straddle) vs realized move

**What.** The ATM straddle price is the market's expected move [hNhLolw563A, F0x5faXXRTI]. Option prices alone reveal the market's probability of finishing above or below a strike [P-hGtRW78rw]. He claims option-implied probabilities beat historical-statistics probabilities, because they reflect the current regime rather than an average of all past regimes [P-hGtRW78rw].

**Underpricing cases, where sellers get hurt:**
- Straddles priced ~1.5–2% (Bank Nifty ~600 pts, Nifty ~250–300 pts), but Nifty moved ~3% and Bank Nifty ranged 4–4.5% (~1,700 pts) [tn3IDCnC6dc].
- Straddle priced ~250 pts for Mon–Thu while Nifty moved ~200 pts a day [xf1DJgNy3mQ].
- Nifty moved ~250 pts in two hours against a ~200 pt straddle [JPqXyHXfGfg].
- Nifty expiry premiums are too low relative to the IV spikes that actually occur. One expiry mistake can erase a week or a month of profit [OFrd9qxUo80].

**Overpricing cases, where sellers benefit:**
- Budget days: over 12 budgets the mean absolute move was ~2.3% (Bank Nifty) and ~1.2% (Nifty). The weekly ATM straddle priced ~4% and ~2.5%, nearly double [8No43FVgZfU].
- A ~1,200 pt Bank Nifty straddle with two sessions left was "very high" [hNhLolw563A].
- A 1-DTE Nifty put ~4% OTM traded near ₹30 in the war sell-off, which he called insane premium [G2Jm-SaT6M8].

**Action rule.** When volatility is high but the straddle is thin relative to likely movement, widen to a strangle. His example was ~200 pts for 3 days at Nifty 18,000 [4bTRImkOyvY]. In high-realized-vol regimes he plans for 500–800 pt Bank Nifty swings [0ioEL11p1kk] or 200–300 pt daily index moves [tY0noMv3lp0] when choosing strikes.

**Caption problem.** One note says premiums price more volatility than is delivered. Its example, though, has the index moving the straddle's full ~0.5% in 15 minutes, which implies the opposite [dmZmt1T5bU0]. The direction of that claim is unclear.

### 2.5 How IV moves with price (spot–vol behaviour and put/call asymmetry)

**Fast falls:**
- IV rises, so puts gain from delta, gamma and vega together and can "explode." Calls are cushioned by vega and decay less than delta implies [dPrLYK6otIo, ZbtIFwwTWhQ].
- Example: on a fast fall, his put went from ₹20 to ~₹50 while the call only went from ₹60 to ~₹50 [GQEbyZhG-ME].
- Tight stops on short calls can be hit even though the market fell [6WGhlEAouxM].
- Far-OTM Bank Nifty puts (37,500–37,700) went from ₹10–18 to ₹300–400 on surprise news, then decayed back toward zero within the session [hPUdSoT2c7g].
- VIX rose ~6.5–7% on a small down day [RtecFQegmSI].

**Gradual rallies:**
- Usually come with falling IV, so vega is negative for holders. His example assumed −1 IV point on a ~1% up move [dPrLYK6otIo].
- Within rallies, IV falls during consolidation and rises again on big upside moves. This is why he took small profits on shorts [L8SZ30on7po].

**Exceptions he flags:**
- It is a myth that VIX must fall when the market rises. A very aggressive rally can lift VIX through fear of missing the upside. He also saw multi-day VIX rises (+2%, +6%, +6%, +7%, +6%) near highs [m3vTimQ3HiE].
- VIX fell ~2% on a day Bank Nifty swung 800 pts down and 600 up. He had no explanation [iPFJBuJqM8Q].

**Breakouts.** An inside-bar breakout comes with volatility expansion [xFZsJsVyU8s].

**Skew.** He never discusses volatility skew as such, meaning IV by strike or a skew index. The nearest he comes is this put/call asymmetry. He also says put ratio spreads work best in falling, high-vol markets where far-OTM puts are rich, and call ratio spreads are less attractive in rising markets [lkOC0gpSmQQ]. Separately, ratio spreads suit VIX near 20 [mDW8Ih4CuuY]. A setup of entering during the post-move spike (calls fall less, puts spike) is low-clarity [jp-dpnaLs38].

### 2.6 After a crash: buyer and seller implications

**Long side (do not).**
- Do not buy calls expecting a bounce after a violent sell-off. As the market recovers slowly, IV falls, and on a small rebound (~300–400 Bank Nifty pts) the vega loss can beat the delta gain [GEdPl2wK2mY].
- Example: on a +1% (~300 pt) Bank Nifty day, every OTM call from 33,000 strike downward on the chain lost value [GEdPl2wK2mY].
- Long straddles made money during the sell-off while IV rose, but not after it peaked [GEdPl2wK2mY].
- Buyers who held before a VIX jump profited. Buyers entering after the jump pay for volatility that has already happened [PiY8pG6Jox4].

**Short side.**
- Shorting calls after a big fall has an edge: a bounce cools IV, so calls rise less than the index move suggests [-IDDp5bvrVQ].
- After a gap-down with ATM options at ~220–230 at the open, he sold a 33,500 straddle (3,000 qty) once the first range formed (~33,400–33,650), expecting fast decay [CfriQ26BKrs].

**Counter-example.** A late-day bet that a sell-off IV spike would cool failed because the market kept falling. He cut at a ₹50,000 loss [-wVTqlE51C8].

### 2.7 Holding shorts through intraday IV spikes

**What.** If the loss comes mainly from IV rather than a large directional move, it should fade if the index stays in range. So hold within a pre-set loss limit [6knNR520aK8, Pt5pbpK1eoI, pdGXhkLJPj0]. He reads a long stretch of no decay with spot flat as a sign IV is still rising, and expects sharp decay when it turns [peakDi79pVs].

**Examples:**

| Situation | Swing | Source |
|---|---|---|
| Shorts entered ~2 pm; VIX rose | Loss of ~₹1–1.3 lakh | [6knNR520aK8] |
| Fast drop, IV spike, then market fell again | ~−₹3.35 lakh peak, recovered to ~−₹1.2 lakh. A bounce did not help because IV fell | [Pt5pbpK1eoI] |
| IV rise with market flat to slightly up (15750 call ₹74→90, 15700 put ₹65→60) | +₹80k to −₹1.2 lakh; held, with a cut level of ₹1.5–2 lakh | [pdGXhkLJPj0] |
| ~1.5 hours of no decay, then IV dropped | −₹40k to +₹73k within 15–30 min | [peakDi79pVs] |
| ~2 pm Nifty entry, index moved only 10–20 pts | MTM ₹67k to ₹19k, then recovered | [HcdusL_8W5U] |
| Re-entry at ~3:10 pm after Bank Nifty ATM went ~170 to ~210 each leg | −₹50k to +₹80k, but slippage left ~₹50k | [GJ-1jOUSekk] |

**When it fails.**
- A ~10% VIX day can make a net-short book lose even on a favourable index move [o2JJ5p03cyc].
- Fresh straddles opened late after an exit ran into a ~300 pt Bank Nifty move plus IV expansion, taking P&L from about +₹10–15k to about −₹1.5 lakh [jztFfYokRqI].
- On a crash day the chart looked flat, but VIX was up ~4.7% (intraday +7–8%, near 22), and the straddle made about zero until the afternoon [v61SICxmkqI].

### 2.8 Time-of-day IV patterns

**Late session (after ~15:00 IST).** He repeatedly saw both legs rise late in the session:
- ~₹70k lost between 15:00 and 15:15, with the day ending ~−₹30k [9pT7h-M2v64].
- Profits shrank after ~3:00–3:05 pm on two Fridays, once from ~+₹70k to a ₹60k loss. He suspects IV plus broker square-off of short positions, but says the cause is unconfirmed [hqdIcWNjFgE].
- He books part of the profit at 3 pm for this reason [ybZYfvQzy7E].
- Weak afternoon decay on a range-bound day; profit fell from ₹40k to ₹20k in 5–10 min [A0sLu7cjjlU].
- Next-week Bank Nifty legs rose from ~370/340 to 385/349 late in the day, which he could not explain (~₹1.2 lakh loss) [s2KhVugNPfI].
- On a fear day, Bank Nifty premium rose ~100 pts into the close [-kE6iIjC1Ys].

**Morning.** On a flat open, premiums and VIX (+5–6%) rose until ~9:30–9:40, then deflated with no index move [iljL1viJ6I8]. See also the 5–10 minute post-open rise [UaR5uzHcLos].

**Clarity.** These are medium-to-low clarity live-trade anecdotes, mostly 4–5 years old. He does not state them as a rule.

### 2.9 Event volatility: build-up and crush

**What.** IV rises before an event with an unknown outcome and collapses once it passes [4hAvzzjA2xw, MusX9A1juic, 1ItbBTjFgVQ].

**Into the event:**
- VIX can rise into the budget, so pure theta selling may fail in the range-bound market beforehand [20cgOw1G6FE].
- He expected VIX elevated into Budget 2022 (1 Feb) and not falling until about the end of the first week of February [LPGCiis_rlg].
- He expects volatility and choppiness into general elections [xI4klDv-W9U].
- A PM speech announcement spiked IV and cost about ₹20k [YtLDcJgJzcQ].

**After the event:**
- Pre-event ATM premiums of ~340 each side, versus a usual 200–210, should collapse the next day even on a flat open. So he does not hold long straddles through events [urrT8zpnGus].
- Crush and decay happened the day after events, with VIX below 20 [OSNCbyGvQm4].
- Budget day saw VIX ~−10% and strong decay despite stop-outs [bLFCt52D89o].
- Post-policy IV drop plus a range gave ~₹40–45k early on a short straddle [GxKIIKl4eZA].
- He expected strong decay the day after an event-driven IV rise [GJ-1jOUSekk].

**Timing rule.** Sell at the start of the event, not before it. His example: MTM went from about −₹10k to +₹88k within 5–7 minutes of re-entry [Ga6QSMLRT4o].

**Overpricing evidence.** See the budget-day study in 2.4 [8No43FVgZfU].

**Clarity.** High and frequent; this is one of his most consistent themes.

### 2.10 Term structure (vega by expiry)

- Far-dated premiums react more to IV changes than near-dated ones. This hurts sellers and helps buyers [tTR4X1FsFgE].
- In a sell-off, a far-dated (24 Feb) Bank Nifty 35,000P/40,000C strangle (1,000 qty) lost ~₹2.5 lakh, mainly because the put gained more than the call lost [6qive5Kb4Jk].
- VIX rises matter more early in the expiry week (Mon/Fri) [d6ZOFGDVw2Y].

### 2.11 VIX as a market-direction and regime signal

**Spikes as warnings:**
- Single-day VIX jumps of about +10%, +15% (back above 20), +20%, and +3.5–4% (crossing 22) are read as warnings of higher volatility ahead [V-R9YyFioe8, AyC9r0_ZiN8, N8jDRk63lK0, tJEhYTG7_k4].
- After a +16% war-fear day, a −8% drop meant fear was fading but not gone [cVxwgVbHYKY].
- He expected VIX above 30 for a week during a prolonged war [E04yFLaCuas].
- After a ~3% small/midcap drop, he expects elevated volatility for 1–2 weeks, spilling into Nifty and Bank Nifty [2dW1cEao03Q].

**Falling VIX as a bullish sign:**
- VIX falling from above 30 toward below 20 means things are settling, which he reads as positive [L3PBLOfzI6w].
- Falling VIX (−5% on the day) plus fading FII selling made the risk-reward on new longs favourable [aDbp7e_Qvxo].
- A record-low VIX (~10.8, the lowest since 2019) came alongside a rally from ~16,800 to ~18,000 [O2h5RlRlQtQ].

**Crypto.** Bitcoin IV of ~60–70 and 8–10% daily moves are why he pays extra for long hedges there [LrBXT5C_YYY].

## 3. How a program would test it

1. **VIX bucket vs realized range (replication)** [X8sW2WNaKAs, kaPyJdhVI9c, H_XvaXezEU0].
   - *Test:* For Nifty and Bank Nifty from 2017 on, bucket days by prior-close India VIX (<14, 14–20, >20). Compute mean absolute gap, open-to-close move, and (H−L)/open, plus weekly equivalents. Check the reported ratios: gaps about 3× higher in the top bucket, ranges about 2.3×. Also check robustness to using percentile buckets.
   - *Data:* daily OHLC and daily India VIX.

2. **Event straddle overpricing** [8No43FVgZfU, urrT8zpnGus, Ga6QSMLRT4o, OSNCbyGvQm4].
   - *Test:* For each budget, RBI policy, and election-result day, compare the prior close ATM straddle (as % of spot) with the realized absolute event-day move. Also measure ATM IV and straddle price from the pre-event close to the next open and close. Compare short straddles entered 1–2 hours before the event start against entries at the start, over 10–30 minutes.
   - *Data:* intraday option chains with timestamps, and an event calendar.

3. **VIX direction regime and short-premium P&L** [RxxeW4MyxJg, Au2cYvYojNM, XmP7nK_TMdo, d-_3zxoHyEg].
   - *Test:* Run a fixed short ATM straddle held from open to close (and a weekly-to-expiry version). Group results by prior 5-day VIX change: falling, flat, rising. Separately, test entries on days VIX fell ≥8% and closed below a low percentile, against all other days. Report mean, hit rate, and tail loss.
   - *Data:* daily VIX and option prices at open and close.

4. **Low-VIX seller returns** [F0x5faXXRTI, uoFMqwhG5-4, P21vgTId9P8, BFZXz79936Y].
   - *Test:* Compare short straddle returns as % of premium and as % of margin with the same stop rules across VIX <12, 12–16, 16–20, and >20. This resolves his internal contradiction.
   - *Data:* the same as test 3, plus historical margin requirements.

5. **Implied-to-realized ratio as a filter** [xf1DJgNy3mQ, JPqXyHXfGfg, tn3IDCnC6dc, 4bTRImkOyvY].
   - *Test:* Compute the ratio of the ATM straddle to (recent mean daily range × days to expiry). Test whether low-ratio days give worse short-straddle P&L, and whether a wider strangle beats the straddle when the ratio is low.
   - *Data:* option chain plus daily OHLC.

6. **Late-session IV drift** [9pT7h-M2v64, hqdIcWNjFgE, ybZYfvQzy7E, A0sLu7cjjlU].
   - *Test:* Using minute-level ATM IV on Bank Nifty and Nifty weeklies, compare the IV change from 14:30–15:00 with 15:00–15:30 IST. Condition on range-bound days and on day of week.
   - *Data:* 1-minute option quotes.

7. **Post-crash call buying** [GEdPl2wK2mY, -IDDp5bvrVQ, PiY8pG6Jox4].
   - *Test:* After days with an index drop of at least X% and a VIX rise of at least Y%, buy OTM calls and hold 1–3 days. Measure P&L conditional on a modest rebound, and split it into delta and vega parts. Mirror the test with short calls.
   - *Data:* daily option chain with IV.

8. **Short-horizon VIX persistence and spike follow-through** [F0x5faXXRTI, AyC9r0_ZiN8, V-R9YyFioe8, 2dW1cEao03Q].
   - *Test:* Check autocorrelation of N-day VIX changes for N = 1–5. Check next-day and next-5-day realized range after one-day VIX jumps of +10% or more and +15% or more, against a matched baseline.
   - *Data:* daily VIX and OHLC.

## 4. Transfer to US and Canadian markets

**Applies largely as stated** (re-estimate the numbers):
- The link between VIX level and realized range.
- The implied-vs-realized straddle comparison.
- Event IV crush (FOMC, CPI, Bank of Canada, earnings).
- The spot–vol asymmetry: puts exploding and calls cushioned on falls, IV bleeding in grinding rallies.
- Higher vega of far-dated options.
- Not buying calls after a fear spike.

US SPX/SPY options and the CBOE VIX are the natural testbed. US daily SPX expiries are the closest match to his expiry-day intraday selling.

**Needs adapting:**
- *Thresholds.* All levels (12, 14, 17, 20, 30) are India VIX levels. Convert them to percentiles or to an IV rank on the local index.
- *Canadian data.* The S&P/TSX 60 VIX (VIXC) exists, but check its availability and history before relying on it. Option liquidity on the TSX 60 and XIU is thin, with wide spreads, so intraday straddle tactics and minute-level IV studies are probably impractical. Computing IV from XIU or SXO chains may be needed.
- *Event calendar.* Replace the Union Budget and RBI meetings with FOMC, BoC, CPI, jobs reports, and the earnings season.
- *Costs.* Slippage on size mattered even in India [GJ-1jOUSekk]. It will be worse in Canadian options.
- *Small/midcap spillover* [2dW1cEao03Q]. Re-test using the Russell 2000 or the TSX Small Cap.

**India-only:**
- The ~15:00 broker square-off explanation [hqdIcWNjFgE].
- The margin-cut regime [A0sLu7cjjlU].
- Specific budget and election dates.
- FII flow as a confirming signal [aDbp7e_Qvxo].
- Wednesday/Thursday weekly decay conventions [d6ZOFGDVw2Y].
- The dated India VIX levels [O2h5RlRlQtQ].

## 5. Gaps and doubts

- **IV rank and IV percentile are essentially absent.** He works with raw India VIX levels and daily % changes, never a rank or percentile of a stock's or index's own IV. Any IV-rank rule would be an extrapolation.
- **Skew is not taught as a concept.** There is no IV-by-strike curve and no skew index. Only the asymmetric put/call reaction and a remark about rich far-OTM puts appear.
- **Historical volatility is barely formalised.** He compares the straddle with recent point moves, not with a computed HV or realized-vol figure. The variance risk premium is implied in his reasoning [d-_3zxoHyEg] but never measured.
- **The evidence is mostly anecdotal.** Only two systematic studies appear: the VIX buckets [X8sW2WNaKAs] and 12 budget days [8No43FVgZfU]. Most intraday IV claims are single live trades, several of which he says he cannot explain [s2KhVugNPfI, iPFJBuJqM8Q, hqdIcWNjFgE].
- **Contradictions:**
  - Whether the VIX level matters for sellers (2.3).
  - Whether straddles are generally overpriced (budget [8No43FVgZfU], 1-DTE puts [G2Jm-SaT6M8]) or underpriced (expiry days [OFrd9qxUo80], [xf1DJgNy3mQ], [tn3IDCnC6dc]).
  - Whether to hold through IV spikes [6knNR520aK8, pdGXhkLJPj0], given that it failed in [-wVTqlE51C8, jztFfYokRqI].
  - Whether VIX falls on rallies [dPrLYK6otIo] or not [m3vTimQ3HiE].
- **Change over time.** In ~5-year-old videos he was unsure about life below VIX 20 [A0sLu7cjjlU] and noted lower profits as VIX fell [BFZXz79936Y]. By ~2 years ago he argued sub-12 VIX was historically good for sellers [F0x5faXXRTI]. The falling-vs-rising VIX framing is concentrated in the 2022–23 videos.
- **Caption issues.** VIX is rendered as "fix," "wicks" or "Wicks" in several videos [F5O2b6_5npQ, E04yFLaCuas, xV7EMUdSL4w]. The tool analytics video gives no results [F5O2b6_5npQ]. The direction of the claim in [dmZmt1T5bU0] is unclear.
- **Not covered:**
  - VIX futures or options.
  - Term-structure contango and backwardation as a signal.
  - Vega sizing or hedging rules.
  - Exact stop rules tied to IV.
  - Single-stock IV and earnings beyond one generic statement [4hAvzzjA2xw].
