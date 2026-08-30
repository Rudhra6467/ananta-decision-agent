"""T4 Opportunity Intelligence — contracts only.

Scanner says: something interesting is happening.
Fair value says: price vs estimate + uncertainty.
Neither says BUY. Neither runs on lab watch 15.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

VERSION = "T4-CONTRACT-v0"

SCANNER_FIELDS = (
    "ts", "asset", "timeframe",
    "fingerprint",          # trend|compression|ret1h|label
    "why_interesting",      # regime_shift | expansion | compression | unusual_return | structure
    "evidence_refs",        # grid cell ids, memory book names
    "not_a_trade",          # always True in v0
)

FV_FIELDS = (
    "ts", "asset", "timeframe",
    "observed_price",
    "estimate",             # model output, not LLM invented level
    "method",               # named, versioned estimator — not "grok thinks"
    "distance_pct",
    "uncertainty",          # band / sample / regime sensitivity
    "inputs_asof",          # PIT only
    "not_a_trade",          # always True in v0
)

REFUSE = {
    "live_scan": False,
    "execute": False,
    "llm_invented_price": False,
    "wire_to_lab_watch": False,
    "create_take": False,
    "keep": False,
}


def candidate(*, asset: str, timeframe: str = "1h", fingerprint: str = "",
              why: str = "", price: Optional[float] = None) -> Dict[str, Any]:
    if not asset or not why:
        return {"ok": False, "reason": "INCOMPLETE_CANDIDATE", "keep": False, **REFUSE}
    return {
        "ok": True,
        "kind": "scanner_candidate",
        "version": VERSION,
        "ts": datetime.now(timezone.utc).isoformat(),
        "asset": asset,
        "timeframe": timeframe,
        "fingerprint": fingerprint,
        "why_interesting": why,
        "observed_price": price,
        "not_a_trade": True,
        "issued": "UNKNOWN",
        **REFUSE,
        "next": "consult knowledge_grid.json — do not TAKE",
    }


def fair_value(*, asset: str, observed_price: Optional[float], estimate: Optional[float],
               method: str, uncertainty: Optional[float] = None) -> Dict[str, Any]:
    if method.lower() in ("llm", "grok", "invented", "gut"):
        return {"ok": False, "reason": "LLM_INVENTED_PRICE", "keep": False, **REFUSE}
    if observed_price is None or estimate is None:
        return {"ok": False, "reason": "INCOMPLETE_FV", "keep": False, **REFUSE}
    dist = None
    try:
        if float(estimate) != 0:
            dist = round((float(observed_price) - float(estimate)) / float(estimate) * 100.0, 4)
    except (TypeError, ValueError):
        return {"ok": False, "reason": "BAD_FV_NUMBERS", "keep": False, **REFUSE}
    return {
        "ok": True,
        "kind": "fair_value_note",
        "version": VERSION,
        "asset": asset,
        "observed_price": observed_price,
        "estimate": estimate,
        "method": method,
        "distance_pct": dist,
        "uncertainty": uncertainty,
        "not_a_trade": True,
        "issued": "UNKNOWN",
        **REFUSE,
        "next": "input to DI, not an order",
    }


def spec() -> Dict[str, Any]:
    return {
        "ok": True,
        "version": VERSION,
        "phase": "I3_INTERFACE / T4_DESIGN",
        "scanner_fields": list(SCANNER_FIELDS),
        "fv_fields": list(FV_FIELDS),
        "refuse": dict(REFUSE),
        "loop": [
            "live market",
            "scanner candidate (interesting, not buy)",
            "market state",
            "fair value note (distance + uncertainty)",
            "knowledge grid",
            "P1 + P2 + veto",
            "TAKE/WAIT/SKIP/UNKNOWN",
            "Ananta hard gates",
            "execution only after I5 earns it",
        ],
        "keep": False,
    }


def print_t4() -> Dict[str, Any]:
    r = spec()
    print(f"\nT4 CONTRACTS  {r['version']}")
    print("=" * 64)
    print("Design only. Not a scanner. Not mispricing execution. Not KEEP.")
    print(f"  live_scan={r['refuse']['live_scan']}  execute={r['refuse']['execute']}  llm_price={r['refuse']['llm_invented_price']}")
    print("-" * 64)
    print("  SCANNER FIELDS: " + ", ".join(r["scanner_fields"]))
    print("  FV FIELDS:      " + ", ".join(r["fv_fields"]))
    print("-" * 64)
    print("  Scanner → something interesting.")
    print("  FV → distance from a named estimate + uncertainty.")
    print("  Grid → which cells looked like this and what +1h did.")
    print("  DI → WAIT/UNKNOWN until I5.")
    print("=" * 64)
    print()
    # refuse demos
    bad = fair_value(asset="BTC/USD", observed_price=78000, estimate=90000, method="llm")
    print(f"  demo refuse LLM FV: ok={bad.get('ok')} reason={bad.get('reason')}")
    print()
    return r
