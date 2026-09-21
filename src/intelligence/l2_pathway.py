#!/usr/bin/env python3
"""M1-C Level-2 pathway. Named catalog + context-conditioned rank + select/refuse.

Drop-in for ananta-decision-agent di_loop. Does not grant paper_take.
Raw sample size is never applicability.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CATALOG_PATH = Path(__file__).with_name("knowledge_catalog_v1.json")
KNOWLEDGE_VERSION = "knowledge.catalog.v1"
RANKING_VERSION = "ranking.v1.context_conditioned"
DECISION_VERSION = "decision.l2.v1"
PAPER_TAKE = False
KEEP = False
EXEC = False
LEGAL_ISSUED = ("NO_TRADE", "WATCH", "WAIT", "SHADOW_PAPER", "UNKNOWN")

FAMILY_FOR_REGIME = {
    "TREND_UP": "continuation",
    "TREND_DOWN": "trend_down",
    "REVERSAL": "reversal",
    "COMPRESSION": "compression",
    "LAG": "lag_catchup",
    "EXPANSION": "context",
    "RANGE": "range",
    "BREAKOUT": "breakout",
    "BREAKDOWN": "breakdown",
    "MEAN_REVERSION": "mean_reversion",
    "MOMENTUM": "continuation",
}

TYPE_RANK = {"strategy": 0, "observe": 0, "when_not": 1, "variant": 2, "veto": 3}


def load_catalog() -> dict[str, Any]:
    return json.loads(CATALOG_PATH.read_text())


def axes(state: dict[str, Any], obj: dict[str, Any]) -> dict[str, Any]:
    family = FAMILY_FOR_REGIME.get(state["regime"], "unknown")
    family_match = obj.get("family") == family
    regime_match = state["regime"] in (obj.get("regimes") or [])
    tf_match = obj.get("tf") == state.get("tf")
    oos = obj.get("oos", "NA")
    n = int(obj.get("n") or 0)
    authority = obj.get("authority", "NONE")
    status = obj.get("status", "")
    typ = obj.get("type", "")

    sample_ok = n >= 30 and typ in ("strategy", "observe")
    evidence = "HIGH" if n >= 30 and oos in ("PASS", "ACCUMULATE") else (
        "MED" if n >= 16 else "LOW"
    )
    if typ in ("when_not", "veto"):
        evidence = "WARN"
        sample_ok = False

    failure_risk = "HIGH" if obj.get("economic") in ("NOT_ECONOMIC", "REJECTED") or oos == "FAIL" else (
        "MED" if oos == "INSUFFICIENT" else "LOW"
    )
    profile_ok = True

    refuse_reasons = []
    if not family_match and typ not in ("veto", "when_not"):
        refuse_reasons.append("FAMILY_MISMATCH")
    if obj.get("live") == "DISABLED" or status == "BENCHED":
        refuse_reasons.append("BENCHED")
    if obj.get("economic") in ("NOT_ECONOMIC", "REJECTED"):
        refuse_reasons.append("NOT_PROMOTABLE")
    if oos == "FAIL":
        refuse_reasons.append("OOS_FAIL")
    if oos == "INSUFFICIENT":
        refuse_reasons.append("INSUFFICIENT_N")
    if authority in ("NONE",) and typ != "observe":
        refuse_reasons.append("NO_AUTHORITY")
    if not PAPER_TAKE:
        refuse_reasons.append("PAPER_GATE_CLOSED")
    if typ in ("when_not", "veto", "variant"):
        refuse_reasons.append("NOT_SELECTABLE")

    result = "WATCH" if typ == "observe" and authority == "WATCH" and family_match else "REFUSE"

    score = 0
    if family_match:
        score += 40
    if regime_match:
        score += 20
    if tf_match:
        score += 10
    if typ in ("strategy", "observe") and family_match:
        if n >= 76:
            score += 8
        elif n >= 30:
            score += 6
        elif n >= 16:
            score += 3
    if oos == "PASS":
        score += 10
    elif oos == "ACCUMULATE":
        score += 6
    if typ in ("when_not", "veto"):
        score = min(score, 25)

    return {
        "id": obj["id"],
        "type": typ,
        "family": obj.get("family"),
        "regimes": list(obj.get("regimes") or []),
        "family_match": "HIGH" if family_match else "LOW",
        "regime_match": "HIGH" if regime_match else "LOW",
        "timeframe_match": "HIGH" if tf_match else "LOW",
        "historical_similarity": "HIGH" if family_match and regime_match else "LOW",
        "oos": oos,
        "sample_n": n,
        "sample_sufficiency": sample_ok,
        "evidence_strength": evidence,
        "failure_risk": failure_risk,
        "authority": authority,
        "status": status,
        "profile_ok": profile_ok,
        "score": score,
        "result": result,
        "refuse_reasons": refuse_reasons,
    }


def rank(state: dict[str, Any], catalog: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    catalog = catalog or load_catalog()
    rows = [axes(state, obj) for obj in catalog["objects"]]
    rows.sort(
        key=lambda r: (
            0 if r["family_match"] == "HIGH" else 1,
            TYPE_RANK.get(r["type"], 9),
            -r["score"],
        )
    )
    return rows


def select(state: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    family = FAMILY_FOR_REGIME.get(state.get("regime"), "unknown")
    family_hits = [r for r in rows if r["family_match"] == "HIGH"]
    best = family_hits[0] if family_hits else None
    watch = [r for r in family_hits if r["result"] == "WATCH"]

    action = "NO_TRADE"
    reason = "NO_VALID_STRATEGY"
    label = "NO_TRADE"
    class_id = "STRATEGY_MATCH"

    if family == "unknown" or not state.get("regime") or state.get("regime") == "UNKNOWN":
        action = "NO_TRADE"
        reason = "STATE_UNCLEAR"
        label = "UNKNOWN"
        class_id = "SCAN_COVERAGE"
        best = None
    elif state.get("observer_match") == "set16" and watch:
        action = "WATCH"
        reason = "MATCH_NOT_TAKE"
        label = "WATCH"
        class_id = "DECISION_GATE"
        best = watch[0]
    elif family == "continuation" and state.get("continuation_would_qualify"):
        action = "NO_TRADE"
        reason = "BEST_AVAILABLE_STRATEGY_HAS_NO_PAPER_AUTHORITY"
        label = "SHADOW_PAPER"
        class_id = "SCAN_COVERAGE"
    elif state.get("hunter_qualifying"):
        action = "WAIT"
        reason = "SCHOOL_CORE_NO_NAMED_VARIANT"
        label = "WAIT"
        class_id = "STRATEGY_MATCH"
    elif state.get("squeeze_qualifying"):
        action = "WAIT"
        reason = "SCHOOL_CORE_NO_NAMED_VARIANT"
        label = "WAIT"
        class_id = "STRATEGY_MATCH"
    elif family_hits and best and "BENCHED" in (best.get("refuse_reasons") or []):
        action = "NO_TRADE"
        reason = "BEST_AVAILABLE_STRATEGY_HAS_NO_PAPER_AUTHORITY"
        label = "SHADOW_PAPER"
        class_id = "SCAN_COVERAGE"

    cited = []
    if best:
        cited.append(best["id"])
    regime = state.get("regime")
    for r in rows:
        applies = r["family_match"] == "HIGH" or (
            r["type"] == "veto" and regime in (r.get("regimes") or [])
        )
        if applies and r["id"] not in cited:
            cited.append(r["id"])
        if len(cited) >= 6:
            break

    return {
        "action": action,
        "label": label,
        "class_id": class_id,
        "reason": reason,
        "best_id": best["id"] if best else None,
        "best": best,
        "cited": cited,
        "counts_for_m2": False,
        "counts_for_paper": False,
        "paper_take": PAPER_TAKE,
        "keep": KEEP,
        "exec": EXEC,
    }


def issued_from_decision(decision: dict[str, Any]) -> str:
    """Map select() to a writer-legal issued value. Never TAKE."""
    label = decision.get("label") or decision.get("action") or "NO_TRADE"
    if label == "TAKE" or decision.get("paper_take"):
        return "NO_TRADE"
    if label in LEGAL_ISSUED:
        return label
    action = decision.get("action") or "NO_TRADE"
    return action if action in LEGAL_ISSUED else "NO_TRADE"


def state_from_observation(
    obs: dict[str, Any] | None,
    st: dict[str, Any] | None = None,
    scan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Structured catalog query from a Hands / observation_v0 row. Does not invent tape."""
    obs = obs or {}
    st = st or {}
    scan = scan or {}
    cand = scan.get("candidate") or {}
    sys = obs.get("system_truth") or {}
    strats = sys.get("strategy_observations") or obs.get("strategy_observations") or []

    def _is(name: str, row: dict[str, Any]) -> bool:
        return str(row.get("strategy") or "").lower() in {name, name.replace("_", "-")}

    hunter_q = any(_is("hunter", s) and s.get("setup_detected") for s in strats)
    squeeze_q = any(_is("squeeze", s) and s.get("setup_detected") for s in strats)
    set16 = any(
        _is("set16", s) and (s.get("setup_detected") or s.get("match") or s.get("decision") == "MATCH")
        for s in strats
    )
    if obs.get("observer_match") == "set16" or st.get("observer_match") == "set16":
        set16 = True

    fp = str(st.get("fingerprint") or cand.get("fingerprint") or "")
    parts = fp.split("|") if fp else []
    trend = parts[0] if parts else str(st.get("trend_flag") or "UNKNOWN")
    comp = parts[1] if len(parts) > 1 else str(st.get("compression_flag") or "UNKNOWN")
    ret = parts[2] if len(parts) > 2 else "UNKNOWN"

    raw_regime = st.get("regime") or obs.get("regime") or ""
    raw = str(raw_regime).upper()
    if set16:
        regime = "LAG"
    elif hunter_q:
        regime = "REVERSAL"
    elif squeeze_q or comp == "COMPRESSION":
        regime = "COMPRESSION"
    elif raw in ("TREND_UP", "TREND_DOWN", "REVERSAL", "COMPRESSION", "LAG", "RANGE", "BREAKOUT", "EXPANSION"):
        regime = raw
    elif trend == "UP" or raw in ("BULL", "BULLISH", "UP"):
        regime = "TREND_UP"
    elif trend == "DOWN" or raw in ("BEAR", "BEARISH", "DOWN"):
        regime = "TREND_DOWN"
    elif st.get("trend_flag") == "UP":
        regime = "TREND_UP"
    elif st.get("trend_flag") == "DOWN":
        regime = "TREND_DOWN"
    else:
        regime = "UNKNOWN"

    asset = st.get("asset") or cand.get("asset") or obs.get("asset") or "BTC/USD"
    tf = "15m" if set16 else (st.get("tf") or cand.get("timeframe") or "1h")
    direction = "LONG" if regime in ("TREND_UP", "LAG") or trend == "UP" else (
        "SHORT" if regime in ("TREND_DOWN",) or trend == "DOWN" else "NONE"
    )
    continuation_would = regime == "TREND_UP" and not hunter_q and not squeeze_q

    return {
        "id": obs.get("id") or st.get("obs_id") or "live.unknown",
        "asset": str(asset).split("/")[0],
        "tf": tf,
        "regime": regime,
        "direction": direction,
        "volatility": "EXPANDING" if comp == "EXPANSION" else ("COMPRESSED" if comp == "COMPRESSION" else "UNKNOWN"),
        "momentum": "POSITIVE" if ret.startswith("UP") else ("NEGATIVE" if ret.startswith("DOWN") else "UNKNOWN"),
        "structure": "INTACT" if regime == "TREND_UP" else regime,
        "liquidity": "NORMAL",
        "continuation_would_qualify": continuation_would,
        "hunter_qualifying": hunter_q,
        "squeeze_qualifying": squeeze_q,
        "observer_match": "set16" if set16 else None,
        "fingerprint": fp or None,
        "source": "observation",
    }


