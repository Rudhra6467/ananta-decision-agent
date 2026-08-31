"""Peek health_sweep card keys. Schema only. Numbers are not ingested."""
from __future__ import annotations

from typing import Any, Dict, List

from src.intelligence.sweep_roster import DAILY_SWEEP, VERSION as ROSTER
from src.tools.ananta_api import get_lab_run, list_lab_runs

VERSION = "SWEEP-PEEK-v0"


def _runs(data: Any) -> List[dict]:
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for k in ("runs", "items", "data"):
            v = data.get(k)
            if isinstance(v, list):
                return [x for x in v if isinstance(x, dict)]
    return []


def _cards(result: dict) -> List[dict]:
    raw = result.get("strategies") or []
    return [s for s in raw if isinstance(s, dict)]


def _key(s: dict) -> str:
    return str(s.get("strategy") or s.get("key") or s.get("name") or "?").lower()


def print_peek() -> Dict[str, Any]:
    listed = list_lab_runs(limit=8)
    runs = _runs(listed.get("data"))
    sweep = next((r for r in runs if r.get("kind") == "health_sweep" and r.get("id")), None)
    run_id = sweep.get("id") if sweep else None
    cards: List[dict] = []
    result_meta: Dict[str, Any] = {}
    if run_id:
        got = get_lab_run(run_id)
        body = got.get("data") if got.get("success") else {}
        result = (body or {}).get("result") if isinstance(body, dict) else {}
        result = result or {}
        cards = _cards(result)
        result_meta = {
            "period": result.get("period"),
            "symbols": result.get("symbols"),
            "strategy_count": result.get("strategy_count"),
            "mode": result.get("mode"),
        }
    by_key = {_key(c): c for c in cards}
    print(f"\nSWEEP PEEK  {VERSION}")
    print("=" * 64)
    print("Schema inventory. Values printed as types/keys only. Not KEEP.")
    print(f"  run={run_id}  meta={result_meta}  roster={ROSTER}")
    print("-" * 64)
    field_map: Dict[str, List[str]] = {}
    for name in DAILY_SWEEP:
        card = by_key.get(name) or {}
        keys = sorted(card.keys()) if card else []
        field_map[name] = keys
        present = bool(card)
        print(f"  {name:<16} present={present} fields={keys[:16]}{'...' if len(keys) > 16 else ''}")
    hunter = by_key.get("hunter") or {}
    sample_keys = sorted(hunter.keys())
    print("-" * 64)
    print(f"  hunter field count={len(sample_keys)}")
    print("  ingest=False  (sweep ≤ Lab health, not CFG contract)")
    print("=" * 64)
    print()
    return {
        "ok": True,
        "version": VERSION,
        "run_id": run_id,
        "meta": result_meta,
        "field_map": field_map,
        "hunter_fields": sample_keys,
        "ingest": False,
        "keep": False,
    }
