# SP1 results: index intraday playbook (Scenario Playbook phase 1)

Spec `sp1_v2.json` sha `37e918d37d0f1e3f` (frozen before any result; reviewed twice independently). Run 2026-10-19T23:45:38+00:00.
**SEEN-period evidence**: 2017-2023 shaped this design through OC v1, so these rows use the seen_val_only rule (verdict on 2018-2023 at the family z = 3.42; 2017 reported). The only confirmatory test is the registered 2024-2026 holdout run.

Unit: net basis points of the index per day (0 on no-trade days), after dated futures costs; option rows in bps of premium per day (EXPLORATORY, synthetic prices); the book in rupees.

| Row | 2017 (t, days) | 2018-2023 (t, days) | Verdict |
|---|---|---|---|
| NIFTY|future_proxy|policy | -1.56 (-0.61, 246) | 3.83 (2.53, 1476) | NOT_SUPPORTED_SEEN |
| NIFTY|future_proxy|vs_intercept_only | -1.07 (-1.05, 246) | 2.56 (1.58, 1476) | NOT_SUPPORTED_SEEN |
| NIFTY|option|policy | 76.05 (0.28, 246) | 498.30 (3.49, 1476) | SUPPORTED_SEEN |
| BANKNIFTY|future_proxy|policy | -3.59 (-1.07, 246) | 2.71 (1.40, 1476) | NOT_SUPPORTED_SEEN |
| BANKNIFTY|future_proxy|vs_intercept_only | -1.87 (-0.86, 246) | 2.27 (1.05, 1476) | NOT_SUPPORTED_SEEN |
| BANKNIFTY|option|policy | 70.97 (0.17, 246) | 289.42 (2.23, 1476) | NOT_SUPPORTED_SEEN |
| BOOK|option|sized | -17.56 (-0.28, 246) | 0.00 (–, 1476) | INCONCLUSIVE |

## Per index

### NIFTY

- validation trades 1195 (days traded 81%); per year {2017: -1.56, 2018: 5.58, 2019: 0.79, 2020: 6.37, 2021: 9.81, 2022: 5.65, 2023: -5.32}; positive folds 5/7; eras {'2017-2019': 1.6, '2020': 6.37, '2021-2023': 3.39}
- benchmarks 2018-2023 (mean, t, days): intercept-only (1.27, 0.73), best fixed of training (1.69, 1.38), costs x2 (2.24, 1.75), Newey-West lag 5 t 2.76
- state-shuffle null: p = 0.005; the null policies made 1203.415 trades on average in 2018-2023
- most chosen: {'D1|ORSTOP|short': 634, 'D0|ATRSTOP|short': 354, 'D2|ORSTOP|short': 68, 'D1|ATRSTOP|short': 67, 'D3|NEXTOPEN|long': 63, 'D1|TRAIL|long': 54, 'D2|TRAIL|long': 36, 'D2|NEXTOPEN|long': 36}

### BANKNIFTY

- validation trades 889 (days traded 60%); per year {2017: -3.59, 2018: 0.44, 2019: -1.24, 2020: 10.19, 2021: 1.68, 2022: 7.29, 2023: -2.3}; positive folds 4/7; eras {'2017-2019': -1.47, '2020': 10.19, '2021-2023': 2.23}
- benchmarks 2018-2023 (mean, t, days): intercept-only (0.43, 0.26), best fixed of training (2.26, 1.43), costs x2 (-0.28, -0.2), Newey-West lag 5 t 1.53
- state-shuffle null: p = 0.125; the null policies made 681.14 trades on average in 2018-2023
- most chosen: {'D1|ORSTOP|short': 192, 'D0|ATRSTOP|short': 156, 'D0|NEXTOPEN|long': 129, 'D1|ATRSTOP|short': 123, 'D1|TRAIL|long': 120, 'D1|TRAIL|short': 91, 'D1|NEXTOPEN|long': 65, 'D2|ORSTOP|short': 55}

## The Rs 60,000 book (EXPLORATORY)

```
{
 "path": "paused at the 22% rule",
 "start_inr": 60000.0,
 "end_inr": 55681.0,
 "max_drawdown": -0.24,
 "pause_date": "2017-04-26",
 "equity_at_year_end": {
  "2017": 55681.0,
  "2018": 55681.0,
  "2019": 55681.0,
  "2020": 55681.0,
  "2021": 55681.0,
  "2022": 55681.0,
  "2023": 55681.0
 },
 "reasons": {
  "size_zero": 90,
  "no_option": 0,
  "loss_cap": 15,
  "paused": 2411,
  "daily_limit_breach": 0,
  "taken": 44
 },
 "unpaused": {
  "path": "unpaused (what would have happened without the pause)",
  "start_inr": 60000.0,
  "end_inr": 4580760.0,
  "max_drawdown": -0.5857,
  "pause_date": "2017-04-26",
  "equity_at_year_end": {
   "2017": 78854.0,
   "2018": 168524.0,
   "2019": 341683.0,
   "2020": 2134099.0,
   "2021": 4942013.0,
   "2022": 8343455.0,
   "2023": 4580760.0
  },
  "reasons": {
   "size_zero": 439,
   "no_option": 16,
   "loss_cap": 188,
   "paused": 0,
   "daily_limit_breach": 0,
   "taken": 1917
  }
 }
}
```

