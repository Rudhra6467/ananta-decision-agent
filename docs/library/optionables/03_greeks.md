<!-- Trading Knowledge Library · Optionables (Optionables, India). Built 2026-10-16 from 434 public videos with captions (of 459 on the channel; members-only videos were not used): one structured note per video (Claude Sonnet 5.5) -> this chapter (Claude Opus 5.5), src/research/library.py. Paraphrased; the transcripts stay on the laptop. Evidence class: external teaching = hypotheses to test, never Ananta rules; nothing in the agent reads docs/library/. -->

# Greeks

## 1. What he teaches here and how it fits his method

Optionables teaches the Greeks as explanations of why option premiums move, not as a prerequisite for trading. He compares them to knowing how an engine works versus driving the car [d6ZOFGDVw2Y]. In his framing:

- **Delta** is the per-point move of the option, read roughly as the probability of finishing in the money.
- **Gamma** is how fast delta changes.
- **Theta** is the daily loss of time value.
- **Vega** is the per-IV-point sensitivity.
- **Rho** he dismisses as unimportant [dPrLYK6otIo, 3pPlHdsHBb4, 0eEhp4WO66U, l4jQUXK6UOc].

The practical uses are three:

1. **A back-of-envelope next-day price estimate**, built as delta × move, plus vega × IV change, minus theta. He uses it to compare ITM, ATM and OTM strikes for buyers [dPrLYK6otIo, 3pPlHdsHBb4, l4jQUXK6UOc, 0eEhp4WO66U].
2. **A narrative for his short-straddle and strangle P&L.** Theta pays when the index consolidates, especially on expiry afternoons. Directional moves (delta and gamma) and rising IV (vega) take that income away [IMjqrkYosgY, Ga6QSMLRT4o, 3uZnthbvz3A, and others].
3. **A claimed structural edge for sellers**, because theta always works against buyers [3pPlHdsHBb4].

Almost every example is Nifty or Bank Nifty weekly options. All of it should be read as his claims, to be tested.

## 2. The ideas

### 2.1 Delta: definition, ranges by moneyness, probability reading

**Definition.** Delta is the expected change in option price per one-point move in the underlying [dPrLYK6otIo, 0eEhp4WO66U, l4jQUXK6UOc, 3pPlHdsHBb4].

**Ranges he quotes for calls.** He describes delta as running from 0 to 1 [3pPlHdsHBb4].

| Moneyness | Delta he quotes | Source |
|---|---|---|
| Deep ITM | about 0.92–0.93 | [0eEhp4WO66U] |
| ITM | about 0.7–0.8 | [l4jQUXK6UOc] |
| ATM | about 0.5 | [0eEhp4WO66U, l4jQUXK6UOc] |
| OTM | about 0.2–0.3 | [l4jQUXK6UOc] |
| Far OTM | about 0.08 | [0eEhp4WO66U] |

In [l4jQUXK6UOc] the ITM and OTM strikes are about 300 Nifty points from spot.

**Worked examples.**
- An 18,000 call with delta 0.31 and premium about 65 should trade near 95 after a 100-point Nifty rise [dPrLYK6otIo]. Arithmetically this is 96; he rounds.
- A 16,000 call went from 30 to 50 on a 100-point rise, which he calls delta 0.2. A further 5 points adds about 1 rupee [3pPlHdsHBb4].

**Probability reading.** He treats delta as roughly the probability of expiring ITM. Sellers re-price, demanding more premium, as that probability rises [dPrLYK6otIo, 3pPlHdsHBb4]. His own example does not line up cleanly: Sensibull showed about 22% ITM probability for the 18,000 call with Nifty at 17,862, while he put delta in the 0.3 range [dPrLYK6otIo].

**Directional P&L.**
- **Long side:** in a one-way rally, positive-delta positions win, calls gain and puts decay [DXTdywSl0D0].
- **Short side:** a sharp fall made a short call leg profit through delta, while a stop on the put leg capped the other side [-wVTqlE51C8].

**Clarity and frequency.** Taught clearly and repeatedly in four dedicated videos. The P&L uses are anecdotal.

