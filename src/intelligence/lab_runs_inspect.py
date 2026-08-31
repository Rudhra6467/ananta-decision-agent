"""Read existing Lab runs. Draft EXP-010 payload. Never auto-POST."""
from __future__ import annotations

from typing import Any, Dict, List

from src.tools.ananta_api import get_lab_run, list_lab_runs

VERSION = "LAB-RUNS-v0"

# Closed budget only. Held-out is walk_forward, not a second search.
EXP010_DRAFT = {
    "kind": "walk_forward",
    "label": "EXP-010 donchian lookback budget — DO NOT POST until human says go",
    "symbols": ["BTC/USD"],
    "period": "1y",
    "timeframe": "1h",
    "strategies": ["donchian-breakout"],
    "metric": "win_rate_pct",
    "folds": 5,
    "min_trades": 8,
    "grid": {
        "note": "Ananta optimize keys are set:/prof: not donchian lookback. "
                "If Donchian length is not a set: key, DO NOT POST this grid.",
        "blocked_until": "confirm grid key for Donchian channel length in Ananta",
    },
    "auto_post": False,
}


def _slim(run: Any) -> Dict[str, Any]:
    if not isinstance(run, dict):
        return {"raw_type": type(run).__name__}
    return {
        "id": run.get("id"),
        "kind": run.get("kind"),
        "status": run.get("status"),
        "label": run.get("label"),
        "symbols": run.get("symbols"),
        "period": run.get("period"),
        "strategies": run.get("strategies"),
        "git_hash": run.get("git_hash"),
        "has_grid": bool(run.get("grid")),
        "has_result": run.get("result") is not None,
        "error": run.get("error"),
        "created_at": run.get("created_at"),
    }


def _as_list(data: Any) -> List[Any]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for k in ("runs", "items", "data"):
            v = data.get(k)
            if isinstance(v, list):
                return v
        if data.get("id"):
            return [data]
    return []


def inspect(*, peek_first: bool = True) -> Dict[str, Any]:
    listed = list_lab_runs(limit=8)
    rows = _as_list(listed.get("data"))
    slims = [_slim(r) for r in rows]
    detail = None
    if peek_first and slims and slims[0].get("id"):
        got = get_lab_run(slims[0]["id"])
        body = got.get("data") if got.get("success") else {}
        detail = {
            "ok": got.get("success"),
            "id": slims[0]["id"],
            "kind": (body or {}).get("kind") if isinstance(body, dict) else None,
            "status": (body or {}).get("status") if isinstance(body, dict) else None,
            "result_keys": list((body or {}).get("result") or {})[:24]
            if isinstance(body, dict) and isinstance(body.get("result"), dict) else None,
            "parameter_honored": None,
            "ingest": False,
        }
    return {
        "ok": bool(listed.get("success")),
        "version": VERSION,
        "n": len(slims),
        "runs": slims,
        "peek": detail,
        "draft_exp010": EXP010_DRAFT,
        "posted": False,
        "catalog": "PENDING",
        "keep": False,
    }


def print_runs() -> Dict[str, Any]:
    r = inspect()
    print(f"\nLAB RUNS  {VERSION}")
    print("=" * 64)
    print("Existing Ananta Lab jobs. Optimize URLs 404 — runs API is the door.")
    print(f"  list_ok={r['ok']} n={r['n']}")
    for row in r["runs"]:
        print(f"  {row.get('kind') or '?':<14} {row.get('status') or '?':<10} "
              f"{str(row.get('label') or '')[:40]}")
    print("-" * 64)
    print("  peek:", r.get("peek"))
    print("  EXP-010 draft auto_post=False  Donchian length key UNCONFIRMED")
    print("  catalog=PENDING  keep=False")
    print("=" * 64)
    print()
    return r
