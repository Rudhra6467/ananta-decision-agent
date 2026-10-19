# OC v1 results: Opening Decision Protocol V1, primary tests

Spec `oc_v1.json` sha `aefc2dd3b3acd741`; implementation notes frozen 2026-10-19T22:07:30+00:00 before any result; code `0f3d009`; run 2026-10-19T22:11:14+00:00.
Dev 2015-2017, validation 2018-2023 (silver only; the 2024+ holdout is sealed and was not read).
Unit: net basis points of the entry price per trade after costs (stocks: per-day mean, then across days). Ledger family OC; every row below counts; the bar now is z = 3.40.

## Primary tests

| Instrument | Variant | Protocol net, dev (t, days) | Protocol net, val (t, days) | Verdict | vs plain rule, val (t) | Verdict | Plain rule net, val (t) | Folds + | m (X2) |
|---|---|---|---|---|---|---|---|---|---|
| NIFTY | k15|E1|X1 | 7.1 (2.74, 435) | -0.7 (-0.32, 915) | REJECTED | 0.7 (0.92) | REJECTED | -1.2 (-0.72) | 6/8 |  |
| NIFTY | k15|E1|X2 | 5.4 (2.25, 435) | -1.4 (-0.76, 915) | REJECTED | -0.4 (-0.47) | REJECTED | -0.7 (-0.44) | 2/8 | 0.706 |
| NIFTY | k15|E2|X1 | 4.6 (1.55, 231) | -2.9 (-1.83, 492) | REJECTED | -1.2 (-1.33) | REJECTED | -1.0 (-0.67) | 2/8 |  |
| NIFTY | k15|E2|X2 | 1.8 (0.71, 231) | -3.1 (-2.06, 492) | REJECTED | -0.8 (-1.03) | REJECTED | -1.5 (-1.11) | 1/8 | 0.343 |
| NIFTY | k30|E1|X1 | 7.1 (2.25, 299) | -2.1 (-0.81, 654) | REJECTED | -1.3 (-1.32) | REJECTED | -0.1 (-0.06) | 6/8 |  |
| NIFTY | k30|E1|X2 | 5.1 (1.74, 299) | -3.4 (-1.47, 654) | REJECTED | -2.0 (-2.17) | REJECTED | -0.4 (-0.19) | 2/8 | 0.66 |
| NIFTY | k30|E2|X1 | 1.6 (0.49, 144) | -3.9 (-2.03, 329) | REJECTED | -0.8 (-0.66) | REJECTED | -2.0 (-1.19) | 2/8 |  |
| NIFTY | k30|E2|X2 | -0.1 (-0.03, 144) | -3.6 (-2.01, 329) | REJECTED | 1.0 (1.04) | REJECTED | -3.6 (-2.58) | 1/7 | 0.234 |
| BANKNIFTY | k15|E1|X1 | 8.5 (2.31, 412) | -0.3 (-0.09, 856) | REJECTED | 2.3 (1.66) | REJECTED | -2.5 (-0.97) | 5/8 |  |
| BANKNIFTY | k15|E1|X2 | 6.8 (2.03, 412) | 0.6 (0.22, 856) | INCONCLUSIVE | 1.5 (1.18) | REJECTED | -1.1 (-0.45) | 4/8 | 0.717 |
| BANKNIFTY | k15|E2|X1 | 3.0 (0.93, 238) | 0.9 (0.35, 445) | REJECTED | 3.0 (2.89) | REJECTED | -2.6 (-1.35) | 5/8 |  |
| BANKNIFTY | k15|E2|X2 | 2.5 (0.84, 238) | -0.4 (-0.17, 445) | REJECTED | 2.8 (3.01) | REJECTED | -3.2 (-1.87) | 3/8 | 0.259 |
| BANKNIFTY | k30|E1|X1 | 6.8 (1.47, 275) | 1.7 (0.45, 591) | REJECTED | 1.9 (1.14) | REJECTED | -0.8 (-0.26) | 4/8 |  |
| BANKNIFTY | k30|E1|X2 | 5.1 (1.30, 275) | 1.0 (0.29, 591) | REJECTED | 0.6 (0.42) | REJECTED | 0.1 (0.04) | 4/8 | 0.603 |
| BANKNIFTY | k30|E2|X1 | 3.7 (0.91, 146) | -1.9 (-0.73, 309) | REJECTED | 1.3 (1.07) | REJECTED | -2.6 (-1.24) | 2/8 |  |
| BANKNIFTY | k30|E2|X2 | 0.5 (0.16, 146) | -0.8 (-0.33, 309) | REJECTED | 2.5 (2.61) | REJECTED | -3.1 (-1.61) | 1/7 | 0.235 |
| STOCKS | k15|E1|X1 | -6.0 (-1.61, 574) | -12.4 (-3.82, 1208) | REJECTED | 11.4 (11.34) | VALIDATED | -13.0 (-9.70) | 1/8 |  |
| STOCKS | k15|E1|X2 | -7.9 (-2.66, 574) | -10.7 (-3.94, 1208) | OPPOSITE | 10.7 (12.47) | VALIDATED | -12.2 (-10.88) | 0/8 | 0.639 |
| STOCKS | k15|E2|X1 | -13.6 (-5.25, 524) | -14.9 (-6.06, 1105) | OPPOSITE | 12.9 (16.15) | VALIDATED | -14.7 (-16.57) | 0/8 |  |
| STOCKS | k15|E2|X2 | -14.0 (-5.86, 524) | -15.2 (-6.61, 1105) | OPPOSITE | 12.9 (18.84) | VALIDATED | -14.7 (-19.79) | 0/8 | 0.304 |
| STOCKS | k30|E1|X1 | -1.6 (-0.34, 497) | -11.0 (-2.51, 1046) | REJECTED | 11.4 (9.45) | VALIDATED | -12.7 (-8.32) | 3/8 |  |
| STOCKS | k30|E1|X2 | -5.1 (-1.39, 497) | -10.3 (-2.90, 1046) | REJECTED | 10.8 (11.10) | VALIDATED | -12.0 (-9.93) | 1/8 | 0.521 |
| STOCKS | k30|E2|X1 | -12.0 (-3.56, 416) | -13.2 (-5.50, 893) | OPPOSITE | 13.2 (15.28) | VALIDATED | -14.4 (-15.04) | 0/8 |  |
| STOCKS | k30|E2|X2 | -12.5 (-4.07, 416) | -13.7 (-6.33, 893) | OPPOSITE | 14.0 (19.93) | VALIDATED | -15.3 (-19.48) | 0/8 | 0.22 |

