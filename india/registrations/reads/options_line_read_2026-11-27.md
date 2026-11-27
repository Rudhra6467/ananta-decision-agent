# The options line (SP1 v2) at 20 scored sessions: read on Fri 27 Nov 2026

Flag 88 (due Wed 25 Nov, read two days late), with flags 197 (sizing) and 243 (does choosing the side add anything?). Go-live checklist items 2 and 4 (`pass_marks_v1.md`). Read-only; nothing here changes a paper rule.

- **Script:** `~/ananta_runs/prelive/reads_sp1.py`, sha256 `43716b8e36e00be67f8985c8c7149c55cf4ad5340e7145cb060fa47839b8a75b`. Output: `~/ananta_runs/prelive/reads_sp1.out`.
- **Read from:** `~/ananta_data/india/paper/sp1/outcomes.jsonl` and `decisions.jsonl` (one scored row per trade, as `write_book` counts them).
- **Which 20 sessions:** the first 20 sessions with decisions from 26 Oct: 26 Oct to Wed 25 Nov. 19 Nov is not one, because no Kite sign-in by 09:10 IST meant no decisions that day. So the 20th session is 25 Nov, not 23 Nov as the item said. Its trade closed at the 26 Nov open and was scored that day. Every trade of the 20 sessions is scored: 4 Nifty and 19 Bank Nifty. The 26 Nov decision could not be traded and is not scored, and the 27 Nov trade is still open, so these figures are also the whole record as it stands.

## The mark (copied unchanged from pass_marks_v1.md)

> **PASS (for a live start of 1 lot)** needs all four of these:
> 1. Its net rupees with realistic fills are above zero over the 20 sessions.
> 2. It is still above zero with its single best trade removed. A line that one trade carried has not shown it can repeat.
> 3. The mean net index move per trade, after costs, is above zero.
> 4. No stop or exit rule was broken in the record. Every trade's exit matches its registered exit (sp1_v2.json).
>
> **FAIL** is any of the first three.
>
> **Watch**, never a fail on its own:
> - a premium above 25% of the Rs 50,000 options money (G-15/G-16 review);
> - realistic fills more than Rs 500 a lot worse than the study fills.

## Result, each index on its own

| | Bank Nifty | Nifty |
|---|---|---|
| Trades | 19 | 4 |
| 1. Net rupees, realistic fills (1 lot) | **Rs +103,219** (yes) | **Rs +3,393** (yes) |
| 2. Without the single best trade | Rs +42,296 (best: 20 Nov, Rs +60,923) (yes) | **Rs -3,641** (best: 2 Nov, Rs +7,034) (**no**) |
| 3. Mean net index move a trade, after costs | +47.0 bp (yes) | +15.0 bp (yes) |
| 4. Every exit matches its registered exit | 19 of 19 (yes) | 4 of 4 (yes) |
| **Verdict** | **PASS** | **FAIL** (condition 2) |

For condition 4, each trade's exit and direction were checked against its own decision row. A NEXTOPEN trade had to be held to the next open or stopped. A stop trade had to be stopped or out at 15:15.

**Bank Nifty's pass rests on two exits nobody can check.** Pre-live T5 (flag 307) found that the exits of 4 Nov (Rs +16,792) and 6 Nov (Rs +34,479) have no recorded price, and Kite no longer serves those expired contracts. Take out those two and the best trade, and Bank Nifty's figure is Rs -8,975. The mark is met on the record as it stands. But how far it is met depends on those two prices, so the line's record should show them as "not checkable" (flag 307's first answer). Twenty sessions is far too few to prove an edge, and a pass only means "go to the next step".

**Nifty fails its mark.** With 4 trades, the line's Nifty result is one trade. Live, the one-overnight rule has skipped every Nifty trade so far (pre-live T1), so live options have only ever meant Bank Nifty. The question this raises for the live start is flag 308, for Madhav (below).

