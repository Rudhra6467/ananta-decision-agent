# FX1 results: Rupee against the dollar: does a sharply weaker rupee precede weaker Indian stocks (and stronger exporters)?

Registered 2026-10-26T15:31:11+00:00 (spec `fx1_v1.json`, written before the run); family fx, k = 10, z = 2.81. Development to 2017, validation 2018-2023; nothing from 2024 on.

## In plain words

**The rupee moves tell us nothing useful about the next weeks of Indian stocks.**
- **Sharp weak-rupee weeks (443 sessions in 2003-17, 158 in 2018-23) and days (440 / 139):** no effect on the Nifty or Bank Nifty over 5 and 20 sessions, and no edge for IT or Pharma over the Nifty. Every row is REJECTED (largest |t| 1.4).
- **TWT-H42 restated on the rupee (a 5% weaker rupee over 126 sessions, or a 3-year high in USD/INR):** these states last for months, so there are too few independent quarters (23 and 10; 9 and 11): INCONCLUSIVE. Where there is a reading it points the other way: in 2018-23 the Nifty's next 21 sessions were about 4% BETTER after a weak-rupee stretch (t 2.8, 10 blocks).
- **Data:** the USD/INR series (FRED DEXINUS) was already in the macro table from 1990, so no new download was needed.

## The rows

Verdicts: VALIDATED and CONDITIONAL would be passes; OPPOSITE means significantly the other way round in 2000/2003-2017 and the same way in 2018-23; INCONCLUSIVE means too few independent blocks (16 needed per period) or a reading below the bar.

| variant | expected | verdict | dev mean | dev t | dev blocks | val mean | val t | val blocks | events dev / val |
|---|---|---|---|---|---|---|---|---|---|
| weak5|nfwd5 | - | REJECTED | +0.46% | +1.44 | 54 | +0.09% | +0.14 | 20 | 443 / 158 |
| weak5|nfwd20 | - | REJECTED | +0.72% | +0.75 | 54 | +0.00% | +0.00 | 20 | 443 / 158 |
| weak5|bankfwd20 | - | REJECTED | -0.37% | -0.29 | 54 | -0.37% | -0.23 | 20 | 443 / 158 |
| weak5|itx20 | + | REJECTED | +0.45% | +0.65 | 54 | -0.66% | -0.72 | 20 | 443 / 158 |
| weak5|pharmax20 | + | REJECTED | +0.37% | +0.56 | 54 | +1.05% | +0.62 | 20 | 443 / 158 |
| weak1|nfwd5 | - | REJECTED | +0.14% | +0.59 | 59 | +0.21% | +0.53 | 23 | 440 / 139 |
| h42_up5|nfwd21 | - | INCONCLUSIVE | +0.46% | +0.44 | 23 | +4.10% | +2.78 | 10 | 747 / 302 |
| h42_up5|nfwd63 | - | INCONCLUSIVE | +1.27% | +0.41 | 23 | +3.37% | +0.99 | 10 | 747 / 302 |
| h42_break3y|nfwd21 | - | INCONCLUSIVE | +4.56% | +1.43 | 9 | +2.29% | +1.23 | 11 | 59 / 59 |
| h42_break3y|nfwd63 | - | INCONCLUSIVE | +12.83% | +1.62 | 9 | +3.93% | +1.12 | 10 | 59 / 59 |
