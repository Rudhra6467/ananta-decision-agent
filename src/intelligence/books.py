"""Named observation books. BTC 1h default. Siblings never replace it."""
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
    "sol": "sol",
    "avax": "avax",
    "link": "link",
    "xrp": "xrp",
    "btc15s": "btc15s",
    "btc15-smoke": "btc15s",
    "15m-smoke": "btc15s",
}


def book(source: str = "replay") -> str:
    return ALIASES.get((source or "replay").lower().strip(), "replay")


def ledger_path(source: str = "replay") -> Path:
    b = book(source)
    if b == "live":
        return OBSERVATION_LOG
    mapping = {
        "eth": "ETH/USD",
        "sol": "SOL/USD",
        "avax": "AVAX/USD",
        "link": "LINK/USD",
        "xrp": "XRP/USD",
    }
    if b in mapping:
        return replay_path_for(symbol=mapping[b])
    if b == "btc15s":
        return Path("observation_replay_smoke_15m.jsonl")
    return REPLAY_LOG


def tag(source: str = "replay") -> str:
    return "live_paper" if book(source) == "live" else "historical_lab"


def artifact(kind: str, source: str = "replay") -> Path:
    b = book(source)
    suffix = "" if b == "replay" else f"_{b}"
    return Path(f"{kind}{suffix}.json")
