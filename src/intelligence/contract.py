"""Agent ↔ Ananta API / data contract checker.

v0 HTTP surface from docs/AGENT_CONTRACT_V0.md plus additive decision_v0.
Does not invent routes. Missing = DATA_GAP, not a fabricated fact.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

CONTRACT_VERSION = 0
DECISION_SCHEMA = "decision_v0"
OBSERVATION_SCHEMA = "observation_v0"

# Routes the agent actually calls. Keep in lockstep with AGENT_CONTRACT_V0.md.
EXPECTED_ROUTES = [
    ("POST", "/api/auth/login", "Login JWT"),
    ("GET", "/api/portfolio", "portfolio_state"),
    ("POST", "/api/orders/manual", "paper / manual order"),
    ("GET", "/api/trades", "paper fills"),
    ("GET", "/api/strategy/registry", "strategy DNA (thesis)"),
    ("GET", "/api/strategy/knowledge", "Wave A SKO"),
    ("GET", "/api/strategy/{key}/profile", "enable + regimes"),
    ("PUT", "/api/strategy/{key}/profile", "enable + regimes"),
    ("POST", "/api/cycle/run", "evaluation cycle"),
    ("GET", "/api/lab/data/coverage", "1y candle proof"),
    ("POST", "/api/lab/runs", "lab backtest"),
    ("GET", "/api/lab/runs", "lab backtest list"),
    ("GET", "/api/lab/observation-replay", "S4 observation_v0 replay"),
    ("GET", "/health", "backend health (no /api prefix)"),
]

# Known holes — do not reason on these until Ananta exposes them.
NOT_A_ROUTE = [
    "/api/orders/paper",
    "/api/summary",
    "/api/opportunity/scan",
    "/api/fair-value",
]


def contract_spec() -> Dict[str, Any]:
    return {
        "agent_api_version": CONTRACT_VERSION,
        "observation_schema": OBSERVATION_SCHEMA,
        "decision_schema": DECISION_SCHEMA,
        "ownership": {
            "ananta": "System facts, market data, portfolio, orders, fills, exits, risk, telemetry",
            "market_truth": "Independent Kraken / Lab candles — not Ananta regime as proof",
            "agent": "interpretation, typed decisions, learning, orchestration",
        },
        "expected_routes": [
            {"method": m, "path": p, "need": n} for m, p, n in EXPECTED_ROUTES
        ],
        "not_a_route": list(NOT_A_ROUTE),
        "decision_vocabulary": ["TAKE", "SKIP", "WAIT", "HOLD", "EXIT", "REDUCE"],
        "control_vocabulary": ["ENABLE", "DISABLE", "KEEP", "WATCH", "CUT"],
        "laws": {
            "no_agent_mongo": True,
            "no_ui_scrape": True,
            "ananta_regime_is_hypothesis": True,
            "hard_safety_outside_llm": True,
        },
    }


def probe(timeout: float = 3.0) -> Dict[str, Any]:
    """Best-effort reachability. Fail soft — never invent a healthy backend."""
    spec = contract_spec()
    try:
        from src.tools.ananta_api import BASE_URL, get_headers
        import requests
    except Exception as e:
        spec["probe"] = {"ok": False, "error": str(e), "reachable": False}
        return spec

    results: List[dict] = []
    reachable = False
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=timeout)
        reachable = r.status_code < 500
        results.append({"path": "/health", "status": r.status_code, "ok": r.status_code == 200})
    except Exception as e:
        results.append({"path": "/health", "ok": False, "error": str(e)})

    if reachable:
        try:
            headers = get_headers()
            r = requests.get(f"{BASE_URL}/api/portfolio", headers=headers, timeout=timeout)
            results.append({"path": "/api/portfolio", "status": r.status_code, "ok": r.status_code == 200})
        except Exception as e:
            results.append({"path": "/api/portfolio", "ok": False, "error": str(e)})

    spec["probe"] = {
        "ok": reachable,
        "base_url_set": True,
        "results": results,
        "note": "Probe is reachability, not permission to TAKE.",
    }
    return spec
