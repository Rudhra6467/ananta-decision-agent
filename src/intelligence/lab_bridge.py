"""Bridge probe: Ananta lab optimize/backtest ↔ Agent CFG catalog.

Does not POST a grid. Does not invent win rates. Wave A untouched.
"""
from __future__ import annotations

from typing import Any, Dict, List

import requests

from src.tools.ananta_api import (
    BASE_URL,
    _auth_headers,
    _owner_token,
    list_lab_runs,
)

VERSION = "LAB-BRIDGE-v0"
EXP_ID = "EXP-010"

CANDIDATE_PATHS = (
    "/api/lab/optimize",
    "/api/lab/optimize/grid",
    "/api/lab/wfa",
    "/api/lab/walk-forward",
    "/api/lab/research",
    "/api/lab/backtest",
    "/api/research",
)


def _probe_path(token: str, path: str) -> Dict[str, Any]:
    url = BASE_URL + path
    row = {"path": path, "get": None, "post_not_sent": True}
    try:
        r = requests.get(url, headers=_auth_headers(token), timeout=20)
        row["get"] = r.status_code
        row["get_hint"] = (r.text or "")[:180]
    except Exception as e:
        row["get"] = "ERR"
        row["get_hint"] = str(e)[:180]
    return row


def probe() -> Dict[str, Any]:
    got = _owner_token()
    if not got.get("success"):
        return {
            "ok": False,
            "version": VERSION,
            "reason": "LOGIN_FAILED",
            "error": got.get("error"),
            "keep": False,
            "scores": None,
        }
    token = got["token"]
    runs = list_lab_runs(limit=5, token=token)
    paths = [_probe_path(token, p) for p in CANDIDATE_PATHS]
    live_ok = [p for p in paths if isinstance(p.get("get"), int) and p["get"] in (200, 201)]
    exists = [p for p in paths if isinstance(p.get("get"), int) and p["get"] not in (404,)]
    return {
        "ok": True,
        "version": VERSION,
        "exp_id": EXP_ID,
        "runs_list": {
            "success": runs.get("success"),
            "status": runs.get("status_code"),
            "error": (str(runs.get("error") or ""))[:200],
            "n": _n_runs(runs.get("data")),
        },
        "paths": paths,
        "get_200": [p["path"] for p in live_ok],
        "not_404": [p["path"] for p in exists],
        "win_rate_after_cost": None,
        "catalog": "PENDING",
        "promote": False,
        "keep": False,
        "law": "Do not POST a grid until a path is confirmed. Observation-replay stays stock.",
    }


def _n_runs(data: Any) -> int:
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        for k in ("runs", "items", "data"):
            v = data.get(k)
            if isinstance(v, list):
                return len(v)
    return 0


def print_bridge() -> Dict[str, Any]:
    r = probe()
    print(f"\nLAB BRIDGE  {r.get('version')}  {r.get('exp_id', EXP_ID)}")
    print("=" * 64)
    print("Discover Ananta optimize API. No scores. No POST grid.")
    print("-" * 64)
    print("  list /api/lab/runs:", r.get("runs_list"))
    print("  GET 200:", r.get("get_200"))
    print("  not 404:", r.get("not_404"))
    for p in r.get("paths") or []:
        print(f"    {p.get('path'):<28} GET={p.get('get')}")
    print("-" * 64)
    print("  catalog=PENDING  win_rate=None  promote=False")
    print("=" * 64)
    print()
    return r
