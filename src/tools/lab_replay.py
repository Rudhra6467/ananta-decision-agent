"""
Stage 4 — pull Ananta historical observation replay and persist observation_v0.

BTC 1y → observation_replay.jsonl
ETH     → observation_replay_ETHUSD.jsonl
smoke   → observation_replay_smoke.jsonl
Never mix into live observation_log.jsonl.
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.tools.observation_log import REPLAY_LOG, SCHEMA, replay_path_for

WAVE_A = ("hunter", "squeeze", "bollinger-mr")
DEFAULT_SYMBOLS = ("BTC/USD",)
DEFAULT_STRIDE = 4


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_replay_jsonl(observations: List[dict], path: Path, *, append: bool = False) -> Path:
    mode = "a" if append and path.exists() else "w"
    with path.open(mode) as f:
        for rec in observations:
            rec.setdefault("schema", SCHEMA)
            rec.setdefault("source", "historical_lab")
            f.write(json.dumps(rec, default=str) + "\n")
    return path


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
        print("SMOKE: max_bars=80 stride bumped. Writes observation_replay_smoke.jsonl.")
        print("Does NOT replace observation_replay.jsonl (BTC 1y).")

    print()
    print("lab replay — Stage 4 historical Observation")
    print("BTC → observation_replay.jsonl · other symbols → sibling file · smoke → _smoke")
    print("Does not touch observation_log.jsonl (live watcher keeps that).")
    print("Does not KEEP / CUT / enable / rewrite strategies.")
    print()

    payloads: List[dict] = []
    written: Dict[str, int] = {}
    for sym in symbols:
        dest = replay_path_for(symbol=sym, smoke=smoke)
        print(f"→ requesting {sym}  stride={stride}  max_bars={max_bars or 'all'} → {dest}")
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
            write_replay_jsonl(obs, dest, append=False)
            written[str(dest)] = len(obs)
            print(f"  wrote {len(obs)} rows → {dest}")
            if dest != REPLAY_LOG:
                print(f"  BTC ledger untouched: {REPLAY_LOG}")
        elif not data.get("ok"):
            print(f"  replay not ok: {data.get('error')}")

    print()
    print(f"Wrote: {written or 'nothing'}")
    print(f"BTC 1y ledger remains: {REPLAY_LOG}")
    print("Live watcher is a separate stream (observation_log.jsonl).")
    print()
    return {
        "ok": any(p.get("ok") for p in payloads),
        "symbols": symbols,
        "written": written,
        "path": str(REPLAY_LOG),
        "payloads": [
            {k: v for k, v in p.items() if k != "observations"} for p in payloads
        ],
        "ts": _utc_now(),
    }


def print_understanding_from_replay() -> None:
    from src.tools.ananta_api import get_strategy_knowledge
    from src.tools.observation_log import read_replay_observations
    from src.tools.observation_log import OBSERVATION_LOG

    print()
    print("STRATEGY UNDERSTANDING REPORT  (seed — not KEEP)")
    print("=" * 64)
    kn = get_strategy_knowledge()
    objects = ((kn.get("data") or {}).get("strategies") or []) if kn.get("success") else []
    by_id = {s.get("strategy_id"): s for s in objects}
    rows = read_replay_observations()
    live_n = 0
    try:
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
        print(f"  Historical TAKE-eq : {per[key].get('TAKE', 0)}   (NOT KEEP)")
        print(f"  Paper observations : {live_n} live ticks")
        print(f"  Current decision   : WATCH")
    print("Enough information to evaluate ≠ enough evidence to KEEP.")
    print("=" * 64)
    print()
