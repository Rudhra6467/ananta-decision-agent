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
from src.intelligence.universe_specs import generate_cells, catalog, ROUTER_REGIMES
from src.tools.observation_log import REPLAY_LOG, _read_jsonl

VERSION = "UNIVERSE-v1.3.1"
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
            "Universe v1.3. Ananta TREND_UP vs independent SMA is stamped. "
            "Clash is a finding, not a continuation rewrite. SUITABLE still cannot KEEP."
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
    print(f"  status: {report.get('status_counts')}")
    print("-" * 64)
    print("  Covered cells — UNTESTED vs TESTED_UNKNOWN vs WASH. Not KEEP.")
    covered = [c for c in report["cells"] if c["coverage"] == "historical_lab"]
    for c in sorted(covered, key=lambda x: (x["strategy"], x["regime"])):
        t = c.get("take_1h") or {}
        print(
            f"    {c['strategy']:<14} {c['regime']:<12} {c['policy']:<12} "
            f"{c['status_class']:<16} n={c['n_rows']:<5} take={c['n_take']:<4} "
            f"depth={c.get('evidence_depth') or 'NONE':<10} "
            f"comp={c.get('outcome_completeness_1h')} "
            f"conf={c.get('confidence_band'):<9} "
            f"+1h={t.get('verdict')}"
        )
    print("-" * 64)
    print("  REGIME vs TAPE  (Ananta hypothesis vs independent SMA). Clash ≠ rewrite.")
    print("  Strategy = all setups vs DNA/router gate. Cell = that regime only.")
    strat_tape = report.get("strategy_vs_tape") or {}
    if not strat_tape:
        print("    no setup tape (replay empty here).")
    for key in sorted(strat_tape):
        tv = strat_tape[key]
        print(
            f"    {key:<14} gate={tv.get('gate') or '—':<12} "
            f"clash={tv.get('clash')}  {tv.get('clash_kind') or ''}  "
            f"tape={tv.get('independent_trend')}  "
            f"aligned={tv.get('aligned')}/{tv.get('n_setup_tape')}"
        )
    cell_clashes = [
        c for c in covered
        if (c.get("regime_vs_tape") or {}).get("clash")
    ]
    for c in sorted(cell_clashes, key=lambda x: (x["strategy"], x["regime"])):
        tv = c.get("regime_vs_tape") or {}
        print(
            f"    cell {c['strategy']:<14} {c['regime']:<12} "
            f"{tv.get('clash_kind')}  tape={tv.get('independent_trend')}  "
            f"aligned={tv.get('aligned')}/{tv.get('n_setup_tape')}"
        )
    print("-" * 64)
    print("  Uncovered specs (no observation_v0 on any cell) — catalogued, not running")
    seen = set()
    covered_keys = {c["strategy"] for c in report["cells"] if c["coverage"] == "historical_lab"}
    for c in report["cells"]:
        if c["strategy"] in seen or c["wave_a"] or c["strategy"] in covered_keys:
            continue
        seen.add(c["strategy"])
        print(f"    {c['strategy']:<22} family={c['family']:<16} fit=UNKNOWN  NO_REPLAY")
    print("-" * 64)
    print("  SUITABLE is not KEEP. WASH is not UNSUITABLE. UNTESTED is not TESTED_UNKNOWN.")
    print("  provenance=evidence_provenance_v0 on every cell (source/version/period/policy).")
    print(f"  saved: {report.get('saved')}")
    print("=" * 64)
    print()
    return report


