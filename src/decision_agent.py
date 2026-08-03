# Ananta Decision Agent
# This will be the main brain of the agent

from typing import TypedDict

class AgentState(TypedDict):
    market_data: dict
    open_positions: list
    decision: str
    reason: str

def make_decision(state: AgentState) -> AgentState:
    """
    This function will later use LangGraph to decide:
    - ENTER_LONG
    - EXIT
    - HOLD
    """
    # Temporary placeholder logic
    state["decision"] = "HOLD"
    state["reason"] = "Agent is not fully built yet"
    return state
