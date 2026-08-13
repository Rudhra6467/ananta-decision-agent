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

    strategy_options = result.get("strategy_options")
    if strategy_options and len(strategy_options) > 1:
        print("RANKED STRATEGY OPTIONS")
        for i, opt in enumerate(strategy_options, 1):
            print(f"  {i}. {opt.get('name')} | Confidence: {opt.get('confidence')} | Style: {opt.get('style')}")
            print(f"     {opt.get('reason')}")
        print()
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

        buy_count = sum(1 for t in open_trades if str(t.get("side", "")).upper() == "BUY")
        sell_count = sum(1 for t in open_trades if str(t.get("side", "")).upper() == "SELL")

        print("  Exposure Summary:")
        print(f"    • Long positions  : {buy_count}")
        print(f"    • Short positions : {sell_count}")

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
