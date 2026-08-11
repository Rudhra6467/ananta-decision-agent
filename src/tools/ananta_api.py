import requests

def login(email: str = "owner@ananta.ai", password: str = "123@ParvathiShiva"):
    """
    Log in as owner and return a fresh access token.
    """
    import requests
    try:
        r = requests.post(
            "https://livetrading247.com/api/auth/login",
            json={"email": email, "password": password},
            headers={"Content-Type": "application/json"},
            timeout=15
        )
        if r.status_code == 200:
            data = r.json()
            return {
                "success": True,
                "token": data.get("token"),
                "email": data.get("email"),
                "role": data.get("role")
            }
        return {"success": False, "status_code": r.status_code, "error": r.text}
    except Exception as e:
        return {"success": False, "error": str(e)}


def enable_strategy(strategy_key: str, enabled: bool = True, allowed_regimes: list = None, token: str = None):
    """
    Enable or disable a strategy using a valid owner token.
    If no token is provided, it will log in automatically.
    """
    import requests

    if not token:
        login_result = login()
        if not login_result.get("success"):
            return {"success": False, "error": "Login failed", "details": login_result}
        token = login_result["token"]

    if allowed_regimes is None:
        allowed_regimes = ["REVERSAL"] if strategy_key == "hunter" else ["COMPRESSION"]

    url = f"https://livetrading247.com/api/strategy/{strategy_key}/profile"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Origin": "https://livetrading247.com",
        "Referer": "https://livetrading247.com/"
    }
    payload = {
        "enabled": enabled,
        "allowed_regimes": allowed_regimes,
        "exit_method": "fixed",
        "exit_params": {
            "target_profit": 5.0,
            "target_loss": 3.5
        }
    }

    try:
        r = requests.put(url, json=payload, headers=headers, timeout=15)
        if r.status_code in (200, 201):
            return {"success": True, "data": r.json()}
        return {"success": False, "status_code": r.status_code, "error": r.text}
    except Exception as e:
        return {"success": False, "error": str(e)}

# Base URL of Ananta
BASE_URL = "https://livetrading247.com"

def get_headers(token: str = None):
    """
    Prepare headers for Ananta API calls.
    """
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Origin": "https://livetrading247.com",
        "Referer": "https://livetrading247.com/",
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

def get_strategy_status(token: str = None):
    """
    Get current strategy registry and enabled status.
    """
    import requests

    if not token:
        login_result = login()
        if not login_result.get("success"):
            return {"success": False, "error": "Login failed", "details": login_result}
        token = login_result["token"]

    try:
        r = requests.get(
            "https://livetrading247.com/api/strategy/registry",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            timeout=15
        )
        if r.status_code == 200:
            return {"success": True, "data": r.json()}
        return {"success": False, "status_code": r.status_code, "error": r.text}
    except Exception as e:
        return {"success": False, "error": str(e)}
