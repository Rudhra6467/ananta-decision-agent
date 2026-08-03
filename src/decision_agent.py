from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    market_data: dict
    open_positions: list
    decision: str
    reason: str
    confidence: float
    messages: Annotated[list, add_messages]

def analyze_market(state: AgentState) -> AgentState:
    """Analyze market conditions in more detail"""
    market = state.get("market_data", {})
    
    trend = market.get("trend", "unknown")
    volatility = market.get("volatility", 1.0)
    rsi = market.get("rsi", 50)
    volume_change = market.get("volume_change_percent", 0)

    analysis = (
        f"Trend: {trend} | Volatility: {volatility} | "
        f"RSI: {rsi} | Volume Change: {volume_change}%"
    )
    state["reason"] = analysis
    return state

def make_decision(state: AgentState) -> AgentState:
    """Stronger decision logic using multiple factors"""
    market = state.get("market_data", {})
    positions = state.get("open_positions", [])

    trend = market.get("trend", "unknown")
    volatility = market.get("volatility", 1.0)
    rsi = market.get("rsi", 50)
    volume_change = market.get("volume_change_percent", 0)

    decision = "HOLD"
    confidence = 0.4
    reason = state.get("reason", "")

    # Strong Long Setup
    if (trend == "TREND_UP" and rsi < 60 and volatility < 2.8 and volume_change > 5):
        decision = "ENTER_LONG"
        confidence = 0.78
        reason += " → Strong uptrend with healthy RSI and rising volume."

    # Strong Short Setup
    elif (trend == "TREND_DOWN" and rsi > 40 and volatility < 2.8 and volume_change < -5):
        decision = "ENTER_SHORT"
        confidence = 0.75
        reason += " → Clear downtrend with confirming volume."

    # Reversal caution
    elif trend == "REVERSAL":
        decision = "HOLD"
        confidence = 0.55
        reason += " → Reversal regime. Waiting for confirmation."

    # Compression / Neutral
    elif trend in ["COMPRESSION", "NEUTRAL"]:
        decision = "HOLD"
        confidence = 0.5
        reason += " → No clear directional edge. Staying flat."

    else:
        decision = "HOLD"
        confidence = 0.45
        reason += " → Conditions not strong enough."

    # Position protection
    if len(positions) > 0 and decision in ["ENTER_LONG", "ENTER_SHORT"]:
        decision = "HOLD"
        confidence = 0.6
        reason += " | Already in a position. Not adding more risk."

    state["decision"] = decision
    state["reason"] = reason
    state["confidence"] = confidence
    return state

def build_agent():
    workflow = StateGraph(AgentState)

    workflow.add_node("analyze", analyze_market)
    workflow.add_node("decide", make_decision)

    workflow.set_entry_point("analyze")
    workflow.add_edge("analyze", "decide")
    workflow.add_edge("decide", END)

    return workflow.compile()

agent = build_agent()
