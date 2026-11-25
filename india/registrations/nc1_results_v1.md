# NC1 results: after news, does a confirmed move continue or fade? (research years, before costs)

Frozen design: `nc1_v1.json`. Code: `india/newskinds.py`, `india/nc1.py`, `india/nc1_run.py`. Ledger study NC1, family news_confirm, bar z 3.55. Generated 2026-11-25T17:36:27+00:00.

## In plain words

**1. Most big moves come without the company's own news.**
- In 2021-2023, about 1 in 5 of each day's 25 biggest gainers and losers had a company filing that day: 20% of gainers and 22% of losers, against 17% of all stock-days.
- The other four in five moved on market, sector or media news, or on no visible news at all.
- Older years have thinner filing records: 6-8% of stock-days carry any filing in 2010-2014, against 15-19% in 2019-2023. So some "no news" days in the early years had news we cannot see.

**2. Which kinds of news move a stock most often.**

| Kind of news | Overnight (2%+ jump at the open) | In session (1%+ move within 15 minutes) | Notes |
|---|---|---|---|
| No news (the baseline) | 5% | 5% | |
| Results | 35% | 44% | most often of all |
| Order wins | 31% | 27% | 84-94% of these big moves were upward |
| USFDA warning letters | 38% | 48% | only 58 and 46 cases |
| Dividends, bonus issues and splits | 29% | 22% | mostly on results days |
| Senior exits, equity raising, buybacks, USFDA approvals | 12-16% | | |
| Analyst meetings | 7% | 3% | hardly move anything |

- **Which way each kind pushes**, by the lift (how much more often a kind comes with a big mover than with an average stock-day):
  - Senior exits come with falls: 2.7x among losers.
  - USFDA warnings come with falls: 5.8x among losers, from few cases.
  - Order wins come with gains: 2.2x among gainers.
  - Results go both ways, 2.4x among gainers and 3.6x among losers: bad results are punished more often than good ones are rewarded.

**3. After the move is confirmed, does it keep going? On average, no: it gives some back. News moves give back less.**
- **Overnight:**
  - A 2%+ opening jump with no news gave back about 1.8% by the close (2018-2023: about 1.0-1.3%).
  - With news, it gave back about 0.8%; with results, 0.5%.
  - "News holds better than no news" passed the strict bar (VALIDATED) for all news, results and dividends.
  - Even with news, though, the jumps still faded on average: OPPOSITE in both periods for all news, results, order wins, promoter and insider disclosures, and new plants.
- **Bad news sticks better than good news:** down-jumps with news gave back about 0.3-0.5%; up-jumps with news gave back about 0.8-1.0%.
- **Over five sessions:** results jumps held (+0.1%). Order-win (-0.9%), new-plant (-2.6%) and buyback (-1.6%) jumps kept giving back.
- **In session, 15 minutes after the news:**
  - A no-news 1% move gave back 0.3% by the close.
  - News moves roughly held: -0.1% for all news, +0.1% for results.
  - "News holds better" passed the bar in the look years and almost passed in the check years (CONDITIONAL).
- **The rare kinds** (USFDA, ratings, pledges, fires) have too few cases for a verdict: INCONCLUSIVE.

**4. What this means for Ananta.**
- A confirmed move with real news, above all results, is more trustworthy than one without. A big jump with no news is the most likely to fade.
- "Confirmed" does not mean "it will keep going": on average, part of an opening jump comes back by the close.
- Ananta uses this to explain moves (the kind of news behind each big mover, every morning), never to trade. A rule from it would need its own forward test against random, and Madhav's yes.
- The moves here are before costs (about 0.3-0.5% for a round trip). A stock that has just jumped is also hard to buy or sell at its opening price.

**The verdicts, by the strict bar (z 3.55):**
- VALIDATED: A|results|edge, A|dividend_bonus_split|edge, A|all_news|edge.
- CONDITIONAL: B|results|edge, B|all_news|edge.
- OPPOSITE in both periods, meaning the move faded: A|all_news|cont (t -8.2 and -10.1), A|results|cont (-5.2 and -2.9), A|holding_change|cont (-4.7 and -2.3), A|order_win|cont (-2.7 and -3.2), A|operations_up|cont (-3.0 and -2.2). The other OPPOSITE rows are significant in the look years only.

**How this run went:** the first attempt, at 12:30 Toronto, was stopped at 12:35 before any outcome was computed. Its joins were spilling to disk (76 GB; the disk fell to 13 GB free). The code was rewritten to one pass, with a capped temp folder (records 6bb9f6b), and the design was not changed.

