from src.state.agent_state import AgentState

def tool_execution_agent(state: AgentState) -> AgentState:
    """
    Asks for permission before simulating an action.
    """
    print("→ Tool Execution Agent is ready...")

    decision = state.get("decision", "None")
    confidence = state.get("confidence", 0)
    entry = state.get("entry_idea", "N/A")
    stop = state.get("stop_loss_idea", "N/A")
    tp = state.get("take_profit_idea", "N/A")

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
        print("→ Simulating paper trade setup in Ananta...")
        print("→ (In future this will actually start a paper trade)")
        state["execution_status"] = "APPROVED - Paper trade simulated"
    else:
        print("\n→ Permission denied. No action taken.")
        state["execution_status"] = "REJECTED by user"

    state["next_agent"] = "supervisor"
    return state
