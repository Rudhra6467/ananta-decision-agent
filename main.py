from src.graph import agent_graph

def run_once():
    print("=" * 55)
    print("           Ananta Multi-Agent System")
    print("=" * 55)
    print()

    initial_state = {
        "messages": [],
        "user_goal": None,
        "risk_tolerance": None,
        "capital": None,
        "preferred_markets": None,
        "experience_level": None,
        "market_data": None,
        "market_regime": None,
        "decision": None,
        "reason": None,
        "confidence": None,
        "portfolio": None,
        "next_agent": None
    }

    result = agent_graph.invoke(initial_state)

    print("\n" + "=" * 55)
    print("           FINAL ANALYSIS RESULT")
    print("=" * 55)
    print()
    print("USER PROFILE")
    print(f"  Goal              : {result.get('user_goal')}")
    print(f"  Risk Tolerance    : {result.get('risk_tolerance')}")
    print(f"  Capital           : ${result.get('capital')}")
    print(f"  Preferred Markets : {result.get('preferred_markets')}")
    print(f"  Experience        : {result.get('experience_level')}")
    print()
    
    print("MARKET ANALYSIS")
    market_data = result.get("market_data") or {}
    print(f"  Symbol            : {market_data.get('symbol', 'BTC')}")
    print(f"  Current Price     : ${market_data.get('price', 'N/A')}")
    print(f"  24h Change        : {market_data.get('change_24h', 'N/A')}%")
    print(f"  Market Regime     : {result.get('market_regime')}")
    print()
    
    print("RECOMMENDATION")
    print(f"  Strategy          : {result.get('decision')}")
    print(f"  Confidence Score  : {result.get('confidence')}")
    print(f"  Reason            : {result.get('reason')}")
    print()

    portfolio = result.get("portfolio")
    if portfolio:
        print("PORTFOLIO ANALYSIS")
        print(f"  Total Value       : ${portfolio.get('total_value')}")
        print(f"  Cash              : ${portfolio.get('cash')}")
        print(f"  Invested          : ${portfolio.get('invested')}")
        print(f"  Open Positions    : {portfolio.get('open_positions')}")
        print(f"  Unrealized PnL    : ${portfolio.get('unrealized_pnl')}")
        print(f"  Risk Score        : {portfolio.get('risk_score')}")
        print(f"  Diversification   : {portfolio.get('diversification_score')}/10")
        print(f"  Notes             : {portfolio.get('notes')}")

    print("=" * 55)


def interactive_mode():
    print("=" * 55)
    print("     Ananta Agent - Interactive Mode")
    print("=" * 55)
    print("Type 'run' to get full analysis")
    print("Type 'exit' to quit")
    print("=" * 55)

    while True:
        user_input = input("\nYou: ").strip().lower()

        if user_input in ["exit", "quit", "q"]:
            print("Goodbye.")
            break
        elif user_input in ["run", "analyze", "start"]:
            run_once()
        else:
            print("Agent: Please type 'run' to analyze or 'exit' to quit.")


if __name__ == "__main__":
    interactive_mode()
