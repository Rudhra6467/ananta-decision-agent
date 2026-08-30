"""Lab candle coverage with a long timeout. Health is cheap; coverage is not."""
from __future__ import annotations

import requests

from src.tools.ananta_api import BASE_URL, _auth_headers, _owner_token


def get_lab_coverage_long(timeout: int = 120):
    got = _owner_token()
    if not got.get("success"):
        return {"success": False, "error": "Login failed", "details": got}
    try:
        r = requests.get(
            f"{BASE_URL}/api/lab/data/coverage",
            headers=_auth_headers(got["token"]),
            timeout=timeout,
        )
        if r.status_code != 200:
            return {"success": False, "status_code": r.status_code, "error": r.text[:500]}
        return {"success": True, "data": r.json()}
    except Exception as e:
        return {"success": False, "error": str(e)}
