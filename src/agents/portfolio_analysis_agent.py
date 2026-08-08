from src.state.agent_state import AgentState
from src.tools.ananta_api import get_portfolio

def portfolio_analysis_agent(state: AgentState) -> AgentState:
    """
    Analyzes the portfolio.
    Tries to use real Ananta data first. Falls back to simulation if needed.
    """
    print("→ Portfolio Analysis Agent is analyzing...")

    capital = state.get("capital", 5000)
    risk = state.get("risk_tolerance", "Medium")

    # Try to get real portfolio from Ananta
    real_portfolio_response = get_portfolio()

    if real_portfolio_response.get("success"):
        data = real_portfolio_response["data"]
        
        portfolio = {
            "total_value": data.get("equity", capital),
            "cash": data.get("cash", 0),
            "invested": data.get("positions_value", 0),
            "open_positions": data.get("slots_used", 0),
            "unrealized_pnl": round(data.get("total_pnl", 0), 2),
            "risk_score": risk,
            "diversification_score": 7.0 if data.get("slots_used", 0) >= 5 else 5.5,
            "notes": f"Real Ananta Portfolio | Daily PnL: {data.get('daily_pnl_pct', 0)}% | Total PnL: {data.get('total_pnl_pct', 0)}%",
            "source": "real_ananta"
        }
        
        print(f"   Using REAL Ananta Portfolio")
        print(f"   Equity: ${portfolio['total_value']} | Open Positions: {portfolio['open_positions']}")
        
    else:
        # Fallback to simulation
        cash_ratio = 0.40
        invested_ratio = 0.60

        portfolio = {
            "total_value": capital,
            "cash": round(capital * cash_ratio, 1),
            "invested": round(capital * invested_ratio, 1),
            "open_positions": 1,
            "unrealized_pnl": round(capital * 0.018, 2),
            "risk_score": risk,
            "diversification_score": 6.5,
            "notes": f"Simulated portfolio based on ${capital} capital.",
            "source": "simulated"
        }
        
        print(f"   Using SIMULATED Portfolio (could not reach Ananta)")
        print(f"   Portfolio Value: ${portfolio['total_value']}")

    state["portfolio"] = portfolio
    state["next_agent"] = "supervisor"
    return state
