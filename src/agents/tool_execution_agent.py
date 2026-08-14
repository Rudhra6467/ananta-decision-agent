from src.state.agent_state import AgentState
from src.tools.ananta_tools import start_paper_trade


def _print_position_cleanup_hint(state: AgentState):
    """When book is heavy, remind user that positions (not only strategies) drive load."""
    load_level = state.get("load_level") or ""
    open_count = state.get("open_positions_count")
    portfolio = state.get("portfolio") or {}
    if open_count is None:
        open_count = portfolio.get("open_positions") or 0
    try:
        open_count = int(open_count)
    except Exception:
        open_count = 0

    if load_level not in ("HIGH", "CRITICAL") and open_count < 7:
        return

    print()
    print("POSITION LOAD NOTE")
    print("-" * 55)
    print(f"  Open positions driving load : {open_count}")
    print(f"  Load level                  : {load_level or 'elevated'}")
    print("  Strategies are trimmed, but open trades still force WAIT bias.")
    print("  Options:")
    print("    • review trades in Ananta cockpit / paper portfolio")
    print("    • close weak or duplicate paper positions")
    print("    • use: sell <symbol> <fraction>   (e.g. sell ARB 1.0)")
    print("    • use: cleanup")
    print("    • re-run analysis after exposure drops")
    print("-" * 55)


