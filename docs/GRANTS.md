# Grants: every authority the system has been given, and its limits

Written 2026-10-15 (research audit cards G8-GRANT and G8-IDLE). A grant is a dated sentence from Madhav. The first one (G8) had no document of its
own: its date and terms survived only in a test comment, and it sat four days with no trades because nothing said what evidence it should produce.
From now on every grant is written here the day it is given, with its limits as numbers and a **minimum-activity plan**.

Nothing in this file reaches real money. Real money needs Rule A (`docs/LOCK.md`): 60 market days of paper operation, both market-dial states
seen, and execution within 3 points of the backtest, plus Madhav's own word.

## What every future grant must carry

1. The date, Madhav's words (or the closest record) and where they are kept.
2. Limits as numbers: money, size, number of positions, markets, daily AI spend, and what it can never touch.
3. A minimum-activity plan: what will run, how much evidence it should produce and by when, and the date it is reviewed. A grant that cannot
   produce evidence inside its window says so on the day it is given.
4. A switch Madhav can use without code, and who owns it.
5. Paper only until Rule A says otherwise.

## Trading and evidence books

| Grant | Date | Source | Limits | Minimum-activity plan | State on 2026-10-15 |
|---|---|---|---|---|---|
| G8 paper ledger | 2026-09-24 | Owner's "operator sentence", recorded second-hand in `tests/test_paper_lab.py` and `src/intelligence/paper_ledger.py` | $1,000 of paper, at most $100 in one position, one position, paper_take on, execution off, costs modelled as an 8 bp haircut (later measured about 10 times too low) | None written. Result: 214 decisions from Sep 19 to Sep 28, no TAKE; first fill Sep 29 | Superseded by SD6; parked with the hourly watch on Oct 11 (D6) |
| Candidate paper books V0 and V1 (frozen trend-dip) | 2026-09-29 (V0), 2026-09-30 (V1) | Operator: "paper-trade it"; "lets start and continue towards our milestone" (`docs/PAPER_LAB_LOCK.md`) | $1,000 of paper each, $100 a position, one per coin, NDAX costs; V0 wind-down from Sep 30; V1's loss-streak breaker TRIPPED Oct 8 | None written. Last trades closed Oct 8 (V0 3, V1 10, none won) | **Retired, Madhav 2026-10-21** (OD-CANDIDATE-BOOKS (a), "for all the recommended items, its yes"): no new entries (`candidate_paper.RETIRED`); books, trades and the breaker kept as history |
| SD6 exits on paper fills | 2026-09-29 | "attach SD6 to paper fills" (`docs/PAPER_LAB_LOCK.md`) | $100 a trade, long only, one position, exit manager ported from Hands, real exchange costs (SD6 v2), execution off | 22 positions to Oct 11 (3 wins, about -$32.5 net, about $24 of it fees) | Parked Oct 11 (D6: "2 setups in 12 days") |
| T3 trend portfolio, 10 coins | 2026-09-30 | MAIN and SHADOW books of $2,000 each ($200 a coin). MAIN waited for approval until Madhav switched Portfolio autopilot on in the Jarvis app on 2026-10-02 06:06 | Paper only; trades a coin only when its share drifts outside 0.5x-1.5x of target (T3-B) | Queue Q2: 6-8 weekly rebalances before it is judged | Running on paper, AUTO |
| T3 trend portfolio, 30 coins | 2026-10-04 | Madhav, Oct 4: "give paper slots in the 30-coin tier, separately"; AUTO since 2026-10-05 02:05 | Paper only; evidence only, never a candidate for real money (Madhav, Oct 15, scope b) | Queue Q8: 6-8 weekly checks | Running on paper, AUTO |
| The $500 NDAX book | 2026-10-11 | Decisions D9 (the book), D12 (brakes), D13 (NDAX only, CAD); `docs/research/BOOK500.md` | $500 of paper in CAD on NDAX coins; core by the dial (BTC 40%, ETH 20%), measured edges up to 30%, judgment up to 10%; brakes enforced in code | No judgment before 20 closed setup trades (BOOK500-LIVE) | Running on paper |
| Jarvis's own book (the brain) | from 2026-10-04 (first decisions) | Brain constitution: default PASS; `jarvis/service/brain.py`; decisions in `brain_decisions` | Paper only; AI spend at most $1.00 a day; a paid web check only within its daily count | Queue Q7: 10 independent market events | Running on paper; no buy since Oct 9 |
| The bold book (fix A8) | 2026-10-15 | Madhav in chat, 06:33 Toronto: "2. approved" (`docs/knowledge/bold_mandate.json`) | Paper only; $100 a trade, at most one new trade a day, must pick on every dial-open day; AI spend at most $0.05 a day; two locks (`BOLD_BOOK=1` and the approved mandate) | Review after 30 closed trades or 60 days, whichever is later, against its random twin | Running (first pick Oct 15) |

## Research, spending and operations

| Grant | Date | Source | Limits |
|---|---|---|---|
| Evidence window and Rules A and B | 2026-10-14 | Madhav, Oct 14 (`docs/knowledge/strategy_status.json`, `evidence_window`) | 60 market days from Oct 15; no real money before it ends and both dial states are seen; no new crypto strategies meanwhile |
| Review #29 and the agent exams (A6, A7) | 2026-10-15 | Madhav: "1. approved", "3. ok" | Review #29 as pre-registered; two exam runs of about $1.3 each, with the keep rule written before the run |
| Review #30 and gate scope (b) | 2026-10-15 | Madhav: "30 yes b, room yes, yes" | #30 as pre-registered; only tiers that could trade real money count for the survivorship gate; "room to the target" closed without a review |
| Worker Mac outside alert | 2026-10-15 | Madhav: "yes and yes" | A phone note when the public site has not answered for 10 minutes, using the existing phone topic; the M2a-G phone alert stopped |
| Ananta Canada | 2026-10-15 | C0 pre-registration approved and frozen (01:59); amendment A1 approved (03:11) | Research only; shares no data, findings, parameters or files with crypto; deferred until the crypto work is done |

## Changing a grant

A grant changes only by Madhav's word in chat, written here the same day. Retiring a setup under the retirement rule (`docs/research/BOOK500.md`)
also waits for his yes: the system only flags it.
