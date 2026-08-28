"""DQ the consults themselves. WAIT/UNKNOWN aftermath, not TAKE quality.

Join consult_log.jsonl to live observation outcomes.
COSTLY after WAIT ≠ TREND_UP enable. Not KEEP.

CLI: lab consult-dq
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

from src.intelligence.attribution import _forward
from src.intelligence.consult import CONSULT_LOG
from src.intelligence.setup_memory import refusal_stamp
from src.tools.observation_log import OBSERVATION_LOG, _read_jsonl

VERSION = "CONSULT-DQ-v0.3"
OUT = Path("consult_dq.json")


def consult_dq() -> Dict[str, Any]:
    logs = _read_jsonl(CONSULT_LOG) if CONSULT_LOG.exists() else []
    obs_rows = _read_jsonl(OBSERVATION_LOG)
    by_id = {}
    for o in obs_rows:
        oid = o.get("obs_id") or ((o.get("system_truth") or {}).get("obs_id"))
        if oid:
            by_id[str(oid)] = o
    stamps = Counter()
    actions = Counter()
    matches = Counter()
    by_action: Dict[str, Counter] = {}
    by_match: Dict[str, Counter] = {}
    by_fp: Dict[str, Counter] = {}
    n_joined = 0
    n_complete = 0
    for row in logs:
        act = str(row.get("knowledge_action") or "?")
        match = str(row.get("match") or "?")
        actions[act] += 1
        matches[match] += 1
        by_action.setdefault(act, Counter())
        by_match.setdefault(match, Counter())
        fp = str(row.get("fp") or "?")
        by_fp.setdefault(fp, Counter())
        obs = by_id.get(str(row.get("obs_id") or ""))
        if not obs:
            stamps["NO_OBS"] += 1
            continue
        n_joined += 1
        fwd = _forward(obs.get("outcome_truth") or {})
        ret = fwd.get("fwd_1h_pct")
        stamp = refusal_stamp(ret)
        stamps[stamp] += 1
        by_action[act][stamp] += 1
        by_match[match][stamp] += 1
        by_fp[fp][stamp] += 1
        if stamp not in ("NO_SAMPLE", "UNUSABLE_CLOCK"):
            n_complete += 1
    report = {
        "ok": True,
        "version": VERSION,
        "n_consults": len(logs),
        "n_joined": n_joined,
        "n_complete_1h": n_complete,
        "data_gap": len(logs) == 0,
        "knowledge_actions": dict(actions),
        "matches": dict(matches),
        "plus_1h_stamps": dict(stamps),
        "plus_1h_by_action": {k: dict(v) for k, v in by_action.items()},
        "plus_1h_by_match": {k: dict(v) for k, v in by_match.items()},
        "plus_1h_by_fp": [
            {"fp": k, "n": sum(v.values()), "stamps": dict(v), "keep": False}
            for k, v in sorted(by_fp.items(), key=lambda kv: -sum(kv[1].values()))[:12]
        ],
        "keep": False,
        "take_enable": False,
        "trend_up_enable": False,
        "laws": {
            "consult_dq_is_not_keep": True,
            "costly_wait_is_not_take_enable": True,
            "sparse_costly_is_not_take": True,
            "live_take_zero_is_watch_not_gap": True,
        },
        "note": (
            "Aftermath of WAIT/UNKNOWN consults. COSTLY means the tape rose after we stood down. "
            "Finding, not KEEP, not TREND_UP."
        ),
    }
    try:
        OUT.write_text(json.dumps(report, indent=2, default=str))
        report["saved"] = str(OUT)
    except Exception:
        report["saved"] = None
    return report


def print_consult_dq() -> Dict[str, Any]:
    report = consult_dq()
    print(f"\nCONSULT DQ  {report.get('version')}")
    print("=" * 64)
    print("WAIT/UNKNOWN aftermath on live tape. Not TAKE quality. Not KEEP.")
    print(
        f"  consults={report.get('n_consults')}  joined={report.get('n_joined')}  "
        f"+1h_complete={report.get('n_complete_1h')}  gap={report.get('data_gap')}  keep=False"
    )
    print(f"  actions={report.get('knowledge_actions')}")
    print(f"  match={report.get('matches')}")
    print(f"  +1h stamps={report.get('plus_1h_stamps')}")
    for act, st in (report.get("plus_1h_by_action") or {}).items():
        print(f"    action {act}: {st}")
    print("  by match")
    for m, st in (report.get("plus_1h_by_match") or {}).items():
        print(f"    match {m}: {st}")
    print("  top fingerprint keys (existing tape — not KEEP)")
    for row in report.get("plus_1h_by_fp") or []:
        print(f"    n={row.get('n'):<4} {row.get('fp')}  {row.get('stamps')}")
    print("-" * 64)
    print("  COSTLY wait ≠ TAKE enable. Sparse UNKNOWN is valid. Wave A stays WATCH.")
    if report.get("saved"):
        print(f"  saved: {report['saved']}")
    print("=" * 64)
    return report
