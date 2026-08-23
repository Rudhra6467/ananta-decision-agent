# S5 — Proposed hypotheses (NOT approved)

**Opened:** 2026-08-23 after `lab compare`  
**Status:** **PARKED pending tape.** Ledger exists (`lab experiments`). `try_run` is refused. Wave A stays **WATCH**.  
**Gate:** live tape accumulates 3–4+ days. Then human approval before any experiment runs. Path remains finding → hypothesis → experiment → validation → human → versioned production.

The attribution engine (`lab attribution`) and experiment ledger are built. That is **not** H3 running.

These are measurement / paper experiments. They are **not** Hunter v1.1.

---

## H1 — Hunter TREND_UP filter (highest signal)

**Finding:** Live 2/2 hunter setups and hist 85/108 hunter setups were `REGIME_FILTERED` in TREND_UP. AGGRESSIVE_PULLBACK exists; router + Wave A allow REVERSAL only.

**Hypothesis:** The implementation generates TREND_UP setups that current policy forbids. That is a contradiction, not proof the profile deserves to trade.

**Proposed experiment (if approved):** Do **not** enable TREND_UP in production. Optional paper-only shadow: log TREND_UP hunter setups as `SHADOW_TAKE_EQ` vs subsequent +1h/+4h **without** filling. Compare to REVERSAL TAKE-eq baseline.

**Reject unless approved:** `allowed_regimes += TREND_UP`, rewriting AGGRESSIVE_PULLBACK, adding Continuation to Wave A.

**PM default:** **do not run H1 as a live enable.** Shadow log only, or wait for stride=1 REVERSAL density.

---

## H2 — Hunter REVERSAL silence (gates too tight?)

**Finding:** 4 TAKE-eq in 154 sampled REVERSAL bars. Silent where allowed.

**Hypothesis:** STABILIZED_REVERSAL gates (RSI 30–35, VCP, HTF, volume exhaustion, support zone) may be conjunctively too rare — **or** REVERSAL itself is rare and the 4 are the true rate.

**Proposed experiment (if approved):** **Measurement only.** Histogram `reason_codes` from `evaluate_primary` on REVERSAL bars (stride=1). Rank which gate kills setups. No param change until the histogram exists.

**Reject unless approved:** Loosening RSI band, disabling VCP, disabling HTF.

**PM default:** **approve H2 as instrumentation** (replay field dump). No strategy mutation.

---

## H3 — Split TAKE-eq by strategy (stop mixing Bollinger into Wave A)

**Finding:** 55 hist TAKE-eq = hunter 4 + squeeze 4 + bollinger 47. Mean +1h after TAKE (−0.056%) is almost entirely bollinger.

**Hypothesis:** Wave A “TAKE quality” is currently a Bollinger number wearing a Wave A badge.

**Proposed experiment (if approved):** Report +15m/+1h/+4h **per strategy** for hist TAKE-eq and live SKIPs. Bollinger stays shadow; hunter/squeeze scored separately.

**PM default:** **approve H3** — it is a report, not a trade.

---

## H4 — Squeeze scarcity (no change)

**Finding:** 10 hist setups, 4 TAKE-eq, all COMPRESSION. Live: 0 setups, 490 REGIME_FILTERED on a BULL/NEUTRAL tape.

**Hypothesis:** Working as designed. Scarce is not broken.

**Proposed experiment:** None. Keep WATCH. Do not add RANGE.

---

## H5 — Audit clock (regime MISCLASSIFIED)

**Finding:** 16.7% live vs 25.6% hist MISCLASSIFIED. Independent flags are 1h; Ananta market label is EMA50/200.

**Hypothesis:** We are scoring a slow label against a fast tape.

**Proposed experiment (if approved):** Add a **slow independent** (4h/24h return / EMA stack from candles) alongside the fast flags. Do not change `classify_regime`.

**PM default:** optional, after H2/H3.

---

## Explicitly not S5

- KEEP / CUT any Wave A name
- Extra agents, Bull/Bear, TradingAgents integration
- Provider zoo, cockpit, $50 live
- Enabling the other 12
- Treating sit-out wash as “always WAIT” or overnight protection as “Hunter is good”

**Recommended approval set:** H3 (report split) + H2 (gate histogram). H1 shadow only if you want it. H4 none. H5 later.
