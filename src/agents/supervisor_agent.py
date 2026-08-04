from src.state.agent_state import AgentState

def supervisor_agent(state: AgentState) -> AgentState:
    print("→ Supervisor Agent is thinking...")

    user_goal = state.get("user_goal")
    market_regime = state.get("market_regime")
    decision = state.get("decision")

    if user_goal is None:
        print("   → Calling User Understanding Agent")
        state["next_agent"] = "user_understanding"
    elif market_regime is None:
        print("   → Calling Market Regime Agent")
        state["next_agent"] = "market_regime"
    elif decision is None:
        print("   → Calling Strategy Recommendation Agent")
        state["next_agent"] = "strategy_recommendation"
    else:
        print("   → All analysis complete. Ending.")
        state["next_agent"] = "end"

    return state
