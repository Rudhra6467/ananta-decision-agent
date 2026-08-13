from src.state.agent_state import AgentState
from src.tools.ananta_api import get_portfolio, get_enabled_strategies

def get_outcome_bias():
    """
    Look at recent decisions and return small confidence adjustments
    based on past outcomes.
    """
    try:
        from src.tools.decision_log import get_recent_decisions
        decisions = get_recent_decisions(limit=20)

        bias = {
            "Breakout Strategy": 0.0,
            "Momentum Continuation": 0.0,
            "Mean Reversion Scalp": 0.0
        }

        for d in decisions:
            strategy = d.get("strategy")
            outcome = d.get("outcome", "pending")

            if strategy not in bias:
                continue

            if outcome == "good":
                bias[strategy] += 0.03
            elif outcome == "bad":
                bias[strategy] -= 0.04

        # Limit the bias
        for k in bias:
            bias[k] = max(-0.10, min(0.10, bias[k]))

        return bias
    except Exception:
        return {
            "Breakout Strategy": 0.0,
            "Momentum Continuation": 0.0,
            "Mean Reversion Scalp": 0.0
        }


def strategy_recommendation_agent(state: AgentState) -> AgentState:
    """
    Generates multiple ranked strategy options with better logic.
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
    except Exception:
        open_positions = 0

    # Base strategies
    breakout = {
        "name": "Breakout Strategy",
        "confidence": 0.72,
        "style": "Aggressive",
        "entry_idea": "Enter only after clear breakout with volume confirmation",
        "stop_loss_idea": "Opposite side of the compression range",
        "take_profit_idea": "1.5x – 2x the range height",
        "reason": "Breakout offers asymmetric upside when compression resolves."
    }

    momentum = {
        "name": "Momentum Continuation",
        "confidence": 0.68,
        "style": "Aggressive",
        "entry_idea": "Enter on strong candle + rising volume",
        "stop_loss_idea": "Below the last higher low / structure",
        "take_profit_idea": "Trail using ATR or previous swing high",
        "reason": "Captures continuation moves quickly. Useful for exploration in paper trading."
    }

    mean_reversion = {
        "name": "Mean Reversion Scalp",
        "confidence": 0.65,
        "style": "Balanced",
        "entry_idea": "Enter near range extremes with rejection confirmation",
        "stop_loss_idea": "Beyond the range high/low",
        "take_profit_idea": "Mid-range or opposite side of the range",
        "reason": "Works well during compression. Lower risk than pure breakout."
    }

    # === Regime Adjustments ===
    if regime == "COMPRESSION":
        breakout["confidence"] = 0.78
        momentum["confidence"] = 0.66
        mean_reversion["confidence"] = 0.73
        breakout["reason"] = "Market is compressing. Breakout has good asymmetric potential."
        mean_reversion["reason"] = "Compression favors mean reversion until expansion begins."

    elif regime == "BULLISH_TRENDING":
        breakout["confidence"] = 0.70
        momentum["confidence"] = 0.84
        mean_reversion["confidence"] = 0.52
        momentum["reason"] = "Strong uptrend detected. Momentum continuation is favored."
        mean_reversion["reason"] = "Mean reversion is less reliable in strong trends."

    elif regime == "BEARISH_TRENDING":
        breakout["confidence"] = 0.67
        momentum["confidence"] = 0.81
        mean_reversion["confidence"] = 0.55
        momentum["reason"] = "Downtrend in progress. Momentum short continuation preferred."
        mean_reversion["reason"] = "Counter-trend mean reversion is riskier here."

    # === Risk Tolerance Adjustments (Aggressive bias) ===
    if risk == "High":
        breakout["confidence"] += 0.05
        momentum["confidence"] += 0.06
        mean_reversion["confidence"] += 0.02
    elif risk == "Low":
        breakout["confidence"] -= 0.08
        momentum["confidence"] -= 0.10
        mean_reversion["confidence"] += 0.04

    # === Open Positions Adjustments ===
    if open_positions >= 7:
        for opt in [breakout, momentum, mean_reversion]:
            opt["confidence"] = max(0.48, opt["confidence"] - 0.14)
            opt["reason"] += f" | Warning: {open_positions} positions already open. Be selective."
        breakout["entry_idea"] = "Only take A+ breakout setups. Portfolio is heavily loaded."
        momentum["entry_idea"] = "Only take very strong momentum signals."
    elif open_positions >= 5:
        for opt in [breakout, momentum, mean_reversion]:
            opt["confidence"] = max(0.55, opt["confidence"] - 0.07)
            opt["reason"] += f" | Note: {open_positions} positions open."

    # === Apply learning bias from past outcomes (AFTER regime/risk/positions) ===
    outcome_bias = get_outcome_bias()
    learning_notes = []

    for opt, key in [
        (breakout, "Breakout Strategy"),
        (momentum, "Momentum Continuation"),
        (mean_reversion, "Mean Reversion Scalp"),
    ]:
        bias_value = outcome_bias.get(key, 0.0)
        if abs(bias_value) >= 0.01:
            opt["confidence"] += bias_value
            direction = "boosted" if bias_value > 0 else "reduced"
            learning_notes.append(f"{key} {direction} by {bias_value:+.2f} from past outcomes")

    if learning_notes:
        print("   Learning adjustments:")
        for note in learning_notes:
            print(f"     • {note}")
    else:
        print("   Learning: no strong past outcomes yet (mark decisions with: mark <num> good/bad)")

    # Clamp confidence between 0.45 and 0.92
    for opt in [breakout, momentum, mean_reversion]:
        opt["confidence"] = round(min(0.92, max(0.45, opt["confidence"])), 2)

    options = [breakout, momentum, mean_reversion]
    options = sorted(options, key=lambda x: x["confidence"], reverse=True)

    # === WAIT Logic ===
    best_confidence = max(opt["confidence"] for opt in options)
    if best_confidence < 0.60 or open_positions >= 8:
        if open_positions >= 8:
            wait_reason = f"Portfolio is overloaded ({open_positions} open positions). Prefer waiting over adding more risk."
        else:
            wait_reason = "Conditions are not attractive enough right now. Better to wait for a clearer setup."

        wait_option = {
            "name": "WAIT",
            "confidence": round(1.0 - best_confidence, 2),
            "style": "Defensive",
            "reason": wait_reason,
            "entry_idea": "No entry",
            "stop_loss_idea": "N/A",
            "take_profit_idea": "N/A"
        }
        options = [wait_option] + options
        top = wait_option
    else:
        top = options[0]

    # Note if top strategy is already enabled (skip for WAIT)
    if top.get("name", "").upper() != "WAIT":
        enabled_strategies = get_enabled_strategies()
        top_key = top.get("name", "").lower().replace(" ", "-")
        if any(top_key in e or e in top_key for e in enabled_strategies):
            top["reason"] += " | This strategy (or similar) is already enabled."
        else:
            top["reason"] += " | Not currently enabled."

    state["decision"] = top["name"]
    state["confidence"] = top["confidence"]
    state["reason"] = top["reason"]
    state["entry_idea"] = top["entry_idea"]
    state["stop_loss_idea"] = top["stop_loss_idea"]
    state["take_profit_idea"] = top["take_profit_idea"]
    state["strategy_options"] = options

    print(f"   Top Recommendation: {top['name']} (Score: {top['confidence']})")
    print(f"   Other options generated: {len(options) - 1}")

    # Create ranking explanation
    ranking_reason = f"Ranked based on current regime ({regime}), risk profile ({risk}), and open positions ({open_positions})."

    if open_positions >= 7:
        ranking_reason += " High position count reduced confidence across aggressive strategies."

    if regime == "COMPRESSION":
        ranking_reason += " Compression favors Breakout and Mean Reversion over pure Momentum."
    elif regime == "BULLISH_TRENDING":
        ranking_reason += " Uptrend favors Momentum Continuation."
    elif regime == "BEARISH_TRENDING":
        ranking_reason += " Downtrend favors Momentum Continuation on the short side."

    if learning_notes:
        ranking_reason += " Confidence also adjusted from past decision outcomes."

    state["ranking_explanation"] = ranking_reason
    state["next_agent"] = "supervisor"
    return state
