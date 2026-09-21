"""G1 — Hands funnel telemetry.

Missing counts stay 0. Never invent bars or assets evaluated.
NO_TRADE without looked=True is NEVER_LOOKED, not evidence.
"""
from __future__ import annotations

from typing import Any

REQUIRED = (
    "cycle_id",
    "bar_tf",
    "last_bar_open",
    "assets_named",
    "assets_evaluated",
    "assets_scanned_ok",
    "timeframes",
    "bars_evaluated",
    "observations",
    "partial_matches",
    "candidate_setups",
    "qualified_candidates",
    "strategy_family_matches",
    "knowledge_retrievals",
    "strategy_variants_considered",
    "ranked_candidates",
    "decisions",
    "paper_candidates",
    "issued",
    "issued_TAKE",
    "issued_WAIT",
    "issued_NO_TRADE",
    "issued_WATCH",
    "issued_SHADOW_PAPER",
    "rejections",
    "rejection_reasons",
    "coverage_gaps",
    "looked",
    "look_class",
)

UNIVERSE = ["BTC", "ETH", "SOL", "ADA", "DOGE", "AVAX", "BCH", "LINK", "LTC", "XRP"]


def look_class(row: dict[str, Any]) -> str:
    looked = bool(row.get("looked"))
    issued = str(row.get("issued") or "")
    evaluated = int(row.get("assets_evaluated") or 0)
    bars = int(row.get("bars_evaluated") or 0)
    if not looked or evaluated == 0 or bars == 0:
        return "NEVER_LOOKED"
    if issued in ("NO_TRADE", "SHADOW_PAPER") and int(row.get("qualified_candidates") or 0) == 0:
        return "LOOKED_NOTHING_VALID"
    if issued == "WATCH":
        return "LOOKED_WATCH"
    if issued == "WAIT":
        return "LOOKED_WAIT"
    return "LOOKED"


def emit(cycle: dict[str, Any] | None = None) -> dict[str, Any]:
    c = cycle or {}
    issued = str(c.get("issued") or "UNKNOWN")
    named = list(c.get("assets_named") or [])
    evaluated = int(c.get("assets_evaluated") or 0)
    row = {
        "id": "hands.funnel.cycle.v2",
        "cycle_id": c.get("cycle_id") or "unknown",
        "bar_tf": c.get("bar_tf") or c.get("tf"),
        "last_bar_open": c.get("last_bar_open") or c.get("ts"),
        "assets_named": named,
        "assets_evaluated": evaluated,
        "assets_scanned_ok": int(c.get("assets_scanned_ok") or evaluated),
        "timeframes": list(c.get("timeframes") or ([c.get("tf")] if c.get("tf") else [])),
        "bars_evaluated": int(c.get("bars_evaluated") or 0),
        "observations": int(c.get("observations") or 0),
        "partial_matches": int(c.get("partial_matches") or c.get("partial_candidates") or 0),
        "candidate_setups": int(c.get("candidate_setups") or 0),
        "qualified_candidates": int(c.get("qualified_candidates") or c.get("qualified_setups") or 0),
        "strategy_family_matches": int(c.get("strategy_family_matches") or 0),
        "knowledge_retrievals": int(c.get("knowledge_retrievals") or 0),
        "strategy_variants_considered": int(c.get("strategy_variants_considered") or 0),
        "ranked_candidates": int(c.get("ranked_candidates") or 0),
        "decisions": int(c.get("decisions") or (1 if issued != "UNKNOWN" else 0)),
        "paper_candidates": int(c.get("paper_candidates") or (1 if issued == "SHADOW_PAPER" else 0)),
        "issued": issued,
        "issued_TAKE": 0,
        "issued_WAIT": 1 if issued == "WAIT" else 0,
        "issued_NO_TRADE": 1 if issued == "NO_TRADE" else 0,
        "issued_WATCH": 1 if issued == "WATCH" else 0,
        "issued_SHADOW_PAPER": 1 if issued == "SHADOW_PAPER" else 0,
        "rejections": list(c.get("rejections") or []),
        "rejection_reasons": list(c.get("rejection_reasons") or []),
        "coverage_gaps": list(c.get("coverage_gaps") or []),
        "looked": bool(c.get("looked")) and evaluated > 0 and int(c.get("bars_evaluated") or 0) > 0,
        "universe_named": UNIVERSE,
        "universe_gap": [a for a in UNIVERSE if a not in {x.split("/")[0] for x in named}],
        "paper_take": False,
        "counts_for_m2": False,
    }
    if evaluated < len(UNIVERSE) and "universe_not_fully_evaluated" not in row["coverage_gaps"]:
        row["coverage_gaps"].append("universe_not_fully_evaluated")
    row["look_class"] = look_class(row)
    return row


def from_writer(obs: dict, st: dict, scan: dict, l2: dict, issued: str) -> dict[str, Any]:
    cand = (scan or {}).get("candidate") or {}
    ranked = (l2 or {}).get("ranked") or []
    family_hits = [r for r in ranked if r.get("family_match") == "HIGH"]
    variants = [r for r in ranked if r.get("type") == "variant"]
    asset = ((l2 or {}).get("state") or {}).get("asset") or (st or {}).get("asset") or (obs or {}).get("asset")
    named = [str(asset).split("/")[0]] if asset else []
    looked = bool(obs) and bool(ranked)
    bars = 1 if obs else 0
    return emit(
        {
            "cycle_id": ((obs or {}).get("system_truth") or {}).get("cycle_id")
            or (obs or {}).get("id")
            or (st or {}).get("obs_id"),
            "bar_tf": ((l2 or {}).get("state") or {}).get("tf"),
            "last_bar_open": (obs or {}).get("ts") or (obs or {}).get("timestamp") or (st or {}).get("ts"),
            "assets_named": named,
            "assets_evaluated": 1 if obs else 0,
            "assets_scanned_ok": 1 if obs else 0,
            "timeframes": [((l2 or {}).get("state") or {}).get("tf") or "unknown"],
            "bars_evaluated": bars,
            "observations": 1 if obs else 0,
            "partial_matches": 1 if cand else 0,
            "candidate_setups": 1 if cand else 0,
            "qualified_candidates": 1
            if ((l2 or {}).get("state") or {}).get("hunter_qualifying")
            or ((l2 or {}).get("state") or {}).get("squeeze_qualifying")
            else 0,
            "strategy_family_matches": len(family_hits),
            "knowledge_retrievals": len(ranked),
            "strategy_variants_considered": len(variants),
            "ranked_candidates": len(ranked),
            "decisions": 1,
            "paper_candidates": 1 if issued == "SHADOW_PAPER" else 0,
            "issued": issued,
            "rejections": [r.get("id") for r in ranked if r.get("result") == "REFUSE"][:8],
            "rejection_reasons": sorted(
                {rr for r in ranked for rr in (r.get("refuse_reasons") or [])}
            ),
            "looked": looked,
            "coverage_gaps": ["writer_side_only_not_hands_universe"] if looked else ["no_observation"],
        }
    )
