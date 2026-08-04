from src.state.agent_state import AgentState
from src.tools.market_tools import get_market_data

def market_regime_agent(state: AgentState) -> AgentState:
    """
    Specialized agent that analyzes the current market regime.
    """
    print("→ Market Regime Agent is analyzing...")

    # Get market data
    market_data = get_market_data()
    state["market_data"] = market_data

    trend = market_data.get("trend", "unknown")
    volatility = market_data.get("volatility", 1.0)
    rsi = market_data.get("rsi", 50)

    # Simple regime logic
    if trend == "TREND_UP" and volatility < 2.5:
        regime = "BULLISH_TRENDING"
        confidence = 0.75
    elif trend == "TREND_DOWN" and volatility < 2.5:
        regime = "BEARISH_TRENDING"
        confidence = 0.73
    elif trend == "COMPRESSION":
        regime = "COMPRESSION"
        confidence = 0.65
    elif trend == "REVERSAL":
        regime = "REVERSAL"
        confidence = 0.60
    else:
        regime = "NEUTRAL"
        confidence = 0.55

    state["market_regime"] = regime
    state["confidence"] = confidence
    state["reason"] = f"Market regime detected as {regime} (RSI: {rsi}, Volatility: {volatility})"
    state["next_agent"] = "supervisor"

    print(f"   Regime: {regime} | Confidence: {confidence}")
    return state
