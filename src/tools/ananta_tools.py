def start_paper_trade(strategy_name: str, capital: float, entry_idea: str, stop_loss: str, take_profit: str):
    """
    This function will later connect to real Ananta paper trading.
    For now it simulates the action clearly.
    """
    print("\n" + "=" * 55)
    print("  ANANTA PAPER TRADE SIMULATION")
    print("=" * 55)
    print(f"Strategy        : {strategy_name}")
    print(f"Allocated Capital: ${capital}")
    print(f"Entry Idea      : {entry_idea}")
    print(f"Stop Loss       : {stop_loss}")
    print(f"Take Profit     : {take_profit}")
    print("-" * 55)
    print("Status: Paper trade has been prepared (simulated).")
    print("In the next phase, this will call the real Ananta API / function.")
    print("=" * 55)

    return {
        "status": "simulated_success",
        "strategy": strategy_name,
        "capital": capital,
        "message": "Paper trade simulated successfully"
    }


def get_paper_performance():
    """
    Later this will fetch real paper trading performance from Ananta.
    """
    return {
        "total_trades": 0,
        "win_rate": 0,
        "profit_factor": 0,
        "net_pnl": 0,
        "message": "No real paper trades connected yet"
    }


def list_available_strategies():
    """
    Later this will list real strategies from Ananta.
    """
    return [
        "Trend Following Long",
        "Trend Following Short",
        "Breakout Strategy",
        "Mean Reversion",
        "Range Trading"
    ]
