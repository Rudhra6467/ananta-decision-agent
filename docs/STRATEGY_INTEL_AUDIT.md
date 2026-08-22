# Strategy Intelligence Audit — 2026-08-22

**Verdict:** PARTIALLY (Wave A operations) / **NO** (rank the full universe).  
**Wave A selection:** **B — manually configured experiment.** Not Agent ranking.

Two confidences are separate:

| | Meaning | Wave A today |
|---|---|---|
| Understanding | Does the Agent know what the strategy is *for*? | **PARTIAL** after `dna` + cycle observations |
| Evidence | Do we have enough outcomes to KEEP? | **LOW** — WAIT/SKIP process only; **0 paper TAKE marks**; 1y lab **not run** (candles too short) |

---

## Why Hunter / Squeeze / Bollinger-MR?

**B. Manually locked Wave A set** (roadmap + NORTH_STAR_LOCK). Later enabled on the live paper book via Agent `enable`.

Not A (Agent ranked 15). Not “those are the only strategies that exist.”  
Continuation is a first-class Ananta executor and is **not** in Wave A on purpose.

Ananta’s own 2026-07-26 Recommended Matrix actually **benched all three** (hunter: no material trades; squeeze: 0% win; bollinger: negative every regime). Wave A is a **re-test**, not a copy of that matrix. That is allowed. It is not proof.

---

## A / B / C — what the Agent actually knows

**A. Code-level (Ananta owns this)**  
Schemas + DNA (`strategy/definitions.py`, `strategy/declarative_defs.py`), profiles (`strategy_profiles.py`), engines (`primary_layer.py`, `squeeze.py`, `continuation.py`, `declarative_engine.py`), router (`router.py`), universal exits (`exit_engine.py`), Lab replay (`lab/backtest.py`).

**B. Agent-context (what is supplied at decision time)**  
Until today: enable/disable, cycle `strategy_observations` (ran / setup / skip / regime / state).  
Now: `dna` command pulls registry DNA.  
**Not** in the decision loop: full entry gates, param values, exit modules, 1y stats, comparison ranks.

**C. Evidence**  
Paper: many WAIT/SKIP `good_process` marks; **no TAKE outcomes**.  
Historical Lab 1y: **blocked** — weakest 1h series = 135 bars (need ≥ 250 warmup; 1y needs ~8k). BTC/ETH/SOL have 736 1h (~1 month), not 1 year.

---

## Live vs DNA conflicts (read from code)

| Strategy | DNA `works_best` | Live router / Wave A allow-list | Implication |
|---|---|---|---|
| hunter | “Trending / recovering” | Router: **REVERSAL only**. Wave A: `['REVERSAL']`. Engine also has AGGRESSIVE_PULLBACK for strong uptrend but **TREND_UP is blocked** (SOL/PAXG SKIPs). | DNA and live gate disagree. Agent must not “understand” hunter as a trend tool. |
| squeeze | Post-consolidation breakouts | Router: **COMPRESSION**. Wave A: `['COMPRESSION']`. | Aligned. Coil + confirmed breakout (not first candle). |
| bollinger-mr | Range-bound | Wave A: `RANGE` + `COMPRESSION`. Matrix: empty regimes (benched). | DNA vs matrix disagree; Wave A is the experiment. |
| continuation | Dips in uptrend | Router: **TREND_UP**. Not Wave A. | Would be the trend-up executor; we did not enable it. |

Execution timeframe in `trading_engine.py` is **1h** (comments in hunter/squeeze files still say 4h in places). Lab default is 1h. Treat **1h** as live truth.

Exits: hunter/squeeze → Universal Exit Engine (structural / ATR trail / time / EMA loss). Declarative strategies also have spec exits; Wave A `enable` currently sets **fixed $5 / $3.5**. Sizing: `normal_lot_usd` default $75.

---

## Inventory (implementation, not names)

Legend: **Access** = Agent can enable via API. **In Wave A** = currently ON for this lab.  
Understanding here = Agent-context, not whether Ananta’s code exists (it does).

