from src.graph import agent_graph
from src.memory import get_last_user_profile
import os

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
        "entry_idea": None,
        "stop_loss_idea": None,
        "take_profit_idea": None,
        "portfolio": None,
        "execution_status": None,
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
    print(f"  Top Strategy      : {result.get('decision')}")
    print(f"  Confidence Score  : {result.get('confidence')}")
    print(f"  Reason            : {result.get('reason')}")
    print(f"  Entry Idea        : {result.get('entry_idea', 'N/A')}")
    print(f"  Stop Loss Idea    : {result.get('stop_loss_idea', 'N/A')}")
    print(f"  Take Profit Idea  : {result.get('take_profit_idea', 'N/A')}")
    print()

    # Show all ranked options if available
    strategy_options = result.get("strategy_options")
    if strategy_options and len(strategy_options) > 1:
        print("RANKED STRATEGY OPTIONS")
        for i, opt in enumerate(strategy_options, 1):
            print(f"  {i}. {opt.get('name')} | Confidence: {opt.get('confidence')} | Style: {opt.get('style')}")
            print(f"     Reason: {opt.get('reason')}")
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
        print()

    # Show real paper trades if available
    from src.tools.ananta_api import get_open_paper_trades
    trades_result = get_open_paper_trades()
    
    if trades_result.get("success") and trades_result.get("count", 0) > 0:
        print("OPEN PAPER TRADES (from Ananta)")
        for i, trade in enumerate(trades_result.get("open_trades", [])[:5], 1):
            print(f"  {i}. {trade.get('symbol')} | {trade.get('side')} | Qty: {round(trade.get('quantity', 0), 4)} | Price: ${trade.get('price')}")
        print(f"  Total shown: {min(5, trades_result.get('count', 0))} of {trades_result.get('count')} paper trades")
        print()

    print("EXECUTION STATUS")
    print(f"  Status            : {result.get('execution_status', 'Not executed')}")
    print("=" * 55)

def interactive_mode():
    print("=" * 55)
    print("     Ananta Agent - Interactive Mode")
    print("=" * 55)
    print("You can type:")
    print("  run / analyze / recommend  → Full analysis")
    print("  profile                    → Show saved profile")
    print("  clear                      → Clear memory")
    print("  help                       → Show commands")
    print("  exit                       → Quit")
    print("=" * 55)

    while True:
        user_input = input("\nYou: ").strip().lower()

        if user_input in ["exit", "quit", "q"]:
            print("Goodbye.")
            break

        elif user_input in ["run", "analyze", "recommend", "start", "analysis"]:
            run_once()

        elif user_input in ["profile", "my profile", "show profile", "what is my profile"]:
            from src.memory import get_last_user_profile
            profile = get_last_user_profile()
            if profile:
                print("\nSaved Profile:")
                print(f"  Goal       : {profile.get('user_goal')}")
                print(f"  Risk       : {profile.get('risk_tolerance')}")
                print(f"  Capital    : ${profile.get('capital')}")
                print(f"  Experience : {profile.get('experience_level')}")
            else:
                print("No saved profile found.")

        elif user_input in ["clear", "clear memory", "reset"]:
            import os
            if os.path.exists("agent_memory.json"):
                os.remove("agent_memory.json")
                print("Memory cleared successfully.")
            else:
                print("No memory file found.")
       
        elif user_input in ["history", "decisions", "log"]:
            from src.tools.decision_log import get_recent_decisions
            decisions = get_recent_decisions(limit=8)
            
            if not decisions:
                print("No decisions logged yet.")
            else:
                print("\nRecent Decisions:")
                print("-" * 55)
                for i, d in enumerate(reversed(decisions), 1):
                    print(f"{i}. {d.get('strategy')} | Confidence: {d.get('confidence')} | Regime: {d.get('regime')}")
                    print(f"   Style: {d.get('style')} | Status: {d.get('status')} | Time: {d.get('timestamp', '')[:19]}")
                print("-" * 55)

        elif user_input in ["help", "commands", "?"]:
            print("\nAvailable commands:")
            print("  run / analyze / recommend  → Full market analysis")
            print("  profile                    → Show your saved profile")
            print("  history                    → Show recent decisions")
            print("  clear                      → Clear saved memory")
            print("  help                       → Show this message")
            print("  exit                       → Quit the agent")

        else:
            print("Agent: I didn't understand that. Type 'help' to see available commands.")

if __name__ == "__main__":
    interactive_mode()
