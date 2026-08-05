from src.state.agent_state import AgentState

def supervisor_agent(state: AgentState) -> AgentState:
    print("→ Supervisor Agent is thinking...")

    if not state.get("user_goal"):
        print("   → Calling User Understanding Agent")
        state["next_agent"] = "user_understanding"
        return state

    if not state.get("market_regime"):
        print("   → Calling Market Regime Agent")
        state["next_agent"] = "market_regime"
        return state

    if not state.get("decision"):
        print("   → Calling Strategy Recommendation Agent")
        state["next_agent"] = "strategy_recommendation"
        return state

    if not state.get("portfolio"):
        print("   → Calling Portfolio Analysis Agent")
        state["next_agent"] = "portfolio_analysis"
        return state

    # For now we stop before tool execution (we will enable it later with permission)
    print("   → All analysis complete. Ending.")
    state["next_agent"] = "end"
    return state
