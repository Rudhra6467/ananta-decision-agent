"""Knowledge consult v0 — DI may ask memory. Memory may not TAKE.

Given current Market Truth flags, retrieve hist lookup for that tape.
knowledge_action is WAIT or UNKNOWN. Never TAKE. Never overrides issued_action.

CLI: lab consult [live|replay]
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from src.intelligence.fingerprint import from_market_truth
from src.intelligence.lookup import lookup
from src.tools.observation_log import OBSERVATION_LOG, REPLAY_LOG, _read_jsonl

VERSION = "CONSULT-v0"
OUT = Path("knowledge_consult.json")


def consult(observation: Optional[dict] = None, *, source: str = "live") -> Dict[str, Any]:
    obs = observation if observation is not None else _latest(source)
    mt = (obs or {}).get("market_truth") or {}
    st = (obs or {}).get("system_truth") or {}
    asset = str(st.get("symbol") or "BTC/USD")
    fp = from_market_truth(mt, asset)
    flag = str(fp.get("trend") or "UNKNOWN")
    if flag in ("UNKNOWN", "", "NONE"):
        hist = {"rows": [], "source": "historical_lab", "flag": flag}
        k_action = "UNKNOWN"
        why = "NO_TAPE_FLAG"
    else:
        hist = lookup(flag, "replay")
        k_action = "WAIT"
        why = "I2_BASELINE_NO_SUITABLE"
        if not (hist.get("rows") or []):
            k_action = "UNKNOWN"
            why = "NO_HIST_FOR_FLAG"
    rows = []
    for r in hist.get("rows") or []:
        rows.append({
            "strategy": r.get("strategy"),
            "TAKE": r.get("TAKE"),
            "depth": r.get("depth"),
            "vs_sitout": r.get("vs_sitout"),
            "mean_1h_take": r.get("mean_1h_take"),
            "mean_1h_skip": r.get("mean_1h_skip"),
            "keep": False,
        })
    report = {
        "ok": True,
        "version": VERSION,
        "source_obs": "live_paper" if source == "live" else "historical_lab",
        "obs_id": (obs or {}).get("obs_id") or ((obs or {}).get("system_truth") or {}).get("obs_id"),
        "fingerprint": {
            "trend": fp.get("trend"),
            "compression": fp.get("compression"),
            "independent_label": fp.get("independent_label"),
            "key": fp.get("key"),
            "data_gap": fp.get("data_gap"),
        },
        "flag": flag,
        "hist_source": hist.get("source"),
        "rows": rows,
        "knowledge_action": k_action,
        "why": why,
        "issued_override": False,
        "keep": False,
        "live_enable": False,
        "trend_up_enable": False,
        "authority_earned": False,
        "laws": {
            "consult_is_not_keep": True,
            "consult_cannot_take": True,
            "consult_cannot_override_issued": True,
            "wave_a_watch": True,
            "i2_hist_baseline_locked": True,
            "unknown_is_valid": True,
        },
        "note": (
            "DI asked memory: given this tape, what happened historically? "
            "Answer at this n is WAIT/UNKNOWN. Memory does not fill."
        ),
    }
    try:
        OUT.write_text(json.dumps(report, indent=2, default=str))
        report["saved"] = str(OUT)
    except Exception:
        report["saved"] = None
    return report


def print_consult(source: str = "live") -> Dict[str, Any]:
    report = consult(source=source)
    print(f"\nKNOWLEDGE CONSULT  {report.get('version')}")
    print("=" * 64)
    print("DI may ask. Memory may not TAKE. Issued action unchanged.")
    print(
        f"  tape={report.get('flag')}  obs={report.get('obs_id') or '—'}  "
        f"knowledge_action={report.get('knowledge_action')}  override=False  keep=False"
    )
    print(f"  why={report.get('why')}")
    fp = report.get("fingerprint") or {}
    print(f"  fp={fp.get('key')}  gap={fp.get('data_gap')}")
    print("-" * 64)
    rows = report.get("rows") or []
    if not rows:
        print("  (no hist rows for this flag — UNKNOWN is valid)")
    for r in rows:
        print(
            f"  {r.get('strategy'):<18} TAKE={r.get('TAKE')}  depth={r.get('depth')}  "
            f"vs_sitout={r.get('vs_sitout')}  +1h_TAKE={r.get('mean_1h_take')}  "
            f"+1h_SKIP={r.get('mean_1h_skip')}"
        )
    print("-" * 64)
    print("  Consult ≠ KEEP. Consult ≠ TREND_UP. Wave A stays WATCH.")
    if report.get("saved"):
        print(f"  saved: {report['saved']}")
    print("=" * 64)
    return report


def _latest(source: str) -> Optional[dict]:
    path = OBSERVATION_LOG if source == "live" else REPLAY_LOG
    rows = _read_jsonl(path)
    return rows[-1] if rows else None
