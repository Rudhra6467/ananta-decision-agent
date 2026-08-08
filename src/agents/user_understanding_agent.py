from src.state.agent_state import AgentState
from src.memory import get_last_user_profile, update_user_memory

def user_understanding_agent(state: AgentState) -> AgentState:
    """
    Understands the user. Uses memory if available, otherwise asks questions.
    """
    print("→ User Understanding Agent is working...")

    # Try to load previous profile from memory
    last_profile = get_last_user_profile()

    if last_profile and not state.get("user_goal"):
        print("   Found previous profile in memory.")
        use_memory = input("Do you want to use your previous profile? (yes/no): ").strip().lower()

        if use_memory in ["yes", "y"]:
            state["user_goal"] = last_profile.get("user_goal")
            state["risk_tolerance"] = last_profile.get("risk_tolerance")
            state["capital"] = last_profile.get("capital")
            state["preferred_markets"] = ["Crypto"]
            state["experience_level"] = last_profile.get("experience_level")

            print(f"   Using saved profile → Goal: {state['user_goal']} | Risk: {state['risk_tolerance']} | Capital: ${state['capital']}")
            state["next_agent"] = "supervisor"
            return state

    # If no memory or user said no → ask questions
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

        state["user_goal"] = goal if goal else "Moderate growth"
        state["risk_tolerance"] = risk if risk in ["Low", "Medium", "High"] else "Medium"
        state["capital"] = capital
        state["preferred_markets"] = ["Crypto"]
        state["experience_level"] = experience if experience else "Intermediate"

        # Save to memory
        update_user_memory(
            state["user_goal"],
            state["risk_tolerance"],
            state["capital"],
            state["experience_level"]
        )

        print("\n   Profile saved to memory.")
        print(f"   Goal: {state['user_goal']}")
        print(f"   Risk: {state['risk_tolerance']} | Capital: ${state['capital']}")

    state["next_agent"] = "supervisor"
    return state
