from src.state.agent_state import AgentState

def user_understanding_agent(state: AgentState) -> AgentState:
    """
    Understands the user by asking questions when information is missing.
    """
    print("→ User Understanding Agent is working...")

    # Ask for missing information
    if not state.get("user_goal"):
        print("\nAgent: I need to understand you better before making recommendations.")
        
        goal = input("What is your main goal? (e.g. Moderate growth, Aggressive growth, Capital protection): ").strip()
        risk = input("What is your risk tolerance? (Low / Medium / High): ").strip().capitalize()
        capital_input = input("How much capital are you working with? (e.g. 5000): ").strip()
        experience = input("What is your experience level? (Beginner / Intermediate / Advanced): ").strip().capitalize()

        try:
            capital = float(capital_input)
        except:
            capital = 5000.0

        state["user_goal"] = goal if goal else "Moderate growth with controlled risk"
        state["risk_tolerance"] = risk if risk in ["Low", "Medium", "High"] else "Medium"
        state["capital"] = capital
        state["preferred_markets"] = ["Crypto"]
        state["experience_level"] = experience if experience else "Intermediate"

        print("\n   Thank you. Profile updated.")
        print(f"   Goal: {state['user_goal']}")
        print(f"   Risk: {state['risk_tolerance']} | Capital: ${state['capital']}")
    else:
        print("   User profile already available.")

    state["next_agent"] = "supervisor"
    return state
