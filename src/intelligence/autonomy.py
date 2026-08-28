"""I6 earned autonomy. Profiles are parameters, not permission.

CLI: lab autonomy
"""
from __future__ import annotations

from typing import Any, Dict

from src.intelligence.profiles import get_active_profile_name

VERSION = "AUTONOMY-v0"


def snapshot() -> Dict[str, Any]:
    return {
        "ok": True,
        "version": VERSION,
        "phase": "I6_BLOCKED",
        "granted": False,
        "profile": get_active_profile_name(),
        "profile_is_not_authority": True,
        "keep": False,
        "reason": "I6_NOT_NOW",
        "needs": [
            "I5 forward paper TAKEs with DQ beating sit-out",
            "Human confirm path",
            "Ananta hard gates still outside the LLM",
        ],
        "modes": {
            "SAFE": "parameter — not granted",
            "MODERATE": "parameter — not granted",
            "AGGRESSIVE": "parameter — not granted",
        },
    }


def grant(*_a, **_k) -> Dict[str, Any]:
    s = snapshot()
    s["ok"] = False
    s["granted"] = False
    return s


def print_autonomy() -> Dict[str, Any]:
    report = snapshot()
    print(f"\nAUTONOMY  {report['version']}  phase={report['phase']}")
    print("=" * 64)
    print("Not granted. SAFE/MODERATE/AGGRESSIVE are knobs, not keys.")
    print(f"  profile={report['profile']}  granted=False  keep=False")
    print("  Earn I5 first. Wave A stays WATCH.")
    print("=" * 64)
    return report
