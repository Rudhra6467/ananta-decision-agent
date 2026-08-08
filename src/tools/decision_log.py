import json
import os
from datetime import datetime

LOG_FILE = "decision_log.json"

def save_decision(decision_data: dict):
    """
    Save a decision to the local log for future analysis.
    """
    logs = []
    
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r") as f:
                logs = json.load(f)
        except:
            logs = []
    
    decision_data["timestamp"] = datetime.utcnow().isoformat()
    logs.append(decision_data)
    
    # Keep only last 100 decisions
    logs = logs[-100:]
    
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
