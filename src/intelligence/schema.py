"""Typed TAKE / SKIP / WAIT / HOLD / EXIT / REDUCE — decision_v0.

A bull claim that cannot point at an Observation row is a speech.
Three confidences stay separate. Never blend into one displayed score.

recommended_action = what the evidence argues.
issued_action      = what is allowed after hard gates + profile.
TAKE on Wave A is recommendable; it is not executable while WATCH.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.intelligence.laws import LAWS

SCHEMA = "decision_v0"

TRADE_ACTIONS = ("TAKE", "SKIP", "WAIT", "HOLD", "EXIT", "REDUCE")
CONTROL_ACTIONS = ("ENABLE", "DISABLE", "KEEP", "WATCH", "CUT", "CYCLE", "CANCEL")
ALL_ACTIONS = TRADE_ACTIONS + CONTROL_ACTIONS

CITATION_SOURCES = (
    "system",
    "market",
    "outcome",
    "historical",
    "paper",
    "user",
    "charter",
    "gate",
)

WAVE_A = ("hunter", "squeeze", "bollinger-mr")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class EvidenceCitation:
    source: str
    ref: str
    claim: str

    def __post_init__(self) -> None:
        src = (self.source or "").lower().strip()
        if src not in CITATION_SOURCES:
            self.source = "system"
        else:
            self.source = src
        self.ref = str(self.ref or "")
        self.claim = str(self.claim or "")

    def as_dict(self) -> Dict[str, str]:
        return {"source": self.source, "ref": self.ref, "claim": self.claim}


@dataclass
class ConfidenceTriplet:
    """understanding / evidence / decision — never one blended number."""

    understanding: float = 0.0
    evidence: float = 0.0
    decision: float = 0.0
    note: str = "three confidences; do not average"

    def __post_init__(self) -> None:
        self.understanding = _clamp01(self.understanding)
        self.evidence = _clamp01(self.evidence)
        self.decision = _clamp01(self.decision)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "understanding": round(self.understanding, 4),
            "evidence": round(self.evidence, 4),
            "decision": round(self.decision, 4),
            "note": self.note,
            "blended": None,
        }


@dataclass
class GateHit:
    code: str
    layer: str  # hard | profile | ananta
    passed: bool
    detail: str

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TypedDecision:
    schema: str = SCHEMA
    ts: str = ""
    obs_id: Optional[str] = None
    cycle_id: Optional[str] = None
    strategy_key: Optional[str] = None
    symbol: Optional[str] = None
    recommended_action: str = "WAIT"
    issued_action: str = "WAIT"
    skip_reason: Optional[str] = None
    thesis: str = ""
    counter_thesis: str = ""
    adjudication: str = ""
    citations: List[EvidenceCitation] = field(default_factory=list)
    confidences: ConfidenceTriplet = field(default_factory=ConfidenceTriplet)
    profile: str = "MODERATE"
    user_intent: str = "OBSERVE"
    gates: List[GateHit] = field(default_factory=list)
    execution_allowed: bool = False
    execution_authority: str = "ananta"
    wave_a_status: str = "WATCH"
    source: str = "live_paper"
    notes: str = ""
    knowledge_consult: Optional[Dict[str, Any]] = None
    keep: bool = False

    def __post_init__(self) -> None:
        if not self.ts:
            self.ts = _utc_now()
        self.recommended_action = _norm_action(self.recommended_action)
        self.issued_action = _norm_action(self.issued_action)

    @property
    def blocked(self) -> bool:
        return self.recommended_action == "TAKE" and not self.execution_allowed

    def as_dict(self) -> Dict[str, Any]:
        return {
            "schema": self.schema,
            "ts": self.ts,
            "obs_id": self.obs_id,
            "cycle_id": self.cycle_id,
            "strategy_key": self.strategy_key,
            "symbol": self.symbol,
            "recommended_action": self.recommended_action,
            "issued_action": self.issued_action,
            "skip_reason": self.skip_reason,
            "thesis": self.thesis,
            "counter_thesis": self.counter_thesis,
            "adjudication": self.adjudication,
            "citations": [c.as_dict() for c in self.citations],
            "confidences": self.confidences.as_dict(),
            "profile": self.profile,
            "user_intent": self.user_intent,
            "gates": [g.as_dict() for g in self.gates],
            "execution_allowed": self.execution_allowed,
            "execution_authority": self.execution_authority,
            "wave_a_status": self.wave_a_status,
            "source": self.source,
            "blocked": self.blocked,
            "notes": self.notes,
            "knowledge_consult": self.knowledge_consult,
            "keep": False,
            "laws": {
                **{k: LAWS[k] for k in (
                    "take_is_not_keep",
                    "take_eq_is_not_paper_take",
                    "paper_take_is_not_live_take",
                    "keep_is_earned_authority",
                    "live_take_zero_is_watch_not_gap",
                    "skip_is_a_decision",
                    "ananta_regime_is_hypothesis",
                    "hard_safety_outside_llm",
                )},
                "no_extra_agents": True,
            },
        }


def _clamp01(x: Any) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, v))


def _norm_action(raw: Any) -> str:
    s = str(raw or "WAIT").upper().strip()
    if s in ("ENTER", "BUY", "SELL"):
        return "TAKE"
    if s in ("SKIPPED",):
        return "SKIP"
    if s in ALL_ACTIONS:
        return s
    return "WAIT"


def is_trade_action(action: str) -> bool:
    return _norm_action(action) in TRADE_ACTIONS
