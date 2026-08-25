# S5 — Hypotheses (measurement vs mutation)

**Opened:** 2026-08-23 after `lab compare`  
**Human lock 2026-08-25:** H3 + H2 approved as **measurement only**. H1 live enable remains **rejected**. Wave A stays **WATCH**. Watcher stays up.  
**try_run** still refuses mutation. H3 report = `lab attribution live` / `lab attribution replay`. H2 waits on Ananta `reason_codes` dump.

Path remains finding → hypothesis → experiment → validation → human → versioned production. These are **not** Hunter v1.1.

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

**Status 2026-08-25:** APPROVED_PENDING_INSTRUMENTATION. Needs Ananta `evaluate_primary` reason_codes on REVERSAL bars (stride=1). Do not loosen gates from this finding.

---

## H3 — Split TAKE-eq by strategy (stop mixing Bollinger into Wave A)

**Finding:** 55 hist TAKE-eq = hunter 4 + squeeze 4 + bollinger 47. Mean +1h after TAKE (−0.056%) is almost entirely bollinger.

**Hypothesis:** Wave A “TAKE quality” is currently a Bollinger number wearing a Wave A badge.

**Proposed experiment (if approved):** Report +15m/+1h/+4h **per strategy** for hist TAKE-eq and live SKIPs. Bollinger stays shadow; hunter/squeeze scored separately.

**PM default:** **approve H3** — it is a report, not a trade.

**Status 2026-08-25:** APPROVED_MEASUREMENT. Run `lab attribution live` and `lab attribution replay`. Engine now joins `outcome_truth.assets[BTC/USD][+1h].ret_pct` (the previous None means were a join bug, not empty tape).

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

**Human lock 2026-08-25:** H3 report + H2 instrumentation approved. H1 live enable rejected. H4 none. H5 later.
Wave A is the first baseline, not the Strategy Center. Next after H3 numbers: Decision Quality v0, then Strategy Research Universe v1. Do not spend weeks rescuing Hunter.
