"""Decision / outcome attribution.

Joins observation_v0 rows to per-strategy TAKE / SKIP / WAIT and forward path.
This is the engine H3 will use. It does not *run* S5-H3.

Never mix bollinger TAKE-eq into hunter. BTC path ≠ strategy PnL.
"""
from __future__ import annotations

from typing import Any, Dict, List

from src.intelligence.schema import WAVE_A, _norm_action
from src.tools.observation_log import OBSERVATION_LOG, REPLAY_LOG, _read_jsonl

HORIZONS = ("fwd_15m_pct", "fwd_1h_pct", "fwd_4h_pct")


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
            "note": f"{path} missing or empty. Not a KEEP/CUT. S5-H3 still parked.",
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
        "note": (
            "Attribution engine only. S5-H3 is PENDING_TAPE and is not running. "
            "Do not read bollinger TAKE-eq as Wave A working. Historical TAKE-eq ≠ KEEP."
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
        "mean_fwd": {h: None for h in HORIZONS},
        "mean_fwd_after_take": {h: None for h in HORIZONS},
        "mean_fwd_after_skip": {h: None for h in HORIZONS},
        "mean_fwd_after_wait": {h: None for h in HORIZONS},
        "_sum": {h: 0.0 for h in HORIZONS},
        "_n": {h: 0 for h in HORIZONS},
        "_sum_take": {h: 0.0 for h in HORIZONS},
        "_n_take": {h: 0 for h in HORIZONS},
        "_sum_skip": {h: 0.0 for h in HORIZONS},
        "_n_skip": {h: 0 for h in HORIZONS},
        "_sum_wait": {h: 0.0 for h in HORIZONS},
        "_n_wait": {h: 0 for h in HORIZONS},
    }


def _accumulate(bucket: dict, obs_row: dict, outcome: dict) -> None:
    bucket["n_rows"] += 1
    if obs_row.get("setup_detected"):
        bucket["n_setup"] += 1
    skip = str(obs_row.get("skip_reason") or "").upper()
    if skip == "REGIME_FILTERED":
        bucket["n_regime_filtered"] += 1
    dec = _classify(obs_row)
    bucket[f"n_{dec.lower()}"] += 1
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


def _classify(obs_row: dict) -> str:
    skip = str(obs_row.get("skip_reason") or "").upper()
    dec = _norm_action(obs_row.get("decision") or "")
    setup = bool(obs_row.get("setup_detected"))
    if skip == "REGIME_FILTERED" or dec == "SKIP":
        return "SKIP"
    if setup or dec == "TAKE":
        return "TAKE"
    return "WAIT"


def _forward(outcome: dict) -> Dict[str, Any]:
    if not outcome:
        return {h: None for h in HORIZONS}
    return {
        "fwd_15m_pct": outcome.get("fwd_15m_pct", outcome.get("btc_fwd_15m_pct")),
        "fwd_1h_pct": outcome.get("fwd_1h_pct", outcome.get("btc_fwd_1h_pct")),
        "fwd_4h_pct": outcome.get("fwd_4h_pct", outcome.get("btc_fwd_4h_pct")),
    }


def finalize(report: Dict[str, Any]) -> Dict[str, Any]:
    for key in ("by_strategy",):
        group = report.get(key) or {}
        for bucket in group.values():
            _means(bucket)
    if report.get("unassigned_or_other"):
        _means(report["unassigned_or_other"])
    return report


def _means(bucket: dict) -> None:
    for label, sum_k, n_k in (
        ("mean_fwd", "_sum", "_n"),
        ("mean_fwd_after_take", "_sum_take", "_n_take"),
        ("mean_fwd_after_skip", "_sum_skip", "_n_skip"),
        ("mean_fwd_after_wait", "_sum_wait", "_n_wait"),
    ):
        out = {}
        for h in HORIZONS:
            n = bucket.get(n_k, {}).get(h, 0)
            out[h] = None if not n else round(bucket[sum_k][h] / n, 4)
        bucket[label] = out
    for k in list(bucket):
        if k.startswith("_"):
            bucket.pop(k, None)


def attribute_print_ready(source: str = "live") -> Dict[str, Any]:
    return finalize(attribute(source=source))
