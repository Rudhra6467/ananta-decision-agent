from src.state.agent_state import AgentState

def tool_execution_agent(state: AgentState) -> AgentState:
    """
    This agent will later execute real actions in Ananta.
    For now it only simulates the action.
    """
    print("→ Tool Execution Agent is ready...")

    decision = state.get("decision", "None")
    print(f"   Received recommendation: {decision}")
    print("   (In future, this agent will execute actions in Ananta after permission)")

    # For now we just mark that tools are ready
    state["next_agent"] = "supervisor"
    return state