def _score_cell(
    cell: dict,
    bucket: Optional[dict],
    fail: Optional[Counter],
    period: Optional[dict] = None,
    tape: Optional[Counter] = None,
) -> dict:
    out = dict(cell)
    out["n_rows"] = int((bucket or {}).get("n_rows") or 0)
    out["n_setup"] = int((bucket or {}).get("n_setup") or 0)
    out["n_take"] = int((bucket or {}).get("n_take") or 0)
    out["n_skip_setup"] = int((bucket or {}).get("n_skip_setup") or 0)
    out["n_wait"] = int((bucket or {}).get("n_wait") or 0)
    tested = cell["coverage"] == "historical_lab"
    if not tested:
        out.update(_depth_fields(tested=False, fit="UNKNOWN", why="NO_OBSERVATION_REPLAY", n_rows=0, n_take=0, n_fwd=0, depth="NONE"))
        out["take_1h"] = None
        out["keep"] = False
        out["provenance"] = _prov(cell, period)
        out["regime_vs_tape"] = _regime_vs_tape(str(cell.get("regime") or ""), tape)
        return out

    bucket = bucket or _empty_bucket()
    n1, m1 = _h(bucket, "take", "fwd_1h_pct")
    n4, m4 = _h(bucket, "take", "fwd_4h_pct")
    ns, ms = _h(bucket, "skip_setup", "fwd_1h_pct")
    n_fwd = int((bucket.get("n_fwd") or {}).get("fwd_1h_pct") or 0)
    take_1h = score_horizon(role="TAKE", n=n1, mean=m1, clock="+1h")
    take_4h = score_horizon(role="TAKE", n=n4, mean=m4, clock="+4h")
    skip_1h = score_horizon(role="SKIP", n=ns, mean=ms, clock="+1h")
    fit, why = fit_from_take(take_1h)
    depth = take_1h["evidence_depth"]
    out.update(
        {
            "fit": fit,
            "why": why,
            "take_1h": take_1h,
            "take_4h": take_4h,
            "skip_setup_1h": skip_1h,
            "failure_top": dict((fail or Counter()).most_common(6)),
            "keep": False,
            "live_enable": False,
        }
    )
    out.update(
        _depth_fields(
            tested=True,
            fit=fit,
            why=why,
            n_rows=out["n_rows"],
            n_take=out["n_take"],
            n_fwd=n_fwd,
            depth=depth,
        )
    )
    out["provenance"] = _prov(cell, period)
    out["regime_vs_tape"] = _regime_vs_tape(str(cell.get("regime") or ""), tape)
    return out


def _gate_vs_tape(strategy: str, tape: Optional[Counter]) -> dict:
    allowed = ROUTER_REGIMES.get(strategy) or frozenset()
    if "TREND_UP" in allowed:
        gate = "TREND_UP"
    elif "TREND_DOWN" in allowed:
        gate = "TREND_DOWN"
    else:
        gate = None
    out = _regime_vs_tape(gate or "", tape)
    out["strategy"] = strategy
    out["gate"] = gate
    if gate:
        out["note"] = (
            f"{strategy} router gate={gate} vs independent SMA on ALL setups. "
            "Clash is a finding, not a rewrite."
        )
    else:
        out["clash"] = False
        out["clash_kind"] = None
        out["expected_independent_trend"] = None
        out["note"] = f"{strategy} has no TREND_UP/DOWN router gate — no clash test."
    return out


def _regime_vs_tape(ananta_regime: str, tape: Optional[Counter]) -> dict:
    """Ananta regime is a hypothesis. Independent SMA-20 is Market Truth."""
    counts = dict(tape or {})
    n = int(sum(counts.values()))
    expected = _expected_independent_trend(ananta_regime)
    aligned = int(counts.get(expected, 0)) if expected else 0
    clash = bool(n >= 5 and expected and (aligned / n) < 0.4)
    top = None
    if counts:
        top = max(counts.items(), key=lambda kv: kv[1])[0]
    kind = f"{ananta_regime}_GATE_VS_INDEPENDENT_{top}" if clash and top else None
    return {
        "ananta_regime": ananta_regime,
        "independent_trend": counts,
        "n_setup_tape": n,
        "expected_independent_trend": expected,
        "aligned": aligned,
        "clash": clash,
        "clash_kind": kind,
        "keep": False,
        "rewrite": False,
        "note": "Ananta 50-EMA TREND_UP ≠ Market Truth SMA-20. Finding, not a rewrite.",
    }


def _expected_independent_trend(regime: str) -> Optional[str]:
    r = (regime or "").upper()
    if r in ("TREND_UP", "BULL"):
        return "UP"
    if r in ("TREND_DOWN", "BEAR"):
        return "DOWN"
    return None


def _prov(cell: dict, period: Optional[dict]) -> dict:
    return provenance(
        strategy=str(cell.get("strategy") or ""),
        asset=str(cell.get("asset") or ""),
        timeframe=str(cell.get("timeframe") or ""),
        regime=str(cell.get("regime") or ""),
        source=str(cell.get("coverage") or "NONE"),
        period=period,
    )


def _depth_fields(*, tested: bool, fit: str, why: str, n_rows: int, n_take: int, n_fwd: int, depth: str) -> dict:
    st = status_class(tested=tested, fit=fit, why=why)
    return {
        "fit": fit,
        "why": why,
        "status_class": st,
        "evidence_depth": depth,
        "coverage_band": coverage_band(n_rows, tested=tested),
        "confidence_band": confidence_band(st, depth, n_take),
        "outcome_completeness_1h": completeness(n_fwd, n_rows),
    }


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
