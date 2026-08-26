"""Monitoring, completeness, auditability, recovery.

CLI: lab system
Does not require a live tape to answer 'is the machine built'.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from src.intelligence.contract import CONTRACT_VERSION, DECISION_SCHEMA, OBSERVATION_SCHEMA
from src.intelligence.experiments import CATALOG
from src.intelligence.profiles import get_active_profile_name
from src.intelligence.schema import WAVE_A
from src.intelligence.user_context import get_user_context

ROOT = Path(".")


def completeness() -> Dict[str, Any]:
    ctx = get_user_context()
    checks = [
        _file("observation_log.py", Path("src/tools/observation_log.py")),
        _file("market_truth.py", Path("src/tools/market_truth.py")),
        _file("outcome_truth.py", Path("src/tools/outcome_truth.py")),
        _file("audit_truth.py", Path("src/tools/audit_truth.py")),
        _file("lab_watch.py", Path("src/lab_watch.py")),
        _file("lab_replay.py", Path("src/tools/lab_replay.py")),
        _file("lab_compare.py", Path("src/tools/lab_compare.py")),
        _file("decision_log.py", Path("src/tools/decision_log.py")),
        _file("cycle_log.py", Path("src/tools/cycle_log.py")),
        _file("ananta_api.py", Path("src/tools/ananta_api.py")),
        _file("di.schema", Path("src/intelligence/schema.py")),
        _file("di.profiles", Path("src/intelligence/profiles.py")),
        _file("di.gates", Path("src/intelligence/gates.py")),
        _file("di.adjudicate", Path("src/intelligence/adjudicate.py")),
        _file("di.experiments", Path("src/intelligence/experiments.py")),
        _file("di.quality", Path("src/intelligence/decision_quality.py")),
        _file("di.h2", Path("src/intelligence/h2.py")),
        _file("di.universe", Path("src/intelligence/universe.py")),
        _file("di.universe_specs", Path("src/intelligence/universe_specs.py")),
        _file("di.evidence", Path("src/intelligence/evidence_engine.py")),
        _file("di.setup_memory", Path("src/intelligence/setup_memory.py")),
        _file("di.fingerprint", Path("src/intelligence/fingerprint.py")),
        _file("di.orchestrate", Path("src/intelligence/orchestrate.py")),
        _ledger("live observation_log.jsonl", Path("observation_log.jsonl"), required=False),
        _ledger("replay observation_replay.jsonl", Path("observation_replay.jsonl"), required=False),
        _ledger("decision_log.json", Path("decision_log.json"), required=False),
        _ledger("cycle_log.jsonl", Path("cycle_log.jsonl"), required=False),
        _ledger("opportunity_log.jsonl", Path("opportunity_log.jsonl"), required=False),
        _ledger("typed_decision.jsonl", Path("typed_decision.jsonl"), required=False),
        _main_py_state(),
    ]
    n_ok = sum(1 for c in checks if c.get("ok"))
    s5 = {k: v["status"] for k, v in CATALOG.items()}
    return {
        "ok": True,
        "machine": "feature-complete-foundation",
        "feature_complete_means_strategy_enabled": False,
        "wave_a": {k: "WATCH" for k in WAVE_A},
        "profile": get_active_profile_name(),
        "intent": ctx.intent,
        "schemas": {
            "observation": OBSERVATION_SCHEMA,
            "decision": DECISION_SCHEMA,
            "agent_api_version": CONTRACT_VERSION,
        },
        "s5": s5,
        "s5_running": False,
        "extra_agents": False,
        "checks": checks,
        "score": f"{n_ok}/{len(checks)}",
        "recovery": _recovery_notes(checks),
        "do_not": [
            "stop lab watch to develop",
            "run H1 as live enable",
            "KEEP Wave A",
            "enable TREND_UP",
            "add Bull/Bear agents",
        ],
    }


def _file(name: str, path: Path) -> Dict[str, Any]:
    ok = path.exists()
    return {"name": name, "path": str(path), "ok": ok, "kind": "code"}


def _ledger(name: str, path: Path, required: bool) -> Dict[str, Any]:
    exists = path.exists()
    n = 0
    if exists:
        try:
            if path.suffix == ".jsonl":
                n = sum(1 for line in path.read_text().splitlines() if line.strip())
            else:
                n = 1
        except Exception:
            n = 0
    return {
        "name": name,
        "path": str(path),
        "ok": exists or not required,
        "kind": "ledger",
        "rows": n,
        "data_gap": not exists,
    }


def _main_py_state() -> Dict[str, Any]:
    p = Path("main.py")
    text = p.read_text() if p.exists() else ""
    recovered = "def interactive_mode" in text and "def run_once" in text
    stub = "_ensure_full_main" in text and not recovered
    return {
        "name": "main.py",
        "path": "main.py",
        "ok": p.exists(),
        "kind": "entry",
        "recovered_interactive": recovered,
        "recovery_stub": stub,
        "note": (
            "Interactive CLI recovers from git on first run if truncated. "
            "lab commands live in src/lab_cli.py and do not need the stub recovered "
            "when invoked via: python -c 'from src.lab_cli import handle_lab_command; handle_lab_command(\"lab system\")'"
        ),
    }


def _recovery_notes(checks: List[dict]) -> List[str]:
    notes = [
        "Leave lab watch 15 and the Ananta backend running.",
        "git pull this commit on the laptop; do not restart the watcher unless it died.",
        "python -m src.intelligence system",
        "python -m src.intelligence paper-sim",
        "If observation_log.jsonl is empty here, that is expected — ledgers live on the laptop.",
    ]
    missing = [c["name"] for c in checks if not c.get("ok") and c.get("kind") == "code"]
    if missing:
        notes.append("Missing code files: " + ", ".join(missing))
    return notes