### The watches (never a fail on their own)

- **Premium above Rs 12,500 (25% of Rs 50,000):** Bank Nifty 18 of 19. The largest was Rs 47,910 on 25 Nov, which the live Rs 37,500 cap would have skipped. Nifty 2 of 4 (Rs 16,744 and Rs 12,675). For Bank Nifty this is the normal size of a lot, not an exception. Madhav's caps of 24 and 25 Nov (flags 247, 269) are the answer to it.
- **Realistic fills more than Rs 500 a lot worse than study:** Bank Nifty 5 trades (Rs 563 to Rs 940); Nifty 1 (Rs 501). Over the whole line the gap is Rs 3,500 (Bank Nifty) and Rs 1,304 (Nifty). Separately, T5 found that 37 of 41 paper fill legs sit outside the recorder's bid and ask (flag 306).
- **G-16, does Bank Nifty's looser margin explain its losses?** Not answerable yet. Over these 20 sessions Bank Nifty did not lose: it made Rs +103,219.

## Flag 243: does choosing the side add anything yet?

The test is the same 23 trades, the same minutes and the same costs, compared with being long the index every time:

- The options line averaged **+41.5 bp a trade**. Always long averaged **+55.4 bp**.
- The line's 3 short calls (28 Oct, 5 Nov, 9 Nov, all Bank Nifty) all lost: -43, -69 and -66 bp.
- It was on the right side 14 of 23 times.

**Read:** on these 23 trades, choosing the side has not added anything. Every long the line took was the same as always long, so the whole gap comes from the 3 shorts. Three trades are far too few to judge a short side. The rule stays frozen, and this is a comparison, not a mark. The yardsticks T10 adds on 2 Dec (follow the gap, fade the gap, open to close) will widen it. This read is the comparison for go-live checklist item 4.

## Flag 197: one trade put about half the options money into one premium on a weak edge

The case is 5 Nov, Bank Nifty: a premium of Rs 24,332, an edge of 0.62 standard errors, a loss of Rs 7,253 (14.5% of Rs 50,000).

- **Edge against outcome so far, Bank Nifty:** 9 trades had an edge under 1 standard error. They made Rs +8,404 together and lost on 4 of the 9. The 10 trades at 1 standard error or more made Rs +94,815, but that includes 20 Nov (Rs +60,923) and 6 Nov (Rs +34,479, one of the exits that cannot be checked).
- **Edge against outcome so far, Nifty:** every trade was above 2.5 standard errors.
- **Size:** the line always trades 1 lot, so its size cannot be cut below one lot. The money side of this question was answered by Madhav on 24 and 25 Nov (flags 247, 269): Rs 75,000 of options money, a Rs 37,500 cap on a 1-lot premium, and at most one position overnight.

**Read:** there is no case for a minimum-edge rule on 19 trades. The trades under 1 standard error are still net positive, and on a sample this small any filter would be fitted to noise. Nothing is changed, and the pattern is noted here to be read again with more trades.

## What was filed

- **Flag 308 (YOU, topic `live-options-nifty`):** should live options start with Bank Nifty only, Nifty staying on paper until it passes a later read? The recommendation is yes. The mark is a pass "for a live start" read per index, and little changes in practice, since the one-overnight rule has skipped every Nifty trade so far.

## The two trials not read today (not yet at their count)

- **RX1 (flag 271):** 19 of 20 sessions scored as of 27 Nov (`paper/rx1_trial.json`; mean so far -0.07% against the average liquid stock). The 20th, 26 Nov, is scored with 27 Nov's prices in tonight's nightly run. The read moves to Sat 28 Nov.
- **The shadow trader (flag 272):** 19 of 20 sessions sealed, the last for 27 Nov (`paper/shadow/summary.json`), and 17 stances scored. The 20th sealed session is Mon 30 Nov. The read moves to Tue 1 Dec, once that session's stance is scored.
