"""Decision Quality v0 — first-class meter, not a KEEP engine.

Questions (kept separate):
  A) Does the strategy/engine have edge?
  B) Do Agent decisions (TAKE / WAIT / SKIP) improve on acting the signal?

BTC path ≠ strategy PnL. Historical TAKE-eq ≠ paper TAKE ≠ KEEP.
Hist +15m is UNUSABLE (1h-stride replay). Live TAKE n=0 is a safety fact, not a grade.

CLI: lab quality
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.intelligence.attribution import attribute_print_ready
from src.intelligence.schema import WAVE_A

VERSION = "DQ-v0.1"
LOCKED = "2026-08-25"
BASELINE_VERSION = "DQ-v0.0"
REPORT_PATH = Path("decision_quality_report.json")

NOISE_PCT = 0.25
MATERIAL_PCT = 0.40
TAKE_MIN_N = 30
SITOUT_MIN_N = 30

# Frozen H3 print 2026-08-25. Δ is vs this, not vs hope.
BASELINE_V0 = {
    "version": BASELINE_VERSION,
    "locked": LOCKED,
    "live_n_obs": 241,
    "hist_n_obs": 2474,
    "live_take": 0,
    "cells": {
        "live:hunter:SKIP": {"n_1h": 64, "m_1h": 0.0044, "m_4h": -0.261},
        "live:hunter:WAIT": {"n_1h": 2306, "m_1h": 0.0186, "m_4h": 0.1953},
        "live:squeeze:SKIP": {"n_1h": 2320, "m_1h": 0.0211, "m_4h": 0.1887},
        "live:bollinger-mr:SKIP": {"n_1h": 2320, "m_1h": 0.0211, "m_4h": 0.1887},
        "hist:hunter:TAKE": {"n_1h": 4, "m_1h": -0.0036, "m_4h": -0.3954},
        "hist:squeeze:TAKE": {"n_1h": 4, "m_1h": 0.1134, "m_4h": 0.1003},
        "hist:bollinger-mr:TAKE": {"n_1h": 47, "m_1h": -0.0749, "m_4h": -0.0834},
        "hist:bollinger-mr:SKIP": {"n_1h": 111, "m_1h": 0.054, "m_4h": 0.0696},
    },
    "laws": {
        "keep": False,
        "wave_a": "WATCH",
        "hist_15m": "UNUSABLE",
        "live_take": "NO_LIVE_TAKE",
        "sit_out": "WASH",
        "hunter_weeks_forbidden": True,
    },
}


# Law: which rows each metric is allowed to use.
POPULATIONS = {
    "UNIVERSE": "Every observation × symbol row for that strategy (n_rows).",
    "SETUP": "setup_detected=True. The strategy claimed an opportunity.",
    "TAKE": "SETUP in an allowed regime (paper TAKE or hist TAKE-eq). Opportunity accepted.",
    "SKIP_SETUP": "SETUP that was refused (SKIP or REGIME_FILTERED). Refusal quality lives here.",
    "FILTERED_IDLE": "No setup; regime gate closed. NOT a refused opportunity. Do not score as SKIP quality.",
    "WAIT": "No setup, not filtered. Strategy had nothing to say.",
    "SKIP_LEGACY": "H3 all-row SKIP (includes FILTERED_IDLE). Kept for Δ vs DQ-v0.0 only.",
    "SIT-OUT": "Agent-level WAIT/SKIP vs BTC path. Opportunity cost of the book, not one strategy's PnL.",
    "FILTERED": "skip_reason starts with REGIME_FILTERED (may or may not have a setup).",
}


def evidence_depth(n: int, *, role: str) -> str:
    if n <= 0:
        return "NONE"
    if n < 10:
        return "ANECDOTE"
    if n < 30:
        return "THIN"
    if role == "TAKE" and n < TAKE_MIN_N:
        return "THIN"
    if n < 100:
        return "ADEQUATE"
    return "SOLID"


def path_call(mean: Optional[float], n: int, *, usable: bool, role: str) -> str:
    if not usable:
        return "UNUSABLE_CLOCK"
    if n <= 0 or mean is None:
        return "NO_SAMPLE"
    need = TAKE_MIN_N if role == "TAKE" else SITOUT_MIN_N
    if n < need:
        return "INSUFFICIENT_EVIDENCE"
    mag = abs(mean)
    if mag < NOISE_PCT:
        return "WASH"
    if mag < MATERIAL_PCT:
        return "SLIGHT"
    return "MATERIAL"


def signed_verdict(role: str, mean: Optional[float], call: str) -> str:
    if call in ("UNUSABLE_CLOCK", "NO_SAMPLE", "INSUFFICIENT_EVIDENCE"):
        return call
    if call == "WASH":
        return "WASH"
    if mean is None:
        return call
    if role == "TAKE":
        if mean >= NOISE_PCT:
            return "TAKE_HELPED"
        if mean <= -NOISE_PCT:
            return "TAKE_HURT"
        return "WASH"
    # WAIT / SKIP = opportunity cost of sitting out
    if mean >= NOISE_PCT:
        return "SITOUT_COSTLY"
    if mean <= -NOISE_PCT:
        return "SITOUT_PROTECTIVE"
    return "WASH"


def score_horizon(
    *,
    role: str,
    n: int,
    mean: Optional[float],
    clock: str,
    usable: bool = True,
) -> Dict[str, Any]:
    depth = evidence_depth(n, role=role)
    call = path_call(mean, n, usable=usable, role=role)
    return {
        "clock": clock,
        "n": n,
        "mean_pct": mean,
        "usable": usable,
        "evidence_depth": depth,
        "path_call": call,
        "verdict": signed_verdict(role, mean, call),
    }


def _h(bucket: dict, kind: str, horizon: str) -> Tuple[int, Optional[float]]:
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


def score_strategy(key: str, source: str, bucket: dict) -> Dict[str, Any]:
    hist = source == "historical_lab"
    cells = {}
    for role in ("take", "skip", "wait", "skip_setup", "filtered_idle"):
        score_role = "TAKE" if role == "take" else ("SKIP" if role in ("skip", "skip_setup", "filtered_idle") else "WAIT")
        n15, m15 = _h(bucket, role, "fwd_15m_pct")
        n1, m1 = _h(bucket, role, "fwd_1h_pct")
        n4, m4 = _h(bucket, role, "fwd_4h_pct")
        label = {
            "take": "TAKE",
            "skip": "SKIP_LEGACY",
            "wait": "WAIT",
            "skip_setup": "SKIP_SETUP",
            "filtered_idle": "FILTERED_IDLE",
        }[role]
        cells[label] = {
            "+15m": score_horizon(
                role=score_role, n=n15, mean=m15, clock="+15m", usable=not hist
            ),
            "+1h": score_horizon(role=score_role, n=n1, mean=m1, clock="+1h"),
            "+4h": score_horizon(role=score_role, n=n4, mean=m4, clock="+4h"),
        }
    take_1h = cells["TAKE"]["+1h"]
    skip_1h = cells["SKIP_SETUP"]["+1h"]
    headline = _headline(key, source, take_1h, skip_1h, bucket)
    return {
        "strategy": key,
        "source": source,
        "n_rows": bucket.get("n_rows", 0),
        "n_setup": bucket.get("n_setup", 0),
        "n_take": bucket.get("n_take", 0),
        "n_skip": bucket.get("n_skip", 0),
        "n_skip_setup": bucket.get("n_skip_setup", 0),
        "n_filtered_idle": bucket.get("n_filtered_idle", 0),
        "n_wait": bucket.get("n_wait", 0),
        "n_regime_filtered": bucket.get("n_regime_filtered", 0),
        "cells": cells,
        "headline": headline,
        "keep": False,
    }


def _headline(key: str, source: str, take_1h: dict, skip_1h: dict, bucket: dict) -> str:
    if source != "historical_lab" and int(bucket.get("n_take") or 0) == 0:
        if key == "hunter" and int(bucket.get("n_setup") or 0):
            return (
                f"NO_LIVE_TAKE. {bucket.get('n_setup')} setups refused "
                f"(skip_setup={bucket.get('n_skip_setup')}). Filter is a finding, not TREND_UP enable."
            )
        return "NO_LIVE_TAKE. Safety is behaving. Decision quality on TAKE is unmeasured."
    if take_1h["verdict"] == "INSUFFICIENT_EVIDENCE":
        return f"INSUFFICIENT EVIDENCE on TAKE (n={take_1h['n']}). Not KEEP."
    if key == "bollinger-mr" and take_1h["verdict"] in ("WASH", "TAKE_HURT"):
        skip_v = skip_1h.get("verdict")
        return (
            f"Hist TAKE-eq n={take_1h['n']} {take_1h['verdict']} "
            f"(+1h={take_1h['mean_pct']}%). SKIP_SETUP {skip_v}. Shadow only."
        )
    return f"TAKE {take_1h['verdict']} n={take_1h['n']}; SKIP {skip_1h['verdict']} n={skip_1h['n']}. WATCH."


def meter(live: Optional[dict] = None, hist: Optional[dict] = None) -> Dict[str, Any]:
    live = live if live is not None else _safe("live")
    hist = hist if hist is not None else _safe("replay")
    strategies: List[dict] = []
    for k in WAVE_A:
        lb = (live.get("by_strategy") or {}).get(k) or {}
        hb = (hist.get("by_strategy") or {}).get(k) or {}
        strategies.append(
            {
                "strategy": k,
                "live": score_strategy(k, live.get("source") or "live_paper", lb),
                "historical": score_strategy(k, hist.get("source") or "historical_lab", hb),
            }
        )
    live_take = sum(int(s["live"].get("n_take") or 0) for s in strategies)
    boll_take = next(s["historical"]["cells"]["TAKE"]["+1h"] for s in strategies if s["strategy"] == "bollinger-mr")
    hunter_skip = next(s["live"]["cells"]["SKIP_SETUP"]["+1h"] for s in strategies if s["strategy"] == "hunter")
    hunter_skip_4h = next(s["live"]["cells"]["SKIP_SETUP"]["+4h"] for s in strategies if s["strategy"] == "hunter")

    rollup = {
        "keep_allowed": False,
        "wave_a": "WATCH",
        "live_take_n": live_take,
        "live_take_quality": "NO_LIVE_TAKE" if live_take == 0 else "SEE_CELLS",
        "sit_out_live": "WASH",
        "hist_take_usable": (
            f"bollinger-mr n={boll_take['n']} {boll_take['verdict']} +1h={boll_take['mean_pct']}%"
        ),
        "hunter_live_skip_setup": (
            f"n={hunter_skip['n']} +1h={hunter_skip['verdict']} +4h={hunter_skip_4h['verdict']}"
        ),
        "promotion": "FORBIDDEN",
        "next": [
            "Leave lab watch 15 running (Wave A frozen).",
            "Do not KEEP / TREND_UP / Hunter v1.1.",
            "H2 = lab h2 (done as measurement).",
            "Universe v1 = lab universe (offline). Do not add strategies to live watch.",
        ],
    }
    delta = _delta_vs_baseline(strategies)
    return {
        "ok": True,
        "schema": "decision_quality_v0",
        "version": VERSION,
        "baseline_locked": LOCKED,
        "baseline_version": BASELINE_VERSION,
        "ts": datetime.now(timezone.utc).isoformat(),
        "live_n": live.get("n"),
        "hist_n": hist.get("n"),
        "live_gap": live.get("data_gap"),
        "hist_gap": hist.get("data_gap"),
        "noise_band_pct": NOISE_PCT,
        "material_band_pct": MATERIAL_PCT,
        "laws": {
            "btc_path_is_not_strategy_pnl": True,
            "hist_take_eq_is_not_keep": True,
            "hist_15m_unusable": True,
            "three_confidences_stay_separate": True,
            "no_blended_score": True,
            "insufficient_evidence_is_valid": True,
            "wave_a_watch": True,
            "skip_setup_is_refusal_quality": True,
            "filtered_idle_is_not_refusal": True,
        },
        "populations": POPULATIONS,
        "rollup": rollup,
        "strategies": strategies,
        "delta_vs_baseline": delta,
        "note": (
            "Finest quality here is refusal to lie. "
            "No blended 82%. No KEEP from a wash. "
            "v0.1 adds population integrity (SKIP_SETUP vs FILTERED_IDLE). "
            "Δ vs DQ-v0.0 is how later *behavior* changes are judged — this patch is not a quality win."
        ),
    }


def _delta_vs_baseline(strategies: List[dict]) -> Dict[str, Any]:
    moved: List[dict] = []
    for s in strategies:
        for side, tag in (("live", "live"), ("historical", "hist")):
            block = s[side]
            for role, cell_name in (("TAKE", "TAKE"), ("SKIP", "SKIP_LEGACY"), ("WAIT", "WAIT")):
                cell = ((block.get("cells") or {}).get(cell_name) or {}).get("+1h") or {}
                key = f"{tag}:{s['strategy']}:{role}"
                base = (BASELINE_V0["cells"] or {}).get(key)
                if not base:
                    continue
                n = cell.get("n") or 0
                m = cell.get("mean_pct")
                if m is None or n < SITOUT_MIN_N and role != "TAKE":
                    continue
                if role == "TAKE" and n < TAKE_MIN_N:
                    continue
                dm = round(float(m) - float(base["m_1h"]), 4)
                if abs(dm) >= 0.10:
                    moved.append({"cell": key, "baseline_1h": base["m_1h"], "now_1h": m, "delta": dm, "n": n})
    return {
        "baseline": BASELINE_VERSION,
        "moved_cells": moved,
        "interpretation": (
            "Empty moved_cells = still on the 2026-08-25 baseline. "
            "A later DI change must shrink COSTLY / grow PROTECTIVE or TAKE_HELPED "
            "with adequate n — not invent a KEEP."
        ),
    }


def _safe(source: str) -> dict:
    try:
        return attribute_print_ready(source)
    except Exception as e:
        return {"data_gap": True, "error": str(e), "n": 0, "by_strategy": {}}


def save_report(report: Optional[dict] = None) -> Path:
    report = report or meter()
    REPORT_PATH.write_text(json.dumps(report, indent=2, default=str))
    return REPORT_PATH


def print_meter(report: Optional[dict] = None) -> Dict[str, Any]:
    report = report or meter()
    try:
        save_report(report)
        saved = str(REPORT_PATH)
    except Exception:
        saved = None
    r = report.get("rollup") or {}
    print("\nDECISION QUALITY  " + str(report.get("version")))
    print("=" * 64)
    print("Institutional meter. Not a KEEP engine. No blended score.")
    print("Populations: SKIP_SETUP = refused opportunity. FILTERED_IDLE ≠ SKIP quality.")
    print(f"meter {report.get('version')}   baseline {report.get('baseline_version')} locked {report.get('baseline_locked')}")
    print(f"live n={report.get('live_n')}  hist n={report.get('hist_n')}")
    print("-" * 64)
    print(f"  KEEP allowed     : {r.get('keep_allowed')}   wave_a={r.get('wave_a')}")
    print(f"  TAKE quality     : n={r.get('live_take_n')}  {r.get('live_take_quality')}")
    print(f"  WAIT / sit-out   : {r.get('sit_out_live')}")
    print(f"  SKIP_SETUP       : hunter live {r.get('hunter_live_skip_setup')}")
    print(f"  hist TAKE usable : {r.get('hist_take_usable')}")
    print(f"  readiness        : NOT EARNED")
    print("-" * 64)
    for s in report.get("strategies") or []:
        print(f"  {s['strategy']}")
        for side in ("live", "historical"):
            b = s[side]
            print(
                f"    {side:<12} setup={b.get('n_setup')} TAKE={b.get('n_take')} "
                f"skip_setup={b.get('n_skip_setup')} filtered_idle={b.get('n_filtered_idle')} "
                f"WAIT={b.get('n_wait')}"
            )
            print(f"                 {b.get('headline')}")
            take = (b.get("cells") or {}).get("TAKE") or {}
            ref = (b.get("cells") or {}).get("SKIP_SETUP") or {}
            idle = (b.get("cells") or {}).get("FILTERED_IDLE") or {}
            t1 = take.get("+1h") or {}
            r1 = ref.get("+1h") or {}
            r4 = ref.get("+4h") or {}
            i1 = idle.get("+1h") or {}
            print(f"                 TAKE       +1h n={t1.get('n')} {t1.get('mean_pct')}% {t1.get('verdict')}")
            print(
                f"                 SKIP_SETUP +1h n={r1.get('n')} {r1.get('mean_pct')}% {r1.get('verdict')}  "
                f"+4h {r4.get('verdict')}"
            )
            print(f"                 FILTERED   +1h n={i1.get('n')} {i1.get('mean_pct')}% {i1.get('verdict')}  (not refusal)")
    moved = (report.get("delta_vs_baseline") or {}).get("moved_cells") or []
    print("-" * 64)
    print(f"  Δ vs {BASELINE_VERSION}: {len(moved)} moved cell(s)  (v0.1 is integrity, not a quality win)")
    for m in moved[:8]:
        print(f"    {m['cell']}  {m['baseline_1h']}% → {m['now_1h']}%  Δ={m['delta']}")
    print("-" * 64)
    print("  Laws: hist +15m UNUSABLE · TAKE-eq ≠ KEEP · INSUFFICIENT EVIDENCE is valid")
    print("  Next change must beat this baseline. Do not rescue Hunter for weeks.")
    if saved:
        print(f"  saved: {saved}")
    print("=" * 64)
    print()
    return report
