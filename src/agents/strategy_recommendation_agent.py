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

# Real Ananta strategies the agent can recommend + enable 1:1
# family → used for mark-outcome learning buckets
ANANTA_STRATEGY_CATALOG = [
    {
        "key": "hunter",
        "name": "Hunter",
        "family": "hunter",
        "style": "Balanced",
        "base": 0.70,
        "entry_idea": "Wait for Hunter reversal / setup filter on scanned symbols",
        "stop_loss_idea": "Use strategy fixed SL (profile target_loss)",
        "take_profit_idea": "Use strategy fixed TP (profile target_profit)",
        "reason": "Core Ananta hunter — selective setups, good default engine strategy.",
    },
    {
        "key": "squeeze",
        "name": "Volatility Squeeze",
        "family": "mean_reversion",
        "style": "Balanced",
        "base": 0.68,
        "entry_idea": "Enter when squeeze releases with direction confirmation",
        "stop_loss_idea": "Beyond squeeze range extreme",
        "take_profit_idea": "Measured move from squeeze height",
        "reason": "Volatility squeeze — strong when range is tight before expansion.",
    },
    {
        "key": "bollinger-mr",
        "name": "Bollinger Mean Reversion",
        "family": "mean_reversion",
        "style": "Balanced",
        "base": 0.66,
        "entry_idea": "Fade extremes at outer Bollinger band with rejection",
        "stop_loss_idea": "Beyond band extreme / range high-low",
        "take_profit_idea": "Mid-band or opposite side of range",
        "reason": "Mean reversion via Bollinger — fits neutral / compression regimes.",
    },
    {
        "key": "ema-cross",
        "name": "EMA Cross",
        "family": "momentum",
        "style": "Aggressive",
        "base": 0.64,
        "entry_idea": "Enter on EMA cross with trend alignment",
        "stop_loss_idea": "Below / above signal EMA structure",
        "take_profit_idea": "Trail with EMA or prior swing",
        "reason": "EMA cross — clean trend-following continuation tool.",
    },
    {
        "key": "continuation",
        "name": "Continuation",
        "family": "momentum",
        "style": "Aggressive",
        "base": 0.63,
        "entry_idea": "Enter on strong continuation candle + volume",
        "stop_loss_idea": "Below last higher low / structure",
        "take_profit_idea": "ATR trail or prior swing",
        "reason": "Momentum continuation — explores trend legs in paper mode.",
    },
    {
        "key": "donchian-breakout",
        "name": "Donchian Breakout",
        "family": "breakout",
        "style": "Aggressive",
        "base": 0.62,
        "entry_idea": "Enter on Donchian channel break with volume",
        "stop_loss_idea": "Opposite side of channel / range",
        "take_profit_idea": "1.5x–2x channel height",
        "reason": "Classic breakout — asymmetric when compression resolves.",
    },
    {
        "key": "supertrend",
        "name": "Supertrend",
        "family": "momentum",
        "style": "Aggressive",
        "base": 0.60,
        "entry_idea": "Enter with Supertrend flip in trend direction",
        "stop_loss_idea": "Other side of Supertrend line",
        "take_profit_idea": "Trail with Supertrend",
        "reason": "Supertrend — simple trend filter for directional legs.",
    },
    {
        "key": "vwap-mr",
        "name": "VWAP Mean Reversion",
        "family": "mean_reversion",
        "style": "Balanced",
        "base": 0.58,
        "entry_idea": "Fade extensions away from VWAP back to mean",
        "stop_loss_idea": "Beyond extension extreme",
        "take_profit_idea": "VWAP / mean reversion target",
        "reason": "VWAP mean reversion — intraday balance tool.",
    },
]

# Learning buckets (mark outcomes still map here)
FAMILY_LABELS = {
    "breakout": "Breakout Strategy",
    "momentum": "Momentum Continuation",
    "mean_reversion": "Mean Reversion Scalp",
    "hunter": "Hunter",
}

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
    "ema cross": "Momentum Continuation",
    "supertrend": "Momentum Continuation",
    "mean reversion scalp": "Mean Reversion Scalp",
    "mean reversion": "Mean Reversion Scalp",
    "bollinger-mr": "Mean Reversion Scalp",
    "bollinger": "Mean Reversion Scalp",
    "bollinger mean reversion": "Mean Reversion Scalp",
    "vwap-mr": "Mean Reversion Scalp",
    "vwap": "Mean Reversion Scalp",
    "squeeze": "Mean Reversion Scalp",
    "volatility squeeze": "Mean Reversion Scalp",
    "hunter": "Hunter",
    "wait": "WAIT",
}


