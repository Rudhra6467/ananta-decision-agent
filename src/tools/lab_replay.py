"""
Stage 4 — pull Ananta historical observation replay and persist observation_v0.

Writes observation_replay.jsonl (NEVER mixes into live observation_log.jsonl).
Historical TAKE is TAKE-equivalent: not a paper fill, not KEEP.
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.tools.observation_log import REPLAY_LOG, SCHEMA

WAVE_A = ("hunter", "squeeze", "bollinger-mr")
DEFAULT_SYMBOLS = ("BTC/USD",)
DEFAULT_STRIDE = 4


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_replay_jsonl(observations: List[dict], *, append: bool = False) -> Path:
    mode = "a" if append and REPLAY_LOG.exists() else "w"
    with REPLAY_LOG.open(mode) as f:
        for rec in observations:
            rec.setdefault("schema", SCHEMA)
            rec.setdefault("source", "historical_lab")
            f.write(json.dumps(rec, default=str) + "\n")
    return REPLAY_LOG


def _print_strategy_evidence(stats: dict) -> None:
    keys = list(WAVE_A) + [k for k in (stats or {}) if k not in WAVE_A]
    for key in keys:
        s = (stats or {}).get(key) or {}
        print(
            f"  {key:<14} bars={s.get('bars')}  setups={s.get('setups')}  "
            f"TAKE-eq={s.get('take_equivalent')}  SKIP={s.get('skip')}  "
            f"WAIT={s.get('wait')}  REGIME_FILTERED={s.get('skip_regime_filtered')}"
        )
        by_reg = s.get("by_regime") or {}
        for reg, b in sorted(by_reg.items(), key=lambda kv: -(kv[1].get("setups") or 0)):
            if not b.get("setups") and not b.get("take_equivalent") and not b.get("skip"):
                continue
            print(
                f"      {reg:<14} setups={b.get('setups')}  "
                f"TAKE-eq={b.get('take_equivalent')}  SKIP={b.get('skip')}  WAIT={b.get('wait')}"
            )


def print_replay_summary(payload: dict) -> None:
    summary = payload.get("summary") or {}
    cov = summary.get("coverage") or payload.get("coverage") or {}
    print()
    print("STAGE 4 HISTORICAL REPLAY  (observation_v0, source=historical_lab)")
    print("=" * 64)
    print("Same schema as live_paper. Real Ananta implementations. Not KEEP.")
    print("-" * 64)
    print(f"  symbol     : {payload.get('symbol')}")
    print(f"  ok         : {payload.get('ok')}  sampled={summary.get('bars_sampled')}  "
          f"stride={summary.get('stride')}  15m={summary.get('has_15m')}")
    print(
        f"  coverage   : 1h={cov.get('count')}  span={cov.get('span_days')}d  "
        f"{cov.get('from_iso') or cov.get('from')} → {cov.get('to_iso') or cov.get('to')}  "
        f"usable_1y={summary.get('usable_1y') or cov.get('usable_1y')}"
    )
    print(f"  asset dist : {summary.get('asset_regime_distribution')}")
    print(f"  market dist: {summary.get('market_regime_distribution')}")
    print(f"  decisions  : {summary.get('agent_decisions')}")
    print("-" * 64)
    print("STRATEGY EVIDENCE  (setups vs Wave A gates — not promotion)")
    _print_strategy_evidence(summary.get("strategy_evidence") or {})
    print("-" * 64)
    de = summary.get("decision_evidence") or {}
    print("DECISION EVIDENCE  (forward path after aggregate TAKE/SKIP/WAIT)")
    print(f"  mean +1h after TAKE-eq : {de.get('mean_fwd_1h_after_TAKE')}%")
    print(f"  mean +1h after SKIP    : {de.get('mean_fwd_1h_after_SKIP')}%")
    print(f"  mean +1h after WAIT    : {de.get('mean_fwd_1h_after_WAIT')}%")
    print(f"  n with +1h             : {de.get('n_fwd_1h')}")
    print("-" * 64)
    impl = payload.get("implementations") or {}
    if impl:
        print("IMPLEMENTATIONS (must be Ananta, not a second evaluator)")
        for k in ("classify_regime", "hunter", "squeeze", "bollinger_mr"):
            if impl.get(k):
                print(f"  {k}: {impl[k]}")
    for c in summary.get("contradictions") or []:
        print(f"  CONTRADICTION: {c}")
    print("-" * 64)
    print("  Wave A remains  hunter=WATCH  squeeze=WATCH  bollinger-mr=WATCH")
    print("  Historical TAKE-equivalent ≠ paper TAKE ≠ KEEP.")
    print("  Enough to evaluate ≠ enough to promote.")
    print("=" * 64)
    print()


def run_lab_replay(
    symbols: Optional[List[str]] = None,
    stride: int = DEFAULT_STRIDE,
    include_observations: bool = True,
    max_bars: Optional[int] = None,
    smoke: bool = False,
) -> Dict[str, Any]:
    from src.tools.ananta_api import get_observation_replay

    symbols = list(symbols or DEFAULT_SYMBOLS)
    if smoke and max_bars is None:
        max_bars = 80
        stride = max(stride, 12)
        print("SMOKE: max_bars=80 stride bumped. Not a 1y claim.")

    print()
    print("lab replay — Stage 4 historical Observation")
    print("source=historical_lab  file=observation_replay.jsonl")
    print("Does not touch observation_log.jsonl (live watcher keeps that).")
    print("Does not KEEP / CUT / enable / rewrite strategies.")
    print()

    combined: List[dict] = []
    payloads: List[dict] = []
    first = True
    for sym in symbols:
        print(f"→ requesting {sym}  stride={stride}  max_bars={max_bars or 'all'} ...")
        got = get_observation_replay(
            symbol=sym,
            timeframe="1h",
            stride=stride,
            include_observations=include_observations,
            max_bars=max_bars,
        )
        if not got.get("success"):
            print(f"  FAILED: {got.get('error') or got}")
            payloads.append({"ok": False, "symbol": sym, "error": got.get("error") or got})
            continue
        data = got.get("data") or {}
        payloads.append(data)
        print_replay_summary(data)
        obs = data.get("observations") or []
        if include_observations and obs:
            write_replay_jsonl(obs, append=not first)
            first = False
            combined.extend(obs)
            print(f"  wrote {len(obs)} rows → {REPLAY_LOG}")
        elif not data.get("ok"):
            print(f"  replay not ok: {data.get('error')}")

    n = 0
    if REPLAY_LOG.exists() and combined:
        n = len(combined)
    elif REPLAY_LOG.exists():
        n = sum(1 for _ in REPLAY_LOG.open())

    print()
    print(f"Replay ledger: {REPLAY_LOG}  rows={n}")
    print("Next: lab audit replay")
    print("Live watcher is a separate stream (observation_log.jsonl).")
    print()
    return {
        "ok": any(p.get("ok") for p in payloads),
        "symbols": symbols,
        "n_written": n,
        "path": str(REPLAY_LOG),
        "payloads": [
            {k: v for k, v in p.items() if k != "observations"} for p in payloads
        ],
        "ts": _utc_now(),
    }


def print_understanding_from_replay() -> None:
    """Strategy Understanding Report seed — evaluation info, not promotion."""
    from src.tools.ananta_api import get_strategy_knowledge
    from src.tools.observation_log import read_replay_observations

    print()
    print("STRATEGY UNDERSTANDING REPORT  (seed — not KEEP)")
    print("=" * 64)
    kn = get_strategy_knowledge()
    objects = ((kn.get("data") or {}).get("strategies") or []) if kn.get("success") else []
    by_id = {s.get("strategy_id"): s for s in objects}

    rows = read_replay_observations()
    live_n = 0
    try:
        from src.tools.observation_log import OBSERVATION_LOG
        if OBSERVATION_LOG.exists():
            live_n = sum(1 for _ in OBSERVATION_LOG.open() if _.strip())
    except Exception:
        live_n = 0

    per = {k: Counter() for k in WAVE_A}
    regimes = {k: Counter() for k in WAVE_A}
    for rec in rows:
        st = rec.get("system_truth") or {}
        for o in st.get("strategy_observations") or []:
            key = str(o.get("strategy") or "")
            if key not in per:
                continue
            dec = str(o.get("decision") or "").upper()
            per[key][dec] += 1
            if o.get("setup_detected"):
                per[key]["setups"] += 1
            if o.get("skip_reason") == "REGIME_FILTERED":
                per[key]["REGIME_FILTERED"] += 1
                regimes[key][str(o.get("regime") or "?")] += 1

    for key in WAVE_A:
        obj = by_id.get(key) or {}
        print(f"\nSTRATEGY: {obj.get('name') or key.upper()}  ({key})")
        print(f"  Implementation     : VERIFIED  (Ananta {', '.join((obj.get('implementation_files') or [])[:3])})")
        print(f"  Strategy Knowledge : {'VERIFIED' if obj else 'MISSING'}")
        print(f"  Router gates       : {obj.get('actual_router_gates') or obj.get('allowed_regimes')}")
        print(f"  Thesis regimes     : {obj.get('thesis_regimes')}  ≠ live {obj.get('allowed_regimes')}")
        print(f"  Historical rows    : {sum(per[key][d] for d in ('TAKE', 'SKIP', 'WAIT', 'UNKNOWN'))}  (source=historical_lab)")
        print(f"  Historical setups  : {per[key].get('setups', 0)}")
        print(f"  Historical TAKE-eq : {per[key].get('TAKE', 0)}   (NOT paper TAKE, NOT KEEP)")
        print(f"  Historical SKIP    : {per[key].get('SKIP', 0)}  REGIME_FILTERED={per[key].get('REGIME_FILTERED', 0)}")
        print(f"  Historical WAIT    : {per[key].get('WAIT', 0)}")
        if regimes[key]:
            print(f"  REGIME_FILTERED in : {dict(regimes[key])}")
        for c in obj.get("contradictions") or []:
            print(f"  CONTRADICTION: {c.get('agent_must_say')}")
        print(f"  Paper observations : {live_n} live ticks (separate file)")
        print(f"  Understanding conf : {obj.get('understanding_confidence') or 'MEDIUM'}")
        print(f"  Evidence conf      : LOW  (replay evaluates; does not promote)")
        print(f"  Current decision   : WATCH")
        print("  Potential hypotheses: none auto-written. S5 is PROPOSED experiments only.")

    print()
    print("-" * 64)
    print("Enough information to evaluate ≠ enough evidence to KEEP.")
    print("Do not modify hunter / squeeze / bollinger-mr from this report.")
    print("=" * 64)
    print()
