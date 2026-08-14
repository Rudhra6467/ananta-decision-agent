from src.state.agent_state import AgentState
from src.tools.ananta_api import get_portfolio, get_enabled_strategies, resolve_strategy_key


# Prefer keeping these when cleaning up an overloaded book
KEEP_PRIORITY = [
    "hunter",
    "bollinger-mr",
    "ema-cross",
    "squeeze",
]

# Prefer turning these off first (more aggressive / overlapping / experimental)
DISABLE_FIRST = [
    "aggressive-movement-cf1358",
    "turtle",
    "keltner-breakout",
    "atr-breakout",
    "donchian-breakout",
    "continuation",
    "time-series-momentum",
    "stochastic-momentum",
    "rsi-momentum",
    "macd-trend",
    "vwap-mr",
    "supertrend",
]

# Map many logged names / keys → canonical recommendation names
STRATEGY_ALIASES = {
    "breakout strategy": "Breakout Strategy",
    "breakout": "Breakout Strategy",
    "donchian-breakout": "Breakout Strategy",
    "donchian": "Breakout Strategy",
    "atr-breakout": "Breakout Strategy",
    "keltner-breakout": "Breakout Strategy",
    "momentum continuation": "Momentum Continuation",
    "momentum": "Momentum Continuation",
    "continuation": "Momentum Continuation",
    "time-series-momentum": "Momentum Continuation",
    "stochastic-momentum": "Momentum Continuation",
    "rsi-momentum": "Momentum Continuation",
    "macd-trend": "Momentum Continuation",
    "ema-cross": "Momentum Continuation",
    "mean reversion scalp": "Mean Reversion Scalp",
    "mean reversion": "Mean Reversion Scalp",
    "bollinger-mr": "Mean Reversion Scalp",
    "bollinger": "Mean Reversion Scalp",
    "vwap-mr": "Mean Reversion Scalp",
    "squeeze": "Mean Reversion Scalp",
    "wait": "WAIT",
}


def _canonical_strategy_name(raw: str):
    if not raw:
        return None
    s = str(raw).strip().lower()
    if s in STRATEGY_ALIASES:
        return STRATEGY_ALIASES[s]
    # soft contains match
    for key, canon in STRATEGY_ALIASES.items():
        if key in s or s in key:
            return canon
    return None


def get_outcome_bias(current_regime: str = None):
    """
    Build confidence adjustments from marked outcomes in decision memory.

    Weights:
      good            +0.05
      bad             -0.06
      good_process    extra +0.03
      bad_process     extra -0.04
      same regime     ×1.25
      recent entries  slightly stronger
    """
    empty = {
        "Breakout Strategy": 0.0,
        "Momentum Continuation": 0.0,
        "Mean Reversion Scalp": 0.0,
        "WAIT": 0.0,
    }
    try:
        from src.tools.decision_log import get_recent_decisions
        decisions = get_recent_decisions(limit=40)
        if not decisions:
            return empty

        bias = dict(empty)
        marked = 0
        regime_u = str(current_regime or "").upper()

        # decisions is oldest→newest; weight newer higher
        n = len(decisions)
        for i, d in enumerate(decisions):
            outcome = str(d.get("outcome", "pending")).lower()
            if outcome not in ("good", "bad", "neutral"):
                continue

            # Resolve strategy from several fields
            candidates = [
                d.get("strategy"),
                d.get("strategy_key"),
                d.get("user_selected"),
                d.get("top_recommendation"),
            ]
            canon = None
            for c in candidates:
                canon = _canonical_strategy_name(c)
                if canon:
                    break
            if not canon:
                continue

            marked += 1
            recency = 0.7 + 0.3 * ((i + 1) / n)  # ~0.7 old → 1.0 newest

            delta = 0.0
            if outcome == "good":
                delta = 0.05
            elif outcome == "bad":
                delta = -0.06
            elif outcome == "neutral":
                delta = 0.0

            quality = str(d.get("decision_quality", "pending")).lower()
            if quality == "good_process":
                delta += 0.03 if outcome != "bad" else 0.01
            elif quality == "bad_process":
                delta -= 0.04 if outcome != "good" else 0.01

            # Same-regime marks matter more
            d_regime = str(d.get("regime", "")).upper()
            if regime_u and d_regime and regime_u == d_regime:
                delta *= 1.25

            bias[canon] = bias.get(canon, 0.0) + delta * recency

        # Clamp per strategy
        for k in list(bias.keys()):
            bias[k] = max(-0.15, min(0.15, round(bias[k], 3)))

        bias["_marked_count"] = marked
        return bias
    except Exception:
        return empty


