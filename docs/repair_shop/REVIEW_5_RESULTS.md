# Repair-shop review #5 (Q5): results (Madhav's reads)

Pre-registration: `REVIEW_5.md` (commit ed67951). Reader: `src/research/reads.py` (commit 87ced4d, with a lookahead test),
both committed before the run. Run 2026-10-03 14:07 UTC on the laptop: 10 coins, 2,139-3,265 daily bars each (2017 to July 2026).
The holdout (Aug-Sep 2026) was not loaded for this test. Full output: `~/ananta_runs/reads/review5_results.json`.

## 1. Does the reader see what Madhav saw? Yes

Point-in-time check on his four SOL buys (candles up to each day only; `review5_cases.json`):

| His buy | What fired |
|---|---|
| C1 Jun 5 (87.67 CAD) | **M1 capitulation** fired at the Jun 5 close (all 3 variants), and again Jun 6. On Jun 4 it was 3 of 4 (volume 1.9x, needed 2.5x). |
| C2 Jun 25 (91.60 CAD) | **M2 higher-low retest** fired Jun 24, 25 and 26, including M2b (BTC made a lower low, SOL did not). |
| C4 Jun 26 (97.95 CAD) | **M2** (same episode as C2). |
| C3 Aug 10 (109 CAD) | **M3 quiet base (a)** fired at the Aug 9 close. On Aug 10 it was 4 of 5: BTC dipped under its 50-day average that day. The breakout read (b) was 5.6% short of the base top, as expected: he bought before the break. |

## 2. Do the reads beat a random day? Not on their own

Primary measure: 30-day hold from the next day's open, net of NDAX costs, minus the same coin's average 30-day return in that
split ("excess"). Counted by independent market events (crypto falls together), not by coins.

| Variant | Status | 2018-2023 events (episodes) | Excess, 30 d | t | 2024-Jul 2026 events (episodes) | Excess, 30 d |
|---|---|---|---|---|---|---|
| M1a capitulation | INSUFFICIENT | 6 (16) | −7.2% | −1.2 | 2 (15) | +3.9% |
| M1b without the BTC panic | INSUFFICIENT | 8 (18) | +11.8% | 0.7 | 2 (15) | +3.9% |
| M1c at least 50% under the high | INSUFFICIENT | 7 (17) | −8.7% | −1.6 | 2 (17) | +3.1% |
| M2a higher-low retest | NOT_SUPPORTED | 17 (26) | −3.6% | −0.7 | 5 (17) | +4.8% |
| M2b plus "BTC lower low" | INSUFFICIENT | 11 (12) | −4.1% | −0.5 | 2 (10) | +23.9% |
| M3a quiet base, upper half | NOT_SUPPORTED | 16 (25) | −4.2% | −0.9 | 8 (16) | +12.1% |
| M3b quiet base, breakout | NOT_SUPPORTED | 9 (10) | +1.9% | 0.2 | 6 (9) | +3.7% |

M1b and M2b are INSUFFICIENT because confirm had only 2 events; their discovery t-values (0.7, −0.5) would not have passed either.
**No variant passes. Nothing is SUPPORTED.**

What the numbers say, in plain words:
- **Capitulation (M1)** in 2018-2023 was mostly 2022: LUNA (May), the June 2022 crash, FTX (Nov). Those lows kept breaking:
  the average deepest drop in the 30 days after the signal was −19%, and the structural stop was hit 44% of the time.
  In 2026 both events (Feb 5, Jun 3) worked: +4.9% average after 30 days, +16% after 90.
- **Higher-low retest (M2)**: 17 events, a small negative excess; positive since 2024 (the June 2026 event had 10 coins).
- **Quiet base (M3a)**: −4.2% at 30 days in 2018-2023, but the 90-day average was very large (+101% net) because of the 2020
  bull run; since 2024, +12.1% excess at 30 days and +14.6% with his stop under the base. Promising, not proven.
- Every read did better in 2024-2026 than in 2018-2023. That is the market Madhav traded in; it is also only 2-8 events.

## 3. What this means

1. His reads find **where to look**: all four of his buys were caught on the right days. That is now live on every coin.
2. On their own they are **not buy signals**. What made his trades work was the reads plus things the reads do not hold: the market
   turning (2026 vs 2022), the news check, buying in steps, a stop under the structure and patience to hold for weeks.
3. By the pre-registered rule, the reads show in the app and in Ask Ananta as evidence with their history; **none rings the phone**
   (only a SUPPORTED read may), and none changes the Explorer.

## 4. Next (each one a new, counted test)
- The blunder guard on the same episodes (exploratory, `reads.py news`): did the news check flag the capitulations that kept falling?
- Combine a read with the decision chain's regime gate (V02) and the T3 portfolio timing, rather than buying the read alone.
- Record every live fire from now on (the app does this); live fires are clean evidence because nobody knows how they end.
