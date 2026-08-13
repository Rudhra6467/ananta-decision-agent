"""CLI helpers for real Ananta paper execution (buy/sell/cycle)."""

def handle_buy(user_input: str) -> bool:
    if not user_input.startswith("buy "):
        return False
    from src.tools.ananta_api import place_manual_paper_order
    parts = user_input.split()
    if len(parts) < 3:
        print("Usage: buy <symbol> <usd_amount>")
        print("Example: buy BTC 25")
        return True
    symbol = parts[1].upper()
    try:
        usd = float(parts[2])
    except Exception:
        print("USD amount must be a number")
        return True
    print(f"You are about to PAPER BUY ${usd} of {symbol}")
    confirm = input("Confirm real paper order on Ananta? (yes/no): ").strip().lower()
    if confirm not in ["yes", "y"]:
        print("Cancelled.")
        return True
    result = place_manual_paper_order(symbol=symbol, side="BUY", notional_usd=usd)
    if result.get("success"):
        trade = (result.get("data") or {}).get("trade") or {}
        print("→ Paper BUY filled on Ananta.")
        print(f"  Symbol   : {trade.get('symbol', symbol)}")
        print(f"  Qty      : {trade.get('quantity')}")
        print(f"  Price    : {trade.get('price')}")
        print(f"  Notional : {trade.get('notional')}")
        print(f"  Trade id : {trade.get('id')}")
    else:
        print(f"→ Failed: {result.get('error') or result}")
    return True


def handle_sell(user_input: str) -> bool:
    if not user_input.startswith("sell "):
        return False
    from src.tools.ananta_api import place_manual_paper_order
    parts = user_input.split()
    if len(parts) < 3:
        print("Usage: sell <symbol> <fraction>")
        print("Example: sell BTC 1.0")
        return True
    symbol = parts[1].upper()
    try:
        frac = float(parts[2])
    except Exception:
        print("Fraction must be a number between 0 and 1")
        return True
    print(f"You are about to PAPER SELL fraction={frac} of {symbol}")
    confirm = input("Confirm real paper order on Ananta? (yes/no): ").strip().lower()
    if confirm not in ["yes", "y"]:
        print("Cancelled.")
        return True
    result = place_manual_paper_order(symbol=symbol, side="SELL", fraction=frac)
    if result.get("success"):
        print("→ Paper SELL submitted on Ananta.")
        print(f"  Response: {str(result.get('data'))[:300]}")
    else:
        print(f"→ Failed: {result.get('error') or result}")
    return True


def handle_cycle(user_input: str) -> bool:
    if user_input != "cycle" and not user_input.startswith("cycle "):
        return False
    from src.tools.ananta_api import run_evaluation_cycle
    parts = user_input.split()
    symbol = parts[1].upper() if len(parts) >= 2 else None
    print("Running one Ananta evaluation cycle" + (f" for {symbol}" if symbol else "") + " ...")
    result = run_evaluation_cycle(symbol=symbol)
    if result.get("success"):
        data = result.get("data") or {}
        print("→ Cycle completed.")
        print(f"  ran_at : {data.get('ran_at')}")
        results = data.get("results") or []
        print(f"  symbols processed: {len(results)}")
        for item in results[:5]:
            sym = item.get("symbol")
            macro = item.get("macro") or {}
            print(f"  • {sym}: bias={macro.get('bias')} conf={macro.get('confidence')} | {str(macro.get('reason', ''))[:80]}")
    else:
        print(f"→ Failed: {result.get('error') or result}")
    return True