## 1. How often each kind of news moves a stock

Part A: overnight news (made public after the 15:30 close or before 09:00), top-500 stocks 2010-2023. A confirmed move is an open at least 2% from the previous close, beyond the Nifty's own gap.

| kind | stock-days | confirmed share | median gap | confirmed | of them up | then to the close | then 5 sessions |
|---|---|---|---|---|---|---|---|
| no news that day | 1,479,323 | +4.7% | +0.41% | 70,266 | - | -1.83% | -1.54% |
| results | 14,287 | +34.9% | +1.28% | 4,981 | +54% | -0.46% | +0.11% |
| order_win | 510 | +31.4% | +1.30% | 160 | +94% | -0.87% | -0.92% |
| usfda_adverse | 58 | +37.9% | +1.44% | 22 | +59% | -0.83% | -2.13% |
| usfda_approval | 210 | +13.3% | +0.72% | 28 | +86% | -1.32% | +0.12% |
| rating_down | 67 | +9.0% | +0.53% | 6 | +17% | -4.53% | -0.87% |
| rating_up | 194 | +6.2% | +0.44% | 12 | +67% | +0.17% | -0.54% |
| fund_raising | 1,508 | +13.3% | +0.56% | 200 | +68% | -0.98% | -1.09% |
| merger_acquisition | 5,367 | +10.9% | +0.53% | 583 | +69% | -0.86% | -0.78% |
| holding_change | 8,114 | +6.4% | +0.46% | 522 | +58% | -1.64% | -0.39% |
| management_exit | 571 | +15.9% | +0.60% | 91 | +32% | -1.08% | -0.54% |
| pledge_default | 709 | +11.3% | +0.48% | 80 | +42% | -1.75% | -0.12% |
| regulatory_legal | 1,161 | +11.4% | +0.50% | 132 | +49% | -0.79% | -0.40% |
| buyback | 886 | +13.2% | +0.50% | 117 | +70% | -0.71% | -1.56% |
| dividend_bonus_split | 5,331 | +29.3% | +1.05% | 1,563 | +60% | -0.59% | -0.07% |
| operations_up | 1,806 | +10.0% | +0.51% | 180 | +84% | -1.49% | -2.60% |
| disruption | 553 | +10.7% | +0.44% | 59 | +49% | -0.68% | -0.85% |
| analyst_meet | 31,952 | +7.1% | +0.39% | 2,259 | +55% | -0.48% | +0.15% |
| all_news | 119,415 | +9.8% | +0.45% | 11,752 | +60% | -0.78% | -0.35% |

Part B: news in session (09:20-15:00), stocks with 5-minute bars 2015-2023. A confirmed move is at least 1% beyond the Nifty in the 15 minutes after the news. 'Then to the close' is the further move in the same direction (a minus means it faded).

| kind | events | confirmed share | median 15-minute move | confirmed | of them up | then to the close |
|---|---|---|---|---|---|---|
| no news that day (every 15 minutes) | 21,781,600 | +4.8% | - | 1,038,473 | - | -0.30% |
| results | 5,466 | +44.3% | +0.79% | 2,421 | +49% | +0.08% |
| order_win | 630 | +27.3% | +0.47% | 172 | +84% | -0.35% |
| usfda_adverse | 46 | +47.8% | +0.76% | 22 | +45% | +0.71% |
| usfda_approval | 452 | +12.8% | +0.33% | 58 | +83% | -0.21% |
| rating_down | 18 | +5.6% | +0.17% | 1 | +100% | -0.21% |
| rating_up | 88 | +8.0% | +0.19% | 7 | +57% | -0.30% |
| fund_raising | 394 | +13.7% | +0.25% | 54 | +59% | -0.21% |
| merger_acquisition | 1,340 | +12.2% | +0.24% | 163 | +73% | +0.10% |
| holding_change | 2,932 | +4.8% | +0.18% | 140 | +54% | -0.40% |
| management_exit | 110 | +11.8% | +0.25% | 13 | +46% | +0.43% |
| pledge_default | 234 | +6.4% | +0.21% | 15 | +40% | -1.32% |
| regulatory_legal | 322 | +9.9% | +0.23% | 32 | +62% | +0.42% |
| buyback | 254 | +7.5% | +0.16% | 19 | +74% | -1.26% |
| dividend_bonus_split | 1,109 | +22.4% | +0.33% | 248 | +52% | -0.10% |
| operations_up | 1,524 | +8.1% | +0.19% | 123 | +80% | -0.32% |
| disruption | 228 | +7.9% | +0.22% | 18 | +56% | +0.47% |
| analyst_meet | 17,542 | +3.0% | +0.16% | 520 | +56% | -0.04% |
| all_news | 60,413 | +11.2% | +0.20% | 6,756 | +58% | -0.11% |

