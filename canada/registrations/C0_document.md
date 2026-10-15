# Ananta Canada C0: pre-registration for review

Oct 14, 2026 · @vamsi

This is the Phase C0 deliverable you ordered: every test Canada will run, frozen in writing before any research data is downloaded. Nothing is purchased and no review runs until you approve this document.

## What this document is

**Your six C0 decisions are recorded below as binding; this document freezes all five reviews before any research data exists.** Once you approve it, this whole document, the five registrations and the code that holds the thresholds and cost formula (with its tests) are copied into the repository and hashed as one bundle; any later change to a criterion, a common rule or a threshold breaks the bundle hash and fails the test suite.

| # | Decision | Recorded as |
| --- | --- | --- |
| 1 | Data source | Norgate Canada Platinum, primary. Verify Mac compatibility and trial access **before** any purchase. |
| 2 | Scope | S&P/TSX Composite and TSX 60 only. TSX Venture, CSE and US-listed twins excluded. |
| 3 | History | 2000 to present. Development 2000–2017, validation 2018–2023, 2024 onward sealed holdout. |
| 4 | Spreads | Daily high-low estimates only, labelled ESTIMATE everywhere. No paid account. A measured-spread upgrade is presented as an option before any purchase. |
| 5 | Budget | Target C$55 a month, Norgate alone. No EODHD, no sector data, no other recurring cost without your approval. Bank of Canada data is free and used. |
| 6 | Sector data | Test whether Norgate gives complete point-in-time membership for all 11 sector indices. No TMX purchase without approval. |

One consequence of decision 5 matters for the validation plan: with Norgate alone there is **no second vendor**, so the 99.5% cross-vendor close test cannot run in C2. Section 9 defines single-vendor checks that run instead and keeps the cross-vendor test written and ready for the day a second vendor is approved.

What your approval unlocks: the Norgate free trial (no purchase), the field-and-coverage check against the trial, and then C1 data acquisition. What it does not unlock: any purchase, any research run before C3's baselines pass their gate, and any look at 2024 onward.

### Revised after an independent review, before your approval

A separate reviewer read the first draft looking for leaks, ambiguities and criteria that pass or fail by construction. It found 15 problems; every one is fixed in place below, and the code and tests were changed to match.

| # | Problem found | Fix now in the document |
| --- | --- | --- |
| 1 | GICS had 10 sectors before 2016-09-01, so "11 sectors from 2000" failed by construction | Sector rules use the sectors existing each day; the sector work starts at the first continuous passing day |
| 2 | CA#4's twins paid the same costs, so costs cancelled out of the very test meant to measure them | CA#4's edge is measured against uncosted twins; the boundary must be contiguous from decile 1 |
| 3 | Outlier and gap rules could delete real crashes (a Valeant-style drop) from held positions | Real crashes are kept; held positions always run through gaps and outliers; exclusions only block new signals |
| 4 | The freeze hash covered the registrations but not the common rules or the code | The whole document, registrations and rule code are hashed as one bundle |
| 5 | Verdicts did not cover every combination of outcomes | One ordered rule, first match wins; cells and variants graded the same way |
| 6 | The holdout test named no statistic and no end date | One statistic per review; the end date is written in your approval note before any computation; zero events means UNINFORMATIVE |
| 7 | Spin-offs and special dividends would look like price drops and create fake dips | Signals use prices adjusted for specials and spin-offs; dips across a distribution day are ignored |
| 8 | The cost estimate used raw prices and included the dip's own wide days | Capital-adjusted highs and lows, overnight adjustment, window ending 5 days before the fill; 2× doubles everything |
| 9 | "Cluster" could be read two ways, changing event counts severalfold | Fixed 10-day clusters, no chaining |
| 10 | No rule for trades crossing period boundaries or 2024 | Trades belong to their signal date; exits in 2024 are skipped; deleted members sold at the next open |
| 11 | CA#4's cost test would pass by construction | Cost curve is reported only; the pass needs a permutation test and enough deciles on both sides |
| 12 | Twin ranking broke when returns were negative or tied | Losing arms rank last, ties count against the rule, shifts drawn per period away from the rule itself |
| 13 | The sector index in CA#3 included the dipping stock itself | The signal stock is excluded; at least 3 other members required |
| 14 | V6, V9 and CA#2's event minimum could not fail | V6 reconciles index changes against published notices; V9 is 300 stratified checks; CA#2 counts dial spells |
| 15 | CA#5's hypothesis, null and test disagreed; its variant names clashed with V1–V9 | Restated; variants renamed CA5-A and CA5-B |

## Norgate verification

