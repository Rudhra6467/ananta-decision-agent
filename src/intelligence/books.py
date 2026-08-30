"""Named observation books. BTC default. ETH/SOL/AVAX are sibling files."""
from __future__ import annotations

from pathlib import Path
from typing import Dict

from src.tools.observation_log import OBSERVATION_LOG, REPLAY_LOG, replay_path_for

ALIASES: Dict[str, str] = {
    "live": "live",
    "live_paper": "live",
    "replay": "replay",
    "historical": "replay",
    "historical_lab": "replay",
    "btc": "replay",
    "eth": "eth",
    "replay-eth": "eth",
    "sol": "sol",
    "replay-sol": "sol",
    "avax": "avax",
    "replay-avax": "avax",
}


def book(source: str = "replay") -> str:
    return ALIASES.get((source or "replay").lower().strip(), "replay")


def ledger_path(source: str = "replay") -> Path:
    b = book(source)
    if b == "live":
        return OBSERVATION_LOG
    if b == "eth":
        return replay_path_for(symbol="ETH/USD")
    if b == "sol":
        return replay_path_for(symbol="SOL/USD")
    if b == "avax":
        return replay_path_for(symbol="AVAX/USD")
    return REPLAY_LOG


def tag(source: str = "replay") -> str:
    return "live_paper" if book(source) == "live" else "historical_lab"


def artifact(kind: str, source: str = "replay") -> Path:
    b = book(source)
    suffix = "" if b == "replay" else f"_{b}"
    return Path(f"{kind}{suffix}.json")
