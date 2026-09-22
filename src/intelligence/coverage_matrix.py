"""G2 — Market-state coverage matrix. Inspect existing catalog. Do not invent strategies."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CATALOG_PATHS = [
    Path(__file__).with_name("knowledge_catalog_v1.json"),
    Path(__file__).resolve().parents[1] / "knowledge_catalog_v1.json",
]

STATES = (
    "TREND_UP", "TREND_DOWN", "RANGE", "BREAKOUT", "BREAKDOWN", "LIQUIDITY_EVENT",
    "REVERSAL", "COMPRESSION", "EXPANSION", "MEAN_REVERSION", "MOMENTUM",
    "VOLATILITY_EVENT", "LAG",
)

DETECTORS = {
    "TREND_UP": {"detector": "continuation", "live": "DISABLED", "status": "BENCHED"},
    "TREND_DOWN": {"detector": None, "live": "NONE", "status": "NONE"},
    "RANGE": {"detector": None, "live": "NONE", "status": "NONE"},
    "BREAKOUT": {"detector": None, "live": "NONE", "status": "NONE"},
    "BREAKDOWN": {"detector": None, "live": "NONE", "status": "NONE"},
    "LIQUIDITY_EVENT": {"detector": None, "live": "NONE", "status": "NONE"},
    "REVERSAL": {"detector": "hunter", "live": "enabled", "status": "ACTIVE_SPARSE"},
    "COMPRESSION": {"detector": "squeeze", "live": "enabled", "status": "ACTIVE_SPARSE"},
    "EXPANSION": {"detector": "h1", "live": "observe-only", "status": "ALARM_ONLY"},
    "MEAN_REVERSION": {"detector": "bollinger_mr", "live": "envelope", "status": "ENVELOPE_NOT_SCHOOL"},
    "MOMENTUM": {"detector": "seq2", "live": "n/a", "status": "WHEN_NOT"},
    "VOLATILITY_EVENT": {"detector": "h1", "live": "observe-only", "status": "ALARM_ONLY"},
    "LAG": {"detector": "set16", "live": "observe-only", "status": "WATCH_ONLY"},
}


def load_catalog() -> dict[str, Any]:
    for p in CATALOG_PATHS:
        if p.exists():
            return json.loads(p.read_text())
    return {"objects": []}


def inspect_state(state: str, objects: list[dict[str, Any]]) -> dict[str, Any]:
    cards = [o for o in objects if state in (o.get("regimes") or [])]
    det = DETECTORS.get(state) or {"detector": None, "live": "NONE", "status": "NONE"}
    paper_eligible = False
    needs_research = det["status"] in ("NONE",) or not cards
    return {
        "state": state,
        "detector": det["detector"],
        "detector_status": det["status"],
        "detector_live": det["live"],
        "relevant_cards": [o["id"] for o in cards],
        "has_strategy_card": any(o.get("type") == "strategy" for o in cards),
        "has_observe_card": any(o.get("type") == "observe" for o in cards),
        "historical_cases": sum(int(o.get("n") or 0) for o in cards),
        "oos_labels": sorted({str(o.get("oos")) for o in cards}),
        "economic_labels": sorted({str(o.get("economic")) for o in cards}),
        "existing_variants": [o["id"] for o in cards if o.get("type") == "variant"],
        "research_only": bool(cards) and not paper_eligible,
        "paper_eligible": paper_eligible,
        "needs_new_strategy_program": needs_research,
        "do_not_invent_strategy": True,
        "result_if_present": (
            "SCAN_COVERAGE" if det["status"] in ("NONE", "BENCHED") else
            "WATCH" if det["status"] == "WATCH_ONLY" else
            "NO_TRADE" if det["status"] in ("ALARM_ONLY", "WHEN_NOT", "ENVELOPE_NOT_SCHOOL") else
            "SCAN_LOGIC"
        ),
    }


def matrix(facing: str | None = None) -> dict[str, Any]:
    objects = (load_catalog().get("objects") or [])
    rows = [inspect_state(s, objects) for s in STATES]
    uncovered = [r["state"] for r in rows if r["detector_status"] in ("NONE", "BENCHED")]
    return {
        "id": "market_state_coverage_matrix.v2",
        "law": "Coverage is state x detector, not fire-count. Do not create strategies to force trades.",
        "facing": facing,
        "rows": rows,
        "uncovered_facing_states": uncovered,
        "paper_eligible_states": [r["state"] for r in rows if r["paper_eligible"]],
        "facing_covered": facing not in uncovered if facing else None,
        "paper_take": False,
    }
