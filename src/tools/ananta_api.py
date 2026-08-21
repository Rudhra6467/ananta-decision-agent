import os
import requests
from dotenv import load_dotenv

# Load .env from project root (if present). Does not override already-set shell env.
load_dotenv()


def get_base_url() -> str:
    """Read on every call so shell/env changes are visible without reimport tricks."""
    return os.getenv("ANANTA_BASE_URL", "https://livetrading247.com").rstrip("/")


# Back-compat alias for any import of BASE_URL (prefer get_base_url()).
BASE_URL = get_base_url()


def format_login_error(login_result: dict) -> str:
    """Human-readable login failure — never hide connection vs auth vs missing env."""
    if not isinstance(login_result, dict):
        return f"Login failed: {login_result}"
    if login_result.get("success"):
        return "ok"
    base = login_result.get("base_url") or get_base_url()
    err = login_result.get("error") or "unknown error"
    code = login_result.get("status_code")
    parts = [f"Login failed → {base}"]
    if code is not None:
        parts.append(f"HTTP {code}")
    parts.append(str(err)[:400])
    hint = login_result.get("hint")
    if hint:
        parts.append(f"Hint: {hint}")
    return " | ".join(parts)


def login(email: str = None, password: str = None):
    """
    Log in as owner and return a fresh access token.
    Credentials are read from environment / .env by default.
    """
    base = get_base_url()
    email = email or os.getenv("ANANTA_EMAIL", "")
    password = password or os.getenv("ANANTA_PASSWORD", "")

    if not email or not password:
        return {
            "success": False,
            "base_url": base,
            "error": "Missing ANANTA_EMAIL or ANANTA_PASSWORD",
            "hint": "Copy .env.example → .env and set email/password to the SAME values as Ananta backend OWNER_EMAIL / OWNER_PASSWORD.",
        }

    url = f"{base}/api/auth/login"
    try:
        r = requests.post(
            url,
            json={"email": email, "password": password},
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        if r.status_code == 200:
            data = r.json()
            token = data.get("token")
            if not token:
                return {
                    "success": False,
                    "base_url": base,
                    "status_code": 200,
                    "error": "Login response had no token field",
                    "hint": "Unexpected API shape — is ANANTA_BASE_URL pointing at the Ananta FastAPI backend?",
                }
            return {
                "success": True,
                "token": token,
                "email": data.get("email"),
                "role": data.get("role"),
                "base_url": base,
            }
        hint = None
        if r.status_code in (401, 403):
            hint = (
                "Credentials rejected. ANANTA_EMAIL/ANANTA_PASSWORD must match "
                "backend OWNER_EMAIL/OWNER_PASSWORD (and owner must be seeded — backend needs those env vars on startup)."
            )
        elif r.status_code == 404:
            hint = "No /api/auth/login on this host — wrong ANANTA_BASE_URL (UI host instead of FastAPI backend?)."
        elif r.status_code >= 500:
            hint = "Backend error — check Ananta uvicorn logs and MongoDB connectivity."
        return {
            "success": False,
            "base_url": base,
            "status_code": r.status_code,
            "error": (r.text or "")[:500],
            "hint": hint,
        }
    except requests.exceptions.ConnectionError as e:
        return {
            "success": False,
            "base_url": base,
            "error": f"Connection refused / unreachable: {e}",
            "hint": (
                "Ananta backend is not reachable at this URL. "
                "Start it: cd Ananta/backend && uvicorn server:app --host 0.0.0.0 --port 8001 --workers 1"
            ),
        }
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "base_url": base,
            "error": "Timeout talking to /api/auth/login",
            "hint": "Backend hung (often MongoDB). Check MONGO_URL and uvicorn logs.",
        }
    except Exception as e:
        return {"success": False, "base_url": base, "error": str(e)}


def ping_backend():
    """
    Diagnose connectivity without requiring a full strategy status pull.
    Returns structured result for the `ping` / `doctor` CLI command.
    """
    base = get_base_url()
    out = {
        "success": False,
        "base_url": base,
        "health": None,
        "api_root": None,
        "login": None,
        "steps": [],
    }

    try:
        r = requests.get(f"{base}/health", timeout=5)
        out["health"] = {"status_code": r.status_code, "body": (r.text or "")[:200]}
        out["steps"].append(f"GET /health → HTTP {r.status_code}")
    except Exception as e:
        out["steps"].append(f"GET /health → FAIL: {e}")
        out["error"] = str(e)
        out["hint"] = "Backend process is not up, or ANANTA_BASE_URL is wrong."
        return out

    try:
        r = requests.get(f"{base}/api/", timeout=5)
        out["api_root"] = {"status_code": r.status_code, "body": (r.text or "")[:200]}
        out["steps"].append(f"GET /api/ → HTTP {r.status_code}")
    except Exception as e:
        out["steps"].append(f"GET /api/ → FAIL: {e}")

    login_result = login()
    out["login"] = {k: v for k, v in login_result.items() if k != "token"}
    if login_result.get("success"):
        out["steps"].append("POST /api/auth/login → OK (token received)")
        out["success"] = True
    else:
        out["steps"].append("POST /api/auth/login → FAIL")
        out["error"] = format_login_error(login_result)
        out["hint"] = login_result.get("hint")
    return out
