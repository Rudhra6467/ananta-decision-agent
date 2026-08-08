import requests

# Base URL of Ananta
BASE_URL = "https://livetrading247.com"

def get_headers(token: str = None):
    """
    Prepare headers for Ananta API calls.
    Later we will handle real authentication properly.
    """
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def get_paper_trades(token: str = None, limit: int = 50):
    """
    Fetch paper trades from Ananta.
    Currently returns the structure. Real token will be added later.
    """
    url = f"{BASE_URL}/api/trades?limit={limit}"
    
    try:
        response = requests.get(url, headers=get_headers(token), timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "data": data,
                "message": "Successfully fetched trades"
            }
        else:
            return {
                "success": False,
                "data": None,
                "message": f"Failed with status {response.status_code}"
            }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": f"Error: {str(e)}"
        }


def get_portfolio(token: str = None):
    """
    Fetch portfolio data from Ananta.
    """
    url = f"{BASE_URL}/api/portfolio"
    
    try:
        response = requests.get(url, headers=get_headers(token), timeout=15)
        
        if response.status_code == 200:
            return {
                "success": True,
                "data": response.json(),
                "message": "Successfully fetched portfolio"
            }
        else:
            return {
                "success": False,
                "data": None,
                "message": f"Failed with status {response.status_code}"
            }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": f"Error: {str(e)}"
        }


def get_account_summary(token: str = None):
    """
    Fetch account summary from Ananta.
    """
    url = f"{BASE_URL}/api/summary"
    
    try:
        response = requests.get(url, headers=get_headers(token), timeout=15)
        
        if response.status_code == 200:
            return {
                "success": True,
                "data": response.json(),
                "message": "Successfully fetched summary"
            }
        else:
            return {
                "success": False,
                "data": None,
                "message": f"Failed with status {response.status_code}"
            }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "message": f"Error: {str(e)}"
        }
def get_open_paper_trades(token: str = None):
    """
    Fetch paper trades and return a clean summary of open ones.
    """
    result = get_paper_trades(token=token, limit=100)
    
    if not result.get("success"):
        return {
            "success": False,
            "open_trades": [],
            "count": 0,
            "message": result.get("message", "Failed to fetch trades")
        }
    
    data = result.get("data", {})
    items = data.get("items", []) if isinstance(data, dict) else []
    
    open_trades = []
    for trade in items:
        if trade.get("status") == "FILLED" and trade.get("mode") == "PAPER":
            open_trades.append({
                "symbol": trade.get("symbol"),
                "side": trade.get("side"),
                "quantity": trade.get("quantity"),
                "price": trade.get("price"),
                "notional": trade.get("notional"),
                "note": trade.get("note"),
                "timestamp": trade.get("timestamp")
            })
    
    return {
        "success": True,
        "open_trades": open_trades[:10],  # limit to latest 10
        "count": len(open_trades),
        "message": f"Found {len(open_trades)} paper trades"
    }
