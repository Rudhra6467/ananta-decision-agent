# DR1 results: Defined-risk option selling on expiry day: the short straddle, the iron fly and the iron condor on Nifty and Bank Nifty, opened at the expiry-day open and closed at the close (2014-2023 real prices), against the same structures three sessions before expiry

Registered 2026-10-30T02:27:14+00:00 (spec `dr1_v1.json`, written before the run); family options_eod, k = 62, z = 3.35. Development 2014-2017, validation 2018-2023; nothing from 2024 on. HISTORICAL BACKTEST, paper only.

Fills: every leg at its daily open and daily close in the exchange file, with the half-spread model and the option charges of the day. The opening print of an option is a thin fill (a known weakness, carried over from GK1). ret = net rupees / premium received for the naked straddle, net rupees / capital at risk (net rupees / wing width x lot, about the exchange margin of a spread) for the defined-risk structures; a structure whose credit is 90%+ of the width (a bad wing print) is dropped and counted. exp3 rows are the control: the same structures three sessions before expiry.

## In plain words

**Expiry-day decay is real from the selling side too, but at Rs 50,000 it is not capturable: the bought wings that make the trade affordable cost about as much as the decay earns, and four legs of spread and charges take the rest. Nothing here passes.**
- **Naked short straddle at the expiry-day open, bought back at the close (315 Nifty and 424 Bank Nifty expiry days):** +10.8% and +13.0% of the premium in 2018-23 (t +2.7 and +4.1; Rs +689 and Rs +1,396 a lot on a median credit of Rs 5,250-6,060; 65% winners) but about -8% and -2% in 2014-17 (monthly expiries only for Nifty): REJECTED at the two-period bar. Worst day Rs -25,000 a lot, 5th percentile Rs -6,000 to -8,600, and the margin is about Rs 1-1.5 lakh a lot: out of reach for the options sleeve whatever the verdict.
- **Iron fly with wings 1% away (the affordable version, margin about Rs 10,000):** the wings cost about Rs 700-1,250 a structure plus two more legs of spread and charges; net Rs -159 (Nifty, OPPOSITE) and Rs -135 (Bank Nifty) a structure, 53-55% winners, longest losing run 7-9.
- **Iron fly with wings 2% away (margin about Rs 17,500-18,750):** Rs +119 and Rs +358 a structure (t +1.3 in validation), 60% winners: positive but far under the bar, and March 2020 cost Rs -15,300 (Nifty) in a month.
- **Iron condor, short 1% out, long 2% out:** credit only Rs 330-700 a structure; Nifty lost (OPPOSITE, 35% winners, an 18-trade losing run), Bank Nifty about zero.
- **The control (the same structures three sessions before expiry, closed the same day):** every defined-risk version lost 4-16% of the width in both periods (VALIDATED the wrong way, 20-37% winners): without expiry-day decay, four legs of friction are a steady loss. So the expiry-day effect is real and specific; the friction is what kills the affordable version of it.
- **Fills:** each leg at the exchange file's daily open and close. The open is a thin print (dropped where a wing's credit reached the width: 0-20 cases a variant); an intraday entry after the first 15 minutes, or a stop, is not modelled and could move these numbers either way.
- **What Ananta does with this:** no paper trial of expiry-day selling at the sleeve's size; the finding joins the exit book as a fact ('the decay is there, the price of the insurance eats it'). If the sleeve ever grows past Rs 1.5 lakh the naked straddle's 2018-23 record could be re-examined with intraday fills from the live recorder, which has been collecting real option quotes since 18 Oct. No rule changes.

## The rows

Verdicts: VALIDATED and CONDITIONAL would be passes; OPPOSITE means significantly the other way round; INCONCLUSIVE means too few independent blocks (16 needed per period) or a reading below the bar. A control row (expected 0) that comes out REJECTED or INCONCLUSIVE is a clean control.