## What the last fold learned (trained 2015-2022, mean predicted net over 2023 days)

```
{
 "NIFTY": [
  {
   "point": "D1",
   "action": "ORSTOP|short",
   "mean_pred_net_bps": 6.89
  },
  {
   "point": "D3",
   "action": "ORSTOP|short",
   "mean_pred_net_bps": 6.05
  },
  {
   "point": "D2",
   "action": "ORSTOP|short",
   "mean_pred_net_bps": 5.31
  },
  {
   "point": "D1",
   "action": "ATRSTOP|short",
   "mean_pred_net_bps": 3.98
  },
  {
   "point": "D0",
   "action": "ATRSTOP|short",
   "mean_pred_net_bps": 3.69
  },
  {
   "point": "D2",
   "action": "ATRSTOP|short",
   "mean_pred_net_bps": 3.65
  }
 ],
 "BANKNIFTY": [
  {
   "point": "D3",
   "action": "ORSTOP|short",
   "mean_pred_net_bps": 6.48
  },
  {
   "point": "D1",
   "action": "ORSTOP|short",
   "mean_pred_net_bps": 4.65
  },
  {
   "point": "D1",
   "action": "TRAIL|short",
   "mean_pred_net_bps": 4.39
  },
  {
   "point": "D1",
   "action": "ATRSTOP|short",
   "mean_pred_net_bps": 3.6
  },
  {
   "point": "D2",
   "action": "ORSTOP|short",
   "mean_pred_net_bps": 3.45
  },
  {
   "point": "D3",
   "action": "ATRSTOP|short",
   "mean_pred_net_bps": 2.98
  }
 ]
}
```

## Folds

```
[
 {
  "index": "NIFTY",
  "test_year": 2017,
  "c": 1.0,
  "c_intercept_only": 1.5,
  "trades": 246,
  "best_fixed": [
   "D1",
   5
  ],
  "lambda_median": 300.0
 },
 {
  "index": "NIFTY",
  "test_year": 2018,
  "c": 2.0,
  "c_intercept_only": 1.5,
  "trades": 162,
  "best_fixed": [
   "D1",
   5
  ],
  "lambda_median": 1000.0
 },
 {
  "index": "NIFTY",
  "test_year": 2019,
  "c": 2.5,
  "c_intercept_only": 2.0,
  "trades": 174,
  "best_fixed": [
   "D1",
   5
  ],
  "lambda_median": 1000.0
 },
 {
  "index": "NIFTY",
  "test_year": 2020,
  "c": 1.5,
  "c_intercept_only": 1.5,
  "trades": 227,
  "best_fixed": [
   "D1",
   5
  ],
  "lambda_median": 1000.0
 },
 {
  "index": "NIFTY",
  "test_year": 2021,
  "c": 2.0,
  "c_intercept_only": 1.5,
  "trades": 189,
  "best_fixed": [
   "D1",
   5
  ],
  "lambda_median": 1000.0
 },
 {
  "index": "NIFTY",
  "test_year": 2022,
  "c": 2.0,
  "c_intercept_only": 1.5,
  "trades": 227,
  "best_fixed": [
   "D1",
   5
  ],
  "lambda_median": 1000.0
 },
 {
  "index": "NIFTY",
  "test_year": 2023,
  "c": 2.0,
  "c_intercept_only": 1.5,
  "trades": 216,
  "best_fixed": [
   "D1",
   5
  ],
  "lambda_median": 1000.0
 },
 {
  "index": "BANKNIFTY",
  "test_year": 2017,
  "c": 1.5,
  "c_intercept_only": 1.5,
  "trades": 230,
  "best_fixed": [
   "D1",
   5
  ],
  "lambda_median": 1000.0
 },
 {
  "index": "BANKNIFTY",
  "test_year": 2018,
  "c": 2.5,
  "c_intercept_only": 1.0,
  "trades": 39,
  "best_fixed": [
   "D1",
   5
  ],
  "lambda_median": 1000.0
 },
 {
  "index": "BANKNIFTY",
  "test_year": 2019,
  "c": 2.5,
  "c_intercept_only": 2.5,
  "trades": 31,
  "best_fixed": [
   "D1",
   5
  ],
  "lambda_median": 1000.0
 },
 {
  "index": "BANKNIFTY",
  "test_year": 2020,
  "c": 2.0,
  "c_intercept_only": 2.0,
  "trades": 168,
  "best_fixed": [
   "D3",
   5
  ],
  "lambda_median": 1000.0
 },
 {
  "index": "BANKNIFTY",
  "test_year": 2021,
  "c": 2.0,
  "c_intercept_only": 1.5,
  "trades": 186,
  "best_fixed": [
   "D3",
   5
  ],
  "lambda_median": 1000.0
 },
 {
  "index": "BANKNIFTY",
  "test_year": 2022,
  "c": 2.0,
  "c_intercept_only": 1.5,
  "trades": 220,
  "best_fixed": [
   "D3",
   5
  ],
  "lambda_median": 1000.0
 },
 {
  "index": "BANKNIFTY",
  "test_year": 2023,
  "c": 0.5,
  "c_intercept_only": 1.5,
  "trades": 245,
  "best_fixed": [
   "D3",
   5
  ],
  "lambda_median": 1000.0
 }
]
```
