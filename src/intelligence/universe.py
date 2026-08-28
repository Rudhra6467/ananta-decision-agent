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


def research() -> Dict[str, Any]:
    cells = generate_cells()
    rows = _read_jsonl(REPLAY_LOG)
    buckets: Dict[str, dict] = {}
    failures: Dict[str, Counter] = {}
    periods: Dict[str, dict] = {}
    tapes: Dict[str, Counter] = {}
    strat_tapes: Dict[str, Counter] = {}

    for obs in rows:
        st = obs.get("system_truth") or {}
        ot = obs.get("outcome_truth") or {}
        mt = obs.get("market_truth") or {}
        ts = str(obs.get("ts") or st.get("ts") or "")
        tf = "1h"
        for o in st.get("strategy_observations") or []:
            key = (o.get("strategy") or "").lower()
            asset = o.get("symbol") or "BTC/USD"
            regime = _regime(o, st)
            cid = f"{key}|{asset}|{tf}|{regime}"
            b = buckets.setdefault(cid, _empty_bucket())
            _accumulate(b, o, ot)
            fc = failures.setdefault(cid, Counter())
            for c in _codes(o):
                if c != "UNCODED":
                    fc[c] += 1
            if ts:
                p = periods.setdefault(cid, {"min_ts": ts, "max_ts": ts, "n_rows": 0})
                p["n_rows"] += 1
                if ts < p["min_ts"]:
                    p["min_ts"] = ts
                if ts > p["max_ts"]:
                    p["max_ts"] = ts
            if o.get("setup_detected"):
                assets = (mt.get("assets") or {}) if isinstance(mt, dict) else {}
                slot = assets.get(asset) if isinstance(assets, dict) else None
                if not slot:
                    if "ETH" in str(asset):
                        slot = mt.get("eth") if isinstance(mt, dict) else None
                    else:
                        slot = mt.get("btc") if isinstance(mt, dict) else None
                fp = from_slot(slot if isinstance(slot, dict) else {})
                trend = str(fp.get("trend") or "UNKNOWN")
                tapes.setdefault(cid, Counter())[trend] += 1
                strat_tapes.setdefault(key, Counter())[trend] += 1

    for b in buckets.values():
        _means(b)

    scored: List[dict] = []
    fit_counts = Counter()
    status_counts = Counter()
    for cell in cells:
        cid = cell["id"]
        bucket = buckets.get(cid)
        entry = _score_cell(cell, bucket, failures.get(cid), periods.get(cid), tapes.get(cid))
        fit_counts[entry["fit"]] += 1
        status_counts[entry["status_class"]] += 1
        scored.append(entry)

    suitable = [c for c in scored if c["fit"] == "SUITABLE"]
    unsuitable = [c for c in scored if c["fit"] == "UNSUITABLE"]
    covered = [c for c in scored if c["coverage"] == "historical_lab"]
    cards = [card_from_cell(c) for c in covered if c.get("policy") == "ALLOWED"]

    report = {
        "ok": True,
        "schema": "strategy_knowledge_v0",
        "version": VERSION,
        "locked": LOCKED,
        "ts": datetime.now(timezone.utc).isoformat(),
        "keep": False,
        "wave_a": "WATCH",
        "live_watch_frozen": True,
        "promotion": "FORBIDDEN",
        "n_specs": len(catalog()),
        "n_cells": len(scored),
        "n_replay_rows": len(rows),
        "n_replay_scored": len(covered),
        "n_suitable": len(suitable),
        "n_unsuitable": len(unsuitable),
        "n_unknown": int(fit_counts.get("UNKNOWN") or 0),
        "fit_counts": dict(fit_counts),
        "status_counts": dict(status_counts),
        "strategy_vs_tape": {
            k: _gate_vs_tape(k, v) for k, v in strat_tapes.items()
        },
        "definition_cards": definition_cards(),
        "i2_family": "donchian-breakout",
        "i2_family_live": False,
        "allowed_cards": cards,
        "laws": {
            "offline_research_only": True,
            "suitable_is_not_keep": True,
            "suitable_is_not_live": True,
            "no_watch_contamination": True,
            "no_hunter_rewrite": True,
            "no_trend_up_enable": True,
            "no_auto_promotion": True,
            "dna_is_not_evidence": True,
            "wave_a_is_baseline_not_library": True,
            "untested_is_not_tested_unknown": True,
            "wash_is_not_unsuitable": True,
            "no_blended_dq_score": True,
            "evidence_without_provenance_is_a_speech": True,
            "ananta_regime_is_not_market_truth": True,
            "regime_clash_is_not_a_rewrite": True,
        },
        "specs": catalog(),
        "cells": scored,
        "candidates": [
            {
                "id": c["id"],
                "fit": c["fit"],
                "why": c["why"],
                "n_take": c["n_take"],
                "note": "Candidate for later human-gated paper — not live, not KEEP.",
            }
            for c in suitable
        ],
        "note": (
            "Universe v1.4. Continuation classifiers named. "
            "Donchian is I2 spec-only (no replay, not live). Clash ≠ rewrite."
        ),
    }
    try:
        KNOWLEDGE_PATH.write_text(json.dumps(report, indent=2, default=str))
        report["saved"] = str(KNOWLEDGE_PATH)
    except Exception:
        report["saved"] = None
    return report
