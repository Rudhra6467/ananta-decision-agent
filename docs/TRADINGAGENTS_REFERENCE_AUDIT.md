# TradingAgents → Agent Ananta — Reference Architecture Audit

**Date:** 2026-08-23  
**Inspected:** [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) `v0.3.1` (main, Apache-2.0, arXiv:2412.20138)  
**Compared to:** Agent Ananta `c8fef40` + Ananta `29e64e2` (S4 replay already run)  
**Status:** Reference only. **Does not change the locked roadmap.** Extra agents remain **not now**.

TradingAgents is a **component-level reference** for one slice of Decision Intelligence.  
It is **not** a competitor to clone, and **not** the architecture of Agent Ananta.

---

## One-line verdict

TradingAgents is a mature **LLM firm-simulation that produces a BUY/HOLD/SELL rating**.  
Agent Ananta is a **decision-intelligence OS over a real trading engine**, with independent evidence.

If we freeze today: they are ahead in multi-agent *workflow packaging*.  
We are ahead in *epistemics, execution truth, SKIP/opportunity cost, and promotion discipline*.  
The second gap is the product.

---

## What the code actually is (vs README)

| README / popular claim | Implementation on `main` v0.3.1 |
|---|---|
| Four analysts run **in parallel** | **Sequential.** `graph/setup.py` chains Market → Social → News → Fundamentals, then Bull. Parallel is marketing. |
| Risk **veto** after trader approval | **Not a veto.** Aggressive / Conservative / Neutral are LLM personalities. Portfolio Manager (another LLM) synthesizes. No programmatic block. |
| Learns from past mistakes | Markdown memory log + **5-day raw return vs SPY (or local index)** + a 2–4 sentence LLM reflection re-injected as prose. Profitability, not decision quality. |
| Full firm + simulated exchange | Graph ends at `Portfolio Manager → END`. Output is a 5-tier **rating**, not an order. `backtrader` is a dependency; the live graph does not place Ananta-style fills. |
| Autonomous without human input | Human picks ticker, date, models, debate depth, then one run. **Not a continuous observer.** |
| Research-backed | True: paper + serious engineering (look-ahead patches, vendor contract, CI). Still an LLM debate over vendor data. |

They independently discovered two problems we locked as laws:

