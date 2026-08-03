# Tools for Ananta Decision Agent

def get_market_data():
    """Temporary placeholder - later this will fetch real market data"""
    return {
        "symbol": "BTC",
        "price": 0,
        "trend": "unknown"
    }

def get_open_positions():
    """Temporary placeholder - later this will fetch paper trading positions"""
    return []

def get_strategy_rules():
    """Temporary placeholder - later this will load strategy rules from Ananta"""
    return {
        "max_risk_per_trade": 0.01,
        "allowed_actions": ["ENTER_LONG", "EXIT", "HOLD"]
    }