**Finding: Norgate does not run on a Mac.** Its updater (NDU) is [Windows-only](https://norgatedata.com/ndu-installation.php) (Windows 10/11, 64-bit; "VM usage is allowed"), and the [Python package](https://pypi.org/project/norgatedata/) only works while NDU runs, with Python inside the same Windows machine. Your Mac is an Apple M4 MacBook Air (24 GB memory, 117 GB free, no virtual-machine software installed), so Norgate needs Windows 11 for ARM in a virtual machine, running Norgate's x64 software through Windows' built-in emulation. Whether NDU works that way is **unconfirmed**; the trial is the test.

### What Norgate's own pages confirm tonight

| Item | Confirmed | Source |
| --- | --- | --- |
| Delisted securities and historical index membership | Included at Platinum level and above | [Packages](https://norgatedata.com/stockmarketpackages.php), [PyPI](https://pypi.org/project/norgatedata/) |
| Canadian exchanges | TSX, TSX Venture, CSE and NEO/Cboe Canada | [FAQ](https://norgatedata.com/data-package-faq.php) |
| History depth | Platinum back to 1990 (the Canadian row links to the Australian history page, so depth needs written confirmation) | [Packages](https://norgatedata.com/stockmarketpackages.php) |
| Price fields | Date, Open, High, Low, Close, Volume, Turnover, Unadjusted Close, Dividend | [PyPI](https://pypi.org/project/norgatedata/) |
| Adjustment modes | None, capital events, capital plus special distributions, total return | [PyPI](https://pypi.org/project/norgatedata/), [FAQ](https://norgatedata.com/data-package-faq.php) |
| Corporate actions | A capital-event flag per day (splits, reverse splits, bonus issues, stock dividends, reorganizations); dividends in the price series; spin-offs and specials only through the adjustment modes | [PyPI](https://pypi.org/project/norgatedata/) |
| Delisting | First and last quoted dates per security; a permanent asset ID that survives symbol changes | [PyPI](https://pypi.org/project/norgatedata/) |
| Index membership | A per-day in/out flag for a named index | [PyPI](https://pypi.org/project/norgatedata/) |
| Classification | GICS and TRBC labels per security, current only (the function takes no date) | [PyPI](https://pypi.org/project/norgatedata/) |
| Trial | 3 weeks, Platinum level, **2 years of history only**, one trial per market | [Free trial](https://norgatedata.com/freetrial.php) |

### What only the trial or Norgate support can confirm

1. NDU and the Python package run on Windows 11 for ARM under emulation. *Trial.*
2. The exact Canadian database names (listed and delisted) and the index names for the Composite, TSX 60 and the 11 capped sector indices. *Trial.*
3. Whether all 11 sector indices carry membership history, and that sectors partition the Composite on every date. *Trial for 2 years; support for depth.*
4. That Canadian prices **and** index membership reach back to 2000. *Support only: the trial shows 2 years.*
5. Whether Norgate carries a total-return version of the Composite. *Trial.*

### The sequence that wastes no trial days and spends nothing

1. **Write to Norgate support** with questions 3 and 4 (draft below; you send it, I don't send messages for you).
2. **Set up Windows on the Mac, free**: [UTM](https://www.intego.com/mac-security-blog/how-to-run-windows-11-for-free-on-an-m1-m2-m3-or-m4-mac/) (free) with Microsoft's Windows 11 ARM image. It installs without a product key; long-term use needs a Windows licence, a one-time cost I will bring to you before the trial ends, not buy. Parallels is excluded: it is a yearly subscription.
3. **Start the 3-week trial only once Windows works**, since Norgate allows one trial per market.
4. **Run the field check script** (written in C0, run only in the trial): it lists databases, index names, fields and per-index membership counts, and writes a coverage report. No research numbers are computed, and because the trial's 2 years fall inside the sealed holdout, the trial files are deleted when the trial ends.
5. **Bring you the purchase decision** with the coverage report and support's answer. Annual Platinum is C$630 (C$52.50 a month, inside your C$55 target); six months is C$346.50 (C$57.75 a month, slightly above).

If NDU fails on Windows for ARM, I stop and bring you options rather than choosing one: Windows 365 (listed by Norgate as supported, recurring cost), a second-hand Windows PC (one-time cost), or a different vendor (point-in-time index membership unconfirmed elsewhere).

**Draft message to Norgate support:**

> Hello, I am evaluating Norgate Canada Platinum for survivorship-free research. Before starting the trial, could you confirm: (1) the earliest date of daily prices for TSX-listed and delisted Canadian equities; (2) the earliest date of historical constituent data for the S&P/TSX Composite, the S&P/TSX 60, and each of the 11 S&P/TSX Capped sector indices; (3) whether a total-return series of the S&P/TSX Composite is available; and (4) whether NDU is known to run on Windows 11 for ARM in a virtual machine on Apple silicon. Thank you.

## Common rules for all five reviews

**These rules apply to CA#1–CA#5 unless a registration states otherwise, and none can change after the first result is seen.** Each registration below gives only what is specific to it.

### Data and universe

- **Source:** Norgate Canada Platinum, padding off. One vendor; the single-vendor checks in section 9 must pass before any review runs.
- **Point-in-time universe:** "member" always means a member of the named index at the close of *t−1*, in every review. A stock deleted from an index is sold at the next open after the deletion shows; membership known only after the fact is never used.
- **Delisted stocks** stay in every universe for the days they were members.
- **Calendar:** trading days are the days the S&P/TSX Composite has a close (the TSE 300 before May 2002, as Norgate records it).
- **Prices:** signals use **capital-plus-specials-adjusted** closes (splits, consolidations, special distributions and spin-offs removed; ordinary dividends not). A *distribution day* is any day the ratio of that series to the capital-only series changes. Returns use total-return-adjusted prices. Costs use capital-adjusted highs and lows.
- **Sectors by era:** GICS had 10 sectors before Real Estate was split out on 2016-09-01, and 11 after. Every sector rule uses the sector indices that existed on that day.

### Periods and the holdout seal

| Period | Dates | Use |
| --- | --- | --- |
| Warm-up | 1999 (if available) | Moving averages and volatility only; no trades |
| Development | 2000-01-01 to 2017-12-31 | First pass of every review |
| Validation | 2018-01-01 to 2023-12-31 | Must confirm the development result |
| Holdout | 2024-01-01 onward | Sealed; see protocol below |

**Start date:** each review starts on the later of 2000-01-04 and the first day every input it uses (prices, index membership, sector membership) has its full warm-up. The start is reported; a shorter period is never extended. **Period ownership:** a trade belongs to the period of its signal date; CA#1, CA#2 and CA#5 run continuously to 2023-12-29, with metrics computed on each period's segment. **The 2024 wall:** a signal whose scheduled exit falls on or after 2024-01-01 is skipped, for strategies and twins alike; positions still open in a continuous run are marked at the last close of 2023.

### Execution

- Signals are computed at the close of day *t*; every entry and exit fills at the **open of *t+1***. No same-close fills.
- No open on *t+1* (halt or missing day): fill at the next available open.
- **Gaps, halts and extreme days never remove a held position's loss or gain.** A held position runs through them to the next available open or to the delisting rule. Data exclusions only block new signals.
- **Lookbacks across gaps:** moving averages, σ and liquidity use the last N available closes; only the 3-day dip return is blocked when days *t−3* to *t* span a gap.
- **Delisting while held:** exit at the last quoted close. If that close is below 50% of the close 60 trading days earlier (a distress sign), a further 30% loss is applied.
- Out-of-market money earns the Bank of Canada overnight rate from Valet (free).

### Costs, all labelled ESTIMATE

- **Commission:** C$0, per the Questrade and Wealthsimple fee tables.
- **Spread:** the Corwin–Schultz two-day estimate from **capital-adjusted** highs and lows, with its authors' overnight adjustment (when day 2's range sits wholly above or below day 1's close, day 2's high and low are shifted by the gap). Negative values become 0; a two-day window containing a capital event is skipped.
- **Window:** for a fill on day *f*, the mean of the daily estimates over the 21 trading days ending on *f−5*, so a dip's own wide ranges never inflate its cost.
- **One-way cost** = max(0.05%, half that mean) + 0.05% slippage. Index-level switching (CA#1, CA#5) applies it to every stock in the basket.
- **Stress rule:** 2× means twice the full one-way cost, floor and slippage included. Every pass criterion must also hold at 2×; a result that survives only at 1× is WEAK at best.
- No taxes, no FX (CAD stocks, CAD account).

### Random twins

Every review is compared with **1,000 random twins** built from the same point-in-time universe, dates, position count and holding lengths, costed identically, with a random seed recorded at freeze so any run repeats exactly.

- **Circular shifts** (CA#1, CA#5) are drawn separately within each period, with offsets drawn without replacement from 63 to N−63 trading days, so no twin is a near-copy of the rule.
- **Ties count against the rule:** a percentile counts only twins the rule beats strictly.
- **Losing arms rank last:** when comparing Calmar, any arm with a compound yearly return ≤ 0 ranks below every arm with a positive return, ordered by return, so a larger loss can never improve a score.
- **Identical costs cancel** in a twin comparison, so "beats its twins" measures selection or timing only. What must hold after costs in absolute terms is stated in each registration.

### Independent events

Rows are never counted as events. Each registration defines its unit and a minimum per period; **below the minimum in either period, the verdict is INSUFFICIENT EVIDENCE**, never pass or fail. **Cluster** (CA#3, CA#4): a cluster starts on the first unclustered signal day in a cell and contains that cell's signals on the next 10 trading days; the next signal after that starts a new cluster. No chaining.

### Verdicts

Verdicts are assigned by this ordered rule; the first match wins:

1. **NOT RUN:** a required input is unavailable (named).
2. **INSUFFICIENT EVIDENCE:** the minimum independent events are not met in development **or** validation.
3. **ENOUGH:** every criterion met in development and validation, at 1× and 2× costs.
4. **WEAK:** every criterion met in development at 1×, and in validation every comparison has the registered sign (drawdown ratio below 1, Calmar at least its comparator's, twin percentile above 50, mean excess above 0).
5. **FAIL:** anything else.

Cells (CA#3) and variants (CA#5) are each graded by this rule, and the review takes the best grade in the order ENOUGH, WEAK, FAIL, INSUFFICIENT EVIDENCE. Every review is reported with the same template, failures included, and no verdict is softened in wording.

### Holdout protocol

1. Data from 2024-01-01 onward is stored in a separate sealed file; research code refuses those dates.
2. Data-quality checks (counts, gaps) may read it; no return, signal or performance number may be computed from it. The Norgate trial's 2 years fall inside the holdout, so the trial probe records counts and dates only, and the trial files are deleted when the trial ends.
3. The seal is broken **once**, for all five reviews together, only after all five have written verdicts in the registry, and only with your recorded approval. The approval note fixes the holdout's end date (the last close before approval) before any computation.
4. **One statistic per review:** CA#1 and each CA#5 variant, Calmar; CA#2, the metric of the outcome it earned (CAGR as return engine, Calmar as loss limiter); CA#3, each graded cell's mean net return per trade; CA#4, edge still falling with liquidity (rank correlation between decile number and edge below zero) and the boundary decile's edge ≥ 0. The criterion: the statistic strictly beats the twins' median, in the same direction as development and validation.
5. **Zero events in the holdout** (the dial never switches, say): UNINFORMATIVE; the verdict is unchanged and labelled so.
6. A review that fails its holdout criterion drops one level (ENOUGH to WEAK, WEAK to FAIL). Nothing is retuned.

### No other variants

Each review runs exactly the parameters frozen here: no alternative lookbacks, thresholds, holding periods or universes. Any new idea becomes a new registration with your approval, and it can never use the holdout.

The group atlas (C3) is measurement only, on development and validation years; nothing in it may become a rule without a new registration.

## CA#1 — The market dial

**Question: does holding Canadian stocks only while the S&P/TSX Composite closes above its 200-day average cut losses enough to beat buy-and-hold on risk-adjusted terms, after costs?** A pass earns the label *loss limiter*; it is a profit claim only if its yearly return also matches buy-and-hold, which is reported but not required.

| Field | Frozen value |
| --- | --- |
| Hypothesis | The dial reduces the worst peak-to-trough loss of a broad Canadian stock basket by at least a quarter, and its return per unit of loss beats both buy-and-hold and random timing. |
| Null | The dial's Calmar is no better than random timing with the same number of switches and days in the market. |
| Universe | S&P/TSX Composite members (TSE 300 before May 2002), point-in-time as of *t−1*. |
| Asset | An equal-weight basket of all eligible members, total return, reset to equal weight on the first trading day of each month. Deleted members are sold at the next open after deletion; added members join at the next monthly reset. |
| Signal | At the close of day *t*: **IN** if the Composite's close is above its 200-trading-day simple average of closes; **OUT** otherwise. No buffer, no confirmation days. |
| Entry and exit | IN after OUT: buy the whole basket at the next open. OUT after IN: sell the whole basket at the next open; cash earns the overnight rate. |
| Benchmark | The same basket held always (buy-and-hold), same resets, same costs. Costs do not cancel here: the dial trades more, so its extra switching is charged. |
| Costs | Common rules; every switch costs the one-way cost of every stock in the basket; monthly resets costed in both arms. |
| Random twin | 1,000 circular shifts of the IN/OUT series per period (common rules). |
| Start | 2000-01-04 if 200 prior trading days of Composite closes exist, else the first day that has them. |
| Independent event | One complete OUT-then-IN cycle. Minimum: **8** in development, **4** in validation. |
| Metrics | Maximum drawdown (MDD), compound yearly return (CAGR), Calmar = CAGR / MDD (losing arms ranked last), days in market, switches. |
| Pass, **both** periods, **1× and 2×** costs | (a) dial MDD ≤ 0.75 × buy-and-hold MDD; (b) dial Calmar ≥ buy-and-hold Calmar; (c) dial Calmar above the **95th percentile** of the 1,000 twins; (d) minimums met. |
| Holdout statistic | Calmar. |
| Data needed | Composite closes, Composite membership, stock prices (total return; capital-adjusted highs and lows for costs), Bank of Canada overnight rate. |

## CA#2 — The trend book

**Question: does holding TSX 60 stocks only while they trend up, and only while the dial is IN, beat holding randomly chosen TSX 60 stocks for the same days, and does it still earn more than cash after twice the estimated costs?** Two outcomes are registered in advance so no result can be relabelled afterwards: a *return engine* (beats the twins on return) and a *loss limiter* (beats them only on risk-adjusted return).

| Field | Frozen value |
| --- | --- |
| Hypothesis | Trend selection within the TSX 60 adds return over random selection of the same number of stocks held for the same days, and the book earns more than cash after 2× costs. |
| Null | Its return is no better than random picks with identical timing, count and holding lengths. |
| Universe | S&P/TSX 60 members, point-in-time as of *t−1*. |
| Book | 60 equal slots, one per possible member. Slot size = 1/60 of book value on the first trading day of each month; unused slots hold cash at the overnight rate. |
| Entry signal | At the close of day *t*: the stock was a member at *t−1*, its signal close is above **both** its 20-day and 50-day simple averages, and CA#1's dial is IN. Buy at the next open if not already held. |
| Exit signal | At the close of day *t*: the close is below either average, **or** CA#1's dial is OUT, **or** the stock has left the TSX 60. Sell at the next open. No stop-loss. |
| Dial | CA#1's definition exactly, whatever CA#1's verdict. |
| Costs | Common rules, per stock, per trade; monthly slot resizing costed. |
| Random twin | For every strategy trade, the twin buys a randomly chosen TSX 60 member eligible on the same entry date and not already held by that twin, for the same number of days at the same slot size. If no eligible name remains, that twin slot holds cash. 1,000 twins; the average overlap between twin and book holdings is reported. |
| Independent event | One dial IN-spell containing at least one trade. Minimum: **8** spells and **100** completed trades in development; **4** spells and **40** trades in validation. |
| Metrics | Book CAGR, MDD, Calmar, trades, average holding days, yearly turnover; equal-weight buy-and-hold TSX 60 reported alongside. |
| Pass as return engine, **both** periods, **1× and 2×** costs | (a) book CAGR above the **95th percentile** of the 1,000 twins; (b) book CAGR at 2× costs above the overnight-rate cash return of the same period; (c) minimums met. |
| Pass as loss limiter (graded only if the return engine is not ENOUGH or WEAK) | Book Calmar above the 95th percentile of twins **and** book MDD ≤ 0.75 × the twins' median MDD, both periods, both cost levels, minimums met. Graded by the common ordered rule and written as "return engine: \[grade\]; loss limiter: \[grade\]". |
| Holdout statistic | CAGR if graded as return engine; Calmar if graded as loss limiter. |
| Data needed | TSX 60 membership, stock prices (signal-adjusted, total return; capital-adjusted highs and lows for costs), Composite closes for the dial, overnight rate. |

## CA#3 — The sharp dip

**Question: after a TSX 60 stock falls unusually hard over three days, does buying it at the next open and holding 10 trading days beat buying a random TSX 60 stock on the same day, after costs?** The dip is measured against each stock's own volatility, so no crypto threshold is carried over. Four cells are registered; crypto's finding sat in one cell, and Canada does not presume which.

| Field | Frozen value |
| --- | --- |
| Hypothesis | Volatility-adjusted sharp dips in liquid Canadian large caps are followed by 10-day returns above same-day random entries, in at least one of the four cells. |
| Null | Dip entries earn no more than random TSX 60 entries on the same dates. |
| Universe | S&P/TSX 60 members, point-in-time as of *t−1*. |
| Dip measure | On signal-adjusted closes: R3 = close on *t* ÷ close on *t−3* − 1. σ = standard deviation of the 20 daily returns ending on *t−3* (the last 20 available). z = R3 ÷ (σ × √3). |
| Signal | z ≤ **−2.5** at the close of day *t*. Ignored if *t−3* to *t* contains a capital event, a distribution day or a data gap, or if the stock is already held. |
| Entry and exit | Buy at the open of *t+1*; sell at the open of the 11th trading day after entry (10 trading days held). **No stop-loss.** |
| Sector index for the split | For the stock's sector on day *t* (the 10 or 11 sector indices of that era): the daily-rebalanced equal-weight mean of the signal-adjusted daily returns of that sector's members as of *t−1*, **excluding the signal stock**, chained into an index. Its own z uses the same R3 and σ formula. Fewer than 3 remaining members: the stock-day is excluded from the split and counted. |
| Cells (four, all graded) | Dial state at the signal close (IN or OUT, CA#1's definition) × dip type: **sector-wide** if the sector index's z ≤ **−1.5** on day *t*, else **stock-only**. |
| Costs | Common rules, per trade. |
| Random twin | For each trade, a random TSX 60 member eligible on the same entry date (excluding that day's signal stocks), same open-to-open 10-day hold. 1,000 draws per cell; the statistic is mean net return per trade. |
| Independent event | Clusters, by the common definition, counted per cell. Minimum per cell: **30** in development, **15** in validation. |
| Metrics | Mean and median net return per trade, mean excess over twins, hit rate, worst trade, clusters per cell. |
| Pass per cell, **both** periods, **1× and 2×** costs | (a) mean net return per trade above the **98.75th percentile** of its twins (0.05 split across four cells); (b) mean net return per trade above zero at 2× costs; (c) minimums met. |
| Review verdict | The best cell grade (common rule). A cell graded ENOUGH is named and is the only cell that may ever be discussed for integration. |
| Holdout statistic | Each graded cell's mean net return per trade versus its twins' median. |
| Data needed | TSX 60 membership, sector-index memberships, stock prices (signal-adjusted, total return; capital-adjusted highs and lows for costs), capital-event and distribution days, Composite closes. Without sector membership, the split is NOT RUN and only the two dial cells are graded, at the 97.5th percentile. |

## CA#4 — The cost law

**Question: as stocks get less liquid, does any edge disappear once costs are paid, and where is the last decile still worth trading?** This review sets the boundary below which the agent may never trade Canadian stocks. The cost side is estimated from daily highs and lows, so the cost curve is **reported, not tested**, and the verdict is **capped at WEAK until spreads are measured**, whatever the numbers say.

| Field | Frozen value |
| --- | --- |
| Hypothesis | The dip rule's edge after costs is larger in the more liquid half of the Composite than in the less liquid half. |
| Null | Edge after costs shows no difference between the liquid and illiquid halves beyond what random shuffling of liquidity labels produces. |
| Universe | S&P/TSX Composite members, point-in-time as of *t−1*. |
| Liquidity deciles | Median daily traded value (Norgate's Turnover, C$) over the last 63 available trading days ending *t−1*. Deciles formed among eligible members on the first trading day of each calendar quarter; decile 1 = most liquid. |
| Trades | CA#3's dip rule exactly (signal, exclusions, next-open entry, 10-day hold, no stop), on every Composite member; all dial states and dip types pooled. |
| Edge | Per trade: net return at the stated cost level **minus the mean gross, uncosted return** of 1,000 random members of the same decile entered on the same date with the same hold. Costs therefore count against the edge instead of cancelling. |
| Cost curve (reported only) | Median estimated one-way cost per decile per period, and its rank correlation with decile number. Not a pass criterion until spreads are measured. |
| Independent event | Clusters, by the common definition, counted per decile. Minimum: **30** per decile in development, **15** in validation. At least **3** deciles on each side (1–5 and 6–10) must meet it, or the verdict is INSUFFICIENT EVIDENCE. |
| Pass, **both** periods, **1× and 2×** costs | Mean edge of deciles 1–5 minus mean edge of deciles 6–10 (qualifying deciles only) is above zero **and** above the **95th percentile** of 1,000 permutations that shuffle decile labels among trades entered on the same date. |
| Tradable boundary (output, whatever the verdict) | The largest *k* such that **every** decile from 1 to *k* has mean edge ≥ 0 at 2× costs in both periods with minimums met; "none" if decile 1 fails. Labelled ESTIMATE. |
| Verdict cap | WEAK at most until measured spreads replace the estimates. |
| Holdout statistic | Edge still falls with liquidity (rank correlation between decile number and edge below zero), and the boundary decile's edge ≥ 0. |
| Data needed | Composite membership, Turnover, prices (signal-adjusted, total return; capital-adjusted highs and lows), capital-event and distribution days. |

## CA#5 — The sector-breadth dial

**Question: does a dial that reads how many sectors are trending up do better than CA#1's single-index dial?** Exactly two variants are registered, CA5-A and CA5-B. If Norgate lacks continuous point-in-time sector membership, CA#5 is **NOT RUN**; today's sector labels are never substituted, because that would use knowledge from the future.

| Field | Frozen value |
| --- | --- |
| Hypothesis | Sector breadth gives a higher Calmar and no larger drawdown than CA#1's dial, with no more than 25% extra switching. |
| Null | Each variant's Calmar is no better than random timing with the same number of switches and days in the market. |
| Universe and asset | Identical to CA#1: the equal-weight basket of Composite members, monthly reset, cash at the overnight rate when OUT. |
| Sector series | For each sector index existing that day (10 before 2016-09-01, 11 after): the daily-rebalanced equal-weight mean of its members' signal-adjusted daily returns, members as of *t−1*, chained into an index. A sector with fewer than 3 members that day is left out of that day's count. |
| Sector state | A sector is UP at the close of *t* if its series is above its own 200-day simple average. |
| CA5-A | IN when more than half of the counted sectors are UP. |
| CA5-B | IN when more than half of the counted sectors are UP **and** CA#1's dial is IN. |
| Start | The first day of continuous sector membership (V8 passing) plus 200 trading days of warm-up. CA#1's dial is recomputed from the same start for every comparison below. |
| Entry, exit, costs | As CA#1. |
| Random twin | 1,000 circular shifts of each variant's IN/OUT series per period (common rules). |
| Independent event | One complete OUT-then-IN cycle. Minimum: **8** in development, **4** in validation. |
| Pass per variant, **both** periods, **1× and 2×** costs | (a) Calmar ≥ CA#1 dial's Calmar from the same start; (b) MDD ≤ CA#1 dial's MDD; (c) switches ≤ 1.25 × CA#1's; (d) Calmar above the **97.5th percentile** of its twins (0.05 split across two variants); (e) minimums met. |
| Review verdict | The better variant's grade (common rule). |
| Holdout statistic | Calmar, per variant. |
| Data needed | Continuous membership history of the sector indices (support must confirm depth), Composite membership and closes, stock prices, overnight rate. |

## Validation, manifests and gap rules

**No review runs until every check below passes on the stored data, and the C2 gate report says so.** The checks run on development and validation years; on holdout years they run counts and gaps only.

### Source manifest, one per pull

Every pull writes a manifest row before its data is used: source and package; NDU and Python package versions; pull time (UTC); padding and adjustment settings; the script's git commit; per security its Norgate asset ID, symbol, name, first and last quoted dates and row count; and a SHA-256 hash of every saved file. A file whose hash no longer matches its manifest is treated as missing.

### Checks at the C2 gate

| # | Check | Rule | Gate |
| --- | --- | --- | --- |
| V1 | Calendar | Every stock row falls on a Composite trading day | Zero rows off-calendar |
| V2 | Price sanity | Low ≤ open, close ≤ high; prices > 0; volume ≥ 0 | Violations ≤ 0.01% of rows, each listed |
| V3 | Gaps | Missing trading days between a stock's first and last quoted date | Gap rules below; member-days with no price ≤ 0.5% of all index member-days |
| V4 | Outliers | Adjusted daily move above 50% | **Kept as real** unless the V9 second record shows the raw close off by more than 5%; only then is that stock-day blocked for new signals. Held positions always run through it. Each outlier listed |
| V5 | Adjustment consistency | Raw-to-adjusted ratio changes only on capital-event, dividend or distribution days | Zero unexplained changes |
| V6 | Survivorship | Norgate's Composite and TSX 60 additions and deletions reconciled against published S&P/TSX index-change notices for 5 randomly chosen years (seeded); delisted members present in every year | ≥ 95% of changes matched; delisted count reported per year |
| V7 | Index membership | Daily TSX 60 count within 58–62; Composite count changes only around rebalance dates or listed corporate events | All days within range; exceptions listed and explained |
| V8 | Sector partition | Each day, every Composite member sits in exactly one of the sector indices existing that day (10 before 2016-09-01, 11 after) | ≥ 99.5% of member-days from the first continuous passing day, which sets CA#3's split and CA#5's start. Never passing: those are NOT RUN |
| V9 | Spot-check | **300** stratified stock-days (a third delisted stocks, a third before 2010, a third the rest; seeded) against a free second record: TMX's own historical pages or a second vendor's free trial. No purchase, no bulk scraping. Days with no free second record are replaced by the next sampled day, and replacements are counted | ≥ **297** of 300 within 0.5% |

### Gap rules

- **Gaps of 1–5 consecutive trading days** while listed: kept as gaps, **never filled**. Lookbacks use the last N available closes; only the 3-day dip return is blocked when its window spans a gap.
- **Gaps longer than 5 days:** no new signals for that stock for the 60 trading days after the gap ends; it is listed in the report.
- **Held positions are never removed by any data rule**: they run through gaps, halts and outliers to the next available open or the delisting rule.
- Index member-days with no price at all count against V3's 0.5% limit.
- Padding is off for every pull; no price is ever invented.

### Cross-vendor agreement test (written now, runs only with a second vendor)

With Norgate alone (your decision 5), there is no second vendor, so this test is **dormant** and V9's 300-day spot-check stands in for it. When you approve a second vendor:

- Compare **unadjusted closes** for every stock-day present in both sources from 2000 to 2023.
- A day agrees if the closes differ by at most 0.5% or C$0.01, whichever is larger.
- **Pass: at least 99.5% of overlapping stock-days agree**, and no single stock agrees on fewer than 95% of its days without an explanation.
- Disagreeing stock-days that cannot be resolved are excluded from research and listed.

### Spread upgrade option (presented, not purchased)

All spreads stay ESTIMATE until you approve one of these: a broker account whose quote feed lets us record real bid-ask spreads (Questrade lists real-time Level 1 as free for clients), or a paid quote dataset. Either one replaces the estimate only after its own 30-day recording and a comparison report; CA#4's WEAK cap lifts only then.

## Built tonight without touching crypto

**Canada now has its own code, registry, storage and tests, and nothing in the crypto service reads or imports any of it.** No research data was downloaded; the lake exists with empty tables.

| Item | Where | Evidence |
| --- | --- | --- |
| Code | `canada/` at the top of the repository, deliberately **outside `docs/`**: the agent's knowledge reader scans `docs/research`, `docs/knowledge`, `docs/repair_shop` and `docs/casebook`, so nothing Canadian can reach it | `paths.py`, `schema.py`, `registry.py`, `validation.py`, `costs.py`, `norgate_probe.py`, `README.md` |
| Registry, namespace CA | `canada/registry/canada_status.json`: a separate file from crypto's strategy\_status.json | Your six decisions, the phase gates, the sealed holdout, budget C$55 with no approved costs, CA1–CA5 all DRAFT\_AWAITING\_APPROVAL and RESEARCH, and a record of tonight's pre-approval revision |
| Bundle freeze | `registry.freeze_bundle()` writes CA1–CA5 and this whole document into `canada/registrations/` and hashes them with `validation.py`, `costs.py` and the test file as one bundle; refuses without an approval note or a second time | `verify()` names any changed file, including a quietly cheaper cost formula |
| Storage | `~/ananta_data/canada/`, outside every crypto folder (code refuses a folder inside one) | `canada_lake.sqlite` with 10 empty tables (0 price rows); `sealed/canada_holdout.sqlite` sealed 2026-10-15 02:39 UTC; empty `raw/` and `manifests/` |
| Holdout guard | `registry.assert_research_dates()` | Refuses any date range touching 2024-01-01 onward while sealed |
| Rules as code | `validation.py` (V1–V9 limits, era sector count, gap rules, the dormant 99.5% test) and `costs.py` (Corwin–Schultz with overnight adjustment, window ending *f−5*, 2× doubles the whole cost) | Tests hold every number to this document |
| Trial probe | `norgate_probe.py`, for the Windows trial only | Records databases, index names, fields and membership counts; computes no returns. **Untested** until the trial runs |
| Tests | `tests/test_canada_isolation.py`, 11 tests | All pass: isolation both ways; nothing under `docs/`; storage refused inside crypto folders; only CA1–CA5, all RESEARCH; holdout dates refused; bundle freeze needs approval and catches tampering; schema and seal; thresholds; cost rules |

One crypto observation from tonight, unrelated to Canada: the nightly registry step ran on its own at 00:00 UTC and re-stamped watches.json and status\_cards.json to Oct 15 with no drift found, which is the first unattended run of the one-truth registry working as designed.

## On your approval, and what stays forbidden either way

**Approve the document as written, or comment on any criterion you want changed; a changed criterion is cheap now and impossible later.**

- [ ] **Approve CA#1–CA#5 and the validation rules as written.** I then freeze each registration into the repository with its hash.
- [ ] **Send the Norgate support message** (section 2), from your own email.
- [ ] **Allow me to install UTM and Windows 11 for ARM on the Mac.** Both free; it adds software and about 40 GB of disk. A Windows licence for use beyond the trial comes back to you as a separate one-time decision.
- [ ] **Start the Norgate trial** once Windows works, then the coverage probe; I bring you the coverage report and the purchase decision.

Forbidden whatever the outcome: purchases or recurring costs without your approval; Canadian data reaching the agent, waking it, or touching a trade; any shared file, data, finding or parameter with crypto; parameter sweeps or reviews beyond CA#1–CA#5; any look at 2024 onward before all five verdicts and your approval; any criterion changed after a result. A failed, insufficient or no-edge-after-costs result is written down exactly as it comes out.

Crypto stays first: the twice-daily reviews, the 60-day window, and any crypto fix come before Canada work every day.
