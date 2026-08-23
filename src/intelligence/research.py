"""Research / strategy-analysis workflow.

Thesis ≠ implementation ≠ router ≠ evidence.
Does not KEEP. Does not enable. Does not rewrite.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.intelligence.adjudicate import WAVE_A_REGIMES
from src.intelligence.attribution import attribute_print_ready
from src.intelligence.experiments import list_experiments
from src.intelligence.schema import WAVE_A


def research(strategy_key: Optional[str] = None) -> Dict[str, Any]:
    key = (strategy_key or "").lower().strip() or None
    keys = [key] if key in WAVE_A else list(WAVE_A)
    live = _safe_attr("live")
    hist = _safe_attr("replay")
    knowledge = _safe_knowledge()
    out_strats: List[dict] = []
    for k in keys:
        live_b = (live.get("by_strategy") or {}).get(k) or {}
        hist_b = (hist.get("by_strategy") or {}).get(k) or {}
        kn = _pick_knowledge(knowledge, k)
        out_strats.append(
            {
                "strategy_id": k,
                "lifecycle": "WATCH",
                "thesis_allowed_regimes": sorted(WAVE_A_REGIMES.get(k, [])),
                "implementation_authoritative": True,
                "knowledge": kn,
                "live_evidence": {
                    "n_rows": live_b.get("n_rows", 0),
                    "n_setup": live_b.get("n_setup", 0),
                    "n_take": live_b.get("n_take", 0),
                    "n_skip": live_b.get("n_skip", 0),
                    "n_regime_filtered": live_b.get("n_regime_filtered", 0),
                    "source": live.get("source"),
                    "data_gap": live.get("data_gap"),
                },
                "historical_evidence": {
                    "n_rows": hist_b.get("n_rows", 0),
                    "n_setup": hist_b.get("n_setup", 0),
                    "n_take": hist_b.get("n_take", 0),
                    "n_skip": hist_b.get("n_skip", 0),
                    "n_regime_filtered": hist_b.get("n_regime_filtered", 0),
                    "source": hist.get("source"),
                    "data_gap": hist.get("data_gap"),
                    "note": "historical TAKE-eq is not KEEP",
                },
                "experiments": [
                    {
                        "id": e["id"],
                        "status": e["status"],
                        "runnable_now": False,
                    }
                    for e in list_experiments()
                    if k in (e.get("strategies") or [])
                ],
                "verdict": "WATCH",
            }
        )
    return {
        "ok": True,
        "mode": "research",
        "wave_a_status": "WATCH",
        "keep": False,
        "strategies": out_strats,
        "laws": {
            "thesis_not_implementation": True,
            "ananta_regime_is_hypothesis": True,
            "three_confidences_separate": True,
        },
    }


def _safe_attr(source: str) -> dict:
    try:
        return attribute_print_ready(source)
    except Exception as e:
        return {"data_gap": True, "error": str(e), "by_strategy": {}}


def _safe_knowledge() -> dict:
    try:
        from src.tools.ananta_api import get_strategy_knowledge

        kn = get_strategy_knowledge()
        if kn.get("success"):
            return kn.get("data") or {}
        return {"data_gap": True, "error": kn.get("error")}
    except Exception as e:
        return {"data_gap": True, "error": str(e)}


def _pick_knowledge(blob: dict, key: str) -> dict:
    if blob.get("data_gap"):
        return {"data_gap": True, "error": blob.get("error")}
    for s in blob.get("strategies") or []:
        if (s.get("strategy_id") or s.get("key") or "").lower() == key:
            return {
                "name": s.get("name"),
                "understanding_confidence": s.get("understanding_confidence"),
                "evidence_confidence": s.get("evidence_confidence"),
                "contradictions": s.get("contradictions") or [],
            }
    return {"data_gap": True}
