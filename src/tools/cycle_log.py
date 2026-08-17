"""
Cycle + opportunity ledger (Phase 4.1 / 4.4).

Append-only JSONL stores. Fail soft — never break the CLI if disk write fails.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

CYCLE_LOG_FILE = "cycle_log.jsonl"
OPPORTUNITY_LOG_FILE = "opportunity_log.jsonl"
AGENT_API_VERSION = 0


def new_cycle_id() -> str:
    return f"cyc_{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:8]}"


def _append_jsonl(path: str, record: dict) -> bool:
    try:
        with open(path, "a") as f:
            f.write(json.dumps(record, default=str) + "\n")
        return True
    except Exception:
        return False


def start_cycle(
    *,
    regime: Optional[str] = None,
    symbol: Optional[str] = None,
    price: Any = None,
    equity: Any = None,
    open_positions: Any = None,
    enabled_strategies: Optional[List[str]] = None,
    enabled_count: Any = None,
    load_level: Optional[str] = None,
    notes: str = "",
) -> str:
    """
    Open a new cycle. Returns cycle_id (always, even if write fails).
    """
    cycle_id = new_cycle_id()
    record = {
        "cycle_id": cycle_id,
        "timestamp": datetime.utcnow().isoformat(),
        "agent_api_version": AGENT_API_VERSION,
        "event": "cycle_start",
        "regime": regime,
        "symbol": symbol,
        "price": price,
        "equity": equity,
        "open_positions": open_positions,
        "enabled_strategies": enabled_strategies or [],
        "enabled_count": enabled_count,
        "load_level": load_level,
        "notes": notes,
    }
    _append_jsonl(CYCLE_LOG_FILE, record)
    return cycle_id


def log_decision(
    cycle_id: str,
    *,
    action: str,
    strategy: Optional[str] = None,
    strategy_key: Optional[str] = None,
    confidence: Any = None,
    reason: Optional[str] = None,
    top_recommendation: Optional[str] = None,
    ranked_options: Optional[List[dict]] = None,
    user_confirmed: Optional[bool] = None,
    user_override: Optional[bool] = None,
    status: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> bool:
    """Log a decision event tied to a cycle (TAKE/SKIP/ENABLE/WAIT/...)."""
    record = {
        "cycle_id": cycle_id,
        "timestamp": datetime.utcnow().isoformat(),
        "agent_api_version": AGENT_API_VERSION,
        "event": "decision",
        "action": (action or "UNKNOWN").upper(),
        "strategy": strategy,
        "strategy_key": strategy_key,
        "confidence": confidence,
        "reason": reason,
        "top_recommendation": top_recommendation,
        "ranked_options": ranked_options or [],
        "user_confirmed": user_confirmed,
        "user_override": user_override,
        "status": status,
    }
    if extra:
        record.update(extra)
    return _append_jsonl(CYCLE_LOG_FILE, record)


def log_opportunities(
    cycle_id: str,
    candidates: List[dict],
    *,
    chosen_action: str,
    chosen_strategy: Optional[str] = None,
    regime: Optional[str] = None,
) -> bool:
    """
    Opportunity ledger: what was available and what was chosen (including SKIP).

    candidates: list of {name, confidence, reason, style?} from ranking
    chosen_action: TAKE | SKIP | WAIT | ENABLE | ...
    """
    record = {
        "cycle_id": cycle_id,
        "timestamp": datetime.utcnow().isoformat(),
        "agent_api_version": AGENT_API_VERSION,
        "event": "opportunities",
        "regime": regime,
        "candidates": candidates or [],
        "chosen_action": (chosen_action or "UNKNOWN").upper(),
        "chosen_strategy": chosen_strategy,
        "skipped": (chosen_action or "").upper() in ("SKIP", "WAIT", "HOLD"),
    }
    return _append_jsonl(OPPORTUNITY_LOG_FILE, record)


def log_outcome_link(
    cycle_id: str,
    *,
    equity: Any = None,
    open_positions: Any = None,
    note: str = "",
) -> bool:
    """Best-effort outcome linkage for a prior cycle."""
    record = {
        "cycle_id": cycle_id,
        "timestamp": datetime.utcnow().isoformat(),
        "agent_api_version": AGENT_API_VERSION,
        "event": "outcome_link",
        "equity": equity,
        "open_positions": open_positions,
        "note": note,
    }
    return _append_jsonl(CYCLE_LOG_FILE, record)


def read_recent_cycles(limit: int = 20) -> List[dict]:
    if not os.path.exists(CYCLE_LOG_FILE):
        return []
    rows: List[dict] = []
    try:
        with open(CYCLE_LOG_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
        return rows[-limit:]
    except Exception:
        return []


def read_recent_opportunities(limit: int = 20) -> List[dict]:
    if not os.path.exists(OPPORTUNITY_LOG_FILE):
        return []
    rows: List[dict] = []
    try:
        with open(OPPORTUNITY_LOG_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
        return rows[-limit:]
    except Exception:
        return []
