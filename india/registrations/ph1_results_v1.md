# PH1 results: the market's phase (Nifty and Bank Nifty, 2003-2023)

Registered 2026-11-05T16:11:44+00:00; k 9, bar z 2.77. Spec: `india/registrations/ph1_v1.json`.
Index rows: the signal days' mean minus all days' mean in the same quarter (t across quarters). Options-line rows: their own mean net basis points, 2018-2023 scored only (seen years).

| variant | verdict | 2003-17 (t) | 2018-23 (t) | days or trades (dev / val) |
|---|---|---|---|---|
| nifty|squeeze|abs_fwd10 | REJECTED | +0.60% (2.56) | -0.14% (-0.30) | 908 / 366 |
| nifty|squeeze|fwd10 | INCONCLUSIVE | -1.20% (-3.17) | -0.02% (-0.04) | 908 / 366 |
| nifty|trend_up|fwd20 | OPPOSITE | -1.70% (-5.25) | -0.91% (-2.38) | 2040 / 881 |
| nifty|trend_down|fwd20 | INCONCLUSIVE | +3.87% (5.68) | +3.44% (4.36) | 664 / 236 |
| nifty|range|abs_fwd10 | OPPOSITE | +0.65% (2.33) | +0.46% (1.46) | 831 / 348 |
| banknifty|squeeze|abs_fwd10 | INCONCLUSIVE | +0.56% (1.79) | +0.01% (0.03) | 833 / 331 |
| nifty|squeeze_low_vix|abs_fwd10 | INCONCLUSIVE | +0.45% (1.71) | -0.81% (-2.08) | 382 / 253 |
| options_line|after_squeeze|net_bps | NOT_SUPPORTED_SEEN | +1.53 (0.21) | +5.43 (0.98) | 146 / 487 |
| options_line|after_range|net_bps | NOT_SUPPORTED_SEEN | -3.84 (-0.18) | +3.83 (0.86) | 45 / 591 |

Share of Nifty days in each phase: trend_up 59%, trend_down 18%, range 23%, squeeze 25%
