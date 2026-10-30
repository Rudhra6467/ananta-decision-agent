# The portfolio on paper (Phase 5 of the 29 Oct 2026 plan), v1 — 30 Oct 2026

Paper only; the account is Madhav's father's (DZT404), read-only; no order is possible anywhere in this code (india/leakcheck.py). Nothing here changes a pinned rule; two questions for Madhav's one yes are listed at the end.

## 1. The three books that are compared
| book | what it is | starts | changes |
|---|---|---|---|
| **Frozen** | the holdings exactly as they stood when the twin opened (22 Oct 2026 snapshot: 13 stocks, cash, the options amount), never traded, only marked | ₹162,509 | none — `paper/account/frozen.json` |
| **The twin** | the same start, run by the allocator in **autonomous** mode (rule alloc-v1-2026-10-23, pinned): sleeves by regime, weak-holding trims (TIDY / TRIM / REDUCE), new stock buys only for a family ADMITTED on the evidence staircase (none today) | ₹162,509 | 3 paper trades so far (options → cash ₹16,000; IEX and JIOFIN trimmed) — `paper/account/state.json` |
| **Nifty 500** | the price index from the same day (dividends of about 1.2–1.5% a year are not in it; said, not added) | — | — |

One row a session in `paper/account/benchmark.jsonl` (from 29 Oct 2026; earlier sessions are not back-filled): twin, frozen, start, the three returns, twin minus frozen. The view and the facts carry the words. **Nothing is read into the gap before 60 sessions.**

Today (29 Oct close): twin −0.62%, frozen −0.53%, Nifty 500 +1.13% since 22 Oct.

## 2. The options sleeve
- Madhav (29 Oct): **"lock it at 50,000."** The allocation rule's `options_inr` is ₹50,000; the twin's sleeve is marked separately and no option trade touches the stock cash.
- **At this size only defined-risk structures are allowed:** a bought option (the most it can lose is its premium), a debit or credit spread with the wings bought, or the options line's one plain lot. Never a naked short option (margin ₹1–1.5 lakh a lot, and DR1 showed the affordable short structures do not pay).
- What the options line does today: one bought lot on paper per decision, scored every session (4 sessions on record). Nothing changes here.

## 3. Written criteria for the paper-to-live decision (the decision stays Madhav's)
All of these, in writing, before any live-mode discussion; none alone is enough:
1. **Sessions:** at least 60 sessions of the twin beside the frozen portfolio and the Nifty 500, every row sealed, none rewritten.
2. **Rules:** every rule the twin would trade live is VALIDATED or CONDITIONAL in the registry, has passed its own 20-session paper trial, and has Madhav's yes on the record (the one-yes list of Phase 7).
3. **Decision quality:** the reconstruction metrics (class-b misses, never-worked share, held-into-falls) at or better than the Phase 0 benchmark; no survival limit crossed on paper (5% a day, 22% from the peak).
4. **Realism:** paper fills checked against the live recorder's real quotes (slippage within the cost model's estimate); costs charged on every leg; the twin's trades reproducible from the allocation ledger.
5. **Result:** the twin does not lose to the frozen portfolio after costs over the window, and its drawdown is no worse; the Nifty 500 gap is reported, not required (a portfolio of 13 names is not an index).
6. **Scope and size:** live would start with the options sleeve (₹50,000, defined-risk only) and the allocator's weak-holding trims; no new stock family goes live before its own trial and yes.
7. **Control:** a separate, explicit live-mode decision; the no-order rule stays until then; a kill switch (the 22% pause) that stops new positions; Madhav can override any paper move and the twin records the difference (it already does: `differs_from_real`).

## 4. Questions for the one yes (Phase 7)
- **Q1 — the sleeve against the regime cap:** the allocator holds options at or under 20% of the book in a downtrend (today ₹34,000 of ₹161,494) while the rule's amount is ₹50,000. Lock the sleeve at ₹50,000 regardless of regime, or keep the cap (the sleeve grows to ₹50,000 when the regime allows)? Recommendation: keep the cap — it is HG1's only passing hedge in rule form.
- **Q2 — the long-term money's rule (FP1):** run the low-volatility or combined tilt as a *fourth* paper book (not the twin) for 12 months, judged on drawdown as much as return? Recommendation: yes, as a shadow book, no money moves.

Sources: allocation_rule_v1.json, paper_config.json, india/account.py, india/allocator.py, fp1_results_v1.md, dr1_results_v1.md, hg1_results_v1.md, the Phase 0 benchmark (docs).
