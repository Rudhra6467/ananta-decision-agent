"""Autonomous-agent orchestration with safety gates.

observe → adjudicate → gate → record → (never self-execute TAKE)

This is the loop that will later run under SAFE/MODERATE/AGGRESSIVE.
Today it always stops before Ananta execution authority.
S5 experiments are not started from this loop.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from src.intelligence.adjudicate import adjudicate
from src.intelligence.experiments import try_run
from src.intelligence.ledgers import record_decision
from src.intelligence.profiles import get_profile
from src.intelligence.user_context import get_user_context, intent_allows_take


def run_cycle(
    observation: Optional[dict] = None,
    *,
    persist: bool = True,
    user_confirmed: bool = False,
) -> Dict[str, Any]:
    """One DI cycle. If observation is None, load the latest live row (or DATA_GAP)."""
    if observation is None:
        observation = _latest_live()
    profile = get_profile()
    ctx = get_user_context()
    decision = adjudicate(
        observation,
        profile=profile,
        user_intent=ctx.intent,
        user_confirmed=user_confirmed and intent_allows_take(ctx.intent),
    )
    from src.intelligence.consult import consult as knowledge_consult

    consult_report = knowledge_consult(observation, source="live")
    slim = {
        "flag": consult_report.get("flag"),
        "match": consult_report.get("match"),
        "n_key": consult_report.get("n_key"),
        "knowledge_action": consult_report.get("knowledge_action"),
        "why": consult_report.get("why"),
        "issued_override": False,
        "keep": False,
    }
    decision.knowledge_consult = slim
    decision.keep = False
    if persist:
        record_decision(decision)

    payload = {
        "ok": True,
        "decision": decision.as_dict(),
        "knowledge_consult": slim,
        "would_execute": False,
        "execute_blocked_by": _execute_block_reasons(decision),
        "profile": profile.name,
        "intent": ctx.intent,
        "s5": "parked",
    }
    return payload


def propose_execution(decision_dict: dict) -> Dict[str, Any]:
    """The only legal 'execution' step: refuse, with reasons.

    A future constrained-autonomy mode will hand a proposal to Ananta's
    paper order API. This package will still not mutate Wave A.
    """
    return {
        "ok": False,
        "executed": False,
        "authority": "ananta",
        "reason": "Decision Intelligence proposes. Ananta executes. Wave A is WATCH.",
        "recommended_action": decision_dict.get("recommended_action"),
        "issued_action": decision_dict.get("issued_action"),
        "execution_allowed": False,
    }


def refuse_s5(exp_id: str) -> Dict[str, Any]:
    return try_run(exp_id)


def _execute_block_reasons(decision) -> list:
    reasons = []
    if not decision.execution_allowed:
        reasons.append("EXECUTION_NOT_ALLOWED")
    if decision.recommended_action == "TAKE":
        reasons.append("WAVE_A_WATCH")
        reasons.append("ANANTA_AUTHORITY")
    reasons.append("NO_SELF_FILL")
    return reasons


def _latest_live() -> Optional[dict]:
    try:
        from src.tools.observation_log import read_recent_observations

        rows = read_recent_observations(limit=1)
        return rows[0] if rows else None
    except Exception:
        return None
