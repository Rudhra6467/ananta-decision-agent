"""Named fair-value interface. Methods are enumerated. Numbers are not invented.

ALLOWED methods may exist as names before they exist as estimators.
execute=False. llm=False. Not KEEP.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

VERSION = "FV-IFACE-v0"

ALLOWED = {
    "sma20_close": "PENDING_IMPLEMENTATION — needs PIT SMA-20 from Ananta candles",
    "vwap_session": "PENDING_IMPLEMENTATION — needs session VWAP as-of ts",
    "not_wired": "Interface only. No estimate.",
}

BANNED = ("llm", "grok", "invented", "gut", "target")


def estimate(
    *,
    asset: str,
    method: str,
    observed_price: Optional[float] = None,
    asof: Optional[str] = None,
) -> Dict[str, Any]:
    m = (method or "").lower().strip()
    if m in BANNED:
        return {
            "ok": False,
            "reason": "LLM_INVENTED_PRICE",
            "method": m,
            "execute": False,
            "keep": False,
        }
    if m not in ALLOWED:
        return {
            "ok": False,
            "reason": "UNKNOWN_METHOD",
            "method": m,
            "allowed": list(ALLOWED),
            "execute": False,
            "keep": False,
        }
    return {
        "ok": False,
        "reason": ALLOWED[m],
        "status": "PENDING_IMPLEMENTATION" if m != "not_wired" else "INTERFACE_ONLY",
        "version": VERSION,
        "ts": datetime.now(timezone.utc).isoformat(),
        "asset": asset,
        "method": m,
        "observed_price": observed_price,
        "asof": asof,
        "estimate": None,
        "distance_pct": None,
        "uncertainty": None,
        "execute": False,
        "keep": False,
        "note": "A named method is not a price. Wire candles before numbers.",
    }


def print_fv() -> Dict[str, Any]:
    print(f"\nFV INTERFACE  {VERSION}")
    print("=" * 64)
    print("Named methods. No number until implemented. execute=False.")
    print("-" * 64)
    for name, why in ALLOWED.items():
        print(f"  {name:<16} {why}")
    print("-" * 64)
    demo = estimate(asset="BTC/USD", method="sma20_close", observed_price=78000)
    print(f"  demo sma20_close: ok={demo['ok']} status={demo.get('status')} estimate={demo.get('estimate')}")
    bad = estimate(asset="BTC/USD", method="llm", observed_price=78000)
    print(f"  demo llm:         ok={bad['ok']} reason={bad.get('reason')}")
    print("=" * 64)
    print()
    return {"ok": True, "version": VERSION, "allowed": list(ALLOWED), "keep": False, "execute": False}
