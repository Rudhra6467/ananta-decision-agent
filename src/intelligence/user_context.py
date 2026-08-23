"""User context and intent.

Intent is a mode, not a personality agent.
OBSERVE / RESEARCH never TAKE.
PROMOTE and AUTONOMOUS are blocked until evidence + human + Trust Report.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.intelligence.profiles import (
    DEFAULT_PROFILE,
    normalize_profile_name,
)
from src.memory import get_last_user_profile, load_memory, save_memory

CONTEXT_FILE = Path("user_context.json")

INTENTS = ("OBSERVE", "RESEARCH", "PAPER_TRADE", "PROMOTE", "AUTONOMOUS")


@dataclass
class UserContext:
    goal: str = "Learn Wave A without promoting"
    risk_tolerance: str = "Medium"
    capital: float = 0.0
    experience_level: str = "Intermediate"
    preferred_markets: List[str] = field(default_factory=lambda: ["Crypto"])
    intent: str = "OBSERVE"
    profile: str = DEFAULT_PROFILE
    confirmation_mode: str = "always"
    constraints: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["profile"] = normalize_profile_name(self.profile)
        d["intent"] = _norm_intent(self.intent)
        d["laws"] = {
            "intent_observe_forbids_take": True,
            "autonomous_blocked_until_trust_report": True,
            "promote_requires_human_and_take_evidence": True,
        }
        return d


def _norm_intent(raw: Optional[str]) -> str:
    s = str(raw or "OBSERVE").upper().strip().replace("-", "_").replace(" ", "_")
    aliases = {
        "WATCH": "OBSERVE",
        "OBS": "OBSERVE",
        "STUDY": "RESEARCH",
        "PAPER": "PAPER_TRADE",
        "TRADE": "PAPER_TRADE",
        "KEEP": "PROMOTE",
        "ENABLE": "PROMOTE",
        "AUTO": "AUTONOMOUS",
        "LIVE": "AUTONOMOUS",
    }
    s = aliases.get(s, s)
    return s if s in INTENTS else "OBSERVE"


def get_user_context() -> UserContext:
    stored = {}
    if CONTEXT_FILE.exists():
        try:
            stored = json.loads(CONTEXT_FILE.read_text()) or {}
        except Exception:
            stored = {}
    mem = load_memory() or {}
    profile_block = mem.get("user_profile") or get_last_user_profile() or {}
    intent = stored.get("intent") or mem.get("user_intent") or "OBSERVE"
    profile = stored.get("profile") or mem.get("risk_profile") or profile_block.get("risk_tolerance") or DEFAULT_PROFILE
    constraints = stored.get("constraints") or [
        "Wave A WATCH",
        "No extra agents",
        "No S5 H1/H2/H3 until tape accumulates",
        "Hard safety outside LLM",
        "Ananta owns execution",
    ]
    return UserContext(
        goal=stored.get("goal") or profile_block.get("user_goal") or "Learn Wave A without promoting",
        risk_tolerance=stored.get("risk_tolerance") or profile_block.get("risk_tolerance") or "Medium",
        capital=float(stored.get("capital") or profile_block.get("capital") or 0.0 or 0),
        experience_level=stored.get("experience_level") or profile_block.get("experience_level") or "Intermediate",
        preferred_markets=list(stored.get("preferred_markets") or ["Crypto"]),
        intent=_norm_intent(intent),
        profile=normalize_profile_name(profile),
        confirmation_mode=stored.get("confirmation_mode") or "always",
        constraints=list(constraints),
    )


def set_user_intent(intent: str) -> UserContext:
    ctx = get_user_context()
    ctx.intent = _norm_intent(intent)
    if ctx.intent in ("PROMOTE", "AUTONOMOUS"):
        # Record the wish; orchestration still blocks it.
        if "blocked_until_evidence" not in ctx.constraints:
            ctx.constraints.append("blocked_until_evidence")
    _persist(ctx)
    mem = load_memory() or {}
    mem["user_intent"] = ctx.intent
    save_memory(mem)
    return ctx


def set_user_context(**kwargs: Any) -> UserContext:
    ctx = get_user_context()
    for k, v in kwargs.items():
        if hasattr(ctx, k) and v is not None:
            setattr(ctx, k, v)
    ctx.intent = _norm_intent(ctx.intent)
    ctx.profile = normalize_profile_name(ctx.profile)
    _persist(ctx)
    return ctx


def intent_allows_take(intent: str) -> bool:
    return _norm_intent(intent) in ("PAPER_TRADE",)


def _persist(ctx: UserContext) -> None:
    try:
        CONTEXT_FILE.write_text(json.dumps(ctx.as_dict(), indent=2))
    except Exception:
        pass
