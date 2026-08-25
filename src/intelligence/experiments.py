"""Experiment proposal → human approval → controlled evaluation.

The ledger can exist while S5 stays parked.
Nothing in this module mutates hunter / squeeze / bollinger-mr.
H1 live enable is rejected even if someone types 'approve'.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

LEDGER = Path("experiments_ledger.jsonl")

# Statuses a row may hold. RUNNING is never written for S5 while parked.
STATUSES = (
    "PROPOSED",
    "PENDING_TAPE",
    "APPROVED",
    "APPROVED_MEASUREMENT",
    "APPROVED_PENDING_INSTRUMENTATION",
    "REJECTED",
    "REJECTED_AS_LIVE_ENABLE",
    "NO_EXPERIMENT",
    "LATER",
    "RUNNING",
    "COMPLETE",
    "SUPERSEDED",
)

# Catalog is the source of truth for S5. Ledger records human actions against it.
CATALOG: Dict[str, Dict[str, Any]] = {
    "S5-H1": {
        "id": "S5-H1",
        "title": "Hunter TREND_UP filter (shadow only)",
        "status": "REJECTED_AS_LIVE_ENABLE",
        "runnable": False,
        "kind": "shadow_log",
        "strategies": ["hunter"],
        "mutates_production": False,
        "live_enable": False,
        "hypothesis": (
            "Implementation generates TREND_UP hunter setups that Wave A policy forbids. "
            "That is a contradiction, not proof the profile deserves to trade."
        ),
        "if_approved": "Paper-only SHADOW_TAKE_EQ log vs +1h/+4h. Never allowed_regimes += TREND_UP.",
        "park_reason": "S5 paused — let live tape accumulate. Live enable rejected.",
    },
    "S5-H2": {
        "id": "S5-H2",
        "title": "Hunter REVERSAL gate histogram",
        "status": "APPROVED_MEASUREMENT",
        "runnable": False,
        "kind": "measurement",
        "strategies": ["hunter"],
        "mutates_production": False,
        "live_enable": False,
        "hypothesis": "STABILIZED_REVERSAL gates may be conjunctively too rare — or REVERSAL itself is rare.",
        "if_approved": "Histogram reason_codes on REVERSAL bars. lab h2. No param change.",
        "park_reason": "Human approved 2026-08-25 as measurement. Report is lab h2. try_run stays refused. No Hunter rewrite.",
    },
    "S5-H3": {
        "id": "S5-H3",
        "title": "Split TAKE-eq +1h by strategy",
        "status": "APPROVED_MEASUREMENT",
        "runnable": False,
        "kind": "report",
        "strategies": ["hunter", "squeeze", "bollinger-mr"],
        "mutates_production": False,
        "live_enable": False,
        "hypothesis": "Wave A TAKE quality is currently a Bollinger number wearing a Wave A badge.",
        "if_approved": "Report +15m/+1h/+4h per strategy. lab attribution live | lab attribution replay.",
        "park_reason": "Human approved 2026-08-25. The report is lab attribution (join outcome_truth.assets). try_run stays refused. No KEEP.",
    },
    "S5-H4": {
        "id": "S5-H4",
        "title": "Squeeze scarcity",
        "status": "NO_EXPERIMENT",
        "runnable": False,
        "kind": "none",
        "strategies": ["squeeze"],
        "mutates_production": False,
        "live_enable": False,
        "hypothesis": "Working as designed. Scarce is not broken.",
        "if_approved": "None. Keep WATCH. Do not add RANGE.",
        "park_reason": "No experiment.",
    },
    "S5-H5": {
        "id": "S5-H5",
        "title": "Slow vs fast audit clock",
        "status": "LATER",
        "runnable": False,
        "kind": "measurement",
        "strategies": [],
        "mutates_production": False,
        "live_enable": False,
        "hypothesis": "MISCLASSIFIED scores a slow EMA market label against a fast 1h flag.",
        "if_approved": "Add a slow independent clock. Do not change classify_regime.",
        "park_reason": "Optional, after H2/H3, after more tape.",
    },
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append(record: dict) -> bool:
    try:
        with LEDGER.open("a") as f:
            f.write(json.dumps(record, default=str) + "\n")
        return True
    except Exception:
        return False


def list_experiments() -> List[Dict[str, Any]]:
    actions = _read_actions()
    out = []
    for item in CATALOG.values():
        row = dict(item)
        row["human_actions"] = [a for a in actions if a.get("id") == item["id"]]
        row["runnable_now"] = False
        row["blocked_by"] = _blocked_by(item)
        out.append(row)
    return out


def get_experiment(exp_id: str) -> Optional[Dict[str, Any]]:
    item = CATALOG.get(_norm_id(exp_id))
    if not item:
        return None
    row = dict(item)
    row["runnable_now"] = False
    row["blocked_by"] = _blocked_by(item)
    return row


def propose(
    *,
    title: str,
    hypothesis: str,
    kind: str = "measurement",
    strategies: Optional[List[str]] = None,
    mutates_production: bool = False,
    note: str = "",
) -> Dict[str, Any]:
    """Append a new PROPOSED experiment. Does not approve. Does not run."""
    if mutates_production:
        record = {
            "event": "reject_proposal",
            "ts": _utc_now(),
            "title": title,
            "reason": "Production mutation proposals must go through versioned human path; auto-rejected as runnable.",
        }
        _append(record)
        return {"ok": False, "error": "mutates_production=True is not auto-runnable", "record": record}
    exp_id = f"PROP-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"
    record = {
        "event": "propose",
        "ts": _utc_now(),
        "id": exp_id,
        "title": title,
        "hypothesis": hypothesis,
        "kind": kind,
        "strategies": strategies or [],
        "status": "PROPOSED",
        "runnable": False,
        "mutates_production": False,
        "live_enable": False,
        "note": note,
    }
    _append(record)
    return {"ok": True, "id": exp_id, "status": "PROPOSED", "runnable_now": False}


def approve(exp_id: str, *, human: str, note: str = "") -> Dict[str, Any]:
    """Record a human approval. Does not start the experiment.

    H1 live enable cannot be approved into a run. Shadow is the only legal shape.
    """
    item = get_experiment(exp_id)
    if item is None:
        return {"ok": False, "error": f"unknown experiment {exp_id}"}
    if item.get("live_enable") or item["id"] == "S5-H1":
        record = {
            "event": "reject_live_enable",
            "ts": _utc_now(),
            "id": item["id"],
            "human": human,
            "note": note or "H1 live enable cannot be approved. Shadow only.",
            "status": "REJECTED_AS_LIVE_ENABLE",
        }
        _append(record)
        return {"ok": False, "error": "H1 live enable is rejected; shadow only", "record": record}
    if item.get("status") in ("NO_EXPERIMENT", "LATER"):
        return {"ok": False, "error": f"{item['id']} is {item['status']}; nothing to approve"}
    record = {
        "event": "approve",
        "ts": _utc_now(),
        "id": item["id"],
        "human": human,
        "note": note,
        "status": "APPROVED",
        "runnable_now": False,
        "park_reason": item.get("park_reason"),
    }
    _append(record)
    return {"ok": True, "id": item["id"], "status": "APPROVED", "runnable_now": False, "note": "Parked until tape gate lifts"}


def try_run(exp_id: str) -> Dict[str, Any]:
    """Refuse mutation. H3 report is `lab attribution`, not try_run."""
    item = get_experiment(exp_id) or {"id": _norm_id(exp_id), "status": "UNKNOWN"}
    record = {
        "event": "try_run_blocked",
        "ts": _utc_now(),
        "id": item.get("id"),
        "status": item.get("status"),
        "blocked_by": _blocked_by(item) if item.get("id") in CATALOG else ["UNKNOWN_EXPERIMENT"],
    }
    _append(record)
    if item.get("id") == "S5-H3":
        hint = "Use lab attribution live / lab attribution replay for the H3 report."
    elif item.get("id") == "S5-H2":
        hint = "Use lab h2 for the H2 histogram."
    else:
        hint = "No S5 mutation run."
    return {
        "ok": False,
        "ran": False,
        "id": item.get("id"),
        "error": f"try_run does not mutate Wave A. {hint}",
        "blocked_by": record["blocked_by"],
    }


def _blocked_by(item: Dict[str, Any]) -> List[str]:
    reasons = ["WAVE_A_WATCH", "NO_PRODUCTION_MUTATION"]
    eid = item.get("id")
    st = item.get("status")
    if eid == "S5-H1" or item.get("live_enable"):
        reasons.append("H1_LIVE_ENABLE_REJECTED")
    if eid == "S5-H2":
        reasons.append("USE_LAB_H2")
    if eid == "S5-H3":
        reasons.append("USE_LAB_ATTRIBUTION")
    if st == "NO_EXPERIMENT":
        reasons.append("NO_EXPERIMENT")
    if st == "LATER":
        reasons.append("LATER")
    if st in ("PENDING_TAPE",):
        reasons.append("S5_PARKED_PENDING_TAPE")
    return reasons


def _norm_id(exp_id: str) -> str:
    s = str(exp_id or "").strip().upper()
    aliases = {
        "H1": "S5-H1",
        "H2": "S5-H2",
        "H3": "S5-H3",
        "H4": "S5-H4",
        "H5": "S5-H5",
    }
    return aliases.get(s, s)


def _read_actions() -> List[dict]:
    if not LEDGER.exists():
        return []
    rows: List[dict] = []
    try:
        for line in LEDGER.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    except Exception:
        return []
    return rows
