from src.state.agent_state import AgentState

def portfolio_analysis_agent(state: AgentState) -> AgentState:
    """
    Analyzes the user's portfolio (simulated for now).
    """
    print("→ Portfolio Analysis Agent is analyzing...")

    capital = state.get("capital", 5000)
    risk = state.get("risk_tolerance", "Medium")

    # Simulated portfolio for now
    portfolio = {
        "total_value": capital,
        "cash": capital * 0.4,
        "invested": capital * 0.6,
        "open_positions": 1,
        "unrealized_pnl": 120.50,
        "risk_score": "Medium",
        "diversification_score": 6.5,
        "notes": "Portfolio is moderately concentrated. Cash buffer is healthy."
    }

    state["portfolio"] = portfolio

    print(f"   Portfolio Value: ${portfolio['total_value']}")
    print(f"   Open Positions: {portfolio['open_positions']} | Unrealized PnL: ${portfolio['unrealized_pnl']}")

    state["next_agent"] = "supervisor"
    return state
