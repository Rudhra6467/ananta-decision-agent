"""G5 — Reconstructable decision snapshot."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def build(* , state=None, scan=None, l2=None, issued="UNKNOWN", ts=None):
    state = state or {}
    scan = scan or {}
    l2 = l2 or {}
    decision = l2.get("decision") or {}
    ranked = l2.get("ranked") or []
    versions = l2.get("versions") or {}
    snap = {
        "id": "decision.snapshot.v1",
        "timestamp": ts or datetime.now(timezone.utc).isoformat(),
        "market_state": {
            "asset": state.get("asset"),
            "tf": state.get("tf"),
            "regime": state.get("regime"),
            "direction": state.get("direction"),
            "volatility": state.get("volatility"),
            "fingerprint": state.get("fingerprint"),
            "hunter_qualifying": bool(state.get("hunter_qualifying")),
            "squeeze_qualifying": bool(state.get("squeeze_qualifying")),
            "observer_match": state.get("observer_match"),
        },
        "scanner": {
            "candidate": (scan.get("candidate") or {}).get("id") or scan.get("candidate"),
            "why_interesting": (scan.get("candidate") or {}).get("why_interesting"),
        },
        "candidate": scan.get("candidate") or None,
        "knowledge_ids": [r.get("id") for r in ranked if r.get("id")],
        "historical_case_ids": [],
        "strategy_ids": [r.get("id") for r in ranked if r.get("type") in ("strategy", "variant")],
        "strategy_version": versions.get("knowledge") or "knowledge.catalog.v1",
        "ranking": [
            {
                "id": r.get("id"),
                "type": r.get("type"),
                "family_match": r.get("family_match"),
                "score": r.get("score"),
                "result": r.get("result"),
                "refuse_reasons": r.get("refuse_reasons") or [],
            }
            for r in ranked[:12]
        ],
        "ranking_version": versions.get("ranking") or "ranking.v1.context_conditioned",
        "selected_strategy": decision.get("best_id"),
        "alternatives_considered": [
            {"id": r.get("id"), "family_match": r.get("family_match"), "refuse_reasons": r.get("refuse_reasons") or []}
            for r in ranked if r.get("id") != decision.get("best_id")
        ][:8],
        "decision": decision.get("action") or "NO_TRADE",
        "reason": decision.get("reason"),
        "class_id": decision.get("class_id"),
        "authority": {"paper_take": False, "keep": False, "exec": False, "level": "L0"},
        "issued": issued,
        "paper_take": False,
        "keep": False,
        "exec": False,
        "counts_for_m2": False,
        "counts_for_paper": False,
        "decision_version": versions.get("decision") or "decision.l2.v1",
        "cited": decision.get("cited") or [],
    }
    snap["complete"] = all(k in snap and snap[k] is not None for k in ("timestamp", "market_state", "issued", "reason"))
    return snap
