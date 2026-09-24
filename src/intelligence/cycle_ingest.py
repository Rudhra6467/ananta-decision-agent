"""Ingest a Hands all-cycle envelope into per-asset L2 + G5.

Does not invent bars. Does not copy BTC onto other names.
Does not grant paper_take / KEEP / exec. Does not count for M2.
Source of truth = envelope symbols[]/results[], not observation_log[-1].
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.intelligence.di_loop import VERSION as LOOP_VERSION
from src.intelligence.di_loop import run
from src.intelligence.hands_funnel import UNIVERSE, emit, _norm_asset

INGEST_VERSION = "cycle.ingest.v3"
OUT = Path("cycle_ingest.json")
FUNNEL_OUT = Path("hands_funnel_cycle.json")
LAB10 = ["BTC", "ETH", "SOL", "ADA", "DOGE", "AVAX", "BCH", "LINK", "LTC", "XRP"]
LOOK_PRIORITY = (
    "LOOKED_ISSUED",
    "LOOKED_SHADOW",
    "LOOKED_WAIT",
    "LOOKED_WATCH",
    "LOOKED_NOTHING_VALID",
)


def _truthy_setup(v: Any) -> bool:
    return v is True or v == "true" or v == "TRUE" or v == 1 or v == "1"


def _norm_regime(raw: Any) -> str | None:
    if raw is None:
        return None
    if isinstance(raw, dict):
        for k in ("asset", "market", "regime", "label", "name"):
            if raw.get(k):
                return _norm_regime(raw.get(k))
        return None
    s = str(raw).strip().upper().replace(" ", "_")
    alias = {
        "BULL": "TREND_UP",
        "BULLISH": "TREND_UP",
        "UP": "TREND_UP",
        "BEAR": "TREND_DOWN",
        "BEARISH": "TREND_DOWN",
        "DOWN": "TREND_DOWN",
        "NEUTRAL": "RANGE",
        "NORMAL": "RANGE",
    }
    s = alias.get(s, s)
    return s if s and s not in ("NONE", "NULL", "UNKNOWN", "") else None


def _regime_from_result(item: dict) -> str | None:
    hit = _norm_regime(item.get("regime"))
    if hit:
        return hit
    for row in item.get("strategy_observations") or []:
        if isinstance(row, dict):
            hit = _norm_regime(row.get("regime"))
            if hit:
                return hit
    for row in item.get("strategies") or []:
        if isinstance(row, dict):
            hit = _norm_regime(row.get("regime"))
            if hit:
                return hit
    return None


def _data_gap_reason(item: dict) -> str | None:
    status = str(item.get("status") or "")
    if status in ("no_market_data", "scan_staggered", "evaluate_symbol_failed"):
        return status
    for row in item.get("strategy_observations") or []:
        if isinstance(row, dict):
            skip = str(row.get("skip_reason") or "")
            if skip in ("no_market_data", "scan_staggered", "DATA_GAP", "missing_observations"):
                return skip
    return None


def _price_from_result(item: dict):
    for k in ("price", "close", "last"):
        if item.get(k) is not None:
            return item.get(k)
    snap = item.get("snapshot") or item.get("market") or {}
    if isinstance(snap, dict):
        for k in ("price", "close", "last"):
            if snap.get(k) is not None:
                return snap.get(k)
    return None


def observation_from_result(item: dict, *, cycle_id: str, ts: str, bar_tf: str) -> dict[str, Any]:
    symbol = str(item.get("symbol") or "")
    asset = _norm_asset(symbol)
    price = _price_from_result(item)
    obs_strats = []
    for row in item.get("strategy_observations") or item.get("strategies") or []:
        if not isinstance(row, dict):
            continue
        row = dict(row)
        if "strategy" not in row and row.get("strategy_id"):
            row["strategy"] = row.get("strategy_id")
        row["setup_detected"] = _truthy_setup(row.get("setup_detected"))
        obs_strats.append(row)
    regime = _regime_from_result(item)
    gap = _data_gap_reason(item)
    return {
        "schema": "observation_v0",
        "id": f"{cycle_id}.{asset or 'UNK'}",
        "ts": ts,
        "source": "hands_cycle_envelope",
        "asset": symbol or asset,
        "regime": regime,
        "bar_tf": bar_tf,
        "strategy_observations": obs_strats,
        "data_gap": gap,
        "system_truth": {
            "cycle_id": cycle_id,
            "symbol": symbol,
            "bar_tf": bar_tf,
            "status": item.get("status"),
            "strategy_observations": obs_strats,
            "regime": item.get("regime"),
        },
        "market_truth": {
            "assets": {symbol: {"price": price, "regime": regime}} if symbol else {},
        },
        "laws": {"invented": False, "copied_from_btc": False, "paper_take": False},
    }


def load_envelope(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text())
    if not isinstance(data, dict):
        raise ValueError("envelope_not_object")
    return data


def rows_from_envelope(env: dict[str, Any]) -> list[dict[str, Any]]:
    results = env.get("results") if isinstance(env.get("results"), list) else []
    symbols = env.get("symbols") if isinstance(env.get("symbols"), list) else []
    by_sym: dict[str, dict] = {}
    for item in results:
        if not isinstance(item, dict):
            continue
        sym = str(item.get("symbol") or "")
        if not sym:
            continue
        by_sym[_norm_asset(sym)] = dict(item)
    for item in symbols:
        if not isinstance(item, dict):
            continue
        raw = str(item.get("symbol") or "")
        key = _norm_asset(raw)
        if not key:
            continue
        if key not in by_sym:
            by_sym[key] = {"symbol": raw, "strategy_observations": item.get("strategies") or []}
        elif not by_sym[key].get("strategy_observations") and item.get("strategies"):
            by_sym[key]["strategy_observations"] = item.get("strategies")
    ordered: list[dict] = []
    seen = set()
    for name in LAB10:
        if name in by_sym:
            ordered.append(by_sym[name])
            seen.add(name)
    for name, item in by_sym.items():
        if name not in seen:
            ordered.append(item)
    return ordered


def _cycle_look_class(counts: dict[str, int], looked_n: int) -> dict[str, Any]:
    """LOOKED_PARTIAL means the universe was not fully looked. Mixed 10/10 is not PARTIAL."""
    never = int(counts.get("NEVER_LOOKED") or 0)
    if looked_n == 0 or never == len(UNIVERSE):
        return {"look_class": "NEVER_LOOKED", "mixed": False, "majority": "NEVER_LOOKED"}
    if looked_n < len(UNIVERSE) or never > 0:
        return {"look_class": "LOOKED_PARTIAL", "mixed": True, "majority": None}
    present = [k for k in LOOK_PRIORITY if int(counts.get(k) or 0) > 0]
    if not present:
        return {"look_class": "LOOKED_NOTHING_VALID", "mixed": False, "majority": "LOOKED_NOTHING_VALID"}
    majority = max(present, key=lambda k: (int(counts.get(k) or 0), -LOOK_PRIORITY.index(k)))
    mixed = len(present) > 1
    return {"look_class": majority, "mixed": mixed, "majority": majority}


def run_envelope(path: str | Path = "/tmp/cycle_all.json") -> dict[str, Any]:
    env = load_envelope(path)
    cycle_id = str(env.get("cycle_id") or "unknown")
    ts = str(env.get("as_of_time") or env.get("ran_at") or "")
    bar_tf = str(env.get("bar_tf") or "unknown")
    rows = rows_from_envelope(env)
    per_asset: dict[str, Any] = {}
    board: list[dict[str, Any]] = []
    stores: list[dict[str, Any]] = []
    for item in rows:
        asset = _norm_asset(item.get("symbol"))
        if asset not in UNIVERSE:
            continue
        obs = observation_from_result(item, cycle_id=cycle_id, ts=ts, bar_tf=bar_tf)
        out = run(obs)
        issued = str(out.get("issued") or "NO_TRADE")
        l2s = out.get("l2_state") or {}
        regime = l2s.get("regime") or obs.get("regime")
        gap = obs.get("data_gap")
        if regime in (None, "", "UNKNOWN") and gap:
            issued = "UNKNOWN"
        per_asset[asset] = {
            "asset": asset,
            "looked": True,
            "bars_evaluated": 1,
            "observations": 1,
            "partial_matches": 1 if out.get("best_id") else 0,
            "candidate_setups": 1 if out.get("best_id") else 0,
            "qualified_candidates": 1 if l2s.get("hunter_qualifying") or l2s.get("squeeze_qualifying") else 0,
            "issued": issued,
            "invented": False,
            "data_gap": gap,
            "regime_source": "hands" if _regime_from_result(item) else "insufficient",
        }
        board.append({
            "asset": asset,
            "regime": regime,
            "tf": l2s.get("tf"),
            "best": out.get("best_id"),
            "issued": issued,
            "why": out.get("why"),
            "data_gap": gap,
            "store": (out.get("decision_store") or {}).get("id"),
        })
        stores.append(out.get("decision_store") or {})
    looked = [a for a in UNIVERSE if per_asset.get(a, {}).get("looked")]
    gaps = []
    if [a for a in UNIVERSE if a not in per_asset]:
        gaps.append("envelope_missing_named_assets")
    extra = [_norm_asset(r.get("symbol")) for r in rows if _norm_asset(r.get("symbol")) not in UNIVERSE]
    extra = [x for x in extra if x]
    if extra:
        gaps.append("envelope_has_names_outside_lab10")
    insuff = [a for a in looked if per_asset[a].get("regime_source") == "insufficient"]
    if insuff:
        gaps.append("regime_insufficient_on_" + ",".join(insuff))
    funnel = emit({
        "cycle_id": cycle_id,
        "bar_tf": bar_tf,
        "last_bar_open": env.get("last_bar_open") or ts,
        "assets_named": looked,
        "assets_evaluated": len(looked),
        "assets_scanned_ok": len(looked),
        "timeframes": [bar_tf],
        "bars_evaluated": len(looked),
        "observations": len(looked),
        "partial_matches": sum(1 for a in looked if per_asset[a].get("partial_matches")),
        "candidate_setups": sum(1 for a in looked if per_asset[a].get("candidate_setups")),
        "qualified_candidates": sum(1 for a in looked if per_asset[a].get("qualified_candidates")),
        "knowledge_retrievals": len(looked),
        "ranked_candidates": len(looked),
        "decisions": len(looked),
        "paper_candidates": sum(1 for a in looked if per_asset[a].get("issued") == "SHADOW_PAPER"),
        "issued": "NO_TRADE",
        "looked": bool(looked),
        "coverage_gaps": gaps,
        "per_asset": per_asset,
    })
    agg = _cycle_look_class(funnel.get("look_class_counts") or {}, funnel.get("looked_asset_n") or 0)
    funnel["look_class"] = agg["look_class"]
    funnel["look_class_mixed"] = agg["mixed"]
    funnel["look_class_majority"] = agg["majority"]
    if agg["mixed"] and "mixed_issued_classes" not in funnel["coverage_gaps"]:
        funnel["coverage_gaps"].append("mixed_issued_classes")
    FUNNEL_OUT.write_text(json.dumps(funnel, indent=2, default=str))
    report = {
        "ok": True,
        "ingest_version": INGEST_VERSION,
        "loop_version": LOOP_VERSION,
        "cycle_id": cycle_id,
        "source": str(path),
        "universe_label": env.get("universe"),
        "n_envelope": len(rows),
        "assets_evaluated": funnel.get("assets_evaluated"),
        "looked_asset_n": funnel.get("looked_asset_n"),
        "look_class": funnel.get("look_class"),
        "look_class_mixed": funnel.get("look_class_mixed"),
        "look_class_majority": funnel.get("look_class_majority"),
        "look_class_counts": funnel.get("look_class_counts"),
        "coverage_gaps": funnel.get("coverage_gaps"),
        "board": board,
        "stores": [s.get("id") for s in stores],
        "paper_take": False,
        "keep": False,
        "exec": False,
        "counts_for_m2": False,
        "g8": "NOT_GRANTED",
    }
    OUT.write_text(json.dumps(report, indent=2, default=str))
    return report


def print_envelope(path: str | Path = "/tmp/cycle_all.json") -> dict[str, Any]:
    r = run_envelope(path)
    print(f"\nCYCLE INGEST  {r.get('ingest_version')}  loop={r.get('loop_version')}")
    print("=" * 64)
    print(f"  cycle_id={r.get('cycle_id')}  source={r.get('source')}")
    print(f"  label={r.get('universe_label')}  envelope_n={r.get('n_envelope')}")
    print(f"  evaluated={r.get('assets_evaluated')} looked_n={r.get('looked_asset_n')}")
    print(f"  look_class={r.get('look_class')} mixed={r.get('look_class_mixed')} majority={r.get('look_class_majority')}")
    print(f"  counts={r.get('look_class_counts')}")
    print(f"  gaps={r.get('coverage_gaps')}")
    print("-" * 64)
    print(f"  {'ASSET':<6} {'REGIME':<14} {'ISSUED':<14} BEST")
    for row in r.get("board") or []:
        gap = f"  gap={row.get('data_gap')}" if row.get("data_gap") else ""
        print(f"  {row.get('asset',''):<6} {str(row.get('regime') or '-'):<14} {str(row.get('issued') or '-'):<14} {row.get('best')}{gap}")
    print("-" * 64)
    print("  paper_take=False keep=False exec=False m2=False G8=NOT_GRANTED")
    print(f"  saved={OUT} funnel={FUNNEL_OUT}")
    print("=" * 64)
    print()
    return r
