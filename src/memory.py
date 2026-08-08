import json
import os

MEMORY_FILE = "agent_memory.json"

def save_memory(data: dict):
    """Save important information to a local file."""
    with open(MEMORY_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_memory() -> dict:
    """Load previous memory if it exists."""
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    return {}

def update_user_memory(user_goal, risk_tolerance, capital, experience_level):
    """Save the latest user profile."""
    memory = load_memory()
    memory["user_profile"] = {
        "user_goal": user_goal,
        "risk_tolerance": risk_tolerance,
        "capital": capital,
        "experience_level": experience_level
    }
    save_memory(memory)
    return memory

def get_last_user_profile():
    """Return the last saved user profile if available."""
    memory = load_memory()
    return memory.get("user_profile", None)
