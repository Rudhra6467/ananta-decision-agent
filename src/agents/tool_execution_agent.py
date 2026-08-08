from src.state.agent_state import AgentState
from src.tools.ananta_tools import start_paper_trade

def tool_execution_agent(state: AgentState) -> AgentState:
    """
    Asks for permission and then calls Ananta tools.
    """
    print("→ Tool Execution Agent is ready...")

    decision = state.get("decision", "None")
    confidence = state.get("confidence", 0)
    entry = state.get("entry_idea", "N/A")
    stop = state.get("stop_loss_idea", "N/A")
    tp = state.get("take_profit_idea", "N/A")
    capital = state.get("capital", 5000)

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
        print("\n→ Permission granted.")
        
        # Call the Ananta tool
        result = start_paper_trade(
            strategy_name=decision,
            capital=capital,
            entry_idea=entry,
            stop_loss=stop,
            take_profit=tp
        )
        
        state["execution_status"] = result["message"]
    else:
        print("\n→ Permission denied. No action taken.")
        state["execution_status"] = "REJECTED by user"

    state["next_agent"] = "supervisor"
    return state




