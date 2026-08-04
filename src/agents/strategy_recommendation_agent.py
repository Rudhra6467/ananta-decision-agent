from src.state.agent_state import AgentState

def strategy_recommendation_agent(state: AgentState) -> AgentState:
    """
    More aggressive strategy recommendation for paper trading.
    """
    print("→ Strategy Recommendation Agent is thinking...")

    regime = state.get("market_regime", "NEUTRAL")
    risk = state.get("risk_tolerance", "Medium")
    capital = state.get("capital", 5000)

    recommendation = {
        "strategy_name": "Stay Flat",
        "reason": "No clear edge.",
        "suitability_score": 0.50
    }

    if regime == "BULLISH_TRENDING":
        recommendation = {
            "strategy_name": "Trend Following Long",
            "reason": f"Bullish trend detected. Taking long bias for paper trading. Capital: ${capital}",
            "suitability_score": 0.78
        }

    elif regime == "BEARISH_TRENDING":
        recommendation = {
            "strategy_name": "Trend Following Short",
            "reason": f"Bearish trend detected. Taking short bias for paper trading.",
            "suitability_score": 0.76
        }

    elif regime == "COMPRESSION":
        recommendation = {
            "strategy_name": "Breakout Strategy",
            "reason": "Market is compressing. Preparing for breakout opportunity.",
            "suitability_score": 0.72
        }

    elif regime == "REVERSAL":
        recommendation = {
            "strategy_name": "Mean Reversion Entry",
            "reason": "Possible reversal. Taking a mean reversion setup for paper testing.",
            "suitability_score": 0.68
        }

    else:  # NEUTRAL
        recommendation = {
            "strategy_name": "Range Trading / Scalping Bias",
            "reason": "Neutral market. Using range/scalping approach instead of staying completely flat.",
            "suitability_score": 0.63
        }

    state["decision"] = recommendation["strategy_name"]
    state["reason"] = recommendation["reason"]
    state["confidence"] = recommendation["suitability_score"]
    state["next_agent"] = "supervisor"

    print(f"   Recommended: {recommendation['strategy_name']} (Score: {recommendation['suitability_score']})")
    return state
