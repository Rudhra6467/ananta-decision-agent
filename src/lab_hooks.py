"""Small lab command hooks. Wave A watch untouched."""
from __future__ import annotations


def run_hook(rest: str) -> bool:
    r = (rest or "").strip().lower()
    table = {
        "coverage": ("src.tools.coverage_client", None),
        "tracks": ("src.intelligence.tracks", "print_tracks"),
        "pipeline": ("src.intelligence.research_pipeline", "print_pipeline"),
        "grid": ("src.intelligence.knowledge_grid", "print_grid"),
        "t4": ("src.intelligence.t4_contracts", "print_t4"),
        "findings": ("src.intelligence.findings", "print_findings"),
        "research": ("src.intelligence.research_exp", "print_research"),
        "episodes": ("src.intelligence.episode_tag", "print_episodes"),
        "slice": ("src.intelligence.episode_slice", "print_slice"),
        "phase": ("src.intelligence.phase_board", "print_board"),
        "phase-board": ("src.intelligence.phase_board", "print_board"),
        "stress": ("src.intelligence.stress_window", "print_window"),
        "objects": ("src.intelligence.lab_objects", "print_objects"),
        "roadmap": ("src.intelligence.roadmap_now", "print_roadmap"),
        "years": ("src.intelligence.years_probe", "print_years"),
    }
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
    key = r.split()[0] if r else ""
    if key in table:
        mod, fn = table[key]
        if fn:
            import importlib
            m = importlib.import_module(mod)
            getattr(m, fn)()
            return True
    if r in ("universe eth", "universe replay-eth", "sru eth"):
        from src.intelligence.universe_book import print_universe_book
        print_universe_book("eth")
        return True
    if r in ("universe sol", "universe replay-sol", "sru sol"):
        from src.intelligence.universe_book import print_universe_book
        print_universe_book("sol")
        return True
    if r in ("universe btc", "universe replay"):
        from src.intelligence.universe import print_universe
        print_universe()
        return True
    return False
