"""I5 human-gated paper TAKE proposal. Always blocked today.

A proposal is not a fill. SUITABLE + vs_sitout edge + user confirm required
before this can even be considered. Wave A stays WATCH.

CLI: lab paper-take
"""
from __future__ import annotations

from typing import Any, Dict, Optional

VERSION = "PAPER-TAKE-v0"
REQUIRED_GATES = (
    "CELL_SUITABLE",
    "VS_SITOUT_TAKE_GT_SITOUT",
    "DQ_NOT_INSUFFICIENT",
    "USER_CONFIRM",
    "ANANTA_HARD_GATES",
    "NOT_WAVE_A_MUTATION",
)


def propose(*, user_confirmed: bool = False, cell: Optional[dict] = None) -> Dict[str, Any]:
    blocked = list(REQUIRED_GATES)
    if not user_confirmed:
        blocked.append("NO_USER_CONFIRM")
    return {
        "ok": False,
        "version": VERSION,
        "placed_order": False,
        "issued_action": "WAIT",
        "phase": "I5_BLOCKED",
        "reason": "I5_NOT_NOW",
        "blocked_by": blocked,
        "user_confirmed": bool(user_confirmed),
        "cell": cell,
        "keep": False,
        "note": "Human-gated paper TAKE is the next *authority* step, not the next code spike. Needs evidence.",
    }


def print_paper_take() -> Dict[str, Any]:
    report = propose(user_confirmed=False)
    print(f"\nPAPER TAKE PROPOSAL  {report['version']}")
    print("=" * 64)
    print("I5 blocked. Proposal ≠ fill. TAKE ≠ KEEP.")
    print(f"  issued={report['issued_action']}  placed_order=False  reason={report['reason']}")
    print("  gates: " + ", ".join(REQUIRED_GATES))
    print("-" * 64)
    print("  Do not manufacture live TAKEs to satisfy this gate. Wave A stays WATCH.")
    print("=" * 64)
    return report
