"""Small lab command hooks. Wave A watch untouched."""
from __future__ import annotations


def run_hook(rest: str) -> bool:
    r = (rest or "").strip().lower()
    if r in ("coverage", "cover"):
        from src.tools.coverage_client import get_lab_coverage_long
        cov = get_lab_coverage_long()
        if not cov.get("success"):
            print(f"Coverage failed: {cov.get('error') or cov}")
            return True
        data = cov.get("data") or {}
        rows = data.get("symbols") or []
        print("\nLAB CANDLE COVERAGE (timeout=120)")
        print("-" * 72)
        usable_n = 0
        for row in rows:
            n = row.get("bars_1h") or 0
            usable = row.get("usable_1y")
            if usable:
                usable_n += 1
            flag = "OK_1Y" if usable else "SHORT"
            print(
                f"  {str(row.get('symbol')):<12} 1h={n:<6} span={row.get('span_days')}d  "
                f"{row.get('from') or '—'} → {row.get('to') or '—'}  {flag}"
            )
        print("-" * 72)
        print(f"  usable_1y: {usable_n}/{len(rows)}")
        print()
        return True
    if r in ("universe eth", "universe replay-eth", "sru eth"):
        from src.intelligence.universe_book import print_universe_book
        print_universe_book("eth")
        return True
    if r in ("fingerprints eth", "fp eth", "fingerprint eth"):
        from src.intelligence.fp_save import print_fp_book
        print_fp_book("eth")
        print("Re-run fingerprints replay after this if fingerprint_report.json must stay BTC.")
        return True
    if r in ("universe btc", "universe replay"):
        from src.intelligence.universe import print_universe
        print_universe()
        return True
    return False
