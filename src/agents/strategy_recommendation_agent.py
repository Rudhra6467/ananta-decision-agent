from src.state.agent_state import AgentState
from src.tools.ananta_api import get_portfolio

def strategy_recommendation_agent(state: AgentState) -> AgentState:
    """
    Generates multiple ranked strategy options.
    Aggressive bias for paper trading phase.
    """
    print("→ Strategy Recommendation Agent is thinking...")

    regime = state.get("market_regime") or "NEUTRAL"
    risk = state.get("risk_tolerance") or "Medium"

    # Get current open positions
    open_positions = 0
    try:
        portfolio_response = get_portfolio()
        if portfolio_response.get("success"):
            open_positions = portfolio_response["data"].get("slots_used", 0)
    except:
        open_positions = 0

    # Define strategy options
    options = []

    # Option 1: Breakout
    breakout = {
        "name": "Breakout Strategy",
        "confidence": 0.76,
        "style": "Aggressive",
        "entry_idea": "Enter only after clear breakout with volume",
        "stop_loss_idea": "Opposite side of the compression range",
        "take_profit_idea": "1.5x – 2x the range height",
        "reason": f"Market is in {regime}. Breakout offers asymmetric upside."
    }

    # Option 2: Momentum Continuation
    momentum = {
        "name": "Momentum Continuation",
        "confidence": 0.71,
        "style": "Aggressive",
        "entry_idea": "Enter on strong candle + volume expansion",
        "stop_loss_idea": "Below the last higher low",
        "take_profit_idea": "Trail using ATR or previous swing",
        "reason": "Captures continuation moves quickly. Good for paper trading exploration."
    }

    # Option 3: Mean Reversion Scalp
    mean_reversion = {
        "name": "Mean Reversion Scalp",
        "confidence": 0.64,
        "style": "Balanced",
        "entry_idea": "Enter near range extremes with confirmation",
        "stop_loss_idea": "Beyond the range high/low",
        "take_profit_idea": "Mid-range or opposite side of range",
        "reason": "Works well in compression. Lower risk than pure breakout."
    }

    # Adjust based on regime
    if regime == "COMPRESSION":
        breakout["confidence"] = 0.78
        momentum["confidence"] = 0.69
        mean_reversion["confidence"] = 0.72
    elif regime == "BULLISH_TRENDING":
        breakout["confidence"] = 0.70
        momentum["confidence"] = 0.82
        mean_reversion["confidence"] = 0.55
    elif regime == "BEARISH_TRENDING":
        breakout["confidence"] = 0.68
        momentum["confidence"] = 0.80
        mean_reversion["confidence"] = 0.58

    # Aggressive bias when risk is High
    if risk == "High":
        breakout["confidence"] += 0.04
        momentum["confidence"] += 0.05
        mean_reversion["confidence"] += 0.02

    # Reduce confidence if too many open positions
    if open_positions >= 7:
        for opt in [breakout, momentum, mean_reversion]:
            opt["confidence"] = max(0.50, opt["confidence"] - 0.12)
            opt["reason"] += f" | Warning: {open_positions} positions already open."
    elif open_positions >= 5:
        for opt in [breakout, momentum, mean_reversion]:
            opt["confidence"] = max(0.55, opt["confidence"] - 0.06)
            opt["reason"] += f" | Note: {open_positions} positions open."

    options = [breakout, momentum, mean_reversion]

    # Sort by confidence (highest first)
    options = sorted(options, key=lambda x: x["confidence"], reverse=True)

    # Primary recommendation = top ranked
    top = options[0]

    state["decision"] = top["name"]
    state["confidence"] = round(top["confidence"], 2)
    state["reason"] = top["reason"]
    state["entry_idea"] = top["entry_idea"]
    state["stop_loss_idea"] = top["stop_loss_idea"]
    state["take_profit_idea"] = top["take_profit_idea"]
    state["strategy_options"] = options  # store all options

    print(f"   Top Recommendation: {top['name']} (Score: {top['confidence']})")
    print(f"   Other options generated: {len(options) - 1}")

    state["next_agent"] = "supervisor"
    return state