### 2.2 Gamma: rate of change of delta; expiry-day risk

**Definition.** Gamma is the change in delta per point, the second derivative of price [dPrLYK6otIo, 3pPlHdsHBb4].

**Examples.**
- Gamma of about 0.0011 takes delta from 0.31 to about 0.37 after a 50-point move [dPrLYK6otIo].
- Gamma of 0.0008 on a delta-0.12 option adds 0.0008 to delta per point [3pPlHdsHBb4].

**Why it matters to buyers.** Delta rises at an increasing rate as an OTM option approaches the money. He credits this compounding for cheap OTM options sometimes multiplying in value [dPrLYK6otIo, 3pPlHdsHBb4].

**When he ignores it.** He drops gamma from his estimates for moves under about 50–70 index points. He says it becomes important around 150–200 points. Leaving it out makes call estimates too low on up-moves [dPrLYK6otIo, l4jQUXK6UOc].

**Short-side risk.** On one Nifty expiry Thursday, large gamma and IV spikes cost him the profits he had made on the Fin Nifty and Bank Nifty expiries that week [OFrd9qxUo80]. This is the only explicit gamma-risk observation in the notes. It is anecdotal, with no numbers.

### 2.3 Theta: daily time decay, and when it actually pays

**Definition.** Theta is the premium lost per day from time alone. He explains it this way: the same distance to the strike must be covered in fewer days, so the ITM probability falls [dPrLYK6otIo, 3pPlHdsHBb4].

**Examples.**
- The 18,000 call loses about 10 rupees a day with 4 days to expiry, going from 65 to about 55 [dPrLYK6otIo].
- An OTM option decays along the path 30 → 27 → 14 → 5 → 0 over five days into expiry, even with a slight upward drift. This illustrates decay accelerating near expiry [3pPlHdsHBb4].

**ITM versus OTM.** Deep ITM and far OTM options with the same time value lose the same rupees to theta. The ITM option, however, gains far more from delta [0eEhp4WO66U].

Worked example, Nifty +10 points, theta assumed at 3 rupees for both strikes:

| Strike | Before | Delta gain | Theta | After |
|---|---|---|---|---|
| 16,800 call (deep ITM) | 495 | +9.2 | −3 | about 501.4 |
| 17,700 call (far OTM) | 10 | +0.8 | −3 | about 7.8 |

So the OTM call loses money despite a favourable move. Note that the equal-theta assumption across a 495-rupee and a 10-rupee option is his simplification.

**Seller's structural edge (claim).**
- Theta is always negative for buyers of calls and puts, whatever the direction, so sellers have a long-run advantage [3pPlHdsHBb4]. He states this with medium clarity and does not address tail losses.
- **Debit structures:** a bullish structure whose long leg carries about 120 of time premium against about 20 on the short leg loses overnight in a flat market. He estimated 1–1.2 lakh on Bank Nifty [9lj7Ta-vsmc].

**Weekends and holidays.**
- He says decay happens every calendar day, including weekends. He acknowledges a competing view that Friday prices already include weekend decay, and does not resolve it. He frames overnight premium as compensation for carrying risk [BFZXz79936Y].
- A holiday before an expiry-week Wednesday means the next-morning P&L graph should include that holiday's decay, so graph estimates are inexact [vRGhcoCUbBE].

**Condition: theta pays only when the index is range-bound.** This is his most frequently repeated practical point.
- A flat, consolidating day produces heavy decay and most of the day's gain [OGPVzN-tt3k, dTaB6gl7Ja4].
- MTM climbed from about −20–25k to profit just by waiting in consolidation. A one-way move can erase this in minutes, so the gain is not real until booked [IMjqrkYosgY].
- A sideways day produced about 1.73 lakh MTM. He expected more if consolidation lasted two more days [eihlpgiPJKA].
- With roughly 20–30 points of net index movement, the book went from about −2,000 to about +72,000 in about 36 minutes, then about 1.2 lakh by 2:18 pm, with no adjustments [WAXCM9CDx8g].
- In a low-VIX regime (VIX about 12, Nifty ranging 40–50 points a day, Bank Nifty 100–150), decay persisted over several days with little adjustment needed [uoFMqwhG5-4].
- **Counter-case:** on a trending, volatile expiry day there was no visible decay in the morning and straddle losses grew. Decay appeared only around 14:15–14:45, once the index sat in a narrow range near the strike [3uZnthbvz3A].

