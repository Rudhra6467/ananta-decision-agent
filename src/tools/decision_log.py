import json
import os
from datetime import datetime

LOG_FILE = "decision_log.json"

def save_decision(decision_data: dict):
    """
    Save a rich decision record for future analysis.
    """
    logs = []

    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r") as f:
                logs = json.load(f)
        except:
            logs = []

    # Add timestamp if not present
    if "timestamp" not in decision_data:
        decision_data["timestamp"] = datetime.utcnow().isoformat()

    # Ensure important fields exist
    decision_data.setdefault("strategy", "Unknown")
    decision_data.setdefault("confidence", 0)
    decision_data.setdefault("style", "Unknown")
    decision_data.setdefault("regime", "Unknown")
    decision_data.setdefault("risk_tolerance", "Unknown")
    decision_data.setdefault("capital", 0)
    decision_data.setdefault("open_positions", 0)
    decision_data.setdefault("status", "simulated")
    decision_data.setdefault("outcome", "pending")  # pending / good / bad / neutral
    decision_data.setdefault("notes", "")

    logs.append(decision_data)

    # Keep only last 150 decisions
    logs = logs[-150:]

    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=2)

    return True


def get_recent_decisions(limit: int = 10):
    """
    Get recent decisions from the log.
    """
    if not os.path.exists(LOG_FILE):
        return []

    try:
        with open(LOG_FILE, "r") as f:
            logs = json.load(f)
        return logs[-limit:]
    except:
        return []


def update_decision_outcome(index_from_end: int, outcome: str, notes: str = ""):
    """
    Update the outcome of a past decision.
    index_from_end: 1 = most recent, 2 = second most recent, etc.
    outcome: good / bad / neutral
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

        with open(LOG_FILE, "w") as f:
            json.dump(logs, f, indent=2)

        return True
    except:
        return False
