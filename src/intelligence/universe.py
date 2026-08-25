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
from src.intelligence.h2 import _codes, _regime
from src.intelligence.universe_specs import generate_cells, catalog
from src.tools.observation_log import REPLAY_LOG, _read_jsonl

VERSION = "UNIVERSE-v1"
LOCKED = "2026-08-25"
KNOWLEDGE_PATH = Path("universe_knowledge.json")


def research() -> Dict[str, Any]:
    cells = generate_cells()
    rows = _read_jsonl(REPLAY_LOG)
    buckets: Dict[str, dict] = {}
    failures: Dict[str, Counter] = {}

    for obs in rows:
        st = obs.get("system_truth") or {}
        ot = obs.get("outcome_truth") or {}
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

    for b in buckets.values():
        _means(b)

    scored: List[dict] = []
    counts = Counter()
    for cell in cells:
        cid = cell["id"]
        bucket = buckets.get(cid)
        entry = _score_cell(cell, bucket, failures.get(cid))
        counts[entry["fit"]] += 1
        scored.append(entry)

    suitable = [c for c in scored if c["fit"] == "SUITABLE"]
    unsuitable = [c for c in scored if c["fit"] == "UNSUITABLE"]
    covered = [c for c in scored if c["coverage"] == "historical_lab"]

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
        "n_unknown": int(counts.get("UNKNOWN") or 0),
        "fit_counts": dict(counts),
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
            "Universe v1. Cells are research, not bots. "
            "SUITABLE still cannot KEEP or enter lab watch. "
            "Uncovered specs stay UNKNOWN until observation_v0 exists."
        ),
    }
    try:
        KNOWLEDGE_PATH.write_text(json.dumps(report, indent=2, default=str))
        report["saved"] = str(KNOWLEDGE_PATH)
    except Exception:
        report["saved"] = None
    return report


def print_universe() -> Dict[str, Any]:
    report = research()
    print(f"\nSTRATEGY RESEARCH UNIVERSE  {report.get('version')}")
    print("=" * 64)
    print("Offline research. Wave A watch FROZEN. keep=False. No live enable.")
    print(
        f"  specs={report.get('n_specs')}  cells={report.get('n_cells')}  "
        f"replay_rows={report.get('n_replay_rows')}  replay_scored={report.get('n_replay_scored')}"
    )
    print(
        f"  SUITABLE={report.get('n_suitable')}  UNSUITABLE={report.get('n_unsuitable')}  "
        f"UNKNOWN={report.get('n_unknown')}"
    )
    print("-" * 64)
    print("  Covered cells (historical_lab BTC/USD 1h) — fit is evidence, not KEEP")
    covered = [c for c in report["cells"] if c["coverage"] == "historical_lab"]
    # Show policy-relevant + any non-UNKNOWN first
    interesting = [c for c in covered if c["policy"] in ("ALLOWED", "ROUTER_ONLY") or c["fit"] != "UNKNOWN"]
    show = interesting or covered
    for c in sorted(show, key=lambda x: (x["strategy"], x["regime"]))[:24]:
        t = c.get("take_1h") or {}
        print(
            f"    {c['strategy']:<14} {c['regime']:<12} policy={c['policy']:<12} "
            f"fit={c['fit']:<11} n_take={c['n_take']:<4} "
            f"+1h={t.get('verdict')} {t.get('mean_pct')}"
        )
    print("-" * 64)
    print("  Uncovered specs (no observation_v0 replay) — catalogued, not running")
    seen = set()
    for c in report["cells"]:
        if c["coverage"] == "NONE" and c["strategy"] not in seen and not c["wave_a"]:
            seen.add(c["strategy"])
            print(f"    {c['strategy']:<22} family={c['family']:<16} fit=UNKNOWN  NO_REPLAY")
    print("-" * 64)
    print("  SUITABLE is not KEEP. SUITABLE is not live watch. Promotion=FORBIDDEN.")
    print(f"  saved: {report.get('saved')}")
    print("=" * 64)
    print()
    return report


def _score_cell(cell: dict, bucket: Optional[dict], fail: Optional[Counter]) -> dict:
    out = dict(cell)
    out["n_rows"] = int((bucket or {}).get("n_rows") or 0)
    out["n_setup"] = int((bucket or {}).get("n_setup") or 0)
    out["n_take"] = int((bucket or {}).get("n_take") or 0)
    out["n_skip_setup"] = int((bucket or {}).get("n_skip_setup") or 0)
    out["n_wait"] = int((bucket or {}).get("n_wait") or 0)
    if cell["coverage"] != "historical_lab":
        out["fit"] = "UNKNOWN"
        out["why"] = "NO_OBSERVATION_REPLAY"
        out["take_1h"] = None
        out["keep"] = False
        return out

    bucket = bucket or _empty_bucket()
    n1, m1 = _h(bucket, "take", "fwd_1h_pct")
    n4, m4 = _h(bucket, "take", "fwd_4h_pct")
    ns, ms = _h(bucket, "skip_setup", "fwd_1h_pct")
    take_1h = score_horizon(role="TAKE", n=n1, mean=m1, clock="+1h")
    take_4h = score_horizon(role="TAKE", n=n4, mean=m4, clock="+4h")
    skip_1h = score_horizon(role="SKIP", n=ns, mean=ms, clock="+1h")
    fit, why = fit_from_take(take_1h)
    out.update(
        {
            "fit": fit,
            "why": why,
            "evidence_depth": take_1h["evidence_depth"],
            "take_1h": take_1h,
            "take_4h": take_4h,
            "skip_setup_1h": skip_1h,
            "failure_top": dict((fail or Counter()).most_common(6)),
            "keep": False,
            "live_enable": False,
        }
    )
    return out


def fit_from_take(take_1h: dict) -> tuple:
    """Evidence fit only. WASH and thin n stay UNKNOWN. Never KEEP."""
    v = take_1h.get("verdict")
    if v in ("INSUFFICIENT_EVIDENCE", "NO_SAMPLE", "UNUSABLE_CLOCK"):
        return "UNKNOWN", v
    if v == "WASH":
        return "UNKNOWN", "WASH"
    if v == "TAKE_HURT":
        return "UNSUITABLE", "TAKE_HURT"
    if v == "TAKE_HELPED":
        return "SUITABLE", "TAKE_HELPED"
    return "UNKNOWN", str(v or "UNKNOWN")


def _h(bucket: dict, kind: str, horizon: str):
    means = bucket.get(f"mean_fwd_after_{kind}") or {}
    ns = bucket.get(f"n_fwd_after_{kind}") or {}
    n = int(ns.get(horizon) or 0)
    m = means.get(horizon)
    try:
        m_f = None if m is None else float(m)
    except (TypeError, ValueError):
        m_f = None
        n = 0
    return n, m_f
