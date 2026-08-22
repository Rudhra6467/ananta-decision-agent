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


def get_last_cycle_id() -> Optional[str]:
    """Return most recent cycle_id from cycle_start events, if any."""
    rows = read_recent_cycles(limit=200)
    for row in reversed(rows):
        if row.get("event") == "cycle_start" and row.get("cycle_id"):
            return row["cycle_id"]
    for row in reversed(rows):
        if row.get("cycle_id"):
            return row["cycle_id"]
    return None


def infer_cycle_action(result: dict) -> str:
    """Map graph result + user choice to TAKE/SKIP/WAIT/ENABLE/CANCEL."""
    explicit = str(result.get("_user_action") or "").upper().strip()
    if explicit in ("TAKE", "SKIP", "WAIT", "ENABLE", "CANCEL", "HOLD", "REDUCE", "EXIT"):
        return explicit
    status = str(result.get("execution_status") or "")
    top = result.get("decision")
    if "No strategy selected" in status or status.lower() == "skipped":
        return "SKIP"
    if "Cancelled" in status or "REJECTED" in status:
        return "CANCEL"
    if "WAIT" in status.upper():
        return "WAIT"
    if "enabled" in status.lower():
        return "ENABLE"
    if top and str(top).upper() in ("WAIT", "SKIP", "HOLD"):
        return str(top).upper()
    if top:
        return "TAKE"
    return "WAIT"


def wave_a_snapshot(marks_limit: int = 50) -> dict:
    """
    Light post-cycle helper: summarize Wave A strategies from decision marks + enables.
    Human still decides KEEP/WATCH/CUT; this only suggests.

    WAIT/NO_SETUP process marks are NOT strategy-success evidence.
    KEEP suggestions require TAKE outcome marks.
    """
    wave = ["hunter", "squeeze", "bollinger-mr"]
    try:
        from src.tools.decision_log import get_recent_decisions
        decisions = get_recent_decisions(limit=marks_limit)
    except Exception:
        decisions = []

    summary = {}
    for key in wave:
        related = [
            d for d in decisions
            if (
                key in str(d.get("strategy_key") or "").lower()
                or key in str(d.get("strategy") or "").lower()
                or key in str(d.get("top_recommendation") or "").lower()
            )
            and str(d.get("action") or "").upper() not in (
                "ENABLE", "DISABLE", "KEEP", "WATCH", "CUT", "CYCLE",
            )
            and str(d.get("status") or "").lower() not in ("enabled", "disabled")
            and str(d.get("strategy_key") or "").lower() != "manual"
            and str(d.get("status") or "").lower() not in ("keep", "watch", "cut")
        ]
        takes = [
            d for d in related
            if str(d.get("action") or "").upper() == "TAKE"
            or str(d.get("status") or "").lower() == "filled"
        ]
        waits = [
            d for d in related
            if str(d.get("action") or "").upper() in ("WAIT", "SKIP", "SKIPPED")
            or str(d.get("status") or "").lower() in ("skipped", "wait")
        ]
        take_good = sum(1 for d in takes if d.get("outcome") == "good")
        take_bad = sum(1 for d in takes if d.get("outcome") == "bad")
        take_neu = sum(1 for d in takes if d.get("outcome") == "neutral")
        take_pend = sum(1 for d in takes if d.get("outcome") == "pending")
        wait_good = sum(1 for d in waits if d.get("outcome") == "good")
        wait_bad = sum(1 for d in waits if d.get("outcome") == "bad")
        wait_neu = sum(1 for d in waits if d.get("outcome") == "neutral")
        wait_pend = sum(1 for d in waits if d.get("outcome") == "pending")
        good, bad, neutral, pending = take_good, take_bad, take_neu, take_pend
        total_marked = good + bad + neutral
        if total_marked == 0 and (wait_good + wait_bad + wait_neu) == 0:
            suggestion = "WATCH"
            note = "No marked outcomes yet — keep gathering evidence."
        elif total_marked == 0:
            suggestion = "WATCH"
            note = (
                f"INSUFFICIENT_EVIDENCE for KEEP — only WAIT/SKIP marks "
                f"(wait good={wait_good} bad={wait_bad}). Need TAKE outcomes."
            )
        elif bad > good + 1:
            suggestion = "CUT"
            note = f"More bad TAKEs ({bad}) than good ({good})."
        elif good >= 3 and good > bad:
            suggestion = "KEEP"
            note = f"Supportive TAKE marks good={good} bad={bad}."
        else:
            suggestion = "WATCH"
            note = (
                f"Mixed/early TAKEs: good={good} bad={bad} neutral={neutral} pending={pending}. "
                f"WAIT marks: good={wait_good} bad={wait_bad}."
            )
        summary[key] = {
            "good": good,
            "bad": bad,
            "neutral": neutral,
            "pending": pending,
            "wait_good": wait_good,
            "wait_bad": wait_bad,
            "wait_neutral": wait_neu,
            "wait_pending": wait_pend,
            "suggestion": suggestion,
            "note": note,
        }
    return summary
