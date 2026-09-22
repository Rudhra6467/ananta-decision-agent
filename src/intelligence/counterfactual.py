"""G7 — Counterfactual on NO_TRADE / WATCH / REFUSE. Does not rewrite the thesis."""
from __future__ import annotations

from typing import Any


def open_case(snapshot: dict[str, Any], *, horizon_hours: float = 4.0) -> dict[str, Any]:
    issued = snapshot.get("issued") or snapshot.get("decision")
    return {
        "id": "counterfactual.v1",
        "status": "OPEN",
        "issued_at": snapshot.get("timestamp"),
        "issued": issued,
        "asset": ((snapshot.get("market_state") or {}).get("asset")),
        "regime": ((snapshot.get("market_state") or {}).get("regime")),
        "reason": snapshot.get("reason"),
        "horizon_hours": horizon_hours,
        "fwd_return_pct": None,
        "mfe_pct": None,
        "mae_pct": None,
        "label": None,
        "labels_allowed": ["CORRECT_REFUSE", "MISSED_OPPORTUNITY", "AMBIGUOUS", "SCAN_COVERAGE", "STATE_RECOGNITION", "KNOWLEDGE_RETRIEVAL", "STRATEGY_MATCH", "STRATEGY_RANKING", "AUTHORITY"],
        "rewrites_thesis": False,
        "counts_for_m2": False,
        "paper_take": False,
        "snapshot_id": snapshot.get("id"),
    }


def close_case(case: dict[str, Any], *, fwd_return_pct: float, mfe_pct: float, mae_pct: float) -> dict[str, Any]:
    out = dict(case)
    out["status"] = "CLOSED"
    out["fwd_return_pct"] = fwd_return_pct
    out["mfe_pct"] = mfe_pct
    out["mae_pct"] = mae_pct
    issued = str(out.get("issued") or "")
    if issued in ("NO_TRADE", "SHADOW_PAPER", "WAIT") and fwd_return_pct >= 3.0 and mfe_pct >= 3.0:
        out["label"] = "MISSED_OPPORTUNITY"
    elif issued in ("NO_TRADE", "SHADOW_PAPER", "WAIT") and fwd_return_pct <= -2.0:
        out["label"] = "CORRECT_REFUSE"
    else:
        out["label"] = "AMBIGUOUS"
    out["counts_for_m2"] = False
    return out
