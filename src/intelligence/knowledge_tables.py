"""Knowledge tables — query saved artifacts. Not a rescan. Not KEEP.

The agent looks these up instead of replaying 10k bars on every decision.
Missing files are DATA_GAP, not invented scores.

CLI: lab tables
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

VERSION = "TABLES-v0"
ARTIFACTS = {
    "memory": Path("setup_memory_index.json"),
    "fingerprints": Path("fingerprint_report.json"),
    "boards": Path("strategy_boards.json"),
    "consult_dq": Path("consult_dq.json"),
    "rank": Path("state_rank.json"),
    "universe": Path("universe_knowledge.json"),
    "cards": Path("evidence_cards.json"),
    "sitout": Path("sitout_report.json"),
}


def _load(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def snapshot() -> Dict[str, Any]:
    loaded: Dict[str, Any] = {}
    gaps: List[str] = []
    for name, path in ARTIFACTS.items():
        blob = _load(path)
        if blob is None:
            gaps.append(name)
            loaded[name] = {"data_gap": True, "path": str(path)}
        else:
            loaded[name] = {
                "data_gap": False,
                "path": str(path),
                "version": blob.get("version") or blob.get("schema"),
                "n": blob.get("n_setups") or blob.get("n_obs") or blob.get("n") or blob.get("consults"),
                "keep": False,
            }
    return {
        "ok": True,
        "schema": "knowledge_tables_v0",
        "version": VERSION,
        "keep": False,
        "ranker": False,
        "scan": False,
        "live_enable": False,
        "gaps": gaps,
        "tables": loaded,
        "how_to_fill": [
            "lab memory / lab fingerprints / lab boards — hist discovery tables",
            "lab consult-dq / lab rank-state / lab sitout — live validation tables",
            "lab universe / lab cards — cell catalogue",
        ],
        "laws": {
            "tables_are_lookups_not_rescans": True,
            "missing_file_is_data_gap": True,
            "table_is_not_keep": True,
            "empty_suitable_is_honest": True,
        },
        "note": (
            "These JSON files are the simple tables. "
            "Agent queries them. It does not re-walk candles to answer 'have I seen this'."
        ),
    }


def print_tables() -> Dict[str, Any]:
    report = snapshot()
    print(f"\nKNOWLEDGE TABLES  {report['version']}")
    print("=" * 64)
    print("Lookup artifacts. Not a rescan. Not KEEP. Gap ≠ invent a score.")
    print("-" * 64)
    for name, row in (report.get("tables") or {}).items():
        gap = "GAP" if row.get("data_gap") else "ok"
        print(
            f"  {name:<14} {gap:<4}  n={row.get('n')}  "
            f"ver={row.get('version') or '—'}  {row.get('path')}"
        )
    print("-" * 64)
    if report.get("gaps"):
        print("  missing: " + ", ".join(report["gaps"]))
        print("  Run the matching lab command on the laptop to materialize the table.")
    else:
        print("  All table files present. Query them; do not rescan 1y candles.")
    print("  Table membership ≠ TAKE. Empty SUITABLE is honest.")
    print("=" * 64)
    print()
    return report