def _canonical_strategy_name(raw: str):
    if not raw:
        return None
    s = str(raw).strip().lower()
    if s in STRATEGY_ALIASES:
        return STRATEGY_ALIASES[s]
    for key, canon in STRATEGY_ALIASES.items():
        if key in s or s in key:
            return canon
    return None


def get_outcome_bias(current_regime: str = None):
    """
    Confidence adjustments from marked outcomes.
    Buckets: Breakout / Momentum / Mean Reversion / Hunter / WAIT
    """
    empty = {
        "Breakout Strategy": 0.0,
        "Momentum Continuation": 0.0,
        "Mean Reversion Scalp": 0.0,
        "Hunter": 0.0,
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
        n = len(decisions)

        for i, d in enumerate(decisions):
            outcome = str(d.get("outcome", "pending")).lower()
            if outcome not in ("good", "bad", "neutral"):
                continue

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
            recency = 0.7 + 0.3 * ((i + 1) / n)

            delta = 0.0
            if outcome == "good":
                delta = 0.05
            elif outcome == "bad":
                delta = -0.06

            quality = str(d.get("decision_quality", "pending")).lower()
            if quality == "good_process":
                delta += 0.03 if outcome != "bad" else 0.01
            elif quality == "bad_process":
                delta -= 0.04 if outcome != "good" else 0.01

            d_regime = str(d.get("regime", "")).upper()
            if regime_u and d_regime and regime_u == d_regime:
                delta *= 1.25

            bias[canon] = bias.get(canon, 0.0) + delta * recency

        for k in list(bias.keys()):
            bias[k] = max(-0.15, min(0.15, round(bias[k], 3)))

        bias["_marked_count"] = marked
        return bias
    except Exception:
        return empty


def suggest_disables(enabled_list, target_max=5, regime="NEUTRAL"):
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
        regime_prefer_disable = ["bollinger-mr", "vwap-mr", "turtle"]
    elif regime_u in ("TREND_DOWN", "BEARISH_TRENDING"):
        regime_prefer_disable = ["turtle", "donchian-breakout", "atr-breakout"]

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


def _build_ananta_options(regime: str, risk: str, enabled_list: list):
    """Score real Ananta strategies for current regime / risk / enable state."""
    regime_u = str(regime or "NEUTRAL").upper()
    options = []

    for spec in ANANTA_STRATEGY_CATALOG:
        conf = float(spec["base"])
        reason = spec["reason"]
        entry = spec["entry_idea"]
        key = spec["key"]

        # Regime tilts
        if regime_u in ("COMPRESSION", "RANGE"):
            if key in ("squeeze", "bollinger-mr", "donchian-breakout", "vwap-mr"):
                conf += 0.08
                reason += " Regime compression/range supports this style."
            if key in ("continuation", "ema-cross", "supertrend"):
                conf -= 0.05
                reason += " Trend tools less ideal while compressed."
        elif regime_u in ("TREND_UP", "BULLISH_TRENDING"):
            if key in ("ema-cross", "continuation", "supertrend", "donchian-breakout"):
                conf += 0.10
                reason += " Uptrend favors momentum / breakout tools."
            if key in ("bollinger-mr", "vwap-mr"):
                conf -= 0.08
                reason += " Pure mean reversion weaker in strong uptrends."
        elif regime_u in ("TREND_DOWN", "BEARISH_TRENDING"):
            if key in ("continuation", "supertrend", "hunter", "ema-cross"):
                conf += 0.08
                reason += " Downtrend — directional / selective tools preferred."
            if key in ("donchian-breakout",):
                conf -= 0.03
        else:  # NEUTRAL
            if key in ("hunter", "squeeze", "bollinger-mr"):
                conf += 0.05
                reason += " Neutral tape — selective / mean-reversion lean."
            if key in ("continuation",):
                conf -= 0.03

        # Risk tolerance
        if risk == "High":
            if spec["style"] == "Aggressive":
                conf += 0.05
            else:
                conf += 0.02
        elif risk == "Low":
            if spec["style"] == "Aggressive":
                conf -= 0.08
            else:
                conf += 0.03
        elif risk == "Medium":
            if key in ("hunter", "squeeze", "bollinger-mr"):
                conf += 0.02

        already_on = key in (enabled_list or [])
        if already_on:
            conf -= 0.02  # mild preference to surface something not already on
            reason += " | Already enabled."
        else:
            reason += " | Not currently enabled."

        options.append({
            "name": spec["name"],
            "strategy_key": key,
            "family": spec["family"],
            "confidence": conf,
            "style": spec["style"],
            "entry_idea": entry,
            "stop_loss_idea": spec["stop_loss_idea"],
            "take_profit_idea": spec["take_profit_idea"],
            "reason": reason,
            "already_enabled": already_on,
        })

    return options


def strategy_recommendation_agent(state: AgentState) -> AgentState:
    """
    Ranks real Ananta strategies (enable 1:1) with load guardrails + learning.
    """
    print("→ Strategy Recommendation Agent is thinking...")

    regime = state.get("market_regime") or "NEUTRAL"
    risk = state.get("risk_tolerance") or "Medium"

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

    enabled_list = []
    try:
        enabled_list = get_enabled_strategies() or []
    except Exception:
        enabled_list = []
    enabled_count = len(enabled_list)

    print(f"   Load check → open positions: {open_positions} | enabled strategies: {enabled_count}")

    options = _build_ananta_options(regime, risk, enabled_list)

    # === RISK GUARDRAILS ===
    load_level = "OK"
    if open_positions >= 10 or enabled_count >= 9 or (open_positions >= 8 and enabled_count >= 6):
        load_level = "CRITICAL"
    elif open_positions >= 7 or enabled_count >= 7:
        load_level = "HIGH"
    elif open_positions >= 5 or enabled_count >= 5:
        load_level = "CAUTION"

    for opt in options:
        if load_level == "CRITICAL":
            penalty = 0.22 if opt["style"] == "Aggressive" else 0.16
            opt["confidence"] = max(0.40, opt["confidence"] - penalty)
            opt["reason"] += (
                f" | RISK: overloaded book "
                f"({open_positions} positions, {enabled_count} strategies on). Prefer WAIT."
            )
            opt["entry_idea"] = "Do not add size until exposure is reduced."
        elif load_level == "HIGH":
            penalty = 0.16 if opt["style"] == "Aggressive" else 0.10
            opt["confidence"] = max(0.45, opt["confidence"] - penalty)
            opt["reason"] += (
                f" | Warning: high load "
                f"({open_positions} positions, {enabled_count} strategies on). Be selective."
            )
        elif load_level == "CAUTION":
            penalty = 0.08 if opt["style"] == "Aggressive" else 0.05
            opt["confidence"] = max(0.50, opt["confidence"] - penalty)
            opt["reason"] += (
                f" | Note: elevated load "
                f"({open_positions} positions, {enabled_count} strategies on)."
            )

        if risk == "Low" and load_level in ("HIGH", "CRITICAL"):
            opt["confidence"] = max(0.40, opt["confidence"] - 0.05)
            opt["reason"] += " | Low risk profile + high load → defensive bias."

    # Cleanup suggestions
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

    # Learning bias by family
    outcome_bias = get_outcome_bias(current_regime=regime)
    learning_notes = []
    marked_count = outcome_bias.pop("_marked_count", 0) if isinstance(outcome_bias, dict) else 0

    for opt in options:
        family = opt.get("family")
        label = FAMILY_LABELS.get(family)
        bias_value = float(outcome_bias.get(label, 0.0) or 0.0) if label else 0.0
        # Hunter also accepts direct Hunter bucket
        if family == "hunter":
            bias_value += float(outcome_bias.get("Hunter", 0.0) or 0.0)
        if abs(bias_value) >= 0.01:
            opt["confidence"] += bias_value
            direction = "boosted" if bias_value > 0 else "reduced"
            learning_notes.append(
                f"{opt['name']} ({family}) {direction} by {bias_value:+.2f}"
            )
            opt["reason"] += f" | Memory: {direction} ({bias_value:+.2f}) from past marks"

    wait_bias = float(outcome_bias.get("WAIT", 0.0) or 0.0)

    if learning_notes:
        print("   Learning adjustments:")
        # de-dupe-ish print first few
        shown = set()
        for note in learning_notes:
            if note not in shown:
                print(f"     • {note}")
                shown.add(note)
        if abs(wait_bias) >= 0.01:
            print(f"     • WAIT bias {wait_bias:+.2f}")
    else:
        print("   Learning: no marked outcomes yet — use: mark <num> good/bad")

    for opt in options:
        opt["confidence"] = round(min(0.92, max(0.40, opt["confidence"])), 2)

    options = sorted(options, key=lambda x: x["confidence"], reverse=True)
    # Keep top 4 Ananta strategies in the menu (plus WAIT if forced)
    options = options[:4]

    best_confidence = max(opt["confidence"] for opt in options) if options else 0.5
    force_wait = (
        load_level == "CRITICAL"
        or open_positions >= 8
        or enabled_count >= 8
        or (risk == "Low" and load_level == "HIGH")
        or best_confidence < 0.58
    )
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

        if abs(wait_bias) >= 0.01:
            wait_conf = round(min(0.90, max(0.50, wait_conf + wait_bias)), 2)
            wait_reason += f" | Memory: WAIT bias {wait_bias:+.2f} from past marks."

        if disable_suggestions:
            cmds = ", ".join(f"disable {k}" for k in disable_suggestions[:5])
            wait_reason += f" Suggested cleanup: {cmds}."

        wait_option = {
            "name": "WAIT",
            "strategy_key": None,
            "family": "wait",
            "confidence": wait_conf,
            "style": "Defensive",
            "reason": wait_reason,
            "entry_idea": "No entry",
            "stop_loss_idea": "N/A",
            "take_profit_idea": "N/A",
            "already_enabled": False,
        }
        options = [wait_option] + options
        top = wait_option
    else:
        top = options[0]

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
    if top.get("strategy_key"):
        state["recommended_strategy_key"] = top["strategy_key"]

    print(f"   Top Recommendation: {top['name']} (Score: {top['confidence']})")
    if top.get("strategy_key"):
        print(f"   Ananta key: {top['strategy_key']}")
    print(f"   Load level: {load_level}")
    print(f"   Other options generated: {len(options) - 1}")

    ranking_reason = (
        f"Ranked real Ananta strategies by regime ({regime}), risk ({risk}), "
        f"open positions ({open_positions}), enabled strategies ({enabled_count})."
    )
    if load_level == "CRITICAL":
        ranking_reason += " CRITICAL load forced strong WAIT preference."
    elif load_level == "HIGH":
        ranking_reason += " High load reduced confidence on aggressive strategies."
    elif load_level == "CAUTION":
        ranking_reason += " Elevated load applied mild confidence haircut."

    if disable_suggestions:
        ranking_reason += " Cleanup suggested: " + ", ".join(disable_suggestions[:5]) + "."

    if regime_u := str(regime).upper():
        if regime_u in ("COMPRESSION", "RANGE"):
            ranking_reason += " Compression/range favors squeeze, bollinger-mr, breakout."
        elif regime_u in ("TREND_UP", "BULLISH_TRENDING"):
            ranking_reason += " Uptrend favors ema-cross, continuation, supertrend."
        elif regime_u in ("TREND_DOWN", "BEARISH_TRENDING"):
            ranking_reason += " Downtrend favors continuation / selective hunter."
        else:
            ranking_reason += " Neutral favors hunter, squeeze, bollinger-mr."

    if learning_notes or abs(wait_bias) >= 0.01:
        ranking_reason += f" Confidence adjusted from {marked_count} marked past outcomes."

    state["ranking_explanation"] = ranking_reason
    state["next_agent"] = "supervisor"
    return state
