from src.decision_agent import agent
from src.tools import get_market_data, get_open_positions

def run_agent():
    print("\n" + "="*50)
    print("ANANTA DECISION AGENT")
    print("="*50)

    # Prepare initial state
    initial_state = {
        "market_data": get_market_data(),
        "open_positions": get_open_positions(),
        "decision": "",
        "reason": "",
        "confidence": 0.0,
        "messages": []
    }

    # Show market data first
    market = initial_state["market_data"]
    print(f"\nMarket Data:")
    print(f"  Symbol       : {market['symbol']}")
    print(f"  Price        : ${market['price']}")
    print(f"  Trend        : {market['trend']}")
    print(f"  Volatility   : {market['volatility']}")
    print(f"  RSI          : {market['rsi']}")
    print(f"  Volume Change: {market['volume_change_percent']}%")

    # Run the agent
    result = agent.invoke(initial_state)

    print("\n" + "-"*50)
    print("AGENT DECISION")
    print("-"*50)
    print(f"Decision   : {result.get('decision')}")
    print(f"Confidence : {result.get('confidence', 0):.0%}")
    print(f"Reason     : {result.get('reason')}")
    print("="*50 + "\n")

if __name__ == "__main__":
    run_agent()