1. **LLM number hallucination** (`dataflows/market_data_validator.py`, issue #830) — they added a deterministic `get_verified_market_snapshot` and tell the market analyst to treat it as source of truth. That is a **weaker cousin of Market Truth**.
2. **Look-ahead leakage** (v0.3.1 #1115) — Alpha Vantage fundamentals leaked future-dated reports into historical runs. They now filter. We designed point-in-time Lab candles from the start.

Those two patches are the strongest evidence that their trajectory and ours *converge on truth-vs-reasoning*, from opposite directions.

---

## Graph topology (theirs)

```text
START
  → Market Analyst ⇄ tools  (sequential, not parallel)
  → Sentiment Analyst ⇄ tools
  → News Analyst ⇄ tools
  → Fundamentals Analyst ⇄ tools
  → Bull Researcher ⇄ Bear Researcher   (round-limited debate)
  → Research Manager                    (structured 5-tier plan)
  → Trader                              (structured Buy/Hold/Sell)
  → Aggressive ⇄ Conservative ⇄ Neutral (round-limited debate)
  → Portfolio Manager                   (structured 5-tier rating)
  → END
       later: pending log → yfinance 5d return vs benchmark → LLM reflection
```

All debate/risk nodes are **prompt personas**. The only hard control is `max_debate_rounds` / `max_risk_discuss_rounds`.

Structured output (Pydantic) is layered onto **three** nodes only: Research Manager, Trader, Portfolio Manager. Everyone else is free-text.

Memory: append-only markdown at `~/.tradingagents/memory/trading_memory.md`. Pending tag → outcome + reflection. Checkpoint: per-ticker SQLite via LangGraph `SqliteSaver`.

---

## Graph topology (ours, today)

**LangGraph (early, not the lab):** supervisor routes User → Regime → Strategy rec → Portfolio → Tool execution. These are role labels, **not** deliberation. Do not pretend we already have a firm simulation.

**The real product loop (locked):**

```text
lab watch / cycle
  → System Truth (Ananta: regime, strategy_observations, portfolio)
  → Market Truth (independent Kraken / Lab candles)
  → Decision TAKE | SKIP | WAIT
  → Outcome Truth (+15m / +1h / +4h)
  → Regime Audit + Decision Audit
  → 1y observation_v0 replay (S4, done)
  → (later) experiment proposal → human approval
```

Ananta **already enforces** what their "risk team" only discusses: `router._REGIME_MAP`, `strategy_regime_ok`, kill switch, slot caps, Universal Exit Engine, live-parity Lab replay.

---

## KEEP / ADAPT / REJECT / ALREADY OURS

| # | Their piece | Verdict | Ananta mapping | When |
|---|---|---|---|---|
| 1 | Bull vs Bear **as LLM personas** | **ADAPT** — keep the *shape*, drop the theater | Decision Intelligence: THESIS → COUNTER-THESIS → EVIDENCE → ADJUDICATION. Claims must cite System / Market / Outcome rows, not each other's prose. | After live vs historical compare + S5. **Not now.** |
| 2 | Aggressive / Conservative / Neutral risk debate | **REJECT as veto; ADAPT as review** | Real veto stays in Ananta (regime, slots, kill, exits). Agent may *argue* risk; Ananta *enforces* it. North Star: policy/risk outside the LLM. | Later |
| 3 | Sequential analyst team (tech/news/sentiment/fundamentals) | **ADAPT specialists only when evidence shows a gap** | Crypto specialists (structure, derivatives, on-chain, news) are Phase 7+, gated. Do not spawn four LLMs to restate RSI. | Explicitly not now (`AGENTS.md`) |
| 4 | Structured Pydantic outputs (rating, action, stop, size) | **KEEP / steal** | Bind TAKE/SKIP/WAIT + skip_reason + evidence citations + confidence triplet to a schema. We already have Contract v0 fields; they are not typed at the LLM boundary. | When Decision Intelligence writes, not before S5 |
| 5 | Markdown decision memory + LLM reflection on 5d alpha | **ADAPT principle; REJECT the store** | `decision_log.json` / `opportunity_log.jsonl` / `observation_log.jsonl` / `observation_replay.jsonl` / `audit_report*.json`. Reflection may summarize; it may not *be* the ledger. Grade SKIP and opportunity cost, not only BUY profitability. | Ongoing (already designed) |
| 6 | `get_verified_market_snapshot` | **ALREADY OURS, stronger** | Independent Market Truth + Lab candles + no-look-ahead replay. Do not let Ananta regime grade Ananta. | S1–S4 done |
| 7 | Look-ahead-safe vendor contract | **ALREADY OURS in Lab; KEEP as a law** | Historical replay uses closed bars only. Never fetch "now" into a past decision. | Locked |
| 8 | Checkpoint / resume (SQLite) | **ADAPT later** | Useful when a deliberation graph is hours long. `lab watch` does not need it. | After Decision Intelligence graph exists |
| 9 | Provider / model catalog (OpenAI, Gemini, Claude, Grok, Bedrock, Ollama…) | **ADAPT later, low priority** | A beautiful router on an unproven decision system is premature. One working lab loop beats twelve providers. | After evidence density |
| 10 | FRED / Polymarket / Reddit / StockTwits | **ADAPT as Market Truth *inputs*** | News/sentiment become observables with timestamps, not extra voters. Same schema, sourced. | Phase 7 Research/PDF |
| 11 | 5-tier Buy/Overweight/Hold/Underweight/Sell | **REJECT as the decision language** | Ours is TAKE / SKIP / WAIT / HOLD / EXIT. HOLD≠WAIT≠SKIP. Overweight is sizing, which Ananta already owns. | Never as replacement |
| 12 | Consensus of many agents as confidence | **REJECT** | Ten agents on the same stale ticker is one opinion. Independent confirmation is required. | Never |
| 13 | LLM defines risk / position size | **REJECT** | Ananta `RiskSettings` + profiles. Agent proposes; engine clamps. | Never |
| 14 | Auto-mutate production strategy from a losing week | **REJECT** | Observation → finding → hypothesis → experiment → validation → **human** → versioned production. | Never automatic |
| 15 | Profitability as the only grade | **REJECT** | BTC path ≠ strategy PnL. Protective SKIP is a good decision. | Locked |
| 16 | CLI product polish, Docker, CI, changelog, tests | **KEEP as engineering bar** | Steal *discipline* (changelog, tests around look-ahead, config-fails-loud). Do not steal the product surface. | Gradual |
| 17 | One-shot "analyze ticker" UX | **REJECT as the product** | Our product is a closed loop around *this* book, *these* strategies, *this* user. "Analyze BTC" is a mode, not the OS. | Never as north star |

---

## Honest scorecard (today)

| Dimension | TradingAgents v0.3.1 | Agent Ananta now | Final Agent Ananta (if we execute the lock) |
|---|---|---|---|
| Multi-agent debate packaging | Strong | Early / unused for lab | Evidence-weighted adjudication |
| LLM provider zoo | Very strong | Not the focus | Later, thin router |
| Checkpoint / resume | Strong | Not needed yet | When graphs are long |
| Independent market facts | Started (verified snapshot) | **Core (S1–S4)** | Core |
| Look-ahead discipline | Patched after a leak | Designed in | Designed in |
| SKIP / WAIT as first-class | HOLD only | Explicit | Explicit + audited |
| Opportunity cost | No | Explicit | Explicit |
| Real execution / exits / gates | Rating only | Ananta engine | Ananta engine |
| Strategy intelligence + contradictions | No | Knowledge Object + 1y replay | Versioned experiments |
| User / personalization | Ticker + date | Partial, later | Major layer |
| Promotion / autonomy | N/A (research tool) | Conservative, WATCH | Evidence-gated |
| Engineering maturity (tests/CI) | Ahead | Lab-grade | Catch up without copying product |

Stars (~99k) measure *narrative and packaging*, not trading correctness. Their own README: educational, not advice. Treat it that way.

---

## How this does **not** change the sprint

Still locked:

- Wave A = hunter / squeeze / bollinger-mr, all **WATCH**
- S4 replay is evidence, not KEEP
- Next: **live vs historical compare**, then S5 **proposed** experiments (human approval)
- No extra agents, no bull/bear nodes, no provider zoo, no cockpit

TradingAgents occupies the **middle** of our eventual graph (research + argument + a rating).  
We own the **loop around it** (user, system truth, market truth, execution, outcome, audit, promotion).

---

## If we ever import deliberation, the rule

```text
Claim
  → cited evidence (System | Market | Outcome, with source)
  → independent confirmation?
  → historical reliability in this regime?
  → contradiction with router / implementation?
  → adjudication
  → TAKE | SKIP | WAIT
  → Ananta enforces
```

A bull agent that cannot point at an Observation row is a speech.

---

## PM action

1. This file is the audit. Roadmap unchanged.  
2. Do not open a TradingAgents integration branch.  
3. After live vs 1y compare, S5 may *cite* "thesis/counter-thesis" as a **proposal template**, not as new agents.  
4. Steal structured outputs when we type Decision Intelligence — not before.

Inspected paths: `tradingagents/graph/setup.py`, `trading_graph.py`, `agents/utils/memory.py`, `graph/reflection.py`, `agents/schemas.py`, `agents/managers/portfolio_manager.py`, `agents/researchers/bull_researcher.py`, `agents/risk_mgmt/conservative_debator.py`, `dataflows/market_data_validator.py`, `CHANGELOG.md` (v0.3.1 look-ahead + router crash-safety).
