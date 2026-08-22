"""
Observation ledger — System + Market + Outcome (Outcome null until Stage 2).

schema: observation_v0
Same shape intended for live paper and future 1y replay.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

OBSERVATION_LOG = Path("observation_log.jsonl")
SCHEMA = "observation_v0"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_observation(record: dict) -> bool:
    try:
        with OBSERVATION_LOG.open("a") as f:
            f.write(json.dumps(record, default=str) + "\n")
        return True
    except Exception:
        return False


def build_observation(
    *,
    system_truth: dict,
    market_truth: dict,
    outcome_truth: Optional[dict] = None,
    source: str = "live_paper",
) -> dict:
    return {
        "schema": SCHEMA,
        "ts": _utc_now(),
        "source": source,
        "system_truth": system_truth,
        "market_truth": market_truth,
        "outcome_truth": outcome_truth,
        "laws": {
            "ananta_regime_is_hypothesis": True,
            "ananta_output_not_proof": True,
            "no_auto_mutation": True,
        },
    }


def read_recent_observations(limit: int = 20) -> List[dict]:
    if not OBSERVATION_LOG.exists():
        return []
    rows: List[dict] = []
    try:
        lines = OBSERVATION_LOG.read_text().strip().splitlines()
        for line in lines[-limit:]:
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    except Exception:
        return []
    return list(reversed(rows))


def print_recent_observations(limit: int = 8) -> None:
    rows = read_recent_observations(limit=limit)
    print("\nOBSERVATION LEDGER (recent)")
    print("=" * 64)
    print("schema=observation_v0  System|Market|Outcome (Outcome Stage 2)")
    print("-" * 64)
    if not rows:
        print("  (empty — run: lab watch)")
        print("=" * 64)
        return
    for r in rows:
        st = r.get("system_truth") or {}
        mt = r.get("market_truth") or {}
        btc = (mt.get("btc") or {}) if isinstance(mt, dict) else {}
        print(
            f"  {str(r.get('ts', ''))[:19]}  dec={st.get('agent_decision')}  "
            f"cycle={st.get('cycle_id') or '-'}  "
            f"BTC={btc.get('price')} ret1h={btc.get('ret_1h_pct')}  "
            f"breadth={mt.get('breadth_1h_pct_positive')}"
        )
        regimes = st.get("regimes_by_symbol") or {}
        if regimes:
            sample = ", ".join(f"{k.split('/')[0]}={v}" for k, v in list(regimes.items())[:5])
            print(f"    ananta_regime(hyp): {sample}")
    print("-" * 64)
    print(f"  file: {OBSERVATION_LOG}  (not KEEP; log only)")
    print("=" * 64)
    print()
