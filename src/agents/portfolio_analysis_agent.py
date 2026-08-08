from src.state.agent_state import AgentState

def portfolio_analysis_agent(state: AgentState) -> AgentState:
    """
    Analyzes the portfolio using the actual capital from the user.
    """
    print("→ Portfolio Analysis Agent is analyzing...")

    capital = state.get("capital", 5000)
    risk = state.get("risk_tolerance", "Medium")

    # More realistic simulation based on actual capital
    cash_ratio = 0.40
    invested_ratio = 0.60

    portfolio = {
        "total_value": capital,
        "cash": round(capital * cash_ratio, 1),
        "invested": round(capital * invested_ratio, 1),
        "open_positions": 1,
        "unrealized_pnl": round(capital * 0.018, 2),  # simulated small profit
        "risk_score": risk,
        "diversification_score": 6.5,
        "notes": f"Portfolio based on ${capital} capital. Cash buffer is healthy."
    }

    state["portfolio"] = portfolio

    print(f"   Portfolio Value: ${portfolio['total_value']}")
    print(f"   Open Positions: {portfolio['open_positions']} | Unrealized PnL: ${portfolio['unrealized_pnl']}")

    state["next_agent"] = "supervisor"
    return state
