from src.state.agent_state import AgentState
from src.tools.market_tools import get_market_data

def market_regime_agent(state: AgentState) -> AgentState:
    """
    Improved Market Regime Agent.
    Uses real price data + better logic.
    """
    print("→ Market Regime Agent is analyzing...")

    market_data = get_market_data()
    state["market_data"] = market_data

    price = market_data.get("price", 0)
    change_24h = market_data.get("change_24h", 0)
    volatility = market_data.get("volatility", 1.0)
    rsi = market_data.get("rsi", 50)

    # Improved regime logic
    if change_24h >= 4 and rsi > 55:
        regime = "BULLISH_TRENDING"
        confidence = 0.82
    elif change_24h <= -4 and rsi < 45:
        regime = "BEARISH_TRENDING"
        confidence = 0.80
    elif abs(change_24h) <= 1.2 and volatility < 1.5:
        regime = "COMPRESSION"
        confidence = 0.75
    elif (change_24h > 1.5 and rsi > 65) or (change_24h < -1.5 and rsi < 35):
        regime = "REVERSAL"
        confidence = 0.68
    else:
        regime = "NEUTRAL"
        confidence = 0.60

    state["market_regime"] = regime
    state["confidence"] = confidence
    state["reason"] = (
        f"Price: ${price} | 24h Change: {change_24h}% | "
        f"RSI: {rsi} | Volatility: {volatility} → Regime: {regime}"
    )
    state["next_agent"] = "supervisor"

    print(f"   Regime: {regime} | Confidence: {confidence}")
    print(f"   Price: ${price} | 24h: {change_24h}%")
    return state
