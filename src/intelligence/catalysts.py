"""I3 catalyst / news interface. Not a feed. Not a trade.

Required fields exist so a future ingest cannot be an LLM headline → BUY.
CLI: lab catalysts
"""
from __future__ import annotations

from typing import Any, Dict, Optional

VERSION = "CATALYST-v0"
REQUIRED = (
    "source",
    "ts",
    "asset",
    "headline",
    "polarity",
    "provenance",
    "uncertainty",
)


def spec() -> Dict[str, Any]:
    return {
        "ok": True,
        "version": VERSION,
        "status": "INTERFACE",
        "live": False,
        "required_fields": list(REQUIRED),
        "keep": False,
        "note": "News is an input to DI. Not a strategy. Not execution.",
    }


def refuse_ingest(*, payload: Optional[dict] = None) -> Dict[str, Any]:
    return {
        "ok": False,
        "ingested": False,
        "reason": "I3_NOT_NOW",
        "missing": [f for f in REQUIRED if not (payload or {}).get(f)],
        "keep": False,
        "llm_headline_is_not_a_trade": True,
    }


def print_catalysts() -> Dict[str, Any]:
    report = spec()
    print(f"\nCATALYSTS  {report['version']}  status={report['status']}")
    print("=" * 64)
    print("Interface only. Required: " + ", ".join(REQUIRED))
    print("  Headline ≠ TAKE. Polarity ≠ KEEP. Wave A stays WATCH.")
    print("=" * 64)
    return report
