"""Setup Evidence Cards v0 — queryable knowledge, not KEEP.

One card per covered strategy (thesis/ALLOWED cell preferred).
No blended score. UNKNOWN/WASH/INSUFFICIENT_EVIDENCE stay first-class.
CLI: lab cards [strategy]
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.intelligence.definition_cards import card_for
from src.intelligence.evidence_engine import card_from_cell
from src.intelligence.universe import research as universe_research
from src.intelligence.universe_specs import catalog

VERSION = "CARDS-v0"
OUT = Path("evidence_cards.json")
LAWS = {
    "card_is_not_keep": True,
    "suitable_is_not_keep": True,
    "unknown_is_valid": True,
    "no_blended_score": True,
}


def _pick_cell(cells: List[dict], strategy: str) -> Optional[dict]:
    mine = [c for c in cells if c.get("strategy") == strategy and c.get("coverage") == "historical_lab"]
    if not mine:
        return None
    ranked = sorted(
        mine,
        key=lambda c: (
            0 if c.get("policy") in ("ALLOWED", "ROUTER_ONLY", "THESIS_ONLY") else 1,
            -(int(c.get("n_take") or 0)),
            -(int(c.get("n_setup") or 0)),
        ),
    )
    return ranked[0]


def cards(strategy: Optional[str] = None) -> Dict[str, Any]:
    uni = universe_research()
    cells = uni.get("cells") or []
    wanted = [strategy.lower()] if strategy else [
        s["key"] for s in catalog() if s.get("observation_v0_coverage")
    ]
    out_cards: List[dict] = []
    for key in wanted:
        cell = _pick_cell(cells, key)
        spec = next((s for s in catalog() if s["key"] == key), {})
        defn = card_for(key) or {}
        if cell:
            card = card_from_cell(cell)
        else:
            card = {
                "schema": "setup_evidence_card_v0",
                "strategy": key,
                "status_class": "UNTESTED",
                "fit": "UNKNOWN",
                "n_take": 0,
                "keep": False,
                "live_enable": False,
            }
        card["family"] = spec.get("family")
        card["thesis"] = spec.get("thesis")
        card["definition_status"] = defn.get("status")
        card["blocked_by"] = defn.get("blocked_by")
        card["alignment"] = defn.get("alignment")
        card["known_clash"] = defn.get("known_clash")
        card["blended_score"] = None
        card["keep"] = False
        card["live_enable"] = False
        out_cards.append(card)
    report = {
        "ok": True,
        "version": VERSION,
        "keep": False,
        "live_watch_frozen": True,
        "n_cards": len(out_cards),
        "cards": out_cards,
        "laws": LAWS,
        "note": "Cards are cells + definition status. Not KEEP. Not a ranker.",
    }
    try:
        OUT.write_text(json.dumps(report, indent=2, default=str))
        report["saved"] = str(OUT)
    except Exception:
        report["saved"] = None
    return report


def print_cards(strategy: Optional[str] = None) -> Dict[str, Any]:
    report = cards(strategy)
    print(f"\nSTRATEGY EVIDENCE CARDS  {report.get('version')}")
    print("=" * 64)
    print("Queryable knowledge. Not KEEP. Not a ranker. Wave A frozen.")
    print(f"  n={report.get('n_cards')}  keep={report.get('keep')}")
    print("-" * 64)
    for c in report.get("cards") or []:
        take = c.get("take_1h") or {}
        print(
            f"  {c.get('strategy'):<18} family={c.get('family') or '—':<16} "
            f"status={c.get('status_class'):<16} policy={c.get('policy') or '—'}"
        )
        print(
            f"    {'' :<18} take={c.get('n_take')}  depth={c.get('evidence_depth') or 'NONE'}  "
            f"+1h={take.get('verdict') or '—'}  conf={c.get('confidence_band') or '—'}  "
            f"def={c.get('definition_status') or '—'}"
        )
        if c.get("known_clash"):
            k = c["known_clash"]
            print(f"    {'' :<18} clash={k.get('kind')} tape={k.get('tape')}")
        if c.get("alignment"):
            a = c["alignment"]
            print(f"    {'' :<18} aligned={a.get('kind')} take_n={a.get('take_n')}")
        if c.get("blocked_by"):
            print(f"    {'' :<18} blocked={c.get('blocked_by')}")
        print(f"    {'' :<18} KEEP=False  live=False")
    print("-" * 64)
    print("  SUITABLE is not KEEP. UNKNOWN is valid. Card ≠ trade.")
    if report.get("saved"):
        print(f"  saved: {report['saved']}")
    print("=" * 64)
    return report