| Strategy | Where | TF | Entry (code) | Exit (code) | Intended regime (live) | Wave A | Agent access | Hist 1y | Paper TAKEs | Understanding | Evidence | Rec |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| hunter | `primary_layer.py` + schema `strategy/definitions.py` | 1h | Support zone + profile (stabilized: RSI 30–35, vol exhaustion, VCP, not chase) | Universal Exit; structural stop below zone | **REVERSAL** (router) | ON | yes | no | 0 | PARTIAL | LOW | **WATCH** |
| squeeze | `squeeze.py` | 1h | BB inside KC (coil) + vol breakout, then RETEST or CONTINUATION (not first candle); stop 20-MA | Universal Exit; EMA-loss prioritized | **COMPRESSION** | ON | yes | no | 0 | PARTIAL | LOW | **WATCH** |
| bollinger-mr | `declarative_defs.py` spec | 1h | close < BB lower | close ≥ BB mid (+ fixed/universal) | RANGE (DNA); Wave A RANGE+COMPRESSION | ON | yes | no | 0 | PARTIAL | LOW | **WATCH** |
| continuation | `continuation.py` | 1h | Uptrend pullback to 20-EMA, RSI 40–62, vol dry | Universal Exit | **TREND_UP** | off | yes, **do not enable** | no | 0 | LOW | LOW | hold |
| ema-cross | declarative | 1h | fast EMA cross above slow | cross below | Matrix: COMPRESSION, RANGE | off | yes | no | 0 | LOW | LOW | hold |
| supertrend | declarative | 1h | supertrend_dir cross above 0 | cross below 0 | COMPRESSION | off | yes | no | 0 | LOW | LOW | hold |
| rsi-momentum | declarative | 1h | RSI cross above entry AND close > trend EMA | RSI < exit | Matrix empty (benched) | off | yes | no | 0 | LOW | LOW | hold |
| macd-trend | declarative | 1h | MACD cross above signal AND MACD>0 | cross below | benched | off | yes | no | 0 | LOW | LOW | hold |
| donchian-breakout | declarative | 1h | close > N-high | close < M-low | COMPRESSION | off | yes | no | 0 | LOW | LOW | hold |
| atr-breakout | declarative | 1h | close > prev close + k×ATR | spec exit empty → engine | TREND_DOWN (matrix) | off | yes | no | 0 | LOW | LOW | hold |
| keltner-breakout | declarative | 1h | close cross above upper KC | cross below mid | RANGE | off | yes | no | 0 | LOW | LOW | hold |
| turtle | declarative | 1h | 20-Donchian high | 10-Donchian low | benched | off | yes | no | 0 | LOW | LOW | hold |
| time-series-momentum | declarative | 1h | ROC lookback cross above 0 | cross below 0 | COMPRESSION | off | yes | no | 0 | LOW | LOW | hold |
| stochastic-momentum | declarative | 1h | %K cross above %D while oversold | %K cross below %D | COMPRESSION, RANGE | off | yes | no | 0 | LOW | LOW | hold |
| vwap-mr | declarative | 1h | close < VWAP lower σ | close ≥ VWAP | benched | off | yes | no | 0 | LOW | LOW | hold |

Sizing/risk shared: `normal_lot_usd`, `max_concurrent_positions`, `max_spread_pct`, kill switches.  
Declarative indicators/params are in `strategy/declarative_defs.py` (exact). Hunter params in `strategy/definitions.py`.

---

## Could the Agent explain, compare, rank, and recommend the full list today?

**No.**

It can **list** them (`dna` / registry) and **operate** three of them on paper cycles.

It cannot yet:

1. Put full entry/exit/param objects into the decision context (Knowledge Object).  
2. Answer “how would Hunter have behaved over 1y?” — candles are ~1 month on majors, ~135 bars on alts.  
3. Count historical false positives / SKIPs (Lab takes; it does not replay Agent WAIT).  
4. Compare squeeze vs hunter in high vol with numbers.  
5. Independently pick the next Wave from the catalog.

**Connect next (still not a new product):**

1. Backfill 1h (`python scripts/backfill_1h.py`) → `lab` 1y JSON (`source=backtest`).  
2. Strategy Knowledge Object for **Wave A only** (identity, thesis, gates, regimes, params, evidence slots).  
3. Per-symbol per-strategy markable rows (already queued).  
4. Then paper TAKEs. KEEP still human + TAKE evidence.

PDFs: methodology/rationale only. **Not** `PDFs → LLM → KEEP`.

Mutation: Agent proposes hypothesis; Lab/paper tests; human promotes a **version**. No rewrite of `hunter` in place.

Wave A mission unchanged: hunter / squeeze / bollinger-mr stay WATCH.
