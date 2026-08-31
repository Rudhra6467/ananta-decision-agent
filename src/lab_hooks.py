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
    if r in ("tracks", "track", "four-tracks"):
        from src.intelligence.tracks import print_tracks
        print_tracks()
        return True
    if r in ("pipeline", "pipe"):
        from src.intelligence.research_pipeline import print_pipeline
        print_pipeline()
        return True
    if r in ("grid", "knowledge-grid", "knowledge grid"):
        from src.intelligence.knowledge_grid import print_grid
        print_grid()
        return True
    if r in ("t4", "scanner-contract", "fv-contract"):
        from src.intelligence.t4_contracts import print_t4
        print_t4()
        return True
    if r in ("findings",):
        from src.intelligence.findings import print_findings
        print_findings()
        return True
    if r in ("research", "exp", "experiments-ledger"):
        from src.intelligence.research_exp import print_research
        print_research()
        return True
    if r in ("episodes", "episode", "episode-tag"):
        from src.intelligence.episode_tag import print_episodes
        print_episodes()
        return True
    if r in ("slice", "episode-slice"):
        from src.intelligence.episode_slice import print_slice
        print_slice()
        return True
    if r in ("stress", "stress-window"):
        from src.intelligence.stress_window import print_window
        print_window()
        return True
    if r in ("objects", "lab-objects"):
        from src.intelligence.lab_objects import print_objects
        print_objects()
        return True
    if r in ("universe eth", "universe replay-eth", "sru eth"):
        from src.intelligence.universe_book import print_universe_book
        print_universe_book("eth")
        return True
    if r in ("universe sol", "universe replay-sol", "sru sol"):
        from src.intelligence.universe_book import print_universe_book
        print_universe_book("sol")
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