## Event days: stand down vs trade through (k30|E1|X1, protocol trades)

| Instrument | Event-day net dev (t, n) | val (t, n) | Non-event val | Verdict |
|---|---|---|---|---|
| NIFTY | – (–, 1) | -10.8 (-0.53, 20) | -1.8 (-0.70, 634) | INCONCLUSIVE |
| BANKNIFTY | 97.4 (0.89, 3) | 3.2 (0.10, 19) | 1.6 (0.44, 572) | INCONCLUSIVE |

## What the protocol decided by 10:15 (index days)

| Instrument | k | State | Why waiting | Days |
|---|---|---|---|---|
| BANKNIFTY | 15 | CONFIRMED_LONG |  | 544 |
| BANKNIFTY | 15 | CONFIRMED_SHORT |  | 724 |
| BANKNIFTY | 15 | WAIT | agreement | 39 |
| BANKNIFTY | 15 | WAIT | breadth | 295 |
| BANKNIFTY | 15 | WAIT | breadth_and_agreement | 138 |
| BANKNIFTY | 15 | WAIT | never_together | 11 |
| BANKNIFTY | 15 | WAIT | no_break | 420 |
| BANKNIFTY | 30 | CONFIRMED_LONG |  | 368 |
| BANKNIFTY | 30 | CONFIRMED_SHORT |  | 498 |
| BANKNIFTY | 30 | WAIT | agreement | 28 |
| BANKNIFTY | 30 | WAIT | breadth | 234 |
| BANKNIFTY | 30 | WAIT | breadth_and_agreement | 130 |
| BANKNIFTY | 30 | WAIT | never_together | 2 |
| BANKNIFTY | 30 | WAIT | no_break | 911 |
| NIFTY | 15 | CONFIRMED_LONG |  | 557 |
| NIFTY | 15 | CONFIRMED_SHORT |  | 793 |
| NIFTY | 15 | WAIT | agreement | 96 |
| NIFTY | 15 | WAIT | breadth | 251 |
| NIFTY | 15 | WAIT | breadth_and_agreement | 111 |
| NIFTY | 15 | WAIT | never_together | 31 |
| NIFTY | 15 | WAIT | no_break | 332 |
| NIFTY | 30 | CONFIRMED_LONG |  | 415 |
| NIFTY | 30 | CONFIRMED_SHORT |  | 538 |
| NIFTY | 30 | WAIT | agreement | 88 |
| NIFTY | 30 | WAIT | breadth | 204 |
| NIFTY | 30 | WAIT | breadth_and_agreement | 97 |
| NIFTY | 30 | WAIT | never_together | 6 |
| NIFTY | 30 | WAIT | no_break | 823 |

