"""Print + save fingerprints for a named book without clobbering BTC."""
from __future__ import annotations

import json
from typing import Any, Dict, Optional

from src.intelligence.books import artifact, book, ledger_path
from src.intelligence.fingerprint import fingerprints


def print_fp(source: str = "replay", strategy: Optional[str] = None) -> Dict[str, Any]:
    report = fingerprints(source)
    dest = artifact("fingerprint_report", source)
    slim = {k: v for k, v in report.items() if k != "saved"}
    slim["book"] = str(ledger_path(source))
    slim["book_name"] = book(source)
    try:
        dest.write_text(json.dumps(slim, indent=2, default=str))
        report["saved"] = str(dest)
    except Exception:
        report["saved"] = None
    from src.intelligence.fingerprint import print_fingerprints as _legacy
    # legacy print still writes fingerprint_report.json — restore BTC default after ETH
    printed = report
    want = (strategy or "").lower().strip() or None
    print(f"\nMARKET TRUTH FINGERPRINTS  {report.get('version')}  book={book(source)}")
    print("=" * 64)
    print(f"  file={ledger_path(source)}  saved={report.get('saved')}  keep=False")
    print(f"  setups={report.get('n_setups')}  data_gap={report.get('n_data_gap')}")
    print("-" * 64)
    slices = report.get("by_strategy") or {}
    shown = 0
    for key, sl in slices.items():
        if want and key != want:
            continue
        shown += 1
        print(
            f"  {key:<14} n={sl.get('n')} TAKE={sl.get('TAKE')} "
            f"COSTLY={sl.get('COSTLY')} PROT={sl.get('PROTECTIVE')} WASH={sl.get('WASH')}"
        )
    if shown == 0:
        print("  no slices")
    print("-" * 64)
    print("  Book save is separate. SUITABLE/KEEP still false.")
    print("=" * 64)
    print()
    if book(source) != "replay":
        print("NOTE: fingerprints() also wrote fingerprint_report.json.")
        print("Restore BTC with: print_fingerprints('replay')")
    return report
