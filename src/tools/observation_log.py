"""
Observation ledger — System + Market + Outcome.

schema: observation_v0
Same shape for live paper (observation_log.jsonl) and 1y replay
(observation_replay.jsonl). Never mix the two files.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

OBSERVATION_LOG = Path("observation_log.jsonl")
REPLAY_LOG = Path("observation_replay.jsonl")
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
            "historical_take_is_not_keep": source == "historical_lab",
            "live_and_historical_are_separate_files": True,
        },
    }


def _read_jsonl(path: Path, limit: Optional[int] = None) -> List[dict]:
    if not path.exists():
        return []
    rows: List[dict] = []
    try:
        lines = path.read_text().strip().splitlines()
        use = lines[-limit:] if limit else lines
        for line in use:
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    except Exception:
        return []
    return rows


def read_recent_observations(limit: int = 20) -> List[dict]:
    return list(reversed(_read_jsonl(OBSERVATION_LOG, limit=limit)))


def read_all_observations() -> List[dict]:
    return _read_jsonl(OBSERVATION_LOG)


def read_replay_observations(limit: Optional[int] = None) -> List[dict]:
    return _read_jsonl(REPLAY_LOG, limit=limit)


def print_recent_observations(limit: int = 8) -> None:
    rows = read_recent_observations(limit=limit)
    print("\nOBSERVATION LEDGER (recent live_paper)")
    print("=" * 64)
    print("schema=observation_v0  System|Market|Outcome")
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
    print(f"  historical replay is a SEPARATE file: {REPLAY_LOG}")
    print("=" * 64)
    print()
