"""CLI helpers for real Ananta paper execution (buy/sell/cycle)."""


def _log_manual_order(side: str, symbol: str, result: dict, extra: dict = None):
    """Write a decision-memory record for a manual paper order."""
    try:
        from src.tools.decision_log import save_decision
        trade = (result.get("data") or {}).get("trade") or {}
        payload = {
            "market": "crypto",
            "symbol": trade.get("symbol") or symbol,
            "price": trade.get("price"),
            "strategy": "manual",
            "strategy_key": "manual",
            "confidence": 0,
            "style": "Manual",
            "reason": f"Manual paper {side} via Agent CLI",
            "entry_idea": f"{side} {symbol}",
            "user_selected": f"manual_{side.lower()}",
            "user_confirmed": True,
            "user_enabled_strategy": False,
            "user_override": False,
            "status": "filled" if result.get("success") else "failed",
            "expected_outcome": "manual_order",
            "notes": f"trade_id={trade.get('id')} notional={trade.get('notional')} qty={trade.get('quantity')}",
        }
        if extra:
            payload.update(extra)
        save_decision(payload)
        print("→ Logged to decision memory.")
    except Exception as e:
        print(f"→ (memory log skipped: {e})")


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
        _log_manual_order("BUY", symbol, result, {"capital": usd})
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
        _log_manual_order("SELL", symbol, result, {"notes": f"fraction={frac}"})
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
        if len(results) > 5:
            print(f"  ... and {len(results) - 5} more")
    else:
        print(f"→ Failed: {result.get('error') or result}")
    return True
