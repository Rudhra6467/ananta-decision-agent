# Main entry point for Ananta Decision Agent

from src.decision_agent import make_decision
from src.tools import get_market_data, get_open_positions, get_strategy_rules

def run_agent():
    print("Starting Ananta Decision Agent...")

    # Get current data (placeholders for now)
    market_data = get_market_data()
    positions = get_open_positions()
    rules = get_strategy_rules()

    # Create initial state
    state = {
        "market_data": market_data,
        "open_positions": positions,
        "decision": "",
        "reason": ""
    }

    # Make decision
    result = make_decision(state)

    print("Decision:", result["decision"])
    print("Reason:", result["reason"])

if __name__ == "__main__":
    run_agent()
