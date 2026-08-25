"""Decision / outcome attribution.

Joins observation_v0 rows to per-strategy TAKE / SKIP / WAIT and forward path.
This IS the H3 measurement report. It does not mutate Wave A.

Never mix bollinger TAKE-eq into hunter. BTC path ≠ strategy PnL.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from src.intelligence.schema import WAVE_A, _norm_action
from src.tools.observation_log import OBSERVATION_LOG, REPLAY_LOG, _read_jsonl

HORIZONS = ("fwd_15m_pct", "fwd_1h_pct", "fwd_4h_pct")
HORIZON_SHORT = {
    "fwd_15m_pct": "+15m",
    "fwd_1h_pct": "+1h",
    "fwd_4h_pct": "+4h",
}


def attribute(source: str = "live") -> Dict[str, Any]:
    """Per-strategy attribution over a ledger. Empty file → DATA_GAP, not a verdict."""
    path = REPLAY_LOG if source in ("replay", "historical", "historical_lab") else OBSERVATION_LOG
    tag = "historical_lab" if path == REPLAY_LOG else "live_paper"
    rows = _read_jsonl(path)
    if not rows:
        return {
            "ok": True,
            "source": tag,
            "n": 0,
            "data_gap": True,
            "h3": "APPROVED_MEASUREMENT",
            "note": (
                f"{path} missing or empty. Not a KEEP/CUT. "
                "H3 is a report; Wave A stays WATCH."
            ),
            "by_strategy": {k: _empty_bucket() for k in WAVE_A},
        }

    buckets = {k: _empty_bucket() for k in WAVE_A}
    other = _empty_bucket()
    agg = _empty_bucket()

    for obs in rows:
        st = obs.get("system_truth") or {}
        ot = obs.get("outcome_truth") or {}
        per = list(st.get("strategy_observations") or [])
        if per:
            for o in per:
                key = (o.get("strategy") or o.get("strategy_key") or "").lower()
                bucket = buckets.get(key, other)
                _accumulate(bucket, o, ot)
                if key in buckets:
                    _accumulate(agg, o, ot)
        else:
            fake = {
                "decision": st.get("agent_decision") or "WAIT",
                "setup_detected": bool(st.get("n_setups")),
                "skip_reason": None,
            }
            _accumulate(agg, fake, ot)

    return {
        "ok": True,
        "source": tag,
        "n": len(rows),
        "data_gap": False,
        "h3": "APPROVED_MEASUREMENT",
        "note": (
            "H3 measurement report — per-strategy forward path. "
            "Do not read bollinger TAKE-eq as Wave A working. "
            "Historical TAKE-eq ≠ paper TAKE ≠ KEEP. BTC path ≠ strategy PnL."
        ),
        "by_strategy": buckets,
        "unassigned_or_other": other,
        "aggregate_warning": (
            "Aggregate mixes strategies. Prefer by_strategy. "
            f"agg_take={agg['n_take']} agg_skip={agg['n_skip']} agg_wait={agg['n_wait']}"
        ),
    }


def _empty_bucket() -> Dict[str, Any]:
    return {
        "n_rows": 0,
        "n_setup": 0,
        "n_take": 0,
        "n_skip": 0,
        "n_wait": 0,
        "n_regime_filtered": 0,
        "n_skip_setup": 0,
        "n_filtered_idle": 0,
        "mean_fwd": {h: None for h in HORIZONS},
        "mean_fwd_after_take": {h: None for h in HORIZONS},
        "mean_fwd_after_skip": {h: None for h in HORIZONS},
        "mean_fwd_after_wait": {h: None for h in HORIZONS},
        "n_fwd": {h: 0 for h in HORIZONS},
        "n_fwd_after_take": {h: 0 for h in HORIZONS},
        "n_fwd_after_skip": {h: 0 for h in HORIZONS},
        "n_fwd_after_wait": {h: 0 for h in HORIZONS},
        "mean_fwd_after_skip_setup": {h: None for h in HORIZONS},
        "mean_fwd_after_filtered_idle": {h: None for h in HORIZONS},
        "n_fwd_after_skip_setup": {h: 0 for h in HORIZONS},
        "n_fwd_after_filtered_idle": {h: 0 for h in HORIZONS},
        "_sum": {h: 0.0 for h in HORIZONS},
        "_n": {h: 0 for h in HORIZONS},
        "_sum_take": {h: 0.0 for h in HORIZONS},
        "_n_take": {h: 0 for h in HORIZONS},
        "_sum_skip": {h: 0.0 for h in HORIZONS},
        "_n_skip": {h: 0 for h in HORIZONS},
        "_sum_wait": {h: 0.0 for h in HORIZONS},
        "_n_wait": {h: 0 for h in HORIZONS},
        "_sum_skip_setup": {h: 0.0 for h in HORIZONS},
        "_n_skip_setup": {h: 0 for h in HORIZONS},
        "_sum_filtered_idle": {h: 0.0 for h in HORIZONS},
        "_n_filtered_idle": {h: 0 for h in HORIZONS},
    }


def _is_regime_filtered(skip: Any) -> bool:
    s = str(skip or "").upper().strip()
    return s == "REGIME_FILTERED" or s.startswith("REGIME_FILTERED")


def _accumulate(bucket: dict, obs_row: dict, outcome: dict) -> None:
    bucket["n_rows"] += 1
    if obs_row.get("setup_detected"):
        bucket["n_setup"] += 1
    if _is_regime_filtered(obs_row.get("skip_reason")):
        bucket["n_regime_filtered"] += 1
    dec = _classify(obs_row)
    bucket[f"n_{dec.lower()}"] += 1
    pop = population_role(obs_row)
    if pop == "SKIP_SETUP":
        bucket["n_skip_setup"] += 1
    elif pop == "FILTERED_IDLE":
        bucket["n_filtered_idle"] += 1
    fwd = _forward(outcome)
    for h in HORIZONS:
        v = fwd.get(h)
        if v is None:
            continue
        try:
            x = float(v)
        except (TypeError, ValueError):
            continue
        bucket["_sum"][h] += x
        bucket["_n"][h] += 1
        bucket[f"_sum_{dec.lower()}"][h] += x
        bucket[f"_n_{dec.lower()}"][h] += 1
        if pop == "SKIP_SETUP":
            bucket["_sum_skip_setup"][h] += x
            bucket["_n_skip_setup"][h] += 1
        elif pop == "FILTERED_IDLE":
            bucket["_sum_filtered_idle"][h] += x
            bucket["_n_filtered_idle"][h] += 1


def population_role(obs_row: dict) -> str:
    """Measurement population — not a KEEP label.

    TAKE          setup in allowed regime (TAKE / TAKE-eq)
    SKIP_SETUP    a setup existed and was refused (SKIP or REGIME_FILTERED)
    FILTERED_IDLE no setup; regime gate closed — NOT a refused opportunity
    WAIT          no setup, not filtered
    """
    setup = bool(obs_row.get("setup_detected"))
    skip = obs_row.get("skip_reason")
    filtered = _is_regime_filtered(skip)
    dec = _norm_action(obs_row.get("decision") or "")
    if dec == "TAKE" or (setup and not filtered and dec != "SKIP"):
        return "TAKE"
    if setup and (filtered or dec == "SKIP"):
        return "SKIP_SETUP"
    if filtered:
        return "FILTERED_IDLE"
    return "WAIT"


def _classify(obs_row: dict) -> str:
    skip = obs_row.get("skip_reason")
    dec = _norm_action(obs_row.get("decision") or "")
    setup = bool(obs_row.get("setup_detected"))
    if _is_regime_filtered(skip) or dec == "SKIP":
        return "SKIP"
    if setup or dec == "TAKE":
        return "TAKE"
    return "WAIT"


def _cell_ret(cell: Any) -> Optional[float]:
    if isinstance(cell, dict) and cell.get("ret_pct") is not None:
        try:
            return float(cell["ret_pct"])
        except (TypeError, ValueError):
            return None
    if isinstance(cell, (int, float)):
        return float(cell)
    return None


def _forward(outcome: dict) -> Dict[str, Any]:
    """Read live nested assets[BTC/USD][+1h].ret_pct AND flat test/legacy keys."""
    out = {h: None for h in HORIZONS}
    if not outcome:
        return out
    assets = outcome.get("assets") or {}
    slot: Any = {}
    if isinstance(assets, dict) and assets:
        slot = assets.get("BTC/USD") or assets.get("BTC") or {}
        if not slot:
            first = next(iter(assets.values()), {})
            if isinstance(first, dict):
                slot = first
    if not isinstance(slot, dict):
        slot = {}
    for h in HORIZONS:
        short = HORIZON_SHORT[h]
        v = _cell_ret(slot.get(short))
        if v is None:
            raw = outcome.get(h)
            if raw is None:
                raw = outcome.get(f"btc_{h}")
            if isinstance(raw, dict):
                v = _cell_ret(raw)
            elif raw is not None:
                try:
                    v = float(raw)
                except (TypeError, ValueError):
                    v = None
        out[h] = v
    return out


def finalize(report: Dict[str, Any]) -> Dict[str, Any]:
    for key in ("by_strategy",):
        group = report.get(key) or {}
        for bucket in group.values():
            _means(bucket)
    if report.get("unassigned_or_other"):
        _means(report["unassigned_or_other"])
    return report


def _means(bucket: dict) -> None:
    for label, sum_k, n_k, n_out in (
        ("mean_fwd", "_sum", "_n", "n_fwd"),
        ("mean_fwd_after_take", "_sum_take", "_n_take", "n_fwd_after_take"),
        ("mean_fwd_after_skip", "_sum_skip", "_n_skip", "n_fwd_after_skip"),
        ("mean_fwd_after_wait", "_sum_wait", "_n_wait", "n_fwd_after_wait"),
        ("mean_fwd_after_skip_setup", "_sum_skip_setup", "_n_skip_setup", "n_fwd_after_skip_setup"),
        ("mean_fwd_after_filtered_idle", "_sum_filtered_idle", "_n_filtered_idle", "n_fwd_after_filtered_idle"),
    ):
        out = {}
        n_map = {}
        for h in HORIZONS:
            n = bucket.get(n_k, {}).get(h, 0)
            n_map[h] = n
            out[h] = None if not n else round(bucket[sum_k][h] / n, 4)
        bucket[label] = out
        bucket[n_out] = n_map
    for k in list(bucket):
        if k.startswith("_"):
            bucket.pop(k, None)


def attribute_print_ready(source: str = "live") -> Dict[str, Any]:
    return finalize(attribute(source=source))