def run_pathway(state: dict[str, Any]) -> dict[str, Any]:
    catalog = load_catalog()
    rows = rank(state, catalog)
    decision = select(state, rows)
    naive = (
        "WATCH because observer MATCHED"
        if state.get("observer_match")
        else "WAIT for hunter/squeeze to fire"
    )
    return {
        "versions": {
            "knowledge": KNOWLEDGE_VERSION,
            "ranking": RANKING_VERSION,
            "decision": DECISION_VERSION,
        },
        "state": state,
        "ranked": rows,
        "decision": decision,
        "naive_default": naive,
        "l2_replaces_naive": decision["reason"] != naive,
    }


MARKETS = [
    {
        "id": "btc.trend_up.2026-09-21",
        "asset": "BTC",
        "tf": "1h",
        "regime": "TREND_UP",
        "direction": "LONG",
        "volatility": "EXPANDING",
        "momentum": "POSITIVE",
        "structure": "INTACT",
        "liquidity": "NORMAL",
        "continuation_would_qualify": True,
        "hunter_qualifying": False,
        "squeeze_qualifying": False,
        "observer_match": None,
    },
    {
        "id": "eth.trend_up.hands.2026-09-19",
        "asset": "ETH",
        "tf": "1h",
        "regime": "TREND_UP",
        "direction": "LONG",
        "volatility": "MODERATE",
        "momentum": "POSITIVE",
        "structure": "INTACT",
        "liquidity": "NORMAL",
        "continuation_would_qualify": True,
        "hunter_qualifying": False,
        "squeeze_qualifying": False,
        "observer_match": None,
    },
    {
        "id": "ada.set16.2026-09-20",
        "asset": "ADA",
        "tf": "15m",
        "regime": "LAG",
        "direction": "LONG",
        "volatility": "LOW",
        "momentum": "LOW",
        "structure": "LAG",
        "liquidity": "NORMAL",
        "continuation_would_qualify": False,
        "hunter_qualifying": False,
        "squeeze_qualifying": False,
        "observer_match": "set16",
    },
    {
        "id": "btc.hunter.hypothetical",
        "asset": "BTC",
        "tf": "1h",
        "regime": "REVERSAL",
        "direction": "LONG",
        "volatility": "UNKNOWN",
        "momentum": "UNKNOWN",
        "structure": "REVERSAL",
        "liquidity": "NORMAL",
        "continuation_would_qualify": False,
        "hunter_qualifying": True,
        "squeeze_qualifying": False,
        "observer_match": None,
    },
]


def main() -> None:
    out = {m["id"]: run_pathway(m) for m in MARKETS}
    dest = Path(__file__).with_name("l2_pathway_runs_v1.json")
    slim = {}
    for k, v in out.items():
        d = v["decision"]
        slim[k] = {
            "action": d["action"],
            "label": d["label"],
            "reason": d["reason"],
            "class_id": d["class_id"],
            "best_id": d["best_id"],
            "cited": d["cited"],
            "top3": [
                {"id": r["id"], "score": r["score"], "family_match": r["family_match"], "result": r["result"]}
                for r in v["ranked"][:3]
            ],
            "naive_default": v["naive_default"],
        }
    dest.write_text(json.dumps(slim, indent=2))
    print(json.dumps(slim, indent=2))


if __name__ == "__main__":
    main()
