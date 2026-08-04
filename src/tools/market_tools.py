import random

def get_market_data():
    """Simulate more realistic crypto market conditions"""
    regimes = ["TREND_UP", "TREND_DOWN", "NEUTRAL", "REVERSAL", "COMPRESSION"]
    regime = random.choice(regimes)

    price = round(random.uniform(58000, 71000), 2)
    volatility = round(random.uniform(0.9, 3.8), 2)
    rsi = round(random.uniform(25, 78), 1)
    volume_change = round(random.uniform(-35, 45), 1)

    return {
        "symbol": "BTC",
        "price": price,
        "trend": regime,
        "volatility": volatility,
        "rsi": rsi,
        "volume_change_percent": volume_change
    }

def get_open_positions():
    """Simulate current open positions"""
    return []

def get_strategy_rules():
    """Basic risk and strategy rules"""
    return {
        "max_risk_per_trade": 0.01,
        "allowed_actions": ["ENTER_LONG", "ENTER_SHORT", "EXIT", "HOLD"],
        "min_rsi_for_long": 35,
        "max_rsi_for_short": 65
}
