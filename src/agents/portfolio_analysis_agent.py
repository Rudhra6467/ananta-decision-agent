from src.state.agent_state import AgentState
from src.tools.ananta_api import get_portfolio

def portfolio_analysis_agent(state: AgentState) -> AgentState:
    """
    Analyzes the portfolio with better commentary.
    """
    print("→ Portfolio Analysis Agent is analyzing...")

    capital = state.get("capital", 5000)
    risk = state.get("risk_tolerance", "Medium")

    real_portfolio_response = get_portfolio()

    if real_portfolio_response.get("success"):
        data = real_portfolio_response["data"]
        
        open_positions = data.get("slots_used", 0)
        total_pnl_pct = data.get("total_pnl_pct", 0)
        daily_pnl_pct = data.get("daily_pnl_pct", 0)
        equity = data.get("equity", capital)
        cash = data.get("cash", 0)
        invested = data.get("positions_value", 0)

        # Create smarter notes
        notes = f"Real Ananta Portfolio | Daily PnL: {daily_pnl_pct}% | Total PnL: {total_pnl_pct}%"

        if open_positions >= 7:
            notes += " | Portfolio is heavily loaded. New entries should be highly selective."
        elif open_positions >= 5:
            notes += " | Moderate exposure. Manage risk carefully."
        elif open_positions <= 2:
            notes += " | Low exposure. Room available for new opportunities."

        if total_pnl_pct < -5:
            notes += " | Portfolio is in noticeable drawdown."
        elif total_pnl_pct > 5:
            notes += " | Portfolio is in healthy profit."

        portfolio = {
            "total_value": equity,
            "cash": cash,
            "invested": invested,
            "open_positions": open_positions,
            "unrealized_pnl": round(data.get("total_pnl", 0), 2),
            "risk_score": risk,
            "diversification_score": 7.0 if open_positions >= 5 else 5.5,
            "notes": notes,
            "source": "real_ananta"
        }
        
        print(f"   Using REAL Ananta Portfolio")
        print(f"   Equity: ${equity} | Open Positions: {open_positions}")
        
    else:
        portfolio = {
            "total_value": capital,
            "cash": round(capital * 0.40, 1),
            "invested": round(capital * 0.60, 1),
            "open_positions": 1,
            "unrealized_pnl": round(capital * 0.018, 2),
            "risk_score": risk,
            "diversification_score": 6.5,
            "notes": f"Simulated portfolio based on ${capital} capital.",
            "source": "simulated"
        }
        
        print(f"   Using SIMULATED Portfolio")

    state["portfolio"] = portfolio
    state["next_agent"] = "supervisor"
    return state
