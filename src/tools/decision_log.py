import json
import os
from datetime import datetime

LOG_FILE = "decision_log.json"

# Canonical decision memory fields (Phase A1)
# market state → recommendation → action → outcome → quality
SCHEMA_DEFAULTS = {
    "timestamp": None,
    "market": "crypto",
    "symbol": "BTC",
    "price": None,
    "change_24h": None,
    "regime": "Unknown",
    "regime_confidence": None,
    "user_goal": None,
    "risk_tolerance": "Unknown",
    "capital": 0,
    "experience_level": None,
    "open_positions": 0,
    "portfolio_equity": None,
    "portfolio_notes": None,
    "top_recommendation": None,
    "ranked_options": [],
    "strategy": "Unknown",
    "strategy_key": None,
    "confidence": 0,
    "style": "Unknown",
    "reason": None,
    "ranking_explanation": None,
    "entry_idea": None,
    "stop_loss_idea": None,
    "take_profit_idea": None,
    "invalidation": None,
    "expected_outcome": "pending",  # e.g. wait / long bias / explore
    "user_selected": None,
    "user_confirmed": False,
    "user_enabled_strategy": False,
    "user_override": False,  # True if user picked something other than top rec
    "status": "simulated",  # simulated / enabled / skipped / cancelled
    "outcome": "pending",  # pending / good / bad / neutral
    "decision_quality": "pending",  # pending / good_process / bad_process / unclear
    "notes": "",
}


def _normalize(decision_data: dict) -> dict:
    """Fill schema defaults without wiping provided values."""
    record = dict(SCHEMA_DEFAULTS)
    for k, v in decision_data.items():
        if v is not None:
            record[k] = v
    if not record.get("timestamp"):
        record["timestamp"] = datetime.utcnow().isoformat()
    return record


def save_decision(decision_data: dict):
    """
    Save a rich decision record for future analysis and memory queries.
    """
    logs = []

    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r") as f:
                logs = json.load(f)
        except Exception:
            logs = []

    record = _normalize(decision_data)
    logs.append(record)

    # Keep last 300 decisions (growing history for the lab)
    logs = logs[-300:]

    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=2)

    return True


def get_recent_decisions(limit: int = 10):
    """
    Get recent decisions from the log (oldest → newest within the slice).
    """
    if not os.path.exists(LOG_FILE):
        return []

    try:
        with open(LOG_FILE, "r") as f:
            logs = json.load(f)
        return logs[-limit:]
    except Exception:
        return []


def update_decision_outcome(index_from_end: int, outcome: str, notes: str = "", decision_quality: str = None):
    """
    Update the outcome of a past decision.
    index_from_end: 1 = most recent, 2 = second most recent, etc.
    outcome: good / bad / neutral
    decision_quality (optional): good_process / bad_process / unclear
    """
    if not os.path.exists(LOG_FILE):
        return False

    try:
        with open(LOG_FILE, "r") as f:
            logs = json.load(f)

        if index_from_end < 1 or index_from_end > len(logs):
            return False

        real_index = len(logs) - index_from_end
        logs[real_index]["outcome"] = outcome
        if notes:
            logs[real_index]["notes"] = notes
        if decision_quality:
            logs[real_index]["decision_quality"] = decision_quality

        with open(LOG_FILE, "w") as f:
            json.dump(logs, f, indent=2)

        return True
    except Exception:
        return False


def get_decisions_by_regime(regime: str, limit: int = 20):
    """Return past decisions in a similar regime (for future memory queries)."""
    if not regime:
        return []
    all_logs = get_recent_decisions(limit=300)
    regime_u = str(regime).upper()
    matched = [d for d in all_logs if str(d.get("regime", "")).upper() == regime_u]
    return matched[-limit:]


def get_decisions_by_strategy(strategy: str, limit: int = 20):
    """Return past decisions for a strategy name (substring match)."""
    if not strategy:
        return []
    all_logs = get_recent_decisions(limit=300)
    key = strategy.lower()
    matched = [d for d in all_logs if key in str(d.get("strategy", "")).lower()]
    return matched[-limit:]
