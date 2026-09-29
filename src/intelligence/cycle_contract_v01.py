"""Shared contract v0.1 — normalize and validate one cycle payload.

Drop into ananta-decision-agent as src/intelligence/cycle_contract_v01.py
(or import from wherever you wire lab/cycle).

Law: Agent → API → Ananta → Mongo. No silent strategies.
WAIT/SKIP ≠ KEEP. Missing fields → UNKNOWN, not a fake SKIP.
bb_bandwidth is not an enabled strategy on this contract.
Outcome +15m/+1h/+4h is v0.2.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

CONTRACT = "ananta.shared.v0.1"
VERSION = "v0.1"

RECOMMENDATIONS = ("TAKE", "WAIT", "SKIP", "EXIT", "REDUCE", "HOLD", "UNKNOWN")
REGIMES = ("DOWN", "NORMAL", "UP", "NEUTRAL", "UNKNOWN")
PROFILES = ("SAFE", "MODERATE", "AGGRESSIVE")
SETUP = ("true", "false", "unknown", True, False, "TRUE", "FALSE", "UNKNOWN")

NOT_ENABLED = frozenset({"bb_bandwidth", "bb-bandwidth", "bollinger_bandwidth"})

REQUIRED_CYCLE = ("cycle_id", "as_of_time", "event_time", "universe", "profile", "strategies")
REQUIRED_ROW = ("strategy_id", "ran", "setup_detected", "recommendation", "skip_reason", "regime")


def _norm_bool(v: Any) -> Optional[bool]:
    if v is True or v == "true" or v == "TRUE":
        return True
    if v is False or v == "false" or v == "FALSE":
        return False
    return None


def _norm_setup(v: Any) -> str:
    if v is True or v == "true" or v == "TRUE":
        return "true"
    if v is False or v == "false" or v == "FALSE":
        return "false"
    return "unknown"


def _norm_upper(v: Any, allowed: Tuple[str, ...], default: str) -> str:
    if v is None:
        return default
    s = str(v).strip().upper()
    return s if s in allowed else default


def normalize_row(row: Dict[str, Any], enabled_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    sid = str(row.get("strategy_id") or "").strip()
    ran = _norm_bool(row.get("ran"))
    if ran is None:
        ran = False
    rec = _norm_upper(row.get("recommendation"), (
        "TAKE", "WAIT", "SKIP", "EXIT", "REDUCE", "HOLD", "UNKNOWN"
    ), "UNKNOWN")
    setup = _norm_setup(row.get("setup_detected"))
    regime = _norm_upper(row.get("regime"), ("DOWN", "NORMAL", "UP", "NEUTRAL", "UNKNOWN"), "UNKNOWN")
    skip = row.get("skip_reason")
    if skip is not None:
        skip = str(skip).strip() or None

    if sid.lower() in NOT_ENABLED or sid.replace("-", "_").lower() in NOT_ENABLED:
        ran = False
        rec = "UNKNOWN"
        setup = "unknown"
        skip = skip or "not_enabled_on_v0.1"
        regime = "UNKNOWN"

    if rec in ("WAIT", "SKIP") and not skip:
        skip = "unspecified"
    if rec in ("TAKE", "EXIT", "REDUCE"):
        skip = None
    if rec == "HOLD":
        # HOLD is a recommendation, not KEEP
        skip = skip
    if not ran:
        rec = "UNKNOWN"
        setup = "unknown"
        skip = skip or "did_not_run"

    return {
        "strategy_id": sid or "unknown",
        "ran": ran,
        "setup_detected": setup,
        "recommendation": rec,
        "skip_reason": skip,
        "regime": regime,
    }


def normalize_cycle(payload: Dict[str, Any], enabled_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    enabled = list(enabled_ids or [])
    raw_rows = payload.get("strategies") or []
    if not isinstance(raw_rows, list):
        raw_rows = []
    by_id: Dict[str, Dict[str, Any]] = {}
    for row in raw_rows:
        if not isinstance(row, dict):
            continue
        norm = normalize_row(row)
        if norm["strategy_id"] != "unknown":
            by_id[norm["strategy_id"]] = norm

    strategies: List[Dict[str, Any]] = []
    seen = set()
    for sid in enabled:
        seen.add(sid)
        if sid in by_id:
            strategies.append(by_id[sid])
        else:
            strategies.append(normalize_row({
                "strategy_id": sid,
                "ran": False,
                "setup_detected": "unknown",
                "recommendation": "UNKNOWN",
                "skip_reason": "silent_strategy",
                "regime": "UNKNOWN",
            }))
    for sid, row in by_id.items():
        if sid not in seen:
            strategies.append(row)

    rec = str(payload.get("profile") or "SAFE").strip().upper()
    if rec not in ("SAFE", "MODERATE", "AGGRESSIVE"):
        rec = "SAFE"

    return {
        "contract": CONTRACT,
        "cycle_id": str(payload.get("cycle_id") or "").strip() or "unknown",
        "as_of_time": str(payload.get("as_of_time") or "").strip() or None,
        "event_time": str(payload.get("event_time") or "").strip() or None,
        "universe": str(payload.get("universe") or "CRYPTO_LAB_10").strip(),
        "profile": rec,
        "strategies": strategies,
    }


def validate_cycle(payload: Dict[str, Any], enabled_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """Return {ok, errors, warnings, cycle}."""
    errors: List[str] = []
    warnings: List[str] = []
    if not isinstance(payload, dict):
        return {"ok": False, "errors": ["payload_not_object"], "warnings": [], "cycle": None}

    missing = [k for k in REQUIRED_CYCLE if k not in payload]
    if missing:
        errors.append("MISSING_CYCLE:" + ",".join(missing))

    raw_rows = payload.get("strategies")
    if raw_rows is None:
        errors.append("MISSING_CYCLE:strategies")
        raw_rows = []
    elif not isinstance(raw_rows, list):
        errors.append("strategies_not_array")
        raw_rows = []

    enabled = list(enabled_ids or [])
    present = set()
    for row in raw_rows:
        if not isinstance(row, dict):
            errors.append("strategy_row_not_object")
            continue
        miss = [k for k in REQUIRED_ROW if k not in row]
        if miss:
            errors.append("MISSING_ROW:" + str(row.get("strategy_id")) + ":" + ",".join(miss))
        sid = str(row.get("strategy_id") or "").strip()
        if sid:
            present.add(sid)
        rec = str(row.get("recommendation") or "").upper()
        if rec in ("WAIT", "SKIP") and not row.get("skip_reason"):
            warnings.append("WAIT_SKIP_WITHOUT_REASON:" + sid)
        if rec == "KEEP":
            errors.append("KEEP_IS_NOT_A_RECOMMENDATION:" + sid)
        if sid.lower().replace("-", "_") in NOT_ENABLED:
            errors.append("NOT_ENABLED_ON_V01:" + sid)

    for sid in enabled:
        if sid not in present:
            errors.append("SILENT_STRATEGY:" + sid)

    cycle = normalize_cycle(payload, enabled_ids=enabled_ids)
    return {"ok": not errors, "errors": errors, "warnings": warnings, "cycle": cycle}


def ensure_coverage(cycle: Dict[str, Any], enabled_ids: List[str]) -> Dict[str, Any]:
    """Fill silent enabled strategies as UNKNOWN. Does not invent TAKE."""
    return normalize_cycle(cycle, enabled_ids=enabled_ids)


if __name__ == "__main__":
    import json as _json
    demo = {
        "cycle_id": "demo",
        "as_of_time": "2026-09-06T13:00:00Z",
        "event_time": "2026-09-06T13:00:00Z",
        "universe": "CRYPTO_LAB_10",
        "profile": "SAFE",
        "strategies": [
            {"strategy_id": "hunter", "ran": True, "setup_detected": False,
             "recommendation": "SKIP", "skip_reason": "no_setup", "regime": "UNKNOWN"},
        ],
    }
    print(_json.dumps(validate_cycle(demo, enabled_ids=["hunter", "squeeze"]), indent=2))
