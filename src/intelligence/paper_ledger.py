"""Paper portfolio ledger. Closed until G8 grant. $100 allocation is not $100 risk."""
from __future__ import annotations

from typing import Any, Dict

SPEC: Dict[str, Any] = {
    "starting": 1000.0,
    "max_notional": 100.0,
    "risk": "stop_distance_of_selected_variant",
    "credentials": "none",
    "paper_take": True,
    "exec": False,
}

def empty_book() -> Dict[str, Any]:
    return {
        "id": "paper.ledger.v1",
        "status": "OPEN_BOUNDED",
        "cash": 1000.0,
        "reserved_capital": 0.0,
        "open_positions": [],
        "realized_pnl": 0.0,
        "unrealized_pnl": 0.0,
        "fees": 0.0,
        "slippage": 0.0,
        "exposure": 0.0,
        "drawdown": 0.0,
        "trade_count": 0,
        "wins": 0,
        "losses": 0,
        "mfe": None,
        "mae": None,
        "duration": None,
        "exit_reason": None,
        "paper_take": True,
        "keep": False,
        "exec": False,
        "counts_for_m2": False,
        "spec": SPEC,
        "last_refuse": None,
        "grant": "g8.paper.authority.grant.v1",
    }

def refuse_fill(reason: str = "PAPER_GATE_CLOSED") -> dict[str, Any]:
    book = empty_book()
    book["last_refuse"] = reason
    return book
