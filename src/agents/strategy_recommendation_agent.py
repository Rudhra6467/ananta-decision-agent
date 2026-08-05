from src.state.agent_state import AgentState

def strategy_recommendation_agent(state: AgentState) -> AgentState:
    """
    Recommends strategy based on market regime + user risk profile.
    More aggressive when risk tolerance is High.
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
            "strategy_name": "Aggressive Trend Following Long",
            "reason": f"Strong bullish trend. High risk profile → taking aggressive long bias. Capital: ${capital}",
            "suitability_score": 0.85
        }

    elif regime == "BEARISH_TRENDING":
        recommendation = {
            "strategy_name": "Aggressive Trend Following Short",
            "reason": f"Clear bearish trend. High risk profile → taking short bias for paper trading.",
            "suitability_score": 0.83
        }

    elif regime == "COMPRESSION":
        recommendation = {
            "strategy_name": "Breakout Strategy (Aggressive)",
            "reason": "Market is compressing. High risk tolerance → preparing for breakout with higher position size bias.",
            "suitability_score": 0.78
        }

    elif regime == "REVERSAL":
        if risk == "High":
            recommendation = {
                "strategy_name": "Mean Reversion Entry (Aggressive)",
                "reason": "Possible reversal + High risk profile → taking mean reversion setup for paper testing.",
                "suitability_score": 0.74
            }
        else:
            recommendation = {
                "strategy_name": "Wait for Confirmation",
                "reason": "Possible reversal. Waiting for clearer confirmation.",
                "suitability_score": 0.60
            }

    else:  # NEUTRAL
        if risk == "High":
            recommendation = {
                "strategy_name": "Range Trading / Scalping (Active)",
                "reason": "Neutral market + High risk profile → using active range/scalping approach instead of staying flat.",
                "suitability_score": 0.70
            }
        else:
            recommendation = {
                "strategy_name": "Stay Flat",
                "reason": "Neutral market. Prefer capital protection.",
                "suitability_score": 0.55
            }

    state["decision"] = recommendation["strategy_name"]
    state["reason"] = recommendation["reason"]
    state["confidence"] = recommendation["suitability_score"]
    state["next_agent"] = "supervisor"

    print(f"   Recommended: {recommendation['strategy_name']} (Score: {recommendation['suitability_score']})")
    return state
