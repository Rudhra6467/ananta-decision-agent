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
    print()
    print("  Suggested Plan:")
    print(f"    • Entry     : {result.get('entry_idea', 'N/A')}")
    print(f"    • Stop Loss : {result.get('stop_loss_idea', 'N/A')}")
    print(f"    • Take Profit: {result.get('take_profit_idea', 'N/A')}")
    print()
    if result.get("ranking_explanation"):
        print(f"  Ranking Logic   : {result.get('ranking_explanation')}")
        print()



    # Show all ranked options if available
    strategy_options = result.get("strategy_options")
    if strategy_options and len(strategy_options) > 1:
        print("RANKED STRATEGY OPTIONS")
        for i, opt in enumerate(strategy_options, 1):
            print(f"  {i}. {opt.get('name')} | Confidence: {opt.get('confidence')} | Style: {opt.get('style')}")
            print(f"     {opt.get('reason')}")
        print()

        # Offer to enable a strategy
        print("Would you like to enable one of these strategies?")
        print("Type: enable <name>   (example: enable hunter)")
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
        open_trades = trades_result.get("open_trades", [])
        
        print("OPEN PAPER TRADES (from Ananta)")
        for i, trade in enumerate(open_trades[:5], 1):
            symbol = trade.get('symbol', 'N/A')
            side = trade.get('side', 'N/A')
            qty = round(trade.get('quantity', 0), 4)
            price = trade.get('price', 'N/A')
            print(f"  {i}. {symbol} | {side} | Qty: {qty} | Price: ${price}")
        
        print(f"  Total shown: {min(5, len(open_trades))} of {trades_result.get('count')} paper trades")
        print()
        
        # Smart exposure summary
        buy_count = sum(1 for t in open_trades if str(t.get("side", "")).upper() == "BUY")
        sell_count = sum(1 for t in open_trades if str(t.get("side", "")).upper() == "SELL")
        
        print("  Exposure Summary:")
        print(f"    • Long positions  : {buy_count}")
        print(f"    • Short positions : {sell_count}")
        
    # Simple intelligent comment on open trades
    if buy_count > 5:
        print("  Note: Portfolio is heavily long. Consider reducing exposure or waiting for better setups.")
    elif sell_count > buy_count:
        print("  Note: More short positions than long. Bias is currently defensive.")
    elif buy_count == 0 and sell_count == 0:
        print("  Note: No open paper trades. Good time to look for new setups.")
    else:
        print("  Note: Exposure looks manageable.")
    print()


    if buy_count > sell_count + 2:
        print("    • Bias            : Currently net long")
    elif sell_count > buy_count + 2:
        print("    • Bias            : Currently net short")
    else:
        print("    • Bias            : Relatively balanced")
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

        elif user_input.startswith("mark "):
            from src.tools.decision_log import update_decision_outcome
            parts = user_input.split()
            
            if len(parts) < 3:
                print("Usage: mark <number> <good/bad/neutral>")
                print("Example: mark 1 good")
            else:
                try:
                    index = int(parts[1])
                    outcome = parts[2].lower()
                    
                    if outcome not in ["good", "bad", "neutral"]:
                        print("Outcome must be: good / bad / neutral")
                    else:
                        success = update_decision_outcome(index, outcome)
                        if success:
                            print(f"→ Decision #{index} marked as '{outcome}'")
                        else:
                            print("Could not update decision. Check the number.")
                except:
                    print("Usage: mark <number> <good/bad/neutral>")

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
                print("-" * 60)

        elif user_input in ["performance", "stats", "summary"]:
            from src.tools.decision_log import get_recent_decisions
            decisions = get_recent_decisions(limit=50)
            
            if not decisions:
                print("No decisions logged yet.")
            else:
                total = len(decisions)
                good = sum(1 for d in decisions if d.get("outcome") == "good")
                bad = sum(1 for d in decisions if d.get("outcome") == "bad")
                neutral = sum(1 for d in decisions if d.get("outcome") == "neutral")
                pending = sum(1 for d in decisions if d.get("outcome") == "pending")
                
                print("\nDecision Performance Summary")
                print("-" * 40)
                print(f"  Total decisions   : {total}")
                print(f"  Marked Good       : {good}")
                print(f"  Marked Bad        : {bad}")
                print(f"  Marked Neutral    : {neutral}")
                print(f"  Still Pending     : {pending}")
                
                if good + bad > 0:
                    win_rate = round((good / (good + bad)) * 100, 1)
                    print(f"  Current Win Rate  : {win_rate}%")
                print("-" * 40)

                for i, d in enumerate(reversed(decisions), 1):
                    outcome = d.get("outcome", "pending")
                    print(f"{i}. {d.get('strategy')} | Conf: {d.get('confidence')} | Outcome: {outcome}")
                    print(f"   Regime: {d.get('regime')} | Style: {d.get('style')} | Positions: {d.get('open_positions')}")
                    print(f"   Time: {str(d.get('timestamp', ''))[:19]}")
                print("-" * 60)


        elif user_input in ["help", "commands", "?"]:
            print("\nAvailable commands:")
            print("  run / analyze / recommend  → Full market analysis")
            print("  status                     → Show all strategies from Ananta")
            print("  enable <name>              → Enable a strategy (with confirmation)")
            print("  disable <name>             → Disable a strategy (with confirmation)")
            print("  profile                    → Show your saved profile")
            print("  history                    → Show recent decisions")
            print("  performance / stats        → Decision performance summary")
            print("  mark <num> good/bad/neutral→ Mark a decision outcome")
            print("  clear                      → Clear saved memory")
            print("  help                       → Show this message")
            print("  exit                       → Quit the agent")
            print("  monitor / health / check     → Quick portfolio & strategy health check")
            print()


        elif user_input.startswith("enable "):
           from src.tools.ananta_api import enable_strategy
           parts = user_input.split()
           if len(parts) < 2:
              print("Usage: enable <strategy_name>")
              print("Example: enable hunter")
           else:
               strategy_name = parts[1].lower()
               print(f"You are about to ENABLE strategy: {strategy_name}")
               confirm = input("Are you sure? (yes/no): ").strip().lower()
               if confirm in ["yes", "y"]:
                   print(f"Enabling strategy: {strategy_name} ...")
                   result = enable_strategy(strategy_name, True)
                   if result.get("success"):
                      print(f"→ Strategy '{strategy_name}' enabled successfully.")
                   else:
                      print(f"→ Failed: {result.get('error') or result}")
               else:
                   print("Cancelled. Strategy was not enabled.")
       
        elif user_input.startswith("disable "):
           from src.tools.ananta_api import enable_strategy
           parts = user_input.split()
           if len(parts) < 2:
              print("Usage: disable <strategy_name>")
              print("Example: disable hunter")
           else:
               strategy_name = parts[1].lower()
               print(f"You are about to DISABLE strategy: {strategy_name}")
               confirm = input("Are you sure? (yes/no): ").strip().lower()
               if confirm in ["yes", "y"]:
                   print(f"Disabling strategy: {strategy_name} ...")
                   result = enable_strategy(strategy_name, False)
                   if result.get("success"):
                      print(f"→ Strategy '{strategy_name}' disabled successfully.")
                   else:
                       print(f"→ Failed: {result.get('error') or result}")
               else:
                   print("Cancelled. Strategy was not disabled.")


        elif user_input in ["monitor", "health", "check"]:
           from src.tools.ananta_api import get_strategy_status, get_open_paper_trades
           from src.tools.ananta_api import get_portfolio  # if available, otherwise skip

           print("\nANANTA AGENT MONITOR")
           print("=" * 50)

           # Enabled strategies
           status_result = get_strategy_status()
           enabled = []
           if status_result.get("success"):
               for s in status_result.get("strategies", []):
                   if s.get("enabled"):
                       enabled.append(s.get("name", s.get("key")))
               print(f"Enabled Strategies : {len(enabled)}")
               if enabled:
                   for name in enabled:
                       print(f"  • {name}")
               else:
                   print("  • None")
           else:
               print("Enabled Strategies : Could not fetch")

           # Open trades
           trades_result = get_open_paper_trades()
           open_count = 0
           if trades_result.get("success"):
               open_count = trades_result.get("count", 0)
               print(f"Open Paper Trades  : {open_count}")
           else:
               print("Open Paper Trades  : Could not fetch")


           # Simple intelligent comment
           print()
           if open_count >= 10:
               print("⚠  Note: Very high number of open trades. Strongly consider reducing exposure.")
           elif open_count >= 7:
               print("⚠  Note: Portfolio is heavily loaded. Be selective with new entries.")
           elif open_count >= 4:
               print("Note: Moderate exposure. Monitor closely.")
           elif open_count == 0:
               print("Note: No open trades. Good time to look for setups.")
           else:
               print("Note: Exposure looks manageable.")

           if len(enabled) >= 5:
               print("Note: Many strategies are enabled. Watch for overlapping signals.")
           print("=" * 50)


        elif user_input in ["status", "strategies", "strategy status"]:
           from src.tools.ananta_api import get_strategy_status
           print("Fetching strategy status from Ananta...")
           result = get_strategy_status()
           if result.get("success"):
               strategies = result.get("strategies", [])
               print("\nSTRATEGY STATUS")
               print("=" * 55)
               if not strategies:
                   print("No strategies found.")
               else:
                   enabled_count = 0
                   for s in strategies:
                       key = s.get("key", "unknown")
                       name = s.get("name", key)
                       status = s.get("status_label", "Unknown")
                       enabled = s.get("enabled", False)
                       if enabled:
                           enabled_count += 1
                           mark = "●"
                       else:
                           mark = "○"
                       print(f"{mark} {name} ({key})  →  {status}")
                   print()
                   print(f"Total: {len(strategies)} strategies | Enabled: {enabled_count}")
           else:
               print(f"Failed to get status: {result.get('error') or result}")

        else:
            print("Agent: I didn't understand that. Type 'help' to see available commands.")

if __name__ == "__main__":
    interactive_mode()