**Intraday timing on expiry and expiry-week days.** All of this is session-specific (IST).

| Source | Window | What he reports |
|---|---|---|
| [GsrNVbSwH04] | from about 1:45–2:00 pm | Acceleration begins; about 20–30k recovered (about 25k loss turned to small profit in about an hour) |
| [M18fQBnjMLA] | about 2:00–2:42 pm | Book went from −10k to +58k with no changes |
| [3uZnthbvz3A] | about 14:15–14:45 | Strong decay once the range narrowed |
| [qyY60yFUp04] | after 3:00 pm | Profit path below |

The [qyY60yFUp04] path: 56k (2:53) → 67k (3:02) → 79k (3:11) → 84k (3:15) → 102k (3:21) → over 120k (3:22). He booked about 116k after slippage.

These are single-day P&L screenshots. He does not separate theta from delta or vega within them.

### 2.4 Vega: IV sensitivity, and IV as theta's offset

**Definition.** Vega is the price change per one-point IV change.

**Examples.**
- Vega of about 8 on the 18,000 call takes it from 65 to 73 for +1 IV point [dPrLYK6otIo].
- An IV rise of 2 points lifting premium from 10 to 12 is vega 1. A Sensibull example showed vega 3.9 on a 19-rupee 16,000 call [3pPlHdsHBb4].
- Calls and puts at the same strike have the same vega [dPrLYK6otIo].

**What drives IV, in his account.** Choppy markets and a higher VIX raise premiums with no index move. His explanation is that sellers demand more for higher expected movement, and buyers see a higher ITM chance [3pPlHdsHBb4, d6ZOFGDVw2Y].

**Long side: IV crush.** A bought 16,000 Nifty call at IV about 37.5% [GEdPl2wK2mY]:
- Index +100 points by about 11 am next day, IV unchanged: projected about +930 rupees.
- Index +100 points, IV falls to about 32%: projected about −18 rupees, so a 100-point favourable move earns nothing.
- Index −100 points, IV jumps to about 65%: projected about +390 rupees. He calls that IV jump exaggerated.

**Short side: IV offsetting theta.**
- If premiums are not falling with time and the index is not moving, rising IV is the usual reason [ybZYfvQzy7E].
- Over about 3 hours with the index at roughly 15,827–15,828, short MTM went from about +11k to about −11k because IV rose [Ga6QSMLRT4o].
- For a short straddle, the net result depends on whether the vega move exceeds the theta gained over the period [9pT7h-M2v64].

Taught clearly across several videos. The magnitude of the IV moves that defeat theta is never quantified.

### 2.5 Rho

He names rho as the fifth Greek but says it matters little because interest rates rarely change. He uses only the other four [3pPlHdsHBb4]. Nothing more in the notes.

### 2.6 The next-day price estimate and strike comparison by percentage

**Two versions of the rule.**
- **Fuller version [dPrLYK6otIo]:** new price = old price + delta × move + vega × IV change + theta × days (theta negative), with gamma ignored.
- **Simpler version [3pPlHdsHBb4]:** new price = old price + delta × move − theta, with vega and gamma both ignored. Example with premium 19.5, delta 0.12, theta about 4.5:
  - Nifty +50 gives about 21.
  - Flat gives about 15.
  - −100 gives about 3.
  - The arithmetic checks.

The later video [dPrLYK6otIo, about 4 years ago] adds vega to the earlier simpler rule [3pPlHdsHBb4, about 5 years ago]. This is possibly a refinement over time. With only two videos, it could equally be a difference of emphasis.

**Comparing strikes by percentage [l4jQUXK6UOc].** Nifty near 16,200; theta in points per day:

