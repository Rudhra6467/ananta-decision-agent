import requests
import random

def get_market_data():
    """
    Get real BTC market data + simple regime detection.
    """
    try:
        # Get real Bitcoin price from CoinGecko (free, no API key needed)
        response = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={
                "ids": "bitcoin",
                "vs_currencies": "usd",
                "include_24hr_change": "true",
                "include_24hr_vol": "true"
            },
            timeout=10
        )
        data = response.json()

        price = data["bitcoin"]["usd"]
        change_24h = data["bitcoin"]["usd_24h_change"]
        volume = data["bitcoin"].get("usd_24h_vol", 0)

        # Simple regime detection based on 24h change
        if change_24h > 3:
            regime = "BULLISH_TRENDING"
        elif change_24h < -3:
            regime = "BEARISH_TRENDING"
        elif abs(change_24h) < 1:
            regime = "COMPRESSION"
        else:
            regime = "NEUTRAL"

        # Approximate RSI-like value from change (simplified)
        rsi = 50 + (change_24h * 2)
        rsi = max(20, min(80, rsi))

        return {
            "symbol": "BTC",
            "price": round(price, 2),
            "trend": regime,
            "volatility": round(abs(change_24h) / 3, 2),
            "rsi": round(rsi, 1),
            "volume_change_percent": round(change_24h, 2),
            "change_24h": round(change_24h, 2)
        }

    except Exception as e:
        print(f"   Warning: Could not fetch real data ({e}). Using simulated data.")
        # Fallback to simulated data
        regimes = ["TREND_UP", "TREND_DOWN", "NEUTRAL", "REVERSAL", "COMPRESSION"]
        regime = random.choice(regimes)
        return {
            "symbol": "BTC",
            "price": round(random.uniform(58000, 71000), 2),
            "trend": regime,
            "volatility": round(random.uniform(0.9, 3.8), 2),
            "rsi": round(random.uniform(25, 78), 1),
            "volume_change_percent": round(random.uniform(-35, 45), 1),
            "change_24h": 0
        }


def get_open_positions():
    return []


def get_strategy_rules():
    return {
        "max_risk_per_trade": 0.01,
        "allowed_actions": ["ENTER_LONG", "ENTER_SHORT", "EXIT", "HOLD"]
    }
