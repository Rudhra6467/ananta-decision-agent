"""Paper-book settings (india/paper_config.json): sizing, caps and universe limits, versioned with git and hashed into every decision.

  from india import settings
  cfg = settings.load(); settings.sha()
  settings.size(cfg, entry, risk_frac) -> (qty, notional)
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

PATH = Path(__file__).with_name("paper_config.json")
MODES = ("fixed_notional", "fixed_risk")


def load() -> dict:
    cfg = json.loads(PATH.read_text())
    if cfg["stock"]["sizing"] not in MODES:
        raise ValueError(f"stock.sizing must be one of {MODES}")
    return cfg


def sha() -> str:
    return hashlib.sha256(PATH.read_bytes()).hexdigest()[:16]


def size(cfg: dict, entry: float, risk_frac: float) -> tuple[float, float]:
    """Quantity and rupee notional for one stock trade. Fractional quantity is kept on purpose: the book studies behaviour, not lot rounding."""
    s = cfg["stock"]
    if s["sizing"] == "fixed_notional":
        notional = float(s["notional_inr"])
    else:
        notional = float(s["risk_inr"]) / risk_frac
    return notional / entry, notional
