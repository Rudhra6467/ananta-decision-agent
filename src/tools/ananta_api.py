import os
import requests
from dotenv import load_dotenv

# Load .env from project root (if present)
load_dotenv()

BASE_URL = os.getenv("ANANTA_BASE_URL", "https://livetrading247.com").rstrip("/")


def login(email: str = None, password: str = None):
    """
    Log in as owner and return a fresh access token.
    Credentials are read from environment / .env by default.
    """
    email = email or os.getenv("ANANTA_EMAIL", "")
    password = password or os.getenv("ANANTA_PASSWORD", "")

    if not email or not password:
        return {
            "success": False,
            "error": "Missing ANANTA_EMAIL or ANANTA_PASSWORD. Set them in a local .env file (see .env.example)."
        }

    try:
        r = requests.post(
            f"{BASE_URL}/api/auth/login",
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


# Map agent recommendation names / aliases → Ananta strategy keys
STRATEGY_NAME_TO_KEY = {
    # Agent recommendation names (primary)
    "breakout strategy": "donchian-breakout",
    "breakout": "donchian-breakout",
    "donchian": "donchian-breakout",
    "momentum continuation": "continuation",
    "momentum": "continuation",
    "continuation strategy": "continuation",
    "mean reversion scalp": "bollinger-mr",
    "mean reversion": "bollinger-mr",
    "mean-reversion": "bollinger-mr",
    "mr scalp": "bollinger-mr",
    "bollinger": "bollinger-mr",
    "wait": None,
    "hold": None,
    "do nothing": None,

    # Direct Ananta names / keys
    "hunter": "hunter",
    "volatility squeeze": "squeeze",
    "vol squeeze": "squeeze",
    "squeeze": "squeeze",
    "continuation": "continuation",
    "ema cross": "ema-cross",
    "ema": "ema-cross",
    "ema-cross": "ema-cross",
    "supertrend": "supertrend",
    "rsi momentum": "rsi-momentum",
    "rsi": "rsi-momentum",
    "rsi-momentum": "rsi-momentum",
    "macd trend": "macd-trend",
    "macd": "macd-trend",
    "macd-trend": "macd-trend",
    "bollinger mean reversion": "bollinger-mr",
    "bollinger-mr": "bollinger-mr",
    "donchian breakout": "donchian-breakout",
    "donchian-breakout": "donchian-breakout",
    "atr breakout": "atr-breakout",
    "atr": "atr-breakout",
    "atr-breakout": "atr-breakout",
    "keltner breakout": "keltner-breakout",
    "keltner": "keltner-breakout",
    "keltner-breakout": "keltner-breakout",
    "turtle trading": "turtle",
    "turtle": "turtle",
    "time series momentum": "time-series-momentum",
    "tsmom": "time-series-momentum",
    "time-series-momentum": "time-series-momentum",
    "stochastic momentum": "stochastic-momentum",
    "stochastic": "stochastic-momentum",
    "stoch": "stochastic-momentum",
    "stochastic-momentum": "stochastic-momentum",
    "vwap mean reversion": "vwap-mr",
    "vwap": "vwap-mr",
    "vwap-mr": "vwap-mr",
    "aggressive movement": "aggressive-movement-cf1358",
    "aggressive": "aggressive-movement-cf1358",
    "aggressive-movement": "aggressive-movement-cf1358",
    "aggressive-movement-cf1358": "aggressive-movement-cf1358",
}


def _normalize_name(name: str) -> str:
    return (
        (name or "")
        .strip()
        .lower()
        .replace("_", "-")
        .replace("  ", " ")
    )


def _fuzzy_match_key(raw: str) -> str:
    """
    Best-effort match when exact alias is missing.
    Prefer longer / more specific keys when multiple match.
    """
    raw = _normalize_name(raw)
    if not raw:
        return None

    candidates = []
    for alias, key in STRATEGY_NAME_TO_KEY.items():
        if key is None:
            continue
        alias_n = _normalize_name(alias)
        if raw == alias_n or raw == key:
            return key
        if raw in alias_n or alias_n in raw or raw in key or key in raw:
            candidates.append((len(key), key))

    if not candidates:
        return None

    # Prefer longer (more specific) key
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def _match_against_registry(raw: str, token: str = None) -> str:
    """Try matching input against live Ananta strategy registry names/keys."""
    try:
        status = get_strategy_status(token=token)
        if not status.get("success"):
            return None
        raw_n = _normalize_name(raw)
        for s in status.get("strategies", []):
            key = (s.get("key") or "").lower()
            name = _normalize_name(s.get("name") or "")
            if not key:
                continue
            if raw_n == key or raw_n == name:
                return key
            if raw_n in key or key in raw_n or raw_n in name or name in raw_n:
                return key
    except Exception:
        return None
    return None


def resolve_strategy_key(name_or_key: str, token: str = None):
    """
    Convert a human strategy name or alias into an Ananta strategy key.

    Resolution order:
      1. Exact alias map
      2. Normalized dash form in map
      3. Fuzzy alias/key contains match
      4. Live registry name/key match (optional network)
      5. None if still unknown (do not invent keys)

    Returns None for WAIT / empty / unknown.
    """
    if not name_or_key:
        return None

    raw = _normalize_name(name_or_key)
    if raw in ("wait", "hold", "skip", "none", "do nothing"):
        return None

    # 1. Exact map
    if raw in STRATEGY_NAME_TO_KEY:
        return STRATEGY_NAME_TO_KEY[raw]

    # 2. Dash-normalized form in map
    normalized = raw.replace(" ", "-")
    if normalized in STRATEGY_NAME_TO_KEY:
        return STRATEGY_NAME_TO_KEY[normalized]

    # 3. Fuzzy local map
    fuzzy = _fuzzy_match_key(raw)
    if fuzzy:
        return fuzzy

    # 4. Live registry (best accuracy when online)
    live = _match_against_registry(raw, token=token)
    if live:
        return live

    # 5. If input already looks like a real key (contains hyphen or known style), pass through
    if "-" in normalized and normalized == raw.replace(" ", "-"):
        # Only accept if it matches a known key value
        known_keys = {v for v in STRATEGY_NAME_TO_KEY.values() if v}
        if normalized in known_keys:
            return normalized

    return None


def enable_strategy(strategy_key: str, enabled: bool = True, allowed_regimes: list = None, token: str = None):
    """
    Enable or disable a strategy using a valid owner token.
    If no token is provided, it will log in automatically.
    """
    if not token:
        login_result = login()
        if not login_result.get("success"):
            return {"success": False, "error": "Login failed", "details": login_result}
        token = login_result["token"]

    resolved = resolve_strategy_key(strategy_key, token=token)
    if not resolved:
        return {
            "success": False,
            "error": f"Unknown strategy '{strategy_key}'. Use status to see valid keys, or enable <key>.",
        }

    strategy_key = resolved

    if allowed_regimes is None:
        _wave_a = {
            "hunter": ["REVERSAL"],
            "squeeze": ["COMPRESSION"],
            "bollinger-mr": ["RANGE", "COMPRESSION"],
        }
        allowed_regimes = _wave_a.get(strategy_key, ["COMPRESSION"])

    url = f"{BASE_URL}/api/strategy/{strategy_key}/profile"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Origin": BASE_URL,
        "Referer": f"{BASE_URL}/"
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
            return {"success": True, "data": r.json(), "strategy_key": strategy_key}
        return {"success": False, "status_code": r.status_code, "error": r.text, "strategy_key": strategy_key}
    except Exception as e:
        return {"success": False, "error": str(e)}


def place_manual_paper_order(
    symbol: str,
    side: str,
    notional_usd: float = None,
    quantity: float = None,
    fraction: float = None,
    order_type: str = "MARKET",
    limit_price: float = None,
    token: str = None,
):
    """
    Place a real paper (or live-routed) order via Ananta POST /api/orders/manual.

    BUY: pass notional_usd (USD to deploy) and/or quantity.
    SELL: pass fraction (0..1) or quantity of an open position.
    Symbol: "BTC" or "BTC/USD" (must be in Ananta enabled_symbols).
    """
    if not token:
        login_result = login()
        if not login_result.get("success"):
            return {"success": False, "error": "Login failed", "details": login_result}
        token = login_result["token"]

    side_u = (side or "").upper()
    if side_u not in ("BUY", "SELL"):
        return {"success": False, "error": "side must be BUY or SELL"}

    payload = {
        "symbol": symbol,
        "side": side_u,
        "order_type": (order_type or "MARKET").upper(),
    }
    if notional_usd is not None:
        payload["notional_usd"] = float(notional_usd)
    if quantity is not None:
        payload["quantity"] = float(quantity)
    if fraction is not None:
        payload["fraction"] = float(fraction)
    if limit_price is not None:
        payload["limit_price"] = float(limit_price)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Origin": BASE_URL,
        "Referer": f"{BASE_URL}/",
    }

    try:
        r = requests.post(
            f"{BASE_URL}/api/orders/manual",
            json=payload,
            headers=headers,
            timeout=30,
        )
        if r.status_code in (200, 201):
            data = r.json() if r.text else {}
            return {"success": True, "data": data, "status_code": r.status_code}
        return {
            "success": False,
            "status_code": r.status_code,
            "error": r.text,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def run_evaluation_cycle(symbol: str = None, token: str = None):
    """
    Trigger one Ananta evaluation cycle (strategies scan / act).
    POST /api/cycle/run or /api/cycle/run/{symbol_base}
    """
    if not token:
        login_result = login()
        if not login_result.get("success"):
            return {"success": False, "error": "Login failed", "details": login_result}
        token = login_result["token"]

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Origin": BASE_URL,
        "Referer": f"{BASE_URL}/",
    }

    if symbol:
        base = symbol.split("/")[0].upper()
        url = f"{BASE_URL}/api/cycle/run/{base}"
    else:
        url = f"{BASE_URL}/api/cycle/run"

    try:
        r = requests.post(url, headers=headers, timeout=60)
        if r.status_code in (200, 201):
            data = r.json() if r.text else {}
            return {"success": True, "data": data, "status_code": r.status_code}
        return {"success": False, "status_code": r.status_code, "error": r.text}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_headers(token: str = None):
    """
    Prepare headers for Ananta API calls.
    """
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Origin": BASE_URL,
        "Referer": f"{BASE_URL}/",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def get_paper_trades(token: str = None, limit: int = 50):
    """
    Fetch paper trades from Ananta.
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
        "open_trades": open_trades[:10],
        "count": len(open_trades),
        "message": f"Found {len(open_trades)} paper trades"
    }


def get_strategy_status(token: str = None):
    """
    Get strategy registry + enabled status for each strategy.
    """
    if not token:
        login_result = login()
        if not login_result.get("success"):
            return {"success": False, "error": "Login failed", "details": login_result}
        token = login_result["token"]

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        r = requests.get(
            f"{BASE_URL}/api/strategy/registry",
            headers=headers,
            timeout=15
        )
        if r.status_code != 200:
            return {"success": False, "status_code": r.status_code, "error": r.text}

        data = r.json()
        strategies = data.get("strategies", [])

        enriched = []
        for s in strategies:
            key = s.get("key")
            if not key:
                continue

            try:
                pr = requests.get(
                    f"{BASE_URL}/api/strategy/{key}/profile",
                    headers=headers,
                    timeout=10
                )
                if pr.status_code == 200:
                    profile_data = pr.json()
                    enabled = profile_data.get("profile", {}).get("enabled", False)
                    s["enabled"] = enabled
                    s["status_label"] = "Enabled" if enabled else "Disabled"
                else:
                    s["enabled"] = False
                    s["status_label"] = "Unknown"
            except Exception:
                s["enabled"] = False
                s["status_label"] = "Unknown"

            enriched.append(s)

        return {"success": True, "strategies": enriched}

    except Exception as e:
        return {"success": False, "error": str(e)}


def get_enabled_strategies(token: str = None):
    """
    Returns a list of currently enabled strategy keys.
    """
    result = get_strategy_status(token)
    if not result.get("success"):
        return []

    enabled = []
    for s in result.get("strategies", []):
        if s.get("enabled"):
            enabled.append(s.get("key"))
    return enabled


def _owner_token(token: str = None):
    if token:
        return {"success": True, "token": token}
    return login()


def _auth_headers(token: str):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Origin": BASE_URL,
        "Referer": f"{BASE_URL}/",
    }


def get_strategy_registry(token: str = None):
    """GET /api/strategy/registry — DNA + schema. Auth optional on Ananta."""
    try:
        headers = {}
        got = _owner_token(token)
        if got.get("success") and got.get("token"):
            headers = _auth_headers(got["token"])
        r = requests.get(f"{BASE_URL}/api/strategy/registry", headers=headers, timeout=20)
        if r.status_code != 200:
            return {"success": False, "status_code": r.status_code, "error": r.text}
        data = r.json()
        return {"success": True, "strategies": data.get("strategies") or data or []}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_lab_coverage(token: str = None):
    got = _owner_token(token)
    if not got.get("success"):
        return {"success": False, "error": "Login failed", "details": got}
    try:
        r = requests.get(
            f"{BASE_URL}/api/lab/data/coverage",
            headers=_auth_headers(got["token"]),
            timeout=20,
        )
        if r.status_code != 200:
            return {"success": False, "status_code": r.status_code, "error": r.text}
        return {"success": True, "data": r.json()}
    except Exception as e:
        return {"success": False, "error": str(e)}


def create_lab_run(payload: dict, token: str = None):
    got = _owner_token(token)
    if not got.get("success"):
        return {"success": False, "error": "Login failed", "details": got}
    try:
        r = requests.post(
            f"{BASE_URL}/api/lab/runs",
            json=payload,
            headers=_auth_headers(got["token"]),
            timeout=30,
        )
        if r.status_code not in (200, 201):
            return {"success": False, "status_code": r.status_code, "error": r.text}
        return {"success": True, "data": r.json()}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_lab_run(run_id: str, token: str = None):
    got = _owner_token(token)
    if not got.get("success"):
        return {"success": False, "error": "Login failed", "details": got}
    try:
        r = requests.get(
            f"{BASE_URL}/api/lab/runs/{run_id}",
            headers=_auth_headers(got["token"]),
            timeout=30,
        )
        if r.status_code != 200:
            return {"success": False, "status_code": r.status_code, "error": r.text}
        return {"success": True, "data": r.json()}
    except Exception as e:
        return {"success": False, "error": str(e)}

