from src.state.agent_state import AgentState
from src.tools.ananta_tools import start_paper_trade

def tool_execution_agent(state: AgentState) -> AgentState:
    """
    Shows ranked options and asks user which one to proceed with.
    Logs a rich decision-memory record on confirm (Phase A1).
    """
    print("→ Tool Execution Agent is ready...")

    options = state.get("strategy_options") or []
    capital = state.get("capital", 5000)
    top_name = (options[0].get("name") if options else state.get("decision")) or "None"

    if not options:
        # Fallback to single recommendation
        decision = state.get("decision", "None")
        entry = state.get("entry_idea", "N/A")
        stop = state.get("stop_loss_idea", "N/A")
        tp = state.get("take_profit_idea", "N/A")
        confidence = state.get("confidence", 0)

        print("\n" + "-" * 50)
        print("  PERMISSION REQUIRED")
        print("-" * 50)
        print(f"Recommended Strategy : {decision}")
        print(f"Confidence           : {confidence}")
        print(f"Entry Idea           : {entry}")
        print(f"Stop Loss Idea       : {stop}")
        print(f"Take Profit Idea     : {tp}")
        print("-" * 50)

        permission = input("Do you want to proceed with this recommendation? (yes/no): ").strip().lower()

        if permission in ["yes", "y"]:
            result = start_paper_trade(decision, capital, entry, stop, tp)
            state["execution_status"] = result["message"]
        else:
            state["execution_status"] = "REJECTED by user"

        state["next_agent"] = "supervisor"
        return state

    # Show ranked options
    print("\n" + "=" * 55)
    print("  SELECT A STRATEGY")
    print("=" * 55)

    for i, opt in enumerate(options, 1):
        print(f"{i}. {opt.get('name')} | Confidence: {opt.get('confidence')} | Style: {opt.get('style')}")
        print(f"   {opt.get('reason')}")
        print()

    print("0. Skip / Do nothing")
    print("=" * 55)

    choice = input("Enter the number of the strategy you want to proceed with: ").strip()

    try:
        choice_num = int(choice)
    except Exception:
        choice_num = 0

    if choice_num == 0 or choice_num > len(options):
        print("\n→ No strategy selected. No action taken.")
        state["execution_status"] = "No strategy selected"

        # Still log a skip for memory completeness
        try:
            from src.tools.decision_log import save_decision
            market_data = state.get("market_data") or {}
            portfolio = state.get("portfolio") or {}
            save_decision({
                "market": "crypto",
                "symbol": market_data.get("symbol", "BTC"),
                "price": market_data.get("price"),
                "change_24h": market_data.get("change_24h"),
                "regime": state.get("market_regime"),
                "user_goal": state.get("user_goal"),
                "risk_tolerance": state.get("risk_tolerance"),
                "capital": capital,
                "experience_level": state.get("experience_level"),
                "open_positions": portfolio.get("open_positions", 0),
                "portfolio_equity": portfolio.get("total_value"),
                "portfolio_notes": portfolio.get("notes"),
                "top_recommendation": top_name,
                "ranked_options": [
                    {"name": o.get("name"), "confidence": o.get("confidence"), "style": o.get("style")}
                    for o in options
                ],
                "strategy": "SKIP",
                "confidence": 0,
                "reason": "User skipped / no strategy selected",
                "ranking_explanation": state.get("ranking_explanation"),
                "user_selected": "SKIP",
                "user_confirmed": False,
                "user_enabled_strategy": False,
                "user_override": False,
                "status": "skipped",
                "expected_outcome": "no_action",
            })
            print("→ Skip logged to decision memory.")
        except Exception:
            pass

        state["next_agent"] = "supervisor"
        return state

    selected = options[choice_num - 1]

    print(f"\n→ You selected: {selected.get('name')}")
    print(f"  Confidence : {selected.get('confidence')}")
    print(f"  Entry      : {selected.get('entry_idea')}")
    print(f"  Stop Loss  : {selected.get('stop_loss_idea')}")
    print(f"  Take Profit: {selected.get('take_profit_idea')}")

    confirm = input("\nConfirm and simulate paper trade? (yes/no): ").strip().lower()

    if confirm in ["yes", "y"]:
        result = start_paper_trade(
            strategy_name=selected.get("name"),
            capital=capital,
            entry_idea=selected.get("entry_idea"),
            stop_loss=selected.get("stop_loss_idea"),
            take_profit=selected.get("take_profit_idea")
        )
        state["execution_status"] = result["message"]

        # Update all recommendation fields so final report matches user choice
        state["decision"] = selected.get("name")
        state["confidence"] = selected.get("confidence")
        state["reason"] = selected.get("reason")
        state["entry_idea"] = selected.get("entry_idea")
        state["stop_loss_idea"] = selected.get("stop_loss_idea")
        state["take_profit_idea"] = selected.get("take_profit_idea")

        selected_name = selected.get("name", "")
        user_override = str(selected_name).upper() != str(top_name).upper()
        enabled_ok = False
        strategy_key = None

        # Offer to enable the strategy for real
        print()
        if selected_name.upper() == "WAIT":
            print("→ WAIT selected — nothing to enable.")
            expected = "wait"
            status = "wait_confirmed"
        else:
            expected = "explore"
            status = "simulated"
            enable_confirm = input(f"Would you like to ENABLE '{selected_name}' strategy in Ananta now? (yes/no): ").strip().lower()
            if enable_confirm in ["yes", "y"]:
                from src.tools.ananta_api import enable_strategy, resolve_strategy_key
                strategy_key = resolve_strategy_key(selected_name)
                if not strategy_key:
                    print(f"→ Could not map '{selected_name}' to an Ananta strategy key.")
                    print("  You can still enable it manually with: enable <name>")
                else:
                    print(f"Enabling strategy: {strategy_key} ...")
                    enable_result = enable_strategy(strategy_key, True)
                    if enable_result.get("success"):
                        print(f"→ Strategy '{strategy_key}' enabled successfully in Ananta.")
                        enabled_ok = True
                        status = "enabled"
                    else:
                        print(f"→ Could not enable automatically: {enable_result.get('error') or enable_result}")
                        print("  You can still enable it manually with: enable <name>")
            else:
                print("→ Strategy not enabled. You can enable it later with: enable <name>")

        # Rich decision memory log (Phase A1)
        from src.tools.decision_log import save_decision
        market_data = state.get("market_data") or {}
        portfolio = state.get("portfolio") or {}

        invalidation = None
        if selected_name.upper() != "WAIT":
            invalidation = selected.get("stop_loss_idea") or "Reassess if regime or exposure changes materially"

        save_decision({
            "market": "crypto",
            "symbol": market_data.get("symbol", "BTC"),
            "price": market_data.get("price"),
            "change_24h": market_data.get("change_24h"),
            "regime": state.get("market_regime"),
            "user_goal": state.get("user_goal"),
            "risk_tolerance": state.get("risk_tolerance"),
            "capital": capital,
            "experience_level": state.get("experience_level"),
            "open_positions": portfolio.get("open_positions", 0),
            "portfolio_equity": portfolio.get("total_value"),
            "portfolio_notes": portfolio.get("notes"),
            "top_recommendation": top_name,
            "ranked_options": [
                {"name": o.get("name"), "confidence": o.get("confidence"), "style": o.get("style")}
                for o in options
            ],
            "strategy": selected_name,
            "strategy_key": strategy_key,
            "confidence": selected.get("confidence"),
            "style": selected.get("style"),
            "reason": selected.get("reason"),
            "ranking_explanation": state.get("ranking_explanation"),
            "entry_idea": selected.get("entry_idea"),
            "stop_loss_idea": selected.get("stop_loss_idea"),
            "take_profit_idea": selected.get("take_profit_idea"),
            "invalidation": invalidation,
            "expected_outcome": expected,
            "user_selected": selected_name,
            "user_confirmed": True,
            "user_enabled_strategy": enabled_ok,
            "user_override": user_override,
            "status": status,
        })
        print("→ Decision logged to memory (rich journal).")
    else:
        print("→ Cancelled.")
        state["execution_status"] = "Cancelled by user"

        try:
            from src.tools.decision_log import save_decision
            market_data = state.get("market_data") or {}
            portfolio = state.get("portfolio") or {}
            save_decision({
                "market": "crypto",
                "symbol": market_data.get("symbol", "BTC"),
                "price": market_data.get("price"),
                "regime": state.get("market_regime"),
                "user_goal": state.get("user_goal"),
                "risk_tolerance": state.get("risk_tolerance"),
                "capital": capital,
                "open_positions": portfolio.get("open_positions", 0),
                "portfolio_equity": portfolio.get("total_value"),
                "top_recommendation": top_name,
                "strategy": selected.get("name"),
                "confidence": selected.get("confidence"),
                "reason": selected.get("reason"),
                "user_selected": selected.get("name"),
                "user_confirmed": False,
                "user_enabled_strategy": False,
                "user_override": str(selected.get("name", "")).upper() != str(top_name).upper(),
                "status": "cancelled",
                "expected_outcome": "no_action",
            })
            print("→ Cancellation logged to decision memory.")
        except Exception:
            pass

    state["next_agent"] = "supervisor"
    return state
