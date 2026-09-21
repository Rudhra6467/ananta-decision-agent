"""Context-conditioned ranking. Do not average strategies into a leaderboard."""
from __future__ import annotations

from typing import Any

ORDER = (
    "family_compatibility",
    "regime_compatibility",
    "timeframe_compatibility",
    "role_strategy_observe_before_when_not_veto",
    "oos_and_sample_only_inside_matching_family_and_role",
    "recent_stability",
    "failure_conditions",
    "strategy_maturity",
    "trust_and_authority",
)


def explain(ranked: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for i, row in enumerate(ranked):
        nxt = ranked[i + 1] if i + 1 < len(ranked) else None
        why = []
        if row.get("family_match") == "HIGH":
            why.append("family matches facing state")
        else:
            why.append("family mismatch — cannot lead")
        if row.get("type") in ("when_not", "veto"):
            why.append("role is warning, not selectable strategy")
        if nxt and row.get("score", 0) >= nxt.get("score", 0):
            why.append(f"score {row.get('score')} >= next {nxt.get('id')} {nxt.get('score')}")
        row = dict(row)
        row["why_above_next"] = "; ".join(why)
        row["do_not_global_average"] = True
        out.append(row)
    return out


def never_global_mean(objects: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "id": "ranking.law.v1",
        "forbidden": "mean(score across all states) as a leaderboard",
        "required": "rank inside the facing state only",
        "order": list(ORDER),
        "n_objects": len(objects),
        "paper_take": False,
    }
