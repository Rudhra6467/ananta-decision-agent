"""One DI pass on the latest live observation.

M1-C/M1-D: state -> catalog -> context rank -> select/refuse + G1-G7 attach.
Memory may not TAKE. paper_take / keep / exec stay false.
Issued may be NO_TRADE | WATCH | WAIT | SHADOW_PAPER | UNKNOWN.
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
from src.intelligence.hands_funnel import from_writer as funnel_from_writer
from src.intelligence.coverage_matrix import matrix as coverage_matrix
from src.intelligence.snapshot import build as build_snapshot
from src.intelligence.exit_engine import plan as exit_plan
from src.intelligence.counterfactual import open_case as open_counterfactual
from src.intelligence.paper_ledger import refuse_fill
from src.intelligence.rank_desk import rank_for
from src.intelligence.scan_candidates import _fp_from_obs, build as build_scan
from src.intelligence.state_card import card as state_card
from src.tools.observation_log import OBSERVATION_LOG, _read_jsonl

VERSION = "DI-LOOP-v1-l2-g1g7"
OUT = Path("di_loop.json")
FUNNEL_OUT = Path("hands_funnel_cycle.json")


def _emit_funnel(obs: dict, st: dict, scan: dict, l2: dict, issued: str) -> dict[str, Any]:
    row = funnel_from_writer(obs, st, scan, l2, issued)
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
                {"id": r.get("id"), "family_match": r.get("family_match"), "refuse_reasons": r.get("refuse_reasons")}
                for r in (l2.get("ranked") or [])
                if r.get("id") != decision.get("best_id")
            ][:6],
        },
    }
    out["funnel"] = _emit_funnel(obs, st, scan, l2, issued)
    out["coverage"] = coverage_matrix((l2.get("state") or {}).get("regime"))
    out["decision_snapshot"] = build_snapshot(state=l2_state, scan=scan, l2=l2, issued=issued, ts=out["ts"])
    out["exit_plan"] = exit_plan(family=next((r.get("family") for r in (l2.get("ranked") or []) if r.get("id") == decision.get("best_id")), None))
    out["counterfactual"] = open_counterfactual(out["decision_snapshot"])
    out["paper_book"] = refuse_fill("PAPER_GATE_CLOSED")
    Path("decision_snapshot.json").write_text(json.dumps(out["decision_snapshot"], indent=2, default=str))
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
    print(f"  paper_take={r.get('paper_take')} keep={r.get('keep')} exec={r.get('exec')} m2={r.get('counts_for_m2')}")
    print(f"  look_class={(r.get('funnel') or {}).get('look_class')}  paper_book={(r.get('paper_book') or {}).get('status')}")
    print("-" * 64)
    print("  L2 cannot TAKE. Paper authority closed. Continuation stays BENCHED.")
    print(f"  saved={r.get('saved')}  versions={r.get('versions')}")
    print("=" * 64)
    print()
    return r