## 2. What comes with the day's biggest gainers and losers

Each session's 25 biggest gainers and 25 biggest losers among the top 500 (3,347 sessions). Any news that day: +15% of gainers and +16% of losers, against +12% of all stock-days. Lift = how many times more often the kind comes with a big mover than with an average stock-day.

| kind | all stock-days | gainers | losers | lift, gainers | lift, losers |
|---|---|---|---|---|---|
| results | +1.49% | +3.52% | +5.34% | 2.4x | 3.6x |
| order_win | +0.09% | +0.20% | +0.06% | 2.2x | 0.7x |
| dividend_bonus_split | +0.54% | +1.21% | +1.53% | 2.2x | 2.8x |
| fund_raising | +0.14% | +0.24% | +0.24% | 1.7x | 1.6x |
| rating_down | +0.01% | +0.01% | +0.01% | 1.5x | 1.3x |
| rating_up | +0.02% | +0.03% | +0.02% | 1.5x | 1.0x |
| usfda_approval | +0.05% | +0.07% | +0.03% | 1.5x | 0.6x |
| merger_acquisition | +0.52% | +0.73% | +0.68% | 1.4x | 1.3x |
| management_exit | +0.05% | +0.06% | +0.14% | 1.3x | 2.7x |
| regulatory_legal | +0.12% | +0.15% | +0.19% | 1.2x | 1.6x |
| analyst_meet | +2.98% | +3.42% | +3.75% | 1.1x | 1.3x |
| operations_up | +0.25% | +0.28% | +0.19% | 1.1x | 0.8x |
| pledge_default | +0.06% | +0.07% | +0.13% | 1.1x | 2.1x |
| buyback | +0.08% | +0.09% | +0.13% | 1.1x | 1.6x |
| holding_change | +0.89% | +0.98% | +1.03% | 1.1x | 1.2x |
| usfda_adverse | +0.01% | +0.01% | +0.04% | 1.1x | 5.8x |
| disruption | +0.06% | +0.06% | +0.07% | 1.0x | 1.2x |

## 3. The registered rows (72): continue (cont) and better than a no-news move (edge)

cont = the move from the confirmation to the close, in the confirmed direction, beyond the Nifty (quarter means). edge = cont minus the no-news move of the same direction (A: same quarter; B: same quarter and time of day). Expect +1 for both. Verdicts by the registry's standard rule.

