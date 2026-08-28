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

VERSION = "CARDS-v0.1"
OUT = Path("evidence_cards.json")
LAWS = {
    "card_is_not_keep": True,
    "suitable_is_not_keep": True,
    "unknown_is_valid": True,
    "no_blended_score": True,
    "computed_tape_beats_stale_stamp": True,
    "clash_is_not_a_rewrite": True,
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
        n_take = int(card.get("n_take") or 0)
        n_setup = int(card.get("n_setup") or 0)
        status = defn.get("status")
        if n_take > 0:
            status = "HIST_SCORED"
        elif n_setup > 0 and not status:
            status = "HIST_SHADOW"
        card["definition_status"] = status
        card["blocked_by"] = None if (n_take > 0 or n_setup > 0) else defn.get("blocked_by")
        tape = (uni.get("strategy_vs_tape") or {}).get(key) or {}
        card["tape"] = {
            "gate": tape.get("gate"),
            "gate_source": tape.get("gate_source"),
            "clash": tape.get("clash"),
            "clash_kind": tape.get("clash_kind"),
            "independent_trend": tape.get("independent_trend"),
            "aligned": tape.get("aligned"),
            "n": tape.get("n_setup_tape"),
            "keep": False,
            "rewrite": False,
        }
        if tape.get("clash"):
            card["known_clash"] = {
                "kind": tape.get("clash_kind"),
                "tape": tape.get("independent_trend"),
                "take_n": n_take,
            }
            card["alignment"] = None
        elif tape.get("gate") and tape.get("n_setup_tape"):
            card["known_clash"] = None
            card["alignment"] = {
                "kind": f"{tape.get('gate')}_VS_INDEPENDENT",
                "tape": tape.get("independent_trend"),
                "take_n": n_take,
                "aligned": tape.get("aligned"),
            }
        else:
            card["alignment"] = None if tape.get("n_setup_tape") else defn.get("alignment")
            card["known_clash"] = None if tape.get("n_setup_tape") else defn.get("known_clash")
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
        "note": "Cards join universe cells + computed SMA-20 tape. Stale PENDING_REPLAY is cleared when n>0. Not KEEP.",
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
        tape = c.get("tape") or {}
        if tape.get("n"):
            print(
                f"    {'' :<18} gate={tape.get('gate') or '—'} src={tape.get('gate_source') or '—'} "
                f"clash={tape.get('clash')} aligned={tape.get('aligned')}/{tape.get('n')} "
                f"tape={tape.get('independent_trend')}"
            )
        if c.get("known_clash"):
            k = c["known_clash"]
            print(f"    {'' :<18} clash={k.get('kind')} tape={k.get('tape')}")
        elif c.get("alignment"):
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
