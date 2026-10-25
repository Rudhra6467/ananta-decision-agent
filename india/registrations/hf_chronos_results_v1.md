# HF-CHRONOS v1 results: a Hugging Face forecaster against the coin flip and Ananta's daily call

Generated 25 Oct 2026 21:52 UTC by `python -m india.hf_chronos run`, from the spec registered before the run (`hf_chronos_v1.json`). Model amazon/chronos-bolt-small@772f3d2, zero-shot, the previous 300 closes. Research tree only: dev 2010-2017, validation 2018-2023. Bar: two-sided Bonferroni z for 10 tries (2.81), t across calendar-quarter means.

## The verdicts

| version | verdict | dev mean | dev t | val mean | val t | quarters dev/val |
|---|---|---|---|---|---|---|
| NIFTY|h1|hit | REJECTED | +0.0150 | +1.35 | +0.0188 | +1.37 | 32/24 |
| NIFTY|h5|hit | INCONCLUSIVE | +0.0533 | +2.69 | +0.0539 | +2.15 | 32/24 |
| BANKNIFTY|h1|hit | INCONCLUSIVE | +0.0244 | +2.99 | +0.0083 | +0.65 | 32/24 |
| BANKNIFTY|h5|hit | INCONCLUSIVE | +0.0375 | +1.83 | +0.0139 | +0.59 | 32/24 |
| NIFTY|h1|vs_call | REJECTED | -0.0314 | -1.35 | -0.0129 | -0.72 | 31/24 |
| NIFTY|h5|vs_call | REJECTED | +0.0009 | +0.02 | -0.0269 | -0.50 | 31/24 |
| BANKNIFTY|h1|vs_call | REJECTED | -0.0097 | -0.51 | -0.0153 | -0.60 | 32/24 |
| BANKNIFTY|h5|vs_call | REJECTED | +0.0288 | +0.84 | -0.0466 | -1.34 | 32/24 |
| NIFTY|h1|longflat_vs_hold | REJECTED | -0.0002 | -1.27 | -0.0003 | -2.14 | 32/24 |
| BANKNIFTY|h1|longflat_vs_hold | REJECTED | -0.0002 | -1.29 | -0.0002 | -1.01 | 32/24 |

Means: hit versions are the hit rate minus 50%; vs_call is Chronos's hit rate minus the daily-call rule's on the rule's call days; longflat_vs_hold is the long/flat rule's net return per session minus holding the index.

## Plain hit rates

| index | horizon | period | sessions | Chronos right | call-rule days | call rule right | Chronos right on those days | forecasts 'up' | outcomes up |
|---|---|---|---|---|---|---|---|---|---|
| NIFTY | h1 | dev | 1984 | 51.5% | 1004 | 51.6% | 49.9% | 63.6% | 52.6% |
| NIFTY | h1 | val | 1484 | 51.9% | 772 | 46.5% | 47.0% | 73.8% | 54.9% |
| NIFTY | h5 | dev | 1987 | 55.3% | 1006 | 53.0% | 53.9% | 73.7% | 56.0% |
| NIFTY | h5 | val | 1480 | 55.3% | 768 | 52.5% | 53.5% | 78.5% | 58.5% |
| BANKNIFTY | h1 | dev | 1987 | 52.4% | 1390 | 50.7% | 50.9% | 63.5% | 52.8% |
| BANKNIFTY | h1 | val | 1484 | 50.8% | 954 | 49.9% | 49.2% | 70.0% | 53.4% |
| BANKNIFTY | h5 | dev | 1987 | 53.7% | 1390 | 49.3% | 52.8% | 76.2% | 55.7% |
| BANKNIFTY | h5 | val | 1480 | 51.3% | 950 | 50.6% | 48.4% | 75.4% | 55.5% |

## Calibration (share of outcomes inside the forecast's 10%-90% band; honest is about 80%)

| index | horizon | dev | val |
|---|---|---|---|
| NIFTY | h1 | 85.7% | 83.5% |
| NIFTY | h5 | 78.8% | 76.3% |
| BANKNIFTY | h1 | 85.0% | 84.4% |
| BANKNIFTY | h5 | 78.1% | 75.9% |

## Reading

- A pass needs |t| at 2.81 in both periods with the expected sign (VALIDATED), or 2.81 in one and 1.65 in the other (CONDITIONAL).
- Against 'always up' (descriptive, not a registered row): the last column is what a forecaster that always says 'up' would score, because the indices rose on most sessions. Chronos says 'up' far more often than the market rose, so most of its edge over 50% is that upward drift, not skill: compare its 'right' column with the 'outcomes up' column.
- Chronos may have seen these indices in its pretraining, so a pass here would still need the forward record; a fail here is a fail.
- From 26 Oct 2026 Chronos writes the next session's forecast to the forecast ledger every evening (source chronos), scored beside the rule, the reviewer and the coin flip in the morning scorecard. Nothing trades on it.
