"""Thesis → counter-thesis → cited evidence → adjudication.

Deterministic. No extra LLM agents. No Bull/Bear personas.
Claims must cite System / Market / Outcome rows (or charter/gate).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from src.intelligence.gates import evaluate_gates
from src.intelligence.profiles import RiskProfile, get_profile
from src.intelligence.schema import (
    WAVE_A,
    ConfidenceTriplet,
    EvidenceCitation,
    TypedDecision,
    _norm_action,
)
from src.intelligence.user_context import get_user_context

# Wave A allowed regimes — locked, mirrors Ananta WAVE_A_REGIMES. Do not expand.
WAVE_A_REGIMES = {
    "hunter": frozenset({"REVERSAL"}),
    "squeeze": frozenset({"COMPRESSION"}),
    "bollinger-mr": frozenset({"RANGE", "COMPRESSION"}),
}


def adjudicate(
    observation: Optional[dict] = None,
    *,
    profile: Optional[RiskProfile] = None,
    user_intent: Optional[str] = None,
    user_confirmed: bool = False,
    regime_audit: Optional[str] = None,
) -> TypedDecision:
    """Produce one typed decision from one observation_v0 row (or DATA_GAP)."""
    profile = profile or get_profile()
    ctx = get_user_context()
    intent = (user_intent or ctx.intent or "OBSERVE").upper()

    if not observation:
        return _data_gap(profile, intent, "no observation row")

    st = observation.get("system_truth") or {}
    mt = observation.get("market_truth") or {}
    ot = observation.get("outcome_truth") or {}
    obs_id = observation.get("obs_id") or st.get("obs_id")
    cycle_id = st.get("cycle_id")
    source = observation.get("source") or "live_paper"
    ananta_ok = bool(st.get("ananta_ok", True))
    rows = list(st.get("strategy_observations") or [])
    missing = not rows and not st.get("n_setups") and st.get("agent_decision") in (None, "UNKNOWN")

    rec, strategy_key, symbol, skip_reason, setup, thesis, counter, cites = _from_observations(
        rows, st, mt, ot, observation
    )

    understanding, evidence, decision_c = _confidences(st, mt, ot, rows, rec, source)
    conf = ConfidenceTriplet(
        understanding=understanding,
        evidence=evidence,
        decision=decision_c,
    )

    port = st.get("portfolio") or {}
    slots = int(port.get("slots_used") or port.get("open_positions") or 0 or 0)
    enabled = _enabled_count(st, rows)

    allowed, issued, hits = evaluate_gates(
        recommended_action=rec,
        strategy_key=strategy_key,
        setup_detected=setup,
        skip_reason=skip_reason,
        profile=profile,
        user_intent=intent,
        ananta_ok=ananta_ok,
        kill_switch=bool(st.get("kill_switch") or port.get("kill_switch")),
        slots_used=slots,
        enabled_count=enabled,
        evidence_confidence=conf.evidence,
        decision_confidence=conf.decision,
        regime_audit=regime_audit,
        user_confirmed=user_confirmed,
        missing_observations=missing,
    )

    adjudication = _adjudicate_text(rec, issued, strategy_key, skip_reason, setup, source, profile)

    return TypedDecision(
        obs_id=obs_id,
        cycle_id=cycle_id,
        strategy_key=strategy_key,
        symbol=symbol,
        recommended_action=rec,
        issued_action=issued,
        skip_reason=skip_reason,
        thesis=thesis,
        counter_thesis=counter,
        adjudication=adjudication,
        citations=cites,
        confidences=conf,
        profile=profile.name,
        user_intent=intent,
        gates=hits,
        execution_allowed=allowed,
        source=source,
        notes="Wave A WATCH. Recommendation is not KEEP. Historical TAKE-eq is not a paper fill.",
    )


def _from_observations(
    rows: List[dict],
    st: dict,
    mt: dict,
    ot: dict,
    observation: dict,
) -> Tuple[str, Optional[str], Optional[str], Optional[str], Optional[bool], str, str, List[EvidenceCitation]]:
    cites: List[EvidenceCitation] = []
    obs_id = observation.get("obs_id") or st.get("obs_id") or "unknown"
    cites.append(
        EvidenceCitation("system", str(obs_id), f"schema={observation.get('schema')} source={observation.get('source')}")
    )

    btc = mt.get("btc") or {}
    if mt:
        cites.append(
            EvidenceCitation(
                "market",
                str(obs_id),
                f"BTC trend={btc.get('trend_flag')} ret_1h={btc.get('ret_1h_pct')} ok={mt.get('ok')}",
            )
        )
    if ot and (ot.get("fwd_1h_pct") is not None or ot.get("btc_fwd_1h_pct") is not None):
        fwd = ot.get("fwd_1h_pct", ot.get("btc_fwd_1h_pct"))
        cites.append(EvidenceCitation("outcome", str(obs_id), f"fwd_1h_pct={fwd}"))

    if not rows:
        decision = _norm_action(st.get("agent_decision") or "WAIT")
        thesis = "No per-strategy observations on this row. Missing information is DATA_GAP, not 'no setup'."
        counter = "Do not invent a setup Ananta did not emit."
        cites.append(EvidenceCitation("charter", "laws.unknown", "UNKNOWN ≠ no setup"))
        return decision if decision in ("WAIT", "SKIP") else "WAIT", None, None, None, None, thesis, counter, cites

    take_eq: List[dict] = []
    skips: List[dict] = []
    waits: List[dict] = []
    for o in rows:
        setup = bool(o.get("setup_detected"))
        dec = _norm_action(o.get("decision") or ("TAKE" if setup else "WAIT"))
        skip = str(o.get("skip_reason") or "")
        if setup and skip.upper() != "REGIME_FILTERED":
            take_eq.append(o)
        elif setup or dec == "SKIP" or skip.upper() == "REGIME_FILTERED":
            skips.append(o)
        else:
            waits.append(o)

    if take_eq:
        chosen = take_eq[0]
        rec = "TAKE"
        setup_flag: Optional[bool] = True
        skip_reason = chosen.get("skip_reason")
    elif skips:
        chosen = skips[0]
        rec = "SKIP"
        setup_flag = bool(chosen.get("setup_detected"))
        skip_reason = chosen.get("skip_reason") or "SKIP"
    else:
        chosen = waits[0] if waits else rows[0]
        rec = "WAIT"
        setup_flag = bool(chosen.get("setup_detected"))
        skip_reason = chosen.get("skip_reason")

    strategy_key = (chosen.get("strategy") or chosen.get("strategy_key") or "").lower() or None
    symbol = chosen.get("symbol")
    regime = chosen.get("regime") or _asset_regime(st, symbol)

    thesis = _thesis(chosen, rec, regime, len(take_eq), len(skips), len(rows))
    counter = _counter_thesis(chosen, rec, st, mt, regime, strategy_key)
    cites.append(
        EvidenceCitation(
            "system",
            f"{obs_id}:{strategy_key}",
            f"setup={chosen.get('setup_detected')} dec={chosen.get('decision')} "
            f"skip={chosen.get('skip_reason')} regime={regime}",
        )
    )
    if rec == "SKIP" and str(skip_reason or "").upper() == "REGIME_FILTERED":
        cites.append(
            EvidenceCitation(
                "gate",
                f"router:{strategy_key}",
                f"Wave A allows {sorted(WAVE_A_REGIMES.get(strategy_key or '', []))} ; saw {regime}",
            )
        )
    return rec, strategy_key, symbol, skip_reason, setup_flag, thesis, counter, cites


def _thesis(chosen: dict, rec: str, regime: Any, n_take: int, n_skip: int, n_rows: int) -> str:
    key = chosen.get("strategy") or "?"
    if rec == "TAKE":
        return (
            f"{key} setup on {chosen.get('symbol')} in {regime} is TAKE-equivalent "
            f"({n_take} take-eq / {n_rows} strategy rows). This is a recommendation, not KEEP."
        )
    if rec == "SKIP":
        return (
            f"{key} produced a setup or skip on {chosen.get('symbol')} "
            f"(skip_reason={chosen.get('skip_reason')}, regime={regime}). SKIP is a decision."
        )
    return (
        f"No actionable setup this observation ({n_rows} rows, take-eq={n_take}, skip={n_skip}). WAIT."
    )


def _counter_thesis(chosen: dict, rec: str, st: dict, mt: dict, regime: Any, strategy_key: Optional[str]) -> str:
    bits: List[str] = []
    ananta = _asset_regime(st, chosen.get("symbol"))
    btc = (mt.get("btc") or {})
    trend = str(btc.get("trend_flag") or "")
    if ananta and trend and str(ananta).upper() not in ("", str(trend).upper()):
        bits.append(
            f"Ananta regime={ananta} vs independent 1h trend_flag={trend}. "
            "Ananta regime is a hypothesis, not proof."
        )
    allowed = WAVE_A_REGIMES.get(strategy_key or "")
    if allowed and regime and str(regime).upper() not in allowed:
        bits.append(
            f"Implementation emitted a {strategy_key} setup in {regime}; "
            f"Wave A policy allows {sorted(allowed)} only. Contradiction, not a trade."
        )
    if rec == "TAKE":
        bits.append("Wave A is WATCH. Live TAKE evidence is still insufficient for KEEP. Historical TAKE-eq ≠ paper TAKE.")
    if not bits:
        bits.append("Counter-thesis: sit-out can be costly or protective; do not treat WAIT as strategy success.")
    return " ".join(bits)


def _adjudicate_text(
    rec: str,
    issued: str,
    strategy_key: Optional[str],
    skip_reason: Optional[str],
    setup: Optional[bool],
    source: str,
    profile: RiskProfile,
) -> str:
    parts = [
        f"recommended={rec}",
        f"issued={issued}",
        f"profile={profile.name}",
        f"source={source}",
    ]
    if strategy_key:
        parts.append(f"strategy={strategy_key}")
    if skip_reason:
        parts.append(f"skip_reason={skip_reason}")
    if rec == "TAKE" and issued != "TAKE":
        parts.append("TAKE blocked by hard gates (Wave A WATCH / Ananta authority). Not KEEP.")
    if rec == "SKIP":
        parts.append("SKIP is first-class; opportunity cost is measured later, not assumed zero.")
    if rec == "WAIT":
        parts.append("WAIT is not KEEP. Process mark only.")
    if setup is None:
        parts.append("DATA_GAP on setup_detected.")
    return "; ".join(parts)


def _confidences(st: dict, mt: dict, ot: dict, rows: list, rec: str, source: str) -> Tuple[float, float, float]:
    understanding = 0.35
    if rows:
        understanding = 0.75
        if all("setup_detected" in (r or {}) for r in rows):
            understanding = 0.85
    if not st.get("ananta_ok", True):
        understanding = min(understanding, 0.40)

    evidence = 0.20  # live TAKE=0 is the current lab fact; stay humble
    if source == "historical_lab":
        evidence = 0.45  # 1y replay exists but TAKE-eq ≠ KEEP
    if ot and ot.get("fwd_1h_pct") is not None:
        evidence = min(0.55, evidence + 0.10)
    if not mt.get("ok", True) and mt:
        evidence = min(evidence, 0.25)

    if rec == "WAIT" and rows:
        decision = 0.70
    elif rec == "SKIP":
        decision = 0.65
    elif rec == "TAKE":
        decision = 0.55  # recommendation only
    else:
        decision = 0.40
    return understanding, evidence, decision


def _asset_regime(st: dict, symbol: Optional[str]) -> Any:
    regimes = st.get("regimes_by_symbol") or {}
    if symbol and symbol in regimes:
        raw = regimes[symbol]
    elif "BTC/USD" in regimes:
        raw = regimes["BTC/USD"]
    else:
        raw = next(iter(regimes.values()), None) if regimes else None
    if isinstance(raw, dict):
        return raw.get("asset") or raw.get("market")
    return raw


def _enabled_count(st: dict, rows: List[dict]) -> int:
    flags = [r for r in rows if r.get("enabled") is True]
    if flags:
        return len({(r.get("strategy") or r.get("strategy_key")) for r in flags})
    return int(st.get("enabled_count") or 0)


def _data_gap(profile: RiskProfile, intent: str, why: str) -> TypedDecision:
    allowed, issued, hits = evaluate_gates(
        recommended_action="WAIT",
        profile=profile,
        user_intent=intent,
        missing_observations=True,
        ananta_ok=False,
    )
    return TypedDecision(
        recommended_action="WAIT",
        issued_action=issued,
        thesis=f"DATA_GAP: {why}",
        counter_thesis="Do not treat silence as no-setup.",
        adjudication=f"issued=WAIT; {why}",
        citations=[EvidenceCitation("charter", "laws.unknown", why)],
        confidences=ConfidenceTriplet(understanding=0.2, evidence=0.1, decision=0.6),
        profile=profile.name,
        user_intent=intent,
        gates=hits,
        execution_allowed=allowed,
        notes="DATA_GAP",
    )