## Trade quality and sizing (validation years, protocol trades)

| Instrument | Variant | Trades/yr | Win rate | Avg win / loss (bps) | PF | Exp. R | Cost share | Rs 1,000-risk: risk-cap share | Rs per trade | Costs x2 val (t) |
|---|---|---|---|---|---|---|---|---|---|---|
| NIFTY | k15|E1|X1 | 152.5 | 0.434 | 54.49 / -42.96 | 0.972 | -0.004 | 0.053 | 1.0 | None | -3.2 (-1.50) |
| NIFTY | k15|E1|X2 | 152.5 | 0.32 | 60.11 / -30.41 | 0.931 | -0.059 | 0.065 | 0.998 | -961.4 | -3.9 (-2.11) |
| NIFTY | k15|E2|X1 | 82.0 | 0.144 | 64.37 / -14.26 | 0.761 | -0.366 | 0.128 | 0.693 | -262.1 | -5.4 (-3.42) |
| NIFTY | k15|E2|X2 | 82.0 | 0.122 | 66.64 / -12.77 | 0.725 | -0.401 | 0.145 | 0.589 | -279.0 | -5.6 (-3.75) |
| NIFTY | k30|E1|X1 | 109.0 | 0.454 | 51.44 / -46.66 | 0.917 | -0.013 | 0.052 | 1.0 | None | -4.6 (-1.77) |
| NIFTY | k30|E1|X2 | 109.0 | 0.349 | 55.89 / -35.16 | 0.851 | -0.07 | 0.061 | 1.0 | None | -5.9 (-2.56) |
| NIFTY | k30|E2|X1 | 54.8 | 0.134 | 67.36 / -14.95 | 0.696 | -0.246 | 0.125 | 0.751 | -214.4 | -6.5 (-3.33) |
| NIFTY | k30|E2|X2 | 54.8 | 0.103 | 74.16 / -12.6 | 0.679 | -0.243 | 0.149 | 0.568 | -105.4 | -6.2 (-3.41) |
| BANKNIFTY | k15|E1|X1 | 142.7 | 0.417 | 81.65 / -58.91 | 0.992 | 0.009 | 0.038 | 1.0 | None | -2.9 (-0.91) |
| BANKNIFTY | k15|E1|X2 | 142.7 | 0.325 | 91.67 / -43.16 | 1.022 | 0.017 | 0.045 | 0.995 | -834.6 | -2.0 (-0.68) |
| BANKNIFTY | k15|E2|X1 | 74.2 | 0.137 | 109.1 / -16.27 | 1.065 | 0.078 | 0.095 | 0.627 | -26.5 | -1.7 (-0.65) |
| BANKNIFTY | k15|E2|X2 | 74.2 | 0.11 | 109.45 / -13.97 | 0.969 | -0.05 | 0.115 | 0.501 | -100.3 | -3.0 (-1.29) |
| BANKNIFTY | k30|E1|X1 | 98.5 | 0.445 | 77.95 / -59.44 | 1.051 | 0.031 | 0.038 | 1.0 | None | -0.9 (-0.23) |
| BANKNIFTY | k30|E1|X2 | 98.5 | 0.343 | 85.87 / -43.45 | 1.034 | 0.049 | 0.045 | 0.998 | -684.0 | -1.6 (-0.48) |
| BANKNIFTY | k30|E2|X1 | 51.5 | 0.152 | 79.01 / -16.36 | 0.867 | -0.153 | 0.107 | 0.676 | -250.8 | -4.4 (-1.74) |
| BANKNIFTY | k30|E2|X2 | 51.5 | 0.139 | 82.93 / -14.35 | 0.934 | -0.151 | 0.117 | 0.576 | -258.1 | -3.4 (-1.36) |
| STOCKS | k15|E1|X1 | 2180.8 | 0.443 | 159.74 / -146.7 | 0.867 | -0.063 | 0.103 | 0.001 | -54.6 | -27.9 (-8.58) |
| STOCKS | k15|E1|X2 | 2180.8 | 0.365 | 169.88 / -113.32 | 0.86 | -0.134 | 0.123 | 0.0 | -99.6 | -26.6 (-9.77) |
| STOCKS | k15|E2|X1 | 782.2 | 0.222 | 166.0 / -63.9 | 0.741 | -0.42 | 0.209 | 0.0 | -228.9 | -31.1 (-12.61) |
| STOCKS | k15|E2|X2 | 782.2 | 0.187 | 169.43 / -55.93 | 0.697 | -0.499 | 0.243 | 0.0 | -269.0 | -31.4 (-13.66) |
| STOCKS | k30|E1|X1 | 1213.2 | 0.457 | 160.31 / -148.05 | 0.912 | -0.04 | 0.101 | 0.002 | -33.8 | -26.4 (-6.01) |
| STOCKS | k30|E1|X2 | 1213.2 | 0.375 | 171.18 / -114.62 | 0.895 | -0.101 | 0.12 | 0.0 | -70.3 | -26.1 (-7.36) |
| STOCKS | k30|E2|X1 | 478.8 | 0.227 | 160.25 / -59.35 | 0.794 | -0.335 | 0.221 | 0.0 | -178.1 | -29.4 (-12.19) |
| STOCKS | k30|E2|X2 | 478.8 | 0.186 | 167.88 / -50.78 | 0.756 | -0.412 | 0.262 | 0.0 | -211.8 | -30.0 (-13.79) |

