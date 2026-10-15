# Repair-shop review #29 results: H07 on a point-in-time tier A, both dial states

Run 2026-10-15 on the pre-registration in `REVIEW_29.md` (approved by Madhav 06:33 Toronto; sha256 c7b52bb8...; the code refuses
to run if it changed). Results file: `docs/research/review29.json`. Code: `src/research/review29.py` (commits 77083dc and 6fc4245,
both before the run).

## Verdict
- **Primary cell, H07 on tier A with the dial CLOSED: PASS.** Expected excess +6.3% a trade over random (pooled over both
  periods, shrunk by n/(n+50)), up from review #26's +5.1%.
- **Secondary cell, the dial OPEN: INSUFFICIENT** (17 market days in 2018-2023, under 30). Nothing changes: still no measured edge
  with the dial open.
- **Madhav's decision on the two coverage-counting fixes (Oct 15, 08:32 Toronto): "1. keep".** The result and its effects stand.

## Data and the coverage gate
- Point-in-time tier A from all 530 eligible Binance USDT pairs (rule v1's list), not the lake's 120: a coin is tier A on a day when
  its median traded value over the previous 30 complete days is at least $20M. Coins that died stay in for the days they traded.
- The registration's download step: the 76 coins that were ever tier A (2018-01 to 2026-07) and had no daily candles were
  downloaded from Binance Data Vision with checksums, then built and quality-checked as in review #22. Download errors: 0. Grades:
  65 A, 7 B, 4 C.
- Coverage, the stop rule: every month from 2018-01 to 2026-07 had at least 99% of tier A's traded value in coins with clean,
  swap-checked daily candles. The lowest month was 99.17%; 418 coins were tier A at some point.
- How the gate got there. Every change below was made before any trade was simulated, and each is written in the code.
  - Pass 1: each coin-month was weighted by its complete days, so one exchange-wide maintenance day failed whole months. Changed
    to a per-coin rule: a coin-month counts when 90% of its trading days are complete.
  - Pass 3: a daily 10x token-swap rule had also been applied to coins that already have minute-level checks, and it flagged
    LUNA's real collapse. Changed so coins with minute data use the minute check, and only daily-only coins use the daily rule.
  - Pass 4, after the download: two months fell short, both from how the code counted.
    - LUNA 2.0 is the new token on the re-used ticker LUNAUSDT from 2022-05-31, and it was tier A in Sep 2022. It is now its own
      coin, checked on its own rows: 1,523 complete days, no suspect.
    - ARB's partial listing-day candle (94.4% of the minutes) no longer counts against March 2023.
  - Pass 5: the gate passed.
- 472 coins were loaded (at least 240 complete days each). Five were left out because they have an unchecked token swap: DEGO, SUN,
  OOKI, DREP and QUICK.
- Costs: each coin's live Universe Rule v2 cost; a coin that no longer trades pays Kraken's 0.40% fee plus twice its tier floor.
  Terra classic pays LUNC's live cost and LUNA 2.0 pays LUNA's. The stress run doubles every cost.
- The holdout (2026-08-01 to 2026-12-14) was not loaded.

## Results
Excess is a trade's net return minus the mean of random tier-A entries held 10 days, in the same dial state and period, at the
same costs. The paired twin is a random tier-A coin entered the same day with the same exit; it is reported only.

| Cell | Period | Trades | Market days | Mean net | Random | Excess | z | Net at 2x cost | Excess without the 2 largest bursts | Paired twin |
|---|---|---|---|---|---|---|---|---|---|---|
| CLOSED | 2018-2023 | 173 | 66 | +6.45% | -3.93% | +10.38% | 4.85 | +4.78% | +4.85% | +3.50% (z 2.98) |
| CLOSED | 2024-Jul 2026 | 94 | 49 | +5.27% | -1.47% | +6.75% | 5.54 | +3.96% | +5.21% | +1.90% (z 1.65) |
| OPEN | 2018-2023 | 22 | 17 | +3.17% | +2.62% | +0.56% | 0.25 | +1.61% | +3.44% | +1.57% (z 0.80) |
| OPEN | 2024-Jul 2026 | 74 | 29 | +1.55% | -4.24% | +5.78% | 3.34 | +0.21% | +6.25% | +0.39% (z 0.27) |

The primary cell's frozen pass marks, each met:
- 2018-2023: at least 30 market days (66); excess above 0 with z of at least 2.5 (z 4.85); net above 0.
- 2024-Jul 2026: excess above 0 with z of at least 2.0 (z 5.54); net above 0.
- Net stays above 0 at double cost in both periods (+4.78%, +3.96%).
- Excess stays above 0 without the two largest bursts in both periods (+4.85%, +5.21%).

## What it means
- The one measured edge survives both gaps the audit raised. Coins that were big and then died are now in (point-in-time, all
  530 pairs), and costs are each coin's live cost. On this wider, harder test the edge came out a little larger than review #26
  found on the 120 coins.
- The random baseline in this cell is negative: with the dial closed, a random tier-A coin held 10 days lost 3.9% (2018-2023)
  and 1.5% (2024-2026) a trade. H07's own trades made +6.5% and +5.3% net. The edge is real return, not just losing less.
- Against its paired twin H07 is ahead in both periods, but the gap is weaker in 2024-2026 (z 1.65).
- With the dial open there is still no measured edge. 2018-2023 has too few market days (17) to judge. In 2024-2026 the excess
  is positive, but the net return is near zero at double cost.

## What changed (decided in the registration)
- `jarvis/service/ev.py`: the H07 / CLOSED / tier A value is now +6.34%, review #29's pooled excess shrunk. It was +5.13% from
  review #26. The brain's expected-value pack and the measured-edge table read this value.
- H07's knowledge line (`brain.KNOWLEDGE`), its status card and its strategy-status entry now cite #29.
- The $500 book's edge sleeve stays as built.
- The holdout stays sealed. It opens once, after the 60-day evidence window and only with Madhav's OK, with the criteria
  unchanged.

## Reproduce
`cd ~/code/ananta-agent-research && ~/ananta_venvs/lake/bin/python -m src.research.review29 coverage`, then
`~/ananta_venvs/lake/bin/python -m src.research.review29`. The seed is 29, and the run writes `docs/research/review29.json`.

## Erratum (2026-10-15, research audit)

- "The holdout stays sealed" (under "What changed") means that no lake review loaded the window from 2026-08-01. It is not fresh: Candidate v3 spent 2026-08-01 to 2026-09-12 once on the lab 10 (`CANDIDATE_V3_HOLDOUT_RESULT.md`), and live paper has run on these coins since 2026-09-29 (H07 since 2026-10-09). The next holdout is live data after a stated date, written in the pre-registration (`RESEARCH_RULES.md`, section 4).