def suggest_disables(enabled_list, target_max=5, regime="NEUTRAL"):
    """
    Pick concrete strategy keys to disable so enabled count moves toward target_max.
    Keeps core strategies when possible; trims aggressive / overlapping ones first.
    """
    if not enabled_list:
        return []

    enabled = list(enabled_list)
    if len(enabled) <= target_max:
        return []

    to_disable = []

    regime_u = str(regime or "").upper()
    regime_prefer_disable = []
    if regime_u in ("NEUTRAL", "COMPRESSION", "RANGE"):
        regime_prefer_disable = [
            "continuation",
            "time-series-momentum",
            "stochastic-momentum",
            "rsi-momentum",
            "macd-trend",
            "aggressive-movement-cf1358",
        ]
    elif regime_u in ("TREND_UP", "BULLISH_TRENDING"):
        regime_prefer_disable = [
            "bollinger-mr",
            "vwap-mr",
            "turtle",
        ]
    elif regime_u in ("TREND_DOWN", "BEARISH_TRENDING"):
        regime_prefer_disable = [
            "turtle",
            "donchian-breakout",
            "atr-breakout",
        ]

    ordered = []
    for key in regime_prefer_disable + DISABLE_FIRST:
        if key not in ordered:
            ordered.append(key)

    for key in ordered:
        if key in enabled and key not in KEEP_PRIORITY and key not in to_disable:
            to_disable.append(key)
            if len(enabled) - len(to_disable) <= target_max:
                break

    if len(enabled) - len(to_disable) > target_max:
        for key in enabled:
            if key not in KEEP_PRIORITY and key not in to_disable:
                to_disable.append(key)
                if len(enabled) - len(to_disable) <= target_max:
                    break

    if len(enabled) - len(to_disable) > target_max:
        for key in enabled:
            if key not in to_disable:
                to_disable.append(key)
                if len(enabled) - len(to_disable) <= target_max:
                    break

    return to_disable