| variant | expected | verdict | dev mean | dev t | dev blocks | val mean | val t | val blocks | trades | win | mean Rs | worst Rs | p5 Rs | max DD Rs | losing run | Mar-2020 Rs |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| NIFTY|exp0|straddle | + | REJECTED | -8.50% | -0.76 | 16 | +10.80% | +2.66 | 24 | 315 | +64.44% | +565 | -25044 | -6043 | -29379 | 5 | +2127 |
| BANK|exp0|straddle | + | REJECTED | -2.17% | -0.16 | 16 | +13.04% | +4.07 | 24 | 424 | +64.86% | +1118 | -22081 | -8603 | -47544 | 5 | +26642 |
| NIFTY|exp0|fly_w1 | + | OPPOSITE | -7.29% | -1.77 | 16 | -0.71% | -0.38 | 24 | 311 | +54.66% | -159 | -15722 | -5484 | -54740 | 7 | -9272 |
| BANK|exp0|fly_w1 | + | REJECTED | -1.69% | -0.31 | 16 | -4.90% | -1.71 | 24 | 404 | +52.72% | -135 | -8841 | -5511 | -102246 | 9 | -13600 |
| NIFTY|exp0|fly_w2 | + | REJECTED | -3.12% | -1.20 | 16 | +1.46% | +1.27 | 24 | 314 | +60.51% | +119 | -14735 | -6825 | -35291 | 6 | -15318 |
| BANK|exp0|fly_w2 | + | REJECTED | +0.30% | +0.08 | 16 | +1.86% | +1.32 | 24 | 417 | +59.95% | +358 | -16372 | -7930 | -55320 | 7 | -3860 |
| NIFTY|exp0|condor_1_2 | + | OPPOSITE | -6.61% | -3.51 | 16 | -2.04% | -2.05 | 24 | 312 | +35.26% | -182 | -10127 | -1425 | -61675 | 18 | -15166 |
| BANK|exp0|condor_1_2 | + | REJECTED | -5.22% | -1.72 | 16 | +0.81% | +0.61 | 24 | 418 | +62.20% | -30 | -10802 | -4325 | -56409 | 7 | +1081 |
| NIFTY|exp3|straddle | 0 | INCONCLUSIVE | -12.50% | -2.57 | 16 | -4.82% | -2.84 | 24 | 311 | +51.77% | -371 | -20327 | -5723 | -151585 | 12 | -29541 |
| BANK|exp3|straddle | 0 | INCONCLUSIVE | -10.60% | -2.15 | 16 | -4.24% | -3.17 | 24 | 415 | +53.73% | -534 | -28231 | -6533 | -243932 | 7 | -6241 |
| NIFTY|exp3|fly_w1 | 0 | VALIDATED | -10.60% | -6.18 | 16 | -11.08% | -6.54 | 24 | 291 | +23.02% | -993 | -11750 | -3832 | -289533 | 24 | -36670 |
| BANK|exp3|fly_w1 | 0 | VALIDATED | -13.26% | -5.26 | 16 | -16.33% | -5.22 | 24 | 345 | +20.00% | -1140 | -19770 | -4120 | -393228 | 47 | -6911 |
| NIFTY|exp3|fly_w2 | 0 | VALIDATED | -6.92% | -3.79 | 16 | -4.28% | -5.36 | 24 | 306 | +36.60% | -673 | -8055 | -4080 | -211025 | 17 | -16537 |
| BANK|exp3|fly_w2 | 0 | VALIDATED | -7.83% | -3.86 | 16 | -6.77% | -5.02 | 24 | 401 | +31.92% | -939 | -15372 | -4443 | -379152 | 15 | -10641 |
| NIFTY|exp3|condor_1_2 | 0 | VALIDATED | -12.46% | -4.81 | 16 | -4.91% | -4.72 | 24 | 303 | +32.34% | -363 | -4193 | -2152 | -109367 | 20 | +571 |
| BANK|exp3|condor_1_2 | 0 | VALIDATED | -11.48% | -5.85 | 16 | -13.36% | -4.86 | 24 | 395 | +26.58% | -766 | -9293 | -3388 | -302457 | 18 | -19283 |

Rupees are per one structure of one lot (the lot of the day). The naked straddle's margin (about Rs 1-1.5 lakh a lot) is not in the table; a defined-risk structure's capital at risk is its risk_rs (median in the manifest).

