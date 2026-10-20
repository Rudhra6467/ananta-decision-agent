# SP1 holdout: the one confirmatory run (2024-01-01 to 2026-10-16)

Frozen spec `sp1_v2.json` sha `37e918d37d0f1e3f`; approved by Madhav 19 Oct 2026 19:52; run 2026-10-20T00:09:44+00:00 through india/sealed.py (logged, single use).
687 sessions. Each test year refitted on all earlier years with the frozen rules (lambda by year-out CV, the margin c by nested CV). Family OC bar z = 3.44; confirmatory rows are one-sided at that bar.
Before scoring: the holdout path reproduced the dev/validation universe, breadth, situation table and outcomes exactly on 2023, and December 2023 again inside the run.

| Row | Holdout mean (t, days) | Verdict | Seen 2018-2023 | Per year |
|---|---|---|---|---|
| SP1H|NIFTY|future_proxy|policy | 4.08 (2.36, 687) | NOT_CONFIRMED | 3.83 (2.53) | {2024: 7.99, 2025: 2.96, 2026: 0.58} |
| SP1H|BANKNIFTY|future_proxy|policy | 4.28 (1.31, 687) | NOT_CONFIRMED | 2.71 (1.40) | {2024: 8.81, 2025: 5.21, 2026: -2.58} |
| SP1H|NIFTY|option|policy | 461.18 (2.50, 687) | NOT_CONFIRMED | 498.30 (3.49) | {2024: 7.99, 2025: 2.96, 2026: 0.58} |
| SP1H|BANKNIFTY|option|policy | 396.54 (1.71, 687) | NOT_CONFIRMED | 289.42 (2.23) | {2024: 8.81, 2025: 5.21, 2026: -2.58} |
| SP1H|BOOK|option|sized | 56.90 (1.34, 687) | NOT_CONFIRMED | – |  |

## NIFTY

- trades 322, days traded 47%
- same rules without the situation (-0.1, -0.08); single best fixed action (-0.08, -0.06); costs x2 (1.76, 1.48); Newey-West lag 5 t 2.40
- folds: [{'test_year': 2024, 'c': 2.5, 'c_intercept_only': 2.0, 'trades': 144, 'best_fixed': ['D1', 5], 'mean_daily_net': 7.99}, {'test_year': 2025, 'c': 2.5, 'c_intercept_only': 2.0, 'trades': 136, 'best_fixed': ['D1', 5], 'mean_daily_net': 2.96}, {'test_year': 2026, 'c': 2.5, 'c_intercept_only': 2.0, 'trades': 42, 'best_fixed': ['D1', 5], 'mean_daily_net': 0.58}]

## BANKNIFTY

- trades 653, days traded 95%
- same rules without the situation (0.08, 0.02); single best fixed action (-1.34, -0.8); costs x2 (1.64, 0.56); Newey-West lag 5 t 1.24
- folds: [{'test_year': 2024, 'c': 0.5, 'c_intercept_only': 0.5, 'trades': 245, 'best_fixed': ['D3', 5], 'mean_daily_net': 8.81}, {'test_year': 2025, 'c': 0.5, 'c_intercept_only': 0.5, 'trades': 247, 'best_fixed': ['D3', 5], 'mean_daily_net': 5.21}, {'test_year': 2026, 'c': 0.5, 'c_intercept_only': 0.5, 'trades': 161, 'best_fixed': ['D3', 5], 'mean_daily_net': -2.58}]

## Rs 60,000 book from 2024-01-01 (EXPLORATORY)

```
{
 "path": "paused at the 22% rule",
 "start_inr": 60000.0,
 "end_inr": 99089.0,
 "max_drawdown": -0.2142,
 "pause_date": null,
 "equity_at_year_end": {
  "2024": 89261.0,
  "2025": 97878.0,
  "2026": 99089.0
 },
 "reasons": {
  "size_zero": 852,
  "no_option": 10,
  "loss_cap": 12,
  "paused": 0,
  "daily_limit_breach": 0,
  "taken": 101
 },
 "unpaused": {
  "path": "unpaused (what would have happened without the pause)",
  "start_inr": 60000.0,
  "end_inr": 99089.0,
  "max_drawdown": -0.2142,
  "pause_date": null,
  "equity_at_year_end": {
   "2024": 89261.0,
   "2025": 97878.0,
   "2026": 99089.0
  },
  "reasons": {
   "size_zero": 852,
   "no_option": 10,
   "loss_cap": 12,
   "paused": 0,
   "daily_limit_breach": 0,
   "taken": 101
  }
 }
}
```