def tool_execution_agent(state: AgentState) -> AgentState:
    """
    Shows ranked options and asks user which one to proceed with.
    Logs a rich decision-memory record on confirm (Phase A1).
    WAIT path skips paper-trade simulation.
    """
    print("→ Tool Execution Agent is ready...")

    options = state.get("strategy_options") or []
    capital = state.get("capital", 5000)
    top_name = (options[0].get("name") if options else state.get("decision")) or "None"

    if not options:
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

    # Show ranked options (real Ananta names + keys when present)
    print("\n" + "=" * 55)
    print("  SELECT A STRATEGY")
    print("=" * 55)

    for i, opt in enumerate(options, 1):
        key = opt.get("strategy_key")
        key_bit = f" [{key}]" if key else ""
        on_bit = " ★on" if opt.get("already_enabled") else ""
        print(
            f"{i}. {opt.get('name')}{key_bit}{on_bit} | "
            f"Confidence: {opt.get('confidence')} | Style: {opt.get('style')}"
        )
        print(f"   {opt.get('reason')}")
        print()

    print("0. Skip / Do nothing")
    print("=" * 55)

    _print_position_cleanup_hint(state)

    choice = input("Enter the number of the strategy you want to proceed with: ").strip()

    try:
        choice_num = int(choice)
    except Exception:
        choice_num = 0

    if choice_num == 0 or choice_num > len(options):
        print("\n→ No strategy selected. No action taken.")
        state["execution_status"] = "No strategy selected"

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
                    {
                        "name": o.get("name"),
                        "key": o.get("strategy_key"),
                        "confidence": o.get("confidence"),
                        "style": o.get("style"),
                    }
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
    selected_name = selected.get("name", "")
    is_wait = str(selected_name).upper() == "WAIT"
    preset_key = selected.get("strategy_key")

    print(f"\n→ You selected: {selected_name}")
    if preset_key:
        print(f"  Ananta key : {preset_key}")
    print(f"  Confidence : {selected.get('confidence')}")
    print(f"  Entry      : {selected.get('entry_idea')}")
    print(f"  Stop Loss  : {selected.get('stop_loss_idea')}")
    print(f"  Take Profit: {selected.get('take_profit_idea')}")

    if is_wait:
        confirm = input("\nConfirm WAIT (no new risk / no enable)? (yes/no): ").strip().lower()
    else:
        confirm = input("\nConfirm this recommendation? (yes/no): ").strip().lower()

    if confirm in ["yes", "y"]:
        if is_wait:
            state["execution_status"] = "WAIT confirmed — no new risk taken"
            print("\n→ WAIT confirmed. No paper trade simulated. No strategy enabled.")
            _print_position_cleanup_hint(state)
        else:
            result = start_paper_trade(
                strategy_name=selected_name,
                capital=capital,
                entry_idea=selected.get("entry_idea"),
                stop_loss=selected.get("stop_loss_idea"),
                take_profit=selected.get("take_profit_idea")
            )
            state["execution_status"] = result["message"]

        state["decision"] = selected_name
        state["confidence"] = selected.get("confidence")
        state["reason"] = selected.get("reason")
        state["entry_idea"] = selected.get("entry_idea")
        state["stop_loss_idea"] = selected.get("stop_loss_idea")
        state["take_profit_idea"] = selected.get("take_profit_idea")

        user_override = str(selected_name).upper() != str(top_name).upper()
        enabled_ok = False
        strategy_key = preset_key

        if is_wait:
            expected = "wait"
            status = "wait_confirmed"
        else:
            expected = "explore"
            status = "simulated"
            label = f"{selected_name}" + (f" [{preset_key}]" if preset_key else "")
            enable_confirm = input(
                f"Would you like to ENABLE {label} in Ananta now? (yes/no): "
            ).strip().lower()
            if enable_confirm in ["yes", "y"]:
                from src.tools.ananta_api import enable_strategy, resolve_strategy_key
                strategy_key = preset_key or resolve_strategy_key(selected_name)
                if not strategy_key:
                    print(f"→ Could not map '{selected_name}' to an Ananta strategy key.")
                    print("  You can still enable it manually with: enable <name>")
                else:
                    print(f"Enabling strategy: {strategy_key} ...")
                    enable_result = enable_strategy(strategy_key, True)
                    if enable_result.get("success"):
                        strategy_key = enable_result.get("strategy_key") or strategy_key
                        print(f"→ Strategy '{strategy_key}' enabled successfully in Ananta.")
                        enabled_ok = True
                        status = "enabled"

                        cycle_now = input(
                            "Strategy enabled. Run one evaluation cycle now? (yes/no): "
                        ).strip().lower()
                        if cycle_now in ["yes", "y"]:
                            from src.tools.ananta_api import run_evaluation_cycle
                            print("Running one Ananta evaluation cycle ...")
                            cycle_result = run_evaluation_cycle()
                            if cycle_result.get("success"):
                                data = cycle_result.get("data") or {}
                                print("→ Cycle completed.")
                                print(f"  ran_at : {data.get('ran_at')}")
                                results = data.get("results") or []
                                print(f"  symbols processed: {len(results)}")
                                for item in results[:5]:
                                    sym = item.get("symbol")
                                    macro = item.get("macro") or {}
                                    print(
                                        f"  • {sym}: bias={macro.get('bias')} "
                                        f"conf={macro.get('confidence')} | "
                                        f"{str(macro.get('reason', ''))[:80]}"
                                    )
                                if len(results) > 5:
                                    print(f"  ... and {len(results) - 5} more")
                            else:
                                print(f"→ Cycle failed: {cycle_result.get('error') or cycle_result}")
                        else:
                            print("→ Skipped cycle. You can run it later with: cycle")
                    else:
                        print(f"→ Could not enable automatically: {enable_result.get('error') or enable_result}")
                        print("  You can still enable it manually with: enable <name>")
            else:
                print("→ Strategy not enabled. You can enable it later with: enable <name>")

        from src.tools.decision_log import save_decision
        market_data = state.get("market_data") or {}
        portfolio = state.get("portfolio") or {}

        invalidation = None
        if not is_wait:
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
                {
                    "name": o.get("name"),
                    "key": o.get("strategy_key"),
                    "confidence": o.get("confidence"),
                    "style": o.get("style"),
                }
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
                "strategy": selected_name,
                "strategy_key": preset_key,
                "confidence": selected.get("confidence"),
                "reason": selected.get("reason"),
                "user_selected": selected_name,
                "user_confirmed": False,
                "user_enabled_strategy": False,
                "user_override": str(selected_name).upper() != str(top_name).upper(),
                "status": "cancelled",
                "expected_outcome": "no_action",
            })
            print("→ Cancellation logged to decision memory.")
        except Exception:
            pass

    state["next_agent"] = "supervisor"
    return state
