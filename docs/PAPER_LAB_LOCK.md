# Paper laboratory lock — 2026-09-22

Primary objective: $1,000 / $100 paper intelligence laboratory.

Runtime law: implemented → reviewed → merged → deployed/running → verified.

Expected running version after deploy: `DI-LOOP-v1-l2-g1g7-persist`.
Until the laptop process prints that string, runtime is still `DI-LOOP-v0`.

paper_take=false. keep=false. exec=false. Continuation BENCHED. SHADOW/WATCH/SET16 are not M2.

G1 funnel v3: 7-state look taxonomy + per-asset counters for BTC ETH SOL ADA DOGE AVAX BCH LINK LTC XRP.
Zeros are real. Do not invent evaluated bars.
G2 coverage audit: zero paper-eligible states. Do not invent strategies.
G5 snapshot persists to `agent_decisions.sqlite` (Hands decision log). cwd JSON is a copy.
G6 exit plan will not open. G7 counterfactual does not rewrite thesis. fills=0.
G8 requires an operator sentence AFTER live-cycle verify. G1–G7 complete does not create G8.

Ranking is context-conditioned. No global average leaderboard.

## SD6 — exit/risk attached to paper fills (granted 2026-09-29)

Operator sentence: "attach SD6 to paper fills". Code: `src/intelligence/paper_exit.py` (`paper.exit.sd6.v1`).

- Every paper TAKE opens a priced position in the agent-side book `paper_book.sqlite`
  (entry = close of the decision bar + 8bp). Never the Hands Mongo book. Never `/api/orders/manual`.
- Exits = port of Hands `backend/exit_engine.py` (A, KILL, F, B, S, D, C, E) on closed 1h bars.
  Differential test vs Hands: 8 / 8,014 bars differ, all the deliberate no-lookahead ATR trail.
- Shadow = Hands "Fixed % Target + Stop" (2.2% / 3.0%) on the same bars. Never trades.
- One position, $100, LONG only (SHORT refused, recorded). Manual kill switch = emergency exit.
- Missing bars = DATA_STALE. No invented exit.
- Live opening requires `paper_exit_proof_v1.json` (`python -m src.intelligence.paper_exit fixture`).
- exec=false, live=false, counts_for_m2=false. M2 credit still needs its own sentence.
- Status: `python -m src.intelligence.paper_exit status`.

Profit-floor rounding bug (F re-firing TIGHTEN and blocking S/D/C/E in ~50% of trades past +1R):
fixed in Hands PR #4 and in SD6 on 2026-09-29. Operator approved the fix.
