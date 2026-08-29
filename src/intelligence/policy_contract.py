"""Decision policy contract — two primaries + veto. Not live Hunter.

Research lock only. Does not rewrite Wave A gates. Does not TAKE.

Primary 1: market state / fingerprint (what environment is this?)
Primary 2: strategy setup + vs_sitout evidence (is this capability plausible?)
Veto:     hard risk / disaster / missing provenance. Can only say NO.

CLI: lab policy
"""
from __future__ import annotations

from typing import Any, Dict, Optional

VERSION = "POLICY-v0"
LIVE_WIRED = False

PRIMARY = (
    {
        "id": "P1_MARKET_STATE",
        "asks": "What environment is this fingerprint?",
        "inputs": ("trend_flag", "compression_flag", "ret_1h_bin", "independent_label"),
        "can_create_take": False,
        "note": "UNKNOWN if key n is sparse. Does not inherit parent WASH.",
    },
    {
        "id": "P2_CAPABILITY_EVIDENCE",
        "asks": "Is a named capability plausible here, vs sit-out?",
        "inputs": ("setup_detected", "board", "n_take", "evidence_depth", "vs_sitout"),
        "can_create_take": False,
        "note": "TAKE only becomes eligible later if vs_sitout is TAKE_GT_SITOUT and depth>=THIN.",
    },
)

VETO = {
    "id": "VETO_ONLY",
    "asks": "Is there a hard reason this must not happen?",
    "inputs": ("ananta_hard_gates", "kill_switch", "catalyst_veto", "missing_provenance"),
    "can_create_take": False,
    "can_only_block": True,
    "note": "News/disaster/liquidity can refuse. They cannot invent a TAKE.",
}


def spec() -> Dict[str, Any]:
    return {
        "ok": True,
        "schema": "decision_policy_v0",
        "version": VERSION,
        "live_wired": LIVE_WIRED,
        "wave_a": "WATCH",
        "keep": False,
        "issued_today": "WAIT_OR_UNKNOWN",
        "primary": list(PRIMARY),
        "veto": dict(VETO),
        "not_this_policy": [
            "Hunter six-gate live rewrite",
            "TREND_UP enable to manufacture TAKEs",
            "LLM headline → BUY",
            "Fair-value number without inputs",
        ],
        "laws": {
            "two_primaries_do_not_equal_take": True,
            "veto_cannot_create_take": True,
            "not_wired_to_live_watcher": True,
            "wave_a_stays_watch": True,
            "policy_version_is_provenance": True,
        },
        "note": (
            "Future I5 paper TAKEs must cite this policy version. "
            "Today the live watcher still uses Wave A gates. Do not mix the two."
        ),
    }


def evaluate_stub(*, fingerprint: Optional[dict] = None, cell: Optional[dict] = None) -> Dict[str, Any]:
    """Always WAIT/UNKNOWN. Exists so tests can prove it cannot TAKE."""
    fp = fingerprint or {}
    key_n = int(fp.get("n") or 0)
    if key_n and key_n < 5:
        action = "UNKNOWN"
        why = "SPARSE_FINGERPRINT_KEY"
    else:
        action = "WAIT"
        why = "POLICY_NOT_LIVE_WIRED"
    return {
        "ok": True,
        "version": VERSION,
        "issued_action": action,
        "why": why,
        "take": False,
        "keep": False,
        "live_wired": False,
        "cell": cell,
        "note": "Stub. Live Wave A policy is unchanged.",
    }


def print_policy() -> Dict[str, Any]:
    report = spec()
    print(f"\nDECISION POLICY  {report['version']}  live_wired={report['live_wired']}")
    print("=" * 64)
    print("Two primaries + veto. Not Hunter rewrite. Not KEEP.")
    print("-" * 64)
    for p in report["primary"]:
        print(f"  {p['id']:<24} {p['asks']}")
    print(f"  {report['veto']['id']:<24} {report['veto']['asks']}  (NO only)")
    print("-" * 64)
    print("  Today issued = WAIT or UNKNOWN. Veto cannot create TAKE.")
    print("  Do not wire this to lab watch 15. Wave A stays WATCH.")
    print("=" * 64)
    print()
    return report
