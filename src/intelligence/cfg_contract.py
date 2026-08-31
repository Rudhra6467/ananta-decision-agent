"""What may enter Agent knowledge from Ananta Lab. Not KEEP."""
from __future__ import annotations

from typing import Any, Dict, Optional

VERSION = "CFG-CONTRACT-v0"

REQUIRED = (
    "exp_id",
    "strategy_family",
    "strategy_version",
    "config_id",
    "entry_parameters",
    "exit_parameters",
    "asset",
    "timeframe",
    "market_state",
    "research_period",
    "is_period",
    "oos_period",
    "n",
    "win_rate",
    "win_rate_after_cost",
    "expectancy_after_cost",
    "profit_factor",
    "avg_win",
    "avg_loss",
    "mfe",
    "mae",
    "max_drawdown",
    "vs_sitout",
    "robustness",
    "wfa_efficiency",
    "source",
    "code_version",
    "created_at",
    "parameter_honored",
    "lab_run_id",
)

LAW = (
    "If parameter_honored is not True, the row MUST NOT enter the catalog as evidence. "
    "No single BEST_STRATEGY. Conditional boards only. Lab winner ≠ KEEP."
)


def may_ingest(row: Dict[str, Any]) -> Dict[str, Any]:
    missing = [k for k in REQUIRED if k not in row]
    honored = row.get("parameter_honored") is True
    ok = (not missing) and honored
    reasons = []
    if missing:
        reasons.append("MISSING_FIELDS:" + ",".join(missing))
    if not honored:
        reasons.append("PARAMETER_NOT_HONORED")
    return {
        "ok": ok,
        "ingest": ok,
        "missing": missing,
        "parameter_honored": honored,
        "reasons": reasons,
        "keep": False,
    }


def empty_row(**kwargs: Any) -> Dict[str, Any]:
    row = {k: None for k in REQUIRED}
    row.update(kwargs)
    row.setdefault("parameter_honored", False)
    row["keep"] = False
    row["promote"] = False
    return row


def print_contract(sample: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    sample = sample or empty_row(exp_id="EXP-010", config_id="donchian-lb20-v1")
    gate = may_ingest(sample)
    print(f"\nCFG CONTRACT  {VERSION}")
    print("=" * 64)
    print(LAW)
    print("-" * 64)
    print("  required fields:", len(REQUIRED))
    print("  sample ingest:", gate)
    print("  boards: HIT_RATE | EXPECTANCY | LOW_MAE  (no polarity)")
    print("  optimize HTTP 404 is expected — use POST /api/lab/runs kind=grid_search|walk_forward")
    print("=" * 64)
    print()
    return {"ok": True, "version": VERSION, "gate": gate, "keep": False}
