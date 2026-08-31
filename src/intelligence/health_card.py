"""Read latest health_sweep Donchian card. Stock defaults only."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.intelligence.cfg_contract import empty_row, may_ingest
from src.intelligence.donchian_keys import STOCK
from src.tools.ananta_api import get_lab_run, list_lab_runs

VERSION = "HEALTH-CARD-v0"


def _runs(data: Any) -> List[dict]:
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for k in ("runs", "items", "data"):
            v = data.get(k)
            if isinstance(v, list):
                return [x for x in v if isinstance(x, dict)]
    return []


def _donchian_card(result: dict) -> Optional[dict]:
    for s in result.get("strategies") or []:
        if not isinstance(s, dict):
            continue
        key = str(s.get("strategy") or s.get("key") or "").lower()
        if key in ("donchian-breakout", "donchian"):
            return s
    return None


def print_health_card() -> Dict[str, Any]:
    listed = list_lab_runs(limit=8)
    runs = _runs(listed.get("data"))
    sweep = next((r for r in runs if r.get("kind") == "health_sweep" and r.get("id")), None)
    card = None
    run_id = sweep.get("id") if sweep else None
    if run_id:
        got = get_lab_run(run_id)
        body = got.get("data") if got.get("success") else {}
        result = (body or {}).get("result") if isinstance(body, dict) else {}
        card = _donchian_card(result or {})
    row = empty_row(
        exp_id="EXP-001-STOCK",
        strategy_family="donchian-breakout",
        strategy_version="declarative-v1-stock",
        config_id=STOCK["config_id"],
        entry_parameters={"dc_entry": STOCK["dc_entry"]},
        exit_parameters={"dc_exit": STOCK["dc_exit"]},
        source="ananta.lab.health_sweep",
        lab_run_id=run_id,
        parameter_honored=True,  # defaults, not a swept variant
        n=(card or {}).get("trades") or (card or {}).get("n"),
        win_rate=(card or {}).get("win_rate_pct") or (card or {}).get("win_rate"),
    )
    # Still refuse full ingest: most REQUIRED metrics absent from a sweep card.
    gate = may_ingest(row)
    print(f"\nHEALTH CARD  {VERSION}")
    print("=" * 64)
    print("Stock Donchian only. Not dc_entry sweep. Not KEEP.")
    print(f"  run={run_id}")
    print(f"  card_keys={list(card)[:16] if card else None}")
    print(f"  win_rate_field={row.get('win_rate')} n={row.get('n')}")
    print(f"  ingest={gate['ingest']} reasons={gate['reasons']}")
    print("  variants remain PENDING until decl:dc_entry is a lab.optimize key")
    print("=" * 64)
    print()
    return {"ok": True, "version": VERSION, "run_id": run_id, "card": card,
            "row": row, "gate": gate, "keep": False}
