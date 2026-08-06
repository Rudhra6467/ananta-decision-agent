from src.state.agent_state import AgentState

def strategy_recommendation_agent(state: AgentState) -> AgentState:
    """
    Improved Strategy Recommendation Agent.
    Gives clearer recommendation + respects actual risk tolerance.
    """
    print("→ Strategy Recommendation Agent is thinking...")

    regime = state.get("market_regime", "NEUTRAL")
    risk = state.get("risk_tolerance", "Medium")
    capital = state.get("capital", 5000)
    price = state.get("market_data", {}).get("price", 0)

    recommendation = {
        "strategy_name": "Stay Flat",
        "reason": "No clear edge at the moment.",
        "suitability_score": 0.50,
        "entry_idea": "None",
        "stop_loss_idea": "None",
        "take_profit_idea": "None"
    }

    if regime == "BULLISH_TRENDING":
        if risk == "High":
            recommendation = {
                "strategy_name": "Aggressive Trend Following Long",
                "reason": f"Strong bullish regime + High risk profile. Looking for long continuation.",
                "suitability_score": 0.85,
                "entry_idea": f"Look for pullback entries near ${round(price * 0.985, 0)}",
                "stop_loss_idea": f"Below recent swing low (~{round(price * 0.97, 0)})",
                "take_profit_idea": f"Target 1: ${round(price * 1.03, 0)} | Target 2: ${round(price * 1.05, 0)}"
            }
        else:
            recommendation = {
                "strategy_name": "Conservative Trend Following Long",
                "reason": f"Bullish regime with {risk} risk tolerance. Preferring safer long setup.",
                "suitability_score": 0.74,
                "entry_idea": f"Wait for confirmation above ${round(price * 1.005, 0)}",
                "stop_loss_idea": f"Tight stop below ${round(price * 0.98, 0)}",
                "take_profit_idea": f"Target around ${round(price * 1.025, 0)}"
            }

    elif regime == "BEARISH_TRENDING":
        if risk == "High":
            recommendation = {
                "strategy_name": "Aggressive Trend Following Short",
                "reason": "Clear bearish regime + High risk → Short bias for paper trading.",
                "suitability_score": 0.83,
                "entry_idea": f"Look for retest entries near ${round(price * 1.015, 0)}",
                "stop_loss_idea": f"Above recent high (~{round(price * 1.03, 0)})",
                "take_profit_idea": f"Target 1: ${round(price * 0.97, 0)}"
            }
        else:
            recommendation = {
                "strategy_name": "Stay Flat / Light Hedge",
                "reason": f"Bearish regime but risk is {risk}. Prefer capital protection.",
                "suitability_score": 0.62,
                "entry_idea": "Avoid aggressive shorts",
                "stop_loss_idea": "N/A",
                "take_profit_idea": "N/A"
            }

    elif regime == "COMPRESSION":
        recommendation = {
            "strategy_name": "Breakout Strategy",
            "reason": f"Market is compressing. Waiting for expansion. Risk profile: {risk}.",
            "suitability_score": 0.76 if risk == "High" else 0.68,
            "entry_idea": "Enter only after clear breakout with volume",
            "stop_loss_idea": "Opposite side of the compression range",
            "take_profit_idea": "1.5x – 2x the range height"
        }

    elif regime == "REVERSAL":
        recommendation = {
            "strategy_name": "Mean Reversion Watch",
            "reason": "Possible reversal forming. Better to wait for confirmation.",
            "suitability_score": 0.65,
            "entry_idea": "Wait for structure confirmation",
            "stop_loss_idea": "Beyond the reversal wick",
            "take_profit_idea": "Previous support/resistance"
        }

    else:  # NEUTRAL
        if risk == "High":
            recommendation = {
                "strategy_name": "Active Range / Scalping Bias",
                "reason": "Neutral market + High risk → active range trading allowed for paper testing.",
                "suitability_score": 0.70,
                "entry_idea": "Buy support / Sell resistance inside range",
                "stop_loss_idea": "Outside the range",
                "take_profit_idea": "Opposite side of range"
            }
        else:
            recommendation = {
                "strategy_name": "Stay Flat",
                "reason": f"Neutral market with {risk} risk tolerance. Prefer waiting.",
                "suitability_score": 0.55,
                "entry_idea": "None",
                "stop_loss_idea": "None",
                "take_profit_idea": "None"
            }

    state["decision"] = recommendation["strategy_name"]
    state["reason"] = recommendation["reason"]
    state["confidence"] = recommendation["suitability_score"]
    
    # Store extra details for later use
    state["entry_idea"] = recommendation["entry_idea"]
    state["stop_loss_idea"] = recommendation["stop_loss_idea"]
    state["take_profit_idea"] = recommendation["take_profit_idea"]

    state["next_agent"] = "supervisor"

    print(f"   Recommended: {recommendation['strategy_name']} (Score: {recommendation['suitability_score']})")
    return state
