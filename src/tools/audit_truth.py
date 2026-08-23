"""
Stage 3 — Thin Regime Audit + Decision Audit.

Compares:
  System Truth (Ananta regime = hypothesis, Agent WAIT/SKIP/TAKE)
  Market Truth (independent Kraken flags at t0)
  Outcome Truth (forward BTC +15m/+1h/+4h)

Verdicts: SUPPORTED / MISCLASSIFIED / UNCERTAIN
Decision: PROTECTIVE / COSTLY / UNCERTAIN

Does NOT KEEP, enable, or rewrite strategies.
BTC path ≠ strategy PnL. No TAKE rows ⇒ no promotion evidence.
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.tools.observation_log import OBSERVATION_LOG

AUDIT_REPORT = Path("audit_report.json")
NOISE_1H = 0.25  # |BTC +1h| below this is chop, not a call
COST_1H = 0.40  # SKIP/WAIT vs rally/drop large enough to score
STRONG_T0 = 0.35  # |ret_1h at observation| for a strong independent label


def _load_rows() -> List[dict]:
    if not OBSERVATION_LOG.exists():
        return []
    rows: List[dict] = []
    for line in OBSERVATION_LOG.read_text().strip().splitlines():
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows


def _ananta_btc_regime(obs: dict) -> Tuple[str, str]:
    st = obs.get("system_truth") or {}
    regimes = st.get("regimes_by_symbol") or {}
    raw = regimes.get("BTC/USD") or regimes.get("BTC") or {}
    if isinstance(raw, dict):
        return (
            str(raw.get("market") or "").upper(),
            str(raw.get("asset") or "").upper(),
        )
    s = str(raw or "").upper()
    return s, ""


def _independent_btc(obs: dict) -> dict:
    mt = obs.get("market_truth") or {}
    btc = mt.get("btc") or {}
    return {
        "ok": bool(mt.get("ok")),
        "trend": str(btc.get("trend_flag") or "").upper(),
        "compression": str(btc.get("compression_flag") or "").upper(),
        "ret_1h": btc.get("ret_1h_pct"),
        "ret_4h": btc.get("ret_4h_pct"),
        "breadth": mt.get("breadth_1h_pct_positive"),
        "price": btc.get("price"),
    }


def _independent_label(ind: dict) -> str:
    if not ind.get("ok"):
        return "UNCLEAR"
    trend = ind.get("trend") or ""
    r1 = ind.get("ret_1h")
    breadth = ind.get("breadth")
    try:
        r1f = float(r1) if r1 is not None else None
    except (TypeError, ValueError):
        r1f = None
    try:
        bf = float(breadth) if breadth is not None else None
    except (TypeError, ValueError):
        bf = None

    strong_up = (r1f is not None and r1f >= STRONG_T0) or (
        trend == "UP" and r1f is not None and r1f >= 0.15 and (bf is None or bf >= 70)
    )
    strong_down = (r1f is not None and r1f <= -STRONG_T0) or (
        trend == "DOWN" and r1f is not None and r1f <= -0.15 and (bf is None or bf <= 40)
    )
    if strong_up and not strong_down:
        return "BULLISH"
    if strong_down and not strong_up:
        return "BEARISH"
    if trend == "FLAT" or (r1f is not None and abs(r1f) < NOISE_1H):
        return "NEUTRAL"
    if trend == "UP" and r1f is not None and r1f >= 0:
        return "BULLISH"
    if trend == "DOWN" and r1f is not None and r1f <= 0:
        return "BEARISH"
    return "UNCLEAR"


def _regime_verdict(ananta_market: str, independent: str) -> Tuple[str, str]:
    a = (ananta_market or "").replace("TREND_UP", "BULL").replace("BULLISH", "BULL")
    if a in ("BULL_TRENDING", "BULLISH_TRENDING"):
        a = "BULL"
    if not a or independent == "UNCLEAR":
        return "UNCERTAIN", "missing Ananta label or independent unclear"
    if a == "BULL" and independent == "BULLISH":
        return "SUPPORTED", "Ananta BULL vs independent bid"
    if a == "BULL" and independent == "BEARISH":
        return "MISCLASSIFIED", "Ananta BULL vs independent offer"
    if a == "BULL" and independent == "NEUTRAL":
        return "UNCERTAIN", "Ananta BULL vs independent chop — not enough to convict"
    if a == "NEUTRAL" and independent == "NEUTRAL":
        return "SUPPORTED", "Ananta NEUTRAL vs independent chop"
    if a == "NEUTRAL" and independent == "BULLISH":
        return "MISCLASSIFIED", "Ananta NEUTRAL vs independent bid"
    if a == "NEUTRAL" and independent == "BEARISH":
        return "MISCLASSIFIED", "Ananta NEUTRAL vs independent offer"
    if a in ("BEAR", "BEARISH") and independent == "BEARISH":
        return "SUPPORTED", "Ananta BEAR vs independent offer"
    if a in ("BEAR", "BEARISH") and independent == "BULLISH":
        return "MISCLASSIFIED", "Ananta BEAR vs independent bid"
    return "UNCERTAIN", f"unmapped pair Ananta={a} independent={independent}"


def _fwd_btc(obs: dict) -> dict:
    ot = obs.get("outcome_truth") or {}
    slot = (ot.get("assets") or {}).get("BTC/USD") or {}

    def _ret(key: str) -> Optional[float]:
        cell = slot.get(key)
        if isinstance(cell, dict) and cell.get("ret_pct") is not None:
            try:
                return float(cell["ret_pct"])
            except (TypeError, ValueError):
                return None
        return None

    return {
        "status": ot.get("status") or "pending",
        "r15": _ret("+15m"),
        "r1h": _ret("+1h"),
        "r4h": _ret("+4h"),
    }


def _decision_verdict(decision: str, fwd: dict) -> Tuple[str, str]:
    dec = (decision or "").upper()
    r1 = fwd.get("r1h")
    r4 = fwd.get("r4h")
    if r1 is None:
        return "UNCERTAIN", "+1h not due — do not score"
    if dec == "TAKE":
        if r1 >= COST_1H:
            return "SUPPORTED", f"TAKE then BTC +1h={r1}%"
        if r1 <= -COST_1H:
            return "COSTLY", f"TAKE then BTC +1h={r1}%"
        return "UNCERTAIN", f"TAKE then BTC +1h={r1}% inside noise"
    # WAIT / SKIP = abstention. BTC path is opportunity-cost, not strategy PnL.
    if r1 >= COST_1H:
        extra = f" (+4h={r4}%)" if r4 is not None else ""
        return "COSTLY", f"{dec} then BTC rallied +1h={r1}%{extra}"
    if r1 <= -COST_1H:
        extra = f" (+4h={r4}%)" if r4 is not None else ""
        return "PROTECTIVE", f"{dec} then BTC dropped +1h={r1}%{extra}"
    extra = f" +4h={r4}%" if r4 is not None else ""
    return "UNCERTAIN", f"{dec} then BTC +1h={r1}% chop{extra}"


def _gate_notes(obs: dict) -> List[str]:
    st = obs.get("system_truth") or {}
    notes = []
    for o in st.get("strategy_observations") or []:
        key = str(o.get("strategy") or o.get("key") or "")
        skip = str(o.get("skip_reason") or "")
        setup = bool(o.get("setup_detected"))
        if key in ("hunter", "squeeze", "bollinger-mr") and (setup or skip):
            notes.append(f"{key}:{('setup' if setup else 'no-setup')}:{skip or o.get('decision')}")
    return notes[:12]


def audit_observations(rows: Optional[List[dict]] = None) -> dict:
    rows = rows if rows is not None else _load_rows()
    scored: List[dict] = []
    regime_c = Counter()
    decision_c = Counter()
    dec_type = Counter()
    hunter_skip = Counter()

    for obs in rows:
        st = obs.get("system_truth") or {}
        a_mkt, a_asset = _ananta_btc_regime(obs)
        ind = _independent_btc(obs)
        ind_label = _independent_label(ind)
        r_verdict, r_why = _regime_verdict(a_mkt, ind_label)
        fwd = _fwd_btc(obs)
        decision = str(st.get("agent_decision") or "UNKNOWN").upper()
        d_verdict, d_why = _decision_verdict(decision, fwd)
        regime_c[r_verdict] += 1
        decision_c[d_verdict] += 1
        dec_type[decision] += 1
        for o in st.get("strategy_observations") or []:
            if str(o.get("strategy") or "") == "hunter":
                hunter_skip[str(o.get("skip_reason") or o.get("decision") or "?")] += 1
        scored.append({
            "ts": obs.get("ts"),
            "decision": decision,
            "ananta_btc_market": a_mkt,
            "ananta_btc_asset": a_asset,
            "independent": ind_label,
            "t0_trend": ind.get("trend"),
            "t0_ret_1h": ind.get("ret_1h"),
            "t0_breadth": ind.get("breadth"),
            "fwd_1h": fwd.get("r1h"),
            "fwd_4h": fwd.get("r4h"),
            "regime_audit": r_verdict,
            "regime_why": r_why,
            "decision_audit": d_verdict,
            "decision_why": d_why,
        })

    n = len(rows)
    n_1h = sum(1 for s in scored if s.get("fwd_1h") is not None)
    costly = [s for s in scored if s["decision_audit"] == "COSTLY"]
    protective = [s for s in scored if s["decision_audit"] == "PROTECTIVE"]
    mis = [s for s in scored if s["regime_audit"] == "MISCLASSIFIED"]

    def _mean(vals):
        xs = [v for v in vals if v is not None]
        return round(sum(xs) / len(xs), 4) if xs else None

    report = {
        "schema": "audit_v0",
        "ts": datetime.now(timezone.utc).isoformat(),
        "n_observations": n,
        "n_with_fwd_1h": n_1h,
        "decisions": dict(dec_type),
        "regime_audit": dict(regime_c),
        "decision_audit": dict(decision_c),
        "mean_fwd_1h_all": _mean([s.get("fwd_1h") for s in scored]),
        "mean_fwd_1h_after_skip_wait": _mean(
            [s.get("fwd_1h") for s in scored if s["decision"] in ("SKIP", "WAIT")]
        ),
        "hunter_skip_reasons_top": dict(hunter_skip.most_common(8)),
        "examples_misclassified": mis[:6],
        "examples_costly": costly[:6],
        "examples_protective": protective[:6],
        "laws": {
            "ananta_regime_is_hypothesis": True,
            "btc_path_is_not_strategy_pnl": True,
            "no_keep": True,
            "no_auto_mutation": True,
        },
        "note": (
            "Thin audit. SUPPORTED/MISCLASSIFIED is about Ananta's BTC market label "
            "vs independent Kraken flags — not Wave A KEEP. Decision COSTLY means "
            "BTC rallied after WAIT/SKIP; it does not prove a strategy TAKE was due."
        ),
    }
    return report


def save_audit_report(report: dict) -> Path:
    AUDIT_REPORT.write_text(json.dumps(report, indent=2, default=str))
    return AUDIT_REPORT


def print_audit(report: Optional[dict] = None) -> None:
    report = report or audit_observations()
    path = save_audit_report(report)
    print()
    print("STAGE 3 AUDIT  (thin — log only, not KEEP)")
    print("=" * 64)
    print("Ananta regime = hypothesis. BTC path ≠ strategy PnL. No auto mutation.")
    print("-" * 64)
    print(
        f"  observations={report.get('n_observations')}  "
        f"with +1h outcome={report.get('n_with_fwd_1h')}"
    )
    print(f"  decisions     : {report.get('decisions')}")
    print(f"  regime audit  : {report.get('regime_audit')}")
    print(f"  decision audit: {report.get('decision_audit')}")
    print(
        f"  mean BTC +1h after SKIP/WAIT: {report.get('mean_fwd_1h_after_skip_wait')}%"
    )
    print(f"  hunter skip reasons: {report.get('hunter_skip_reasons_top')}")
    print("-" * 64)
    print("REGIME — Ananta BTC market label vs independent Kraken")
    print("  SUPPORTED      label matched independent bid/chop/offer")
    print("  MISCLASSIFIED  label disagreed with a clear independent state")
    print("  UNCERTAIN      chop, missing horizon, or weak independent signal")
    print("-" * 64)
    print("DECISION — WAIT/SKIP vs subsequent BTC path (opportunity cost)")
    print(f"  noise band |+1h| < {NOISE_1H}% → UNCERTAIN")
    print(f"  |+1h| ≥ {COST_1H}% → COSTLY (rally after sit-out) or PROTECTIVE (drop)")
    print("-" * 64)

    def _ex(title, items):
        print(title)
        if not items:
            print("  (none)")
            return
        for s in items[:5]:
            print(
                f"  {str(s.get('ts') or '')[:19]}  "
                f"dec={s.get('decision')}  ananta={s.get('ananta_btc_market')}  "
                f"indep={s.get('independent')}  +1h={s.get('fwd_1h')}  "
                f"→ {s.get('regime_audit')}/{s.get('decision_audit')}"
            )
            why = s.get("regime_why") if "MISCLASSIFIED" in title else s.get("decision_why")
            if why:
                print(f"      {why}")

    _ex("MISCLASSIFIED regime examples", report.get("examples_misclassified") or [])
    _ex("COSTLY sit-out examples", report.get("examples_costly") or [])
    _ex("PROTECTIVE sit-out examples", report.get("examples_protective") or [])
    print("-" * 64)
    print("  Not KEEP. Need TAKE outcomes for promotion. Wave A stays WATCH.")
    print(f"  saved: {path}")
    print("=" * 64)
    print()
