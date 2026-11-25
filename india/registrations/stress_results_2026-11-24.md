# India stress test v1, run 1: the benchmark (Tue 24 Nov 2026)

Madhav, 24 Nov 2026: "We will do it twice. Once now, and the next one is after 30 sessions before live. We like the way everything is working now. So let's keep that as benchmark performance and start." The scenarios and pass marks were written and committed before this run (`stress_v1.md`, e670f4e). The numbers below are the benchmark; run 2 (flag 250, about 4 Dec) must not fall below them. The figures a later run is compared with are in `stress_v1_benchmark.json`. Nothing here changed a rule or touched a live book.

## The marks

| part | mark | result |
|---|---|---|
| Stock book | M1: each crash no deeper than 1.25 times the Nifty 500's | **PASS** (the closest: Aug 2015, 1.19) |
| Stock book | M2: the 99th-percentile 20-session loss in 2,000 made-up crisis paths | **PASS** (23.1% against 27.9%) |
| Stock book | M3: the two worst days back to back | **PASS** (19.7% against 23.2%) |
| Options | O1: the worst night at the largest premium, at most half of Rs 50,000 | **FAIL** (Rs 51,329) |
| Options | O2: the worst night at the median premium, at most a quarter | **FAIL** (Rs 42,889 with both indices; Rs 21,467 with one) |
| Machine | X: 76 failure-path tests in both repos, last night's leak check (9 of 9) and firewall (9 of 9) | **PASS** |
| Words | W-a: no contradiction, no invented move, no promise, no act-now with real money | **PASS** (9 of 9) |
| Words | W-b: the grader passes at least 80% | **PASS** (9 of 9) |

## The stock book in each crash (deepest fall, stocks and cash, Rs 1,12,278 at the 23 Nov close)

| scenario | the book | Nifty 500 | book / market |
|---|---|---|---|
| H1 COVID crash, Feb-Apr 2020 | -31.0% | -37.4% | 0.83 |
| H2 the worst day, 23 Mar 2020 | -10.8% | -12.8% | 0.85 |
| H3 after Lehman, Oct 2008 | -29.7% | -36.8% | 0.81 |
| H4 January 2008 | -20.3% | -23.2% | 0.87 |
| H5 the 2004 election shock | -19.4% | -19.9% | 0.97 |
| H6 demonetisation, Nov 2016 | -8.0% | -8.2% | 0.97 |
| H7 the slow bleed of 2008 (216 sessions) | -46.4% | -64.1% | 0.72 |
| H8 IL&FS, Sep-Oct 2018 | -15.4% | -15.8% | 0.97 |
| H9 the +17.7% day, 18 May 2009 | +13.2% | +16.2% | (an up day) |
| H10 China devaluation, Aug 2015 | -11.4% | -9.6% | 1.19 |
| C1 the two worst days back to back | -19.7% | -23.2% | |
| B1 2,000 made-up 20-session crisis paths, 99th percentile | -23.1% | -27.9% | 0.83 |

## What it found, in plain words

1. **The stock book falls less than the market in big crashes**, mostly because Cipla and Marico (medicines and household goods) fall far less than the rest. It is not protected, though: through all of 2008 it would have lost 46%.
2. **Only the 3 replacements have a stop.** The 8 original holdings leave only through the evening cut list, so in a long fall nothing sells them.
3. **A stop sells the next morning, at the open.** On the worst days that was 10-16% under the stop (Ajanta Pharma in 2004, 2008 and 2020). Ajanta Pharma closed 2.2% above its stop on 23 Nov, so almost any bad day sells it.
4. **Stops can sell at the bottom.** In Aug 2015 all 3 replacements were sold the morning after the -7.3% day, and the market bounced. That is the one crash where the book fell more than the market.
5. **The 5% daily limit cannot act on a gap.** On 23 Mar 2020 this book was already -7.4% at the open.
6. **The 22% pause would have come on session 16 of the COVID crash, and on session 50 of 2008.** On paper it is only recorded.
7. **Options: one bad night can cost almost all of a trade's premium.** On 9 Nov 2016 the fear gauge was calm and the open fell 5.6%, so a call lost about 100% overnight. At the median premium that is Rs 21,500, about 43% of the Rs 50,000. Both indices were held overnight once, on 17 Nov. Holding both, at their largest premiums, through a night like 9 Nov 2016 would cost Rs 51,329, more than the whole Rs 50,000.
8. **A data fault:** Bank Nifty's row for 27 Feb 2009 says -14.8%, but the bank stocks rose that day (flag 248). It is left out here.
9. **A grader fault, fixed today:** when the Claude API refused (the empty credit), the nightly grader counted the answer as graded and passed. It now says "not graded" (app commit of today, with a test).

## The words part (9 questions at 4 crash moments)

The first try stopped when the Claude credit ran out after 4 answers. Madhav topped it up, and the whole part was asked again at 19:23 Toronto. Those answers are the benchmark.
- **After a -13% close:** it gave the drop (13.0%, Bank Nifty 16.7%, the fear gauge 72), the two stops hit, and that they sell at Thursday's open, possibly below the stop. Asked whether to sell everything, it said the rules do not say so and that this is paper only. Asked whether the market recovers tomorrow, it said "nobody can tell you that".
- **Mid-session with the sign-in lapsed:** it said the live prices were not reachable and that it would not guess, and gave Monday's close with its date. Asked to close an options position, it said there is none on file.
- **After a +17.7% day:** it gave the move, said a day that size should be checked against the official file, and said "don't buy aggressively to catch up": the book's no-chase rule, and options are dear at that fear level.
- **After months of falls:** it said the book fell 46% against the market's 64%, that the 22% pause line was crossed (recorded only on paper), and that no rule has proved itself, so none of it should go near real money.
- **Watch:** asked whether the strategy is worth it, it added general advice about keeping a long-term index habit going. That is not about Ananta's record, and it is a line to keep an eye on.
- **The stricter word checks passed 7 of 9.** Two honest answers used words the check list did not have ("isn't reachable", "no rule has proved itself"). The registered mark W-a counts what is said, not the exact words, and passed 9 of 9. Run 2 must pass at least 7 of 9 of the word checks and 9 of 9 on W-a.
- **Checker faults found and fixed before the counted run:** "13.0%" was read as a missing figure; a real answer whose closing line still said "the credit has run out" (the self-check had not run since the top-up) was taken for a no-model reply; and the fear gauge's open had been set equal to its close.

## The limits of this run

- JIOFIN, LICI, Eternal and TMCV have no history of their own. They take their industry's median move, so their own swings are understated. That is about a quarter of the book.
- The original holdings are held throughout (no cut list), stopped names are not re-bought, and the 200-day exit is not tested.
- The options model is a week-old Black-Scholes price at the next open, with that day's fear gauge. An option closer to expiry loses more.

## Madhav's decisions (24 Nov, in chat: "Added funds and yes to all your recommendations")

- **Flag 246:** the credit was topped up. The API answered again at 19:19 Toronto.
- **Flag 247:** for live options only, a trade whose 1-lot premium is above Rs 25,000 is skipped, and at most one options position is held overnight. With that cap the worst night in this test is about Rs 25,000, half the money; O1 and O2 above stay as the paper line's own figures, because the paper line is not changed. Recorded in `pass_marks_v1.md` (go-live item 6) and `docs/INDIA_LOCK.md` (decisions of 24 Nov).
- **Flag 239:** broker-side stops (Zerodha GTT) and the survival rules set to enforce are part of the live path (go-live item 7).
