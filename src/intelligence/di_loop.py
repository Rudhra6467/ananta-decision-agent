"""One DI pass on the latest live observation.

M1-C: state -> named catalog retrieve -> context rank -> select/refuse.
Memory may not TAKE. paper_take / keep / exec stay false.
Issued may be NO_TRADE | WATCH | WAIT | SHADOW_PAPER | UNKNOWN.
SHADOW_PAPER and WATCH are development evidence, never M2 school TAKEs.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from src.intelligence.findings import findings as load_findings
from src.intelligence.l2_pathway import (
    LEGAL_ISSUED,
    issued_from_decision,
    run_pathway,
    state_from_observation,
)
from src.intelligence.rank_desk import rank_for
from src.intelligence.scan_candidates import _fp_from_obs, build as build_scan
from src.intelligence.state_card import card as state_card
from src.tools.observation_log import OBSERVATION_LOG, _read_jsonl

VERSION = "DI-LOOP-v1-l2"
OUT = Path("di_loop.json")
FUNNEL_OUT = Path("hands_funnel_cycle.json")


def _emit_funnel(obs: dict, st: dict, scan: dict, l2: dict, issued: str) -> dict[str, Any]:
    """Partial G1 counters from this writer cycle. Missing counts stay 0, not invented."""
    cand = scan.get("candidate") or {}
    ranked = l2.get("ranked") or []
    family_hits = [r for r in ranked if r.get("family_match") == "HIGH"]
    assets_named = [st.get("asset") or "BTC/USD"]
    evaluated = 1 if obs else 0
    row = {
        "cycle_id": (obs.get("system_truth") or {}).get("cycle_id") or obs.get("id") or st.get("obs_id"),
        "bar_tf": l2.get("state", {}).get("tf"),
        "last_bar_open": obs.get("ts") or obs.get("timestamp") or st.get("ts"),
        "assets_named": assets_named,
        "assets_evaluated": evaluated,
        "timeframes": [l2.get("state", {}).get("tf") or "unknown"],
        "bars_evaluated": evaluated,
        "observations": 1 if obs else 0,
        "partial_candidates": 1 if cand else 0,
        "candidate_setups": 1 if cand else 0,
        "qualified_setups": 1 if (l2.get("state") or {}).get("hunter_qualifying") or (l2.get("state") or {}).get("squeeze_qualifying") else 0,
        "strategy_family_matches": len(family_hits),
        "knowledge_retrievals": len(ranked),
        "decisions": 1,
        "paper_candidates": 1 if issued == "SHADOW_PAPER" else 0,
        "issued_TAKE": 0,
        "issued_WAIT": 1 if issued == "WAIT" else 0,
        "issued_NO_TRADE": 1 if issued in ("NO_TRADE", "SHADOW_PAPER") else 0,
        "issued_WATCH": 1 if issued == "WATCH" else 0,
        "coverage_gaps": ["universe_not_fully_evaluated"] if evaluated < 10 else [],
        "looked": bool(obs) and bool(ranked),
        "note": "Partial writer-side funnel. Hands cycle still must emit the full spec.",
    }
    FUNNEL_OUT.write_text(json.dumps(row, indent=2, default=str))
    return row


def run(obs: Dict[str, Any] | None = None) -> Dict[str, Any]:
    rows = _read_jsonl(OBSERVATION_LOG) if OBSERVATION_LOG.exists() else []
    if obs is None:
        obs = rows[-1] if rows else {}
    st = state_card(obs)
    fp = st.get("fingerprint") or (_fp_from_obs(obs) if obs else "UNKNOWN|UNKNOWN|UNKNOWN|UNCLEAR")
    scan = build_scan()
    rank = rank_for(fp)
    find = load_findings()
    l2_state = state_from_observation(obs, st, scan)
    l2 = run_pathway(l2_state)
    decision = l2["decision"]
    issued = issued_from_decision(decision)
    if issued not in LEGAL_ISSUED:
        issued = "NO_TRADE"
    if issued == "TAKE":
        issued = "NO_TRADE"

    hurt = find.get("unsuitable_or_hurt") or []
    naive_issued = rank.get("issued") or scan.get("issued") or "UNKNOWN"
    if naive_issued not in ("WAIT", "UNKNOWN"):
        naive_issued = "WAIT"

    out = {
        "ok": True,
        "version": VERSION,
        "ts": datetime.now(timezone.utc).isoformat(),
        "obs_id": obs.get("id") or st.get("obs_id"),
        "live_n": len(rows),
        "fingerprint": fp,
        "price": st.get("price"),
        "sma20": st.get("sma20"),
        "vwap": st.get("vwap"),
        "issued": issued,
        "action": decision.get("action"),
        "reason": decision.get("reason"),
        "class_id": decision.get("class_id"),
        "best_id": decision.get("best_id"),
        "cited": decision.get("cited") or [],
        "can_take": False,
        "paper_take": False,
        "keep": False,
        "exec": False,
        "counts_for_m2": False,
        "counts_for_paper": False,
        "why": decision.get("reason") or "L2_NO_VALID_STRATEGY",
        "naive_issued": naive_issued,
        "naive_why": rank.get("why") or "I2_BASELINE_NO_SUITABLE",
        "naive_default": l2.get("naive_default"),
        "l2_replaces_naive": True,
        "scan_why": (scan.get("candidate") or {}).get("why_interesting"),
        "rank_rows": [
            {
                "id": r.get("id"),
                "type": r.get("type"),
                "family": r.get("family"),
                "family_match": r.get("family_match"),
                "score": r.get("score"),
                "result": r.get("result"),
                "authority": r.get("authority"),
                "status": r.get("status"),
                "sample_n": r.get("sample_n"),
            }
            for r in (l2.get("ranked") or [])[:8]
        ],
        "desk_rank_rows": rank.get("rows") or [],
        "hurt_n": len(hurt),
        "missing_state": st.get("fields_missing_for_richer_state") or [],
        "l2_state": l2_state,
        "versions": l2.get("versions"),
        "snapshot": {
            "knowledge_version": (l2.get("versions") or {}).get("knowledge"),
            "ranking_version": (l2.get("versions") or {}).get("ranking"),
            "decision_version": (l2.get("versions") or {}).get("decision"),
            "retrieved": [r.get("id") for r in (l2.get("ranked") or [])],
            "selected": decision.get("best_id"),
            "rejected": [
                r.get("id")
                for r in (l2.get("ranked") or [])
                if r.get("id") != decision.get("best_id") and r.get("family_match") == "HIGH"
            ],
            "why_not_alternatives": [
                {
                    "id": r.get("id"),
                    "family_match": r.get("family_match"),
                    "refuse_reasons": r.get("refuse_reasons"),
                }
                for r in (l2.get("ranked") or [])
                if r.get("id") != decision.get("best_id")
            ][:6],
        },
    }
    out["funnel"] = _emit_funnel(obs, st, scan, l2, issued)
    OUT.write_text(json.dumps(out, indent=2, default=str))
    out["saved"] = str(OUT)
    return out


def print_loop() -> Dict[str, Any]:
    r = run()
    print(f"\nDI LOOP  {r['version']}")
    print("=" * 64)
    print("State -> catalog -> context rank -> select/refuse. Never TAKE.")
    print(f"  fp={r.get('fingerprint')}  price={r.get('price')} sma20={r.get('sma20')}")
    print(f"  l2_regime={((r.get('l2_state') or {}).get('regime'))}  tf={((r.get('l2_state') or {}).get('tf'))}")
    print(f"  issued={r.get('issued')}  why={r.get('why')}  best={r.get('best_id')}")
    print(f"  cited={r.get('cited')}")
    print(f"  naive={r.get('naive_issued')} / {r.get('naive_why')}")
    print(f"  paper_take={r.get('paper_take')} keep={r.get('keep')} exec={r.get('exec')} m2={r.get('counts_for_m2')}")
    print("-" * 64)
    for x in (r.get("rank_rows") or [])[:6]:
        print(
            f"  {str(x.get('id') or ''):<32} fam={x.get('family_match'):<4} "
            f"score={x.get('score')} {x.get('result')} n={x.get('sample_n')}"
        )
    print("-" * 64)
    print("  L2 cannot TAKE. Paper authority closed. Continuation stays BENCHED.")
    print(f"  saved={r.get('saved')}  versions={r.get('versions')}")
    print("=" * 64)
    print()
    return r