## Data used and left out

```
{
 "stock_days_ranked": 219500,
 "no_link_or_data": 20349,
 "ca_block": 17,
 "no_rvol_base": 1307,
 "eligible": 197827,
 "breadth_days": 2175,
 "breadth_undefined_days": 20,
 "e2_failed_BASELINE_k15": 52738,
 "confirmed_BASELINE_k15": 129978,
 "e2_failed_FILTERED_k15": 6474,
 "confirmed_FILTERED_k15": 18965,
 "e2_failed_BASELINE_k30": 33052,
 "confirmed_BASELINE_k30": 83401,
 "e2_failed_FILTERED_k30": 3881,
 "confirmed_FILTERED_k30": 10645,
 "index_days_both": 2212,
 "special": 2,
 "incomplete": 7,
 "breadth_undefined": 32,
 "index_days_used": 2171,
 "e2_failed_NIFTY_BASELINE_k15": 690,
 "confirmed_NIFTY_BASELINE_k15": 1839,
 "e2_failed_NIFTY_FILTERED_k15": 418,
 "confirmed_NIFTY_FILTERED_k15": 1350,
 "e2_failed_NIFTY_BASELINE_k30": 484,
 "confirmed_NIFTY_BASELINE_k30": 1348,
 "e2_failed_NIFTY_FILTERED_k30": 320,
 "confirmed_NIFTY_FILTERED_k30": 953,
 "e2_failed_BANKNIFTY_BASELINE_k15": 724,
 "confirmed_BANKNIFTY_BASELINE_k15": 1751,
 "e2_failed_BANKNIFTY_FILTERED_k15": 471,
 "confirmed_BANKNIFTY_FILTERED_k15": 1268,
 "e2_failed_BANKNIFTY_BASELINE_k30": 520,
 "confirmed_BANKNIFTY_BASELINE_k30": 1260,
 "e2_failed_BANKNIFTY_FILTERED_k30": 334,
 "confirmed_BANKNIFTY_FILTERED_k30": 866,
 "lot_carried_dates": [
  "2021-03-30"
 ]
}
```

Strata (gap, VIX tercile, Nifty vs 50-day, event day, expiry day, era, weekday) are in `manifests/oc_v1_results.json` (report only, never tested).
