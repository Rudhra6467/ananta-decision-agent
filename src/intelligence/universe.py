"""Strategy Research Universe v1 — offline research track.

Generate strategy × asset × timeframe × regime cells from specs.
Score covered cells against observation_replay.jsonl through DQ-v0.
Does not touch lab watch. Does not KEEP. Does not enable.

CLI: lab universe
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.intelligence.attribution import _accumulate, _empty_bucket, _means
from src.intelligence.decision_quality import score_horizon
from src.intelligence.evidence_engine import (
    card_from_cell,
    completeness,
    confidence_band,
    coverage_band,
    provenance,
    status_class,
)
from src.intelligence.fingerprint import from_slot
from src.intelligence.h2 import _codes, _regime
from src.intelligence.definition_cards import cards as definition_cards, print_definitions
from src.intelligence.universe_specs import generate_cells, catalog, ROUTER_REGIMES
from src.tools.observation_log import REPLAY_LOG, _read_jsonl

VERSION = "UNIVERSE-v1.4"
LOCKED = "2026-08-25"
KNOWLEDGE_PATH = Path("universe_knowledge.json")
