from src.state.agent_state import AgentState
from src.tools.ananta_tools import start_paper_trade

def tool_execution_agent(state: AgentState) -> AgentState:
    """
    Shows ranked options and asks user which one to proceed with.
    """
    print("→ Tool Execution Agent is ready...")

    options = state.get("strategy_options") or []
    capital = state.get("capital", 5000)

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
        state["decision"] = selected.get("name")
        state["confidence"] = selected.get("confidence")
        state["entry_idea"] = selected.get("entry_idea")
        state["stop_loss_idea"] = selected.get("stop_loss_idea")
        state["take_profit_idea"] = selected.get("take_profit_idea")

        # Log the decision for future analysis
        from src.tools.decision_log import save_decision
        save_decision({
            "strategy": selected.get("name"),
            "confidence": selected.get("confidence"),
            "style": selected.get("style"),
            "regime": state.get("market_regime"),
            "risk_tolerance": state.get("risk_tolerance"),
            "capital": capital,
            "open_positions": state.get("portfolio", {}).get("open_positions", 0),
            "entry_idea": selected.get("entry_idea"),
            "stop_loss_idea": selected.get("stop_loss_idea"),
            "take_profit_idea": selected.get("take_profit_idea"),
            "status": "simulated"
        })
        print("→ Decision logged for future analysis.")

        # Offer to enable the strategy for real
        print()
        selected_name = selected.get("name", "")
        if selected_name.upper() == "WAIT":
            print("→ WAIT selected — nothing to enable.")
        else:
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
                    else:
                        print(f"→ Could not enable automatically: {enable_result.get('error') or enable_result}")
                        print("  You can still enable it manually with: enable <name>")
            else:
                print("→ Strategy not enabled. You can enable it later with: enable <name>")
    else:
        print("→ Cancelled.")
        state["execution_status"] = "Cancelled by user"

    state["next_agent"] = "supervisor"
    return state
