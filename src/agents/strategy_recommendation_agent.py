from src.state.agent_state import AgentState
from src.tools.ananta_api import get_portfolio, get_enabled_strategies, resolve_strategy_key


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
    Generates multiple ranked strategy options with risk guardrails.
    Paper-trading bias remains, but overload forces WAIT preference.
    """
    print("→ Strategy Recommendation Agent is thinking...")

    regime = state.get("market_regime") or "NEUTRAL"
    risk = state.get("risk_tolerance") or "Medium"

    # --- Portfolio load ---
    open_positions = 0
    try:
        portfolio_response = get_portfolio()
        if portfolio_response.get("success"):
            data = portfolio_response.get("data") or {}
            open_positions = (
                data.get("slots_used")
                or data.get("open_positions")
                or 0
            )
            try:
                open_positions = int(open_positions)
            except Exception:
                open_positions = 0
    except Exception:
        open_positions = 0

    # --- Enabled strategies load ---
    enabled_list = []
    try:
        enabled_list = get_enabled_strategies() or []
    except Exception:
        enabled_list = []
    enabled_count = len(enabled_list)

    print(f"   Load check → open positions: {open_positions} | enabled strategies: {enabled_count}")

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

    elif regime in ("BULLISH_TRENDING", "TREND_UP"):
        breakout["confidence"] = 0.70
        momentum["confidence"] = 0.84
        mean_reversion["confidence"] = 0.52
        momentum["reason"] = "Strong uptrend detected. Momentum continuation is favored."
        mean_reversion["reason"] = "Mean reversion is less reliable in strong trends."

    elif regime in ("BEARISH_TRENDING", "TREND_DOWN"):
        breakout["confidence"] = 0.67
        momentum["confidence"] = 0.81
        mean_reversion["confidence"] = 0.55
        momentum["reason"] = "Downtrend in progress. Momentum short continuation preferred."
        mean_reversion["reason"] = "Counter-trend mean reversion is riskier here."

    # === Risk Tolerance Adjustments ===
    if risk == "High":
        breakout["confidence"] += 0.05
        momentum["confidence"] += 0.06
        mean_reversion["confidence"] += 0.02
    elif risk == "Low":
        breakout["confidence"] -= 0.08
        momentum["confidence"] -= 0.10
        mean_reversion["confidence"] += 0.04

    # === RISK GUARDRAILS (positions + enabled strategies) ===
    # Levels:
    #   CAUTION  : positions >= 5 OR enabled >= 5
    #   HIGH     : positions >= 7 OR enabled >= 7
    #   CRITICAL : positions >= 10 OR enabled >= 9 OR (positions >= 8 and enabled >= 6)
    load_level = "OK"
    if open_positions >= 10 or enabled_count >= 9 or (open_positions >= 8 and enabled_count >= 6):
        load_level = "CRITICAL"
    elif open_positions >= 7 or enabled_count >= 7:
        load_level = "HIGH"
    elif open_positions >= 5 or enabled_count >= 5:
        load_level = "CAUTION"

    if load_level == "CRITICAL":
        for opt in [breakout, momentum, mean_reversion]:
            # Aggressive styles hit harder
            penalty = 0.22 if opt["style"] == "Aggressive" else 0.16
            opt["confidence"] = max(0.40, opt["confidence"] - penalty)
            opt["reason"] += (
                f" | RISK: overloaded book "
                f"({open_positions} positions, {enabled_count} strategies on). Prefer WAIT."
            )
        breakout["entry_idea"] = "Do not add size. Book is critically loaded."
        momentum["entry_idea"] = "Do not add size. Book is critically loaded."
        mean_reversion["entry_idea"] = "Only consider if closing other risk first."

    elif load_level == "HIGH":
        for opt in [breakout, momentum, mean_reversion]:
            penalty = 0.16 if opt["style"] == "Aggressive" else 0.10
            opt["confidence"] = max(0.45, opt["confidence"] - penalty)
            opt["reason"] += (
                f" | Warning: high load "
                f"({open_positions} positions, {enabled_count} strategies on). Be selective."
            )
        breakout["entry_idea"] = "Only take A+ breakout setups. Portfolio is heavily loaded."
        momentum["entry_idea"] = "Only take very strong momentum signals."

    elif load_level == "CAUTION":
        for opt in [breakout, momentum, mean_reversion]:
            penalty = 0.08 if opt["style"] == "Aggressive" else 0.05
            opt["confidence"] = max(0.50, opt["confidence"] - penalty)
            opt["reason"] += (
                f" | Note: elevated load "
                f"({open_positions} positions, {enabled_count} strategies on)."
            )

    # Low risk tolerance amplifies load pressure
    if risk == "Low" and load_level in ("HIGH", "CRITICAL"):
        for opt in [breakout, momentum, mean_reversion]:
            opt["confidence"] = max(0.40, opt["confidence"] - 0.05)
            opt["reason"] += " | Low risk profile + high load → defensive bias."

    # === Apply learning bias from past outcomes ===
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

    # Clamp confidence
    for opt in [breakout, momentum, mean_reversion]:
        opt["confidence"] = round(min(0.92, max(0.40, opt["confidence"])), 2)

    options = [breakout, momentum, mean_reversion]
    options = sorted(options, key=lambda x: x["confidence"], reverse=True)

    # === WAIT Logic (stronger under load) ===
    best_confidence = max(opt["confidence"] for opt in options)
    force_wait = (
        load_level == "CRITICAL"
        or open_positions >= 8
        or enabled_count >= 8
        or (risk == "Low" and load_level == "HIGH")
        or best_confidence < 0.58
    )

    if force_wait:
        if load_level == "CRITICAL":
            wait_reason = (
                f"CRITICAL load: {open_positions} open positions and "
                f"{enabled_count} strategies enabled. Prefer WAIT / reduce exposure."
            )
            wait_conf = 0.82
        elif open_positions >= 8 or enabled_count >= 8:
            wait_reason = (
                f"High load ({open_positions} positions, {enabled_count} strategies on). "
                f"Prefer waiting over adding more risk."
            )
            wait_conf = 0.75
        elif risk == "Low" and load_level == "HIGH":
            wait_reason = (
                f"Low risk profile with high portfolio load "
                f"({open_positions} positions / {enabled_count} strategies). Defensive WAIT preferred."
            )
            wait_conf = 0.72
        else:
            wait_reason = "Conditions are not attractive enough right now. Better to wait for a clearer setup."
            wait_conf = round(max(0.55, 1.0 - best_confidence), 2)

        wait_option = {
            "name": "WAIT",
            "confidence": wait_conf,
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
        top_key = resolve_strategy_key(top.get("name", ""))
        if top_key and top_key in enabled_list:
            top["reason"] += " | This strategy is already enabled."
        elif top_key:
            top["reason"] += " | Not currently enabled."
        else:
            # Fallback soft match
            soft = top.get("name", "").lower().replace(" ", "-")
            if any(soft in e or e in soft for e in enabled_list):
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
    print(f"   Load level: {load_level}")
    print(f"   Other options generated: {len(options) - 1}")

    ranking_reason = (
        f"Ranked based on regime ({regime}), risk ({risk}), "
        f"open positions ({open_positions}), enabled strategies ({enabled_count})."
    )

    if load_level == "CRITICAL":
        ranking_reason += " CRITICAL load forced strong WAIT preference."
    elif load_level == "HIGH":
        ranking_reason += " High load reduced confidence on aggressive strategies."
    elif load_level == "CAUTION":
        ranking_reason += " Elevated load applied mild confidence haircut."

    if regime == "COMPRESSION":
        ranking_reason += " Compression favors Breakout and Mean Reversion over pure Momentum."
    elif regime in ("BULLISH_TRENDING", "TREND_UP"):
        ranking_reason += " Uptrend favors Momentum Continuation."
    elif regime in ("BEARISH_TRENDING", "TREND_DOWN"):
        ranking_reason += " Downtrend favors Momentum Continuation on the short side."

    if learning_notes:
        ranking_reason += " Confidence also adjusted from past decision outcomes."

    state["ranking_explanation"] = ranking_reason
    state["next_agent"] = "supervisor"
    return state