| row | dev mean | dev t | dev quarters | val mean | val t | val quarters | confirmed events | verdict |
|---|---|---|---|---|---|---|---|---|
| A|results|cont | -0.684% | -5.17 | 30 | -0.319% | -2.93 | 24 | 4,981 | OPPOSITE |
| A|results|edge | +1.275% | +9.09 | 30 | +0.634% | +4.75 | 24 | 4,981 | VALIDATED |
| A|order_win|cont | -0.816% | -2.68 | 27 | -0.807% | -3.20 | 24 | 160 | OPPOSITE |
| A|order_win|edge | +0.955% | +3.66 | 27 | +0.088% | +0.34 | 24 | 160 | INCONCLUSIVE |
| A|usfda_adverse|cont | -0.131% | -0.10 | 9 | -1.499% | -1.95 | 4 | 22 | INCONCLUSIVE |
| A|usfda_adverse|edge | +1.195% | +0.91 | 9 | -0.580% | -1.00 | 4 | 22 | INCONCLUSIVE |
| A|usfda_approval|cont | -1.542% | -0.69 | 10 | -1.261% | -1.26 | 8 | 28 | INCONCLUSIVE |
| A|usfda_approval|edge | +0.110% | +0.05 | 10 | -0.312% | -0.30 | 8 | 28 | INCONCLUSIVE |
| A|rating_down|cont | -1.195% | -1.79 | 3 | -7.863% | -1.85 | 3 | 6 | INCONCLUSIVE |
| A|rating_down|edge | +0.943% | +1.21 | 3 | -6.958% | -1.71 | 3 | 6 | INCONCLUSIVE |
| A|rating_up|cont | +0.400% | +0.25 | 4 | -0.564% | -0.89 | 5 | 12 | INCONCLUSIVE |
| A|rating_up|edge | +2.129% | +1.66 | 4 | +0.134% | +0.20 | 5 | 12 | INCONCLUSIVE |
| A|fund_raising|cont | -1.665% | -2.59 | 25 | -0.184% | -0.25 | 23 | 200 | OPPOSITE |
| A|fund_raising|edge | +0.249% | +0.39 | 25 | +0.723% | +0.99 | 23 | 200 | REJECTED |
| A|merger_acquisition|cont | -1.451% | -3.56 | 31 | -0.408% | -1.72 | 24 | 583 | OPPOSITE |
| A|merger_acquisition|edge | +0.480% | +1.40 | 31 | +0.506% | +1.92 | 24 | 583 | REJECTED |
| A|holding_change|cont | -2.651% | -4.69 | 29 | -1.180% | -2.25 | 21 | 522 | OPPOSITE |
| A|holding_change|edge | -0.641% | -1.19 | 29 | -0.276% | -0.53 | 21 | 522 | REJECTED |
| A|management_exit|cont | -0.454% | -0.46 | 21 | -1.658% | -2.23 | 22 | 91 | REJECTED |
| A|management_exit|edge | +1.529% | +1.57 | 21 | -0.658% | -0.88 | 22 | 91 | REJECTED |
| A|pledge_default|cont | -3.861% | -1.51 | 9 | -0.852% | -1.34 | 17 | 80 | INCONCLUSIVE |
| A|pledge_default|edge | -1.754% | -0.68 | 9 | +0.202% | +0.31 | 17 | 80 | INCONCLUSIVE |
| A|regulatory_legal|cont | -1.282% | -1.89 | 26 | -0.232% | -0.45 | 23 | 132 | OPPOSITE |
| A|regulatory_legal|edge | +0.631% | +0.93 | 26 | +0.739% | +1.47 | 23 | 132 | REJECTED |
| A|buyback|cont | -1.077% | -1.82 | 24 | -0.630% | -1.21 | 21 | 117 | OPPOSITE |
| A|buyback|edge | +0.879% | +1.40 | 24 | +0.312% | +0.63 | 21 | 117 | REJECTED |
| A|dividend_bonus_split|cont | -0.928% | -3.84 | 30 | -0.225% | -1.19 | 24 | 1,563 | OPPOSITE |
| A|dividend_bonus_split|edge | +0.984% | +4.79 | 30 | +0.717% | +3.57 | 24 | 1,563 | VALIDATED |
| A|operations_up|cont | -1.811% | -3.03 | 29 | -1.310% | -2.18 | 23 | 180 | OPPOSITE |
| A|operations_up|edge | -0.001% | -0.00 | 29 | -0.383% | -0.65 | 23 | 180 | REJECTED |
| A|disruption|cont | -1.014% | -1.38 | 12 | -0.499% | -0.96 | 17 | 59 | INCONCLUSIVE |
| A|disruption|edge | +0.934% | +1.09 | 12 | +0.409% | +0.78 | 17 | 59 | INCONCLUSIVE |
| A|analyst_meet|cont | -0.708% | -3.01 | 6 | -0.485% | -4.30 | 24 | 2,259 | INCONCLUSIVE |
| A|analyst_meet|edge | +0.401% | +1.63 | 6 | +0.461% | +4.08 | 24 | 2,259 | INCONCLUSIVE |
| A|all_news|cont | -1.163% | -8.24 | 31 | -0.595% | -10.06 | 24 | 11,752 | OPPOSITE |
| A|all_news|edge | +0.792% | +10.55 | 31 | +0.347% | +5.00 | 24 | 11,752 | VALIDATED |
| B|results|cont | +0.154% | +1.69 | 16 | +0.073% | +0.71 | 20 | 2,421 | INCONCLUSIVE |
| B|results|edge | +0.495% | +5.23 | 16 | +0.329% | +3.13 | 20 | 2,421 | CONDITIONAL |
| B|order_win|cont | -0.427% | -1.29 | 15 | -0.332% | -1.13 | 19 | 172 | INCONCLUSIVE |
| B|order_win|edge | -0.019% | -0.06 | 15 | -0.088% | -0.31 | 19 | 172 | INCONCLUSIVE |
| B|usfda_adverse|cont | +1.294% | +1.70 | 10 | +0.430% | +0.54 | 7 | 22 | INCONCLUSIVE |
| B|usfda_adverse|edge | +1.587% | +2.08 | 10 | +0.730% | +0.89 | 7 | 22 | INCONCLUSIVE |
| B|usfda_approval|cont | -0.117% | -0.61 | 13 | -0.351% | -1.28 | 14 | 58 | INCONCLUSIVE |
| B|usfda_approval|edge | +0.262% | +1.21 | 13 | -0.092% | -0.33 | 14 | 58 | INCONCLUSIVE |
| B|rating_down|cont | - | +nan | 0 | - | +nan | 1 | 1 | INCONCLUSIVE |
| B|rating_down|edge | - | +nan | 0 | - | +nan | 1 | 1 | INCONCLUSIVE |
| B|rating_up|cont | - | +nan | 2 | -0.228% | -0.39 | 5 | 7 | INCONCLUSIVE |
| B|rating_up|edge | - | +nan | 2 | +0.073% | +0.14 | 5 | 7 | INCONCLUSIVE |
| B|fund_raising|cont | -0.563% | -0.84 | 11 | -0.218% | -0.58 | 15 | 54 | INCONCLUSIVE |
| B|fund_raising|edge | -0.141% | -0.22 | 11 | +0.003% | +0.01 | 15 | 54 | INCONCLUSIVE |
| B|merger_acquisition|cont | -0.127% | -0.56 | 16 | +0.067% | +0.18 | 20 | 163 | REJECTED |
| B|merger_acquisition|edge | +0.232% | +1.05 | 16 | +0.321% | +0.88 | 20 | 163 | REJECTED |
| B|holding_change|cont | -0.937% | -1.13 | 10 | -0.932% | -1.51 | 16 | 140 | INCONCLUSIVE |
| B|holding_change|edge | -0.583% | -0.69 | 10 | -0.687% | -1.12 | 16 | 140 | INCONCLUSIVE |
| B|management_exit|cont | +0.590% | +0.97 | 5 | -0.427% | -1.13 | 5 | 13 | INCONCLUSIVE |
| B|management_exit|edge | +0.889% | +1.48 | 5 | -0.157% | -0.43 | 5 | 13 | INCONCLUSIVE |
| B|pledge_default|cont | - | +nan | 2 | +0.089% | +0.09 | 11 | 15 | INCONCLUSIVE |
| B|pledge_default|edge | - | +nan | 2 | +0.353% | +0.38 | 11 | 15 | INCONCLUSIVE |
| B|regulatory_legal|cont | -0.333% | -0.37 | 8 | +0.848% | +1.33 | 10 | 32 | INCONCLUSIVE |
| B|regulatory_legal|edge | +0.042% | +0.04 | 8 | +1.061% | +1.62 | 10 | 32 | INCONCLUSIVE |
| B|buyback|cont | -1.867% | -2.14 | 6 | -1.270% | -1.99 | 7 | 19 | INCONCLUSIVE |
| B|buyback|edge | -1.547% | -1.82 | 6 | -1.084% | -1.73 | 7 | 19 | INCONCLUSIVE |
| B|dividend_bonus_split|cont | -0.480% | -1.16 | 15 | -0.544% | -1.71 | 20 | 248 | INCONCLUSIVE |
| B|dividend_bonus_split|edge | -0.123% | -0.30 | 15 | -0.312% | -0.97 | 20 | 248 | INCONCLUSIVE |
| B|operations_up|cont | -0.650% | -2.32 | 16 | -0.328% | -1.12 | 20 | 123 | OPPOSITE |
| B|operations_up|edge | -0.270% | -0.94 | 16 | -0.099% | -0.33 | 20 | 123 | REJECTED |
| B|disruption|cont | +0.682% | +0.46 | 5 | +0.165% | +0.22 | 8 | 18 | INCONCLUSIVE |
| B|disruption|edge | +1.057% | +0.72 | 5 | +0.503% | +0.69 | 8 | 18 | INCONCLUSIVE |
| B|analyst_meet|cont | -0.102% | -0.39 | 10 | -0.037% | -0.26 | 20 | 520 | INCONCLUSIVE |
| B|analyst_meet|edge | +0.187% | +0.73 | 10 | +0.204% | +1.44 | 20 | 520 | INCONCLUSIVE |
| B|all_news|cont | -0.052% | -0.88 | 16 | -0.135% | -2.94 | 20 | 6,756 | REJECTED |
| B|all_news|edge | +0.301% | +4.78 | 16 | +0.111% | +2.58 | 20 | 6,756 | CONDITIONAL |