def strategy_recommendation_agent(state: AgentState) -> AgentState:
    """
    Generates multiple ranked strategy options with risk guardrails.
    Paper-trading bias remains, but overload forces WAIT + cleanup suggestions.
    Marked outcomes (good/bad) nudge ranking over time.
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
    load_level = "OK"
    if open_positions >= 10 or enabled_count >= 9 or (open_positions >= 8 and enabled_count >= 6):
        load_level = "CRITICAL"
    elif open_positions >= 7 or enabled_count >= 7:
        load_level = "HIGH"
    elif open_positions >= 5 or enabled_count >= 5:
        load_level = "CAUTION"

    if load_level == "CRITICAL":
        for opt in [breakout, momentum, mean_reversion]:
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

    if risk == "Low" and load_level in ("HIGH", "CRITICAL"):
        for opt in [breakout, momentum, mean_reversion]:
            opt["confidence"] = max(0.40, opt["confidence"] - 0.05)
            opt["reason"] += " | Low risk profile + high load → defensive bias."

    # === Cleanup suggestions when overloaded ===
    target_enabled = 4 if risk == "Low" else 5
    disable_suggestions = []
    if load_level in ("HIGH", "CRITICAL") and enabled_count > target_enabled:
        disable_suggestions = suggest_disables(
            enabled_list,
            target_max=target_enabled,
            regime=regime,
        )

    if disable_suggestions:
        print("   Suggested cleanup (disable these to reduce load):")
        for key in disable_suggestions:
            print(f"     • disable {key}")

    # === Apply learning bias from past outcomes ===
    outcome_bias = get_outcome_bias(current_regime=regime)
    learning_notes = []
    marked_count = outcome_bias.pop("_marked_count", 0) if isinstance(outcome_bias, dict) else 0

    for opt, key in [
        (breakout, "Breakout Strategy"),
        (momentum, "Momentum Continuation"),
        (mean_reversion, "Mean Reversion Scalp"),
    ]:
        bias_value = float(outcome_bias.get(key, 0.0) or 0.0)
        if abs(bias_value) >= 0.01:
            opt["confidence"] += bias_value
            direction = "boosted" if bias_value > 0 else "reduced"
            learning_notes.append(f"{key} {direction} by {bias_value:+.2f} from marked outcomes")
            opt["reason"] += f" | Memory: {direction} ({bias_value:+.2f}) from past marks"

    wait_bias = float(outcome_bias.get("WAIT", 0.0) or 0.0)

    if learning_notes:
        print("   Learning adjustments:")
        for note in learning_notes:
            print(f"     • {note}")
        if abs(wait_bias) >= 0.01:
            print(f"     • WAIT bias {wait_bias:+.2f}")
    else:
        print("   Learning: no marked outcomes yet — use: mark <num> good/bad")
        print("             optional quality: mark <num> good good_process")

    for opt in [breakout, momentum, mean_reversion]:
        opt["confidence"] = round(min(0.92, max(0.40, opt["confidence"])), 2)

    options = [breakout, momentum, mean_reversion]
    options = sorted(options, key=lambda x: x["confidence"], reverse=True)

    # === WAIT Logic (stronger under load; nudged by WAIT memory) ===
    best_confidence = max(opt["confidence"] for opt in options)
    force_wait = (
        load_level == "CRITICAL"
        or open_positions >= 8
        or enabled_count >= 8
        or (risk == "Low" and load_level == "HIGH")
        or best_confidence < 0.58
    )
    # If WAIT was marked good often, prefer it a bit more when borderline
    if wait_bias >= 0.05 and best_confidence < 0.68 and load_level in ("CAUTION", "HIGH", "CRITICAL"):
        force_wait = True

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

        # Apply WAIT memory nudge
        if abs(wait_bias) >= 0.01:
            wait_conf = round(min(0.90, max(0.50, wait_conf + wait_bias)), 2)
            wait_reason += f" | Memory: WAIT bias {wait_bias:+.2f} from past marks."

        if disable_suggestions:
            cmds = ", ".join(f"disable {k}" for k in disable_suggestions[:5])
            wait_reason += f" Suggested cleanup: {cmds}."

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
    state["disable_suggestions"] = disable_suggestions
    state["load_level"] = load_level
    state["enabled_count"] = enabled_count
    state["open_positions_count"] = open_positions

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

    if disable_suggestions:
        ranking_reason += (
            " Cleanup suggested: "
            + ", ".join(disable_suggestions[:5])
            + "."
        )

    if regime == "COMPRESSION":
        ranking_reason += " Compression favors Breakout and Mean Reversion over pure Momentum."
    elif regime in ("BULLISH_TRENDING", "TREND_UP"):
        ranking_reason += " Uptrend favors Momentum Continuation."
    elif regime in ("BEARISH_TRENDING", "TREND_DOWN"):
        ranking_reason += " Downtrend favors Momentum Continuation on the short side."

    if learning_notes or abs(wait_bias) >= 0.01:
        ranking_reason += f" Confidence adjusted from {marked_count} marked past outcomes."

    state["ranking_explanation"] = ranking_reason
    state["next_agent"] = "supervisor"
    return state
