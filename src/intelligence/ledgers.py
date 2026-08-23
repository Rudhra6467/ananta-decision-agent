"""Typed decision ledger + first-class SKIP.

Does not replace decision_log.json / cycle_log.jsonl / opportunity_log.jsonl.
Appends typed_decision.jsonl so DI records are reconstructable.
SKIP is a decision with a reason, not the absence of TAKE.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.intelligence.schema import TypedDecision

TYPED_LOG = Path("typed_decision.jsonl")


def record_decision(decision: TypedDecision) -> bool:
    try:
        with TYPED_LOG.open("a") as f:
            f.write(json.dumps(decision.as_dict(), default=str) + "\n")
    except Exception:
        return False
    _mirror_legacy(decision)
    return True


def record_skip(
    *,
    cycle_id: Optional[str],
    obs_id: Optional[str],
    strategy_key: Optional[str],
    symbol: Optional[str],
    skip_reason: str,
    setup_detected: bool,
    extra: Optional[dict] = None,
) -> bool:
    """First-class SKIP row. Opportunity cost is attached later by attribution."""
    from src.intelligence.schema import EvidenceCitation, ConfidenceTriplet, GateHit

    d = TypedDecision(
        obs_id=obs_id,
        cycle_id=cycle_id,
        strategy_key=strategy_key,
        symbol=symbol,
        recommended_action="SKIP",
        issued_action="SKIP",
        skip_reason=skip_reason,
        thesis=f"SKIP {strategy_key} {symbol} reason={skip_reason} setup={setup_detected}",
        counter_thesis="SKIP opportunity cost is unknown until Outcome Truth is attached.",
        adjudication="SKIP is a decision. Not 'no setup'. Not KEEP.",
        citations=[
            EvidenceCitation("system", str(obs_id or cycle_id or ""), f"skip_reason={skip_reason}"),
        ],
        confidences=ConfidenceTriplet(understanding=0.7, evidence=0.2, decision=0.7),
        execution_allowed=False,
        notes="skip_ledger",
    )
    if extra:
        d.notes = f"skip_ledger {extra}"
    return record_decision(d)


def read_typed(limit: int = 20) -> List[dict]:
    if not TYPED_LOG.exists():
        return []
    rows: List[dict] = []
    try:
        for line in TYPED_LOG.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    except Exception:
        return []
    return rows[-limit:]


def _mirror_legacy(decision: TypedDecision) -> None:
    """Best-effort: keep Phase 4 ledgers in sync. Fail soft."""
    try:
        from src.tools.decision_log import save_decision
        from src.tools.cycle_log import log_decision, log_opportunities, get_last_cycle_id, start_cycle

        cid = decision.cycle_id or get_last_cycle_id() or start_cycle(notes="typed_decision")
        save_decision(
            {
                "cycle_id": cid,
                "obs_id": decision.obs_id,
                "symbol": decision.symbol,
                "strategy": decision.strategy_key,
                "strategy_key": decision.strategy_key,
                "action": decision.issued_action,
                "recommended_action": decision.recommended_action,
                "reason": decision.adjudication,
                "notes": decision.notes,
                "confidence": None,  # never store a blended number
                "confidences": decision.confidences.as_dict(),
                "status": "observed",
                "schema": decision.schema,
                "profile": decision.profile,
                "execution_allowed": decision.execution_allowed,
            }
        )
        log_decision(
            cid,
            action=decision.issued_action,
            strategy=decision.strategy_key,
            strategy_key=decision.strategy_key,
            reason=decision.adjudication,
            extra={
                "obs_id": decision.obs_id,
                "recommended_action": decision.recommended_action,
                "skip_reason": decision.skip_reason,
                "schema": decision.schema,
            },
        )
        if decision.issued_action in ("SKIP", "WAIT", "HOLD"):
            log_opportunities(
                cid,
                candidates=[
                    {
                        "strategy": decision.strategy_key,
                        "symbol": decision.symbol,
                        "decision": decision.issued_action,
                        "skip_reason": decision.skip_reason,
                    }
                ],
                chosen_action=decision.issued_action,
                chosen_strategy=decision.strategy_key,
            )
    except Exception:
        return
