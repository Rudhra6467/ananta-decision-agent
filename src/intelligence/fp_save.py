"""Save fingerprint reports per book so ETH cannot clobber BTC."""
from __future__ import annotations

import json
from typing import Any, Dict

from src.intelligence.books import artifact
from src.intelligence.fingerprint import fingerprints, print_fingerprints


def print_fp_book(source: str = "replay") -> Dict[str, Any]:
    report = fingerprints(source)
    dest = artifact("fingerprint_report", source)
    try:
        slim = {k: v for k, v in report.items() if k != "saved"}
        dest.write_text(json.dumps(slim, indent=2, default=str))
        report["saved"] = str(dest)
    except Exception:
        pass
    printed = print_fingerprints(source)
    printed["saved_book"] = str(dest)
    print(f"  book file: {dest}")
    return printed
