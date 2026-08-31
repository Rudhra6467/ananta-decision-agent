"""Map Lab health_sweep cards onto CFG contract. They do not fit. Not KEEP."""
from __future__ import annotations

from typing import Any, Dict, List

from src.intelligence.cfg_contract import MUST_HAVE_VALUE, REQUIRED
from src.tools.ananta_api import get_lab_run, list_lab_runs

VERSION = "SWEEP-MAP-v0"

LAB_HEALTH_FIELDS = (
    "best_exit",
    "best_regime",
    "best_timeframe",
    "capture_rate_pct",
    "headline",
    "name",
    "per_symbol",
    "profit_left_usd",
    "recommendation",
    "regime_breakdown",
    "strategy",
    "timeframe_comparison",
    "total_captured_usd",
    "total_mfe_usd",
    "weak_regime",
)

# Honest aliases only. Not a translation that invents missing science.
ALIAS = {
    "total_mfe_usd": "mfe",  # dollars, not % path MFE
    "strategy": "strategy_family",
}

LAW = (
    "Health sweep answers: which exit/regime/TF captured MFE on a 3m daily cut. "
    "CFG contract answers: after-cost win vs sit-out on a named config_id. "
    "Lab recommendation ≠ TAKE. best_exit ≠ config_id. capture_rate ≠ win_rate_after_cost."
)


def _runs(data: Any) -> List[dict]:
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for k in ("runs", "items", "data"):
            v = data.get(k)
            if isinstance(v, list):
                return [x for x in v if isinstance(x, dict)]
    return []


def _shape(val: Any) -> str:
    if val is None:
        return "None"
    if isinstance(val, dict):
        return "dict[" + ",".join(sorted(val.keys())[:12]) + "]"
    if isinstance(val, list):
        n = len(val)
        inner = _shape(val[0]) if n and not isinstance(val[0], (int, float, str)) else type(val[0]).__name__ if n else "empty"
        return f"list(n={n},{inner})"
    if isinstance(val, str):
        return f"str(len={len(val)})"
    return type(val).__name__


def print_map() -> Dict[str, Any]:
    listed = list_lab_runs(limit=8)
    runs = _runs(listed.get("data"))
    sweep = next((r for r in runs if r.get("kind") == "health_sweep" and r.get("id")), None)
    run_id = sweep.get("id") if sweep else None
    hunter: Dict[str, Any] = {}
    if run_id:
        got = get_lab_run(run_id)
        body = got.get("data") if got.get("success") else {}
        result = (body or {}).get("result") if isinstance(body, dict) else {}
        cards = [s for s in (result or {}).get("strategies") or [] if isinstance(s, dict)]
        for s in cards:
            if str(s.get("strategy") or "").lower() == "hunter":
                hunter = s
                break
    overlap_required = [k for k in LAB_HEALTH_FIELDS if k in REQUIRED]
    alias_hits = {src: dst for src, dst in ALIAS.items() if dst in REQUIRED}
    missing_must = list(MUST_HAVE_VALUE)
    print(f"\nSWEEP MAP  {VERSION}")
    print("=" * 64)
    print(LAW)
    print("-" * 64)
    print(f"  lab fields={len(LAB_HEALTH_FIELDS)}  cfg required={len(REQUIRED)}  exact overlap={overlap_required}")
    print(f"  alias only={alias_hits}")
    print(f"  CFG must-have still empty={missing_must}")
    print("-" * 64)
    print("  hunter nested shapes (types/keys, not scores)")
    for k in LAB_HEALTH_FIELDS:
        print(f"    {k:<22} {_shape(hunter.get(k))}")
    print("-" * 64)
    print("  ingest=False  parameter_honored=False  KEEP=False")
    print("  Next Lab artifact for EXP-010 is grid_search/walk_forward, not this card.")
    print("=" * 64)
    print()
    return {
        "ok": True,
        "version": VERSION,
        "run_id": run_id,
        "overlap": overlap_required,
        "alias": alias_hits,
        "ingest": False,
        "keep": False,
    }
