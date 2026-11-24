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
| Machine | X: 75 failure-path tests in both repos, last night's leak check (9 of 9) and firewall (9 of 9) | **PASS** |
| Words | W-a, W-b | **not finished**: the Claude credit ran out after 4 of 9 answers; those 4 passed (flag 249 re-runs it) |

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

## The words part (4 of 9 answered before the credit ran out)

- **After a -13% close:** it gave the drop (13.0%, Bank Nifty 16.7%, the fear gauge 72), the stops hit and that they sell at the next open. Asked whether to sell everything, it said there is no such rule and why. Asked whether the market recovers tomorrow, it said "nobody can tell you that".
- **Mid-session with the sign-in lapsed:** it said it could not see live prices and gave the last close with its date. It did not guess.
- One check was wrong on the first try: it took "13.0%" for a missing figure. It was fixed, and the saved answers were scored again without asking again.

## The limits of this run

- JIOFIN, LICI, Eternal and TMCV have no history of their own. They take their industry's median move, so their own swings are understated. That is about a quarter of the book.
- The original holdings are held throughout (no cut list), stopped names are not re-bought, and the 200-day exit is not tested.
- The options model is a week-old Black-Scholes price at the next open, with that day's fear gauge. An option closer to expiry loses more.

## Waiting for Madhav

- **Flag 246:** the Claude credit ran out again.
- **Flag 247:** the options premium cap and the overnight rule for the live start.
- **Flag 239:** joined: broker-side stops and the survival rules set to enforce belong in the live path.
