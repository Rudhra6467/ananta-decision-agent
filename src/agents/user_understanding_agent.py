from src.state.agent_state import AgentState

def user_understanding_agent(state: AgentState) -> AgentState:
    """
    Understands the user's goals, risk, capital, and preferences.
    For now we use a sample profile. Later this will come from conversation.
    """
    print("→ User Understanding Agent is analyzing user profile...")

    # Sample user profile (we will make this dynamic later)
    state["user_goal"] = "Moderate growth with controlled risk"
    state["risk_tolerance"] = "Medium"
    state["capital"] = 5000.0
    state["preferred_markets"] = ["Crypto"]
    state["experience_level"] = "Intermediate"

    print(f"   Goal: {state['user_goal']}")
    print(f"   Risk: {state['risk_tolerance']} | Capital: ${state['capital']}")

    state["next_agent"] = "supervisor"
    return state
