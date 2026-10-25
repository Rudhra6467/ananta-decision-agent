# HF-CHRONOS v1: a Hugging Face forecaster against the coin flip and Ananta's daily call (registered 25 Oct 2026, before any run)

Madhav asked (25 Oct): add Hugging Face where it helps Ananta, for predictions, reconstructions or comparisons.

**The question.** Chronos-Bolt is Amazon's free time-series model on Hugging Face (`amazon/chronos-bolt-small`, revision 772f3d2). It forecasts
a series from its own past. Without any fitting, does it call the direction of the Nifty 50 and Bank Nifty over the next session and the next
5 sessions better than a coin flip and better than Ananta's daily-call rule? Is its range honest, so that about 80% of outcomes land inside
its 10%-90% band?

**The data.** Daily closes 2010-2023 from the research tree only (dev 2010-2017, validation 2018-2023). Nothing from 2024 on is read.

**The method.** The model sees only the previous 300 closes at each session. That is the same window the live forecast can read (460
calendar days at most), so the backtest tests what runs forward. Ten versions are registered, each expected to come out positive:
- direction hits against 50%, for each index at 1 and 5 sessions;
- hits against the daily-call rule on the days that rule makes a call;
- for each index, a long/flat rule (long the next session when the model says up, else flat) after futures costs, against simply holding.

The bar is the registry's two-sided Bonferroni z for 10 tries (2.81), with t across calendar-quarter means. Calibration is reported, not
voted on.

**Disclosure.** Chronos was pretrained on public time series that may include these indices, so the backtest may flatter it. The forward
record is the real test: from 26 Oct, every evening it writes the next session's forecast to the forecast ledger before the open, scored beside
the rule, the reviewer and the coin flip. Nothing trades on it.

Spec: `hf_chronos_v1.json`. Code: `india/hf_chronos.py`.