| Strike | Premium | Delta | Theta |
|---|---|---|---|
| 15,900 call (ITM) | about 352 | 0.78 | 10 |
| 16,200 call (ATM) | about 154 | 0.51 | 13 |
| 16,500 call (OTM) | about 46 | 0.22 | 9 |

Estimated one-day change, applying delta × move − theta:

| Nifty move | ITM | ATM | OTM |
|---|---|---|---|
| +25 | about +2.8% | about −0.3% | about −7% |
| +100 | about +19.5% | about +24.5% | about +28% |
| −25 | about −8% | about −16% | about −31% |
| −100 | about −24% | about −41% | about −67% |

Spot checks against the deltas and thetas reproduce his figures closely. He notes gamma would raise the ATM and OTM figures on up-moves.

**His conclusion.** Compare risk across strikes by percentage of premium, not rupees per lot. ITM calls suit small expected moves. OTM calls pay only on large moves and lose the most on adverse ones [l4jQUXK6UOc, 0eEhp4WO66U].

## 3. How a program would test it

1. **Next-day estimate accuracy.**
   - *Claim:* for Nifty and Bank Nifty weekly options, the estimate old + Δ·ΔS + vega·ΔIV + θ (one day) predicts the next-day mid-price. Absolute error should stay small (for example within about 5% of premium) when |ΔS| < 70 points, and grow materially when |ΔS| > 150 points.
   - *Comparison:* run against the delta-theta-only version.
   - *Data:* end-of-day (or same-time-of-day) option chains with model Greeks and IV, spot, by strike and days to expiry.
   [dPrLYK6otIo, 3pPlHdsHBb4]

2. **Moneyness asymmetry.**
   - *Claim:* conditional on next-day spot moves of about +25, +100, −25 and −100 points (±10), the average percentage premium change for calls about 300 points ITM, ATM and 300 points OTM matches the ordering in his table.
   - *Specifically:* ITM is best on small up-moves; OTM is best on large up-moves and worst on all down-moves.
   - *Data:* daily chains, 3–5 days to expiry.
   [l4jQUXK6UOc, 0eEhp4WO66U]

3. **Range-bound versus trending theta capture.**
   - *Claim:* the P&L of a short ATM straddle held over an intraday window is positive and larger when the window's high-low range is below a threshold (for example 0.3% of spot) than when it exceeds it.
   - *Decomposition:* split P&L into theta, delta/gamma and vega contributions.
   - *Data:* 1-minute option and spot prices, plus intraday IV.
   [OGPVzN-tt3k, dTaB6gl7Ja4, IMjqrkYosgY, 3uZnthbvz3A, uoFMqwhG5-4]

4. **Expiry-afternoon acceleration.**
   - *Claim:* on expiry days where spot stays within ±0.25% of the ATM strike from 13:45 to 15:30 IST, ATM straddle premium decays faster per minute after about 13:45 and after 15:00 than in the morning session.
   - *Data:* 1-minute expiry-day option prices across many expiries.
   [GsrNVbSwH04, M18fQBnjMLA, qyY60yFUp04, 3uZnthbvz3A]

5. **IV versus theta on flat periods.**
   - *Claim:* in intraday windows where spot moves less than about 0.1%, short ATM straddle P&L is negative when ATM IV rises by more than a threshold, and the sign is predictable from vega·ΔIV versus elapsed theta.
   - *Data:* intraday IV series, chains, and an event calendar.
   [ybZYfvQzy7E, Ga6QSMLRT4o, 9pT7h-M2v64]

6. **IV crush on long calls.**
   - *Claim:* for near-ATM long calls, the one-day breakeven index move rises with the IV drop. A 5–6 vol-point drop should require about a 100-point Nifty gain at roughly 37% IV.
   - *Method:* a pricing-model check plus a historical check around IV drops.
   [GEdPl2wK2mY]

7. **Weekend decay.**
   - *Claim:* the Friday-close to Monday-open (or Monday-close) change in ATM time value for weekly options, holding spot and IV fixed, differs from the average weekday overnight change.
   - *Purpose:* this resolves which of the two views he mentions holds in practice.
   - *Data:* daily or opening chains.
   [BFZXz79936Y, vRGhcoCUbBE]

