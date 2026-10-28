# RX1 results: the 12 reconstruction drafts (run 28 Oct 2026)

Madhav approved all 12 drafts at 12:23 Toronto on 28 Oct. The spec (`rx1_v1.json`, commit dff5952) was written and committed before any outcome was read.

**Bar:** k = 151 (z 3.59). It spans the families "technical" (46 variants) and "exit" (93 variants) plus these 12.

**Data:** development 2000-2017, validation 2018-2023. No 2024+ data and no sealed folder was read. Manifest: `manifests/lab5_rx1.json`.

**Baseline:** the average liquid stock loses 0.22% from the open to the close of a session (it earns its return overnight). So every "fall" result below is measured against that same day's average, not against zero.

## The answers
| Draft(s) | Variant | Signal vs average (dev / val) | t (dev / val) | Verdict |
|---|---|---|---|---|
| 3, 4: breaking below the 20-day range | next session, open to close | -0.05% / +0.20% | -0.9 / 2.7 | REJECTED |
| 9: same, steady fall | next close to close | -0.14% / +0.04% | -2.7 / 0.7 | REJECTED |
| 6: 52-week low | next session, open to close | +0.02% / +0.13% | 0.1 / 1.2 | REJECTED |
| 5: falling below the 200-day | next session, open to close | **-0.18% / -0.12%** | **-4.9 / -2.5** | **CONDITIONAL** |
| 10: pullback in an uptrend | next session, open to close | -0.09% / -0.03% | -2.4 / -1.0 | INCONCLUSIVE |
| 11: rising below the 200-day | next session, open to close | +0.12% / +0.04% | 3.3 / 1.1 | INCONCLUSIVE |
| 12: rising inside its range | next session, open to close | -0.02% / -0.03% | -0.5 / -1.2 | REJECTED |
| 1: league gap, rising below the 200-day | 5 sessions | +0.25% / +0.19% | 1.7 / 1.6 | INCONCLUSIVE |
| 2: league gap, inside the range | 5 sessions | -0.34% / -0.05% | -2.5 / -0.4 | OPPOSITE |
| 7: pullbacks that never worked | time stop on day 3 vs hold 20 sessions | -0.44% / -0.26% per month | -2.4 / -1.5 | OPPOSITE |
| 8: random control | same time stop | -0.24% / -0.24% | -2.0 / -1.7 | OPPOSITE |
| 8: random control, Nifty under its 200-day | same time stop | -0.48% / -0.64% | -2.0 / -2.1 | OPPOSITE |

## In plain words
- **Seven of the eight "missed situation" drafts have no rule that could be known before the move.**
  - Stocks that broke their 20-day range, made a 52-week low, pulled back in an uptrend, rose below the 200-day or rose inside their range did about the same as the average stock the next day.
  - These drafts are answered with no: a missed move in these situations was hindsight, not a missed rule.
- **The one with something: a stock falling 2% or more while already below its 200-day average.**
  - Over the next session, open to close, it did 0.18% worse than the average stock in 2000-2017 and 0.12% worse in 2018-2023 (CONDITIONAL: strong early, weaker later).
  - On its own, shorting such a stock at the open earned about +0.36% after a 0.10% intraday cost.
  - But about 0.22% of that is the ordinary open-to-close drift every stock shows, and shorting is intraday-only in Indian cash, with fills at the open assumed.
  - Proposal at most: a 20-session paper trial of "avoid buying, or exit, stocks that fall 2% under their 200-day", never a short book.
- **The two reference-trader gaps:**
  - Rising below the 200-day held a small, non-significant edge over 5 sessions (+0.2%).
  - "Inside the range in an uptrend" came out the opposite way (-0.34% in 2000-2017).
  - The best trades in these situations were hindsight.
- **Pullbacks that never worked (draft 7):** leaving on day 4 when a trade has not gained a quarter of its planned risk did not help.
  - Per trade it changed little (-0.22% held 20 days against -0.17% with the time stop).
  - Month by month it was worse (OPPOSITE).
  - The poor timing is a property of the entry, not something a quick exit fixes.
- **Random control (draft 8):** the same time stop hurt random picks, most when the Nifty was under its 200-day (-0.5% to -0.6% a trade).
  - Holding into falls is the cost of holding: the faster exit gave up the rebounds.
  - The control keeps its rules, as the spec said it would.

## What changes
- No rule changes.
- One proposal waits for Madhav's yes: the 20-session paper trial of the "falling under the 200-day" filter (draft 5).
- The other 11 drafts are answered.
- Suggested, not done: stop the reconstruction from re-drafting an answered situation for 60 sessions. This touches the reconstruction's rules, so it waits for Madhav's yes.