8. **Seller edge.**
   - *Claim:* systematically selling OTM weekly options (fixed delta, for example 0.2) to expiry has positive mean P&L after costs, with the full left tail reported.
   - *Data:* the full expiry history, plus costs and slippage.
   [3pPlHdsHBb4]

## 4. Transfer

**Applies as is (pure option math).** These carry over directly to US options (SPX, SPY, QQQ, single stocks) and to Canadian options (XIU, TSX-listed equity options on the Montréal Exchange):
- Greek definitions.
- The delta-vega-theta estimate.
- Percentage-of-premium comparison across strikes.
- The IV-offsets-theta logic.
- The IV-crush case.
- Equal vega for calls and puts at the same strike.
- The debit-structure time-premium point.

**Needs adapting.**
- **Point thresholds.** The 25/100-point scenarios, the 50–70 and 150–200-point gamma limits, and the 300-point moneyness spacing are Nifty-specific. Restate them as percent of spot or in standard deviations.
- **Session windows.** The 13:45 / 14:15 / after-15:00 IST windows correspond, if they hold at all, to the last 1.5 hours and last 30 minutes of the US session. The closest US analogue is SPX 0DTE. There is no comparable daily-expiry product on the TSX. Canadian index options (SXO) and most equity options are illiquid, so wide spreads would swamp intraday theta capture.
- **Costs.** US per-contract commissions and Canadian spreads differ from Indian per-lot costs and STT.
- **Volatility gauge.** VIX levels (Indian VIX about 12) need mapping to VIX or VIXC regimes.

**India-only.**
- Specific expiry-weekday effects (Nifty Thursday, the Fin Nifty and Bank Nifty sequence).
- Holiday-before-Wednesday-expiry cases.
- Sensibull screenshots.

Separately from these notes: Indian weekly expiry schedules and the set of indices with weeklies have changed since these videos were published. Any Indian backtest must use the contract calendar actually in force on each date.

## 5. Gaps and doubts

**Delta.**
- The delta-as-probability equivalence is loose, and his own example shows a mismatch (22% versus about 0.3) [dPrLYK6otIo].
- The 0.2 "delta" in [3pPlHdsHBb4] comes from a 100-point move, so it is an average over the move with gamma mixed in, not a point delta.
- Put delta (sign, range −1 to 0) is not covered in these notes.

**Theta.**
- The weekend question is raised but left unresolved [BFZXz79936Y].
- Equal theta for a 495-rupee ITM and a 10-rupee OTM option is an assumption, not observed data [0eEhp4WO66U].
- His three ITM/ATM/OTM thetas (10/13/9) show ATM highest, which differs from the equal-theta framing.

**Attribution.** Most theta evidence is single-day live P&L, totalling many lakhs across [qyY60yFUp04, M18fQBnjMLA, WAXCM9CDx8g, eihlpgiPJKA]. None of it decomposes P&L into delta, gamma, vega and theta, so "theta did it" is his attribution, not something measured.

**Missing numbers and clarity.**
- No quantified thresholds for "range-bound" or "trending," beyond the daily ranges in [uoFMqwhG5-4].
- No quantified size of IV rise that defeats theta.
- Clarity is medium on [BFZXz79936Y, GsrNVbSwH04, qyY60yFUp04, uoFMqwhG5-4] and low on [vRGhcoCUbBE].

**Gamma risk.** Gamma risk to sellers is mentioned once, with no numbers [OFrd9qxUo80]. The seller-edge claim [3pPlHdsHBb4] does not address tail losses or margin.

**Not covered here:**
- Position-level (portfolio) Greeks and delta-neutral hedging rules.
- Skew and smile, and how vega differs across strikes and expiries.
- Second-order Greeks (vanna, charm, vomma).
- Rho, beyond dismissing it.
- How Greeks behave across monthly versus weekly expiries.
- Which pricing model or data source his Greeks come from (apparently Sensibull).

**Possible change over time.** The fuller estimate including vega appears in a later video [dPrLYK6otIo] than the simpler one [3pPlHdsHBb4]. The evidence is too thin to call this a deliberate revision.
